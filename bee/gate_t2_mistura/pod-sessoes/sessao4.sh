#!/usr/bin/env bash
# Pre-requisito #6 do gate de sucesso: bal-12 e pt-50 a 350M — transferencia de ESCALA.
#
# DESENHO (declarado antes de rodar):
#   · MESMO horizonte da replicacao de 09-04 a 170M: 3.051 passos x 32.768 tok = 100M tokens,
#     mesmos pools (pool_bal-12.bin / pool_pt-50.bin), mesmo holdout, 3 sementes.
#     So' a ESCALA muda (§2g: mesmos itens, mesma regua, mesmo n).
#   · LR: o 170M rodou a 3e-3, que e' 4,32x a Step Law dele neste horizonte (6,94e-4).
#     Para o 376M (vocab 64k, embedding amarrado) a Step Law da' 3,93e-4; a MESMA posicao
#     relativa e' 4,32 x 3,93e-4 = 1,69e-3. Manter 3e-3 poria o 350M a 7,6x do otimo dele
#     e a comparacao viraria afirmacao sobre LR (§2f). Schedule identico: OneCycle cos, 2%%.
#   · SANIDADE, decidida ANTES de ler o resultado: a 100M tokens o 376M tem de fechar com
#     perda_media_100 ABAIXO do 170M (pt-50 5,05 / bal-12 5,28). Se ficar acima, o braco
#     esta' quebrado por LR e a taxa de troca dele NAO e' evidencia (§2f: braco morto entra
#     na tabela com o motivo).
# 🔴 MEDIDO 22:43 UTC: com `set -e` sozinho o traceback do treino passou batido — o status do
#    pipeline `python | grep -v` e' o do grep. Sem pipefail, "SESSAO COMPLETA" saiu em 75 s
#    com zero modelos treinados.
set -eo pipefail
cd /root
bash espera_vram.sh 28000
echo "########## [1/2] TREINO 350M  $(date -u '+%H:%M UTC')"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_t2_mistura.py treinar \
  --escala 350m --bracos bal-12,pt-50 --sementes 42,43,44 --passos 3051 --lr 1.7e-3 \
  2>&1 | grep -vE 'Loading|it/s\]'
bash espera_vram.sh 28000
echo "########## [2/2] AVALIACAO 350M  $(date -u '+%H:%M UTC')"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_t2_mistura.py avaliar \
  --escala 350m --bracos bal-12,pt-50 --sementes 42,43,44 \
  2>&1 | grep -vE 'Loading|it/s\]'
echo "########## SESSAO 4 COMPLETA  $(date -u '+%H:%M UTC')"
