"""Fase 1 (dados) — Destilar TOOL-USE de professor aberto: a abelha agentica.

Por que esta abelha primeiro: e a evidencia mais forte da literatura de que
especializacao pequena bate modelo gigante generalista (xLAM-2-8B supera GPT-4o
e Claude 3.5 em tool-calling). E o coracao de um sistema agentico.

O que o dado ensina (3 comportamentos, nao 1):
  1. pedido que EXIGE ferramenta   -> JSON {"tool": ..., "args": {...}}
  2. pedido que NAO exige          -> resposta direta em texto
     (over-calling e a falha classica; ~1/3 das sementes sao desse tipo)
  3. pedido AMBIGUO / faltando arg -> pedir o que falta, NAO inventar

⚠️ VALIDACAO DURA (par ruim estraga adapter): quando o professor devolve JSON,
conferimos contra data/agentic_tools.json — a ferramenta tem que existir, os
args obrigatorios tem que estar presentes e nao pode haver arg desconhecido.
O que nao valida vai para <out>.rejects.jsonl com o motivo, e NAO treina.

REGRA DURA do projeto: professor ABERTO (assert_teacher_allowed).

Uso:
    python data/07_distill_agentic.py --dry-run
    python data/07_distill_agentic.py --workers 16
    python data/07_distill_agentic.py --teacher qwen/qwen3.5-9b --limit 20

Saida: data/raw/agentic_<tag>.jsonl  ({instruction, response, kind})
Retomavel: relanca e continua de onde parou.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (DATA_DIR, DEFAULT_TEACHER, RAW_DIR, assert_teacher_allowed,  # noqa: E402
                    ensure_dirs)
from common import read_jsonl  # noqa: E402
from teacher_api import call_teacher  # noqa: E402

# Catalogo + system prompt vivem em tool_catalog.py: TREINO, AVALIACAO e PRODUCAO
# (orchestrator/registry.py) importam a MESMA funcao. Antes o bees.json tinha uma
# copia resumida A MAO que nao listava ferramenta nenhuma — a abelha era treinada
# com o catalogo a vista e servida as cegas. Reexportado para nao quebrar os evals,
# que importam `build_system`/`load_tools` deste modulo via importlib.
from tool_catalog import TOOLS_FILE, build_system, load_tools, tools_prompt  # noqa: F401,E402


# ---------------------------------------------------------------- validação ---

def extract_json(text: str) -> dict | None:
    """Tenta ler um objeto JSON da resposta. None = nao e chamada de ferramenta.

    Tolera cerca de ```json ... ``` (modelos adoram cercar), mas NAO tolera texto
    solto junto do JSON — nesse caso o dado e ruim e vai para rejects.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def validate_call(obj: dict, tools: dict) -> str | None:
    """Retorna None se o par e valido, ou a razao da rejeicao."""
    if "tool" not in obj:
        return "json sem campo 'tool'"
    name = obj["tool"]
    if name not in tools:
        return f"ferramenta inexistente: {name!r}"
    args = obj.get("args", {})
    if not isinstance(args, dict):
        return "'args' nao e objeto"
    spec = tools[name]
    known = set(spec.get("args", {}))
    missing = [a for a in spec.get("required", []) if a not in args or args[a] in ("", None)]
    if missing:
        return f"{name}: args obrigatorios ausentes: {missing}"
    unknown = [a for a in args if a not in known]
    if unknown:
        return f"{name}: args desconhecidos: {unknown}"
    return None


# Aritmetica nao-trivial: o professor tende a responder de cabeca E ERRAR.
# Caso real (piloto 2026-07-24): "48239 vezes 1177" -> respondeu 56.757.303 em
# texto; o certo e 56.777.303. Errou a conta E ignorou a calculator. O validador
# de JSON nao pega isso (a resposta nem era JSON), entao checamos aqui.
_ARITH_INTENT = re.compile(
    r"\b(calcul\w*|quanto\s+(?:é|e|vale)|resultado|raiz|potência|potencia|"
    r"divid\w*|multiplic\w*|vezes|somat\w*)\b|[×÷]|\d\s*[\*/^]\s*\d",
    re.IGNORECASE,
)
_BIG_NUMBER = re.compile(r"\d{3,}")


def looks_like_hard_math(prompt: str) -> bool:
    """Pedido de conta com numero de 3+ digitos -> deveria usar a calculator."""
    return bool(_ARITH_INTENT.search(prompt) and _BIG_NUMBER.search(prompt))


