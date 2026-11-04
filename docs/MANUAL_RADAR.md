# Manual do Radar — tendências do nicho (Mensageiro de Fé e Curioso)

Lido pela sessão agendada semanal do Claude. Objetivo: descobrir o que está viralizando nos
nichos dos dois canais e transformar isso em insumo para os roteiristas.

## Regras

- **Não colete dados do TikTok de forma automatizada** (não faça scraping, não use endpoints internos,
  não contorne login/bloqueio). Use só as fontes abaixo.
- Não publique nada, não mexa em segredos, não altere código do sistema.

## Passo a passo

1. `git pull`. Dispare a coleta e espere terminar:
   `gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/radar.yml/dispatches -X POST -f ref=main`
   (acompanhe pelo `/actions/runs`, depois `git pull`). Os dados ficam em `dados/radar/<data>_biblico.json`
   e `dados/radar/<data>_espaco.json` (Shorts do YouTube BR mais vistos em 7 dias).
   Se o arquivo não vier (sem chave YOUTUBE_API_KEY), siga só com as fontes do passo 2 e avise no resumo.
2. Complemente com **busca na web** (notícias e datas da semana: feriados religiosos, eventos
   astronômicos — eclipses, chuvas de meteoros, lançamentos, descobertas da NASA/ESA) e com
   **Google Trends Brasil** se acessível. Leia também `dados/metricas/` (prints/anotações do Eric
   sobre o desempenho dos próprios vídeos), se houver.
3. Lembre o perfil do público do Mensageiro de Fé (~75% homens, ver MANUAL_ROTEIRISTA.md): ao sugerir
   pautas, adapte o que viraliza no nicho (muitas vezes voltado a mulheres) a esse público, e anote se
   ele mudou quando o Eric mandar novos prints.
4. **Analise por canal** (ignore vídeos que não são em português do Brasil ou fora do nicho):
   - temas/personagens que mais aparecem no topo (ex.: Jesus chorando, Salmo 91, buracos negros);
   - **padrões de gancho nos títulos** (pergunta, "ninguém te contou", número, "você sabia");
   - duração típica dos que mais viralizaram (curtos ≤ 20 s × longos ≥ 60 s);
   - formatos (versículo na tela, narração de história, oração, lista de fatos);
   - o que perdeu força em relação ao relatório anterior (compare com o último `docs/radar/AAAA-MM-DD.md`).
5. Escreva `docs/radar/<data>.md` e copie para `docs/radar/RADAR.md` (o mais recente, lido pelos
   roteiristas), com, para cada canal:
   - **Em alta** (3–6 temas, cada um com 1–2 exemplos: título, visualizações, link);
   - **Ganchos que estão funcionando** (3–5 modelos de frase adaptados ao canal);
   - **Duração e formato recomendados**;
   - **Evitar** (o que está saturado ou caiu);
   - **5 pautas sugeridas** já no estilo do canal (Mensageiro de Fé: Jesus como personagem principal).
6. **Alimente as filas:** acrescente as 5 pautas sugeridas ao FIM de `pautas/biblico.txt` e
   `pautas/espaco.txt` (sem duplicar o que já está lá ou já foi feito em `roteiros/`).
7. Escreva `docs/radar/ultimo_resumo.txt` (máx. ~1.200 caracteres, texto simples para celular):
   3 destaques de cada canal + as pautas adicionadas. Commit e push de tudo.
8. Envie o resumo ao Telegram:
   `gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/avisar.yml/dispatches -X POST -f ref=main -f 'inputs[arquivo]=docs/radar/ultimo_resumo.txt'`
9. Termine com um resumo curto em português do que foi encontrado e alterado.
