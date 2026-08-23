"""Rejulga reforco e pares com o executor ATUAL, em vez de descartar as belas.

🔴 POR QUE (E6, 2026-08-22). O rejection sampling foi colhido com `run_python` devolvendo
`{"compila": True}` e `run_sql` devolvendo `{"linhas": [{"n": 1}]}` — CONSTANTES. Qualquer
entrada valida "acertava", e entraram 116 exemplos de reforco e 32 pares sem informacao
nenhuma (`{"code": "f"}` entre eles).

Corrigidas as ferramentas, o certo nao e' jogar fora tudo que veio delas — e' **executar de
novo** e manter o que sobrevive. Descartar por origem puniria tambem os exemplos que estavam
certos; rejulgar separa os dois.

⚠️ Rejulgar so' e' possivel porque o gabarito e' recuperavel: o prompt do exemplo colhido e' o
MESMO do treino, entao da' para reencontrar a referencia. Sem isso, restaria descartar.

Uso:
    python comeia/data/rejulgar_colheita.py --treino .../sft_agentic.jsonl \\
        --reforco .../e6_reforco.jsonl --pares .../e6_pares.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "eval"))

import tools_exec as TE                                    # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)


def chave_prompt(msgs) -> str:
    return json.dumps(msgs, sort_keys=True, ensure_ascii=False)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--treino", type=Path, required=True)
    ap.add_argument("--reforco", type=Path, required=True)
    ap.add_argument("--pares", type=Path, required=True)
    a = ap.parse_args()

    TE.garantir_fixtures()

    # gabarito por prompt
    ref_de: dict[str, dict] = {}
    for ln in a.treino.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("kind") != "tool_call":
            continue
        msgs = list(r.get("prompt") or [])
        ref = next((m["content"] for m in (r.get("completion") or [])
                    if m["role"] == "assistant"), None)
        obj = _d7.extract_json(ref) if ref else None
        if obj:
            ref_de[chave_prompt(msgs)] = obj
    print(f"gabaritos recuperaveis: {len(ref_de)}")

    def bate(prompt, chamada_txt) -> bool | None:
        """None = nao da' para julgar (sem gabarito)."""
        ref_obj = ref_de.get(chave_prompt(prompt))
        if ref_obj is None:
            return None
        ok_r, res_r = TE.executar(ref_obj)
        if not ok_r:
            return None
        try:
            obj = json.loads(chamada_txt)
        except Exception:
            return False
        ok_p, res_p = TE.executar(obj)
        return bool(ok_p and TE.resultados_batem(res_p, res_r))

    # ── reforco
    linhas = [json.loads(l) for l in a.reforco.read_text(encoding="utf-8").splitlines() if l.strip()]
    mantidos, caidos, sem_juiz = [], Counter(), 0
    for r in linhas:
        if r.get("kind") != "tool_call":
            mantidos.append(r)                       # `text` nao passa por execucao
            continue
        v = bate(r["prompt"], r["completion"][0]["content"])
        if v is None:
            sem_juiz += 1
            continue
        if v:
            mantidos.append(r)
        else:
            try:
                caidos[json.loads(r["completion"][0]["content"]).get("tool")] += 1
            except Exception:
                caidos["?"] += 1
    n_tool_antes = sum(1 for r in linhas if r.get("kind") == "tool_call")
    n_tool_dep = sum(1 for r in mantidos if r.get("kind") == "tool_call")
    print()
    print(f"REFORCO  {len(linhas)} -> {len(mantidos)}   "
          f"(tool_call {n_tool_antes} -> {n_tool_dep}, caiu {sum(caidos.values())}, "
          f"sem gabarito {sem_juiz})")
    for t, n in caidos.most_common():
        print(f"    caiu  {t:24} {n}")

    # ── pares: chosen tem de continuar certo E rejected tem de continuar errado
    pares = [json.loads(l) for l in a.pares.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok_pares, motivos = [], Counter()
    for r in pares:
        c = bate(r["prompt"], r["chosen"])
        e = bate(r["prompt"], r["rejected"])
        if c is None or e is None:
            motivos["sem gabarito"] += 1
        elif not c:
            motivos["chosen deixou de acertar"] += 1
        elif e:
            motivos["rejected passou a acertar"] += 1
        else:
            ok_pares.append(r)
    print()
    print(f"PARES    {len(pares)} -> {len(ok_pares)}")
    for m, n in motivos.most_common():
        print(f"    caiu  {m:32} {n}")

    a.reforco.with_suffix(".rejulgado.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in mantidos), encoding="utf-8")
    a.pares.with_suffix(".rejulgado.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in ok_pares), encoding="utf-8")
    print()
    print(f"[OK] {a.reforco.with_suffix('.rejulgado.jsonl').name} · "
          f"{a.pares.with_suffix('.rejulgado.jsonl').name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
