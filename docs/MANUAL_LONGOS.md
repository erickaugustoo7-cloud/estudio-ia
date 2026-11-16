# Manual do roteirista — Vídeos longos do YouTube (Mensageiro de Fé)

Um vídeo longo **horizontal (16:9)** por execução, **só para o YouTube** (canal "Mensageiro de Fé | Sobre Jesus").
Meta do Eric (09/11): monetizar rápido — 1.000 inscritos e 4.000 horas assistidas. Os longos são o motor de horas.

## Qual vídeo fazer hoje
- **Quarta e sábado: FILME bíblico** (12–20 min). Pauta: primeira linha não comentada de `pautas/filmes.txt`.
  Modelo aprovado: `roteiros_animados/jose_do_egito.json`.
- **Demais dias: ORAÇÃO PARA DORMIR** (~20–22 min de oração FALADA, sem cauda de música — decisão do Eric em 16/11: a música de 20 min não segurava o público). Pauta: primeira linha não comentada de
  `pautas/oracoes_longas.txt`. Modelo aprovado (tom humano, 16/11): `roteiros_animados/oracao_noite_refugio_salmo46.json`.
- Remova a linha usada da pauta. Se a pauta acabar, escolha um tema novo que ainda não exista em `roteiros_animados/`.

## Passo a passo
1. `git pull`. Leia este manual, `docs/REGRAS_FIXAS.md` e o modelo do formato do dia (copie `estilo_imagem`,
   `prefixo_imagem`, `prefixo_video`, `formato`, `duracao_max`, `palavras_por_bloco`, `plataformas` e, na oração,
   `tipo`, `volume_musica`, `estilo_voz`; nunca `cauda_musical_min`).
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
- `texto_capa`: 3 linhas (curta / PALAVRA-CHAVE / complemento) — ver "Título e miniatura" abaixo; `cena_capa`: índice da
  cena com a imagem mais forte (só é usada se a foto emocional da miniatura falhar).
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

## Oração para dormir — tom HUMANO e EMOCIONAL (padrão desde 16/11, referência: canal Grace Oasis, 835 mil inscritos)
O que os grandes canais de oração fazem e nós não fazíamos:
1. **Abre falando com a PESSOA, não com Deus** (cenas 1–3): "Se você está assistindo isso agora, talvez o seu dia tenha
   sido pesado. Talvez ninguém tenha perguntado como você está. Deus perguntou. E Ele trouxe você até aqui."
   Nomeie dores concretas do dia a dia (conta atrasada, filho longe, diagnóstico, casamento frio, solidão, cansaço).
2. **Convida a orar junto**: "Feche os olhos. Coloque a mão no peito. Respire fundo… e repita comigo, no seu coração."
3. **A oração em 1ª pessoa, como gente de verdade fala com Deus**: frases curtas, pausas ("…"), confissões honestas
   ("Senhor, eu não vou fingir que estou bem."), pedidos específicos, entregas ("Eu solto isso agora nas Tuas mãos."),
   gratidão no fim. Nada de linguagem de livro ou de sermão; nada de frases genéricas em sequência.
4. **Escritura no meio, explicada em 1 frase** ("Davi escreveu isso fugindo… e mesmo assim dormiu em paz.").
5. **Momento de pedido do público**: "Se você tem um pedido, escreva nos comentários. Eu vou orar por ele." (o Eric responde.)
6. Inscreva-se falado antes do Amém (regra já existente) e bênção final em 2ª pessoa ("Durma em paz. Você não está sozinho.").
- `"estilo_voz"`: "emocionado e íntimo, como quem ora de verdade por alguém que sofre; voz baixa, pausada, com ternura"
  (vai como metadado da voz Gemini; não é narrado).

