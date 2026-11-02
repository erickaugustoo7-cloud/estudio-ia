"""Gera amostras do MESMO texto em várias vozes gratuitas e manda para o Telegram.
Não altera a produção — serve só para escolher a voz.

Uso: python ferramentas/amostras_voz.py
"""
import asyncio
import os
import subprocess
import time
import traceback
from pathlib import Path

import requests

TEXTO = (
    "Ele perdeu tudo em um único dia. O nome dele era Jó. "
    "E o que ele fez em seguida é uma das cenas mais fortes da Bíblia. "
    "Ele rasgou a roupa, se jogou no chão e adorou a Deus. E disse: o Senhor deu, o Senhor tirou. "
    "Bendito seja o nome do Senhor. Se hoje você está no seu pior dia, lembre-se de Jó. "
    "A dor não é o fim da sua história."
)
SAIDA = Path("amostras_voz")
SAIDA.mkdir(exist_ok=True)
resultados = []


def mp3(wav: Path, nome: str) -> Path:
    destino = SAIDA / f"{nome}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "128k", str(destino)],
                   check=True)
    return destino


def registrar(nome, descricao, func):
    t = time.time()
    try:
        arq = func()
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "csv=p=0", str(arq)], capture_output=True, text=True).stdout or 0)
        resultados.append((nome, descricao, arq, time.time() - t, dur, None))
        print(f"OK  {nome}: {time.time() - t:.0f}s para gerar {dur:.0f}s de áudio")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        resultados.append((nome, descricao, None, time.time() - t, 0, str(e)[:200]))
        print(f"ERRO {nome}: {e}")


# ---------- 1) edge-tts (o que usamos hoje) ----------
def edge(voz, ritmo="-5%"):
    import edge_tts

    def _f():
        destino = SAIDA / f"edge_{voz}.mp3"
        asyncio.run(edge_tts.Communicate(TEXTO, voz, rate=ritmo).save(str(destino)))
        return destino
    return _f


# ---------- 2) Kokoro-82M (Apache 2.0, roda local, rápido) ----------
def kokoro(voz):
    def _f():
        import soundfile as sf
        from kokoro_onnx import Kokoro
        base = Path("modelos_kokoro")
        k = Kokoro(str(base / "kokoro-v1.0.onnx"), str(base / "voices-v1.0.bin"))
        audio, sr = k.create(TEXTO, voice=voz, speed=0.95, lang="pt-br")
        wav = SAIDA / f"kokoro_{voz}.wav"
        sf.write(wav, audio, sr)
        return mp3(wav, f"kokoro_{voz}")
    return _f


# ---------- 3) Chatterbox Multilingual (MIT, roda local, mais expressivo) ----------
_cb = {}


def chatterbox(nome, exaggeration, cfg):
    def _f():
        import torchaudio as ta
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        if "m" not in _cb:
            _cb["m"] = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
        m = _cb["m"]
        wav_t = m.generate(TEXTO, language_id="pt", exaggeration=exaggeration, cfg_weight=cfg)
        wav = SAIDA / f"{nome}.wav"
        ta.save(str(wav), wav_t, m.sr)
        return mp3(wav, nome)
    return _f


VOZES = [
    ("1_atual_antonio", "edge-tts · Antonio (voz atual do canal)", edge("pt-BR-AntonioNeural")),
    ("2_edge_macerio", "edge-tts · Macerio Multilingual (masculina, mais nova)", edge("pt-BR-MacerioMultilingualNeural")),
    ("3_edge_thalita", "edge-tts · Thalita Multilingual (feminina, mais nova)", edge("pt-BR-ThalitaMultilingualNeural")),
    ("4_kokoro_alex", "Kokoro-82M · pm_alex (masculina)", kokoro("pm_alex")),
    ("5_kokoro_dora", "Kokoro-82M · pf_dora (feminina)", kokoro("pf_dora")),
    ("6_chatterbox_calmo", "Chatterbox Multilingual · tom calmo", chatterbox("6_chatterbox_calmo", 0.4, 0.5)),
    ("7_chatterbox_emocao", "Chatterbox Multilingual · mais emoção", chatterbox("7_chatterbox_emocao", 0.75, 0.3)),
]
for nome, desc, f in VOZES:
    registrar(nome, desc, f)

# ---------- envio ----------
tok, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
linhas = ["🎙️ AMOSTRAS DE VOZ — mesmo texto em cada uma:"]
for nome, desc, arq, tger, dur, erro in resultados:
    linhas.append(f"{nome}: {desc} — " + (f"{dur:.0f}s de áudio, gerado em {tger:.0f}s" if arq else f"falhou ({erro})"))
resumo = "\n".join(linhas)
print(resumo)
(SAIDA / "resumo.txt").write_text(resumo, encoding="utf-8")
if tok and chat:
    requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id": chat, "text": resumo}, timeout=30)
    for nome, desc, arq, *_ in resultados:
        if arq:
            with open(arq, "rb") as fh:
                requests.post(f"https://api.telegram.org/bot{tok}/sendAudio",
                              data={"chat_id": chat, "title": nome, "performer": desc, "caption": desc},
                              files={"audio": (arq.name, fh, "audio/mpeg")}, timeout=120)
