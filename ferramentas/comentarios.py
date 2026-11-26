"""Lista comentários sem resposta do canal e (opcionalmente) responde.
LISTAR: TOKEN_NOME=YT_REFRESH_TOKEN_CURIOSO python ferramentas/comentarios.py
RESPONDER: + RESPONDER_ID=<id do comentário> RESPOSTA="texto"."""
import os
import requests

tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
    "refresh_token": os.environ["YT_TOKEN"], "grant_type": "refresh_token"}).json()
print("escopos:", tok.get("scope"))
H = {"Authorization": f"Bearer {tok['access_token']}"}
API = "https://www.googleapis.com/youtube/v3"
if os.getenv("RESPONDER_ID"):
    r = requests.post(f"{API}/comments?part=snippet", headers=H, timeout=30,
                      json={"snippet": {"parentId": os.environ["RESPONDER_ID"], "textOriginal": os.environ["RESPOSTA"]}})
    print("resposta:", r.status_code, r.text[:400])
else:
    canal = requests.get(f"{API}/channels?part=id&mine=true", headers=H, timeout=30).json()["items"][0]["id"]
    r = requests.get(f"{API}/commentThreads?part=snippet,replies&allThreadsRelatedToChannelId={canal}&maxResults=50&order=time",
                     headers=H, timeout=30)
    print("listar:", r.status_code)
    for t in r.json().get("items", []):
        s = t["snippet"]; c = s["topLevelComment"]["snippet"]
        print(f"COMENTARIO {s['topLevelComment']['id']} | video {s.get('videoId')} | respostas {s.get('totalReplyCount')} | "
              f"{c['publishedAt'][:16]} | {c['authorDisplayName']}: {c['textOriginal'][:300]!r}")
    if r.status_code != 200:
        print(r.text[:400])
