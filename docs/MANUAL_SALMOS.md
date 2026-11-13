# Manual — Salmos narrados (voz do Eric)

Um salmo (ou trecho de salmo) narrado com a **voz do Eric** (clone autorizado por ele), vertical 9:16, **70–120 s**,
para TikTok, Instagram, Facebook e YouTube Shorts. Substitui os curtos de versículo sobre imagem, que o Instagram
marcou como "conteúdo não original" em 12/11/2026. Originalidade é a prioridade.

## Passo a passo
1. `git pull`. Pauta: primeira linha não comentada de `pautas/salmos_narrados.txt` (remova-a). Fila vazia → escolha
   um salmo que ainda não exista em `roteiros_animados/salmo_*_narrado.json`.
2. Texto bíblico: **Almeida de domínio público** (Revista e Corrigida edição de 1898/1911). Confira cada versículo
   na busca na web. Na dúvida sobre a edição, NÃO use NVI/ARA/NAA/NTLH (têm direitos autorais): use a Almeida antiga.
3. Copie `roteiros_animados/salmo_139_narrado.json` (mantenha `"tipo": "salmo"`, `"voz": "eric"`,
   `"fonte_imagem": "cloudflare"`, `"serie": "Salmos narrados"`, estilo e prefixos) e escreva
   `roteiros_animados/salmo_<numero>_narrado.json`:
   - cena 1: abertura curta ("Salmo 23. Ouça com calma…"), última cena: fecho curto e original convidando a
     comentar "Amém" e **terminando com o convite para seguir**: "Siga o Mensageiro de Fé para ouvir um salmo
     por dia" (o validador cobra "siga") — varie as outras palavras a cada salmo;
   - 4–7 cenas no total, 180–320 palavras (o validador aceita 120–420), trechos por blocos de versículos;
   - imagens de natureza/luz que combinem com cada bloco (monte, mar, deserto, céu estrelado, vale, campo, rio,
     cruz no fim), sem rosto, pessoas só minúsculas ao longe ou nenhuma (`"vazia": true`), nada moderno;
   - `titulo` = **curiosidade ou dor real, não o nome do salmo** (dados de 13/11: "Salmo 23 — O Senhor é o meu pastor" teve 87% de retenção mas só 73 views; histórias com gancho tiveram 600+). Ex.: "O salmo que Davi escreveu fugindo para salvar a vida (Salmo 3)", "Por que o Salmo 23 fala do vale da sombra da morte". `gancho_tela` = 2–5 palavras de curiosidade ("DAVI ESTAVA FUGINDO"); a 1ª frase narrada (antes do texto bíblico) conta em 1 linha o contexto que prende; `legenda` com o versículo-chave, a
     referência "(Almeida)" e um convite; `hashtags` (5); `fontes` com a referência.
4. `python ferramentas/validar_animacao.py roteiros_animados/<arquivo>.json` até dar **OK**. Sem OK, não produza.
5. Commit/push (autor estudio-bot, e-mail estudio-bot@users.noreply.github.com) e dispare `kaggle-wan.yml` pela
   API REST (nunca GraphQL). Confira só que entrou na fila e termine — não acompanhe até o fim, nunca cancele.
Não publique nada, não mexa em segredos, não altere o código do sistema.
