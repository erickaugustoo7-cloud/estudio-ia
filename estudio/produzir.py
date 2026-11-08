"""Orquestrador de produção: pauta → roteiro → revisão → voz → imagens → vídeo → fila de aprovação.

Uso:
  python -m estudio.produzir --canal espaco
  python -m estudio.produzir --canal biblico --pauta "O Salmo 91"
  python -m estudio.produzir --canal espaco --roteiro meu_roteiro.json --sem-envio --sem-issue   (teste local)
"""
import argparse
import json
import os
import random
import re
import subprocess
from datetime import datetime
from pathlib import Path

from estudio.base import SAIDA, carregar_canal, log
from estudio.agentes import (diretor, montador, montador_hf, narrador, publicador, revisor,
                             revisor_visual, roteirista, visual)

MARCA_INI, MARCA_FIM = "<!--DADOS", "DADOS-->"


def montar_texto_post(canal: dict, roteiro: dict) -> str:
    legenda = roteiro["legenda"].strip()
    tags_na_legenda = re.findall(r"#\w+", legenda)
    legenda = re.sub(r"\s*#\w+", "", legenda).strip()  # hashtags ficam só no bloco final
    tags = []
    for t in canal["hashtags_fixas"] + tags_na_legenda + roteiro.get("hashtags", []):
        t = "#" + t.lstrip("#").replace(" ", "")
        if t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    return f"{legenda}\n\n{' '.join(tags[:8])}"


