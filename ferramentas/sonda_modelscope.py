"""Sonda das capacidades da API do ModelScope (tradução, visão, edição de imagem)."""
import base64, json, os, time
import requests
B = "https://api-inference.modelscope.ai"
H = {"Authorization": f"Bearer {os.environ['MODELSCOPE_TOKEN']}", "Content-Type": "application/json"}

def chat(modelo, msgs, **kw):
    t = time.time()
    r = requests.post(f"{B}/v1/chat/completions", headers=H, json={"model": modelo, "messages": msgs, **kw}, timeout=120)
    try:
        txt = r.json()["choices"][0]["message"]["content"]
    except Exception:
        txt = r.text[:300]
    print(f"CHAT {modelo} {r.status_code} {time.time()-t:.1f}s :: {str(txt)[:400]!r}", flush=True)

def imagem(corpo):
    r = requests.post(f"{B}/v1/images/generations", headers={**H, "X-ModelScope-Async-Mode": "true"}, json=corpo, timeout=60)
    if r.status_code >= 400:
        print("IMG ERRO", corpo.get("model"), r.status_code, r.text[:300]); return None
    tid = r.json()["task_id"]
    for _ in range(60):
        time.sleep(4)
        st = requests.get(f"{B}/v1/tasks/{tid}", headers={**H, "X-ModelScope-Task-Type": "image_generation"}, timeout=30).json()
        if st.get("task_status") in ("SUCCEED", "FAILED"):
            print("IMG", corpo.get("model"), st.get("task_status"), str(st)[:300]); return st.get("output_images", [None])[0]
    print("IMG timeout"); return None

desc = "Os egípcios molhavam a areia para arrastar blocos de 2 toneladas. 🔔 Inscreva-se no Antes de Nós."
for m in ("Qwen/Qwen3.5-122B-A10B", "Qwen/Qwen3.8-27B", "deepseek-ai/DeepSeek-V4.1-Flash"):
    chat(m, [{"role": "user", "content": "Traduza para espanhol latino e inglês. Responda só JSON {\"es\":...,\"en\":...}:\n" + desc}])

url = imagem({"model": "Tongyi-MAI/Z-Image-Turbo", "prompt": "cinematic photo of ancient Egyptian desert at dawn with a modern red plastic chair in the foreground and pyramids behind", "size": "1344x768", "steps": 9})
print("URL", url)
if url:
    b64 = base64.b64encode(requests.get(url, timeout=60).content).decode()
    for m in ("Qwen-Ambassador/Qwen3.8-Omni-Flash", "OpenGVLab/InternVL3_5-241B-A28B", "PaddlePaddle/ERNIE-4.5-VL-28B-A3B-PT"):
        for u in (url, f"data:image/jpeg;base64,{b64}"):
            chat(m, [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": u}},
                     {"type": "text", "text": "Há algum objeto moderno nesta cena do Egito antigo? Responda JSON {ok:bool, motivo:str}."}]}])
    for m in ("Qwen/Qwen-Image-Edit", "MusePublic/Qwen-Image-Edit"):
        for campo in ("image_url", "image"):
            out = imagem({"model": m, "prompt": "remove the red plastic chair, replace it with sand", campo: [url]})
            print("EDIT", m, campo, out)
            if out:
                break
