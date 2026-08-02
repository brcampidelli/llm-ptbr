# Estudo — 9 fontes (multiagente, 9 agentes) — 2026-08-01

> Estudo dirigido a **aplicar ao BEE e aos nossos projetos de LLM**, não só a acompanhar a fronteira.
> 9 fontes lidas a fundo por 9 agentes paralelos (WebFetch + cruzamento com fontes primárias),
> cada uma com **checagem de honestidade** (várias são datadas 2026 — filtramos hype/preview) e
> **aplicação concreta**. Consolidado durante o pré-treino do Bee-150M-v2.

## TL;DR — os achados que movem a agulha

1. ⭐ **Otimizador Muon** (DeepSeek V4 + Kimi K3 Per-Head) — vale um **experimento direto no Bee-150M JÁ**. Baixo risco, implementação PyTorch madura e independente, e ataca justamente nosso **LR agressivo (3e-3)** ao reduzir sensibilidade ao schedule. Teste limpo: mesmo dado/tokens, AdamW vs Muon (Muon nas matrizes 2D + AdamW em embeddings/norms), comparar loss e **bpb no holdout PT**.
2. ⭐ **Dados sintéticos PT + filtragem** (Qwen, estilo Cosmopedia) — o item de **maior ROI pra atacar nossa falta de token** (o Gate 2 diagnosticou 535× menos treino que o SmolLM2). Gerar conteúdo didático PT via professor aberto + filtrar por qualidade. É o "andar de baixo" que a maioria das fontes de fronteira ignora, e é o nosso terreno.
3. ⭐ **Sequência de pós-treino: destilação+SFT → ORPO → RLVR** (post-training 2026). O compute vai na **fase 1** (destilação, onde nasce a capacidade); ORPO como estágio único de preferência; **RLVR onde há gabarito/verificação = reward verificável de graça** (ex.: múltipla escolha com gabarito; começar com rejection sampling, subir pra GRPO só se valer). Cada fase = um **adapter da COMEIA**.
4. **QAT/MXFP4** (Kimi K3) — caminho pra rodar o Bee **local barato**. Pra nós: **PTQ primeiro** (treinar bf16, quantizar int8/int4 depois, medir bpb); QAT só no SFT final se o PTQ doer. ⚠️ Conexão crítica: **unlearning falha após quantização** — se quantizarmos, não confiar em unlearning pra remover dado.
5. **Arquitetura do Bee auditada: quase tudo certo.** GQA 9/3 ✅, RMSNorm pré-norm ✅, RoPE theta 10k (pra seq 2048) ✅, tied embeddings **essencial** (12% dos params). Único ponto a vigiar: geometria **30×576 fundo-e-fino** — defensável a 150M (MobileLLM apoia deep-thin sub-1B), mas ao escalar **engrossar d_model mais rápido que a profundidade** (aspect ratio rumo a 40–85).

---

## Tema A — Fronteira de treino 2026 (DeepSeek V4, Kimi K3, Qwen)

### DeepSeek V4 (MoE 1,6T/49B ativos · atenção híbrida · Muon · mHC)
- **CSA + HCA (atenção comprimida):** CSA comprime a sequência ~4:1 + indexer FP4 seleciona top-512 blocos + janela de 128 tokens crus; HCA comprime 128:1 com atenção densa pra coerência global. Ganhos vs GQA: FLOPs 0,10–0,27× e KV-cache ~0,07–0,10×. **Só relevante pra nós se formos pra contexto longo** — exige kernels dedicados pesados; fora do Colab por ora.
- **Muon:** ortogonaliza o update das matrizes 2D (Newton-Schulz) antes de aplicar → melhor condicionamento, menos sensível ao LR. Literatura independente (usado em Kimi/Moonshot). **→ experimento no Bee (item 1 do TL;DR).**
- **mHC (Manifold-Constrained Hyper-Connections):** residual vira mistura por token projetada no politopo de Birkhoff (não-expansiva) pra estabilizar redes MUITO profundas. **Não adotar** — feito pra 60+ camadas trilionárias; nossos 30 layers + init escalado + RMSNorm já resolvem, e sai da regra "LlamaConfig puro".
- **Honestidade:** confiança **alta** que existe (pesos MIT no HF, relatório técnico, API); benchmarks auto-reportados e ratios de FLOPs teóricos → não usar como ranking.

