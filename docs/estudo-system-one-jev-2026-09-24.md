# System One / Jev — o que é, o que é evidência, e o que vale para o Bee (2026-09-24)

> Segundo estudo sobre o tema (o primeiro: [`estudo-decisoes-calibradas-2026-09-19.md`](estudo-decisoes-calibradas-2026-09-19.md),
> com G-C1/G-C3/G-C1b/G-C4 medidos). Feito por 4 agentes em paralelo: (1) docs e integrações da TypeSafe,
> (2) os 5 artigos do arXiv + busca + 7 artigos adicionais, (3) o repositório `laya` inteiro, (4) alternativas
> abertas no GitHub/Hugging Face. Regra de sempre: número de terceiro não entra como resultado nosso.

## Em uma frase

O Jev é um **classificador hospedado** que devolve uma distribuição sobre opções declaradas pelo usuário.
A mecânica é a que o Bee já tem — **ler a probabilidade só sobre as opções e calibrar** —, e a parte que
seria nova ("RLCD", o treino de calibração) **continua sem método, artigo, pesos ou função de recompensa**.
O que o ecossistema ainda não tem é justamente o que o projeto pode produzir: decisões tipadas **medidas em
português**, um portão de risco de ação pequeno e aberto, e calibração verificada por terceiros.

## 1. O produto, com a API real

- `POST https://api.typesafe.ai/v1/systemone` · `{model, state, questions:{nome: Question}}` → `{answers, usage}`.
  Versão `jev-1.13.0`. Acesso direto por convite; **sem convite via Cloudflare** (`typesafe/jev`) e Vercel AI Gateway.
- **Choice:** `criteria` opção→descrição, até **255 opções** → `choice`, `probabilities`, `confidence`. Doc recomenda
  uma opção "nenhuma das anteriores"; o Pydantic admite que **a ordem das opções altera o resultado**.
- **Score:** 2–10 níveis ordenados → `score = Σ nível·p`, `probabilities`, `confidence`.
- **Noul:** sim/não → só `noul = P(sim)`.
- **`confidence = (K·p_max − 1)/(K − 1)`** — é o p_max reescalado, nada mais (conferido no exemplo da doc).
- Preço US$ 0,042/M tokens de entrada, saída grátis; 64k de contexto (32k na Cloudflare); latência ~100–500 ms.
- **Limitações declaradas (jev-1.13):** não conta nem faz conta; fraco em números e datas; perde precisão com
  estado irrelevante; lê negação ao pé da letra; **não trata o estado como hostil (injeção)**. **Português:
  "aceito, com precisão menor"** — sem número nenhum.

## 2. Afirmações × evidência

| afirmação | evidência | veredito |
|---|---|---|
| "RLCD" treina probabilidades honestas | nenhum artigo, recompensa, diagrama de confiabilidade ou peso; busca no arXiv vazia; a sigla já existia (2307.12950) | **marketing** (confirma o estudo de 19/09) |
| 40–200× mais rápido, "444× mais barato" | metodologia não publicada; repetido por parceiros como "TypeSafe reports" | não verificável |
| "0% de alucinação" | tipo zero é por construção; alucinação não medida | enganoso — o erro vira classificação errada confiante |
| LangChain: variância 92–913× menor, 100% de acerto | **5 casos distintos × 100 repetições, 1 revisor**; variância entre repetições de um forward é ~0 por arquitetura | não diz nada sobre qualidade |
| Injeção move o veredito (bloqueio 0,76 → 0,48) | terceiro (Octomind), caso único | risco real; a LangChain passou a tirar a saída das ferramentas da entrada |
| Acidentes do Texas: ECE 0,012–0,045, F1 0,908 vs humanos | 2609.24052, 195k narrativas, bootstrap por cluster — **o melhor estudo do lote (7/10)** | real, e achou um limite: **a grade de probabilidade tem piso 0,01** — não calibra taxas < 1% |

**Os artigos do arXiv** (5 da lista + 7 achados) saíram em 5 dias após o lançamento, quase todos usando o Jev
como API. Rigor 3–7/10. Padrões recorrentes: baseline trivial treinado ganha (JEVQA: ExtraTrees 0,957 × Jev
0,824); treinado comparado a zero-shot (Smart If); ganhos de latência que **somem com cache** ou contra um
cascade barato (borda, REFLEX).

