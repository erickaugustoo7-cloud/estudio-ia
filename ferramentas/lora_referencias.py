"""Gera as imagens de referência para o LoRA de estilo do Antes de Nós (Z-Image-Turbo no ModelScope),
com a mesma direção de fotografia em todas e uma gradação de cor única. Saída em base64 no log."""
import base64, io, json, os, sys, pathlib
sys.path.insert(0, ".")
from estudio.kaggle_wan import _rodar_modelscope
from PIL import Image, ImageEnhance
ESTILO = ("cinematic documentary film still, shot on ARRI Alexa, 35mm anamorphic lens, natural volumetric light, "
          "warm golden highlights and teal shadows, soft atmospheric haze, fine film grain, National Geographic, "
          "scientifically accurate, realistic textures, no text, no watermark, no modern objects")
prompts = [l.strip() for l in open("dados/lora/prompts_antes_de_nos.txt") if l.strip()]
itens = [{"tipo": "imagem", "nome": f"ref_{i:02d}", "resolucao": "1344x768", "seed": 1000 + i,
          "prompt": f"{p}, {ESTILO}"} for i, p in enumerate(prompts)]
p = pathlib.Path("lora"); p.mkdir(exist_ok=True)
os.environ.setdefault("MODELSCOPE_PARALELO", "4")
saida, rel = _rodar_modelscope(itens, p, "lora")
print("REL", rel[:200])
leg = {}
for i, pr in enumerate(prompts):
    f = saida / f"ref_{i:02d}.png"
    if not f.exists():
        continue
    im = Image.open(f).convert("RGB")
    im = ImageEnhance.Contrast(im).enhance(1.05)  # gradação única do canal
    r, g, b = im.split(); r = r.point(lambda x: min(255, int(x * 1.03))); b = b.point(lambda x: int(x * 0.97))
    im = Image.merge("RGB", (r, g, b))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    dados = base64.b64encode(buf.getvalue()).decode()
    for k in range(0, len(dados), 60000):
        print(f"REF ref_{i:02d} {dados[k:k + 60000]}")
    leg[f"ref_{i:02d}"] = f"antesdenos_doc, {pr}"
print("LEGENDAS " + json.dumps(leg, ensure_ascii=False))
