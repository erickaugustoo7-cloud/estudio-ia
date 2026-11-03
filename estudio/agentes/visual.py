"""Diretor de arte: busca/gera uma imagem por cena, com várias fontes gratuitas em cascata.

- nasa: NASA Image Library (domínio público, sem chave)
- pollinations: imagem gerada por IA (FLUX). Com POLLINATIONS_API_KEY os limites são bem maiores.
- commons: Wikimedia Commons — pinturas e fotos em domínio público (sem chave)
- fundo: último recurso, gerado localmente com FFmpeg (o vídeo nunca para por falta de imagem)
"""
import os
import random
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path

import requests

from estudio.base import log

UA = {"User-Agent": "estudio-ia/1.0 (https://github.com/erickaugustoo7-cloud/estudio-ia)"}

ORDEM = {
    "nasa": ["nasa", "pollinations", "commons"],
    "pollinations": ["pollinations", "commons"],
    # bíblico: busca por palavra-chave no Commons trazia imagens fora do tema — melhor repetir a anterior
    "pollinations_estrito": ["pollinations"],
    "commons": ["commons", "pollinations"],
}


def _baixar(url: str, destino: Path, headers=None, timeout=120) -> tuple[bool, str]:
    try:
        r = requests.get(url, headers={**UA, **(headers or {})}, timeout=timeout)
        if r.ok and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20_000:
            destino.write_bytes(r.content)
            return True, "ok"
        return False, f"HTTP {r.status_code} {r.headers.get('content-type', '')} {len(r.content)}B"
    except requests.RequestException as e:
        return False, type(e).__name__


def _nasa(cena: dict, destino: Path, usados: set, **_) -> bool:
    busca = cena.get("busca_imagem") or cena.get("busca_nasa")
    if not busca:
        return False
    try:
        r = requests.get("https://images-api.nasa.gov/search",
                         params={"q": busca, "media_type": "image"}, headers=UA, timeout=30)
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
            if url and _baixar(url.replace("http://", "https://"), destino)[0]:
                usados.add(nasa_id)
                return True
    return False


def _pollinations(cena: dict, destino: Path, usados: set, canal: dict, seed: int) -> bool:
    prompt = f"{cena['prompt_imagem']}. {canal.get('regra_visual_pessoas', '')}. {canal['estilo_visual'].strip()}"
    q = urllib.parse.quote(prompt[:900])
    chave = os.getenv("POLLINATIONS_API_KEY")
    params = f"width=1080&height=1920&seed={seed}&nologo=true&model=flux"
    tentativas = []
    if chave and not _SEM_SALDO:
        tentativas.append((f"https://gen.pollinations.ai/image/{q}?{params}", {"Authorization": f"Bearer {chave}"}, (0,)))
    # anônimo: limite de ~1 imagem por intervalo, então espera com paciência em vez de desistir
    tentativas.append((f"https://image.pollinations.ai/prompt/{q}?{params}", {}, (0, 20, 40, 60)))
    for url, headers, esperas in tentativas:
        for espera in esperas:
            time.sleep(espera)
            ok, motivo = _baixar(url, destino, headers, timeout=150)
            if ok:
                return True
            log("visual", f"pollinations: {motivo}")
            if headers and motivo.startswith("HTTP 402"):
                _SEM_SALDO.append(True)  # chave sem saldo: não insiste nela nas próximas cenas
                log("visual", "chave Pollinations sem saldo (402) — usando o acesso anônimo")
                break
    return False


_SEM_SALDO: list = []


def _commons(cena: dict, destino: Path, usados: set, **_) -> bool:
    busca = cena.get("busca_imagem") or cena.get("busca_nasa") or cena.get("prompt_imagem", "")[:80]
    for termo in (f"{busca} painting", busca):
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params={
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"{termo} filetype:bitmap", "gsrlimit": 15,
                "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1600,
            })
            paginas = list(r.json().get("query", {}).get("pages", {}).values())
        except Exception as e:  # noqa: BLE001
            log("visual", f"Commons indisponível: {e}")
            return False
        paginas.sort(key=lambda p: p.get("index", 99))
        for p in paginas:
            info = (p.get("imageinfo") or [{}])[0]
            licenca = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "").lower()
            if p["title"] in usados or "public domain" not in licenca and "pd" not in licenca and "cc0" not in licenca:
                continue  # só domínio público: dispensa atribuição no vídeo
            if info.get("width", 0) < 800:
                continue
            if _baixar(info.get("thumburl") or info["url"], destino)[0]:
                usados.add(p["title"])
                return True
    return False


def _fundo(destino: Path, i: int) -> None:
    """Fundo escuro com degradê suave, gerado localmente — nunca falha."""
    cores = ["0x1a1208", "0x0b1026", "0x140a1f", "0x061a1a"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"gradients=s=1080x1920:c0={cores[i % 4]}:c1=0x000000:x0=540:y0=300:x1=540:y1=1900:d=1",
                    "-frames:v", "1", str(destino)], check=True)


FONTES = {"nasa": _nasa, "pollinations": _pollinations, "commons": _commons}


RESERVAS: list = []  # cenas que não vieram da fonte principal (aparecem na Issue)


def gerar_imagens(canal: dict, cenas: list[dict], pasta: Path) -> list[Path]:
    RESERVAS.clear()
    usados, imagens, anterior = set(), [], None
    seed_base = random.randint(1, 10**6)
    ordem = ORDEM.get(canal["fonte_visual"], ["pollinations", "commons"])
    for i, cena in enumerate(cenas):
        destino = pasta / f"cena_{i:02d}.jpg"
        fonte_usada = None
        fixa = cena.get("imagem")  # imagem escolhida a dedo (ex.: a abertura com a Bíblia)
        if fixa and Path(fixa).is_file():
            shutil.copy(fixa, destino)
            fonte_usada = "fixa"
        for nome in ([] if fonte_usada else ordem):
            if FONTES[nome](cena=cena, destino=destino, usados=usados, canal=canal, seed=seed_base + i):
                fonte_usada = nome
                break
        if fonte_usada not in (ordem[0], "fixa"):
            RESERVAS.append(i + 1)
        if not fonte_usada and anterior:
            shutil.copy(anterior, destino)
            fonte_usada = "repetida"
        if not fonte_usada:
            _fundo(destino, i)
            fonte_usada = "fundo"
        log("visual", f"cena {i + 1}/{len(cenas)} pronta ({fonte_usada})")
        imagens.append(destino)
        anterior = destino
    return imagens
