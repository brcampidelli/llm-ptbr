# Diversidade de catálogo — 10,9% → 85,8%, e a régua que tornou o número possível

> **2026-08-24.** US$ 0 de GPU paga. O E5, o E6 e o rejection sampling apontaram três vezes
> para o mesmo lugar: o modelo revertia para as ferramentas que memorizou, e nenhuma
> intervenção de runtime ou de preferência alcançava isso. Este estágio ataca por treino, com
> uma régua construída do zero — porque a anterior não conseguia medir o que importava.

---

## 1. O resultado

| modelo | executou | ferramenta certa | args idênticos | over-calling | JSON válido |
|---|---:|---:|---:|---:|---:|
| **adapter E2** (treinado em 14 ferramentas) | **10,9%** | 49,3% | 2,7% | **59,4%** | 38,7% |
| e7-diverso semente 42 | **86,2%** | 99,4% | 64,6% | **0,0%** | 81,8% |
| e7-diverso semente 43 | **85,3%** | 98,6% | 64,5% | 0,2% | 81,2% |
| **média · amplitude** | **85,8% · 0,9 pp** | 99,0% | 64,6% | 0,1% | 81,5% |

**Os dois eixos se moveram juntos** — condição declarada antes de rodar. Subir execução chamando
mais não valeria nada; aqui a execução subiu 75 pp **e** o over-calling zerou.

⭐ **A variância de semente caiu 5×**: o E6 mediu 4,7 pp com n=85; aqui é **0,9 pp** com n=1000.
Ampliar o holdout não melhorou só o intervalo de confiança — reduziu o ruído de rodada, que era
o que impedia o E6 de decidir.

### Três ressalvas que vão junto do número

⚠️ **Não é generalização para ferramenta inédita.** 121 das 123 ferramentas do holdout estão no
treino. O que foi medido é: **pedido inédito, tupla de argumentos inédita, catálogo variável**.
Separar também por nome de ferramenta deixaria poucas de fora e o holdout perderia o n.

⚠️ **A comparação é contra um adapter de outro regime.** O E2 viu 14 ferramentas; este viu 123.
Parte dos +75 pp é "treinou no domínio certo", não "receita melhor".

⚠️ **A proporção tool:text é herdada, não otimizada.** Usei 1,44:1 (a do corpus do E3). O
projeto tem duas medições em direções opostas sobre ela — o E4 viu colapso de recusa nessa
razão, o E6 viu over-calling cair. Aqui não colapsou; a razão certa segue sendo decisão a medir.

---

## 2. ⭐ O que destravou: três tipos de argumento, e a classe é MEDIDA

O `mundo_aberto.py` só pontuava por execução ferramenta cuja **fórmula** desse para escrever — e
no gigaverbo isso selecionava exatamente as **aritméticas templadas**. Parei de tratar "eco"
como defeito único:

| tipo | equivalência correta | taxa medida |
|---|---|---|
| **extraído** — o valor está literalmente no pedido | igualdade normalizada **é** a semântica | `send_email.recipient` 94,8% |
| **temporal** — "amanhã às 15h" → `2026-03-15T15:00` | normaliza e compara | `create_todo.due_date` 56,7% |
| **formulado** — o modelo redige | não há critério exato: **fica de fora** | `send_email.subject` 0,0% |

A divisão saiu quase **binária** (~95% ou ~0%), e a validação **split-half deu 96,7%** de
concordância entre metades do corpus. Sem isso, "derivei do corpus" seria um limiar pegando
ruído.

**Resultado:** 149 ferramentas com ≥1 argumento pontuável, cobrindo **83,6% das chamadas** e
**4.293 tuplas distintas** — contra 181 do escopo por fórmula.

⚠️ **Excluir os formulados facilita o escore**, então a régua imprime sempre a cobertura
(52,7% dos argumentos pontuados na base) e o modo de cada caso.

---

## 3. A régua anterior era 600 cópias de 87 problemas

Antes de chegar aqui eu anunciei um holdout "de 600 casos, ±4 pp". **Era falso:**

