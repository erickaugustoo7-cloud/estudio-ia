"""Anima as cenas de um roteiro animado com o Wan 2.2 (FastWan 5B) na GPU grátis do Kaggle.

1. Gera a ilustração de cada cena (estilo desenho) com as fontes de imagem do sistema.
2. Monta um "kernel" do Kaggle (script Python) com as imagens embutidas e o envia pela API.
3. O Kaggle instala o Wan2GP (open source), baixa o modelo e anima cada imagem (~4 s por cena).
4. Espera terminar, baixa os clipes e manda a sequência para o Telegram.

Uso:  python -m estudio.kaggle_wan roteiros_animados/tempestade.json
Precisa dos segredos KAGGLE_USERNAME e KAGGLE_KEY (conta com telefone verificado).
"""
import base64
import shutil
import json
import re
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from estudio.base import SAIDA, carregar_canal, log
from estudio.agentes import publicador, visual

ESTILO = ("cinematic photorealistic epic film still, dramatic volumetric god rays, floating dust particles, deep chiaroscuro, "
          "muted earthy tones, vertical 9:16")
REGRA = ("Jesus and all people only seen from behind, as dark silhouettes or tiny figures far away, faces never visible. "
         "Only the characters described, no crowd, no extra people in the background. "
         "Strictly first century objects: clay and stone only, no glass cups, no bottles, nothing modern. "
         "Reject random objects that were not requested (bottles, potted plants, hanging lamps, furniture, statues) "
         "and architecture from the wrong culture or period (for example Chinese pagodas in Babylon)")
SLUG = "estudio-animacao"
# assinatura no rodapé, igual à dos outros vídeos (branca 70%, espaçada)
ESTILO_ASSINATURA = ("Style: Sig,DejaVu Sans,30,&H4DFFFFFF,&H4DFFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,6,0,1,2,1,2,"
                     "70,70,110,1")

SCRIPT_KAGGLE = r'''
import base64, shutil, json, os, subprocess, sys, time
from pathlib import Path
t0 = time.time()
def sh(cmd, **kw):
    print(">>", cmd if isinstance(cmd, str) else " ".join(cmd), flush=True)
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-4000:], flush=True)
        raise SystemExit(f"falhou: {cmd}")
    return r.stdout
print(sh("nvidia-smi"), flush=True)
CENAS = json.loads(base64.b64decode("__CENAS__"))
OUT = Path("/kaggle/working/clipes"); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/kaggle/temp"); TMP.mkdir(parents=True, exist_ok=True)
ROOT = TMP / "Wan2GP"
sh(["git", "clone", "-q", "--depth", "1", "https://github.com/deepbeepmeep/Wan2GP.git", str(ROOT)])
sh("apt-get update -qq && apt-get install -y -qq --no-install-recommends ffmpeg libglib2.0-0 libgl1 libportaudio2")
import torch
cons = TMP / "constraints.txt"
linhas = [f"torch=={torch.__version__.split('+')[0]}"]
for nome in ("torchvision", "torchaudio"):
    try:
        linhas.append(f"{nome}=={__import__(nome).__version__.split('+')[0]}")
    except Exception:
        pass
cons.write_text("\n".join(linhas) + "\n")
env = {**os.environ, "PIP_NO_CACHE_DIR": "1", "HF_HOME": str(TMP / "hf"), "XDG_CACHE_HOME": str(TMP / "cache")}
os.environ.update(env)
sh([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt"), "-c", str(cons)], env=env)
alvo = ROOT / "preprocessing/matanyone/tools/interact_tools.py"
if alvo.exists():
    alvo.write_text(alvo.read_text().replace("matplotlib.use('TkAgg')", "matplotlib.use('Agg')"))
print(f"instalação ok em {time.time() - t0:.0f}s", flush=True)
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
from shared.api import init
session = init(root=ROOT, output_dir=OUT, cli_args=["--attention", "sdpa", "--profile", "5"])
rel = {}
for i, c in enumerate(CENAS):
    ini = time.time()
    if c.get("tipo") == "imagem":  # ilustração com o Z-Image Turbo (Apache 2.0)
        s = {"model_type": c.get("modelo", "z_image"), "prompt": c["prompt"], "resolution": c.get("resolucao", "768x1344"),
             "num_inference_steps": c.get("passos", 8), "guidance_scale": 0, "seed": c.get("seed", 42), "batch_size": 1}
    else:  # animação com o Wan 2.2 FastWan
        img = TMP / f"cena_{i}.jpg"
        img.write_bytes(base64.b64decode(c["img"]))
        try:
            from PIL import Image
            w, h = (int(x) for x in c.get("resolucao", "704x1280").split("x"))
            Image.open(img).convert("RGB").resize((w, h), Image.LANCZOS).save(img, quality=95)
        except Exception as e:
            print("ampliar imagem:", e, flush=True)
        s = {"model_type": "ti2v_2_2_fastwan", "prompt": c["prompt"], "image_prompt_type": "S",
             "image_start": str(img), "resolution": c.get("resolucao", "704x1280"), "video_length": c.get("quadros", 97),
             "num_inference_steps": c.get("passos", 4), "guidance_scale": 1, "flow_shift": 3, "seed": c.get("seed", 42),
             "negative_prompt": c.get("negativo", "")}
    try:
        res = session.submit_task(s).result()
    except Exception as e:
        print(f"item {i}: exceção {e}", flush=True)
        rel[i] = {"ok": False, "erro": str(e)[:300]}
        continue
    arqs = [str(f) for f in getattr(res, "generated_files", [])]
    print(f"item {i} ({c.get('tipo', 'video')}): ok={res.success} {time.time() - ini:.0f}s {arqs}", flush=True)
    if not res.success:
        for e in res.errors:
            print("  erro:", e.message, flush=True)
    nome = c.get("nome", f"clipe_{i}")
    for f in arqs:
        ext = Path(f).suffix.lower()
        if ext in (".mp4", ".png", ".jpg", ".jpeg", ".webp"):
            Path(f).rename(OUT / f"{nome}{ext}")
            break
    rel[i] = {"ok": res.success, "segundos": round(time.time() - ini)}
(OUT / "relatorio.json").write_text(json.dumps({"total_s": round(time.time() - t0), "cenas": rel}))
print("FIM", json.dumps(rel), flush=True)
'''


