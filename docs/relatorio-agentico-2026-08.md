# Relatório — capacidade agêntica do Bee-350M (E8 → E14)

> **2026-08-24 a 26.** US$ 0 de GPU paga (RTX 5070 local). Sete estágios, quatro intervenções
> adotadas, **cinco reprovadas por medição**, e sete defeitos de instrumento encontrados — três
> deles em números que eu já havia reportado como resultado.
>
> Este documento existe porque **o que sobrevive de um ciclo assim não é o modelo, é o método**.
> As leis transferíveis estão destiladas em `~/.claude/rules/bee-pretreino-licoes.md` §2q–§2w.

---

## 1. O resultado, em uma tabela

| modelo | ferramenta | executou | over-calling | amplitude de semente |
|---|---:|---:|---:|---:|
| adapter E2 (14 ferramentas) | 50,0% | 9,6% | 28,6% | — |
| e8 (ferramenta inédita) | 96,9%\* | 58,9% | 0,0%\* | 1,5 pp |
| e11 (catálogo balanceado) | 74,2% | 54,3% | 13,3% | 0,5 pp |
| e12 (split estratificado) | 79,9% | 69,4% | 16,8% | 1,1 pp |
| **e13 (+ e-mail diverso) — ADOTADO** | **82,1%** | **72,3%** | 16,0% | 4,3 pp |
| e14 (+ vocabulário coberto) | 81,3% | 68,6% | 16,1% | 1,7 pp |

\* ⚠️ **Os números do e8 estão marcados porque são artefato.** Ver §3.1: o catálogo tinha 1–2
ferramentas em 100% dos casos e a correta era sempre a primeira.

⚠️ **Linhas diferentes usam réguas diferentes** e não se comparam entre si. Cada mudança de
régua está declarada em §4. O `exec_*.json` agora grava o SHA do perfil de argumentos
justamente para isso não depender de alguém lembrar de avisar.

---

## 2. O que foi adotado, e o que foi reprovado

| intervenção | efeito | veredito |
|---|---:|---|
| **restrição de decodificação à CHAVE do esquema** | **+16,4 pp** · +144/−0 | ✅ **adotada** |
| **catálogo balanceado (dado)** | **+30 pp** | ✅ **adotada** |
| **split estratificado por tipo de valor** | régua honesta | ✅ **adotada** |
| **e-mail diversificado (dado)** | **+12,0 pp de cópia** · p=0,0024 | ✅ **adotada** |
| retentativa em runtime (E5, anterior) | +1,2 pp | ❌ abaixo do ruído |
| preferência DPO/IPO/KTO (E6, anterior) | +2,4 pp | ❌ abaixo do ruído |
| ligação de papel (hipótese) | 2,9% de assinatura | ❌ refutada por sonda |
| restrição ao VALOR (fecha em qualquer ponto) | **−9,0 pp** | ❌ reprovada |
| restrição ao VALOR (span maximal) | **−15,8 pp** | ❌ reprovada |
| cobrir vocabulário fechado | **−3,7 pp** · p=0,002 | ❌ reprovada |

⭐ **Padrão: as quatro adoções são de DADO ou de FORMATO DE SAÍDA; nenhuma é de runtime sobre
uma distribuição já formada.** Retentativa, preferência, votação e as duas restrições de valor
somam sete tentativas de runtime e **nenhuma passou** do piso de ruído.

A única exceção — a restrição de **chave** — não tenta melhorar a distribuição: ela **elimina**
uma região do espaço de saída que é comprovadamente inválida.

---

## 3. Os quatro achados sobre o modelo

### 3.1 🔴 O modelo aprendera a CONTAR, não a selecionar

O corpus deu dois atalhos perfeitamente preditivos:

| atalho | no treino |
|---|---|
| **tamanho** do catálogo | positivos 1–2 ferramentas · negativos 6 · **sobreposição 0 de 12.011** |
| **posição** da correta | primeira em **1.617 de 1.617** |

