"""Vídeos curtos (9–20 s): leão em movimento ao fundo + versículo fixo na tela (ou palavra por palavra, com "revelar": true).

Sem narração: trilha instrumental gerada. A imagem do leão é gerada por IA e animada
(zoom lento, "respiração", brilho pulsando e partículas de luz) para parecer viva.

Uso:  python -m estudio.curto roteiros_curtos/josue_1_9.json [outro.json ...] [--sem-envio] [--sem-issue]
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
from estudio.agentes import publicador, visual
from estudio.agentes.montador import _gerar_trilha
from estudio.produzir import abrir_issue, montar_texto_post

ESTILO_LEAO = ("ultra realistic cinematic wildlife photography, majestic male lion, detailed mane, "
               "dark black background, dramatic golden rim light, shallow depth of field, film grain, "
               "vertical 9:16, no text, no letters, no watermark")
POR_PALAVRA = 0.42  # segundos entre uma palavra e outra (ritmo de leitura confortável)


def _f(x: float) -> str:
    return f"{x:.3f}"


def _composicao(canal, r, dur) -> str:
    destaque = "#FFD27A"
    palavras = r["versiculo"].split()
    t0 = 1.0
    elems, anim = [], []

    # ---- leão: zoom lento + "respiração" + leve deriva ----
    elems.append(f'<div id="leao" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="0">'
                 f'<img id="foto" src="leao.jpg" /></div>')
    # movimento já no 1º quadro: zoom de impacto (0,9 s) e depois o zoom lento
    anim.append('tl.fromTo("#foto",{scale:1.32,yPercent:0},{scale:1.06,duration:0.9,ease:"power3.out"},0);')
    anim.append(f'tl.to("#foto",{{scale:1.2,yPercent:-2.5,duration:{_f(dur - 0.9)},ease:"none"}},0.9);')
    # clarão dourado rápido na abertura
    elems.append(f'<div id="clarao" class="clip" data-start="0" data-duration="1.2" data-track-index="2"></div>')
    anim.append('tl.fromTo("#clarao",{opacity:0.75},{opacity:0,duration:0.9,ease:"power2.out"},0);')
    respiros = max(1, int(dur // 3.2))
    anim.append(f'tl.fromTo("#leao",{{scale:1}},{{scale:1.025,duration:1.6,ease:"sine.inOut",yoyo:true,repeat:{respiros * 2 - 1}}},0);')

    # ---- brilho dourado pulsando ----
    elems.append(f'<div id="brilho" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="1"></div>')
    anim.append(f'tl.fromTo("#brilho",{{opacity:0.15}},{{opacity:0.55,duration:2.2,ease:"sine.inOut",yoyo:true,'
                f'repeat:{max(1, int(dur // 2.2))}}},0);')

    # ---- partículas de luz subindo ----
    rnd = random.Random(r["versiculo"])
    pts = []
    for k in range(34):
        x, y, tam = rnd.uniform(20, 1060), rnd.uniform(500, 1900), rnd.uniform(3, 9)
        pts.append(f'<i id="p{k}" style="left:{x:.0f}px;top:{y:.0f}px;width:{tam:.1f}px;height:{tam:.1f}px"></i>')
        ini = rnd.uniform(0, dur * 0.4)
        anim.append(f'tl.fromTo("#p{k}",{{y:0,opacity:0}},{{y:-{rnd.uniform(250, 650):.0f},opacity:{rnd.uniform(0.4, 0.9):.2f},'
                    f'duration:{_f(dur - ini)},ease:"none"}},{_f(ini)});')
    elems.append(f'<div id="particulas" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="2">{"".join(pts)}</div>')

    # ---- faixa do gancho (visível no quadro 0, sai aos ~2,6 s) ----
    revelar = r.get("revelar", False)  # padrão: versículo fixo desde o 1º quadro (melhor para curtos)
    if revelar and r.get("gancho_tela"):
        elems.append(f'<div id="gancho" class="clip" data-start="0" data-duration="2.9" data-track-index="3">'
                     f'<span>{html.escape(r["gancho_tela"].upper())}</span></div>')
        anim.append('tl.to("#gancho span",{scale:1.06,duration:0.18,ease:"power2.out",yoyo:true,repeat:1},0.25);')
        anim.append('tl.to("#gancho span",{opacity:0,y:-30,duration:0.3,ease:"power2.in"},2.55);')

    # ---- versículo palavra por palavra ----
    spans = " ".join(f'<span id="v{j}">{html.escape(p)}</span>' for j, p in enumerate(palavras))
    tam = 74 if len(palavras) <= 18 else 66 if len(palavras) <= 28 else 60
    ref_html = f'<div id="ref">{html.escape(r["referencia"])}</div>'
    elems.append(f'<div id="verso" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="4" '
                 f'style="font-size:{tam}px">{spans}{ref_html}</div>')
    for j in range(len(palavras) if revelar else 0):
        anim.append(f'tl.fromTo("#v{j}",{{opacity:0,y:18}},{{opacity:1,y:0,duration:0.35,ease:"power2.out"}},{_f(t0 + j * POR_PALAVRA)});')
    t_ref = t0 + len(palavras) * POR_PALAVRA + 0.2
    if revelar:
        anim.append(f'tl.fromTo("#ref",{{opacity:0,letterSpacing:"0.5em"}},{{opacity:1,letterSpacing:"0.22em",duration:0.8,ease:"power2.out"}},{_f(t_ref)});')

    elems.append(f'<div id="assinatura" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="5">'
                 f'{html.escape(canal["nome"])}</div>')
    elems.append(f'<audio src="musica.mp3" data-start="0" data-duration="{_f(dur)}" data-volume="0.55" '
                 f'data-fade-in="0.8" data-fade-out="1.5" data-track-index="6"></audio>')

    return f"""<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="gsap.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden}}
