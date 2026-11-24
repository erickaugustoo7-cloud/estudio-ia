"""Tira o "*" literal da capa de um vídeo já publicado e reenvia a miniatura.
Uso: RUN_ID=... VIDEO_ID=... python ferramentas/remendar_capa.py  (token em YT_REFRESH_TOKEN)."""
import glob
import os

import requests
from PIL import Image, ImageFilter

thumb = sorted(glob.glob("art/**/thumb.jpg", recursive=True))[0]
im = Image.open(thumb).convert("RGB")
W, H = im.size
s = W / 960  # coordenadas medidas na capa em 960x540
caixa = tuple(int(v * s) for v in (38, 252, 98, 318))  # onde ficou o "*" antes de GIGANTES
# preenche com o fundo logo à esquerda/acima, borrado, para não deixar mancha
fonte = im.crop((0, caixa[1], caixa[0], caixa[3])).resize((caixa[2] - caixa[0], caixa[3] - caixa[1]))
im.paste(fonte.filter(ImageFilter.GaussianBlur(6)), caixa[:2])
im.save("thumb_corrigida.jpg", quality=92)
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).json()["access_token"]
r = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={os.environ['VIDEO_ID']}",
                  headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"},
                  data=open("thumb_corrigida.jpg", "rb").read(), timeout=120)
print("miniatura:", r.status_code, r.text[:300])