## 3. O que é estabelecido — e casa com o que já medimos

1. **Softmax restrita às opções declaradas** dá probabilidade usável e zero saída malformada — é o nosso G-C1.
2. **Temperatura/isotônica depois** conserta a maior parte do ECE (acidentes 3,3×, radiologia 0,12 → 0,008) —
   é o nosso G-C3 (T≈2, ECE → 0,02–0,04).
3. ⭐ **Escolher QUAL é fácil e calibra; decidir SE agir é difícil — e as duas não se correlacionam.** Três
   fontes independentes: REFLEX (seleção 98,4% × decisão de chamar **52%**, BFCL), AgentAbstain (φ ≈ −0,10
   entre agir e abster, 17 modelos de fronteira), JevBench (coorte de adequação 82% classe majoritária). É
   exatamente o nosso 350M: Choice ECE 0,04, "chamar?" superconfiante.
4. **Treinar calibração, quando se treina, é SFT com CE + Brier nos logits de rótulo** — JevLite (Qwen3-4B + LoRA
   r16, **3 sementes**, AUROC 96,9–97,7) e Smart If. Não RL. Coerente com a lei que três grupos mediram: RL
   binário descalibra, SFT calibra.
5. **Calibração não transfere entre tarefas** (AnyJev, Smart If), e **a ordem das opções muda 2,6–23% das
   decisões** (JevLite, AnyJev). Nossa temperatura transferiu entre **sementes** — isso não garante entre tarefas.

## 4. Os repositórios abertos

