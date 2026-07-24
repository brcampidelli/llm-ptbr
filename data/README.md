# Fase 2 — Pipeline de dados PT-BR

O diferencial de um modelo PT-BR é o **dado**. Este pipeline produz os arquivos que a Fase 3 consome.

## Regra dura (não negociável)
Destilação **só de professores abertos** (`ALLOWED_TEACHERS` em `config.py`).
**Nunca** GPT/Claude/Gemini como professor — os ToS proíbem treinar modelo concorrente com as saídas
e isso contamina a licença do nosso release aberto. O `assert_teacher_allowed()` falha alto e cedo
se alguém tentar.

## Runbook (na ordem)

```powershell
# ambiente
.\.venv\Scripts\Activate.ps1
$env:OPENROUTER_API_KEY = "<sua chave>"

# 1) Destilar de professor aberto a partir das sementes PT-BR
python data/01_distill_teacher.py --seeds data/seeds_ptbr.txt --teacher Qwen/Qwen3-235B-A22B --dry-run
python data/01_distill_teacher.py --seeds data/seeds_ptbr.txt --teacher Qwen/Qwen3-235B-A22B

# 2) Traduzir datasets EN de alta qualidade, com QC
python data/02_translate_qc.py --dataset allenai/tulu-3-sft-mixture --limit 500

# 3) Filtro de qualidade + dedup (exato e aproximado)
python data/03_filter_dedup.py --report-only     # inspecionar antes
python data/03_filter_dedup.py

# 4) Decontaminação vs. os benchmarks de teste  ← etapa que torna a avaliação honesta
python data/04_decontaminate.py --benchmarks "eval/benchmarks/*.jsonl"

# 5) Splits finais (formato chat p/ TRL/Unsloth)
python data/05_build_splits.py --holdout 500
```

## Arquivos
| Arquivo | Papel |
|---|---|
| `config.py` | decisões centrais: professores permitidos, limiares de qualidade, caminhos |
| `common.py` | I/O jsonl, normalização, n-gramas, heurística de "portuguesidade" |
| `seeds_ptbr.txt` | ~70 prompts-semente PT-BR (conhecimento, raciocínio, código, escrita, jurídico, negócios, segurança) |
| `01_distill_teacher.py` | gera pares instrução→resposta com professor aberto (retomável) |
| `02_translate_qc.py` | traduz datasets EN→PT-BR com QC (rejeitados vão para `.rejects.jsonl`) |
| `03_filter_dedup.py` | filtro de qualidade + dedup exato e aproximado (Jaccard c/ índice invertido) |
| `04_decontaminate.py` | remove treino que vaza os benchmarks (13-grama) |
| `05_build_splits.py` | monta `sft_ptbr.jsonl` + holdout interno |

## Fluxo dos dados
```
seeds_ptbr.txt ─┐
                ├─> raw/*.jsonl ─> clean.jsonl ─> decontaminated.jsonl ─> sft_ptbr.jsonl
datasets EN ────┘      (01,02)        (03)             (04)                   (05)
```

## Modo CoT (destilação com raciocínio) — upgrade nº1

`01_distill_teacher.py --cot` liga o **canal de reasoning nativo** do OpenRouter: o professor
raciocina antes de responder, e guardamos `reasoning` (raciocínio) + `response` (resposta limpa)
separados. `05_build_splits.py --cot` embute o raciocínio como `<think>…</think>` no alvo de treino.

```powershell
# destilar COM raciocínio (use um --tag distinto do run sem-CoT!)
python data/01_distill_teacher.py --seeds data/seeds_ptbr_expanded.txt --teacher deepseek/deepseek-v4-flash --tag deepseek-cot --cot --workers 20
# ...03, 04 iguais...
python data/05_build_splits.py --cot --holdout 300   # inclui o raciocínio no alvo
```

**Validado (2026-07-24):** o canal nativo dá separação limpa (resposta sem duplicar o raciocínio).
⚠️ **Caveat honesto:** o *idioma* do raciocínio é misto — DeepSeek raciocina em inglês em algumas
tarefas (ex.: tradução) e em PT nas outras. As respostas ficam sempre limpas/corretas; só o
raciocínio varia. Decisão em aberto: treinar no raciocínio como está (misto), ou filtrar só o
raciocínio PT-BR no `05` (via `pt_ratio`), ou treinar só na resposta (professor raciocina →
resposta melhor, mais seguro).

## O que observar
- **`03` com `--report-only`** mostra quanto cada filtro está cortando. Se estiver cortando demais,
  calibrar os limiares em `config.py` (não relaxar o de portuguesidade sem olhar amostras).
- **`04` acima de 5% contaminado = alerta.** Significa que alguma fonte inclui os próprios benchmarks.
  Auditar `contaminated.jsonl` antes de treinar.
- **Ampliar as sementes** é o caminho mais barato de ganhar qualidade: mais domínios, mais variedade
  de formato de pergunta. Iterar dados > iterar hiperparâmetros.

(O conteúdo de `raw/` e `processed/` é ignorado no git — ver `.gitignore`.)