| | anunciado | real |
|---|---:|---:|
| casos | 600 | 600 |
| **problemas distintos** | — | **87** |
| maior problema | — | **250× = 42% do holdout** |
| Wilson | ±4,0 pp | **±10,3 pp** — o antigo era ±10,4 |

A causa foi a minha regra de admissão: aceitar só ferramenta com semântica validável escolhe as
templadas. `calculate_discount` tem 1.450 chamadas e **52** tuplas de argumento distintas.
**Validabilidade e diversidade são anticorrelacionadas neste corpus.**

O holdout novo: **1.000 casos, 1.000 tuplas distintas, 123 ferramentas, maior delas 9,2%,
Wilson ±2,8 pp**.

---

## 4. Três separações erradas antes da certa

| tentativa | por que vazou |
|---|---|
| hash do prompt inteiro | 93% dos pedidos apareciam no treino — o *function masking* do E3 **cria** o mesmo pedido com e sem a ferramenta |
| dedup por tupla | 76,2% ainda tinham o **prompt exato** no treino |
| **componente conexo** (pedido **ou** tupla) | 0 vazamentos |

⭐ **A unidade de separação tem de ser tudo que é compartilhado.** Isso é um grafo, e a
separação correta é por componente conexo.

⚠️ **E mesmo assim vazaram 265 negativos** por um descasamento no meu roteamento. Em vez de
caçar o descasamento, pus uma **guarda posterior** que filtra o holdout final contra o treino
final — 520 removidos, e o resultado passou a ser 0/1480. **Guarda que depende de a construção
estar certa não é guarda: é a mesma suposição escrita duas vezes.**

---

## 5. Outros defeitos que a construção revelou

- 🔴 **Colisão de nome:** `send_email` existe nas 14 simuladas **e** no gigaverbo, com esquemas
  diferentes. Minha hierarquia decidia pelo nome e mandava **176 de 1.000** referências para a
  fórmula errada. O critério certo é a **referência**: só se ela executa sob a fórmula é que a
  fórmula descreve aquela chamada.
- 🔴 **`argumentos identicos` lia 0/600** porque o `==` cru comparava **tipo** (`"200"` × `200`).
  No holdout antigo lia 37,6% porque ali o modelo emitia inteiros — **a régua media o formato do
  número**.
- 🔴 **`JSON valido` lia 5/600** porque validava contra o catálogo de 14, não o do prompt.
- ⚠️ **Rótulo enganoso:** a régua chamava de `recusado` tanto "o modelo escolheu outra
  ferramenta" (erro do modelo) quanto "não há critério" (limite do instrumento). Agora são
  `ferramenta_errada` e `sem_criterio`.

✅ Todas as correções verificadas como **inertes no holdout antigo** — 55/85, 75/85, 32/85
idênticos — inclusive depois que percebi que a primeira versão afrouxava a validação de schema.

---

## 6. O modo de falha depende da família da ferramenta

Decomposição das 891 falhas do adapter E2 no holdout diverso:

| modo | n | % |
|---|---:|---:|
| não produziu chamada | 333 | 37,4% |
| ferramenta **errada** | 174 | **19,5%** |
| ferramenta certa, **argumentos errados** | 384 | **43,1%** |

⭐ No holdout aritmético a ferramenta errada era **51%** das falhas. Aqui é 19,5%, e a perda
migrou para os argumentos. **Aritmética cobra roteamento; ferramenta diversa cobra extração de
valor** — e um holdout de uma família só (o antigo era 90% de uma) não mostra a diferença.

---

## 7. O que fica

1. **A régua é o ativo.** 1.000 problemas distintos, 123 ferramentas, ±2,8 pp, variância de
   semente 0,9 pp. Toda comparação futura roda nela e no holdout de 85 — o antigo mede dentro
   da distribuição de 14 ferramentas, o novo mede leitura de catálogo.
2. **O que E5, E6 e RS não alcançavam era de treino.** Retentativa deu +1,2 pp, preferência
   +2,4 pp, rejection sampling concentrou no que o modelo já fazia. Dado diverso deu +75 pp.
3. ⚠️ **A pergunta seguinte é ferramenta inédita** — separar por nome, aceitar o n menor, e
   medir. É o único eixo de generalização que este experimento não tocou.
