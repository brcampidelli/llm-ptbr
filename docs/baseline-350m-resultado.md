# Baseline do Bee-350M base — as 9 medições antes de qualquer pós-treino

> **2026-08-20, 01:47.** Estágio 0 do plano de pós-treino, concluído. Modelo
> `BrCamp/bee-350m-pt-base`, revisão `2cb20ac8b910`. Nove capacidades medidas em **31,4 min**
> na RTX 5070 local, custo US$ 0 — mais o gate de matemática, que levou 4,5 h à parte.

---

## 1. Por que este número existe

`arXiv:2604.08880`: destilação de CoT **piorou** a matemática na maioria das configurações, e a
literatura anterior não viu porque comparava variantes treinadas entre si — nunca contra o
ponto de partida. Este projeto pagou a mesma conta em casa: o SFT generalista PT-BR
desperdiçou esforço porque o base já ia bem, e a abelha agêntica funcionou porque o base
estava em 45,7%, com espaço de sobra.

**Sem o número de partida, "melhorou" é opinião.** É isto aqui.

---

## 2. O quadro completo

| capacidade | Bee-350M base | piso trivial | referência externa |
|---|---|---|---|
| **Tradução en→pt** | **BLEU 27,1** · chrF++ 51,1 · 97% no idioma-alvo | copiar = BLEU 2,5 | opus-mt = BLEU 50,5 |
| **Tradução pt→en** | **BLEU 19,6** · chrF++ 43,3 · 86% no idioma-alvo | copiar = BLEU 2,5 | opus-mt-ROMANCE = 45,1 |
| **Matemática** | `pass@256` **22,0%** · `pass@1` 0,32% | — | gate 3% → **aprovado** |
| **Instrução (IFEval-PT)** | **30,4%** por instrução · 12,8% por prompt | — | referência 100% |
| **Sentimento** | **49,7%** [46–54] · balanceada 49,7% | léxico **79,0%** · só "não" 73,2% | nlptown 89,8% |
| **Resumo** | **0,0%** útil (compressão 0,88 · cobertura 84%) | LEAD-2 **51,3%** | — |
| **Atendimento** | **0,0%** útil (`json_ok` 0,0%) · risco de política **0%** | regra **60,4%** | — |
| **Código interno** (877) | `pass@1` **0,0%** · **78% sem código** | — | teto verificado 100% |
| **Código HumanEval-XL** (80) | `pass@1` **0,0%** · **96% sem código** | — | teto verificado 100% |
| **Agêntico** (85 tool + 65 texto) | exec **0/85** · JSON válido **0** · under-call **85/85** | — | referências 85/85 executam |

---

## 3. O padrão que atravessa tudo: o gargalo é FORMATO, não capacidade

Três capacidades marcaram zero, e em nenhuma das três o zero significa "não sabe":

| | número que parece ruim | número que explica |
|---|---|---|
| resumo | 0,0% útil | **cobriu 84% dos fatos**; reprovou por **compressão 0,88** — não encurta |
| código | `pass@1` 0,0% | **78% das respostas não continham bloco de código extraível** |
| agêntico | exec 0/85 | **JSON válido: 0**. Nunca emitiu uma chamada |
| atendimento | 0,0% útil | `json_ok` 0,0% — sem JSON, intenção e dados são zero por construção |

⭐ **Um modelo base não sabe parar, não sabe emitir estrutura, e não sabe obedecer a um
formato de saída — e é exatamente isso que o SFT ensina.** Onde a tarefa é contínua com o
pré-treino (traduzir, seguir instrução de escrita), há capacidade real e medível. Onde exige
formato, há zero. Isso é uma notícia boa disfarçada de ruim: o espaço de ganho do E2 é enorme
e está num eixo barato.

⚠️ **E um zero que NÃO é boa notícia:** `over-call = 0/65` no agêntico parece virtude e não é.
O modelo nunca chama ferramenta nenhuma, então nunca chama errado. Um número que só é bom
porque o comportamento inteiro está ausente **não é linha de base de segurança** — vai ter de
ser remedido depois do SFT, quando o modelo passar a chamar.

---

## 4. As duas capacidades onde o resultado é substantivo

### 4.1 ⭐ Tradução — o achado positivo do baseline

**BLEU 27,1 en→pt, sem uma linha de SFT**, contra 2,5 de copiar a fonte. E **97% das saídas
saem em português**. Um modelo de 345M pré-treinado só em PT, que nunca foi treinado para
traduzir, faz mais da metade do BLEU de um `opus-mt` **dedicado a esta tarefa** (50,5).

