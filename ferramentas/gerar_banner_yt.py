"""Banner do canal do YouTube (2560x1440, área segura central 1546x423) com FLUX no Cloudflare + texto."""
import base64
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROMPT = ("ultra wide panoramic landscape at golden sunset, a wooden cross on a rocky mountain summit in the center, "
          "rays of divine light behind it, layered mountain ranges and soft mist in the valleys, first stars in a deep "
          "blue sky on the edges, classical oil painting, biblical era, reverent and peaceful, no people, no text, "
          "no letters, no watermark")
FONTES = Path("assets/fontes")


def gerar(destino, semente):
    conta, token = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
                      headers={"Authorization": f"Bearer {token}"}, timeout=180,
                      files={"prompt": (None, PROMPT), "width": (None, "1920"), "height": (None, "1080"),
                             "seed": (None, str(semente))})
    r.raise_for_status()
    dados = r.content if r.headers.get("content-type", "").startswith("image") else base64.b64decode(r.json()["result"]["image"])
    destino.write_bytes(dados)


def compor(fundo, saida):
    img = Image.open(fundo).convert("RGB").resize((2560, 1440), Image.LANCZOS)
    veu = Image.new("L", img.size, 0)
    ImageDraw.Draw(veu).rounded_rectangle((560, 560, 2000, 880), radius=120, fill=150)
    img = Image.composite(Image.new("RGB", img.size, (8, 6, 4)), img, veu.filter(ImageFilter.GaussianBlur(70)))
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(str(FONTES / "Anton-Regular.ttf"), 150)
    f2 = ImageFont.truetype(str(FONTES / "Montserrat-Black.ttf"), 46)
    for txt, f, y, cor, borda in (("MENSAGEIRO DE FÉ", f1, 575, (255, 205, 60), 8),
                                  ("HISTÓRIAS DE JESUS  •  ORAÇÕES PARA DORMIR  •  FILMES BÍBLICOS", f2, 790, (255, 255, 255), 4)):
        w = d.textlength(txt, font=f)
        d.text(((2560 - w) / 2 + 5, y + 6), txt, font=f, fill=(0, 0, 0))
        d.text(((2560 - w) / 2, y), txt, font=f, fill=cor, stroke_width=borda, stroke_fill=(0, 0, 0))
    img.save(saida, quality=92)


def main():
    pasta = Path("assets/perfil")
    pasta.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate((7, 77, 777), 1):
        bruto = pasta / f"banner_yt_fundo_{i}.jpg"
        gerar(bruto, s)
        compor(bruto, pasta / f"banner_youtube_{i}.jpg")
        print("ok", i)


if __name__ == "__main__":
    main()
