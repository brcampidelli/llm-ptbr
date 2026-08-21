# Triagem de 17 fontes (2026-08-21) — e por que 14 delas não servem ao Bee

> Dois PDFs e quinze links do arXiv. A conclusão honesta primeiro: **este lote é uma varredura
> ampla do arXiv recente, não uma seleção para o Bee.** Três fontes tocam o projeto, e as três
> compartilham o mesmo ponto cego. Vale mais dizer isso do que espremer relevância de onde
> não há.

---

## 1. O que não tem relação com o Bee (11 de 17)

| fonte | assunto |
|---|---|
| **PDF 2608.13576** BCIJelly | ecossistema de pesquisa em interface cérebro-computador (67 pág.) |
| **PDF 2608.19284** | limite de Shockley-Queisser para células solares nanoestruturadas |
| 2608.11744 VistaFuzz | fuzzing de bibliotecas Python guiado por documentação |
| 2608.15073 BOCoDe | benchmark de otimização bayesiana em engenharia |
| 2608.15709 Logos | verificação formal de reescrita de SQL |
| 2608.20167 BreakGuard | testes gerados por LLM para *breaking changes* |
| 2608.19487 | agente otimizando código científico em HPC (85% de tempo economizado) |
| 2608.19749 | florestas causais de sobrevivência com controles negativos |
| 2608.19767 skchange | biblioteca de detecção de *changepoints* |
| 2608.20184 PEtab SciML | formato de intercâmbio para ML científico |
| 2608.19703 Loreley | busca *quality-diversity* em repositórios (resultado nulo: −0,135%) |

⚠️ Os dois PDFs anexados — os únicos que exigiram download deliberado — são de neurociência e
de física de semicondutores. Não há como derivar deles nada sobre pós-treino de LLM.

---

## 2. O que é relevante para o Bruno, mas não para o Bee (1)

**2608.13913 — AlphaSeek: Trajectory-Level Self-Iterative Factor Mining.** Mineração automática
de fatores alfa financeiros com LLM agêntico. Retorno anualizado **8,28%** com *information
ratio* **1,29** no CSI300, contra **−2,67% a −4,24%** de Linear e XGBoost.

⚠️ Antes de qualquer entusiasmo: é backtest em índice chinês, e o projeto tem regra própria
sobre isso — resultado de backtest não é resultado de operação. Mas o desenho (LLM propõe
hipótese → constrói fator → backtesta → itera) é o mesmo laço do agente que já opera o eToro,
e o número de referência dos baselines clássicos negativos é informativo.

---

## 3. O que toca o Bee (3) — e o ponto cego que as três dividem

| fonte | menor modelo | resultado |
|---|---|---|
| **2608.15165 SkillCommit** | **Qwen3.5-9B** | 78,15% vs 50,80% sem skills; transferência entre famílias 69,62% vs 36,91% |
| **2608.09248 Emotion2Skill** | **Qwen3-8B** | ALFWorld 47,4% vs 21,9%; WebShop +26,9 pp |
| 2608.14944 SkillComposer | não especifica | rearrumação 92% vs 50% |

⭐ **O tema é coerente e é o nosso:** as três acumulam **bibliotecas de habilidades
reutilizáveis** e ganham capacidade agêntica **sem atualizar parâmetro nenhum**. Para um modelo
com capacidade disputada — e o E2 mediu isso no Bee-350M, onde o full FT comprou agêntico
vendendo instrução (25,2% contra 30,0% do base) — um método que adiciona habilidade sem tocar
nos pesos é exatamente o que a restrição pede.

### 🔴 E agora o problema, que é o mesmo nas três

**O menor modelo testado é 8B. O Bee tem 345M — 23× menor.** A regra do projeto é explícita:
*o que só foi validado em ≥7B é aposta, não receita.*

Pior: perguntado diretamente, o SkillCommit **não mede o roteador**. A seleção de skill é feita
por recuperação semântica com validação comportamental, e **não há acurácia de roteamento
reportada, nem ablação com modelo base fraco, nem discussão de falha em modelo pequeno**.

⚠️ **Esse é exatamente o ponto cego que eu declarei no relatório do E2**: o número do braço (b)
supõe roteador perfeito, é teto e não sistema. A diferença é que lá isso está escrito como
ressalva, e aqui não está escrito. Um método cujo ganho depende de escolher a skill certa, sem
medir a taxa de escolha certa, não é transferível para um modelo que acerta **32%** no
IFEval — porque um roteador que erra dois terços das vezes torna a biblioteca pior que inútil.

### O que sobra de aproveitável

1. **A direção converge com o que o E2 já mediu.** As três chegam, por outro caminho e em 8B,
   ao mesmo lugar do braço (b): **especializar e rotear ganha de um modelo único genérico.**
   O Bee tem isso medido em 345M — 64,7% contra 48,2% do adapter multi-task.
2. **O roteador do Bee é determinístico**, e o projeto já mediu 80% de *fast-path* sem chamada
   de LLM. Isso é uma vantagem sobre o desenho dos papers, não uma limitação: onde eles
   dependem do modelo escolher, o Bee escolhe por código.
3. **A ablação do SkillCommit tem um número útil**: tirar *Patch Induction* custa **17,78 pp**,
   contra 4,44 pp de tirar agrupamento ou consolidação. Se um dia a ideia for testada aqui,
   é por onde começar — e o resto do método é margem.

---

## 4. Duas fontes com metodologia parcialmente aproveitável

- **2608.17379 PTXBench** (Qwen3.6-27B) — traz **ablação de mistura de dados** e **ablação de
  qualidade do teacher**, além de SFT condicionada a reparo. O E4 do Bee é justamente
  otimização de mistura, e a estrutura da ablação serve de referência. ⚠️ 27B.
- **2608.13681** (Qwen3.5-27B) — currículo de SFT em **três estágios** (pré-treino de domínio →
  SFT com dados de debug → SFT da tarefa), 87,2% em tradução C→Rust batendo modelos 8,5–27,6×
  maiores. A ideia de currículo em estágios é transferível em princípio; o número não é.

---

## 5. O que este lote muda no plano

**Nada.** E isso é um resultado, não uma decepção: o E3 segue como está, o E4 continua sendo
otimização de mistura, e nenhuma das 17 fontes traz evidência na faixa <1B que justifique
mudar rota.

⭐ O valor real do lote foi negativo-informativo: **três equipes independentes convergiram, em
8–9B, para "especializar e rotear ganha de modelo único"** — que é a conclusão que o E2 tirou
em 345M com a grade de LR cercando o ótimo dos dois lados. Convergência de evidência
independente é a coisa mais barata que existe para aumentar confiança numa decisão já tomada.
