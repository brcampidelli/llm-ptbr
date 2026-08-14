# Os testes de US$ 0 — o que eles derrubaram (2026-08-13)

O estudo de ~60 papers ([estudo-bee-350m.md](estudo-bee-350m.md)) terminou com sete verificações
que custam **zero de GPU alugada** e que precisavam rodar **antes** de comprometer os US$ 300 do
Bee-350M. Este documento é o resultado delas.

⭐ **Duas das três primeiras derrubaram uma premissa** — uma do estudo, duas do próprio projeto.

---

## 1. Auditoria de repetição interna do corpus — **o item de maior ROI do estudo não se aplica**

### O que se esperava

arXiv:2606.24998, medido em **344M** (o tamanho exato do Bee-350M): quando documentos repetidos
consomem **10% do orçamento de FLOPs**, o treino equivale a usar só **67% dos FLOPs** — um terço da
computação perdido, e **nada no log reclama**. O estudo classificou isso como o **quarto membro** da
família de falhas silenciosas e estimou retorno de **até US$ 100 dos US$ 300**.

### Como foi medido

`bee/auditar_repeticao.py` — **censo**, não amostra. Lê o `train.bin` que o treino vai efetivamente
consumir (o `bee/medir_dedup.py` anterior estimava por amostra de dois parquets da fonte).

Duas camadas: hash de 64 bits do documento inteiro (exato) e MinHash bottom-16 sobre 5-gramas de
**token** com LSH de 4 bandas (quase-duplicata, Jaccard ≥ 0,80).

### Resultado — censo de 27.463.666 documentos / 21.722.230.888 tokens

| | documentos | tokens | % dos FLOPs |
|---|---:|---:|---:|
| únicos | 27.381.332 | 21.660.374.737 | **99,715%** |
| repetido 2× | 74.444 | 56.814.268 | 0,262% |
| repetido 3–10× ⚠️ *o pico do dano* | 5.123 | 3.501.686 | **0,016%** |
| repetido 11–100× | 1.728 | 1.044.096 | 0,005% |
| repetido 101–1000× | 1.039 | 496.101 | 0,002% |
| **duplicata EXATA (≥2)** | **252** | **58.924** | **0,000%** |

**Guarda de fechamento:** 21.749.694.554 contra 21.749.694.553 — erro **0,0000%**. Um censo que
perde documento não é censo; este fecha.

### Veredito

> **O corpus está limpo. 0,28% dos FLOPs em documentos repetidos — 36× abaixo do cenário do
> paper.** A faixa que mais dói (3–10×) é **0,016%**.

O `fineweb-2` já aplica MinHash na origem, e isso aparece na medição. **Os "até US$ 100
recuperáveis" não existem** — a conta do Bee-350M volta a ser a conta simples.

⚠️ **Ressalva honesta:** o LSH bottom-16 com 4 bandas × 4 tem recall de ~88% em Jaccard 0,80, então
a taxa real fica perto de **0,32%**, não 0,28%. A diferença não muda o veredito por duas ordens de
grandeza, e a camada exata (hash do documento inteiro) é exata.

**Custo: US$ 0 e 42 minutos.** O valor de um teste barato não é só o que ele confirma — foi ele que
evitou um esforço de deduplicação que renderia zero.

---

## 2. Auditoria do holdout agêntico — **17,6% dos itens são impossíveis por construção**

### O que se suspeitava

A refutação adversarial levantou: *"ninguém mediu quantos dos itens não resolvidos são impossíveis.
Se ~25% do conjunto for insolúvel por construção, 72,9% é o teto do BENCHMARK — e nenhum tamanho de
modelo move teto de benchmark."*

O projeto tem precedente: um avaliador de mundo fechado já mediu **23,5%** onde o real era **57,6%**.

### Como foi medido — `comeia/eval/auditar_holdout.py`

Dois testes objetivos, sem julgar "isso parece difícil":

**(A) Exige a string literal?** Perturbação que **preserva o sentido**: reordenar as palavras. Uma
query de busca com as mesmas palavras em outra ordem é a mesma busca. Se o resultado muda, nem um
modelo perfeito passa — o item mede ortografia, não capacidade.

**(B) Exige informação que o usuário nunca deu?** Palavra de conteúdo no gabarito ausente do pedido.

### ⚠️ Os falsos positivos que o teste automático produziu — e a correção

O detector automático errou três vezes, e cada erro ensinou algo:

