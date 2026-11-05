"""Gera a capa da Página do Facebook (1640x856) com FLUX no Cloudflare + texto por cima."""
import base64
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROMPTS = [
    "wide cinematic landscape at golden sunrise, rays of divine light breaking through clouds over misty hills, "
    "a small wooden cross on a distant hill in silhouette, warm gold and amber tones, peaceful and reverent, "
    "classical oil painting look, no text, no letters, no watermark",
    "wide cinematic scene, an ancient open bible on a rustic wooden table lit by a candle on the left, "
    "a window behind showing a golden sunrise over hills, warm amber light, deep soft shadows, "
    "classical oil painting look, no text, no letters, no watermark",
]
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONTE2 = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def gerar(prompt, destino):
    conta, token = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
                      headers={"Authorization": f"Bearer {token}"}, timeout=180,
                      files={"prompt": (None, prompt), "width": (None, "1792"), "height": (None, "928"),
                             "seed": (None, str(random.randint(1, 10**6)))})
    r.raise_for_status()
    dados = r.content if r.headers.get("content-type", "").startswith("image") else base64.b64decode(r.json()["result"]["image"])
    destino.write_bytes(dados)


def compor(fundo, saida):
    img = Image.open(fundo).convert("RGB").resize((1640, 856), Image.LANCZOS)
    # véu escuro no centro para o texto (área segura do celular: centro ~1200x700)
    veu = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(veu)
    d.ellipse((220, 200, 1420, 660), fill=150)
    veu = veu.filter(ImageFilter.GaussianBlur(90))
    img = Image.composite(Image.new("RGB", img.size, (10, 6, 2)), img, veu)
    d = ImageDraw.Draw(img)
    t1, t2 = "Mensageiro de Fé", "Uma palavra de fé por dia"
    f1, f2 = ImageFont.truetype(FONTE, 112), ImageFont.truetype(FONTE2, 46)
    for txt, f, y, cor in ((t1, f1, 330, (255, 214, 130)), (t2, f2, 480, (255, 255, 255))):
        w = d.textlength(txt, font=f)
        d.text(((1640 - w) / 2 + 3, y + 3), txt, font=f, fill=(0, 0, 0))
        d.text(((1640 - w) / 2, y), txt, font=f, fill=cor)
    img.save(saida, quality=92)


def main():
    pasta = Path("assets/perfil")
    pasta.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(PROMPTS, 1):
        bruto = pasta / f"capa_fundo_{i}.jpg"
        gerar(p, bruto)
        compor(bruto, pasta / f"capa_facebook_{i}.jpg")
        print("ok", i)


if __name__ == "__main__":
    main()
