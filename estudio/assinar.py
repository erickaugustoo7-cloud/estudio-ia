"""Coloca a assinatura do canal num vídeo já produzido (artefato de outra execução) e abre nova aprovação.

Uso (no GitHub Actions, depois de baixar o artefato para saida/):  python -m estudio.assinar
"""
import json
import subprocess
from pathlib import Path

from estudio.base import SAIDA, carregar_canal, log
from estudio.agentes import publicador
from estudio.kaggle_wan import ESTILO_ASSINATURA, _dur, _ts
from estudio.produzir import abrir_issue


def main():
    canal = carregar_canal("biblico")
    video = next(SAIDA.rglob("video.mp4"))
    pasta = video.parent
    total = _dur(video)
    ass = pasta / "assinatura.ass"
    ass.write_text("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
                   "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
                   "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
                   f"MarginL, MarginR, MarginV, Encoding\n{ESTILO_ASSINATURA}\n\n[Events]\n"
                   "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                   f"Dialogue: 2,{_ts(0)},{_ts(total)},Sig,,0,0,0,,{canal['nome'].upper()}\n", encoding="utf-8")
    novo = pasta / "video_assinado.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", f"subtitles={ass}",
                    "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(novo)], check=True)
    novo.replace(video)
    roteiro = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    texto_post = (pasta / "post.txt").read_text(encoding="utf-8")
    no_tg = publicador.telegram_video(video, f"🎨 [Animação] {roteiro['titulo']} · {total:.0f}s (com assinatura)", texto_post)
    link = abrir_issue({**canal, "estilo_nome": "animação Wan 2.2"}, roteiro, texto_post, pasta, total, [],
                       roteiro.get("fontes", [roteiro["titulo"]])[0], no_tg)
    if no_tg and link:
        publicador.telegram_mensagem(f"✅ Aprovar para Instagram e Facebook: {link}")
    log("assinar", f"pronto: {link}")


if __name__ == "__main__":
    main()
