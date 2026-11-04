# Manual do roteirista — Curioso (canal `espaco`)

Lido pela sessão agendada do Claude que escreve **um roteiro verificado por execução** para o
canal Curioso (espaço, astronomia e "como as coisas funcionam"). Português do Brasil.

## Passo a passo de cada execução

1. `git pull`. Leia `canais/espaco.yaml`, este manual e, se existir, `docs/radar/RADAR.md`
   (tendências da semana — dê preferência aos temas e formatos de gancho que ele indicar).
2. **Pauta:** a primeira linha não comentada de `pautas/espaco.txt`. Se vazia, escolha um tema
   novo com fato surpreendente e verificável, sem repetir `roteiros/` nem `historico/espaco.json`.
3. **Pesquise e confirme cada número/fato em fonte confiável** (NASA, ESA, INPE, Space.com,
   enciclopédias, artigos). Use a busca na web. Nada de memória sem conferir. Hipótese = diga que é hipótese.
4. Escreva `roteiros/<slug>.json` (formato abaixo) e rode
   `python ferramentas/validar_roteiro.py roteiros/<arquivo>.json --canal=espaco` até dar OK.
5. Remova a linha usada da fila (se veio da fila). Commit e push.
6. Dispare (REST, nunca GraphQL):
   ```
   gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/produzir.yml/dispatches \
     -X POST -f ref=main -f 'inputs[canal]=espaco' -f 'inputs[roteiro]=roteiros/<arquivo>.json'
   ```
7. Acompanhe até terminar (~15–25 min). Se falhar, leia o log, corrija se for o roteiro e tente
   de novo **uma** vez. O workflow manda o vídeo ao Telegram e abre a Issue.
8. Resumo final: título, duração (linha `[narrador]`), link da Issue, fontes usadas.

Não publique nada, não mexa em segredos, não altere outras partes do sistema.

## Estrutura que retém

1. **Gancho (cena 1, só ele, ≤ 12 palavras):** fato surpreendente em forma de mistério.
   Ex.: "Existe um planeta onde o dia dura mais que o ano."
2. **2ª frase: mini-resposta + nova promessa.** Ex.: "É Vênus, o nosso vizinho. E isso nem é a
   coisa mais estranha sobre ele." Nunca contexto ou aula na 2ª frase.
3. Escalada de fatos, do mais curioso ao mais impressionante; analogias do dia a dia
   ("como estar a um quilômetro de profundidade no oceano").
4. Fechar com **pergunta para comentário** + CTA do canal ("Siga para descobrir uma curiosidade nova todo dia.").
- **195–225 palavras** (~70–85 s). Números por extenso. Sem emojis/listas na narração.
- **8 ou 9 cenas**; troca de imagem a cada 1–2 frases. Trechos juntados com espaço = narração.
- Sem tom de aula ("Neste vídeo", "Vamos entender"). Sem sensacionalismo nem conspiração.

## Imagens

`busca_imagem`: 2–4 palavras em inglês que achem a foto certa no acervo da NASA (ex.: "Venus Magellan",
"Saturn rings Cassini"). Seja específico — busca genérica traz foto fora do tema.
`prompt_imagem`: descrição em inglês da cena (é usada se a NASA não tiver a imagem).

## Texto na tela e legenda

- `gancho_tela`: até 7 palavras, complementa a fala, sem emoji.
- `legenda`: 1–2 linhas com o fato principal em números + pergunta ("Você aguentaria morar lá? 👇").
- `hashtags`: 4 específicas. `fontes`: as referências usadas.

Formato igual ao de `roteiros/venus_dia_ano.json` (exemplo aprovado).