| erro | por quê | correção |
|---|---|---|
| `calculator` marcado como sensível | o sufixo corrompedor gera erro de sintaxe. **Medido:** `sqrt(1444)` e `38` **batem** — o executor compara **valor** | veredito humano explícito |
| `get_weather "Rio de Janeiro"` marcado como literal | reordenar dá *"Janeiro de Rio"* — **nome próprio não é sacola de palavras** | (A) restrito a `query`/`busca` |
| `run_python` marcado como sensível | devolve só `{"compila": true}` | veredito humano explícito |

Os nove itens ambíguos foram lidos **à mão** e o veredito de cada um está no código, com
justificativa — o número é reproduzível e auditável.

### Resultado

| categoria | itens | % |
|---|---:|---:|
| gabarito não executa | 0/85 | 0,0% |
| (A) exige a string literal, ordem inclusa | 12/85 | 14,1% |
| (B) exige informação que o usuário nunca deu | 8/85 | 9,4% |
| ⚠️ **impossível por construção (A ∪ B)** | **15/85** | **17,6%** |

Por ferramenta: **`web_search` 12/13** · `http_get` 2/4 · `write_file` 1/2. Todas as outras: zero.

### A causa raiz, e ela é de uma linha

`_web_search` devolve `{"query": query.strip().lower(), ...}` — a comparação por execução
**degenera em igualdade de string**. Medido:

```
"populacao estimada Sao Paulo 2024 IBGE"  ≠  "Sao Paulo populacao estimada 2024 IBGE"
```

Um modelo que escreve a busca **certa** em outra ordem é contado como erro. E há gabaritos que
exigem palavras que o pedido nunca deu: um `"2025"` inventado, um `"IBGE"` inventado, a sintaxe
`site:twitter.com`.

### Veredito

> **Teto máximo alcançável por qualquer modelo neste holdout: 82,4%.**

Contra o pass@16 medido de 72,9%, **ainda sobra ~9,5 pp de folga real** — então o teto **não** é só
do benchmark, e a hipótese não se confirma inteira. Mas os números do projeto estão sistematicamente
deprimidos: relativo ao alcançável, o pass@16 é **88,5%** e a execução (65,9%) é **80,0%**.

### 🔴 Dois problemas de dado achados de passagem

1. **Letra de música sob copyright dentro do holdout.** O item `write_file` exige reproduzir
   *Imagine* (Lennon) na íntegra — o executor compara a contagem de bytes. Além de impossível, é
   conteúdo protegido num dataset que o projeto publica. **Deve sair.**
2. **Meta-prompt de geração vazado como pedido do usuário.** Um item `run_python` tem como
   "mensagem do usuário" o texto *"Goal: Generate 15 new and varied user requests that require the
   `run_python` tool"* — a instrução usada para **gerar** os exemplos entrou como se fosse um. Ele é
   solúvel (qualquer código que compile passa), mas é dado corrompido — e **é preciso conferir se o
   mesmo vazamento está no conjunto de treino.**

### O que fazer

**Não** reescrever o executor às pressas: mudar `_web_search` altera **todos** os números agênticos
já publicados. O caminho é versionar — `tools_exec` v2 comparando a query por **sacola de palavras
de conteúdo** (ou Jaccard ≥ 0,8), re-medir tudo, e reportar as duas séries lado a lado com a data da
troca. Enquanto isso não acontece, **todo número agêntico do projeto deve vir com a nota de que o
teto do holdout é 82,4%, não 100%.**

---

## 3. A curva de pass@k (k até 256)

*Em execução — `comeia/eval/eval_passk_curva.py`, n=256 amostras por exemplo, nos dois checkpoints
(pré e pós-autoaprendizado) para o diff por problema.*

---

## Nota de método — uma lição que se repetiu duas vezes hoje

**A guarda deste próprio script estava quebrada.** O campo do holdout é `kind="tool_call"`, e eu
escrevi `if tipo != "tool": continue` — a guarda pulou os 85 exemplos, verificou **zero** referências
e imprimiu `✅` assim mesmo. É o item que a regra global chama de *"guarda fora do fluxo não guarda
nada"*, agora pela segunda vez no mesmo projeto.

**Correção que ficou:** toda guarda conta quantos itens verificou e **aborta se o número for zero**.

**E o throughput mentiu de novo.** A primeira medição de geração deu **3.865 ms/amostra**; com a CPU
livre, **109 ms** — 35× de diferença, porque a auditoria do corpus estava rodando e a geração de um
modelo de 151M é **CPU-bound**. A regra do projeto (medir em regime, três leituras coincidentes) vale
para a máquina inteira, não só para o passo de treino.
