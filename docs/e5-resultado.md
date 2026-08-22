# Estágio 5 — agêntico sem treino: as duas alavancas do plano falharam, e a régua era o problema

> **2026-08-22.** US$ 0 de GPU paga — rodou inteiro na RTX 5070 de 8 GB. O E5 existia para
> colher os 27,7 pp de folga já mapeados, por três caminhos sem treino. **Dois dos três
> caíram na medição**, e o que sobrou não estava no plano: a régua colapsava sob amostragem,
> e um terço do holdout é pontuado por igualdade de string em vez de execução.

---

## 0. A linha de base teve de ser refeita antes de qualquer coisa

O critério do plano era **"57,6% → ≥65%"**. Os 57,6% são do **Bee-150M**. O E2 já entregou
**64,7%** no 350M — ou seja, o alvo estava satisfeito pela escala + SFT antes de o E5 existir.
Medir o E5 no 350M contra o 150M teria creditado ao estágio um ganho que foi do anterior:
§2g em lugar novo.

Linha de base refeita, mesmo modelo, mesma régua: **65,9%** (56/85), depois da correção do
executor da §3.

---

## 1. 🔴 5b — a premissa é falsa: o executor NÃO é um verificador forte

O plano dizia: *"modelo pequeno não se autocorrige, mas o executor determinístico **é** o
verificador forte. k=2–4 colhe a parte sintática da folga sem treinar nada."*

Três políticas, todas decidíveis **sem gabarito** (que é a condição de ser realizável):

| política | acerto | vs greedy |
|---|---:|---:|
| **A.** greedy uma vez | 56/85 = **65,9%** | — |
| **B.** amostrar k=4, servir a 1ª que executa | 53/85 = 62,4% | **−3,5 pp** |
| **C.** greedy; se não executar, cair para B | 57/85 = **67,1%** | **+1,2 pp** |

⭐ **B é pior que não fazer nada.** E o motivo é direto: **95,3% das chamadas executam e só
62,4% estão certas.** "Executa" não filtra quase nada — o laço quase nunca dispara, e quando
dispara serve uma amostra a temperatura 0,8, que é pior que o greedy.

**C rendeu +1 caso.** O fallback disparou em 10 dos 85 e resgatou 1.

### ⚠️ E +1,2 pp está abaixo do ruído

Três rodadas **idênticas** de k=4 (mesma config, seed livre), medidas por acaso ao longo do
estágio:

| rodada | pass@1 | pass@4 |
|---|---:|---:|
| e5-hib-k4 | 0,562 | 0,694 |
| e5-k4 | 0,579 | 0,706 |
| e5-pol-k4 | 0,588 | 0,682 |
| | | **amplitude 2,3 pp** |

O efeito de C é **metade do piso de ruído**. O critério do plano era folga absoluta ≥7 pp.
**Veredito: 5b NÃO entrega.**

### O teto, decomposto — e por que ele não é colhível

Dos 85 casos com ferramenta:

| | casos | |
|---|---:|---|
| greedy acerta | 56 | — |
| greedy **executa mas erra** | **19** | invisível sem gabarito |
| greedy **não produz chamada executável** | **10** | única janela do harness |

Um harness só enxerga a terceira linha: teto absoluto **+11,8 pp**, realizado **+1,2 pp**.
Os 19 da segunda linha são **22,4 pp** que o `pass@k` anuncia e nenhuma política de runtime
alcança — é essa a diferença entre "há cauda" e "dá para colher".

---

## 2. ⭐ 5c — a premissa do paper não vale aqui; o defeito é outro

O 5c existia para segmentar por **idioma do argumento** (arXiv:2601.05366: o modelo escolhe a
ferramenta certa e escreve o parâmetro no idioma do usuário, violando convenção inglesa).