### Duração e estrutura (padrão desde 16/11)
- `"tipo": "oracao"`, **2000–2800 palavras, 40–90 cenas** (~20 s cada), `"palavras_por_bloco": 520`, SEM `cauda_musical_min`.
- Música só de fundo, baixinha, sob a voz (`volume_musica` ~0.2). Nada de 20 min só de música.
- `capitulos` obrigatórios (4–12), para o público pular para a parte que precisa. Sequência que funciona:
  Acolhida → o salmo/promessa do dia → oração "do jeito que eu estou" → pela mente/ansiedade → pela família e filhos →
  pela saúde → pelas contas e trabalho → perdão (dos outros e de si) → o versículo central → gratidão → pedidos dos
  comentários → quem está longe de Deus → promessas para a noite (3–4 versículos curtos, Almeida) → silêncio guiado
  com respiração → leitura lenta do salmo → inscreva-se → bênção final → amém.
- Modelo completo: `roteiros_animados/oracao_noite_refugio_salmo46.json`.

### Título e miniatura (padrão desde 16/11)
- `titulo_youtube` emocional e direto, em 2ª pessoa ou pedido: "ORE ISSO ANTES DE DORMIR | Entregue Sua Ansiedade a Deus",
  "Senhor, Cuida da Minha Casa Esta Noite | Oração da Noite", "Deus Não Dorme: Durma em Paz Hoje | Salmo 121".
- `texto_capa` = **3 linhas**: curta / PALAVRA-CHAVE / complemento (a linha mais curta sai ENORME). Ex.:
  ["ORE ISSO", "ANTES", "DE DORMIR"], ["SENHOR,", "CUIDA", "DA MINHA CASA"], ["ENTREGUE", "TUDO", "A DEUS HOJE"].
- A miniatura agora é gerada sozinha no estilo dos grandes canais: foto emocional de uma pessoa orando à direita,
  céu à esquerda, texto branco limpo e "O R A Ç Ã O  D A  N O I T E" embaixo. Opcional: `capa_prompt` (inglês) para
  escolher a pessoa/cena da foto (ex.: "a tired Brazilian mother praying at a kitchen table at night...").

## Regras que continuam
- **Short isca (obrigatório):** `"short_isca": {"cenas": [i], "texto_topo": "DEUS NÃO DORME", "titulo": "...", "hashtags": [...]}`.
  Escolha a cena (ou 2 seguidas) com a frase mais forte e consoladora, 12–45 palavras (Short de 8–20 s; Shorts curtos
  são assistidos várias vezes — "Em paz me deito" teve 156% de retenção). Opcional: `"trecho"` = cópia exata de parte
  da cena para recortar só aquela frase. O sistema monta o Short vertical com a mesma voz e as mesmas imagens e abre
  uma Issue separada; o Eric publica depois da oração e liga o Short a ela em "Vídeo relacionado".
- **Convite para se inscrever (falado):** numa das 3 últimas cenas, ANTES do "Amém" final, uma frase curta como
  "Se esta oração te ajudou, inscreva-se no canal para orarmos juntos toda noite." (o validador cobra "inscreva").
- **Sem GPU:** use `"fonte_imagem": "cloudflare"` (imagens no Cloudflare/Pollinations, revisão rigorosa, todas as cenas
  com movimento de câmera e `"animar": false`). Assim a oração não depende da cota semanal do Kaggle.
- Estrutura: acolhida em 2ª pessoa (você) → convite para orar junto → oração em 1ª pessoa parafraseando um salmo ou
  promessa bíblica → pedido nos comentários + inscreva-se → bênção final. Original, sem copiar orações prontas.
- Imagens de noite, paz e natureza da época (céu estrelado, colinas, lago, oliveiras, lamparina de barro). Nada de
  lamparina/lanterna de vidro, casas modernas, móveis modernos. Varie as imagens: ~20 s cada, sem repetir a mesma
  paisagem em sequência.
- Varie o tema a cada dia para não parecer conteúdo repetido (motivo nº 1 de recusa na monetização).

## Regras de imagem
As mesmas de `docs/REGRAS_FIXAS.md`: nenhum rosto, pessoas só minúsculas ao longe, nada moderno, prompts com
no máximo 3–4 elementos, objetos da época pelo nome (barro, pedra, madeira, lã, linho, bronze).
