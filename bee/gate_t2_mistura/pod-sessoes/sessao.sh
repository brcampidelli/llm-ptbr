set -e
cd /root
echo "########## [1/3] VARREDURA DE FORMA (4 formas, ~985M nao-emb)"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_throughput_1g.py   --pool bee/gate_t2_mistura/pool_pt-50.bin --passos 40 --grad-checkpoint   --micro-batches 4 --seq-lens 2048   --formas 16:2432:6592,24:1984:5376,28:1856:4992,40:1536:4160 2>&1 | grep -vE 'Loading|it/s]'
echo "########## [2/3] SWEEP DE LR (grade que cerca a Step Law)"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_lr_1g.py   --pool bee/gate_t2_mistura/pool_pt-50.bin --lrs 5e-4,1e-3,2e-3 --passos 1000 2>&1 | grep -vE 'Loading|it/s]'
echo "########## [3/3] BRACO DE TRANSFERENCIA"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_t2_mistura.py treinar   --bracos bal-12,pt-50 --sementes 42,43,44 --passos 3051 2>&1 | grep -E 'BRACO|guarda de rot|passo  3050|runs:'
echo "########## SESSAO COMPLETA"
