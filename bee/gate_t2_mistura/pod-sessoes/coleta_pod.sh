#!/usr/bin/env bash
# Completa a coleta no pod: os 4 idiomas que nao estao a 100% localmente.
#
# ORDEM POR VALOR, de proposito: deu e fra estao em ZERO (2,5B tokens cada), jpn em 3,4%
# (+2,41B), spa em 83,5% (+0,41B). Se o pod morrer no meio, o que ja' desceu e' o que mais vale.
#
# ⚠️ ESTE POD NAO TEM VOLUME DE REDE — so' um overlay de 60 GB (45 livres). Tudo aqui e'
#    efemero: se o pod cair ou for encerrado antes do download, a coleta se perde. Por isso o
#    lado de ca' baixa idioma a idioma, em vez de esperar o fim.
#
# ⭐ O coletor le' o fineweb-2 com streaming=True e SEM shuffle: o que ele pega e' o PREFIXO
#    deterministico do stream. Logo os shards 0000..0053 de `spa` que ja' existem localmente
#    devem sair identicos aqui — o que sera' VERIFICADO por hash antes de aproveitar, nunca
#    suposto.
set -eo pipefail
cd /root
echo "########## COLETA  $(date -u '+%H:%M UTC')  ·  livre: $(df -h / | awk 'NR==2{print $4}')"
bash bee/coletar_1g.sh --idiomas deu,fra,jpn,spa
echo "########## COLETA ENCERRADA  $(date -u '+%H:%M UTC')"
