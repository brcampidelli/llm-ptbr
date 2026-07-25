"""Avaliacao da ABELHA AGENTICA — a regua certa para esta abelha.

Por que nao usar o run_baseline.py: os benchmarks PT-BR sao MULTIPLA ESCOLHA e
medem conhecimento. Tool-use e GERACAO com formato rigido e uma DECISAO (usar ou
nao usar ferramenta). Multipla escolha nao mede nada disso — foi essa regua
errada que deixou o SFT generalista "sem resultado" a n=300.

Mede 4 coisas no holdout (data/processed/sft_agentic.eval.jsonl):

  1. JSON VALIDO       — dos casos que pedem ferramenta, quantos saem como JSON
                         parseavel e valido contra o catalogo (reusa o validador
                         do data/07_distill_agentic.py: ferramenta existe, args
                         obrigatorios presentes, nenhum arg desconhecido).
  2. FERRAMENTA CERTA  — escolheu a MESMA ferramenta da referencia.
  3. OVER-CALLING      — ⚠️ a falha classica: caso que NAO precisa de ferramenta
                         respondido com JSON. E o risco de colapso de modo (a
                         abelha vira "so JSON" e perde a resposta em texto).
  4. UNDER-CALLING     — caso que precisa de ferramenta respondido em texto.

Compare o base contra o adapter — e o teste "cada abelha bate o base NA TAREFA
DELA" do plano.

Uso (na L4):
    python eval/eval_agentic.py                                    # base (referencia)
    python eval/eval_agentic.py --peft /content/drive/MyDrive/qwen35-4b-agentica
    python eval/eval_agentic.py --peft ... --limit 60              # amostra rapida
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402

# Reusa o catalogo E o validador da destilacao — uma so fonte de verdade.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", ROOT / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

DEFAULT_EVAL = ROOT / "data" / "processed" / "sft_agentic.eval.jsonl"


def get_messages(row: dict) -> list[dict]:
    """Aceita os DOIS formatos de split: {messages} e {prompt, completion}.

    O holdout agentico usa prompt/completion (para o TRL mascarar a loss do
    prompt no treino — ver data/05_build_splits.py). Aqui so precisamos das
    mensagens em ordem, então concatenamos.
    """
    if row.get("messages"):
        return row["messages"]
    return list(row.get("prompt") or []) + list(row.get("completion") or [])


def split_example(row: dict) -> tuple[str | None, str, str, str]:
    """(system, user, referencia, kind) a partir do formato chat."""
    system = user = ref = None
    for m in get_messages(row):
        if m["role"] == "system":
            system = m["content"]
        elif m["role"] == "user":
            user = m["content"]
        elif m["role"] == "assistant":
            ref = m["content"]
    return system, user or "", ref or "", row.get("kind", "?")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", default=None, help="adapter da abelha agentica")
    ap.add_argument("--data", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new", type=int, default=200)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    rows = [r for r in read_jsonl(args.data) if get_messages(r)]
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print(f"ERRO: nenhum exemplo em {args.data}", file=sys.stderr)
        return 1

    tools = _d7.load_tools()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kwargs: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
        )
    print(f"modelo : {args.model}")
    print(f"adapter: {args.peft or '(base, sem adapter)'}")
    print(f"holdout: {len(rows)} exemplos de {args.data.name}\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    if args.peft:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    # contadores
    n_tool = n_text = 0
    json_ok = tool_right = 0
    over_call = under_call = 0
    falhas: list[tuple[str, str, str]] = []

    for i, row in enumerate(rows, 1):
        system, user, ref, kind = split_example(row)
        msgs = ([{"role": "system", "content": system}] if system else []) \
            + [{"role": "user", "content": user}]
        tpl: dict = {"add_generation_prompt": True, "return_tensors": "pt", "return_dict": True}
        try:
            enc = tok.apply_chat_template(msgs, enable_thinking=False, **tpl)
        except TypeError:
            enc = tok.apply_chat_template(msgs, **tpl)
        inputs = {k: v.to("cuda") for k, v in dict(enc).items() if hasattr(v, "to")}
        plen = inputs["input_ids"].shape[1]
        with torch.no_grad():
            gen = model.generate(**inputs, max_new_tokens=args.max_new, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        raw = tok.decode(gen[0][plen:], skip_special_tokens=True).strip()
        pred, _ = strip_think(raw)

        pred_obj = _d7.extract_json(pred)
        ref_obj = _d7.extract_json(ref)

        if kind == "tool_call":
            n_tool += 1
            if pred_obj is None:
                under_call += 1
                falhas.append(("under-call", user[:60], pred[:60]))
            else:
                if _d7.validate_call(pred_obj, tools) is None:
                    json_ok += 1
                else:
                    falhas.append(("json invalido", user[:60], pred[:60]))
                if ref_obj and pred_obj.get("tool") == ref_obj.get("tool"):
                    tool_right += 1
                elif ref_obj:
                    falhas.append((f"tool errada (ref={ref_obj.get('tool')})",
                                   user[:60], str(pred_obj.get("tool"))[:40]))
        else:                                  # kind == "text"
            n_text += 1
            if pred_obj is not None:
                over_call += 1
                falhas.append(("OVER-CALL", user[:60], pred[:60]))

        if i % 20 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)}", flush=True)

    def pct(a: int, b: int) -> str:
        return f"{a}/{b} = {a/b:.1%}" if b else "n/a"

    print("\n" + "=" * 66)
    print(f"{'casos que EXIGEM ferramenta':<34} {n_tool}")
    print(f"  JSON valido (catalogo)           {pct(json_ok, n_tool)}")
    print(f"  ferramenta CERTA (= referencia)  {pct(tool_right, n_tool)}")
    print(f"  under-calling (respondeu texto)  {pct(under_call, n_tool)}")
    print("-" * 66)
    print(f"{'casos que NAO exigem ferramenta':<34} {n_text}")
    print(f"  ⚠️ OVER-CALLING (veio JSON)       {pct(over_call, n_text)}")
    print("=" * 66)
    score = (json_ok + tool_right + (n_text - over_call)) / max(1, 2 * n_tool + n_text)
    print(f"score composto: {score:.1%}  (JSON valido + tool certa + nao-over-call)")

    if falhas:
        print(f"\nprimeiras {min(8, len(falhas))} falhas:")
        for tipo, q, p in falhas[:8]:
            print(f"  [{tipo}] q: {q}")
            print(f"       -> {p}")

    if args.tag:
        outdir = ROOT / "eval" / "results"
        outdir.mkdir(parents=True, exist_ok=True)
        payload = {
            "tag": args.tag, "model": args.model, "peft": args.peft,
            "n_tool": n_tool, "n_text": n_text, "json_ok": json_ok,
            "tool_right": tool_right, "over_call": over_call,
            "under_call": under_call, "score": score,
        }
        p = outdir / f"agentic_{args.tag}.json"
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
