# SFT agêntico do Bee-1G — decaído (final 20B) × platô (marco_15B), 3 sementes (2026-09-24)

> Pergunta: o checkpoint de melhor loss (decaído, ~2,6× mais curvo pela densidade de solução) é pior ponto de
> partida para SFT, como o 2609.08966 mediu num MoE de 30B? Medido no pod RTX 5090, receita do C-full do
> 350M (LoRA r16/α32, lr 1,2e-3, 698 passos, lote efetivo 16, corpus `treino_e19c_neg_uteis.jsonl`), régua
> agêntica com a config de referência (holdout balanceado, 536 tool / 268 texto) + capacidades com `--chat`.
> Logs em `docs/logs-sft1g-2026-09-24/`.

## 🔴 Defeito de receita achado antes de valer: tokens de chat NÃO treinados no pré-treino

A primeira rodada (s42) deu **0% de execução no decaído** e 58,8% no platô. Lidas as saídas cruas (§2e):
o decaído emitia **a chamada certa seguida de " Mitgl"** no lugar de `<|im_end|>`, nunca parava e virava
JSON inválido. Causa: `<|im_start|>`, `<|im_end|>` e `<|pad|>` nunca aparecem no corpus de pré-treino;
só o weight decay mexeu nas linhas deles a partir da mesma inicialização. No checkpoint final as três
**diferem em ~2×10⁻⁵ (norma 0,55)**; com embedding atado ao lm_head, **os três logits empatam** e LoRA
sozinho não treina embedding. O platô também sofria: terminador certo 44,7%, especial errado 41%.

**Correção:** `sft_qlora.py --tokens-treinaveis "<|im_start|>,<|im_end|>"` (PEFT `trainable_token_indices`,
só essas duas linhas) + `loss_type="nll"` (mesma conta do `chunked_nll` padrão do TRL 1.9, que quebrava
com o wrapper). Aplicada **igual nos dois braços**; muda a receita em relação ao C-full do 350M (declarado).
Sonda de 150 passos antes da rodada completa (§2v): terminador certo **0% → 97,5%**. Rodada completa:
**94–97% de terminador certo, 0 especial errado** em todos os braços. Resultados sem a correção guardados
como `*-s42-semtokens`.

Guarda de versão: com `transformers` 5.14.1 (fixado na receita) o 1G reproduziu o bpb de 5.16.1 (0,9370).

## Resultado — régua agêntica (exec_ok sobre 536; over-call sobre 268)

| braço | s42 | s43 | s44 | **média ± dp** | over-call | under-call |
|---|---:|---:|---:|---:|---:|---:|
| **final (decaído)** | 396 | 365 | 368 | **376,3 ± 17,1 (70,2%)** | 42,3 (15,8%) | 77,3 |
| **15B (platô)** | 371 | 378 | 316 | **355,0 ± 34,0 (66,2%)** | 48,7 (18,2%) | 58,0 |
| *350M C-full, mesma receita (4090/5070)* | | | | *~369–372 (≈69%)* | *~14%* | |

