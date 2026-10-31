"""Narrador: voz neural gratuita (edge-tts) + tempo exato de cada palavra para as legendas."""
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

from estudio.base import log


async def _sintetizar(texto, voz, ritmo, mp3: Path):
    palavras = []
    com = edge_tts.Communicate(texto, voz, rate=ritmo, boundary="WordBoundary")
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                ini = chunk["offset"] / 1e7  # unidades de 100 ns
                palavras.append({"ini": ini, "fim": ini + chunk["duration"] / 1e7, "texto": chunk["text"]})
    return palavras


def duracao(arquivo: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(arquivo)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def narrar(canal: dict, texto: str, pasta: Path) -> tuple[Path, list[dict], float]:
    mp3 = pasta / "narracao.mp3"
    palavras = asyncio.run(_sintetizar(texto, canal["voz"], canal.get("ritmo_voz", "+0%"), mp3))
    dur = duracao(mp3)
    log("narrador", f"{dur:.1f}s de áudio, {len(palavras)} palavras sincronizadas")
    return mp3, palavras, dur
