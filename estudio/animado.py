"""Animações estilo desenho (até ~20 s): passagem bíblica narrada, em "motion comic".

Cada cena é uma ilustração 2D gerada por IA. O personagem/objeto principal é recortado do fundo
(rembg, open source) e os dois planos se movem em velocidades diferentes (profundidade). Por cima,
efeitos animados no HyperFrames: ondas (distorção SVG), chuva, vento, relâmpago, raios de luz,
partículas, estrelas e brasas. Narração Gemini + legenda palavra a palavra + música da Pixabay.

Uso:  python -m estudio.animado roteiros_animados/tempestade.json [outro.json ...] [--sem-envio] [--sem-issue]
"""
import argparse
import html
import json
import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from estudio.base import RAIZ, SAIDA, carregar_canal, log
from estudio.agentes import montador, narrador, publicador, visual
from estudio.agentes.montador_hf import _preparar_musica
from estudio.produzir import abrir_issue, montar_texto_post

ESTILO_DESENHO = ("2D hand-drawn animated feature film still, cel-shaded cartoon illustration, clean soft outlines, "
                  "painterly detailed background, warm cinematic colors, expressive lighting, vertical 9:16, "
                  "no text, no letters, no watermark")
REGRA_PESSOAS = ("Jesus and all people only seen from behind, in silhouette or at a distance, "
                 "faces never visible")
DESTAQUE = "#FFD27A"


def _f(x: float) -> str:
    return f"{x:.3f}"


# ---------------------------------------------------------------- recorte do personagem
_SESSAO = []


def recortar(img: Path, destino: Path) -> bool:
    """Separa o primeiro plano (PNG com transparência). Devolve False se o recorte não ficou útil."""
    try:
        from rembg import new_session, remove
        from PIL import Image
        if not _SESSAO:
            _SESSAO.append(new_session("isnet-general-use"))
        im = Image.open(img).convert("RGB")
        fg = remove(im, session=_SESSAO[0], post_process_mask=True)
        alfa = fg.getchannel("A")
        cobertura = sum(1 for v in alfa.resize((108, 192)).getdata() if v > 128) / (108 * 192)
        if not 0.03 <= cobertura <= 0.75:
            log("animado", f"recorte descartado ({cobertura:.0%} da imagem)")
            return False
        fg.save(destino)
        log("animado", f"recorte ok ({cobertura:.0%} da imagem)")
        return True
    except Exception as e:  # noqa: BLE001 — sem recorte, a cena só não terá profundidade
        log("animado", f"recorte indisponível ({e})")
        return False


