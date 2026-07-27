"""Fase 2.2 — Traduzir datasets SFT de alta qualidade (EN) para PT-BR, com controle de qualidade.

Pega datasets abertos de referência (Tulu 3, OpenHermes, UltraFeedback...) e traduz
instrução+resposta para português usando um modelo ABERTO como tradutor.

QC aplicado a cada par traduzido:
  - tradução não pode estar vazia nem virar cópia do inglês
  - razão de tamanho PT/EN dentro de uma faixa sã (pega truncamento e alucinação)
  - "portuguesidade" mínima (pega tradução que ficou em inglês)

Uso:
    python data/02_translate_qc.py --dataset allenai/tulu-3-sft-mixture --limit 500
    python data/02_translate_qc.py --dataset ... --dry-run

Requer: OPENROUTER_API_KEY e `pip install datasets`.
Retomável (pula o que já foi traduzido).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import MIN_PT_RATIO, RAW_DIR, assert_teacher_allowed, ensure_dirs  # noqa: E402
from common import pt_ratio, read_jsonl  # noqa: E402
from importlib import import_module  # noqa: E402

TRANSLATE_SYSTEM = (
    "Você é um tradutor profissional EN→PT-BR. Traduza o texto do usuário para "
    "português brasileiro natural e fluente. Preserve formatação, código, números "
    "e nomes próprios. Responda APENAS com a tradução, sem comentários."
)

# Faixa sã de razão de comprimento PT/EN. Português costuma ficar ~10-30% maior.
MIN_LEN_RATIO = 0.6
MAX_LEN_RATIO = 2.2


def translate(text: str, model: str, api_key: str, timeout: int = 120) -> str:
    import urllib.request

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 3000,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"].strip()


def qc_pass(en: str, pt: str) -> tuple[bool, str]:
    """Retorna (passou, motivo_da_rejeicao)."""
    if not pt or len(pt) < 10:
        return False, "traducao vazia/curta"
    if pt.strip() == en.strip():
        return False, "traducao identica ao original (nao traduziu)"
    ratio = len(pt) / max(len(en), 1)
    if not (MIN_LEN_RATIO <= ratio <= MAX_LEN_RATIO):
        return False, f"razao de tamanho suspeita ({ratio:.2f})"
    if pt_ratio(pt) < MIN_PT_RATIO:
        return False, f"portuguesidade baixa ({pt_ratio(pt):.2f})"
    return True, ""


def extract_pair(row: dict) -> tuple[str, str] | None:
    """Normaliza os formatos mais comuns de dataset SFT para (instrucao, resposta)."""
    if "messages" in row and isinstance(row["messages"], list):
        user = next((m.get("content") for m in row["messages"] if m.get("role") == "user"), None)
        asst = next((m.get("content") for m in row["messages"] if m.get("role") == "assistant"), None)
        if user and asst:
            return user, asst
    for ik, ok in (("instruction", "output"), ("prompt", "response"), ("question", "answer")):
        if row.get(ik) and row.get(ok):
            return row[ik], row[ok]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="id do dataset no Hugging Face")
    ap.add_argument("--split", default="train")
    # tradução não exige teacher forte — mistral-nemo é Apache-2.0, tem PT explícito
    # e custa $0,019/$0,03 por 1M (≈420 mil pares por US$10).
    ap.add_argument("--translator", default="mistralai/mistral-nemo")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.translator)
    ensure_dirs()

    tag = args.dataset.split("/")[-1].lower().replace("-", "_")
    out_path = RAW_DIR / f"translated_{tag}.jsonl"
    rejects_path = RAW_DIR / f"translated_{tag}.rejects.jsonl"

    try:
        load_dataset = import_module("datasets").load_dataset
    except ModuleNotFoundError:
        print("ERRO: falta `pip install datasets`.", file=sys.stderr)
        return 1

    print(f"carregando {args.dataset} [{args.split}] ...")
    ds = load_dataset(args.dataset, split=args.split, streaming=True)

    done: set[str] = set()
    if out_path.exists():
        done = {r["instruction_en"] for r in read_jsonl(out_path) if "instruction_en" in r}
        print(f"[retomada] {len(done)} ja traduzidos")

    if args.dry_run:
        print(f"[dry-run] traduziria ate {args.limit} pares -> {out_path}")
        for i, row in enumerate(ds):
            pair = extract_pair(row)
            if pair:
                print(f"  exemplo: {pair[0][:90]}")
            if i >= 2:
                break
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY.", file=sys.stderr)
        return 1

    ok = rejected = skipped = 0
    with out_path.open("a", encoding="utf-8") as fout, rejects_path.open("a", encoding="utf-8") as frej:
        for row in ds:
            if ok + rejected >= args.limit:
                break
            pair = extract_pair(row)
            if not pair:
                skipped += 1
                continue
            instr_en, resp_en = pair
            if instr_en in done:
                continue

            try:
                instr_pt = translate(instr_en, args.translator, api_key)
                time.sleep(args.sleep)
                resp_pt = translate(resp_en, args.translator, api_key)
            except Exception as e:  # rede/API — não derruba o lote
                print(f"  FALHA de traducao: {type(e).__name__}: {e}", file=sys.stderr)
                time.sleep(2.0)
                continue

            passed_i, why_i = qc_pass(instr_en, instr_pt)
            passed_r, why_r = qc_pass(resp_en, resp_pt)
            record = {
                "instruction": instr_pt,
                "response": resp_pt,
                "instruction_en": instr_en,
                "source": f"translated:{args.dataset}",
                "translator": args.translator,
            }
            if passed_i and passed_r:
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                fout.flush()
                ok += 1
            else:
                record["reject_reason"] = why_i or why_r
                frej.write(json.dumps(record, ensure_ascii=False) + "\n")
                rejected += 1

            if (ok + rejected) % 25 == 0:
                print(f"  ok={ok} rejeitados={rejected}")
            time.sleep(args.sleep)

    print(f"\nConcluido: {ok} aprovados, {rejected} rejeitados (QC), {skipped} sem formato reconhecido")
    print(f"  -> {out_path}")
    print(f"  -> rejeitados em {rejects_path} (revisar para calibrar o QC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
