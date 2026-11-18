"""Confere um roteiro feito à mão antes de produzir.  Uso: python ferramentas/validar_roteiro.py roteiros/x.json [--canal=espaco]"""
import json
import sys

r = json.load(open(sys.argv[1], encoding="utf-8"))
erros = []
for campo in ("titulo", "gancho_tela", "narracao", "cenas", "legenda", "hashtags", "fontes"):
    if not r.get(campo):
        erros.append(f"falta o campo '{campo}'")
palavras = len(r.get("narracao", "").split())
curto = "--curto" in sys.argv  # oração/vídeo de até 30 s
pmin, pmax = (50, 68) if curto else (195, 225) if "--canal=espaco" in sys.argv else (165, 195)
if not pmin <= palavras <= pmax:
    erros.append(f"narração com {palavras} palavras (o alvo é {pmin}–{pmax})")
junto = " ".join(c["trecho"] for c in r.get("cenas", []))
if junto != r.get("narracao"):
    erros.append("os trechos das cenas, juntados com espaço, não são idênticos à narração")
cmin, cmax = (4, 6) if curto else (7, 10)
if not cmin <= len(r.get("cenas", [])) <= cmax:
    erros.append(f"{len(r.get('cenas', []))} cenas (use {cmin}–{cmax})")
if len(r.get("gancho_tela", "").split()) > 7:
    erros.append("gancho_tela com mais de 7 palavras")
if "parte" in r.get("gancho_tela", "").lower():
    erros.append("gancho_tela não deve ter 'Parte N' (vai só na legenda)")
if r.get("cenas") and len(r["cenas"][0]["trecho"].split()) > 16:
    erros.append("a primeira cena deve conter só o gancho (frase curta)")
if r.get("cenas"):  # retenção dos Shorts (estudo de 18/11, REGRAS_FIXAS 15–19)
    abre = r["cenas"][0]["trecho"].lower()
    for ruim in ("olá", "oi, ", "bem-vind", "mensageiro de fé", "neste vídeo", "no vídeo de hoje", "se você está assistindo"):
        if ruim in abre:
            erros.append(f"gancho: abertura genérica proibida ('{ruim}') — comece pelo fato surpreendente ou pela dor")
    if r.get("gancho_tela") and not set(r["gancho_tela"].lower().split()) & set(abre.replace(",", " ").replace(".", " ").split()):
        erros.append("gancho_tela e a 1ª frase falada precisam dizer a mesma coisa (quem assiste sem som lê o gancho)")
for i, c in enumerate(r.get("cenas", []), 1):
    if not c.get("prompt_imagem"):
        erros.append(f"cena {i} sem prompt_imagem")
print(f"{palavras} palavras, {len(r.get('cenas', []))} cenas")
print("\n".join("ERRO: " + e for e in erros) or "OK — pronto para produzir")
sys.exit(1 if erros else 0)
