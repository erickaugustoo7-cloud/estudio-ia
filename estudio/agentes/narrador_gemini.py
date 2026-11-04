"""Narração com Gemini TTS (voz mais natural e expressiva, gratuita com GEMINI_API_KEY).

O Gemini não informa o tempo de cada palavra, então o áudio é alinhado ao texto com o
faster-whisper (reconhecimento de fala local, gratuito). As legendas usam sempre as palavras
exatas do roteiro; o Whisper só fornece os tempos.
Qualquer falha (limite diário, erro, alinhamento ruim) → o narrador cai para o edge-tts.
"""
import base64
import difflib
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path

import requests

from estudio.base import log

API = "https://generativelanguage.googleapis.com/v1beta"
_WHISPER = None


def _norm(p: str) -> str:
    p = unicodedata.normalize("NFD", p.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in p if unicodedata.category(c) != "Mn"))


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def sintetizar(texto: str, cfg: dict, destino_wav: Path) -> None:
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError("GEMINI_API_KEY ausente")
    corpo = {"contents": [{"parts": [{"text": cfg["estilo"].strip() + " Texto: " + texto}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": cfg["voz"]}}}}}
    ultimo = ""
    for espera in (0, 30, 60):
        time.sleep(espera)
        r = requests.post(f"{API}/models/{cfg['modelo']}:generateContent", params={"key": chave},
                          json=corpo, timeout=300)
        if r.ok:
            dados = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            pcm = destino_wav.with_suffix(".pcm")
            pcm.write_bytes(dados)
            _ffmpeg("-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(pcm), str(destino_wav))
            return
        ultimo = f"HTTP {r.status_code}: {r.text[:200]}"
        if r.status_code not in (429, 500, 503):
            break
    raise RuntimeError(f"Gemini TTS falhou ({ultimo})")


def alinhar(audio: Path, texto: str) -> tuple[list[dict], float]:
    """Tempo de cada palavra do roteiro, a partir das palavras reconhecidas pelo Whisper."""
    global _WHISPER
    from faster_whisper import WhisperModel
    if _WHISPER is None:
        _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = _WHISPER.transcribe(str(audio), language="pt", word_timestamps=True, vad_filter=False)
    reconhecidas = [w for s in segs for w in (s.words or [])]
    roteiro = texto.split()
    a = [_norm(w) for w in roteiro]
    b = [_norm(w.word) for w in reconhecidas]
    tempos = [None] * len(roteiro)
    casadas = 0
    for bloco in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(bloco.size):
            w = reconhecidas[bloco.b + k]
            tempos[bloco.a + k] = (w.start, w.end)
            casadas += 1
    cobertura = casadas / max(1, len(roteiro))
    # preenche as não casadas interpolando entre as vizinhas
    for i, t in enumerate(tempos):
        if t is None:
            ant = next((tempos[j][1] for j in range(i - 1, -1, -1) if tempos[j]), 0.0)
            prox_j = next((j for j in range(i + 1, len(tempos)) if tempos[j]), None)
            prox = tempos[prox_j][0] if prox_j is not None else ant + 0.4
            lacuna = (prox_j - i) if prox_j is not None else 1
            passo = max(0.05, (prox - ant) / (lacuna + 1))
            tempos[i] = (ant + passo * 0.1, ant + passo)
    palavras = [{"ini": float(i), "fim": float(f), "texto": re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", w) or w}
                for w, (i, f) in zip(roteiro, tempos)]
    return palavras, cobertura


def narrar(canal: dict, texto: str, pasta: Path, duracao) -> tuple[Path, list[dict], float]:
    cfg = canal["gemini_tts"]
    wav = pasta / "narracao_gemini.wav"
    sintetizar(texto, cfg, wav)
    mp3 = pasta / "narracao.mp3"
    dur = duracao(wav)
    alvo_max = cfg.get("duracao_max", 90)
    fator = min(1.15, dur / alvo_max) if dur > alvo_max else 1.0  # acelera um pouco se passar do teto
    filtro = ["-af", f"atempo={fator:.3f}"] if fator > 1.0 else []
    _ffmpeg("-i", str(wav), *filtro, "-c:a", "libmp3lame", "-q:a", "2", str(mp3))
    dur = duracao(mp3)
    palavras, cobertura = alinhar(mp3, texto)
    if cobertura < 0.8:
        raise RuntimeError(f"alinhamento fraco ({cobertura:.0%} das palavras) — a voz pode ter mudado o texto")
    log("narrador", f"voz Gemini {cfg['voz']} ({cfg['modelo']}, x{fator:.2f}) — {dur:.1f}s, "
                    f"{len(palavras)} palavras, alinhamento {cobertura:.0%}")
    return mp3, palavras, dur
