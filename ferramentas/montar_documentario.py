"""Converte um roteiro de documentário (markdown com "## seções") + plano visual (yaml) no JSON de produção."""
import json
import re
import sys
from pathlib import Path

import yaml

md, plano, saida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
meta = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8")) if len(sys.argv) > 4 else {}
texto = md.read_text(encoding="utf-8")
secoes = [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"^## (?:[\w.]+\. )?(.+?)\n(.*?)(?=^## |\Z)", texto, re.S | re.M)]
visuais = yaml.safe_load(plano.read_text(encoding="utf-8"))
assert len(visuais) == len(secoes), f"plano visual tem {len(visuais)} seções, roteiro tem {len(secoes)}"
cenas, caps = [], []
for (titulo, corpo), plano_s in zip(secoes, visuais):
    caps.append({"cena": len(cenas), "titulo": titulo})
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", " ".join(l.strip() for l in corpo.splitlines() if l.strip())) if f.strip()]
    buf, k = [], 0
    def fecha():
        global k
        if not buf:
            return
        item = plano_s[k % len(plano_s)]; k += 1
        tipo, termo = next(iter(item.items()))
        c = {"trecho": " ".join(buf), "prompt_imagem": f"documentary reconstruction, {termo}, prehistoric, natural light",
             "vazia": True, "animar": False}
        c["busca_video" if tipo == "v" else "acervo"] = termo
        cenas.append(c); buf.clear()
    for f in frases:
        buf.append(f)
        if len(" ".join(buf).split()) >= 26:
            fecha()
    if buf and len(" ".join(buf).split()) < 14 and cenas and len(cenas) > caps[-1]["cena"]:
        cenas[-1]["trecho"] += " " + " ".join(buf); buf.clear()
    fecha()
r = {**meta, "cenas": cenas, "capitulos": caps}
saida.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(cenas), "cenas,", sum(len(c["trecho"].split()) for c in cenas), "palavras,", len(caps), "capítulos;",
      sum("acervo" in c for c in cenas), "cenas de museu")
