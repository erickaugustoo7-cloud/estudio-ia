"""Teste de clone da voz do Eric (com autorização dele) usando Chatterbox Multilingual (licença MIT).

1) separa a voz da música do áudio de referência (Demucs);
2) recorta ~20 s de fala limpa;
3) gera amostras em português com a voz clonada e manda para o Telegram.
"""
import os
import subprocess
from pathlib import Path

import requests

REF = Path("assets/voz/eric_video_original.wav")
SAIDA = Path("amostras_clone")
TEXTOS = [
    ("salmo139", "Senhor, tu me sondaste, e me conheces. Tu sabes o meu assentar e o meu levantar; "
                 "de longe entendes o meu pensamento. Cercas o meu andar e o meu deitar, "
                 "e conheces todos os meus caminhos."),
    ("oracao", "Se você vai dormir com o coração pesado hoje, fique até o fim. Senhor Jesus, eu te entrego este dia. "
               "Tudo o que deu certo e tudo o que doeu. Cuida de quem eu amo enquanto eu durmo. Amém."),
]


def telegram(arquivo, legenda):
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if t and c:
        with open(arquivo, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{t}/sendAudio", data={"chat_id": c, "caption": legenda},
                          files={"audio": f}, timeout=120)


def main():
    SAIDA.mkdir(exist_ok=True)
    # 1) separa a voz (htdemucs, dois stems: vocals / no_vocals)
    subprocess.run(["python", "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-o", str(SAIDA / "sep"), str(REF)],
                   check=True)
    voz = next((SAIDA / "sep").rglob("vocals.wav"))
    # 2) recorta 20 s de fala (pula o início), mono 24 kHz, volume normalizado
    ref = SAIDA / "referencia_limpa.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "6", "-t", "20", "-i", str(voz), "-ac", "1", "-ar", "24000",
                    "-af", "highpass=f=70,loudnorm=I=-18", str(ref)], check=True)
    telegram(ref, "Referência: sua voz separada da música (20 s)")
    # 3) clone
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    modelo = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    for nome, texto in TEXTOS:
        for ex in (0.5, 0.35):  # exagero/emoção: 0.5 padrão, 0.35 mais calmo
            wav = modelo.generate(texto, language_id="pt", audio_prompt_path=str(ref), exaggeration=ex, cfg_weight=0.4)
            destino = SAIDA / f"clone_{nome}_{int(ex * 100)}.wav"
            ta.save(str(destino), wav, modelo.sr)
            mp3 = destino.with_suffix(".mp3")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(destino), "-q:a", "2", str(mp3)], check=True)
            telegram(mp3, f"Clone da sua voz — {nome} (emoção {ex})")
            print("ok", mp3)


if __name__ == "__main__":
    main()
