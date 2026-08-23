"""E6 — roda os bracos de preferencia em sequencia e avalia todos com a MESMA regua.

Bracos (o controle e' SFT+RS, NUNCA SFT puro — comparar contra SFT puro reproduziria o falso
positivo que o plano avisa):

    ctrl          SFT + rejection sampling            (treinado a' parte, ver --ctrl)
    dpo           + DPO   (sigmoid)  sobre 930 pares
    ipo           + IPO   (arXiv:2310.12036 — preferencia de VERIFICADOR e' deterministica,
                           o regime exato em que o DPO degenera qualquer que seja o beta)
    kto-restrito  + KTO   so' nos prompts que tambem viraram par   -> comparavel com DPO/IPO
    kto-completo  + KTO   em tudo que o KTO alcanca (misto + all_right) -> "vale a pena?"

⚠️ Os dois KTO existem porque ele alcanca 657 prompts contra 324 dos outros. Um KTO que ganhe
so' no modo completo mediu VOLUME, nao funcao de perda (§2g).

Criterio declarado ANTES: adotar so' com folga >= 5 pp na execucao E sem perda >= 2 pp nas
outras reguas. Expectativa honesta do plano: 0 a +3 pp, com probabilidade real de sinal
negativo. Se render menos de 5 pp o resultado e' "nao adotar" — NAO "repetir com outro beta".

Uso:
    python comeia/train/rodar_e6.py --ctrl comeia/models/e6-ctrl-sft-rs
    python comeia/train/rodar_e6.py --ctrl ... --so-avaliar
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent      # comeia/
PY = sys.executable
PROC = RAIZ / "data" / "processed"
MODELOS = RAIZ / "models"
BASE = "BrCamp/bee-350m-pt-base"

# (tag, argumentos extras do dpo_qlora)
BRACOS = [
    ("dpo", ["--data", str(PROC / "e6_pares_v2c.jsonl"), "--loss-type", "sigmoid"]),
    ("ipo", ["--data", str(PROC / "e6_pares_v2c.jsonl"), "--loss-type", "ipo"]),
    # ⚠️ KTO exige batch REAL > 1 (nao efetivo): o termo de KL dele compara DENTRO do lote,
    #    e com batch 1 ele vira identico ao reward implicito — a TRL recusa, com razao.
    #    2 x 8 mantem o batch efetivo em 16, igual aos outros bracos.
    ("kto-restrito", ["--data", str(PROC / "e6_kto_restritoc.jsonl"), "--kto",
                      "--batch-size", "2", "--grad-accum", "8"]),
    ("kto-completo", ["--data", str(PROC / "e6_kto_completoc.jsonl"), "--kto",
                      "--batch-size", "2", "--grad-accum", "8"]),
]


def rodar(cmd: list[str], log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"  $ {' '.join(cmd[1:4])} ... -> {log.name}", flush=True)
    t0 = time.time()
    with log.open("w", encoding="utf-8") as fh:
        # -u: sem isto o log fica VAZIO ate' o processo morrer, e progresso invisivel e'
        #     indistinguivel de travamento (lição do E5).
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
    print(f"    -> rc={r.returncode} em {(time.time() - t0) / 60:.1f} min", flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctrl", type=Path, required=True, help="adapter do controle SFT+RS")
    ap.add_argument("--logs", type=Path,
                    default=Path.home() / "AppData/Local/Temp/e6logs")
    ap.add_argument("--lr", type=float, default=5e-6,
                    help="⚠️ DPO usa LR 1e-6..5e-6, NUNCA o 6e-4 do SFT. SmolLM2 usa 1e-6 "
                         "com beta 0,5 inclusive em 135M/360M.")
    ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--so-avaliar", action="store_true")
    a = ap.parse_args()
    a.logs.mkdir(parents=True, exist_ok=True)

    if not a.ctrl.exists():
        print(f"ERRO: controle {a.ctrl} nao existe — treine-o antes", file=sys.stderr)
        return 2

    # ── treino
    if not a.so_avaliar:
        print("=" * 70)
        print("TREINO DOS BRACOS DE PREFERENCIA (partindo do controle SFT+RS)")
        print("=" * 70)
        for tag, extra in BRACOS:
            saida = MODELOS / f"e6-{tag}"
            if saida.exists():
                print(f"  {tag}: ja' existe, pulando")
                continue
            rc = rodar([PY, "-u", str(RAIZ / "train" / "dpo_qlora.py"),
                        "--model", BASE, "--sft-adapter", str(a.ctrl),
                        "--out", str(saida), "--lr", f"{a.lr:g}", "--beta", f"{a.beta:g}",
                        "--epochs", str(a.epochs)] + extra,
                       a.logs / f"treino_{tag}.log")
            if rc != 0:
                print(f"  ⚠️ {tag} falhou (rc={rc}) — segue para o proximo; o braco entra")
                print("     na tabela final como FALHOU, nao omitido (omitir faria 'testado e")
                print("     morreu' parecer 'nao testado').")

    # ── avaliacao: MESMA regua, greedy (deterministico), com despejo por caso
    print()
    print("=" * 70)
    print("AVALIACAO — greedy, mesma regua, despejo por caso para o teste pareado")
    print("=" * 70)
    alvos = [("ctrl", a.ctrl)] + [(t, MODELOS / f"e6-{t}") for t, _ in BRACOS]
    prontos = []
    for tag, cam in alvos:
        if not cam.exists():
            print(f"  {tag}: adapter ausente — NAO avaliado")
            continue
        res = RAIZ / "eval" / "results" / f"casos_e6-{tag}.jsonl"
        if res.exists():
            print(f"  {tag}: ja' avaliado")
            prontos.append((tag, res))
            continue
        rc = rodar([PY, "-u", str(RAIZ / "eval" / "eval_agentic_exec.py"),
                    "--model", BASE, "--peft", str(cam), "--chat", "--k", "1",
                    "--parar-controle", "--tag", f"e6-{tag}", "--dump"],
                   a.logs / f"eval_{tag}.log")
        if rc == 0 and res.exists():
            prontos.append((tag, res))

    # ── comparacao pareada
    base = next((r for t, r in prontos if t == "ctrl"), None)
    outros = [r for t, r in prontos if t != "ctrl"]
    if base and outros:
        print()
        subprocess.run([PY, "-u", str(RAIZ / "eval" / "comparar_pareado.py"),
                        "--base", str(base), "--braco"] + [str(x) for x in outros])
    else:
        print("\n⚠️ sem controle avaliado ou sem bracos — nao ha' comparacao a fazer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
