"""Imagens de época LIBERADAS para uso comercial, direto dos acervos abertos de museus (CC0 / domínio público).
Sem chave: The Met, Art Institute of Chicago, Cleveland Museum of Art. Cada imagem volta com o crédito para a descrição.
Nunca usa Google Imagens nem acervos "só não comercial" (ex.: British Museum)."""
from __future__ import annotations

import random
from pathlib import Path

import requests

UA = {"User-Agent": "estudio-ia/1.0 (documentarios educativos; contato via GitHub)"}
_USADOS: set[str] = set()


def _met(q: str, n: int = 12) -> list[dict]:
    r = requests.get("https://collectionapi.metmuseum.org/public/collection/v1/search",
                     params={"q": q, "hasImages": "true"}, headers=UA, timeout=30).json()
    out = []
    for oid in (r.get("objectIDs") or [])[:n * 3]:
        try:
            o = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}",
                             headers=UA, timeout=30).json()
        except Exception:  # noqa: BLE001
            continue
        if o.get("isPublicDomain") and o.get("primaryImage"):
            out.append({"url": o["primaryImage"], "titulo": o.get("title", ""), "data": o.get("objectDate", ""),
                        "cultura": o.get("culture", ""), "fonte": "The Metropolitan Museum of Art (CC0)",
                        "pagina": o.get("objectURL", "")})
        if len(out) >= n:
            break
    return out


def _aic(q: str, n: int = 12) -> list[dict]:
    r = requests.get("https://api.artic.edu/api/v1/artworks/search", headers=UA, timeout=30, params={
        "q": q, "limit": n * 2, "query[term][is_public_domain]": "true",
        "fields": "id,title,image_id,date_display,place_of_origin,is_public_domain"}).json()
    iiif = (r.get("config") or {}).get("iiif_url", "https://www.artic.edu/iiif/2")
    return [{"url": f"{iiif}/{a['image_id']}/full/1686,/0/default.jpg", "url_menor": f"{iiif}/{a['image_id']}/full/843,/0/default.jpg",
             "titulo": a.get("title", ""), "data": a.get("date_display", ""), "cultura": a.get("place_of_origin", ""),
             "fonte": "Art Institute of Chicago (CC0)", "pagina": f"https://www.artic.edu/artworks/{a['id']}"}
            for a in r.get("data", []) if a.get("image_id") and a.get("is_public_domain")][:n]


def _cleveland(q: str, n: int = 12) -> list[dict]:
    r = requests.get("https://openaccess-api.clevelandart.org/api/artworks/", headers=UA, timeout=30,
                     params={"q": q, "has_image": 1, "cc0": 1, "limit": n}).json()
    out = []
    for a in r.get("data", []):
        img = ((a.get("images") or {}).get("print") or (a.get("images") or {}).get("web") or {}).get("url")
        if img and a.get("share_license_status") == "CC0":
            out.append({"url": img, "titulo": a.get("title", ""), "data": a.get("creation_date", ""),
                        "cultura": ", ".join(a.get("culture") or []), "fonte": "Cleveland Museum of Art (CC0)",
                        "pagina": a.get("url", "")})
    return out


def _relevancia(c: dict, q: str) -> float:
    texto = f"{c['titulo']} {c['cultura']}".lower()
    pal = [w for w in q.lower().split() if len(w) > 2]
    return sum(w.rstrip("s") in texto for w in pal) / max(len(pal), 1)


def buscar(q: str, n: int = 12) -> list[dict]:
    """Junta os três acervos, sem repetir imagens já usadas no vídeo; as mais relevantes (palavras da busca no
    título/cultura) primeiro."""
    res = []
    for f in (_met, _aic, _cleveland):
        try:
            achou = f(q, n)
            print(f"acervo: {f.__name__} '{q}' → {len(achou)}")
            res += achou
        except Exception as e:  # noqa: BLE001
            print(f"acervo: {f.__name__} falhou para '{q}': {e}")
    res = [x for x in res if x["url"] not in _USADOS]
    for x in res:
        x["rel"] = _relevancia(x, q)
    return sorted(res, key=lambda x: -x["rel"])


def baixar(q: str, destino: Path, min_lado: int = 900) -> dict | None:
    """Baixa a melhor imagem de museu para a busca (grande o bastante para vídeo 1080p). Devolve o crédito."""
    from PIL import Image
    cands = buscar(q)
    melhores = [c for c in cands if c["rel"] >= 0.5] or cands
    random.shuffle(melhores[:6])
    for c in melhores[:10]:
        for url in (c["url"], c.get("url_menor")):
            if not url:
                continue
            try:
                r = requests.get(url, headers=UA, timeout=60)
                if not r.ok or len(r.content) < 30000:
                    print(f"acervo: download {r.status_code} {len(r.content)}B {url[:80]}")
                    continue
                destino.write_bytes(r.content)
                with Image.open(destino) as im:
                    if min(im.size) < min_lado * 0.6 or max(im.size) < min_lado:
                        continue
                    im.convert("RGB").save(destino, quality=92)
                _USADOS.add(c["url"])
                return c
            except Exception:  # noqa: BLE001
                continue
    return None
