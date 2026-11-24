# Regras fixas do canal Mensageiro de Fé — decisões do Eric (valem para TODO roteiro e vídeo)

Antes de produzir qualquer vídeo, confira item por item. Se algum não for cumprido, NÃO produza.

## Imagem e animação
1. **Nenhum rosto, de ninguém** (Jesus, Maria, discípulos, servos, convidados, anjos). O vídeo deforma rostos.
2. **Pessoas não são o assunto da cena.** No máximo: mãos/braços em close, ou figuras minúsculas ao longe.
   Nada de "homem de costas", "mulher de véu", "casal", "discípulos" como figura principal — foi isso que gerou
   rostos e personagens virando para a câmera.
3. Nos prompts de imagem NÃO escreva "no people", "nobody", "silhouettes" (o gerador desenha gente quando lê
   essas palavras); descreva só o lugar e os objetos. A história é contada por **objetos e ambiente**: potes, mesa, lamparinas, pães, redes, barco, água, porta, estrada,
   céu, luz. Falas de personagens aparecem com uma imagem de ambiente/objeto ligada a elas.
4. **Nada moderno**: sem vidro, garrafa, taça, luz elétrica, construção moderna. Só barro, pedra, madeira, tecido.
5. Movimento só do ambiente: fogo, luz, água, vento em tecidos e folhas, câmera lenta. Nada de gente se mexendo.
6. Estilo das animações (aprovado 07/11): **cinematográfico realista**, planos abertos e altos, luz volumétrica,
   figuras minúsculas ao longe, arquitetura certa da época. Nunca "cartoon" infantil, objetos com rosto ou mascotes.
   Se um clipe continuar com defeito depois de refeito, ele é trocado pela imagem aprovada com zoom lento.

## Roteiro
7. História com contexto: onde, por que importava na época, falas do texto bíblico, detalhes concretos, virada,
   significado para "você". Nada inventado; versículos conferidos na web.
8. Animações: 8–12 planos, 100–150 palavras, cada plano 6–17 palavras.
9. Narração natural (sem aceleração), legenda palavra a palavra, música baixa, assinatura "MENSAGEIRO DE FÉ",
   selo da série quando houver.

## Processo
10. Nada é publicado sem a aprovação do Eric (etiqueta "aprovado" na Issue). A rotina diária produz sozinha, mas só
    depois de o roteiro passar pelo validador abaixo.
11. Rodar `python ferramentas/validar_animacao.py roteiros_animados/<arquivo>.json` — tem que dar OK.

## Títulos dos Shorts (dados do canal, 17/11)
12. Shorts de história/curiosidade bíblica têm mediana de 456 views; orações curtas, 173; títulos abstratos de 2–4
    palavras ("Terei confiança", "Pausa no meio do dia", "Coragem não é não ter medo") ficaram com 3–7 views.
    Todo título de Short precisa ter **uma pergunta, um fato surpreendente ou uma história com personagem**
    (ex.: "O diabo citou o Salmo 91 para Jesus", "O pão dos pobres nas mãos de Jesus", "Para quem está esperando
    uma resposta de Deus"). Nunca título abstrato curto, nunca só hashtags/emoji.
13. Volume: no máximo 3 Shorts por dia no YouTube do Mensageiro, todos no formato acima. Qualidade > quantidade.

## Ponte Short → vídeo longo (decisão do Eric, 17/11)
14. O vídeo longo do dia é, sempre que possível, a **versão completa do tema de um Short que já funcionou**
    (fila em pautas/pontes.txt). O título do longo retoma o gancho do Short, e a Issue/Telegram lembram o Eric de
    ligar o Short ao longo em "Vídeo relacionado".

## Shorts e Short isca — retenção (estudo do Eric, 18/11)
15. **Gancho no 1º segundo, dito E escrito na tela:** 5–10 palavras com o fato surpreendente ou a dor, nunca saudação
    ("Olá", "Você sabia…?" genérico, nome do canal). A maioria assiste o começo sem som: o gancho precisa estar no
    `gancho_tela`/texto do topo com as mesmas palavras.
16. **Primeira imagem = a mais forte** do vídeo (movimento ou rosto/emoção), nunca paisagem parada de abertura.
17. **Entrega antes do fim:** a resposta prometida chega até ~70% do tempo; a última frase **volta para o começo**
    (loop: quem chega ao fim quer ver de novo) ou abre a pergunta que o vídeo longo responde.
18. **Short isca — Mensageiro (decisão do Eric, 23/11):** o trecho é a frase de CONSOLO mais forte da oração, falando
    direto com a pessoa ("Se você está esperando uma resposta de Deus, ouça isto…"), 12–45 palavras; título e
    `texto_topo` no mesmo tom ("PARA QUEM ESTÁ ESPERANDO"). NADA de mistério ("o detalhe que ninguém percebe",
    "a palavra escondida"): rendeu 10–100 views contra ~1.000 dos Shorts de consolo. Antes de Nós: continua laço aberto.
19. **Uma chamada só no fim**, curta ("Siga para a parte 2", "A oração completa está no vídeo abaixo").
