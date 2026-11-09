"""Revisor visual: o Gemini (gratuito) olha cada cena e confere se a imagem combina com o trecho narrado.

Se a imagem estiver fora do tema, tiver texto/letras escritas ou corpos deformados, a cena é
gerada de novo pela IA de imagem com um prompt corrigido (uma tentativa por cena).
Sem GEMINI_API_KEY ou em caso de erro, o vídeo segue normalmente (a revisão é só uma camada extra).
"""
import base64
import io
import json
import re
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

from estudio.base import gemini_flash, log
from estudio.agentes import visual

API = "https://generativelanguage.googleapis.com/v1beta"
MODELO = os.getenv("GEMINI_VISAO", "")

PERGUNTA = """Você revisa imagens de um vídeo vertical. Canal: {canal}.
Trecho narrado nesta cena: "{trecho}"
Descrição pedida para a imagem: "{prompt}"
Regras do canal: {regras}

A imagem serve para essa cena? Reprove somente se houver um problema claro:
- não tem relação com o trecho (lugar, época ou assunto errado);
- tem texto, letras, logotipo ou marca d'água visível;
- pessoas ou animais deformados (rostos derretidos, mãos/membros errados);
- quebra as regras do canal.
Responda só com JSON: {{"ok": true|false, "motivo": "curto", "novo_prompt": "prompt em inglês corrigido, se ok=false"}}"""


PERGUNTA_RIGOROSA = """Você é o controle de qualidade rigoroso de um filme bíblico cinematográfico. Canal: {canal}.
Trecho narrado nesta cena: "{trecho}"
Descrição pedida para a imagem: "{prompt}"
Época e lugar desta cena: {epoca}
Regras do canal: {regras}

Examine a imagem inteira com atenção, incluindo cantos, fundo e horizonte, e responda a cada item:
1. Há QUALQUER objeto moderno? Exemplos: poste de luz, luminária, fio elétrico, estrada asfaltada ou pavimentada,
   cerca de arame, banco ou mesa de madeira moderna, celular, telefone, papel/cartão, garrafa, copo de vidro,
   telhado vermelho de telha moderna, prédio, casa moderna, carro, roupa moderna (terno, jaqueta, calça jeans).
2. Há rosto humano visível, ou pessoa grande/em primeiro plano como assunto (mãos são permitidas só se pedidas)?
3. Há multidão, fila de pessoas ou gente que a descrição não pediu?
4. A arquitetura e a paisagem combinam com a época e o lugar DESTA cena (indicados acima)?
   Ex.: colunas egípcias numa cena no Egito estão certas; num acampamento de pastores em Canaã, não.
5. Há corpo, mão ou objeto deformado, texto, letras ou marca d'água?
6. A imagem representa o que a descrição pede (os elementos principais estão lá)?
Itens 1, 2, 3 e 5: na dúvida, reprove. Estátuas com rosto também contam como rosto.
Itens 4 e 6: reprove só se estiver claramente errado (cultura ou época trocada, elemento principal ausente).
Não exija nada além da descrição: a imagem não precisa contar a história inteira do trecho.
Responda só com JSON: {{"ok": true|false, "motivo": "curto, citando o item que falhou", "novo_prompt": "prompt em inglês corrigido e mais simples (sem mencionar pessoas que não devem aparecer), se ok=false"}}"""


def _miniatura(img: Path, largura: int = 432) -> str:
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(img), "-vf", f"scale={largura}:-2",
                          "-q:v", "5", "-f", "mjpeg", "-"], capture_output=True, check=True).stdout
    return base64.b64encode(out).decode()


