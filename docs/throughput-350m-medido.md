# Throughput do Bee-350M na RTX 5090 — medido (2026-08-14)

> **Custo da medição: ~US$ 0,15.** Pod `bee-350m-throughput` (`d0jq0zih4mqdv0`), RTX 5090,
> US$ 1,02/h. E ela **derrubou a projeção de custo do estudo pela metade**.

---

## O número que importa

| | FLOP/s efetivo | 21,75B tokens | US$ |
|---|---:|---:|---:|
| **projeção do estudo** (extrapolada do 151M) | 5,670e13 | 220,3 h | **218** |
| **medido no 345M** (ckpt ligado) | 9,052e13 | 138,3 h | **141** |
| **medido no 345M** (ckpt DESLIGADO) | **1,113e14** | **112,5 h** | **115** |

Confirmado em **duas corridas independentes** (35 e 45 passos): 53,72k e **53,73k tok/s** —
concordância de **0,02%**. A regra das três leituras coincidentes está satisfeita com folga.

⭐ **A extrapolação do 151M subestimava em 60%.** Um modelo maior usa a GPU **melhor** —
matmuls maiores, menos overhead por token. Extrapolar throughput de um degrau para outro é tão
inválido quanto herdar LR: os dois dependem de N.

**Consequência direta:** o run principal custa **US$ 115**, não US$ 218. Com saldo de
US$ 260,70, a reserva sobe de US$ 36 para **US$ 146** — bem acima dos US$ 60–80 que o estudo
pediu, e o histórico de cinco falhas silenciosas deste projeto justifica cada dólar dela.

---

## A varredura de configuração

Todas com a geometria final (32×960, 15q/5kv, inter 2560, Qwen3 + QK-Norm), seq 2048, AdamW,
bf16 autocast, Liger com patch de `qwen3` **conferido no modelo instanciado**.

| micro-batch | grad-accum | ckpt | tok/s (mediana) | spread | 21,75B | US$ |
|---:|---:|:---:|---:|---:|---:|---:|
| 8 | 4 | ✅ | 43,69k | 5,2% | 138,3 h | 141 |
| **8** | **4** | **❌** | **53,72k** | **0,1%** | **112,5 h** | **115** |
| 16 | 2 | ❌ | 🔴 OOM (faltaram 20 MiB) | | | |
| 24 | 2 | ❌ | 🔴 OOM | | | |
| 12 | 3 | ❌ | 🔴 OOM (faltaram 46 MiB) | | | |
| 10 | 3 | ❌ | 🔴 OOM (faltaram 100 MiB) | | | |
| 16 | 2 | ✅ | 44,01k | 6,3% | 137,3 h | 140 |
| 8 (**sem Liger**) | 4 | ❌ | 🔴 OOM | | | |

⭐ **Desligar o gradient checkpointing rende +23%** e cabe: a 5090 tem 32 GiB e o passo usa
~8,1 GiB com checkpointing. Sem ele o consumo sobe muito (o OOM em MB=16 mostra ~31,3 GiB), mas
**MB=8 cabe com folga**. O checkpointing existia para caber na L4/5070 — nesta placa ele só
custa tempo.

⚠️ **A margem em MB=16 é de 20 MiB.** Isso é fragilidade, não folga: qualquer variação de
alocador derruba o run. **MB=8 é a escolha, não MB=16.**

⭐ **Spread de 0,1%** entre passos 20–34 (contra 5,2% com checkpointing) — é a leitura mais
estável já obtida neste projeto, e satisfaz com sobra a regra das três leituras coincidentes.

### 🔴 `torch.compile` é INCOMPATÍVEL com o Liger nesta combinação

```
torch._dynamo.exc.TorchRuntimeError: Dynamo failed to run FX node with fake tensors:
  call_function addmm ... got TypeError("unsupported operand type(s) for *:
  'torch.dtype' and 'FakeTensor'")
from user code:
  .../liger_kernel/ops/fused_linear_cross_entropy.py, line 229, in ... torch.addmm(
```

torch 2.8.0+cu128 · liger-kernel (última) · transformers 5.15.0. **É um ou outro, não os dois.**
O `compile` gastou minutos de CPU (medido: **65 W, 0% de GPU, 1.944 MiB**) antes de falhar — a
compilação de 32 camadas é cara, mas num run de 112 h seria irrelevante *se funcionasse*.

⚠️ **O que quase passou batido:** a primeira tentativa rodou com `grep -E "REGIME|21,75B|OOM"`
e **não imprimiu nada** — a falha não casava com nenhum padrão. Um filtro estreito demais faz
um erro parecer um resultado vazio. Refeito sem filtro, o erro apareceu inteiro. É o mesmo
defeito de aparato que aparece em `licoes-de-metodo.md` §6–8.

---

## Como foi medido (e por que assim)

- **Regime, não aquecimento.** Só os passos ≥20 entram na mediana. O passo 0 marcou 11,23k
  tok/s — 4× abaixo do real. É exatamente o erro de 5× que já custou uma decisão de
  infraestrutura a este projeto.
