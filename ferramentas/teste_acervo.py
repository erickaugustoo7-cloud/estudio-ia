import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from estudio.agentes import acervo  # noqa: E402
Path("acervo_teste").mkdir(exist_ok=True)
for k, q in enumerate(sys.argv[1].split(";")):
    print("==", q, "→", len(acervo.buscar(q)), "candidatas")
    c = acervo.baixar(q, Path(f"acervo_teste/{k:02d}.jpg"))
    print("   ", (c["fonte"] + " | " + c["titulo"][:70] + " | " + c["data"]) if c else "NADA")
