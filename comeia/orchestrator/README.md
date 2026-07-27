# COMEIA — orquestrador de SLMs especializadas (Fase 0)

> A comeia vence por **decomposição + roteamento**, não por "somar cérebros pequenos".
> Ela quebra a tarefa até virar subtarefas estreitas que uma SLM faz melhor e 10–30× mais
> barato, e chama o modelo forte **só** no raciocínio residual difícil.

## A arquitetura

**1 backbone (Qwen3.5-4B) carregado UMA vez + N adapters LoRA trocados a quente (hot-swap).**
Cada adapter é uma "abelha" especializada — vira "1 modelo + N personalidades". Isso resolve
VRAM (backbone ~3 GB + adapters de dezenas de MB) e coordenação de uma vez. O **orquestrador é
código** (topologia "Code Agency" da NVIDIA), não um LLM gigante.

```
query ──► Router (regras + complexidade) ──► escolhe a abelha
                                              │
        ┌─────────────────────────────────────┼───────────────────────┐
        ▼                 ▼                     ▼                       ▼
   agentica          coder              chat_ptbr (default)      base_forte (fallback)
   (tool-use)       (código)           SFT-v2, PT-BR            raciocínio difícil
   [adapter]        [adapter]          [adapter REAL]           [backbone base hoje;
    FAST             FAST               FAST                     7-11B/nuvem depois] slow
```

## Arquivos
| Arquivo | Papel |
|---|---|
| `bees.json` | **registry das abelhas** (nome, adapter, gatilhos, fast-path). Adicionar abelha = editar aqui. |
| `registry.py` | dataclasses `Bee`/`Registry` + loader do JSON |
| `hive.py` | **engine**: carrega o backbone 1×, hot-swap de adapters LoRA (PEFT `set_adapter`/`disable_adapter`) |
| `router.py` | **roteador determinístico** + a métrica-chave (**fração de fast-path**) |
| `run.py` | CLI: chat interativo, batch, e `--route-only` (testa rota sem GPU) |

## Como rodar

**Testar o roteador SEM GPU** (valida rota + métrica de graça, roda em qualquer lugar):
```bash
python comeia/orchestrator/run.py --route-only --sample
python comeia/orchestrator/run.py --route-only --batch prompts.txt
```

**A comeia de verdade** (precisa de GPU + o adapter da abelha chat):
```bash
# Colab L4 (o adapter SFT-v2 está no Drive):
python comeia/orchestrator/run.py --batch prompts.txt --max-new 256
python comeia/orchestrator/run.py                    # chat interativo

# Local: aponte o adapter para onde ele estiver
python comeia/orchestrator/run.py --chat-adapter models/qwen3.5-4b-ptbr-sft
```

## A métrica que decide tudo
O `Router` reporta a **fração de fast-path** — quantas queries evitam o modelo caro (o fallback).
**Alta ⇒ a comeia é econômica; baixa ⇒ é só complexidade.** Medir isto obsessivamente.

## Estado (Fase 0)
- ✅ Roteamento + métrica **validados localmente** (80% fast-path na amostra: chat/código/tool-use
  nas abelhas baratas; só o raciocínio difícil no fallback).
- ✅ `chat_ptbr` = adapter SFT-v2 real (a 1ª abelha).
- 🔜 `agentica` (Fase 1) e `coder` (Fase 2): gatilhos já ativos, mas **sem adapter próprio ainda** →
  hoje caem no backbone base. Fabricar o adapter = rodar `comeia/data/` + `comeia/train/sft_qlora.py` e ajustar
  o `adapter_path` no `bees.json`.
- 🔜 abelha multimodal (Fase 4): modelo separado ~9B (Qwen3.5-VL-9B), fora do "1 backbone + N adapters".

## Limites honestos (do plano)
- **Overhead de coordenação é o calcanhar de Aquiles** — 2–3 abelhas + 1 roteador, não 10.
- A **heurística de complexidade** do roteador é um placeholder (regras + tamanho). A Fase 3 troca por
  um classificador pequeno treinado nos clusters de tarefa (passo S3/S6 da NVIDIA).
- **Latência serial** soma quando a cadeia é longa — a comeia só ganha se o fast-path evita o modelo
  caro na maioria das vezes.