Emissão de chamada por tamanho de catálogo: `1 → 100% · 3 → 87% · 4 → 9% · 6 → 0%`. **Limiar
entre 3 e 4** — regra de contagem em forma pura, não dificuldade crescente. E reordenar duas
ferramentas, sem mudar mais nada, leva o acerto de **100,0% a 0,0%** (44 quebrados, 0
consertados, p=0,0000), com os casos não tocados bit a bit idênticos.

⚠️ **Dois números que eu reportara com destaque eram este defeito:** "a seleção generaliza,
96,9%" foi medida onde 77% dos casos tinham UMA ferramenta; e "over-calling 0,0%" era zero
**por construção** — o mesmo modelo marca **50,5%** com catálogo balanceado.

**Diagnóstico definitivo — o mesmo modelo nas duas réguas:**

| modelo | balanceado | antigo | oscilação |
|---|---:|---:|---:|
| e8 | 24,5% | **85,5%** | **61,0 pp** |
| e11 | 54,3% | 59,0% | **4,7 pp** |

**A distância entre as duas réguas É o atalho.**

### 3.2 ⭐⭐ O modelo sintetiza e-mail, não copia — e é porque decorou 22 endereços

Sonda controlada, 108 casos pareados, tudo igual menos um caractere:

| degrau | tokens | formato | copiou exato |
|---|---:|---|---:|
| d1 | 3 | texto | 74,1% |
| d4 | **14** | texto | **71,3%** |
| d6 | 16 | sem `@` | 60,2% |
| **d5** | **16** | **com `@`** | **41,7%** |

**Comprimento é plano de 3 a 14 tokens.** O `@` custa **−18,5 pp**, pareado 21×1, p=0,0000. E o
que o modelo escreve denuncia:

```
alvo:   Zorak.Vintel@Quandrix-7739.com
previu: Zorak@Quandrix-7739.com    16×   ← descarta o que não cabe no molde
        Zorak                      14×
```

**A causa estava no treino:** 724 ocorrências de e-mail e **22 distintos** — `boss@company.com`
em 47%, os três mais comuns cobrindo 79%. Trocando por 868 endereços inéditos, **sem um exemplo
novo**, a cópia foi de 41,7% para **53,7% nas duas sementes** (p=0,0024).

### 3.3 O que NÃO é o gargalo — três hipóteses minhas, refutadas por sonda

| hipótese | sonda | veredito |
|---|---|---|
| ligação por **posição** (`value`/`total` trocados) | trocar os dois valores no texto | **2,9%** de assinatura — refutada |
| **comprimento** do valor | escada de 3 a 14 tokens | plano — refutada |
| formato estruturado (`@`) | `@` × sem `@`, mesmo tamanho | **−18,5 pp** — confirmada |

⭐ As duas refutações não foram desperdício: cada uma teria justificado uma intervenção sobre
causa errada. A do comprimento eu ia usar como argumento para a restrição de valor.

### 3.4 ⭐⭐ Diversidade não é receita geral

| tipo de valor | ocorrências | distintos | copia **visto** | copia **inédito** | memoriza? |
|---|---:|---:|---:|---:|---|
| número | 6855 | 75 | 97% | 96% | não |
| **frase** | 770 | **37** | 83% | 86% | **não** |
| palavra | 1321 | 116 | 91% | 77% | **+14 pp** |
| ↳ vocabulário fechado | — | — | 90% | **72%** | **+18 pp** |
| ↳ cadeia arbitrária | — | — | 100% | 100% | n=9/14, não decide |

⭐ **`frase` é o contraexemplo decisivo:** 37 distintos, `john doe` em 53% das ocorrências, e
zero memorização. **Concentração não implica dano.**

E cobrir o vocabulário fechado **piorou** (−3,7 pp, s43 p=0,002): trocar `italian` — 209
ocorrências, a cozinha dominante em pedidos reais — por cozinhas raras **afasta o treino do
teste**. No e-mail não havia distribuição natural a preservar; aqui havia.

---

## 4. Os sete defeitos de instrumento

Cada um produziu, ou quase produziu, um número que eu teria reportado.

