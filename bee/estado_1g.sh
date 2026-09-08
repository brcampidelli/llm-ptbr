#!/usr/bin/env bash
# Le' o estado do run no pod e imprime UMA linha de campos. Existe para ser testavel sozinho.
#
# 🔴 POR QUE VIROU ARQUIVO PROPRIO. A versao anterior montava este comando como uma string
#    multilinha dentro de `ssh "..."`, com continuacoes de linha e aspas escapadas. Ela estava
#    MALFORMADA — `bash: -c: line 3: unexpected EOF while looking for matching '"'` — e falhou
#    em TODOS os 31 ciclos. O vigia reportou "ssh sem resposta", que e' a resposta certa para um
#    ssh que falha, mas a falha era do MEU comando, nao da rede.
#
# ⭐ O que denunciou foi uma CONTRADICAO: o supervisor lia o treino pela mesma rota, no mesmo
#    minuto, enquanto o vigia acusava 31 falhas seguidas. §5 — quando dois aparelhos internos se
#    contradizem, o defeito esta' no aparato. Investigar a contradicao ANTES de teorizar sobre a
#    rede foi o que achou o bug em dois minutos.
#
# ✅ Agora o comando remoto e' um ARQUIVO no pod, sem escapes, e da' para roda-lo a mao e ver a
#    saida. Comando que so' existe embutido numa string nunca e' testado isoladamente.
#
# Saida: MARCO   (se o diretorio do marco existe)
#     ou D <epoch> <segundos_log_parado> <passo> <segundos_supervisor_parado>
#        <ultima linha do supervisor.log>
set -u
cd /workspace/bee1g 2>/dev/null || { echo "ERRO cd"; exit 1; }
MARCO="${1:-marco_1B}"

if [ -d "bee-1g/$MARCO" ]; then
  echo MARCO
  exit 0
fi

agora=$(date +%s)
mt_log=$(stat -c %Y treino.log 2>/dev/null || echo 0)
mt_sup=$(stat -c %Y supervisor.log 2>/dev/null || echo 0)
passo=$(grep -aoE 'passo +[0-9]+/' treino.log 2>/dev/null | tail -1 | grep -oE '[0-9]+')

echo "D $agora $(( agora - mt_log )) ${passo:-0} $(( agora - mt_sup ))"
tail -1 supervisor.log 2>/dev/null | sed 's/^.*UTC] //'
