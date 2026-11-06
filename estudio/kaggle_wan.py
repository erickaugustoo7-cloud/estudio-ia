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
REGRA = ("Jesus and all people only seen from behind, in silhouette or at a distance, faces never visible. "
         "Only the characters described, no crowd, no extra people in the background")
SLUG = "estudio-animacao"
# assinatura no rodapé, igual à dos outros vídeos (branca 70%, espaçada)
ESTILO_ASSINATURA = ("Style: Sig,DejaVu Sans,30,&H4DFFFFFF,&H4DFFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,6,0,1,2,1,2,"
                     "70,70,110,1")

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
    ini = time.time()
    if c.get("tipo") == "imagem":  # ilustração com o Z-Image Turbo (Apache 2.0)
        s = {"model_type": c.get("modelo", "z_image"), "prompt": c["prompt"], "resolution": c.get("resolucao", "768x1344"),
             "num_inference_steps": c.get("passos", 8), "guidance_scale": 0, "seed": c.get("seed", 42), "batch_size": 1}
    else:  # animação com o Wan 2.2 FastWan
        img = TMP / f"cena_{i}.jpg"
        img.write_bytes(base64.b64decode(c["img"]))
        s = {"model_type": "ti2v_2_2_fastwan", "prompt": c["prompt"], "image_prompt_type": "S",
             "image_start": str(img), "resolution": c.get("resolucao", "480x832"), "video_length": c.get("quadros", 97),
             "num_inference_steps": 3, "guidance_scale": 1, "flow_shift": 3, "seed": c.get("seed", 42),
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
    try:
        log("wan", _kaggle("kernels", "push", "-p", str(kdir)).strip())
    except RuntimeError as e:  # tenta de novo sem escolher a GPU (o Kaggle escolhe a disponível)
        log("wan", f"push recusado ({e}); tentando sem machine_shape")
        meta.pop("machine_shape", None)
        (kdir / "kernel-metadata.json").write_text(json.dumps(meta))
        log("wan", _kaggle("kernels", "push", "-p", str(kdir)).strip())
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
there; keep bodies and faces stable (no new poses, no bending, no splitting); prefer gentle natural motion: cloth and hair
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


def _quadros(seg: float) -> int:
    """Wan 2.2 5B gera a 24 fps, com 4k+1 quadros; teto de 121 (~5 s)."""
    n = int(seg * 24) + 1
    n = n + (1 - n % 4) % 4
    return max(49, min(121, n))


def main():
    from estudio.agentes import montador, narrador
    from estudio.agentes.montador_hf import _preparar_musica
    from estudio.produzir import abrir_issue, montar_texto_post

    caminho = Path(sys.argv[1])
    r = json.loads(caminho.read_text(encoding="utf-8"))
    canal = carregar_canal("biblico")
    canal_img = {**canal, "estilo_visual": r.get("estilo_imagem", ESTILO), "regra_visual_pessoas": REGRA}
    pasta = SAIDA / f"wan_{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    pasta.mkdir(parents=True)
    narrado = all(c.get("trecho") for c in r["cenas"]) and not r.get("sem_narracao")

    # 1) narração primeiro: o tempo de cada cena define quantos quadros o Wan precisa gerar
    tempos, palavras, dur, mp3 = [4.0] * len(r["cenas"]), [], 0.0, None
    if narrado:
        texto = " ".join(c["trecho"] for c in r["cenas"])
        canal_voz = {**canal, "gemini_tts": {**canal["gemini_tts"], "duracao_max": r.get("duracao_max", 20)}} \
            if canal.get("gemini_tts") else canal
        mp3, palavras, dur = narrador.narrar(canal_voz, texto, pasta)
        tempos = montador.tempos_das_cenas(r["cenas"], palavras, dur)
        tempos[-1] += 0.8  # respiro no fim

    # 2) ilustrações: Z-Image Turbo no Kaggle (2 opções por cena; o Gemini escolhe a que serve)
    semente = random.randint(1, 10**6)
    cenas, imgs, cenas_img, avisos = [], [], [], []
    estilo = r.get("estilo_imagem", ESTILO)
    fonte = r.get("fonte_imagem", os.getenv("FONTE_IMAGEM", "kaggle"))
    opcoes = int(r.get("opcoes_imagem", 2))
    for c in r["cenas"]:
        cenas_img.append({**c, "prompt_imagem": f"2D cartoon animation style illustration: {c['prompt_imagem']}"})
    if fonte == "kaggle":
        itens = [{"tipo": "imagem", "nome": f"img_{i}_{k}", "seed": semente + 100 * i + k,
                  "prompt": f"{c['prompt_imagem']}. {REGRA}. {estilo}"}
                 for i, c in enumerate(cenas_img) for k in range(opcoes)]
        saida_img, rel_img = _rodar_kaggle(itens, pasta, "imagens")
        log("wan", f"imagens: {rel_img[:200]}")
        from estudio.agentes.revisor_visual import _avaliar
        chave = os.getenv("GEMINI_API_KEY")
        for i, c in enumerate(cenas_img):
            cand = sorted(x for x in saida_img.rglob(f"img_{i}_*.*") if x.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
            escolhida = None
            for x in cand:
                jpg = pasta / f"cena_{i}_{x.stem.split('_')[-1]}.jpg"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(x), "-q:v", "2", str(jpg)], check=True)
                try:
                    v = _avaliar(chave, canal_img, c, jpg) if chave else {"ok": True}
                except Exception as e:  # noqa: BLE001
                    v = {"ok": True, "motivo": f"revisão indisponível ({e})"}
                log("wan", f"cena {i + 1} opção {x.stem[-1]}: {'ok' if v.get('ok') else 'reprovada'} {v.get('motivo', '')}")
                if v.get("ok"):
                    escolhida = jpg
                    break
                escolhida = escolhida or jpg
            if not escolhida:
                raise SystemExit(f"o Kaggle não gerou imagem para a cena {i + 1}")
            if not v.get("ok"):
                avisos.append(f"Cena {i + 1}: nenhuma opção passou na revisão ({v.get('motivo', '')}) — confira.")
            img = pasta / f"cena_{i}.jpg"
            escolhida.replace(img)
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
        peq = pasta / f"cena_{i}_480.jpg"  # o Wan anima em 480x832: manda a imagem já no tamanho (script menor)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(img), "-vf", "scale=480:832", "-q:v", "4", str(peq)], check=True)
        movimento = _movimento(img, c.get("prompt_movimento") or c["prompt_imagem"])
        cenas.append({"img": base64.b64encode(peq.read_bytes()).decode(), "seed": semente + i,
                      "quadros": _quadros(tempos[i] + 0.4),
                      "prompt": f"2D cartoon animation, smooth natural motion. {movimento}",
                      "negativo": ("extra people, new characters appearing, duplicated person, body splitting, extra limbs, "
                                   "morphing, bending over, sudden pose change, faces, text, watermark, distorted body, flicker")})

    # 3) animação no Kaggle
    saida_vid, resumo = _rodar_kaggle(cenas, pasta, "video")
    clipes = sorted(saida_vid.rglob("clipe_*.mp4"), key=lambda c: int(c.stem.split("_")[1]))
    if len(clipes) != len(cenas):
        raise SystemExit(f"o Kaggle devolveu {len(clipes)} de {len(cenas)} clipes — veja o log acima")

    # 4) montagem: cada clipe ajustado ao tempo da cena, transição suave, legenda, voz e música baixa
    X = 0.4
    partes = []
    for i, (cl, d) in enumerate(zip(clipes, tempos)):
        alvo = d + (X if i < len(clipes) - 1 else 0)
        fator = alvo / max(_dur(cl), 0.1)
        out = pasta / f"parte_{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cl), "-vf",
                        f"setpts={fator:.4f}*PTS,fps=30,scale=1080:1920:flags=lanczos,format=yuv420p",
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
                    "-map", ant if filtro else "0:v", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", str(base)], check=True)

    ass = pasta / "legendas.ass"
    total = _dur(base)
    if narrado:
        montador.gerar_legendas(palavras, ass)
    else:
        ass.write_text(montador.gerar_legendas([], ass).read_text())
    extra = ("Style: Topo,DejaVu Serif,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,8,70,70,300,1\n"
             f"{ESTILO_ASSINATURA}\n"
             "Style: Ref,DejaVu Serif,44,&H007AD2FF,&H007AD2FF,&H00000000,&H64000000,-1,0,0,0,100,100,6,0,1,4,2,2,70,70,330,1\n")
    t = ass.read_text().replace("\n[Events]", extra + "\n[Events]", 1)
    t += f"Dialogue: 1,{_ts(0)},{_ts(2.6)},Topo,,0,0,0,,{r.get('gancho_tela', r['titulo']).upper()}\n"
    t += f"Dialogue: 2,{_ts(0)},{_ts(total)},Sig,,0,0,0,,{canal['nome'].upper()}\n"  # assinatura do canal
    if r.get("referencia"):
        t += f"Dialogue: 1,{_ts(max(0, total - 3.2))},{_ts(total)},Ref,,0,0,0,,{r['referencia'].upper()}\n"
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
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(video)]
    subprocess.run(cmd, check=True)
    montador.normalizar_volume(video)

    t0 = 0.0
    for i, d in enumerate(tempos):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0 + d / 2:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=540:-1", str(pasta / f"previa_{i}.jpg")], check=False)
        t0 += d
    roteiro = {"titulo": r["titulo"], "narracao": " ".join(c.get("trecho", "") for c in r["cenas"]),
               "legenda": r.get("legenda", r["titulo"]), "hashtags": r.get("hashtags", []), "fontes": r.get("fontes", [])}
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")
    texto_post = montar_texto_post(canal, roteiro)
    (pasta / "post.txt").write_text(texto_post, encoding="utf-8")
    no_tg = publicador.telegram_video(video, f"🎨 [Animação Wan 2.2] {r['titulo']} · {total:.0f}s", texto_post)
    link = abrir_issue({**canal, "estilo_nome": "animação Wan 2.2"}, roteiro, texto_post, pasta, total,
                       avisos + [f"Kaggle: {resumo[:300]}"], r.get("referencia", r["titulo"]), no_tg)
    if no_tg and link:
        publicador.telegram_mensagem(f"✅ Aprovar para Instagram e Facebook: {link}")
    log("wan", f"concluído: {video} · {link}")


if __name__ == "__main__":
    main()
