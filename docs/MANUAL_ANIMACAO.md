# Manual do roteirista — Animações (Mensageiro de Fé)

Uma animação por execução: passagem bíblica marcante em **estilo cinematográfico realista, 45–75 s**, 8 a 12 planos, narrada.
**Modelo aprovado pelo Eric (07/11): `roteiros_animados/daniel_cova_leoes.json`** — copie os campos `estilo_imagem`,
`prefixo_imagem`, `prefixo_video` e adapte só `epoca_imagem` à época/lugar da história.
O formato foi aprovado pelo Eric em 06/11 (exemplo: `roteiros_animados/ressurreicao.json`).

## Passo a passo
1. `git pull`. Leia este manual, `canais/biblico.yaml` e, se existir, `docs/radar/RADAR.md`.
2. Pauta: a primeira linha não comentada de `pautas/animacoes.txt` (remova-a depois). Se vazia, escolha
   um momento forte dos Evangelhos com Jesus que ainda não exista em `roteiros_animados/`.
3. Leia a passagem na web (NVI/ARA/NAA) e não invente nada: falas, nomes e ordem dos fatos conferidos.
4. Leia docs/REGRAS_FIXAS.md. Escreva `roteiros_animados/<slug>.json` (formato abaixo), rode `python ferramentas/validar_animacao.py roteiros_animados/<slug>.json` até dar OK, e confira:
   `python -c "import json;r=json.load(open('roteiros_animados/<slug>.json'));print(sum(len(c['trecho'].split()) for c in r['cenas']))"`
   → **entre 100 e 150 palavras** no total, e cada cena com **6 a 16 palavras** (cada cena vira um clipe de até
   ~6 s; trecho maior que isso deixa o movimento em câmera lenta). Use `"duracao_max": 90`. Referência por extenso na penúltima cena; a última fica para a aplicação + convite.
5. Commit/push e dispare (REST, nunca GraphQL):
   `gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/kaggle-wan.yml/dispatches -X POST -f ref=main -f 'inputs[roteiro]=roteiros_animados/<slug>.json'`
6. Acompanhe até terminar (~40 min; consulte a cada 1–2 min). Se falhar, leia o log
   (`gh run view <id> --log | grep -E "\[wan\]|error" | tail -40`), corrija se for o roteiro e dispare de novo **uma** vez.
   O workflow manda o vídeo ao Telegram e abre a Issue de aprovação.
7. Termine com resumo curto: título, referência, duração (linha `[narrador]`), avisos e link da Issue.
Nunca publique nada, nunca mexa em segredos.

## Série "Os milagres de Jesus" (decisão do Eric, 06/11)
- Enquanto a fila tiver linhas "Parte N | ...", cada animação é um episódio da série. No JSON, inclua
  `"serie": "Os milagres de Jesus"` e `"parte": N` (o vídeo mostra o selo "OS MILAGRES DE JESUS · PARTE N" no topo).
- A última frase da cena 4 termina com o convite: "Siga para ver o próximo milagre." (conta nas 28–34 palavras).
- Legenda: 1ª linha = oração curta com emoji + " (Parte N)"; 2ª = referência; 3ª = "Comente Amém e siga a série 🙏".
- Quando a série acabar, volte a escolher momentos fortes dos Evangelhos.

## Regras de conteúdo
- Jesus é o personagem principal, em momento de emoção forte (milagre, toque, perdão, cruz, ressurreição).
- **Conte a história com contexto** (decisão do Eric, 06/11: a versão de 33 palavras ficou "pobre e sem contexto").
  Estrutura em 10–12 cenas, com MAIS FALAS dos personagens tiradas do texto (decisão do Eric, 06/11):
  1. Onde e o que está acontecendo, com o problema já no gancho ("Um casamento em Caná. ... o vinho acabou.").
  2. Por que isso importava naquela época (costume, vergonha, doença, medo, distância) — o contexto que o público não sabe.
  3. Quem age e o que diz (fala curta do texto bíblico, com a referência conferida).
  4–5. A ação de Jesus em detalhes concretos do texto (números, objetos, gestos: "seis potes de pedra", "até a borda").
  6. A reação/virada (quem se espanta, o que mudou).
  7. O significado + aplicação pessoal para "você" + referência por extenso + convite da série.
- Detalhes concretos do próprio texto bíblico valem mais que adjetivos. Nada inventado.
- Frases curtas, ritmo falado; no máximo 1 citação literal curta. Linha cristã ampla, sem doutrina de denominação.
- `gancho_tela`: até 6 palavras (aparece no 1º quadro). `referencia`: ex. "Marcos 4:39".

## Estilo cinematográfico (padrão — referência: vídeo "Daniel na cova dos leões" do @essenciadorein)
- Planos ABERTOS e ALTOS: cidades vistas do alto, cavernas vistas de cima, paisagens amplas. Quando houver gente, ela é
  minúscula ao longe ("a tiny distant kneeling man") e a cena leva `"vazia": false`; nas cenas sem gente, `"vazia": true`.
- A luz conta a emoção: feixe de luz do céu, tochas, fumaça, poeira no ar, amanhecer, luar.
- Arquitetura e objetos certos para a época, por nome: Babilônia = "mud-brick ziggurat, blue glazed Ishtar Gate,
  Mesopotamian palace"; Judeia do séc. I = "first century Judea stone houses, olive trees"; Egito = "ancient Egyptian
  temples and obelisks". Nunca só o nome da cidade.
- Cada prompt com no máximo 3–4 elementos principais (lugar, luz, o objeto/figura central). Prompt longo faz o gerador
  inventar objetos aleatórios (garrafas, plantas, luminárias).
- Movimento: câmera lenta (descendo, aproximando, afastando), luz, fumaça, poeira, tecidos; animais podem se acomodar devagar.

## Prompts de imagem (inglês)
- **Nenhum rosto aparece, de ninguém** (decisão do Eric, 06/11: o vídeo deforma rostos). Conte o milagre pelos
  OBJETOS e pelo AMBIENTE em close: mãos, potes, pães, redes, barco, água, luz, portas, lamparinas. Pessoas só como
  silhuetas escuras de costas ou figuras minúsculas ao longe. Festa/multidão = mesa, lamparinas e silhuetas distantes.
- Jesus, quando aparecer: figura de costas, parada, de preferência média/pequena no quadro (o vídeo às vezes vira
  personagens grandes para a câmera).
- Descreva só o essencial e **todas** as figuras que devem aparecer ("three women ... kneeling"), lugar e luz.
- Sempre época bíblica: "first century Judea", "rock-cut tomb", "olive trees", "no modern objects".
- Jesus: "a bearded man with long brown hair in a white robe seen from behind". Rostos nunca de frente.
- Evite pedir multidão; se a cena precisa de povo, diga "a few people in the distance". Prefira enquadramentos que naturalmente escondem rostos: Jesus de costas, mãos e objetos em primeiro plano (potes, pães, barco), figuras pequenas ao longe.
- `prompt_movimento`: movimentos suaves do que está na imagem (roupa ao vento, luz, água, nuvens, câmera
  aproximando). Nunca peça mudança de pose, gente se curvando/levantando ou objetos surgindo.

## Formato
```json
{"titulo": "...", "gancho_tela": "...", "referencia": "Marcos 4:39", "duracao_max": 22, "volume_musica": 0.12,
 "cenas": [{"trecho": "...", "prompt_imagem": "...", "prompt_movimento": "..."}],
 "legenda": "1ª linha oração curta com 1–2 emojis\nReferência\nComente \"Amém\" ...",
 "hashtags": ["#Jesus", "..."], "fontes": ["Marcos 4:35-41"]}
```
