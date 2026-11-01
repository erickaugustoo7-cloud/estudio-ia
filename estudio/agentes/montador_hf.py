"""Editor com HyperFrames (HTML + GSAP → MP4, open source da HeyGen, Apache 2.0).

Gera uma composição HTML por vídeo e renderiza no Chrome headless. Comparado ao FFmpeg puro,
entrega transições suaves, gancho animado na abertura, legenda "pop" palavra a palavra e
barra de progresso — o visual dos canais grandes de curiosidades.
Se a renderização falhar, o orquestrador cai automaticamente para o montador FFmpeg.
"""
import html
import os
import shutil
import subprocess
from pathlib import Path

from estudio.base import RAIZ, log
from estudio.agentes.montador import _musica, blocos_legenda

VERSAO_HF = "0.8.223"  # fixada: o mesmo roteiro sempre renderiza igual

TEMAS = {
    "biblico": {"destaque": "#FFD27A", "fundo": "#140d05", "fonte_titulo": "'DejaVu Serif', Georgia, serif"},
    "espaco": {"destaque": "#5CE1FF", "fundo": "#02040d", "fonte_titulo": "'Montserrat', 'DejaVu Sans', sans-serif"},
}


def _f(x: float) -> str:
    return f"{x:.3f}"


def _composicao(canal, titulo, imagens, tempos, palavras, dur, tem_musica) -> str:
    tema = {**TEMAS.get(canal["slug"], TEMAS["espaco"]), **canal.get("tema", {})}
    fim = dur + 0.4
    elems, anim = [], []

    # ---- cenas: crossfade de 0,5 s + zoom lento alternando direção ----
    inicio = 0.0
    for i, (img, d) in enumerate(zip(imagens, tempos)):
        ultima = i == len(imagens) - 1
        dur_cena = (fim - inicio) if ultima else d + 0.5
        elems.append(
            f'<img id="c{i}" class="clip cena" src="{img.name}" data-start="{_f(inicio)}" '
            f'data-duration="{_f(dur_cena)}" data-track-index="0" style="z-index:{i + 1}" />'
        )
        direcao = 3 if i % 2 == 0 else -3
        if i == 0:  # abertura com movimento imediato: zoom de impacto e depois o zoom lento
            anim.append('tl.fromTo("#c0",{scale:1.35,xPercent:0},{scale:1.06,duration:1.1,ease:"power3.out"},0);')
            anim.append(f'tl.to("#c0",{{scale:1.18,xPercent:{direcao},duration:{_f(max(0.5, dur_cena - 1.1))},'
                        f'ease:"none"}},1.1);')
        else:
            anim.append(f'tl.fromTo("#c{i}",{{scale:1.0,xPercent:0}},{{scale:1.16,xPercent:{direcao},'
                        f'duration:{_f(dur_cena)},ease:"none"}},{_f(inicio)});')
        if i > 0:
            anim.append(f'tl.fromTo("#c{i}",{{opacity:0}},{{opacity:1,duration:0.5,ease:"power1.inOut"}},{_f(inicio)});')
        inicio += d

    # ---- gancho animado na abertura ----
    # visível já no quadro 0 (é o que aparece na prévia do feed); pulsa uma vez e sai aos ~3 s
    elems.append(f'<div id="gancho" class="clip" data-start="0" data-duration="3.2" data-track-index="2">'
                 f'<span>{html.escape(titulo.upper())}</span></div>')
    anim.append('tl.set("#gancho span",{opacity:1,scale:1},0);')
    anim.append('tl.to("#gancho span",{scale:1.08,duration:0.18,ease:"power2.out",yoyo:true,repeat:1},0.25);')
    anim.append('tl.to("#gancho span",{opacity:0,y:-30,duration:0.3,ease:"power2.in"},2.85);')

    # ---- legenda palavra a palavra ----
    blocos = blocos_legenda(palavras)
    for b, bloco in enumerate(blocos):
        ini = bloco[0]["ini"]
        prox_bloco = blocos[b + 1][0]["ini"] if b + 1 < len(blocos) else fim
        fim_bloco = min(bloco[-1]["fim"] + 0.15, prox_bloco)  # nunca sobrepõe o bloco seguinte
        spans = " ".join(f'<span id="w{b}_{j}">{html.escape(p["texto"].upper())}</span>' for j, p in enumerate(bloco))
        elems.append(f'<div id="b{b}" class="clip legenda" data-start="{_f(ini)}" '
                     f'data-duration="{_f(max(0.2, fim_bloco - ini))}" data-track-index="3">{spans}</div>')
        anim.append(f'tl.fromTo("#b{b}",{{opacity:0,y:24,scale:0.92}},{{opacity:1,y:0,scale:1,duration:0.12,ease:"power2.out"}},{_f(ini)});')
        for j, p in enumerate(bloco):
            prox = bloco[j + 1]["ini"] if j + 1 < len(bloco) else fim_bloco
            anim.append(f'tl.set("#w{b}_{j}",{{color:"{tema["destaque"]}",scale:1.12}},{_f(p["ini"])});')
            anim.append(f'tl.set("#w{b}_{j}",{{color:"#ffffff",scale:1}},{_f(prox)});')

    # ---- barra de progresso + assinatura ----
    elems.append(f'<div id="barra" class="clip" data-start="0" data-duration="{_f(fim)}" data-track-index="4"></div>')
    anim.append(f'tl.fromTo("#barra",{{scaleX:0}},{{scaleX:1,duration:{_f(fim)},ease:"none"}},0);')
    elems.append(f'<div id="assinatura" class="clip" data-start="0" data-duration="{_f(fim)}" data-track-index="4">'
                 f'{html.escape(canal["nome"])}</div>')

    # ---- áudio ----
    elems.append(f'<audio src="narracao.mp3" data-start="0" data-duration="{_f(dur)}" data-volume="1" data-track-index="5"></audio>')
    if tem_musica:
        elems.append(f'<audio src="musica.mp3" data-start="0" data-duration="{_f(fim)}" data-volume="0.08" '
                     f'data-fade-in="1" data-fade-out="2" data-track-index="6"></audio>')

    fonte = ""
    if (RAIZ / "assets/fontes/Montserrat.ttf").exists():
        fonte = "@font-face{font-family:'Montserrat';src:url('Montserrat.ttf');font-weight:100 900;}"

    return f"""<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="gsap.min.js"></script>
<style>
{fonte}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:{tema['fundo']}}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:'Montserrat','DejaVu Sans',sans-serif}}
.cena{{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover;transform-origin:50% 50%}}
#veu{{position:absolute;inset:0;z-index:50;pointer-events:none;
  background:linear-gradient(180deg,rgba(0,0,0,.45) 0%,rgba(0,0,0,0) 22%,rgba(0,0,0,0) 52%,rgba(0,0,0,.7) 100%)}}
#gancho{{position:absolute;left:60px;right:60px;top:260px;z-index:60;text-align:center}}
#gancho span{{display:inline-block;font-family:{tema['fonte_titulo']};font-weight:900;font-size:84px;line-height:1.12;
  color:#111;background:{tema['destaque']};padding:22px 34px;border-radius:22px;
  box-shadow:0 14px 40px rgba(0,0,0,.6);letter-spacing:-0.01em;transform-origin:50% 50%}}
.legenda{{position:absolute;left:50px;right:50px;top:1240px;z-index:70;text-align:center;
  font-weight:900;font-size:84px;line-height:1.15;color:#fff;
  -webkit-text-stroke:3px rgba(0,0,0,.9);paint-order:stroke fill;text-shadow:0 8px 22px rgba(0,0,0,.8)}}
.legenda span{{display:inline-block;margin:0 10px}}
#barra{{position:absolute;left:0;top:0;width:1080px;height:12px;z-index:80;background:{tema['destaque']};transform-origin:0 50%}}
#assinatura{{position:absolute;left:0;right:0;bottom:120px;z-index:80;text-align:center;font-size:30px;
  font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:rgba(255,255,255,.75)}}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{_f(fim)}" data-width="1080" data-height="1920" data-fps="30">
<div id="veu" class="clip" data-start="0" data-duration="{_f(fim)}" data-track-index="1"></div>
{chr(10).join(elems)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(anim)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""


def _preparar_musica(canal, destino: Path, dur: float) -> bool:
    faixa = _musica(canal, destino.parent)
    if not faixa:
        return False
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(faixa),
                    "-t", f"{dur + 0.5:.2f}", "-c:a", "libmp3lame", "-q:a", "4", str(destino)], check=True)
    return True


def montar(canal, titulo, imagens, tempos, narracao: Path, palavras, dur, pasta: Path) -> Path:
    proj = pasta / "hf"
    proj.mkdir(exist_ok=True)
    for img in imagens:
        shutil.copy(img, proj / img.name)
    shutil.copy(narracao, proj / "narracao.mp3")
    shutil.copy(RAIZ / "node_modules/gsap/dist/gsap.min.js", proj / "gsap.min.js")
    fonte = RAIZ / "assets/fontes/Montserrat.ttf"
    if fonte.exists():
        shutil.copy(fonte, proj / "Montserrat.ttf")
    tem_musica = _preparar_musica(canal, proj / "musica.mp3", dur)
    (proj / "index.html").write_text(
        _composicao(canal, titulo, imagens, tempos, palavras, dur, tem_musica), encoding="utf-8")

    final = pasta / "video.mp4"
    cmd = [str(RAIZ / "node_modules/.bin/hyperframes"), "render", "-o", str(final), "--fps", "30",
           "--crf", "21", "--max-bitrate", "3500k", "--quiet"]
    log("montador", "renderizando com HyperFrames…")
    subprocess.run(cmd, cwd=proj, check=True,
                   env={**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY": "0"})
    log("montador", f"vídeo final (HyperFrames): {final}")
    return final
