# Estágio 6 — o gate de preferência não pode ser decidido: o ruído de treino é maior que o limiar

> **2026-08-23.** US$ 0 de GPU paga — rodou inteiro na RTX 5070 de 8 GB. O E6 é um **gate**:
> quatro braços de preferência contra um controle SFT+RS, com critério de adoção declarado
> antes (≥5 pp de folga absoluta). Os braços rodaram. O gate **não decide** — e o motivo é o
> resultado.

---

## 1. 🔴 A medição que anula as outras

Três rodadas de SFT sobre **o mesmo dado, com a mesma receita**:

| rodada | acerto |
|---|---:|
| E2 (micro-batch 4×4, numa 5090) | 55/85 = **64,7%** |
| semente 42 (1×16) | 49/85 = 57,6% |
| semente 43 (1×16) | 45/85 = **52,9%** |
| **amplitude** | **10 casos = 11,8 pp** |

**Só a semente**, com tudo o mais idêntico, move **4,7 pp** e troca **14 casos** (+5/−9).

O limiar de adoção do gate é **5 pp**. O ruído de treino é **4,7 pp**. Qualquer folga da ordem
do critério cabe inteira dentro de "retreinar com outra semente".

⚠️ E isso não é um defeito do E6 — é uma propriedade do aparato que só apareceu agora, porque
**nunca se tinha treinado a mesma receita duas vezes**. O `sft_qlora.py` tinha `seed=42`
cravado; um treinador sem controle de semente não permite medir a própria variância.

---

## 2. Os braços, e por que o quadro não sustenta veredito

| braço | estrito | harness | over-call | folga vs controle | McNemar |
|---|---:|---:|---:|---:|---:|
| adapter E2 (ponto de partida) | 55/85 · 64,7% | 55 | 12/65 | — | — |
| SFT sem RS, semente 42 | 49/85 · 57,6% | 49 | 12/65 | — | — |
| SFT sem RS, semente 43 | 45/85 · 52,9% | 48 | 15/65 | — | — |
| **controle SFT+RS** | 50/85 · 58,8% | 52 | 11/65 | — | — |
| + DPO | 55/85 · 64,7% | 56 | 12/65 | **+5,9 pp** | p=0,125 |
| + IPO | 55/85 · 64,7% | 56 | 12/65 | **+5,9 pp** | p=0,125 |
| + KTO restrito (324 prompts) | 51/85 · 60,0% | 53 | **9/65** | +1,2 pp | p=1,000 |
| + KTO completo (657 prompts) | 53/85 · 62,4% | 54 | 13/65 | +3,5 pp | p=0,250 |

Pela regra declarada antes, DPO e IPO passariam (+5,9 pp ≥ 5 pp). **Não passam**, porque
+5,9 pp é da ordem do ruído de semente medido na §1.

### O que ainda se pode afirmar

⭐ **Volume ajuda o KTO, e a diferença é volume mesmo.** Os mesmos 324 prompts dão +1,2 pp;
acrescentar os 333 `all_right` — que não formam par e por isso são inacessíveis a DPO/IPO —
leva a +3,5 pp. Os dois modos existiam exatamente para separar isso: um KTO que só ganhasse no
modo completo teria medido volume e não função de perda (§2g). Mediu volume, e está dito.

⭐ **KTO restrito é o único braço que reduz over-calling** (11 → 9). DPO e IPO sobem para 12, o
KTO completo para 13. Subir execução chamando mais não é ganho líquido.

⚠️ **DPO e IPO empatam em 55/85, mas não são o mesmo modelo:** os pesos diferem e eles
discordam em **8 dos 85 casos** — as diferenças se cancelam no agregado. Um holdout de 85 itens
não resolve a diferença entre duas funções de perda de preferência.

---

## 3. O erro que eu cometi no meio do caminho

Reportei que **"o rejection sampling custou 5 casos"**, comparando minha rodada nova (50/85)
contra o adapter do E2 (55/85). Está errado por duas razões:

1. o controle certo é **minha própria rodada sem RS** (49/85) — contra ela o RS deu **+1 caso**;
2. eu afirmei "mesma receita" tendo lido os *defaults* do `grid_e2.py` em vez do
   `training_args.json` salvo dentro da pasta do próprio adapter, que registrava
   `batch_size 4 / grad_accum 4` contra os meus `1 / 16`.

