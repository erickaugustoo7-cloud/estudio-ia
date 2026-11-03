"""Gera imagens candidatas para a ABERTURA dos vídeos bíblicos (a Bíblia aberta do 'Jesus chorou').

As candidatas vão para assets/aberturas/candidatas/ (commitadas pelo workflow) e para o Telegram,
numeradas, para escolher a melhor. A escolhida vira assets/aberturas/biblia.jpg e é usada na
primeira cena dos roteiros que tiverem "imagem": "assets/aberturas/biblia.jpg".
"""
import os
import random
import time
import urllib.parse
from pathlib import Path

import requests

BASE = ("an ancient open bible lying on a rustic wooden table in the foreground, sharp focus on the pages, "
        "pages glowing with warm golden light, a single lit candle on the left side, "
        "{fundo}, shallow depth of field, cinematic composition, bright warm amber highlights, "
        "classical oil painting look, vertical 9:16, highly detailed, no text, no letters, no watermark")
FUNDOS = [
    "robed people standing in the softly blurred background, seen from behind",
    "a few robed figures in silhouette in the blurred background near a bright window",
    "an ancient stone room with soft rays of light in the blurred background",
    "robed people standing in the softly blurred background, seen from behind",
]
SAIDA = Path("assets/aberturas/candidatas")


def baixar(prompt: str, seed: int, destino: Path) -> bool:
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width=1080&height=1920&seed={seed}&nologo=true&model=flux"
    for espera in (0, 20, 40, 60, 60):
        time.sleep(espera)
        try:
            r = requests.get(url, timeout=150)
            if r.ok and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20_000:
                destino.write_bytes(r.content)
                return True
            print("falhou:", r.status_code)
        except requests.RequestException as e:
            print("erro:", type(e).__name__)
    return False


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    for i, fundo in enumerate(FUNDOS, 1):
        destino = SAIDA / f"opcao_{i}.jpg"
        if not baixar(BASE.format(fundo=fundo), random.randint(1, 10**6), destino):
            continue
        print("ok", destino)
        if token and chat:
            with open(destino, "rb") as f:
                requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", timeout=60,
                              data={"chat_id": chat, "caption": f"Abertura — opção {i}"}, files={"photo": f})


if __name__ == "__main__":
    main()
