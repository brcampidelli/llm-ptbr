"""G-C3 REALIZADO — o limiar movido, medido de verdade (§2r: o teto nao e' o ganho; o dano se mede DEPOIS).

O calibracao_poshoc.py estima um TETO: casos tool que o corte 0,5 perde e um τ menor recupera, vezes
P(exec_ok | chamou). Aqui a chamada e' GERADA para esses casos — greedy com o prefixo '{"tool": "' forcado
(eval_agentic_exec.py --forcar-chamada --indices), mesma config de referencia (§2aa) — e o executor diz
quantas cumprem. Gera-se UMA vez para o conjunto maximo (tool, nao chamado pelo greedy, p_call >= τ_min)
e toda a curva em τ sai do mesmo despejo.

Politica medida, para cada τ:  a decisao e' do LOGIT (p_call >= τ) e a geracao e' do greedy.
  • caso ja' chamado pelo greedy → inalterado (o despejo da eval)
  • tool nao chamado, p >= τ    → chamada forcada: exec_ok medido aqui
  • texto nao chamado, p >= τ   → vira over-call por CONSTRUCAO (nao precisa gerar: e' o custo exato)
  • p < τ                       → texto, inalterado
Saldo por τ: +Δexec_ok (medido) sobre 536 tool · +Δover_call (exato) sobre 268 texto.

⚠️ O que isto NAO mede: o greedy dos casos ja' chamados foi gerado noutra GPU (pod 4090) para 11 adapters
(§2ae, ~2 casos/536 de deriva) — os deltas aqui sao PAREADOS no mesmo caso, entao a deriva nao entra no
delta; entra so' na base absoluta.

Uso:
  python comeia/eval/calibracao_poshoc_realizado.py --peft comeia/models/e19c-s42 comeia/models/e19c-s43 comeia/models/e19c-s44
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPO = RAIZ.parent
LIMIARES = (0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1)
FLAGS_CFGREF = ["--k", "1", "--chat", "--parar-controle", "--restrito", "--restrito-ferramenta", "--por-argumento",
                "--lote", "16", "--max-len", "1700"]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", nargs="+", required=True)
    ap.add_argument("--data", default="comeia/data/processed/holdout_balanceado.eval.jsonl")
    ap.add_argument("--casos-dir", type=Path, default=RAIZ / "eval" / "results")
    ap.add_argument("--tau-min", type=float, default=0.1)
    ap.add_argument("--saida", default="docs/calibracao-poshoc-realizado-350m-2026-09-19.json")
    ap.add_argument("--so-ler", action="store_true", help="nao gera; so' le' despejos ja' existentes")
    a = ap.parse_args()

    saida = {"_regua": {"politica": "decisao pelo logit (p_call >= tau), geracao greedy com prefixo forcado; texto acima de tau = over-call por construcao",
                        "flags_eval": FLAGS_CFGREF + ["--forcar-chamada", "--indices"], "tau_min": a.tau_min, "limiares": LIMIARES}, "adapters": {}}
    for adp in a.peft:
        nome = Path(adp).name
        pc = a.casos_dir / f"casos_calib_{nome}.jsonl"
        calib = [json.loads(l) for l in pc.read_text(encoding="utf-8").splitlines() if l.strip()]
        chamou = lambda c: bool(c["greedy"] and (c["greedy"].get("chamou") if "chamou" in c["greedy"] else (c["greedy"].get("ferramenta_pred") or c["greedy"].get("over_call"))))
        iniciou = lambda c: bool(c["greedy"] and (c["greedy"]["iniciou_chamada"] if "iniciou_chamada" in c["greedy"] else (c["greedy"].get("bruto") or "").lstrip().startswith("{")))
        n_tool = sum(1 for c in calib if c["is_tool"]); n_text = len(calib) - n_tool
        base_exec = sum(1 for c in calib if c["is_tool"] and c["greedy"] and c["greedy"].get("exec_ok"))
        base_over = sum(1 for c in calib if not c["is_tool"] and chamou(c))
        # candidatos = under-call PROPRIO (o greedy nem comecou '{'); chamada quebrada (comecou e nao parseou) fica fora:
        # forcar o prefixo reproduz o mesmo bruto (medido: 0 de 11 recuperadas) — nao e' decisao, e' geracao
        quebradas = [c for c in calib if c["is_tool"] and iniciou(c) and not chamou(c)]
        cand = [c for c in calib if c["is_tool"] and not iniciou(c) and c["p_call"] >= a.tau_min]
        tag = f"gc3-forcado-{nome}"
        dj = a.casos_dir / f"casos_{tag}.jsonl"
        if not dj.exists() and not a.so_ler and cand:
            idx = a.casos_dir / f"indices_{tag}.json"
            idx.write_text(json.dumps([c["i"] for c in cand]), encoding="utf-8")
            cmd = [sys.executable, str(RAIZ / "eval" / "eval_agentic_exec.py"), "--model", a.model, "--peft", adp, "--data", a.data,
                   *FLAGS_CFGREF, "--forcar-chamada", "--indices", str(idx), "--tag", tag, "--dump"]
            print(f"\n{nome}: gerando {len(cand)} chamadas forcadas (tool nao chamados com p >= {a.tau_min}) …", flush=True)
            log = a.casos_dir / f"{tag}.log"
            with log.open("w", encoding="utf-8") as fh:
                rc = subprocess.run(cmd, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, env=os.environ).returncode
            if rc != 0 or not dj.exists():
                print(f"🔴 eval falhou (rc {rc}) — ver {log}"); continue
        forc = {}
        if dj.exists():
            forc = {d["i"]: d for d in (json.loads(l) for l in dj.read_text(encoding="utf-8").splitlines() if l.strip())}
        R = {"n_tool": n_tool, "n_text": n_text, "base_exec_ok": base_exec, "base_over_call": base_over,
             "under_call_greedy": sum(1 for c in calib if c["is_tool"] and not iniciou(c)), "chamadas_quebradas_tool": len(quebradas),
             "candidatos": len(cand), "gerados": len(forc), "tag": tag, "por_limiar": []}
        for t in LIMIARES:
            rec = [c for c in cand if c["p_call"] >= t]
            faltam = [c["i"] for c in rec if c["i"] not in forc]
            d_exec = sum(1 for c in rec if forc.get(c["i"], {}).get("exec_ok"))
            d_over = sum(1 for c in calib if not c["is_tool"] and not iniciou(c) and c["p_call"] >= t)
            R["por_limiar"].append({"tau": t, "recuperados": len(rec), "exec_ok_recuperados": d_exec,
                                    "p_exec_ok_recuperados": d_exec / len(rec) if rec else None, "novos_over_call": d_over,
                                    "exec_ok_total": base_exec + d_exec, "over_call_total": base_over + d_over,
                                    "delta_pp_exec_ok": 100 * d_exec / n_tool, "delta_pp_over_call": 100 * d_over / n_text,
                                    "sem_geracao": len(faltam)})
        saida["adapters"][nome] = R
        print(f"\n{nome}  base: exec_ok {base_exec}/{n_tool} · over {base_over}/{n_text} · under-call {R['under_call_greedy']} (+ {len(quebradas)} chamadas quebradas, fora) · candidatos p>={a.tau_min}: {len(cand)} · gerados {len(forc)}")
        for d in R["por_limiar"]:
            pe = "—" if d["p_exec_ok_recuperados"] is None else f"{d['p_exec_ok_recuperados']:.2f}"
            print(f"  τ {d['tau']:.2f}  recupera {d['recuperados']:3d} → exec_ok {d['exec_ok_recuperados']:3d} ({pe}) · novos over {d['novos_over_call']:3d}"
                  f"  ⇒ exec_ok {d['exec_ok_total']}/{n_tool} ({d['delta_pp_exec_ok']:+.1f} pp) · over {d['over_call_total']}/{n_text} ({d['delta_pp_over_call']:+.1f} pp)"
                  + (f"  ⚠️ {d['sem_geracao']} sem geracao" if d["sem_geracao"] else ""))
    Path(a.saida).write_text(json.dumps(saida, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsalvo em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
