"""Publicador 100% gratuito.

- Instagram: publicação automática de Reels pela API oficial (Instagram API com login do Instagram).
  O vídeo sobe direto do GitHub Actions para a Meta (upload resumável) — não precisa hospedar em lugar nenhum.
- TikTok: o vídeo + legenda chegam no seu Telegram, prontos para salvar e postar no app (≈30 s).
"""
import os
import time
from pathlib import Path

import requests

from estudio.base import log

IG_API = "https://graph.instagram.com/" + os.getenv("IG_API_VERSION", "v26.0")


# ---------------- Telegram ----------------
def telegram_ativo() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def telegram_mensagem(texto: str) -> None:
    if not telegram_ativo():
        return
    requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": texto, "disable_web_page_preview": True},
        timeout=30,
    )


def telegram_video(video: Path, legenda_curta: str, texto_post: str) -> bool:
    """Envia o MP4 (toca direto no celular) e, em seguida, a legenda pronta para copiar."""
    if not telegram_ativo():
        log("publicador", "Telegram não configurado — pulando envio")
        return False
    tam_mb = video.stat().st_size / 1e6
    if tam_mb > 49:  # limite da Bot API é 50 MB
        log("publicador", f"vídeo com {tam_mb:.0f} MB — acima do limite do Telegram")
        telegram_mensagem(f"{legenda_curta}\n⚠️ Vídeo com {tam_mb:.0f} MB, baixe pelo GitHub.")
        return False
    with open(video, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendVideo",
            data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "caption": legenda_curta[:1000],
                  "supports_streaming": "true", "width": 1080, "height": 1920},
            files={"video": (video.name, f, "video/mp4")},
            timeout=300,
        )
    if not r.ok:
        log("publicador", f"Telegram falhou: {r.text[:200]}")
        return False
    telegram_mensagem(texto_post)  # mensagem separada = fácil de copiar no celular
    log("publicador", "vídeo enviado ao Telegram")
    return True


# ---------------- Instagram ----------------
def instagram_reel(token: str, video: Path, legenda: str) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{IG_API}/me", params={"fields": "user_id,username"}, headers=h, timeout=30)
    me.raise_for_status()
    ig_id = me.json()["user_id"]

    # 1) cria o container do Reel em modo de upload resumável
    c = requests.post(f"{IG_API}/{ig_id}/media", headers=h, timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": legenda, "share_to_feed": "true",
    })
    c.raise_for_status()
    cont = c.json()
    cont_id = cont["id"]
    uri = cont.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{IG_API.rsplit('/', 1)[1]}/{cont_id}"

    # 2) envia os bytes do vídeo direto para a Meta
    dados = video.read_bytes()
    up = requests.post(uri, data=dados, timeout=600, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(dados)),
    })
    up.raise_for_status()

    # 3) espera a Meta processar
    for _ in range(40):
        time.sleep(15)
        st = requests.get(f"{IG_API}/{cont_id}", params={"fields": "status_code,status"}, headers=h, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            return {"status": "failed", "errorMessage": st.get("status", st.get("status_code"))}
    else:
        return {"status": "failed", "errorMessage": "Meta não terminou de processar em 10 min"}

    # 4) publica
    pub = requests.post(f"{IG_API}/{ig_id}/media_publish", data={"creation_id": cont_id}, headers=h, timeout=60)
    if not pub.ok:
        return {"status": "failed", "errorMessage": pub.text[:300]}
    media_id = pub.json()["id"]
    link = requests.get(f"{IG_API}/{media_id}", params={"fields": "permalink"}, headers=h, timeout=30).json()
    return {"status": "published", "publicUrl": link.get("permalink", "")}


# ---------------- Meta (chave da Página: publica no Instagram e na Página do Facebook) ----------------
FB_API = "https://graph.facebook.com/v23.0"


def meta_contas(token: str) -> tuple[str, str | None]:
    """Com a chave da Página, descobre o ID da Página e o da conta do Instagram ligada a ela."""
    r = requests.get(f"{FB_API}/me", params={"fields": "id,name,instagram_business_account",
                                               "access_token": token}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d["id"], (d.get("instagram_business_account") or {}).get("id")


def _esperar_container(token, cont_id) -> str | None:
    for _ in range(40):
        time.sleep(15)
        st = requests.get(f"{FB_API}/{cont_id}", params={"fields": "status_code,status", "access_token": token},
                          timeout=30).json()
        if st.get("status_code") == "FINISHED":
            return None
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            return st.get("status") or st.get("status_code")
    return "Meta não terminou de processar em 10 min"


def instagram_reel_meta(token: str, ig_id: str, video: Path, legenda: str) -> dict:
    c = requests.post(f"{FB_API}/{ig_id}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": legenda, "share_to_feed": "true",
        "access_token": token})
    c.raise_for_status()
    cont = c.json()
    dados = video.read_bytes()
    up = requests.post(cont.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v23.0/{cont['id']}",
                       data=dados, timeout=600,
                       headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(dados))})
    up.raise_for_status()
    erro = _esperar_container(token, cont["id"])
    if erro:
        return {"status": "failed", "errorMessage": erro}
    pub = requests.post(f"{FB_API}/{ig_id}/media_publish", data={"creation_id": cont["id"], "access_token": token},
                        timeout=60)
    if not pub.ok:
        return {"status": "failed", "errorMessage": pub.text[:300]}
    link = requests.get(f"{FB_API}/{pub.json()['id']}", params={"fields": "permalink", "access_token": token},
                        timeout=30).json()
    return {"status": "published", "publicUrl": link.get("permalink", "")}


