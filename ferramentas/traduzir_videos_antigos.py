"""Acrescenta título e descrição em espanhol e inglês (localizations) aos vídeos JÁ publicados no canal."""
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes.publicador import _traducoes_youtube  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).json()
H = {"Authorization": f"Bearer {tok['access_token']}"}
print("escopos do token:", tok.get("scope"))
canal = requests.get(f"{API}/channels", headers=H, params={"part": "contentDetails", "mine": "true"}).json()
uploads = canal["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
ids, pt = [], None
while True:
    r = requests.get(f"{API}/playlistItems", headers=H, params={"part": "contentDetails", "playlistId": uploads,
                                                               "maxResults": 50, **({"pageToken": pt} if pt else {})}).json()
    ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
    pt = r.get("nextPageToken")
    if not pt:
        break
feitos = falhas = 0
for k in range(0, len(ids), 50):
    lote = requests.get(f"{API}/videos", headers=H, params={"part": "snippet,localizations", "id": ",".join(ids[k:k + 50])}).json()
    for v in lote.get("items", []):
        if {"es", "en"} <= set((v.get("localizations") or {}).keys()):
            continue
        sn = v["snippet"]
        loc = _traducoes_youtube(sn["title"], sn.get("description", ""))
        if not loc:
            falhas += 1
            continue
        corpo = {"id": v["id"], "snippet": {"title": sn["title"], "description": sn.get("description", ""),
                                            "categoryId": sn.get("categoryId", "22"), "tags": sn.get("tags", []),
                                            "defaultLanguage": "pt-BR"},
                 "localizations": {**(v.get("localizations") or {}), **loc}}
        r = requests.put(f"{API}/videos", headers=H, params={"part": "snippet,localizations"}, json=corpo)
        if r.ok:
            feitos += 1
            print(f"ok  {sn['title'][:60]}  →  {loc.get('es', {}).get('title', '')[:60]}")
        else:
            falhas += 1
            print(f"ERRO {r.status_code} {sn['title'][:50]}: {r.text[:300]}")
            if r.status_code == 403:
                break
        time.sleep(1)
print(f"\nTraduzidos: {feitos} · falhas: {falhas} · vídeos no canal: {len(ids)}")
