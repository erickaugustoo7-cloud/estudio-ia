"""Fila de publicação: os vídeos aprovados saem aos poucos (alguns por dia, por canal), não todos de uma vez.

Postar dezenas de vídeos no mesmo minuto derruba o alcance, estoura o limite do Instagram (25 posts/24 h pela API)
e o limite de envios do YouTube. A fila resolve isso.

Uso:
  python -m estudio.fila_publicacao montar    # aprova todos os pendentes → etiqueta "fila"
  python -m estudio.fila_publicacao publicar  # publica o próximo da fila de cada canal
"""
import json
import re
import subprocess
import sys

from estudio.base import log
from estudio.produzir import MARCA_FIM, MARCA_INI

FORA = {"publicado", "aprovado", "rejeitado", "publicando", "fila", "fila-erro"}


def gh(*args) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def _issues(estado="open", etiqueta="aprovacao") -> list[dict]:
    return json.loads(gh("issue", "list", "--state", estado, "--label", etiqueta, "--limit", "500",
                         "--json", "number,title,labels,body"))


def _dados(body: str) -> dict | None:
    try:
        trecho = body.split(MARCA_INI, 1)[1].split(MARCA_FIM, 1)[0]
        return json.loads(re.search(r"\{.*\}", trecho, re.S).group(0))
    except Exception:  # noqa: BLE001
        return None


def _artefato_ok(d: dict) -> bool:
    try:
        arts = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{d['run_id']}/artifacts"))["artifacts"]
        return any(a["name"] == d["artefato"] and not a["expired"] for a in arts)
    except Exception:  # noqa: BLE001
        return False


def montar():
    for nome, cor in (("fila", "FBCA04"), ("fila-erro", "D93F0B")):
        subprocess.run(["gh", "label", "create", nome, "--color", cor, "--force"], capture_output=True)
    publicados = {i["title"] for i in _issues("closed", "publicado")}
    vistos, entrou, pulou = set(), [], []
    for i in sorted(_issues(), key=lambda x: -x["number"]):  # mais novo primeiro: versão mais recente fica
        nomes = {l["name"] for l in i["labels"]}
        if nomes & FORA:
            continue
        d = _dados(i["body"] or "")
        if i["title"] in publicados or i["title"] in vistos:
            pulou.append(f"#{i['number']} (repetido)")
            continue
        if not d or not _artefato_ok(d):
            pulou.append(f"#{i['number']} (vídeo expirado)")
            continue
        vistos.add(i["title"])
        gh("issue", "edit", str(i["number"]), "--add-label", "fila")
        entrou.append(i["number"])
    log("fila", f"{len(entrou)} na fila; pulados: {', '.join(pulou) or 'nenhum'}")


def _tentativas(n: str) -> int:
    coms = json.loads(gh("issue", "view", n, "--json", "comments"))["comments"]
    return sum("Resultado da publicação" in c.get("body", "") for c in coms)


def _canal(i: dict) -> str:
    return next((l["name"].split(":", 1)[1] for l in i["labels"] if l["name"].startswith("canal:")), "?")


def _publicar_um(i: dict) -> bool:
    n = str(i["number"])
    log("fila", f"{_canal(i)}: publicando #{n} {i['title']}")
    r = subprocess.run([sys.executable, "-m", "estudio.publicar", "--issue", n])
    if json.loads(gh("issue", "view", n, "--json", "state"))["state"] != "OPEN":
        gh("issue", "edit", n, "--remove-label", "fila", "--remove-label", "fila-erro")
        return True
    # falhou em alguma rede (Instagram instável, limite do YouTube…): vai para "fila-erro" e é tentado de novo
    # nas próximas rodadas — só as redes que faltam, as que já saíram não repetem
    gh("issue", "edit", n, "--remove-label", "fila", "--add-label", "fila-erro")
    log("fila", f"#{n} com falha (código {r.returncode}) → fila-erro")
    return False


def publicar():
    sem = {"publicado", "publicando"}
    fila = [i for i in _issues("open", "fila") if not {l["name"] for l in i["labels"]} & sem]
    erros = [i for i in _issues("open", "fila-erro") if not {l["name"] for l in i["labels"]} & sem]
    novos: dict[str, dict] = {}
    for i in sorted(fila, key=lambda x: -x["number"]):
        novos.setdefault(_canal(i), i)
    repetir: dict[str, dict] = {}
    for i in sorted(erros, key=lambda x: x["number"]):  # 1 nova tentativa por canal, até 5 no total
        if _canal(i) not in repetir and _tentativas(str(i["number"])) < 5:
            repetir[_canal(i)] = i
    for i in [*repetir.values(), *novos.values()]:
        _publicar_um(i)
    log("fila", f"restam {max(len(fila) - len(novos), 0)} na fila; {len(erros)} aguardando nova tentativa")

if __name__ == "__main__":
    {"montar": montar, "publicar": publicar}[sys.argv[1]]()
