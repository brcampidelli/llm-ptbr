# Estudo — Hugging Face (Pricing · Spaces · ZeroGPU) aplicado ao Bee

**Data:** 2026-08-02 · **Método:** multi-agente (3 pesquisadores paralelos: pricing/Jobs · Spaces · ZeroGPU) ·
**Fontes pedidas:** huggingface.co/pricing, /spaces/launch, /docs/hub/spaces-zerogpu.

> Pergunta: a Hugging Face serve pro Bee (LLM 150M, ~31h de pré-treino, cabe em ~24GB)? Pra **treinar**,
> **hospedar**, **servir** ou **demo**? **Resposta curta: a HF é o ecossistema full-stack natural do Bee —
> imbatível ($0) pra HOSPEDAR os pesos+corpus e pro DEMO; e tem uma opção real de TREINO (HF Jobs, ~$78/run)
> que é sem-atrito mas não a mais barata. Spaces/ZeroGPU NÃO treinam (teto de 120s por chamada).**

⚠️ **Regra de ouro da HF:** a assinatura mensal ($9 PRO / $20 Team / $50 Ent) compra **features e cota** —
**não compra compute**. GPU-hora e storage acima da cota são pagos à parte, medidos por minuto. Valores de
jul-ago/2026; a HF reajusta — confirmar no billing na hora.

---

## As 5 etapas do Bee na HF — onde e quanto custa

| Etapa | Onde na HF | Custo |
|---|---|---:|
| **TREINAR** (pré-treino 31h A100) | **HF Jobs** (A100 large $2,50/h, pay-as-you-go, sem assinatura) | **~$78/run** |
| **HOSPEDAR** pesos (150M ≈ 300MB) + corpus (26GB público) | Hub / LFS | **$0** |
| **DEMO** interativo (pós-SFT) | **Spaces + ZeroGPU** (Gradio) ou CPU Basic | **$0** |
| **SERVIR** em produção | Inference Endpoints (T4 $0,50/h, pausável) | centavos → ~$360/mês 24/7 |
| **SFT** (fine-tune leve depois) | HF Jobs (A100/L4) | horas × $0,80-2,50 |

**Free vs PRO ($9/mês):** pra publicar o Bee e rodar o demo, **Free basta**. PRO só se justifica pra demo
robusto (ZeroGPU 8× cota + prioridade de fila) e folga de storage privado (1TB vs 100GB). Nada obrigatório.

---

## 1. HF Jobs — a opção de TREINO (achado principal) 🎯

Existe compute pago-por-uso pra workload arbitrário (fine-tune, **pré-treino**, inferência) via `hf jobs`
CLI/Python/API — roda um comando + imagem Docker no hardware escolhido.
- **Requisito:** só **saldo positivo** no billing — **não exige PRO**. Sem crédito grátis incluso; paga o que usa.
- **Cobrança:** por minuto (build não conta; falha suspende). ⚠️ **timeout default 30min** → setar `--timeout 40h`
  senão o job morre no meio.
- **A100 large (80GB): $2,50/h** → pré-treino do Bee (~31h) = **~$78/run**. Outros: L40S $1,80 · A10G $1,00-1,50 ·
  H200 $5,00 · RTX PRO 6000 $2,75 · CPU $0,01. (Sem H100 no catálogo de Jobs.)

**Leitura:** treinar o Bee inteiro na HF custa ~$78 numa A100, **sem muro de quota** (≠ GCP) e **já integrado
ao Hub** (corpus e pesos vivem lá). Mais caro que Vast/RunPod, mas o menor atrito de todos pra quem já está
no ecossistema HF.

## 2. Spaces — é pra HOSPEDAR demo, NÃO treinar

- Space = repo Git que hospeda **app/demo** (Gradio / Streamlit / Docker / Static). Confirmado: **não é
  plataforma de treino** (execução app-oriented, disco efêmero, sleep por ociosidade).
- Hardware ($/h): CPU Basic **grátis** · CPU Upgrade $0,03 · T4 $0,40-0,60 · L4 $0,80 · A10G $1,00-1,50 ·
  A100 80GB $2,50. (H100 removido em dez/2025.) Pago **não dorme** por padrão (cobra 24/7) — configurar
  sleep/pause pra zerar custo ocioso.
- **31h de pré-treino num Space = não** (modelo de execução errado, disco efêmero, sleep, e no ZeroGPU o
  teto de 120s por chamada). Space entra só **depois do SFT**, pro demo.
