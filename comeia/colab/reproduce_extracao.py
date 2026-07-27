"""Reproduz a abelha de EXTRAÇÃO do zero, num comando, em ~35 min de L4.

Por que existe: o adapter vive em `/content` no Colab e morre com o runtime. Já
perdemos um assim nesta sessão. Persistir na Drive resolve, mas o mount depende de
um fluxo OAuth interativo — então a defesa que NÃO depende de ninguém clicar em
nada é **reprodução barata e determinística**.

⭐ O que torna a reprodução confiável agora: o split é decidido por
`sha1(documento)` (data/13), não por embaralhar uma lista. Antes, regerar o gate
mudava o holdout inteiro (o gate não é bit-reproduzível — geração em lote muda o
padding e a aritmética junto, e duas execuções deram 513 e 510 difíceis). Com hash,
duas execuções do gate que diferem em 3 itens produzem holdouts que diferem nesses
3 — o treino de hoje continua válido contra o holdout de amanhã.

Uso (na L4):
    python colab/reproduce_extracao.py                          # tudo
    python colab/reproduce_extracao.py --out /content/drive/MyDrive/qwen35-4b-extracao
    python colab/reproduce_extracao.py --skip-gate              # gate já rodou
    python colab/reproduce_extracao.py --eval                    # + avaliar no fim

Etapas (cada uma pula se a saída já existe — retomável):
    1. gate    data/12  ~20 min   base nos 934 itens → hard/easy
    2. splits  data/13  instante  hash-estável, estratificado por idioma
    3. treino  train/   ~32 min   QLoRA 2 épocas, loss mascarada no prompt
    4. eval    eval/    ~11 min   (opcional) ganho + regressão + alucinação
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARD = ROOT / "data" / "raw" / "extraction_hard.jsonl"
TRAIN = ROOT / "data" / "processed" / "sft_extraction.jsonl"


def etapa(nome: str, cmd: list[str], pular_se: Path | None = None) -> bool:
    """Roda uma etapa, pulando se a saída já existe. False = falhou."""
    if pular_se and pular_se.exists() and pular_se.stat().st_size > 0:
        print(f"[{nome}] ⏭  já existe ({pular_se.name}), pulando")
        return True
    print(f"\n[{nome}] ▶ {' '.join(cmd[1:])}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    dt = time.time() - t0
    ok = r.returncode == 0
    print(f"[{nome}] {'✅' if ok else '❌'} {dt/60:.1f} min", flush=True)
    return ok


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/content/qwen35-4b-extracao",
                    help="onde salvar o adapter. ⚠️ /content MORRE com o runtime — "
                         "prefira um caminho na Drive se ela estiver montada.")
    ap.add_argument("--epochs", type=float, default=2.0,
                    help="2 = config medida (a coder mostrou 2 > 1 e > mistura)")
    ap.add_argument("--max-seq-len", type=int, default=1536,
                    help="⚠️ suba para 3072+ se o dataset tiver documentos LONGOS "
                         "(data/11 --doc-len longo), senão eles são truncados em silêncio")
    ap.add_argument("--batch-size", type=int, default=12, help="lote do gate/eval")
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--eval", action="store_true", help="avaliar no fim (+11 min)")
    args = ap.parse_args()

    py = sys.executable
    t0 = time.time()
    print(f"reproduzindo a abelha de extracao → {args.out}")
    print(f"epocas {args.epochs} | max_seq_len {args.max_seq_len}\n")

    if not args.skip_gate:
        if not etapa("1/4 gate", [py, "data/12_filter_extraction.py",
                                  "--batch-size", str(args.batch_size)], HARD):
            return 1
    if not etapa("2/4 splits", [py, "data/13_build_extraction_splits.py"], TRAIN):
        return 1
    if not etapa("3/4 treino", [py, "train/sft_qlora.py",
                                "--data", str(TRAIN), "--out", args.out,
                                "--epochs", str(args.epochs),
                                "--max-seq-len", str(args.max_seq_len)]):
        return 1
    if args.eval and not etapa("4/4 eval", [py, "eval/eval_extraction.py",
                                            "--peft", args.out,
                                            "--batch-size", str(args.batch_size),
                                            "--tag", "repro"]):
        return 1

    print(f"\n{'=' * 60}")
    print(f"✅ abelha reproduzida em {(time.time() - t0)/60:.1f} min → {args.out}")
    if args.out.startswith("/content/") and not args.out.startswith("/content/drive"):
        print("⚠️ este caminho MORRE no proximo runtime. Copie para a Drive:")
        print(f"   !cp -r {args.out} /content/drive/MyDrive/")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
