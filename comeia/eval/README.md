# Fase 1 — Avaliação PRIMEIRO (antes de treinar)

Regra de ouro: **medir antes de treinar.** Sem baseline não há como saber se estamos competindo.
Esta fase custa ~US$0 de treino e valida a stack antes de qualquer gasto com GPU.

## Objetivo
1. Instalar o `lm-evaluation-harness` (EleutherAI) com as tasks PT-BR (ver `comeia/setup/`).
2. Rodar a **Qwen3-4B crua** (local, nesta máquina) → registrar o **baseline** (o número a bater).
   O 8B fica para a fase de cloud; o baseline do 8B roda lá quando escalarmos.
3. Fixar o conjunto qualitativo PT-BR (prompts próprios de instrução/segurança).

## Benchmarks-alvo (PT-BR)
- **ENEM** (challenge / 2022+) — raciocínio multidisciplinar em PT.
- **BLUEX** — vestibulares USP/UNICAMP.
- **ASSIN2** — similaridade semântica + inferência (STS/RTE).
- **OAB / exams PT** — jurídico, bom estressor.
- **MMLU-PT / GSM8K-PT** (traduzidos) — checar que não há regressão de capacidade geral.

Espelhar a metodologia do **Open PT-LLM Leaderboard** (mesmas tasks/few-shot) para que o número
seja comparável ao ranking público.

## Setup (rodar numa máquina com GPU — cloud alugada ou local para modelos ≤4B)

```bash
# ambiente
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U "lm-eval[api]" accelerate torch

# clonar o harness (para tasks customizadas PT-BR, se necessário)
git clone https://github.com/EleutherAI/lm-evaluation-harness
pip install -e ./lm-evaluation-harness
```

## Rodar o baseline (Qwen3-4B crua, local)

```powershell
# ajustar as tasks conforme disponibilidade no harness / repos da comunidade PT-BR
lm_eval `
  --model hf `
  --model_args pretrained=Qwen/Qwen3-4B,dtype=bfloat16 `
  --tasks enem_challenge,bluex,assin2_rte,assin2_sts `
  --num_fewshot 3 `
  --batch_size auto `
  --output_path comeia/eval/results/qwen3-4b-baseline.json
```
> Se os 8 GB estourarem no eval, quantizar (carregar em 4-bit) ou reduzir `--batch_size` para 1.

> Nota: os nomes exatos das tasks PT-BR podem variar entre versões do harness e repositórios da
> comunidade (ex.: `eduagarcia/lm-evaluation-harness-pt`). Confirmar na Fase 0 e travar as versões.

## Registrar o resultado
- Salvar o JSON em `comeia/eval/results/` e anotar o número por benchmark na tabela de metas do `README.md`.
- Esse baseline é o alvo. Cada fase de treino (SFT→DPO→RL) precisa mostrar ganho vs. ele **sem
  regredir** em MMLU-PT/GSM8K-PT.

## Checklist da Fase 1
- [ ] Ambiente + harness instalados.
- [ ] Tasks PT-BR resolvidas e versões travadas.
- [ ] Baseline Qwen3-8B rodado e salvo em `comeia/eval/results/`.
- [ ] Números copiados para a tabela de metas do README.
- [ ] Conjunto qualitativo PT-BR (20–50 prompts próprios) definido em `eval/qualitativo-ptbr.md`.
