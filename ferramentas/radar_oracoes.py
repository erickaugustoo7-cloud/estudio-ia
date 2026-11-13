"""Radar de orações longas: vídeos de oração mais vistos no YouTube Brasil nos últimos 30 dias (API oficial)."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://www.googleapis.com/youtube/v3"
BUSCAS = ["oração para dormir", "oração da noite", "oração poderosa", "oração da madrugada", "salmo para dormir"]


def main():
    chave = os.environ["YOUTUBE_API_KEY"]
    desde = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, origem = [], {}
    for q in BUSCAS:
        r = requests.get(f"{API}/search", timeout=30, params={
            "key": chave, "part": "snippet", "q": q, "type": "video", "regionCode": "BR", "relevanceLanguage": "pt",
            "publishedAfter": desde, "order": "viewCount", "videoDuration": "long", "maxResults": 25})
        r.raise_for_status()
        for it in r.json().get("items", []):
            v = it["id"]["videoId"]
            if v not in origem:
                ids.append(v)
                origem[v] = q
    videos = []
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos", timeout=30, params={"key": chave, "part": "snippet,statistics,contentDetails",
                                                               "id": ",".join(ids[i:i + 50])})
        r.raise_for_status()
        for it in r.json().get("items", []):
            s, st = it["snippet"], it.get("statistics", {})
            videos.append({"titulo": s["title"], "canal": s["channelTitle"], "publicado": s["publishedAt"][:10],
                           "views": int(st.get("viewCount", 0)), "duracao": it["contentDetails"]["duration"],
                           "busca": origem[it["id"]]})
    videos.sort(key=lambda x: -x["views"])
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    Path("dados/radar").mkdir(parents=True, exist_ok=True)
    Path(f"dados/radar/{hoje}_oracoes.json").write_text(json.dumps({"coletado_em": hoje, "videos": videos},
                                                                    ensure_ascii=False, indent=1))
    for v in videos[:40]:
        print(f"{v['views']:>9} | {v['titulo'][:90]} | {v['canal']}")


if __name__ == "__main__":
    main()
