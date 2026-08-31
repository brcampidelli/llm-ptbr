# E20 / E21 — resumo por dado: a curva de dose, e o preço que aparece nela

> **A pergunta:** `resumo útil` está em **0,0% em todos os artefatos** do projeto, e o gargalo
> medido é uma condição só — `comprimiu` falha **150/150**. Dobrar o parâmetro não move
> (151M e 345M falham nos mesmos 150). **Dado dirigido resolve?**
>
> **Resposta:** ⭐⭐ **resolve em parte, e o preço só aparece na dose maior.** A 2,6% de dose o
> resumo quase não move e o eixo agêntico não sente nada. A 6,5%, `útil` salta para **14,7%** —
> e a execução agêntica cai **9,0 pp**.
>
> 🔴 **"Capacidade é disputada" (E2) estava certo.** Eu concluí no E20 que acrescentar tarefa
> nova não cobrava; estava errado — a dose era pequena demais para mostrar.
>
> Custo total: **US$ 0,54** de professor e ~4 h de GPU local.

---

## A curva, em três pontos

Os três corpora têm **698 passos** — o mesmo do C-full. Só o corpus muda, então a diferença é
atribuível ao dado e não ao volume de treino.

| | C-full | E20 | **E21** |
|---|---:|---:|---:|
| exemplos de resumo | 0 | 291 | **773** |
| dose no corpus | 0% | 2,6% | **6,5%** |

### Resumo — todas as condições, não o agregado

| falhas (de 150) | C-full | E20 | **E21** | LEAD-2 |
|---|---:|---:|---:|---:|
| `comprimiu` | 150 | 147 | **122** | 15 |
| `cobriu` | 37 | 17 | **6** | 58 |
| `sem_entidade_inventada` | 55 | **0** | 2 | 0 |
| `sem_numero_inventado` | 41 | 14 | 🔴 **36** | 0 |
| `respondeu` | 33 | 17 | **15** | 0 |

| | C-full | E20 | **E21** | piso LEAD-2 |
|---|---:|---:|---:|---:|
| **útil** | 0,0% | 0,7% | ⭐ **14,7%** | **51,3%** |
| razão de compressão | 0,881 | 0,470 | **0,410** | 0,26 |
| cobertura | 77,8% | 79,2% | 78,0% | 69,0% |

⭐⭐ **`útil` foi de 0,7% para 14,7% ao passar de 2,6% para 6,5% de dose** — 21×, com 2,5× de
dado. A resposta é fortemente não-linear na dose.

⚠️ **E `sem_numero_inventado` REGREDIU** (14 → 36 falhas). Comprimindo mais forte, o modelo
parafraseia número. É custo real da dose, e só aparece porque as cinco condições vão no
relatório — o agregado `útil` subindo esconderia.

🔴 **O modelo continua perdendo para o `head -2` por 36,7 pp.**

### Eixo agêntico — o preço

| | C-full (3 sementes) | E20 | **E21** |
|---|---:|---:|---:|
| ferramenta certa | 77,7% ± 1,4 | 81,0% | **66,8%** |
| executou e cumpriu | 68,1% ± 1,3 | 72,6% | 🔴 **59,1%** |
| under-calling | 15,8% ± 0,8 | 11,4% | 🔴 **27,8%** |
| over-calling | 14,6% ± **0,37** | 18,7% | **10,4%** |
| **macro** | **76,8% ± 0,76** | 77,0% | **74,4%** |

🔴 **A 2,6% não houve custo; a 6,5% a execução caiu 9,0 pp e a macro 2,4 pp**, com o
under-calling dobrando. A capacidade é disputada — o E20 só não mostrou porque a dose era
pequena demais.

⚠️ **Uma semente contra três** nos dois braços novos. A queda de 9,0 pp é 7× o desvio de semente
do C-full (1,31), então está fora do ruído; mas a leitura formal exige três sementes (§2x).

---

## 🔴 A correção que este experimento me obrigou a fazer