A assimetria de direção é informativa: **en→pt (27,1) é muito melhor que pt→en (19,6)**, e a
taxa de idioma-alvo cai de 97% para 86%. O modelo escreve português muito melhor do que
escreve inglês — o que é exatamente o esperado de um corpus 100% PT, e serve de sanidade da
medição.

### 4.2 🔴 Sentimento — a capacidade que não está lá

**49,7% é o acaso**, e a acurácia balanceada confirma: também 49,7%. O modelo respondeu
"positivo" em **554 de 600**. Isso é prior, não leitura.

E aqui o zero **não** é formato: a medição é por verossimilhança (compara o logprob de
" positivo" contra " negativo"), não por geração livre. Não há JSON para errar nem formato
para desobedecer.

⭐ **O censo por token já tinha previsto:** sentimento tem **4 exemplos** no `sft_misto`
inteiro. Não há gradiente. É a confirmação mais limpa do dia de que o E3 (geração de dado)
precisa vir antes do que o plano previa para as quatro capacidades sub-representadas.

---

## 5. Reprodutibilidade — o baseline se mediu duas vezes

As réguas usam decodificação **greedy** com dados fixos, então uma segunda passada deve
reproduzir exatamente. Reproduziu: IFEval **30,4% / 12,8%** nas duas execuções, resumo 0,0%,
tradução BLEU 27,1, sentimento 49,7%, atendimento 0,0%. **O aparato é determinístico**, o que
é pré-requisito para o E2 comparar 15 braços entre si.

---

## 6. O que este baseline custou em bugs — e todos eram do aparato

Quatro tentativas até fechar. Nenhuma falha foi do modelo:

| # | o que apareceu | causa real |
|---|---|---|
| 1 | 9 min na 1ª régua sem uma linha de progresso | `capture_output=True` no orquestrador bufferizava o filho — **cegueira por escolha própria**, e foi o que impediu de ver a GPU a 31% |
| 2 | régua de código projetando 2,8 h | geração sem lote. Corrigida: **11×**, e no grid do E2 seriam **42 h** |
| 3 | régua agêntica "travada" 21 min | 🔴 duas vezes diagnosticada errado. `py-spy dump` mostrou a pilha em `generate` → **estava lenta, não travada**. Corrigida com lote: **50×** |
| 4 | monitor deu falso positivo de "fechou" | o arquivo-alvo já existia do run anterior. O monitor agora **aborta se o alvo existir no lançamento** |

E dois bugs achados de brinde no `tools_exec`, os dois reais:

- 🔴 **`ast.Pow` sem guarda de expoente.** A calculadora sempre foi "segura" — usa AST, não
  `eval()` — e isso é verdade e não bastava: `9**9**9` é expressão **inteiramente válida** que
  exaure CPU e memória sem executar nada proibido. **Segurança contra execução e contra
  exaustão de recurso são ameaças diferentes**, e o vocabulário de "sandbox seguro" esconde a
  segunda.
- ⚠️ **`factorial` nunca funcionou.** Estava na tabela desde sempre; o avaliador de AST devolve
  `float` e `math.factorial` exige `int`, então toda chamada levantava `TypeError` — **contado
  como falha do modelo**. Ninguém tinha executado a função.

⭐ **A lição de instrumentação:** `utilization.gpu` em 22% com progresso invisível é
indistinguível de travamento **se a régua só imprime a cada 20 exemplos**. Ou o passo é menor,
ou o log é mais frequente — não os dois grandes ao mesmo tempo. E calibrar um monitor de
estagnação sem olhar a cadência de impressão do que ele vigia produz falso positivo, que é
pior que não ter monitor: ensina a ignorá-lo.

---

## 7. O que isto decide para o E2

1. **Matemática entra**, com `pass@256` de 22% e gate aprovado. O caminho é rejection sampling
   com verificador por execução — o gabarito já é executável.
2. **Tradução tem base real** e é candidata a ganho barato: o modelo já traduz, falta formato
   e consistência de direção.
3. **Sentimento, atendimento, resumo e tradução continuam com menos de 1,5% do gradiente cada**
   — o grid vai medi-las e **não vai conseguir discriminar arquitetura nelas**. Isso já está
   impresso em toda execução do `grid_e2.py`.
4. **O espaço de ganho está em formato**, e formato é o que o SFT faz melhor e mais barato.
   A expectativa correta para o E2 não é "o modelo fica mais inteligente" — é "o modelo passa
   a emitir o que já sabe".
