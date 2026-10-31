"""Roteirista: transforma a pauta em roteiro completo (narração, cenas, legenda, hashtags)."""
from estudio.base import llm_json, log

FORMATO = """{
  "titulo": "título curto interno",
  "narracao": "texto corrido que será narrado, começando pelo gancho",
  "cenas": [
    {"trecho": "frase da narração que esta cena cobre (copie literalmente)",
     "busca_nasa": "2-4 english keywords for NASA image search",
     "prompt_imagem": "english image prompt describing the scene"}
  ],
  "legenda": "legenda do post (2-4 linhas, com emoji moderado, termina com o CTA)",
  "hashtags": ["#exemplo"],
  "fontes": ["referência bíblica ou fonte científica usada"]
}"""


def escrever(canal: dict, pauta: str) -> dict:
    pmin, pmax = canal["palavras_alvo"]
    cmin, cmax = canal["cenas"]
    sistema = (
        f"Você é o roteirista do canal '{canal['nome']}' para Reels e TikTok.\n"
        f"Persona: {canal['persona']}\n"
        "Linha editorial:\n- " + "\n- ".join(canal["linha_editorial"]) + "\n"
        "Proibido:\n- " + "\n- ".join(canal["proibido"]) + "\n\n"
        "Regras de roteiro:\n"
        f"- Narração com {pmin} a {pmax} palavras (o vídeo PRECISA passar de 60 segundos).\n"
        "- A primeira frase é o gancho: curta, surpreendente, faz a pessoa parar de rolar.\n"
        "- Frases curtas, ritmo falado, português do Brasil natural. Nada de listas ou emojis na narração.\n"
        "- Escreva números por extenso quando forem falados (\"trezentos mil\").\n"
        f"- Termine com: {canal['cta']}\n"
        f"- Divida a narração em {cmin} a {cmax} cenas; os trechos, em ordem, devem cobrir a narração inteira.\n"
        f"- Regra visual: {canal['regra_visual_pessoas']}.\n"
        "Responda SOMENTE com JSON neste formato:\n" + FORMATO
    )
    roteiro = llm_json(sistema, f"Pauta: {pauta}", max_tokens=2500)
    palavras = len(roteiro["narracao"].split())
    log("roteirista", f"'{roteiro['titulo']}' — {palavras} palavras, {len(roteiro['cenas'])} cenas")
    return roteiro
