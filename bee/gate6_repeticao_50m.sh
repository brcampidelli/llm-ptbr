#!/usr/bin/env bash
# Gate #6 do estudo do arXiv (2609.11917): repeticao de idioma escasso num modelo DENSO — Bee-50M/64k.
#
# O QUE DECIDE: se o deficit de dado nao-PT para o PROXIMO run (63B tokens => R≈3; 143-170B => R≈7-9
# por idioma, com os 1,43B unicos de cada um) e' bloqueio ou nao. O artigo mede em denso: R≤8 com
# degradacao "leve", forte so' apos R>64; e misturar o dominio repetido com um dominio grande NAO
# repetido protege quando os dois sao proximos. Medido entre GENEROS em ingles — aqui entre IDIOMAS.
#
# DESENHO (declarado antes de rodar) — 2x2 fatorial + 2 sementes extras:
#   {jpn unico 1,0B | jpn 125M x 8} x {sozinho | + 1,0B PT unico}, semente 42
#   + jpn_unico s43 e jpn_rep8 s43 (PISO DE RUIDO e a penalidade de repeticao com 2 sementes)
#   + jpn_rep3 s42 (333M x 3): a penalidade no R do run de 63B — acrescentado apos o R=8 dar +0,13
#   Modelo: ESCADA 50m com --vocab 64000 = 67,3M params instanciados (dry-run local) — a escala "80M" do artigo.
#   LR EXPLICITO 2,5e-3 em todos (§2d: com --lr 0 a Step Law derivaria LR diferente para 1B e 2B).
#   Metrica: val loss (nats/token) no HOLDOUT LIMPO DE JPN, mesma regua/tokenizador em todos.
#   Perguntas (respondidas por bee/gate6_ler.py, criterio la'):
#     (1) penalidade de repeticao = rep8 − unico, sozinho. > piso? quanto?
#     (2) a mistura protege? (rep8_mix − unico_mix) < (rep8 − unico) alem do piso?
#     (3) PT ajuda jpn? unico_mix − unico (transferencia/regularizacao sem repeticao)
# O QUE NAO MOSTRA: 1B params; R entre 8 e 64; os outros 6 idiomas; a diluicao real de 7% do pt-50
# (a mistura aqui e' 50/50); efeito em PT. Se empatar, o artigo NAO esta' refutado — o regime e' outro.
#
# Uso (no pod, dentro de /workspace/llm-ptbr, apos bee/gate6_preparar.sh): bash bee/gate6_repeticao_50m.sh
set -u
cd "$(dirname "$0")/.."
DADOS=${DADOS:-/root/gate6/dados}   # disco do container; /workspace e o volume de rede do run
TOK=${TOK:-/workspace/bee1g/bee/tok_t1/64k-multi}
OUT=${OUT:-/workspace/gate6/saidas}
LR=${LR:-2.5e-3}
COMUM="--tamanho 50m --vocab 64000 --tokenizer $TOK --epocas 1.0 --micro-batch 16 --grad-accum 2 \
       --schedule wsd --lr-estavel-frac 0.55 --lr $LR --ckpt-cada 1000000 --aval-cada 500 --amostra-cada 1000000 --sem-liger --sem-compilar"
mkdir -p "$OUT"
diz() { echo "[$(date -u '+%m-%d %H:%M UTC')] $*" | tee -a "$OUT/gate.log"; }

braco() {   # nome dados semente
  local nome=$1 dados=$2 sem=$3
  if [ -f "$OUT/$nome/FIM" ]; then diz "$nome ja concluido — pulando"; return 0; fi
  [ -f "$DADOS/$dados/train.bin" ] || { diz "🔴 dados ausentes: $DADOS/$dados (rode bee/gate6_preparar.sh)"; return 1; }
  diz "INICIO $nome · dados $dados · semente $sem · lr $LR"
  env PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python3 bee/pretrain.py $COMUM \
      --dados "$DADOS/$dados" --seed "$sem" --out "$OUT/$nome" > "$OUT/$nome.log" 2>&1
  local rc=$?
  if [ $rc -eq 0 ]; then
    grep -aE "validação final" "$OUT/$nome.log" | tail -1 | tee -a "$OUT/gate.log"
    touch "$OUT/$nome/FIM"; diz "FIM $nome (rc 0)"
  else
    diz "🔴 $nome FALHOU (rc $rc) — ver $OUT/$nome.log"; tail -5 "$OUT/$nome.log" | tee -a "$OUT/gate.log"
  fi
  return $rc
}

diz "gate #6 repeticao em denso · 50m/64k · lr $LR · dados $DADOS"
# o par que decide primeiro (sozinho), depois o par misturado, depois as sementes extras
braco jpn_unico_s42     jpn_unico     42
braco jpn_rep8_s42      jpn_rep8      42
braco jpn_unico_mix_s42 jpn_unico_mix 42
braco jpn_rep8_mix_s42  jpn_rep8_mix  42
braco jpn_unico_s43     jpn_unico     43
braco jpn_rep8_s43      jpn_rep8      43
# acrescentado 2026-09-17 (apos +0,13 nats em R=8): R=3 e' o regime de um run de 63B tokens no pt-50
braco jpn_rep3_s42      jpn_rep3      42
diz "todos os bracos executados — consolidar com bee/gate6_ler.py --saidas $OUT"
