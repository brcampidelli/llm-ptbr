"""Baseline EXTERNO — a medição que faltava, e que decide se o projeto vale.

⚠️ POR QUE EXISTE. Até hoje **todo** número deste projeto tem a forma:

    adapter vs. o NOSSO PRÓPRIO base, em itens escolhidos porque o base erra neles

Isso é circular por construção. "+43 pp" mede recuperação sobre um ponto de
partida deliberadamente selecionado para falhar, e não responde à pergunta que
decide tudo: **o adapter ganha de alguém que não seja nós mesmos?**

Este script mede 4 concorrentes na MESMA régua, no MESMO holdout:

  1. base ZERO-SHOT        — o que já reportávamos (o piso artificial)
  2. base FEW-SHOT (k=3)   — ⭐ O CONCORRENTE QUE IMPORTA. Se o few-shot empatar
                             com o adapter, então não treinamos uma habilidade:
                             consertamos um prompt ruim com 32 min de GPU. Este
                             é o teste que separa "especialização" de "prompt".
  3. ADAPTER               — a nossa abelha
  4. PROFESSOR (opcional)  — modelo aberto via API. Dá o TETO prático da tarefa e
                             o custo por documento, que é o que decide se a
                             comeia é econômica ou só complexidade.

⚠️ Os exemplos do few-shot vêm do TREINO, nunca do holdout — senão o few-shot
estaria lendo a prova. Verificado em código (assert), não por disciplina.

Uso (na L4):
    python eval/eval_external.py --peft /content/qwen35-4b-extracao-v2
    python eval/eval_external.py --peft ... --com-professor     # + API (~US$0,30)
    python eval/eval_external.py --peft ... --limit 40          # piloto
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "eval"))
from common import read_jsonl, strip_think  # noqa: E402
from config import DEFAULT_TEACHER, assert_teacher_allowed  # noqa: E402
from schema_check import load_schemas  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("ev", ROOT / "eval" / "eval_extraction.py")
_ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ev)

EVAL_HARD = ROOT / "data" / "processed" / "sft_extraction.eval.jsonl"
TRAIN = ROOT / "data" / "processed" / "sft_extraction.jsonl"


def monta_fewshot(treino: list[dict], k: int, holdout_docs: set[str]) -> list[dict]:
    """k exemplos do TREINO, um por schema diferente, como turnos de chat.

    ⚠️ `assert` contra vazamento: se um exemplo do few-shot estivesse no holdout,
    o few-shot leria a prova e o experimento inteiro mediria a coisa errada. Este
    projeto já teve holdout contaminado uma vez (a coder, ~52 de 60); não é um
    risco teórico.
    """
    vistos, shots = set(), []
    for r in treino:
        if r["schema"] in vistos:
            continue
        doc = r["prompt"][0]["content"].split("DOCUMENTO:\n", 1)[-1]
        assert doc not in holdout_docs, "VAZAMENTO: exemplo do few-shot está no holdout"
        shots += [{"role": "user", "content": r["prompt"][0]["content"]},
                  {"role": "assistant", "content": r["completion"][0]["content"]}]
        vistos.add(r["schema"])
        if len(vistos) >= k:
            break
    return shots


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
    ap.add_argument("--train", type=Path, default=TRAIN)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--max-new", type=int, default=400)
    ap.add_argument("--shots", type=int, default=3)
    ap.add_argument("--com-professor", action="store_true",
                    help="mede tambem o professor aberto via API (custa centavos)")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    schemas = load_schemas()
    rows = list(read_jsonl(args.eval))
    treino = list(read_jsonl(args.train))
    if args.limit:
        rows = rows[: args.limit]
    holdout_docs = {r["prompt"][0]["content"].split("DOCUMENTO:\n", 1)[-1] for r in rows}
    shots = monta_fewshot(treino, args.shots, holdout_docs)

    key = None
    if args.com_professor:
        assert_teacher_allowed(args.teacher)          # REGRA DURA: professor aberto
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            print("ERRO: --com-professor exige OPENROUTER_API_KEY.", file=sys.stderr)
            return 1

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kw: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)

    print(f"holdout : {len(rows)} itens ({args.eval.name})")
    print(f"few-shot: {args.shots} exemplos do TREINO ({len(shots)//2} pares), "
          f"vazamento verificado ✅")
    print(f"adapter : {args.peft}")
    print(f"professor: {args.teacher if args.com_professor else '(desligado)'}\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    def gen(prompts: list[str], prefixo: list[dict] | None = None) -> list[str]:
        textos = []
        for p in prompts:
            msgs = (prefixo or []) + [{"role": "user", "content": p}]
            try:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                            enable_thinking=False, tokenize=False)
            except TypeError:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
            textos.append(s)
        enc = tok(textos, return_tensors="pt", padding=True, truncation=True,
                  max_length=4096).to("cuda")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        plen = enc["input_ids"].shape[1]
        return [strip_think(tok.decode(o[plen:], skip_special_tokens=True).strip())[0]
                for o in out]

    braços = ["base 0-shot", f"base {args.shots}-shot", "ADAPTER"]
    if args.com_professor:
        braços.append("professor")
    acc = {b: _ev.novo() for b in braços}

    for i in range(0, len(rows), args.batch_size):
        lote = rows[i: i + args.batch_size]
        prompts = [r["prompt"][0]["content"] for r in lote]
        refs = [json.loads(r["completion"][0]["content"]) for r in lote]
        docs = [p.split("DOCUMENTO:\n", 1)[-1] for p in prompts]

        saidas = {"ADAPTER": gen(prompts)}
        with model.disable_adapter():
            saidas["base 0-shot"] = gen(prompts)
            saidas[f"base {args.shots}-shot"] = gen(prompts, shots)

        if args.com_professor:
            from teacher_api import call_teacher
            outs = []
            for p in prompts:
                try:
                    outs.append(call_teacher(p, args.teacher, key, temperature=0.0,
                                             max_tokens=args.max_new))
                except Exception:
                    outs.append("")
            saidas["professor"] = outs

        for nome, outs in saidas.items():
            for r, ref, doc, saida in zip(lote, refs, docs, outs):
                _ev.medir(saida, ref, schemas[r["schema"]], doc, acc[nome])
        print(f"  {min(i + args.batch_size, len(rows))}/{len(rows)}", flush=True)

    print("\n" + "=" * 78)
    print("⭐ BASELINE EXTERNO — o adapter ganha de alguém que não seja nós mesmos?")
    print("=" * 78)
    _ev.cabecalho()
    for b in braços:
        print(_ev.linha(b, acc[b]))
    print("-" * 78)

    def perf(b):
        return acc[b]["perfeito"] / max(1, acc[b]["n"])

    fs = f"base {args.shots}-shot"
    d = perf("ADAPTER") - perf(fs)
    print(f"\n⭐ ADAPTER − FEW-SHOT: {d:+.1%}")
    if d > 0.05:
        print("   ✅ o adapter ensina algo que o prompt não alcança. A especialização vale.")
    elif d < -0.05:
        print("   🔴 o FEW-SHOT ganha. Treinamos para consertar prompt ruim — o adapter")
        print("      não se justifica nesta tarefa. Revisar antes de treinar mais abelhas.")
    else:
        print("   ⚠️ EMPATE TÉCNICO. O ganho reportado vinha em boa parte do prompt fraco,")
        print("      não da especialização. O adapter só se justifica por custo/latência —")
        print("      few-shot paga tokens extras em toda query.")
    if args.com_professor:
        print(f"\n   ADAPTER − PROFESSOR: {perf('ADAPTER') - perf('professor'):+.1%}"
              "   (professor = teto prático da tarefa)")

    if args.tag:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"external_{args.tag}.json"
        p.write_text(json.dumps({"peft": args.peft, "shots": args.shots,
                                 "resultado": acc}, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
