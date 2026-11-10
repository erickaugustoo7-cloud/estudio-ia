"""Publica o vídeo de uma issue aprovada e registra o resultado na própria issue.

Uso: python -m estudio.publicar --issue 12
"""
import argparse
import json
import os
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

    info = json.loads(gh("issue", "view", n, "--json", "body,labels,state,comments,createdAt"))
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

    so = [x.strip() for x in os.getenv("PLATAFORMAS", "").split(",") if x.strip()]
    if so:  # publicar só nas plataformas pedidas (ex.: PLATAFORMAS=facebook)
        canal = {**canal, "publicar_em": [p for p in canal["publicar_em"] if p in so]}
        log("publicar", f"somente: {', '.join(canal['publicar_em'])}")

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
    rot = video.parent / "roteiro.json"
    roteiro = json.loads(rot.read_text(encoding="utf-8")) if rot.exists() else {}
    if roteiro.get("plataformas"):  # ex.: filme longo vai só para o YouTube
        canal = {**canal, "publicar_em": [p for p in canal["publicar_em"] if p in roteiro["plataformas"]]}
        log("publicar", f"plataformas do vídeo: {', '.join(canal['publicar_em'])}")
    # Vídeos feitos antes de 09/11/2026 09:15 UTC usam trilhas da Pixabay, que o Content ID do YouTube reivindica:
    # com mais de 60 s o Short é bloqueado no mundo todo. Esses não vão para o YouTube (seguem para as outras redes).
    if "youtube" in canal["publicar_em"] and info.get("createdAt", "9") < "2026-11-09T09:15:00Z":
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(video)], capture_output=True, text=True).stdout.strip() or 0)
        if dur > 60:
            canal = {**canal, "publicar_em": [p for p in canal["publicar_em"] if p != "youtube"]}
            log("publicar", f"música antiga (Pixabay) e {dur:.0f}s: fora do YouTube para não ser bloqueado")
    res = publicador.publicar(canal, video, dados["texto_post"], fb_video_id=fb_ant,
                              titulo=roteiro.get("titulo_youtube") or roteiro.get("titulo", ""), tags=roteiro.get("hashtags"))

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
    if sucesso and so:
        gh("issue", "edit", n, "--remove-label", "publicando", "--remove-label", "aprovado")
    elif sucesso:
        gh("issue", "edit", n, "--add-label", "publicado", "--remove-label", "publicando")
        gh("issue", "close", n)
    else:
        gh("issue", "edit", n, "--remove-label", "publicando", "--remove-label", "aprovado")
        log("publicar", "houve falha — confira o comentário na issue e aprove de novo se fizer sentido")


if __name__ == "__main__":
    main()
