#!/usr/bin/env bash
# Coleta os 7 idiomas nao-PT para o Bee-1G. Alvo: 2,5B tokens cada no 64k-multi.
#
# 🔴 MEDIDO 2026-09-04: a primeira versao imprimiu "COLETA COMPLETA" com CINCO idiomas em zero.
#    O DNS caiu (getaddrinfo failed) e o laco `for` do bash IGNORA o codigo de saida de cada
#    iteracao — o laco terminou, entao a mensagem saiu. Nada reclamou.
# ✅ Agora: cada idioma e' VERIFICADO pelo que ficou em disco, nao pelo fato de o comando ter
#    rodado; falha marca o idioma e o resumo final ABORTA com a lista do que faltou.
#
# ⚠️ Os Mcar sao derivados da fertilidade MEDIDA por idioma (gate-t1-vocab.json). Balancear por
#    CARACTERE daria contagens de token muito diferentes entre escritas (§2g).
cd "$(dirname "$0")/.."
OUT=bee/corpus_multi_1g
MIN_FRAC=0.90                       # fracao minima do alvo para considerar o idioma pronto
declare -A ALVO=( [spa]=10541 [fra]=9810 [deu]=9282 [eng]=10017 [arb]=7801 [cmn]=3405 [jpn]=4752 )
declare -A MCAR_POR_GB=( [spa]=970 [fra]=970 [deu]=950 [eng]=950 [arb]=620 [cmn]=370 [jpn]=360 )
falharam=()

mcar_em_disco() {  # estima Mcar pelo tamanho comprimido — grosseiro, so' para a guarda
  local c=$1 b
  b=$(du -cb $OUT/bee_corpus_${c}_*.jsonl.zst 2>/dev/null | tail -1 | cut -f1) || b=0
  echo $(( b / 1048576 * ${MCAR_POR_GB[$c]} / 1024 ))
}

for c in spa fra deu eng arb cmn jpn; do
  tem=$(mcar_em_disco $c); alvo=${ALVO[$c]}
  if [ "$tem" -ge $(( alvo * 90 / 100 )) ]; then echo "== $c: ja' tem ~${tem} Mcar, pulando"; continue; fi
  [ "$tem" -gt 0 ] && { echo "== $c: parcial (~${tem} Mcar de $alvo) — refazendo do zero"; rm -f $OUT/bee_corpus_${c}_*.jsonl.zst; }
  echo "== $c: alvo $alvo Mcar  ($(date '+%H:%M'))"
  HF_HUB_DISABLE_SYMLINKS_WARNING=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 \
    .venv/Scripts/python.exe bee/coletar_multilingue.py --idiomas $c \
    --mb-por-idioma $alvo --unidade caracteres --out $OUT > /tmp/col_$c.log 2>&1
  rc=$?
  tem=$(mcar_em_disco $c)
  if [ $rc -ne 0 ] || [ "$tem" -lt $(( alvo * 90 / 100 )) ]; then
    echo "   🔴 $c FALHOU (rc=$rc, ~${tem} Mcar de $alvo): $(grep -oE '[A-Za-z]*Error.*' /tmp/col_$c.log | head -1)"
    falharam+=("$c")
  else
    echo "   ✅ $c: ~${tem} Mcar"
    [ -f $OUT/MANIFEST.json ] && cp $OUT/MANIFEST.json $OUT/MANIFEST_${c}.json
  fi
done

echo "----"
if [ ${#falharam[@]} -ne 0 ]; then
  echo "🔴 COLETA INCOMPLETA — faltaram: ${falharam[*]}"
  echo "   rode de novo: bash bee/coletar_1g.sh   (os prontos sao pulados)"
  exit 1
fi
echo "✅ COLETA COMPLETA nos 7 idiomas  $(date '+%H:%M')"
du -sh $OUT
