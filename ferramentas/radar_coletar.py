"""Radar: coleta o que está viralizando no nicho (YouTube Shorts BR, API oficial) para cada canal.

Salva dados/radar/<data>_<canal>.json com os vídeos curtos mais vistos dos últimos 7 dias
(título, canal, visualizações, curtidas, comentários, duração, data, descrição curta).
A análise (padrões de gancho, temas, duração) é feita depois pela sessão do Claude.

Requer o segredo YOUTUBE_API_KEY (YouTube Data API v3, gratuita). Sem chave, não coleta.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BUSCAS = {
    "biblico": ["Jesus", "versículo bíblico", "oração", "palavra de Deus", "história bíblica",
                "mensagem de fé", "Deus fala com você", "salmo"],
    "espaco": ["curiosidades espaço", "astronomia curiosidades", "você sabia ciência",
               "universo curiosidades", "planetas", "como funciona", "buraco negro", "NASA"],
}
API = "https://www.googleapis.com/youtube/v3"


def _segundos(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def coletar(canal: str, chave: str) -> dict:
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, termo_de = [], {}
    for termo in BUSCAS[canal]:
        r = requests.get(f"{API}/search", timeout=30, params={
            "key": chave, "part": "id", "type": "video", "q": termo, "videoDuration": "short",
            "regionCode": "BR", "relevanceLanguage": "pt", "publishedAfter": desde,
            "order": "viewCount", "maxResults": 25})
        r.raise_for_status()
        for it in r.json().get("items", []):
            vid = it["id"]["videoId"]
            if vid not in termo_de:
                ids.append(vid)
                termo_de[vid] = termo
    videos = []
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos", timeout=30, params={
            "key": chave, "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])})
        r.raise_for_status()
        for v in r.json().get("items", []):
            sn, st = v["snippet"], v.get("statistics", {})
            videos.append({
                "id": v["id"], "url": f"https://youtube.com/shorts/{v['id']}", "busca": termo_de[v["id"]],
                "titulo": sn["title"], "canal": sn["channelTitle"], "publicado": sn["publishedAt"],
                "idioma": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                "descricao": (sn.get("description") or "")[:300], "tags": sn.get("tags", [])[:15],
                "duracao_s": _segundos(v["contentDetails"].get("duration")),
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "comentarios": int(st.get("commentCount", 0)),
            })
    videos.sort(key=lambda v: v["views"], reverse=True)
    return {"canal": canal, "coletado_em": datetime.now(timezone.utc).isoformat(), "janela_dias": 7,
            "fonte": "YouTube Data API v3 (Shorts, região BR, pt)", "total": len(videos), "videos": videos[:120]}


def main():
    chave = os.getenv("YOUTUBE_API_KEY")
    if not chave:
        print("YOUTUBE_API_KEY não configurada — nada coletado.")
        sys.exit(0)
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for canal in BUSCAS:
        dados = coletar(canal, chave)
        destino = Path("dados/radar") / f"{hoje}_{canal}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{canal}: {dados['total']} vídeos → {destino}")


if __name__ == "__main__":
    main()
