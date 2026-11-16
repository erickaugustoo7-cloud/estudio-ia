"""Gera modelos da miniatura emocional para o Eric aprovar: 3 fotos (pessoa orando) x 2 variações de cor."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes import publicador, visual  # noqa: E402

SAIDA = Path("assets/amostras_capa")
SAIDA.mkdir(parents=True, exist_ok=True)
FOTOS = [
    ("noite", "photorealistic emotional portrait of a Brazilian woman in her thirties with eyes closed, praying with hands "
              "clasped near her chin, a single tear on her cheek, soft warm rim light, placed on the RIGHT third of the frame; "
              "the LEFT two thirds are an empty deep blue night sky with stars and soft moonlight bokeh, cinematic, 16:9, no text",
     ["ORE ISSO", "ANTES", "DE DORMIR"], "Oração da noite"),
    ("manha", "photorealistic emotional portrait of a Brazilian man in his forties with a short beard, eyes closed, holding "
              "an old leather Bible against his chest, golden sunrise light on his face, placed on the RIGHT third of the frame; "
              "the LEFT two thirds are an empty golden and blue sunrise sky over mountains, cinematic, 16:9, no text",
     ["SENHOR,", "CUIDA", "DA MINHA CASA"], "Oração da manhã"),
    ("refugio", "photorealistic emotional portrait of a Brazilian woman in her fifties with grey streaks in her hair, eyes "
                "closed, hands pressed together in prayer, peaceful expression, soft moonlight, placed on the RIGHT third of the "
                "frame; the LEFT two thirds are an empty dark blue stormy sky with clouds opening to moonlight, cinematic, 16:9, no text",
     ["QUANDO TUDO", "DESABA", "ORE ISSO"], "Oração da noite"),
]
canal = {"nome": "Mensageiro de Fé", "estilo_visual": "photorealistic cinematic photography", "moderno": True,
         "regra_visual_pessoas": "one person, natural face and hands, no deformities, no text"}
for nome, prompt, linhas, sub in FOTOS:
    foto = SAIDA / f"foto_{nome}.png"
    cena = {"prompt_imagem": prompt, "largura": 1344, "altura": 768}
    if not visual.gerar_uma(canal, cena, foto, random.randint(1, 99999)):
        print("falhou", nome)
        continue
    publicador.capa_emocional(foto, linhas, SAIDA / f"capa_{nome}_dourado.jpg", subtitulo=sub, destaque_dourado=True)
    publicador.capa_emocional(foto, linhas, SAIDA / f"capa_{nome}_branco.jpg", subtitulo=sub, destaque_dourado=False)
    foto.unlink()
    print("ok", nome)