# ---------------------------------------------------------------- efeitos
def _efeitos(i: int, efeitos: list[str], ini: float, d: float, rnd: random.Random, elems: list, anim: list,
             filtros: list) -> None:
    fim = ini + d
    if "agua" in efeitos or "ondas" in efeitos:
        forte = "ondas" in efeitos
        filtros.append(
            f'<filter id="fa{i}" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence id="ta{i}" type="turbulence" baseFrequency="0.006 0.035" numOctaves="2" seed="{i + 3}"/>'
            f'<feDisplacementMap in="SourceGraphic" scale="{34 if forte else 16}"/></filter>')
        anim.append(f'tl.fromTo("#ta{i}",{{attr:{{baseFrequency:"0.006 0.035"}}}},'
                    f'{{attr:{{baseFrequency:"0.009 0.05"}},duration:{_f(d / 2)},ease:"sine.inOut",yoyo:true,repeat:1}},{_f(ini)});')
        anim.append(f'tl.fromTo("#ta{i}",{{attr:{{seed:{i + 3}}}}},{{attr:{{seed:{i + 3 + int(d * 6)}}},duration:{_f(d)},'
                    f'ease:"steps({max(1, int(d * 6))})"}},{_f(ini)});')
    if "chuva" in efeitos:
        gotas = []
        for k in range(70):
            x, tam = rnd.uniform(-200, 1080), rnd.uniform(60, 140)
            gotas.append(f'<i id="r{i}_{k}" style="left:{x:.0f}px;top:-200px;height:{tam:.0f}px"></i>')
            vel = rnd.uniform(0.45, 0.8)
            anim.append(f'tl.fromTo("#r{i}_{k}",{{y:{rnd.uniform(-300, 1900):.0f},x:0}},{{y:"+=2300",x:"+=420",duration:{_f(vel)},'
                        f'ease:"none",repeat:{int(d / vel) + 1}}},{_f(ini)});')
        elems.append(f'<div class="chuva" style="z-index:{i * 10 + 6}">{"".join(gotas)}</div>')
    if "vento" in efeitos:
        linhas = []
        for k in range(14):
            y, w = rnd.uniform(200, 1700), rnd.uniform(180, 420)
            linhas.append(f'<i id="v{i}_{k}" style="top:{y:.0f}px;width:{w:.0f}px"></i>')
            vel = rnd.uniform(0.7, 1.3)
            anim.append(f'tl.fromTo("#v{i}_{k}",{{x:-500,opacity:0}},{{x:1500,opacity:0.5,duration:{_f(vel)},ease:"power1.in",'
                        f'repeat:{int(d / vel)},delay:{rnd.uniform(0, 0.8):.2f}}},{_f(ini)});')
        elems.append(f'<div class="vento" style="z-index:{i * 10 + 6}">{"".join(linhas)}</div>')
        alvo_v = f"#fg{i}" if f'id="fg{i}"' in "".join(elems) else f"#bg{i}"
        anim.append(f'tl.fromTo("{alvo_v}",{{skewX:-1.2}},{{skewX:1.2,duration:0.6,ease:"sine.inOut",yoyo:true,'
                    f'repeat:{max(1, int(d / 0.6))}}},{_f(ini)});')
    if "relampago" in efeitos:
        elems.append(f'<div id="rl{i}" class="relampago" style="z-index:{i * 10 + 7}"></div>')
        for t in sorted(rnd.uniform(ini + 0.3, fim - 0.6) for _ in range(2)):
            anim.append(f'tl.fromTo("#rl{i}",{{opacity:0}},{{opacity:0.85,duration:0.05,yoyo:true,repeat:3,ease:"none"}},{_f(t)});')
    if "luz" in efeitos:
        elems.append(f'<div id="lz{i}" class="luz" style="z-index:{i * 10 + 5}"></div>')
        anim.append(f'tl.fromTo("#lz{i}",{{opacity:0.25,rotation:-4}},{{opacity:0.7,rotation:4,duration:{_f(d)},ease:"sine.inOut"}},{_f(ini)});')
    if "particulas" in efeitos or "brasas" in efeitos:
        cor = "#ff9a3c" if "brasas" in efeitos else "#ffd98a"
        pts = []
        for k in range(30):
            x, y, tam = rnd.uniform(20, 1060), rnd.uniform(600, 1900), rnd.uniform(3, 9)
            pts.append(f'<i id="p{i}_{k}" style="left:{x:.0f}px;top:{y:.0f}px;width:{tam:.1f}px;height:{tam:.1f}px;'
                       f'background:{cor};box-shadow:0 0 12px 3px {cor}aa"></i>')
            anim.append(f'tl.fromTo("#p{i}_{k}",{{y:0,opacity:0}},{{y:-{rnd.uniform(250, 600):.0f},x:{rnd.uniform(-60, 60):.0f},'
                        f'opacity:{rnd.uniform(0.4, 0.9):.2f},duration:{_f(d)},ease:"none"}},{_f(ini)});')
        elems.append(f'<div class="particulas" style="z-index:{i * 10 + 6}">{"".join(pts)}</div>')
    if "estrelas" in efeitos:
        pts = []
        for k in range(40):
            x, y, tam = rnd.uniform(0, 1080), rnd.uniform(0, 900), rnd.uniform(2, 5)
            pts.append(f'<i id="e{i}_{k}" style="left:{x:.0f}px;top:{y:.0f}px;width:{tam:.1f}px;height:{tam:.1f}px"></i>')
            anim.append(f'tl.fromTo("#e{i}_{k}",{{opacity:0.2}},{{opacity:1,duration:{rnd.uniform(0.5, 1.2):.2f},yoyo:true,'
                        f'repeat:{int(d)},ease:"sine.inOut"}},{_f(ini + rnd.uniform(0, 0.5))});')
        elems.append(f'<div class="estrelas" style="z-index:{i * 10 + 4}">{"".join(pts)}</div>')


