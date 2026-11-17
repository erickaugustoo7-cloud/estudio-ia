"""Gera e aplica a capa vertical dourada em Shorts já publicados.
Uso: python ferramentas/capas_shorts.py ID1,ID2  (ou "recentes:15" para os Shorts mais novos do canal)."""
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes.publicador import capa_short, linhas_do_titulo  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).json()
H = {"Authorization": f"Bearer {tok['access_token']}"}
saida = Path("capas_shorts"); saida.mkdir(exist_ok=True)
arg = sys.argv[1]
if arg.startswith("recentes"):
    n = int(arg.split(":")[1]) if ":" in arg else 15
    c = requests.get(f"{API}/channels", headers=H, params={"part": "contentDetails", "mine": "true"}).json()["items"][0]
    r = requests.get(f"{API}/playlistItems", headers=H, params={"part": "contentDetails", "maxResults": 50,
                     "playlistId": c["contentDetails"]["relatedPlaylists"]["uploads"]}).json()
    ids = [i["contentDetails"]["videoId"] for i in r["items"]]
else:
    ids, n = arg.split(","), 999
feitos = 0
for k in range(0, len(ids), 50):
    for v in requests.get(f"{API}/videos", headers=H, params={"part": "snippet,contentDetails",
                                                               "id": ",".join(ids[k:k + 50])}).json()["items"]:
        d = v["contentDetails"]["duration"]
        if "H" in d or ("M" in d and int(d.split("PT")[1].split("M")[0]) >= 3) or feitos >= n:
            continue  # só Shorts (até 3 min)
        quadro = saida / f"{v['id']}_quadro.jpg"
        for nome in ("oardefault", "oar2", "maxresdefault", "hqdefault"):
            r = requests.get(f"https://i.ytimg.com/vi/{v['id']}/{nome}.jpg", timeout=30)
            if r.ok and len(r.content) > 5000:
                quadro.write_bytes(r.content); break
        capa = capa_short(quadro, linhas_do_titulo(v["snippet"]["title"]), saida / f"{v['id']}.jpg")
        if not capa:
            continue
        r = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={v['id']}",
                          headers={**H, "Content-Type": "image/jpeg"}, data=capa.read_bytes(), timeout=120)
        print(("ok   " if r.ok else f"ERRO {r.status_code} {r.text[:200]} ") + v["id"] + " " + v["snippet"]["title"])
        feitos += 1
