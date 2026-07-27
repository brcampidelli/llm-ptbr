# Estudo de artigos — 2026-07-24

Leitura de ~24 fontes (LoRA, otimizadores, destilação, Gemma 4, Qwen 3.5, 15 arxiv) durante o
treino de 5h no Colab. Organizado por **o que muda no nosso projeto**, com juízo crítico — não
repasse cego dos resumos.

## TL;DR — ações ranqueadas por impacto

| # | Ação | Origem | Custo |
|---|---|---|---|
| 1 | **Destilar a cadeia de raciocínio (CoT) do professor**, não só a resposta final | Google Distillation | baixo (mudar prompt do teacher) |
| 2 | **Gerar k candidatos por prompt e filtrar por qualidade** na destilação | Google Distillation | baixo |
| 3 | **Gate de QA pós-quantização em PT-BR** (viés em geração aberta) | QuantiBias `2607.21063` | médio |
| 4 | **Não quantizar o caminho recorrente** (conv1d/SSM) do Gated DeltaNet | Qwen3.5 config | verificar (provável já OK) |
| 5 | **Holdout com ground-truth** para escolher o melhor checkpoint | Google open-tuning | baixo |
| 6 | **Steering de consistência factual cross-lingual** como complemento barato ao DPO | `2607.19243` | médio (pós-DPO) |
| 7 | **Revisitar licença do Gemma 4** (fontes dizem Apache 2.0 agora) | Gemma 4 model card | 5 min |
| 8 | Testar **Unsloth** para QLoRA do Qwen3.5 (2x, −70% VRAM) | comunidade | médio |

---

## 1. Qwen3.5-4B — arquitetura (nossa base) + CORREÇÃO importante

**Specs confirmadas** (config.json + o que observamos rodando): denso multimodal, **32 camadas
híbridas = 24 Gated DeltaNet (atenção linear) + 8 atenção plena** (padrão 3:1), hidden 2560,
GQA 16Q/4KV, **vocab 248.320 (201 idiomas, PT-BR nativo)**, contexto 256K, `partial_rotary 0.25`,
`tie_word_embeddings`, head MTP para speculative decoding, `mamba_ssm_dtype=float32`. Apache-2.0.
Não há quant oficial do 4B — fazemos o nosso.

**⚠️ CORREÇÃO (juízo crítico):** o agente afirmou que `AutoModelForCausalLM` "não funciona" no
Qwen3.5 (só `Qwen3_5ForConditionalGeneration`). **Isso está errado para o nosso caso** — e temos
prova empírica: nosso `comeia/train/sft_qlora.py` usa `AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-4B")`
e **está treinando agora mesmo na L4**. No transformers 5.x, o auto-mapping resolve
`qwen3_5 → Qwen3_5ForCausalLM` (o backbone de texto). Ou seja: carregar como CausalLM **já pega só
a parte de texto** e ignora a torre de visão — a recomendação "congele a visão" é atendida
automaticamente. Lição: evidência do run > reconstrução do agente a partir de fontes secundárias.

**O que É verdadeiro e importa para o nosso LoRA:**
- As **24 camadas Gated DeltaNet não têm `q/k/v_proj` padrão** — têm in-proj + `conv1d` (kernel 4) +
  gates delta-rule. Nossa config LoRA (`q,k,v,o,gate,up,down`) então adapta: **MLP (gate/up/down) nas
  32 camadas** + **atenção (q/k/v/o) só nas 8 camadas plenas**. O peft simplesmente ignora os nomes
  ausentes nas camadas DeltaNet (sem erro). **Isso é aceitável para a v1** — cobre bem o modelo.
  Melhoria futura possível: adicionar as in-proj do DeltaNet aos alvos, mas é arriscado; deixar como está.
- **Não quantizar o caminho recorrente:** o estado SSM roda em fp32 e é mais sensível que atenção.
  Boa notícia: o bitsandbytes 4-bit só quantiza camadas **Linear** — o `conv1d` e norms ficam em
  bf16 automaticamente. Então nosso QLoRA provavelmente já respeita isso. **Verificar** que o treino
  não desestabiliza (loss saudável — até agora, sim).
- **Não estender vocab, não mexer no RoPE** — já não mexemos. Correto.

**Confirmação externa:** a plataforma de tuning do Google **lista Qwen 3.5 como suportado para LoRA**
— nossa escolha de base + método está no caminho de primeira classe.

---

## 2. LoRA + otimizador — o que manter (e o que NÃO seguir cego)

- **`r=16` é seguro** (o paper original mostra r=8 competitivo até em 175B). Fixar `lora_alpha`
  acoplado ao r (16 ou 32) — nossa config usa alpha=32. OK.
- **⚠️ Não seguir o "só q/v" do paper de 2021.** O LoRA original (Hu et al.) recomenda concentrar em
  `q_proj`/`v_proj`. Mas o **QLoRA moderno (Dettmers 2023, defaults Unsloth/Axolotl) mostrou que mirar
  TODOS os linear layers dá melhor qualidade** — e nossa config já faz isso. Mantemos all-linear.
- **`paged_adamw_8bit` é a escolha certa** para L4 — o "paged" migra estados do otimizador para a RAM
  em picos, evitando OOM. Manter. Se houver spikes de loss no **DPO**, ligar `percentile_clipping=5`.
- Como o base está congelado em 4-bit, a memória do otimizador só cobre os params LoRA (pequenos) —
  o ganho do 8-bit é modesto, mas o paged vale como rede de segurança.

---

## 3. Destilação — upgrades (o achado de maior ROI)

O SOTA do Google (serviço de destilação) faz além do que fazemos hoje:
1. **Captura o reasoning trace (CoT) do professor**, não só a resposta final. Nossa destilação pega
   só a resposta. **Incluir o raciocínio do professor nos alvos** é o principal diferencial em tarefas
   de raciocínio. Mudança barata: ajustar o system prompt do teacher para expor o CoT.
