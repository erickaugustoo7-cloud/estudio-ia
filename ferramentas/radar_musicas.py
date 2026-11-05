"""Músicas religiosas em alta (YouTube Data API, região BR) — para escolher o som dos vídeos no TikTok.
Salva dados/radar/<data>_musicas.json. Requer YOUTUBE_API_KEY."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://www.googleapis.com/youtube/v3"
BUSCAS = ["louvor", "música gospel", "hino gospel", "adoração", "louvor instrumental",
          "worship", "música gospel 2026", "fundo musical oração", "gospel lançamento"]


def main():
    chave = os.environ["YOUTUBE_API_KEY"]
    ids, origem = [], {}
    for dias, ordem in ((30, "viewCount"), (7, "viewCount")):
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for q in BUSCAS:
            r = requests.get(f"{API}/search", timeout=30, params={
                "key": chave, "part": "id", "type": "video", "q": q, "videoCategoryId": "10",
                "regionCode": "BR", "relevanceLanguage": "pt", "publishedAfter": desde,
                "order": ordem, "maxResults": 25})
            r.raise_for_status()
            for it in r.json().get("items", []):
                v = it["id"]["videoId"]
                if v not in origem:
                    ids.append(v)
                    origem[v] = f"{q} ({dias}d)"
    # parada oficial de música mais popular no Brasil (filtrada depois para gospel)
    r = requests.get(f"{API}/videos", timeout=30, params={
        "key": chave, "part": "id", "chart": "mostPopular", "regionCode": "BR",
        "videoCategoryId": "10", "maxResults": 50})
    for it in r.json().get("items", []):
        if it["id"] not in origem:
            ids.append(it["id"])
            origem[it["id"]] = "em alta BR (música)"
    videos = []
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos", timeout=30, params={
            "key": chave, "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])})
        for v in r.json().get("items", []):
            sn, st = v["snippet"], v.get("statistics", {})
            videos.append({"titulo": sn["title"], "canal": sn["channelTitle"], "publicado": sn["publishedAt"][:10],
                           "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                           "duracao": v["contentDetails"].get("duration"), "origem": origem[v["id"]],
                           "idioma": sn.get("defaultAudioLanguage"), "url": f"https://youtu.be/{v['id']}",
                           "tags": sn.get("tags", [])[:10]})
    videos.sort(key=lambda v: v["views"], reverse=True)
    destino = Path("dados/radar") / f"{datetime.now(timezone.utc):%Y-%m-%d}_musicas.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(videos), "vídeos →", destino)


if __name__ == "__main__":
    main()