def abrir_issue(canal, roteiro, texto_post, pasta, duracao, problemas, pauta, no_telegram) -> str:
    run_id = os.getenv("GITHUB_RUN_ID", "")
    url_run = f"{os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{run_id}"
    dados = {"canal": canal["slug"], "run_id": run_id, "artefato": f"video-{canal['slug']}-{run_id}",
             "pasta": pasta.name, "texto_post": texto_post}
    onde = "📱 **Já está no seu Telegram.** " if no_telegram else ""
    avisos = "\n".join(f"- ⚠️ {p}" for p in problemas) or "- Nenhum"
    fontes = "\n".join(f"- {f}" for f in roteiro.get("fontes", [])) or "- —"
    corpo = f"""## 🎬 {roteiro['titulo']}
**Canal:** {canal['nome']} · **Duração:** {duracao:.0f}s · **Estilo visual:** {canal.get('estilo_nome', 'padrão')} · **Pauta:** {pauta}

### ▶️ {onde}[Baixar pelo GitHub (artefato da execução)]({url_run})

### Legenda do post
```
{texto_post}
```

### Narração (confira antes de aprovar)
<details><summary>Ler o texto narrado</summary>

{roteiro['narracao']}
</details>

### Apontamentos do Revisor
{avisos}

### Fontes
{fontes}

---
**Para publicar no Instagram:** etiqueta `aprovado`. **Para descartar:** etiqueta `rejeitado`.
**TikTok:** poste manualmente o vídeo que chegou no Telegram, com a legenda acima. Marque "Conteúdo gerado por IA".
Quer mudar a legenda? Edite o campo `texto_post` abaixo antes de aprovar.

<details><summary>Dados da publicação (editável)</summary>

{MARCA_INI}
```json
{json.dumps(dados, ensure_ascii=False, indent=2)}
```
{MARCA_FIM}
</details>
"""
    titulo = f"[{canal['slug']}] {roteiro['titulo']}"
    for nome, cor in (("aprovacao", "FBCA04"), (f"canal:{canal['slug']}", "1D76DB")):
        subprocess.run(["gh", "label", "create", nome, "--color", cor, "--force"], capture_output=True)
    out = subprocess.run(
        ["gh", "issue", "create", "--title", titulo, "--body", corpo,
         "--label", "aprovacao", "--label", f"canal:{canal['slug']}"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canal", required=True)
    ap.add_argument("--pauta")
    ap.add_argument("--roteiro", help="JSON de roteiro pronto (pula Diretor/Roteirista/Revisor)")
    ap.add_argument("--sem-envio", action="store_true", help="não envia ao Telegram")
    ap.add_argument("--sem-issue", action="store_true")
    a = ap.parse_args()

    canal = carregar_canal(a.canal)
    pasta = SAIDA / f"{a.canal}_{datetime.now():%Y%m%d_%H%M%S}"
    pasta.mkdir(parents=True)
    problemas = []

    if a.roteiro:
        roteiro = json.loads(Path(a.roteiro).read_text(encoding="utf-8"))
        pauta = a.pauta or roteiro["titulo"]
    else:
        pauta = diretor.proxima_pauta(canal, a.pauta)
        roteiro = roteirista.escrever(canal, pauta)
        roteiro, problemas = revisor.revisar(canal, roteiro)
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")

    canal_voz = {**canal, "vozes": [roteiro["voz"]]} if roteiro.get("voz") else canal  # voz fixa no roteiro
    if roteiro.get("duracao_max") and canal_voz.get("gemini_tts"):  # formato curto (ex.: oração de 30 s)
        canal_voz = {**canal_voz, "gemini_tts": {**canal_voz["gemini_tts"], "duracao_max": roteiro["duracao_max"]}}
    mp3, palavras, dur = narrador.narrar(canal_voz, roteiro["narracao"], pasta)
    if dur < 61 and not a.roteiro:
        # o Revisor pode ter encurtado: estende pelo ritmo real da voz e narra de novo (uma vez)
        por_seg = len(roteiro["narracao"].split()) / max(dur, 1)
        roteiro = roteirista.estender(canal, roteiro, int((64 - dur) * por_seg) + 10)
        (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")
        mp3, palavras, dur = narrador.narrar(canal_voz, roteiro["narracao"], pasta)
    if dur < 61 and not roteiro.get("duracao_max"):
        problemas.append(f"Vídeo com {dur:.0f}s — abaixo de 1 minuto não conta no Creator Rewards do TikTok.")

    estilos = canal.get("estilos_visuais") or {}
    if estilos:
        nome_estilo = os.getenv("ESTILO_VISUAL") or roteiro.get("estilo") or random.choice(sorted(estilos))
        if nome_estilo in estilos:
            canal = {**canal, "estilo_visual": estilos[nome_estilo], "estilo_nome": nome_estilo}
            log("orquestrador", f"estilo visual: {nome_estilo}")
    imagens = visual.gerar_imagens(canal, roteiro["cenas"], pasta)
    problemas += revisor_visual.revisar(canal, roteiro["cenas"], imagens)
    if visual.RESERVAS:
        problemas.append(f"Cenas {', '.join(map(str, visual.RESERVAS))} não vieram da IA de imagem "
                         "(foram repetidas ou de reserva) — confira antes de postar.")
    tempos = montador.tempos_das_cenas(roteiro["cenas"], palavras, dur)
    video = None
    if canal.get("motor_video", "hyperframes") == "hyperframes":
        try:
            video = montador_hf.montar(canal, roteiro.get("gancho_tela") or roteiro["titulo"], imagens, tempos, mp3, palavras, dur, pasta)
        except Exception as e:  # noqa: BLE001 — qualquer falha cai no motor FFmpeg
            log("montador", f"HyperFrames falhou ({e}); usando FFmpeg")
            problemas.append("Render HyperFrames falhou — vídeo montado com o motor simples (FFmpeg).")
    if video is None:
        legendas = montador.gerar_legendas(palavras, pasta / "legendas.ass")
        video = montador.montar(canal, imagens, tempos, mp3, legendas, pasta)

    montador.normalizar_volume(video)
    texto_post = montar_texto_post(canal, roteiro)
    (pasta / "post.txt").write_text(texto_post, encoding="utf-8")

    no_telegram = False
    if not a.sem_envio:
        no_telegram = publicador.telegram_video(
            video, f"🎬 [{canal['nome']}] {roteiro['titulo']} · {dur:.0f}s · estilo {canal.get('estilo_nome', 'padrão')}", texto_post)
    if not a.sem_issue:
        link = abrir_issue(canal, roteiro, texto_post, pasta, dur, problemas, pauta, no_telegram)
        log("orquestrador", f"aguardando aprovação: {link}")
        publicador.telegram_mensagem(f"✅ Aprovar (Instagram, Facebook e YouTube): {link}")
    if not a.roteiro:
        diretor.registrar_no_historico(canal["slug"], roteiro["titulo"], pauta)
    log("orquestrador", f"concluído em {pasta}")


if __name__ == "__main__":
    main()
