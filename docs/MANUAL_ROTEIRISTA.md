# Manual do roteirista — Mensageiro de Fé (canal `biblico`)

Este manual é lido pela sessão agendada do Claude que escreve **um roteiro verificado por execução**
e manda produzir o vídeo. Ele resume tudo o que as métricas reais do TikTok do canal ensinaram.
Siga à risca. Escreva tudo em português do Brasil.

## Passo a passo de cada execução

1. Atualize o repositório (`git pull`). Leia `canais/biblico.yaml`, este manual e, se existir,
   `docs/radar/RADAR.md` (tendências da semana do Radar — use os ganchos e temas em alta que
   combinem com o foco do canal; o foco em Jesus continua valendo).
2. **Escolha a pauta:** a primeira linha não comentada de `pautas/biblico.txt`.
   Se a fila estiver vazia, crie uma pauta nova seguindo o foco abaixo, sem repetir
   nada que já exista em `roteiros/` ou em `historico/biblico.json`.
3. **Leia o texto bíblico da passagem** (use a busca na web, por exemplo bibliaonline.com.br
   ou bible.com, versões ARA/NVI/NAA) e anote os versículos exatos. Não confie na memória.
4. Escreva o roteiro em `roteiros/<slug_curto>.json` no formato abaixo.
5. Rode `python ferramentas/validar_roteiro.py roteiros/<arquivo>.json` e corrija até dar OK.
6. **Revise você mesmo, frase por frase, contra o texto bíblico**: nenhum detalhe inventado
   (nomes, números, falas, ordem dos fatos). Interpretações devem ser leves e comuns a todas
   as tradições cristãs.
7. Remova a linha usada de `pautas/biblico.txt` (se veio da fila).
8. Commit e push (`git add roteiros pautas && git commit -m "roteiro: <título>" && git push`).
9. Dispare a produção (REST, nunca GraphQL):
   ```
   gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/produzir.yml/dispatches \
     -X POST -f ref=main -f 'inputs[canal]=biblico' \
     -f 'inputs[roteiro]=roteiros/<arquivo>.json' -f 'inputs[estilo]=pintura'
   ```
10. Acompanhe a execução até terminar (`gh api repos/erickaugustoo7-cloud/estudio-ia/actions/runs/<id>`,
    consultando a cada 30–60 s; leva ~15–25 min). Se falhar, leia o log
    (`gh run view <id> --log | tail -80`), corrija se o problema for o roteiro e dispare de novo
    **uma** vez. O próprio workflow envia o vídeo ao Telegram do Eric e abre a Issue de aprovação.
11. Termine com um resumo curto: título, pauta, duração (linha `[narrador]` do log) e link da Issue.

Nunca publique nada, nunca mexa em segredos/tokens, nunca altere outros arquivos do sistema
sem necessidade. Se algo fora do roteiro estiver quebrado, apenas relate no resumo.

## Foco editorial (o que funciona no canal)

- **Jesus é o personagem principal**, em um momento de **emoção forte** nos Evangelhos:
  lágrimas, toque, olhar, perdão, cruz, ressurreição. Mostre como Jesus trata as pessoas e o que
  isso diz sobre como ele trata *você*. Os dois vídeos que o TikTok classificou como
  "excepcionalmente envolventes" foram "Jesus chorou" e "O ladrão na cruz".
- Evite histórias longas do Antigo Testamento: prendem nos 2 s mas ninguém termina e quase ninguém curte.
- Linha cristã ampla, sem doutrina de denominação. Nada de: batismo infantil, Maria/santos,
  dons espirituais, dízimo, escatologia detalhada, sábado, política, prometer milagre/prosperidade,
  pedir dinheiro, medo ou culpa como gancho.
- Parafraseie; cite literalmente no máximo 2 versículos curtos. Sempre diga a referência.

## Perfil do público (TikTok, 28/10–03/11)

- **73% de quem assiste e 79% dos seguidores são homens** — incomum no nicho (o topo do nicho em
  português fala com mulheres). Os vídeos que mais funcionam mostram Jesus com homens que falharam,
  lutaram ou foram restaurados (Pedro, o ladrão na cruz, o pai do filho pródigo, Zaqueu).
- Priorize personagens e situações com que esse público se identifica: culpa, fracasso, recomeço,
  ser pai, sustentar a família, coragem, ansiedade com trabalho e dinheiro (sem prometer prosperidade).
- Nas orações guiadas, alterne temas universais (sono, ansiedade, saúde) com temas que falam com
  homens ("oração do pai pela família", "para quem carrega o peso de sustentar a casa").

## Estrutura que retém (dados reais do canal)

1. **Gancho (cena 1, só ele, ≤ 12 palavras):** loop aberto, fala com o mistério ou com "você".
   Ex. vencedor: "Existe um versículo de apenas duas palavras que revela o coração de Deus."
   Outros: "Teve um dia em que Jesus não disse nada. Só olhou. E um homem desabou."
   Nunca comece com saudação, nome do canal ou contexto.
2. **2ª frase (até ~6 s): mini-resposta concreta + nova pergunta.** É aqui que o canal mais perde
   gente (o "Jesus chorou" segura o dobro dos outros no segundo 6). Ex.: "Esse homem era Pedro.
   Está em Lucas, capítulo vinte e dois. Mas o que veio depois é ainda mais bonito."
   Proibido usar a 2ª frase para contexto ("Naquela época...", "Era o dia...").