def facebook_reel(token: str, page_id: str, video: Path, descricao: str) -> dict:
    ini = requests.post(f"{FB_API}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": token},
                        timeout=60)
    ini.raise_for_status()
    vid = ini.json()["video_id"]
    dados = video.read_bytes()
    up = requests.post(ini.json().get("upload_url") or f"https://rupload.facebook.com/video-upload/v23.0/{vid}",
                       data=dados, timeout=600,
                       headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(dados))})
    up.raise_for_status()
    fim = requests.post(f"{FB_API}/{page_id}/video_reels", timeout=60, data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": descricao,
        "access_token": token})
    if not fim.ok:
        return {"status": "failed", "errorMessage": fim.text[:300]}
    return {"status": "published", "publicUrl": f"https://www.facebook.com/reel/{vid}"}


def publicar(canal: dict, video: Path, texto: str, pular: set = frozenset()) -> dict:
    meta = os.getenv(canal.get("secret_token_meta", "") or "_")
    if meta:  # chave da Página: Instagram + Facebook com a mesma chave
        resultados = {}
        try:
            page_id, ig_id = meta_contas(meta)
        except requests.HTTPError as e:
            return {"meta": {"status": "failed", "errorMessage": f"chave da Página inválida — {e.response.text[:300]}"}}
        for plat in canal["publicar_em"]:
            if plat in pular:
                continue
            try:
                if plat == "instagram":
                    resultados[plat] = (instagram_reel_meta(meta, ig_id, video, texto) if ig_id else
                                        {"status": "failed", "errorMessage": "Instagram não está ligado à Página"})
                elif plat == "facebook":
                    resultados[plat] = facebook_reel(meta, page_id, video, texto)
            except requests.HTTPError as e:
                resultados[plat] = {"status": "failed", "errorMessage": f"{e} — {e.response.text[:300]}"}
            log("publicador", f"{plat}: {resultados[plat]['status']}")
        return resultados
    return _publicar_ig_antigo(canal, video, texto, pular)


def _publicar_ig_antigo(canal: dict, video: Path, texto: str, pular: set = frozenset()) -> dict:
    resultados = {}
    if "instagram" in canal["publicar_em"] and "instagram" not in pular:
        nome_secret = canal["secret_token_instagram"]
        token = os.getenv(nome_secret)
        if not token:
            resultados["instagram"] = {"status": "pulado", "errorMessage": f"secret {nome_secret} não configurado"}
        else:
            try:
                resultados["instagram"] = instagram_reel(token, video, texto)
            except requests.HTTPError as e:
                resultados["instagram"] = {"status": "failed", "errorMessage": f"{e} — {e.response.text[:300]}"}
        log("publicador", f"instagram: {resultados['instagram']['status']}")
    return resultados
