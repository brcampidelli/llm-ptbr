"""E6 com TRÊS SEMENTES POR BRAÇO — o único jeito de o gate voltar a decidir algo.

🔴 POR QUE. Medido em 2026-08-23: a mesma receita de SFT, mesmo dado, só trocando a semente,
move 4,7 pp e troca 14 dos 85 casos. O limiar de adoção do gate era 5 pp — abaixo do ruído do
próprio aparato. Com uma semente por braço, +5,9 pp do DPO é indistinguível de retreinar.

⭐ CADA SEMENTE É UMA RÉPLICA COMPLETA, não só uma semente no último passo. O braço DPO da
semente 43 parte do CONTROLE da semente 43. Ramificar os quatro braços de um controle único
mediria só a variância do DPO e esconderia a do SFT que veio antes — que é justamente a maior.

    semente s ->  sem-RS(s)                    (controle negativo: RS ajuda?)
                  ctrl-SFT+RS(s)               (o controle do gate)
                     +-- DPO(s) IPO(s) KTO-restrito(s) KTO-completo(s)

⚠️ O QUE ISTO NÃO CONSERTA: o holdout tem 85 itens e o intervalo de Wilson segue ±10 pp. Três
sementes dão a variância ENTRE rodadas, não mais poder sobre itens novos. O ganho é poder
dizer "o efeito é maior que o ruído de treino", não "o efeito generaliza".

Uso:
    python comeia/train/rodar_e6_sementes.py --sementes 42 43 44
    python comeia/train/rodar_e6_sementes.py --sementes 42 43 44 --so-agregar
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable
PROC = RAIZ / "data" / "processed"
MODELOS = RAIZ / "models"
RESULTS = RAIZ / "eval" / "results"
BASE = "BrCamp/bee-350m-pt-base"

# adapters da semente 42 que ja' existem com outro nome — reaproveitados, nao retreinados
APELIDOS = {
    ("sem-rs", 42): "e6-ctrl-sem-rs",
    ("sem-rs", 43): "e6-semente43",
    ("ctrl", 42): "e6-ctrl-sft-rs",
    ("dpo", 42): "e6-dpo",
    ("ipo", 42): "e6-ipo",
    ("kto-restrito", 42): "e6-kto-restrito",
    ("kto-completo", 42): "e6-kto-completo",
}
TAGS_EVAL = {
    ("sem-rs", 42): "e6-sem-rs", ("sem-rs", 43): "e6-semente43",
    ("ctrl", 42): "e6-ctrl", ("dpo", 42): "e6-dpo", ("ipo", 42): "e6-ipo",
    ("kto-restrito", 42): "e6-kto-restrito", ("kto-completo", 42): "e6-kto-completo",
}

PREFERENCIA = [
    ("dpo", ["--data", str(PROC / "e6_pares_v2c.jsonl"), "--loss-type", "sigmoid"]),
    ("ipo", ["--data", str(PROC / "e6_pares_v2c.jsonl"), "--loss-type", "ipo"]),
    # KTO exige batch REAL > 1: o KL dele compara dentro do lote
    ("kto-restrito", ["--data", str(PROC / "e6_kto_restritoc.jsonl"), "--kto",
                      "--batch-size", "2", "--grad-accum", "8"]),
    ("kto-completo", ["--data", str(PROC / "e6_kto_completoc.jsonl"), "--kto",
                      "--batch-size", "2", "--grad-accum", "8"]),
]
SFT = [("sem-rs", PROC / "sft_grupo_ferramenta.jsonl"),
       ("ctrl", PROC / "e6_ctrl_sft_rs.jsonl")]


def dir_de(braco: str, s: int) -> Path:
    return MODELOS / APELIDOS.get((braco, s), f"e6-{braco}-s{s}")


def tag_de(braco: str, s: int) -> str:
    return TAGS_EVAL.get((braco, s), f"e6-{braco}-s{s}")


def rodar(cmd: list[str], log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with log.open("w", encoding="utf-8") as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
    print(f"    rc={r.returncode} · {(time.time() - t0) / 60:.1f} min · {log.name}", flush=True)
    return r.returncode


def main() -> int:
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--logs", type=Path, default=Path.home() / "AppData/Local/Temp/e6logs")
    ap.add_argument("--so-agregar", action="store_true")
    a = ap.parse_args()
    a.logs.mkdir(parents=True, exist_ok=True)

    if not a.so_agregar:
        for s in a.sementes:
            print(f"===== SEMENTE {s} " + "=" * 50, flush=True)
            for braco, dados in SFT:
                d = dir_de(braco, s)
                if d.exists():
                    print(f"  {braco}-s{s}: ja' existe", flush=True)
                    continue
                print(f"  treinando {braco}-s{s}", flush=True)
                rodar([PY, "-u", str(RAIZ / "train" / "sft_qlora.py"), "--model", BASE,
                       "--data", str(dados), "--lr", "1.2e-3", "--epochs", "2",
                       "--batch-size", "1", "--grad-accum", "16", "--seed", str(s),
                       "--out", str(d)], a.logs / f"sft_{braco}_s{s}.log")
            ctrl = dir_de("ctrl", s)
            if not ctrl.exists():
                print(f"  ⚠️ sem controle da semente {s} — bracos de preferencia pulados")
                continue
            for braco, extra in PREFERENCIA:
                d = dir_de(braco, s)
                if d.exists():
                    print(f"  {braco}-s{s}: ja' existe", flush=True)
                    continue
                print(f"  treinando {braco}-s{s} (a partir do controle da MESMA semente)",
                      flush=True)
                rodar([PY, "-u", str(RAIZ / "train" / "dpo_qlora.py"), "--model", BASE,
                       "--sft-adapter", str(ctrl), "--out", str(d), "--lr", "5e-6",
                       "--beta", "0.1", "--epochs", "1"] + extra,
                      a.logs / f"pref_{braco}_s{s}.log")

        print("===== AVALIACAO " + "=" * 52, flush=True)
        for s in a.sementes:
            for braco in ["sem-rs", "ctrl"] + [b for b, _ in PREFERENCIA]:
                d, t = dir_de(braco, s), tag_de(braco, s)
                if not d.exists():
                    continue
                if (RESULTS / f"casos_{t}.jsonl").exists():
                    continue
                print(f"  avaliando {braco}-s{s}", flush=True)
                rodar([PY, "-u", str(RAIZ / "eval" / "eval_agentic_exec.py"), "--model", BASE,
                       "--peft", str(d), "--chat", "--k", "1", "--parar-controle",
                       "--tag", t, "--dump"], a.logs / f"eval_{braco}_s{s}.log")

    # ── agregacao
    print()
    print("=" * 84)
    print(f"E6 COM {len(a.sementes)} SEMENTES — media +- amplitude por braco")
    print("=" * 84)
    dados: dict[str, dict[int, dict]] = {}
    for braco in ["sem-rs", "ctrl"] + [b for b, _ in PREFERENCIA]:
        for s in a.sementes:
            f = RESULTS / f"exec_{tag_de(braco, s)}.json"
            if f.exists():
                dados.setdefault(braco, {})[s] = json.loads(f.read_text(encoding="utf-8"))

    print(f"{'braco':16} " + "".join(f"{'s' + str(s):>8}" for s in a.sementes)
          + f"{'media':>9}{'ampl':>7}{'over medio':>12}")
    for braco in ["sem-rs", "ctrl"] + [b for b, _ in PREFERENCIA]:
        d = dados.get(braco, {})
        vs = [d[s]["exec_ok"] for s in a.sementes if s in d]
        ov = [d[s]["over_call"] for s in a.sementes if s in d]
        if not vs:
            print(f"{braco:16} " + "  (sem rodadas)")
            continue
        cel = "".join(f"{d[s]['exec_ok']:>8}" if s in d else f"{'--':>8}" for s in a.sementes)
        print(f"{braco:16} {cel}{sum(vs)/len(vs):>9.1f}{max(vs)-min(vs):>7}"
              f"{sum(ov)/len(ov):>12.1f}")

    # ⭐ o teste que importa: diferenca PAREADA POR SEMENTE contra o controle da MESMA semente.
    #    Comparar medias entre bracos misturaria a variancia de semente de volta.
    ctrl = dados.get("ctrl", {})
    if ctrl:
        print()
        print("folga contra o controle DA MESMA SEMENTE (o unico pareamento valido):")
        print(f"{'braco':16} " + "".join(f"{'s' + str(s):>8}" for s in a.sementes)
              + f"{'media':>9}{'ampl':>7}   veredito")
        for braco, _ in PREFERENCIA:
            d = dados.get(braco, {})
            dif = [d[s]["exec_ok"] - ctrl[s]["exec_ok"]
                   for s in a.sementes if s in d and s in ctrl]
            if not dif:
                continue
            m = sum(dif) / len(dif)
            pp = m / 85 * 100
            amp = max(dif) - min(dif)
            # ⚠️ o efeito so' conta se a MEDIA passar o limiar E o sinal for consistente
            consistente = all(x > 0 for x in dif) or all(x < 0 for x in dif)
            v = ("ADOTAR" if pp >= 5 and consistente else
                 "NAO ADOTAR" if pp < 5 else "INCONSISTENTE entre sementes")
            cel = "".join(f"{d[s]['exec_ok'] - ctrl[s]['exec_ok']:>+8}"
                          if s in d and s in ctrl else f"{'--':>8}" for s in a.sementes)
            print(f"{braco:16} {cel}{pp:>+8.1f}pp{amp:>7}   {v}")
        print()
        print("⚠️ 'consistente' = mesmo sinal nas tres sementes. Media acima do limiar com")
        print("   sinal trocando entre sementes e' ruido com sorte, nao efeito.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
