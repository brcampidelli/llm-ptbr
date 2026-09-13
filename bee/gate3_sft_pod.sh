#!/usr/bin/env bash
# Gate #3 do estudo do arXiv — no POD (RTX 5090): SFT do Bee-350M com duas intervencoes, 3 sementes,
# receita IDENTICA a do E19 C-full (comeia/models/e19c-s4x/training_args.json), depois a avaliacao
# com a config de referencia (exec_e19c-*-cfgref.json).
#
#   (a) catperturbado      — comeia/data/perturbar_catalogo.py  (arXiv 2609.04184; SEM remover nao usadas, §2u)
#   (b) recusa_especifica  — comeia/data/recusas_especificas.py (arXiv 2609.04714; recusa mantida, template fora)
#
# REFERENCIAS (3 sementes cada): e13 (recusa em template) e C-full (resposta util) — REMEDIDAS NESTE POD,
# porque a regua greedy/bf16 deriva com o hardware (medido: −3/536 e −3/268 entre 5070 e 4090, §2t/§2g).
# PISO: a dispersao entre sementes do C-full (local: exec_ok 66,8-69,4; over 14,2-14,9) — recalculada no pod.
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

avaliar() {   # nome caminho_do_adapter  -> comeia/eval/results/exec_<nome>-cfgref.json (config de referencia, §2aa)
  local nome=$1 adp=$2
  [ -f "comeia/eval/results/exec_$nome-cfgref.json" ] && return 0
  PYTHONUNBUFFERED=1 python3 comeia/eval/eval_agentic_exec.py --model $BASE --peft "$adp" --data $HOLD \
    --k 1 --chat --parar-controle --restrito --restrito-ferramenta --por-argumento --lote 16 --max-len 1700 \
    --tag "$nome-cfgref" --dump > "$OUT/$nome.eval.log" 2>&1 \
    || { diz "🔴 eval falhou: $nome"; tail -5 "$OUT/$nome.eval.log"; return 1; }
  python3 - "comeia/eval/results/exec_$nome-cfgref.json" <<'PY' | tee -a "$OUT/gate3.log"
import json, sys; d = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"  RESULTADO {sys.argv[1].split('exec_')[-1]}: " + " · ".join(f"{k}={d.get(k)}" for k in ("exec_ok","n_tool","over_call","n_text","under_call","tool_right","args_exact") if k in d))
PY
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
  [ -f "comeia/eval/results/exec_$nome-cfgref.json" ] || { diz "EVAL $nome"; avaliar "$nome" "$adp"; }
}

# Referencias REMEDIDAS neste pod (§2g: mesma regua = mesmo codigo, mesmas flags E mesmo hardware).
#   e13 s42/43/44  — recusa em template   — adapters enviados por scp para $OUT/refs/e13-s4x
#   C-full s42     — resposta util        — e' o controle (BrCamp/bee-350m-pt-assistente, raiz)
#   C-full s43/44  — idem                 — subpastas seed-43/ seed-44/ do mesmo repo (snapshot_download;
#                                           `subfolder=` do PeftModel nao acha os pesos, ver model card)
baixar_cfull() {   # semente
  local d="$OUT/refs/cfull-s$1"
  [ -f "$d/adapter_model.safetensors" ] && return 0
  python3 - "$1" "$d" <<'PY' || return 1
import os, shutil, sys
from huggingface_hub import snapshot_download
sem, dest = sys.argv[1], sys.argv[2]
p = snapshot_download("BrCamp/bee-350m-pt-assistente", allow_patterns=[f"seed-{sem}/*"])
os.makedirs(dest, exist_ok=True)
src = os.path.join(p, f"seed-{sem}")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), dest)
print("  baixado", dest, sorted(os.listdir(dest)))
PY
}
referencias() {
  local s
  for s in 42 43 44; do
    [ -f "$OUT/refs/e13-s$s/adapter_model.safetensors" ] || { diz "🔴 referencia ausente: $OUT/refs/e13-s$s (scp de comeia/models/e13-email-s$s)"; return 1; }
    [ -f "comeia/eval/results/exec_gate3-ref-e13-s$s-cfgref.json" ] || diz "REFERENCIA e13 s$s"
    avaliar "gate3-ref-e13-s$s" "$OUT/refs/e13-s$s" || return 1
  done
  for s in 43 44; do
    baixar_cfull "$s" || { diz "🔴 nao baixou C-full s$s"; return 1; }
    [ -f "comeia/eval/results/exec_gate3-ref-cfull-s$s-cfgref.json" ] || diz "REFERENCIA C-full s$s"
    avaliar "gate3-ref-cfull-s$s" "$OUT/refs/cfull-s$s" || return 1
  done
}

deps

# ✅ §2aa — A REGUA DO POD TEM DE REPRODUZIR UM NUMERO PUBLICADO antes de medir braco novo.
#    O C-full s42 (BrCamp/bee-350m-pt-assistente = comeia/models/e19c-s42, sha256 020512b1 identico)
#    mediu exec_ok 372/536 e over_call 39/268 na RTX 5070 local com esta config (exec_e19c-cfgref.json).
#    MEDIDO 2026-09-13 na RTX 4090 do pod, mesma config, mesmo perfil de argumentos: 369/536 e 36/268.
#    Config identica, 3 ferramentas diferentes, deriva de −3/+3 nos dois lados: a regua greedy em bf16
#    muda com o HARDWARE, como ja mudava com o lote (§2t). Por isso:
#      · dentro da tolerancia (|Δ| ≤ 8 exec_ok, ≤ 6 over_call) => e' deriva numerica: seguir, MAS remedir
#        TODAS as referencias neste pod (referencias()) e comparar so' pod-com-pod (§2g);
#      · fora dela => e' config/versao errada (o modo de falha da §2aa: 3,2% onde era 71,8%): abortar.
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
ref = {'exec_ok': 372, 'over_call': 39}
assert d.get('n_tool') == 536 and d.get('n_text') == 268, 'n diferente do publicado — holdout errado'
de, do = d['exec_ok'] - ref['exec_ok'], d['over_call'] - ref['over_call']
exato = de == 0 and do == 0
tolera = abs(de) <= 8 and abs(do) <= 6
print(f\"  controle: exec_ok {d['exec_ok']}/536 · over_call {d['over_call']}/268 · publicado (5070) 372/536 · 39/268 · deriva {de:+d} / {do:+d} -> \"
      + ('REPRODUZ' if exato else ('DERIVA DE HARDWARE, dentro da tolerancia: referencias serao remedidas neste pod' if tolera else 'NAO REPRODUZ')))
sys.exit(0 if tolera else 2)" | tee -a "$OUT/gate3.log"
[ "${PIPESTATUS[0]}" -eq 0 ] || { diz "🔴 A REGUA DO POD NAO REPRODUZ O C-FULL PUBLICADO — abortando (§2aa). Conferir versoes e config."; exit 2; }
referencias || { diz "🔴 referencias nao remedidas — sem comparacao a fazer (§2g)"; exit 3; }
diz "gate #3 · referencias remedidas aqui (5070 → 4090); os numeros locais (e13 71,8-75,2 · C-full 66,8-69,4) ficam so' como sanidade"
for sem in 42 43 44; do
  braco catperturbado "$sem"
  braco recusa_especifica "$sem"
done
diz "fim — consolidar localmente com os artefatos em comeia/eval/results/exec_gate3-*-cfgref.json"
