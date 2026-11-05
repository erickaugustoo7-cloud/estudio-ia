"""Diagnóstico: cria containers de Reel no Instagram (SEM publicar) com variações do vídeo para achar a causa da falha."""
import subprocess, sys, time
from pathlib import Path
import requests
from estudio.agentes.publicador import FB_API, meta_contas
import os

tok = os.environ["META_TOKEN_BIBLICO"]
_, ig = meta_contas(tok)
src = Path(sys.argv[1])
def ff(*a): subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)
var = {
    "30s": ["-i", str(src), "-t", "30", "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart"],
    "55s": ["-i", str(src), "-t", "55", "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart"],
    "completo_1M": ["-i", str(src), "-c:v", "libx264", "-b:v", "1M", "-maxrate", "1M", "-bufsize", "2M", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart"],
    "completo_sem_audio": ["-i", str(src), "-an", "-c:v", "libx264", "-crf", "23", "-movflags", "+faststart"],
}
for nome, args in var.items():
    out = Path(f"v_{nome}.mp4"); ff(*args, str(out))
    dados = out.read_bytes()
    c = requests.post(f"{FB_API}/{ig}/media", data={"media_type": "REELS", "upload_type": "resumable", "access_token": tok}, timeout=60).json()
    up = requests.post(c["uri"], data=dados, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(dados))}, timeout=600)
    st = "?"
    if up.ok:
        for _ in range(30):
            time.sleep(10)
            st = requests.get(f"{FB_API}/{c['id']}", params={"fields": "status_code,status", "access_token": tok}, timeout=30).json()
            if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
    print(f"{nome}: {len(dados)/1e6:.1f} MB | upload {up.status_code} {up.text[:120]} | {st}")