#leao{{position:absolute;inset:0;transform-origin:50% 40%}}
#foto{{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover;transform-origin:50% 40%}}
#clarao{{position:absolute;inset:0;z-index:8;pointer-events:none;
  background:radial-gradient(ellipse 80% 50% at 50% 35%,rgba(255,220,150,.9),rgba(255,200,110,.25) 60%,rgba(0,0,0,0) 100%)}}
#brilho{{position:absolute;inset:0;z-index:5;pointer-events:none;mix-blend-mode:screen;
  background:radial-gradient(ellipse 60% 35% at 50% 32%,rgba(255,196,90,.55),rgba(255,196,90,0) 70%)}}
#veu{{position:absolute;inset:0;z-index:6;
  background:linear-gradient(180deg,rgba(0,0,0,.35) 0%,rgba(0,0,0,0) 25%,rgba(0,0,0,.15) 45%,rgba(0,0,0,.82) 72%,rgba(0,0,0,.9) 100%)}}
#particulas{{position:absolute;inset:0;z-index:7}}
#particulas i{{position:absolute;border-radius:50%;background:#ffd98a;box-shadow:0 0 12px 3px rgba(255,200,100,.7)}}
#gancho{{position:absolute;left:60px;right:60px;top:240px;z-index:20;text-align:center}}
#gancho span{{display:inline-block;font-family:'DejaVu Serif',Georgia,serif;font-weight:900;font-size:76px;line-height:1.12;
  color:#111;background:{destaque};padding:20px 32px;border-radius:22px;box-shadow:0 14px 40px rgba(0,0,0,.6)}}
#verso{{position:absolute;left:70px;right:70px;top:1020px;z-index:20;text-align:center;
  font-family:'EB Garamond','DejaVu Serif',Georgia,serif;font-weight:600;font-size:74px;line-height:1.22;color:#fff;
  text-shadow:0 6px 24px rgba(0,0,0,.95)}}
