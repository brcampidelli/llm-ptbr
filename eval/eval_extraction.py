"""Avaliação da ABELHA DE EXTRAÇÃO — a régua que o treino não dá.

Por que não confiar na métrica de treino: a token accuracy fechou em ~98%, mas o
alvo é um JSON curto onde boa parte dos tokens são as CHAVES DO SCHEMA, que são
fixas e triviais de prever. Acertar `"valor_total":` não é a habilidade que
queremos; acertar **1240.0 em vez de 9999.0** é. Aqui medimos o valor.

Mede 5 coisas, e as duas últimas existem porque os números anteriores mentiriam
sem elas:

  1. CAMPOS CERTOS       — acerto campo a campo contra a referência, tolerante a
                           FORMATO (1.240,00 == 1240.0; 12/03/2026 == 2026-03-12).
                           É a métrica principal.
  2. CONFORME            — obrigatórios, tipos, enum, campo fora do schema.
  3. ⭐ ALUCINAÇÃO        — valor `grounded` que não existe no documento. É 6% das
                           falhas do base e o erro mais perigoso em produção,
                           porque sai JSON bonito com dado inventado dentro.
  4. ⚠️ CAMPO ESQUECIDO   — a referência tem, o modelo omitiu. EXISTE porque o
                           dataset ficou enviesado para extrações esparsas (46% dos
                           documentos com opcional ausente, contra os 35% pedidos —
                           efeito de seleção do filtro). Sem separar este erro,
                           **sub-extração passaria por virtude**: um modelo que
                           omite tudo nunca alucina e teria "0% de alucinação".
  5. CAMPO EXTRA         — o modelo preencheu o que a referência deixou de fora.
                           Nem sempre é erro (o professor pode ter esquecido), por
                           isso é reportado, não penalizado.

Roda nos DOIS holdouts, e o segundo é o que pega dano colateral:
  --eval  sft_extraction.eval.jsonl   difícil (o base erra) → mede o GANHO
  --easy  sft_extraction.easy.jsonl   fácil (o base acerta) → mede a REGRESSÃO
Foi um holdout fácil que expôs os −17,5 pp de dano colateral da coder.

⚠️ MESMA RÉGUA: uma carga do modelo, adapter ligado = abelha, `disable_adapter()`
= base. Mesmo prompt (o de produção, embutido no dataset), mesma decodificação.

Uso (na L4):
    python eval/eval_extraction.py --peft /content/drive/MyDrive/qwen35-4b-extracao
    python eval/eval_extraction.py --peft ... --limit 40      # piloto
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402
from schema_check import (avaliar, campos_certos, load_schemas,  # noqa: E402
                          norm_data, norm_numero, norm_texto)

EVAL_HARD = ROOT / "data" / "processed" / "sft_extraction.eval.jsonl"
EVAL_EASY = ROOT / "data" / "processed" / "sft_extraction.easy.jsonl"
NOMES = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês"}


def novo() -> dict:
    # ⚠️ `alucinou` tem denominador PRÓPRIO (`aluc_n`): só conta entre as saídas que
    # chegaram a produzir um JSON conforme. Sem isso, "não saiu JSON" entraria como
    # alucinação — e não sair JSON não é inventar dado, é outra falha. Misturar as
    # duas inflaria a taxa de alucinação justamente no modelo que responde pior.
    return {"n": 0, "json_ok": 0, "conforme": 0, "alucinou": 0, "aluc_n": 0,
            "acertos": 0, "campos": 0, "esquecidos": 0, "extras": 0, "perfeito": 0}


def medir(saida: str, ref: dict, schema: dict, documento: str, acc: dict) -> None:
    """Acumula as 5 métricas de uma resposta em `acc`."""
    acc["n"] += 1
    ver = avaliar(saida, schema, documento, strict=False)   # tolerante: medindo VALOR
    obj = ver["obj"] or {}
    acc["json_ok"] += int(ver["json_ok"])
    acc["conforme"] += int(ver["conforme"])
    if ver["json_ok"] and ver["conforme"]:      # só quem chegou a produzir campos
        acc["aluc_n"] += 1
        acc["alucinou"] += int(not ver["grounded"])

    a, t = campos_certos(obj, ref, schema)
    acc["acertos"] += a
    acc["campos"] += t

    # ⚠️ separar sub-extração de alucinação: sem isto, omitir tudo pareceria virtude
    presentes_ref = {k for k in schema["fields"] if ref.get(k) is not None}
    presentes_mod = {k for k in schema["fields"] if obj.get(k) is not None}
    acc["esquecidos"] += len(presentes_ref - presentes_mod)
    acc["extras"] += len(presentes_mod - presentes_ref)
    acc["perfeito"] += int(ver["conforme"] and ver["grounded"] and a == t and t > 0)


def linha(rot: str, d: dict) -> str:
    n = max(1, d["n"])
    c = max(1, d["campos"])
    an = max(1, d["aluc_n"])
    return (f"{rot:<10} {d['perfeito']:>3}/{d['n']:<4} {d['perfeito']/n:>6.1%}   "
            f"{d['acertos']/c:>6.1%}   {d['conforme']/n:>6.1%}  "
            f"{d['alucinou']/an:>6.1%}   {d['esquecidos']:>4}  {d['extras']:>4}")


def cabecalho() -> None:
    print(f"{'':<10} {'perfeitos':>12}   {'campos':>6}   {'conf':>6}  "
          f"{'ALUCIN':>6}   {'esq':>4}  {'extra':>4}")
    print("-" * 72)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", required=True)
    ap.add_argument("--eval", type=Path, default=EVAL_HARD)
    ap.add_argument("--easy", type=Path, default=EVAL_EASY)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--max-new", type=int, default=400)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    schemas = load_schemas()
    conjuntos = {}
    for rot, path in (("DIFÍCIL", args.eval), ("fácil", args.easy)):
        if path and Path(path).exists():
            rows = list(read_jsonl(path))
            conjuntos[rot] = rows[: args.limit] if args.limit else rows
    if not conjuntos:
        print("ERRO: nenhum holdout encontrado.", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kw: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)

    print(f"adapter : {args.peft}")
    for rot, rows in conjuntos.items():
        print(f"holdout {rot:<8}: {len(rows)} itens")
    print()

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"                 # OBRIGATORIO para lote
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    def gen(prompts: list[str]) -> list[str]:
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
        return [strip_think(tok.decode(o[plen:], skip_special_tokens=True).strip())[0]
                for o in out]

    resultado: dict = {}
    for rot, rows in conjuntos.items():
        tot = {"base": novo(), "adapter": novo()}
        por_lang = {"base": defaultdict(novo), "adapter": defaultdict(novo)}
        feito = 0
        for i in range(0, len(rows), args.batch_size):
            lote = rows[i: i + args.batch_size]
            prompts = [r["prompt"][0]["content"] for r in lote]
            refs = [json.loads(r["completion"][0]["content"]) for r in lote]
            # documento = o final do prompt depois de "DOCUMENTO:\n"
            docs = [p.split("DOCUMENTO:\n", 1)[-1] for p in prompts]

            saidas = {"adapter": gen(prompts)}
            with model.disable_adapter():
                saidas["base"] = gen(prompts)

            for nome, outs in saidas.items():
                for r, ref, doc, saida in zip(lote, refs, docs, outs):
                    sch = schemas[r["schema"]]
                    medir(saida, ref, sch, doc, tot[nome])
                    medir(saida, ref, sch, doc, por_lang[nome][r["lang"]])
            feito = min(i + args.batch_size, len(rows))
            print(f"  [{rot}] {feito}/{len(rows)}", flush=True)

        print("\n" + "=" * 72)
        print(f"⭐ HOLDOUT {rot}  ({len(rows)} itens)   "
              f"{'→ mede o GANHO' if rot == 'DIFÍCIL' else '→ mede a REGRESSÃO'}")
        print("=" * 72)
        cabecalho()
        print(linha("base", tot["base"]))
        print(linha("ADAPTER", tot["adapter"]))
        print("-" * 72)
        d = tot["adapter"]["perfeito"] / max(1, tot["adapter"]["n"]) - \
            tot["base"]["perfeito"] / max(1, tot["base"]["n"])
        dc = tot["adapter"]["acertos"] / max(1, tot["adapter"]["campos"]) - \
            tot["base"]["acertos"] / max(1, tot["base"]["campos"])
        sinal = "✅" if d > 0 else ("⚠️ REGRESSÃO" if d < 0 else "igual")
        print(f"delta perfeitos: {d:+.1%}   delta campos: {dc:+.1%}   {sinal}")

        print(f"\npor idioma (perfeitos base → adapter):")
        for lang in sorted(por_lang["adapter"]):
            b, a = por_lang["base"][lang], por_lang["adapter"][lang]
            pb, pa = b["perfeito"] / max(1, b["n"]), a["perfeito"] / max(1, a["n"])
            print(f"  {NOMES.get(lang, lang):<10} {pb:>6.1%} → {pa:>6.1%}  "
                  f"({a['perfeito']}/{a['n']})  {pa-pb:+.1%}")
        resultado[rot] = {"base": tot["base"], "adapter": tot["adapter"],
                          "por_lang": {k: dict(v) for k, v in por_lang["adapter"].items()}}

    print("\n" + "=" * 72)
    print("LEITURA: 'perfeitos' = conforme + sem alucinar + TODOS os campos certos.")
    print("'esq' alto com alucinação baixa = SUB-EXTRAÇÃO, não virtude — o modelo")
    print("estaria calando em vez de errar, e isso também é falha.")
    print("=" * 72)

    if args.tag:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"extraction_{args.tag}.json"
        p.write_text(json.dumps({"peft": args.peft, "resultado": resultado},
                                indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
