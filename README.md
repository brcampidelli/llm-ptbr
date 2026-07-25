# 🐝 A COMEIA — orquestrador local de SLMs especializadas

> Um orquestrador em código coordenando **várias SLMs especializadas** ("abelhas") sobre **um único
> backbone** Qwen3.5-4B, com adapters LoRA trocados a quente. Pesos abertos.
> Plano completo: `~/.claude/plans/estou-pensando-em-desenvolver-partitioned-unicorn.md`

## Tese em uma frase

**A comeia vence por decomposição + roteamento — não por "somar cérebros pequenos".** Ela quebra a
tarefa até virar subtarefas estreitas que uma SLM faz melhor e **10–30× mais barato**, e chama o
modelo forte **só** no raciocínio residual difícil.

### Honestidade sobre o que é hype
- ❌ **"N SLMs pequenas somadas igualam uma LLM grande"** — nenhuma fonte prova isso.
- ✅ **O que a literatura sustenta:** em tarefas estreitas e repetitivas (o grosso do trabalho de um
  agente: parsear, formatar, escolher ferramenta, extrair), uma SLM afinada **iguala ou supera** um
  generalista gigante. Base: NVIDIA, *[Small Language Models are the Future of Agentic
  AI](https://arxiv.org/abs/2506.02153)* — topologia **"Code Agency"**, onde o orquestrador é
  **código**, não um LLM. Casos reais: 40–70% das chamadas de agentes (MetaGPT 60%, Cradle 70%)
  são substituíveis por SLM.
- ⚠️ **O moat não é o modelo** (open-weight virou commodity). É a **orquestração + os dados de
  especialização + o pipeline de fine-tune**.

## A arquitetura

```
query ──► Router (regras + complexidade) ──► escolhe a abelha
                                              │
        ┌─────────────────┬───────────────────┼──────────────────────┐
        ▼                 ▼                   ▼                      ▼
   agentica            coder             chat_ptbr (default)   base_forte (fallback)
   tool-use            código            PT-BR                 raciocínio difícil
   [adapter]           [adapter]         [adapter REAL]         [backbone base]
    FAST                FAST              FAST                   slow
```

**1 backbone carregado UMA vez + N adapters LoRA a quente.** Cada abelha é um adapter → vira
"1 modelo + N personalidades", resolvendo **VRAM e coordenação de uma vez**.

| Item | VRAM medida (L4) |
|---|---|
| Backbone Qwen3.5-4B em 4-bit NF4 | **2,98 GB** de 22 GB |
| Cada adapter LoRA (r=16) | dezenas de MB |
| → **dezenas de abelhas cabem sobre um backbone** | ✅ verificado |
| Abelha multimodal (Fase 4, ~9B separado) | ~6–7 GB (única fora do backbone único) |

## ⭐ A métrica que decide tudo: fração de fast-path

Quantas queries **evitam o modelo caro**. Alta ⇒ a comeia é econômica. Baixa ⇒ é só complexidade.
Medida em toda rota pelo `Router` e reportada ao fim de cada execução.

## 📊 Resultados medidos

### Fase 0 — a comeia rodando na L4 (2026-07-24) ✅
```
⭐ FRACAO DE FAST-PATH: 80.0%  (8/10)
   chat_ptbr 4 (40%) · coder 2 (20%) · agentica 2 (20%) · base_forte 2 (20%)
latencia media: 18.3s  (min 10.1s / max 24.2s)
```
Backbone carregado 1× (2,98 GB), adapter real da `chat_ptbr` por cima, hot-swap em 10/10 gerações,
roteamento correto em todas (código→`coder`, tool-use→`agentica`, difícil→`base_forte`).

### O experimento que MATOU a hipótese generalista (e mudou o projeto)
SFT generalista PT-BR, **5.657 exemplos** destilados, avaliado a **n=300** (poder estatístico real):

| Task | Baseline | SFT-v2 | Delta | Veredito |
|---|---|---|---|---|
| `assin_paraphrase` | 0,680 | 0,723 | +0,043 | ruído |
| `assin_entailment` | 0,563 | 0,583 | +0,020 | ruído |
| `hellaswag_pt` | 0,600 | 0,610 | +0,010 | ruído |
| `truthfulqa_pt_mc2` | 0,484 | 0,486 | +0,002 | ruído |
| `arc_pt` | 0,563 | 0,560 | −0,003 | ruído |
| `xwinograd_pt` | 0,776 | 0,768 | −0,008 | ruído |
| `belebele_por_Latn` | 0,913 | 0,900 | −0,013 | ruído |

**Ganhos: 0 · Regressões: 0 · 7/7 dentro do ruído** (limiar ≈ ±7,5pp a n=300).

**Leitura honesta:** não é bug — é achado. Uma base instruct já forte (Qwen3.5-4B) **não melhora com
mais destilação de instrução genérica**. Além disso, benchmark de múltipla escolha mede
*conhecimento*, que SFT não adiciona. Conclusão: o valor não está em "um Qwen um pouco melhor" —
está em **especialização + orquestração**. Daí a comeia.

*(Histórico: SFT-v1 com 1.840 exemplos a n=100 deu o mesmo resultado, mas sem poder estatístico para
concluir. Por isso repetimos com 3× mais dados e n=300.)*

## As abelhas

| Abelha | Foco | Estado |
|---|---|---|
| `chat_ptbr` | chat/generalista PT-BR | ✅ **adapter real** (SFT-v2, 5.657 ex) |
| `agentica` | tool-use / seguir instrução | 🔨 **1.495 exemplos prontos**, adapter em treino (Fase 1) |
| `coder` | código em escopo limitado | ⏳ Fase 2 (gatilhos já ativos) |
| `base_forte` | fallback do raciocínio difícil | ✅ backbone base (futuro: 7–11B/nuvem) |
| multimodal | imagem/áudio | ⏳ Fase 4 — modelo **separado ~9B** (Qwen3.5-VL) |

### Abelha agêntica — o dado ensina 3 comportamentos, não 1
| Comportamento | Exemplos | % |
|---|---|---|
| pedido exige ferramenta → JSON `{"tool","args"}` | 886 | 59% |
| pedido **não** exige → resposta direta em texto | 609 | **41%** |
| pedido ambíguo → pede o que falta, não inventa | (incluído acima) | — |

Os 41% sem ferramenta são **de propósito**: *over-calling* (chamar ferramenta para tudo) é a falha
clássica de modelo agêntico. Validação dura contra o catálogo (`data/agentic_tools.json`):
ferramenta tem que existir, args obrigatórios presentes, nenhum arg desconhecido — **2,8%
rejeitados** vão para `.rejects.jsonl` e não treinam.

## 🐛 Bugs reais encontrados por RODAR (não por revisar)

1. **`apply_chat_template` devolve `BatchEncoding` no transformers 5.x** — não tensor puro.
   `generate()` quebrava com `AttributeError`. Estava **latente também** no `quantibias_gate.py`.
2. **O professor errou uma conta e respondeu de cabeça:** `48239 × 1177` → devolveu 56.757.303
   (correto: **56.777.303**) em texto, em vez de usar a `calculator`. O validador de JSON não pega
   (a resposta nem era JSON). Corrigido com regra explícita no prompt **+** guard
   `looks_like_hard_math()` que rejeita aritmética de 3+ dígitos feita de cabeça.
3. **O Qwen3.5 gasta os tokens raciocinando** (`<think>`) e a resposta final truncava. Agora
   `enable_thinking=False` por padrão + `strip_think()` como rede (trata bloco fechado, fechamento
   órfão e bloco **aberto/truncado**, onde não existe resposta e o sistema avisa em vez de fingir).

## Estrutura
```
├── orchestrator/   # 🐝 A COMEIA — registry, engine (hot-swap), router, CLI
│   ├── bees.json   #    registry das abelhas (adicionar abelha = editar o JSON)
│   ├── hive.py     #    backbone 1× + hot-swap de adapters LoRA
│   ├── router.py   #    roteador determinístico + fração de fast-path
│   └── run.py      #    CLI: chat / batch / --route-only (testa rota SEM GPU)
├── data/           # pipeline de dados (destilação, self-instruct, preferências, agêntico)
├── train/          # SFT e DPO via QLoRA
├── eval/           # harness PT-BR (lm-eval), comparação com significância, gate QuantiBias
├── colab/          # receita da L4 (Colab Pro+)
└── models/         # checkpoints (ignorado no git)
```

## Como rodar

**Testar o roteamento SEM GPU** (valida rota + métrica de graça, roda em qualquer máquina):
```bash
python orchestrator/run.py --route-only --sample
```

**A comeia de verdade** (GPU + adapter):
```bash
python orchestrator/run.py --sample --max-new 256
python orchestrator/run.py --chat-adapter models/qwen3.5-4b-ptbr-sft   # adapter local
```

**Fabricar uma abelha nova** (exemplo: a agêntica):
```bash
python data/07b_expand_agentic.py --target 1500          # sementes: 91 -> 1690
python data/07_distill_agentic.py --seeds data/seeds_agentic_expanded.txt --workers 16
python data/05_build_splits.py --in data/raw/agentic_<prof>.jsonl \
    --out data/processed/sft_agentic.jsonl --system-file data/agentic_system.txt
python train/sft_qlora.py --data data/processed/sft_agentic.jsonl    # -> adapter
# registrar o adapter_path no orchestrator/bees.json
```

## Custo real até aqui
**≈ US$ 1,75** de destilação (todo o dado: 5.657 PT-BR + 1.495 agênticos) + Colab Pro+ (assinatura
que o Bruno já tinha). O dataset **não é o gargalo financeiro** — com US$10 dá ~65 mil pares via
`deepseek-v4-flash`. Rodar `python data/00_check_teachers.py` regenera a tabela de preços.

## Metas medíveis ("competitivo" = número, não sensação)
- [x] **Baseline registrado** (n=300)
- [x] **Pipeline ponta-a-ponta validado** (dados → treino → avaliação com significância)
- [x] **Hipótese generalista testada e refutada** com poder estatístico
- [x] **Comeia rodando**: backbone 1×, hot-swap, roteamento correto, fast-path 80%
- [ ] **Abelha agêntica bate o base NA TAREFA DELA** (eval de tool-use, não MMLU)
- [ ] **Avaliação de geração com juiz** (múltipla escolha não mede o que SFT muda)
- [ ] **Fast-path alto o bastante** para a comeia ser mais barata que chamar o forte sempre
- [ ] **Roda local**: GGUF quantizado no RTX 5070 8 GB
- [ ] **Release**: model card + pesos + demo no HF

## Regras duras do projeto
- **Nunca** treinar com saídas de GPT/Claude/Gemini (ToS proíbem + contaminam a licença aberta).
  Destilação só de **professores abertos** — `assert_teacher_allowed()` falha alto e cedo.
- **Decontaminação** obrigatória: treino não pode vazar os benchmarks.
- **Iterar dados antes de hiperparâmetros** — quase todo ganho vem do dado.
- **Testar > confiar no design:** os 3 bugs acima só apareceram ao rodar de verdade.

## Hardware
- Local: **RTX 5070 Laptop 8 GB** (Blackwell sm_120 — exige PyTorch **cu128**) · Ultra 9 275HX · 31 GB RAM.
- Treino/avaliação: **Colab Pro+ (L4, 22 GB)** — a capacidade (sem OOM, caminho para 9B) é o valor real,
  não a velocidade bruta.

Última atualização: 2026-07-24.