def _avaliar(chave, canal, cena, img, rigoroso=False) -> dict:
    texto = (PERGUNTA_RIGOROSA if rigoroso else PERGUNTA).format(canal=canal["nome"], trecho=cena.get("trecho", ""),
                            epoca=cena.get("epoca_imagem") or canal.get("epoca_imagem", "a da narração"),
                            prompt=cena.get("prompt_imagem", ""),
                            regras=canal.get("regra_visual_pessoas", "nenhuma"))
    corpo = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": _miniatura(img, 896 if rigoroso else 432)}},
                                     {"text": texto}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    # o "lite" responde bem mais rápido e basta para checar tema/texto/deformações
    modelos = [MODELO or "gemini-flash-lite-latest", gemini_flash(), "gemini-flash-latest"]
    if rigoroso:  # filmes: o modelo mais forte primeiro (o lite deixava passar poste, celular, terno)
        modelos = [gemini_flash(), "gemini-flash-latest", "gemini-flash-lite-latest"]
    r = None
    for modelo in dict.fromkeys(modelos):  # tenta o mais novo; se estiver sobrecarregado, outro
        for espera in (0, 8):
            time.sleep(espera)
            c = corpo
            if re.match(r"gemini-3", modelo):  # modelos 3.x pensam muito por padrão: checklist não precisa
                c = {**corpo, "generationConfig": {**corpo["generationConfig"], "thinkingConfig": {"thinkingLevel": "low"}}}
            try:
                r = requests.post(f"{API}/models/{modelo}:generateContent", params={"key": chave}, json=c,
                                  timeout=90 if rigoroso else 40)
                if r.status_code == 400 and c is not corpo:  # modelo não aceita thinkingLevel: manda sem
                    r = requests.post(f"{API}/models/{modelo}:generateContent", params={"key": chave}, json=corpo,
                                      timeout=90 if rigoroso else 40)
            except requests.RequestException:
                continue  # demorou: tenta de novo / outro modelo
            if r.ok:
                v = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
                if isinstance(v, list):  # às vezes o Gemini devolve [ {...} ]
                    v = next((x for x in v if isinstance(x, dict)), {"ok": False, "motivo": "resposta inválida"})
                return v
            if r.status_code not in (429, 500, 503):
                break
    raise RuntimeError(f"HTTP {r.status_code}" if r is not None else "sem resposta do Gemini")


def revisar(canal: dict, cenas: list[dict], imagens: list[Path]) -> list[str]:
    """Revisa e corrige as cenas no lugar. Devolve avisos para a Issue."""
    chave = os.getenv("GEMINI_API_KEY")
    if not chave or os.getenv("SEM_REVISAO_VISUAL"):
        return []
    avisos, trocadas, falhas = [], 0, 0
    prazo = time.time() + 8 * 60  # a revisão nunca segura o vídeo por mais de ~8 minutos
    log("revisor-visual", f"modelo {MODELO or 'gemini-flash-lite-latest'} (reserva {gemini_flash()})")
    for i, (cena, img) in enumerate(zip(cenas, imagens)):
        if cena.get("imagem") or (i == 0 and canal.get("imagem_abertura")):
            continue  # imagem escolhida a dedo
        if time.time() > prazo:
            avisos.append(f"Revisão visual parou na cena {i + 1} por tempo — confira as cenas seguintes.")
            break
        try:
            v = _avaliar(chave, canal, cena, img)
        except Exception as e:  # noqa: BLE001
            log("revisor-visual", f"cena {i + 1}: não revisada ({e})")
            falhas += 1
            if falhas >= 2:  # Gemini fora do ar: não atrasa o vídeo
                avisos.append("Revisão visual não rodou (Gemini indisponível) — confira as imagens.")
                break
            continue
        falhas = 0  # só desiste após 2 falhas SEGUIDAS
        if v.get("ok", True):
            log("revisor-visual", f"cena {i + 1}: ok")
            time.sleep(4)  # respeita o limite gratuito por minuto
            continue
        log("revisor-visual", f"cena {i + 1}: reprovada ({v.get('motivo')}) — gerando outra")
        nova = dict(cena, prompt_imagem=v.get("novo_prompt") or cena.get("prompt_imagem", ""))
        tmp = img.with_name(img.stem + "_nova.jpg")
        if visual.gerar_uma(canal, nova, tmp, semente=int(time.time()) % 10**6):
            try:
                v2 = _avaliar(chave, canal, nova, tmp)
            except Exception:  # noqa: BLE001
                v2 = {"ok": True}
            if v2.get("ok", True):
                shutil.move(tmp, img)
                trocadas += 1
                log("revisor-visual", f"cena {i + 1}: substituída")
                continue
        avisos.append(f"Cena {i + 1}: a revisão visual apontou \"{v.get('motivo')}\" e não achou substituta — confira.")
        time.sleep(4)
    if trocadas:
        avisos.append(f"Revisor visual trocou {trocadas} cena(s) que estavam fora do tema.")
    return avisos
