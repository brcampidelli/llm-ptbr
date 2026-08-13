# Lições de método — o que este projeto pagou para aprender

> **Leia antes de treinar qualquer Bee novo.** Este documento existe porque os erros mais
> caros deste projeto **não deram erro**: a loss caía, o log parecia saudável, e o defeito só
> apareceu ao comparar com algo externo — às vezes semanas depois.
>
> Complementa `licoes-pretreino.md` (detalhe do pré-treino), `agentico-medicao.md` (medição
> agêntica) e `sft-resultado.md` (SFT). Aqui está o que atravessa todos eles.

---

## Parte I — A família que custou mais caro: **dado sumindo em silêncio**

Três ocorrências, três causas diferentes, **o mesmo modo de falha**. Nunca tinham sido postas
lado a lado, e é justamente a comparação que revela o padrão.

| # | onde | o que sumiu | como se manifestou |
|---|---|---|---|
| 1 | pré-treino | o **objetivo** (previa t+2 em vez de t+1) | loss caindo normalmente por 2 semanas |
| 2 | pré-treino | **37% do corpus** nunca entrou | nada; a cobertura não era reportada |
| 3 | SFT | **100% dos exemplos agênticos** | treino rodou 354 passos em vez de 447 |

### 1. Deslocamento duplo de rótulos — 2 semanas, ~US$ 34

`LlamaForCausalLM.forward(labels=L)` desloca **por dentro**. Passar um `y` já deslocado
desloca duas vezes.

```python
perda = modelo(input_ids=x, labels=y).loss   # ❌ treina para prever t+2
perda = modelo(input_ids=x, labels=x).loss   # ✅ o rótulo é o PRÓPRIO input
```

**Por que não deu erro:** a validação usava a mesma convenção errada. Perplexidade caiu 77→63
e o treino parecia saudável do início ao fim.

**Como foi pego:** `gate_pareado.py` usava `labels=x` (correto) e, com **75× menos dados**,
media bpb **40% melhor**. Setenta e cinco vezes mais dado produzindo resultado pior é
impossível — mas foram construídas cinco hipóteses elaboradas antes de alguém ler a
impossibilidade.

**Custo medido:** bpb 2,218 → **1,021**, com 10× menos dados.

**Guarda:** `conferir_convencao_de_rotulos()` roda antes do passo 1 e **aborta**. ⚠️ Com dado
de treino **real** — com tokens aleatórios a diferença cai de 1,85 para 0,0074 e a guarda não
dispara: um teste que passa sem testar nada.

### 2. Amostragem com reposição — 37% do corpus

`torch.randint` a cada passo amostra **com reposição**: a cobertura tende a `1 − 1/e = 63,2%`.
Medido: 63,5%. De 9,87B tokens, **~3,6B nunca entraram**.

**Guarda:** `AmostradorPermutado` percorre blocos permutados até o fim; cobertura reportada no
log e conferida contra 100%.

### 3. `max_seq_len` curto no SFT — 100% do agêntico

O prompt agêntico tem 1.096–1.191 tokens só no catálogo de ferramentas; o default era 1.024.
Quando o prompt sozinho estoura o limite, a *completion* é truncada fora, o exemplo fica
**inteiramente mascarado** e o TRL o descarta **sem erro**.

**Como foi pego:** contando passos. Previu ~447, executou **354** = 79,2%. E 1.495/7.152 =
**20,9%**. Bate na casa decimal.

**Guarda:** `sft.py` **aborta** se >1% do dataset for descartado por truncamento.

### ⭐ A regra que sai dos três

> **Se um dado novo entra e a métrica não se move, a primeira hipótese é que ele não entrou —
> não que "não ajudou".**

E o corolário operacional: **conte os passos**. O número de passos executados contra o
previsto é o detector mais barato que existe para dado que sumiu.

---

## Parte II — O instrumento mente antes do fenômeno

Duas ocorrências em que o **avaliador** estava errado e quase produziu decisão de produto.

### 4. Avaliador com mundo fechado — 23,5% que não existiam

O executor determinístico foi escrito com um mundo **fechado**: 6 cidades, 5 tickers, 3
arquivos. O holdout usa o mundo real — Brasília, `/var/log/syslog`, `ABEV3`. Resultado: **35
dos 85 exemplos eram impossíveis de acertar por construção**, porque a própria chamada de
*referência* falhava. Taxa medida: 23,5%. Taxa real: **57,6%**.

**Como foi pego:** implausibilidade. `read_file` 0/10 e `list_dir` 0/10 — zero absoluto em
ferramenta simples, num modelo que fazia 91% em `get_weather`.

**Guardas:** mundo simulado **aberto e determinístico** (hash da entrada normalizada), nunca
lista branca; e uma guarda que **executa todas as referências antes de carregar qualquer
modelo** — se o gabarito não roda, o avaliador está errado. Ela se pagou na primeira
execução, pegando `sqrt()` faltando na calculadora.

