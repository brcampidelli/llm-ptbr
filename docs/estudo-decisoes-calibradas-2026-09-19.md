# Decisões calibradas — Jev/System One, RLCD, RLCR, RLSR — e o que isso vale para o Bee (2026-09-19)

> Estudo dos 6 links pedidos + os arquivos que eles apontam (docs completos da TypeSafe em
> `llms-full.txt`, o repositório `system-one-adapter-python`, a página de evals, o artigo do MIT no
> texto completo, o 2601.13284 no texto completo, e os 105 resultados da busca do arXiv com os 5 mais
> relevantes lidos por inteiro). Regra do projeto: **o número do artigo não entra como resultado; só o
> que for medido aqui entra** — e aqui nada foi medido ainda. A seção 6 diz o que medir e quanto custa.

**Em uma frase:** "capacidade de decisão calibrada" não é uma arquitetura nova — é (1) restringir a
saída a um **token de decisão** entre opções definidas, (2) **ler a probabilidade** desse token em vez
do texto, e (3) **treinar/ajustar para que essa probabilidade seja honesta** (80% de confiança ⇒ ~80%
de acerto). O Bee já faz (1) e (2) sem saber (a régua de sentimento lê logprob de " positivo" ×
" negativo"; o agêntico decide chamar/não chamar); **(3) nunca foi medido em nenhum modelo deste
projeto** — e é o que separa "o modelo decide" de "o software pode confiar na decisão".

---

## 1. O que cada fonte diz — e o que ela não mostra

### 1.1 TypeSafe — *Introducing System One Models and Jev* (Diogo Almeida, 15/09/2026)

- **System One model** = modelo que recebe um *estado* (texto/JSON) e *perguntas tipadas*, e devolve
  **decisões + probabilidades**, nunca texto. Três primitivos: **Choice** (uma opção entre N, com
  distribuição e `confidence`), **Score** (nível numa escala ordinal, valor ponderado pela
  distribuição), **Noul** (sim/não, devolve P(sim)). Todas as perguntas de uma chamada são avaliadas
  **em paralelo** sobre o mesmo estado (não sequencialmente, token a token).
- **RLCD** — *Reinforcement Learning for Calibrated Decisions* — é o nome que eles dão ao pós-treino.
  **Nenhum detalhe é publicado**: nem recompensa, nem perda, nem tamanho do modelo, nem pesos. O nome
  **não existe na literatura** (a busca do arXiv pelo termo devolve 105 artigos, nenhum com esse
  método); os métodos publicados com o mesmo objetivo se chamam RLCR, RLSR, *calibration-aware RL* (§1.4–1.6).
- Números que eles mesmos qualificam: 70–500 ms contra 3–329 s (40–200×); US$ 0,042/Mtok de entrada,
  saída grátis; "0% de alucinação" — **declaradamente não empírico**: é garantia de esquema (a saída
  sempre é uma das opções), não de acerto. O eval de workflows (evals.typesafe.ai) põe o Jev em
  **67,8% de acurácia média a US$ 0,0004 e 0,4 s/caso**, contra Opus 5 73,1% / US$ 0,18 / 38 s e
  Sonnet 5 67,8% / US$ 0,12 / 78 s — com o rótulo de referência sendo a **média de dois modelos da
  concorrência** (viés admitido) e as tarefas escritas pela própria equipe (viés admitido).
- **Limites lidos nos docs, não no blog:** só texto (sem imagem/áudio); **inglês é o idioma principal
  de treino — "outros idiomas, inclusive CJK, têm acurácia menor; teste no seu conteúdo"**; contexto
  64k por chamada (32k de estado); cardinalidade máxima 255; pesos fechados; rate limits "mudando
  dinamicamente". Para o Bee (PT-BR) isso é **uma variável a medir, não uma promessa**.

### 1.2 LangChain — *Building a Harness with Jev* (Runkle & Lovell, 17/09/2026)

Post de integração, não medição. O que transfere é o **desenho**: LLM para gerar, Jev para decidir.
Dois middlewares: **roteamento de modelo** (Jev classifica o pedido e escolhe o modelo barato ou o
caro) e **Auto Mode** (Jev classifica cada chamada de ferramenta como arriscada ou não *antes* de
executar — o padrão dos harnesses de código, que era fechado, exposto como classificador barato).
Chamada: `TypeSafeClassifier().invoke(state=..., questions={"urgent": Noul(...)})` →
`response.nouls["urgent"].noul` (0,999 no exemplo). Nenhum número de acurácia.

