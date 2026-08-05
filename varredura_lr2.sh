#!/bin/bash
# Extensao da varredura: a curva ainda descia em 6e-4, entao o joelho esta acima.
# 2e-3 e ~o LR do PRE-treino (3e-3) — se ainda melhorar ali, o sinal e' de que
# o SFT estava subtreinado por LR o tempo todo, nao de que achamos o otimo.
cd "C:/Users/brcam/Desktop/Desenvolvendo Projetos/Desenvolvendo LLM"
for lr in 1e-3 2e-3; do
  echo "=== LR $lr ==="
  .venv/Scripts/python.exe bee/sft.py \
    --modelo models/bee-150m-v3-base \
    --dados comeia/data/processed/sft_combinado.jsonl \
    --epocas 1 --lr $lr --save-steps 999 \
    --out models/_lr_$lr > docs/lr-$lr.log 2>&1
done
echo "EXTENSAO CONCLUIDA"
