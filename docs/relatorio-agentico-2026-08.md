# Relatório — capacidade agêntica do Bee-350M (E8 → E16)

> **2026-08-24 a 27.** US$ 0 de GPU paga (RTX 5070 local). Sete estágios, quatro intervenções
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
| **e13 (+ e-mail diverso) — ADOTADO** | **82,6%** | **73,1%** | 17,3% | dp 2,53 pp (3 sementes) |
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

## 6b. Onde a investigação parou — e o que fechou o caminho

Depois do e13, o resíduo se decompõe assim (1.072 casos, duas sementes):

| modo de falha | % |
|---|---:|
| **recusou quando devia chamar** | **9,2%** |
| **ferramenta errada** | **8,5%** |
| referência temporal não está no pedido | 6,1% |
| valor errado (extraído) | 6,0% |
| ✅ acertou | 72,3% |

Mais **16,8% de over-calling**. ⭐ **A decisão binária "chamar ou não" custa 26% — mais que
todos os erros de argumento somados.** Três hipóteses foram testadas e **as três caíram**:

| hipótese | teste | veredito |
|---|---|---|
| quantidade de negativos | varredura de razão tool:text | ❌ **já está no ótimo** |
| diversidade dos negativos | contagem de distintos | ❌ 4.228 pedidos distintos em 4.421 |
| capacidade de comparar com o catálogo | curva de catálogo até 15 | ❌ **recusa é plana** |

### Varredura tool:text — a razão atual já é a certa

Total constante (8.842), 4 razões, 1 semente. Métrica **macro** (média de execução e recusa
correta), porque o agregado pesaria as chamadas mais que as recusas e embutiria a resposta.

| razão | exec | recusa ok | **macro** |
|---|---:|---:|---:|
| 1,0:1 | 67,2% | 82,8% | 75,0% |
| **1,5:1** | 70,3% | **85,8%** | **78,1%** |
| 2,0:1 | 71,8% | 81,3% | 76,6% |
| 3,0:1 | **75,7%** | 76,5% | 76,1% |

Trade-off monotônico: de 1,0 a 3,0 a execução sobe **8,5 pp** e a recusa cai **6,3 pp**. O
treino está em **1,52:1** — no pico. ⚠️ A amplitude do macro (3,1 pp) quase cabe no desvio de
semente (2,53 pp): **alerta, não decide**.

⭐ Uso real disto: **a razão escolhe o ponto de operação, não melhora o modelo.** Custo alto de
ação indevida → 1,0:1 (recusa 82,8%); não perder pedido → 3,0:1 (execução 75,7%). Nenhuma
melhora os dois.

### ⭐⭐ Duas capacidades, e só uma escala com o catálogo

| catálogo | 350M ferram | 150M ferram | 350M recusa | 150M recusa |
|---:|---:|---:|---:|---:|
| 1–6 | 80,0% | 71,8% | 82,5% | 78,4% |
| 5 | 77,2% | 62,5% | 82,8% | 78,4% |
| 10 | 64,0% | 48,3% | 82,1% | 78,0% |
| **15** | **48,5%** | **39,4%** | **82,5%** | **78,4%** |

*"Alguma ferramenta serve?"* é **plano** — 0,7 pp de amplitude em quinze pontos de catálogo,
**nos dois modelos**. *"Qual delas?"* desaba **31,5 pp**. Não é propriedade deste modelo; é da
tarefa.

🔴 **E escalar não conserta:** queda relativa **39%** (350M) contra **45%** (150M), com queda
absoluta praticamente igual (31,5 × 32,5 pp). A vantagem do modelo maior **sobe e volta**:
8,2 → 14,7 → 15,7 → **9,1 pp**.

⚠️ **Erro de leitura registrado:** com três pontos (8,2 → 14,7 → 15,7) declarei *"a vantagem
cresce, logo seleção escala com parâmetro"*. O quarto mostrou uma **corcova**, não uma
tendência. **Três pontos monotônicos não são tendência quando a curva pode virar.**

⚠️ E os `holdout_cat*` do estágio anterior estavam **contaminados** (27 de 37 ferramentas no
treino do e13) por terem sido construídos contra um split antigo — reconstruídos antes de usar.
**Artefato de avaliação envelhece quando o treino muda, e não avisa.**

---

## 7. O que fica aberto

1. ✅ **RESOLVIDO com a terceira semente (2026-08-27).** Com duas, o e13 dava 70,1% e 74,4% —
   amplitude 4,3 pp — e eu reportei que a folga cabia dentro dela. A s44 deu **74,6%**, junto
   da s43: a s42 era a ponta baixa de três, não instabilidade. **Média 73,1%, desvio 2,53 pp,
   folga real +3,7 pp** — eu tinha subestimado o modelo por causa de uma amostra de dois.
   ⚠️ Ainda assim não chamo de significativo: 3 sementes contra as 2 do e12 é comparação
   assimétrica. Ver §2x da regra global.
   ⚠️ E **ampliar o holdout não era a solução**: sobravam 35 tuplas nas raízes reservadas, e
   dobrar a régua exigiria queimar 20% do treino.
2. **A extração de valor segue sendo o gargalo** — e nenhuma restrição de decodificação a
   alcança, porque o problema é capacidade, não escolha.
3. 🔴 **O gargalo real é seleção em catálogo grande:** 48,5% de acerto com 15 ferramentas, e
   escalar 2,3× o parâmetro não conserta. É o regime de uso real — um agente de produção tem
   dezenas de rotas. **Sem caminho conhecido no dado ou no tamanho atuais.**
4. ✅ **A proporção tool:text foi medida (§6b): 1,52:1 já é o ótimo.** Deixa de ser pergunta
   aberta e vira parâmetro de ponto de operação.
5. ⚠️ **RETIRADO o apoio à escala como próximo degrau.** A curva de catálogo era o teste barato
   que a justificaria, e deu o contrário. 2 h de medição evitaram uma decisão de US$ 300 tomada
   por analogia.