- **`laya`** (NandhaKishorM, Apache-2.0, 20k★ em 5 dias): clone aberto do Jev, mas **encoder** (ModernBERT/mmBERT,
  322–421M), não LLM. O "RL" é destilação supervisionada com ruído (o autor admitiu na issue #238). Benchmark
  **selado 30,8% × público 58,4%**; checkpoints base **abaixo da classe majoritária**; português ~0,46 de acurácia
  com ECE 0,34–0,51; confiança devolvida ≠ confiança calibrada. **Não adotar.** Três peças a copiar: a perda
  ordinal RPS (como termo direto, não REINFORCE), temperatura por (tipo × tamanho do catálogo) com piso, e o
  **teste metamórfico** (permutar opções e medir quanto a distribuição muda — a régua do nosso §2u).
- **`open-alternative-jev`** (Apache-2.0): várias perguntas **empacotadas num forward**, softmax sobre letras,
  T-scaling — throughput 2,3×. **A técnica mais útil para uma camada de decisão sobre o Bee.**
- **AnyJev** (Nokia): média sobre rotações cíclicas das opções ÷ prior do rótulo — troca por ordem 0,23 → 0,07.
- Bosun (Qwen3 0,6/1,7B), Von, OpenJev (**licença não-comercial**), jevper: autorreportados, origem de dados
  não divulgada → **referência de medição, não componente** (regra de proveniência do projeto).
- Guards (Qwen3Guard-0.6B, Llama Guard, Granite Guardian): medem **conteúdo**, não risco de ação; o único com
  "risco de function call" é o Granite Guardian, 3–8B e só inglês.
- **Não encontrado** (ausência na busca, não no mundo): benchmark de decisão tipada em PT-BR; modelo ≤3B com
  calibração medida por terceiros em PT; portão de risco de ação pequeno, multilíngue e aberto; pesos do Jev.

## 5. O que muda para o Bee — decisões e testes, do mais barato ao mais caro

| # | o quê | custo | o que decide |
|---|---|---:|---|
| 1 | **Slot de decisão tipado para "chamar?"** — pergunta com rótulos de 1 token (A = chamar, B = responder), softmax só sobre {A,B}, **limiar escolhido por nós** em vez do argmax sobre 64k tokens (corte implícito p≈0,14) | < US$ 0,50 (só avaliação) | se o "SE agir" fica tão bem-calibrado quanto o "QUAL"; torna explícito o limiar que o G-C3 mostrou valer 4,5 pp |
| 2 | **Teste metamórfico + desviesamento AnyJev** no Choice sobre o catálogo | ~US$ 1 | quanto a ordem do catálogo move nossas decisões (§2u) e se a média sobre rotações conserta |
| 3 | **Temperatura em outra tarefa/holdout** (não só outra semente) | < US$ 1 | se o T≈2 é da receita ou do holdout |
| 4 | **Empacotar várias perguntas num forward** no Bee, pareado contra 1 por vez, ECE por posição | US$ 0 | latência/custo de uma camada de decisão para o Chimera; risco de contaminação entre perguntas |
| 5 | **CE + Brier nos logits de rótulo via LoRA**, 3 sementes (receita JevLite) — *se* 1–3 mostrarem calibração ruim que a temperatura não conserte | ~US$ 5 | substitui de vez o G-C6/RLCR na fila |
| 6 | **Régua de triagem PT-BR** (tickets reais do PassaPro, itens distintos, ordem sorteada): Bee-350M/1G × Laya-multilingual × mDeBERTa-NLI × Jev via Cloudflare | ~US$ 0–2 | o "precisão menor em português" que a TypeSafe declara sem número — e se o Bee é uma camada de decisão PT melhor que a oferta pronta |

**Decisões que já saem daqui:**
- **G-C6 (RLCR) sai de vez da fila.** O único "RL de calibração" do ecossistema não é publicado; a alternativa
  com evidência (CE + Brier supervisionado) é mais barata e é o item 5.
- **Auto-avaliação por prompt não se busca.** Se voltar, é pergunta tipada treinada com Brier — e mesmo em
  modelos de fronteira é o elo fraco (REFLEX).
- **Toda afirmação de calibração do projeto sai com ECE entre tarefas e taxa de troca por ordem**, além de ECE
  entre sementes.

## 6. Chimera e PassaPro

- **Chimera:** guarda de chamada de ferramenta no estilo `AutoModeMiddleware` da LangChain antes de `run_shell`,
  `chimera_sql_write`, `chimera_git` — **ao lado dos guards determinísticos, nunca no lugar** (lição de 09/07); a
  entrada do guarda **nunca inclui saída de ferramenta** (injeção); log de estado, opções, ordem, versão e confiança.
  Roteamento por confiança: < 0,6 humano · 0,6–0,85 em ação de risco pede confirmação · > 0,85 age.
- **PassaPro:** triagem de suporte como Choice + "outro", com roteamento por confiança. Para testar, Jev via
  Cloudflare basta; **para produção, o Bee local evita mandar dado de aluno a terceiros** — e o item 6 da tabela
  diz se ele é bom o suficiente.
- **Interface:** servir o Bee num endpoint **compatível com o formato `/v1/systemone`** (Choice = logprob
  normalizado; Noul = decisão com T; Score = média ponderada; `confidence` pela fórmula da TypeSafe) faz o SDK,
  o `langchain-typesafe` e o `TypeSafeModel` do Pydantic funcionarem trocando só o `baseURL`.

## 7. O que ficou sem leitura

Os dois posts do X (403); os termos de uso/retenção de dados da TypeSafe via Cloudflare/Vercel; as fontes
primárias de jev-certify (CLINC150) e da auditoria KoBBQ; a tabela numérica do 2609.07395.

## Fontes principais

docs.typesafe.ai (introduction, quickstart, llms-full.txt, confidence, primitives, models, model-jaggedness,
patterns) · typesafe.ai/blog · LangChain (building-a-harness-with-jev; jev-agent-evals-langsmith;
github danielgshea/jev-as-a-judge) · Vercel AI Gateway · Cloudflare `typesafe/jev` · Pydantic AI · VentureBeat
(injeção) · arXiv 2609.24395, .24052, .23986, .23886, .22753, .27607, .26532, .23959, 2607.10059, 2508.00264,
2609.07395 · github NandhaKishorM/laya (inteiro, issues #131 #156 #185 #238 #252) · ikermoel/open-alternative-jev ·
nokia-applied-research/AnyJev · Mapika/decider · fstandhartinger/jevbench · wfzyx/von · zhangcy122/OpenJev ·
zhulinchng/jevper · HF: convaiinnovations/laya(-multilingual), Hanno-Labs/bosun-v3.1-1.7b, Qwen3Guard-Gen-0.6B,
granite-guardian, mDeBERTa-xnli, GLiNER2 · lm-polygraph · RouteLLM · semantic-router · xgrammar.