def _kaggle(*args, check=True) -> str:
    r = subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"kaggle {' '.join(args)}: {r.stdout[-800:]} {r.stderr[-800:]}")
    return r.stdout + r.stderr


def _ts(t: float) -> str:
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def _dur(arq: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                                capture_output=True, text=True).stdout.strip() or 0)


def _rodar_kaggle(cenas: list, pasta: Path, etapa: str = "video") -> tuple[Path, str]:
    usuario = os.environ["KAGGLE_USERNAME"]
    kdir = pasta / f"kernel_{etapa}"
    kdir.mkdir()
    pacote = base64.b64encode(json.dumps(cenas).encode()).decode()
    (kdir / "script.py").write_text(SCRIPT_KAGGLE.replace("__CENAS__", pacote), encoding="utf-8")
    meta = {"id": f"{usuario}/{SLUG}", "title": SLUG, "code_file": "script.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "machine_shape": os.getenv("KAGGLE_MAQUINA", "NvidiaTeslaT4"),
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (kdir / "kernel-metadata.json").write_text(json.dumps(meta))
    log("wan", f"script: {(kdir / 'script.py').stat().st_size / 1024:.0f} KB")
    # Se uma sessão anterior (ex.: produção cancelada no GitHub) ainda roda no Kaggle, o push é recusado (400):
    # espera ela terminar antes de enviar.
    for _ in range(45):
        st = _kaggle("kernels", "status", f"{usuario}/{SLUG}", check=False).lower()
        if not any(x in st for x in ("running", "queued")):
            break
        log("wan", f"sessão anterior ainda ativa no Kaggle ({st.strip()[-40:]}) — aguardando")
        time.sleep(120)
    for tentativa in range(6):
        try:
            log("wan", _kaggle("kernels", "push", "-p", str(kdir)).strip())
            break
        except RuntimeError as e:
            if tentativa == 5:
                raise
            log("wan", f"push recusado ({str(e)[-200:]}); nova tentativa em 5 min")
            if tentativa == 1:  # sem escolher a GPU (o Kaggle escolhe a disponível)
                meta.pop("machine_shape", None)
                (kdir / "kernel-metadata.json").write_text(json.dumps(meta))
            time.sleep(300)
    inicio, status = time.time(), ""
    while time.time() - inicio < float(os.getenv("WAN_LIMITE_MIN", "150")) * 60:
        time.sleep(60)
        status = _kaggle("kernels", "status", f"{usuario}/{SLUG}", check=False)
        log("wan", f"{(time.time() - inicio) / 60:.0f} min — {status.strip()[-60:]}")
        if any(x in status.lower() for x in ("complete", "error", "cancel")):
            break
    saida = pasta / f"kaggle_{etapa}"
    saida.mkdir()
    _kaggle("kernels", "output", f"{usuario}/{SLUG}", "-p", str(saida), check=False)
    for lg in saida.glob("*.log"):
        texto = lg.read_text(errors="ignore")
        try:  # o log do Kaggle vem em JSON (lista de {stream_name, data})
            texto = "".join(x.get("data", "") for x in json.loads(texto))
        except Exception:  # noqa: BLE001
            pass
        (pasta / f"kaggle_log_{etapa}.txt").write_text(texto)
        print("\n".join(texto.splitlines()[-40:]))
    rel = next(saida.rglob("relatorio.json"), None)
    log("wan", f"status final: {status.strip()[-60:]} · {len(list(saida.rglob('*.*')))} arquivo(s)")
    return saida, rel.read_text() if rel else ""


MOVIMENTO_PERGUNTA = """You write motion prompts for an image-to-video model (Wan 2.2) that animates THIS exact image.
Desired feel for the scene: "{desejado}"
Rules: describe ONLY elements that are clearly visible in the image; never add people, animals or objects that are not
there; people must stay completely still and keep facing the same direction (never turning around, never looking at the
camera, no head movement, no new poses, no bending, no splitting); prefer gentle natural motion: cloth and hair
in the breeze, light and rays, clouds, water, leaves, particles, a slow camera push-in. One short English sentence, max 45 words.
Answer only JSON: {{"movimento": "..."}}"""


def _movimento(img: Path, desejado: str) -> str:
    """O Gemini olha a ilustração pronta e descreve um movimento só com o que está nela (evita o Wan inventar gente)."""
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        return desejado
    try:
        import requests
        from estudio.agentes.revisor_visual import API, _miniatura
        from estudio.base import gemini_flash
        corpo = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": _miniatura(img)}},
                                         {"text": MOVIMENTO_PERGUNTA.format(desejado=desejado)}]}],
                 "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
        for modelo in dict.fromkeys(["gemini-flash-lite-latest", gemini_flash(), "gemini-flash-latest"]):
            r = requests.post(f"{API}/models/{modelo}:generateContent", params={"key": chave}, json=corpo, timeout=40)
            if r.ok:
                mov = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])["movimento"]
                log("wan", f"movimento ({img.stem}): {mov}")
                return mov
    except Exception as e:  # noqa: BLE001
        log("wan", f"prompt de movimento automático falhou ({e})")
    return desejado


