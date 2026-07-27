# GATE 1 v1 — fertilidade do tokenizador Bee (2026-07-27) · ⚠️ SUPERADO

> ⚠️ **ESTE DOCUMENTO FOI SUPERADO** por [gate-1-v2-tokenizador-2026-07-27.md](gate-1-v2-tokenizador-2026-07-27.md).
> Os números aqui foram medidos de verdade, mas **dois deles mudam de leitura**:
> 1. O **"−5,4% vs. o melhor rival"** era contra um páreo mais fraco (só Qwen e SmolLM2). Com o
>    **tiktoken o200k** incluído — a mesma família de algoritmo que a nossa — a margem real é
>    **−3,9%**. A vantagem existe, mas é menor do que celebramos aqui.
> 2. Este tokenizador foi treinado num corpus com **0% de código** e **sem normalizer**. O v2 tem
>    10% de código e NFC.
>
> Mantido como registro do que foi medido na época.

> O primeiro gate do Bee, e o mais barato do projeto: ~4 min de CPU. A aposta inteira do Bee é o
> nicho português. Se o nosso tokenizador não fosse mais eficiente em PT que os rivais, a aposta
> teria falhado aqui — em vez de depois de 22 h de GPU.

## Resultado

**Fertilidade** = tokens por palavra. **Menor é melhor.** Holdout de 400 docs PT + 400 EN, buckets
`sha1(doc) % 100 < 2`, **disjuntos do treino do tokenizador**.

| tokenizador | vocab | **PT** | EN |
|---|---:|---:|---:|
| **Bee (nosso)** | 32.000 | **1,416** | 1,450 |
| Qwen3.5-4B | 248.044 | 1,496 | 1,334 |
| SmolLM2-135M | 49.152 | 2,241 | 1,344 |

- **PT: −5,4% vs. Qwen** (melhor rival) e **−36,8% vs. SmolLM2**.
- Com vocab **7,8× menor** que o do Qwen: 32k × 576 = **18,4M** de embedding, contra 143M — que num
  modelo de 150M seria inviável (95% do orçamento de parâmetros só na tabela de embedding).

**O que isso compra:** no mesmo orçamento de FLOPs, o Bee vê ~5% mais texto PT por passo que o Qwen
e ~58% mais que o SmolLM2. Vale para treino e para inferência.

## ⚠️ Ressalvas (o que o gate NÃO diz)

1. **Em inglês somos piores:** 1,450 contra 1,334 do Qwen, **+8,7%**. Dentro do limite que o script
   vigia (alerta só acima de +25%), mas é o preço explícito da aposta — 32k concentrados em PT não
   cobrem EN como 248k. Com ~20% do corpus em inglês, encarece essa fatia em ~9%.
2. **O SmolLM2 perder em PT não é mérito nosso, é a tese:** ele foi treinado só em inglês. É
   exatamente o buraco que o Bee ocupa.
3. **O corpus deste tokenizador tem 0% de código** (ver falha do `python-edu` abaixo). Um tokenizador
   sem código gasta mais tokens em código. **Não medimos isso** e não vamos fingir que medimos.
4. Fertilidade mede **eficiência de representação**, não qualidade do modelo. É condição necessária
   para a aposta, não suficiente.

## ⭐ Defeito encontrado ANTES de rodar o gate

A primeira versão do script montava `hold_pt`/`hold_en` a partir dos primeiros 8 MB dos shards — e o
treino lia **os mesmos shards, do início**. O holdout estava **dentro** do treino: o Bee teria visto o
texto de teste e os rivais (Qwen, SmolLM2) não. O gate mediria a nosso favor.

Corrigido com a mesma técnica de `comeia/data/13_build_extraction_splits.py`: balde estável por
`sha1(documento) % 100`, 2% no holdout, disjunto por construção. Testado: **interseção 0** em 5.000
documentos, 1,9% real, estável entre chamadas. (commit `c756b18`)

## Corpus usado

1,84 GB em 10 shards. Auditoria de mistura (medida, não assumida):

| fonte | pedido | obtido | aproveitamento |
|---|---:|---:|---:|
| fineweb2-por | 35% | 38% | 98% |
| portuguese-pd | 15% | 16% | 64% |
| wikipedia-pt | 10% | 11% | 90% |
| legal-pt | 5% | 5% | 39% |
| fineweb-edu-en | 15% | 16% | 99% |
| cosmopedia-en | 10% | 11% | 91% |
| **python-edu** | 10% | **0%** | **0%** |

Idioma detectado: **PT 79% · EN 20% · código 0%**. Alvo era 65% ±10 pp → **fora**.

**Causa raiz do `python-edu` = 0%:** o subset `python-edu` do `HuggingFaceTB/smollm-corpus` **não traz
o texto** — só `blob_id`/`repo_name`/`path`; o conteúdo vem do S3 do Software Heritage. O coletor
pediu o campo `text`, achou vazio em 100% dos registros e descartou tudo. A fatia de 10% foi
redistribuída, empurrando PT para 79%. **O mesmo problema vale para `bigcode/the-stack-v2`**, que
também é só ponteiro — o substituto precisa ter conteúdo inline e licença já filtrada.

Foi a auditoria de mistura (`detect_lang` sobre a amostra, §1.5 do plano) que pegou isso. Sem ela, a
falha só apareceria como "o modelo não sabe código" depois do treino.

## Consequência

- ✅ **A aposta do nicho tem base empírica.** Seguir para a arquitetura (`bee/config.py`).
- 🔴 **Bloqueante para o treino, não para o gate:** consertar a fonte de código e recoletar. Os
  1,84 GB servem ao tokenizador; 3B tokens a ~1,42 tokens/palavra pedem **~12 GB** de texto.
- O tokenizador ficará **estável** a partir daqui: trocá-lo depois invalida qualquer checkpoint.
  Se a fonte de código mudar a mistura de forma relevante, é melhor retreinar o tokenizador **antes**
  do pré-treino do que conviver com ele.

## Artefatos

✅ **Persistidos na Drive** (2026-07-27, md5 conferido contra o original): o tokenizador em
`MyDrive/BEE/tokenizer-v1/` (`tokenizer.json` md5 `64a3559a6bb57e7010330b4622cf8bb2`), junto do
`MANIFEST.json` (procedência e licença por shard), do `gate_fertilidade.json` e do `gate1.log`.
Reproduzir custa ~4 min de CPU **dado o corpus**; o corpus custa ~1 h de coleta.

Reprodução:

```
python bee/train_tokenizer.py --corpus <corpus> --vocab 32000
```
