# Mundo simulado aberto — o holdout de 85 casos media memorização de catálogo

> **2026-08-23.** US$ 0. O E5 e o E6 apontaram o mesmo gargalo: com 85 casos e ±10 pp de
> intervalo, nenhuma medição futura distingue intervenção de ruído. A ampliação do mundo
> simulado destrava holdout, rejection sampling e resolução de uma vez — e a primeira medição
> nela mostrou que **o holdout antigo usava as mesmas 14 ferramentas do treino**.

---

## 1. O que existe agora

| | holdout antigo | **holdout aberto** |
|---|---:|---:|
| casos com ferramenta | 85 | **600** |
| **pontuados por execução** | **61** (24 eram string — E5c) | **600** |
| casos de texto (over-calling) | 65 | 300 |
| ferramentas distintas | 14 | 12 validadas de 747 |
| intervalo de Wilson a p≈0,35 | ±10 pp | **±4 pp** |

Sobraram **1.206** casos validados para rejection sampling — o único componente que o E6 mediu
como positivo e estável.

⚠️ **Concentração declarada:** `calculate_discount` é 59% do holdout e `calculate_tip` 31%.
Ele resolve muito melhor o eixo "acerta a conta" e mede "sabe usar ferramenta" de forma mais
estreita. Os dois holdouts continuam reportados lado a lado — trocar um pelo outro no meio de
uma comparação seria mudar o instrumento entre os grupos (§2g).

---

## 2. ⭐ O que torna isto honesto: o dataset traz o resultado correto

A armadilha óbvia seria um simulador genérico que só faz hash de `(ferramenta, args)` —
igualdade exata disfarçada de execução, o defeito que o E5c documentou em `web_search`. Ampliar
assim multiplicaria os casos e pioraria a régua.

O que evita isso: **cada exemplo do gigaverbo tem a chamada seguida do resultado computado.**

```
{"tool":"calculate_tip","args":{"bill_amount":50,"tip_percentage":15}} -> {"tip_amount":7.5}
```

Então cada fórmula é conferida contra **milhares de pares (entrada, resultado) reais**, e
"implementei a semântica certa" virou número medido. Corte: **95%**. Quem não reproduz vira
**eco rotulado**, não semântica falsa.

| aprovadas (12) | acerto |
|---|---:|
| `calculate_discount` (1.761 casos) | **99,9%** |
| `calculate_tip` (669) | 99,3% |
| `calculate_area` (158) | 99,4% |
| `calculate_bmi` (227) | 98,7% |
| `calculate_tax` (272) | 97,8% |
| +7 menores | 100% |

Reprovadas e rebaixadas a eco: `calculate_loan_payment` (74,3%), `calculate_age` (85,1%),
`calculate_interest` (93,4%), `convert_currency` (80,1%), `calculate_age_difference` (0% — é
outra semântica: diferença entre datas, não idade).

### As quatro fórmulas erradas que a validação pegou

Sem ela eu teria chamado o resultado de "execução":

| ferramenta | args | meu | dataset | causa |
|---|---|---:|---:|---|
| `calculate_tax` | `tax_rate: 0.2` | 100 | 10.000 | 0,2 é **fração** (medido: 107 de 3.385 vêm assim) |
| `calculate_loan_payment` | `term: 60` | 238 | 955,65 | 60 são **meses** |
| `calculate_age` | nasceu 1990 | 35 | 31 | referência é **2021** (230 de 238 casos) |
| `convert_currency` | 1000 USD→EUR | — | — | cotações do dataset, não reais |

Todas as constantes vieram **derivadas do corpus**, não escolhidas.

⚠️ E uma sutileza que quase passou: em `convert_currency`, a divergência de cotação **não é
defeito de pontuação** — previsto e referência passam pela mesma função, então a constante é
indiferente. Adotar a do dataset serve para a VALIDAÇÃO ficar significativa, não para a régua
funcionar.

---

## 3. 🔴 O achado: o modelo reverte para o catálogo em que treinou

Adapter do E2 no holdout aberto: **204/600 = 34,0%** [30,3%–37,9%].

| ferramenta | prevê a certa | executa |
|---|---:|---:|
| `calculate_discount` | 336/353 = **95%** | 199 = 56% |
| `calculate_tip` | 37/187 = **20%** | 2 = 1% |

Nos 130 casos restantes de gorjeta o modelo emite **`calculator`** — ferramenta do catálogo de
14 em que ele treinou, e que não está no catálogo do prompt.

**Decomposição das 396 falhas:**

| modo | n | % |
|---|---:|---:|
| ferramenta errada ou nenhuma | 202 | 51% |
| ferramenta certa, argumentos errados | 194 | 49% |
| ↳ destes, **omitiu argumento obrigatório** | **145** | 75% |

⭐ **O holdout de 85 casos usa as mesmas 14 ferramentas do treino** — ele media desempenho
dentro da distribuição e nunca poderia mostrar isto.

⚠️ **E não se compara 34,0% com os 64,7% do holdout antigo**: itens diferentes, ferramentas
diferentes, dificuldade diferente. O que se pode dizer é que existe agora uma régua que mede
generalização de catálogo, e que ela encontra um buraco que a outra não alcançava.

---

## 4. Dois defeitos meus no construtor, e as guardas que ficaram

