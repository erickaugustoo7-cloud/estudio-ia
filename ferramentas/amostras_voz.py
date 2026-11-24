"""Gera o mesmo trecho do Antes de Nós em várias vozes GRATUITAS para o Eric escolher às cegas (24/11).
Cada amostra sai como MP3 e é impressa em base64 no log (os artefatos não descem no ambiente do Claude)."""
import asyncio
import base64
import subprocess
import sys
from pathlib import Path

TEXTO = ("Seus antepassados caminharam ao lado de preguiças do tamanho de elefantes. Não é exagero e não é lenda. "
         "Num deserto de areia branca, os cientistas encontraram pegadas de uma dessas preguiças. E, dentro delas, "
         "encontraram outra coisa. No final deste documentário, eu vou te mostrar o que estava dentro dessas pegadas.")
OUT = Path("amostras"); OUT.mkdir(exist_ok=True)
EDGE = {"edge_antonio": ("pt-BR-AntonioNeural", "-4%", "-2Hz"),  # a atual
        "edge_andrew": ("en-US-AndrewMultilingualNeural", "-6%", "-3Hz"),
        "edge_brian": ("en-US-BrianMultilingualNeural", "-6%", "-3Hz"),
        "edge_thalita": ("pt-BR-ThalitaMultilingualNeural", "-5%", "+0Hz"),
        "edge_ava": ("en-US-AvaMultilingualNeural", "-6%", "-2Hz"),
        "edge_francisca": ("pt-BR-FranciscaNeural", "-5%", "-2Hz")}


async def edge():
    import edge_tts
    for nome, (voz, rate, pitch) in EDGE.items():
        try:
            await edge_tts.Communicate(TEXTO, voz, rate=rate, pitch=pitch).save(str(OUT / f"{nome}.mp3"))
            print("ok", nome)
        except Exception as e:  # noqa: BLE001
            print("falhou", nome, e)


def piper():
    try:
        base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx"
        subprocess.run(["curl", "-sL", "-o", "faber.onnx", base], check=True)
        subprocess.run(["curl", "-sL", "-o", "faber.onnx.json", base + ".json"], check=True)
        subprocess.run([sys.executable, "-m", "piper", "-m", "faber.onnx", "-f", "piper.wav", "--length-scale", "1.08"],
                       input=TEXTO.encode(), check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "piper.wav", "-b:a", "96k", str(OUT / "piper_faber.mp3")], check=True)
        print("ok piper_faber")
    except Exception as e:  # noqa: BLE001
        print("falhou piper", e)


def kokoro():
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
        pipe = KPipeline(lang_code="p")
        for voz in ("pm_alex", "pm_santa"):
            partes = [a for _, _, a in pipe(TEXTO, voice=voz, speed=0.95)]
            sf.write(f"{voz}.wav", np.concatenate(partes), 24000)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{voz}.wav", "-b:a", "96k",
                            str(OUT / f"kokoro_{voz}.mp3")], check=True)
            print("ok kokoro", voz)
    except Exception as e:  # noqa: BLE001
        print("falhou kokoro", e)


asyncio.run(edge())
piper()
kokoro()
for f in sorted(OUT.glob("*.mp3")):
    b = base64.b64encode(f.read_bytes()).decode()
    for i in range(0, len(b), 60000):
        print(f"AMOSTRA {f.stem} {b[i:i + 60000]}")
