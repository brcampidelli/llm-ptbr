#!/usr/bin/env bash
# Gate #1 do estudo do arXiv (2609.04577 + 2609.11655): Muon x AdamW, Bee-50M, 1,06B tokens/braco.
#
# O QUE DECIDE: o otimizador do PROXIMO pre-treino. O artigo mede 1,3-1,9x de eficiencia de token
# no regime de overtraining (>= 20 tok/param). Aqui: 53M params x 1,06B tokens = 20 tok/param —
# o INICIO do regime do artigo (1x Chinchilla), nao o meio. Um 50M em vez do 150M porque no 150M
# o mesmo regime custaria 3B tokens por braco (US$ 53 nos 4 bracos).
#
# DESENHO (declarado antes de rodar):
#   4 bracos pareados: {adamw, muon} x {semente 42, 43}, MESMO train.bin (1,06B tokens de PT 32k,
#   fatia de dados22b), MESMO schedule WSD, MESMO lr de pico pela Step Law (3,3e-3).
#   + 2 bracos de sensibilidade: {adamw, muon} a 3x lr, semente 42 — §2f: nao comparar um
#   otimizador perto do otimo dele com o outro longe do dele.
#   Metrica: val loss/ppl no val.bin (mesmo tokenizador em todos = pareado). PISO DE RUIDO: a
#   diferenca entre as duas sementes de AdamW. Muon so "ganha" se a folga passar desse piso.
#   ⚠️ Nao ha ancora publicada para o 50M. Os dois AdamW ancoram um ao outro.
#
# O QUE NAO MOSTRA: regime de 4-8x Chinchilla (o artigo cobre ate la); modelo de 1B; 64k
# multilingue. Se o Muon empatar aqui, o artigo NAO esta refutado — so nao esta confirmado onde
# custava US$ 8 confirmar.
#
# Uso (no pod, em /workspace/gate_muon): bash bee/gate_muon_50m.sh
set -u
cd "$(dirname "$0")/.."
DADOS=${DADOS:-/workspace/gate_muon/dados}      # train.bin (1,06B tok) + val.bin + meta.json
TOK=${TOK:-/workspace/bee-150m-pt-base}           # o tokenizador 32k do 150M/350M (so decodifica amostras)
OUT=${OUT:-/workspace/gate_muon/saidas}
LR=${LR:-3.3e-3}
LR3=$(python3 -c "print($LR*3)")
COMUM="--tamanho 50m --dados $DADOS --tokenizer $TOK --epocas 1.0 --micro-batch 16 --grad-accum 2 \
       --schedule wsd --lr-estavel-frac 0.55 --ckpt-cada 1000000 --aval-cada 500 --amostra-cada 1000000 --sem-liger --sem-compilar"
mkdir -p "$OUT"
diz() { echo "[$(date -u '+%m-%d %H:%M UTC')] $*" | tee -a "$OUT/gate.log"; }

braco() {   # nome otimizador semente lr
  local nome=$1 opt=$2 sem=$3 lr=$4
  if [ -f "$OUT/$nome/FIM" ]; then diz "$nome ja concluido — pulando"; return 0; fi
  diz "INICIO $nome · $opt · semente $sem · lr $lr"
  env PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python3 bee/pretrain.py $COMUM \
      --otimizador "$opt" --seed "$sem" --lr "$lr" --out "$OUT/$nome" > "$OUT/$nome.log" 2>&1
  local rc=$?
  if [ $rc -eq 0 ]; then
    grep -aE "validação final|VALIDAÇÃO" "$OUT/$nome.log" | tail -1 | tee -a "$OUT/gate.log"
    touch "$OUT/$nome/FIM"; diz "FIM $nome (rc 0)"
  else
    diz "🔴 $nome FALHOU (rc $rc) — ver $OUT/$nome.log"; tail -5 "$OUT/$nome.log" | tee -a "$OUT/gate.log"
  fi
  return $rc
}

diz "gate muon x adamw · 50m · dados $DADOS · lr $LR (3x = $LR3)"
# pareados primeiro, alternando otimizadores para que uma queda no meio nao vicie o par
braco adamw_s42 adamw 42 "$LR"
braco muon_s42  muon  42 "$LR"
braco adamw_s43 adamw 43 "$LR"
braco muon_s43  muon  43 "$LR"
# sensibilidade a lr
braco adamw_lr3 adamw 42 "$LR3"
braco muon_lr3  muon  42 "$LR3"
diz "todos os bracos executados — consolidar com bee/gate_muon_50m_ler.py"
