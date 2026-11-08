"""Leva vídeos curtos já aprovados (issues) para o YouTube como Shorts, espaçando as publicações.

Uso: python -m estudio.youtube_shorts --issues 99,84,113 --intervalo 3
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from estudio.agentes import publicador
from estudio.base import log
from estudio.produzir import MARCA_FIM, MARCA_INI


def gh(*args) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issues", required=True)
    ap.add_argument("--intervalo", type=float, default=3, help="horas entre um Short e o próximo (0 = todos agora)")
    a = ap.parse_args()
    linhas, agora = [], datetime.now(timezone.utc)
    for k, n in enumerate(x.strip() for x in a.issues.split(",") if x.strip()):
        info = json.loads(gh("issue", "view", n, "--json", "body,title,comments"))
        if any("✅ **youtube**" in c.get("body", "") for c in info.get("comments", [])):
            log("shorts", f"#{n} já está no YouTube — pulando")
            continue
        trecho = info["body"].split(MARCA_INI, 1)[1].split(MARCA_FIM, 1)[0]
        dados = json.loads(re.search(r"\{.*\}", trecho, re.S).group(0))
        destino = Path("baixado") / n
        destino.mkdir(parents=True, exist_ok=True)
        try:
            gh("run", "download", str(dados["run_id"]), "-n", dados["artefato"], "-D", str(destino))
        except subprocess.CalledProcessError as e:
            linhas.append(f"❌ #{n}: não consegui baixar o vídeo ({e.stderr[:120]})")
            continue
        video = next(destino.rglob("video.mp4"))
        rot = video.parent / "roteiro.json"
        roteiro = json.loads(rot.read_text(encoding="utf-8")) if rot.exists() else {}
        titulo = (roteiro.get("titulo") or info["title"].split("] ", 1)[-1]).strip()
        titulo = f"{titulo} 🙏 #shorts"
        quando = None
        if a.intervalo and k:
            quando = (agora + timedelta(hours=a.intervalo * k)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        try:
            r = publicador.youtube_upload(video, titulo, dados["texto_post"], roteiro.get("hashtags"), agendar=quando)
        except Exception as e:  # noqa: BLE001
            r = {"status": "failed", "errorMessage": str(e)[:300]}
        if r["status"] == "published":
            hora = (datetime.fromisoformat(quando.replace(".000Z", "+00:00")) - timedelta(hours=3)).strftime("%d/%m %H:%M") \
                if quando else "agora"
            gh("issue", "comment", n, "--body", f"- ✅ **youtube** (Short, publica {hora}): {r['publicUrl']}")
            linhas.append(f"✅ {titulo} — {hora} — {r['publicUrl']}")
        else:
            linhas.append(f"❌ {titulo}: {r.get('errorMessage', '')}")
        log("shorts", linhas[-1])
    if linhas:
        publicador.telegram_mensagem("▶️ Shorts no YouTube\n" + "\n".join(linhas))


if __name__ == "__main__":
    main()
