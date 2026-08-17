#!/usr/bin/env bash
# ⭐ FORK DE DECAIMENTO — o experimento que separa DUAS hipoteses que a curva pareada
#    do Bee-350M nao distingue.
#
# O FATO A EXPLICAR: comparado ao Bee-150M no MESMO numero de tokens, o 350M sai
#   1B  -4,55%  ·  3B  -0,90%  ·  6B  +0,66%  ·  10B  +2,52%
# — deteriorando monotonicamente. Duas leituras cabem no mesmo dado:
#
#   (a) ARTEFATO DE SCHEDULE. O 150M usou cosine e ja vinha COLHENDO decaimento nesses
#       pontos (LR em 99,8% → 96,8% → 85,7% → 62,2% do pico). O 350M usa WSD e esta
#       cravado no plato de 55%. Compara-se um modelo que esta assentando com outro que
#       ainda esta explorando: o segundo SEMPRE parece pior, e a diferenca some no fim.
#   (b) SUBTREINO REAL. O 350M vai a 63 tokens/parametro contra 143 do 150M.
#
# ⚠️ Antecipar o decaimento no run PRINCIPAL nao testaria a hipotese — CONSUMIRIA ela:
#    se o modelo saltasse, nao daria para saber se foi o decaimento ou o dado a mais.
#    Por isso: BIFURCA. Uma copia do estado atual decai; o principal segue intocado.
#
# O DESENHO:
#   · parte do `checkpoint.pt` (modelo + Adam + posicao no dado), NAO de um marco solto.
#     Sem os momentos do otimizador seria um restart disfarcado de continuacao.
#   · termina em 15B tokens — o unico ponto adiante onde o Bee-150M tem marco medido
#     (bpb 0,870), entao a comparacao e' maca-com-maca.
#   · decaimento de 20% na forma 1-sqrt(t), que e' o que o IMU-1 mede como equivalente
#     ao cosine. Nao inventar forma nova num experimento cujo objeto E' a forma.
#
# 🔴 O `--lr` VAI EXPLICITO, E ISSO NAO E' DETALHE. Com `--lr 0` o script deriva pela
#    Step Law a partir de `passos*tokens_por_passo`; como o fork termina em 15B e nao em
#    21,75B, o LR sairia (15/21,75)^0,307 = 10,8% MENOR. O experimento mediria "decaimento
#    + LR diferente" e o resultado seria inatribuivel. O valor abaixo e' o do run principal.
#
# CUSTO: 63.880 passos a ~54k tok/s = ~21,5 h a US$ 1,02/h = ~US$ 22.

set -euo pipefail

CORPUS=/corpus
CKPT=/workspace/bee-350m-fork
REPO=/workspace/llm-ptbr

# Congelados do run principal (linha "LR pico 2.181e-03 (Step Law N=345M, D=21.75B)").
LR_PICO=2.18105796e-3
PASSOS=228881          # 15,00B tokens a 65.536 tokens/passo
FRAC_DECAI=0.20        # decai a partir do passo 183.104

echo "=============================================================="
echo " BEE-350M — FORK DE DECAIMENTO"
echo "=============================================================="
nvidia-smi --query-gpu=name,memory.total,power.limit --format=csv,noheader

# --------------------------------------------------------- 0) 🔴 A GUARDA QUE IMPORTA
# Sem o checkpoint, `pretrain.py` nao falha: ele comeca do passo 0 com pesos aleatorios,
# imprime tudo verde, e so horas depois alguem nota que o experimento nao existe. Mesma
# familia de "o dado some e nada reclama" que ja custou tres vezes a este projeto.
if [ ! -s "$CKPT/checkpoint.pt" ]; then
  echo "🔴 ABORTA: $CKPT/checkpoint.pt nao existe." >&2
  echo "   Este script CONTINUA um treino; ele nao comeca um." >&2
  echo "   Copie o checkpoint do pod principal antes (scp) e rode de novo." >&2
  exit 1
fi

python - <<PY || exit 1
import sys, torch
ck = torch.load("$CKPT/checkpoint.pt", map_location="cpu", weights_only=False)
faltando = [k for k in ("modelo", "opt", "passo") if k not in ck]
if faltando:
    print(f"🔴 ABORTA: checkpoint sem {faltando}. Chaves: {list(ck)}", file=sys.stderr)
    sys.exit(1)
p = ck["passo"]
print(f"✅ checkpoint valido: passo {p:,} ({p*65536/1e9:.2f}B tokens) · "
      f"otimizador {'sim' if 'opt' in ck else 'NAO'} · "
      f"posicao no dado {'sim' if 'gerador' in ck else 'NAO'}")
if p >= $PASSOS:
    print(f"🔴 ABORTA: o checkpoint ja passou do alvo ({p:,} >= $PASSOS).", file=sys.stderr)
    sys.exit(1)
print(f"   faltam {$PASSOS - p:,} passos = {($PASSOS - p)*65536/54000/3600:.1f} h a 54k tok/s")
PY

# --------------------------------------------------------- 1) codigo
if [ -d "$REPO/.git" ]; then git -C "$REPO" pull --ff-only
else git clone --depth 1 https://github.com/brcampidelli/llm-ptbr.git "$REPO"; fi
cd "$REPO"
echo "commit: $(git rev-parse --short HEAD)"

# --------------------------------------------------------- 2) dependencias
pip install -q -U "transformers>=5.14" liger-kernel huggingface_hub

# --------------------------------------------------------- 3) corpus
mkdir -p "$CORPUS"
if [ ! -s "$CORPUS/train.bin" ]; then
  echo "--- baixando corpus (43,5 GB) do HF ---"
  HF_HUB_DISABLE_XET=1 python - <<'PY'
from huggingface_hub import snapshot_download
print("baixado em", snapshot_download("BrCamp/bee-corpus-pt-22b", repo_type="dataset",
                                      local_dir="/corpus", max_workers=8))
PY
fi

# --------------------------------------------------------- 4) o corpus e' o certo?
# ⚠️ Aqui isto e' MAIS critico que num run novo: o fork retoma a POSICAO no dado a partir
# do estado do gerador. Um corpus diferente faz a mesma posicao apontar para outro texto,
# e o "mesmo treino, so com decaimento" vira duas variaveis mudando de uma vez.
python bee/conferir_corpus.py "$CORPUS" || {
  echo "🔴 ABORTA: o corpus nao confere com a referencia do run principal."; exit 1; }

# --------------------------------------------------------- 5) o run
echo "=============================================================="
echo " decaindo ate 15B tokens · LR pico congelado em $LR_PICO"
echo "=============================================================="
exec python bee/pretrain.py \
  --tamanho 350m \
  --dados   "$CORPUS" \
  --tokenizer models/bee-150m-v3-base \
  --out     "$CKPT" \
  --passos  "$PASSOS" \
  --lr      "$LR_PICO" \
  --micro-batch 8 --grad-accum 4 \
  --sem-checkpointing \
  --liger --sem-compilar \
  --schedule wsd --frac-decaimento "$FRAC_DECAI" --lr-estavel-frac 0.55 \
  --ckpt-cada 500 \
  --marcos 13 \
  --aval-cada 500 --amostra-cada 2000 \
  2>&1 | tee -a "$CKPT/fork.log"