### Kimi K3 (MoE 2,8T/16 ativos · QAT MXFP4 · KDA)
- ⭐ **QAT com MXFP4/MXFP8:** treina consciente da quantização **desde o SFT** — pesos em FP4 (com fator de escala por bloco), ativações FP8; o gradiente "vê" o erro de quantização e os pesos aprendem a compensar de fábrica. Sai em 4 bits sem etapa lossy separada (1,4TB vs 5,6TB FP16).
- **Aplicação:** um Bee pequeno quantizado sem perda = objetivo de serving local. **Faseado:** Bee-150M agora **não** faz QAT (treina bf16, PTQ depois via GGUF/AWQ, mede bpb antes/depois); QAT só no SFT final se PTQ doer; **int8 é a aposta segura**, FP4 só com validação forte (modelo pequeno tem pouca redundância).
- **KDA/AttnRes/Per-Head Muon:** otimizações de fronteira; não adotar antes de um denso sólido.
- **Honestidade:** ⚠️ lançamento recente com muito hype de blog SEO; existência **alta confiança**, benchmarks proprietários **baixa**.

### Evolução Qwen (metodologia replicável)
- **Padrão que se repete:** escalar dados **com curadoria** + **sintetizar onde a web é fraca** (math/código) + treinar em **estágios** (geral → conhecimento → contexto longo) + **MoE** pra escalar sem explodir inferência.
- ⭐ **Dados sintéticos PT** (item 2 do TL;DR) — o análogo do Cosmopedia pro nosso corpus.
- **Multilinguismo valida focar em PT — por contraste:** o Qwen banca 119 idiomas porque tem 36T tokens (dilui a *curse of multilinguality*). Nós não temos essa escala → **concentrar o budget em PT é a jogada certa**.
- **MoE/upcycling denso→MoE** validado como direção pro nosso degrau 1B→4B (precisaremos do global load-balancing pros experts não colapsarem).
- **Contexto longo = último estágio** (depois do pré-treino base), como eles fazem.

---

## Tema B — Agentes (Qwen AgentWorld)

- **Language World Model:** aprende a **prever como o ambiente reage à ação** (7 domínios: terminal, web, SWE, MCP, Android, SO, busca), treinado em >10M trajetórias reais (CPT→SFT→RL). Achado de manchete: **treinar como world model melhorou desempenho agêntico mesmo sem treinar como agente**.
- ⭐ **Aplicação à abelha agêntica (COMEIA):** o insight aproveitável é **trajetória de ambiente real vale mais que tool-use narrado** (carrega a consequência: saída/erro reais). **Copiar a ideia, não a implementação:** montar um **"mini-AgentWorld"** — sandbox de terminal (Docker/subprocess) + um punhado de tools, logando `(estado, ação, observação, sucesso/erro)`. Isso dá trajetórias reais pra SFT + **eval set com ground truth de graça** + reward determinístico pra RL leve.
- **Fora do nosso alcance:** treinar um world model que *substitua* o ambiente (>10M trajetórias, MoE 35–397B). Na nossa escala, **executar o ambiente real é mais barato que simular** — por isso não precisamos do simulador.
- **Honestidade:** existência/pesos **alta**; AgentWorldBench é do próprio autor e margens sobre GPT-5.4/Opus são <1 ponto → cético nos números.

---

## Tema C — Pós-treino & adaptação (post-training 2026, real-time learning, unlearning)

