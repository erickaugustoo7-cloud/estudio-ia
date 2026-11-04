"""Utilidades compartilhadas: caminhos, config dos canais, LLM e log."""
import json
import os
import re
import time
from pathlib import Path

import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"


def log(agente: str, msg: str) -> None:
    print(f"[{agente}] {msg}", flush=True)


def _texto(item) -> str:
    """Um item de lista do YAML com "texto: mais texto" vira dict; devolve como frase."""
    if isinstance(item, dict):
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def carregar_canal(slug: str) -> dict:
    with open(RAIZ / "canais" / f"{slug}.yaml", encoding="utf-8") as f:
        canal = yaml.safe_load(f)
    for chave in ("linha_editorial", "proibido"):
        canal[chave] = [_texto(i) for i in canal.get(chave, [])]
    return canal


# ---------------------------------------------------------------------------
# LLM gratuito com fallback automático.
# Todos os provedores falam o formato OpenAI (chat/completions), então é um cliente só.
# Ordem padrão: Groq → Gemini → Pollinations (este último nem precisa de chave).
# Troque a ordem com a variável LLM_PROVEDORES, ex.: "gemini,groq,pollinations".
# ---------------------------------------------------------------------------
def gemini_flash() -> str:
    """Modelo Gemini Flash mais novo disponível para a chave (os nomes mudam com o tempo)."""
    global _GEMINI_CACHE
    if os.getenv("GEMINI_MODEL"):
        return os.environ["GEMINI_MODEL"]
    if _GEMINI_CACHE:
        return _GEMINI_CACHE
    _GEMINI_CACHE = "gemini-flash-latest"
    chave = os.getenv("GEMINI_API_KEY")
    if chave:
        try:
            import re as _re
            import requests as _rq
            r = _rq.get("https://generativelanguage.googleapis.com/v1beta/models",
                        params={"key": chave, "pageSize": 200}, timeout=20)
            nomes = []
            for m in r.json().get("models", []):
                n = m["name"].split("/")[-1]
                if ("generateContent" in m.get("supportedGenerationMethods", []) and _re.fullmatch(r"gemini-\d+(\.\d+)?-flash", n)):
                    nomes.append(n)
            if nomes:
                _GEMINI_CACHE = max(nomes, key=lambda n: float(_re.search(r"\d+(\.\d+)?", n).group()))
        except Exception:  # noqa: BLE001
            pass
    return _GEMINI_CACHE


_GEMINI_CACHE = ""

PROVEDORES = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "chave": "GROQ_API_KEY",
        "modelo": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "json_mode": True,
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "chave": "GEMINI_API_KEY",
        "modelo": None,  # descoberto na hora: gemini_flash()
        "json_mode": True,
    },
    "pollinations": {
        "url": "https://text.pollinations.ai/openai",
        "chave": "POLLINATIONS_API_KEY",  # opcional
        "chave_opcional": True,
        "modelo": os.getenv("POLLINATIONS_TEXT_MODEL", "openai"),
        "json_mode": False,
    },
}


def _extrair_json(texto: str) -> dict:
    texto = re.sub(r"<think>.*?</think>", "", texto.strip(), flags=re.S)  # modelos que "pensam alto"
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.S)
    if m:
        texto = m.group(1)
    else:
        ini, fim = texto.find("{"), texto.rfind("}")
        texto = texto[ini : fim + 1]
    return json.loads(texto)


def _chamar(nome: str, cfg: dict, sistema: str, usuario: str, max_tokens: int) -> str:
    chave = os.getenv(cfg["chave"])
    if not chave and not cfg.get("chave_opcional"):
        raise LookupError(f"{cfg['chave']} não configurada")
    corpo = {
        "model": cfg["modelo"] or gemini_flash(),
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    if cfg["json_mode"]:
        corpo["response_format"] = {"type": "json_object"}
    if "gpt-oss" in (cfg["modelo"] or ""):
        corpo["reasoning_effort"] = "low"  # raciocínio curto: menos tokens, cabe no limite por minuto
        corpo["max_tokens"] = max_tokens + 1500
    headers = {"Content-Type": "application/json"}
    if chave:
        headers["Authorization"] = f"Bearer {chave}"

    for tentativa in range(3):
        r = requests.post(cfg["url"], json=corpo, headers=headers, timeout=180)
        if r.status_code == 429 or r.status_code >= 500:  # limite por minuto ou instabilidade: espera e tenta de novo
            espera = min(int(float(r.headers.get("retry-after", 20 * (tentativa + 1)))), 90)
            log("llm", f"{nome}: HTTP {r.status_code}, aguardando {espera}s")
            time.sleep(espera)
            continue
        if r.status_code == 400 and ("response_format" in corpo or "reasoning_effort" in corpo):
            corpo.pop("response_format", None)  # provedor/modelo não aceita esses campos: tenta sem
            corpo.pop("reasoning_effort", None)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""
    raise RuntimeError(f"{nome}: limite de requisições persistente")


def llm_json(sistema: str, usuario: str, max_tokens: int = 2000) -> dict:
    """Pede uma resposta em JSON, tentando cada provedor gratuito até um funcionar."""
    ordem = [p.strip() for p in os.getenv("LLM_PROVEDORES", "groq,gemini,pollinations").split(",") if p.strip()]
    sistema += "\n\nResponda SOMENTE com um objeto JSON válido, sem texto antes ou depois."
    erros = []
    for nome in ordem:
        cfg = PROVEDORES[nome]
        for tentativa in range(2):
            try:
                texto = _chamar(nome, cfg, sistema, usuario, max_tokens)
                resultado = _extrair_json(texto)
                log("llm", f"respondido por {nome} ({cfg['modelo']})")
                return resultado
            except LookupError as e:  # provedor sem chave: pula direto
                erros.append(f"{nome}: {e}")
                break
            except (json.JSONDecodeError, ValueError, KeyError):
                erros.append(f"{nome}: JSON inválido (tentativa {tentativa + 1})")
            except requests.RequestException as e:
                erros.append(f"{nome}: {e}")
                break
            except RuntimeError as e:
                erros.append(str(e))
                break
    raise RuntimeError("Nenhum LLM gratuito respondeu: " + " | ".join(erros))
