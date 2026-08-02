# Estudo — GPU no Google Cloud (Compute Engine) aplicado ao Bee

**Data:** 2026-08-02 · **Método:** multi-agente (3 pesquisadores paralelos: catálogo/specs · preço/crédito ·
como-treinar/atritos) · **Fonte pedida:** `docs.cloud.google.com/compute/docs/gpus?hl=pt-br` + páginas ligadas.

> Pergunta: o Google Cloud é bom lugar pra treinar o **Bee** (LLM 150M, cabe em ~24GB com Liger, ~31h/run,
> checkpoint a cada 250 passos, corpus ~26GB)? Comparado a Colab / Vast / RunPod / Brev.
> **Resposta curta: tecnicamente sim, mas é a PIOR combinação de preço + atrito das opções — e o
> atrito nº1 (quota de GPU) transforma o "crédito grátis de US$300" num beco sem saída pra conta nova.**

⚠️ **Honestidade de método:** as tabelas oficiais do GCP renderizam por JavaScript e a página de preço
truncou/redirecionou no fetch. Specs de VRAM são padrão de indústria (confiáveis); **preços e
disponibilidade por zona vêm de agregadores (Thunder Compute, gpucost.org, CloudZero) — trate como ±10%
e confirme no console/calculadora GCP na hora.**

---

## 1. Catálogo de GPU (o que cabe o Bee)

| GPU | VRAM | Família de máquina | cabe o Bee (~24GB)? |
|---|---|---|:---:|
| T4 | 16 GB | N1 (anexável) | ❌ não cabe |
| V100 | 16 GB | N1 | ❌ |
| P100 / P4 | 16 / 8 GB | N1 (legado) | ❌ |
| **L4** | **24 GB** | **G2** | ⚠️ cabe **justo** (o "folgado" some; L4 é lenta pra LLM) |
| **A100 40GB** | 40 GB | **A2 Standard** (`a2-highgpu-1g`) | ✅ **encaixe ideal** |
| A100 80GB | 80 GB | A2 Ultra (`a2-ultragpu-1g`) | ✅ (é a referência dos 31h; exagero de VRAM p/ 150M) |
| H100 80GB | 80 GB | A3 | ✅ exagero (1/2/4 GPUs só saem em Spot/Flex-start) |
| H200 / B200 | 141 / ~180 GB | A4 (bloco de 8) | ✅ exagero absurdo · escassas |

**Leitura:** pro 150M, **A100-40GB** é o encaixe certo (cabe folgado, mesma classe de velocidade da A100-80GB
— o treino não é limitado por VRAM e sim por compute). **L4 24GB** é o piso barato, mas bem mais lenta →
wall-time real > 31h. Tudo de A100 pra cima é exagero de memória.

## 2. Preço — GCP NÃO é competitivo fora do crédito

| Provedor / modo | GPU | $/h | Custo/run (~31h) |
|---|---|---:|---:|
| **Vast.ai** | RTX 4090 24GB | ~$0,28 | **~$9** ⭐ mais barato |
| **RunPod** | RTX 4090 24GB | ~$0,69 | ~$21 |
| **GCP Spot** | A100-40GB | ~$1,10 | **~$34** |
| **RunPod** | A100-80GB | ~$1,39 | ~$43 (preço fixo, sem preempção) |
| **GCP Spot** | A100-80GB | ~$2,00 | ~$62 |
| **GCP on-demand** | A100-80GB | ~$5,07 | **~$157** 🔴 cobra a VM inteira |

- **On-demand GCP (~$157) é 4-7× mais caro** que RunPod A100-80GB ($43) ou Vast. Até o **Spot GCP (~$62)
  perde** pro RunPod on-demand ($43).
- Descontos: Spot 60-91% (flutua, preempta); **Committed-Use (1-3 anos) é inútil** pra runs esporádicos.
- ⚠️ Ressalva do 4090 (Vast/RunPod): os 31h são medidos em A100; no 4090 o Bee cabe mas o wall-time difere
  (provavelmente maior) — o custo/run consumer é ordem de grandeza, não exato.

## 3. O crédito de US$300 e o MURO da quota (o fator decisivo) 🔴

O único atrativo do GCP é o **crédito grátis de US$300 (90 dias)** — cobriria ~2 runs on-demand ou ~5-7
Spot **de graça**. **MAS** esbarra no atrito nº1, confirmado nos docs:

1. **Conta nova = quota 0 de GPU.** A quota `GPUS_ALL_REGIONS` vem em `0.0`. Erro clássico ao subir a VM:
   `Quota 'GPUS_ALL_REGIONS' exceeded. Limit: 0.0 globally`.
