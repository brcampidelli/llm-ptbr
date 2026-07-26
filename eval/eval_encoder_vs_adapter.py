"""ENCODER × ADAPTER nos campos EXTRATIVOS — a objeção de 2026-07-25, decidida.

A objeção registrada contra o próprio plano: *"extração é tarefa de encoder; um
modelo de 110–300M faz em CPU por ~1/40 do custo do 4B. Nunca medimos, e se o
encoder ganhar eu estaria defendendo elegância arquitetural contra economia real."*

⚠️ COMPARAÇÃO JUSTA, e é aqui que ela pode ser fraudada sem má intenção:
  • MESMO holdout (mesmo `bucket()` por sha1 do documento);
  • MESMOS campos — só os `grounded` de tipo texto, que é o escopo da objeção. O
    adapter é avaliado APENAS nesses campos, ignorando enum/data/número, mesmo
    sabendo que ele acerta esses também. Cobrar do encoder o que ele não foi feito
    para fazer daria um resultado favorável a nós e sem valor.
  • MESMA métrica: o valor extraído bate com a referência (`norm_texto`).

Reporta também o custo real: parâmetros, latência por documento e se roda em CPU.
Um encoder que empata em qualidade e roda 15× mais barato GANHA a decisão de
produto, mesmo perdendo em elegância.

Uso (na L4):
    python eval/eval_encoder_vs_adapter.py --peft /content/bee-extracao \\
        --encoder /content/bee-encoder-ner
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402
from schema_check import (avaliar, build_task_prompt, load_schemas,  # noqa: E402
                          norm_texto)

EVAL_NER = ROOT / "data" / "processed" / "encoder_ner.eval.jsonl"
NOMES = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês"}


def campos_extrativos(schema: dict) -> list[str]:
    """Os campos que a objeção cobre: `grounded` E de tipo texto."""
    return [k for k, s in schema["fields"].items()
            if s.get("grounded") and s["type"] in ("string", "array[string]")]


def bio_para_campos(tokens: list[str], labels: list[str]) -> dict[str, list[str]]:
    """Decodifica BIO de volta para {campo: [valores]}."""
    out: dict[str, list[str]] = defaultdict(list)
    atual, buf = None, []
    for tk, lb in zip(tokens, labels):
        if lb.startswith("B-"):
            if atual:
                out[atual].append(" ".join(buf))
            atual, buf = lb[2:], [tk]
        elif lb.startswith("I-") and atual == lb[2:]:
            buf.append(tk)
        else:
            if atual:
                out[atual].append(" ".join(buf))
            atual, buf = None, []
    if atual:
        out[atual].append(" ".join(buf))
    return dict(out)


def acerta(got, ref) -> bool:
    """Comparação por conjunto normalizado — mesma régua para os dois lados."""
    g = {norm_texto(x) for x in (got if isinstance(got, list) else [got]) if str(x).strip()}
    r = {norm_texto(x) for x in (ref if isinstance(ref, list) else [ref]) if str(x).strip()}
    return bool(r) and g == r


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", required=True)
    ap.add_argument("--encoder", required=True)
    ap.add_argument("--ner-eval", type=Path, default=EVAL_NER)
    ap.add_argument("--raw", type=Path,
                    default=ROOT / "data" / "raw" / "extraction_hard.jsonl")
    ap.add_argument("--raw-easy", type=Path,
                    default=ROOT / "data" / "raw" / "extraction_easy.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--max-new", type=int, default=400)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    schemas = load_schemas()
    ner = list(read_jsonl(args.ner_eval))
    if args.limit:
        ner = ner[: args.limit]
    # casa cada item do NER com o documento/extração originais pelos tokens
    brutos = {}
    for r in list(read_jsonl(args.raw)) + list(read_jsonl(args.raw_easy)):
        brutos[" ".join(r["documento"].split())] = r
    itens = []
    for r in ner:
        chave = " ".join(" ".join(r["tokens"]).split())
        # busca tolerante: os tokens do NER vêm de regex, não do texto cru
        achou = next((v for k, v in brutos.items()
                      if norm_texto(k).replace(" ", "")[:120]
                      == norm_texto(chave).replace(" ", "")[:120]), None)
        if achou:
            itens.append((r, achou))
    print(f"holdout NER : {len(ner)} | casados com o bruto: {len(itens)}")
    if len(itens) < len(ner) * 0.8:
        print("⚠️ casamento baixo — a comparação ficaria enviesada. Abortando.",
              file=sys.stderr)
        return 1

    import torch
    from transformers import (AutoModelForCausalLM, AutoModelForTokenClassification,
                              AutoTokenizer, BitsAndBytesConfig)

    # ---------- encoder ----------
    etok = AutoTokenizer.from_pretrained(args.encoder, add_prefix_space=True)
    emod = AutoModelForTokenClassification.from_pretrained(args.encoder)
    n_enc = sum(p.numel() for p in emod.parameters())
    emod.eval()
    dev_enc = "cuda" if torch.cuda.is_available() else "cpu"
    emod.to(dev_enc)

    def encoder_extrai(r) -> dict:
        enc = etok(r["tokens"], is_split_into_words=True, truncation=True,
                   max_length=512, return_tensors="pt").to(dev_enc)
        with torch.no_grad():
            log = emod(**enc).logits[0].argmax(-1).tolist()
        wids = enc.word_ids(0)
        labs, visto = ["O"] * len(r["tokens"]), set()
        for pos, w in enumerate(wids):
            if w is not None and w not in visto:
                visto.add(w)
                labs[w] = emod.config.id2label[log[pos]]
        return bio_para_campos(r["tokens"], labs)

    t0 = time.time()
    saidas_enc = [encoder_extrai(r) for r, _ in itens]
    lat_enc = (time.time() - t0) / max(1, len(itens))

    # ---------- adapter ----------
    kw = {"dtype": torch.bfloat16, "device_map": {"": 0},
          "quantization_config": BitsAndBytesConfig(
              load_in_4bit=True, bnb_4bit_quant_type="nf4",
              bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)}
    qtok = AutoTokenizer.from_pretrained(args.model)
    if qtok.pad_token is None:
        qtok.pad_token = qtok.eos_token
    qtok.padding_side = "left"
    qmod = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    from peft import PeftModel
    qmod = PeftModel.from_pretrained(qmod, args.peft)
    qmod.eval()
    n_dec = sum(p.numel() for p in qmod.parameters())

    t0 = time.time()
    saidas_dec = []
    for i in range(0, len(itens), args.batch_size):
        lote = itens[i: i + args.batch_size]
        textos = []
        for _, b in lote:
            msgs = [{"role": "user",
                     "content": build_task_prompt(schemas[b["schema"]], b["documento"])}]
            try:
                textos.append(qtok.apply_chat_template(msgs, add_generation_prompt=True,
                                                       enable_thinking=False, tokenize=False))
            except TypeError:
                textos.append(qtok.apply_chat_template(msgs, add_generation_prompt=True,
                                                       tokenize=False))
        enc = qtok(textos, return_tensors="pt", padding=True, truncation=True,
                   max_length=2048).to("cuda")
        with torch.no_grad():
            out = qmod.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                                pad_token_id=qtok.eos_token_id)
        plen = enc["input_ids"].shape[1]
        for o, (_, b) in zip(out, lote):
            txt = strip_think(qtok.decode(o[plen:], skip_special_tokens=True).strip())[0]
            saidas_dec.append(avaliar(txt, schemas[b["schema"]], b["documento"])["obj"] or {})
        print(f"  adapter {min(i+args.batch_size, len(itens))}/{len(itens)}", flush=True)
    lat_dec = (time.time() - t0) / max(1, len(itens))

    # ---------- comparação, SÓ nos campos extrativos ----------
    acc = {"encoder": defaultdict(lambda: [0, 0]), "ADAPTER": defaultdict(lambda: [0, 0])}
    for (r, b), se, sd in zip(itens, saidas_enc, saidas_dec):
        sch = schemas[b["schema"]]
        for campo in campos_extrativos(sch):
            ref = b["extracao"].get(campo)
            if ref is None:
                continue
            for nome, saida in (("encoder", se), ("ADAPTER", sd)):
                a = acc[nome][r["lang"]]
                a[1] += 1
                a[0] += int(acerta(saida.get(campo, []), ref))

    print("\n" + "=" * 74)
    print("⭐ ENCODER × ADAPTER — só campos EXTRATIVOS (o escopo da objeção)")
    print("=" * 74)
    print(f"{'idioma':<12} {'encoder':>14} {'ADAPTER':>14}   leitura")
    print("-" * 74)
    tot = {"encoder": [0, 0], "ADAPTER": [0, 0]}
    for lang in sorted(acc["ADAPTER"]):
        e, d = acc["encoder"][lang], acc["ADAPTER"][lang]
        for k, v in (("encoder", e), ("ADAPTER", d)):
            tot[k][0] += v[0]
            tot[k][1] += v[1]
        pe, pd = e[0] / max(1, e[1]), d[0] / max(1, d[1])
        leitura = ("ADAPTER melhor" if pd > pe + 0.02 else
                   "⚠️ ENCODER melhor" if pe > pd + 0.02 else "empate")
        print(f"{NOMES.get(lang, lang):<12} {e[0]:>5}/{e[1]:<7} {d[0]:>5}/{d[1]:<7}   {leitura}")
    print("-" * 74)
    pe = tot["encoder"][0] / max(1, tot["encoder"][1])
    pd = tot["ADAPTER"][0] / max(1, tot["ADAPTER"][1])
    print(f"{'TOTAL':<12} {pe:>13.1%} {pd:>13.1%}   delta {pd-pe:+.1%}")

    print(f"\nCUSTO:")
    print(f"  encoder : {n_enc/1e6:>6.0f}M params · {lat_enc*1000:>6.0f} ms/doc")
    print(f"  ADAPTER : {n_dec/1e6:>6.0f}M params · {lat_dec*1000:>6.0f} ms/doc"
          f"  ({n_dec/n_enc:.0f}× mais parâmetros, {lat_dec/max(1e-9,lat_enc):.0f}× mais lento)")

    print("\n⭐ VEREDITO DA OBJEÇÃO:")
    if pe > pd + 0.02:
        print("  🔴 o ENCODER GANHA nos campos extrativos, sendo muito menor e mais rápido.")
        print("     A comeia deveria ter as DUAS rotas: encoder para extrair, decoder")
        print("     para inferir. Eu estava defendendo elegância contra economia.")
    elif pd > pe + 0.02:
        print("  ✅ o ADAPTER ganha até no terreno do encoder. A objeção não se sustenta")
        print("     nesta tarefa — schema aberto num decoder vale o custo.")
    else:
        print("  ⚠️ EMPATE. Empate favorece o ENCODER na decisão de produto: mesma")
        print("     qualidade por uma fração do custo. O decoder só se justifica pelo")
        print("     schema aberto (campo novo sem retreinar), que é real mas precisa")
        print("     ser cobrado como requisito, não assumido como vantagem.")

    if args.tag:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"encoder_vs_adapter_{args.tag}.json"
        p.write_text(json.dumps(
            {"encoder": {"params_M": n_enc / 1e6, "ms_doc": lat_enc * 1000, "acc": pe},
             "adapter": {"params_M": n_dec / 1e6, "ms_doc": lat_dec * 1000, "acc": pd},
             "por_lang": {k: dict(v) for k, v in acc.items()}},
            indent=2, ensure_ascii=False, default=list), encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
