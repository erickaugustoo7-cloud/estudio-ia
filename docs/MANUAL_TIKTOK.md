# Manual do roteirista — Curtos do TikTok (Mensageiro de Fé)

Dois por dia. Vão para o Telegram do Eric, que posta à mão no TikTok (e, se aprovar, sai no Facebook).
**Não vão para Instagram nem YouTube** (o Instagram marcou a conta por "conteúdo não original" em 12/11).

## Por que este formato (dados do perfil, 13/11)
- Os vídeos que bombaram (8–12 mil views) têm **imagem cinematográfica forte, quase sem texto** no primeiro quadro.
- Os que ficaram em ~70 views tinham a **faixa amarela com frase** no topo e o mesmo molde repetido.
- Shorts de 9–15 s sobre sono/paz foram assistidos mais de uma vez (156% de retenção no YouTube).

## Regras
- `"tipo": "tiktok"`, vertical, **4–7 cenas, 35–75 palavras** (15–30 s), `"plataformas": ["facebook"]`.
- **Gancho falado na 1ª frase** (curiosidade ou dor real): "Jesus escreveu no chão duas vezes. E ninguém sabe o quê."
  `gancho_tela`: 1–5 palavras (aparece só nos 2,6 s iniciais, sem faixa, sobre a imagem).
- Uma virada no meio (o detalhe que quase ninguém sabe, ou a promessa bíblica), final curto.
- **Última cena pede para seguir:** "Siga o Mensageiro de Fé para mais…" (o validador cobra "sig").
- No máximo **1 cena animada** (a do gancho, para ter movimento no 1º segundo). Imagens no Kaggle
  (`"fonte_imagem": "kaggle"`, `"opcoes_imagem": 2`), regras de imagem de `docs/REGRAS_FIXAS.md`.
- Nada inventado; citação literal curta com referência. Almeida (domínio público) para citar.
- Manhã: curiosidade bíblica (série "O que quase ninguém sabe"). Tarde: oração curta de consolo, em 1ª pessoa.
- `legenda` termina com uma pergunta para comentar (comentário ajuda a distribuição). 5 hashtags.
- Modelo aprovado: `roteiros_animados/tiktok_jesus_escreveu_no_chao.json`.

## Passo a passo
1. `git pull`; pauta = primeira linha não comentada de `pautas/tiktok.txt` (apague-a). Se acabar, tema novo
   que ainda não exista em `roteiros_animados/`.
2. Escreva `roteiros_animados/tiktok_<slug>.json` e rode `python ferramentas/validar_animacao.py <arquivo>` até **OK**.
3. Commit/push (e-mail noreply) e dispare pela API REST:
   `gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/kaggle-wan.yml/dispatches -X POST -f ref=main -f 'inputs[roteiro]=roteiros_animados/tiktok_<slug>.json' -f 'inputs[maquina]=NvidiaTeslaT4'`
4. Confira só que entrou na fila e termine. Nunca cancele uma produção que já chegou ao Kaggle. Nunca publique nada.
