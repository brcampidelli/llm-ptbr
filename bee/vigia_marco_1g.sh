#!/usr/bin/env bash
# Avisa quando o Bee-1G alcanca um marco. Sinal de vida = mtime do log, nunca `pgrep`.
#
# 🔴 BUG 1 CORRIGIDO — a ETA estava 10x inflada. A versao anterior usava "22 s por passo", mas
#    22 s e' o intervalo entre LINHAS DE LOG, e cada linha cobre 10 passos. O resultado eram
#    "~58 h" para um marco que estava a 6 h. Numero plausivel que ninguem confere — a mesma
#    familia de tudo que este projeto colhe.
# ✅ Agora a taxa NAO e' constante nenhuma: e' MEDIDA entre os dois ultimos ciclos (passo e
#    relogio), como o §3 manda. No primeiro ciclo, quando ainda nao ha dois pontos, ele escreve
#    "medindo" em vez de estimar — dizer "nao sei ainda" e' melhor que inventar.
#
# 🔴 BUG 2 CORRIGIDO — o vigia imprimia a ultima linha do supervisor.log a cada ciclo, sem dizer
#    de quando ela era. Com o supervisor parado desde as 16:27, todo ciclo repetia "retomando do
#    checkpoint..." e parecia que ele estava retomando AGORA. Era o contrario: significava que
#    nada acontecia. Linha antiga apresentada como se fosse atual e' desinformacao.
# ✅ Agora so' aparece quando MUDA, e sempre com a idade dela ao lado.
#
# Uso:
#   bash bee/vigia_marco_1g.sh <marco_dir> <passo_alvo> [root@IP] [porta]
#   bash bee/vigia_marco_1g.sh marco_1B 30517
set -u
MARCO="${1:-marco_1B}"; ALVO="${2:-30517}"
POD="${3:-root@157.157.221.29}"; PORT="${4:-54182}"   # default = bee-1g-run3
KEY="$HOME/.ssh/runpod_bee"; DIR=/workspace/bee1g
PARADO_MAX=420; INTERVALO=300; MAX=400

sshpod() { timeout 80 ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=35 \
                 -o ServerAliveInterval=15 -p "$PORT" "$POD" "$1" 2>/dev/null; }

p_ant=0; t_ant=0; sup_ant=""; sem_ssh=0; parado_ha=0
echo "vigia de $MARCO (passo $ALVO) · taxa MEDIDA entre ciclos, nao constante"

for i in $(seq 1 $MAX); do
  # ✅ o comando remoto e um ARQUIVO no pod (bee/estado_1g.sh), testavel sozinho.
  #    A versao anterior montava uma string multilinha com escapes aqui e estava
  #    MALFORMADA: falhou nos 31 ciclos e reportou tudo como "ssh sem resposta".
  r=$(sshpod "bash $DIR/bee/estado_1g.sh $MARCO" | tail -2)
  ts=$(date -u '+%H:%M UTC')
  linha=$(echo "$r" | head -1); sup=$(echo "$r" | tail -1)

  case "$linha" in
    MARCO) echo "[$ts] ciclo $i: ⭐ $MARCO ALCANCADO"; break ;;
    D\ *)
      sem_ssh=0
      set -- $linha; agora=$2; parado=$3; passo=${4:-0}; sup_idade=${5:-0}
      if [ "$parado" -gt "$PARADO_MAX" ]; then
        parado_ha=$((parado_ha + 1))
        echo "[$ts] ciclo $i: 🔴 log parado ha ${parado}s no passo $passo — supervisor deve estar"
        echo "        relancando (12,6 GB de checkpoint levam minutos). ${parado_ha}o ciclo assim."
        [ "$parado_ha" -ge 6 ] && { echo "[$ts] 🔴🔴 30 min parado — nao e' relancamento normal."; break; }
      else
        parado_ha=0
        # ✅ taxa MEDIDA, nao suposta
        if [ "$p_ant" -gt 0 ] && [ "$passo" -gt "$p_ant" ]; then
          dp=$((passo - p_ant)); dt=$((agora - t_ant))
          eta=$(awk -v f=$((ALVO - passo)) -v dp=$dp -v dt=$dt 'BEGIN{printf "%.1f", (dt>0&&dp>0)? f*dt/dp/3600 : -1}')
          tps=$(awk -v dp=$dp -v dt=$dt 'BEGIN{printf "%.1f", (dt>0)? dp/dt*32768/1000 : 0}')
          echo "[$ts] ciclo $i: passo $passo/$ALVO · ${eta}h · ${tps}k tok/s medido neste intervalo"
        else
          echo "[$ts] ciclo $i: passo $passo/$ALVO · ETA: medindo (preciso de dois pontos)"
        fi
        p_ant=$passo; t_ant=$agora
      fi
      # ✅ so' quando MUDA, e com a idade ao lado
      if [ -n "$sup" ] && [ "$sup" != "$sup_ant" ]; then
        echo "        supervisor (ha ${sup_idade}s): $sup"
        sup_ant="$sup"
      fi ;;
    *) sem_ssh=$((sem_ssh + 1))
       echo "[$ts] ciclo $i: ssh sem resposta ($sem_ssh) — NAO conta como fim" ;;
  esac
  [ "$i" = "$MAX" ] && { echo "TETO — nao e' conclusao."; exit 2; }
  sleep "$INTERVALO"
done

echo
echo "===================== ESTADO NO MARCO ====================="
sshpod "cd $DIR
echo '--- snapshot:'; ls -la bee-1g/$MARCO 2>/dev/null | head -5 || echo '  ausente'
echo '--- supervisor (todas as intervencoes):'; cat supervisor.log 2>/dev/null | tail -10
echo '--- treino:'; grep -avE 'Loading|it/s\]' treino.log | tail -8
echo '--- throughput SUSTENTADO (§3):'
grep -aoE '[0-9.]+k tok/s' treino.log | tr -dc '0-9.\n' | awk 'NR>3&&\$1>0{s+=\$1;n++;if(n==1||\$1<mn)mn=\$1;if(\$1>mx)mx=\$1} END{if(n)printf \"  n=%d  media %.1fk  min %.1fk  max %.1fk\n\",n,s/n,mn,mx}'
echo '--- GPU e disco:'
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu --format=csv,noheader
df -h /workspace | tail -1"
exit 0
