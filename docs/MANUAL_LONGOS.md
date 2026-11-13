# Manual do roteirista — Vídeos longos do YouTube (Mensageiro de Fé)

Um vídeo longo **horizontal (16:9)** por execução, **só para o YouTube** (canal "Mensageiro de Fé | Sobre Jesus").
Meta do Eric (09/11): monetizar rápido — 1.000 inscritos e 4.000 horas assistidas. Os longos são o motor de horas.

## Qual vídeo fazer hoje
- **Quarta e sábado: FILME bíblico** (12–20 min). Pauta: primeira linha não comentada de `pautas/filmes.txt`.
  Modelo aprovado: `roteiros_animados/jose_do_egito.json`.
- **Demais dias: ORAÇÃO PARA DORMIR** (~7 min de oração + 20 min só de música). Pauta: primeira linha não comentada de
  `pautas/oracoes_longas.txt`. Modelo aprovado: `roteiros_animados/oracao_noite_salmo91.json`.
- Remova a linha usada da pauta. Se a pauta acabar, escolha um tema novo que ainda não exista em `roteiros_animados/`.

## Passo a passo
1. `git pull`. Leia este manual, `docs/REGRAS_FIXAS.md` e o modelo do formato do dia (copie `estilo_imagem`,
   `prefixo_imagem`, `prefixo_video`, `formato`, `duracao_max`, `palavras_por_bloco`, `plataformas` e, na oração,
   `cauda_musical_min`, `volume_musica`, `cena_cauda`).
2. Leia a passagem na web (NVI/ARA/NAA). Nada inventado: nomes, falas, números e ordem dos fatos conferidos.
   Citações literais curtas (até ~15 palavras cada), sempre com a referência.
3. Escreva `roteiros_animados/<slug>.json` e rode `python ferramentas/validar_animacao.py roteiros_animados/<slug>.json`
   até dar **OK** (o validador reconhece o formato horizontal: filme = 60–110 cenas, 900–1400 palavras, até 10 cenas
   animadas; oração = 18–30 cenas, 800–1100 palavras, até 6 animadas). Sem OK, não produza.
4. Commit/push (e-mail noreply) e dispare pela API REST (nunca GraphQL):
   `gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/kaggle-wan.yml/dispatches -X POST -f ref=main -f 'inputs[roteiro]=roteiros_animados/<slug>.json' -f 'inputs[maquina]=NvidiaTeslaT4'`
5. **Não acompanhe até o fim** (leva 1h30–3h): confira só que a execução entrou na fila e termine. O workflow manda
   o vídeo ao Telegram e abre a Issue de aprovação. **Nunca cancele** uma produção que já chegou ao Kaggle
   (a sessão continua lá e trava a fila).
6. Termine com um resumo curto: título do YouTube, formato, referência, nº de cenas e o link da execução.
Nunca publique nada, nunca mexa em segredos/tokens, não altere o código do sistema.

## Campos obrigatórios (além dos do modelo)
- `titulo_youtube` (até 100 caracteres, padrão "TEMA EM CAIXA ALTA | complemento com a palavra que as pessoas buscam").
  Ex.: "ORAÇÃO DA NOITE | Salmo 23 para Dormir em Paz", "MOISÉS | O Filme Bíblico (Êxodo 1–14)".
- `texto_capa`: 2 linhas curtas para a miniatura (ex.: ["SALMO 23", "DURMA EM PAZ"]); `cena_capa`: índice da cena
  com a imagem mais forte (sem texto, sem gente em destaque).
- **Capa que faz clicar (sem mentir):** `texto_capa` = 2 linhas de 1 a 3 palavras com a emoção ou o conflito
  (filme: "VENDIDO" / "PELOS IRMÃOS", "O MAR" / "SE ABRIU"; oração: "SALMO 23" / "DURMA EM PAZ", "ANSIEDADE?" / "ORE COMIGO").
  O selo ("FILME BÍBLICO"/"ORAÇÃO PARA DORMIR") e o rodapé ("+20 min de música"/"Filme completo") entram sozinhos;
  troque com `selo_capa` / `rodape_capa` se quiser.
- **Filme: `capitulos`** = lista `{"cena": índice, "titulo": "..."}` (8–14 capítulos). Viram os marcadores de tempo da
  descrição (o YouTube mostra como capítulos e isso aumenta o tempo assistido). Orações ganham capítulos automáticos.
- `legenda` (descrição do YouTube: resumo, versículo-chave com referência e convite para comentar "Amém" e se inscrever),
  `hashtags` (5), `fontes`.

## Filme bíblico
- Narração de documentário/filme: começa com um gancho forte (a cena mais dramática), depois volta ao início.
- Contexto histórico e geográfico que o público não sabe; detalhes concretos do texto valem mais que adjetivos.
- Cada cena tem um trecho curto (3–30 palavras) e uma imagem. Use `epoca_imagem` por cena quando o lugar muda
  (ex.: Canaã x Egito x deserto), como no José.
- No máximo 10 cenas com `"animar": true` — as mais cinematográficas (céu, água, fogo, tempestade, luz). As outras
  ganham movimento de câmera automático.

## Oração para dormir
- **Convite para se inscrever (falado):** numa das 3 últimas cenas, ANTES do "Amém" final, uma frase curta como
  "Se esta oração te ajudou, inscreva-se no canal para orarmos juntos toda noite." (o validador cobra "inscreva").
- **Sem GPU:** use `"fonte_imagem": "cloudflare"` (imagens no Cloudflare/Pollinations, revisão rigorosa, todas as cenas
  com movimento de câmera e `"animar": false`). Assim a oração não depende da cota semanal do Kaggle.
- Voz calma, em 1ª pessoa ("Senhor, esta noite..."), parafraseando um salmo ou promessa bíblica, versículo a versículo.
  Original, sem copiar orações prontas. Termina convidando a descansar e entregar a noite a Deus.
- Imagens de noite, paz e natureza da época (céu estrelado, colinas, lago, oliveiras, lamparina de barro). Nada de
  lamparina/lanterna de vidro, casas modernas, móveis modernos. `cena_cauda`: a imagem mais limpa (paisagem sem objetos),
  porque fica 20 min na tela.
- Varie o tema a cada dia para não parecer conteúdo repetido (motivo nº 1 de recusa na monetização).

## Regras de imagem
As mesmas de `docs/REGRAS_FIXAS.md`: nenhum rosto, pessoas só minúsculas ao longe, nada moderno, prompts com
no máximo 3–4 elementos, objetos da época pelo nome (barro, pedra, madeira, lã, linho, bronze).
