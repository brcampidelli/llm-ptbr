# Ferramenta inédita — a seleção generaliza (96,9%), a extração não (37,7%)

> **2026-08-24.** US$ 0. Último eixo de generalização que faltava: o modelo treina em **112
> ferramentas** e é testado em **37 que nunca viu** — nem elas, nem seus quase-sinônimos.
> Duas sementes.

---

## 1. O resultado

Mesmos 728 itens, mesma régua, comparação pareada:

| modelo | executou | ferramenta certa | args idênticos | over-calling |
|---|---:|---:|---:|---:|
| **adapter E2** (14 ferramentas) | **9,6%** | 50,0% | 0,7% | 28,6% |
| e8 semente 42 | 59,6% | 96,7% | 37,2% | 0,0% |
| e8 semente 43 | 58,1% | 97,1% | 38,2% | 0,0% |
| **média · amplitude** | **58,9% · 1,5 pp** | **96,9% · 0,4 pp** | 37,7% | 0,0% |

**McNemar: +365 discordantes a favor, −1 contra, p = 0,000.**

⭐⭐ **A seleção de ferramenta generaliza quase por completo: 96,9% em ferramentas nunca vistas.**
O modelo lê o catálogo do prompt e escolhe certo. **Não era memorização de mapeamentos
pedido→ferramenta** — que era a hipótese alternativa que o experimento anterior não conseguia
descartar.

**E o ganho é amplo, não concentrado:**

| ferramenta | E2 | e8 | n |
|---|---:|---:|---:|
| `calculate_tax` | 0% | **97%** | 30 |
| `create_task` | 34% | **91%** | 64 |
| `search_music` | 0% | 74% | 23 |
| `create_calendar_event` | 15% | 62% | 117 |
| `schedule_meeting` | 0% | 44% | 95 |
| `book_flight` | 0% | 28% | 32 |
| **`send_email`** | 2% | **14%** | 125 |

---

## 2. ⭐⭐ O que falha: a chave do argumento, não o valor

Das 294 falhas:

| modo | n | % |
|---|---:|---:|
| ferramenta errada ou ausente | 24 | 8,2% |
| ferramenta certa, argumentos errados | 270 | 91,8% |
| ↳ **valor CERTO, chave ERRADA** | **62** | **23,0%** |
| ↳ valor de fato errado | 208 | 77,0% |

E o padrão das chaves inventadas é inequívoco:

```
recipient        → receptor          49×   ← tradução literal para português
recipient_email  → request_email      5×
recipient        → receivable         2×
return_date      → passegger_date     1×
```

⭐ **O modelo lê o catálogo para escolher a ferramenta e deixa de ler para copiar o nome do
argumento** — produz uma chave plausível, muitas vezes traduzida. É por isso que `send_email`
(17,2% do holdout) é a pior ferramenta: ele acerta a ferramenta em 124/125, escreve o conteúdo
certo, e chama o destinatário de `receptor`.

### Isto corrige uma refutação minha

No E5c eu **descartei** a hipótese do arXiv:2601.05366 — *"o modelo escreve o parâmetro no
idioma do usuário, violando a convenção de execução"* — porque as referências daquele holdout já
usavam português nos **valores** (`{"city": "Brasília"}`).

Estava certo sobre os valores. **Não olhei as chaves.** O fenômeno estava lá, e só apareceu num
holdout com ferramentas cujas chaves são em inglês. A refutação era válida para o holdout que eu
tinha e falsa para o fenômeno.

---

## 3. Como o split foi feito, e as duas armadilhas

🔴 **Separar pelo nome exato deixaria o quase-sinônimo no treino.** `calculate_tip` no holdout
com `calculate_tip_amount` no treino não é ferramenta inédita, e o número sairia inflado.

⭐ Agrupei por **raiz = (família do verbo, objeto)**: junta
`find_restaurant`/`search_restaurants`, e mantém `send_email` separado de `check_email`, que são
ações diferentes sobre o mesmo objeto. Uma versão anterior tirava só o prefixo verbal e juntava
esses dois — errado. **150 ferramentas → 137 raízes.**

⚠️ E onde houve dúvida, **agrupei**: agrupar demais custa dado de treino, agrupar de menos infla
o resultado. **Os dois erros não são simétricos.**

🔴 **Teto por ferramenta.** Sem ele, `create_calendar_event` e `send_email` davam **55%** do
holdout e eu estaria medindo "sabe calendário e e-mail inéditos". Com teto de 6%, as duas
maiores somam 33,3%. É o mesmo defeito de concentração que já custou um holdout inteiro — agora
no eixo da ferramenta em vez do eixo da tupla.

**Guardas, todas em zero:** ferramenta do holdout no treino **0/37** · raiz **0/32** · pedido
**0/1092** · tuplas distintas **728/728** · Wilson **±3,3 pp**.

⚠️ **E o e7-diverso não pôde servir de teto superior**: ele viu 67,7% dos pedidos deste holdout.
Conferi antes de propor a linha, não depois.

---

## 4. O arco inteiro, em uma tabela

| intervenção | ganho medido |
|---|---:|
| retentativa em runtime (E5) | +1,2 pp — abaixo do ruído |
| preferência: DPO/IPO/KTO (E6) | +2,4 pp — abaixo do ruído de semente |
| votação por maioria | **0,0 pp** — empate exato com greedy |
| rejection sampling | concentrou no que o modelo já fazia (0 de 374 prompts de gorjeta) |
| **dado diverso, ferramentas conhecidas** | **+75 pp** |
| **dado diverso, ferramentas inéditas** | **+49,3 pp** |

⭐ **O que três estágios de runtime e preferência não alcançavam era de treino.** E o motivo
agora é nomeável: eles operavam sobre a distribuição que o modelo já tinha, e o problema era a
distribuição.

---

## 5. O que fica

1. ⭐ **Alvo medido e acionável:** 23% das falhas de argumento são **de chave, não de conteúdo**
   — o valor certo já está lá. **Decodificação restrita ao esquema** torna `receptor`
   impossível por construção. São 62 casos (8,5% do holdout), zero treino. Era a ação nº 1 do
   estudo de papers (arXiv:2608.04464, arXiv:2604.04233) e agora tem número.
2. **A extração de valor é o gargalo real** (208 de 294 falhas). Não se resolve por harness.
3. **A régua é o ativo permanente:** três holdouts, cada um medindo uma coisa diferente — 85
   casos (dentro da distribuição de 14 ferramentas), 1.000 (leitura de catálogo), 728
   (ferramenta inédita). Nenhum substitui o outro.
4. ⚠️ **A variância de semente ficou em 1,5 pp** com n=728, contra 4,7 pp com n=85. O tamanho
   do holdout compra poder duas vezes: no intervalo e no ruído de rodada.