| # | defeito | sintoma | como foi pego |
|---|---|---|---|
| 1 | classe `temporal` decidida por **regex no nome**, não medida | 75% das falhas de argumento eram convenção do corpus | ler os exemplos: o gabarito ia nas duas direções |
| 2 | guarda que **afirmava** exclusão não implementada | escore caiu 22 pp | aritmética: excluir args deveria facilitar |
| 3 | condição de exclusão ≠ condição do pontuador | 113 casos com previsão **idêntica** ao gabarito reprovados | invariante novo |
| 4 | máquina de estados sem **arrays** na restrição de chave | 35 casos destruídos | queda em `ferramenta`, onde a intervenção não age |
| 5 | reconstrução de prompt perdeu **um acento** | 12 pp de queda em `cat1` | `cat1` deveria replicar o original |
| 6 | analisador de horário com `\b` que lia `00:00` em ISO | inverteu duas categorias | autoteste do próprio analisador |
| 7 | `--lote` diferente entre rodadas | 6,8% de itens divergentes | repetir a rodada com a mesma config: 0/440 |

⭐ **O que pegou cinco dos sete foi um número implausível na métrica errada** — uma queda onde a
intervenção não tem mecanismo de agir. Não foi cautela; foi contradição aritmética.

⚠️ E o #7 quase virou uma "descoberta": eu anunciei um **terceiro piso de ruído do projeto** que
não existe. A régua é determinística com lote fixo (0/440 ao repetir); o que muda a saída é o
tamanho do lote (bf16 batelado).

---

## 5. Custo operacional medido

| | |
|---|---|
| treino por semente (698 passos, 11k exemplos) | **86–95 min** local, US$ 0 |
| ⚠️ **treino desacompanhado** | **10× a 30× mais lento** — rebaixamento de relógio (180 MHz de 3090) |
| custo real disso | o e12 levou **6h15** em vez de 95 min |
| avaliação (1.092 casos) | ~10 min |
| RunPod (estimado) | ~45 min + ~40 de setup, ~US$ 1,50/semente |

⭐ **Para run desacompanhado, o RunPod deixou de ser marginal** — não pela velocidade nominal,
mas porque lá não há gerenciamento de energia de notebook sabotando o processo.

⚠️ E `PYTHONUNBUFFERED=1` é obrigatório: sem ele a guarda de delta e a loss só aparecem no log
**depois que o processo sai** — uma guarda que só se lê no fim não protege o run.

---

## 6. Estado do instrumento (o ativo que fica)

| régua | n | o que mede |
|---|---:|---|
| `holdout_balanceado` | 536 | ferramenta inédita, catálogo 1–6, posição sorteada, tipos alinhados |
| `sonda_dens_d1..d6` | 108 ×6 | capacidade de cópia por comprimento e por formato |
| `sonda_papel_*` | 34 | ligação por rótulo × por posição |
| `holdout_bal_v1_emails` | 440 | ⚠️ **contaminado** para o e12+ (27 de 37 ferramentas no treino) |

**Guardas ativas no avaliador:** gabaritos executam antes de carregar modelo · `sem_criterio`
fora do denominador com contagem impressa · **previsão idêntica à referência não pode falhar**
· mascaramentos de chave e de valor contados, com aviso se forem zero · config e SHA do perfil
gravados no artefato.

⚠️ **O que o instrumento NÃO mede:** cópia de cadeia densa em pedido natural. Alinhar as
distribuições tirou o e-mail do holdout (26,6% → 0,5%), e não foi possível construir uma
terceira régua — ferramentas de e-mail livres do treino dão **24 casos**; mesma ferramenta com
pedido inédito dá **4**. **Alinhar treino/teste e medir generalização para um tipo raro são
objetivos que competem.**

---

## 7. O que fica aberto

1. **A folga do e13 sobre o e12 (+2,9 pp) está dentro da própria amplitude de semente
   (4,3 pp).** Só a sonda de e-mail tem significância. Para adotar com confiança seria preciso
   uma terceira semente ou um holdout maior.
2. **A extração de valor segue sendo o gargalo** — e nenhuma restrição de decodificação a
   alcança, porque o problema é capacidade, não escolha.
3. **Catálogo acima de 6 é extrapolação:** os negativos só podem ser subamostrados, então o
   treino não contém catálogos maiores.
4. **A proporção tool:text (1,44:1) segue herdada, não otimizada** — declarado desde o E7.
