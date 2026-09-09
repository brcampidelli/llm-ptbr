#!/usr/bin/env bash
# Lanca o pre-treino do Bee-1G de forma IDEMPOTENTE. Roda NO POD.
#
# 🔴 POR QUE EXISTE. Ate 2026-09-09 havia duas rotas de relancamento — o supervisor de dentro
#    do contentor e o de fora, por ssh — e cada uma chamava o `pretrain.py` por conta propria.
#    Duas rotas independentes para a MESMA acao significa que, no dia em que as duas dispararem
#    juntas, dois treinos escrevem o mesmo checkpoint.pt na mesma GPU. A trava do supervisor
#    externo nao resolve isso: ela e' local a maquina dele, e o outro supervisor esta em outra.
#
# ✅ A trava tem de morar ONDE A ACAO ACONTECE. Aqui: no pod. Quem chega primeiro lanca; o
#    segundo ve o log fresco e nao faz nada. As duas rotas continuam existindo — e' bom que
#    existam, sao modos de falha diferentes — mas convergem para UM lugar que decide.
#
# ⚠️ E ha uma janela que a checagem por mtime sozinha NAO cobre: carregar 12,6 GB de checkpoint
#    leva ~4 min sem escrever no log. Nessa janela o segundo chamador leria "parado" e lancaria
#    um gemeo. Por isso ha um segundo carimbo, .lancado_em, com prazo proprio.
#
# Saida: LANCADO | JA_VIVO <s> | LANCADO_RECENTE <s> | OUTRO_LANCADOR <pid>
set -u
cd /workspace/bee1g || exit 1
LOG=/workspace/bee1g/treino.log
LOCK=/workspace/bee1g/.lancar.lock
CARIMBO=/workspace/bee1g/.lancado_em
PARADO_MAX=${PARADO_MAX:-420}   # log parado alem disto = treino morto
CARENCIA=${CARENCIA:-600}       # tempo de carregar o checkpoint, sem escrever no log

if ! mkdir "$LOCK" 2>/dev/null; then
  v=$(cat "$LOCK/pid" 2>/dev/null || echo 0)
  if kill -0 "$v" 2>/dev/null; then echo "OUTRO_LANCADOR $v"; exit 5; fi
  rm -rf "$LOCK"; mkdir "$LOCK" || exit 5    # lock orfao de pid morto e' assumido
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

agora=$(date +%s)
desde_lanc=$(( agora - $(cat "$CARIMBO" 2>/dev/null || echo 0) ))
[ "$desde_lanc" -lt "$CARENCIA" ] && { echo "LANCADO_RECENTE $desde_lanc"; exit 0; }
parado=$(( agora - $(stat -c %Y "$LOG" 2>/dev/null || echo 0) ))
[ "$parado" -le "$PARADO_MAX" ] && { echo "JA_VIVO $parado"; exit 0; }

echo "$agora" > "$CARIMBO"
{ echo; echo "### LANCADO por $(hostname) $(date -u +%FT%TZ) — log estava parado ha ${parado}s"; } >> "$LOG"
setsid nohup env PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python3 bee/pretrain.py \
  --tamanho 1b --vocab 64000 --dados pool --tokenizer bee/tok_t1/64k-multi \
  --out /workspace/bee1g/bee-1g --epocas 1.0 --micro-batch 4 --grad-accum 4 \
  --schedule wsd --lr 9.61e-4 --lr-estavel-frac 0.55 \
  --marcos 1,3,6,10,15,20 --ckpt-cada 250 --sem-liger --sem-compilar \
  >> "$LOG" 2>&1 < /dev/null &
echo "LANCADO"