def classify(text: str, tools: dict, prompt: str = "") -> tuple[str, str | None]:
    """Classifica a resposta do professor: (kind, motivo_rejeicao)."""
    obj = extract_json(text)
    if obj is None:
        # nao e JSON -> resposta direta ou pedido de esclarecimento.
        if "{" in text and '"tool"' in text:
            # tentou chamar ferramenta mas com texto solto em volta / json quebrado
            return "reject", "parece chamada de ferramenta mal formada (texto+json ou json invalido)"
        if prompt and looks_like_hard_math(prompt):
            return "reject", ("aritmetica de 3+ digitos respondida de cabeca: deveria ter "
                              "usado calculator (risco de conta errada no alvo de treino)")
        return "text", None
    reason = validate_call(obj, tools)
    return ("reject", reason) if reason else ("tool_call", None)


# --------------------------------------------------------------------- main ---

def load_seeds(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"sementes nao encontradas: {path}")
    if path.suffix == ".jsonl":
        return [(r.get("prompt") or r.get("instruction") or "").strip()
                for r in read_jsonl(path) if (r.get("prompt") or r.get("instruction"))]
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    # console do Windows e cp1252: acentos/emoji no print quebram. Forca UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=Path, default=DATA_DIR / "seeds_agentic.txt")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--tag", default="agentic")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--temperature", type=float, default=0.3,
                    help="baixa: tool-call e formato rigido, nao criatividade")
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.teacher)   # REGRA DURA: professor aberto
    ensure_dirs()

    tools = load_tools()
    system = build_system(tools)
    seeds = load_seeds(args.seeds)
    if args.limit:
        seeds = seeds[: args.limit]

    out_path = RAW_DIR / f"{args.tag}_{args.teacher.split('/')[-1]}.jsonl"
    rej_path = out_path.with_suffix(".rejects.jsonl")

    done: set[str] = set()
    if out_path.exists():
        done = {r["instruction"] for r in read_jsonl(out_path) if "instruction" in r}
        print(f"[retomada] {len(done)} exemplos ja existentes")
    pending = [s for s in seeds if s not in done]

    print(f"professor : {args.teacher}")
    print(f"ferramentas: {len(tools)} no catalogo")
    print(f"sementes  : {len(seeds)} (pendentes: {len(pending)})")
    print(f"saida     : {out_path}")
    print(f"rejeitados: {rej_path}")

    if args.dry_run:
        print("\n[dry-run] nada chamado. System prompt montado:\n")
        print(system[:1200] + ("..." if len(system) > 1200 else ""))
        print("\nPrimeiras sementes pendentes:")
        for s in pending[:5]:
            print(f"  - {s[:90]}")
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY.", file=sys.stderr)
        return 1

    counters = {"tool_call": 0, "text": 0, "reject": 0, "fail": 0, "done": 0}
    lock = threading.Lock()
    total = len(pending)

    def work(prompt: str) -> None:
        try:
            resp = call_teacher(prompt, args.teacher, api_key, system=system,
                                temperature=args.temperature, max_tokens=700)
        except Exception as e:
            with lock:
                counters["fail"] += 1; counters["done"] += 1
                print(f"  FALHA: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(15.0 if "429" in str(e) else 2.0)
            return

        kind, reason = classify(resp, tools, prompt)
        rec = {"instruction": prompt, "response": resp, "kind": kind}
        with lock:
            if kind == "reject":
                rec["reject_reason"] = reason
                frej.write(json.dumps(rec, ensure_ascii=False) + "\n"); frej.flush()
            else:
                # normaliza o JSON valido (indentacao consistente = alvo estavel)
                if kind == "tool_call":
                    rec["response"] = json.dumps(extract_json(resp), ensure_ascii=False)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); fout.flush()
            counters[kind] += 1; counters["done"] += 1
            d = counters["done"]
            if d % 20 == 0 or d == total:
                print(f"  [{d}/{total}] tool={counters['tool_call']} texto={counters['text']} "
                      f"rejeitados={counters['reject']} falhas={counters['fail']}", flush=True)
        time.sleep(args.sleep)

    print(f"workers   : {args.workers}\n")
    with out_path.open("a", encoding="utf-8") as fout, \
         rej_path.open("a", encoding="utf-8") as frej:
        if args.workers <= 1:
            for p in pending:
                work(p)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(work, pending))

    keep = counters["tool_call"] + counters["text"]
    print(f"\nConcluido: {keep} exemplos validos "
          f"({counters['tool_call']} chamadas de ferramenta + {counters['text']} respostas diretas), "
          f"{counters['reject']} rejeitados, {counters['fail']} falhas")
    print(f"  -> {out_path}")
    if counters["reject"]:
        print(f"  ⚠️ inspecione {rej_path} ANTES de treinar (motivo em 'reject_reason')")
    print("Proximo: 03_filter_dedup / 05_build_splits, depois train/sft_qlora.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
