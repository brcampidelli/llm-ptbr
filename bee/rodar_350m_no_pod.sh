#!/usr/bin/env bash
# ⭐ LANCAMENTO DO BEE-350M NUMA RTX 5090 DO RUNPOD.
#
# Cola isto num terminal do JupyterLab do pod. Ele e' IDEMPOTENTE: se o pod cair e voltar,
# rodar de novo retoma de onde parou (o `pretrain.py` restaura modelo + otimizador +
# scheduler + POSICAO NO DADO a partir do checkpoint).
#
# ⚠️ ARRANJO DE DISCO — a licao de checkpoint persistente, aplicada:
#     /workspace         = network volume, 50 GB, SOBREVIVE ao pod  -> CHECKPOINTS
#     /corpus            = disco do container, 150 GB, APAGADO no stop -> CORPUS (44 GB)
#   O corpus vive no disco efemero de proposito: ele e' re-baixavel do HF em minutos, e
#   nao cabe no volume de 50 GB junto com os checkpoints.
#
# Custo medido: 112,5 h a US$ 1,02/h = ~US$ 115 (ver docs/throughput-350m-medido.md).

set -euo pipefail

CORPUS=/corpus
CKPT=/workspace/bee-350m
REPO=/workspace/llm-ptbr

echo "=============================================================="
echo " BEE-350M — preparo"
echo "=============================================================="
nvidia-smi --query-gpu=name,memory.total,power.limit --format=csv,noheader

# ---------------------------------------------------------------- 1) codigo
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" pull --ff-only
else
  git clone --depth 1 https://github.com/brcampidelli/llm-ptbr.git "$REPO"
fi
cd "$REPO"
echo "commit: $(git rev-parse --short HEAD)"

# ---------------------------------------------------------------- 2) dependencias
pip install -q -U "transformers>=5.14" liger-kernel huggingface_hub

# ---------------------------------------------------------------- 3) corpus
mkdir -p "$CORPUS"
if [ ! -s "$CORPUS/train.bin" ]; then
  echo "--- baixando corpus (43,5 GB) do HF ---"
  # ⚠️ HF_HUB_DISABLE_XET=1: o Xet faz dedup em RAM e derruba a transferencia.
  HF_HUB_DISABLE_XET=1 python - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download("BrCamp/bee-corpus-pt-22b", repo_type="dataset",
                      local_dir="/corpus", max_workers=8)
print("baixado em", p)
PY
fi
ls -l "$CORPUS"

# ---------------------------------------------------------------- 4) GUARDA: o corpus e' o certo?
# Tamanho e' necessario, nao suficiente — o hash e' que decide (licao registrada).
python bee/conferir_corpus.py "$CORPUS" || {
  echo "🔴 ABORTA: o corpus nao confere com a referencia."; exit 1; }

# ---------------------------------------------------------------- 5) o run
mkdir -p "$CKPT"
echo "=============================================================="
echo " BEE-350M — treino  (checkpoints em $CKPT, que sobrevive ao pod)"
echo "=============================================================="
exec python bee/pretrain.py \
  --tamanho 350m \
  --dados   "$CORPUS" \
  --tokenizer models/bee-150m-v3-base \
  --out     "$CKPT" \
  --tokens-alvo 21.75e9 \
  --micro-batch 8 --grad-accum 4 \
  --sem-checkpointing \
  --liger --sem-compilar \
  --schedule wsd --frac-decaimento 0.20 --lr-estavel-frac 0.55 \
  --ckpt-cada 500 \
  --marcos 1,3,6,10,15,21 \
  --aval-cada 500 --amostra-cada 2000 \
  2>&1 | tee -a "$CKPT/treino.log"
