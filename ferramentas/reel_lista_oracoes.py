"""Reel vertical (só Facebook) com as capas das orações longas + narração; links vão num comentário.
Uso: python ferramentas/reel_lista_oracoes.py gerar | publicar"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes import publicador  # noqa: E402

OUT = Path("reel"); OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
OURO, AZUL = (246, 190, 66), (12, 30, 72)
FONTE = "assets/fontes/Montserrat-Black.ttf"
ANTON = "assets/fontes/Anton-Regular.ttf"
SLIDES = [  # (rótulo na tela, id do vídeo)
    ("DORMIR EM PAZ", "vrNmSGPtbjg"), ("DORMIR EM PAZ", "6_9nYWWUhzo"), ("DORMIR EM PAZ", "RQgcEFMWVOo"),
    ("PEDIR PROTEÇÃO", "_8HAQPL2InI"), ("OS DIAS DIFÍCEIS", "lxBe23icJIM"),
    ("QUEM ESTÁ CANSADO", "1f-Y-HqnryA"), ("COMEÇAR O DIA", "3Oo9DvxasKs")]
NARRACAO = ("Tem uma oração para cada momento da sua vida. Para dormir em paz, quando a mente não desliga. "
            "Para pedir proteção para você e para a sua família. Para os dias em que tudo parece desabar. "
            "Para quando você está cansado de tudo. E para entregar o seu dia nas mãos de Deus, logo pela manhã. "
            "Separamos todas as orações do Mensageiro de Fé num só lugar. "
            "Os links estão no comentário fixado. Escolha a sua, e ore com a gente hoje.")
LEGENDA = ("Tem uma oração para cada momento da sua vida 🙏 Os links de todas estão no comentário fixado 👇\n\n"
           "Qual delas você mais precisa hoje? #oração #fé #Deus #salmos #oraçãodanoite")


def fonte(caminho, tam):
    return ImageFont.truetype(caminho, tam)


def centro(d, y, txt, f, cor, sombra=True):
    w = d.textlength(txt, font=f)
    if sombra:
        d.text(((W - w) / 2 + 4, y + 5), txt, font=f, fill=(0, 0, 0))
    d.text(((W - w) / 2, y), txt, font=f, fill=cor)


def slide(img: Image.Image, rotulo: str, destino: Path, topo="UMA ORAÇÃO PARA", rodape=None):
    fundo = img.copy().resize((int(img.width * H / img.height), H))
    fundo = fundo.crop(((fundo.width - W) // 2, 0, (fundo.width - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(30))
    fundo = Image.blend(ImageEnhance.Brightness(fundo).enhance(0.5), Image.new("RGB", (W, H), AZUL), 0.45)
    cap = img.resize((1000, int(img.height * 1000 / img.width)))
    y0 = (H - cap.height) // 2 + 60
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle((40 + 10, y0 + 16, 40 + cap.width + 10, y0 + cap.height + 16), fill=200)
    fundo = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), fundo, sombra.filter(ImageFilter.GaussianBlur(20)))
    fundo.paste(cap, (40, y0))
    d = ImageDraw.Draw(fundo)
    d.rectangle((40, y0 - 6, 40 + cap.width, y0 - 2), fill=OURO)
    centro(d, 330, topo, fonte(FONTE, 52), (255, 255, 255))
    f = fonte(ANTON, 120)
    while d.textlength(rotulo, font=f) > 980:
        f = fonte(ANTON, f.size - 6)
    centro(d, 410, rotulo, f, OURO)
    centro(d, y0 + cap.height + 70, rodape or "MENSAGEIRO DE FÉ", fonte(FONTE, 40), (235, 240, 255))
    fundo.save(destino, quality=92)


def gerar():
    import edge_tts
    imgs = []
    for k, (rot, vid) in enumerate(SLIDES):
        for nome in ("maxresdefault", "hqdefault"):
            r = requests.get(f"https://i.ytimg.com/vi/{vid}/{nome}.jpg", timeout=30)
            if r.ok and len(r.content) > 10000:
                (OUT / f"thumb_{k}.jpg").write_bytes(r.content); break
        imgs.append(Image.open(OUT / f"thumb_{k}.jpg").convert("RGB"))
        slide(imgs[-1], rot, OUT / f"s_{k}.jpg")
    # abertura e fechamento
    slide(imgs[0], "CADA MOMENTO DA SUA VIDA", OUT / "s_ini.jpg", topo="UMA ORAÇÃO PARA")
    slide(imgs[3], "LINKS NO COMENTÁRIO FIXADO", OUT / "s_fim.jpg", topo="TODAS AS ORAÇÕES", rodape="ESCOLHA A SUA E ORE COM A GENTE")
    mp3 = OUT / "voz.mp3"
    asyncio.run(edge_tts.Communicate(NARRACAO, "pt-BR-FranciscaNeural", rate="-6%").save(str(mp3)))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                               capture_output=True, text=True).stdout)
    ordem = ["s_ini.jpg"] + [f"s_{k}.jpg" for k in range(len(SLIDES))] + ["s_fim.jpg"]
    pesos = [1.3] + [1.0] * len(SLIDES) + [2.2]
    total = dur + 1.0
    partes = []
    for k, (nome, p) in enumerate(zip(ordem, pesos)):
        seg = total * p / sum(pesos)
        n = int(seg * 30)
        out = OUT / f"p_{k}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(OUT / nome), "-vf",
                        f"scale={int(W * 1.1)}:{int(H * 1.1)},zoompan=z='min(1+0.0009*on,1.08)':x='iw/2-(iw/zoom/2)':"
                        f"y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps=30", "-t", f"{seg:.2f}", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "20", str(out)], check=True)
        partes.append(out)
    (OUT / "lista.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "lista.txt"),
                    "-i", str(mp3), "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", str(OUT / "reel.mp4")], check=True)
    print("duração", round(total, 1), "s")
    if publicador.telegram_ativo():
        publicador.telegram_video(OUT / "reel.mp4", "📘 [Facebook — prévia do Reel com as orações]", LEGENDA)


def publicar():
    token = os.environ["META_TOKEN"]
    page_id, _ = publicador.meta_contas(token)
    r = publicador.facebook_reel(token, page_id, Path(sys.argv[2]), LEGENDA)
    print("reel", json.dumps(r))
    if r.get("status") != "published":
        raise SystemExit(1)
    lista = Path("dados/posts/fb_lista_oracoes.txt").read_text(encoding="utf-8").strip()
    import time
    for _ in range(12):  # o Reel leva um tempo para aceitar comentários
        c = requests.post(f"{publicador.FB_API}/{r['video_id']}/comments", data={"message": lista, "access_token": token},
                          timeout=60)
        print("comentário", c.status_code, c.text[:200])
        if c.ok:
            break
        time.sleep(20)


if __name__ == "__main__":
    {"gerar": gerar, "publicar": publicar}[sys.argv[1]]()
