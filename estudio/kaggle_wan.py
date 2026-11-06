"""Anima as cenas de um roteiro animado com o Wan 2.2 (FastWan 5B) na GPU grátis do Kaggle.

1. Gera a ilustração de cada cena (estilo desenho) com as fontes de imagem do sistema.
2. Monta um "kernel" do Kaggle (script Python) com as imagens embutidas e o envia pela API.
3. O Kaggle instala o Wan2GP (open source), baixa o modelo e anima cada imagem (~4 s por cena).
4. Espera terminar, baixa os clipes e manda a sequência para o Telegram.

Uso:  python -m estudio.kaggle_wan roteiros_animados/tempestade.json
Precisa dos segredos KAGGLE_USERNAME e KAGGLE_KEY (conta com telefone verificado).
"""
import base64
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from estudio.base import SAIDA, carregar_canal, log
from estudio.agentes import publicador, visual

ESTILO = ("2D hand-drawn animated feature film still, cel-shaded cartoon illustration, clean soft outlines, "
          "painterly background, warm cinematic colors, vertical 9:16, no text, no watermark")
REGRA = "Jesus and all people only seen from behind, in silhouette or at a distance, faces never visible"
SLUG = "estudio-animacao"

SCRIPT_KAGGLE = r'''
import base64, json, os, subprocess, sys, time
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
    img = TMP / f"cena_{i}.jpg"
    img.write_bytes(base64.b64decode(c["img"]))
    ini = time.time()
    s = {"model_type": "ti2v_2_2_fastwan", "prompt": c["prompt"], "image_prompt_type": "S",
         "image_start": str(img), "resolution": c.get("resolucao", "480x832"), "video_length": c.get("quadros", 97),
         "num_inference_steps": 3, "guidance_scale": 1, "flow_shift": 3, "seed": c.get("seed", 42)}
    job = session.submit_task(s)
    res = job.result()
    arqs = [str(f) for f in getattr(res, "generated_files", [])]
    print(f"cena {i}: ok={res.success} {time.time() - ini:.0f}s {arqs}", flush=True)
    if not res.success:
        for e in res.errors:
            print("  erro:", e.message, flush=True)
    for f in arqs:
        if f.endswith(".mp4"):
            Path(f).rename(OUT / f"clipe_{i}.mp4")
    rel[i] = {"ok": res.success, "segundos": round(time.time() - ini)}
(OUT / "relatorio.json").write_text(json.dumps({"total_s": round(time.time() - t0), "cenas": rel}))
print("FIM", json.dumps(rel), flush=True)
'''


def _kaggle(*args, check=True) -> str:
    r = subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"kaggle {' '.join(args)}: {r.stdout[-800:]} {r.stderr[-800:]}")
    return r.stdout + r.stderr


def main():
    caminho = Path(sys.argv[1])
    r = json.loads(caminho.read_text(encoding="utf-8"))
    canal = carregar_canal("biblico")
    canal_img = {**canal, "estilo_visual": r.get("estilo_imagem", ESTILO), "regra_visual_pessoas": REGRA}
    pasta = SAIDA / f"wan_{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    pasta.mkdir(parents=True)
    semente = random.randint(1, 10**6)
    cenas = []
    for i, c in enumerate(r["cenas"]):
        img = pasta / f"cena_{i}.jpg"
        cena_img = {**c, "prompt_imagem": f"2D cartoon animation style illustration: {c['prompt_imagem']}"}
        if not visual.gerar_uma(canal_img, cena_img, img, semente + i):
            raise SystemExit(f"sem imagem para a cena {i + 1}")
        movimento = c.get("prompt_movimento") or c["prompt_imagem"]
        cenas.append({"img": base64.b64encode(img.read_bytes()).decode(), "seed": semente + i,
                      "prompt": f"2D cartoon animation, smooth natural motion. {movimento}"})
    usuario = os.environ["KAGGLE_USERNAME"]
    kdir = pasta / "kernel"
    kdir.mkdir()
    pacote = base64.b64encode(json.dumps(cenas).encode()).decode()
    (kdir / "script.py").write_text(SCRIPT_KAGGLE.replace("__CENAS__", pacote), encoding="utf-8")
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{usuario}/{SLUG}", "title": SLUG, "code_file": "script.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": os.getenv("KAGGLE_MAQUINA", "NvidiaTeslaT4"),
        "dataset_sources": [], "competition_sources": [], "kernel_sources": []}))
    log("wan", _kaggle("kernels", "push", "-p", str(kdir)).strip())

    inicio = time.time()
    status = ""
    while time.time() - inicio < float(os.getenv("WAN_LIMITE_MIN", "150")) * 60:
        time.sleep(60)
        status = _kaggle("kernels", "status", f"{usuario}/{SLUG}", check=False)
        log("wan", f"{(time.time() - inicio) / 60:.0f} min — {status.strip()[-90:]}")
        if any(s in status.lower() for s in ("complete", "error", "cancel")):
            break
    saida = pasta / "kaggle"
    saida.mkdir()
    _kaggle("kernels", "output", f"{usuario}/{SLUG}", "-p", str(saida), check=False)
    for lg in saida.glob("*.log"):
        texto = lg.read_text(errors="ignore")
        try:  # o log do Kaggle vem em JSON (lista de {stream_name, data})
            texto = "".join(x.get("data", "") for x in json.loads(texto))
        except Exception:  # noqa: BLE001
            pass
        (pasta / "kaggle_log.txt").write_text(texto)
        print("\n".join(texto.splitlines()[-60:]))
    clipes = sorted(saida.rglob("clipe_*.mp4"))
    log("wan", f"status final: {status.strip()[-90:]} · {len(clipes)} clipe(s)")
    if not clipes:
        raise SystemExit("o Kaggle não devolveu clipes — veja o log acima")
    lista = pasta / "lista.txt"
    lista.write_text("".join(f"file '{c.resolve()}'\n" for c in clipes))
    video = pasta / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-an", str(video)], check=True)
    for i, c in enumerate(clipes):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(c), "-frames:v", "1",
                        "-vf", "scale=540:-1", str(pasta / f"previa_{i}.jpg")], check=False)
    rel = next(saida.rglob("relatorio.json"), None)
    resumo = rel.read_text() if rel else ""
    publicador.telegram_video(video, f"🧪 [Teste Wan 2.2] {r['titulo']} — só animação, sem voz", resumo[:900])
    log("wan", f"concluído: {video} {resumo}")


if __name__ == "__main__":
    main()