2. **O trial de US$300 está PROIBIDO de pedir aumento de quota** (doc explícito: conta de teste "não será
   possível solicitar uma mudança na cota"). → **beco sem saída:** com o crédito trial você **não roda GPU**.
3. **Precisa fazer upgrade pra conta paga** (billing ativo) primeiro — o crédito continua valendo. Aí pode
   pedir quota, **mas** conta nova sem histórico de faturamento costuma ser **rejeitada ou jogada pra
   "contate Vendas"**. Relato documentado: 48-72h travado mesmo com billing pago + ID verificado, sem
   resolver no período.
4. **Quota Spot é SEPARADA** (`PREEMPTIBLE_GPUS` / `NVIDIA_L4_GPUS`) — pro plano Spot, pedir a certa.

→ **Vast e RunPod NÃO têm quota nenhuma** — aluga e começa em minutos. Pra sair do Colab **hoje**, ganham
de lavada.

## 4. Como treinar (se passar do muro) — resumo

- **Imagem Deep Learning VM (DLVM)** = "Colab pronto" sem desconexão: PyTorch + CUDA + driver + cuDNN/NCCL
  já instalados. Família `pytorch-latest-gpu`, project `deeplearning-platform-release`.
- VM Spot: `--provisioning-model=SPOT --instance-termination-action=STOP` + **startup script** que detecta
  o último checkpoint no disco e retoma. Preempção manda ACPI soft-off (~30s de aviso) → shutdown script
  dá `sync` no checkpoint.
- **Disco persistente SOBREVIVE à preempção** (é o que salva nosso checkpoint a cada 250 passos — grave no
  pd, nunca só em RAM/boot efêmero). `pd-balanced` ~$0,10/GB/mês → ~$10/mês num disco de 100GB (barato; o
  custo real é GPU-hora).
- ⚠️ **Taxa de preempção de GPU Spot não é publicada** — GPUs são disputadas; em zona congestionada a VM
  pode não religar. Mitigação = checkpoint frequente (já temos) + múltiplas zonas + fallback on-demand se
  o prazo apertar.

## 5. Pegadinhas de custo (confirmadas)

- **Disco cobra com a VM DESLIGADA** — só deletar o disco para de cobrar (erro clássico de "desliguei, achei
  que parou"). Boot disk da DLVM (~50-100GB) também soma.
- **IP estático ocioso cobra o DOBRO** (~$0,01/h reservado-não-usado vs $0,005 em uso) → usar **IP efêmero**.
- **Egress** ~$0,12/GB (ingress grátis → subir corpus de 26GB é free; baixar o modelo de 150M é trivial).
  Manter disco+VM na **mesma zona**.
- **VM RUNNING cobra GPU mesmo sem treinar** → `STOP` ao terminar. Cuidado com `DELETE` na preempção
  (apaga a VM; disco de dados com auto-delete OFF).

---

## Veredito pro Bee

**GCP fica em ÚLTIMO das 4 nuvens** pra um run rápido/solo do Bee — pior preço (fora do crédito) e pior
atrito (quota). O crédito de US$300 é sedutor mas **não descola do muro da quota** numa conta nova.

- **Sair do Colab agora, barato, sem burocracia:** **Vast (4090 ~$9)** → **RunPod (4090 $21 / A100 $43)**.
  Continua a recomendação anterior. Brev (NVIDIA) e GCP não competem em atrito.
- **Quando o GCP compensa:** se o Bruno **já for/virar conta paga com histórico de billing**, quiser infra
  integrada (IAM, buckets, múltiplas zonas pra caçar Spot) e **pedir a quota `NVIDIA_L4_GPUS`/`PREEMPTIBLE_GPUS`
  dias antes**. Aí: DLVM PyTorch em **A100-40GB Spot** (~$34/run) ou **L4 Spot**, com o crédito de US$300
  potencialmente cobrindo alguns runs de graça — **desde que a quota saia**.
- **Escalar 500M-1B depois:** A100-80GB (`a2-ultragpu-1g`); H100 só quando o gargalo virar tempo, não VRAM.

**Ranking final (Bee-150M, run rápido):** Vast ≫ RunPod > Brev ≈ Colab Pro+ > **GCP** (só sobe se o crédito
US$300 clarear a quota).

---

## Incertezas honestas
- Preços on-demand exatos do GCP: página oficial truncou no fetch; números de agregadores (±10%).
- Se o ~$5,07/h da A100-80GB inclui 100% da VM `a2-ultragpu-1g` (vCPU/RAM podem somar).
- Preço Spot exato flutua trimestralmente; **taxa de preempção de GPU não é publicada** (só empírico).
- Prazo/chance de aprovação de quota não é cravado em doc (relatos: minutos com histórico; dias/rejeição sem).
- VRAM da B200 no GCP e preço isolado de H200/B200 não confirmados na fonte primária.

**Fontes:** [GCP GPU machine types](https://docs.cloud.google.com/compute/docs/gpus) ·
[Accelerator-optimized machines](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines) ·
[GPU regions & zones](https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones) ·
[Spot VMs](https://docs.cloud.google.com/compute/docs/instances/spot) ·
[Allocation quotas](https://docs.cloud.google.com/compute/resource-usage) ·
[GCP Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features) ·
gpucost.org/GCP · Thunder Compute · CloudZero (ago/2026).