### 🔴 17,3% do holdout era impossível — e a guarda existente não pega

Primeira versão: `calculate_tip` deu **0/158**. Fui atrás por implausibilidade e achei que
**37,5% dos diálogos do gigaverbo são multi-turno** — o assistente pergunta os valores e o
usuário responde no turno seguinte. Eu pegava só a **primeira** fala do usuário e descartava
justamente os números. Referência `{"bill_amount": 50}` para um pedido onde o 50 não aparece.

⚠️ A guarda *"os gabaritos executam"* **passa** nesse caso: a chamada de referência é
perfeitamente válida — ela só não é **derivável do pedido**. São condições diferentes, e o
projeto só tinha a primeira.

✅ **Guarda nova (respondibilidade):** todo número da referência tem de aparecer no contexto.
Descartou 270 casos; verificado depois: **zero não-deriváveis restantes**.

### 🔴 Duas métricas mediam outra coisa

| métrica | lia | real | causa |
|---|---:|---:|---|
| `argumentos identicos` | 0/600 = **0,0%** | 198/600 = 33,0% | `==` cru em dict: o modelo emite `"200"`, a ref tem `200` — comparava **tipo** |
| `JSON valido` | 5/600 = 0,8% | 404/600 = 67,3% | validava contra o catálogo de **14**, não o do prompt do exemplo |

⭐ No holdout antigo `argumentos identicos` lia 37,6% porque ali o modelo emitia inteiros: **a
régua estava medindo o formato do número**, e só se percebe isso quando o formato muda.

✅ Controle obrigatório: as correções são **inertes no holdout antigo** — 75/85 e 32/85,
idênticos. Inclusive depois que percebi que minha primeira versão afrouxava a validação de
schema (75 → 76) e voltei atrás: onde o schema existe ele tem prioridade sobre o nome.

---

## 4b. 🔴 O rejection sampling amplifica o que o modelo já faz — medido

Rodado nos 1.206 casos de catálogo inédito (+837 de texto, proporção 1,44:1 preservada para
não deslocar a decisão). k=8, 4 h de GPU local, US$ 0.

| ferramenta | entrada | reforço | **rendimento** | pares |
|---|---:|---:|---:|---:|
| `calculate_discount` | 710 | 589 | **83%** | 1.528 |
| **`calculate_tip`** | **374** | **0** | **0%** | **0** |
| `calculate_bmi` | 14 | 9 | 64% | 23 |
| `calculate_tax` | 35 | 5 | 14% | 18 |
| `calculate_sales_tax` | 40 | 2 | 5% | 6 |
| **total** | **1.206** | **848** | 70% | **2.129** |

🔴 **374 prompts de gorjeta entraram e zero saíram** — nenhum exemplo de reforço, nenhum par,
em 2.992 amostras. A aritmética é idêntica à do desconto (`base × taxa / 100`); o que separa
83% de 0% é o modelo associar "gorjeta" a `calculator`, ferramenta que ele memorizou, em vez
de ler o catálogo do prompt.

⭐ **Consequência estrutural: o RS concentra em vez de preencher.** A entrada era 58,9%
desconto; o reforço saiu **69,5%**, e os pares **71,8%**. Treinar nele empurraria o modelo
ainda mais para a ferramenta que ele já domina, sem tocar no buraco.

⚠️ **Isso não é falha da execução — é o método.** RS colhe da cauda existente; onde a
capacidade é 0%, não há cauda. O `all_wrong` (664 prompts, 55,1%) é exatamente onde está a
capacidade que falta, e é de onde o RS não tira nada por construção.

### O que a rodada refutou da minha própria previsão

Eu tinha registrado que a colheita seria "quase vazia". Não foi: **2.129 pares** contra 930 no
mundo fechado, e `misto` subiu de 32,7% para **44,9%**. O que mudou foi a outra ponta —
`all_right` desabou de 335 prompts para **1**. Em catálogo inédito o modelo quase nunca acerta
*sempre*, mas acerta *às vezes* com mais frequência: é o regime de mais sinal de preferência,
não menos. A previsão errou o sinal e acertou o efeito prático.

### E o lado do texto funcionou

Reforço final **848 tool / 601 text = 58,5%**, contra os 59,3% do original — a colheita
simétrica manteve a proporção quase exata. ⚠️ Mas a razão de rejeição diz algo: 3.264 amostras
de texto foram descartadas por **"chamou ferramenta"** quando não devia. O over-calling não é
só alto na régua; é o modo dominante nas amostras.

---

## 5. O que fica

1. **Toda comparação agêntica futura roda nos dois holdouts.** O antigo mede dentro da
   distribuição, o aberto mede generalização de catálogo. Um número só esconde qual dos dois.
2. **O alvo agora tem nome:** 51% das falhas é substituição de ferramenta, 37% é omissão de
   argumento obrigatório. Nenhum dos dois é resolvido por retentativa (E5) nem por preferência
   (E6) — são de treino.
3. **1.206 casos validados esperando rejection sampling**, com catálogos diversos — que é
   exatamente o que falta ao modelo.
4. ⚠️ **A concentração do holdout (90% em duas ferramentas) é a próxima dívida.** Ampliar exige
   validar mais fórmulas, e as que sobraram são as difíceis: as que o dataset registra de forma
   inconsistente consigo mesmo.
