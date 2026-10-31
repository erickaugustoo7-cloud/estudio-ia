"""Diretor: escolhe a próxima pauta (sua fila primeiro; se vazia, cria uma nova sem repetir)."""
import json

from estudio.base import RAIZ, llm_json, log


def _arquivo_pautas(slug):
    return RAIZ / "pautas" / f"{slug}.txt"


def _arquivo_historico(slug):
    return RAIZ / "historico" / f"{slug}.json"


def carregar_historico(slug) -> list:
    arq = _arquivo_historico(slug)
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []


def registrar_no_historico(slug, titulo, pauta) -> None:
    hist = carregar_historico(slug)
    hist.append({"titulo": titulo, "pauta": pauta})
    arq = _arquivo_historico(slug)
    arq.parent.mkdir(exist_ok=True)
    arq.write_text(json.dumps(hist[-300:], ensure_ascii=False, indent=1), encoding="utf-8")


def proxima_pauta(canal: dict, pauta_manual: str | None = None) -> str:
    slug = canal["slug"]
    if pauta_manual:
        log("diretor", f"pauta manual: {pauta_manual}")
        return pauta_manual

    arq = _arquivo_pautas(slug)
    linhas = arq.read_text(encoding="utf-8").splitlines() if arq.exists() else []
    for i, linha in enumerate(linhas):
        if linha.strip() and not linha.strip().startswith("#"):
            del linhas[i]  # consome a pauta
            arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
            log("diretor", f"pauta da fila: {linha.strip()}")
            return linha.strip()

    # Fila vazia: o Diretor cria uma pauta nova, evitando repetir o histórico
    ja_feitos = [h["titulo"] for h in carregar_historico(slug)][-80:]
    r = llm_json(
        sistema=(
            f"Você é o diretor de conteúdo do canal '{canal['nome']}'.\n"
            f"Persona: {canal['persona']}\n"
            "Linha editorial:\n- " + "\n- ".join(canal["linha_editorial"])
        ),
        usuario=(
            "Proponha UMA pauta nova para um vídeo vertical de ~70 segundos com alto potencial "
            "de retenção e compartilhamento. Não repita nem se aproxime destes temas já feitos:\n"
            + "\n".join(f"- {t}" for t in ja_feitos)
            + '\n\nResponda só com JSON: {"pauta": "..."}'
        ),
        max_tokens=200,
    )
    log("diretor", f"pauta criada: {r['pauta']}")
    return r["pauta"]