CLIPE_PERGUNTA = """These are 3 frames (start, middle, end) of a short animated clip for a Christian channel.
Intended scene: "{cena}"
Reject (ok=false) if ANY frame shows: a visible human face (front or profile) or a deformed/melted face or body,
a person turning toward the camera, people or animals appearing that are not in the first frame, extra or melted limbs,
ANY modern object anywhere in the frame (lamp posts, street lights, electric wires, paved or asphalt roads, phones,
paper cards, glass cups, bottles, modern benches or tables, modern buildings or red tile roofs, cars),
modern clothing (suits, jackets, jeans), crowds or lines of people not described in the scene,
text or watermark, or heavy flicker/morphing between frames. Check corners and background carefully.
Small dark silhouettes seen from behind are fine. Answer only JSON: {{"ok": true/false, "motivo": "curto, em português"}}"""


def _checar_clipe(clipe: Path, cena: str) -> dict:
    """O Gemini olha 3 quadros do clipe animado e reprova rostos, gente surgindo, deformações e objetos modernos."""
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        return {"ok": True}
    try:
        import requests
        from estudio.agentes.revisor_visual import API
        from estudio.base import gemini_flash
        d = _dur(clipe)
        partes = []
        for k, frac in enumerate((0.1, 0.5, 0.92)):
            q = clipe.with_name(f"{clipe.stem}_q{k}.jpg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{d * frac:.2f}", "-i", str(clipe), "-frames:v", "1",
                            "-vf", "scale=640:-1", "-q:v", "3", str(q)], check=True)
            partes.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(q.read_bytes()).decode()}})
        corpo = {"contents": [{"parts": partes + [{"text": CLIPE_PERGUNTA.format(cena=cena)}]}],
                 "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        for modelo in dict.fromkeys([gemini_flash(), "gemini-flash-latest", "gemini-flash-lite-latest"]):
            r = requests.post(f"{API}/models/{modelo}:generateContent", params={"key": chave}, json=corpo, timeout=60)
            if r.ok:
                v = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
                if isinstance(v, list):
                    v = next((x for x in v if isinstance(x, dict)), {"ok": False})
                return v
    except Exception as e:  # noqa: BLE001
        log("wan", f"checagem do clipe falhou ({e})")
    return {"ok": False, "motivo": "checagem indisponível — por segurança vira ilustração com movimento de câmera"}


_SEM_GENTE = re.compile(r",?\s*\b(no people|nobody[^,.]*|no faces?|faces? (?:not|never) visible|no crowd|no extra people[^,.]*|"
                        r"(?:tiny |small )?(?:distant )?(?:dark )?silhouettes? of [^,.]*|seen from behind|no modern objects|no glass)\b", re.I)


def _prompt_imagem(base: str, estilo: str, vazia: bool = True,
                   epoca: str = "Strictly first century objects of clay, stone, wood and cloth") -> str:
    """O Z-Image não tem prompt negativo: escrever "no people" faz ele DESENHAR gente. Tira essas menções e descreve
    a cena como vazia (natureza-morta/ambiente) quando não há mãos em cena."""
    limpo = _SEM_GENTE.sub("", base).replace(" ,", ",").strip(" ,.")
    if re.search(r"\bhands?\b|\barms?\b", limpo, re.I):
        extra = "close-up framing on the hands and objects only, cropped at the wrists"
    elif vazia:
        extra = "empty deserted scene, still life, environment only"
    else:  # cena aberta com figuras minúsculas ao longe (plano alto, estilo cinematográfico)
        extra = "very wide high-angle establishing shot, every figure tiny and far away"
    return f"{limpo}. {extra}. {epoca}. {estilo}"


def _quadros(seg: float) -> int:
    """Wan 2.2 5B gera a 24 fps, com 4k+1 quadros; teto de 145 (~6 s)."""
    n = int(seg * 24) + 1
    n = n + (1 - n % 4) % 4
    return max(49, min(145, n))


def main():
    from estudio.agentes import montador, narrador
    from estudio.agentes.montador_hf import _preparar_musica
    from estudio.produzir import abrir_issue, montar_texto_post

    caminho = Path(sys.argv[1])
    r = json.loads(caminho.read_text(encoding="utf-8"))
    canal = carregar_canal("biblico")
    canal_img = {**canal, "estilo_visual": r.get("estilo_imagem", ESTILO), "regra_visual_pessoas": REGRA,
                 "epoca_imagem": r.get("epoca_imagem", "")}
    pasta = SAIDA / f"wan_{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    pasta.mkdir(parents=True)
    narrado = all(c.get("trecho") for c in r["cenas"]) and not r.get("sem_narracao")

    # 1) narração primeiro: o tempo de cada cena define quantos quadros o Wan precisa gerar
    tempos, palavras, dur, mp3 = [4.0] * len(r["cenas"]), [], 0.0, None
    if narrado:
        texto = " ".join(c["trecho"] for c in r["cenas"])
        canal_voz = {**canal, "gemini_tts": {**canal["gemini_tts"], "duracao_max": r.get("duracao_max", 20)}} \
            if canal.get("gemini_tts") else canal
        limite = int(r.get("palavras_por_bloco", 170))
        if len(texto.split()) <= limite + 40:
            mp3, palavras, dur = narrador.narrar(canal_voz, texto, pasta)
        else:  # filme longo: a voz é gerada em blocos de cenas e emendada (cada pedido ao Gemini fica curto)
            grupos, atual, n = [], [], 0
            for c in r["cenas"]:
                w = len(c["trecho"].split())
                if atual and n + w > limite:
                    grupos.append(atual)
                    atual, n = [], 0
                atual.append(c)
                n += w
            grupos.append(atual)
            voz_bloco = {**canal_voz, "gemini_tts": {**canal_voz["gemini_tts"], "duracao_max": 999}} \
                if canal_voz.get("gemini_tts") else canal_voz
            def _blocos(cfg: dict, so_gemini: bool):
                """Narra todos os blocos com a MESMA voz; se a Gemini falhar em um, recomeça tudo no Edge."""
                partes, palavras, dur = [], [], 0.0
                for k, g in enumerate(grupos):
                    sub = pasta / f"voz_{k:02d}"
                    shutil.rmtree(sub, ignore_errors=True)
                    sub.mkdir()
                    txt = " ".join(c["trecho"] for c in g)
                    if so_gemini:
                        from estudio.agentes import narrador_gemini
                        for tent in range(1, 4):
                            try:
                                mp3k, palk, durk = narrador_gemini.narrar(cfg, txt, sub, narrador.duracao)
                                break
                            except Exception as e:  # noqa: BLE001
                                log("wan", f"voz Gemini bloco {k + 1} tentativa {tent}/3 falhou ({e})")
                                if tent == 3 or "429" in str(e) or "quota" in str(e).lower():
                                    return None
                    else:
                        random.seed(4242)  # mesmo ritmo e tom em todos os blocos
                        mp3k, palk, durk = narrador.narrar(cfg, txt, sub)
                    palavras += [{**pw, "ini": pw["ini"] + dur, "fim": pw["fim"] + dur} for pw in palk]
                    partes.append(mp3k)
                    dur += durk
                    log("wan", f"voz bloco {k + 1}/{len(grupos)}: {durk:.1f}s")
                return partes, palavras, dur
            res = _blocos(voz_bloco, True) if voz_bloco.get("tts") == "gemini" and voz_bloco.get("gemini_tts") else None
            if res is None:
                log("wan", "voz Gemini indisponível para o filme inteiro; narrando TUDO com uma única voz do Edge")
                res = _blocos({**voz_bloco, "forcar_edge": True, "vozes": [voz_bloco["voz"]]}, False)
                random.seed()
            partes, palavras, dur = res
            lista_v = pasta / "voz_lista.txt"
            lista_v.write_text("".join(f"file '{x.resolve()}'\n" for x in partes))
            mp3 = pasta / "narracao.mp3"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista_v),
                            "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
            dur = _dur(mp3) or dur
        tempos = montador.tempos_das_cenas(r["cenas"], palavras, dur)
        tempos[-1] += 0.8  # respiro no fim
    # orações para dormir: só música no final — feita à parte (imagem parada), não esticando a última cena
    cauda = float(r.get("cauda_musical_min", 0) or 0) * 60

    # 2) ilustrações: Z-Image Turbo no Kaggle (2 opções por cena; o Gemini escolhe a que serve)
    semente = random.randint(1, 10**6)
    horiz = r.get("formato") == "horizontal"  # filmes longos do YouTube: 16:9
    W, H = (1920, 1080) if horiz else (1080, 1920)
    cenas, imgs, cenas_img, avisos = [], [], [], []
    estilo = r.get("estilo_imagem", ESTILO)
    prefixo_img = r.get("prefixo_imagem", "cinematic photorealistic film still:")
    fonte = r.get("fonte_imagem", os.getenv("FONTE_IMAGEM", "kaggle"))
    opcoes = int(r.get("opcoes_imagem", 3))
    for c in r["cenas"]:
        cenas_img.append({**c, "prompt_imagem": f"{prefixo_img} {c['prompt_imagem']}"})
    if fonte == "kaggle":
        from estudio.agentes.revisor_visual import _avaliar
        chave = os.getenv("GEMINI_API_KEY")
        escolhidas, pendentes, prompts, motivos = {}, list(range(len(cenas_img))), {}, {}
        reserva = {}  # só imagens que ficaram SEM revisão (Gemini fora do ar), nunca as reprovadas
        for rodada in (1, 2, 3):  # rodadas extras só para as cenas reprovadas, com o prompt corrigido pelo revisor
            if not pendentes:
                break
            itens = []
            for i in pendentes:
                base_p = prompts.get(i) or cenas_img[i]["prompt_imagem"]
                itens += [{"tipo": "imagem", "nome": f"img_{i}_r{rodada}{k}", "seed": semente + 100 * i + 10 * rodada + k,
                           "resolucao": "1344x768" if horiz else "768x1344",
                           "prompt": _prompt_imagem(base_p, estilo, cenas_img[i].get("vazia", True),
                                                    cenas_img[i].get("epoca_imagem") or
                                                    r.get("epoca_imagem", "Strictly first century objects of clay, stone, wood and cloth"))}
                          for k in range(opcoes if rodada == 1 else max(opcoes, 2))]
            saida_img, rel_img = _rodar_kaggle(itens, pasta, f"imagens{rodada}")
            log("wan", f"imagens (rodada {rodada}): {rel_img[:200]}")
            for i in list(pendentes):
                cand = sorted(x for x in saida_img.rglob(f"img_{i}_r{rodada}*.*")
                              if x.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
                for x in cand:
                    jpg = pasta / f"cena_{i}_{x.stem.split('_')[-1]}.jpg"
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(x), "-q:v", "2", str(jpg)], check=True)
                    try:
                        v = _avaliar(chave, canal_img, cenas_img[i], jpg, rigoroso=True) if chave else {"ok": True}
                    except Exception as e:  # noqa: BLE001 — sem revisão NÃO é aprovação
                        v = {"ok": False, "motivo": f"revisão indisponível ({e})"}
                        reserva.setdefault(i, jpg)
                    log("wan", f"cena {i + 1} {x.stem.split('_')[-1]}: {'ok' if v.get('ok') else 'reprovada'} {v.get('motivo', '')}")
                    if v.get("ok"):
                        escolhidas[i] = jpg
                        pendentes.remove(i)
                        break
                    motivos[i] = v.get("motivo", "")
                    if v.get("novo_prompt"):
                        prompts[i] = f"{prefixo_img} {v['novo_prompt']}"
        if not escolhidas:
            raise SystemExit("nenhuma imagem passou na revisão — produção interrompida para não sair com erros")
        for i in range(len(cenas_img)):
            escolhida = escolhidas.get(i) or reserva.get(i)
            if i not in escolhidas and escolhida:
                avisos.append(f"Cena {i + 1}: imagem sem revisão (Gemini indisponível) — confira antes de aprovar.")
            if not escolhida:  # reprovada em todas as rodadas: repete a cena aprovada mais próxima (com outro movimento)
                j = min(escolhidas, key=lambda k: (abs(k - i), k > i))
                escolhida = escolhidas[j]
                cenas_img[i]["animar_bloqueado"] = True
                avisos.append(f"Cena {i + 1}: nenhuma imagem passou ({motivos.get(i, '')}); usei a imagem da cena {j + 1}.")
                log("wan", f"cena {i + 1}: reprovada em todas as rodadas → reaproveita a cena {j + 1}")
            img = pasta / f"cena_{i}.jpg"
            shutil.copy(escolhida, img)
            imgs.append(img)
    else:  # fontes antigas (Cloudflare/Pollinations) + revisão que refaz as ruins
        for i, c in enumerate(cenas_img):
            img = pasta / f"cena_{i}.jpg"
            if not visual.gerar_uma(canal_img, c, img, semente + i):
                raise SystemExit(f"sem imagem para a cena {i + 1}")
            imgs.append(img)
        try:
            from estudio.agentes import revisor_visual
            avisos += revisor_visual.revisar(canal_img, cenas_img, imgs)
        except Exception as e:  # noqa: BLE001
            log("wan", f"revisão visual indisponível ({e})")
    for i, (c, img) in enumerate(zip(r["cenas"], imgs)):
        res_v = r.get("resolucao_video", "1280x704" if horiz else os.getenv("WAN_RESOLUCAO", "704x1280"))  # 720p: rostos e mãos mais estáveis
        peq = pasta / f"cena_{i}_wan.jpg"  # manda a imagem já no tamanho do Wan (script menor)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(img), "-vf", "scale=832:480" if horiz else "scale=480:832",
                        "-q:v", "5", str(peq)], check=True)  # pacote leve (o Kaggle recusa script grande); o Wan amplia
        if not c.get("animar", True) or cenas_img[i].get("animar_bloqueado"):
            continue  # cena parada: ilustração com movimento de câmera (sem GPU)
        movimento = _movimento(img, c.get("prompt_movimento") or c["prompt_imagem"])
        cenas.append({"nome": f"clipe_{i}", "idx": i, "img": base64.b64encode(peq.read_bytes()).decode(), "seed": semente + i,
                      "quadros": _quadros(tempos[i] + 0.4), "resolucao": res_v,
                      "passos": int(r.get("passos_video", os.getenv("WAN_PASSOS", "4"))),
                      "prompt": f"{r.get('prefixo_video', 'Cinematic epic film shot, slow and subtle motion.')} {movimento}",
                      "negativo": ("extra people, new characters appearing, duplicated person, body splitting, extra limbs, "
                                   "morphing, bending over, sudden pose change, turning around, looking at the camera, head turning, "
                                   "face appearing, faces, cartoon face on objects, anthropomorphic objects, mascot, characters, "
                                   "person entering, text, watermark, distorted body, flicker")})

    # 3) animação no Kaggle
    por_idx = {c["idx"]: c for c in cenas}
    clipes, resumo = {}, ""
    if cenas:
        saida_vid, resumo = _rodar_kaggle(cenas, pasta, "video")
        clipes = {int(c.stem.split("_")[1]): c for c in saida_vid.rglob("clipe_*.mp4")}
        if len(clipes) != len(cenas):
            raise SystemExit(f"o Kaggle devolveu {len(clipes)} de {len(cenas)} clipes — veja o log acima")

    # 3b) controle de qualidade do movimento: clipes reprovados são refeitos uma vez com câmera parada e movimento mínimo
    ruins = {}
    for i, cl in sorted(clipes.items()):
        v = _checar_clipe(cl, r["cenas"][i].get("prompt_imagem", ""))
        log("wan", f"clipe {i + 1}: {'ok' if v.get('ok') else 'reprovado'} {v.get('motivo', '')}")
        if not v.get("ok"):
            ruins[i] = v.get("motivo", "")
    if ruins and os.getenv("WAN_REFAZER", "1") == "1":
        refazer = []
        for i in ruins:
            c2 = {**por_idx[i], "nome": f"clipe_{i}", "seed": por_idx[i]["seed"] + 777,
                  "prompt": ("Cinematic epic film shot, static camera, almost still image, "
                             "only subtle flicker of the lamp light and a gentle breeze in cloth and leaves")}
            refazer.append(c2)
        saida_r, _ = _rodar_kaggle(refazer, pasta, "refazer")
        for i in list(ruins):
            novo = next(saida_r.rglob(f"clipe_{i}.mp4"), None)
            if novo:
                v = _checar_clipe(novo, r["cenas"][i].get("prompt_imagem", ""))
                log("wan", f"clipe {i + 1} refeito: {'ok' if v.get('ok') else 'ainda reprovado'} {v.get('motivo', '')}")
                clipes[i] = novo
                if v.get("ok"):
                    ruins.pop(i)
    def _zoom(i: int, seg: float) -> Path:
        """Ilustração com movimento de câmera suave (aproxima, afasta ou desliza), variando de cena para cena."""
        fixo = pasta / f"clipe_fixo_{i}.mp4"
        n = max(1, int(seg * 30))
        mov = [("min(1+0.0010*on,1.15)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
               ("max(1.15-0.0010*on,1.0)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
               ("1.12", f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
               ("1.12", f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)")][i % 4]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(imgs[i]), "-vf",
                        f"scale={int(W * 1.2)}:{int(H * 1.2)},zoompan=z='{mov[0]}':x='{mov[1]}':y='{mov[2]}'"
                        f":d={n}:s={W}x{H}:fps=30", "-t", f"{seg:.2f}", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", str(fixo)], check=True)
        return fixo

    for i, motivo in ruins.items():
        clipes[i] = _zoom(i, tempos[i] + 0.6)
        log("wan", f"clipe {i + 1}: substituído pela ilustração aprovada com zoom lento ({motivo})")
    for i in range(len(r["cenas"])):
        if i not in clipes:
            clipes[i] = _zoom(i, tempos[i] + 0.6)
    clipes = [clipes[i] for i in range(len(r["cenas"]))]

    # 4) montagem: cada clipe ajustado ao tempo da cena, transição suave, legenda, voz e música baixa
    X = 0.4
    partes = []
    for i, (cl, d) in enumerate(zip(clipes, tempos)):
        alvo = d + (X if i < len(clipes) - 1 else 0)
        fator = alvo / max(_dur(cl), 0.1)
        out = pasta / f"parte_{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cl), "-vf",
                        f"setpts={fator:.4f}*PTS,fps=30,scale={W}:{H}:flags=lanczos,format=yuv420p",
                        "-t", f"{alvo:.3f}", "-an", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", str(out)], check=True)
        partes.append((out, alvo))
    ent, filtro, ant, off = [], [], "[0:v]", 0.0
    for i, (pt, alvo) in enumerate(partes):
        ent += ["-i", str(pt)]
    for i in range(1, len(partes)):
        off += partes[i - 1][1] - X
        filtro.append(f"{ant}[{i}:v]xfade=transition=fade:duration={X}:offset={off:.3f}[x{i}]")
        ant = f"[x{i}]"
    base = pasta / "base.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ent, "-filter_complex", ";".join(filtro) or "null",
                    "-map", ant if filtro else "0:v", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-video_track_timescale", "15360", str(base)], check=True)
    if cauda > 0:  # final só com música: última ilustração parada, um pouco mais escura (codifica rápido)
        escura, fim = pasta / "cauda.png", pasta / "cauda.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(imgs[int(r.get("cena_cauda", len(r["cenas"]) - 1))]), "-vf",
                        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.12",
                        str(escura)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(escura),
                        "-t", f"{cauda:.1f}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-tune", "stillimage",
                        "-crf", "20", "-preset", "veryfast", "-video_track_timescale", "15360", str(fim)], check=True)
        lista_c = pasta / "cauda_lista.txt"
        lista_c.write_text(f"file '{base.resolve()}'\nfile '{fim.resolve()}'\n")
        junto = pasta / "base_cauda.mp4"
        juntar = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista_c)]
        try:  # mesmo formato dos dois lados: junta sem recodificar
            subprocess.run([*juntar, "-c", "copy", str(junto)], check=True)
            assert abs(_dur(junto) - (_dur(base) + cauda)) < 3
        except Exception:  # noqa: BLE001
            subprocess.run([*juntar, "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                            "-r", "30", str(junto)], check=True)
        junto.replace(base)
        log("wan", f"cauda musical de {cauda / 60:.0f} min adicionada")

    ass = pasta / "legendas.ass"
    total = _dur(base)
    if narrado:
        montador.gerar_legendas(palavras, ass)
    else:
        ass.write_text(montador.gerar_legendas([], ass).read_text())
    extra = ("Style: Topo,DejaVu Serif,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,8,70,70,300,1\n"
             f"{ESTILO_ASSINATURA}\n"
             "Style: Serie,DejaVu Sans,34,&H007AD2FF,&H007AD2FF,&H00000000,&H80000000,-1,0,0,0,100,100,5,0,1,3,1,8,70,70,170,1\n"
             "Style: Ref,DejaVu Serif,44,&H007AD2FF,&H007AD2FF,&H00000000,&H64000000,-1,0,0,0,100,100,6,0,1,4,2,2,70,70,330,1\n")
    t = ass.read_text().replace("\n[Events]", extra + "\n[Events]", 1)
    t += f"Dialogue: 1,{_ts(0)},{_ts(2.6)},Topo,,0,0,0,,{r.get('gancho_tela', r['titulo']).upper()}\n"
    t += f"Dialogue: 2,{_ts(0)},{_ts(total)},Sig,,0,0,0,,{canal['nome'].upper()}\n"  # assinatura do canal
    if r.get("serie"):  # selo da série no topo durante todo o vídeo
        selo = f"{r['serie']} · Parte {r['parte']}" if r.get("parte") else r["serie"]
        t += f"Dialogue: 2,{_ts(0)},{_ts(total)},Serie,,0,0,0,,{selo.upper()}\n"
    if r.get("referencia"):
        t += f"Dialogue: 1,{_ts(max(0, total - 3.2))},{_ts(total)},Ref,,0,0,0,,{r['referencia'].upper()}\n"
    if horiz:  # mesma identidade, posições e tamanhos ajustados para 16:9
        t = (t.replace("PlayResX: 1080\nPlayResY: 1920", "PlayResX: 1920\nPlayResY: 1080")
             .replace("Style: Base,Montserrat,82,", "Style: Base,Montserrat,62,").replace(",70,70,560,1", ",120,120,95,1")
             .replace(",70,70,300,1", ",120,120,110,1").replace(",70,70,170,1", ",120,120,40,1")
             .replace(",70,70,330,1", ",120,120,190,1").replace("6,0,1,2,1,2,70,70,110,1", "6,0,1,2,1,2,70,70,28,1"))
    ass.write_text(t, encoding="utf-8")

    musica = pasta / "musica.mp3"
    tem_musica = _preparar_musica(canal, musica, total)
    vol = r.get("volume_musica", 0.12)
    video = pasta / "video.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(base)]
    audio = []
    if mp3:
        cmd += ["-i", str(mp3)]
        audio.append("[1:a]aresample=48000,apad[voz]")
    if tem_musica:
        cmd += ["-i", str(musica)]
        k = 2 if mp3 else 1
        audio.append(f"[{k}:a]aresample=48000,volume={vol},afade=t=in:d=0.8,afade=t=out:st={max(0, total - 1.8):.2f}:d=1.8[mus]")
    if mp3 and tem_musica:
        audio.append("[voz][mus]amix=inputs=2:duration=first:normalize=0[a]")
    elif mp3:
        audio.append("[voz]anull[a]")
    elif tem_musica:
        audio.append("[mus]anull[a]")
    fontes = Path("assets/fontes").resolve()
    vf = f"subtitles={ass}:fontsdir={fontes}"
    cmd += ["-filter_complex", f"[0:v]{vf}[v];" + ";".join(audio), "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium" if total < 600 else "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(video)]
    subprocess.run(cmd, check=True)
    montador.normalizar_volume(video)

    t0 = 0.0
    for i, d in enumerate(tempos):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0 + d / 2:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=540:-1", str(pasta / f"previa_{i}.jpg")], check=False)
        t0 += d
    if horiz:  # miniatura do YouTube a partir da ilustração mais forte (sem legendas)
        k = int(r.get("cena_capa", 0))
        publicador.capa_youtube(imgs[min(k, len(imgs) - 1)], r.get("texto_capa") or [r["titulo"]], pasta / "thumb.jpg")
    roteiro = {"titulo": r["titulo"], "narracao": " ".join(c.get("trecho", "") for c in r["cenas"]),
               "legenda": r.get("legenda", r["titulo"]), "hashtags": r.get("hashtags", []), "fontes": r.get("fontes", []),
               "titulo_youtube": r.get("titulo_youtube"),
               "plataformas": r.get("plataformas") or (["youtube"] if total > 180 else None)}  # filme longo: só YouTube
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")
    texto_post = montar_texto_post(canal, roteiro)
    (pasta / "post.txt").write_text(texto_post, encoding="utf-8")
    no_tg = publicador.telegram_video(video, f"🎨 [Animação Wan 2.2] {r['titulo']} · {total:.0f}s", texto_post)
    link = abrir_issue({**canal, "estilo_nome": "animação Wan 2.2"}, roteiro, texto_post, pasta, total,
                       avisos + [f"Kaggle: {resumo[:300]}"], r.get("referencia", r["titulo"]), no_tg)
    if no_tg and link:
        destino = "YouTube" if total > 180 else "Instagram, Facebook e YouTube"
        publicador.telegram_mensagem(f"✅ Aprovar ({destino}): {link}")
    log("wan", f"concluído: {video} · {link}")


if __name__ == "__main__":
    main()
