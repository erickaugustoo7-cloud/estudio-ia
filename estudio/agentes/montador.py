"""Editor: monta o vídeo vertical 1080x1920 só com FFmpeg (rápido e grátis no GitHub Actions).

Imagens com zoom lento (Ken Burns) + narração + música opcional + legenda palavra a palavra.
"""
import random
import subprocess
from pathlib import Path

from estudio.base import RAIZ, log

FPS = 30
W, H = 1080, 1920


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


# ---------------- tempos de cada cena ----------------
def tempos_das_cenas(cenas: list[dict], palavras: list[dict], dur_total: float) -> list[float]:
    """Usa o tempo real das palavras narradas para cortar cada cena no ponto certo."""
    contagem = [max(1, len(c["trecho"].split())) for c in cenas]
    total = sum(contagem)
    n = len(palavras)
    inicios, acumulado = [0.0], 0
    for c in contagem[:-1]:
        acumulado += c
        idx = min(n - 1, round(acumulado / total * n))  # proporcional, robusto a pequenas diferenças
        inicios.append(palavras[idx]["ini"] if n else dur_total * acumulado / total)
    fins = inicios[1:] + [dur_total]
    return [max(1.0, f - i) for i, f in zip(inicios, fins)]


def normalizar_volume(video: Path) -> None:
    """Deixa o áudio no volume padrão das redes (-14 LUFS), sem mexer no vídeo."""
    tmp = video.with_name("video_norm.mp4")
    try:
        _ffmpeg("-i", str(video), "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:a", "aac", "-b:a", "160k", str(tmp))
        tmp.replace(video)
        log("montador", "volume normalizado (-14 LUFS)")
    except Exception as e:  # noqa: BLE001
        log("montador", f"normalização de volume falhou ({e}); mantendo o original")


# ---------------- legendas ----------------
def _ts(s: float) -> str:
    h, s = divmod(max(0.0, s), 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def blocos_legenda(palavras: list[dict], max_palavras: int = 3) -> list[list[dict]]:
    """Agrupa as palavras em blocos curtos (quebra também em pausas da fala)."""
    blocos, atual = [], []
    for p in palavras:
        if atual and (len(atual) == max_palavras or p["ini"] - atual[-1]["fim"] > 0.35):
            blocos.append(atual)
            atual = []
        atual.append(p)
    if atual:
        blocos.append(atual)
    return blocos


def gerar_legendas(palavras: list[dict], destino: Path) -> Path:
    cab = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Base,Montserrat,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,"
        "7,3,2,70,70,560,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    blocos = blocos_legenda(palavras)
    linhas = []
    for b, bloco in enumerate(blocos):
        proximo = blocos[b + 1][0]["ini"] if b + 1 < len(blocos) else float("inf")
        for j, p in enumerate(bloco):
            fim = bloco[j + 1]["ini"] if j + 1 < len(bloco) else min(p["fim"] + 0.15, proximo)
            partes = [
                ("{\\c&H00D7FF&}" + w["texto"].upper() + "{\\c&HFFFFFF&}") if k == j else w["texto"].upper()
                for k, w in enumerate(bloco)
            ]
            linhas.append(f"Dialogue: 0,{_ts(p['ini'])},{_ts(fim)},Base,,0,0,0,,{' '.join(partes)}")
    destino.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return destino


# ---------------- vídeo ----------------
def _clipe(imagem: Path, dur: float, saida: Path, i: int):
    frames = max(1, round(dur * FPS))
    zoom_in = i % 2 == 0
    z = "min(1.0+0.0007*on,1.18)" if zoom_in else "max(1.18-0.0007*on,1.0)"
    vf = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        "format=yuv420p"
    )
    _ffmpeg("-i", str(imagem), "-vf", vf, "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(saida))


# Acordes da trilha ambiente gerada (Hz). Original, sem direitos autorais.
ACORDES = {
    "biblico": [[130.81, 196.00, 261.63, 329.63], [110.00, 164.81, 220.00, 277.18],
                [146.83, 220.00, 293.66, 369.99], [123.47, 185.00, 246.94, 311.13]],   # maiores, calorosos
    "espaco": [[110.00, 164.81, 246.94, 329.63], [98.00, 146.83, 220.00, 293.66],
               [87.31, 130.81, 196.00, 261.63], [103.83, 155.56, 233.08, 311.13]],    # suspensos, misteriosos
}


def _gerar_trilha(canal: dict, destino: Path, dur: float = 150) -> Path:
    """Trilha ambiente sintetizada no FFmpeg: acorde sustentado com pulsação lenta e eco."""
    acordes = ACORDES.get(canal.get("slug"), ACORDES["espaco"])
    acorde = random.choice(acordes)
    vel = random.uniform(0.07, 0.15)  # pulsação lenta
    termos = "+".join(f"{0.22 / (k + 1):.3f}*sin(2*PI*{f}*t)" for k, f in enumerate(acorde))
    expr = f"({termos})*(0.65+0.35*sin(2*PI*{vel:.3f}*t))"
    _ffmpeg("-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={dur}",
            "-af", "lowpass=f=1800,aecho=0.8:0.85:900|1400:0.35|0.25,afade=t=in:d=3,volume=0.9",
            "-c:a", "libmp3lame", "-q:a", "4", str(destino))
    return destino


def _musica(canal: dict, pasta_trabalho: Path | None = None) -> Path | None:
    pasta = RAIZ / canal.get("musica", "")
    faixas = sorted(pasta.glob("*.mp3")) if canal.get("musica") and pasta.is_dir() else []
    if faixas:
        return random.choice(faixas)
    if canal.get("trilha_gerada", True) and pasta_trabalho:
        return _gerar_trilha(canal, pasta_trabalho / "trilha_gerada.mp3")
    return None


def montar(canal, imagens, tempos, narracao: Path, legendas: Path, pasta: Path) -> Path:
    clipes = []
    for i, (img, d) in enumerate(zip(imagens, tempos)):
        c = pasta / f"clipe_{i:02d}.mp4"
        _clipe(img, d, c, i)
        clipes.append(c)
        log("montador", f"clipe {i + 1}/{len(imagens)} ({d:.1f}s)")

    lista = pasta / "clipes.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in clipes), encoding="utf-8")
    base = pasta / "base.mp4"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(base))

    final = pasta / "video.mp4"
    fontes = RAIZ / "assets" / "fontes"
    filtro_video = f"[0:v]ass={legendas.as_posix()}:fontsdir={fontes.as_posix()}[v]"
    musica = _musica(canal, pasta)
    args = ["-i", str(base), "-i", str(narracao)]
    if musica:
        args += ["-stream_loop", "-1", "-i", str(musica)]
        filtro = (filtro_video + ";[2:a]volume=0.08[m];[1:a][m]amix=inputs=2:duration=first:"
                  "dropout_transition=0:normalize=0[a]")
        log("montador", f"música: {musica.name}")
    else:
        filtro = filtro_video + ";[1:a]anull[a]"
    _ffmpeg(*args, "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "3500k", "-bufsize", "7000k",
            "-r", str(FPS),  # teto de bitrate: ~30 MB por vídeo de 70 s (limite do Telegram é 50 MB)
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-shortest", "-movflags", "+faststart", str(final))
    log("montador", f"vídeo final: {final}")
    return final
