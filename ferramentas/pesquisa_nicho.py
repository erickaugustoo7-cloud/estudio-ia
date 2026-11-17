"""Pesquisa de nicho no YouTube (Brasil, pt): para cada busca, pega os vídeos mais vistos dos últimos 90 dias e mede
o tamanho e a idade dos canais que estão vencendo. Nicho bom = muitas views + canais pequenos/novos no topo."""
import json
import os
import statistics as st
import sys
from datetime import datetime, timedelta, timezone

import requests

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).json()
H = {"Authorization": f"Bearer {tok['access_token']}"}
agora = datetime.now(timezone.utc)
desde = (agora - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
buscas = [b.strip() for b in open(sys.argv[1], encoding="utf-8") if b.strip() and not b.startswith("#")]
out = []
for q in buscas:
    for dur in ("short", "long"):
        r = requests.get(f"{API}/search", headers=H, params={
            "part": "snippet", "q": q, "type": "video", "order": "viewCount", "publishedAfter": desde,
            "regionCode": "BR", "relevanceLanguage": "pt", "maxResults": 25, "videoDuration": dur}).json()
        if "error" in r:
            print("ERRO", q, str(r)[:200]); continue
        vids = [i["id"]["videoId"] for i in r.get("items", [])]
        if not vids:
            continue
        vs = requests.get(f"{API}/videos", headers=H, params={"part": "statistics,snippet,contentDetails",
                                                               "id": ",".join(vids)}).json()["items"]
        chs = {c["id"]: c for c in requests.get(f"{API}/channels", headers=H, params={
            "part": "statistics,snippet", "id": ",".join({v["snippet"]["channelId"] for v in vs})}).json()["items"]}
        linhas = []
        for v in vs:
            c = chs.get(v["snippet"]["channelId"], {})
            subs = int(c.get("statistics", {}).get("subscriberCount", 0) or 0)
            criado = c.get("snippet", {}).get("publishedAt", "2000-01-01T00:00:00Z")[:10]
            idade = (agora.date() - datetime.fromisoformat(criado).date()).days
            linhas.append({"views": int(v["statistics"].get("viewCount", 0)), "subs": subs, "idade_canal_dias": idade,
                           "canal": c.get("snippet", {}).get("title", "?"), "titulo": v["snippet"]["title"],
                           "id": v["id"], "dur": v["contentDetails"]["duration"]})
        views = [x["views"] for x in linhas]
        pequenos = [x for x in linhas if x["subs"] < 50000]
        novos = [x for x in linhas if x["idade_canal_dias"] < 365]
        res = {"busca": q, "formato": dur, "n": len(linhas), "mediana_views": int(st.median(views)),
               "top3_views": sorted(views, reverse=True)[:3],
               "pct_canais_pequenos": round(100 * len(pequenos) / len(linhas)),
               "pct_canais_novos": round(100 * len(novos) / len(linhas)),
               "mediana_views_pequenos": int(st.median([x["views"] for x in pequenos])) if pequenos else 0,
               "exemplos_pequenos": sorted(pequenos, key=lambda x: -x["views"])[:3]}
        out.append(res)
        print(f"{q:42s} {dur:5s} mediana={res['mediana_views']:>9,} pequenos={res['pct_canais_pequenos']:>3}% "
              f"novos={res['pct_canais_novos']:>3}% med_peq={res['mediana_views_pequenos']:>9,}")
json.dump(out, open("pesquisa_nicho.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
