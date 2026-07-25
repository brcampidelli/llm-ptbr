# Estudo — 11 papers (2026-07-24), lidos contra a COMEIA

> Critério de leitura: cada paper foi julgado por **o que muda na COMEIA**, não por interesse
> acadêmico. Veredito honesto por paper (adotar / talvez / descartar) e ações ranqueadas ao fim.

## 🔴 O achado que mudou uma decisão HOJE

**arXiv 2606.03557** (gateway de roteamento por SLM) reportou:

| Modelo | val loss | token acc | **acurácia na tarefa** | **saídas inválidas** |
|---|---|---|---|---|
| SmolLM2-360M-FT | **0,0775** | **97,4%** | **49,2%** | **22,6%** |
| Qwen2.5-0.5B-FT | 0,0724 | 97,5% | 83,0% | 3,2% |

Nossa abelha agêntica estava em **loss 0,0755 / token acc 98,2%** — numericamente colada no modelo
que se revelou **ruim na tarefa real**. Isso é confirmação independente de que **loss e entropia não
medem competência**. Foi o que nos levou a: (a) tratar `eval/eval_agentic.py` (acurácia + JSON
inválido + over-calling) como o único gate de release de adapter; (b) investigar e achar o bug de
mascaramento (93,8% da nossa loss caía em prompt repetido — ver commit `4b15145`).

---

## Papers por veredito

### ✅ ADOTAR

**arXiv 2603.06713 — ATLAS: "Scaling Agentic Capabilities, Not Context"** *(o paper âncora)*
Mesmo backbone que o nosso (Qwen3-4B), mesmo problema (tool-use em SLM), mesmas restrições.
- Qwen3-4B: Task Fulfillment **2,73 → 4,15** (+52%); fronteira Kimi K2 (1T params) = 4,38 → **95% da fronteira**.
- **PTC (orquestração programática) sozinho, SEM treino: 2,36 → 2,94 (+25%)**. Emite um programa
  Python que orquestra as ferramentas em vez de N turnos JSON — ataca qualidade *e* latência serial.
- **Juiz pequeno ABERTO bate juiz grande fechado sob rubrica:** Qwen3-30B **3,87** vs GPT-4o 3,43.
  Nossa regra dura de licença sai **de graça** aqui — cumprir não custa qualidade.
- Rubrica de 4 eixos: Task Fulfillment, **Tool Appropriateness**, Tool Grounding, Parameter Accuracy.
  O 2º eixo pune chamar ferramenta quando não devia = **anti-colapso-de-modo na função de perda**.
- Só **304 tarefas** de treino. O gargalo é o **sinal (recompensa densa)**, não o volume.
- Máscara de gradiente em tokens não gerados pelo modelo → foi a pista que nos levou ao nosso bug.

**arXiv 2602.11202 — interwhen: verificação em tempo de teste**
- τ²-bench: **32,17% → 87,70%** (+55,53 pp) **a 96,93% do custo de tokens** — verificar saiu *mais barato*.
- Verificação de **processo** > só-resposta: +10,53 pp (SpatialMap), Maze 88,80% → 97,93%.
- **Extrator de estado pode ser um 3B:** 0,4 pp de diferença vs GPT-5.4 → cabe como adapter leve nosso.
- Verificadores rodam **assíncronos**; só interrompem em violação → caminho correto não paga latência.
- Aplicação direta: verificar em cada tool-call se (i) JSON válido, (ii) ferramenta existe,
  (iii) args conformes, **(iv) o modo (JSON vs texto) corresponde à intenção** ← barreira em runtime
  contra "virar só JSON", sem retreinar.

**arXiv 2504.04915 — Collab-RAG**
- **SFT only = 47,0 EM → 53,0 com DPO iterativo** (+6 pp). SFT sozinho quase não move — **explica
  nosso 7/7 no ruído**.
- **3B fine-tunado > 32B congelado** na tarefa dele. Destilação perde do laço de preferência.
- Hiperparâmetros publicados: **N=5** amostras, **β=0,5** (KL forte = menos deriva = menos colapso),
  **2 rodadas** de DPO (platô na 3ª), lr 2e-6 → 1e-6/5e-7.
- **A regra mais subestimada, copiar já:** descartar prompts em que **todas as N amostras têm a mesma
  recompensa** — remove o que a abelha já acerta sempre (fonte de overfit) e o que erra sempre (ruído).
- Nosso ajuste de licença: o "leitor/ambiente" pode ser a própria `base_forte` → zero professor externo.

**arXiv 2606.03557 — gateway de roteamento** *(o playbook do nosso roteador)*
- Receita transplantável: **1.000 exemplos por rota × 5 rotas**, saída JSON
  `{rota, label, confiança, query_normalizada}`, QLoRA 4-bit, 3 épocas (~1.700 passos).
