# bpb de PT nos marcos do Bee-1G — 2026-09-10

> ⚠️ **Isto NÃO é uma leitura do gate.** O critério declarado
> ([`gate-sucesso-bee-1g.md`](gate-sucesso-bee-1g.md) §3.1) cobra bpb PT ≤ Bee-350M **no ponto
> final, decaído**. Os dois marcos medidos aqui são de **platô do WSD** e as âncoras são de modelo
> **decaído** — compará-los mede o schedule tanto quanto o modelo (§2d), com viés **contra** o
> Bee-1G. Servem como ponto de curva do Bee-1G contra si mesmo.

**Régua:** `bee/ancora_pt.py` · bpb = nats/ln2 / **bytes** · `cuda`/bf16 · teto 1,5 MB por holdout ·
`seq_len` 2048 · lote 1 · `transformers` 5.16.1 (a versão que escreveu os snapshots) · RTX 5070.
Artefatos: [`bpb-pt-bee1g-marcos.json`](bpb-pt-bee1g-marcos.json) e
[`bpb-pt-350m-decaido-15b-vs-2175b.json`](bpb-pt-350m-decaido-15b-vs-2175b.json).

## 1. Medido

| modelo | tokens | regime | `wiki/limpo` | `corpus_multi_pt/limpo` |
|---|---:|---|---:|---:|
| Bee-150M | 21,75B | decaído | 0,9497 | 0,9318 |
| **Bee-350M** (âncora do gate) | 21,75B | decaído | **0,9240** | **0,9052** |
| Bee-350M variante 15B | 15,00B | decaído | 0,9302 | 0,9083 |
| Qwen3-0.6B-Base | ~36T | decaído | 0,9424 | 1,0986 |
| Bee-1G `marco_1B` | **1,278B** | platô | 1,1086 | 1,1085 |
| Bee-1G `marco_3B` | 3,000B | platô | **1,0808** | **1,0653** |

⭐ **A régua se validou dentro de cada passada.** A folga publicada de 2,76% entre 150M e 350M
reproduziu em **+2,71%** (`wiki/limpo`) e **+2,85%** (`corpus_multi_pt/limpo`). E o 350M final saiu
com os mesmos seis valores em **três** passadas independentes do dia — a régua é determinística
entre rodadas, o que autoriza comparar células medidas em passadas diferentes.

## 2. 🔴 O rótulo do `marco_1B` mente por 27,8%

`marco_1B/marco.json` registra **1.277.984.768 tokens no passo 39.001** — e não 1B no passo 30.517
como o nome e o plano dizem. O snapshot ficou para trás durante os reinícios do pod antigo e só foi
gravado quando um relançamento sobreviveu.

⚠️ Não é preciosismo: os marcos existem para a curva de escala ser **medição** e não extrapolação.
Ajustar `L(D)` com D = 1e9 num ponto que é 1,278e9 erra o expoente em 28%. É a §2z — **o nome do
artefato afirma o que o conteúdo desmente** — e a defesa é ler o `marco.json`, nunca o log nem o
nome do diretório.

⚠️ E eu vinha repetindo *"marco_1B: val loss 3,4927 / ppl 32,9"* em vários relatórios. Aquilo é a
validação do passo 30.500. O artefato diz **3,4359 / 31,06**.

## 3. A trajetória do Bee-1G contra si mesmo

Os dois pontos estão no **mesmo regime de LR** (`5,29e-04`; o warmup terminou no passo 12.210), o
que é a condição que a §2d exige para comparar marcos.

| | 1,278B → 3,000B (2,35×) | expoente local |
|---|---:|---:|
| `wiki/limpo` | −2,51% | `D^-0,030` |
| `corpus_multi_pt/limpo` | −3,90% | `D^-0,047` |

⚠️ **As duas réguas discordam do expoente em 56%.** Com dois pontos não há resíduo para conferir
nada (§5: ajuste com graus de liberdade zero descreve, não valida). O terceiro ponto é o
`marco_6B`.

**Piso de ruído da validação**, medido em 6 validações consecutivas no mesmo platô (passos
91.500–92.750): dp **0,0025**, amplitude **0,0076**. A queda de val loss entre os marcos
(0,1197) é ~16× a amplitude — é sinal, não ruído.

## 4. ⭐ O 350M estava saturado em dado — e isso reformula a pergunta

| | 15,00B → 21,75B (1,45×) | expoente |
|---|---:|---:|
| `wiki/limpo` | +0,67% | `D^-0,018` |
| `corpus_multi_pt/limpo` | +0,34% | `D^-0,009` |

O card do 15b publica **0,19%** para os mesmos 45% de dado, num holdout que não existe mais. Aqui
dá 0,34% e 0,67%: ⚠️ a **direção e a ordem de grandeza** reproduzem, a **magnitude difere até
3,5×**. Reprodução qualitativa, não numérica.

⭐⭐ Portanto a âncora **0,9240** não é *"o 350M com 21,75B"* — é essencialmente **o valor saturado
em dado de um modelo de 345M**. Mais dado não a move. A pergunta do gate deixa de ser *"o Bee-1G
alcança um modelo com 7× mais português?"* e passa a ser **"3× de parâmetro batem um 345M já
saturado em dado?"** — o eixo em que este projeto mediu que a escala paga (151M→345M rendeu 2,76%).

