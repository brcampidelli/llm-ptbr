# 🔴 MEDIDO 2026-09-04: matei uma sessao e lancei a seguinte 3 s depois. A VRAM do processo
#    morto ainda estava sendo devolvida pelo driver, e QUATRO formas + CINCO LRs estouraram —
#    9 medicoes perdidas por uma corrida de liberacao, nao por falta de memoria.
#    Esperar por tempo fixo e' supor; esperar pelo NUMERO e' medir.
LIVRE_MIN=${1:-28000}
for i in $(seq 1 60); do
  usado=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
  total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
  livre=$(( total - usado ))
  if [ "$livre" -ge "$LIVRE_MIN" ]; then echo "VRAM livre: ${livre} MiB (>= ${LIVRE_MIN}) apos $((i*5))s"; exit 0; fi
  sleep 5
done
echo "🔴 VRAM nao liberou: so' ${livre} MiB livres de ${total}"; exit 1