#verso span{{display:inline-block}}
#ref{{margin-top:44px;text-align:center;font-family:'DejaVu Serif',Georgia,serif;
  font-size:40px;font-weight:700;color:{destaque};text-transform:uppercase;letter-spacing:.22em}}
#assinatura{{position:absolute;left:0;right:0;bottom:110px;z-index:20;text-align:center;font-family:'DejaVu Sans',sans-serif;
  font-size:28px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:rgba(255,255,255,.7)}}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{_f(dur)}" data-width="1080" data-height="1920" data-fps="30">
<div id="veu" class="clip" data-start="0" data-duration="{_f(dur)}" data-track-index="1"></div>
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


def produzir_curto(caminho: Path, sem_envio: bool, sem_issue: bool) -> None:
    canal = carregar_canal("biblico")
    r = json.loads(caminho.read_text(encoding="utf-8"))
    pasta = SAIDA / f"curto_{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    proj = pasta / "hf"
    proj.mkdir(parents=True)
    n = len(r["versiculo"].split())
    if r.get("revelar", False):
        dur = max(13.0, round(1.0 + n * POR_PALAVRA + 3.6, 2))
    else:  # texto fixo: tempo de leitura folgado; ao terminar o TikTok repete (conta como visto até o fim)
        dur = max(9.0, round(n * 0.32 + 3.5, 1))

    canal_img = {**canal, "estilo_visual": r.get("estilo_imagem", ESTILO_LEAO),
                 "regra_visual_pessoas": r.get("regra_pessoas", "no people")}
    ok = visual.gerar_uma(canal_img, {"prompt_imagem": r.get("prompt_imagem") or r["prompt_leao"]},
                          proj / "leao.jpg", semente=random.randint(1, 10**6))
    if not ok:
        raise RuntimeError("não foi possível gerar a imagem do leão")
    _gerar_trilha(canal, proj / "musica.mp3", dur + 1)
    shutil.copy(RAIZ / "node_modules/gsap/dist/gsap.min.js", proj / "gsap.min.js")
    (proj / "index.html").write_text(_composicao(canal, r, dur), encoding="utf-8")

    video = pasta / "video.mp4"
    log("curto", f"renderizando '{r['titulo']}' ({dur:.1f}s)…")
    subprocess.run([str(RAIZ / "node_modules/.bin/hyperframes"), "render", "-o", str(video), "--fps", "30",
                    "--crf", "20", "--max-bitrate", "4000k", "--quiet"], cwd=proj, check=True,
                   env={**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY": "0"})
    shutil.copy(proj / "leao.jpg", pasta / "leao.jpg")
    from estudio.agentes.montador import normalizar_volume
    normalizar_volume(video)

    roteiro = {"titulo": r["titulo"], "narracao": f"(sem narração) {r['versiculo']} — {r['referencia']}",
               "legenda": r["legenda"], "hashtags": r.get("hashtags", []), "fontes": [r["referencia"]]}
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=2), encoding="utf-8")
    texto_post = montar_texto_post(canal, roteiro)
    (pasta / "post.txt").write_text(texto_post, encoding="utf-8")
    no_telegram = False
    if not sem_envio:
        no_telegram = publicador.telegram_video(video, f"🦁 [Curto] {r['titulo']} · {dur:.0f}s", texto_post)
    if not sem_issue:
        link = abrir_issue({**canal, "estilo_nome": "leão (curto)"}, roteiro, texto_post, pasta, dur,
                           ["Vídeo curto (< 60 s): não conta para o Creator Rewards, serve para movimentar o perfil."],
                           r["referencia"], no_telegram)
        log("curto", f"aguardando aprovação: {link}")
    log("curto", f"concluído: {video}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiros", nargs="+")
    ap.add_argument("--sem-envio", action="store_true")
    ap.add_argument("--sem-issue", action="store_true")
    a = ap.parse_args()
    for c in a.roteiros:
        produzir_curto(Path(c), a.sem_envio, a.sem_issue)


if __name__ == "__main__":
    main()
