"""Confere um roteiro animado contra as regras fixas (docs/REGRAS_FIXAS.md). Uso: python ferramentas/validar_animacao.py <arquivo>"""
import json
import re
import sys

PESSOAS = r"\b(man|woman|women|men|person|people|jesus|mary|maria|disciples?|servants?|bride|groom|couple|guests?|" \
          r"angel|crowd|boy|girl|child|children|figure|figures|silhouettes?|bearded|robe)\b"
PERMITIDO = r"\b(hands?|arms?)\b|tiny distant|far away in the distance|tiny figures"
MODERNO = r"\b(glass|bottle|electric|bulb|plastic|modern)\b"

r = json.load(open(sys.argv[1], encoding="utf-8"))
erros = []
cenas = r.get("cenas", [])
palavras = sum(len(c["trecho"].split()) for c in cenas)
if not 10 <= len(cenas) <= 12:
    erros.append(f"{len(cenas)} cenas (use 10–12)")
if not 120 <= palavras <= 150:
    erros.append(f"{palavras} palavras (use 120–150)")
for i, c in enumerate(cenas, 1):
    n = len(c["trecho"].split())
    if not 6 <= n <= 16:
        erros.append(f"cena {i}: {n} palavras no trecho (6–16)")
    p = c.get("prompt_imagem", "").lower()
    sem_neg = re.sub(r"\bno [a-z ,]+", "", p)  # ignora negações ("no faces, no people")
    if re.search(PESSOAS, sem_neg) and not re.search(PERMITIDO, sem_neg):
        erros.append(f"cena {i}: pessoa como assunto da imagem → conte pela cena/objeto ({re.search(PESSOAS, sem_neg).group(0)})")
    if re.search(MODERNO, re.sub(r"\bno [a-z ]+", "", p)):
        erros.append(f"cena {i}: objeto moderno no prompt")
    m = (c.get("prompt_movimento") or "").lower()
    if re.search(r"\b(turns?|walks?|raises?|bows?|looks? at|kneel|stands? up|sits? down)\b", m):
        erros.append(f"cena {i}: movimento de pessoa no prompt_movimento")
print("OK" if not erros else "PROBLEMAS:\n- " + "\n- ".join(erros))
sys.exit(1 if erros else 0)
