# RunPod Instant Clusters — vale para o Bee-1B? (2026-08-12)

Avaliação pedida pelo Bruno. Agora dá para responder com **throughput medido**, não com
especificação de folheto: o Bee-150M acabou de rodar 21,7B tokens de ponta a ponta.

## A âncora: o que a RTX 5090 realmente entregou

| | medido |
|---|---|
| modelo | 151,2M params |
| tokens | 21,7B |
| tempo | 96,47 h (347.292 s) |
| custo | ~US$ 97 (US$ 0,99/h) |

Pela conta de `6ND`: `6 × 151,2e6 × 21,7e9 = 1,97e19 FLOPs` em 347.292 s →
**5,67e13 FLOP/s efetivos**. Esse é o número a usar para projetar, porque já inclui tudo que
uma especificação esconde: dataloader, otimizador, checkpoint, teto elétrico.

## Projeção para o Bee-1B numa única 5090

| tokens | FLOPs | tempo | custo |
|---|---:|---:|---:|
| 20B (Chinchilla, 20× params) | 1,2e20 | **588 h ≈ 24,5 dias** | ~US$ 582 |
| 40B | 2,4e20 | 49 dias | ~US$ 1.164 |
| 143B (mesma razão tokens/params do 150M) | 8,6e20 | 175 dias | ~US$ 4.160 |

## ⭐ A conclusão que muda a decisão: o 1B **cabe** numa 5090

Pré-treino full custa ~12–16 bytes/param (pesos + grads + estados fp32 do Adam):
**1B ≈ 16 GB**, e a 5090 tem **32 GB**. O run do 150M usou 7,8 GB de 32.

Ou seja: **não precisamos de cluster para o modelo caber.** Precisaríamos de cluster só para
o run não durar 25 dias. Isso muda completamente a natureza da pergunta.

## O que um cluster compra — e o que ele cobra

Com escala perfeita, 8 GPUs fazem em 73,5 h o que uma faz em 588 h, **pelo mesmo custo total**
(8× o preço/hora ÷ 8× menos horas). Escala perfeita não existe: em treino distribuído por
rede, a eficiência típica fica entre 70% e 85% por causa da sincronização de gradientes.

> **Cluster não economiza dinheiro. Ele compra tempo, e cobra um ágio de 15–40% por isso.**

Para o Bee-1B a 20B tokens: **~3,5–4,3 dias por ~US$ 670–815**, contra 24,5 dias por US$ 582.

## Por que eu não recomendaria agora

1. **O código é single-GPU.** `pretrain.py` não tem FSDP nem DeepSpeed. Portar, depurar
   sincronização e validar que a loss distribuída bate com a single-GPU é trabalho real — e é
   exatamente a classe de mudança onde este projeto já se queimou três vezes com dado sumindo
   ou rótulo deslocado *sem erro nenhum*.
2. **Não temos throughput medido do 1B.** Toda a tabela acima assume que a eficiência de
   FLOP/s do 151M se mantém em 1B. É plausível (o modelo maior tende a usar melhor a GPU), mas
   **é uma suposição, e suposição não dimensiona hardware neste projeto.**
3. **O degrau natural é o 500M, não o 1B.** ~10B tokens, ~8 dias, ~US$ 190 numa 5090 — e
   confirma se a curva de escala se comporta antes de comprometer 4 dígitos.

## O que fazer antes de decidir (custo: ~US$ 0,10)

O mesmo protocolo que salvou a escolha de GPU da última vez:

```bash
python bee/pretrain.py --params 1b --passos 40 --dry-run   # cabe? quanto de VRAM?
python bee/pretrain.py --params 1b --passos 40             # tok/s em regime
```

Cinco minutos numa 5090 dão o throughput real do 1B. Com ele, a tabela acima deixa de ser
projeção e vira orçamento — e aí a conversa sobre cluster passa a ter base.

⚠️ **Ler o log inteiro, a partir do passo ~20, com três leituras consecutivas coincidentes.**
Numa única hora deste projeto eu errei o throughput três vezes seguidas lendo números soltos,
e cada erro produziu uma recomendação de hardware diferente.

## Veredito

**Instant Clusters: não agora.** Guardar para quando (a) o 500M estiver medido, (b) o
`pretrain.py` tiver caminho distribuído testado contra o single-GPU, e (c) houver um run cujo
tempo em uma GPU seja inaceitável — não apenas longo. Hoje o Bee-1B em 20B tokens custa
US$ 582 e 25 dias numa placa só, sem uma linha de código novo. Esse é o caminho barato.
