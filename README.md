# Desenvolvendo LLM — Modelo PT-BR generalista, aberto e competitivo

> Bitácora do projeto. Objetivo: adaptar uma base aberta forte num **modelo PT-BR generalista**
> competitivo (pesos abertos no Hugging Face). Não treinar do zero — vencer no **pós-treino + dados
> PT-BR + avaliação**. Plano completo: `~/.claude/plans/estou-pensando-em-desenvolver-partitioned-unicorn.md`.

## Tese em uma frase
Modelo pequeno (3B–8B) bem pós-treinado > modelo gigante genérico no idioma/nicho certo.
Prova viva na literatura: **PEARL** (Qwen3-4B + RL agêntico supera DeepSeek-V3.2-685B na tarefa dele).

## Decisões (2026-07-23)
| Decisão | Escolha |
|---|---|
| Objetivo | Modelo **PT-BR generalista** |
| Abordagem | **Adaptar base aberta** (não from-scratch, não continued-pretraining pesado) |
| Licença | **Pesos abertos** (Apache-2.0 preferencial) |
| Base | **Qwen3.5-4B — FECHADO** (Apache-2.0, 262K ctx→1M, **201 idiomas**, multimodal; tem variante `-Base`). Escala para **Qwen3.5-9B** na cloud. |
| Provedor / início | **Esta máquina (RTX 5070 8GB)** — loop Tier A local no Qwen3-4B, **US$0**. Cloud só ao escalar 8B/RL. |
| Compute | Começar **Tier A local (US$0)**, escalar para Tier B cloud só com tração provada |

### Por que Qwen3.5 (vs Mistral/Gemma)
- **Multilíngue/PT-BR:** o mais forte — **201 idiomas e dialetos** no Qwen3.5. Mistral foca EN/EU; Gemma bom mas menos.
- **Licença:** **Apache-2.0** limpa (Mistral também). ⚠️ **Gemma NÃO é Apache** — licença própria do Google com restrições de uso → atrito para release aberto.
- **Faixa de tamanhos:** mesma família → 4B local e 9B cloud sem trocar de ecossistema.
- ⚠️ Correção feita em 2026-07-23: o plano inicial dizia "Qwen3-4B", mas o catálogo já está em
  **Qwen3.5/3.6**. Verificado no HF: `Qwen/Qwen3.5-4B` é Apache-2.0 e tem `Qwen/Qwen3.5-4B-Base`.

### Custo de dados (verificado na API do OpenRouter, 2026-07-23)
Rodar `python data/00_check_teachers.py` regenera esta tabela com preços atuais.

| Professor | $/M in | $/M out | Pares por US$10 |
|---|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 0 | 0 | **ilimitado*** (550B, ctx 1M) |
| `nvidia/nemotron-3-super-120b-a12b:free` | 0 | 0 | ilimitado* |
| `deepseek/deepseek-v4-flash` ⭐ padrão | 0,098 | 0,196 | **65.832** |
| `qwen/qwen3.5-9b` | 0,10 | 0,15 | 83.333 |
| `mistralai/mistral-nemo` (tradução) | 0,019 | 0,03 | 419.287 |
| `deepseek/deepseek-v4-pro` (premium) | 0,435 | 0,87 | 14.831 |

\* grátis, mas com rate limit — serve para volume moderado, não para lotes grandes.

**Implicação:** com US$10 dá para gerar **~65 mil pares PT-BR de alta qualidade**. O dataset deixou
de ser o gargalo financeiro do projeto.

### Hardware verificado (2026-07-23)
- GPU **RTX 5070 Laptop, 8 GB VRAM** (Blackwell, compute **sm_120**, driver 577.13) · CPU Ultra 9 275HX 24c · 31 GB RAM · 577 GB livres.
- **Teto dos 8 GB:** QLoRA em ≤4B e inferência quantizada = OK aqui. 8B full / RL / GRPO = cloud.
- ⚠️ **Blackwell precisa de PyTorch build CUDA 12.8 (cu128)** — o torch estável comum não traz kernels sm_120. Ver `setup/`.

## 📊 BASELINE — Qwen3.5-4B crua (2026-07-23)

Suíte `quick`, 4-bit NF4, 3-shot, `--limit 100`. **É o número a superar.**

| Task | Métrica | Baseline |
|---|---|---|
| `belebele_por_Latn` | acc | **0,930** |
| `xwinograd_pt` | acc | **0,800** |
| `assin_paraphrase` | acc | 0,660 |
| `arc_pt` | acc_norm | 0,580 |
| `hellaswag_pt` | acc_norm | 0,570 |
| `assin_entailment` | acc | **0,560** ← mais fraco |
| `truthfulqa_pt_mc2` | acc | 0,455 |
| `arc_pt` | acc | 0,500 |
| `hellaswag_pt` | acc | 0,390 |

**Leitura:** compreensão de leitura já é forte (0,93) — não é aí que ganhamos. As oportunidades
reais são **`assin_entailment` (0,56)**, `hellaswag_pt` e `truthfulqa_pt_mc2`.

⚠️ **Ressalva estatística:** com `--limit 100` o erro-padrão é ≈ ±0,05. **Diferença menor que
~10 pontos percentuais não é significativa.** Para declarar vitória de verdade, rodar
`--suite core --limit 0` (inclui `mmmlu_pt_br`, demorado) e comparar aí.

Arquivo: `eval/results/baseline-quick_20260723-230837.json`

## 🧪 SFT-v1 — resultado (2026-07-24)