### 1.3 MIT CSAIL — *Teaching AI models to say "I'm not sure"* (21/04/2026) → **RLCR** (arXiv 2507.16806, ICLR 2026)

A fonte de verdade por trás da notícia. **RLCR = Reinforcement Learning with Calibration Rewards:**

- O modelo raciocina, responde **e emite uma confiança verbalizada** q ∈ [0,1]. A recompensa é
  **correção + Brier**: `R = 1[y=y*] − (q − 1[y=y*])²`.
- **Teorema 1:** com qualquer *proper scoring rule* **limitada** (Brier, esférica) a recompensa é
  maximizada quando q = P(acerto) **e** y é a resposta mais provável — calibração sem custo de
  acurácia. ⚠️ **Com log-loss (ilimitada) o teorema cai**: o modelo pode preferir errar de propósito
  com q=0 para zerar a penalidade. Isso importa se alguém for implementar.
- **Medido (Qwen2.5-7B base, GRPO sem KL, 32 rollouts, batch 2048):** HotpotQA in-domain — RLVR
  acc 63,0% / ECE 0,37; **RLCR acc 62,1% / ECE 0,03**; classificador BCE separado ECE 0,07 (e custa
  um segundo modelo de 7B). Fora do domínio (6 datasets): RLVR **piora** a calibração do base
  (0,40 → 0,46), RLCR melhora (0,21). Em matemática: RLVR ECE 0,26 → RLCR 0,10, mesma acurácia.
- ⭐ **Achado que muda desenho:** RL puro com recompensa binária **destrói calibração** — o modelo fica
  mais capaz e mais superconfiante ao mesmo tempo (Puri). E a **ablação** (Tabela 2): só a
  recompensa (sem raciocinar sobre incerteza) já leva ECE 0,37 → 0,09 com o mesmo custo de tokens
  do RLVR; só o prompt de "analise sua incerteza" sem a recompensa dá 0,34 — **treinar vale 10× mais
  que pedir**.
- Bônus de inferência: a confiança verbalizada serve de *reward model* grátis — votação ponderada
  por confiança bate votação simples e best-of-N por verossimilhança.
- O que não mostra: só 7B, só Qwen; tarefas de resposta única (HotpotQA/matemática); a variante
  SFT+RLCR (melhor calibração) **perdeu 7 pp de acurácia OOD** por esquecimento — o aquecimento SFT
  não é grátis.

### 1.4 arXiv 2601.13284 — *Balancing Classification and Calibration in Decision-Making LLMs via Calibration-Aware RL* (Yaldiz et al., USC/AWS, 19/01/2026)

O artigo mais próximo do que o Bee faz, porque a confiança aqui **não é verbalizada — é a
probabilidade do token de decisão** (`P(y_d | x, raciocínio)`), que é o que se tem "de graça" num
modelo local.

- **Setup:** Qwen3-1.7B/4B/8B, LoRA r16, tarefas de decisão (CommonsenseQA, OpenBookQA, moderação
  OpenAI, XSTest), 500 exemplos de treino, ~500 GPU-h no total.
- **Key Finding 1 — o trade-off:** SFT calibra (ECE 29,9 → 7,4 no 1.7B/CSQA) com ganho modesto de
  acurácia (+1 pp); GRPO ganha mais acurácia (+6 pp) e **fica superconfiante** (ECE 24,4; quase toda
  predição com p > 0,99). *"A redução de ECE do GRPO é só a acurácia subindo; a distribuição de
  confiança é indistinguível do base."*
- **Key Finding 2 — por que RL não consegue calibrar:** amostrando 64 rollouts por pergunta,
  **97,6–99,9% têm p(token de decisão) > 0,99**, certo ou errado. Não há rollout calibrado para o RL
  reforçar. Vale para qualquer base moderno: *"achar um LLM instruído e bem calibrado é difícil"*.
- **Key Finding 3 — o token de decisão é EXTRAÇÃO, não avaliação:** trocando o raciocínio pelo de um
  exemplo com o rótulo oposto, **92–100% das decisões viram** — e continuam com p ≈ 1. O token só
  copia a conclusão do raciocínio; não carrega a incerteza. ⭐ Isso é a versão formal do que este
  projeto mediu como "o modelo aprendeu a CONTAR" (§2u): a decisão herda o atalho do texto anterior.
