# Estudo — 17 fontes arXiv (lote 2) · multiagente · 2026-07-30

> Segundo lote do dia, lido enquanto o Bee-150M rodava. **Workflow de 7 agentes** (6 leitores em
> paralelo, 2-3 papers cada via WebFetch, + 1 síntese-chefe), com o contexto do Bee **e** os achados
> dos lotes anteriores injetados para evitar re-descoberta. Régua: 🟢 toca pré-treino/tokenizador/
> init/LR/schedule (ainda ajustável) OU método barato aplicável já · 🟡 fase futura · 🔴 exige
> 7B+/RL caro/fora do nicho.

## 1. Leitura de conjunto — retrato honesto

**Acesso:** 16 das 17 lidas integralmente. **1 parcial:** PARED/*Inverse RL* (2607.24900) — PDF com
resultados em streams comprimidos que o WebFetch não decodifica, `/html/` 404; método lido pelo
abstract, mas tamanhos/datasets/win-rates **não recuperados**. Veredito 🔴 apoiado na CATEGORIA (IRL de
alinhamento com discriminador), não em números que não li. EffGen (2602.00887) deu 404 no HTML, lida
via `/abs/`+PDF.

**Faixa de tamanho:** só **3** operam na faixa do Bee (≤500M): SemChunk-C (17–150M, encoder de código),
Robust RL for Small LM Agents (70–500M — o único que crava a faixa em pré/pós-treino) e Guarded Query
Routing (piso 270M–0,8B). VQA endoscopia toca 0,2–1,1B (nossa faixa de hardware, domínio errado). As
outras **12** vivem em 1,5B–1T.

**Quantas mudam algo no Bee:** **zero** mexem no pré-treino rodando agora (passo ~5700) — coerente com
o plano, deixa terminar. Mas — e aqui o lote se separa dos anteriores — **três fontes tocam a faixa
70–500M com dados reais**, e duas entregam achado empírico direto sobre decisões nossas.

**Comparação com os lotes anteriores (majoritariamente negativos, sinal só em higiene de avaliação):
este lote é MELHOR** — não porque muda o pré-treino (não muda), mas porque:
- pela 1ª vez há **medição na nossa faixa** que vira portão de decisão (capacity-headroom, do Robust RL
  70–500M);
- o **roteador determinístico da COMEIA** deixa de ser "reforçado por analogia" e ganha **número contra
  a alternativa** (Gemma 270M rotea a 8,30/100; não-LLM 2–3 ordens de grandeza mais rápido);
- a higiene de avaliação reaparece por **três caminhos independentes** (seesaw, Pass@1 do GRPO,
  decomposição ID/OOD) — mesma música, agora em coro.

Veredito estrutural mantém: a safra 2026 ataca escala grande/pós-treino/serving; **ninguém pré-treina
150M do zero em PT com 1 L4**. O nicho segue solitário. Mas este lote entrega mais sinal utilizável que
os dois anteriores somados.

---

## 2. ⭐ AÇÕES ACIONÁVEIS AGORA (🟢) — ordenadas por retorno/esforço

Nenhuma mexe no run em andamento. Custo ≈ zero (medição ou decisão de projeto), sem reescrever código.

| # | Ação concreta | Fonte | Frente | Por que ganha |
|---|---|---|---|---|
| 1 | **Nunca reportar métrica agregada sozinha.** Toda medição (pré-treino/SFT/COMEIA) quebra por tarefa + testa consistência sob paráfrase; rejeição e acerto medidos SEPARADAMENTE, nunca só um F1/média. | Hetero Merging (seesaw), ReCo (Pass@1↑/cobertura↓), Guarded Routing (ID/OOD) | Avaliação (transversal) | 3 fontes independentes provam que a média esconde regressão. Custo nenhum. |
| 2 | **Decisão travada: o Bee NÃO rotea a si mesmo.** SLM<0,8B como roteador = **8,30/100** medido; mesmo os que "funcionam" ficam 2–6× mais lentos que fastText/WideMLP com desempenho pior. O fast-path determinístico de 80% da COMEIA está certo — anexar este número como defesa. | Guarded Query Routing (270M–9B) | COMEIA/roteador | Evidência empírica direta contra a alternativa. Barra erro futuro caro. |
| 3 | **Portão capacity-headroom: medir a PPL de validação PT do SFT ANTES de cogitar RL/DPO em qualquer degrau.** Se a base não estiver fluente, NÃO gastar GPU com RL — investir em mais SFT. Pythia-70M colapsou (ganho NEGATIVO); 360M/410M funcionou. | Robust RL for Small LM Agents (70–500M) | SFT/escada | Único paper na nossa faixa exata. Evita queimar a L4 numa etapa fadada. Reforça "150M é piso, RL só de ~350M pra cima". |
| 4 | **Treinar o Bee/abelhas para emitir resposta + span de evidência** (não só resposta) + métrica de grounding no eval do RAG do PassaPro. Em modelos pequenos o objetivo auxiliar melhora a PRÓPRIA resposta, não só a rastreabilidade. | VQA Endoscopy (0,2–1,1B) + GI grounding | SFT + RAG PassaPro | Ganho desproporcional em modelos pequenos + rastreabilidade de graça (o PassaPro precisa apontar o artigo/edital de origem de qualquer forma). |
| 5 | **Decisões de portão/roteador como QA binária de 1 token** ("isto é código? sim/não"). Rápido, determinístico de parsear, casa com "portão determinístico + extrator nunca validador". | Shieldstral (3B, reformulação binária) | COMEIA/roteador + SFT | Padrão barato, independe de escala. O único grão do Shieldstral que eu adotaria com confiança. |
| 6 | **Delegar cálculo para fora do LLM (Program-of-Thought):** qualquer abelha que precise de número (juros, prazos, vigência) gera expressão executável e roda fora — não raciocina aritmética em texto. | CreditCardQA (PoT>CoT, +5,7 a +6,2 pts) | SFT/COMEIA + RAG PassaPro | Alinhado a "Bee é extrator, não calculadora". PoT é mais confiável por ser verificável. |

**Nota de honestidade:** as 6 são baratas, mas nenhuma é um botão no pré-treino atual. As de maior ROI
(1, 2, 3) são **disciplina de método e decisão de projeto** — o retorno é evitar erro futuro e medir a
coisa certa. Isso É o achado do lote: **em 150M, engenharia de harness/avaliação rende MAIS que mais
parâmetros** (padrão EffGen: +11,2% a 1,5B vs +2,4% a 32B).

---

## 3. GUARDADO PARA AS PRÓXIMAS FASES (🟡)

### (a) SFT / pós-treino
- **Treinar no que o modelo erra** (dados corretivos erro-dirigidos). *MedThink.* → *Gatilho: quando o
  SFT começar, rodar o Bee num set de avaliação, coletar erros, gerar pares corretivos.* **Hipótese a
  medir** (quanto menor o aluno, mais provável que não absorva).
- **Professor MÉDIO destila melhor que gigante para aluno pequeno** (14B > 72B). *FutureMind* (converge
  com MedThink e com a regra "LLM grande/pequeno demais como professor/validador piora"). → *Gatilho:
  testar professor 14B–32B contra 70B+/Opus antes de gastar no caro.*
- **3 correções de PPO em modelo pequeno** (herdaríamos os bugs via LoRA/TRL): (a) *merge-and-
  reinitialize* do adapter p/ destravar gradiente no PEFT; (b) updates de RL em **float32** (bf16 dá
  overflow na razão de importância); (c) reward whitening + cap ρ̄≤5 + rollback. *Robust RL (70–500M).*
  → *Gatilho: runbook de SFT/COMEIA por preferência.*
- **Objetivo auxiliar multi-tarefa ajuda MAIS os menores** (Florence-2 0,2B ganhou mais que os de 1B);
  **QLoRA rank 8 em GPU pequena validado** (0,2–1,1B num 3090 Ti). *VQA Endoscopy.* → *Gatilho: misturar
  tarefa auxiliar correlacionada ("cite o trecho") no SFT de `chat_ptbr`.*
- **Limpar dados antes de treinar** (recuperar trajetórias, reescrever passos com erro de tool).
  *MindForge.* → *Gatilho: se gerarmos dados sintéticos de código p/ a `coder`.*

### (b) COMEIA / adapters / roteamento
- **LoRA ≈ full SFT re-confirmado** (<1 pt: 87,1% vs 87,8%). *Shieldstral* (converge com VQA). A aposta
  em adapters LoRA sobre backbone único absolvida de novo.
- **Fatores explícitos de complexidade como features do roteador de regra** (comprimento, presença de
  código, verbo de tarefa, necessidade de RAG). *EffGen* (roteamento por complexidade batendo
  LangChain/AutoGen). → *Gatilho: engenharia do roteador — roubar os fatores, NÃO o framework.*
- **Loop verificador-determinístico externo** (gerar→rodar linter/teste→devolver erro→regerar) dá +3–4pp
  sem tocar o modelo; **multi-sampling** (gerar N, selecionar por verificador) espreme modelo pequeno.
  *SLM Code Opt. + CreditCardQA.* → *Gatilho: `coder`/`agentica`, só onde EXISTE verificador barato —
  NÃO generaliza para chat PT ou RAG de concurso.*
- **Destilação de oráculo para tarefa bem-recortada** (17M igualou Qwen-7B em chunking, 400× menor).
  *SemChunk-C.* Valida a tese central da COMEIA — reforça "Bee EXECUTA classificação bem-definida, não
  JULGA".
- **SLERP para mesclar adapters** (0,6·gerado + 0,3·público + 0,1·base: F1 84,4→88,7). *Shieldstral.* →
  *Gatilho: alternativa a testar ao hot-swap — medir antes, pode não transferir p/ adapters tão
  pequenos quanto as abelhas.*
- **Soft-prompt/prefix-tuning por abelha** (~2M params, um tensor por especialista) casa com hot-swap
  sem recompilar. *REPREC.* → *Gatilho: experimento de baixa prioridade — explicitamente não medido em
  <1B e historicamente mais instável que LoRA em modelos pequenos.*

### (c) RAG dos SaaS (PassaPro)
- **Classificação de tokens > geração para tarefas estruturais** (encoder pequeno em CPU ~0,03s/512tok,
  não alucina). *SemChunk-C.* → *Gatilho: SE o "chunk por artigo" saturar.*
- **Planejar retrieval por tipo de pergunta** (vigência ≠ requisito ≠ comparativa). *FutureMind.* →
  *Gatilho: design do retriever — no orquestrador, não carga no Bee.*
- **Conjunto de predição conformal como sinal de deferência** (singleton→responde local; conjunto
  maior→escala pro Gemini). *Conformal Cascade* — aplica-se a múltipla escolha, e o PassaPro É
  concursos. **Ressalva dura:** exige N=16 decodificações/query, caro; só se compensar.
- **Regressão de dificuldade** (medir QUAIS fatores derrubam o acerto — comparação, ramificação
  condicional, 3ª pessoa) em vez de acurácia agregada. *CreditCardQA.* Questões de prova = eval set com
  ground-truth de graça.

### (d) Quantização / serving RTX 5070 8GB
- **InferScale (KV injection GPU-nativa via connector vLLM)** ataca "contexto compartilhado
  re-prefillado a cada request" — o RAG do PassaPro re-injetando os mesmos trechos. 3,6–4,8× de TTFT.
  *InferScale (7–14B).* → *Gatilho: SE TTFT virar gargalo medido.* **Ressalvas duras:** store KV de
  1,8–4,8 GB/conversa (proibitivo em 8GB, medir se escala com d_model 576); acurácia CAI ~3pp (até −16pp
  multi-hop) — **assustador em domínio jurídico**. Não adotar antes do gargalo.
- **Chunked RoPE** (guardar keys pré-RoPE) valida "KV-cache de prefixo estável é a métrica de custo
  certa" (bate com `harness-engineering`). Conhecer, não adotar.
- **Otimização de prompt de tool-call (−57% tokens)** = latência/VRAM no Cesar (Gemma local) e Chimera.
  *EffGen.* Vale para VirtualSector independentemente do Bee.

### (e) Escada 350M → 1B
- **RL/DPO só fica realista de ~350M pra cima** (70M colapsou; 360M/410M funcionou). *Robust RL.*
  Coerente com "150M é piso, crescer largura primeiro". Não planejar alinhamento por preferência abaixo
  de 350M.
- **Operação "union" (encaixar tensor menor no maior preservando função)** é vizinha conceitual de
  warm-start / expansão de largura ao subir de degrau. *Hetero Merging.* ⚠️ **NÃO é o que o paper faz**
  (eles interpolam pesos, não inicializam treino) — fio a puxar quando formos crescer LARGURA.

---

## 4. CONVERGÊNCIAS (≥2 fontes → mesma conclusão)

1. **Métrica agregada engana — sempre decompor.** Hetero Merging (seesaw) + ReCo (Pass@1↑ enquanto
   Pass@k↓) + Guarded Routing (ganho vinha de recuperar ID, não de melhorar rejeição) + CreditCardQA
   (regressão de dificuldade). **Quatro fontes deste lote**, e o **mesmo sinal dos lotes anteriores** —
   a convergência mais forte de todo o estudo até agora.
2. **Roteador determinístico da COMEIA reforçado.** Guarded Routing (SLM<0,8B a 8,30/100) + EffGen
   (roteamento por complexidade bate frameworks com LLM-no-loop) + Conformal Cascade (economiza 43% mas
   ao custo de 16 amostragens/query — veneno pra GPU pequena). Convergem com os lotes anteriores (não
   adotar DSPy/LangGraph/neural). Agora com número.
3. **Minúsculo + tarefa recortada + oráculo = caminho, não ingenuidade.** SemChunk-C (17M = Qwen-7B em
   chunking) + Shieldstral (3B = 20B em safety) + VQA (0,2B ganha mais que 1B). Valida a aposta central
   da COMEIA.
4. **Professor médio > gigante para aluno pequeno.** FutureMind (14B > 72B) + MedThink (correção
   erro-dirigida) convergem com a regra da base.
5. **LoRA/QLoRA rank baixo em GPU pequena validado.** Shieldstral (LoRA ≈ full SFT) + VQA (QLoRA rank 8
   num 3090 Ti p/ 0,2–1,1B).

---

## 5. CONFRONTOS com o que já decidimos (honestidade brutal)

**Não há contradição direta — e isso NÃO é confirmação.**

- **Nenhuma fonte contradiz** geometria/LR/init/tokenizador/escada do Bee. Mas nenhuma **testou** um
  decoder generativo de 150M em PT do zero — a ausência de contradição vem de os papers estarem em
  OUTRO espaço (7B+, pós-treino, código, inglês). **Silêncio ≠ absolvição.**
- **Tensão fraca (não confronto) sobre "small > large":** SemChunk-C mostra 17M = 7B, mas numa tarefa
  ESTRUTURAL estreita (fronteiras de chunk), com encoder discriminativo, em código C. NÃO é evidência
  de que um decoder 150M em PT bata 7B em algo generativo. Se alguém citar isso como "o Bee-150M compete
  com grandes", é leitura errada — provam "tarefa recortada + oráculo = minúsculo basta", que é a aposta
  da COMEIA, bem mais modesta.
- **Um método bate de frente com uma regra nossa (e por isso é descartado):** PARED treina um
  **discriminador que julga** se um texto parece humano — pôr um modelo pequeno no papel de
  validador/juiz, que já concluímos que PIORA com LLM <8B. Não é confronto com uma escolha, é
  confirmação de que "Bee é extrator, nunca validador" descarta corretamente uma categoria inteira.
- **Atenção sobre o portão PPL<20:** o achado mais acionável do lote, MAS o limiar foi medido em inglês
  (TinyStories/Wikitext). Nossa fertilidade PT 1,37 muda a escala — **usar o conceito (base fluente
  antes de RL), não o número 20 cru.**

---

## 6. NÃO APLICÁVEL (🔴)

- **MedThink** (2605.08094) — destilação 72B→7B, médico, n=100. Só "treine no que ele erra" sobrevive (🟡).
- **FutureMind** (2602.01222) — training-free sobre 3B+ com retrieval multi-hop; assume modelo que já raciocina.
- **MindForge** (2607.27146) — agente de código 27B, contexto 512K, 8 épocas Megatron.
- **GI Endoscopy VQA** (2607.27122) — multimodal + médico; máscaras/Grad-CAM não existem no mundo texto-só. Só a lição metodológica (🟡).
- **ReCo/GRPO** (2607.26862) — RL caro (n=1024 rollouts, 2×A6000–B200). Só "Pass@1 engana".
- **Hetero LLM Merging** (2607.18026) — merge irreversível (oposto do hot-swap auditável), ganhos marginais, Qwen 3B–32B. Só o seesaw (🟢).
- **PARED/IRL** (2607.24900) — alinhamento por IRL com discriminador; fora de escala E contra "Bee nunca valida". *Números não lidos.*
- **REPREC** (2607.24845) — recsys, LLM 3B congelado + encoder externo. Só o ponteiro soft-prompt (🟡).
- **CreditCardQA** (2607.26952) — benchmark inglês 20B–1T. Só PoT + regressão de dificuldade (🟢).
- **Conformal Cascade** (2607.25018) — 3,8B–70B, 16 decodificações/query proibitivo. Só uso pontual em múltipla escolha (🟡).

---

## 7. Os aprendizados que levo deste lote

1. **Melhor que os dois anteriores** — não muda o pré-treino, mas pela 1ª vez há medição na faixa
   70–500M que vira portão de decisão (capacity-headroom) e número empírico contra a alternativa ao
   roteador determinístico.
2. **Higiene de avaliação é lei, provada por 4 caminhos independentes neste único lote** (seesaw,
   Pass@1/Pass@k, ID/OOD, regressão de dificuldade). Ação de maior ROI de todo o estudo: nunca reportar
   média agregada sem quebra por tarefa + consistência sob paráfrase.
3. **Roteador determinístico da COMEIA triplamente absolvido** e agora com número. "Fazer o Bee rotear a
   si mesmo" é erro medido — decisão travada.
4. **Em 150M, harness/avaliação rende MAIS que mais parâmetros.** Direciona esforço para o harness da
   COMEIA antes de crescer a escada.
5. **A aposta central da COMEIA (minúsculo + tarefa recortada + oráculo) tem lastro empírico**
   (SemChunk-C 17M = Qwen-7B numa tarefa estrutural). Analogia disciplinada, não transplante — vale
   para EXECUTAR classificação, nunca para VALIDAR/julgar.
6. **Achado negativo honesto:** o nicho do Bee segue solitário na literatura de 2026. As decisões do
   pré-treino são nossas para medir, não copiar. O valor deste lote está nas fases futuras
   (SFT/COMEIA/RAG) e na régua de avaliação.
7. **Nenhuma dependência pesada nova recomendada.** DSPy/GEPA/LangGraph descartados pela 3ª vez;
   GRPO/IRL/merging/multimodal fora de escala. Os 17 papers, somados, dizem ao Bee: **continue
   simples** — roteador por regra, avaliação decomposta, LoRA rank baixo, extrator nunca validador.