## 5. 🔴 Por que não há projeção neste documento

Tentei projetar o ponto final e a conclusão **inverteu** ao trocar um único parâmetro emprestado:

| fator de decaimento usado | projeção `wiki/limpo` a 20B | veredito contra 0,9240 |
|---|---:|---|
| −4,3% (meu, transferido de uma medida de *loss*) | 0,978 | reprova |
| **−10,3%** (medido e publicado, em bpb) | **0,916** | passa |

O valor correto é o segundo: o card do 15b registra o **mesmo modelo, nos mesmos 15,00B**, medindo
**0,9167** no platô e **0,8223** decaído. Eu havia chamado o meu −4,3% de *"generoso"*; era 2,4×
menor que o medido.

⚠️ **Uma extrapolação que muda de veredito conforme qual número de terceiro eu escolho não carrega
informação sobre o gate.** Somam-se: 2 pontos extrapolados 6,7× além do dado, réguas que discordam
do expoente em 56%, e um fator de decaimento medido noutro modelo, noutro corpus, noutro holdout.

⚠️ **O que segue sem verificação nesta régua:** os 10,3%. Verificá-los exigiria o checkpoint de
**platô** do 350M a 15B, que não está publicado — só o decaído.

## 6. A única comparação que já é justa hoje

Contra o **Qwen3-0.6B-Base** — multilíngue como ele, decaído, treinado em ordens de magnitude mais
token — o Bee-1G com **3B tokens** já ganha em `corpus_multi_pt/limpo` (1,0653 contra 1,0986) e
perde em `wiki/limpo` (1,0808 contra 0,9424).

⚠️ Mesmo aqui o Bee-1G está no platô e o Qwen decaído, então o viés é contra ele.

## 7. O que resolve

O ponto final decaído do Bee-1G. Faltam ~17B tokens e ~312 h de GPU. Antes disso:

- **`marco_6B`** dá o terceiro ponto e permite conferir se o expoente local tem resíduo;
- ⚠️ e nenhum marco de platô responde ao gate, por construção.

## 8. O que estes números não mostram

- **capacidade** — o E2 mediu que bpb e capacidade são coisas diferentes;
- **comparação entre idiomas** — bpb carrega viés crosslinguístico; estes números são todos de PT
  e só comparam entre si. Não há âncora externa por idioma nesta máquina;
- **o valor absoluto contra o 0,8207 publicado** — holdout diferente;
- **`limpo` é limpo para o Bee-1G**, por fingerprint de 32 tokens no 64k contra o corpus dele.
  ⚠️ Não é necessariamente limpo para o **350M**, que treinou noutro corpus: se ele viu parte
  desses documentos, o número dele está bom demais — viés **conservador** para "o 1G ganhou" e
  **confundidor** para "o 1G perdeu".

---

## Adendo 2026-09-12 — `marco_6B`, e a primeira previsão pré-registrada

`marco_6B/marco.json`: **5.999.984.640 tokens · passo 183.105 · val_loss 3,2621 · ppl 26,10**.
Desta vez o rótulo bate com o conteúdo (o desvio de 27,8% do `marco_1B` foi artefato dos
reinícios do pod antigo). Três pontos, todos em `lr 5,29e-04`:

| marco | tokens | val loss | expoente local (par anterior) |
|---|---:|---:|---:|
| 1B | 1,278B | 3,4359 | — |
| 3B | 3,000B | 3,3162 | −0,042 |
| 6B | 6,000B | **3,2621** | **−0,024** |

⭐ **A inclinação caiu pela metade entre os dois trechos.** Não é lei de potência pura: há um
termo irredutível, e três pontos bastam para vê-lo — dois não bastavam.

Ajuste `L = E + A·D^−α` (3 parâmetros, 3 pontos — **resíduo zero por construção**; §5: descreve,
não valida): **E = 3,183 · A = 0,304 · α = 0,751**.

⚠️ `E` é a assíntota **do platô**, não o piso do modelo: o decaimento final tira ~10% (medido no
350M). E `α = 0,75` é o eixo de dado de **um** modelo no platô, não comparável ao α de Chinchilla.

**Previsão pré-registrada, escrita antes do dado:** `marco_10B` (passo 305.175) → **val loss
3,237 ± 0,008** (o ± é o piso de ruído medido em 6 validações consecutivas). Se cair dentro, a
forma se sustenta e o `marco_15B` vira segundo teste; se cair fora, a forma está errada e o
motivo é a informação. É para isso que os marcos existem: a curva vira medição, não extrapolação.

Ainda sem projeção de bpb ou de gate: a razão da §5 do documento continua de pé.

**bpb do `marco_6B` na mesma régua** ([`bpb-pt-bee1g-marco-6B.json`](bpb-pt-bee1g-marco-6B.json);
a régua reproduziu o 350M final com os seis valores idênticos em quatro passadas até aqui):

