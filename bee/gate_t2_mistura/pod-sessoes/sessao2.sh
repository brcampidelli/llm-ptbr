set -e
cd /root
echo "########## [1/3] FORMA — 4 formas, cabecas compativeis"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_throughput_1g.py   --pool bee/gate_t2_mistura/pool_pt-50.bin --passos 40 --grad-checkpoint   --micro-batches 4 --seq-lens 2048   --formas 16:2560:40:10:5504,24:2048:32:8:4672,28:1792:28:4:4928,40:1536:24:6:3840 2>&1 | grep -vE 'Loading|it/s]'
echo "########## [2/3] LR estendido para BAIXO — o melhor estava na borda"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_lr_1g.py   --pool bee/gate_t2_mistura/pool_pt-50.bin --lrs 1.25e-4,2.5e-4,5e-4,1e-3,2e-3 --passos 1000 2>&1 | grep -vE 'Loading|it/s]'
echo "########## [3/3] TRANSFERENCIA"
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python3 bee/gate_t2_mistura.py treinar   --bracos bal-12,pt-50 --sementes 42,43,44 --passos 3051 2>&1 | grep -E 'BRACO|guarda de rot|runs:|epocas'
echo "########## SESSAO COMPLETA"