### Sequência de pós-treino do Bee (do mais barato ao mais caro)
1. ⭐ **Destilação + SFT (fase 1, obrigatória):** gerar dados PT de um professor aberto (self-instruct) + **rejection sampling** (best-of-N + filtro) → SFT/QLoRA em ChatML. **Onde vai o compute** — é o gargalo real (falta token). *A fonte llm-stats omite destilação/self-instruct/rejection sampling — justo as técnicas de baixo compute que mais importam pra nós.*
2. ⭐ **ORPO (fase 2):** funde SFT+preferência num objetivo único — **sem reward model, sem reference model, sem pares separados**. Um estágio no lugar de dois. Alternativa: **SimPO** (DPO sem reference model, +6–7 pts vs DPO, economiza memória — crítico no Colab). DPO em queda (viés de comprimento, precisa reference). **KTO** se tivermos feedback binário (thumbs de usuários).
3. ⚠️ **RLVR onde há gabarito/verificação (fase 3, o achado):** ex. múltipla escolha — prompt = questão, reward = 1 se alternativa == gabarito → **reward verificável de graça**. Começar com **rejection sampling sobre o gabarito** (mesma reward, sem loop de RL, barato); subir pra **GRPO leve** (8–16 amostras/prompt, sem critic) só se justificar. ⚠️ RL não cria capacidade que o SFT não plantou — só afia. GRPO pede A100.
- **Encaixe COMEIA:** cada fase = um **adapter LoRA separado** (SFT / ORPO / RLVR) que a COMEIA compõe/roteia → testa RLVR isolado sem tocar a base, reverte barato se degradar.

### Real-time learning (COMEIA validada)
- **Divisor:** conhecimento → **RAG** (não-paramétrico, barato); estilo/domínio → **adapter**; raciocínio → **RL**. Não empurrar tudo pro peso.
- ⭐ **COMEIA = a tese central:** adapters LoRA hot-swap + roteador = "domínio vai em adapter, não em retreino". Regras de ouro a adotar **literalmente**: (a) adapters **separados por domínio** (não misturar → evita catastrophic forgetting); (b) tratar **todo update de adapter como um deploy** (quality gate no holdout PT + canary + **rollback**); (c) pra re-treinar adapter, usar **replay buffer** (misturar amostras do mix anterior) + **eval por fatia** ("3% de ganho na média esconde 30% de regressão em 5% da população").
- **RAG = real-time learning barato:** conhecimento que muda (ex. legislação, docs versionados) **nunca** vira fine-tune → índice (pgvector + tsvector `portuguese` + RRF + reranker) + **avaliador de faithfulness**. Onde houver gabarito/ground-truth, vira eval set de graça.
- **Problema aberto (o ponto duro da COMEIA):** **composição de múltiplos adapters** — nenhuma fonte trata bem merge/empilhamento. É o que teremos de resolver quando empilharmos muitos.

### Machine unlearning (prevenir > remediar)
- **Por que é difícil:** conhecimento distribuído nos pesos, não tem `DELETE WHERE`. Métodos (gradient ascent, NPO, SISA, unlearning via adapters/MAAT) vivem no trade-off **esquecer × preservar**.
- ⭐ **Plano A continua sendo NÃO deixar entrar** (MANIFEST de licença + auditoria de procedência antes do treino). Unlearning é **Plano B e não é confiável**: vaza em membership inference, e **reaparece após quantização** (ICLR 2025) — conexão direta com nosso plano de quantizar.
- **COMEIA localiza o risco:** dado problemático num adapter → descarta/re-treina **só o adapter**, não o backbone. **Desenhar adapters sharded por origem** desde já (exclusão LGPD = descartar o adapter certo). **Nunca** apresentar unlearning como conformidade LGPD garantida.

---

## Tema D — Fundamentos (arquitetura, viés)

### Auditoria arquitetural do Bee-150M
| escolha | veredito |
|---|---|
| GQA 9 Q / 3 KV (head_dim 64) | ✅ sensato (MobileLLM valida cortar KV em modelos pequenos) |
| RMSNorm pré-norm | ✅ estado da arte, nada a revisar |
| RoPE theta 10000 (seq 2048) | ✅ adequado; só subir theta (100k–500k)/YaRN se estender contexto >4k |
| tied embeddings, vocab 32k (~18,4M = 12%) | ✅ **essencial** em modelo pequeno (sem tie: ~25% dos params) |
| geometria 30×576 (fundo-e-fino, aspect ~19) | ⚠️ **defensável** a 150M (MobileLLM apoia deep-thin sub-1B), mas vigiar |
- **Ao escalar 350M→1B:** aumentar **d_model mais rápido que profundidade** (mirar aspect ratio 40–85: ex. 350M ~1024×24; 1B ~2048×24), reavaliar GQA (4–8 KV heads conforme H cresce), subir theta só se estender contexto. RMSNorm/SwiGLU/tying seguem válidos (tying rende menos em 1B+).

