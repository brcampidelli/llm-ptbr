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

⚠️ O holdout `[7,23]` vem do **corpus antigo**, e a fonte `fineweb2-por` dele sai do mesmo
`fineweb-2 por_Latn` que alimenta o corpus novo. **Há risco de contaminação do braço novo.**
Duas defesas: (a) os shards `[7,23]` foram excluídos do treino do v3, mas **não da coleta
nova** — conferir com `bee/medir_dedup.py` antes de confiar no número; (b) a linha de
`portuguese-pd` é imune (livros de domínio público, fora do fineweb-2) e por isso é a
decisiva, exatamente como foi contra o Tucano.

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
2. Checar contaminação do holdout `[7,23]` contra o corpus novo
3. Subir os `.bin` (HF Hub, conta já autenticada) → pod RunPod
4. Três `pretrain.py` a 3B tokens, mesma config do ponto de 3B da escada (batch global
   524k, seq 2048, LR 3e-3 cosine → 3e-4, 1 época)
5. `eval_gate2.py` nos três, contra SmolLM2 e Tucano, no mesmo holdout
6. Decidir pela tabela acima
