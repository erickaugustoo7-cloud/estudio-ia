"""Banner (2560x1440) e foto de perfil (800x800) do canal Perguntas da História.
Fundo: mosaico antigo do Cleveland Museum of Art (CC0). Fonte: Cinzel (SIL Open Font License)."""
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes import acervo  # noqa: E402

OUT = Path("identidade"); OUT.mkdir(exist_ok=True)
fonte = OUT / "Cinzel.ttf"
fonte.write_bytes(requests.get("https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf", timeout=60).content)
MONT = "assets/fontes/Montserrat-Black.ttf"
OURO, ESCURO = (226, 178, 92), (18, 13, 9)

# fundo: só CC0 (sem obrigação de crédito no banner)
res = [x for x in acervo._cleveland("mosaic", 20) if "CC0" in x["fonte"]
       and not any(e in x["titulo"].lower() for e in ("adam", "eve", "venus", "nude", "bath"))]
res.sort(key=lambda x: "pavement" not in x["titulo"].lower())  # padrão geométrico primeiro: sem figuras humanas
print("candidatos:", [x["titulo"] for x in res][:8])
fundo = None
for c in res:
    r = requests.get(c["url"], headers=acervo.UA, timeout=60)
    if r.ok and len(r.content) > 100000:
        (OUT / "mosaico.jpg").write_bytes(r.content)
        im = Image.open(OUT / "mosaico.jpg").convert("RGB")
        if min(im.size) >= 1200:
            fundo = im; print("fundo:", c["titulo"], c["data"], c["pagina"]); break
if fundo is None:
    fundo = Image.new("RGB", (2560, 1440), ESCURO)


def preencher(im, W, H):
    e = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * e) + 1, int(im.height * e) + 1), Image.LANCZOS)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))


def tingir(im, escurecer):
    im = ImageEnhance.Color(im).enhance(0.55)
    im = Image.blend(im, Image.new("RGB", im.size, ESCURO), escurecer)
    return im


def centro(d, y, txt, f, cor, W):
    w = d.textlength(txt, font=f)
    d.text(((W - w) / 2 + 4, y + 5), txt, font=f, fill=(0, 0, 0))
    d.text(((W - w) / 2, y), txt, font=f, fill=cor)


# BANNER 2560x1440 — área segura (aparece em todos os aparelhos): 1546x423 no centro
W, H = 2560, 1440
b = tingir(preencher(fundo, W, H), 0.62)
vin = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(min(255, v * 1.1)))
b = Image.composite(Image.new("RGB", (W, H), ESCURO), b, vin)
d = ImageDraw.Draw(b)
ft = ImageFont.truetype(str(fonte), 150); ft.set_variation_by_axes([800])
fs = ImageFont.truetype(MONT, 40)
centro(d, 560, "PERGUNTAS DA HISTÓRIA", ft, OURO, W)
d.line((W / 2 - 160, 755, W / 2 + 160, 755), fill=OURO, width=4)
centro(d, 785, "AS PERGUNTAS QUE NINGUÉM FAZ SOBRE A HISTÓRIA DA HUMANIDADE", fs, (240, 232, 218), W)
b.save(OUT / "banner.jpg", quality=92)

# FOTO DE PERFIL 800x800 (o YouTube recorta em círculo)
A = 800
a = tingir(preencher(fundo, A, A), 0.70)
d = ImageDraw.Draw(a)
d.ellipse((30, 30, A - 30, A - 30), outline=OURO, width=14)
fq = ImageFont.truetype(str(fonte), 560); fq.set_variation_by_axes([900])
bb = d.textbbox((0, 0), "?", font=fq)
x, y = (A - (bb[2] - bb[0])) / 2 - bb[0], (A - (bb[3] - bb[1])) / 2 - bb[1]
d.text((x + 8, y + 10), "?", font=fq, fill=(0, 0, 0))
d.text((x, y), "?", font=fq, fill=OURO)
a.save(OUT / "perfil.jpg", quality=95)

# prévia de como fica no celular (corte da área segura) para conferência
seg = b.crop(((W - 1546) // 2, (H - 423) // 2, (W + 1546) // 2, (H + 423) // 2))
seg.save(OUT / "banner_area_celular.jpg", quality=85)
print("ok")
