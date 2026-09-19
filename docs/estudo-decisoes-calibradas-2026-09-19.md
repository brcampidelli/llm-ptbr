# Decisões calibradas — Jev/System One, RLCD, RLCR, RLSR — e o que isso vale para o Bee (2026-09-19)

> Estudo dos 6 links pedidos + os arquivos que eles apontam (docs completos da TypeSafe em
> `llms-full.txt`, o repositório `system-one-adapter-python`, a página de evals, o artigo do MIT no
> texto completo, o 2601.13284 no texto completo, e os 105 resultados da busca do arXiv com os 5 mais
> relevantes lidos por inteiro). Regra do projeto: **o número do artigo não entra como resultado; só o
> que for medido aqui entra**. A seção 6 diz o que medir e quanto custa; **G-C1, G-C3 e G-C1b estão
> medidos nas §§8–10** (US$ 0, RTX 5070, 2026-09-19).

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
| **G-C3** pós-hoc ✅ §9 | temperatura/isotônica num split de 20% | sobre G-C1 | US$ 0 | ECE cai para < 0,05 sem mudar acurácia (2601 Tab. 5) |
| **G-C1b** Noul de argumentos ✅ §10 | o modelo sabe quando a própria chamada está errada? | auto-avaliação Sim/Não no 1º token + verossimilhança teacher-forced dos argumentos, sobre o greedy do G-C1 | 5070, ~25 s/adapter, US$ 0 | c_sim AUROC < 0,6 (nunca treinado); logP dos argumentos AUROC 0,60–0,70; combinada sobe o fim-a-fim para 0,70–0,75 |
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

---

## 8. G-C1 medido (2026-09-19) — o Bee-350M já decide calibrado onde é SFT, e é superconfiante onde não é

`comeia/eval/calibracao_agentica.py` · 12 adapters (e13, C-full, recusa específica, catálogo perturbado
× 3 sementes) · holdout balanceado (536 tool / 268 texto) · RTX 5070 · transformers 5.14.1 · ~3,4 min
por adapter, um forward por caso + um lote por catálogo (zero geração). Artefato:
`calibracao-agentica-350m-2026-09-19.json`. **Guarda de aparato:** a escolha de ferramenta lida por
logit reproduz o greedy da eval em **98,1–98,8%** dos casos (mesma régua, §2g); e dois defeitos foram
pegos antes de confiar — o `--data` default apontava para o holdout ANTIGO (14 ferramentas: under-call
95%, AUROC 0,50, visto ao ler o top-5 do 1º token), e o `transformers 5.14.1` isolado tinha sido
apagado pela limpeza do Temp (reinstalado, versões impressas no log).

| braço (média de 3 sementes) | Noul "chamar?" AUROC · ECE · conf>0,99 | Choice "qual?" acc · ECE · AUROC | fim-a-fim acc@25 → @50 → @100 · ECE · AUROC (corrigido, ver ⚠️) |
|---|---|---|---|
| e13 (recusa em template) | **0,928** · 0,083 · 39% | 0,923 · **0,042** · 0,915 | **0,945** → 0,891 → 0,769 · 0,142 · **0,735** |
| C-full (resposta útil) | 0,901 · **0,127** · 36% | 0,918 · 0,039 · 0,937 | 0,904 → 0,853 → 0,740 · 0,178 · 0,696 |
| recusa específica | 0,931 · 0,076 · 39% | 0,912 · 0,049 · 0,920 | 0,924 → 0,879 → 0,774 · 0,137 · 0,723 |
| catálogo perturbado | 0,901 · 0,115 · 35% | 0,922 · 0,041 · 0,938 | 0,929 → 0,865 → 0,751 · 0,168 · 0,701 |

⚠️ **Correção no mesmo dia (ao preparar o G-C3):** a primeira versão desta coluna contava **todo caso de
texto como certo** — o despejo da eval só rotula `ferramenta_pred` nos casos de ferramenta; nos de texto
o over-call está em `over_call`, e o cruzamento lia só o primeiro campo (acc@100 saía 0,79–0,83; o certo
é 0,74–0,77, e o AUROC fim-a-fim é **0,70–0,74**, não 0,64–0,66 — os over-calls têm confiança baixa e,
contados como erro, *melhoram* a discriminação). Família da §2z: um `join` que não acha o campo não
dá erro; dá um número plausível. Reconstruído sem GPU (`--rejuntar`) a partir dos `casos_calib_*.jsonl`.

