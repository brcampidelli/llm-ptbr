"""Fase 2 (dados) — Filtro "O BASE ERRA": mantém só as tarefas que ensinam algo.

⭐ A REGRA. O gate de 2026-07-25 mostrou que o base resolve 93,3% das tarefas de
função geradas pelo professor — treinar nelas não ensinaria nada (foi exatamente o
que aconteceu com o SFT generalista PT-BR: base sem espaço, 0 de 7 ganhos).
Collab-RAG (arXiv 2504.04915) formaliza a saída: **descartar itens em que todas as
amostras têm a mesma recompensa**, porque não carregam sinal. Aqui isso vira:

    manter a tarefa  ⟺  a solução do professor PASSA  E  o base FALHA

O dataset passa a ser, por construção, o conjunto do que o modelo NÃO sabe — um
currículo automático, sem ninguém rotular dificuldade a dedo.

⚠️ CONSISTÊNCIA COM A AVALIAÇÃO: o SYSTEM e os parâmetros de geração são
IMPORTADOS de eval/eval_coder.py. Se o filtro usasse prompt diferente do eval,
"o base erra aqui" não significaria "o base erra lá" e a dificuldade medida não
transferiria. Um bug subtil que vale prevenir por construção.

⚡ GERAÇÃO EM LOTE: sem isso o filtro é inviável — a ~12 s/tarefa, 4.000
candidatas levariam ~13 h. Com --batch-size 8 cai para ~1,5-2 h.

Uso (na L4 — precisa de GPU):
    python data/09_filter_hard_tasks.py --limit 60 --batch-size 8      # piloto
    python data/09_filter_hard_tasks.py --batch-size 8                 # tudo
    python data/09_filter_hard_tasks.py --samples 2                    # mais rigoroso

Saída: data/raw/coder_tasks_hard.jsonl  (as que o base errou) e
       data/raw/coder_tasks_easy.jsonl  (as que ele acertou — não treinam, mas
       servem de holdout "fácil" para checar que não regredimos)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "eval"))
from common import read_jsonl, strip_think  # noqa: E402
from code_exec import extract_code, run_tests  # noqa: E402

# ⚠️ mesma condição da avaliação — importado, não copiado.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("ec", ROOT / "eval" / "eval_coder.py")
_ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ec)
SYSTEM = _ec.SYSTEM

IN = ROOT / "data" / "raw" / "coder_tasks.jsonl"
OUT_HARD = ROOT / "data" / "raw" / "coder_tasks_hard.jsonl"
OUT_EASY = ROOT / "data" / "raw" / "coder_tasks_easy.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--tasks", type=Path, default=IN)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8,
                    help="geracao em lote — SEM isto o filtro e inviavel")
    ap.add_argument("--max-new", type=int, default=420)
    ap.add_argument("--samples", type=int, default=1,
                    help="tentativas do base por tarefa. 1 = guloso (deterministico, "
                         "barato). >1 usa amostragem: a tarefa so e 'dificil' se o base "
                         "falhar em TODAS — mais rigoroso, custa k vezes mais")
    ap.add_argument("--temperature", type=float, default=0.7, help="usado se --samples>1")
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--no-4bit", action="store_true")
    args = ap.parse_args()

    tasks = [t for t in read_jsonl(args.tasks) if t.get("prompt") and t.get("tests")]
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        print(f"ERRO: nenhuma tarefa em {args.tasks}", file=sys.stderr)
        return 1

    # retomada: nao refiltrar o que ja foi decidido
    decididas: set[str] = set()
    for p in (OUT_HARD, OUT_EASY):
        if p.exists():
            decididas |= {r["name"] for r in read_jsonl(p) if "name" in r}
    if decididas:
        antes = len(tasks)
        tasks = [t for t in tasks if t["name"] not in decididas]
        print(f"[retomada] {len(decididas)} ja decididas, {antes - len(tasks)} puladas")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kwargs: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
        )
    print(f"modelo    : {args.model} (BASE, sem adapter — e ele que precisa errar)")
    print(f"candidatas: {len(tasks)}")
    print(f"lote      : {args.batch_size} | amostras/tarefa: {args.samples}")
    print(f"saidas    : {OUT_HARD.name} (treina) / {OUT_EASY.name} (holdout facil)\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"          # OBRIGATORIO para geracao em lote
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    model.eval()

    def gen_batch(prompts: list[str]) -> list[str]:
        """Gera para vários prompts de uma vez (o que torna o filtro viável)."""
        textos = []
        for p in prompts:
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}]
            try:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                            enable_thinking=False, tokenize=False)
            except TypeError:
                s = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
            textos.append(s)
        enc = tok(textos, return_tensors="pt", padding=True, truncation=True,
                  max_length=2048).to("cuda")
        gen_kw = dict(max_new_tokens=args.max_new, pad_token_id=tok.eos_token_id)
        if args.samples > 1:
            gen_kw.update(do_sample=True, temperature=args.temperature, top_p=0.95)
        else:
            gen_kw.update(do_sample=False)
        with torch.no_grad():
            out = model.generate(**enc, **gen_kw)
        plen = enc["input_ids"].shape[1]
        return [tok.decode(o[plen:], skip_special_tokens=True).strip() for o in out]

    n_hard = n_easy = 0
    motivos: Counter[str] = Counter()

    with OUT_HARD.open("a", encoding="utf-8") as fh, OUT_EASY.open("a", encoding="utf-8") as fe:
        for i in range(0, len(tasks), args.batch_size):
            lote = tasks[i: i + args.batch_size]
            # k tentativas: a tarefa e "facil" se o base acertar em QUALQUER uma
            acertou = [False] * len(lote)
            razoes: list[str] = [""] * len(lote)
            for _ in range(max(1, args.samples)):
                saidas = gen_batch([t["prompt"] for t in lote])
                for j, (t, raw) in enumerate(zip(lote, saidas)):
                    if acertou[j]:
                        continue
                    code = extract_code(strip_think(raw)[0])
                    if not code:
                        razoes[j] = "base nao devolveu codigo"
                        continue
                    res = run_tests(code, t["tests"], timeout=args.timeout)
                    if res.ok:
                        acertou[j] = True
                    else:
                        razoes[j] = res.reason[:140]

            for t, ok, razao in zip(lote, acertou, razoes):
                if ok:
                    fe.write(json.dumps(t, ensure_ascii=False) + "\n")
                    n_easy += 1
                else:
                    rec = dict(t)
                    rec["base_failed_reason"] = razao
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_hard += 1
                    cat = ("sem codigo" if "nao devolveu" in razao else
                           "timeout" if "timeout" in razao else
                           "assert falhou" if "assert" in razao else "erro de execucao")
                    motivos[cat] += 1
            fh.flush(); fe.flush()
            feito = min(i + args.batch_size, len(tasks))
            print(f"  {feito}/{len(tasks)} | DIFICEIS (base errou): {n_hard} "
                  f"({n_hard/max(1,feito):.0%}) | faceis: {n_easy}", flush=True)

    total = n_hard + n_easy
    print("\n" + "=" * 62)
    print(f"⭐ TAREFAS QUE ENSINAM (base errou): {n_hard}/{total} = {n_hard/max(1,total):.1%}")
    print(f"   descartadas por serem faceis    : {n_easy}/{total} = {n_easy/max(1,total):.1%}")
    print("-" * 62)
    print("como o base erra nas dificeis:")
    for k, v in motivos.most_common():
        print(f"   {k:<20} {v:>3}  ({v/max(1,n_hard):.0%})")
    print("=" * 62)
    print(f"\n-> {OUT_HARD}  (usar para treinar)")
    print(f"-> {OUT_EASY}  (holdout 'facil': checar que nao regredimos nelas)")
    if n_hard < 150:
        print(f"\n⚠️ {n_hard} tarefas dificeis e POUCO para SFT. Aproveitamento medido: "
              f"{n_hard/max(1,total):.0%} -> para ~300 dificeis, gerar ~{int(300/max(0.01,n_hard/max(1,total)))} "
              "candidatas (data/08_gen_coder_tasks.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
