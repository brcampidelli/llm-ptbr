# Dados intermediários da COMEIA perdidos em 2026-07-27 — e como reconstruir

> Registro honesto de um erro operacional meu (Claude), com o custo real e o caminho de volta.
> Não é um bug do projeto; é um erro de processo que virou regra.

## O que aconteceu

Durante a reorganização do repositório (`data/` → `comeia/data/`), rodei no Colab:

```bash
mv data/raw comeia/data/ ; mv data/processed comeia/data/ ; rm -rf data eval tokenizer
```

Os dois `mv` **falharam** — `mv: cannot move 'data/raw' to 'comeia/data/raw': Directory not empty`,
porque o `git reset --hard` já havia recriado `comeia/data/raw` com os arquivos versionados. Mas
encadeei com `;` em vez de `&&`, então o `rm -rf` rodou **assim mesmo** e apagou tudo que não estava
rastreado pelo git.

## O que se perdeu (todos não-rastreados, todos gerados)

| arquivo | conteúdo | como reconstruir | custo |
|---|---|---|---|
| `data/raw/extraction_<prof>.jsonl` | 934 documentos + extrações do professor | `comeia/data/11_gen_extraction.py` | ~US$ 0,30 + ~25 min |
| `data/processed/sft_extraction.jsonl` | 370 itens que "o base erra" | `comeia/data/12_filter_extraction.py` | GPU, ~15 min |
| `data/processed/extraction_*.jsonl` | splits difícil/fácil (holdout) | `comeia/data/13_build_extraction_splits.py` | segundos |
| `data/raw/coder_tasks_hard/_easy.jsonl` | 239 difíceis + 638 fáceis | `comeia/data/09_filter_hard_tasks.py` | GPU, ~20 min |
| `data/processed/encoder_ner.*` | spans BIO para o baseline de encoder | `comeia/data/14_build_encoder_spans.py` | segundos |
| `eval/results/*.json` | resultados brutos dos evals | re-rodar os evals | GPU |

**Atalho:** `comeia/colab/reproduce_extracao.py` refaz a cadeia inteira da extração num comando,
~35–54 min, retomável.

## O que NÃO se perdeu

- ✅ **O adapter de extração** — na Drive, `MyDrive/qwen35-4b-extracao`, md5 `29fe61fc…` conferido
  contra o original que produziu os números publicados.
- ✅ **Os adapters `agentica` e `coder`** — já estavam na Drive.
- ✅ **Todos os resultados medidos** — estão em [comeia-sobre-qwen.md](comeia-sobre-qwen.md) e nos
  demais docs. Nenhuma conclusão do projeto depende dos arquivos apagados.
- ✅ **As entradas de origem** — `coder_tasks.jsonl`, `extraction_tasks.jsonl`, as sementes e os
  `sft_agentic/sft_ptbr` estão versionados no git.
- ✅ **`external_full.json`** (baseline externo de 4 braços) — copiado para a Drive antes.

## Decisão: não reconstruir agora

Em 2026-07-27 o projeto passou a focar **exclusivamente no Bee**; a camada COMEIA-sobre-Qwen entrou em
modo histórico. Regenerar esses intermediários gastaria GPU e destilação em dado que não vamos treinar
no curto prazo. Fica o caminho documentado acima, para quando a COMEIA for reaplicada **sobre o Bee** —
e nesse momento o dado terá de ser regerado de qualquer forma, porque o filtro "o base erra" depende
de *qual* é o base.

## A regra que fica

**Nunca encadear remoção recursiva depois de um comando que pode falhar.** Em vez de
`mv A B ; rm -rf A`, uma das duas formas:

```bash
mv A/* B/ && rmdir A          # só remove se o mv passou
```
```bash
mv A B_backup_$(date +%s)     # renomear em vez de apagar: reversível
```

A regra já existia no projeto na forma "antes de deletar ou sobrescrever, olhe o alvo". O que faltou
foi aplicá-la a um comando encadeado, onde o alvo mudou entre a decisão e a execução.
