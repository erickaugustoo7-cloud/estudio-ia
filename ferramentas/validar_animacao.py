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
novela = bool(r.get("moderno"))
if r.get("tipo") == "novela":  # novela cristã de hoje: personagens fixos com rosto, gancho no começo e "siga" no fim
    lim_c, lim_p, lim_t = (8, 14), (150, 260), (6, 40)
    for c in r.get("cenas", []):  # novela com falas: toda fala precisa de uma voz definida
        q = (c.get("personagem") or "Narrador").split(" (")[0]
        if c.get("personagem") and q != "Narrador" and q not in r.get("vozes", {}):
            erros.append(f"personagem '{q}' sem voz em \"vozes\"")
    if not r.get("personagens_regra"):
        erros.append("novela sem personagens_regra (ficha visual fixa dos personagens)")
    if "sig" not in (r["cenas"][-1]["trecho"].lower() if r.get("cenas") else ""):
        erros.append("última cena precisa pedir para seguir (ex.: 'Siga para ver a parte 2')")
elif r.get("tipo") == "tiktok":  # curto do TikTok (docs/MANUAL_TIKTOK.md)
    if "sig" not in (r["cenas"][-1]["trecho"].lower() if r.get("cenas") else ""):
        erros.append("última cena precisa pedir para seguir (ex.: 'Siga para mais')")
    if sum(bool(c.get("animar")) for c in r.get("cenas", [])) > 1:
        erros.append("TikTok: no máximo 1 cena animada (a do gancho)")
    if r.get("plataformas") != ["facebook"]:
        erros.append('TikTok: plataformas deve ser ["facebook"] (TikTok é postado à mão; Instagram e YouTube ficam de fora)')
    if len(r.get("gancho_tela", "").split()) > 5 or not r.get("gancho_tela"):
        erros.append("TikTok: gancho_tela de 1 a 5 palavras")
elif r.get("tipo") in ("salmo", "historia") and "sig" not in (r["cenas"][-1]["trecho"].lower() if r.get("cenas") else ""):
    erros.append("última cena precisa convidar a seguir (ex.: 'Siga o Mensageiro de Fé para ouvir um salmo por dia')")
if r.get("tipo") == "novela":
    pass  # limites já definidos acima
elif r.get("tipo") == "tiktok":  # 15–30 s: gancho falado, 1 virada, convite a seguir
    lim_c, lim_p, lim_t = (4, 7), (35, 75), (4, 22)
elif r.get("tipo") == "historia":  # história narrada com a voz do Eric, sem GPU (70–90 s)
    lim_c, lim_p, lim_t = (7, 12), (140, 240), (6, 40)
elif r.get("tipo") == "salmo":  # Salmos narrados: texto bíblico corrido sobre poucas imagens (1–2 min)
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
    if oracao and not any("inscreva" in c["trecho"].lower() for c in cenas[-3:]):
        erros.append("oração sem convite falado para se inscrever nas 3 últimas cenas (ex.: 'inscreva-se no canal')")
    if oracao:  # Short isca: trecho forte da oração, ligado a ela pelo "Vídeo relacionado" (MANUAL_LONGOS.md)
        isca = r.get("short_isca") or {}
        ids = isca.get("cenas") or []
        if not ids:
            erros.append('falta short_isca {"cenas": [i], "texto_topo": "...", "titulo": "..."} (Short que leva à oração)')
        elif any(not (0 <= int(x) < len(cenas)) for x in ids) or max(ids) - min(ids) > 1:
            erros.append("short_isca.cenas: índices inválidos (no máximo 2 cenas seguidas)")
        else:
            texto = isca.get("trecho") or " ".join(cenas[int(x)]["trecho"] for x in range(min(ids), max(ids) + 1))
            if isca.get("trecho") and isca["trecho"] not in " ".join(cenas[int(x)]["trecho"] for x in
                                                                   range(min(ids), max(ids) + 1)):
                erros.append("short_isca.trecho precisa ser cópia exata de parte dessas cenas")
            if not 12 <= len(texto.split()) <= 45:
                erros.append(f"short_isca: {len(texto.split())} palavras (use 12–45, Short de 8–20 s)")
            if len(isca.get("texto_topo", "").split()) > 4 or not isca.get("texto_topo"):
                erros.append("short_isca.texto_topo: 1 a 4 palavras")
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
    if not novela and re.search(PESSOAS, sem_neg) and not re.search(PERMITIDO, sem_neg):
        erros.append(f"cena {i}: pessoa como assunto da imagem → conte pela cena/objeto ({re.search(PESSOAS, sem_neg).group(0)})")
    if not novela and re.search(MODERNO, re.sub(r"\bno [a-z ]+", "", p)):
        erros.append(f"cena {i}: objeto moderno no prompt")
    m = (c.get("prompt_movimento") or "").lower()
    if re.search(r"\b(turns?|walks?|raises?|bows?|looks? at|kneel|stands? up|sits? down)\b", m):
        erros.append(f"cena {i}: movimento de pessoa no prompt_movimento")
print("OK" if not erros else "PROBLEMAS:\n- " + "\n- ".join(erros))
sys.exit(1 if erros else 0)
