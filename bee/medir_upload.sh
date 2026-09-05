#!/usr/bin/env bash
# Mede a taxa de UPLOAD desta maquina para um pod — em regime, nao num numero solto.
#
# 🔴 POR QUE ISTO EXISTE. O plano do Bee-1G depende de levar dezenas de GB ate' o pod, e eu
#    nunca medi upload. Medi DOWNLOAD (6 MB/s) e a tentacao e' supor simetria — em linha
#    residencial ela quase nunca vale, e o erro e' sempre para o lado otimista.
#
# ⚠️ TRES ARMADILHAS que este script evita, todas ja' pagas neste projeto:
#
#  1. AMOSTRA CURTA (§3). Handshake de ssh e slow-start de TCP dominam uma transferencia
#     pequena: 3 arquivos deram "6 MB/s" no download e isso nao e' regime. Aqui o default sao
#     ~600 MB e reportam-se TRES leituras — se elas nao coincidirem, nao ha' numero.
#
#  2. COMPRESSAO NO TRANSPORTE. `scp -C`/`tar -z` comprimem, e dado de token uint16 comprime
#     bem — a taxa medida sairia inflada e nao valeria para o arquivo real. Aqui NAO se usa
#     compressao, e mede-se com o dado VERDADEIRO (um shard do corpus), nunca com /dev/zero,
#     que comprime a quase nada e mentiria por um fator enorme.
#
#  3. DESTINO ERRADO. Escrever no overlay do contentor e no volume de rede tem custo
#     diferente. O parametro --destino existe para medir onde o dado vai de fato morar.
#
# ⚠️ E o que ele NAO mede: variacao ao longo do dia, e o efeito de uma transferencia de horas
#    (throttling do provedor). Uma medida de 10 min e' um TETO otimista para uma de 3 h.
#
# Uso:
#   bash bee/medir_upload.sh root@IP PORTA [--destino /workspace/teste] [--mb 600]
set -u
[ $# -lt 2 ] && { echo "uso: bash bee/medir_upload.sh root@IP PORTA [--destino DIR] [--mb N]"; exit 2; }
POD=$1; PORT=$2; shift 2
KEY="$HOME/.ssh/runpod_bee"; DEST=/root/_upload_teste; MB=600
while [ $# -gt 0 ]; do
  case "$1" in
    --destino) DEST="$2"; shift 2 ;;
    --mb) MB="$2"; shift 2 ;;
    *) echo "argumento desconhecido: $1"; exit 2 ;;
  esac
done
cd "$(dirname "$0")/.."

# dado REAL: shards do corpus, que e' exatamente o que vai subir de verdade
mapfile -t ARQ < <(ls -1 bee/corpus_multi_1g/*.zst 2>/dev/null | head -60)
[ ${#ARQ[@]} -eq 0 ] && { echo "🔴 sem shards em bee/corpus_multi_1g para medir com dado real"; exit 3; }

sshpod() { ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=20 -p "$PORT" "$POD" "$1"; }
sshpod "mkdir -p $DEST" || { echo "🔴 nao consegui criar $DEST no pod"; exit 4; }

echo "medindo upload para $POD:$DEST — 3 leituras de ~${MB} MB, dado real, SEM compressao"
echo
leituras=()
for r in 1 2 3; do
  # monta um lote de ~MB megabytes de shards reais
  lote=(); soma=0
  for f in "${ARQ[@]}"; do
    s=$(stat -c%s "$f"); soma=$((soma + s/1048576)); lote+=("$(basename "$f")")
    [ "$soma" -ge "$MB" ] && break
  done
  t0=$(date +%s%N)
  tar cf - -C bee/corpus_multi_1g "${lote[@]}" | sshpod "tar xf - -C $DEST"
  rc=$?
  t1=$(date +%s%N)
  [ $rc -ne 0 ] && { echo "🔴 leitura $r falhou (rc=$rc)"; exit 5; }
  seg=$(( (t1-t0)/1000000000 )); [ "$seg" -lt 1 ] && seg=1
  taxa=$(echo "$soma $seg" | awk '{printf "%.2f", $1/$2}')
  leituras+=("$taxa")
  echo "  leitura $r: ${soma} MB em ${seg}s = ${taxa} MB/s"
  sshpod "rm -rf $DEST && mkdir -p $DEST"
done

# §3: tres leituras coincidentes, ou nao ha' numero
awk -v a="${leituras[0]}" -v b="${leituras[1]}" -v c="${leituras[2]}" 'BEGIN{
  min=a; max=a; for(x in y);
  if(b<min)min=b; if(c<min)min=c; if(b>max)max=b; if(c>max)max=c;
  med=(a+b+c)/3; disp=(max-min)/med*100;
  printf "\nmedia %.2f MB/s · dispersao %.1f%%\n", med, disp;
  if (disp > 20) {
    print "🔴 dispersao acima de 20% — as leituras NAO coincidem, nao ha numero em regime (§3)."
    print "   Repita; se persistir, a linha esta instavel e o planejamento tem de usar o PIOR caso."
    exit 1
  }
  print "\ntempo para o que o plano precisa subir:"
  printf "  20 GB (metade PT do pool pt-50, minimo)      %5.1f h\n", 20480/med/3600;
  printf "  40 GB (pool pt-50 inteiro, 20B tokens)       %5.1f h\n", 40960/med/3600;
  printf "  70 GB (os dois corpora crus)                 %5.1f h\n", 71680/med/3600;
  print "\n⚠️ Estes sao TETOS OTIMISTAS: medida de minutos nao ve throttling de horas."
}'
saida=$?
sshpod "rm -rf $DEST"
exit $saida
