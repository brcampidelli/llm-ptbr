"""Fase 2.6 — Gerar pares de preferência (chosen/rejected) para o DPO.

Fecha a última dependência do train/dpo_qlora.py. Ideia (error bootstrapping do
Learn2Zinc + destilação de professor aberto):
  - chosen   = resposta de um professor FORTE (aberto) — o alvo a preferir.
  - rejected = resposta PIOR, de uma destas fontes (--rejected-mode):
      * weak    : um modelo aberto mais fraco (default) — roda agora, sem GPU.
      * student : as respostas do PRÓPRIO 4B pós-SFT (error bootstrapping puro) —
                  lidas de um arquivo {instruction, response} gerado na GPU.
      * degraded: o mesmo professor forte, mas instruído a dar resposta superficial.

⚠️ DPO é sensível a PARES RUINS. Por isso um JUIZ ABERTO valida cada par:
  - se o juiz concorda que 'chosen' é melhor → mantém;
  - se o juiz acha 'rejected' melhor → INVERTE (o par vira chosen=melhor);
  - se EMPATE → descarta (sinal fraco vira ruído no DPO).
Posição A/B é randomizada por item para não enviesar o juiz.

REGRA DURA: todos os modelos (chosen, rejected, juiz) são ABERTOS (config.py).

Uso:
    python data/06_build_preferences.py --seeds data/seeds_ptbr_expanded.txt \
        --chosen deepseek/deepseek-v4-pro --rejected-mode weak --rejected mistralai/mistral-nemo
    python data/06_build_preferences.py --seeds ... --rejected-mode student \
        --student-file data/raw/student_responses.jsonl
    python data/06_build_preferences.py --seeds ... --limit 20 --dry-run

Requer OPENROUTER_API_KEY. Retomável. Saída: data/processed/preferences_ptbr.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PREF_OUT, assert_teacher_allowed, ensure_dirs  # noqa: E402
from common import read_jsonl  # noqa: E402
from teacher_api import TeacherError, call_teacher  # noqa: E402

SYS_ANSWER = (
    "Você é um assistente brasileiro especialista. Responda SEMPRE em português "
    "brasileiro natural e correto. Seja preciso, completo e claro."
)
SYS_DEGRADED = (
    "Você é um assistente apressado. Responda em português brasileiro de forma "
    "CURTA e SUPERFICIAL, sem detalhes nem exemplos. Não se esforce."
)
SYS_JUDGE = (
    "Você é um avaliador imparcial de qualidade de respostas em português brasileiro. "
    "Dada uma pergunta e duas respostas (A e B), escolha a MELHOR considerando: "
    "correção factual, completude, clareza e português correto. Ao FINAL, escreva "
    "exatamente 'VEREDITO=A', 'VEREDITO=B' ou 'VEREDITO=E' (E = empate)."
)
# Delimitador inequívoco: não confundir com letras soltas do raciocínio (ex.: o 'E'
# de 'processo'). Fallback: última letra isolada numa linha, se o modelo não seguir.
_VERDICT_RE = re.compile(r"VEREDITO\s*=\s*([ABE])", re.IGNORECASE)
_VERDICT_LINE_RE = re.compile(r"(?m)^\s*([ABE])\s*$")


def load_seeds(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"sementes nao encontradas: {path}")
    if path.suffix == ".jsonl":
        return [(r.get("prompt") or r.get("instruction") or "").strip()
                for r in read_jsonl(path) if (r.get("prompt") or r.get("instruction"))]
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_student(path: Path) -> dict[str, str]:
    """Mapa instrução→resposta do aluno (para --rejected-mode student)."""
    out: dict[str, str] = {}
    for r in read_jsonl(path):
        instr = r.get("instruction") or r.get("prompt")
        resp = r.get("response")
        if instr and resp:
            out[instr.strip()] = resp.strip()
    return out


def judge_pair(prompt: str, a: str, b: str, judge: str, api_key: str) -> str:
    """Retorna 'A', 'B' ou 'E'. Falha/ambíguo → 'E' (descartado, DPO não vê ruído)."""
    q = (f"PERGUNTA: {prompt}\n\nRESPOSTA A:\n{a}\n\nRESPOSTA B:\n{b}\n\n"
         "Qual é melhor? Justifique brevemente e termine com VEREDITO=A, VEREDITO=B ou VEREDITO=E.")
    try:
        # 512 tokens: juízes com reasoning gastam tokens pensando antes do veredito.
        raw = call_teacher(q, judge, api_key, system=SYS_JUDGE, temperature=0.0, max_tokens=512)
    except Exception:
        return "E"
    m = _VERDICT_RE.search(raw)
    if m:
        return m.group(1).upper()
    m2 = _VERDICT_LINE_RE.search(raw.upper())  # fallback: letra sozinha numa linha
    return m2.group(1) if m2 else "E"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=Path, required=True)
    ap.add_argument("--chosen", default="deepseek/deepseek-v4-pro",
                    help="professor FORTE p/ a resposta 'chosen'")
    ap.add_argument("--rejected-mode", choices=["weak", "student", "degraded"], default="weak")
    ap.add_argument("--rejected", default="mistralai/mistral-nemo",
                    help="modelo fraco p/ 'rejected' (modo weak); modo degraded usa o --chosen")
    ap.add_argument("--student-file", type=Path, default=None,
                    help="jsonl {instruction,response} do aluno (modo student)")
    ap.add_argument("--judge", default="qwen/qwen3.5-9b", help="juiz aberto que valida os pares")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Guard de licença: chosen, rejected (se modelo) e juiz precisam ser abertos.
    assert_teacher_allowed(args.chosen)
    assert_teacher_allowed(args.judge)
    if args.rejected_mode == "weak":
        assert_teacher_allowed(args.rejected)
    ensure_dirs()

    seeds = load_seeds(args.seeds)
    if args.limit:
        seeds = seeds[: args.limit]

    student: dict[str, str] = {}
    if args.rejected_mode == "student":
        if not args.student_file or not args.student_file.exists():
            print("ERRO: --rejected-mode student exige --student-file existente.", file=sys.stderr)
            return 1
        student = load_student(args.student_file)
        seeds = [s for s in seeds if s in student]  # só onde temos resposta do aluno
        print(f"[student] {len(seeds)} prompts com resposta do aluno")

    # Retomada.
    done: set[str] = set()
    if PREF_OUT.exists():
        done = {r["prompt"] for r in read_jsonl(PREF_OUT) if "prompt" in r}
        print(f"[retomada] {len(done)} pares ja existentes")
    pending = [s for s in seeds if s not in done]

    print(f"chosen   : {args.chosen}")
    print(f"rejected : modo={args.rejected_mode}"
          + (f" ({args.rejected})" if args.rejected_mode == 'weak' else ""))
    print(f"juiz     : {args.judge}")
    print(f"prompts  : {len(seeds)} (pendentes: {len(pending)})")
    print(f"saida    : {PREF_OUT}")

    if args.dry_run:
        print("\n[dry-run] nada chamado. Custo estimado: ~3-4 chamadas/par "
              "(chosen + rejected + juiz). Exemplos pendentes:")
        for s in pending[:3]:
            print(f"  - {s[:90]}")
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY.", file=sys.stderr)
        return 1

    counters = {"ok": 0, "skip": 0, "swap": 0, "fail": 0, "done": 0}
    lock = threading.Lock()
    total = len(pending)
    rng = random.Random(args.seed)

    def gen_rejected(prompt: str) -> str:
        if args.rejected_mode == "student":
            return student[prompt]
        if args.rejected_mode == "degraded":
            return call_teacher(prompt, args.chosen, api_key, system=SYS_DEGRADED,
                                temperature=0.9, max_tokens=512)
        return call_teacher(prompt, args.rejected, api_key, system=SYS_ANSWER,
                            temperature=0.7, max_tokens=1024)

    def work(prompt: str) -> None:
        try:
            chosen = call_teacher(prompt, args.chosen, api_key, system=SYS_ANSWER,
                                  temperature=0.7, max_tokens=2048)
            rejected = gen_rejected(prompt)
        except Exception as e:
            with lock:
                counters["fail"] += 1; counters["done"] += 1
                print(f"  FALHA: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(15.0 if "429" in str(e) else 2.0)
            return

        # Pares degenerados não servem.
        if not rejected.strip() or chosen.strip() == rejected.strip():
            with lock:
                counters["skip"] += 1; counters["done"] += 1
            return

        # Juiz com posição randomizada (evita viés A/B).
        swap = rng.random() < 0.5
        a, b = (rejected, chosen) if swap else (chosen, rejected)
        verdict = judge_pair(prompt, a, b, args.judge, api_key)
        winner = {"A": a, "B": b}.get(verdict)

        if winner is None:  # empate → descarta (ruído p/ DPO)
            with lock:
                counters["skip"] += 1; counters["done"] += 1
            time.sleep(args.sleep)
            return

        loser = b if winner is a else a
        did_swap = winner is not chosen  # o "rejected" venceu → invertemos
        rec = json.dumps(
            {"prompt": prompt, "chosen": winner, "rejected": loser,
             "chosen_src": args.chosen if not did_swap else f"rejected:{args.rejected_mode}",
             "swapped": did_swap},
            ensure_ascii=False,
        )
        with lock:
            fout.write(rec + "\n"); fout.flush()
            counters["ok"] += 1; counters["done"] += 1
            if did_swap:
                counters["swap"] += 1
            d = counters["done"]
            if d % 25 == 0 or d == total:
                print(f"  [{d}/{total}] ok={counters['ok']} skip={counters['skip']} "
                      f"swap={counters['swap']} falhas={counters['fail']}", flush=True)
        time.sleep(args.sleep)

    print(f"workers  : {args.workers}\n")
    with PREF_OUT.open("a", encoding="utf-8") as fout:
        if args.workers <= 1:
            for p in pending:
                work(p)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(work, pending))

    print(f"\nConcluido: {counters['ok']} pares ({counters['swap']} invertidos pelo juiz), "
          f"{counters['skip']} descartados, {counters['fail']} falhas -> {PREF_OUT}")
    print("Proximo: python train/dpo_qlora.py --sft-adapter <SFT> --data data/processed/preferences_ptbr.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