- **Método (uma linha de perda):** GRPO em todos os tokens **exceto** o de decisão (vantagem zerada
  ali) **+ λ·CE no token de decisão com alvo one-hot se acertou e UNIFORME se errou** (λ = 0,001), com
  a probabilidade presa em [1/|C|, 1] para o greedy não virar. Resultado: acurácia do GRPO mantida,
  ECE 24,4 → 16,0 (1.7B), 16,8 → 12,9 (4B), 14,8 → 10,6 (8B); em OOD (OBQA) 11,5 → 5,3, 6,7 → 1,9.
  Pós-hoc (isotônica) em cima leva a 2,8–3,8. **Não chega ao SFT em calibração; chega ao GRPO em
  acurácia.**
- Prompts publicados (Apêndice B); código não.

### 1.5 arXiv 2603.06604 — *Know When You're Wrong* (Xie, Liu, Yao — Amazon Alexa, 18/02/2026)

- **Confiança normalizada:** `ĉ(y|x) = c(y|x) / Σ_{y'∈Y} c(y'|x)` — a probabilidade do rótulo
  **renormalizada só sobre as opções válidas**, não sobre o vocabulário inteiro. AUROC até **+33%**
  contra a probabilidade crua. ⭐ **É exatamente o que `eval_sentimento_pt.py` já calcula** (logprob
  de " positivo" e " negativo" no mesmo prompt) — o Bee tem isso e nunca leu a calibração.
- **Auto-avaliação para geração aberta:** gerar, depois perguntar *"Esta resposta está correta?
  Sim/Não"* e ler P(Sim)/(P(Sim)+P(Não)) no **primeiro token** (`max_tokens=1`). AUROC 0,75–0,86 em 5
  famílias sem treinar nada — a capacidade é emergente; a **calibração** não é (ECE 0,11–0,26).
- **Teoria simples e útil:** SFT/pré-treino = MLE = minimiza KL(dados ‖ modelo) ⇒ calibra por
  construção; PPO/GRPO = gradiente ponderado por vantagem ⇒ **afia** a distribuição (mesma vantagem
  pequena, massa exponencialmente maior); DPO otimiza *razão* de preferência, não probabilidade
  absoluta ⇒ também afia. Medido no Qwen3-4B com o **mesmo dado**: SFT AUROC 0,879 / ECE 0,034;
  GRPO 0,809 / 0,135; DPO 0,785 / 0,117.
- **Receita prática:** um SFT leve **depois** do RL, com **auto-destilação** (o próprio modelo gera
  as respostas, filtra-se as corretas) restaura a calibração **sem** perder acurácia (GSM8K 92,5% →
  94,6% com auto-destilação; **83,1%** se o SFT usar os rótulos originais do dataset — é o §2ab do
  projeto em outra roupa: mudar a forma do alvo custa capacidade).
- **Aplicação medida:** RAG adaptativo — recuperar só quando ĉ < τ usa **58% das buscas** e captura
  **95% do ganho** de recuperar sempre (TriviaQA). ⭐ É a mesma economia do "recuperar antes de
  perguntar" do Bee, com a confiança do modelo decidindo *quando* recuperar.

### 1.6 arXiv 2607.03528 — *Aligning LMs with Selective Prediction* (RLSR, Luo et al., Minnesota, 03/07/2026)

- Tese: **calibração ≠ seleção.** Calibração pede que 80% signifique 80%; seleção pede que **os
  acertos fiquem ranqueados acima dos erros** (métrica: AURC — área da curva risco × cobertura). Um
  modelo perfeitamente calibrado pode selecionar mal e vice-versa.
- **RLSR:** recompensa = ±α_i, com α_i o peso harmônico do *rank* de confiança dentro do lote
  (B×G rollouts agrupados, 1.536 amostras). "Lifted AURC" = sinal ± para criar push-pull entre
  certos e errados.
