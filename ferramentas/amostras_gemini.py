"""Amostras de voz do Gemini TTS (gratuito com GEMINI_API_KEY) + a voz atual, enviadas ao Telegram.
Não altera a produção."""
import asyncio
import base64
import os
import subprocess
import time
from pathlib import Path

import requests

TEXTO = ("Se você vai dormir com o coração pesado hoje, fique até o fim. "
         "A paz de Jesus não depende de tudo dar certo. Ela chega no meio da noite difícil. "
         "Agora, feche os olhos e repita comigo. "
         "Senhor Jesus, eu te entrego este dia. Tudo o que deu certo e tudo o que doeu. "
         "Tira do meu coração a preocupação que eu não consigo carregar. "
         "Cuida de quem eu amo enquanto eu durmo. Me dá a tua paz, aquela que o mundo não dá. Amém.")
ESTILO = ("Leia em português do Brasil, como um narrador cristão acolhedor conduzindo uma oração à noite: "
          "voz calma, baixa e sincera, ritmo pausado, com pequenas pausas entre as frases, sem soar teatral. Texto: ")
VOZES = [("Algieba", "masculina, suave"), ("Enceladus", "masculina, sussurrada/íntima"),
         ("Charon", "masculina, grave"), ("Sulafat", "feminina, calorosa"), ("Vindemiatrix", "feminina, gentil")]
SAIDA = Path("amostras_gemini")
API = "https://generativelanguage.googleapis.com/v1beta"


def modelo_tts(chave):
    r = requests.get(f"{API}/models", params={"key": chave, "pageSize": 200}, timeout=30)
    nomes = [m["name"].split("/")[-1] for m in r.json().get("models", []) if "tts" in m["name"]]
    print("modelos TTS disponíveis:", nomes)
    for pref in ("flash", "pro"):
        for n in nomes:
            if pref in n:
                return n
    return "gemini-2.5-flash-preview-tts"


def gemini(chave, modelo, voz, destino):
    corpo = {"contents": [{"parts": [{"text": ESTILO + TEXTO}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    for tentativa in range(4):
        r = requests.post(f"{API}/models/{modelo}:generateContent", params={"key": chave}, json=corpo, timeout=180)
        if r.status_code == 429:
            print(voz, "limite de uso (429), esperando…")
            time.sleep(40)
            continue
        r.raise_for_status()
        dados = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
        pcm = destino.with_suffix(".pcm")
        pcm.write_bytes(dados)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1",
                        "-i", str(pcm), "-c:a", "libmp3lame", "-q:a", "3", str(destino)], check=True)
        return True
    return False


def edge(destino):
    import edge_tts
    asyncio.run(edge_tts.Communicate(TEXTO, "pt-BR-AntonioNeural", rate="+8%").save(str(destino)))


def telegram(arquivo, legenda):
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if t and c:
        with open(arquivo, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{t}/sendAudio", data={"chat_id": c, "caption": legenda,
                          "title": legenda}, files={"audio": f}, timeout=60)


def main():
    SAIDA.mkdir(exist_ok=True)
    chave = os.environ["GEMINI_API_KEY"]
    modelo = os.getenv("MODELO") or modelo_tts(chave)
    print("usando", modelo)
    vozes = VOZES
    if os.getenv("VOZES"):
        vozes = [(v, "") for v in os.environ["VOZES"].split(",")]
    else:
        ref = SAIDA / "0_atual_antonio.mp3"
        edge(ref)
        telegram(ref, "Voz ATUAL — Antonio (Edge)")
    for i, (voz, desc) in enumerate(vozes, 1):
        destino = SAIDA / f"{i}_gemini_{voz}.mp3"
        try:
            if gemini(chave, modelo, voz, destino):
                telegram(destino, f"Gemini {voz} — modelo {modelo}" + (f" ({desc})" if desc else ""))
                print("ok", voz)
        except Exception as e:  # noqa: BLE001
            print("falhou", voz, e)
        time.sleep(25)  # respeita o limite gratuito


if __name__ == "__main__":
    main()
