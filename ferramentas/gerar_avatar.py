"""Gera opções de foto de perfil (1024x1024) com FLUX no Cloudflare: homem de joelhos diante da cruz."""
import base64
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

BASE = ("classical oil painting, biblical era, soft golden divine light, reverent and peaceful, highly detailed, "
        "centered composition for a circular profile picture, the subject and the cross in the middle of the frame, "
        "no text, no letters, no watermark")
PROMPTS = [
    "a robed man seen from behind, kneeling in prayer on a rocky mountain top, head lifted toward a large wooden cross "
    "on the summit, glowing golden sunset sky with rays of light behind the cross, warm amber and deep blue tones",
    "a robed man in side view kneeling with hands clasped before a tall wooden cross on a hill, his face hidden in shadow, "
    "brilliant golden sunrise behind the cross, beams of light, soft mist in the valleys below",
    "a robed man seen from behind kneeling on a rocky hillside at dusk, face lifted to the sky, a wooden cross "
    "silhouetted against a glowing golden horizon, first stars in a deep blue sky, strong contrast",
]


def gerar(prompt, destino, semente):
    conta, token = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
                      headers={"Authorization": f"Bearer {token}"}, timeout=180,
                      files={"prompt": (None, f"{prompt}, {BASE}"), "width": (None, "1024"), "height": (None, "1024"),
                             "seed": (None, str(semente))})
    r.raise_for_status()
    dados = r.content if r.headers.get("content-type", "").startswith("image") else base64.b64decode(r.json()["result"]["image"])
    destino.write_bytes(dados)


def previa_circular(origem, saida):
    """Mostra como fica recortada em círculo (como no TikTok/Instagram/YouTube)."""
    img = Image.open(origem).convert("RGB").resize((512, 512), Image.LANCZOS)
    mascara = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, 511, 511), fill=255)
    fundo = Image.new("RGB", (512, 512), (255, 255, 255))
    fundo.paste(img, (0, 0), mascara.filter(ImageFilter.GaussianBlur(1)))
    fundo.save(saida, quality=90)


def main():
    pasta = Path("assets/perfil")
    pasta.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, p in enumerate(PROMPTS):
        for s in (11, 42):
            n += 1
            destino = pasta / f"avatar_{n}.jpg"
            try:
                gerar(p, destino, 1000 * i + s)
                previa_circular(destino, pasta / f"avatar_{n}_circulo.jpg")
                print("ok", destino)
            except Exception as e:  # noqa: BLE001
                print("falhou", n, e)


if __name__ == "__main__":
    main()