- **Medido (Qwen2.5-7B, HotpotQA):** AURC RLVR 0,56 · RLCR 0,51 · **RLSR 0,44**; acurácia a 10% de
  cobertura 45,5 / 53,5 / **66,0%**. **RLCR tem o melhor ECE (0,05) e perde em AURC** — as duas
  coisas são objetivos diferentes. Tabela 2 (controlando acurácia): E[c|certo] − E[c|errado] =
  0,01 (RLVR), 0,06 (RLCR), **0,37 (RLSR)**.
- Para o Bee, a lição é de **desenho de gate**: se o uso é "agir só quando confiante", a régua é
  **acurácia@cobertura / AURC**, não ECE.

### 1.7 A busca do arXiv (105 resultados, 22 relevantes)

A query é o termo de marketing da TypeSafe, então a maioria é ruído (calibração de sensores, RL em
trânsito, gêmeos digitais). Os 22 relevantes se organizam em 4 famílias, todas de 2025–26:

| família | representantes | o que acrescenta |
|---|---|---|
| RL com regra de pontuação | 2507.16806 (RLCR), 2603.29492 (radiologia), 2609.16601 (SAVOR, multimodal) | Brier/log-clipado como recompensa; funciona em texto, imagem e laudo |
| RL na cabeça de decisão | **2601.13284**, 2606.08543 (PAEC: entropia por posição no RLVR) | intervir no token de decisão, não na trajetória |
| seleção/abstenção | **2607.03528** (RLSR), 2502.06884 (abstenção conformal aprendida por RL, garante 90% de cobertura), 2606.29863 (KbSD: fronteira de conhecimento em busca agêntica — quando confiar na memória, quando buscar, quando abster) | a métrica certa é AURC; abstenção como ação treinável |
| estado de crença em agentes | 2605.11436 (Agent-BRACE: claims atômicos com rótulo ordinal de certeza; +14,5 pp em tarefas longas num 3B) | confiança por **fato**, não por resposta — o que um harness de agente consome |

⚠️ **synthszr.com** (glossário) não respondeu (timeout em curl, no Chrome e via fetch) — não lido.

---

## 2. O que é a "capacidade de decisão", destilado

Três peças, e cada uma tem um instrumento:

1. **Formulação como decisão.** Perguntas com espaço de resposta fechado (Choice/Score/Noul).
   Instrumento: o *estado* + a pergunta viram um prompt cujo próximo token é o rótulo.
2. **Probabilidade lida, não gerada.** `ĉ = P(rótulo | x)` renormalizada sobre as opções válidas
   (2603.06604 eq. 1). Custa **um forward, zero geração** — 100–500× mais barato que uma resposta
   de LLM, e é isso que sustenta os "40–200×" da TypeSafe. Qualquer modelo local dá isso de graça.
3. **Honestidade da probabilidade.** Duas réguas distintas (2607.03528): **ECE/Brier** (80% ⇒ 80%)
   e **AURC/acurácia@cobertura** (os acertos ficam no topo). E três formas de obtê-la, em ordem de
   custo: **pós-hoc** (temperatura/Platt/isotônica num split de calibração, US$ 0) → **SFT** (calibra
   por MLE, mas ganha pouca acurácia) → **RL com perda de calibração** (RLCR/2601 §5; ganha acurácia
   sem perder calibração; caro: rollouts).

E uma lei transversal, medida por três grupos independentes: **RL com recompensa binária afia a
distribuição e destrói a calibração; SFT a preserva.** Qualquer plano de RL no Bee (o E6 já testou
DPO/IPO/KTO) tem de medir ECE/AURC ao lado da acurácia — o projeto nunca mediu.

---

## 3. O que o Bee já tem disso (sem nome) e o que nunca mediu

| peça | existe no Bee? | onde | medido? |
|---|---|---|---|
| decisão Noul | **sim** — chamar/não chamar ferramenta (over/under-call) | `eval_agentic_exec.py`, holdout balanceado 536/268 | acurácia sim; **P(chamar) nunca lida** |
| decisão Choice | **sim** — seleção de ferramenta no catálogo | idem, `tool_right` | acurácia sim; **distribuição sobre o catálogo nunca lida** |
| decisão Noul por logprob | **sim** — sentimento " positivo" × " negativo" | `eval_sentimento_pt.py` | acurácia (81,8% e13 · 56,0% C-full); **ECE nunca** |
| confiança para rotear | **sim, fora do modelo** — o recuperador IDF (§ "recuperar antes de perguntar": 90,1% × 48,5%) | `comeia/eval` | como filtro, não como confiança |
| calibração de qualquer coisa | **não** | — | **nunca** |
| seleção (agir só quando confiante) | **não** | — | nunca |

