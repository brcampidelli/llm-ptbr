# GATE 1 v2 — tokenizador retreinado no corpus COM código (2026-07-27)

> Substitui o [gate v1](gate-1-fertilidade-2026-07-27.md). O v1 continua válido como registro do que
> foi medido na época, mas **dois dos seus números mudam de leitura** — ver §"O que o v1 dizia".

## Decisão: **vocab 32.000, normalizer NFC**

`MyDrive/BEE/tokenizer-v2/` · md5 `bf6887ead6ec93c55645a52181ce0d84` (conferido contra o original).

## Fertilidade (tokens/palavra · menor é melhor)

Holdout de 400 docs PT + 400 EN + **400 código**, buckets `sha1 % 100 < 2`, disjuntos do treino.

| tokenizador | vocab | **PT** | EN | **CODE** |
|---|---:|---:|---:|---:|
| **Bee v2 (nosso)** | 32.000 | **1,370** | 1,880 | 4,570 |
| Qwen3.5-4B | 248.044 | 1,496 | 1,334 | 2,536 |
| SmolLM2-135M | 49.152 | 2,241 | 1,344 | 2,879 |
| **tiktoken o200k** (GPT-4o) | 200.019 | **1,426** | **1,281** | **2,341** |

**Em português: −3,9% vs. o melhor rival** (tiktoken). Em inglês somos +47% piores; em código, +95%.

## ⭐ A varredura de vocab, e por que o "GATE APROVADO" enganava

Rodamos 4 tamanhos. O gate — que compara **só fertilidade PT contra o rival** — aprovou 48k, 64k e
96k. **Os três são escolhas piores**, e o pior deles é o que o gate mais elogiou.

| vocab | params | emb% | fert. PT | **custo = N × f** | vs 32k | veredito do gate |
|---:|---:|---:|---:|---:|---:|---|
| **32k** | 151,1M | 12,2% | 1,370 | **207,1** | — | ⚠️ marginal (+3,9%) |
| 48k | 160,3M | 17,2% | 1,322 | 212,0 | +2,4% | ✅ aprovado (+7,2%) |
| 64k | 169,6M | 21,7% | 1,295 | 219,6 | +6,1% | ✅ aprovado (+9,2%) |
| 96k | 188,0M | 29,4% | 1,266 | 238,0 | **+14,9%** | ✅ aprovado (+11,2%) |

**A conta:** FLOPs de treino ≈ 6·N·tokens, e tokens = palavras × fertilidade. Para o mesmo texto, o
custo é proporcional a **N × f**. Vocab maior corta `f` mas aumenta `N` — só vale se a queda compensar.

**Não compensa, e a razão é estrutural:** o ganho de fertilidade **decai** (−3,5% → −2,0% → −2,2%)
enquanto o embedding **cresce linearmente** (+9,2M, +9,2M, +18,4M params). Com 96k, a tabela de
embedding seria **29,4% do modelo inteiro** — quase um terço dos parâmetros sem fazer raciocínio.

⭐ **A régua foi fixada ANTES de medir** (`48k precisa < 1,291; 64k < 1,221; 96k < 1,101`). Isso não é
formalidade: sem ela, o `✅ GATE APROVADO` teria levado à escolha do 96k, o mais caro de todos. **Um
gate mede o que foi programado para medir, não o que decide.**

## ⭐ Código: vocab não é o gargalo — e isso é um achado negativo útil

| vocab | fert. código |
|---:|---:|
| 32k | 4,570 |
| 96k | 4,067 |

**Quadruplicar o vocab melhora só −11%**, e nem 96k chega perto dos 2,341 do tiktoken. A hipótese
"nosso vocab é pequeno demais para código" está **testada e rejeitada**. O gargalo é *quanto código o
tokenizador viu*: 10% do nosso corpus contra o treino do GPT-4o. Aumentar essa fatia resolveria — ao
custo de português, que é a aposta inteira do projeto. **Fica como trade-off consciente, não como
descuido.**

## O que o v1 dizia, e o que muda

O v1 reportou **"−5,4% em PT contra o melhor rival"**. Aquele número não estava errado, mas era
**contra um rival mais fraco**: o v1 só tinha Qwen e SmolLM2 no páreo. Com o **tiktoken o200k**
incluído (a mesma família de algoritmo que a nossa, ByteLevel BPE), a margem real é **−3,9%**.

**A vantagem em português é menor do que celebramos.** Ela existe e é real, mas o rival certo a
encolheu em 1,5 ponto. Foi exatamente para isso que o tiktoken entrou depois do estudo das 7 fontes —
bater tokenizador de outra família seria fácil e diria pouco.

O v1 também **não media código** (o corpus dele tinha 0%), então nada do que ele disse sobre isso
existia. A coluna CODE é nova.

## O que mudou no tokenizador, e por quê

1. **Normalizer NFC** (o v1 não tinha nenhum). Em PT isso não é detalhe: `"ação"` tem **6 bytes**
   precomposto e **8** decomposto, e `prec == deco` é `False` — viram tokens diferentes num BPE
   ByteLevel. Nosso corpus mistura web, Wikipédia e livros digitalizados, que chegam nas duas formas.
   ⚠️ **NFC e não NFKC**: NFKC converte `①`→`1`, `ﬁ`→`fi`, `Ⅻ`→`XII` — não é reversível, e
   reversibilidade é a propriedade que o paper do SentencePiece defende.
2. **Corpus com 10% de código** (o v1 tinha 0%).
3. **Terceira coluna no gate** (CODE) + alerta próprio por domínio.
4. **tiktoken como rival.**

Fundamentação: [estudo de 7 fontes sobre tokenização](estudo-tokenizacao-2026-07-27.md).

## Reprodução

```
python bee/train_tokenizer.py --corpus <corpus> --vocab 32000 --normalizar nfc
```
~8 min de CPU. A varredura está em `gate_vocab{48000,64000,96000}.json` na Drive.