### Viés (risco real pra público BR)
- **Origens:** corpus PT carrega estereótipos BR **concentrados** (70% PT não dilui); jurisprudência/domínio público são **datados**; RLHF/SFT injeta valores de quem anota.
- **Riscos de aplicação (genérico):** num uso de conhecimento factual → **erro factual/fonte desatualizada** costuma ser o risco maior, mais que fairness social; em atendimento/geração aberta → não pode discriminar (reputacional/legal).
- **Medir barato em PT** (poucos benchmarks): **testes de contraste** (mesmo prompt trocando nome/gênero/região), templates de estereótipo ocupacional, adaptar StereoSet/CrowS-Pairs à mão; onde houver gabarito, **acurácia por tópico** como métrica objetiva. Tratar como **monitoramento contínuo com amostra pequena**, não score populacional.
- **Mitigar (pré/in/pós):** filtrar/rebaixar fontes tóxicas + **marcar vigência** da jurisprudência (metadado no RAG); **dados de contraste no SFT**; **guardrails** na inferência (classificador de toxicidade na saída; citar fonte e preferir recusar a alucinar).

---

## Plano de ação priorizado

**Agora (Bee-150M, viável no Colab):**
- [ ] **Experimento Muon** vs AdamW no pré-treino do Bee (loss + bpb no holdout PT) — maior ROI/menor risco.
- [ ] **Pipeline de dados sintéticos PT** (Cosmopedia-style via professor aberto + filtro de qualidade) pra atacar a falta de token — reusa `data/teacher_api.py` + `assert_teacher_allowed`.
- [ ] **Pós-treino fase 1** (destilação + SFT/QLoRA em ChatML) quando o v2 fechar.
- [ ] **COMEIA como pipeline de deploy:** quality gate no holdout PT + rollback pra todo adapter; adapters separados por domínio + sharded por origem (LGPD).
- [ ] **RAG** (quando aplicável) com marcação de vigência + faithfulness (também mitiga viés/desatualização).

**Próximo degrau (350M→1B, precisa A100+):**
- [ ] Ajustar **geometria** (aspect ratio 40–85, d_model > profundidade) + reavaliar GQA.
- [ ] **ORPO/SimPO** (fase 2) e **RLVR onde há gabarito** (fase 3: rejection sampling → GRPO).
- [ ] **PTQ** (int8/int4) do Bee e medir bpb; **QAT** só se o PTQ doer.
- [ ] **Mini-AgentWorld** (sandbox local) pra treinar a abelha agêntica com trajetórias reais.

**Futuro / fora de escala (não fingir que dá agora):**
- Upcycling denso→MoE (Bee-1B+, com global load-balancing); atenção comprimida CSA/HCA pra contexto longo; mHC; world model próprio.

**Descartar / não confiar:**
- Unlearning como garantia LGPD (usar prevenção na entrada + adapters removíveis).
- Benchmarks auto-reportados de DeepSeek V4 / Kimi K3 / AgentWorld como ranking.
- Adotar KDA/AttnRes/mHC/CSA-HCA antes de ter um denso sólido e uma necessidade medida.

---
*Fontes: DeepSeek V4 (HF/ResterChed + arXiv 2606.19348) · Kimi K3 (HF/ResterChed + kimi.com) · Qwen AgentWorld (mobiletime + Alibaba Cloud + arXiv 2606.24597) · Evolução Qwen (Data Science Dojo) · Real-time learning (FutureAGI) · Post-training 2026 (llm-stats) · Machine unlearning (DS Academy + ACL 2024/ICLR 2025) · Arquitetura LLM (testRigor + MobileLLM/Kaplan) · Viés (testRigor).*