⭐ **A leitura mais importante deste estudo é a §2q aplicada a nós mesmos:** todos os vereditos
agênticos do projeto (E8–E19, gate #3) são sobre **acurácia a 100% de cobertura**. Não há um número
que diga se o modelo *sabe quando erra*. E há motivo para suspeitar que não sabe: o atalho da §2u
(catálogo 1–2 ⇒ chame; 6 ⇒ recuse) é o caso limite de decisão-como-extração do 2601.13284 — a
confiança de um atalho é ~1 por construção.

---

## 4. Dá para o Bee ter essa capacidade? Sim — em três degraus, e o primeiro é hoje

**Degrau 0 — sem treinar nada (US$ 0, horas):** um `bee/decidir.py` que recebe estado + perguntas
(Choice/Score/Noul), monta o prompt, e lê `ĉ` no primeiro token da resposta, renormalizada sobre as
opções. Serve para qualquer modelo do projeto (350M base, adapters, o 1G quando sair). O que se ganha
de imediato: **a régua de calibração** (ECE, Brier, AUROC, AURC, acurácia@cobertura) para tudo que já
existe. É o gate G-C1 da §6.

**Degrau 1 — calibrar pós-hoc (US$ 0):** temperatura/Platt/isotônica ajustadas num split de
calibração (20% do holdout, nunca o de teste — §2o). O 2601.13284 mede que a isotônica sobre um GRPO
leva ECE 12 → 5 e sobre o modelo deles 9 → 3. Se o Degrau 0 mostrar AUROC alto e ECE alto (o padrão
"discriminação boa, calibração ruim" que o 2603 acha em cinco famílias), este degrau resolve a maior
parte de graça.

**Degrau 2 — treinar para isso.** Duas rotas, e o projeto tem a pré-condição rara para a segunda:
- *SFT com auto-destilação* (2603.06604): já é o que o E19 faz — as guardas dos negativos úteis são
  a mesma ideia. O custo é o de sempre (698 passos, 3 sementes).
- *RL com recompensa verificável + calibração* (RLCR/2601 §5): **o Bee tem um verificador
  determinístico** (o executor de mundo aberto que pontua `exec_ok`) — exatamente a "recompensa
  verificável" que RLVR/RLCR exigem e que a maioria das tarefas não tem. Um GRPO com
  `R = exec_ok − (q − exec_ok)²` (ou o CE no token de decisão do 2601) é implementável com o TRL que
  já usamos, em LoRA no 350M, numa 5090. ⚠️ Mas o E6 mediu que DPO/IPO ficaram **dentro do ruído**
  em acurácia, e o 2601 mediu que RL sozinho **piora** calibração — este degrau só entra depois de os
  Degraus 0 e 1 dizerem quanto falta, e com ECE/AURC como métrica primária, não acurácia.

**E o Bee-1G (base multilíngue):** um modelo base decide por logits como qualquer outro (o 2601 usa o
mesmo prompt "responda com UMA letra" no modo sem raciocínio). Acurácia será a de um base; a
**calibração de um base tende a ser melhor que a de um instruído** (2601 Apêndice D, 2603 §4.1) —
vale medir no marco_15B como linha de base, custa minutos.

---

## 5. Onde mais isso encaixa (fora do Bee)

| sistema | decisão que hoje é LLM ou regra | forma System One | ganho esperado | risco a medir |
|---|---|---|---|---|
| **Chimera** (VPS, OpenRouter) | triagem de suporte do PassaPro, urgência, roteamento de job, "esta ação de ferramenta é arriscada?" | Noul/Choice com `confidence` gate; **Auto Mode** antes de `run_shell`/SQL | latência 0,4 s × dezenas de s; custo ~US$ 0,0004/decisão; **calibração** para escalar ao humano | PT-BR "lower accuracy" (docs); medir ECE no nosso histórico de tickets antes de ligar |
| **PassaPro** | classificação de dúvidas, detecção de intenção, moderação | Choice/Score em batch (map-reduce sobre a base) | custo 100× menor que LLM | idem PT-BR; pesos fechados = dependência |
| **Trading (Chimera/eToro)** | leitura de regime/cenário | Score calibrado como *input* de regra, nunca como ordem | probabilidade honesta em vez de "confiante" | **hard rules continuam mandando**; RL de decisão em finanças é onde o 2502.06884 (abstenção conformal) é o padrão certo, não o Jev |
| **Harness do Claude/Chimera** | "vale a pena chamar o modelo caro?" | roteamento por confiança (LangChain middleware) | menos chamadas caras | o roteador tem de ser calibrado, senão só move o erro |

⚠️ **Antes de qualquer adoção do Jev:** o `system-one-adapter-python` (MIT, 27 KB de cliente) roda
**a mesma pergunta num LLM barato** (OpenAI/Anthropic, modo `probabilities`) com o mesmo contrato de
resposta — é o instrumento para comparar Jev × Haiku × o próprio Bee **na mesma régua, nos nossos
dados em PT** (§2g). Sem isso, "40–200×" é a medição deles em inglês nas tarefas deles.

---

## 6. Gates propostos (custo declarado; ordem = do grátis ao caro)

| gate | pergunta | como | custo | veredito declarado antes |
|---|---|---|---|---|
| **G-C1** calibração do agêntico | os adapters (e13, C-full, recusa_esp., 3 sementes) sabem quando erram? | `bee/decidir.py` sobre o holdout balanceado: P(chamar) no 1º token; distribuição sobre o catálogo; ECE, Brier, AUROC, **AURC e acurácia@50%** | 5070, ~20 min/adapter, US$ 0 | previsão pré-registrada: AUROC 0,70–0,85 (emergente, 2603); ECE > 0,15 (superconfiança de SFT em catálogo balanceado); **se AUROC < 0,6, a confiança é o atalho e o Degrau 1 não salva** |
| **G-C2** sentimento | e13 × C-full: 81,8 × 56,0 de acurácia — e a calibração? | ECE/AUROC sobre os logprobs que a régua já calcula | minutos, US$ 0 | se o e13 tem AUROC alto, o número dele é capacidade; se ECE alto e AUROC ~0,5, é viés de classe (o base cravava 554/600 "positivo") |
| **G-C3** pós-hoc | temperatura/isotônica num split de 20% | sobre G-C1 | US$ 0 | ECE cai para < 0,05 sem mudar acurácia (2601 Tab. 5) |
| **G-C4** base 1G | calibração do marco_15B em decisão de 1 letra (CSQA-PT? não existe) → usar o holdout agêntico como Choice no base | minutos | linha de base para comparar com o pós-treino |
| **G-C5** Jev × Bee × Haiku em PT | 200 casos do holdout agêntico como Noul/Choice pelo adapter | US$ ~2 de API | mede o "lower accuracy" em PT que os docs declaram |
| **G-C6** RLCR/2601 no 350M | GRPO+Brier com o executor como recompensa | 5090, ~8 h, US$ ~10 | só se G-C1/G-C3 deixarem AURC ruim e acurácia estagnada; métrica primária AURC |

**Não fazer:** trocar o E19 por "Jev decide" no produto sem G-C5; usar log-loss como recompensa
(Teorema 1 do RLCR — incentiva errar de propósito); ler ECE como prova de seleção (RLSR).

---

## 7. Ressalvas de rigor das fontes

- TypeSafe: sem paper, sem pesos, sem método; evals com referência = média da concorrência e tarefas
  próprias; "0% alucinação" é esquema, não acerto; inglês primeiro. **Vendedor, não medição.**
- LangChain: post de parceria, zero números.
- RLCR (MIT): sólido — teorema, ablação, OOD, código público; só 7B/Qwen.
- 2601.13284: sólido no diagnóstico (Tabelas 2–3 são o achado); o método fica **atrás do SFT** em
  calibração e não publica código; 500 GPU-h.
- 2603.06604: teoria de bar (KL vs vantagem) mas as medições no mesmo dado são limpas; Alexa.
- RLSR: 5 sementes, dois modelos, código; o argumento "calibração ≠ seleção" é o mais transferível.
- Busca do arXiv: termo de marketing; 83 de 105 resultados são ruído.

Artefatos deste estudo (scratch, não versionados): textos completos dos 7 artigos, `llms-full.txt`
da TypeSafe (874 KB), árvore do adapter, `busca.json` com os 105 abstracts.
