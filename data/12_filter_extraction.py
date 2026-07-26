"""Fase 2 (dados) — Filtro "O BASE ERRA" para a abelha de extração.

⭐ A REGRA, já validada duas vezes neste projeto:

    manter o item  ⟺  a extração do professor PASSA  E  o base FALHA

Sem isso o dataset fica cheio de coisa que o modelo já sabe, e treinar não ensina
nada — foi literalmente o que aconteceu com o SFT generalista PT-BR (0 de 7 ganhos
a n=300). Collab-RAG (arXiv 2504.04915) formaliza: descartar itens em que todas as
amostras têm a mesma recompensa, porque não carregam sinal. Na coder essa regra
transformou "ganho marginal" em +40 pp.

⚠️ MESMO PEDIDO DO EVAL E DA PRODUÇÃO. O prompt vem de
`schema_check.build_task_prompt` — a mesma função que o eval e o `hive` usam. Se o
filtro usasse prompt diferente, "o base erra aqui" não significaria "o base erra
lá", e a dificuldade medida não transferiria. Este projeto já pagou por essa lição
duas vezes: a `agentica` era servida com um prompt diferente do de treino (custou
45,8 pp escondidos) e o holdout da `coder` saiu contaminado por eu ter cortado o
arquivo antes do shuffle.

⚠️ AVALIAÇÃO É TOLERANTE (`strict=False`), aceitação de treino é ESTRITA. Aqui
medimos o BASE, então a pergunta é "ele pegou o valor certo?", não "formatou como
eu queria". Cobrar formato do base o faria parecer pior do que é, e nós
manteríamos itens fáceis achando que são difíceis.

O QUE CONTA COMO ERRO DO BASE (qualquer um destes):
  - não sai JSON;
  - sai fora do schema (obrigatório ausente, tipo, enum, campo inventado);
  - ⭐ alucina (valor `grounded` que não está no documento);
  - acerta menos que `--min-campos` dos campos da referência.

⚡ GERAÇÃO EM LOTE: sem isso é inviável. A ~8 s/item, 900 itens levariam 2 h.

Uso (na L4 — precisa de GPU):
    python data/12_filter_extraction.py --limit 40 --batch-size 8    # piloto
    python data/12_filter_extraction.py --batch-size 8               # tudo

Saída: data/raw/extraction_hard.jsonl  (o base errou → TREINA)
       data/raw/extraction_easy.jsonl  (o base acertou → não treina, mas é o
                                        HOLDOUT que detecta dano colateral)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAW_DIR  # noqa: E402
from common import read_jsonl  # noqa: E402
from schema_check import (avaliar, build_task_prompt, campos_certos,  # noqa: E402
                          load_schemas)

IN = RAW_DIR / "extraction_tasks.jsonl"
OUT_HARD = RAW_DIR / "extraction_hard.jsonl"
OUT_EASY = RAW_DIR / "extraction_easy.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--tasks", type=Path, default=IN)
    ap.add_argument("--limit", type=int, default=0,
                    help="⚠️ pega os N PRIMEIROS do arquivo BRUTO — use so para piloto. "
                         "Nao serve de holdout: o 05_build_splits embaralha antes de "
                         "separar, e foi assim que o eval da coder saiu contaminado.")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=400)
    ap.add_argument("--min-campos", type=float, default=1.0,
                    help="fracao dos campos da referencia que o base precisa acertar "
                         "para o item contar como FACIL. 1.0 = tem que acertar todos.")
    ap.add_argument("--no-4bit", action="store_true")
    args = ap.parse_args()

    schemas = load_schemas()
    itens = list(read_jsonl(args.tasks))
    if not itens:
        print(f"ERRO: {args.tasks} vazio ou inexistente.", file=sys.stderr)
        return 1
    if args.limit:
        itens = itens[: args.limit]

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kwargs: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)

    print(f"modelo    : {args.model} (BASE, sem adapter)")
    print(f"itens     : {len(itens)} | lote: {args.batch_size}")
    print(f"criterio  : base FALHA => treina | acerta >= {args.min_campos:.0%} dos campos => facil")
    print(f"saidas    : {OUT_HARD.name} (treina) / {OUT_EASY.name} (holdout)\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"          # OBRIGATORIO para geracao em lote
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    model.eval()

    def gen_batch(prompts: list[str]) -> list[str]:
        """⚠️ SEM system prompt — igual ao build_task_prompt/eval/produção."""
        textos = []
        for p in prompts:
            msgs = [{"role": "user", "content": p}]
            try:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                            enable_thinking=False, tokenize=False)
            except TypeError:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
            textos.append(s)
        enc = tok(textos, return_tensors="pt", padding=True, truncation=True,
                  max_length=2048).to("cuda")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        plen = enc["input_ids"].shape[1]
        return [tok.decode(o[plen:], skip_special_tokens=True).strip() for o in out]

    n_hard = n_easy = 0
    motivos: Counter[str] = Counter()
    por_lang: dict[str, Counter] = {}
    fh = OUT_HARD.open("w", encoding="utf-8")
    fe = OUT_EASY.open("w", encoding="utf-8")
    try:
        for i in range(0, len(itens), args.batch_size):
            lote = itens[i: i + args.batch_size]
            prompts = [build_task_prompt(schemas[r["schema"]], r["documento"]) for r in lote]
            try:
                saidas = gen_batch(prompts)
            except Exception as e:
                print(f"  [lote {i} falhou: {type(e).__name__}] tratando como difícil",
                      file=sys.stderr)
                saidas = [""] * len(lote)

            for r, saida in zip(lote, saidas):
                sch = schemas[r["schema"]]
                # ⚠️ tolerante: medindo o BASE, a pergunta e o VALOR, nao o formato
                ver = avaliar(saida, sch, r["documento"], strict=False)
                acertos, total = campos_certos(ver["obj"], r["extracao"], sch)
                frac = acertos / total if total else 0.0

                if not ver["json_ok"]:
                    motivo = "sem_json"
                elif not ver["conforme"]:
                    motivo = "fora_do_schema"
                elif not ver["grounded"]:
                    motivo = "ALUCINOU"
                elif frac < args.min_campos:
                    motivo = "campo_errado"
                else:
                    motivo = None

                lang = r.get("lang", "?")
                por_lang.setdefault(lang, Counter())["n"] += 1
                if motivo:
                    motivos[motivo] += 1
                    por_lang[lang]["hard"] += 1
                    n_hard += 1
                    fh.write(json.dumps({**r, "base_motivo": motivo,
                                         "base_frac_campos": round(frac, 3)},
                                        ensure_ascii=False) + "\n")
                else:
                    n_easy += 1
                    fe.write(json.dumps(r, ensure_ascii=False) + "\n")

            feito = min(i + args.batch_size, len(itens))
            print(f"  {feito}/{len(itens)} | difíceis {n_hard} · fáceis {n_easy}", flush=True)
    finally:
        fh.close()
        fe.close()

    tot = n_hard + n_easy
    print("\n" + "=" * 68)
    print(f"o base ERROU  : {n_hard}/{tot} = {n_hard / tot:.1%}  → TREINA nestes")
    print(f"o base acertou: {n_easy}/{tot} = {n_easy / tot:.1%}  → holdout de nao-regressao")
    if motivos:
        print("\ncomo o base errou:")
        for m, c in motivos.most_common():
            print(f"  {c:>4}  ({c / max(1, n_hard):.0%})  {m}")
    if len(por_lang) > 1:
        print("\ndificuldade por idioma (base errou / total):")
        for lang, c in sorted(por_lang.items()):
            print(f"  {lang}: {c['hard']}/{c['n']} = {c['hard'] / max(1, c['n']):.0%}")
    print("=" * 68)
    print("\n⭐ LEITURA DO GATE:")
    if n_hard / max(1, tot) < 0.15:
        print("  o base ja resolve quase tudo — treinar aqui provavelmente NAO rende.")
        print("  Antes de gastar GPU: schemas mais difíceis, ou desistir desta abelha.")
    else:
        print(f"  ha {n_hard} itens de sinal real. Vale treinar.")
    print(f"\n{OUT_HARD}\n{OUT_EASY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
