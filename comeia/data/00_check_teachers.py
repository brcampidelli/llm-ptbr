"""Fase 2.0 — Validar os professores contra a API real do OpenRouter.

Alguns IDs em ALLOWED_TEACHERS foram inferidos pelo padrão de nomenclatura do
OpenRouter. Este script confirma quais existem de fato, mostra o preço atual e
estima quantos pares cabem no orçamento. Rode ANTES de gastar chave.

Uso:
    python data/00_check_teachers.py
    python data/00_check_teachers.py --budget 10 --out-tokens 700
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ALLOWED_TEACHERS, DEFAULT_TEACHER  # noqa: E402

API = "https://openrouter.ai/api/v1/models"


def fetch_models() -> dict[str, dict]:
    req = urllib.request.Request(API, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return {m["id"]: m for m in payload.get("data", [])}


def price(model: dict, key: str) -> float:
    try:
        return float(model.get("pricing", {}).get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=10.0, help="orcamento em USD")
    ap.add_argument("--in-tokens", type=int, default=150, help="tokens de entrada por par")
    ap.add_argument("--out-tokens", type=int, default=700, help="tokens de saida por par")
    args = ap.parse_args()

    try:
        catalog = fetch_models()
    except Exception as e:
        print(f"ERRO ao consultar o OpenRouter: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(f"catalogo OpenRouter: {len(catalog)} modelos\n")
    print(f"{'ID':<38} {'status':<10} {'$/M in':>9} {'$/M out':>9} {'pares/$' + str(int(args.budget)):>12}")
    print("-" * 82)

    ok_any = False
    for tid in sorted(ALLOWED_TEACHERS):
        m = catalog.get(tid)
        if not m:
            print(f"{tid:<38} {'AUSENTE':<10} {'-':>9} {'-':>9} {'-':>12}")
            continue
        ok_any = True
        # pricing do OpenRouter vem por TOKEN; multiplicar por 1M para ler em $/M
        p_in = price(m, "prompt") * 1_000_000
        p_out = price(m, "completion") * 1_000_000
        cost_pair = (args.in_tokens / 1e6) * p_in + (args.out_tokens / 1e6) * p_out
        pairs = int(args.budget / cost_pair) if cost_pair > 0 else 0
        pairs_s = "ilimitado*" if cost_pair == 0 else f"{pairs:,}".replace(",", ".")
        marker = " <- padrao" if tid == DEFAULT_TEACHER else ""
        print(f"{tid:<38} {'OK':<10} {p_in:>9.4f} {p_out:>9.4f} {pairs_s:>12}{marker}")

    print("-" * 82)
    print(f"* gratuito = sem custo, mas com rate limit (nao serve para volume alto)")
    print(f"premissa: {args.in_tokens} tokens de entrada + {args.out_tokens} de saida por par\n")

    if not ok_any:
        print("NENHUM professor valido. Revise ALLOWED_TEACHERS em data/config.py.", file=sys.stderr)
        return 1
    if DEFAULT_TEACHER not in catalog:
        print(f"AVISO: o professor padrao ({DEFAULT_TEACHER}) nao existe no catalogo. "
              "Escolha outro com --teacher nos scripts 01/02.", file=sys.stderr)
        return 1

    print("Remova de ALLOWED_TEACHERS os que aparecem como AUSENTE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
