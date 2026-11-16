"""Fotografa as métricas públicas do canal no YouTube (Data API) para medir o impacto das mudanças.
Grava dados/metricas/youtube_<data>.json e imprime um resumo comparando com a fotografia anterior."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://www.googleapis.com/youtube/v3"
CHAVE = os.environ["YOUTUBE_API_KEY"]
HANDLE = os.getenv("YT_HANDLE", "@MensageirodeF")
PASTA = Path("dados/metricas")


def get(rec, **p):
    r = requests.get(f"{API}/{rec}", params={**p, "key": CHAVE}, timeout=30)
    r.raise_for_status()
    return r.json()


def segundos(iso):
    h, m, s = (int(x or 0) for x in re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso).groups())
    return h * 3600 + m * 60 + s


canal = get("channels", part="statistics,contentDetails,snippet", forHandle=HANDLE)["items"][0]
uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while True:
    pl = get("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50, **({"pageToken": tok} if tok else {}))
    ids += [i["contentDetails"]["videoId"] for i in pl["items"]]
    tok = pl.get("nextPageToken")
    if not tok:
        break
videos = []
for k in range(0, len(ids), 50):
    for v in get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[k:k + 50]))["items"]:
        st = v["statistics"]
        videos.append({"id": v["id"], "titulo": v["snippet"]["title"], "publicado": v["snippet"]["publishedAt"],
                       "duracao_s": segundos(v["contentDetails"]["duration"]), "views": int(st.get("viewCount", 0)),
                       "likes": int(st.get("likeCount", 0)), "comentarios": int(st.get("commentCount", 0))})
agora = datetime.now(timezone.utc)
foto = {"data": agora.isoformat(), "inscritos": int(canal["statistics"].get("subscriberCount", 0)),
        "views_total": int(canal["statistics"].get("viewCount", 0)), "videos": videos}
PASTA.mkdir(parents=True, exist_ok=True)
anteriores = sorted(PASTA.glob("youtube_*.json"))
destino = PASTA / f"youtube_{agora:%Y-%m-%d_%H%M}.json"
destino.write_text(json.dumps(foto, ensure_ascii=False, indent=1))

longos = [v for v in videos if v["duracao_s"] > 180]
shorts = [v for v in videos if v["duracao_s"] <= 180]
print(f"Inscritos: {foto['inscritos']} · views totais: {foto['views_total']} · vídeos: {len(videos)} "
      f"({len(longos)} longos, {len(shorts)} Shorts)")
if anteriores:
    ant = json.loads(anteriores[-1].read_text())
    dias = (agora - datetime.fromisoformat(ant["data"])).total_seconds() / 86400
    print(f"Desde {ant['data'][:10]} ({dias:.1f} dias): +{foto['inscritos'] - ant['inscritos']} inscritos, "
          f"+{foto['views_total'] - ant['views_total']} views")
    vant = {v["id"]: v for v in ant["videos"]}
    novos = [v for v in videos if v["id"] not in vant]
    if novos:
        print("Vídeos novos desde a última fotografia:")
        for v in sorted(novos, key=lambda x: -x["views"]):
            print(f"  {v['views']:>6} views · {v['likes']} likes · {v['comentarios']} coment. · "
                  f"{v['duracao_s'] // 60} min · {v['titulo'][:70]}")
print("Top 10 por views:")
for v in sorted(videos, key=lambda x: -x["views"])[:10]:
    print(f"  {v['views']:>6} · {'longo' if v['duracao_s'] > 180 else 'Short'} · {v['titulo'][:70]}")
sys.exit(0)
