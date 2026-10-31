"""Diretor de arte: busca/gera uma imagem por cena.

- nasa: NASA Image Library (domínio público, sem chave) → fallback IA
- pollinations: imagem gerada por IA (FLUX via Pollinations)
"""
import os
import random
import shutil
import urllib.parse
from pathlib import Path

import requests

from estudio.base import log

UA = {"User-Agent": "estudio-ia/1.0"}


def _baixar(url: str, destino: Path, headers=None, timeout=120) -> bool:
    try:
        r = requests.get(url, headers={**UA, **(headers or {})}, timeout=timeout)
        if r.ok and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20_000:
            destino.write_bytes(r.content)
            return True
    except requests.RequestException as e:
        log("visual", f"falha ao baixar: {e}")
    return False


def _nasa(busca: str, destino: Path, usados: set) -> bool:
    try:
        r = requests.get(
            "https://images-api.nasa.gov/search",
            params={"q": busca, "media_type": "image"}, headers=UA, timeout=30,
        )
        itens = r.json()["collection"]["items"][:15]
    except Exception as e:  # noqa: BLE001
        log("visual", f"NASA indisponível: {e}")
        return False
    random.shuffle(itens)
    for item in itens:
        nasa_id = item["data"][0]["nasa_id"]
        if nasa_id in usados:
            continue
        try:
            arquivos = [i["href"] for i in requests.get(
                f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nasa_id)}", headers=UA, timeout=30
            ).json()["collection"]["items"]]
        except Exception:  # noqa: BLE001
            continue
        for sufixo in ("~large.jpg", "~medium.jpg", "~orig.jpg"):
            url = next((a for a in arquivos if a.endswith(sufixo)), None)
            if url and _baixar(url.replace("http://", "https://"), destino):
                usados.add(nasa_id)
                return True
    return False


def _pollinations(prompt: str, destino: Path, seed: int) -> bool:
    chave = os.getenv("POLLINATIONS_API_KEY")
    q = urllib.parse.quote(prompt)
    params = f"width=1080&height=1920&seed={seed}&nologo=true&model=flux"
    headers = {"Authorization": f"Bearer {chave}"} if chave else {}
    for base in ("https://gen.pollinations.ai/image/", "https://image.pollinations.ai/prompt/"):
        if _baixar(f"{base}{q}?{params}", destino, headers):
            return True
    return False


def gerar_imagens(canal: dict, cenas: list[dict], pasta: Path) -> list[Path]:
    usados, imagens, anterior = set(), [], None
    estilo = canal["estilo_visual"].strip()
    regra = canal.get("regra_visual_pessoas", "")
    seed_base = random.randint(1, 10**6)
    for i, cena in enumerate(cenas):
        destino = pasta / f"cena_{i:02d}.jpg"
        ok = False
        if canal["fonte_visual"] == "nasa" and cena.get("busca_nasa"):
            ok = _nasa(cena["busca_nasa"], destino, usados)
        if not ok:
            ok = _pollinations(f"{cena['prompt_imagem']}. {regra}. {estilo}", destino, seed_base + i)
        if not ok and anterior:
            shutil.copy(anterior, destino)  # último recurso: repete a imagem anterior
            ok = True
        if not ok:
            raise RuntimeError(f"Sem imagem para a cena {i}")
        log("visual", f"cena {i + 1}/{len(cenas)} pronta")
        imagens.append(destino)
        anterior = destino
    return imagens
