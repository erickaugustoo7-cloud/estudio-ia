"""Estudo do nicho cristão no YouTube (PT-BR): o que mais acumula visualizações em Shorts e em vídeos longos.

Para cada termo, busca os vídeos mais vistos (order=viewCount, regionCode=BR, relevanceLanguage=pt):
  - Shorts publicados nos últimos 90 dias
  - vídeos longos (> 4 min) publicados nos últimos 365 dias
Depois baixa estatísticas dos vídeos e dos canais. Salva dados/estudo/youtube_<data>.json.
Custo: ~100 unidades de cota por busca (≈ 50 buscas ≈ 5.000 de 10.000/dia).
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://www.googleapis.com/youtube/v3"
TERMOS = ["oração", "oração da noite", "oração da manhã", "oração poderosa", "salmo 91", "versículo do dia",
          "mensagem de Deus para você", "Deus está falando com você", "Jesus", "milagres de Jesus",
          "história bíblica", "bíblia animada", "desenho bíblico", "personagens bíblicos", "Davi e Golias",
          "Daniel na cova dos leões", "pregação", "estudo bíblico", "Apocalipse", "profecia bíblica",
          "louvor", "testemunho"]


def seg(iso):
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return 0 if not m else sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1)))


def busca(chave, termo, dur, dias):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    p = {"key": chave, "part": "id", "type": "video", "q": termo, "regionCode": "BR", "relevanceLanguage": "pt",
         "publishedAfter": desde, "order": "viewCount", "maxResults": 50}
    if dur:
        p["videoDuration"] = dur
    r = requests.get(f"{API}/search", params=p, timeout=30)
    r.raise_for_status()
    return [it["id"]["videoId"] for it in r.json().get("items", [])]


def main():
    chave = os.environ["YOUTUBE_API_KEY"]
    achados = {}  # id -> {termos, recortes}
    for termo in TERMOS:
        for recorte, dur, dias in (("shorts_90d", "short", 90), ("longos_365d", "medium", 365), ("longos_365d", "long", 365)):
            try:
                for vid in busca(chave, termo, dur, dias):
                    a = achados.setdefault(vid, {"termos": set(), "recortes": set()})
                    a["termos"].add(termo)
                    a["recortes"].add(recorte)
            except Exception as e:  # noqa: BLE001
                print("busca falhou", termo, recorte, e)
    ids = list(achados)
    videos, canais = [], set()
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos", timeout=30, params={"key": chave, "part": "snippet,statistics,contentDetails",
                                                                 "id": ",".join(ids[i:i + 50])})
        r.raise_for_status()
        for v in r.json().get("items", []):
            sn, st = v["snippet"], v.get("statistics", {})
            canais.add(sn["channelId"])
            videos.append({"id": v["id"], "titulo": sn["title"], "canal": sn["channelTitle"], "canal_id": sn["channelId"],
                           "publicado": sn["publishedAt"], "idioma": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                           "duracao_s": seg(v["contentDetails"].get("duration")),
                           "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                           "comentarios": int(st.get("commentCount", 0)),
                           "descricao": (sn.get("description") or "")[:200], "tags": sn.get("tags", [])[:12],
                           "termos": sorted(achados[v["id"]]["termos"]), "recortes": sorted(achados[v["id"]]["recortes"])})
    canais_l, cl = [], list(canais)
    for i in range(0, len(cl), 50):
        r = requests.get(f"{API}/channels", timeout=30, params={"key": chave, "part": "snippet,statistics",
                                                                   "id": ",".join(cl[i:i + 50])})
        r.raise_for_status()
        for c in r.json().get("items", []):
            st = c.get("statistics", {})
            canais_l.append({"id": c["id"], "nome": c["snippet"]["title"], "criado": c["snippet"].get("publishedAt"),
                             "pais": c["snippet"].get("country"), "inscritos": int(st.get("subscriberCount", 0)),
                             "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0))})
    out = Path("dados/estudo")
    out.mkdir(parents=True, exist_ok=True)
    arq = out / f"youtube_{datetime.now():%Y-%m-%d}.json"
    arq.write_text(json.dumps({"coletado": datetime.now(timezone.utc).isoformat(), "termos": TERMOS,
                               "videos": videos, "canais": canais_l}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(videos)} vídeos, {len(canais_l)} canais → {arq}")


if __name__ == "__main__":
    main()
