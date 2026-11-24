"""Imagens Z-Image Turbo no Modal (substitui o Kaggle, suspenso em 21/11).
Uso: modal run estudio/modal_imagens.py --entrada itens.json --saida pasta/
itens.json = lista de {"nome", "prompt", "resolucao": "1344x768", "seed", "passos"} (mesmo formato do Kaggle).
Custo: GPU L4 cobrada por segundo, dentro do crédito gratuito do Modal; pesos ficam num Volume (baixa uma vez só)."""
import json
import time
from pathlib import Path

import modal

app = modal.App("estudio-imagens")
pesos = modal.Volume.from_name("estudio-hf-cache", create_if_missing=True)
imagem = (modal.Image.debian_slim(python_version="3.11")
          .pip_install("torch==2.5.1", "transformers>=4.51", "accelerate", "sentencepiece", "safetensors", "pillow",
                       "git+https://github.com/huggingface/diffusers")
          .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "0"}))


@app.cls(image=imagem, gpu="L4", volumes={"/cache": pesos}, timeout=60 * 30, scaledown_window=60, max_containers=1)
class ZImage:
    @modal.enter()
    def carregar(self):
        import torch
        from diffusers import ZImagePipeline
        t = time.time()
        self.pipe = ZImagePipeline.from_pretrained("Tongyi-MAI/Z-Image-Turbo", torch_dtype=torch.bfloat16)
        self.pipe.enable_model_cpu_offload()
        pesos.commit()
        print(f"modelo pronto em {time.time() - t:.0f}s", flush=True)

    @modal.method()
    def gerar(self, item: dict) -> tuple[str, bytes, float]:
        import io
        import torch
        t = time.time()
        w, h = (int(x) for x in item.get("resolucao", "768x1344").split("x"))
        img = self.pipe(prompt=item["prompt"], width=w, height=h, num_inference_steps=item.get("passos", 9),
                        guidance_scale=0.0, generator=torch.Generator("cuda").manual_seed(int(item.get("seed", 42)))).images[0]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return item.get("nome", "img"), buf.getvalue(), time.time() - t


@app.local_entrypoint()
def main(entrada: str, saida: str):
    itens = json.loads(Path(entrada).read_text())
    out = Path(saida)
    out.mkdir(parents=True, exist_ok=True)
    t0, rel = time.time(), {}
    for i, res in enumerate(ZImage().gerar.map(itens, return_exceptions=True)):
        if isinstance(res, Exception):
            print(f"item {i}: erro {res}", flush=True)
            rel[i] = {"ok": False, "erro": str(res)[:300]}
            continue
        nome, dados, seg = res
        (out / f"{nome}.png").write_bytes(dados)
        rel[i] = {"ok": True, "segundos": round(seg)}
        print(f"item {i} ok {seg:.0f}s", flush=True)
    (out / "relatorio.json").write_text(json.dumps({"total_s": round(time.time() - t0), "cenas": rel}))
    print("FIM", sum(v["ok"] for v in rel.values()), "/", len(itens), flush=True)
