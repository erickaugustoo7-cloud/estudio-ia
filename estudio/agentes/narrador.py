"""Narrador: voz neural gratuita (edge-tts) + tempo exato de cada palavra para as legendas."""
import asyncio
import json
import random
import subprocess
from pathlib import Path

import edge_tts

from estudio.base import log


async def _sintetizar(texto, voz, ritmo, mp3: Path, tom="+0Hz"):
    palavras = []
    com = edge_tts.Communicate(texto, voz, rate=ritmo, pitch=tom, boundary="WordBoundary")
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


def _variacao(base: str, unidade: str, faixa: int) -> str:
    """Soma uma variação aleatória pequena ao ritmo/tom base (ex.: "+5%" → "+3%")."""
    valor = int(base.rstrip(unidade) or 0) + random.randint(-faixa, faixa)
    return f"{valor:+d}{unidade}"


def narrar(canal: dict, texto: str, pasta: Path) -> tuple[Path, list[dict], float]:
    """Alterna entre as vozes do canal e varia levemente ritmo e tom a cada vídeo,
    para a narração não ficar idêntica à de canais automáticos que usam a mesma voz."""
    mp3 = pasta / "narracao.mp3"
    vozes = list(canal.get("vozes") or [canal["voz"]])
    random.shuffle(vozes)
    if canal.get("voz") and canal["voz"] not in vozes:
        vozes.append(canal["voz"])  # voz principal sempre como reserva
    por_voz = canal.get("ritmo_por_voz") or {}
    tom = _variacao(canal.get("tom_voz", "+0Hz"), "Hz", 3)
    erros = []
    for voz in vozes:
        # cada voz tem seu ritmo base (o Antonio é naturalmente mais lento que a Thalita)
        ritmo = _variacao(por_voz.get(voz, canal.get("ritmo_voz", "+0%")), "%", 2)
        try:
            palavras = asyncio.run(_sintetizar(texto, voz, ritmo, mp3, tom))
            if palavras:
                break
            erros.append(f"{voz}: sem marcações de palavra")
        except Exception as e:  # noqa: BLE001 — voz indisponível: tenta a próxima
            erros.append(f"{voz}: {e}")
    else:
        raise RuntimeError("Nenhuma voz funcionou: " + " | ".join(erros))
    dur = duracao(mp3)
    log("narrador", f"voz {voz} (ritmo {ritmo}, tom {tom}) — {dur:.1f}s, {len(palavras)} palavras sincronizadas")
    return mp3, palavras, dur