### 5. Critério de veredito multiplicativo

O código imprimiu **"NÃO há cauda útil"** para `pass@1` 52,3% → `pass@16` 72,9%. A condição
era `pass@k > pass@1 × 1,5` — critério **multiplicativo**, que com `pass@1` alto exige 78,6%,
quase o teto. Ele pune justamente o modelo que já vai bem.

**Guarda:** folga **absoluta** (≥5 pp) somada à fração do espaço restante capturada (≥15%).

⚠️ **A lição real:** repassar veredito impresso por código sem conferir contra os números
crus teria fechado uma porta que estava aberta.

---

## Parte III — As leis medidas

Enunciados curtos, cada um com o número que o sustenta. Valem para o próximo Bee.

### 1. Rejection sampling move o **piso** rumo ao teto — e não move o teto

| | antes | depois |
|---|---:|---:|
| pass@1 | 52,3% | **57,6%** |
| pass@16 | 72,9% | **72,9%** |

A folga aproveitável encolheu de 20,6 para 15,3 pp: **cada iteração rende menos**. Elevar o
teto exige capacidade ou dado novo, não reamostrar o que já existe.

### 2. Num modelo pequeno, a **capacidade é disputada**

Ensinar multi-turno por full fine-tune custou **−5,9 pp** de execução single-turn e −7,0 pp de
argumentos exatos. O mesmo dado em **adapter LoRA** custou **zero** — e ficou melhor no alvo.

| | full FT | adapter |
|---|---:|---:|
| multi-turno ancorado | 89,4% | **91,8%** |
| single-turn (execução) | 60,0% | **65,9%** |
| tamanho | 302 MB | **24 MB** |

⭐ É a validação da tese da COMEIA: **backbone congelado, capacidade nova em adapter**.

### 3. Colher só um lado desloca a decisão

O rejection sampling só produz `tool_call` (só a chamada tem verificação por execução). A
proporção foi de 59,3% → 75,8% tool e o over-calling subiu **+7,6 pp**. Colhendo os dois lados
(56,9% tool), ganha-se nos **dois** eixos.

### 4. **$/bilhão de tokens**, nunca $/hora

| GPU | TDP | tok/s | $/h | **$/B tokens** |
|---|---:|---:|---:|---:|
| RTX 5090 | 600 W | 62,9k | 0,99 | **4,37** |
| RTX PRO 4500 | 200 W | 42,1k | 0,74 | 4,88 |

A placa 25% mais barata por hora saiu **36% mais cara por token**. O preditor é o **TDP**.

### 5. Toda intervenção que **bloqueia** precisa ser medida nos dois lados

O `verifier.py` interceptava 4 over-calls em 14 — parecia útil. Mas bloqueava **7 chamadas
legítimas em 85**: saldo **−4**. Estava piorando o sistema havia semanas, e ninguém sabia
porque só se media o ganho.

### 6. Não herdar hiperparâmetro medido sobre outro modelo

O LR 1e-3 do SFT fora otimizado **sobre o modelo bugado**. Remedido sobre a base correta: o
ótimo é **6e-4** (2,9% melhor). E LoRA opera em regime diferente ainda: **1e-3**, com a curva
caindo 10× entre 1e-4 e 1e-3.

### 7. Ler throughput **em regime**

Medir com 6 passos de aquecimento deu **21,7 s/passo**; o valor real era **4,4 s/passo** —
erro de 5×, que gerou uma decisão de infraestrutura equivocada. Só confiar a partir do passo
~20, com três leituras coincidentes.

---

## Parte IV — O que estava certo desde o início

Não mexer sem medir:

- **Arquitetura** `LlamaConfig` sem código custom — tudo que existe (PEFT, TRL, vLLM) funciona
  sem adaptação, e o recipe é o mesmo em toda a escada.
- **LR por Step Law** (`η* = 1,79·N^-0,713·D^0,307`).
- **Tokenizador PT próprio** — 0,2183 tok/byte contra 0,3576 do SmolLM2.
- **Gates pareados baratos** antes de run longo — 5 min contra dias.
- **Procedência de dados** verificada na origem, nunca pelo rótulo.
- **Marcos de scaling** salvos durante o treino: a curva vira **medição**, não extrapolação.

---

## Checklist antes de qualquer run longo

- [ ] guarda de rótulos roda e **aborta** (com dado real)
- [ ] cobertura de amostragem reportada = 100%/época
- [ ] nº de exemplos após truncamento == nº carregado (SFT) — **aborta** se não
- [ ] gabaritos do avaliador **executam** antes de medir qualquer modelo
- [ ] `--dry-run` de 3 passos passa
- [ ] throughput em regime (passo ≥20, três leituras coincidentes)
- [ ] custo em **$/B tokens**
- [ ] corpus verificado por **hash** contra a referência
- [ ] marcos de scaling programados
- [ ] checkpoint em disco **persistente**
- [ ] gate de sucesso **definido antes** de gastar
