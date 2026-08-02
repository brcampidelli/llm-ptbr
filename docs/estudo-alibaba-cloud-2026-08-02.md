# Estudo — Alibaba Cloud (GPU) aplicado ao Bee

**Data:** 2026-08-02 · **Método:** multi-agente (2 pesquisadores paralelos: catálogo/preço · crédito/atritos/BR) ·
**Ponto de partida:** página de campanha `alibabacloud.com/en/campaign/cloud-server`.

> Pergunta: o Alibaba Cloud vale pra treinar o Bee (LLM 150M→escalando, ~31h/run, cabe em 24GB)?
> **Resposta curta: NÃO pra um solo brasileiro hoje. Fica EMPATADO/ABAIXO da GCP no ranking — e por um
> motivo pior que a GCP: falta de disponibilidade de GPU no portal internacional (ClusterMAX classifica
> como "Unavailable Tier"), somada a preço maior e 3 atritos empilhados.**

⚠️ **Confiança:** famílias de instância e modelos de GPU vêm dos **docs oficiais** (alta confiança). Os
**preços $/h vêm de agregadores terceiros** (DeployBase jun/2025 e mar/2026) — o console exige login e não
expõe GPU em tabela pública. Trate preço como ordem de grandeza, não cotação.

---

## 1. Catálogo de GPU (ECS, oficial)

| Família | GPU | VRAM | cabe o Bee? |
|---|---|---|:---:|
| gn6i | T4 | 16 GB | ❌ |
| gn6v/gn6e | V100 | 16/32 GB | ⚠️ 32GB sim |
| gn7i | A10 | 24 GB | ⚠️ justo |
| **gn7 / ebmgn7** | **A100** | **40 GB** | ✅ encaixe |
| **gn7e / ebmgn7e** | **A100** | **80 GB** (NVLink) | ✅ (multi-GPU) |
| gn8v | H100 | 80–96 GB* | ⚠️ disponibilidade incerta |
| gn9g | Blackwell | 48–72 GB | ⚠️ não confirmado |

*Doc lista "H100 96GB" (H100 padrão é 80GB — SKU especial ou erro de extração). Regiões internacionais:
**Singapura, Tóquio, Mumbai, Sydney** (China é portal/conta separados).

## 2. Preço (agregadores — média/baixa confiança) e custo/run

| GPU | Alibaba intl on-demand | RunPod (baseline) |
|---|---:|---:|
| A100-40GB | ~$1,80–2,20/h | — |
| A100-80GB | ~$2,45/h | **$1,39/h** |
| H100-80GB | ~$3,20–4,50/h | **$2,99/h** |

**Custo de UM run do Bee (~31h A100):** Alibaba **~$62–76** vs **RunPod ~$43** → **+44% a +77% mais caro**.
Spot da Alibaba (se confiável) daria ~$22–26, **mas o spot internacional é justamente o que menos se
confirmou** (o portal intl não expõe tier de spot tão claro quanto os players chineses domésticos). Reserved
(1–3 anos) não faz sentido pra run único.

## 3. ⚠️ Restrições de exportação (crítico)
- **A100/H100** banidos p/ China desde 2022; **H800/A800** (variantes NVLink-capado) banidas 2023; **H20**
  restrita 2025. **AI Diffusion Rule (2025)** pôs **Singapura/Malásia/Índia/UAE em tier intermediário** com
  licença/VEU pra chips avançados.
- **Pro Bee:** o **A100 (gn7/gn7e) É oferecido em Singapura** — aposta realista. **H800/H20 são mercado
  chinês** (não conte). **H100 (gn8v)** no catálogo, mas provisionar como cliente novo em Singapura sob o AI
  Diffusion Rule é **incerto**.

## 4. Atritos pra usuário BR solo (o que mata)
1. **Free trial NÃO cobre GPU** (mesma pegadinha da GCP): o grátis é **ECS CPU 1-core/1GB por 12 meses**; há
   créditos pay-as-you-go (~$300–1.200, **60 dias**, valor pra PF não confirmado), mas GPU sai do bolso +
   depende de quota. Sem Free Tier permanente com GPU.
