"""Lista os vídeos do canal (id, data, privacidade, duração, título) — inclui não listados e agendados."""
import os

import requests

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ[os.getenv("TOKEN_ENV", "YT_REFRESH_TOKEN")], "grant_type": "refresh_token"}).json()
if "access_token" not in tok:
    raise SystemExit(f"token recusado: {tok}")
print("escopos:", tok.get("scope"))
H = {"Authorization": f"Bearer {tok['access_token']}"}
c = requests.get(f"{API}/channels", headers=H, params={"part": "contentDetails,snippet,statistics", "mine": "true"}).json()["items"][0]
print("CANAL:", c["id"], c["snippet"]["title"], c["snippet"].get("customUrl"), "inscritos:", c["statistics"].get("subscriberCount"))
if os.getenv("IDS"):  # status detalhado de vídeos específicos (envio recusado, processando…)
    v = requests.get(f"{API}/videos", headers=H, params={"part": "status,processingDetails,contentDetails,snippet",
                                                          "id": os.environ["IDS"]}).json()
    print("IDS pedidos:", os.environ["IDS"], "encontrados:", len(v.get("items", [])))
    for x in v.get("items", []):
        print("STATUS", x["id"], x["status"], x.get("processingDetails"), x["contentDetails"].get("duration"),
              x["snippet"]["thumbnails"].get("maxres", x["snippet"]["thumbnails"].get("high", {})).get("url"))
pl = c["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tk = [], None
while True:
    r = requests.get(f"{API}/playlistItems", headers=H, params={"part": "contentDetails", "playlistId": pl,
                                                                 "maxResults": 50, "pageToken": tk}).json()
    ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
    tk = r.get("nextPageToken")
    if not tk or len(ids) >= int(os.getenv("LIMITE", "60")):
        break
for k in range(0, len(ids), 50):
    v = requests.get(f"{API}/videos", headers=H, params={"part": "snippet,status,contentDetails,statistics",
                                                          "id": ",".join(ids[k:k + 50])}).json()
    for x in v.get("items", []):
        print("\t".join([x["id"], x["snippet"]["publishedAt"][:16], x["status"]["privacyStatus"],
                         x["status"].get("publishAt", "")[:16], x["contentDetails"]["duration"],
                         x["statistics"].get("viewCount", "0"), x["snippet"]["title"]]))
