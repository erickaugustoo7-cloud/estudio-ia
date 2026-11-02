"""Roteirista: transforma a pauta em roteiro completo (narração, cenas, legenda, hashtags)."""
import json

from estudio.base import llm_json, log

FORMATO = """{
  "titulo": "título curto interno",
  "gancho_tela": "texto grande na tela nos 3 primeiros segundos (máx. 7 palavras)",
  "narracao": "texto corrido que será narrado, começando pelo gancho",
  "cenas": [
    {"trecho": "frase da narração que esta cena cobre (copie literalmente)",
     "busca_imagem": "2-4 english keywords to search a real photo or classic painting of this scene",
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
        "- GANCHO (o mais importante: 70% das pessoas decidem em 2 segundos se ficam):\n"
        "  * A primeira frase narrada tem no máximo 10 palavras, fala direto com 'você' e cria curiosidade "
        "ou identificação imediata (ex.: 'Se você acordou ansioso hoje, ouça isso.' / "
        "'Você nunca mais vai olhar a Lua do mesmo jeito.').\n"
        "  * Nunca comece com saudação, com o nome do canal ou repetindo o título.\n"
        "  * PADRÃO QUE MAIS RETÉM (dados reais do canal): abrir com um fato surpreendente ou um mistério "
        "que só se resolve no final — um 'loop aberto'. Ex. vencedor: 'Existe um versículo de apenas duas "
        "palavras que revela o coração de Deus.' A pessoa fica para descobrir qual é.\n"
        "  * A segunda frase (até ~6 segundos) entrega uma MINI-RESPOSTA concreta e curta e já abre uma nova "
        "pergunta. Ex. vencedor: gancho 'Existe um versículo de apenas duas palavras que revela o coração de Deus.' "
        "→ 2ª frase 'Jesus chorou. Está em João onze, trinta e cinco.' NUNCA use a 2ª frase para dar contexto "
        "('Era o dia...', 'Naquela época...') — dados do canal mostram que isso derruba a retenção.\n"
        "  * A PRIMEIRA cena cobre SOMENTE a frase do gancho (corte de imagem por volta de 3 segundos); "
        "nas cenas seguintes, troque de imagem a cada 1 ou 2 frases.\n"
        "  * PROIBIDO tom de aula: nada de 'Descubra', 'Vamos entender', 'explicado', 'frase a frase', "
        "'Neste vídeo'. Conte como HISTÓRIA (personagem, problema, virada), não como estudo.\n"
        "  * Guarde a revelação mais forte para perto do fim e prometa-a no começo "
        "(ex.: 'e o final dessa história muda tudo').\n"
        "  * gancho_tela: frase de até 7 palavras para a tela, complementa a fala (não a repete), "
        "desperta curiosidade ou emoção. Sem emojis.\n"
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
    if palavras < pmin:  # modelos gratuitos costumam encurtar: pede para estender uma vez
        roteiro = estender(canal, roteiro, pmin + 15 - palavras)
    return roteiro


def estender(canal: dict, roteiro: dict, faltam: int) -> dict:
    """Acrescenta ~`faltam` palavras de conteúdo novo, mantendo gancho e CTA."""
    sistema = (
        f"Você é o roteirista do canal '{canal['nome']}'. O roteiro abaixo ficou curto demais: "
        "o vídeo precisa passar de 60 segundos.\n"
        f"Acrescente cerca de {faltam} palavras de conteúdo NOVO e interessante (um detalhe extra, "
        "um exemplo do dia a dia, uma curiosidade relacionada) no meio da narração. "
        "Mantenha o gancho no início e o CTA no final. Não invente fatos: use só o que você tem certeza.\n"
        "Atualize as cenas para que os trechos, em ordem, cubram a narração inteira "
        "(pode acrescentar 1 ou 2 cenas). Mantenha os demais campos.\n"
        "Responda SOMENTE com o roteiro completo em JSON, no mesmo formato:\n" + FORMATO
    )
    novo = llm_json(sistema, json.dumps(roteiro, ensure_ascii=False), max_tokens=3000)
    if len(novo.get("narracao", "").split()) > len(roteiro["narracao"].split()) and novo.get("cenas"):
        log("roteirista", f"estendido para {len(novo['narracao'].split())} palavras")
        return {**roteiro, **novo}
    return roteiro