**Previsão pré-registrada × medido:** AUROC previsto 0,70–0,85 → medido **0,90–0,93** (errei para o
lado pessimista: a confiança do Bee **não** é o atalho da §2u — o holdout balanceado tirou o atalho e a
confiança sobreviveu); "ECE > 0,15" → **não** no Noul (0,08–0,13) nem no Choice (0,04), **sim** no
fim-a-fim (0,16–0,21). O que os artigos previam e se confirmou: SFT calibra (Choice ECE 0,04 em 12/12).

Três achados, todos com 3 sementes por braço:

1. **A escolha de ferramenta já é calibrada e discriminativa** (ECE 0,03–0,06, AUROC 0,89–0,95, acc
   0,90–0,93 em catálogos de 2–6). Nenhuma intervenção necessária — e o Bee ganha de graça a garantia
   de esquema que a TypeSafe vende ("0% de alucinação"): `--restrito-ferramenta` já a dá desde o E10.
2. **A decisão de chamar separa bem e é superconfiante em todos os braços**: 31–47% dos casos com
   confiança > 0,99; o pior ECE (C-full, 0,127) coincide com o maior under-call por logit (**25,9%**
   dos casos de ferramenta abaixo de p=0,5 contra 15,6% do e13) — o modelo diz "não chamo" com 99% e
   deveria chamar. É onde o G-C3 (temperatura/isotônica, US$ 0) tem o que fazer, e é uma **leitura
   nova do E19**: os 5,9 pp de execução que o C-full custou são, em parte, **confiança mal posta**,
   não capacidade — um limiar movido recuperaria chamadas sem retreinar (medido no G-C3, §9, com o
   custo em over-call ao lado, §2r). ⚠️ *"Under-call por logit"* (p<0,5) **não é** o under-call do
   greedy: o greedy é argmax do 1º token, e com a massa restante espalhada por muitos tokens de texto
   o `{` é argmax com p bem abaixo de 0,5 — o menor p entre casos que o greedy chamou é **0,14** em
   todos os 12 adapters. O under-call real do C-full é **15,8%** (80–87/536), não 25,9%.
