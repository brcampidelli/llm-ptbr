"""Avaliação da abelha CODER — pass@1 por EXECUÇÃO (o juiz é o interpretador).

Régua certa para esta abelha: a função gerada passa nos testes? Objetivo, barato e
sem alucinação de juiz. Nada de múltipla escolha (foi a régua errada que fez o SFT
generalista parecer "sem resultado").

⭐ USO MAIS IMPORTANTE — medir o BASE ANTES de treinar. A lição do dia: o SFT
generalista PT-BR desperdiçou esforço porque o base já era forte (0,93 no belebele,
sem espaço). A abelha agêntica funcionou porque o base estava em 45,7% (muito
espaço). Se o base já resolver quase tudo aqui, NÃO vale treinar — e é melhor
descobrir isso em 10 minutos de avaliação que em 3 horas de GPU.

Mede:
  pass@1        — % de funções que passam em TODOS os asserts
  sintaxe ok    — % que ao menos parseia/roda (separa "errou a lógica" de "nem compila")
  sem código    — % de respostas em que não veio código nenhum
  motivos       — distribuição das falhas (assert / erro de execução / timeout)

Uso:
    python eval/eval_coder.py --limit 30                       # BASE (referência)
    python eval/eval_coder.py --peft <adapter> --limit 30
    python eval/eval_coder.py --limit 0 --tag base-completo
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402
from code_exec import extract_code, run_tests  # noqa: E402

DEFAULT_TASKS = ROOT / "data" / "raw" / "coder_tasks.jsonl"

SYSTEM = (
    "Você é um programador Python. Complete a função pedida. Responda SOMENTE com o "
    "código da função completa, dentro de um bloco ```python. Sem explicação antes "
    "ou depois. A função deve ser pura: sem input(), open(), os, sys ou rede."
)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", default=None)
    ap.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--limit", type=int, default=30, help="0 = todas")
    ap.add_argument("--max-new", type=int, default=420,
                    help="codigo precisa de mais tokens que JSON de tool-call")
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--show-fails", type=int, default=4)
    args = ap.parse_args()

    tasks = [t for t in read_jsonl(args.tasks) if t.get("prompt") and t.get("tests")]
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        print(f"ERRO: nenhuma tarefa em {args.tasks}", file=sys.stderr)
        return 1

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
    print(f"tarefas: {len(tasks)} de {args.tasks.name}\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    if args.peft:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    n_pass = n_nocode = 0
    motivos: Counter[str] = Counter()
    falhas: list[tuple[str, str]] = []

    for i, t in enumerate(tasks, 1):
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": t["prompt"]}]
        tpl = {"add_generation_prompt": True, "return_tensors": "pt", "return_dict": True}
        try:
            enc = tok.apply_chat_template(msgs, enable_thinking=False, **tpl)
        except TypeError:
            enc = tok.apply_chat_template(msgs, **tpl)
        inputs = {k: v.to("cuda") for k, v in dict(enc).items() if hasattr(v, "to")}
        plen = inputs["input_ids"].shape[1]
        with torch.no_grad():
            g = model.generate(**inputs, max_new_tokens=args.max_new, do_sample=False,
                               pad_token_id=tok.eos_token_id)
        raw = tok.decode(g[0][plen:], skip_special_tokens=True).strip()
        answer, _ = strip_think(raw)
        code = extract_code(answer)

        if not code:
            n_nocode += 1
            motivos["sem codigo"] += 1
            falhas.append((t["name"], "nao devolveu codigo"))
        else:
            res = run_tests(code, t["tests"], timeout=args.timeout)
            if res.ok:
                n_pass += 1
            else:
                # categoriza o motivo (separa "errou a logica" de "nem roda")
                r = res.reason
                cat = ("timeout" if "timeout" in r else
                       "assert falhou" if "assert falhou" in r else
                       "padrao proibido" if "proibido" in r else
                       "erro de execucao")
                motivos[cat] += 1
                falhas.append((t["name"], r[:110]))

        if i % 10 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  pass@1 parcial: {n_pass/i:.1%}", flush=True)

    n = len(tasks)
    rodou = n - n_nocode
    print("\n" + "=" * 66)
    print(f"tarefas avaliadas   : {n}")
    print(f"⭐ pass@1 (execucao) : {n_pass}/{n} = {n_pass/n:.1%}")
    print(f"devolveu codigo      : {rodou}/{n} = {rodou/n:.1%}")
    if rodou:
        print(f"pass@1 entre as que devolveram codigo: {n_pass}/{rodou} = {n_pass/rodou:.1%}")
    print("-" * 66)
    print("motivos das falhas:")
    for k, v in motivos.most_common():
        print(f"   {k:<20} {v:>3}  ({v/n:.0%})")
    print("=" * 66)

    if args.show_fails and falhas:
        print(f"\nprimeiras {min(args.show_fails, len(falhas))} falhas:")
        for nome, r in falhas[: args.show_fails]:
            print(f"   {nome}: {r}")

    if args.tag:
        outdir = ROOT / "eval" / "results"
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / f"coder_{args.tag}.json"
        p.write_text(json.dumps({
            "tag": args.tag, "model": args.model, "peft": args.peft,
            "n": n, "pass1": n_pass / n, "n_pass": n_pass,
            "no_code": n_nocode, "motivos": dict(motivos),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