2. **KYC com revisão manual (~3 dias úteis)** + documento oficial. RunPod = cadastra e usa na hora.
3. **Quota de GPU** precisa ser pedida e justificada (igual/pior que GCP).
4. **Cartão:** aceita Visa/Master/Amex internacional (cobra $1 de pré-auth), **mas há relatos de bloqueio de
   transação** — sem PayPal/pré-pago/virtual.
5. **Disponibilidade:** **ClusterMAX (SemiAnalysis) = "Unavailable Tier"** — GPUs modernas não prontamente
   disponíveis fora da China; foco é o mercado doméstico. Este é o veredito que mais pesa.

## 5. Residência de dados / risco
Cloud chinesa → o **governo dos EUA já escrutinou** como a Alibaba guarda dados. Corpus do Bee é público
(baixo risco), mas "treinei em cloud chinesa" pode virar **pergunta desconfortável em due diligence** se
buscar investimento EUA/Europa. Ponto de imagem que RunPod/Vast/GCP não têm.

## 6. PAI-Lingjun (treino distribuído)
Existe internacionalmente (Singapura): DLC, RDMA 800Gbit/s, caso oficial de pré-treino do **Qwen2-72B** em
4 nós × 8 A100/A800/H800. **Overkill pro Bee hoje** (1 GPU). Começa a fazer sentido só em **7B+ multi-nó** —
e aí compare com clusters H100 de RunPod/CoreWeave/Lambda antes.

## 7. 🇧🇷 Novidade a vigiar: Data Center Alibaba em São Paulo (ago/2026)
A Alibaba inaugurou seu **1º DC no Brasil (SP) em agosto/2026**, com promessa de preço **~30% abaixo de
AWS/GCP**. ⚠️ **NÃO confirmado se o DC de SP oferece GPU/IA self-service no lançamento** (cobertura fala em
"DC para IA" sem SKU público; provavelmente nasce enterprise-first). **Gatilho de reavaliação:** se SP
publicar SKUs de GPU (A100/H100) com preço baixo + billing self-service → "GPU local em SP + latência mínima
do BR + preço" mudaria o jogo. Vale um lembrete pra checar em 1–2 meses.

---

## Veredito pro Bee

**Ranking atualizado:** `Vast ≫ RunPod > Brev ≈ Colab > GCP ≥ Alibaba Cloud`.

Alibaba fica **empatada/abaixo da GCP**, e pior: a GCP ao menos tem GPU depois que você vence a quota; na
Alibaba internacional o gargalo é **a própria disponibilidade de GPU** ("Unavailable Tier") + preço maior +
KYC 3 dias + quota + risco de cartão BR. Contra o RunPod (cadastro instantâneo, GPU on-demand, cartão BR,
sem KYC pesado), perde em todos os eixos que importam pra treinar **hoje**.

**Recomendação:** **RunPod como principal, Vast como spot barato.** Não investir tempo abrindo conta Alibaba
agora. **Único gatilho:** o DC de São Paulo publicar GPU self-service com preço baixo — checar em 1–2 meses.

## Incertezas honestas
- Preço $/h oficial (só agregadores; console exige login). Spot A100 intl não confirmado.
- Valor/validade do crédito grátis pra **pessoa física** (fontes divergem $300–1.200/60d).
- Se o DC de SP tem GPU no lançamento (sem SKU oficial).
- Caso real de conta BR nova rodando GPU na Alibaba intl (não encontrado).

**Fontes:** [GPU instance families (oficial)](https://www.alibabacloud.com/help/en/egs/gpu-accelerated-compute-optimized-instance-families) ·
[PAI-Lingjun (oficial)](https://www.alibabacloud.com/en/product/pai-lingjun) ·
[ClusterMAX/SemiAnalysis "Unavailable Tier"](https://www.clustermax.ai/cloudreview/alibabacloud) ·
[DeployBase intl GPU pricing](https://deploybase.ai/articles/alibaba-cloud-gpu-pricing-for-international-users) ·
[Free Trials (oficial)](https://www.alibabacloud.com/help/en/user-center/product-overview/learn-about-free-trials) ·
[Real-name verification (oficial)](https://www.alibabacloud.com/help/en/account/real-name-authentication/) ·
Jornal do Comércio / Convergência Digital (DC São Paulo, ago/2026).
