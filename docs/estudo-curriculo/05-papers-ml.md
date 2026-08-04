# 05 — Papers de ML: o que é aplicável ao Bee agora

**Data:** 2026-08-04
**Escopo:** 3 PDFs locais (`ARTIGOS/`) + 5 links arXiv + varredura da listagem cs.LG recente.
**Contexto do Bee:** 151M params (30 camadas, d_model 576, GQA 9q/3kv, vocab 32k, seq 2048), pré-treino v3 = 9,87B tokens únicos / 1 época → **bpb PT 3,457**. SmolLM2-135M = **2,010**.

> ⚠️ **Aviso de método.** Os 3 PDFs locais e 4 dos 5 links são, em sua maioria esmagadora, **irrelevantes ao Bee** — foram sorteados de um feed genérico de "Machine Learning", não selecionados por tema. Em vez de forçar aplicabilidade inexistente, este documento (a) registra honestamente o que cada um é, (b) usa a listagem cs.LG recente — que era parte da tarefa — para achar o que de fato toca as 3 hipóteses abertas, e (c) puxa a literatura canônica mínima necessária para **decidir** sobre geometria e LR. Tudo que foi lido está marcado; tudo que só foi visto pelo título está marcado como **não lido**.

---

## 1. Inventário

### 1.1 Fontes designadas na tarefa

| Fonte | Título real | Acessível? | Do que trata | Relevância ao Bee |
|---|---|---|---|---|
| `ARTIGOS/2402.04557v1.pdf` | *An Artificial Intelligence (AI) workflow for catalyst design and optimization* (Lai et al., Tsinghua/NUS) | ✅ lido | LLM + otimização bayesiana + active learning para síntese de catalisadores de amônia | **Zero.** Química, não LM. |
| `ARTIGOS/2607.17979v1.pdf` | *Harness Engineering for LLM-Driven GPU Kernel Generation* (Shui et al., Baidu) | ✅ lido | Harness + controller para agentes gerarem kernels CUDA no concurso FlashInfer/MLSys 2026 (B200) | **Marginal** — só no nível de *processo experimental* (§3.7) |
| `ARTIGOS/2608.02455v1.pdf` | *Aggregate-then-Calibrate for Human-Centered Assessment with Theoretical Guarantees* (Xie et al., Rutgers/RUC/FSU) | ✅ lido | Agregar julgamentos humanos ordinais + calibrar scores de modelo por regressão isotônica | **Marginal** — só para montar eval humano do SFT (§3.8) |
| `arxiv.org/pdf/2607.17979` | idem PDF local | ✅ verificado | **Bate.** Mesmo título, mesmos autores (Yue Shui, Chenyu Ma, Hangfei Xu, Shengzhao Wen, Yanpeng Wang) | — |
| `arxiv.org/html/2608.02538v1` | *Interaction Is Not Necessary for Order-Optimal 1-Bit Mean Estimation* (Hu & Zhong) | ✅ acessível | Teoria de estimação distribuída: protocolo não-adaptativo atinge complexidade amostral ótima em 1 bit | **Zero.** Teoria estatística pura. |
| `arxiv.org/html/2608.02528v1` | *Uncertainty Is Not Enough: Value-of-Information Routing for Mixtures of LoRA Experts* (VI-MoLE) | ✅ acessível | Roteamento de LoRA experts por risco certificado (conformal split) em vez de incerteza | **Zero para o Bee hoje** (§3.5) |
| `arxiv.org/html/2608.02456v1` | *Real-time dynamics of the two-step charge-density-wave transition in bulk 1T-TaS₂* | ✅ acessível | Física da matéria condensada com force fields de ML | **Zero.** Não é sobre LM. |
| `arxiv.org/html/2608.02412v1` | *Why Large Language Models Fail at Tabular Prediction* (Garnelo & Czarnecki) | ✅ acessível | Por que LLM perde para baselines clássicos em tabular; causa = dimensionalidade | **Zero para treino** (§3.6) |
| `arxiv.org/search/?query=Machine+Learning` | Busca genérica | ✅ acessível | 40 títulos extraídos | 1 achado forte → §1.2 |

**Nenhum link retornou 404.** Todos os IDs de 2026 resolvem. Os que falharam foram tentativas *minhas* de acessar HTML de papers antigos (`2402.14905v1/v2`) e configs gated — anotadas onde ocorrem.

### 1.2 Achado da varredura da listagem (era o ponto da busca genérica)

Da listagem cs.LG de 2026-08-03/04, **um único título** toca uma hipótese aberta do Bee:

| ID | Título | Lido? | Por que importa |
|---|---|---|---|
| **2608.02064** | **Geometry-Guided Layerwise FFN Width Allocation in Transformers** (Mudarisov, Burtsev, State) | ✅ **lido** | Único paper recente que treina **128M / 256M / 440M do zero** variando alocação de largura por camada. Ataca a hipótese (b). |