**Veredito: indistinguível.** Final +21 casos (+4,0 pp), t ≈ 1,0 — a dispersão entre sementes (17 e 34
casos, **3–6 pp**) é maior que a do 350M (4,4 pp no gate #3). A **disposição de chamar** oscila muito com a
semente nos dois braços (under-call 37–95), o que aponta para limiar (G-C3), não capacidade.

⚠️ **Duas leituras intermediárias que as sementes desfizeram (§2x):** com s42 "o 1G passa o 350M
(73,9% × 69%)"; com s42+s43 "o decaído oscila mais". Com 3 sementes: o 1G **empata** com o 350M na
execução agêntica, e quem desabou numa semente foi o platô.

## Capacidades (média ± dp, 3 sementes, `--chat`)

| capacidade | final | 15B | 350M C-full | piso | base 1G (sem SFT) |
|---|---:|---:|---:|---:|---:|
| tradução en→pt chrF2 | **24,2 ± 6,5** | 16,2 ± 3,2 | 27,5 ± 6,1 | 21,5 | 50,85 |
| tradução pt→en chrF2 | 15,2 ± 4,2 | 13,8 ± 1,8 | 19,1 ± 1,4 | 22,7 | 40,41 |
| sentimento | 44,8 ± 3,2 | 50,1 ± 0,2 | 56,8 ± 2,1 | 79,0 | 43,5 |
| resumo — cobertura | **82,7 ± 15,4** | 57,5 ± 6,6 | 72,8 ± 7,0 | — | 88,0 |
| resumo — útil | 0,0 | 0,0 | 0,0 | 51,3 | 0,0 |
| atendimento — JSON válido | 35,1 ± 18,9 | 27,3 ± 20,4 | 30,9 ± 7,6 | — | 0,0 |
| atendimento — útil | 0,0 | 0,0 | 0,0 | 60,4 | 0,0 |
| IFEval estrito/instrução | 30,3 ± 0,3 | 31,0 ± 0,2 | 29,2 ± 0,8 | — | 30,2 |

- **O SFT agêntico destrói a tradução no 1G como no 350M** (§2z): en→pt 50,85 no base → 24,2/16,2
  (piso de copiar 21,5); pt→en abaixo do piso nos dois braços. O corpus do C-full não protege tradução.
- **Nas capacidades o decaído tende a preservar mais** (en→pt +8,0, t≈1,9; resumo-cobertura +25, t≈2,6),
  o **oposto** do que a previsão da densidade sugeria. Com 3 sementes e dispersões grandes, "tende".

## O que isto diz sobre a densidade (2609.08966)

O decaído é ~2,6× mais curvo (medido, corrigido pela escala dos pesos), e **isso não virou SFT pior**
neste regime — LoRA de 698 passos num 1B denso. Refutação vale para esta receita e este holdout (§2q):
o artigo mediu SFT completo num MoE de 30B; LoRA mexe num subespaço pequeno e pode ser insensível à
curvatura global. **Decisão prática: o pós-treino parte do final (decaído)** — empate na régua agêntica,
tendência melhor nas capacidades, e é o checkpoint de menor loss.

## Próximo passo sugerido

G-C1/G-C3 nos 6 adapters (US$ 0, ~15 min no pod): a oscilação de under-call entre sementes (37–95) tem
a assinatura de limiar que no 350M a temperatura estabilizou; se estabilizar aqui, o "empate com o 350M"
pode virar ganho só com calibração. E a tradução precisa de corpus próprio no SFT (E20/E21 do 350M:
adapter separado dobrou o alvo sem custo agêntico).

## G-C1 / G-C3 nos 6 adapters (US$ ~0,25, pod)

Artefatos: `calibracao-agentica-1g-{final,15B}-5090.json`, `calibracao-poshoc-1g-5090.json`.

| | final (3 sementes) | 15B (3 sementes) | 350M C-full (ref.) |
|---|---|---|---|
| Choice "qual ferramenta" acc · ECE · AUROC | **0,92 · 0,04–0,05 · 0,92–0,95** | 0,86–0,89 · 0,06–0,09 · 0,88–0,90 | 0,92 · 0,04 · 0,94 |
| "chamar?" AUROC (p vs classe) | 0,91–0,92 | 0,89–0,92 | 0,90 |
| fim-a-fim AUROC · acc no quartil confiante | **0,75–0,77 · 0,93–0,97** | 0,71–0,77 · 0,89–0,93 | 0,70–0,74 · 0,90–0,94 |
| temperatura (2 dobras) → ECE da confiança | T 1,8–2,0 → **0,03–0,06** | T 1,6–2,2 → 0,02–0,07 | T ≈2 → 0,02–0,04 |
| temperatura transferida entre sementes | T 1,95–2,19, ECE 0,03–0,07 | T 1,78–2,04 | idem |

1. **A escolha de ferramenta do decaído é melhor e mais calibrada que a do platô, nas 3 sementes** — a
   primeira diferença consistente entre os pontos de partida (acc 0,92 × 0,86–0,89; AUROC 0,92–0,95 ×
   0,88–0,90). Soma-se às capacidades: tudo aponta para o final.
2. **A temperatura (T ≈ 2) calibra a confiança de novo, e transfere entre sementes** — a mesma lei do 350M.
3. 🔴 **O limiar NÃO estabiliza a disposição de chamar entre sementes.** O AUROC é igual nas três (o modelo
   ordena os casos igual), mas a escala do p_call muda com a semente: com τ fixo em 0,10 no decaído o
   under-call vai a 4,9 / 9,9 / 11,2% e o over-call a 31 / 22 / 24% — a dispersão só muda de lado; com a
   isotônica transferida a s42 dispara (over 41%). **A oscilação é da semente, não do corte**: estabilizar
   pede mais dado de negativo/positivo ou mais passos, não pós-processamento.
4. Teto do limiar movido (τ 0,15, estimativa — no 350M o realizado igualou o teto): **+2,2 a +3,2 pp** de
   execução no decaído, pagando **+1,5 a +6 pp** de over-call. Ganho pequeno; decisão de custo, não de método.

**Leitura:** o 1G pós-SFT decide **qual** ferramenta tão bem quanto o 350M e roteia pela confiança melhor
(AUROC fim-a-fim 0,75–0,77); a decisão de **se** chamar continua sendo o elo fraco — agora com a informação
nova de que no 1G ela varia com a semente de um jeito que calibração não conserta. Coerente com o estudo
System One (REFLEX/AgentAbstain): escolher calibra, decidir agir não.
