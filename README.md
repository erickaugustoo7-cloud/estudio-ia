# Estúdio IA — empresa de conteúdo operada por agentes

Dois canais (📖 **Bíblico** e 🚀 **Espaço & Como Funciona**) produzidos por agentes de IA. Tudo roda no **GitHub Actions**, sem custo fixo: você alimenta pautas, recebe os vídeos no Telegram, aprova o Instagram com um toque e posta no TikTok manualmente.

## Como funciona

```
Diretor ─► Roteirista ─► Revisor (fatos + compliance) ─► Narrador (voz) ─► Visual (imagens)
   ─► Montador (HyperFrames, com FFmpeg de reserva) ─► Telegram (vídeo + legenda) + Issue de aprovação
   ─► você aprova ─► Instagram automático · TikTok manual pelo celular
```

| Agente | O que faz | Ferramenta | Custo |
|---|---|---|---|
| Diretor | Pega a próxima pauta da fila ou cria uma nova sem repetir | LLM gratuito (ver abaixo) | grátis |
| Roteirista | Narração de ~70 s com gancho, cenas, legenda, hashtags | LLM gratuito | grátis |
| Revisor | Checa fatos, linha editorial e regras das plataformas; corrige ou bloqueia | LLM gratuito | grátis |
| Narrador | Voz neural pt-BR + tempo exato de cada palavra | edge-tts | grátis |
| Visual | Espaço: fotos da NASA (domínio público). Bíblico: imagens por IA | NASA API / Pollinations | grátis |
| Montador | Vertical 1080×1920: gancho animado na abertura, transições suaves, zoom lento, legenda "pop" palavra a palavra, barra de progresso, música opcional | HyperFrames (HTML + GSAP → MP4, open source da HeyGen); FFmpeg como reserva automática | grátis |
| Entregador | Manda o vídeo e a legenda pronta para o seu Telegram | Bot do Telegram | grátis |
| Publicador | Publica o Reel no Instagram após sua aprovação | API oficial do Instagram | grátis |

**Custo: zero.** Os textos usam LLMs com plano gratuito, em cadeia com fallback automático:

1. **Groq** — `openai/gpt-oss-120b` (1.000 pedidos/dia grátis; cada vídeo usa 2–3)
2. **Google Gemini** — `gemini-2.5-flash` pelo AI Studio (plano gratuito)
3. **Pollinations** — sem chave nenhuma, último recurso

Se um provedor estiver sem chave, fora do ar ou no limite, o próximo assume. Troque a ordem com a variável `LLM_PROVEDORES` (*Settings > Secrets and variables > Actions > Variables*) e o modelo com `GROQ_MODEL` / `GEMINI_MODEL`. Actions em repositório privado tem 2.000 min/mês grátis; cada vídeo leva ~5–8 min com HyperFrames (4 vídeos/dia ≈ 800 min/mês). Se apertar, troque `motor_video` para `ffmpeg` no `canais/*.yaml` (~3 min por vídeo).

**Por que o TikTok é manual:** a API do TikTok só publica em modo privado até o app passar por uma auditoria deles. A alternativa paga (Blotato) usa um app já auditado. Se um dia valer a pena automatizar, só o módulo `publicador.py` muda.

## Configuração (uma vez só)

### 1. Contas
- Instagram: transforme cada conta em **conta profissional (Criador ou Empresa)**.
- TikTok: contas normais. Rótulo **"Conteúdo gerado por IA"** sempre ligado ao postar.

