#!/usr/bin/env bash
# Supervisiona o pre-treino do Bee-1G DE FORA do pod, por ssh.
#
# 🔴 POR QUE FORA. O `supervisor_1g.sh` roda DENTRO do contentor e por isso morre junto com ele.
#    Em 2026-09-07 o contentor do pod reiniciou DUAS VEZES em tres horas (PID 1 com 1h52 na
#    primeira, 30 min na segunda) — e na segunda o supervisor foi embora sem escrever uma linha.
#    Um supervisor que morre com o que supervisiona nao supervisiona nada.
#
# 🔴🔴 E NAO SE USA `pgrep` PARA NADA. Testado contra o estado real, com o treino comprovadamente
#    morto, TODAS as variantes respondiam VIVO: o `-f` casa a linha de comando inteira, e a do
#    shell que faz a pergunta contem o padrao. Quem pergunta sempre casa a si mesmo.
#
# ✅ SINAL DE VIDA = mtime do treino.log. O treino escreve a cada ~22 s; parado alem de
#    PARADO_MAX esta' morto. Sinal POSITIVO de trabalho, nao ausencia de sinal negativo.
#
# ⚠️ SSH FORA NAO E' MORTE. Este pod ja' passou 4,5 h sem rede com o trabalho rodando por dentro.
#    Relancar sem conseguir olhar seria relancar as cegas — e nem da', o ssh e' o unico caminho.
#    Falha de ssh e' CONTADA e nomeada, nunca tratada como morte.
#
# ⚠️ E ELE VIGIA O CONTENTOR TAMBEM: uptime do PID 1 menor que o do ciclo anterior significa
#    reinicio. E' o gatilho combinado com o dono para trocar de host — entao ele CONTA e AVISA,
#    em vez de so' religar em silencio e deixar o padrao invisivel.
set -u
# ⚠️ ENDPOINT E ARGUMENTO, nao constante. Ficou cravado ate 2026-09-08 porque editar um
#    script em execucao e perigoso (o bash le por deslocamento de byte). Ao trocar de pod
#    (run2 -> run3) o IP continuou o mesmo e SO A PORTA mudou — o tipo de diferenca que
#    passa despercebida e faz o supervisor vigiar uma maquina que nao e a do treino.
#    Uso: bash bee/supervisor_externo_1g.sh [root@IP] [porta]
POD="${1:-root@157.157.221.29}"; KEY="$HOME/.ssh/runpod_bee"; PORT="${2:-54182}"
DIR=/workspace/bee1g
PARADO_MAX=420          # 7 min sem escrever = morto
MAX_FALHAS=5            # relancamentos sem avancar o passo antes de desistir
INTERVALO=90
MAX_CICLOS=1200         # 1200 x 90 s = 30 h

sshpod() { timeout 80 ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=35 \
                 -o ServerAliveInterval=15 -p "$PORT" "$POD" "$1" 2>/dev/null; }
diz() { echo "[$(date -u '+%m-%d %H:%M UTC')] $*"; }

# ⚠️ UMA copia do comando, usada em toda partida — duas divergem, e a que diverge roda de noite.
LANCAR="cd $DIR && (setsid nohup env PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python3 bee/pretrain.py \
--tamanho 1b --vocab 64000 --dados pool --tokenizer bee/tok_t1/64k-multi --out $DIR/bee-1g \
--epocas 1.0 --micro-batch 4 --grad-accum 4 --schedule wsd --lr 9.61e-4 --lr-estavel-frac 0.55 \
--marcos 1,3,6,10,15,20 --ckpt-cada 250 --sem-liger --sem-compilar >> $DIR/treino.log 2>&1 < /dev/null &)"

diz "supervisor EXTERNO iniciado · vida = mtime do treino.log · teto $PARADO_MAX s"
# 🔴 up_ant COMECAVA EM 999999 e o primeiro ciclo SEMPRE acusava reinicio, porque qualquer
#    uptime real e menor que a sentinela. Nao era ruido inofensivo: comecando com
#    reinicios=1, o PRIMEIRO reinicio de verdade ja batia o limiar de "2+ = trocar de host"
#    — e trocar de host custa um pod novo e o tempo de retomada. Alarme que dispara no caso
#    normal ou se aprende a ignorar, ou faz agir cedo demais. Ambos custam.
falhas=0; ultimo_passo=0; sem_ssh=0; up_ant=0; reinicios=0

for i in $(seq 1 $MAX_CICLOS); do
  r=$(sshpod "cd $DIR 2>/dev/null || exit 1
    test -d bee-1g/marco_20B && { echo FIM; exit 0; }
    echo \"D \$(( \$(date +%s) - \$(stat -c %Y treino.log 2>/dev/null || echo 0) )) \
\$(grep -aoE 'passo +[0-9]+/' treino.log 2>/dev/null | tail -1 | grep -oE '[0-9]+' || echo 0) \
\$(awk '{print int(\$1)}' /proc/uptime)\"" | tail -1)

  case "$r" in
    FIM) diz "✅ marco 20B — treino completo."; exit 0 ;;
    D\ *)
      sem_ssh=0
      set -- $r; parado=$2; passo=${3:-0}; up=${4:-0}
      # reinicio de contentor: uptime do PID 1 MENOR que o do ciclo anterior
      if [ "$up_ant" -gt 0 ] && [ "$up" -lt "$up_ant" ]; then   # ✅ so compara com ponto anterior REAL
        reinicios=$((reinicios + 1))
        diz "⚠️ CONTENTOR REINICIOU (uptime $up s < $up_ant s) — ${reinicios}o desta vigilia."
        [ "$reinicios" -ge 2 ] && diz "   🔴 2+ reinicios: e' o gatilho combinado para trocar de host (plano b)."
      fi
      up_ant=$up

      if [ "$parado" -gt "$PARADO_MAX" ]; then
        if [ "$passo" -le "$ultimo_passo" ] && [ "$ultimo_passo" -gt 0 ]; then
          falhas=$((falhas + 1))
          diz "🔴 morto no passo $passo (parado ${parado}s) — SEM avanco. Falha $falhas/$MAX_FALHAS"
        else
          falhas=0
          diz "🔴 morto no passo $passo (parado ${parado}s) — avancou desde $ultimo_passo"
        fi
        if [ "$falhas" -ge "$MAX_FALHAS" ]; then
          diz "🔴🔴 DESISTINDO: $MAX_FALHAS relancamentos sem avancar. Nao e' flutuacao —"
          diz "     ha' algo que mata o treino sempre no mesmo ponto."
          exit 3
        fi
        ultimo_passo=$passo
        diz "   relancando do checkpoint..."
        sshpod "$LANCAR" >/dev/null
        sleep 240      # carregar 12,6 GB de checkpoint leva minutos
      else
        ultimo_passo=$passo
        [ $((i % 10)) -eq 1 ] && diz "passo $passo/610353 · escreveu ha ${parado}s · $reinicios reinicios"
      fi ;;
    *) sem_ssh=$((sem_ssh + 1))
       diz "ssh sem resposta ($sem_ssh seguidos) — NAO conta como morte" ;;
  esac
  [ "$i" = "$MAX_CICLOS" ] && { diz "TETO DE 30 H — nao e' conclusao."; exit 2; }
  sleep "$INTERVALO"
done