- ⚠️ Criar Space **com compute** (mesmo CPU grátis) hoje pode exigir plano pago na conta — confirmar.

## 3. ZeroGPU — GPU grátis, mas só pra DEMO (nunca treino)

- Alocação **dinâmica** de GPU (só durante função `@spaces.GPU`): **NVIDIA RTX Pro 6000 Blackwell** fatiada —
  `large`=48GB (default) / `xlarge`=96GB. ⚠️ Não é mais H200 (era em 2024-25; a doc atual diz RTX Pro 6000).
  **Só Gradio + PyTorch 2.8+.**
- **Limites que definem tudo:** **teto de 120s por chamada** (hard cap, não sobe nem no PRO) · quota diária
  **5min free / 40min PRO** · Spaces ZeroGPU: 2 (free) / 10 (PRO).
- **Treinar? NÃO, categórico** — 120s/chamada + quota em minutos/dia + sem estado de GPU persistente entre
  chamadas. "Not designed for long-running training."
- **Demo do Bee? SIM, ideal** — 150M em bf16 ocupa <1-2GB (slice tem 48GB, sobra centenas de vezes); geração
  curta roda em <60s; **grátis** até no tier free (2 Spaces, 5min/dia). Só lembrar: **tem que ser Gradio**.

## 4. Storage — hospedar Bee + corpus = $0

- **Repo público** (models/datasets): grátis, best-effort, sem limite rígido. Corpus 26GB público cabe folgado
  (é dataset com valor pra comunidade — o caso que eles querem). Manter poucos arquivos Parquet (<100k arquivos).
- **Privado:** Free 100GB · PRO 1TB. Pesos do Bee (~300MB fp16) = insignificante.
- Storage pago só se estourar: público $12/TB/mês, privado $18/TB/mês — **o Bee está ordens de magnitude
  abaixo → custo esperado $0.**

---

## Veredito pro Bee

A HF **não** é onde o Bee-150M treina mais barato — mas é onde ele **mora**:

- **TREINAR:** HF Jobs (~$78/run A100) entra no ranking como opção **sem-atrito** (sem quota, integrada ao Hub),
  porém mais cara que Vast ($9) / RunPod ($21-43) / GCP-Spot ($34). Boa como fallback frictionless se o Colab
  cair e não quiser mexer em Vast.
- **HOSPEDAR + DEMO:** aqui a HF é **imbatível ($0)** — Hub pros pesos/corpus, ZeroGPU/CPU pro demo pós-SFT.
  Nenhuma outra opção compete nisso. É o destino natural do Bee publicado.
- **SERVIR produção:** Inference Endpoints se um dia virar produto com tráfego.

**Ranking de TREINO atualizado (Bee-150M, run rápido):**
Vast (~$9) ≫ RunPod-4090 ($21) > GCP-Spot-A100 ($34, *se* a quota sair) > RunPod-A100 ($43) > **HF Jobs ($78)** >
GCP on-demand ($157). **HF Jobs = o mais caro dos "sem-atrito", mas o mais integrado.**

**Papel definido da HF no projeto:** casa dos pesos e do corpus (grátis), casa do demo (grátis via ZeroGPU),
e uma via de treino de conveniência (Jobs) — não a via barata.

---

## Incertezas honestas
- Preços de assinatura/hardware são snapshot jul-ago/2026; HF reajusta — conferir no billing.
- "Best-effort" do storage público grátis não é número garantido; 26GB é seguro hoje.
- HF Jobs cobra por minuto real → os ~$78 são sobre as 31h nominais de A100 (data-loading real fatura).
- ZeroGPU: cold-start exato em segundos não publicado (pra 150M é ordem de segundos); teto 120s às vezes
  "estica" a 240s de forma não-confiável — tratar 120s como firme; quota PRO 40min/dia (doc atual; fóruns
  antigos diziam 25min).

**Fontes:** [HF Pricing](https://huggingface.co/pricing) · [HF Jobs](https://huggingface.co/docs/hub/jobs) ·
[Jobs Pricing](https://huggingface.co/docs/hub/jobs-pricing) · [Spaces](https://huggingface.co/docs/hub/spaces) ·
[Spaces GPUs](https://huggingface.co/docs/hub/spaces-gpus) · [ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu) ·
[Inference Endpoints Pricing](https://huggingface.co/docs/inference-endpoints/pricing) ·
[Storage Limits](https://huggingface.co/docs/hub/storage-limits).
