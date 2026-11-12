"""Narração com a voz do próprio Eric (clone autorizado por ele) — Chatterbox Multilingual (licença MIT), em CPU.

A referência é tirada do vídeo dele (assets/voz/eric_video_original.wav): a voz é separada da música (Demucs)
uma vez e guardada em cache. O texto é falado frase a frase (o modelo perde qualidade em trechos longos)
e as frases são emendadas com pausas curtas; o tempo de cada palavra vem do mesmo alinhador (Whisper)."""
import os
import re
import subprocess
from pathlib import Path

from estudio.base import log

REF_ORIG = Path("assets/voz/eric_video_original.wav")
CACHE = Path(os.getenv("VOZ_CLONE_CACHE", Path.home() / ".cache" / "estudio-voz-clone"))
_MODELO = None
EMOCAO = float(os.getenv("VOZ_CLONE_EMOCAO", "0.35"))  # 0.35 = mais calmo (orações e salmos)


def referencia() -> Path:
    ref = CACHE / "eric_referencia_limpa.wav"
    if ref.exists():
        return ref
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run(["python", "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-o", str(CACHE / "sep"),
                    str(REF_ORIG)], check=True)
    voz = next((CACHE / "sep").rglob("vocals.wav"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "6", "-t", "20", "-i", str(voz), "-ac", "1", "-ar", "24000",
                    "-af", "highpass=f=70,loudnorm=I=-18", str(ref)], check=True)
    return ref


def _modelo():
    global _MODELO
    if _MODELO is None:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        _MODELO = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return _MODELO


def _frases(texto: str, maximo: int = 220) -> list[str]:
    partes, atual = [], ""
    for f in re.split(r"(?<=[.!?;:])\s+", texto.strip()):
        if atual and len(atual) + len(f) > maximo:
            partes.append(atual)
            atual = f
        else:
            atual = f"{atual} {f}".strip()
    if atual:
        partes.append(atual)
    return partes


def narrar(texto: str, pasta: Path, duracao) -> tuple[Path, list[dict], float]:
    import torch
    import torchaudio as ta
    from estudio.agentes.narrador_gemini import alinhar
    m, ref = _modelo(), referencia()
    pedacos, pausa = [], torch.zeros(1, int(m.sr * 0.35))
    for i, f in enumerate(_frases(texto)):
        wav = m.generate(f, language_id="pt", audio_prompt_path=str(ref), exaggeration=EMOCAO, cfg_weight=0.4)
        pedacos += [wav, pausa]
        log("narrador", f"voz do Eric: frase {i + 1} ({len(f)} caracteres)")
    wav_path = pasta / "narracao_clone.wav"
    ta.save(str(wav_path), torch.cat(pedacos, dim=1), m.sr)
    mp3 = pasta / "narracao.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path), "-af", "loudnorm=I=-16:TP=-1.5",
                    "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
    palavras, cobertura = alinhar(mp3, texto)
    dur = duracao(mp3)
    log("narrador", f"voz do Eric (clone): {dur:.1f}s, alinhamento {cobertura:.0%}")
    return mp3, palavras, dur