# ---------------------------------------------------------------- composição
MOVIMENTOS = {  # (escala inicial, escala final, x final %, y final %) do fundo; o 1º plano anda o dobro
    "zoom_in": (1.06, 1.2, 0, -1), "zoom_out": (1.22, 1.06, 0, 1), "pan_esq": (1.15, 1.15, -4, 0),
    "pan_dir": (1.15, 1.15, 4, 0), "subir": (1.15, 1.15, 0, -4), "balanco": (1.14, 1.2, 0, 0),
}


def _composicao(canal, r, cenas, tempos, tem_fg, palavras, dur) -> str:
    fim = dur + 0.6
    elems, anim, filtros = [], [], []
    rnd = random.Random(r["titulo"])
    inicio = 0.0
    for i, (cena, d) in enumerate(zip(cenas, tempos)):
        ultima = i == len(cenas) - 1
        dc = (fim - inicio) if ultima else d + 0.5
        efeitos = cena.get("efeitos", [])
        agua = "agua" in efeitos or "ondas" in efeitos
        s0, s1, x1, y1 = MOVIMENTOS.get(cena.get("movimento", "zoom_in"), MOVIMENTOS["zoom_in"])
        camadas = [f'<img id="bg{i}" class="plano" src="cena_{i}.jpg" />']
        if agua:  # cópia do fundo só na metade de baixo, distorcida como água
            camadas.append(f'<img id="ag{i}" class="plano agua" src="cena_{i}.jpg" style="filter:url(#fa{i})" />')
        if tem_fg[i]:
            camadas.append(f'<img id="fg{i}" class="plano" src="fg_{i}.png" />')
        alvo = f'"#bg{i}"' + (f',"#ag{i}"' if agua else "")
        anim.append(f'tl.fromTo([{alvo}],{{scale:{s0},xPercent:0,yPercent:0}},{{scale:{s1},xPercent:{x1},yPercent:{y1},'
                    f'duration:{_f(dc)},ease:"none"}},{_f(inicio)});')
        if tem_fg[i]:  # primeiro plano anda mais que o fundo → sensação de profundidade
            anim.append(f'tl.fromTo("#fg{i}",{{scale:{s0},xPercent:0,yPercent:0}},{{scale:{s1 + (s1 - s0) * 0.8 + 0.03:.3f},'
                        f'xPercent:{x1 * 2},yPercent:{y1 * 2 - 0.6},duration:{_f(dc)},ease:"none"}},{_f(inicio)});')
            anim.append(f'tl.fromTo("#fg{i}",{{y:0}},{{y:-10,duration:1.4,ease:"sine.inOut",yoyo:true,'
                        f'repeat:{max(1, int(dc / 1.4))}}},{_f(inicio)});')
        if cena.get("movimento") == "balanco":  # barco no mar agitado
            anim.append(f'tl.fromTo("#c{i}",{{rotation:-1.6}},{{rotation:1.6,duration:1.1,ease:"sine.inOut",yoyo:true,'
                        f'repeat:{max(1, int(dc / 1.1))}}},{_f(inicio)});')
        if i == 0:
            anim.append('tl.fromTo("#c0",{scale:1.25},{scale:1,duration:0.9,ease:"power3.out"},0);')
        else:
            anim.append(f'tl.fromTo("#c{i}",{{opacity:0}},{{opacity:1,duration:0.5,ease:"power1.inOut"}},{_f(inicio)});')
        _efeitos(i, efeitos, inicio, dc, rnd, camadas, anim, filtros)  # efeitos ficam dentro da cena
        elems.append(f'<div id="c{i}" class="clip cena" data-start="{_f(inicio)}" data-duration="{_f(dc)}" '
                     f'data-track-index="{i % 2}" style="z-index:{i * 10 + 1}">{"".join(camadas)}</div>')
        inicio += d

    # título no 1º quadro (é a prévia no feed)
    elems.append(f'<div id="gancho" class="clip" data-start="0" data-duration="2.8" data-track-index="2">'
                 f'<span>{html.escape(r.get("gancho_tela", r["titulo"]).upper())}</span></div>')
    anim.append('tl.to("#gancho span",{opacity:0,y:-30,duration:0.3,ease:"power2.in"},2.45);')

    # legenda palavra a palavra
    blocos = montador.blocos_legenda(palavras)
    for b, bloco in enumerate(blocos):
        ini = bloco[0]["ini"]
        prox = blocos[b + 1][0]["ini"] if b + 1 < len(blocos) else fim
        fb = min(bloco[-1]["fim"] + 0.15, prox)
        spans = " ".join(f'<span id="w{b}_{j}">{html.escape(p["texto"].upper())}</span>' for j, p in enumerate(bloco))
        elems.append(f'<div id="b{b}" class="clip legenda" data-start="{_f(ini)}" data-duration="{_f(max(0.2, fb - ini))}" '
                     f'data-track-index="3">{spans}</div>')
        anim.append(f'tl.fromTo("#b{b}",{{opacity:0,y:20,scale:0.92}},{{opacity:1,y:0,scale:1,duration:0.12,ease:"power2.out"}},{_f(ini)});')
        for j, p in enumerate(bloco):
            pj = bloco[j + 1]["ini"] if j + 1 < len(bloco) else fb
            anim.append(f'tl.set("#w{b}_{j}",{{color:"{DESTAQUE}"}},{_f(p["ini"])});')
            anim.append(f'tl.set("#w{b}_{j}",{{color:"#ffffff"}},{_f(pj)});')

    if r.get("referencia"):
        t = max(0.0, dur - 3.0)
        elems.append(f'<div id="ref" class="clip" data-start="{_f(t)}" data-duration="{_f(fim - t)}" data-track-index="4">'
                     f'{html.escape(r["referencia"])}</div>')
        anim.append(f'tl.fromTo("#ref",{{opacity:0,letterSpacing:"0.5em"}},{{opacity:1,letterSpacing:"0.22em",duration:0.8}},{_f(t)});')
    elems.append(f'<div id="assinatura" class="clip" data-start="0" data-duration="{_f(fim)}" data-track-index="4">'
                 f'{html.escape(canal["nome"])}</div>')
    elems.append(f'<audio src="narracao.mp3" data-start="0" data-duration="{_f(dur)}" data-volume="1" data-track-index="5"></audio>')
    elems.append(f'<audio src="musica.mp3" data-start="0" data-duration="{_f(fim)}" data-volume="{canal.get("musica_volume", 0.3)}" '
                 f'data-fade-in="0.6" data-fade-out="1.5" data-track-index="6"></audio>')

    return f"""<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="gsap.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:'DejaVu Sans',sans-serif}}
.cena{{position:absolute;inset:-40px;transform-origin:50% 50%;overflow:hidden}}
.plano{{position:absolute;left:40px;top:40px;width:1080px;height:1920px;object-fit:cover;transform-origin:50% 55%}}
.agua{{clip-path:inset(56% 0 0 0)}}
.chuva,.vento,.particulas,.estrelas{{position:absolute;inset:0;pointer-events:none;overflow:hidden}}
.chuva i{{position:absolute;width:3px;transform:rotate(-12deg);background:linear-gradient(rgba(220,230,255,0),rgba(220,230,255,.55))}}
.vento i{{position:absolute;left:0;height:3px;border-radius:3px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.6),rgba(255,255,255,0))}}
.particulas i{{position:absolute;border-radius:50%}}
.estrelas i{{position:absolute;border-radius:50%;background:#fff;box-shadow:0 0 6px 2px rgba(255,255,255,.7)}}
.relampago{{position:absolute;inset:0;background:#eef3ff;opacity:0;mix-blend-mode:screen;pointer-events:none}}
.luz{{position:absolute;left:-540px;top:-700px;width:2160px;height:2400px;pointer-events:none;mix-blend-mode:screen;
  transform-origin:50% 0;background:repeating-conic-gradient(from 160deg at 50% 0%,rgba(255,215,140,.0) 0deg,rgba(255,215,140,.35) 3deg,rgba(255,215,140,0) 7deg,rgba(255,215,140,0) 11deg);
  -webkit-mask-image:linear-gradient(180deg,#000 0%,rgba(0,0,0,.6) 45%,transparent 80%)}}
#veu{{position:absolute;inset:0;z-index:90;pointer-events:none;
  background:linear-gradient(180deg,rgba(0,0,0,.4) 0%,rgba(0,0,0,0) 20%,rgba(0,0,0,0) 55%,rgba(0,0,0,.65) 100%)}}
#gancho{{position:absolute;left:60px;right:60px;top:250px;z-index:95;text-align:center}}
#gancho span{{display:inline-block;font-family:'DejaVu Serif',Georgia,serif;font-weight:900;font-size:72px;line-height:1.12;
  color:#fff;text-shadow:0 6px 26px rgba(0,0,0,.95),0 0 4px rgba(0,0,0,.9)}}
.legenda{{position:absolute;left:50px;right:50px;top:1250px;z-index:96;text-align:center;font-weight:900;font-size:78px;
  line-height:1.15;color:#fff;-webkit-text-stroke:3px rgba(0,0,0,.9);paint-order:stroke fill;text-shadow:0 8px 22px rgba(0,0,0,.8)}}
.legenda span{{display:inline-block;margin:0 10px}}
#ref{{position:absolute;left:0;right:0;top:1520px;z-index:96;text-align:center;font-family:'DejaVu Serif',Georgia,serif;
  font-size:42px;font-weight:700;color:{DESTAQUE};text-transform:uppercase;text-shadow:0 4px 18px rgba(0,0,0,.9)}}
#assinatura{{position:absolute;left:0;right:0;bottom:110px;z-index:96;text-align:center;font-size:28px;font-weight:700;
  letter-spacing:.2em;text-transform:uppercase;color:rgba(255,255,255,.7)}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute">{"".join(filtros)}</svg>
<div id="root" data-composition-id="main" data-start="0" data-duration="{_f(fim)}" data-width="1080" data-height="1920" data-fps="30">
<div id="veu" class="clip" data-start="0" data-duration="{_f(fim)}" data-track-index="7"></div>
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


# ---------------------------------------------------------------- produção
def produzir_animado(caminho: Path, sem_envio: bool, sem_issue: bool) -> Path:
    canal = carregar_canal("biblico")
    r = json.loads(caminho.read_text(encoding="utf-8"))
    pasta = SAIDA / f"animado_{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    proj = pasta / "hf"
    proj.mkdir(parents=True)
    cenas = r["cenas"]
    texto = " ".join(c["trecho"] for c in cenas)

    canal_voz = canal
    if canal.get("gemini_tts"):
        canal_voz = {**canal, "gemini_tts": {**canal["gemini_tts"], "duracao_max": r.get("duracao_max", 20)}}
    mp3, palavras, dur = narrador.narrar(canal_voz, texto, pasta)
    tempos = montador.tempos_das_cenas(cenas, palavras, dur)

    canal_img = {**canal, "estilo_visual": r.get("estilo_imagem", ESTILO_DESENHO), "regra_visual_pessoas": REGRA_PESSOAS}
    semente = random.randint(1, 10**6)
    imagens = []
    for i, c in enumerate(cenas):
        destino = proj / f"cena_{i}.jpg"
        if not visual.gerar_uma(canal_img, c, destino, semente + i):
            raise RuntimeError(f"não foi possível gerar a imagem da cena {i + 1}")
        imagens.append(destino)
    avisos = []
    try:
        from estudio.agentes import revisor_visual
        avisos += revisor_visual.revisar(canal_img, cenas, imagens)
    except Exception as e:  # noqa: BLE001
        log("animado", f"revisão visual indisponível ({e})")
    tem_fg = [recortar(img, proj / f"fg_{i}.png") if c.get("recorte", True) else False
              for i, (img, c) in enumerate(zip(imagens, cenas))]

    shutil.copy(mp3, proj / "narracao.mp3")
    if not _preparar_musica(canal, proj / "musica.mp3", dur + 1):
        montador._gerar_trilha(canal, proj / "musica.mp3", dur + 1)
    shutil.copy(RAIZ / "node_modules/gsap/dist/gsap.min.js", proj / "gsap.min.js")
    (proj / "index.html").write_text(_composicao(canal, r, cenas, tempos, tem_fg, palavras, dur), encoding="utf-8")

    video = pasta / "video.mp4"
    log("animado", f"renderizando '{r['titulo']}' ({dur:.1f}s, {sum(tem_fg)}/{len(cenas)} cenas com profundidade)…")
    subprocess.run([str(RAIZ / "node_modules/.bin/hyperframes"), "render", "-o", str(video), "--fps", "30",
                    "--crf", "20", "--max-bitrate", "4500k", "--quiet"], cwd=proj, check=True,
                   env={**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY": "0"})
    montador.normalizar_volume(video)

    # prévias (um quadro do meio de cada cena) para conferência
    t = 0.0
    for i, d in enumerate(tempos):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t + d / 2:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=540:-1", str(pasta / f"previa_{i}.jpg")], check=False)
        t += d

    roteiro = {"titulo": r["titulo"], "narracao": texto, "legenda": r["legenda"],
               "hashtags": r.get("hashtags", []), "fontes": r.get("fontes", [])}
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")
    texto_post = montar_texto_post(canal, roteiro)
    (pasta / "post.txt").write_text(texto_post, encoding="utf-8")
    no_telegram = False
    if not sem_envio:
        no_telegram = publicador.telegram_video(video, f"🎨 [Animação] {r['titulo']} · {dur:.0f}s", texto_post)
    if not sem_issue:
        link = abrir_issue({**canal, "estilo_nome": "animação desenho"}, roteiro, texto_post, pasta, dur,
                           avisos, r.get("referencia", r["titulo"]), no_telegram)
        log("animado", f"aguardando aprovação: {link}")
        if no_telegram and link:
            publicador.telegram_mensagem(f"✅ Aprovar para Instagram e Facebook: {link}")
    log("animado", f"concluído: {video}")
    return pasta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiros", nargs="+")
    ap.add_argument("--sem-envio", action="store_true")
    ap.add_argument("--sem-issue", action="store_true")
    a = ap.parse_args()
    falhas = []
    for c in a.roteiros:
        try:
            produzir_animado(Path(c), a.sem_envio, a.sem_issue)
        except Exception as e:  # noqa: BLE001
            log("animado", f"FALHOU {c}: {e}")
            falhas.append(c)
    if falhas:
        raise SystemExit(f"{len(falhas)} animação(ões) falharam: {', '.join(falhas)}")


if __name__ == "__main__":
    main()
