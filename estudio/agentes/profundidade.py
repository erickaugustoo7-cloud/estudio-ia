"""Efeito 2.5D ("parallax") em imagem parada: estima a profundidade com o Depth Anything V2 Small (Apache 2.0,
roda em CPU) e move a câmera de modo que o primeiro plano se desloca mais que o fundo — parece filmado, não um zoom
chapado. Ideia do Eric a partir do DepthPro2 do ModelScope (24/11). Sem GPU, sem custo.

clipe_2d5(img, destino, seg, W, H, mov) -> Path | None   (None = falhou; quem chama cai no zoom comum)
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np

FPS = 30
MODELO = "depth-anything/Depth-Anything-V2-Small-hf"


@lru_cache(maxsize=1)
def _estimador():
    from transformers import pipeline
    return pipeline("depth-estimation", model=MODELO, device=-1)


def mapa_profundidade(img) -> np.ndarray:
    """0 = longe, 1 = perto, suavizado para não rasgar as bordas."""
    import cv2
    from PIL import Image
    pil = img if isinstance(img, Image.Image) else Image.open(img).convert("RGB")
    d = np.array(_estimador()(pil)["depth"], dtype=np.float32)
    d = cv2.resize(d, pil.size, interpolation=cv2.INTER_CUBIC)
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    d = cv2.GaussianBlur(d, (0, 0), sigmaX=max(3, pil.size[0] / 200))
    return d


def clipe_2d5(img: Path, destino: Path, seg: float, W: int, H: int, mov: int = 0, forca: float = 1.0) -> Path | None:
    import cv2
    try:
        src = cv2.imread(str(img))
        # trabalha um pouco maior que a saída para sobrar margem nas bordas
        M = 1.12
        bw, bh = int(W * M), int(H * M)
        src = cv2.resize(src, (bw, bh), interpolation=cv2.INTER_LANCZOS4)
        prof = mapa_profundidade(Path(img))
        prof = cv2.resize(prof, (bw, bh), interpolation=cv2.INTER_LINEAR)
        n = max(2, int(seg * FPS))
        gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        cx, cy = W / 2, H / 2
        ox, oy = (bw - W) / 2, (bh - H) / 2
        amp = 0.045 * forca  # fração da largura que o primeiro plano anda a mais que o fundo
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                 "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                                 "-preset", "veryfast", "-pix_fmt", "yuv420p", str(destino)], stdin=subprocess.PIPE)
        for f in range(n):
            t = f / (n - 1)
            e = t * t * (3 - 2 * t)  # suaviza começo e fim
            # 4 movimentos que se alternam: aproximar, afastar, deslizar →, deslizar ←
            if mov % 4 == 0:
                z, dx = 0.06 * e, 0.0
            elif mov % 4 == 1:
                z, dx = 0.06 * (1 - e), 0.0
            elif mov % 4 == 2:
                z, dx = 0.03, (e - 0.5)
            else:
                z, dx = 0.03, (0.5 - e)
            # amostragem: a escala e o deslocamento crescem com a proximidade (profundidade)
            px = np.clip(gx + ox, 0, bw - 1).astype(np.int32)
            py = np.clip(gy + oy, 0, bh - 1).astype(np.int32)
            d = prof[py, px]
            escala = 1.0 + z * (0.35 + 0.65 * d)
            mx = (gx - cx) / escala + cx + ox - dx * amp * W * (d - 0.5)
            my = (gy - cy) / escala + cy + oy
            quadro = cv2.remap(src, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REFLECT)
            proc.stdin.write(quadro.tobytes())
        proc.stdin.close()
        proc.wait()
        return destino if proc.returncode == 0 and destino.exists() else None
    except Exception as e:  # noqa: BLE001 — o efeito é um extra: falhou, o vídeo sai com o zoom comum
        print(f"[profundidade] falhou em {img}: {e}", flush=True)
        return None
