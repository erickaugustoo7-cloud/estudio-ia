"""Corrige títulos/descrições/traduções dos vídeos do Antes de Nós que herdaram textos do Mensageiro (oração, 🙏, Amém).
Eric viu "oração" na descrição dos vídeos do canal de documentários (24/11)."""
import os
import re
import sys

import requests

sys.path.insert(0, os.getcwd())
from estudio.agentes.publicador import _traducoes_youtube  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_REFRESH_TOKEN_CURIOSO"], "grant_type": "refresh_token"}).json()
H = {"Authorization": f"Bearer {tok['access_token']}"}
c = requests.get(f"{API}/channels", headers=H, params={"part": "contentDetails,snippet", "mine": "true"}).json()["items"][0]
assert "Antes" in c["snippet"]["title"], f"token não é do Antes de Nós: {c['snippet']['title']}"
pl = c["contentDetails"]["relatedPlaylists"]["uploads"]
ids = [i["contentDetails"]["videoId"] for i in requests.get(f"{API}/playlistItems", headers=H, params={
    "part": "contentDetails", "playlistId": pl, "maxResults": 50}).json().get("items", [])]
CTA = ("🔔 Inscreva-se no Antes de Nós e ative o sininho: documentários sobre o mundo antes de nós — pré-história, "
       "primeiras civilizações e os mistérios da história humana.")
TROCAS = [
    (r"🔔 Inscreva-se no Mensageiro de Fé[^\n]*", CTA),
    (r"A oração completa para dormir está no vídeo relacionado\.\s*Escreva Amém e inscreva-se para orarmos juntos toda noite\.",
     "O documentário completo está no vídeo relacionado. Inscreva-se no Antes de Nós para não perder os próximos."),
    (r"#(oracao|oração|fe|fé|jesus|deus|biblia|bíblia|mensageirodefe)\b\s*", ""),
]
PROIBIDO = re.compile(r"ora[çc][ãa]o|orarmos|amém|amem|mensageiro|🙏", re.I)
v = requests.get(f"{API}/videos", headers=H, params={"part": "snippet,localizations", "id": ",".join(ids)}).json()["items"]
for x in v:
    sn = x["snippet"]
    t0, d0 = sn["title"], sn.get("description", "")
    t = t0.replace(" 🙏", "").replace("🙏", "")
    d = d0
    for a, b in TROCAS:
        d = re.sub(a, b, d)
    loc = x.get("localizations", {})
    loc_ruim = any(PROIBIDO.search(l.get("title", "") + l.get("description", "")) for l in loc.values())
    if t == t0 and d == d0 and not loc_ruim:
        print("OK", x["id"], t0)
        continue
    novo = {"title": t, "description": d, "categoryId": sn.get("categoryId", "27"), "tags": sn.get("tags", []),
            "defaultLanguage": sn.get("defaultLanguage", "pt-BR")}
    corpo = {"id": x["id"], "snippet": novo}
    partes = "snippet"
    nova_loc = _traducoes_youtube(t, d, cristao=False)
    if nova_loc:
        corpo["localizations"] = nova_loc
        partes = "snippet,localizations"
    r = requests.put(f"{API}/videos", headers=H, params={"part": partes}, json=corpo)
    print("CORRIGIDO" if r.ok else "ERRO", x["id"], r.status_code, "|", t0, "->", t, "| restou proibido:",
          bool(PROIBIDO.search(t + d)), r.text[:200] if not r.ok else "")
