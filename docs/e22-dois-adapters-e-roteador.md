# E22 — dois adapters e um roteador: separar recupera as duas capacidades

> **A pergunta:** o E21 mediu que enfiar resumo no adapter agêntico rende `útil` 14,7% e **custa
> 9,0 pp de execução** agêntica. O E2 já havia medido a saída — capacidade em adapter separado
> custou **zero**. Isso replica para o par (agêntico, resumo)?
>
> **Resposta:** ⭐⭐ **sim, e o ganho é maior do que evitar o custo.** Resumo **mais que dobrou**
> (14,7% → **33,3%**) e o eixo agêntico ficou **intacto**, porque o adapter A não foi tocado.
>
> ⚠️ E o resumo **continua perdendo para o `head -2`** por 18,0 pp. A distância caiu de 36,7 para
> 18,0 — está a meio caminho, não resolvido.

---

## A arquitetura

| | corpus | passos | função |
|---|---|---:|---|
| **A** = `e19c-s42` | 6.739 tool + 4.319 negativos úteis | 698 | chamar ferramenta |
| **B** = `e22-texto-s42` | **773 resumo** + 4.319 negativos úteis | 698 | responder em texto |
| **roteador** | `comeia/eval/roteador.py`, 30 linhas, sem GPU | — | escolhe A ou B |

⭐ Os cinco corpora desta sequência (C-full, E20, E21, E22) usam **698 passos**. Só o corpus
muda, então a diferença é atribuível ao dado e não ao volume de treino.

---

## O resultado

| | resumo `útil` | macro agêntica |
|---|---:|---:|
| C-full — 1 adapter, só agêntico | 0,0% | **76,8% ± 0,76** |
| E21 — 1 adapter, tudo junto (6,5% de resumo) | 14,7% | 74,4% |
| **E22 — 2 adapters + roteador** | ⭐ **33,3%** | ⭐ **76,8%** |
| piso LEAD-2 / referência | **51,3%** | — |

### Resumo, condição a condição

| falhas (de 150) | C-full | E21 | **adapter B** | LEAD-2 |
|---|---:|---:|---:|---:|
| `comprimiu` | 150 | 122 | ⭐ **79** | 15 |
| `respondeu` | 33 | 15 | **4** | 0 |
| `sem_numero_inventado` | 41 | 36 | **23** | 0 |
| `sem_entidade_inventada` | 55 | 2 | **1** | 0 |
| `cobriu` | 37 | **6** | 🔴 **26** | 58 |

| | C-full | E21 | **B** | limite |
|---|---:|---:|---:|---:|
| razão de compressão | 0,881 | 0,410 | ⭐ **0,350** | ≤ **0,35** |
| cobertura | 77,8% | 78,0% | 74,8% | — |

⭐ A compressão chegou **exatamente ao limite da régua**. ⚠️ E há uma troca dentro do próprio
resumo: `cobriu` piorou de 6 para 26 falhas — comprimindo mais, o modelo perde fatos. É a tensão
que o `2608.12426` mede em restrições compostas, e ela **só aparece porque as cinco condições vão
no relatório**; o agregado `útil` subindo de 14,7% para 33,3% a esconderia.

### O adapter B no eixo agêntico — 0,0%, e isso é o desenho

```
ferramenta certa    0/536 = 0,0%      under-calling  536/536 = 100,0%
```

Ele **nunca emite chamada de ferramenta**, porque não treinou em nenhuma. Não é falha; é a razão
de o roteador existir.

### O roteador

**954 de 954** (536 tool + 268 texto agêntico + 150 resumo).

⚠️ **E esse é o número menos interessante do experimento.** Este par de tarefas é separável por
uma frase quase única (*"Resuma o texto abaixo"*), então 100% aqui **não é evidência de que
rotear é fácil em geral** — é evidência de que este par é separável.

⭐ O que torna o teste honesto: os exemplos de resumo têm **catálogo de ferramentas no
`system`**, posto ali de propósito (§2u). Sem isso o roteador poderia decidir pela presença do
catálogo — uma característica superficial — e não estaria lendo o pedido.

---

## ⭐⭐ O que isto confirma

É a **replicação do achado do E2 em outro par de capacidades**:

| | dentro do adapter | em adapter separado |
|---|---|---|
| **E2** — multi-turno | −5,9 pp de execução | **zero** |
| **E22** — resumo | −2,4 pp de macro, `útil` 14,7% | **zero**, `útil` **33,3%** |

E acrescenta uma coisa que o E2 não tinha: **separar não só evita o custo, como mais que dobra o
alvo.** Livre da competição com 6.739 exemplos de chamada de ferramenta, o mesmo dado de resumo
rende 2,3× mais.

---

## ⚠️ O que continua em aberto, e o custo real

1. **O resumo ainda perde para o `head -2` por 18,0 pp** (33,3% × 51,3%). Metade do caminho.
2. **Uma semente** para o adapter B, contra três do C-full. Pela §2x isso é direção, não folga.
3. **Só o resumo foi medido no adapter B** (`--so resumo`). As outras oito capacidades dele não
   foram medidas — não posso afirmar que ele não quebrou nada mais.
4. **O custo da arquitetura é real:** dois adapters de 34 MB em memória, mais um roteador que
   tem de estar certo. Um erro de roteamento entrega a tarefa ao adapter que **não sabe fazê-la**
   — e o adapter B falha 100% do agêntico, então o erro é caro.
5. **`atendimento útil` e `código pass@1` seguem em 0%** em todos os artefatos.

---

## A receita que sai daqui, para atendimento e código

1. corpus por capacidade, com a **régua virando a guarda** da geração, validada contra o estado
   quebrado;
2. **catálogo de ferramentas no `system`** dos exemplos, para não criar atalho superficial (§2u);
3. fonte de **texto real**, nunca o gerador do holdout (§2o);
4. **adapter próprio**, não dose dentro do adapter agêntico;
5. o roteador ganha um ramo, e sua acurácia é medida **isolada** antes do fim a fim;
6. ⚠️ e o piso trivial da capacidade vai ao lado do número — sem ele, 33,3% pareceria vitória
   quando ainda perde para copiar duas frases.
