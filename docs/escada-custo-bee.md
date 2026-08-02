# Escada de custo do Bee — de 150M a modelo grande

**Data:** 2026-08-02 · **Base de preço:** RunPod (a plataforma recomendada — ver
[estudo-ferramentas-nlp-gpu](estudo-ferramentas-nlp-gpu-2026-08-02.md)).

> Quanto custa evoluir o Bee de 150M → 350M → … → modelo grande? Estimativa ancorada em **dado real**:
> o Bee-150M treina a **~85k tok/s numa A100-80GB** e faz **9,87B tokens em ~31h** (MFU ~25% — a
> arquitetura fundo-e-fina é ineficiente em GPU, como o `bee/pretrain.py` documenta). A partir daí é
> física: **custo ≈ 6 × params × tokens ÷ (eficiência × FLOPs por dólar da GPU)**.

## Tabela (preços RunPod, on-demand)

| Bee | Params | Tokens de treino | GPU sugerida | Tempo aprox. | **Custo on-demand** | Com Spot (~−40%) | Faixa |
|---|---|---|---|---|---:|---:|---|
| **150M** ✅ | 150M | 10B | 1× A100-80GB | ~31h | **~$45** | ~$25 | solo/grátis |
| **350M** | 350M | 20B | 1–2× A100 | ~4–6 dias | **~$200** | ~$120 | solo |
| **500M** | 500M | 30B | 2× A100 | ~5–7 dias | **~$450** | ~$270 | solo |
| **1B** | 1B | 50B | 4× A100 | ~10–12 dias | **~$1.500** | ~$900 | solo/doação |
| **3B** | 3B | 100B | 8× H100 | ~7–8 dias | **~$4.500** | ~$2.700 | patrocínio |
| **7B** | 7B | 200B | 8–16× H100 | ~2–5 semanas | **~$20.000** | ~$12.000 | investimento |
| **13B** | 13B | 350B | 16× H100 | semanas | **~$65.000** | ~$40.000 | investimento |
| **30–70B** (fronteira) | 30–70B | 1–2 **trilhões** | cluster 256–1024× H100 | meses | **US$ 1–10 milhões+** | — | cluster |

## Método e premissas (honestas)
- **Fórmula:** FLOPs de treino `C = 6 · N · D` (N = params, D = tokens). Custo `= C · ($/h) ÷ (MFU · pico_FLOPs · 3600)`.
- **Âncora empírica:** 150M @ 10B tok em 31h numa A100 → 80 TFLOP/s efetivos → **MFU ≈ 25%** (bate com
  a nota do `pretrain.py`: "~26% do teto da L4"). Usei MFU 25% até 1B (A100) e ~35% de 3B pra cima
  (H100 satura melhor com matmuls maiores).
- **Preços RunPod:** A100-80GB **$1,39/h**, H100-80GB **$2,99/h**. Multi-GPU escala linear em $ e tempo
  (mais GPUs = proporcionalmente mais caro/hora e menos horas → o custo total não muda).
- **Spot/Community (RunPod) corta ~40%** — seguro pra nós porque fazemos checkpoint a cada 250 passos.
- **Incerteza ±50%:** MFU real, preço de GPU (flutua) e o orçamento de tokens escolhido movem o número.

## As duas alavancas
1. **Params × tokens multiplicam.** Dobrar params E dobrar tokens = **4× o custo**. É por isso que a
   escada sobe rápido.
2. **Tokens é a alavanca que você controla.** Usei orçamentos "over-trained" (~30–66 tok/param — filosofia
   SmolLM, bom pra modelo pequeno rodar barato depois). Cortar pra **Chinchilla-ótimo (~20 tok/param)**
   derruba o custo ~40–50% em cada linha, ao preço de um modelo um pouco menos afiado.

## Veredito (onde parar / onde investir)
- **Até Bee-1B (~$1–2k):** faixa de **solo / doação**. Um 1B PT-forte já é útil e publicável — teto
  natural do bootstrap.
- **Bee-3B a 13B ($5k–65k):** faixa de **patrocínio / investimento pequeno**. Precisa de cheque, mas é
  acessível a uma startup.
- **30B+ fronteira ($1M+):** só com **investimento de verdade / cluster**. Outro jogo.

**A boa notícia:** o código é o MESMO em todos os degraus — só muda `--tamanho` e a fatura. Cada real de
doação/investimento vira capacidade direta, sem reescrever nada. É o desenho do projeto (a esteira que
roda em qualquer escala).

> Ver também a "Escada de escalonamento" do plano (`bee`), que já previa as duas paredes (VRAM e tempo).
> Esta tabela atualiza aquela com **preços reais de RunPod** e a **âncora empírica de MFU** do v1/v3.
