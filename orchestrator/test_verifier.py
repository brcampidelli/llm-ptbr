"""Mede a PRECISÃO do verificador contra o holdout rotulado — SEM GPU.

Por que isto existe: o verificador só ajuda se acertar quando afirma "esta query
não precisa de ferramenta". Um falso positivo aí BLOQUEIA uma chamada legítima e
piora o sistema. Então medimos antes de ligar, usando os rótulos que já temos
(data/processed/sft_agentic.eval.jsonl, 150 exemplos: 85 tool_call + 65 text).

Interpretação da matriz:
  disse 'text'  & era text       -> ✅ bloquearia over-calling corretamente
  disse 'text'  & era tool_call  -> ❌ FALSO POSITIVO PERIGOSO (bloqueia chamada boa)
  disse 'tool'  & era tool_call  -> ✅ forçaria a chamada corretamente
  disse 'tool'  & era text       -> ❌ falso positivo (forçaria chamada errada)
  disse 'unknown'                -> ⚪ não interfere (seguro)

Uso:
    python orchestrator/test_verifier.py
    python orchestrator/test_verifier.py --show-errors
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_jsonl  # noqa: E402
from verifier import expected_mode  # noqa: E402

DATA = ROOT / "data" / "processed" / "sft_agentic.eval.jsonl"


def get_user(row: dict) -> str:
    msgs = row.get("messages") or (list(row.get("prompt") or [])
                                   + list(row.get("completion") or []))
    for m in msgs:
        if m.get("role") == "user":
            return m["content"]
    return ""


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args()

    rows = [r for r in read_jsonl(args.data) if r.get("kind")]
    if not rows:
        print(f"ERRO: nenhum exemplo rotulado em {args.data}", file=sys.stderr)
        return 1

    mat: Counter[tuple[str, str]] = Counter()
    erros_perigosos, erros_leves = [], []

    for r in rows:
        q = get_user(r)
        truth = "text" if r["kind"] == "text" else "tool"
        pred = expected_mode(q)
        mat[(pred, truth)] += 1
        if pred == "text" and truth == "tool":
            erros_perigosos.append(q)
        elif pred == "tool" and truth == "text":
            erros_leves.append(q)

    n = len(rows)
    print(f"holdout: {n} exemplos rotulados\n")
    print(f"{'verificador disse':<20} {'era tool_call':>14} {'era text':>10}")
    print("-" * 46)
    for pred in ("tool", "text", "unknown"):
        print(f"{pred:<20} {mat[(pred,'tool')]:>14} {mat[(pred,'text')]:>10}")
    print("-" * 46)

    n_unknown = mat[("unknown", "tool")] + mat[("unknown", "text")]
    acertos = mat[("text", "text")] + mat[("tool", "tool")]
    fp_perigoso = mat[("text", "tool")]
    fp_leve = mat[("tool", "text")]
    opinou = n - n_unknown

    print(f"\nnão interferiu (unknown) : {n_unknown}/{n} = {n_unknown/n:.1%}  (seguro)")
    print(f"opinou                   : {opinou}/{n} = {opinou/n:.1%}")
    if opinou:
        print(f"  acertos                : {acertos}/{opinou} = {acertos/opinou:.1%}")
        print(f"  ❌ FP PERIGOSO (bloquearia chamada boa): {fp_perigoso}/{opinou} "
              f"= {fp_perigoso/opinou:.1%}")
        print(f"  ⚠️ FP leve (forçaria chamada errada)   : {fp_leve}/{opinou} "
              f"= {fp_leve/opinou:.1%}")

    # O número que decide: precisão quando diz "text" (é o que barra over-calling)
    disse_text = mat[("text", "text")] + mat[("text", "tool")]
    if disse_text:
        prec = mat[("text", "text")] / disse_text
        print(f"\n⭐ PRECISÃO ao dizer 'não precisa de ferramenta': "
              f"{mat[('text','text')]}/{disse_text} = {prec:.1%}")
        print("   (é esta que barra o over-calling; <90% = arriscado ligar)")
        cobertura = mat[("text", "text")] / max(1, mat[("text", "text")]
                                                + mat[("unknown", "text")]
                                                + mat[("tool", "text")])
        print(f"   cobertura dos casos de texto: {cobertura:.1%}")

    if args.show_errors:
        if erros_perigosos:
            print(f"\n❌ FALSOS POSITIVOS PERIGOSOS ({len(erros_perigosos)}):")
            for q in erros_perigosos[:12]:
                print(f"   - {q[:95]}")
        if erros_leves:
            print(f"\n⚠️ falsos positivos leves ({len(erros_leves)}):")
            for q in erros_leves[:12]:
                print(f"   - {q[:95]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