- Fine-tuning: 0.5B **24,8% → 83,0%** (+58,2 pp). Latência **392 ms**.
- Trade-off explícito: **1.5B só com prompt = 94,6% / 0% inválido, mas 1.777 ms** (4,5× mais lento).
- **A camada de validação é o que salva:** o registry valida o JSON do roteador; saída inválida
  degrada para regras em vez de derrubar o sistema. Não precisa ser perfeito — precisa ser *validável*.

**arXiv 2607.08938 — Better Harnesses, Smaller Models**
- **89,7% da performance do LLM a 4% do custo.** Melhor caso: **5,0% → 99,4%** (com custo caindo).
- O que o otimizador de fato escolheu: **adicionar contexto 86%**, criar ferramentas 43%, filtrar 29%
  — **nada de pesos**. Confirma: harness > SFT no nosso regime.
- **ρ = −0,96 entre diversidade de tarefa e ganho** (89,1% → 68,0% do menos ao mais diverso).
  ⇒ **cada abelha deve ter escopo o MAIS ESTREITO possível.** Se `coder` virar "tudo de código",
  o ganho evapora. Fatiar por tarefa (refactor / geração / testes), não por domínio.
- **Achado negativo útil:** criação de sub-agentes por SLM **falhou** → reforça manter o orquestrador
  em **código determinístico** e não migrar para LLM-planner.

### 🟡 TALVEZ (adotar em partes)

**arXiv 2602.00887 — EffGen** (Apache-2.0, serve de baseline)
- **Escalonamento complementar — e isto corrige uma priorização nossa:** compressão de prompt rende
  **+11,2% em 1,5B** vs **+2,4% em 32B**; roteamento rende **+3,6% em 1,5B** vs **+7,9% em 32B**.
  ⇒ Na nossa faixa (4B), **compressão vale ~3× mais que roteamento**. Eu vinha chamando o roteador de
  "calcanhar de Aquiles" — ele é **fragilidade**, não a maior alavanca.
- Compressão de prompt: **57% em média** (até 70–80%). Nosso system prompt de **928 tokens** é alvo óbvio.
- Tensão real: paralelismo de subtarefas colide com hot-swap serial de adapter → **agrupar subtarefas
  por adapter** para amortizar swaps.

**arXiv 2605.03312 — MemFlow** (adotar a estrutura de controle, não o miolo de memória)
- **+23,4 pp com o modelo CONGELADO**, generalizando por 5 famílias. Terceira confirmação de
  "orquestração > pesos" no nosso regime.
- **Roteador em cascata de 3 camadas:** regras → SLM classificador → fallback por keyword. Nossas
  regras atuais viram a camada 1; o classificador entra como camada 2. Não jogamos nada fora.
- Quanto vale cada peça: bypass do roteador **−8,4 pp**; estratégia da rota **−18,7 pp**.
  ⇒ O que a rota **faz** importa mais que a decisão de rota.
- **Alerta de latência:** o roteador consumiu **58% dos tokens** do pipeline. Medir "% resolvido na
  camada 1 de regras" como métrica de primeira classe.
- Especificação do nosso `base_forte`: escalonamento dispara em **14,9%**, adota em **3,4%**.
  Se `base_forte` estiver sendo acionada muito acima de ~15%, roteador ou abelhas estão descalibrados.
- Orçamento de contexto **por rota** (0 a 8.000 tokens) — ganho de latência sem custo de treino.

**arXiv 2607.20216 — SLMs orquestrados (malware)**
- **Valida o backbone:** Qwen3-4B foi o melhor SLM, batendo todos os 7–8B testados. Pipeline inteiro
  em **~6 GB** → cabe na RTX 5070 8 GB.
- ⚠️ **Latência de encadeamento quantificada: 1,8 s solo → 105,6 s híbrido (~59×).**
  ⇒ Promove a fração de fast-path a **variável dominante de latência**; justifica **teto de
  profundidade de cadeia** no orquestrador.
- **Honestidade:** o SLM orquestrado (35,30%) **não venceu** o LLM grounded (38,22%) — só o LLM
  ungrounded (34,77%). Não usar como prova de "SLM orquestrado > LLM".
- O verifier deles quase não mudou nada (35,30 → 35,04); o ganho veio de **ferramentas/evidência**.
  ⇒ Investir em ferramentas + retrieval antes de verificador ou debate.
- ⚠️ **LIMITE REAL DA NOSSA ARQUITETURA:** os ensembles que funcionam usam **famílias diferentes**
  (Qwen3-4B + Foundation-Sec-8B) para vieses indutivos complementares. Adapters LoRA sobre **um único
  backbone compartilham o mesmo prior** → ganhos tipo debate/consenso entre abelhas devem ser mais
  fracos. **Hipótese a testar, não fato assumido.**