2. **k candidatos por prompt (4-5) + filtro por qualidade** → alvos melhores. Aplicável direto ao
   nosso `01_distill_teacher.py` (amostrar k, ranquear).
3. **Destilação prompt-only** (professor gera os alvos, sem ground-truth) — é exatamente o nosso caso.
   Confirma que não precisamos rotular manualmente.
4. **Números de referência:** ≥1.000 exemplos (temos 5.657 ✅), seq ≤ 8192 tokens (usamos 2048 ✅),
   **poucas épocas (1-4)** — não 20; escolher o melhor checkpoint por validação.
5. **`2607.20456` (Learn2Zinc):** **error bootstrapping** — coletar as próprias falhas do 4B e gerar
   pares erro→correção com um professor forte, misturando com a geração direta ("Augmented recipe").
   Casa com nossa destilação. E a lição de **separar métrica de forma (formato) de conteúdo (raciocínio)**
   na avaliação — evita superestimar o modelo.

---

## 4. Quantização & deploy

- **`2607.21063` QuantiBias:** modelos quantizados mantêm métricas curtas de segurança mas **aumentam
  viés/estereótipo em geração aberta** (multilíngue). Vira um **gate de QA pós-quantização**: comparar
  fp16 vs GGUF Q4/Q5 em **geração aberta PT-BR**, medindo por *bits efetivos* (não pelo nome do quant),
  e reprovar regressão. Pega o que os evals de múltipla escolha escondem.
- **Régua de edge (Gemma 4 E2B, referência competitiva):** um 2B em INT4 roda em **<1,5 GB, ~7,6 tok/s
  decode num Raspberry Pi 5**. Baliza concreta para medir o custo de deploy do nosso Qwen3.5-4B quant.
- **Gate de qualidade >5%:** ao quantizar (GGUF/bnb-4bit), reprovar se cair >5% vs fp16 — crítico
  porque o estado recorrente do Gated DeltaNet é mais sensível à quantização.

---

## 5. Alinhamento / pós-treino barato

- **`2607.19243` (Cross-Lingual Factual Consistency):** *steering* em tempo de inferência (modula
  ativações) para reduzir alucinação em língua não-inglesa **sem re-treino**. Ataca exatamente nosso
  eixo (PT-BR + factualidade) e é um **complemento barato ao DPO**, plugável no deploy. Ler o PDF
  completo antes de implementar.
- **`2607.19326` (MaLoRA/MaRA):** variante de LoRA com gate por token + seleção de evidência (RAG).
  Tecnicamente sólido, mas adiciona dependência de Mamba/complexidade. Só se priorizarmos reasoning
  multi-hop. Guardar como referência.
- **`2607.20301` (Temporal Portability):** se o Qwen lançar update do 4B, dá para **reaplicar nossos
  adapters SFT/DPO sobre o novo base sem re-treinar** (quase-ortogonalidade em alta dim). Guardar.

---

## 6. Gemma 4 — revisitar licença + truques portáveis

- **⚠️ Correção pendente:** 3 fontes (model card oficial, guia visual, Datature) dizem **Apache 2.0**
  para o Gemma 4. Meu argumento anterior ("Gemma não é Apache") pode estar desatualizado (valia p/
  Gemma 1/2/3). **Verificar na fonte primária.** Mesmo assim, **Qwen3.5 continua melhor para nós**:
  vocab 248K vs 262K do Gemma → menos parâmetros gastos em embeddings num 4B, e sem overhead
  multimodal que não usamos.
- **Truques portáveis do Gemma 4** (independentes da base, para otimização de inferência futura):
  compressão de KV cache (K=V nas camadas globais, GQA 8:1), `p-RoPE`, PLE (Per-Layer Embeddings),
  shared KV cache.

---

## 7. Veredito dos 15 arxiv (acionáveis vs descartados)

**Acionáveis para nós:** `2607.19243` (factual cross-lingual) · `2607.21063` (QuantiBias) ·
`2607.20456` (Learn2Zinc SFT) · `2607.20301` (temporal portability) · `2607.19326` (MaLoRA, situacional).

**Descartados (fora do escopo — MoE que não usamos, robótica, interpretabilidade pura, AutoML tabular):**
`2607.16255`, `2607.15674`, `2607.18691`, `2607.20596`, `2607.20427`, `2607.16721`, `2607.20058`,
`2607.20478`, `2607.20933`, `2607.21495`.

---

## Mudanças concretas propostas nos nossos arquivos (para depois do SFT atual)

1. `comeia/data/01_distill_teacher.py`: system prompt do teacher pedindo **CoT explícito**; opção `--k-candidates`
   para amostrar k respostas e ranquear.
2. `comeia/data/`: adicionar um **holdout com ground-truth** (~200-300 pares de referência PT-BR, curados)
   separado do holdout destilado, para seleção de checkpoint.
3. `comeia/eval/`: adicionar um **gate QuantiBias-style** (geração aberta PT-BR, fp16 vs GGUF) antes de publicar.
4. `comeia/train/dpo_qlora.py` (a criar): DPO sobre o adapter SFT; `percentile_clipping=5` se houver spikes.
5. Deploy: **gate de qualidade >5%** ao quantizar; benchmark de edge (comparar com a régua do Gemma E2B INT4).

## Fontes que não abriram (pendências)
- Reddit (Gemma 4 e Qwen 3.5 27B) — bloqueio de domínio no WebFetch. Tentar via extensão Chrome se
  quiser fechar a visão "de comunidade".
- Blog oficial `qwen.ai/blog?id=qwen3.5` — SPA em JS; reconstruído via config.json + fontes secundárias.
