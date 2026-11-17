"""Mostra dados públicos de um vídeo de referência (título, canal, números, descrição, tags) via YouTube Data API."""
import os
import sys

import requests

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).json()
H = {"Authorization": f"Bearer {tok['access_token']}"}
for vid in sys.argv[1].split(","):
    v = requests.get(f"{API}/videos", headers=H, params={"part": "snippet,contentDetails,statistics,topicDetails", "id": vid}).json()
    if not v.get("items"):
        print("não encontrado:", vid, str(v)[:300]); continue
    v = v["items"][0]; sn = v["snippet"]
    c = requests.get(f"{API}/channels", headers=H, params={"part": "snippet,statistics", "id": sn["channelId"]}).json()["items"][0]
    print("=" * 70)
    print("TÍTULO:", sn["title"])
    print("CANAL:", c["snippet"]["title"], "| inscritos:", c["statistics"].get("subscriberCount"),
          "| vídeos:", c["statistics"].get("videoCount"), "| views totais:", c["statistics"].get("viewCount"))
    print("PUBLICADO:", sn["publishedAt"], "| DURAÇÃO:", v["contentDetails"]["duration"])
    print("VIEWS:", v["statistics"].get("viewCount"), "| LIKES:", v["statistics"].get("likeCount"),
          "| COMENTÁRIOS:", v["statistics"].get("commentCount"))
    print("IDIOMA:", sn.get("defaultLanguage"), sn.get("defaultAudioLanguage"))
    print("THUMB:", sn["thumbnails"].get("maxres", sn["thumbnails"]["high"])["url"])
    print("TAGS:", ", ".join(sn.get("tags", [])))
    print("DESCRIÇÃO:\n" + sn.get("description", ""))
    cm = requests.get(f"{API}/commentThreads", headers=H, params={"part": "snippet", "videoId": vid, "maxResults": 15, "order": "relevance"}).json()
    print("\nCOMENTÁRIOS EM DESTAQUE:")
    for t in cm.get("items", []):
        s = t["snippet"]["topLevelComment"]["snippet"]
        print(f"- ({s.get('likeCount')}👍) {s['textOriginal'][:200]}")
