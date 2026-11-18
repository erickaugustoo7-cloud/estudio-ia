"""Todos os dados do canal pela API: Data API (vídeos, views, likes, comentários) + Analytics API (se o token tiver
o escopo yt-analytics.readonly: tempo assistido, retenção, origem do tráfego, público)."""
import json
import os
from datetime import date, timedelta

import requests

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ[os.getenv("TOKEN_ENV", "YT_REFRESH_TOKEN")], "grant_type": "refresh_token"}).json()
print("escopos:", tok.get("scope"))
H = {"Authorization": f"Bearer {tok['access_token']}"}
c = requests.get(f"{API}/channels", headers=H, params={"part": "contentDetails,snippet,statistics", "mine": "true"}).json()["items"][0]
out = {"canal": {"id": c["id"], "titulo": c["snippet"]["title"], "criado": c["snippet"]["publishedAt"], **c["statistics"]}}
ids, tk = [], None
while True:
    r = requests.get(f"{API}/playlistItems", headers=H, params={"part": "contentDetails", "maxResults": 50, "pageToken": tk,
                     "playlistId": c["contentDetails"]["relatedPlaylists"]["uploads"]}).json()
    ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
    tk = r.get("nextPageToken")
    if not tk:
        break
vids = []
for k in range(0, len(ids), 50):
    for v in requests.get(f"{API}/videos", headers=H, params={"part": "snippet,contentDetails,statistics,status",
                                                               "id": ",".join(ids[k:k + 50])}).json()["items"]:
        vids.append({"id": v["id"], "titulo": v["snippet"]["title"], "publicado": v["snippet"]["publishedAt"],
                     "dur": v["contentDetails"]["duration"], "status": v["status"]["privacyStatus"],
                     **{x: int(v["statistics"].get(x, 0)) for x in ("viewCount", "likeCount", "commentCount")}})
out["videos"] = vids
# Analytics (precisa do escopo yt-analytics.readonly)
ini, fim = (date.today() - timedelta(days=90)).isoformat(), date.today().isoformat()
def rel(params):
    r = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers=H,
                     params={"ids": "channel==MINE", "startDate": ini, "endDate": fim, **params})
    return r.json() if r.ok else {"erro": r.status_code, "msg": r.text[:200]}
out["analytics"] = {
    "por_video": rel({"dimensions": "video", "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,shares",
                      "sort": "-estimatedMinutesWatched", "maxResults": 200}),
    "por_dia": rel({"dimensions": "day", "metrics": "views,estimatedMinutesWatched,subscribersGained,subscribersLost"}),
    "trafego": rel({"dimensions": "insightTrafficSourceType", "metrics": "views,estimatedMinutesWatched"}),
    "tipo_conteudo": rel({"dimensions": "creatorContentType", "metrics": "views,estimatedMinutesWatched,subscribersGained"}),
    "publico": rel({"dimensions": "ageGroup,gender", "metrics": "viewerPercentage"}),
    "paises": rel({"dimensions": "country", "metrics": "views,estimatedMinutesWatched", "sort": "-views", "maxResults": 10}),
    "dispositivo": rel({"dimensions": "deviceType", "metrics": "views,estimatedMinutesWatched"}),
}
print("ANALISE_JSON:" + json.dumps(out, ensure_ascii=False))
