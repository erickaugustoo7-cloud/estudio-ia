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
    rr = requests.get("https://collectionapi.metmuseum.org/public/collection/v1/search",
                      params={"q": q, "hasImages": "true"}, headers=UA, timeout=30)
    if not rr.ok:
        raise RuntimeError(f"HTTP {rr.status_code}")
    r = rr.json()
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


def _wikimedia(q: str, n: int = 12) -> list[dict]:
    """Wikimedia Commons: só domínio público, CC0 e CC BY / CC BY-SA (com crédito). Nada de NC (não comercial) ou ND."""
    import re
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} filetype:bitmap",
        "gsrlimit": n * 2, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1920}).json()
    out = []
    for pg in (r.get("query") or {}).get("pages", {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        lic = (md.get("LicenseShortName") or {}).get("value", "")
        ok = lic.lower() in ("public domain", "cc0", "pd") or (lic.upper().startswith("CC BY") and
                                                              "NC" not in lic.upper() and "ND" not in lic.upper())
        if not ok or ii.get("width", 0) < 1000:
            continue
        autor = re.sub("<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:60] or "autor desconhecido"
        out.append({"url": ii.get("thumburl") or ii["url"], "titulo": pg.get("title", "").replace("File:", "").rsplit(".", 1)[0],
                    "data": "", "cultura": re.sub("<[^>]+>", "", (md.get("ImageDescription") or {}).get("value", ""))[:200],
                    "fonte": f"Wikimedia Commons — {autor} ({lic})", "pagina": ii.get("descriptionurl", "")})
    return out[:n]


# nu artístico é permitido no YouTube, mas pode limitar anúncios: fica de fora
_EVITAR = ("nude", "naked", "venus", "aphrodite", "bather", "life study", "eros", "erotic", "nymph", "satyr", "leda",
           "crucifixion", "skull", "mummy", "corpse", "execution", "battle scene", "athlete", "torso", "kouros",
           "youth", "warrior figure", "male figure", "female figure", "bather", "portrait", "engraving of", "self-portrait")


def _relevancia(c: dict, q: str) -> float:
    texto = f"{c['titulo']} {c['cultura']}".lower()
    pal = [w for w in q.lower().split() if len(w) > 2]
    return sum(w.rstrip("s") in texto for w in pal) / max(len(pal), 1)


def buscar(q: str, n: int = 12) -> list[dict]:
    """Junta os três acervos, sem repetir imagens já usadas no vídeo; as mais relevantes (palavras da busca no
    título/cultura) primeiro."""
    res = []
    for f in (_met, _aic, _cleveland, _wikimedia):
        try:
            achou = f(q, n)
            print(f"acervo: {f.__name__} '{q}' → {len(achou)}")
            res += achou
        except Exception as e:  # noqa: BLE001
            print(f"acervo: {f.__name__} falhou para '{q}': {e}")
    res = [x for x in res if x["url"] not in _USADOS
           and not any(e in f"{x['titulo']} {x['cultura']}".lower() for e in _EVITAR)]
    for x in res:
        x["rel"] = _relevancia(x, q)
    return sorted(res, key=lambda x: -x["rel"])


def baixar(q: str, destino: Path, min_lado: int = 900) -> dict | None:
    """Baixa a melhor imagem de museu para a busca (grande o bastante para vídeo 1080p). Devolve o crédito."""
    from PIL import Image
    cands = buscar(q)
    n_pal = len([w for w in q.split() if len(w) > 2])
    minimo = 0.99 if n_pal <= 2 else 0.6  # "copper axe" precisa ter "copper" E "axe" no título
    melhores = [c for c in cands if c["rel"] >= minimo]  # sem nada relevante: o roteiro cai para Pixabay/IA
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


def compor(img: Path, destino: Path, W: int, H: int) -> Path:
    """Peça de museu (às vezes em pé, fundo branco) dentro do quadro do vídeo sem distorcer: fundo com a própria
    imagem desfocada e escurecida, peça inteira no centro com uma sombra leve."""
    from PIL import Image, ImageFilter, ImageEnhance
    im = Image.open(img).convert("RGB")
    fundo = im.copy()
    esc = max(W / fundo.width, H / fundo.height)
    fundo = fundo.resize((int(fundo.width * esc) + 1, int(fundo.height * esc) + 1))
    fundo = fundo.crop(((fundo.width - W) // 2, (fundo.height - H) // 2, (fundo.width - W) // 2 + W, (fundo.height - H) // 2 + H))
    fundo = ImageEnhance.Brightness(fundo.filter(ImageFilter.GaussianBlur(40))).enhance(0.45)
    esc = min(W * 0.92 / im.width, H * 0.92 / im.height)
    peca = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
    x, y = (W - peca.width) // 2, (H - peca.height) // 2
    sombra = Image.new("L", (W, H), 0)
    sombra.paste(255, (x + 10, y + 14, x + peca.width + 10, y + peca.height + 14))
    fundo = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), fundo, sombra.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6)))
    fundo.paste(peca, (x, y))
    fundo.save(destino, quality=93)
    return destino
