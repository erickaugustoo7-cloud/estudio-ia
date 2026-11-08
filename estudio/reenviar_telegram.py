"""Reenvia ao Telegram um vídeo já produzido (artefato baixado em saida/), comprimindo se passar de 50 MB."""
import sys
from pathlib import Path

from estudio.base import SAIDA, log
from estudio.agentes import publicador


def main():
    video = next(SAIDA.rglob("video.mp4"))
    post = video.parent / "post.txt"
    titulo = sys.argv[1] if len(sys.argv) > 1 else "Vídeo"
    ok = publicador.telegram_video(video, f"🎬 {titulo}", post.read_text(encoding="utf-8") if post.exists() else "")
    log("reenviar", "enviado" if ok else "falhou")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
