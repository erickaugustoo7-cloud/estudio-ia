import sys, pathlib, json
sys.path.insert(0, ".")
from estudio.agentes.publicador import _traducoes_youtube
from estudio.agentes import revisor_visual
from estudio.kaggle_wan import _rodar_modelscope, _editar_modelscope
loc = _traducoes_youtube("Como os Egípcios Construíram as Pirâmides? | Documentário",
                         "Molhar a areia reduzia o atrito pela metade.\n\n🔔 Inscreva-se no Antes de Nós e ative o sininho.", cristao=False)
print("TRAD", json.dumps(loc, ensure_ascii=False)[:600])
p = pathlib.Path("t"); p.mkdir()
saida, _ = _rodar_modelscope([{"tipo": "imagem", "nome": "x", "resolucao": "1344x768", "seed": 3, "prompt":
    "cinematic photo of ancient Egyptian workers near the pyramids, a modern blue pickup truck parked in the foreground"}], p, "t")
img = saida / "x.png"; url = (saida / "x.url").read_text()
texto = revisor_visual.PERGUNTA_DOCUMENTARIO.format(canal="Antes de Nós", trecho="Os trabalhadores das pirâmides",
        epoca="Egito, 2560 a.C.", prompt="ancient Egyptian workers near the pyramids", regras="nenhuma")
print("REV_RESERVA", revisor_visual._avaliar_modelscope(texto, img, True))
ed = _editar_modelscope(url, "Fix this documentary still: there is a modern pickup truck. Remove it and replace with sand and stone blocks. Keep everything else.", p / "ed.jpg", 1344, 768)
print("EDIT", ed)
if ed:
    print("REV_EDITADA", revisor_visual._avaliar_modelscope(texto, ed, True))
