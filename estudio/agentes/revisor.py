"""Revisor: verificação de fatos + compliance numa única chamada (economiza tokens).

Devolve o roteiro corrigido ou bloqueia a produção quando o problema é grave.
"""
import json

from estudio.base import llm_json, log


class RoteiroBloqueado(Exception):
    pass


def revisar(canal: dict, roteiro: dict) -> tuple[dict, list[str]]:
    sistema = (
        f"Você é o revisor-chefe do canal '{canal['nome']}'. Sua função é proteger a "
        "credibilidade do canal e a conta nas plataformas.\n"
        "Verifique:\n"
        "1. FATOS: todo número, data, nome, referência bíblica ou afirmação científica está correto? "
        "Na dúvida, corrija para uma versão que você tem certeza ou remova.\n"
        "2. LINHA EDITORIAL:\n- " + "\n- ".join(canal["linha_editorial"]) + "\n"
        "3. PROIBIDO:\n- " + "\n- ".join(canal["proibido"]) + "\n"
        "4. Políticas do Instagram/TikTok: sem desinformação, sem clickbait enganoso, sem pedir engajamento em troca de benefício.\n\n"
        "Se houver problema corrigível, reescreva os campos afetados mantendo o mesmo formato "
        "(se mudar a narração, ajuste também os trechos das cenas). "
        "Se o tema inteiro for inviável, marque gravidade 'bloquear'.\n"
        'Responda SOMENTE com JSON: {"gravidade": "ok"|"corrigido"|"bloquear", '
        '"problemas": ["..."], "roteiro": {roteiro completo, corrigido ou igual}}'
    )
    r = llm_json(sistema, json.dumps(roteiro, ensure_ascii=False), max_tokens=3500)
    problemas = r.get("problemas", [])
    if r["gravidade"] == "bloquear":
        raise RoteiroBloqueado("; ".join(problemas) or "bloqueado pelo revisor")
    log("revisor", f"{r['gravidade']} — {len(problemas)} apontamento(s)")
    return r.get("roteiro") or roteiro, problemas
