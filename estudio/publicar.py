"""Publica o vídeo de uma issue aprovada e registra o resultado na própria issue.

Uso: python -m estudio.publicar --issue 12
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from estudio.base import carregar_canal, log
from estudio.agentes import publicador
from estudio.produzir import MARCA_FIM, MARCA_INI


def gh(*args) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    n = ap.parse_args().issue

    info = json.loads(gh("issue", "view", n, "--json", "body,labels,state,comments"))
    etiquetas = {l["name"] for l in info["labels"]}
    if "publicado" in etiquetas or info["state"] != "OPEN":
        log("publicar", "issue já publicada ou fechada — nada a fazer (evita post duplicado)")
        return

    trecho = info["body"].split(MARCA_INI, 1)[1].split(MARCA_FIM, 1)[0]
    dados = json.loads(re.search(r"\{.*\}", trecho, re.S).group(0))
    canal = carregar_canal(dados["canal"])

    # Plataformas que já saíram numa tentativa anterior não são publicadas de novo
    ja_feitas = {p for c in info.get("comments", []) for p in canal["publicar_em"]
                 if f"✅ **{p}**" in c.get("body", "")}
    if ja_feitas:
        canal = {**canal, "publicar_em": [p for p in canal["publicar_em"] if p not in ja_feitas]}
        log("publicar", f"já publicadas antes: {', '.join(sorted(ja_feitas))}")

    subprocess.run(["gh", "label", "create", "publicando", "--color", "C5DEF5", "--force"], capture_output=True)
    gh("issue", "edit", n, "--add-label", "publicando")

    # Baixa o vídeo do artefato da execução que o produziu
    destino = Path("baixado") / n
    destino.mkdir(parents=True, exist_ok=True)
    try:
        gh("run", "download", dados["run_id"], "-n", dados["artefato"], "-D", str(destino))
    except subprocess.CalledProcessError as e:
        gh("issue", "edit", n, "--remove-label", "publicando", "--remove-label", "aprovado")
        gh("issue", "comment", n, "--body",
           f"❌ Não consegui baixar o vídeo (artefatos expiram em 14 dias). Detalhe: {e.stderr[:300]}")
        return
    video = next(destino.rglob(f"{dados['pasta']}/video.mp4"), None) or next(destino.rglob("video.mp4"))
    fb_ant = next((m.group(1) for c in info.get("comments", [])
                   for m in [re.search(r"facebook\.com/reel/(\d+)", c.get("body", ""))] if m), None)
    res = publicador.publicar(canal, video, dados["texto_post"], fb_video_id=fb_ant)

    linhas = ["## 📤 Resultado da publicação"]
    sucesso = True
    for plat, r in res.items():
        st = r.get("status")
        if st == "published":
            linhas.append(f"- ✅ **{plat}**: publicado {r.get('publicUrl', '')}")
        else:
            sucesso = False
            linhas.append(f"- ❌ **{plat}**: {st} — {r.get('errorMessage', '')}")
    linhas.append("- 📱 **tiktok**: postagem manual com o vídeo do Telegram")
    gh("issue", "comment", n, "--body", "\n".join(linhas))
    if sucesso:
        publicador.telegram_mensagem("📤 Publicado!\n" + "\n".join(
            f"• {p}: {r.get('publicUrl', '')}" for p, r in res.items()) + "\nFalta só o TikTok (vídeo e legenda acima).")
    subprocess.run(["gh", "label", "create", "publicado", "--color", "0E8A16", "--force"], capture_output=True)
    if sucesso:
        gh("issue", "edit", n, "--add-label", "publicado", "--remove-label", "publicando")
        gh("issue", "close", n)
    else:
        gh("issue", "edit", n, "--remove-label", "publicando", "--remove-label", "aprovado")
        log("publicar", "houve falha — confira o comentário na issue e aprove de novo se fizer sentido")


if __name__ == "__main__":
    main()