**arXiv 2603.06647 — IBN (LLM vs SLMs)**
- **DMR (Dual-Modular Redundancy) — a ideia mais aproveitável:** rodar a query em **duas abelhas
  plausíveis** quando o roteador estiver com baixa confiança; convergem = aceita, divergem = **escala
  para `base_forte`**. Dá ao roteador um **sinal de incerteza objetivo hoje**, sem treinar nada. E com
  hot-swap sobre um backbone único, o custo marginal é só o swap — quase grátis para nós, caro para
  arquiteturas com N modelos.
- Instrumentar latência **por abelha**: no caso deles o "Senior" consumiu 51% e os "Juniors" 7% —
  otimizar a etapa errada não faz nada.
- ⚠️ **Ignorar os números:** BLEU/METEOR/ROUGE medem sobreposição de n-grama, não correção funcional,
  e a comparação é enviesada (SLM finetunado vs LLM só com prompt).

**arXiv 2603.22866 — Aerial Agentic AI** (validação externa + 1 dica)
- **9 decisões locais por 1 sincronização com a nuvem** = literalmente a nossa fração de fast-path
  usada como resultado publicável. Validação externa da nossa métrica-chave.
- Dica de latência ainda não explorada: empilhar **AWQ + operator fusion + FlashAttention** deu
  **−22% energia e +133% velocidade** vs qualquer um isolado. Hoje só fazemos NF4.
- Evidência fraca (simulação, figuras sem tabelas, zero ablação). Adotar ideias, não números.

### ❌ DESCARTAR (a técnica)

**arXiv 2506.13514 — TensorSLM**
Compressão de embeddings via Tensor-Train: 2× de compressão, **−50% de energia**, mas o gargalo que
ataca (embedding dominando a memória) só existe em modelos **<1B**. Nosso 4B em NF4 usa **2,98 GB de
22 GB** — não temos problema de VRAM. LoRA hot-swap nem toca em embeddings → zero sinergia.
**O que vale é a metodologia:** medir **joules e ms por query** como métricas de primeira classe.
Converteria nossos "80% de fast-path" (adimensional) em "X% menos energia, Y ms de p95" — afirmação
verificável. É workshop paper de escopo sub-bilhão em Raspberry Pi; citá-lo como fundamento da COMEIA
seria esticar.

---

## Ações ranqueadas (impacto ÷ esforço)

| # | Ação | Fonte | Esforço | Estado |
|---|---|---|---|---|
| 0 | **Mascarar a loss no prompt** | ATLAS (pista) + medição própria | horas | ✅ **feito** (`4b15145`) |
| 1 | **Gate de release por acurácia + taxa de inválido + over-calling** (não loss) | 2606.03557 | horas | ✅ **feito** (`eval_agentic.py`) |
| 2 | **Verificador determinístico de tool-call no orquestrador** (JSON válido → ferramenta existe → args → **modo certo**), assíncrono, `max_retries=5` | interwhen | baixo, sem GPU | ⏭️ próximo |
| 3 | **Comprimir o system prompt de 928 tokens** (meta ~57%) | EffGen | baixo | ⏭️ |
| 4 | **Rejection-sampling SFT + 2 rodadas DPO** (N=5, β=0,5, descartar prompts com recompensa uniforme), recompensa **condicional ao modo** | Collab-RAG + ATLAS | médio (reusa `dpo_qlora.py`) | ⏭️ |
| 5 | **Roteador em cascata**: regras (atual) → classificador 0.6B QLoRA (1.000 ex/rota) → fallback, com **validação de schema** | 2606.03557 + MemFlow | médio | ⏭️ |
| 6 | **DMR** como gatilho de escalonamento para `base_forte` | IBN | baixo | ⏭️ |
| 7 | **Teto de profundidade de cadeia** + orçamento de contexto por rota + latência por abelha | 2607.20216 + MemFlow | baixo | ⏭️ |
| 8 | Estreitar escopo das abelhas (fatiar `coder` por tarefa) | 2607.08938 (ρ=−0,96) | decisão de design | ⏭️ |

## Três correções ao meu próprio julgamento anterior
1. **"O roteador é o calcanhar de Aquiles"** — é fragilidade, mas na nossa faixa de tamanho rende
   ~3× menos que compressão de prompt (EffGen) e menos que a estratégia da rota (MemFlow, −8,4 vs −18,7 pp).
2. **"A loss caiu 94% = está aprendendo"** — errado. 93,8% da loss era prompt repetido (medição nossa),
   e 2606.03557 mostra o mesmo regime de loss num modelo ruim na tarefa.
3. **"Somar abelhas dá efeito de ensemble"** — as abelhas compartilham o prior do backbone único;
   os ensembles que funcionam na literatura usam famílias diferentes. Limite real, registrado.
