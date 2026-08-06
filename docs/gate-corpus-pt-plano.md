# Gate de corpus: o português puro melhora o Bee? — plano (2026-08-06)

Experimento que decide se vale trocar de corpus **antes** de pagar por modelo maior. Vem
direto de [`gate-tucano.md`](gate-tucano.md): o Tucano-160m, do mesmo tamanho do Bee, é
1,88× melhor em texto limpo com ~200B tokens 100% PT contra os nossos ~6,9B de PT.

## ⚠️ O confundimento que este desenho tem que resolver

O corpus novo muda **duas coisas ao mesmo tempo** em relação ao antigo:

1. **Pureza de idioma** — 100% PT contra ~70% PT + 20% EN + 10% código
2. **Filtro de qualidade** — top 60% pelo classificador FineWeb-Edu-PT

Rodar "antigo × novo" e ver o novo ganhar **não diria qual das duas causou**. E as duas têm
custos futuros muito diferentes: pureza de idioma é de graça (é só não misturar), enquanto
filtrar mais forte custa jogar corpus fora.

⭐ **Metade da separação já está medida.** O gate pareado de 2026-08-05 isolou o filtro
sozinho: **+1,6%**, real (o IC exclui zero em 4 pontos) mas **não cresce com escala**. Então
se o corpus novo ganhar muito mais que 1,6%, o excedente é atribuível à pureza de idioma.

## Os braços

Três braços, **mesmo modelo (Bee-150M), mesmo orçamento de tokens, mesma configuração** —
a única variável é o corpus.

| braço | corpus | testa |
|---|---|---|
| **1. antigo** | `train.bin` do v3 (70% PT + EN + código) | linha de base |
| **2. novo ABC** | `pt_A+B+C` — 100% PT, top 60% | pureza + filtro brando |
| **3. novo A** | `pt_A` — 100% PT, top 10% | pureza + filtro forte |

Comparar 2 contra 3 dá, de quebra, a curva de **quanto filtrar** no corpus novo — a mesma
pergunta que as faixas foram criadas para responder de graça.

## Orçamento

3B tokens por braço. Justificativa: a escada de scaling mostrou que 1B→3B move a
perplexidade de 115,2 para 75,2 — é o regime onde diferença de corpus aparece com folga.
A 3B tokens o custo medido é **$12,8 por braço** na RTX 5090, ou **~$38 no total**.

⚠️ **Não usar mais que 3B por braço.** O corpus antigo tem ~9,87B; passar disso obrigaria a
repetir época em um braço e não no outro, o que viraria outro confundimento.

## ⭐ A régua: bpb externo, NUNCA a perplexidade de validação

A perplexidade de validação de cada braço sai do **seu próprio corpus** — distribuições
diferentes, números incomparáveis. O braço novo teria perplexidade menor só por validar em
texto mais limpo, sem o modelo ter melhorado em nada.

A comparação honesta é `bee/eval_gate2.py` no holdout compartilhado (shards `[7,23]`), onde
já existem os números de referência:

| | bpb PT agregado | `portuguese-pd` (fonte limpa) |
|---|---:|---:|
| Bee-150M v3 (9,87B) | 3,457 | 4,148 |
| Tucano-160m (~200B PT) | 1,739 ⚠️ contaminado | 2,204 |
| SmolLM2-135M (~2T EN) | 2,010 | 2,257 |

### ✅ CONTAMINAÇÃO INVESTIGADA E DESCARTADA — o holdout `[7,23]` serve

**Medido em 2026-08-06 com `bee/holdout_limpo.py`.** Montei um holdout de web PT no parquet
40 (`002_00012`), série do crawl que nenhuma coleta do Bee tocou, e remedi os três modelos:
os bpb reproduzem os do `[7,23]` **dentro de ~1%** (Tucano 0,884 vs 0,896 · SmolLM2 1,551 vs
1,560 · Bee 2,228 vs 2,203). Se houvesse contaminação relevante, o holdout suspeito daria
número melhor — não dá.

⭐ **Decisão: usar o holdout do parquet 40 no gate mesmo assim.** É limpo por construção, e
agora validado contra o antigo. Não custa nada e remove a dúvida de vez.

<details>
<summary>O raciocínio que me levou a declarar contaminação (a preocupação era legítima; a conclusão, não)</summary>

### ⚠️ risco de contaminação na linha `fineweb2-por`

Não é hipótese. O `bee/expand_corpus.py` registra que a expansão do v3 rodou com
`--skip-files 8`, e explica por quê: **os parquets 0-7 já tinham sido consumidos pela coleta
original em streaming** (a do v1). Logo:

| parquets | quem consumiu |
|---|---|
| 0-7 | coleta original em streaming → corpus v1 |
| 8+ | `expand_corpus.py` → expansão do v3 |
| **0-12** | **a coleta nova (esta)** — atravessa as duas |

Os shards de holdout `[7,23]` saem desse mesmo material. Então os braços treinados no corpus
novo veriam **parte do próprio holdout de avaliação**, e a linha `fineweb2-por` sairia
inflada a favor deles.

⚠️ Cheguei a concluir o oposto — que os parquets 0-7 estariam limpos — lendo `--skip-files 8`
sem ler o motivo documentado logo acima. O `skip` existia justamente porque aquela região
**já tinha sido consumida**, não porque estivesse livre.

⭐ **O conserto não é restringir o treino, é construir um holdout limpo.** Baixar UM parquet
de índice alto e nunca tocado (ex.: 40), extrair ~400 documentos e usá-lo como fonte nova de
avaliação. Custa ~10 min de download e conserta a medição **para todos os modelos de uma vez**
— Bee antigo, Bee novo, Tucano e SmolLM2 passam a ter uma linha de web PT em que nenhum deles
pôde ter treinado. Restringir o corpus de treino, ao contrário, jogaria fora dado bom e ainda
deixaria o holdout velho suspeito.

**Enquanto o holdout limpo não existe, a linha decisiva é `portuguese-pd`** (livros de
domínio público do PleIAs, fora do fineweb-2 por construção) — imune a qualquer sobreposição
de parquet.

</details>

## Critério de decisão, declarado ANTES de medir

Sobre o braço 1 (antigo), em `portuguese-pd`:

| resultado | leitura | ação |
|---|---|---|
| ganho > 10% | pureza de idioma é causa real e grande | coletar o resto do `por_Latn` e treinar o Bee-150M no corpus novo cheio |
| ganho 2-10% | causa real mas modesta | trocar de corpus (é de graça) e ir para o Bee-500M |
| ganho ≈ 1,6% | é só o filtro; pureza não fez nada | a hipótese do Tucano cai; reabrir o diagnóstico |
| sem ganho | o corpus não era o problema | ⚠️ voltar para tamanho do modelo — mas aí com evidência |

## Ordem de execução

1. `bee/juntar_pt.py --faixas ABC` e `--faixas A` → dois `train.bin`
2. ✅ **Holdout limpo construído e as referências remedidas** (`bee/holdout_limpo.py`,
   parquet 40) — Tucano 0,884 · SmolLM2 1,551 · Bee-150M v3 **2,228**. É contra esses
   números que os braços serão comparados
3. Subir os `.bin` (HF Hub, conta já autenticada) → pod RunPod
4. Três `pretrain.py` a 3B tokens, mesma config do ponto de 3B da escada (batch global
   524k, seq 2048, LR 3e-3 cosine → 3e-4, 1 época)
5. `eval_gate2.py` nos três, contra SmolLM2 e Tucano, no mesmo holdout
6. Decidir pela tabela acima
