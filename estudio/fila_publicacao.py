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


def publicar():
    fila = [i for i in _issues("open", "fila") if not {l["name"] for l in i["labels"]} & {"publicado", "publicando"}]
    por_canal: dict[str, dict] = {}
    for i in sorted(fila, key=lambda x: -x["number"]):
        canal = next((l["name"].split(":", 1)[1] for l in i["labels"] if l["name"].startswith("canal:")), "?")
        por_canal.setdefault(canal, i)
    for canal, i in por_canal.items():
        n = str(i["number"])
        log("fila", f"{canal}: publicando #{n} {i['title']}")
        r = subprocess.run([sys.executable, "-m", "estudio.publicar", "--issue", n])
        estado = json.loads(gh("issue", "view", n, "--json", "state"))["state"]
        if estado != "OPEN":
            continue  # publicado e fechado
        # falhou em alguma rede: sai da fila para não travar os próximos (revisar depois)
        gh("issue", "edit", n, "--remove-label", "fila", "--add-label", "fila-erro")
        log("fila", f"#{n} com falha (código {r.returncode}) → fila-erro")
    restantes = len(fila) - len(por_canal)
    log("fila", f"restam {max(restantes, 0)} na fila")


if __name__ == "__main__":
    {"montar": montar, "publicar": publicar}[sys.argv[1]]()