**Isso é 1 caso em 30.** As referências deste holdout já usam português nos campos livres
(`{"city": "Brasília"}`, `{"query": "últimas notícias..."}`) e inglês só nos identificadores
(`ticker: AAPL`, `/var/log`) — escrever em português é o comportamento **certo** aqui.

Modo de falha real dos 30 que falharam:

| modo | n | % |
|---|---:|---:|
| sem JSON parseável | 9 | 30,0% |
| valor diferente | 7 | 23,3% |
| ferramenta errada | 7 | 23,3% |
| chaves diferentes | 6 | 20,0% |
| **idioma** | **1** | **3,3%** |

### 🔴 E a segmentação que importava: como o caso é PONTUADO

| | acerto |
|---|---:|
| ferramentas pontuadas por **execução** (11 delas, 61 casos) | **77,0%** |
| ferramentas pontuadas por **eco de string** (3 delas, 24 casos) | **33,3%** |

**16 das 30 falhas** estão em `web_search`, `http_get` e `summarize_url`. Motivo:

```python
def _web_search(a):
    (q,) = _exigir(a, "query")
    return {"query": str(q).strip().lower(), "resultados": BUSCA_FIXA}
```

`BUSCA_FIXA` é idêntica para todos, logo não discrimina nada: **a comparação inteira é
igualdade exata da string da query**, vestida de equivalência funcional. Qualquer paráfrase
igualmente boa conta como erro.

Casos lidos um a um (a evidência é a leitura, não a tabela):

- ref `"filmes em cartaz Brasília hoje"` × previsto `"filmes em cartaz nos cinemas de Brasília
  hoje"` — as duas buscam a mesma coisa;
- ref `"população estimada São Paulo 2024 IBGE"` × previsto `"população São Paulo 2024"` — **a
  referência inventou "IBGE", que o usuário não pediu; a previsão é mais fiel que o gabarito**;
- `max_results` aparece em umas referências e não em outras, sem nada no pedido que decida. O
  modelo sempre emite `max_results: 5` e é reprovado por sorteio em ~metade delas.

⚠️ **Declarado, não consertado.** Dizer que duas buscas são "a mesma" exige um critério que
este projeto não tem, e inventar um (sobreposição de palavras, por exemplo) seria escolher o
limiar que produz o número desejado. Ficou a constante `PONTUADAS_POR_ECO` em `tools_exec.py`
e a divisão impressa em toda análise.

---

## 3. O que estava quebrado e foi consertado

### 3.1 🔴 A régua colapsa sob amostragem: 0,6% num modelo que faz 65,9%

`pass@4` deu **0,0%** nos primeiros 12 exemplos, onde o greedy faz 80%. Contradição de margem
absurda ⇒ o defeito está no aparato.

Saída crua, mesmo pedido:

```
greedy:   {"tool": "get_stock_price", "args": {...}}<|im_start|>       ← 42 tokens, para
amostra:  {"tool": "get_stock_price", "args": {...}}\x1e\nPara você... ← 320 tokens, não para
```

**A chamada está perfeita nos dois.** O que muda é o token de fim. O `paradas.py` já
documentava que o LoRA termina em `<|im_start|>` (id 1) em vez de `<|im_end|>`, e o incluía na
parada de propósito — mas **sob amostragem o terminador escapa para bytes de controle
vizinhos** (`\x00`, `\x0f`, `\x1e`; ids 192–225), que não param nada. A geração enchia 320
tokens e o parser recebia chamadas concatenadas.

Duas correções, ambas de runtime:

1. **`--parar-controle`** — os 30 ids de byte C0 entram no conjunto de parada. Derivados do
   tokenizador, não adivinhados.
2. **`primeiro_objeto()`** — parser que lê a primeira chamada completa, como um harness real.

