"""Fase 2 (dados) — Splits da abelha de extração.

Converte {schema, lang, documento, extracao} no formato de treino, com as DUAS
cicatrizes deste projeto embutidas:

⚠️ 1. FORMATO prompt/completion, não "messages". No formato `messages` o TRL
calcula a loss em TODOS os tokens. No dataset agêntico isso pôs **93,8% da loss
nos tokens do prompt** (system de 928 tokens, idêntico em 1.495 exemplos): a loss
despencou 1,273 → 0,0755 **decorando o catálogo**, não aprendendo a tarefa. Aqui o
prompt é ainda mais pesado (o schema + o documento inteiro), então o risco seria
maior. Em prompt/completion o TRL mascara o prompt sozinho.

⭐ 2. HOLDOUT ESTÁVEL POR HASH DO DOCUMENTO — e isto conserta um defeito que já
custou um retreino. A versão anterior embaralhava o pool e cortava os primeiros N.
Parecia correto (embaralhar antes de separar), mas tinha uma dependência
escondida: `shuffle` sobre uma lista de 510 itens dá permutação COMPLETAMENTE
diferente da de 513. E o gate NÃO é bit-reproduzível — a geração em lote muda o
padding e a aritmética de ponto flutuante junto, então duas execuções deram 513 e
510 difíceis. Resultado: um holdout regerado depois do treino nascia contaminado,
com ~73% dele dentro do treino. Tive que retreinar.

Agora a pertinência ao holdout é decidida pelo **conteúdo do documento**
(`sha1(documento) % 1000 < corte`), não pela posição dele numa lista. Isso torna o
split:
  - ESTÁVEL — o mesmo documento cai sempre do mesmo lado, independente de quantos
    itens o gate classificou como difíceis nesta execução;
  - ROBUSTO à não-reprodutibilidade do gate — dois gates que diferem em 3 itens
    produzem holdouts que diferem nesses 3, não em 73%;
  - AUDITÁVEL — dá para verificar de fora se um documento é de treino ou de teste
    sem reproduzir o pipeline todo.

O holdout continua ESTRATIFICADO por idioma (o corte é aplicado por idioma), senão
o francês — o idioma mais difícil, 62% de erro do base — ficaria sub-representado
justo na avaliação.

TRÊS SAÍDAS, e a terceira é a que pega dano colateral:
  sft_extraction.jsonl        treino (o base ERRA nestes)
  sft_extraction.eval.jsonl   holdout difícil — mede o ganho
  sft_extraction.easy.jsonl   holdout FÁCIL (o base acerta) — mede a REGRESSÃO.
                              Foi este tipo de holdout que expôs os −17,5 pp de
                              dano colateral da coder, que de outra forma
                              teriam passado despercebidos.

Uso:
    python data/13_build_extraction_splits.py
    python data/13_build_extraction_splits.py --holdout 160
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESSED_DIR, RAW_DIR, ensure_dirs  # noqa: E402
from common import read_jsonl, write_jsonl  # noqa: E402
from schema_check import build_task_prompt, load_schemas  # noqa: E402

IN_HARD = RAW_DIR / "extraction_hard.jsonl"
IN_EASY = RAW_DIR / "extraction_easy.jsonl"
OUT_TRAIN = PROCESSED_DIR / "sft_extraction.jsonl"
OUT_EVAL = PROCESSED_DIR / "sft_extraction.eval.jsonl"
OUT_EASY = PROCESSED_DIR / "sft_extraction.easy.jsonl"


def bucket(documento: str, seed: int = 42) -> int:
    """0..999 estável a partir do CONTEÚDO do documento.

    A chave do split. `sha1` porque precisa ser estável entre processos — o `hash()`
    do Python é randomizado por execução (PYTHONHASHSEED) e daria splits diferentes
    a cada run, que é exatamente o problema que estamos consertando.
    """
    h = hashlib.sha1(f"{seed}:{documento}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 1000


def to_pc(row: dict, schemas: dict) -> dict:
    """{documento, extracao} → {prompt, completion} no formato de produção.

    O `prompt` é EXATAMENTE `build_task_prompt` — a mesma função que o filtro, o
    eval e o `hive` usam. Se o treino visse um pedido diferente do de produção, a
    abelha aprenderia a responder a uma pergunta que ninguém faz. (Foi assim que
    a agêntica perdeu 45,8 pp: treinada com catálogo, servida sem.)

    A resposta é JSON compacto e com as chaves na ORDEM DO SCHEMA — formato
    estável ensina formato estável; ordem aleatória ensinaria ruído.
    """
    sch = schemas[row["schema"]]
    obj = {k: row["extracao"][k] for k in sch["fields"] if k in row["extracao"]
           and row["extracao"][k] is not None}
    return {
        "prompt": [{"role": "user", "content": build_task_prompt(sch, row["documento"])}],
        "completion": [{"role": "assistant",
                        "content": json.dumps(obj, ensure_ascii=False)}],
        "schema": row["schema"],
        "lang": row["lang"],
    }


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--in-hard", type=Path, default=IN_HARD)
    ap.add_argument("--in-easy", type=Path, default=IN_EASY)
    ap.add_argument("--holdout", type=int, default=140,
                    help="itens difíceis reservados p/ avaliar o ganho (estratificado por idioma)")
    ap.add_argument("--easy-eval", type=int, default=140,
                    help="itens fáceis reservados p/ medir REGRESSAO")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    ensure_dirs()
    schemas = load_schemas()
    hard = list(read_jsonl(args.in_hard))
    easy = list(read_jsonl(args.in_easy))
    if not hard:
        print(f"ERRO: {args.in_hard} vazio. Rode o 12_filter_extraction antes.", file=sys.stderr)
        return 1

    # ⭐ Split por HASH DO DOCUMENTO, estratificado por idioma. Ver o docstring:
    # a versão que embaralhava e cortava os primeiros N dependia do TAMANHO do
    # pool, e o gate não é bit-reproduzível — isso já custou um retreino.
    por_lang: dict[str, list] = defaultdict(list)
    for r in hard:
        por_lang[r["lang"]].append(r)

    evalset, treino = [], []
    for lang, rows in por_lang.items():
        cota = min(len(rows), max(1, args.holdout // max(1, len(por_lang))))
        # corte no espaço do hash que rende ~cota itens deste idioma
        corte = round(1000 * cota / max(1, len(rows)))
        eval_lang = [r for r in rows if bucket(r["documento"], args.seed) < corte]
        # ajuste fino determinístico: se o hash rendeu demais/de menos, corrige
        # pela ORDEM DO HASH (estável), nunca por shuffle
        eval_lang.sort(key=lambda r: bucket(r["documento"], args.seed))
        eval_lang = eval_lang[:cota]
        marcados = {id(r) for r in eval_lang}
        evalset += eval_lang
        treino += [r for r in rows if id(r) not in marcados]

    easy_eval = sorted(easy, key=lambda r: bucket(r["documento"], args.seed))[: args.easy_eval]
    treino.sort(key=lambda r: bucket(r["documento"], args.seed + 1))   # ordem estável

    write_jsonl(OUT_TRAIN, (to_pc(r, schemas) for r in treino))
    write_jsonl(OUT_EVAL, (to_pc(r, schemas) for r in evalset))
    write_jsonl(OUT_EASY, (to_pc(r, schemas) for r in easy_eval))

    def dist(rows):
        return dict(sorted(Counter(r["lang"] for r in rows).items()))

    print(f"difíceis lidos : {len(hard)}   fáceis lidos: {len(easy)}")
    print()
    print(f"TREINO         : {len(treino):>4}  {dist(treino)}  → {OUT_TRAIN.name}")
    print(f"holdout difícil: {len(evalset):>4}  {dist(evalset)}  → {OUT_EVAL.name}")
    print(f"holdout fácil  : {len(easy_eval):>4}  {dist(easy_eval)}  → {OUT_EASY.name}")
    print()

    # sanidade contra o erro da coder: nenhum documento do holdout no treino
    docs_treino = {r["documento"] for r in treino}
    vaz_hard = sum(1 for r in evalset if r["documento"] in docs_treino)
    vaz_easy = sum(1 for r in easy_eval if r["documento"] in docs_treino)
    print(f"⭐ contaminação: holdout difícil {vaz_hard}/{len(evalset)} · "
          f"fácil {vaz_easy}/{len(easy_eval)}  "
          f"{'✅ limpo' if not (vaz_hard or vaz_easy) else '⚠️ VAZOU'}")

    ex = to_pc(treino[0], schemas)
    p, c = ex["prompt"][0]["content"], ex["completion"][0]["content"]
    print(f"\nexemplo — prompt {len(p)} chars / completion {len(c)} chars "
          f"({len(c) / (len(p) + len(c)):.0%} do exemplo é o alvo da loss)")
    print(f"  ...{p[-90:].strip()}")
    print(f"  → {c[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
