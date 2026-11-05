# Manual dos vídeos curtos — Mensageiro de Fé (10 por dia)

Lido pela sessão agendada que escreve o lote diário de curtos (9–16 s, texto fixo na tela, sem
narração; o Eric coloca um som popular do TikTok ao postar). Português do Brasil.

## Passo a passo

1. `git pull`. Leia este manual, `docs/radar/RADAR.md` (se existir) e liste `roteiros_curtos/`
   para **não repetir** versículos/frases nem cenas usados nos últimos 30 dias (veja `git log --since="30 days ago" -- roteiros_curtos`).
2. Escreva **10 arquivos** novos em `roteiros_curtos/<slug>.json`:
   - **6 versículos bíblicos** (texto fiel à Bíblia — confira na busca na web, versão NVI/NAA/ARA; até ~35 palavras);
   - **4 mensagens motivacionais cristãs** escritas por você (originais, nunca frases de autores conhecidos;
     até ~30 palavras), com fundamento bíblico. Se ela se apoiar num versículo, use
     `"referencia": "Inspirado em <livro cap:vers>"`; senão deixe `"referencia": ""`.
3. Commit e push. Dispare **um único** lote (REST, nunca GraphQL):
   ```
   gh api repos/erickaugustoo7-cloud/estudio-ia/actions/workflows/curto.yml/dispatches -X POST -f ref=main \
     -f 'inputs[roteiros]=roteiros_curtos/a.json roteiros_curtos/b.json ...'
   ```
4. Acompanhe até terminar (~30–60 min). Se algum curto falhar, corrija o arquivo e dispare só ele de novo.
5. Resumo final: os 10 títulos, quais deram aviso e os links das Issues.

## Regras de conteúdo

- Público ~75% masculino: força, coragem, cansaço, recomeço, família, trabalho, ansiedade,
  confiança no tempo de Deus, perdão. Sem prometer prosperidade, cura ou milagre; sem pedir dinheiro;
  sem política; sem medo/culpa; sem "Deus mandou te dizer".
- Mensagens motivacionais: frases curtas, concretas, que alguém mandaria para um amigo.
- **Variedade obrigatória dentro do lote:** 10 cenas diferentes. Alterne natureza (mar, montanha,
  tempestade, deserto, floresta, céu estrelado, nascer/pôr do sol), animais (leão, águia, cordeiro —
  no máximo 2 animais por lote), objetos (vela, Bíblia, cruz ao pôr do sol, estrada, porta aberta)
  e pessoas **sempre de costas ou em silhueta**.
- Distribua o tom ao longo do dia (o Eric posta na ordem das Issues): 3 de manhã (começo do dia,
  força), 4 à tarde (cansaço, trabalho, confiança), 3 à noite (paz, descanso, gratidão).

## Formato do arquivo

```json
{
  "titulo": "Nosso refúgio",
  "versiculo": "Deus é o nosso refúgio e a nossa fortaleza, auxílio sempre presente na adversidade.",
  "referencia": "Salmo 46:1",
  "prompt_imagem": "<cena em inglês: assunto principal, lugar, luz>",
  "estilo_imagem": "ultra realistic cinematic photography, dramatic golden light, deep shadows, film grain, vertical 9:16, no text, no letters, no watermark",
  "regra_pessoas": "any person only seen from behind or in silhouette, face never visible",
  "legenda": "Senhor, sê o meu refúgio hoje 🙏⛈️\nSalmo 46:1\nComente \"Amém\" se essa palavra é para você.",
  "hashtags": ["#Salmo46", "#fé", "#versiculododia", "#Deus"]
}
```
O campo `versiculo` é o texto que aparece na tela (para mensagens motivacionais, a própria mensagem).