⚠️ **Deliberadamente NÃO inclui os bytes altos** (0x80–0xF7), que também aparecem no fim das
gerações. Em BPE de byte um acentuado *é* uma sequência desses bytes — o `í` de "Brasília" sai
como 0xC3 0xAD, e cada um sozinho decodifica para U+FFFD. Parar neles truncaria português
válido no meio da palavra. Os C0 são seguros porque 0x00–0x1F nunca ocorre dentro de UTF-8
multibyte. **A diferença entre as duas faixas é a diferença entre uma guarda e um bug.**

**Resultado: 0,0% → 57,9% de pass@1 amostrado, sem retreinar nada.**

#### As duas guardas antes de eu confiar nisso

Afrouxar a régua a favor da própria hipótese é o erro que parece confirmação (§2g). Então:

- **as duas réguas dão idêntico no greedy** — 55/55 execução, 12/12 over-calling. A régua do
  harness não é mais frouxa em geral; ela só difere onde o terminador escapa.
- **adicionar os 30 ids de parada não muda nada no greedy** — a intervenção é inerte onde deve
  ser inerte.

As duas réguas ficam reportadas **lado a lado**, sempre. A diferença entre elas *é* o tamanho
do problema de terminação.

### 3.2 Barra final no caminho

`_list_dir`/`_read_file`/`_write_file` normalizavam acento, caixa e espaço — "porque ortografia
não deve decidir acerto" — mas não a barra final. `/home/usuario/documentos/` e
`/home/usuario/documentos` davam `listagem_id` diferente (2643245086 × 2755588874), nos dois
campos, porque `_det` também chama `_norm`.

Corrigido com `_norm_caminho()` separada, testada para **não** colapsar caminhos genuinamente
diferentes. Efeito medido e declarado: **+1 caso, 64,7% → 65,9%**.

### 3.3 ⚡ 18× no avaliador

O caminho `k>1` gerava um exemplo por vez, com o comentário afirmando que
`num_return_sequences` "já enche o batch sozinho". Não enche: batch 4 num modelo de 350M deixa
a GPU em **8%** — o gargalo é lançamento de kernel por passo de decodificação. Dava ~100 s por
exemplo e projetava **4 horas**.

Batelando B exemplos × k amostras: **13m30**, GPU a 59%.

⚠️ Diagnóstico por `py-spy dump --locals` (`i: 12` depois de 20 min), não por dedução — o log
só imprime a cada 20 exemplos e não havia saída nenhuma para ler. É a mesma lição que já está
no docstring da própria função, aplicada de novo.

---

## 4. O que o E5 entrega, honestamente

| item | efeito |
|---|---|
| régua funcionando sob amostragem | 0,0% → 57,9% (pass@1) — **medição, não capacidade** |
| barra final no executor | +1,2 pp (+1 caso) |
| política híbrida (5b) | +1,2 pp (+1 caso) — **abaixo do ruído de 2,3 pp** |
| avaliador 18× mais rápido | 4 h → 13 min |
| 5c | premissa refutada; 33% do holdout pontuado por string |

**Ganho de capacidade real: nenhum.** O E5 não colheu folga — ele descobriu que boa parte da
folga anunciada não existia (era régua) e que a parte que existe não é alcançável por runtime
(precisa de gabarito).

---

## 5. Consequências para os estágios seguintes

1. **E7 (GRPO agêntico) perde seu gatilho.** O plano diz "só rodar se o Estágio 5 render e o
   E6 não". O E5 não rendeu.
2. **O `web_search` precisa de decisão antes de qualquer número agêntico novo.** Com 24 dos 85
   casos pontuados por eco, mover a taxa agregada é em boa parte mover uma loteria de string.
   Ou o holdout muda, ou toda comparação futura reporta a divisão execução/eco.
3. **Os 19 "executa mas erra" são o alvo real.** São 22,4 pp, não são detectáveis em runtime, e
   nenhuma quantidade de retentativa os alcança. Só treino ou verificador mais forte.
4. ⚠️ **Toda comparação agêntica futura precisa do piso de ruído junto.** 2,3 pp entre rodadas
   idênticas com n=85. Efeito abaixo disso não é efeito.
