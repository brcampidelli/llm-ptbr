#!/usr/bin/env bash
# Prepara os dados do gate #1 NO POD: fatia de 1,06B tokens do dados22b (PT, 32k) + val + meta.
# Copia para o disco do container para nao disputar I/O do volume com o run principal.
set -eu
ORIG=${ORIG:-/workspace/dados22b}; DEST=${DEST:-/root/gate_muon/dados}; N=${N:-1060000000}   # DEST no disco do CONTAINER (/workspace e o volume de rede compartilhado com o run)
mkdir -p "$DEST"
python3 - "$ORIG" "$DEST" "$N" <<'PY'
import sys, json, numpy as np, pathlib, hashlib
orig, dest, n = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
tr = np.memmap(orig / "train.bin", dtype=np.uint16, mode="r")
assert len(tr) >= n, (len(tr), n)
# fatia do MEIO do corpus (o inicio e' faixa A pura; o meio mistura A/B/C como o run real)
ini = (len(tr) - n) // 2
np.asarray(tr[ini:ini + n]).tofile(dest / "train.bin")
val = np.fromfile(orig / "val.bin", dtype=np.uint16); val.tofile(dest / "val.bin")
meta = json.load(open(orig / "meta.json")); meta.update({"_gate": "muon_50m", "_fatia": [int(ini), int(ini + n)], "_origem": str(orig)})
json.dump(meta, open(dest / "meta.json", "w"), indent=1)
h = hashlib.md5(open(dest / "train.bin", "rb").read(1 << 26)).hexdigest()[:12]
print(f"train.bin: {n:,} tokens (fatia [{ini:,}, {ini+n:,}) de {len(tr):,}) · val.bin {len(val):,} tokens · md5 dos 64 MB iniciais {h}")
PY
ls -la "$DEST"