3. **História** com personagem, problema e virada, frases curtas, ritmo falado. Nada de tom de
   aula ("Descubra", "Vamos entender", "Neste vídeo", "explicado").
4. **Revelação mais forte perto do fim** (prometida no começo).
5. **Aplicação curta e pessoal** ("E não desistiu de você.").
6. **Pedido final** (alterne para medir compartilhamentos):
   - execução das **05h** (vídeo da manhã): "Salve este vídeo para ouvir de novo quando precisar, e siga para receber uma palavra de fé todos os dias."
   - execução das **17h** (vídeo da noite): "Envie para alguém que precisa ouvir isso, e siga para receber uma palavra de fé todos os dias."
   - O vídeo da manhã pode ser uma oração para começar o dia ou uma história; o da noite, história ou oração da noite.

- **Tamanho: 165–195 palavras** (dá ~75–90 s; precisa passar de 60 s). Números por extenso
  ("vinte e dois"). Sem emojis nem listas na narração.
- **8 ou 9 cenas.** A cena 1 é só o gancho e precisa da imagem MAIS FORTE do vídeo (é a capa no
  feed): uma cena concreta, luminosa e com contraste, ligada ao gancho (ex.: uma vela acesa sobre uma
  Bíblia aberta, um homem de costas diante de uma cruz ao pôr do sol, mãos estendidas para a luz).
  Varie de vídeo para vídeo. Nas outras, troque de imagem a cada 1–2 frases.
- **Os trechos das cenas, juntados com um espaço, devem ser idênticos à narração.**

## Imagens (prompt_imagem, em inglês)

Pintura a óleo clássica, era bíblica, luz dourada. **Pessoas sempre de costas, em silhueta ou na
sombra — nunca o rosto de Jesus.** Descreva a cena concreta do trecho (lugar, luz, objetos).
Ex.: "a man in ancient robes seen from behind warming his hands at a small fire in a stone
courtyard at night, other shadowy figures around". O estilo é acrescentado automaticamente.

## Texto na tela e legenda

- `gancho_tela`: até 7 palavras, complementa a fala (não repete), sem emoji, **sem "Parte N"**.
- `legenda`: 1ª linha = oração curta em 1ª pessoa (≤ 10 palavras, 1–2 emojis), ex.
  "Senhor, obrigado por não desistir de mim 😭🙏"; 2ª linha = referência; 3ª = convite para comentar
  "Amém" e enviar/salvar. Sem hashtags dentro da legenda.
- `hashtags`: 4 específicas do tema (as fixas do canal entram sozinhas).
- `fontes`: as referências exatas usadas.

## Formato do arquivo

```json
{
  "titulo": "O olhar de Jesus para Pedro",
  "gancho_tela": "Ele não disse nada. Só olhou.",
  "estilo": "pintura",
  "narracao": "<texto completo>",
  "cenas": [
    {"trecho": "<gancho>", "busca_imagem": "", "prompt_imagem": ""},
    {"trecho": "<frase(s)>", "busca_imagem": "2-4 english keywords", "prompt_imagem": "<english prompt>"}
  ],
  "legenda": "Senhor, ... 🙏\nLucas 22:61\nComente \"Amém\" e envie para alguém que ...",
  "hashtags": ["#Jesus", "#Pedro", "#perdão", "#amordeDeus"],
  "fontes": ["Lucas 22:54-62", "João 21:15-17"]
}
```

Exemplos aprovados: `roteiros/jesus_chorou.json`, `roteiros/ladrao_na_cruz.json`, `roteiros/pedro_olhar.json`.

## Formato "oração guiada com Jesus" (quando a pauta indicar)

Indicado pelo Radar (04/11): orações em 2ª pessoa são o formato que mais viraliza e mais gera
comentários no nicho em português. **A oração vem PRIMEIRO** (decisão do Eric após assistir ao 1º
teste: quem chega pelo gancho quer orar logo). A explicação vem depois, como recompensa prometida.
Estrutura (mesmas regras de tamanho, cenas e validação):
1. Gancho pessoal (cena 1), sem promessa nem "Deus mandou te dizer": ex. "Se você vai dormir com o
   coração pesado hoje, faça essa oração comigo."
2. Convite + loop aberto: "Feche os olhos e repita. E no final, eu te conto [a frase que Jesus
   disse / o que Jesus fez] para [momentos assim]."
3. Oração curta em 1ª pessoa (5–7 frases simples, 3 cenas), terminando em "Amém." Sem pedir
   dinheiro, sem prometer cura/milagre.
4. Ponte: "Sabe [isso] que você acabou de pedir? Jesus [prometeu/fez] isso…"
5. A cena de Jesus (2–3 frases) + a referência bíblica.
6. Fechamento: "Se você orou comigo, escreva Amém nos comentários." + enviar/salvar.
Legenda: 1ª linha = a oração resumida; depois a referência; depois "Escreva Amém 🙏".
**Texto na tela (`gancho_tela`) das orações: sempre "Faça essa oração …"** (decisão do Eric — "Ore
isso" soa seco e ficou ruim). Ex.: "Faça essa oração antes de dormir", "Faça essa oração ao
acordar", "Faça essa oração pela sua família". Na narração, o convite segue o mesmo tom:
"Faça essa oração comigo agora." / "Feche os olhos e faça essa oração comigo."
Exemplo aprovado: `roteiros/oracao_dormir_paz.json`.
