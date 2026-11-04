"""Confere um roteiro feito à mão antes de produzir.  Uso: python ferramentas/validar_roteiro.py roteiros/x.json [--canal=espaco]"""
import json
import sys

r = json.load(open(sys.argv[1], encoding="utf-8"))
erros = []
for campo in ("titulo", "gancho_tela", "narracao", "cenas", "legenda", "hashtags", "fontes"):
    if not r.get(campo):
        erros.append(f"falta o campo '{campo}'")
palavras = len(r.get("narracao", "").split())
pmin, pmax = (195, 225) if "--canal=espaco" in sys.argv else (165, 195)
if not pmin <= palavras <= pmax:
    erros.append(f"narração com {palavras} palavras (o alvo é {pmin}–{pmax})")
junto = " ".join(c["trecho"] for c in r.get("cenas", []))
if junto != r.get("narracao"):
    erros.append("os trechos das cenas, juntados com espaço, não são idênticos à narração")
if not 7 <= len(r.get("cenas", [])) <= 10:
    erros.append(f"{len(r.get('cenas', []))} cenas (use 8 ou 9)")
if len(r.get("gancho_tela", "").split()) > 7:
    erros.append("gancho_tela com mais de 7 palavras")
if "parte" in r.get("gancho_tela", "").lower():
    erros.append("gancho_tela não deve ter 'Parte N' (vai só na legenda)")
if r.get("cenas") and len(r["cenas"][0]["trecho"].split()) > 16:
    erros.append("a primeira cena deve conter só o gancho (frase curta)")
for i, c in enumerate(r.get("cenas", [])[1:], 2):
    if not c.get("prompt_imagem"):
        erros.append(f"cena {i} sem prompt_imagem")
print(f"{palavras} palavras, {len(r.get('cenas', []))} cenas")
print("\n".join("ERRO: " + e for e in erros) or "OK — pronto para produzir")
sys.exit(1 if erros else 0)