Primeiro treino completo: QLoRA no Qwen3.5-4B, 1.840 exemplos PT-BR destilados, 1 época.
Avaliado na mesma config do baseline (suíte `quick`, 4-bit, 3-shot, `--limit 100`).

| Task | Baseline | SFT-v1 | Delta | Veredito |
|---|---|---|---|---|
| `assin_paraphrase` (nativo PT) | 0,660 | 0,700 | +0,040 | ruído |
| `assin_entailment` (nativo PT) | 0,560 | 0,590 | +0,030 | ruído |
| `truthfulqa_pt_mc2` | 0,455 | 0,469 | +0,014 | ruído |
| `hellaswag_pt` | 0,570 | 0,580 | +0,010 | ruído |
| `belebele_por_Latn` | 0,930 | 0,920 | −0,010 | ruído |
| `arc_pt` | 0,580 | 0,560 | −0,020 | ruído |
| `xwinograd_pt` | 0,800 | 0,760 | −0,040 | ruído |

**Ganhos: 0 · Regressões: 0 · Todos dentro do ruído (n=100, limiar ≈ ±14pp).**

**Interpretação honesta:**
- **Não** é falha do pipeline. É falta de poder estatístico + efeito pequeno. A curva de loss já era
  plana (1,09 → ~0,96 e estabiliza) — previmos este resultado antes de avaliar.
- As 2 tasks **nativas em PT** subiram mais (+0,04, +0,03), mas com 7 tasks isso é indistinguível do
  acaso. **Hipótese a testar**, não resultado.
- Causa provável: o Qwen3.5-4B **Instruct** já sabia fazer o que ensinamos → pouco gradiente.
- Para detectar ~3pp com confiança seria preciso **n≈4.000/task** — inviável nesta máquina, viável na
  A100 do Colab. **A resposta "o treino funcionou?" esta máquina não consegue dar.**

**Próximos passos (ranqueados por alavanca):**
1. Partir do **`Qwen3.5-4B-Base`** (sem pós-treino) — maior impacto, mesmo custo.
2. **DPO** em vez de SFT — aprende com a diferença boa/ruim, dá sinal mesmo com texto já aceitável.
3. Avaliação com **n grande** na A100.
4. Professor mais forte nos domínios fracos (`assin_entailment`, `truthfulqa`).

Arquivos: `eval/results/sft-v1_20260724-042200.json` · adapter `models/qwen3.5-4b-ptbr-sft-v1/`

## ➡️ Migração para Colab Pro+ (em andamento, 2026-07-24)
Motivo: todos os gargalos do dia foram os 8 GB de VRAM + Windows (fallback lento do gated delta rule,
`flash-linear-attention` não instala). Ver `docs/colab-setup.md`. `colab-mcp` já configurado.

## Metas medíveis ("competitivo" = número, não sensação)
- [x] **Baseline registrado** ✅ (tabela acima)
- [x] **Pipeline validado ponta-a-ponta** ✅ (dados → treino → avaliação comparável, US$ 0,50)
- [ ] **Ganho estatisticamente significativo** — pendente (precisa de n grande → Colab)
- [ ] **Ganho pós-SFT**: superar o baseline em ENEM/BLUEX/ASSIN2 sem regredir em MMLU/GSM8K traduzidos.
- [ ] **Ganho pós-DPO**: melhora adicional em qualidade/alinhamento (aval. qualitativa PT-BR).
- [ ] **Competitivo**: empatar/superar modelos abertos de tamanho semelhante no **Open PT-LLM Leaderboard**.
- [ ] **Roda no hardware do Bruno**: GGUF quantizado carrega e responde no RTX 5070 8GB / VPS.
- [ ] **Release**: model card + pesos (full+GGUF) + demo no HF.

## Estrutura
```
├── artigos para estudos/   # 12 PDFs de estudo (já existiam)
├── docs/                   # leituras da Fase 0, notas de decisão
├── eval/                   # Fase 1 — harness de avaliação PT-BR (lm-eval)
├── data/                   # Fase 2 — pipelines de dados PT-BR (destilação/tradução/filtro)
├── train/                  # Fase 3–5 — configs SFT / DPO / GRPO
└── models/                 # checkpoints (ignorado no git)
```

## Status atual (2026-07-23)
- ✅ **Fase 0** — scaffold, base/hardware travados, **ambiente instalado e validado** (`setup/README.md`).
  QLoRA 4-bit testado de verdade na GPU Blackwell: funciona.
- ✅ **Fase 2 (código)** — pipeline de dados completo e testado end-to-end com fixtures (`data/`).
- ✅ **Fase 3 (código)** — `train/sft_qlora.py` escrito e com dry-run validado.
- ⏭️ **Fase 1 — PRÓXIMO PASSO: rodar o baseline do Qwen3-4B** (`eval/README.md`).
  Sem esse número não há como provar ganho. Precisa resolver as tasks PT-BR do harness.
- ⏳ **Fase 2 (execução)** — depende de `OPENROUTER_API_KEY` para destilar/traduzir.

## Regras duras do projeto
- **Nunca** treinar com saídas de GPT/Claude/Gemini (ToS proíbem + contamina a licença aberta).
  Destilação só de **professores abertos** (Qwen3-235B, Llama-405B, DeepSeek…).
- **Decontaminação** obrigatória: dados de treino não podem vazar os benchmarks de teste.
- Iterar **dados** antes de iterar hiperparâmetros — quase todo ganho vem do dado.

Última atualização: 2026-07-23.
