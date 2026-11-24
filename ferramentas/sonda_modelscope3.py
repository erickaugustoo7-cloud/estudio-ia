import base64, os, requests, time
B = "https://api-inference.modelscope.ai"
H = {"Authorization": f"Bearer {os.environ['MODELSCOPE_TOKEN']}", "Content-Type": "application/json"}
urls = {"antes": "https://modelscope-studios.oss-cn-zhangjiakou.aliyuncs.com/aigc/text-to-image/73d0db97-505b-4a6e-a01c-437dbb5d362b.png",
        "depois": "https://modelscope-studios.oss-cn-zhangjiakou.aliyuncs.com/aigc/text-to-image/2db36ec4-b18f-4a5d-adc2-58b0a5be085f.png"}
from PIL import Image
import io
for k, u in urls.items():
    im = Image.open(io.BytesIO(requests.get(u, timeout=60).content)).convert("RGB"); im.thumbnail((900, 900))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
    b = base64.b64encode(buf.getvalue()).decode()
    for i in range(0, len(b), 60000): print(f"IMG {k} {b[i:i+60000]}")
for m in ("Qwen/Qwen3.5-122B-A10B", "Qwen/Qwen3.5-35B-A3B", "Qwen/Qwen3.5-27B", "Shanghai_AI_Laboratory/Intern-S1-mini"):
    r = requests.post(f"{B}/v1/chat/completions", headers=H, timeout=120, json={"model": m, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": urls["antes"]}},
        {"type": "text", "text": "Há algum objeto moderno nesta cena do Egito antigo? Responda só JSON {\"ok\":bool,\"motivo\":str}."}]}]})
    try: t = r.json()["choices"][0]["message"]["content"]
    except Exception: t = r.text[:200]
    print("VIS", m, r.status_code, repr(t[:300]))