3. **Roteamento por confiança funciona hoje, sem treinar** — o quartil mais confiante acerta
   **90–95%** contra 74–77% no total — **e tem teto**: a confiança p_call·p_tool enxerga pouco o erro
   de argumento (AUROC fim-a-fim 0,70–0,74 depois da correção acima; o #4b mediu que a maioria dos
   erros restantes é de argumento). A terceira pergunta é o Noul de auto-avaliação do 2603.06604 ("os argumentos estão
   completos e corretos? Sim/Não" lido no 1º token) — uma linha a mais no mesmo instrumento; entra
   como G-C1b.

⚠️ O que este gate não mostra: calibração em catálogos inéditos (o holdout é balanceado por
construção, catálogos de 1–6); a confiança sob `--restrito-ferramenta` (aqui o Choice é livre sobre
o catálogo — mas o greedy restrito concorda em 98%); e o custo do limiar movido (G-C3 mede).

---

## 9. G-C3 medido (2026-09-19) — temperatura conserta a confiança; o limiar era o argmax, e mover o limiar compra execução pagando em over-call 1:1

`comeia/eval/calibracao_poshoc.py` (US$ 0, CPU, sobre os `casos_calib_*.jsonl` do G-C1) +
`comeia/eval/calibracao_poshoc_realizado.py` (a versão **realizada**: gera a chamada forçada para os casos
que o limiar recupera — `eval_agentic_exec.py --forcar-chamada --indices`, config de referência §2aa, RTX
5070, ~2 min por semente). Artefatos: `calibracao-poshoc-350m-2026-09-19.json`,
`calibracao-poshoc-realizado-350m-2026-09-19.json`.

**Protocolo.** Três mapas monótonos p → p′ sobre o Noul "chamar?" (p_call do G-C1): **temperatura**
(σ(z/T), 1 parâmetro), **Platt** (σ(a·z+b)), **isotônica** (PAV). Ajuste em 2 dobras estratificadas —
cada caso é avaliado pelo mapa ajustado na *outra* metade — repetido em 5 sorteios (o ± abaixo é o piso do
sorteio). Quarto protocolo, **transferência**: mapa ajustado nas outras duas sementes da receita, aplicado à
terceira. Métricas do G-C1 sobre a probabilidade (ECE_prob, Brier, NLL) e sobre a decisão a 0,5 (acurácia,
under/over-call, ECE da confiança, AUROC, AURC). Duas invariâncias declaradas antes: mapa monótono **não
muda o ranking** (AUROC(p vs classe) igual por construção), e temperatura pura **não move o corte**
(z/T = 0 ⇔ z = 0) — ela corrige a confiança, não a decisão.

### 9.1 O que a calibração pós-hoc faz (média de 3 sementes ± dp entre sementes)

| receita | protocolo | acurácia | under | over | ECE_prob | **ECE_conf** | conf>0,99 | corte em p cru |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **C-full** | greedy (argmax) | — | **0,158** | 0,144 | | | | p mín. chamado **0,141** |
| | logit, corte 0,5 (G-C1) | 0,784 | 0,259 | 0,132 | 0,157 | 0,127 | 36% | 0,5 |
| | temperatura 2-dobras (T≈2,2) | 0,784 | 0,259 | 0,132 | 0,123 | **0,042**±0,013 | 1% | 0,5 |
| | Platt 2-dobras | 0,855 | 0,103 | 0,230 | 0,058 | 0,044 | 9% | 0,139 |
| | isotônica 2-dobras | 0,856 | 0,083 | 0,266 | **0,040** | 0,035 | 25% | 0,064 |
| | transferência (isotônica) | 0,857 | 0,083 | 0,264 | 0,034 | **0,023** | 16% | 0,094 |
| **e13** | greedy (argmax) | — | 0,091 | 0,173 | | | | 0,152 |
| | logit, corte 0,5 | 0,850 | 0,156 | 0,137 | 0,102 | 0,083 | 39% | 0,5 |
| | temperatura 2-dobras (T≈1,8) | 0,850 | 0,156 | 0,137 | 0,097 | **0,024** | 1% | 0,5 |
| | Platt 2-dobras | 0,869 | 0,093 | 0,207 | 0,047 | 0,023 | 11% | 0,179 |
| | isotônica 2-dobras | 0,876 | 0,051 | 0,269 | 0,034 | 0,030 | 34% | 0,067 |
| | transferência (isotônica) | 0,881 | 0,053 | 0,252 | 0,031 | 0,029 | 26% | 0,067 |
| recusa específica | logit 0,5 → temperatura → isotônica | 0,854 → 0,854 → 0,882 | 0,161 → 0,161 → 0,074 | 0,117 → 0,117 → 0,205 | 0,106 → 0,084 → 0,031 | 0,076 → **0,019** → 0,027 | 39% → 4% → 28% | 0,5 → 0,5 → 0,124 |
| catálogo perturbado | logit 0,5 → temperatura → isotônica | 0,796 → 0,796 → 0,856 | 0,233 → 0,233 → 0,093 | 0,147 → 0,147 → 0,246 | 0,152 → 0,123 → 0,041 | 0,115 → **0,037** → 0,033 | 35% → 1% → 27% | 0,5 → 0,5 → 0,126 |

Três leituras:

1. ⭐ **Temperatura (T ≈ 1,6–2,3) leva o ECE da confiança de 0,08–0,13 para 0,02–0,04 em 12/12, sem
   tocar em uma decisão** — e a fração de casos com confiança > 0,99 cai de 31–47% para 1–4%. É o
   resultado pré-registrado (2601 Tab. 5) e sai de graça: **um escalar por receita**. A transferência
   entre sementes dá o mesmo (ECE_conf 0,03–0,05 com o T das irmãs): o mapa é da *receita*, não do
   artefato — calibra-se uma vez.
2. 🔴 **O "corte 0,5 no logit" do G-C1 era a regra de decisão errada, e o greedy já a corrigia.** A
   decisão real é argmax do 1º token sobre 32k tokens; `{` ganha com p bem abaixo de 0,5 porque o resto
   da massa se espalha por centenas de inícios de texto — em todos os 12 adapters o menor p entre
   casos que o greedy chamou é **0,10–0,19**. Platt e isotônica, ajustados sem ver o caso, colocam o
   corte em **0,06–0,18** — em cima do argmax. Logo o "under-call por logit 25,9%" do §8 era um artefato
   da regra 0,5: o under-call real do C-full é **15,8%**, e a acurácia da decisão (0,78 → 0,86) que os
   mapas "ganham" é, em sua maior parte, a que o greedy já tinha. ⚠️ Lição de instrumento: **ler a
   probabilidade de uma classe contra um limiar fixo, quando a decisão é argmax contra um vocabulário
   inteiro, mede outra coisa** — a confiança da decisão tem de ser lida na régua da própria decisão.
3. A isotônica devolve conf > 0,99 em 25–34% dos casos (degraus com acerto 1,0 nos blocos extremos) —
   é calibrada *neste* holdout, mas com n = 402 por dobra é a que mais varia entre sorteios (dp do
   ECE_prob 0,005–0,011 contra 0,000–0,004 da temperatura). Para produção: temperatura para a confiança,
   e o limiar escolhido pelo custo (abaixo), não pelo mapa.

### 9.2 O limiar movido, REALIZADO no C-full (3 sementes) — o teto valia, e a conta é 1:1

Política medida: **a decisão é do logit (p_call ≥ τ), a geração é do greedy**. Caso que o greedy já
chamou → inalterado; caso tool que o greedy *não começou* a chamar e p ≥ τ → chamada gerada com o
prefixo `{"tool": "` forçado (restritor de esquema por cima) e executada; caso texto não chamado com
p ≥ τ → over-call **por construção** (custo exato, sem gerar). Chamadas que o greedy *começou* e não
parseou (12/11/14 por semente) ficam **fora**: forçar o prefixo reproduz o mesmo bruto (0 de 11
recuperadas quando eu as incluí) — é defeito de geração, não de decisão. Base: exec_ok 372/367/359 de
536 (68,3%), over-call 39/37/40 de 268 (14,4%), under-call próprio 80/87/87.

| τ | tool recuperados | dos quais exec_ok | P(exec_ok \| recuperado) | texto → over-call | **Δ exec_ok** | **Δ over-call** |
|---:|---:|---:|---:|---:|---:|---:|
| 0,35 | 2,7 | 1,7 | 0,72 | 3,3 | +0,3 pp | +1,2 pp |
| 0,30 | 5,0 | 3,7 | 0,79 | 4,7 | +0,7 pp | +1,7 pp |
| 0,25 | 9,0 | 7,3 | 0,82 | 5,7 | +1,4 ± 0,3 pp | +2,1 ± 1,5 pp |
| 0,20 | 15,7 | 14,0 | 0,88 | 9,3 | +2,6 ± 0,9 pp | +3,5 ± 2,4 pp |
| **0,15** | 27,0 | 24,0 | **0,88** | 15,0 | **+4,5 ± 1,0 pp** | **+5,6 ± 3,0 pp** |
| 0,10 | 39,3 | 32,3 | 0,82 | 24,0 | +6,0 ± 1,0 pp | +9,0 ± 3,7 pp |

- ⭐ **As chamadas recuperadas executam tão bem quanto as espontâneas (0,82–0,88 contra 0,84 média):**
  o modelo *sabia* a ferramenta (o Choice acerta 78–100% dos recuperados, conforme semente e τ) e os argumentos — só não
  começou a chamar. O teto do §9.1 (recuperados × P(exec_ok|chamou)) **não era otimista** aqui:
  realizado 30/19/23 contra teto 25/19/23 por semente. É o caso raro em que a §2r não morde — e só se
  sabe porque foi medido.
- ⭐⭐ **Reinterpretação do E19.** Os 5,9 pp de execução que o C-full custava contra o e13 eram, em
  boa parte, **limiar**: com τ = 0,15 o C-full vai a exec_ok **72,8%** com over-call **20,0%** — em
  cima do ponto de operação do próprio e13 (74,0% · 17,3%). A "forma da classe negativa" (§2ab)
  moveu a **disposição** de chamar, não a capacidade de chamar certo. O que se paga é o mesmo que se
  ganha, em casos: a cada tool recuperado, ~0,6 texto vira over-call (τ 0,15: 24 contra 15 por
  semente) — no holdout balanceado isso é lucro; **na produção o τ é decisão de custo** (o que custa
  mais, uma ferramenta a menos ou uma chamada a mais?), e a variância entre sementes do custo
  (dp 3,0 pp) é maior que a do ganho (1,0 pp).
- ⚠️ O que isto não mostra: o holdout é balanceado por construção (§2u), catálogos de 1–6; os deltas
  são pareados por caso, mas a base greedy de s43/s44 veio do pod 4090 e a de s42 da 5070 (§2ae, ~2
  casos/536 de deriva — entra na base, não no delta); e um só τ para as três sementes foi escolhido
  *olhando* a curva — o τ de produção sai do custo, não desta tabela.

**Previsão pré-registrada × medido:** ECE_conf < 0,05 com qualquer mapa → ✅ (0,035–0,044 no C-full,
0,02–0,03 no resto); corte em 0,2–0,35 → ❌ **0,06–0,18** (e a razão foi entender que a decisão é argmax);
under-call 26% → <15% → ✅ no quadro do logit (8–10%), mas a base certa era o greedy (15,8%); teto
+5–12 pp e realizado menor → realizado **+4,5 pp** a τ 0,15 e **igual ao teto**, não menor;
transferência a < 0,02 de ECE da 2-dobras → ✅ (0,00–0,02).

---

## 10. G-C1b medido (2026-09-19) — o modelo não sabe se auto-avaliar (responde `{` a tudo); a verossimilhança dos argumentos é o sinal barato que existe, e vale +4 pp no quartil confiante

`comeia/eval/calibracao_argumentos.py` · 12 adapters · população = casos em que o greedy **chamou**
(478–522 por adapter; 439–479 de ferramenta) · RTX 5070 · **um forward por caso**, ~25 s por adapter.
Artefato: `calibracao-argumentos-350m-2026-09-19.json` (+ `casos_calibargs_*.jsonl`).

Dois sinais sobre a chamada greedy já gerada (o `bruto` do despejo):
**(A) auto-avaliação** — prompt + chamada como turno do assistente + usuário: *"A chamada acima está
correta e completa para o pedido? Responda apenas Sim ou Não."* → c_sim = P(Sim)/(P(Sim)+P(Não)) no 1º
token (variantes de caixa/espaço somadas; `Nao` → `Na`+`o` excluído); **(B) verossimilhança
teacher-forced** — logP de cada token do bruto dado o prefixo, média e mínimo sobre os tokens de
`"args"` ao fim (e sobre a chamada inteira). Correto = exec_ok (tool) ou False (texto: over-call é
chamada errada por definição). ⚠️ O bruto saiu de decodificação restrita: a logP aqui é a
**irrestrita** — o que o modelo tinha, não o que a máscara escolheu.

| receita (3 sementes) | acc das chamadas (tool) | 1º token após a pergunta | P(Sim)+P(Não) < 1% | c_sim AUROC · média | **logP média args AUROC** (tool / todas) · acc@50 | logP mín. args | logP média chamada inteira |
|---|---:|---|---:|---|---|---:|---:|
| e13 | 0,835 | `{` em **100%** | 100% | 0,468 · 0,02 | **0,755** / 0,767 · 0,948 | 0,744 | 0,761 |
| C-full | 0,834 | `{` em **100%** | 97% | 0,611±0,058 · 0,19 | **0,729** / 0,758 · 0,938 | 0,718 | 0,721 |
| recusa específica | 0,830 | `{` em **100%** | 100% | 0,479 · 0,02 | **0,745** / 0,766 · 0,946 | 0,727 | 0,737 |
| catálogo perturbado | 0,854 | `{` em **100%** | 97% | 0,614±0,026 · 0,19 | **0,742** / 0,760 · 0,953 | 0,720 | 0,726 |

E o fim-a-fim recomposto (804 casos; chamou: p_call·p_tool·c, não chamou: 1−p_call):

| receita | confiança | AUROC | AURC | acc@25 | acc@50 | acc@100 | ECE |
|---|---|---:|---:|---:|---:|---:|---:|
| e13 | G-C1 (c = 1) | 0,735 | 0,117 | 0,945 | 0,891 | 0,769 | 0,142 |
| | × c_sim | 0,637 | 0,145 | 0,922 | 0,812 | 0,769 | 0,545 |
| | **× exp(logP média args)** | **0,757** | **0,097** | **0,985** | 0,892 | 0,769 | **0,118** |
| C-full | G-C1 | 0,696 | 0,145 | 0,904 | 0,853 | 0,740 | 0,178 |
| | × c_sim | 0,602 | 0,186 | 0,866 | 0,773 | 0,740 | 0,448 |
| | **× exp(logP média args)** | **0,715** | **0,131** | **0,940** | 0,855 | 0,740 | **0,157** |
| recusa específica | G-C1 → × logP média args | 0,723 → **0,760** | 0,120 → 0,097 | 0,924 → **0,968** | 0,879 → 0,905 | 0,774 | 0,137 → 0,115 |
| catálogo perturbado | G-C1 → × logP média args | 0,701 → **0,715** | 0,133 → 0,123 | 0,929 → **0,952** | 0,865 → 0,869 | 0,751 | 0,168 → 0,148 |

Leituras:

1. 🔴 **A auto-avaliação não existe neste modelo — e o modo de falha é mais forte que "responde Sim a
   tudo": ele não responde.** Em 12/12 adapters, o primeiro token depois da pergunta é `{` em **100%**
   dos casos: perguntado se a chamada está certa, o modelo *chama de novo*. P(Sim)+P(Não) fica abaixo
   de 1% em 97–100% dos casos; a razão c_sim é acaso no e13 e na recusa específica (AUROC 0,47–0,48)
   e um resíduo no C-full/catálogo (0,61 ± 0,06) que não é probabilidade de nada (média 0,19, ECE
   0,45–0,55; multiplicada na confiança, **piora** o fim-a-fim em 0,06–0,10 de AUROC). É a §2e ao
   contrário: a régua escuta, o modelo é que nunca aprendeu a falar isso — o Noul de auto-avaliação do
   2603.06604 é comportamento **treinado**, não emergente em 350M com SFT agêntico.
2. ⭐ **A verossimilhança dos argumentos separa chamada certa de errada com AUROC 0,73–0,76** — acima
   da previsão (0,60–0,70), consistente nas 4 receitas, e a *média* vence o *mínimo* (0,72–0,74) e a
   chamada inteira. É o sinal mais barato que existe (já está no forward que gera) e nunca tinha sido
   lido neste projeto. Roteando por ele, a metade mais confiante das chamadas acerta **94–95%**
   contra 83–85% do total.
3. **Combinado à confiança do G-C1, sobe o fim-a-fim — mas pouco:** AUROC +0,02 a +0,04, AURC
   −0,01 a −0,02, e o quartil mais confiante passa de 90–95% para **94–98,5%** de acerto (+3 a +4 pp).
   A previsão ("0,64 → 0,70–0,75") acertou o destino e errou a base — a base corrigida (§8) já era
   0,70–0,74. O que isso diz: **a maior parte do erro de argumento é confiante** — sintetizar um
   e-mail plausível (§2w) ou traduzir a chave (§2q) não deixa marca na verossimilhança. Sinal barato
   serve para *rotear* (agir só no quartil bom), não para *consertar*; consertar é treino.

**Previsão pré-registrada × medido:** c_sim AUROC < 0,6 e quase constante → ✅ e13/recusa (0,47–0,48),
≈ C-full/catpert (0,61, mas sem massa: `{` em 100%); logP args AUROC 0,60–0,70 → **0,73–0,76**, melhor;
combinada sobe o fim-a-fim para 0,70–0,75 → ✅ 0,715–0,760, mas a partir de 0,70–0,74 (ganho +0,02–0,04);
"se não subir, o erro é confiante" → subiu pouco: o erro é, em maioria, confiante.

### 10.1 O que fica para o harness (Degrau 1, US$ 0, hoje)

1. **Confiança da decisão de chamar:** ler p_call e passar por temperatura (T ≈ 2 no C-full, 1,8 no
   e13 — um escalar por receita, ajustado uma vez, transfere entre sementes). ECE 0,02–0,04.
2. **Limiar:** o greedy já opera em τ ≈ 0,14; abaixar para 0,15–0,20 compra +2,6 a +4,5 pp de execução
   por +3,5 a +5,6 pp de over-call no C-full — **decisão de custo do produto**, medida, não estimada.
3. **Rotear pelo que se sabe:** p_call · p_tool · exp(logP média dos argumentos). O quartil mais
   confiante acerta 94–98%; o que está abaixo vai para confirmação/humano. O que **não** fazer:
   perguntar ao modelo se acertou.
4. **O que só treino resolve:** os erros de argumento confiantes (a maioria) e a auto-avaliação —
   candidatos ao G-C6 (RLCR com o executor como recompensa), se um dia valer o custo.
