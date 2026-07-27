# Suíte de avaliação PT-BR — tasks validadas

Descoberta importante (2026-07-23): o **`lm-eval` 0.4.12 já traz uma suíte PT-BR rica** (305 tasks
com PT/POR/BR no nome, de 14.222 no total). Não é preciso instalar fork da comunidade para ter um
baseline sério.

Todas as tasks abaixo foram **testadas nesta máquina** — carregam e baixam o dataset sem erro.

## Suíte núcleo (o baseline)

| Task | O que mede | Por que está aqui |
|---|---|---|
| `mmmlu_pt_br` ⭐ | Conhecimento multidisciplinar (MMLU da OpenAI traduzido) | É **pt-BR específico**, não PT genérico. 14.042 questões. O número principal. |
| `arc_pt` | Raciocínio científico | Clássico, comparável entre modelos |
| `hellaswag_pt` | Senso comum / continuação | Clássico |
| `truthfulqa_pt_mc2` | Veracidade (resistência a falsidade popular) | Mede alucinação |
| `xwinograd_pt` | Correferência / ambiguidade | Sensível a qualidade linguística real |
| `assin_entailment` | Inferência textual (ASSIN) | **Benchmark nativo em português**, não traduzido |
| `assin_paraphrase` | Paráfrase (ASSIN) | **Nativo em português** |
| `belebele_por_Latn` | Compreensão de leitura | Alta qualidade, multilíngue |
| `global_piqa_prompted_por_latn_braz` | Senso comum físico | Tem variante **brasileira** explícita (`braz`) |
| `include_base_44_portuguese` | Conhecimento regional em português | Mede o que modelo genérico não sabe |

## Alternativas / extras (também validadas)
`m_mmlu_pt` · `mmlu_prox_lite_pt` (versão leve, mais rápida) · `mmlu_prox_pt` · `global_mmlu_pt` ·
`mmlu_pt_llama` · `arc_challenge_mt_pt` · `truthfulqa_pt_mc1` · `flores_pt` · `multiblimp_por` ·
`sib_por_prompt_[1-5]` · `afrisenti_por_prompt_[1-5]`

## ❌ Não usar (verificado)
- **`portuguese_bench`** — falha: depende de `facebook/flores`, que é **gated** no HF. Exigiria
  aceitar os termos do dataset e `HF_TOKEN`. Não vale o atrito.
- **ENEM / BLUEX / OAB / FaQuAD / HateBR / TweetSentBR** — **não existem** no lm-eval core. Vivem no
  fork da comunidade `eduagarcia/lm-evaluation-harness-pt` (o do Open PT-LLM Leaderboard).
  Opcional: instalar depois para comparar direto com o leaderboard público. Não bloqueia o baseline.

## Comando do baseline

⚠️ **Use `eval/run_baseline.py`, NÃO o CLI `lm_eval`.**
No transformers 5.x o CLI quebra com `load_in_4bit` — o argumento vai direto para o construtor
do modelo (`TypeError: Qwen3_5ForCausalLM.__init__() got an unexpected keyword argument
'load_in_4bit'`). O script monta o `BitsAndBytesConfig` e passa via kwargs do `HFLM`, que é o
único caminho que funciona. Sem 4-bit, o 4B em bf16 ocupa ~8 GB e não cabe nos 8 GB da placa.

```powershell
.\.venv\Scripts\Activate.ps1

# amostra rapida — para iterar
python eval/run_baseline.py --limit 200

# rodada completa — o numero oficial
python eval/run_baseline.py --limit 0 --tag baseline-oficial

# avaliar um checkpoint treinado (compara contra o baseline)
python eval/run_baseline.py --peft models/qwen3.5-4b-ptbr-sft --tag sft-v1
```

### Notas de execução (8 GB de VRAM)
- Quantização 4-bit NF4 ligada por padrão; `--no-4bit` só se sobrar VRAM.
- **`mmmlu_pt_br` tem 14.042 questões** — a rodada completa é demorada. Use `--limit 200` para
  iterar e guarde `--limit 0` para o número oficial.
- Rodar o baseline **antes** de qualquer treino. É o número que temos que superar.
- Resultados vão para `eval/results/<tag>_<timestamp>.json` — nunca sobrescrevem.
