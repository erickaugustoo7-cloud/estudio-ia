"""Confere um roteiro animado contra as regras fixas (docs/REGRAS_FIXAS.md). Uso: python ferramentas/validar_animacao.py <arquivo>"""
import json
import re
import sys

PESSOAS = r"\b(man|woman|women|men|person|people|jesus|mary|maria|disciples?|servants?|bride|groom|couple|guests?|" \
          r"angel|crowd|boy|girl|child|children|figure|figures|silhouettes?|bearded|robe)\b"
PERMITIDO = r"\b(hands?|arms?)\b|tiny distant|tiny winged|far away in the distance|tiny figures"
MODERNO = r"\b(glass|bottle|electric|bulb|plastic|modern)\b"

r = json.load(open(sys.argv[1], encoding="utf-8"))
erros = []
cenas = r.get("cenas", [])
palavras = sum(len(c["trecho"].split()) for c in cenas)
oracao = bool(r.get("cauda_musical_min"))
if r.get("tipo") == "salmo":  # Salmos narrados: texto bíblico corrido sobre poucas imagens (1–2 min)
    lim_c, lim_p, lim_t = (3, 8), (120, 420), (8, 120)
elif r.get("formato") == "horizontal":  # vídeo longo do YouTube (docs/MANUAL_LONGOS.md)
    lim_c, lim_p, lim_t, max_anim = ((18, 30), (800, 1100), (12, 55), 6) if oracao else \
                                    ((60, 110), (900, 1400), (3, 30), 10)
    for campo in ("titulo_youtube", "texto_capa", "cena_capa", "legenda", "hashtags"):
        if not r.get(campo) and r.get(campo) != 0:
            erros.append(f"falta o campo {campo}")
    if not oracao and len(r.get("capitulos", [])) < 3:
        erros.append("filme sem capitulos (mínimo 3) — veja docs/MANUAL_LONGOS.md")
    for linha in r.get("texto_capa", []):
        if len(linha.split()) > 3:
            erros.append(f"texto_capa longo demais: '{linha}' (até 3 palavras por linha)")
    if r.get("plataformas") != ["youtube"]:
        erros.append('plataformas deve ser ["youtube"]')
    if len(r.get("titulo_youtube", "")) > 100:
        erros.append("titulo_youtube com mais de 100 caracteres")
    anim = sum(bool(c.get("animar")) for c in cenas)
    if anim > max_anim:
        erros.append(f"{anim} cenas animadas (máx. {max_anim}: o Kaggle demora; o resto ganha movimento de câmera)")
else:
    lim_c, lim_p, lim_t = (8, 12), (100, 150), (6, 17)
if not lim_c[0] <= len(cenas) <= lim_c[1]:
    erros.append(f"{len(cenas)} cenas (use {lim_c[0]}–{lim_c[1]})")
if not lim_p[0] <= palavras <= lim_p[1]:
    erros.append(f"{palavras} palavras (use {lim_p[0]}–{lim_p[1]})")
for i, c in enumerate(cenas, 1):
    n = len(c["trecho"].split())
    if not lim_t[0] <= n <= lim_t[1]:
        erros.append(f"cena {i}: {n} palavras no trecho ({lim_t[0]}–{lim_t[1]})")
    p = c.get("prompt_imagem", "").lower()
    sem_neg = re.sub(r"\bno [a-z ,]+", "", p)  # ignora negações ("no faces, no people")
    sem_neg = re.sub(r"silhouettes? of (the )?(palm|tree|hill|mountain|city|temple|pyramid|ship|boat|wall|tower)\w*", "", sem_neg)
    if re.search(PESSOAS, sem_neg) and not re.search(PERMITIDO, sem_neg):
        erros.append(f"cena {i}: pessoa como assunto da imagem → conte pela cena/objeto ({re.search(PESSOAS, sem_neg).group(0)})")
    if re.search(MODERNO, re.sub(r"\bno [a-z ]+", "", p)):
        erros.append(f"cena {i}: objeto moderno no prompt")
    m = (c.get("prompt_movimento") or "").lower()
    if re.search(r"\b(turns?|walks?|raises?|bows?|looks? at|kneel|stands? up|sits? down)\b", m):
        erros.append(f"cena {i}: movimento de pessoa no prompt_movimento")
print("OK" if not erros else "PROBLEMAS:\n- " + "\n- ".join(erros))
sys.exit(1 if erros else 0)