| marco | tokens | `wiki/limpo` | expoente local | `corpus_multi_pt/limpo` | expoente local |
|---|---:|---:|---:|---:|---:|
| 1B | 1,278B | 1,1086 | — | 1,1085 | — |
| 3B | 3,000B | 1,0808 | −0,030 | 1,0653 | −0,047 |
| **6B** | 6,000B | **1,0642** | **−0,022** | **1,0524** | **−0,018** |
| âncora 350M | 21,75B | 0,9240 | | 0,9052 | |

A desaceleração da val loss aparece também no bpb, nas duas réguas. Continua platô; continua sem
projeção. ⚠️ O gate #5 mediu que o holdout de PT tem 6% de quase-duplicatas com o treino e que o
efeito na val loss é −0,006 nats (0,8× o ruído) — a curva acima não muda com isso.

## Adendo 2026-09-15 — `marco_10B`: a previsão pré-registrada acertou (na borda)

`marco_10B/marco.json`: **9.999.974.400 tokens · passo 305.175 · val_loss 3,2300 · ppl 25,28**.
A previsão escrita três dias antes era **3,237 ± 0,008 → [3,229; 3,245]**. O ajuste de 3 parâmetros
sobre 3 pontos dava 3,2369 em D = 10B; o medido ficou **0,007 abaixo**, dentro da faixa, na borda de
baixo. ⚠️ Uma leitura só, e a série de validação vizinha (298k–301k, a cada 250 passos) oscila
entre 3,232 e 3,246 — o ruído de um ponto tem o tamanho da faixa. O que se afirma: **a forma
`E + A·D^−α` é compatível com o quarto ponto**; o que não se afirma: precisão maior que ±0,008.
Agora há 4 pontos para 3 parâmetros — o primeiro grau de liberdade de resíduo (§5) — e o
`marco_15B` (passo 457.763) é o próximo teste, com a previsão a registrar no reajuste.

| marco | tokens | val loss | expoente local | previsto |
|---|---:|---:|---:|---:|
| 1B | 1,278B | 3,4359 | — | — |
| 3B | 3,000B | 3,3162 | −0,042 | — |
| 6B | 6,000B | 3,2621 | −0,024 | — |
| **10B** | 10,000B | **3,2300** | **−0,019** | 3,237 ± 0,008 ✅ |

A desaceleração continua monotônica na val loss multilíngue (−0,042 → −0,024 → −0,019).

**bpb na mesma régua** ([`bpb-pt-bee1g-marco-10B.json`](bpb-pt-bee1g-marco-10B.json); md5 do
snapshot conferido contra a origem, `9765554a…`):

| marco | tokens | `wiki/limpo` | exp. local | `corpus_multi_pt/limpo` | exp. local |
|---|---:|---:|---:|---:|---:|
| 1B | 1,278B | 1,1086 | — | 1,1085 | — |
| 3B | 3,000B | 1,0808 | −0,030 | 1,0653 | −0,047 |
| 6B | 6,000B | 1,0642 | −0,022 | 1,0524 | −0,018 |
| **10B** | 10,000B | **1,0479** | **−0,030** | **1,0423** | **−0,019** |
| âncora 350M | 21,75B | 0,9240 | | 0,9052 | |

⚠️ No `wiki/limpo` o trecho 6B→10B saiu *mais* inclinado que o 3B→6B (−0,030 contra −0,022); no
`corpus_multi_pt/limpo` não (−0,019 contra −0,018). Duas réguas de PT discordando sobre a
inclinação de um trecho é ruído de holdout (276 docs, 0,94 MB), não sinal — §3: três leituras
coincidentes, e aqui há duas que não coincidem. Fica registrado, não interpretado. Os seis
holdouts caíram juntos: `wiki/sujo` 1,0015 → 0,9827, `corpus_multi_pt/sujo` 0,9816 → 0,9708.

**Densidade de solução** ([`densidade-solucao-bee1g-marco-10B.json`](densidade-solucao-bee1g-marco-10B.json),
mesmas 100 amostras de ruído dos outros marcos; guarda §2aa: bpb sem perturbação = âncora 1,0479):

| σ | ΔL mediana 6B | ΔL mediana 10B | pareado 10B − 6B | 10B pior em |
|---:|---:|---:|---:|---:|
| 0,01 | +0,3136 | +0,3103 | −0,0025 | 44/100 |
| 0,005 | +0,0766 | +0,0736 | −0,0012 | 43/100 |
| 0,001 | +0,0033 | +0,0028 | −0,0001 | 44/100 |

⭐ **A curvatura parou de subir.** 1B→3B achatou (0/100), 3B→6B afiou (96/100), 6B→10B **empatou**
(44/100 — indistinguível de 50). A leitura de três pontos ("a densidade sobe no platô") era, de
novo, uma leitura de dois trechos; com quatro pontos a série de curvatura em σ=0,01 é
**3.618 → 2.735 → 3.136 → 3.103**: uma queda, uma subida, um platô. Sem tendência para
extrapolar — e o par decisivo continua sendo o do fim (platô 15B contra 20B decaído), que é o que
o 2609.08966 mede.
