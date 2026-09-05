#!/usr/bin/env bash
# Coleta os 7 idiomas nao-PT para o Bee-1G. Alvo: 2,5B tokens cada no 64k-multi.
#
# 🔴 MEDIDO 2026-09-04 (1o defeito): a primeira versao imprimiu "COLETA COMPLETA" com CINCO
#    idiomas em zero. O DNS caiu e o laco `for` do bash IGNORA o codigo de saida de cada
#    iteracao — o laco terminou, entao a mensagem saiu. Nada reclamou.
#
# 🔴🔴 MEDIDO 2026-09-04 (2o defeito, pior): a correcao daquilo foi VERIFICAR o disco — mas com
#    um ESTIMADOR. O `mcar_em_disco()` derivava o numero de caracteres do tamanho COMPRIMIDO,
#    multiplicando por uma razao cravada a mao. Censo contado depois, nos 221 shards em disco:
#
#        idioma   Mcar REAL   Mcar ESTIMADO   erro
#        arb           7801            2193   -72%
#        cmn           3405            1379   -60%
#        eng          10017            3225   -68%
#        spa           8805            2760   -69%
#
#    Sub-estimava entre 60% e 72% em TODOS. Consequencia: arb, cmn e eng estao a **100,0% do
#    alvo** e o driver os classificava como parciais — e o ramo "parcial" faz `rm -f`. Rodar de
#    novo APAGARIA os 221 shards, inclusive os tres idiomas prontos. Estimativa dirigindo acao
#    destrutiva, e errando sempre para o mesmo lado.
#
# 🔴 3o defeito: `cp MANIFEST.json MANIFEST_<c>.json` ficava no ramo de SUCESSO. Idioma que nao
#    chegava a 90% nunca atualizava o proprio arquivo — e o que sobrava ali era o de OUTRA
#    corrida. Os seis MANIFEST_*.json de 09:03 descrevem `fra`, que tem ZERO shards em disco.
#    §2z: arquivo cujo NOME afirma o que o CONTEUDO nao e'.
#
# ✅ AGORA: quem decide e' o censo CONTADO (`bee/censo_coleta_1g.py`, 0,8 min para os 221
#    shards). E `rm -f` nunca acontece sozinho — exige `--refazer <idiomas>` explicito, porque o
#    coletor renumera os shards a partir de 0000 e nao sabe retomar.
#
# Uso:
#     bash bee/coletar_1g.sh                    # coleta o que falta, nao apaga nada
#     bash bee/coletar_1g.sh --refazer jpn,spa  # apaga esses e recoleta do zero
cd "$(dirname "$0")/.."
OUT=bee/corpus_multi_1g
CENSO=docs/censo-coleta-1g.json
# o mesmo script roda no Windows (venv do projeto) e no pod Linux (python3 do sistema)
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=$(command -v python3)
[ -n "$PY" ] || { echo "🔴 sem interpretador Python"; exit 4; }
MIN_PCT=90                          # % do alvo para considerar o idioma pronto
declare -A ALVO=( [spa]=10541 [fra]=9810 [deu]=9282 [eng]=10017 [arb]=7801 [cmn]=3405 [jpn]=4752 )

REFAZER=""
IDIOMAS="spa fra deu eng arb cmn jpn"
while [ $# -gt 0 ]; do
  case "$1" in
    --refazer) REFAZER="$2"; shift 2 ;;
    # 🔴 restringe a corrida SEM mexer no censo: o censo continua contando TUDO que ha' em
    #    disco, entao o relatorio final nao passa a mentir por omissao. So' o laco encolhe.
    --idiomas) IDIOMAS=$(echo "$2" | tr ',' ' '); shift 2 ;;
    *) echo "uso: bash bee/coletar_1g.sh [--idiomas a,b,c] [--refazer a,b]"; exit 2 ;;
  esac
done

recensear() {  # CONTA o disco — nunca estima
  $PY bee/censo_coleta_1g.py --processos 6 --out "$CENSO" > /tmp/censo.log 2>&1 \
    || { echo "🔴 o censo falhou; veja /tmp/censo.log"; exit 3; }
}

pct_de() {  # % do alvo, lido do censo contado
  $PY -c "import json,sys; d=json.load(open('$CENSO',encoding='utf-8'));\
print('%.1f' % d['por_idioma'].get('$1',{}).get('pct_do_alvo',0.0))"
}

echo "== censo inicial (contado, nao estimado)"
recensear
falharam=()

for c in $IDIOMAS; do
  pct=$(pct_de $c); alvo=${ALVO[$c]}
  pronto=$($PY -c "print(1 if $pct >= $MIN_PCT else 0)")

  if [ "$pronto" = "1" ]; then
    echo "== $c: ${pct}% do alvo — pronto, pulando"
    continue
  fi

  # 🔴 nao apaga sozinho: o numero que mandava apagar errava 70%
  if $PY -c "import sys; sys.exit(0 if $pct > 0 else 1)"; then
    case ",$REFAZER," in
      *",$c,"*)
        echo "== $c: ${pct}% — --refazer pedido, APAGANDO os shards e recoletando"
        rm -f $OUT/bee_corpus_${c}_*.jsonl.zst ;;
      *)
        echo "== $c: ${pct}% do alvo, PARCIAL — nao vou apagar."
        echo "   o coletor renumera de 0000 e nao retoma; para refazer:"
        echo "   bash bee/coletar_1g.sh --refazer $c"
        falharam+=("$c(parcial ${pct}%)")
        continue ;;
    esac
  fi

  echo "== $c: alvo $alvo Mcar  ($(date '+%H:%M'))"
  HF_HUB_DISABLE_SYMLINKS_WARNING=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 \
    $PY bee/coletar_multilingue.py --idiomas $c \
    --mb-por-idioma $alvo --unidade caracteres --out $OUT > /tmp/col_$c.log 2>&1
  rc=$?
  recensear                              # reconta DEPOIS — o disco e' a verdade
  pct=$(pct_de $c)
  ok=$($PY -c "print(1 if $pct >= $MIN_PCT else 0)")
  if [ "$rc" -ne 0 ] || [ "$ok" != "1" ]; then
    echo "   🔴 $c FALHOU (rc=$rc, ${pct}% do alvo): $(grep -oE '[A-Za-z]*Error.*' /tmp/col_$c.log | head -1)"
    falharam+=("$c(${pct}%)")
  else
    echo "   ✅ $c: ${pct}% do alvo"
  fi
done

echo "----"
echo "== censo final"
$PY bee/censo_coleta_1g.py --processos 6 --out "$CENSO" | tail -16

if [ ${#falharam[@]} -ne 0 ]; then
  echo "🔴 COLETA INCOMPLETA — faltaram: ${falharam[*]}"
  echo "   o censo em $CENSO diz exatamente o que ha' em disco, por idioma."
  exit 1
fi
# ⚠️ "COMPLETA" so' pode falar dos idiomas que ESTA corrida percorreu — dizer "nos 7" quando
#    `--idiomas` restringiu seria a mesma mentira por omissao que o censo veio consertar.
echo "✅ COLETA COMPLETA em: $IDIOMAS  $(date '+%H:%M')"
echo "   (o censo acima cobre os 7; esta corrida percorreu os listados)"
