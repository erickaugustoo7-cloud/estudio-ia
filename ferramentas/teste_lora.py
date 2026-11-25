"""Testa os estilos (LoRA) treinados no Civision pela API do ModelScope e imprime as imagens em base64 no log."""
import base64, io, os, sys, time
import requests
from PIL import Image

TOK = os.environ["MODELSCOPE_TOKEN"]; BASE = "https://api-inference.modelscope.ai"
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}
TESTES = [
    ("msg_base", "Tongyi-MAI/Z-Image", "EricIA/mensageiro-estilo", 30,
     "mensageiro_fe, a small oil lamp on a wooden table beside an open old book at night, warm light, ancient Judea"),
    ("msg_turbo", "Tongyi-MAI/Z-Image-Turbo", "EricIA/mensageiro-estilo", 9,
     "mensageiro_fe, a shepherd far away on a hill with sheep at golden sunrise, ancient Israel"),
    ("adn_base", "Tongyi-MAI/Z-Image", "EricIA/antes-de-nos-estilo", 30,
     "antesdenos_doc, a herd of woolly mammoths walking across a frozen steppe at dawn, mist, documentary photo"),
]
for nome, modelo, lora, passos, prompt in TESTES:
    corpo = {"model": modelo, "prompt": prompt, "size": "1344x768", "seed": 7, "steps": passos, "loras": lora}
    r = requests.post(f"{BASE}/v1/images/generations", headers={**H, "X-ModelScope-Async-Mode": "true"}, json=corpo, timeout=60)
    print(nome, "POST", r.status_code, r.text[:300], flush=True)
    if r.status_code != 200:
        continue
    tid = r.json().get("task_id")
    for _ in range(90):
        time.sleep(5)
        st = requests.get(f"{BASE}/v1/tasks/{tid}", headers={**H, "X-ModelScope-Task-Type": "image_generation"}, timeout=30).json()
        if st.get("task_status") in ("SUCCEED", "FAILED"):
            break
    print(nome, "STATUS", st.get("task_status"), str(st)[:300], flush=True)
    if st.get("task_status") == "SUCCEED":
        im = Image.open(io.BytesIO(requests.get(st["output_images"][0], timeout=60).content)).convert("RGB")
        im.thumbnail((960, 960)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
        d = base64.b64encode(buf.getvalue()).decode()
        for k in range(0, len(d), 60000):
            print(f"IMG {nome} {d[k:k+60000]}")
