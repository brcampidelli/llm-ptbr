#!/usr/bin/env bash
# Supervisiona o pre-treino do Bee-1G: detecta morte e RETOMA do checkpoint, sozinho.
#
# 🔴 POR QUE EXISTE. Em 2026-09-07 o contentor do pod reiniciou sozinho as ~12:00 UTC e matou o
#    treino no passo 11.810 de 610.353. Nao houve traceback nem OOM — o processo foi terminado,
#    nao falhou. PID 1 com 1h52 de vida enquanto o treino escrevia ate as 11:56 e' a prova.
#    Segunda falha de infraestrutura em dois dias neste datacenter (a primeira foi 4,5 h de
#    queda de rede). Um run de ~395 h nao fecha sem retomada automatica.
#
# 🔴🔴 E POR QUE A DETECCAO NAO USA `pgrep`. O vigia anterior fazia `pgrep -f pretrain.py` e
#    reportou "RODANDO" por 2 HORAS depois da morte: o `-f` casa a linha de comando inteira, e a
#    linha do proprio shell que roda a checagem contem a string `pretrain.py`. **O vigia
#    encontrava a si mesmo.** Nao deu erro — deu uma resposta plausivel, que e' pior.
#
# ✅ O SINAL DE VIDA E' O MTIME DO LOG. O treino escreve a cada 10 passos (~22 s); se o log fica
#    parado alem de MAX_PARADO, esta morto, independentemente do que qualquer pgrep diga. E' um
#    sinal POSITIVO de trabalho, nao a ausencia de um sinal negativo.
#
# ⚠️ GUARDA CONTRA LACO DE MORTE: se o treino morrer MAX_FALHAS vezes sem avancar o passo, para
#    de retomar e grita. Retomar para sempre um treino que morre no mesmo ponto queimaria o
#    credito sem produzir nada — e pareceria "supervisao funcionando".
set -u
cd "$(dirname "$0")/.."
OUT=/workspace/bee1g/bee-1g
LOG=/workspace/bee1g/treino.log
SUP=/workspace/bee1g/supervisor.log
# 🔴 ELE SO ESCREVIA QUANDO AGIA — e por isso um supervisor VIVO e um MORTO produziam
#    exatamente o mesmo arquivo. Em 2026-09-09 o supervisor.log estava parado ha 10,5 h com
#    o processo rodando normalmente, e nao havia como distinguir isso de ter morrido. E a
#    lição de ontem chegando pelo outro lado: `kill -0` responde sobre EXISTENCIA e o log
#    silencioso nao responde nada — faltava o sinal POSITIVO de execucao.
# ✅ A BATIDA e escrita TODO ciclo, saudavel ou nao. Quem quiser saber se o supervisor roda
#    usa o mesmo criterio que ele usa para o treino: a idade do arquivo contra o intervalo.
BATIDA=/workspace/bee1g/.supervisor_batida
MAX_PARADO=420          # 7 min sem escrever no log = morto (o treino escreve a cada ~22 s)
MAX_FALHAS=5            # retomadas seguidas sem avancar o passo antes de desistir
INTERVALO=60

# ✅ O COMANDO NAO MORA MAIS AQUI. Ele mora em bee/lancar_1g.sh, que e idempotente e e o
#    MESMO chamado pelo supervisor externo. Duas rotas de relancamento sao boas (sao modos
#    de falha diferentes); duas COPIAS do comando nao — divergem, e a que diverge roda de
#    madrugada. O lancador recusa se o log estiver fresco ou se outro acabou de lancar.
lancar() { bash /workspace/bee1g/bee/lancar_1g.sh | tee -a "$SUP"; }

passo_atual() { grep -aoE 'passo +[0-9]+/' "$LOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+'; }
diz() { echo "[$(date -u '+%m-%d %H:%M UTC')] $*" | tee -a "$SUP"; }

diz "supervisor iniciado · sinal de vida = mtime de $(basename $LOG) · teto $MAX_PARADO s"
falhas=0
ultimo_passo=$(passo_atual); ultimo_passo=${ultimo_passo:-0}

while true; do
  agora=$(date +%s)
  mt=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  parado=$(( agora - mt ))
  p=$(passo_atual); p=${p:-0}
  echo "$agora $p $parado" > "$BATIDA"   # ✅ batida: prova de execucao

  if [ -d "$OUT/marco_20B" ]; then
    diz "✅ marco 20B alcancado — treino completo. Supervisor encerrando."
    exit 0
  fi

  if [ "$parado" -gt "$MAX_PARADO" ]; then
    if [ "$p" -le "$ultimo_passo" ]; then
      falhas=$((falhas + 1))
      diz "🔴 morto no passo $p (log parado ha ${parado}s) — SEM avanco desde a ultima retomada. Falha $falhas/$MAX_FALHAS"
    else
      falhas=0
      diz "🔴 morto no passo $p (log parado ha ${parado}s) — avancou desde $ultimo_passo, retomando"
    fi
    if [ "$falhas" -ge "$MAX_FALHAS" ]; then
      diz "🔴🔴 DESISTINDO: $MAX_FALHAS retomadas sem avancar o passo. Isto NAO e' flutuacao de"
      diz "     infraestrutura — ha algo que mata o treino sempre no mesmo ponto. Ver $LOG."
      exit 3
    fi
    ultimo_passo=$p
    echo "" >> "$LOG"
    diz "   retomando do checkpoint (o pretrain.py carrega modelo+otimizador+passo+gerador)"
    lancar
    sleep 180        # da tempo de carregar o checkpoint de 12,6 GB antes de julgar de novo
  else
    ultimo_passo=$p
  fi
  sleep "$INTERVALO"
done
