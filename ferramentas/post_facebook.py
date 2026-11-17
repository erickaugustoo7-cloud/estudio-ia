"""Publica um post de texto (com links) na Página do Facebook do canal. Uso: python ferramentas/post_facebook.py arquivo.txt"""
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes.publicador import FB_API, meta_contas  # noqa: E402

token = os.environ["META_TOKEN"]
page_id, _ = meta_contas(token)
texto = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
r = requests.post(f"{FB_API}/{page_id}/feed", data={"message": texto, "access_token": token}, timeout=60)
print("status", r.status_code, r.text[:400])
r.raise_for_status()
print("POST_ID", r.json().get("id"), f"https://www.facebook.com/{r.json().get('id')}")
