"""Refaz no padrão aprovado (16/11, dourado) as miniaturas dos vídeos longos já produzidos, para o Eric trocar no YouTube."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes import publicador, visual  # noqa: E402
from estudio.agentes.revisor_visual import _avaliar  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402

SAIDA = Path("assets/capas_youtube")
SAIDA.mkdir(parents=True, exist_ok=True)
CEU_NOITE = "the LEFT two thirds are an empty deep blue night sky with stars and soft moonlight bokeh"
def foto(quem, extra=""):
    return (f"photorealistic emotional portrait of {quem}, {extra}soft warm rim light, placed on the RIGHT third of the "
            f"frame, face and hands sharp and natural; {CEU_NOITE}, cinematic, shallow depth of field, 16:9, no text")
CAPAS = [
    ("salmo91", foto("a Brazilian woman in her forties with eyes closed, praying with hands clasped near her chin, "), ["ORE O", "*SALMO 91", "ANTES DE DORMIR"], "Oração da noite"),
    ("salmo23", foto("an elderly Brazilian man with white hair, eyes closed, peaceful face, hands resting on an old Bible, "), ["DURMA COM O", "*SALMO 23", "ESTA NOITE"], "Oração da noite"),
    ("salmo4", foto("a young Brazilian woman lying on a pillow with eyes closed and hands together in prayer, calm face, "), ["ORE ISSO", "*ANTES", "DE DORMIR"], "Oração da noite"),
    ("ansiedade", foto("a Brazilian woman in her thirties with eyes closed, one hand on her chest, a tear on her cheek, "), ["ENTREGUE A", "*ANSIEDADE", "A DEUS HOJE"], "Oração da noite"),
    ("salmo121", foto("a Brazilian mother in her thirties praying with eyes closed beside a sleeping child, "), ["DEUS NÃO", "*DORME", "DESCANSE NELE"], "Oração da noite"),
    ("cansados", foto("a tired Brazilian man in his forties with a short beard, eyes closed, head bowed over clasped hands, "), ["ESTÁ", "*CANSADO?", "VENHA A MIM"], "Oração da noite"),
    ("isaias41", foto("a Brazilian woman in her fifties with grey streaks in her hair, eyes closed, hands pressed together, "), ["MEDO DO", "*AMANHÃ?", "ORE ISSO"], "Oração da noite"),
    ("jose_do_egito", ("photorealistic cinematic film still of a young Hebrew man in a torn colorful robe sitting at the bottom of "
                       "a dry stone pit, looking up with tears in his eyes, a beam of light from above, placed on the RIGHT third "
                       "of the frame; the LEFT two thirds are dark stone wall and deep blue shadow, ancient Canaan, 16:9, no text"),
     ["TRAÍDO", "*PELOS IRMÃOS", "JOSÉ DO EGITO"], "Filme bíblico"),
]
canal = {"nome": "Mensageiro de Fé", "estilo_visual": "photorealistic cinematic photography", "moderno": True,
         "regra_visual_pessoas": "one person (or a mother with her child), natural face and hands, no deformities, no text"}
chave = os.getenv("GEMINI_API_KEY")
so = os.getenv("SO", "")
for nome, prompt, linhas, sub in CAPAS:
    if so and nome not in so.split(","):
        continue
    cena = {"prompt_imagem": prompt, "largura": 1344, "altura": 768, "trecho": "miniatura de oração"}
    feito = False
    for t in range(4):
        png = SAIDA / f"_{nome}_{t}.png"
        if not visual.gerar_uma(canal, cena, png, random.randint(1, 99999)):
            continue
        jpg = png.with_suffix(".jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-q:v", "2", str(jpg)], check=True)
        res = _avaliar(chave, canal, cena, jpg, rigoroso=True) if chave else {"ok": True}
        print(nome, t, res.get("ok"), res.get("motivo", "")[:120])
        if res.get("ok") or t == 3:
            publicador.capa_emocional(jpg, linhas, SAIDA / f"capa_{nome}.jpg", subtitulo=sub)
            feito = True
        png.unlink(missing_ok=True)
        jpg.unlink(missing_ok=True)
        if feito:
            break