Outros títulos da listagem que **apenas vi o título** (não li — registro para não inventar):

| ID | Título | Veredito preliminar |
|---|---|---|
| 2608.02560 | Structured Memory for Edge Language Models: Persistent Context via O(1) SSM State Injection | Inferência/memória, não pré-treino → baixa |
| — (#29) | One QK Channel, Many Sources: Guarding Low-Precision Attention Collapse | **Talvez** relevante se o Bee treina em bf16 e há instabilidade de atenção. Não investigado. |
| — (#40) | DART: Decoded Attention over Recurrent States for Efficient Long-Context | Inferência longa → não agora |
| 2608.02391 | Cooperative Coevolution for Resource-Constrained Agentic LLM Post-Training | Pós-treino agêntico → não agora |
| — (#24) | Start Classifying: Categorical Critics for LLM Reinforcement Learning | RL, fase muito posterior |

### 1.3 Literatura canônica puxada para decidir as hipóteses (fora da lista original, mas necessária)

| ID | Título | Lido? | Hipótese que ataca |
|---|---|---|---|
| **2402.14905** | MobileLLM: Optimizing Sub-billion Parameter Language Models | abstract + config oficial | **(b) geometria** |
| **2503.04715** | Predictable Scale Part I: Step Law | abstract + fórmulas | **(c) LR** |
| **2406.17557** | The FineWeb Datasets: Decanting the Web for the Finest Text Data | abstract + números de ablação | **(a) corpus** |
| 2502.02737 | SmolLM2: When Smol Goes Big — Data-Centric Training | abstract | (a) corpus |
| 2606.14150 | Small LLMs: Pruning vs. Training from Scratch | abstract | rota alternativa |
| 2408.13359 | Power Scheduler: Batch Size and Token Number Agnostic LR Scheduler | abstract | (c) LR |
| — | `config.json` de `HuggingFaceTB/SmolLM2-135M` e `MobileLLM-125M` | ✅ lidos verbatim | **(b) geometria — decisivo** |

---

## 2. Os papers acessíveis, um a um

### 2.1 Harness Engineering for LLM-Driven GPU Kernel Generation (2607.17979) — lido

- **Problema.** Agentes de código geram kernels CUDA plausíveis, mas o gargalo não é o modelo: é o *loop de engenharia em volta* — baselines desatualizados, cobertura incompleta de workloads, promoção ruidosa, perda de proveniência do profiler.
- **Método.** Separação explícita entre **evaluation harness** (compila, checa correção, mede latência alinhada ao oficial, arquiva artefatos) e **optimization controller** (converte evidência de NCU/Torch Profiler em estado de gargalo, escolhe **uma** direção de otimização por rodada, detecta platô, escreve na memória de trajetória). Skills humanas codificam contrato do candidato, referências e regras de promoção. Codex + Claude Code geram candidatos dentro dessas restrições. Promoção só com **varredura completa da distribuição de workloads**, nunca com um speedup isolado; probes rejeitados são arquivados como memória negativa.
- **Resultado principal, com número.** Speedups de latência média sobre os baselines FlashInfer: **1,62× (MoE FP8), 18,05× (DSA top-k), 29,68× (DSA attention), 1,12× (GDN decode), 13,70× (GDN prefill)**. Os artefatos **Agent-Assisted** batem os **Full-Agent** (LoongFlow PES) em todas as definições: os Full-Agent ficam **1,35×–13,25× mais lentos**, e dois deles ficam *abaixo* do baseline FlashInfer (MoE FP8 em **0,27×**, GDN Decode em **0,83×**).
- **Limitação declarada pelos autores.** O paper afirma explicitamente que **não propõe** novo runtime de serving, nova arquitetura de modelo, nem otimizador autônomo; e que os números "**não são scores oficiais finais de leaderboard**", e sim medições retidas de artefatos arquivados. A afirmação transferível declarada é sobre o *harness*, não sobre um modelo resolver kernels sozinho.

### 2.2 Aggregate-then-Calibrate (2608.02455) — lido

- **Problema.** Tarefas de avaliação centradas em humano (qualidade de um paper, carga de trabalho de um entregador) não têm ground truth verificável. Só-humano sofre de escalas heterogêneas; só-modelo aprende de proxies enviesados.
- **Método.** Dois estágios. **Stage-1:** agrega julgamentos *comparativos* (não notas absolutas) num ranking de consenso `σ̂`, com um modelo de agregação de ranking que modela a confiabilidade de cada anotador. **Stage-2:** projeta isotonicamente os scores do modelo preditivo sobre a ordem `σ̂` — ou seja, `ŝ = argmin_{y∈M_σ̂} ‖y − s_p‖²`. Insight central, ancorado em psicofísica (Weber–Fechner): **pessoas são mais confiáveis comparando do que pontuando em valor absoluto**, então extrai-se só a informação ordinal delas e a escala métrica vem do modelo.
- **Resultado principal, com número.** Garantias teóricas em vez de tabela de benchmark: **Teorema 3.6** (agregação heterogênea é estritamente mais eficiente estatisticamente que a homogênea quando as habilidades dos anotadores variam), **Teorema 3.8** (bound de risco da calibração isotônica *mesmo com o ranking de consenso mal especificado*), **Teorema 3.12** (AtC domina assintoticamente a avaliação só-modelo). Empiricamente, `‖ŝ − s‖² < ‖s_p − s‖²`, consistente em datasets semi-sintéticos e reais.
- **Limitação declarada.** O framework assume ruído do modelo independente do ruído dos anotadores (`ε ⊥ δ`) e ruído gaussiano `δ ~ N(0, σ²Iₙ)` no consenso. Sem essa independência, as garantias não se sustentam.

### 2.3 Geometry-Guided Layerwise FFN Width Allocation (2608.02064) — lido ⭐

- **Problema.** A largura escondida da FFN é **constante ao longo da profundidade** por convenção, não por medida. As FFNs são a maior fatia dos parâmetros do Transformer. Dá para alocar essa capacidade a partir de uma medição de forward-pass?
- **Método.** Trata cada FFN como transportando uma nuvem de representações de tokens e quantifica a mudança geométrica induzida por três estatísticas: *correspondence-preserving shift*, *distorção de Gromov-Wasserstein* e *homologia persistente de grau 1* — cada uma sob métrica crua e normalizada por escala. Um surrogate de aproximação por camada dá um otimizador exato de orçamento fixo. Diagnóstico feito em 7 modelos pré-treinados (Llama 3.2 1B/3B, Llama 3.1 8B, Gemma 2 2B/9B, Gemma 3 1B, Mistral 7B v0.3), depois **treino do zero pareado por seed** em 128M/256M (3 seeds) e 440M (5 seeds), OpenWebText, mesmos parâmetros totais, mesmo budget de tokens e mesmo AdamW entre as regras.
- **Resultado principal, com número.** Em **440M, 5 seeds pareadas**:

  | Regra | Val loss | PPL | Δ vs uniforme |
  |---|---|---|---|
  | Uniforme (baseline) | 3,449 ± 0,022 | 31,47 | — |
  | Cosine taper (TLM) | 3,446 ± 0,022 | 31,37 | **−0,003** |
  | Topológica/hiperbólica | 3,430 ± 0,023 | 30,88 | **−0,019** |
  | Gromov/esférica | 3,433 ± 0,028 | 30,97 | **−0,016** |
  | Anti-topológica/crua (controle) | 3,515 ± 0,098 | 33,62 | **+0,066** |

  A melhor alocação geométrica entrega **≈6,3× a redução média do cosine taper**. O controle deliberadamente desalinhado é **pior que uniforme** — o que é a evidência de que o sinal geométrico não é ruído.
- **Limitação declarada (quase verbatim).** "A limitação central é a **ausência de uma varredura direta de largura por camada**." Somam-se: as estatísticas geométricas são estimativas de amostra finita, com variância e custo diferentes; o embedding hiperbólico de raio fixo é só uma transformação não-linear da distância angular e **não testa uma hierarquia radial aprendida**; o schedule é medido num modelo de referência e **transferido** para um modelo-alvo treinado do zero, ou seja, **estabilidade do perfil sob mudança arquitetural é assumida, não demonstrada**; o controle anti-work muda direção *e* geometria ao mesmo tempo, então não isola alinhamento tão limpo quanto um perfil normalizado revertido/permutado isolaria; e **"os intervalos de 3 seeds em escala pequena permanecem largos"** — isto é, em 128M/256M os intervalos de confiança se sobrepõem.

### 2.4 Os quatro sem aplicação (registro honesto)

- **2402.04557 — Catalyst design.** LLM extrai parâmetros de síntese da literatura → otimização bayesiana → loop de active learning para amônia. Nada transferível.
- **2608.02538 — 1-Bit Mean Estimation.** Protocolo não-adaptativo randomizado atinge complexidade amostral ótima: `O_k((σ/ε)² log(1/δ))` para k>2, `O((σ/ε)² log(σ/ε) log(1/δ))` para k=2, `O_k((σ/ε)^{k/(k−1)} log(1/δ))` para 1<k<2 — casando o lower bound minimax adaptativo e respondendo afirmativamente um problema em aberto do COLT 2026. Teoria de estimação distribuída; não toca treino de LM.
- **2608.02456 — 1T-TaS₂.** Barreiras de 108 meV (deformação-formação) vs 207 meV (deslizamento), parede de domínio 79 meV, transições a 200K e 350K, supercélulas de 1404 átomos por 5 ns. É física, com ML só como force field.
- **2608.02412 — Why LLMs Fail at Tabular Prediction.** Claude-opus-4-6 em inferência pura, sem fine-tune, contra 9 baselines clássicos em 31 datasets. Achado: **dimensionalidade é decisiva** — a acurácia do LLM cai com o número de features (**slope −0,009/dim, r = −0,21**) enquanto todos os baselines ficam planos ou melhoram (**+0,000 a +0,012**). Em 2D, um processo gaussiano reproduz o LLM com **91,6% de concordância de grid**; em alta dimensão o melhor baseline concorda só **64,8%**. É um estudo de *comportamento de inferência de um modelo pronto* — não diz nada sobre pré-treinar um 151M.

---

## 3. ⭐ APLICABILIDADE AO BEE

### 3.1 🔴 NÃO SE APLICA — e a triagem é dura

| Achado | Veredito | Por quê |
|---|---|---|
| Workflow de catalisadores (2402.04557) | **NÃO SE APLICA** | Domínio químico. |
| 1-bit mean estimation (2608.02538) | **NÃO SE APLICA** | Teoria de comunicação/estimação distribuída. Nenhum ponto de contato com pré-treino. |
| Dinâmica de CDW em 1T-TaS₂ (2608.02456) | **NÃO SE APLICA** | Matéria condensada. |
| LLM em tabular (2608.02412) | **NÃO SE APLICA** | Mede inferência de um modelo frontier pronto. O Bee não faz tabular e o achado (degradação com dimensionalidade) não tem alavanca de treino. |
| VI-MoLE (2608.02528) | **NÃO SE APLICA** | Assume (i) um modelo base com **múltiplos LoRA experts já treinados**, (ii) um conjunto de calibração para conformal split, (iii) que o custo dominante é *inferência*. O Bee tem 1 modelo, 0 experts, e o gargalo é qualidade de pré-treino, não roteamento. Os deltas são pequenos mesmo no cenário deles (78,1% vs 77,5% de acurácia; 2,85 vs 3,00 experts ativos) — não é o tipo de ganho que fecha 3,457 → 2,010. |
| Speedups de kernel CUDA (2607.17979, os 1,62×–29,68×) | **NÃO SE APLICA** | Kernels feitos para **B200, CUDA 13.2, PyTorch 2.12**, operadores MoE FP8 / DSA sparse attention / Gated Delta Net. O Bee é Llama denso com GQA numa RTX 5070 de 8 GB ou A100 alugada. Zero overlap de operador e de hardware. |
| Alocação geométrica de largura de FFN (2608.02064) — **como intervenção** | **NÃO SE APLICA AGORA** | Ver §3.4. O ganho é de **−0,019 de val loss**. O gap do Bee é de **1,447 bpb**. Duas ordens de grandeza de diferença. |

### 3.2 🟢 APLICÁVEL JÁ — nº 1: parar de tratar geometria como suspeita

**Isto é o achado mais valioso deste estudo e não veio de um paper — veio de dois `config.json`.**

```
Bee               : 30 camadas · d_model 576 · 9q/3kv · vocab 32k · seq 2048
MobileLLM-125M    : 30 camadas · d_model 576 · 9q/3kv · vocab 32000 · max_pos 2048   ← idêntico
SmolLM2-135M      : 30 camadas · d_model 576 · 9q/3kv · vocab 49152 · ffn 1536       ← idêntico na geometria
```

Lidos verbatim de `vonjack/MobileLLM-125M-HF/config.json` (espelho do `facebook/MobileLLM-125M`, que está gated) e `HuggingFaceTB/SmolLM2-135M/config.json`. Ambos: `hidden_size: 576`, `num_hidden_layers: 30`, `num_attention_heads: 9`, `num_key_value_heads: 3`, `intermediate_size: 1536`, `tie_word_embeddings: true`.

**Como usar:** não faça nada. Cancele qualquer plano de redesenhar a geometria. A hipótese (b) está morta — detalhes numéricos em §4.1.

### 3.3 🟢 APLICÁVEL JÁ — nº 2: parar de tratar o LR 3e-3 como suspeito

O **Step Law** (2503.04715, 3.700 modelos treinados do zero, ~1M horas de H800, 100T tokens) dá forma fechada:

```
η*(N, D) = 1,79 · N^(−0,713) · D^(0,307)
B*(D)    = 0,58 · D^(0,571)          [em tokens]
```

Ajustado em **N ∈ {60M, 120M, 210M, 270M, 430M, 540M, 1B}** e **D ∈ {2B, 4B, 8B, 20B, 100B}**. **O Bee (N=151M, D=9,87B) cai dentro da caixa de ajuste** — não é extrapolação.

**Como usar (cálculo já feito):**

| Cenário | N | D | η* previsto |
|---|---|---|---|
| Bee v3, N total | 1,51e8 | 9,87e9 | **3,09e-3** |
| Bee v3, N não-embedding (~132M) | 1,32e8 | 9,87e9 | **3,40e-3** |
| Bee v2 (corpus antigo) | 1,51e8 | 3,74e9 | **2,29e-3** |

**O Bee usou 3e-3.** Está a **3–13% do ótimo previsto**, e os autores reportam que suas estimativas desviam do melhor global por busca exaustiva em apenas **0,094%**, num paisagem que eles descrevem como **convexa com ótimo largo**.

**Ação concreta:** rode `B*(9,87e9) = 0,58 · (9,87e9)^0,571 ≈ 2,95e5 tokens/batch` ≈ **144 sequências de 2048**. Compare com o batch efetivo real do Bee (batch × grad-accum × seq). Se estiver muito longe disso, aí sim há um hiperparâmetro fora do lugar — mas é o **batch**, não o LR. Custo do check: 5 minutos, zero GPU.

### 3.4 🟡 APLICÁVEL DEPOIS — alocação geométrica de largura de FFN (2608.02064)

- **Por que não agora.** Ganho medido: **−0,019 de val loss** em 440M (e em 128M/256M os intervalos de 3 seeds **se sobrepõem** — os próprios autores dizem isso). O gap do Bee é **3,457 − 2,010 = 1,447 bpb**. Gastar um pré-treino inteiro para caçar −0,019 quando falta 1,447 é alocação errada de GPU-hora.
- **Por que guardar.** Quando o Bee estiver na faixa de 2,1–2,2 bpb e o problema for espremer o último décimo, esta é uma intervenção **de custo zero em parâmetros** (mesmo total de params, mesmo budget de tokens) que bate um cosine taper por 6,3×.
- **Pré-condição declarada pelos autores:** o schedule é medido num modelo de referência e **transferido**; a estabilidade do perfil sob mudança arquitetural é *assumida*. Como o Bee compartilha a geometria exata do SmolLM2-135M, medir o perfil normalizado de work no **SmolLM2-135M** e transferir para o Bee é o cenário mais favorável possível para essa suposição. Guardar como experimento de fase 3.

### 3.5 🟡 APLICÁVEL DEPOIS — VI-MoLE (2608.02528), com ressalva

Só faz sentido num Bee futuro que tenha **vários LoRA adaptadores de domínio** (ex.: PT jurídico, PT concursos, PT conversacional) e onde compute de inferência importe. Não é o caso. Registrado por completude, não por promessa.

### 3.6 🟢 APLICÁVEL JÁ — nº 3: disciplina de harness (2607.17979), no nível de processo

Este é o único uso legítimo do paper de kernels, e é real. O padrão que ele valida:

1. **Gate pareado barato antes de sweep caro.** Eles nunca promovem por um speedup isolado — primeiro um gate representativo contra o baseline *da mesma rodada*, só depois a varredura completa.
2. **Uma hipótese por rodada.** O controller seleciona **uma** direção de otimização por vez.
3. **Memória negativa arquivada.** Probes rejeitados são guardados para não re-explorar rotas mortas.
4. **Supervisor de platô.** Detecta estagnação, ciclos, regressão e retornos decrescentes, e carrega direções bloqueadas para a rodada seguinte.

**Por que isso é aplicável ao Bee agora:** o ciclo v2→v3 gastou um pré-treino completo (2,6× mais corpus, 9,87B tokens) para mover **~0,1%** de bpb. Isso é exatamente o modo de falha que o harness previne: **compromisso de budget total antes de um gate barato**. Com um gate pareado — dois runs de ~300M–500M tokens, mesma seed, só variando o corpus — a resposta "corpus maior não move a agulha" teria custado ~5% do GPU-hora. **Instituir esse gate é a mudança de processo de maior retorno do Bee**, e é gratuita.

### 3.7 🟡 APLICÁVEL DEPOIS — AtC (2608.02455) para o eval do SFT

O SFT do Bee (eval_loss 6,58 → 3,58, "aprendeu forma, conteúdo fraco") precisa de um eval de conteúdo, e loss não mede isso. O insight utilizável do AtC: **coletar julgamentos comparativos (A vs B), não notas absolutas** — porque anotadores (humanos ou LLM-juízes) são confiáveis em ordenar e não em pontuar. Depois agregar em ranking de consenso e calibrar isotonicamente qualquer score de modelo sobre essa ordem. Custa pouco e o Teorema 3.8 garante bound de risco **mesmo se o ranking de consenso estiver mal especificado**. Marcado como DEPOIS porque o gargalo do Bee é pré-treino, não medição de SFT.

---

## 4. Cruzamento com as 3 hipóteses abertas

### 4.1 Hipótese (b) — GEOMETRIA: **REFUTADA**

A hipótese afirma que a razão d_model/camadas do Bee é **19,2 (576/30)** contra **85–130 dos modelos reais**. Os números 85–130 estão certos — para modelos de **1B a 70B**. Estão **errados como referência para 151M**.

**Evidência 1 — os dois SOTA da classe usam a geometria exata do Bee.**
`MobileLLM-125M` (Meta) e `SmolLM2-135M` (HuggingFace), desenvolvidos independentemente, convergiram para `30 × 576`, 9 heads de query, 3 de KV, FFN 1536, embeddings amarrados. A razão deles é **19,2 — o mesmo número**. O modelo que faz **bpb 2,010**, contra o qual o Bee está sendo medido, é geometricamente **indistinguível do Bee**.

**Evidência 2 — o paper do MobileLLM existe precisamente para argumentar o contrário da hipótese.**
Abstract verbatim: *"Contrary to prevailing belief emphasizing the pivotal role of data and parameter quantity in determining model quality, our investigation underscores the significance of model architecture for sub-billion scale LLMs. Leveraging **deep and thin** architectures, coupled with embedding sharing and grouped-query attention..."* — e o resultado é **+2,7% / +4,3%** de acurácia sobre o SOTA anterior de 125M/350M. A conclusão do trabalho é que, abaixo de 1B, **fundo e fino ganha de raso e largo com parâmetros casados** — modelos de 30 ou 42 camadas superam os de 12 camadas em ~125M. O Bee já está no lado certo dessa fronteira.

**Evidência 3 — o único paper recente que mexe em geometria mede um efeito 76× menor que o gap.**
2608.02064: melhor alocação geométrica = **−0,019** de val loss. Gap do Bee = **1,447 bpb**. Geometria não é onde mora 1,447.

> **Conclusão:** a geometria do Bee não é apenas aceitável — é a escolha canônica da classe, validada por dois laboratórios independentes. **Nenhum GPU-hora deve ir para redesenho de geometria.** A referência "85–130" foi importada de uma faixa de escala errada.

### 4.2 Hipótese (c) — LR 3e-3: **REFUTADA**

`η*(1,51e8, 9,87e9) = 1,79 · (1,51e8)^(−0,713) · (9,87e9)^(0,307) = 3,09e-3`.

O Bee usou **3e-3**. Erro de **~3%** contra uma lei ajustada em 3.700 modelos, com o Bee **dentro** da faixa de ajuste (60M–1B params, 2B–100B tokens), num regime que os autores caracterizam como **convexo de ótimo largo** e cujas estimativas ficam a **0,094%** do ótimo por busca exaustiva.

A referência que sugeria "3× alto" (o ref Burkov) é uma regra de bolso genérica, não uma lei ajustada por escala. Onde os dois discordam, o Step Law tem 3.700 modelos e o outro tem uma heurística.

**Ressalva honesta:** o Step Law prescreve o **pico** do LR. Ele não valida o **schedule** (warmup, forma do decay, LR final). O *Power Scheduler* (2408.13359) ataca exatamente essa lacuna — LR agnóstico a batch size e número de tokens, ajustado com modelos proxy pequenos. **O que ainda vale checar:** o LR final do Bee decaiu de fato? Um cosine que não completa o decay, ou um decay para um piso alto demais, deixa loss na mesa e **não seria capturado** pela verificação do pico. Isso é um check de 5 minutos no log de treino.

> **Conclusão:** o pico do LR está certo. Verifique o **schedule** e o **batch size** (§3.3), não o pico.

### 4.3 Hipótese (a) — QUALIDADE/COMPOSIÇÃO DO CORPUS: **É A QUE SOBRA, E A EVIDÊNCIA A SUSTENTA**

Com (b) e (c) refutadas, (a) fica de pé sozinha — e não por eliminação apenas.

**Evidência quantitativa — FineWeb / FineWeb-Edu (2406.17557).** Modelos de ablação de 1,71B, arquitetura Llama, seq 2048:
- **MMLU: 33% → 37%** (≈**+12% relativo**) com apenas **38B tokens** — igualando o desempenho *final* de um dataset concorrente com **~10× menos tokens**.
- **ARC: 46% → 57%** (≈**+24% relativo**).
- O classificador educacional (treinado em anotações sintéticas do Llama-3-70B, **F1 82%**, threshold 3/5) reduz **15T → 1,3T tokens**: **descarta ~91% do corpus** e o resultado melhora dramaticamente.

Ou seja: **jogar fora 91% dos tokens melhorou o modelo.** Isso é a contraprova direta e literal do axioma "mais token resolve" — e é congruente com o que o Bee mediu por conta própria.

**Evidência corroborante — SmolLM2 (2502.02737).** O subtítulo é *"Data-Centric Training of a Small Language Model"*. A receita é multi-estágio, misturando web com math/code/instrução, com **ablações em escala pequena** guiando as taxas de mistura a cada estágio, e datasets novos (FineMath, Stack-Edu, SmolTalk) criados justamente onde os existentes eram pequenos ou de baixa qualidade demais. A família que produziu o baseline de 2,010 do Bee é explicitamente um projeto **de dados**, não de arquitetura.

**Diagnóstico próprio, e é o número mais importante deste documento.**
Sob a forma padrão `L(D) = E + A·D^(−α)` com α ≈ 0,28 (expoente de dados do Chinchilla), passar de 3,74B → 9,87B (fator **2,64×**) deveria ter cortado a parcela redutível da loss em:

```
1 − 2,64^(−0,28) = 1 − e^(−0,272) = 23,8%
```

**O Bee observou ~0,1%.** Isso é ~200× abaixo do esperado. A leitura correta **não é** "mais token não ajuda" — é:

> **O Bee não está na curva de scaling de dados. Ele está saturado por outra coisa antes de a quantidade de tokens passar a importar.**

Com geometria e LR-pico descartados, os candidatos para esse "outra coisa", em ordem de probabilidade:
1. **Tokens nominais ≫ tokens efetivos** — duplicação/near-duplicação e boilerplate. No FineWeb, deduplicação foi um dos maiores levers isolados. "9,87B únicos" precisa ser auditado: único em qual granularidade — documento? parágrafo? MinHash?
2. **Distribuição do corpus** — se for dominado por um registro (ex.: notícia ou legislativo), o modelo satura naquele registro e o eval mede outro.
3. **Mismatch treino↔eval** — se o held-out de bpb vem de uma distribuição fora do corpus, boa parte de 3,457 é *domain shift irredutível*, não capacidade. **Isto é falsificável em 20 minutos** e deveria ser feito antes de qualquer outra coisa.
4. **Schedule de LR / batch** — §4.2.

**Contexto que a hipótese "mais token não resolve" precisa incorporar:** o Bee moveu 2,6×. A distância até o baseline é **~200×** (9,87B → ~2T). Chinchilla-ótimo para 151M é ~3B tokens (20 tok/param); o Bee está em **65 tok/param**; o SmolLM2-135M está em **~14.800 tok/param**, ou seja, **~740× de overtraining deliberado**. É *assim* que ele chega a 2,010. A conclusão defensável do experimento v2→v3 é **"2,6× não move"**, não **"escala de dados não move"** — mas o fato de 2,6× ter rendido 200× menos que o previsto diz que **há um bug ou um teto de qualidade antes**, e é isso que deve ser caçado antes de comprar 200× de tokens.

---

## 5. Veredito — o que fazer, em ordem de retorno esperado

| # | Ação | Custo | Retorno esperado | Base |
|---|---|---|---|---|
| **1** | **Auditar o eval de bpb antes de tudo.** O held-out vem da mesma distribuição do corpus de treino? A conversão token-loss → bpb usa o bytes/token real do tokenizer de 32k nesse texto? Rodar o SmolLM2-135M no **mesmo** script de eval e conferir se reproduz 2,010. | ~1h, 0 GPU-hora de treino | **Altíssimo.** Se o pipeline de eval estiver enviesado, todo o resto é perseguir fantasma. Assimetria máxima. | §4.3 item 3 |
| **2** | **Medir tokens efetivos vs nominais.** MinHash/near-dup em nível de documento e parágrafo sobre os 9,87B. Reportar taxa de duplicação e distribuição por fonte/registro. | ~1 dia CPU | **Alto.** Explica diretamente por que 2,64× rendeu 0,1% em vez de 23,8%. | FineWeb 2406.17557; §4.3 |
| **3** | **Instituir o gate pareado barato** antes de qualquer pré-treino completo: 2 runs de 300–500M tokens, mesma seed, variando **uma** coisa. Arquivar resultados negativos. | ~5% do GPU-hora de um run | **Alto.** Teria matado o experimento v3 por ~R$ 50 em vez de um pré-treino inteiro. Muda a economia de todos os experimentos futuros. | 2607.17979 §3.6 |
| **4** | **Replicar a receita FineWeb-Edu em PT.** Anotar ~500k amostras com um teacher (build.nvidia.com já está no fluxo do projeto), treinar um classificador de qualidade educacional, ficar com o topo, e **retreinar com corpus menor e melhor**. | 1 pré-treino | **Alto.** É o único achado da literatura com magnitude compatível com o gap: +12% rel MMLU / +24% rel ARC, e igualou um baseline com **10× menos tokens**, descartando 91% do corpus. | 2406.17557 |
| **5** | **Checar schedule de LR e batch size.** Confirmar decay completo; comparar batch efetivo com `B* ≈ 2,95e5 tokens` (~144 seqs de 2048). **Não mexer no pico de 3e-3.** | 5 min | **Médio.** Barato demais para não fazer. | Step Law 2503.04715; §3.3 |
| **6** | **Escalar tokens — mas só depois de 1–4.** O gap real é ~200×, não 2,6×. Escalar um corpus sujo multiplica o problema em vez de resolvê-lo. | Alto | **Médio, condicional.** | §4.3 |
| **7** | **Considerar a rota de pruning/destilação como plano B.** 2606.14150: com budget de tokens limitado e um pai pré-treinado em mãos, **init por pruning bate consistentemente init aleatório**; a vantagem estreita conforme o budget cresce e quase some na razão de pruning mais alta. Para o Bee (budget limitado, 151M), a condição favorável está satisfeita. **Bloqueador:** licença do pai e vocab próprio de 32k. | Médio | **Médio, condicional.** | 2606.14150 |
| **8** | **NÃO FAZER: redesenhar geometria.** | — | **Negativo.** | §4.1 |
| **9** | **NÃO FAZER: mexer no LR pico.** | — | **Negativo.** | §4.2 |
| **10** | Arquivar para fase 3: alocação geométrica de largura de FFN (medir o perfil no SmolLM2-135M, que tem geometria idêntica, e transferir); AtC para eval comparativo do SFT. | — | Baixo agora | §3.4, §3.7 |

### Síntese em três frases

As duas hipóteses arquiteturais do Bee estão mortas por evidência numérica direta: **a geometria 30×576 é literalmente a mesma do MobileLLM-125M e do SmolLM2-135M** (a razão 85–130 veio de modelos 10–100× maiores), e **o LR 3e-3 está a 3% do que o Step Law prescreve** para N=151M, D=9,87B — dentro da faixa em que a lei foi ajustada. Resta o corpus, e o sinal mais forte não é a eliminação e sim um número: passar de 3,74B para 9,87B tokens deveria ter cortado ~23,8% da loss redutível e cortou ~0,1%, o que significa que **o Bee não está limitado por dados — está saturado antes disso**. Antes de comprar os ~200× de tokens que separam o Bee do baseline, gaste um dia auditando o eval e a duplicação real do corpus, e institua o gate pareado barato — porque o experimento que custou um pré-treino inteiro para descobrir "não mudou nada" era um experimento de R$ 50.

---

## 6. Registro de acesso (para auditoria)

**Acessados e lidos:** `2402.04557v1.pdf`, `2607.17979v1.pdf`, `2608.02455v1.pdf` (via `pdftotext`); `arxiv.org/abs/2607.17979`, `html/2608.02538v1`, `html/2608.02528v1`, `html/2608.02456v1`, `html/2608.02412v1`, `arxiv.org/search/?query=Machine+Learning`, `arxiv.org/list/cs.LG/recent`, `html/2608.02064v1`, `abs/2503.04715`, `html/2503.04715v7`, `abs/2402.14905`, `abs/2606.14150`, `html/2406.17557v2`, `abs/2608.02528`, `abs/2608.02412`, `export.arxiv.org/api` (várias queries).
**Configs lidos verbatim:** `HuggingFaceTB/SmolLM2-135M/config.json`, `vonjack/MobileLLM-125M-HF/config.json`.

**NÃO acessados (falhas registradas, nada inventado a partir deles):**
- `arxiv.org/html/2402.14905v1` e `v2` → **HTTP 404**. O MobileLLM não tem versão HTML no arXiv; as tabelas de ablação de profundidade×largura **não foram lidas na fonte primária**. As afirmações de §4.1 sobre o MobileLLM se apoiam em (i) o abstract verbatim do `abs/`, e (ii) o `config.json` oficial — ambos verificados. A frase "30 ou 42 camadas superam 12 camadas em ~125M" vem de **busca web secundária**, não do PDF, e está marcada como tal.
- `huggingface.co/facebook/MobileLLM-125M/config.json` e `-350M` → **HTTP 401** (repo gated). Usado o espelho `vonjack/MobileLLM-125M-HF`, que declara `hidden_size 576 / 30 layers / 9 heads / 3 kv / vocab 32000`. Config do 350M **não obtido**.
- `semanticscholar.org/arxiv/2402.14905` → **HTTP 404**.
- Fórmulas do Step Law: extraídas do HTML `v7`; os **coeficientes 1,79 / −0,713 / 0,307 / 0,58 / 0,571 não foram conferidos contra o PDF**. Antes de tomar decisão irreversível de hiperparâmetro, conferir na fonte. Os cálculos de η* deste documento são meus, a partir dessa fórmula.
- Papers 2608.02560, 2608.02391 e os itens #24/#29/#40 da listagem: **apenas títulos**, não lidos.
