# Gate de sucesso do Bee-1G (T4) — declarado ANTES de gastar

> **Data da declaração: 2026-09-04.** Nada abaixo pode ser alterado depois que o run começar,
> exceto para registrar que um critério se mostrou impossível de medir — e aí a alteração vai
> datada e o critério original fica visível, riscado, com o motivo.
>
> Construído sobre a [revisão de 2026-09-04](revisao-bee-1g-2026-09-04.md), que rebaixou o Gate T2
> e listou oito pré-requisitos. **Este gate só é executável depois deles** (§6).
>
> Modelo de relatório: [Manacá-1B](https://arxiv.org/abs/2608.30114) — *erro padrão e teste pareado
> em toda comparação, harness validado contra número publicado*. É a nossa §2aa escrita por outra
> equipe, e é o padrão que o relatório final tem de cumprir.

---

## 0. As quatro perguntas que todo número deste gate responde

Antes de qualquer critério, a régua de cada linha declara:

1. **em que régua** — holdout, bytes, modo (`cuda/bf16`), lote, `max_new` por idioma;
2. **contra que piso** — trivial, sem modelo, medido no mesmo conjunto;
3. **com que ruído** — o piso de dispersão de semente ou de amostragem, ao lado;
4. **o que NÃO mostra** — escrito, porque uma régua incapaz de exibir um efeito não é evidência
   contra ele (§2q).

Uma linha sem as quatro **não entra no relatório**.

---

## 1. Guardas de execução — abortam, não avisam

Todas rodam **antes do passo 1** ou **a cada marco**, com dado real. Cada uma já existe em código
e já foi testada contra o estado quebrado (§2t), exceto onde marcado.

| guarda | onde | dispara se |
|---|---|---|
| convenção de rótulos (§1) | `gate_throughput_1g.py`, com dado real | `|loss − CE manual| > 0,01` |
| amostragem sem reposição (§2) | `SemReposicao`, cobertura no log | cobertura ≠ prevista no fim da época |
| taxa de descarte do holdout | `gate_t2_mistura.py` | fora de `[PCT/3, PCT×3]` — pega invertido **e** morto |
| mistura efetiva ≈ rótulo (§2r) | `gate_t2_mistura.py` | desvio > 1 pp em qualquer idioma |
| `uint32` + ida-e-volta do pool | `gate_t1_bpb.py` | `max_id ≥ vocab` ou tamanho gravado ≠ contado |
| LR explícito no comando (§2d) | script do run | `--lr` ausente → aborta antes de começar |
| ⚠️ **novo** — checkpoint em dois lugares | script do run | marco sem cópia **fora do pod** → aborta o marco seguinte |
| ⚠️ **novo** — `seq_len` da config = 2048 | script do run | `ESCADA["1b"].seq_len ≠ 2048` → aborta |

⭐ A penúltima nasceu hoje: um pod morreu com o `corpus_multi_extra` dentro. **Dado que só existe
num pod não existe.**

---

## 2. Marcos programados — a curva vira medição, não extrapolação

Marcos em **tokens vistos**: `1B · 3B · 6B · 10B · 15B · 20B` (e a cada 10B além disso, se o
orçamento for maior).

Em cada marco, **nesta ordem**:

1. checkpoint gravado **e copiado para fora do pod** — só então o marco conta;
2. **3 saídas cruas** com `skip_special_tokens=False`, **lidas com os olhos** (§2e) — 30 s que
   separam "o modelo não sabe" de "a régua não escuta";
3. bpb por idioma nos holdouts fixos (§3.1), mesma régua sempre;
4. throughput de regime desde o marco anterior (§3, três leituras).

🔴 **Regra de leitura dos marcos (§2d):** todos os marcos de um mesmo run estão no **mesmo regime
de LR**, então a curva entre eles é legítima. **Nenhum marco intermediário compara com outro
run** — só o ponto final, ambos decaídos. E ⚠️ **platô de bpb no platô do WSD não é saturação**:
o 350M ficou plano de 10B a 15B e caiu 12% ao decair. Não abortar por isso.

---

## 3. Critérios de sucesso — medidos no ponto FINAL, decaído

### 3.1 Português — bpb, na mesma régua do 350M

| régua | holdout | piso | critério |
|---|---|---|---|
| bpb PT (a) | `bee/gate/holdout_wiki.json` — 300 docs Wikipédia-PT, 1,03 MB, **que nenhum braço treinou** | bpb do **gzip** do mesmo texto | **≤ Bee-350M no MESMO holdout** |
| bpb PT (b) | PT do `corpus_multi` — balde `sha1 % 100 < 2`, 1,5 MB, o holdout dos gates T1/T2 | idem | idem |

> ### ✅⭐⭐ [MEDIDO 09-04] As âncoras existem, e a régua foi validada
>
> `bee/ancora_pt.py`, artefato `docs/ancora-pt-t4.json`. Régua: bpb, `cuda/bf16`, 1,5 MB por
> holdout, `seq_len` 2048.
>
> | holdout | Bee-150M | **Bee-350M = ÂNCORA** | folga |
> |---|---:|---:|---:|
> | `wiki` — Wikipédia-PT, 300 docs, 1,03 MB | 0,9434 | **0,9175** | **+2,75%** |
> | `corpus_multi` PT — 438 docs, 1,49 MB | 0,8857 | **0,8576** | +3,18% |
>
> ⭐⭐ **§2aa cumprida na única forma possível.** O número publicado do 350M (0,8207) veio de um
> holdout que não existe mais, então ele não pode ser reproduzido. Mas a **folga publicada de
> 2,76% sobre o 150M** pode — e reproduziu em **+2,75%** no `wiki`. Uma folga entre dois modelos
> na mesma régua sobrevive à troca de holdout; o valor absoluto não.
>
> 🔴 **O 0,8207 fica descartado como critério.** As âncoras são **0,9175** (wiki) e **0,8576**
> (corpus_multi), cada uma no seu holdout, nunca a média.
>
> ⚠️ E a diferença entre os dois (0,9175 contra 0,8576, o mesmo modelo) é a razão de reportá-los
> separados: a Wikipédia-PT é 7% mais difícil. ⭐ A folga da escala também é maior **dentro** da
> distribuição de treino (3,18% no fineweb-2) que **fora** dela (2,75% na Wikipédia).

**O que não mostra:** capacidade. O E2 mediu que bpb e capacidade são coisas diferentes, e o
próprio 350M passou de 0% a 86% em tradução pt→en com 2,76% de bpb.

### 3.2 Os outros sete idiomas — bpb, dentro de cada coluna

| régua | holdout | piso | critério |
|---|---|---|---|
| bpb por idioma | os 7 do `corpus_multi`, 1,5 MB cada, mesmo balde | gzip do mesmo texto | **≤ o modelo público Apache-2.0 mais próximo, POR IDIOMA** — candidato: `Qwen3-0.6B` |

⭐ **§2aa antes de comparar:** reproduzir **um** número publicado do modelo público na nossa
régua. Se o controle não bate com o publicado, não há comparação a fazer, só dois números errados.

🔴 **Leia por coluna, nunca entre colunas** ([`2608.25089`](https://arxiv.org/abs/2608.25089)):
bpb carrega viés crosslinguístico de tokenização e ortografia. *"arb 1,2 contra cmn 0,9"* não diz
nada. A comparação entre idiomas é a §3.3.

**O que não mostra:** o mesmo da §3.1, e ainda: um modelo público de 0,6B com vocab de 150k
tokeniza estes idiomas melhor que o nosso `64k` — perder para ele em CJK pode ser tokenizador,
não modelo. A régua da §3.3 separa isso.

### 3.3 Entre idiomas — NLL por sentença em corpus paralelo

| régua | conjunto | critério |
|---|---|---|
| NLL por sentença, sequências **semanticamente equivalentes** | FLORES+ devtest, os 8 idiomas (CC-BY-SA-4.0: **só leitura**, nunca redistribuído) | **sem critério de aprovação — é diagnóstico**, reportado ao lado da §3.2 |

É o comparador que `2608.25089` chama de honesto. Reportado sempre; **nunca usado para
aprovar ou reprovar**, porque não há piso trivial para ele e não há número do 350M.

### 3.4 Tradução — o eixo declarado do projeto

| par | régua | piso de copiar a fonte | critério |
|---|---|---|---|
| en→pt | chrF2, 300 pares, `eval_traducao_pt.py` | **21,5** | > piso **e ≥ 350M (51,1)** |
| pt→en | idem | **22,7** | > piso **e ≥ 350M (43,3)** |
| es/fr/de/ar/zh/ja → pt | chrF2, FLORES+ devtest, 300 pares por par | **a medir** no mesmo conjunto | > piso de copiar a fonte |
| pt → es/fr/de/ar/zh/ja | idem | a medir | > piso |

⚠️ **Três avisos que vão no relatório:**
- **`max_new` por idioma, calibrado pela fertilidade** ([Mind the Cap](https://arxiv.org/abs/2608.04160)):
  com 8 idiomas de fertilidades diferentes, um teto fixo vira a variável medida. **Taxa de
  truncamento ao lado de todo número.**
- **idioma-alvo** reportado separado do chrF2 — o 150M fazia chrF2 17 com **0%** no idioma certo.
- é o **modelo base**; fluência só se mede pós-SFT. Este critério mede se a capacidade **existe**.

**O que não mostra:** qualidade além do piso. chrF2 acima de copiar a fonte diz que o modelo
traduz; não diz que traduz bem. Juiz sensível a fluência fica para o pós-treino.

### 3.5 As nove capacidades — nenhuma pode regredir do 350M

Consolidador `comeia/eval/baseline_8_capacidades.py` + matemática, **cada uma com o piso do
próprio arquivo ao lado**, e rodado **sem `--chat`** porque é base (§2e: medir no formato em que
treinou).

| capacidade | 350M base | piso trivial | critério no 1G |
|---|---:|---:|---|
| tradução en→pt chrF2 | 51,12 | 21,5 | ≥ 350M (§3.4) |
| tradução pt→en chrF2 | 43,30 | 22,7 | ≥ 350M |
| resumo — cobertura | 84,0% | — | ≥ 350M − ruído |
| resumo — útil | 0,0% | 51,3% | reportado; **sem critério** (nunca treinado) |
| atendimento — útil | 0,0% | 60,4% | reportado; sem critério |
| sentimento (logprob) | 49,7% | **79,0%** | ⚠️ **≥ piso léxico** — o 350M está ABAIXO do piso |
| IFEval-PT estrito/instrução | 30,4% | — | ≥ 350M − ruído, **decomposto por verificador** (§2y) |
| código pass@1 | 0,0% | — | reportado; sem critério |
| agêntico | 0/85 | — | reportado; sem critério |
| matemática pass@256 | 44/200 | — | ≥ 350M − ruído |

**Regra de leitura:** *"− ruído"* é o piso de ruído **já medido** para cada régua (semente 0,9 pp
em n=1000; amostragem 2,3 pp; régua 0 em greedy). Diferença menor que o ruído **não é regressão
nem ganho**.

🔴 **A linha do sentimento é o único critério mais duro que "não regredir":** o 350M base está em
49,7% contra um piso léxico de 79,0% — ele degenera para "positivo" em 554 de 600. Um modelo de
1B que continue abaixo de contar a palavra "não" **falhou nessa capacidade**, independente do bpb.

**O que não mostra:** as capacidades **pós-SFT**. Resumo, atendimento, código e agêntico estão em
zero no base por nunca terem sido treinados — o E2 e o E19 mediram que saem do zero com dado. Este
gate mede o base; o pós-treino tem gate próprio (plano §4).

### 3.6 Throughput e custo — o run tem de bater o que o gate mediu

| métrica | medido no gate | critério |
|---|---:|---|
| tok/s em regime, `mb=4 seq=2048` | **14.470** | ≥ 90% (13.000) sustentado |
| VRAM de pico | 24,9 GB | < 30 GB |
| US$/B tokens | 19,00 | reportado real no fim, contra o projetado |

⚠️ O gate mediu 40 passos — **teto otimista**. Queda de 10% em run longo é térmica ou I/O e é
esperada; **queda de 20% sustentada por mais de 1 h é investigação**, não aceitação.

---

## 4. Critérios de PARADA — abortam o run

| condição | ação |
|---|---|
| qualquer guarda da §1 dispara | aborta |
| bpb PT num marco **pior que o marco anterior em > 2%**, dentro do mesmo regime de LR | pausa e investiga — §5: aparato antes de fenômeno |
| throughput < 80% do medido por > 1 h | pausa, `nvidia-smi power.draw` (teto elétrico? — §4) |
| checkpoint do marco sem cópia externa | não avança |
| 3 saídas cruas do marco são **repetição de um token** ou vazias | aborta — é o modo de falha do Madlad e do adapter colapsado |

🔴 **O que NÃO é motivo de parada:** bpb plano no platô do WSD (§2d); perda de treino que ordena
diferente do holdout (o gate de faixas mediu isso — memorização, não sinal); marco intermediário
pior que o ponto final de outro run.

---

## 5. O que este gate NÃO decide — declarado

- **a decisão do dono** (plano §1/§6.3): quanto do orçamento preserva PT versus adiciona idiomas,
  e em **1 ou 2 estágios** (revisão §2.3, §2.13). O gate mede o que sair; não escolhe o ponto;
- **capacidades pós-SFT** — gate próprio;
- **o valor da tradução como dado** (T-TRAD estágio final) — não rodou;
- **comparação enc-dec × dec-only** (plano T0.a): se o eixo de tradução falhar na §3.4, **esta é a
  primeira hipótese**, e não existe na literatura em ≤1,5B do zero.

---

## 6. Pré-requisitos — o gate não é executável antes destes

Copiados da [revisão §4](revisao-bee-1g-2026-09-04.md), com o estado:

| # | pré-requisito | custo | estado |
|---|---|---|---|
| 1 | `ESCADA["1b"].seq_len` → **2048** | minutos | ✅ feito em 09-04 |
| 2 | **âncora do 350M** nos dois holdouts de texto da §3.1 | 5070, minutos | ✅ **feito 09-04** — 0,9175 / 0,8576 |
| 3 | **re-tokenizar os 21,97B PT** em `64k-multi` (lossless, verificado por shard) | CPU 6,1 h com 5 processos | ✅ **feito 09-04** — 39/39, **23,868B** em 64k, docs 26,3M idênticos, `max_id` 63.999 |
| 4 | **coletar 7 idiomas a 2,5B tokens** cada (alvo por TOKEN, não por caractere) | banda ~3,8 h | ✅ **feito 09-05** — censo **contado** ([`censo-coleta-1g.json`](censo-coleta-1g.json)): **418 shards, 20,73M docs, 55.608 Mcar, os 7 idiomas a 100,0% = 17,500B tokens**. Os 4 que faltavam (`deu`/`fra`/`jpn`/`spa`) foram coletados no pod em 30 min |
| 5 | **mini-sweep de LR** que cerca 1e-3 (3 pontos × 1 semente × 2.000 passos) | ~US$ 3 | ✅ **feito 09-04** — 5 pontos, mínimo **interior em 2,5e-4** a 32,8M tokens; ⚠️ a guarda mirava o horizonte do RUN e foi corrigida — para 20B, escalar: **~1,8e-3** |
| 6 | **braço de transferência do T2** (`bal-12` e `pt-50` a 350M) — **ou** risco aceito por escrito | ~US$ 6 | ✅ **rodado 09-05** ([`gate-t2-mistura-350m.json`](gate-t2-mistura-350m.json)) — Qwen3 376M, LR 1,7e-3, 3 sementes, 4,8 h. ⭐ A **vantagem de PT transfere** (pior `pt-50` 1,459 < melhor `bal-12` 1,526). 🔴 A **taxa de troca não é resolvível**: 0,41× / 2,56× / 3,15× entre sementes, e as três condições se sobrepõem. ⚠️ Escala e tok/param **confundidos** — 0,27 aqui contra ~20 no run |
| 7 | ❓ **decisão do dono** — ponto da troca, e 1 ou 2 estágios | — | ❌ |
| 8 | reproduzir **um** número publicado (§2aa) | 5070, minutos | ✅ **feito 09-04** — folga 2,76% → +2,75% |

⚠️ 3 e 4 são os longos, **não precisam de GPU**, e podem rodar em paralelo desde já.

---

## 7. O formato do relatório final

Uma tabela por seção acima, e em **toda** comparação: valor, erro padrão (ou amplitude entre
sementes/amostras), `n`, e o `t` pareado quando houver par. Toda célula reaproveitada de outra
rodada carrega `_procedencia` (§2z). O JSON de saída deriva o nome da config (§2z) e grava a
config completa da régua (§2aa). **Nenhum número entra sem o piso ao lado.**