### 2. Bot do Telegram (2 min)
1. No Telegram, fale com **@BotFather** → `/newbot` → guarde o token.
2. Mande qualquer mensagem para o seu bot.
3. Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` e copie o número em `"chat":{"id": ...}`.

### 3. App da Meta para o Instagram (grátis, ~15 min)
1. Em developers.facebook.com, crie um app do tipo **Empresa** e adicione o produto **Instagram** → *API com login do Instagram*.
2. Em **Funções do app**, adicione as duas contas do Instagram como **Testadores do Instagram** e aceite o convite no Instagram (*Configurações > Apps e sites > Convites de teste*).
3. Em *Gerar tokens de acesso*, gere um token para cada conta (permissões `instagram_business_basic` e `instagram_business_content_publish`). Esse token já é de longa duração (60 dias).
4. O app pode ficar em **modo de desenvolvimento**: como só publica nas suas próprias contas, não precisa de revisão da Meta.

### 4. Chaves de LLM (grátis, sem cartão)
- **Groq:** console.groq.com → *API Keys*.
- **Gemini:** aistudio.google.com → *Get API key*. No plano gratuito o Google pode usar os textos para melhorar os produtos dele — sem problema aqui, já que os roteiros vão ser públicos.
Uma das duas já basta; com as duas, o sistema fica mais resistente a limites.

### 5. Repositório
1. Crie um repositório **privado** no GitHub e suba esta pasta.
2. Em **Settings > Secrets and variables > Actions**, crie:

| Secret | Valor |
|---|---|
| `GROQ_API_KEY` | chave do Groq |
| `GEMINI_API_KEY` | chave do Gemini (opcional, reserva) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | token do bot e o seu chat id |
| `IG_TOKEN_BIBLICO` / `IG_TOKEN_ESPACO` | token de cada conta do Instagram |
| `GH_PAT` | opcional — token pessoal do GitHub (*Secrets: read and write*) para renovar os tokens do Instagram sozinho todo mês |
| `POLLINATIONS_API_KEY` | opcional — limites maiores de imagem (enter.pollinations.ai) |

3. Em **Settings > Actions > General > Workflow permissions**, marque *Read and write permissions*.

## Operação diária

- **Pautas:** escreva uma por linha em `pautas/biblico.txt` e `pautas/espaco.txt`. Fila vazia → o Diretor cria sozinho.
- **Produção automática:** 2 vídeos por canal por dia (~08:47 e ~16:47). Para mudar, edite o `cron` em `.github/workflows/produzir.yml`.
- **Produção sob demanda:** aba *Actions > Produzir vídeos > Run workflow* (dá para passar uma pauta específica).
- **Telegram:** cada vídeo chega como vídeo tocável + mensagem com a legenda pronta + link da Issue.
- **TikTok:** salve o vídeo do Telegram, poste no app e cole a legenda.
- **Instagram:** na Issue (app do GitHub), etiqueta `aprovado` → publica o Reel e manda o link no Telegram. Etiqueta `rejeitado` → descarta. Para mudar a legenda, edite `texto_post` no bloco de dados antes de aprovar.
- **Validade:** os vídeos ficam 14 dias guardados no Actions; aprove dentro desse prazo.
- **Tokens do Instagram:** renovados todo dia 1º pelo workflow *Renovar tokens* (com `GH_PAT`). Sem `GH_PAT`, gere um token novo a cada ~60 dias.
- **Música:** coloque `.mp3` livres de direitos em `assets/musica/biblico` e `assets/musica/espaco` (ex.: Biblioteca de Áudio do YouTube). Sem arquivos, o vídeo sai só com narração.

## Ajustes finos (sem mexer em código)

Tudo de cada canal está em `canais/*.yaml`: persona, linha editorial, o que é proibido, voz, velocidade, tamanho do roteiro, estilo visual, motor de vídeo, CTA e hashtags.

**Visual do vídeo (HyperFrames):** a composição é gerada em `estudio/agentes/montador_hf.py`. Cores de destaque e fonte de título por canal ficam em `TEMAS` (ou num bloco `tema:` no YAML, ex.: `tema: {destaque: "#FF7A00"}`). Para ver a composição de um vídeo, abra `saida/<pasta>/hf/` e rode `npx hyperframes preview`.

Vozes pt-BR úteis: `pt-BR-AntonioNeural`, `pt-BR-FranciscaNeural`, `pt-BR-ThalitaMultilingualNeural`.

## Teste local

```bash
pip install -r requirements.txt   # precisa de ffmpeg instalado
npm install                       # HyperFrames + GSAP (precisa de Node 22+ e Chrome)
export GROQ_API_KEY=...   # ou GEMINI_API_KEY
python -m estudio.produzir --canal espaco --sem-envio --sem-issue
```
O resultado fica em `saida/`.

## Regras que o sistema já respeita
- Lembrete do rótulo **"gerado por IA"** em toda Issue para o TikTok.
- Vídeos com mais de 60 s (requisito do Creator Rewards); o Revisor avisa na issue quando não passa.
- Nada sai sem aprovação humana; se uma publicação falhar e você aprovar de novo, não duplica o que já saiu.