- **Tokens aleatórios.** Throughput não depende do valor dos tokens, só das formas. Isso evita
  subir 43,5 GB de corpus para medir velocidade. ⚠️ Em contrapartida, esta medição **não**
  valida nada sobre qualidade de dado nem sobre o carregador.
- **Guarda do Liger.** O script aborta se o patch de `qwen3` não aparecer no modelo
  instanciado. Sem ela, `apply_liger_kernel_to_llama` num modelo Qwen3 seria um no-op
  silencioso, e a única evidência seria a corrida ser mais lenta que o previsto.

### ⭐ É o Liger que permite desligar o checkpointing

Sem Liger, `MB=8 CKPT=0` **estoura**. O `fused_linear_cross_entropy` nunca materializa a matriz
de logits (8 × 2048 × 32.000), e é exatamente essa economia que abre espaço para dispensar o
gradient checkpointing. Os dois não são otimizações independentes: **um habilita o outro**.

Consequência: a guarda que aborta quando o patch do Liger não pega (implementada em
`pretrain.py` neste mesmo dia) não é zelo — sem ela, um Liger silenciosamente inativo faria o
run **estourar a VRAM ou rodar 23% mais devagar**, sem mensagem nenhuma.

---

## A GPU está saturada em computação, não presa num teto elétrico

Cinco leituras durante o regime da configuração vencedora:

```
553,41 W · 99% · 27.710 MiB · 57 °C · 2887 MHz
558,57 W · 97% · 27.710 MiB · 57 °C · 2887 MHz
555,28 W · 99% · 27.710 MiB · 58 °C · 2887 MHz
556,29 W · 99% · 27.710 MiB · 58 °C · 2887 MHz
556,16 W · 99% · 27.710 MiB · 57 °C · 2895 MHz
```

**553–559 W de um limite de 600 W (92%)**, clock **cravado** em 2887 MHz, 57 °C. Sem throttling
térmico nem de clock.

⭐ Compare com o diagnóstico que reprovou a RTX PRO 4500 no estudo de GPUs: *"utilização alta +
potência no limite = teto elétrico; nesse regime batch maior é pior"*. A PRO 4500 ficava cravada
em **200,0 W** (o limite exato) com throughput baixo. A 5090 está a 92% do envelope **com o
clock estável** — é o regime saudável, e a diferença aparece no `$/B tokens`.

**27.710 de 32.607 MiB (85%)** explica por que MB=10 já estoura: não há para onde crescer.

---

## ⚠️ O que esta medição NÃO diz

- **Não mediu o `pretrain.py` real** — mediu um benchmark com a mesma geometria, mesmo
  otimizador e mesmo laço. O script real ainda tem carregamento de dados, avaliação periódica e
  checkpointing em disco, que **reduzem** o throughput efetivo. Trate os US$ 115 como **piso**.
- **Não mediu com o corpus real** em disco de rede, cuja leitura pode limitar.
- **Uma placa, uma sessão.** Variação entre instâncias do mesmo modelo de GPU não foi medida.

## Números do ambiente

`RTX 5090 · 32.607 MiB · 600 W` · torch 2.8.0+cu128 · transformers 5.15.0 (local: 5.14.1)

⚠️ `nproc` respondeu **384** e `free` respondeu **755 GB** — são do **host**, não do container
(o pod recebeu **48 vCPU e 94 GB**, e a tela de deploy prometia 15 vCPU / 62 GB — os tres
numeros sao diferentes). É a armadilha que já custou 3 h a este projeto; nada foi dimensionado
por eles.

---

## A configuração escolhida

```bash
python bee/pretrain.py --tamanho 350m \
  --dados dados_pt_22b --tokenizer models/bee-150m-v3-base \
  --micro-batch 8 --grad-accum 4 --sem-checkpointing \
  --liger --sem-compilar --tokens-alvo 21.75e9
```

| item | valor | por quê |
|---|---|---|
| micro-batch | **8** | 10 e 12 estouram; 16 estoura sem checkpointing |
| gradient checkpointing | **desligado** | +23%, e cabe porque o Liger evita os logits |
| Liger | **ligado** | é o que permite desligar o checkpointing |
| `torch.compile` | **desligado** | incompatível com o Liger nesta versão |

**Custo do run principal: US$ 115** (112,5 h). Com saldo de US$ 260,70, a reserva fica em
**US$ 146** — muito acima dos US$ 60–80 que o estudo pediu.

## Ambiente exato do pod

`bee-350m-throughput` (`d0jq0zih4mqdv0`) · EUR-IS-1 Secure Cloud · RTX 5090 1× ·
48 vCPU (AMD EPYC 9J14) · 94 GB RAM · container 150 GB · **network volume 50 GB em
`/workspace`** (`bee-350m-throughput_volume`).

⚠️ **O volume de 50 GB não cabe o corpus** (`train.bin` = 43,5 GB) **mais** checkpoints. Para o
run real: corpus no disco do container (recuperável) e **checkpoints no volume de rede** — que é
a lição de disco persistente que o projeto já pagou.

⚠️ **Pod parado custa US$ 0,000/h** (confirmado no diálogo de Stop). Os pods antigos parados na
conta não drenam saldo.