No E20 eu escrevi: *"adicionar uma capacidade nova não custou a antiga — o que refina o achado
do E2 e do E19: capacidade é disputada vale para trocas grandes, não para acrescentar 2,6% de
tarefa nova."*

**Estava errado.** O E21 mostra que cobra sim — a 2,6% o efeito estava abaixo do que aquele
desenho conseguia exibir. É a §2q aplicada a mim: *"não observei" só vira "não existe" depois de
mostrar que o aparato conseguiria observar.* Uma dose que move o alvo em 0,7 pp não tem poder
para exibir o custo no outro eixo.

---

## Desenho — três decisões que valem para as próximas capacidades

**1. A régua virou a guarda da geração.** Três das quatro condições de `avaliar_resumo` não
precisam de `fatos_essenciais` e entram direto no laço. ⭐ E foram validadas **contra o estado
quebrado**: rodadas sobre a fonte inteira — que é o que o modelo devolvia (razão 0,88) —
**reprovam 300 de 300**. O LEAD-2 passa em 17–31%, então também não são vácuas.

**2. O catálogo de ferramentas vai no `system` dos exemplos de resumo.** Sem isso o modelo
aprenderia *"sem system → resuma"*: uma característica superficial separando as classes, que é a
§2u literal. Com o catálogo, ele tem de ler o pedido.

**3. A fonte é texto real do fineweb-2** (`bee/edu/anotado.jsonl`), **não** os 10 moldes que
geram o holdout. Treinar com os moldes ensinaria o template e o holdout mediria memorização
(§2o).

### ⚠️ E uma guarda que estava no eixo errado

A v1 exigia 34% dos 6 números mais salientes e **rejeitou 26% das gerações** — a maior causa de
recusa. Mas `cobriu` falha em apenas 17/150 no modelo treinado: **cobertura não era o gargalo,
compressão era.** Filtrar no eixo errado matava de fome o sinal que se queria ensinar. Afrouxada
para ≥1 de 6, a aceitação subiu de 47,9% para 54,3%.

---

## O que isto decide

⭐⭐ **Não é dose maior — é adapter separado.** Para levar o resumo acima do piso de 51,3%
seria preciso uma dose bem maior, e a curva mostra que o custo agêntico cresce junto. Este
projeto já mediu a saída certa uma vez: no E2, multi-turno por **full FT** custou −5,9 pp de
execução e por **adapter LoRA separado** custou **zero**. Aqui está tudo empilhado num adapter só.

**Próximo passo recomendado:** dois adapters (agêntico + resumo) com roteador, medindo cada um
na sua régua e o par no conjunto — em vez de procurar a dose que equilibra duas capacidades num
adapter só.

⚠️ **E o que continua verdade:** `atendimento útil` e `código pass@1` seguem em 0% em todos os
artefatos, e nenhuma intervenção deste eixo os tocou.

---

## Fontes externas que chegaram junto e falam com isto

Da triagem de ~4.000 resumos do arXiv (2026-08-31, 6 agentes):

- **`2604.17930`** — em GPT-2 de **124M**, injetar **1% de sintético dirigido** conserta 8 dos 9
  piores paradigmas do BLiMP (20,9% → 69,4%) com o agregado preservado — **e uma capacidade
  resiste mesmo assim**. Dado dirigido em dose pequena funciona nesta escala, e nem tudo cede.
- **`2608.12426`** — 369.753 checagens: um modelo que passa restrições individuais a **41%**
  satisfaz as oito juntas em **5,7%**, e restrições **estruturais** custam 2× mais que lexicais.
  Resumo é restrição composta — a falha pode ser multiplicativa, o que explica por que mover
  `comprimiu` sozinho não basta para `útil`.
- **`2606.04272`** — composição do dado de pré-treino é alavanca mais forte que escala do
  modelo, e as capacidades gerais **degradam depois do SFT**. É o achado próprio deste projeto,
  confirmado de fora.
