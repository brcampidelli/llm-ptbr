#!/usr/bin/env bash
# Gate #3 do estudo do arXiv — no POD (RTX 5090): SFT do Bee-350M com duas intervencoes, 3 sementes,
# receita IDENTICA a do E19 C-full (comeia/models/e19c-s4x/training_args.json), depois a avaliacao
# com a config de referencia (exec_e19c-*-cfgref.json).
#
#   (a) catperturbado      — comeia/data/perturbar_catalogo.py  (arXiv 2609.04184; SEM remover nao usadas, §2u)
#   (b) recusa_especifica  — comeia/data/recusas_especificas.py (arXiv 2609.04714; recusa mantida, template fora)
#
# REFERENCIAS ja medidas (mesma regua, 3 sementes cada): e13 (recusa em template) e C-full (resposta util).
# PISO: a dispersao entre sementes do C-full (exec_ok 66,8-69,4; over 14,2-14,9).
# ⚠️ Versoes FIXADAS nas dos adapters de referencia (transformers 5.14.1 · trl 1.9.0 · peft 0.19.1):
#    a §2aa manda ler a config no artefato, e o artefato diz isso. Trocar de versao entre os bracos
#    e a referencia seria mudar a regua entre os grupos (§2g).
#
# Uso: no pod, dentro do clone do repo em /workspace/llm-ptbr:  bash bee/gate3_sft_pod.sh
set -u
cd "$(dirname "$0")/.."
OUT=${OUT:-/workspace/gate3}; mkdir -p "$OUT" comeia/eval/results
BASE=BrCamp/bee-350m-pt-base
HOLD=comeia/data/processed/holdout_balanceado.eval.jsonl
diz() { echo "[$(date -u '+%m-%d %H:%M UTC')] $*" | tee -a "$OUT/gate3.log"; }

deps() {
  python3 -c "import transformers,trl,peft;print(transformers.__version__,trl.__version__,peft.__version__)" 2>/dev/null | grep -q "^5.14.1 1.9.0 0.19.1$" && return 0
  diz "instalando dependencias fixadas..."
  pip install -q --break-system-packages "transformers==5.14.1" "trl==1.9.0" "peft==0.19.1" bitsandbytes accelerate datasets huggingface_hub 2>&1 | tail -2
  python3 -c "import transformers,trl,peft,bitsandbytes;print('  transformers',transformers.__version__,'trl',trl.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)"
}

braco() {   # corpus semente
  local corpus=$1 sem=$2 nome="gate3-$1-s$2" adp="$OUT/$1-s$2" dados
  case "$corpus" in
    catperturbado)     dados=comeia/data/processed/treino_e19c_catperturbado.jsonl ;;
    recusa_especifica) dados=comeia/data/processed/treino_e19d_recusa_especifica_v2.jsonl ;;   # v2: sem abertura dominante (v1 tinha 62% 'Nao consigo calcular')
    *) diz "🔴 corpus desconhecido: $corpus"; return 1 ;;
  esac
  [ -f "$dados" ] || { diz "🔴 corpus ausente: $dados"; return 1; }
  if [ ! -f "$adp/FIM_TREINO" ]; then
    diz "TREINO $nome"
    PYTHONUNBUFFERED=1 python3 comeia/train/sft_qlora.py --model $BASE --data "$dados" --out "$adp" \
      --max-seq-len 2048 --epochs 3 --max-steps 698 --lr 0.0012 --batch-size 1 --grad-accum 16 \
      --lora-r 16 --lora-alpha 32 --save-steps 200 --seed "$sem" > "$OUT/$nome.treino.log" 2>&1 \
      && touch "$adp/FIM_TREINO" || { diz "🔴 treino falhou: $nome"; tail -5 "$OUT/$nome.treino.log"; return 1; }
    diz "  treino ok · $(grep -aoE 'train_loss[^,]*' "$OUT/$nome.treino.log" | tail -1)"
  fi
  if [ ! -f "comeia/eval/results/exec_$nome-cfgref.json" ]; then
    diz "EVAL $nome"
    PYTHONUNBUFFERED=1 python3 comeia/eval/eval_agentic_exec.py --model $BASE --peft "$adp" --data $HOLD \
      --k 1 --chat --parar-controle --restrito --restrito-ferramenta --por-argumento --lote 16 --max-len 1700 \
      --tag "$nome-cfgref" --dump > "$OUT/$nome.eval.log" 2>&1 \
      || { diz "🔴 eval falhou: $nome"; tail -5 "$OUT/$nome.eval.log"; return 1; }
    python3 - "comeia/eval/results/exec_$nome-cfgref.json" <<'PY' | tee -a "$OUT/gate3.log"
import json, sys; d = json.load(open(sys.argv[1], encoding="utf-8"))
def g(*ks, default=None):
    x = d
    for k in ks:
        x = x.get(k, {}) if isinstance(x, dict) else {}
    return x if x != {} else default
print(f"  RESULTADO {sys.argv[1].split('exec_')[-1]}: " + " · ".join(f"{k}={d.get(k)}" for k in ("exec_ok","exec_ok_pct","over_call","over_call_pct","under_call","ferramenta_certa") if k in d))
PY
  fi
}

deps

# ✅ §2aa — A REGUA DO POD TEM DE REPRODUZIR UM NUMERO PUBLICADO antes de medir braco novo.
#    O C-full s42 (BrCamp/bee-350m-pt-assistente) mediu exec_ok 372/536 e over_call 39/268 com esta
#    config (exec_e19c-cfgref.json). Tolerancia: 0 — a regua e' deterministica com lote 16.
CTRL=comeia/eval/results/exec_gate3-controle-cfull-s42-cfgref.json
if [ ! -f "$CTRL" ]; then
  diz "CONTROLE §2aa: reavaliando o C-full s42 publicado"
  PYTHONUNBUFFERED=1 python3 comeia/eval/eval_agentic_exec.py --model $BASE --peft BrCamp/bee-350m-pt-assistente \
    --data $HOLD --k 1 --chat --parar-controle --restrito --restrito-ferramenta --por-argumento --lote 16 --max-len 1700 \
    --tag gate3-controle-cfull-s42-cfgref > "$OUT/controle.eval.log" 2>&1 || { diz "🔴 controle falhou"; tail -5 "$OUT/controle.eval.log"; exit 1; }
fi
python3 -c "
import json, sys
d = json.load(open('$CTRL', encoding='utf-8'))
ref = {'exec_ok': 372, 'over_call': 39, 'n_tool': 536, 'n_text': 268}
ok = all(d.get(k) == v for k, v in ref.items())
print(f\"  controle: exec_ok {d.get('exec_ok')}/{d.get('n_tool')} · over_call {d.get('over_call')}/{d.get('n_text')} · publicado 372/536 · 39/268 -> {'REPRODUZ' if ok else 'NAO REPRODUZ'}\")
sys.exit(0 if ok else 2)" | tee -a "$OUT/gate3.log"
[ "${PIPESTATUS[0]}" -eq 0 ] || { diz "🔴 A REGUA DO POD NAO REPRODUZ O C-FULL PUBLICADO — abortando (§2aa). Conferir versoes e config."; exit 2; }
diz "gate #3 · referencias: e13 exec 71,8-75,2 over 16,8-17,5 · C-full exec 66,8-69,4 over 14,2-14,9"
for sem in 42 43 44; do
  braco catperturbado "$sem"
  braco recusa_especifica "$sem"
done
diz "fim — consolidar localmente com os artefatos em comeia/eval/results/exec_gate3-*-cfgref.json"