É a §2g — comparar duas coisas medidas de jeitos diferentes — cometida por quem estava
invocando a §2g nas mensagens anteriores. O arquivo que desmentia a afirmação estava a um `cat`
de distância.

---

## 4. Guardas que dispararam, uma delas errado

### 🔴 A guarda de likelihood displacement deu falso positivo

Ela abortou DPO e IPO no passo 3. O log:

```
passo   logps/chosen   logps/rejected   margins
  1        -8,364         -30,16          0
  3       -14,95         -69,97          0,0016   <- abortou
```

**As duas log-probs caíram juntas, ~2×.** Deslocamento é o `chosen` afundando *enquanto a
margem sobe*; aqui a margem é 0,0016 (e **negativa** no IPO). `logps` é **soma** por sequência,
então um lote com completions mais longas derruba o número sem nada ter acontecido — e o LR
ainda estava em warmup.

A v1 comparava um valor bruto contra outro lote. A v2 exige as **três** condições do fenômeno:
queda abaixo da **mediana** das primeiras leituras, **sustentada** por 3 leituras, **e com a
margem subindo**, só depois do warmup. Escrever guarda que dispara é fácil; escrever guarda que
dispara **pelo motivo certo** exige a assinatura completa.

⚠️ Consequência: os primeiros DPO/IPO eram runs de **3 passos** e o "+2,4 pp" que reportei era
o controle com ruído.

### As outras

- **`logging_steps=10` cegava a guarda**: ela ancora no primeiro valor logado, que seria o
  passo 10 — dez passos depois do marco. Agora é 1.
- **A guarda de delta de pesos passou**: 14.336/28.672 = exatamente 50%, o esperado do LoRA com
  B em zero (no passo 1 só B se move, porque `dL/dA ∝ B = 0`).

---

## 5. O que estava quebrado no ferramental

| defeito | efeito |
|---|---|
| `15_rejection_sampling.py` sem `--peft`, sem parada, parser estrito | amostraria o **base**, sem parar, com o parser que dá 0,6% sob amostragem (E5) |
| `DPOConfig` da TRL 1.9 não aceita `max_prompt_length` | os 4 braços morriam no construtor; o arquivo nunca tinha rodado nesta versão |
| `prompt` conversacional × `chosen` string | TRL exige o mesmo formato nos dois |
| `check_data` só conhecia pares | dizia "0 pares válidos" sobre um arquivo KTO perfeito |
| KTO com batch real 1 | a TRL recusa, com razão: o KL dele compara **dentro** do lote |
| micro-batch 4 na 5070 | **237 s/passo** (25× mais lento) por paginação — o sintoma documentado é lentidão, não OOM |

⭐ E o rejection sampling corrigido entregou o 5a sobre 866 prompts verificáveis:
`all_right` 335 (38,7%) · `all_wrong` 248 (28,6%) · **`misto` 283 (32,7%)** → **930 pares**
(`quase` 723, `lixo` 207), bem acima do piso de fracasso de 97–325.

Recuperar os negativos crus triplicou o insumo (311 → 930). E o viés de comprimento que temi
não existe: nos pares `quase` (78% do total) o comprimento mediano de `chosen` e `rejected` é
**idêntico**.

---

## 6. O que fica

1. 🔴 **Nenhuma comparação entre adapters é interpretável sem o ruído de semente ao lado.**
   Toda folga abaixo de ~5 pp neste holdout é indistinguível de retreinar. Isso vale
   retroativamente para as comparações finas do E2 (as grandes — 0% → 64,7% — seguem de pé).
2. **O gate do E6 fica sem veredito.** Não é "não adotar" nem "adotar": é *não decidível com
   este aparato*. Decidir exigiria ou ~3 sementes por braço (4× o custo), ou um holdout bem
   maior — e o E5 já mostrou que ampliá-lo esbarra em quantas ferramentas dá para simular.
3. **O `--seed` agora existe** no `sft_qlora.py`, e nenhum braço futuro deve ser reportado sem
   pelo menos duas sementes.
4. **Sobrevive um sinal barato:** o KTO restrito é o único braço que baixou over-calling
   (11 → 9) — pequeno, mas na direção certa e no eixo que o projeto já mediu que se desloca.
