# 🐝 BEE — uma LLM em português, treinada do zero

**O que é:** um modelo de linguagem construído **do zero** — tokenizador nosso, arquitetura nossa,
corpus montado por nós, pesos inicializados aleatoriamente e treinados por nós. A aposta é o
**português**: é o único lugar onde um modelo pequeno nosso pode ganhar de alguém.

**Onde estamos:** o Bee **existe e roda**. Três pré-treinos completos (v1, v2, v3), Gate 2 medido,
SFT feito. E o resultado central é honesto e desconfortável: **o Gate 2 não passou** — o Bee-150M
perde do SmolLM2-135M em português por larga margem. O que aprendemos investigando esse fracasso
vale mais que o modelo, e está tudo abaixo.

> **Por que o projeto mudou.** Ele nasceu como "construir uma LLM do zero". Em 2026-07-26 a pergunta
> foi feita direto — *estamos fazendo isso?* — e a resposta honesta era **não**: o que existia era o
> Qwen4B + ~130 MB de adapters nossos. Método real e validado, mas o modelo era de outra pessoa.
> A decisão foi pré-treinar de verdade, e reaplicar sobre o Bee o método que já funcionou 4×.

---

## Estado atual — o que está medido

### ⭐ GATE 1 — fertilidade do tokenizador: **APROVADO** (2026-07-27)

Fertilidade = tokens por palavra. **Menor é melhor.** Holdout de 400 docs PT + 400 EN, buckets
`sha1(doc) % 100 < 2`, **disjuntos do treino do tokenizador**.

| tokenizador | vocab | **PT** | EN |
|---|---:|---:|---:|
| **Bee (nosso)** | 32.000 | **1,416** | 1,450 |
| Qwen3.5-4B | 248.044 | 1,496 | 1,334 |
| SmolLM2-135M | 49.152 | 2,241 | 1,344 |

**−5,4% de tokens/palavra em PT contra o Qwen; −36,8% contra o SmolLM2** — com um vocab **7,8×
menor**. Custo do gate: **4 minutos de CPU**. Confirmado depois no Gate 2 sobre texto real:
0,3114 tokens/byte contra 0,3938 do SmolLM2. **O tokenizador é a parte que funcionou.**

### 🔴 GATE 2 — o Bee bate o SmolLM2 em português? **NÃO** (2026-08-03)

bits-por-byte em holdout PT nunca visto (shards 7/23, mantidos fora do treino por
`prepare_data.py`). **Menor é melhor.** bpb é comparável entre tokenizadores diferentes —
perplexidade não seria.

| | tokens únicos | épocas | **bpb PT** | vs SmolLM2 |
|---|---:|---:|---:|---:|
| Bee v1 | 3,74B | 1 | 3,460 | −72,2% |
| Bee v2 | 3,74B | 3 | 3,530 | −75,7% |
| **Bee v3** | **9,87B** | 1 | **3,457** | **−72,0%** |
| SmolLM2-135M | ~2T | — | **2,010** | — |

**Triplicar o corpus moveu o bpb em 0,1%.** O v3 bate o v2 (mais tokens únicos > mais épocas), mas
o ganho absoluto contra o v1 é nulo. Custo do v3: 18.816 passos, **21,76 h de A100-80GB (~US$ 34)**,
perplexidade de validação 77,4 → 63,0.

### ⭐ O que a investigação do fracasso descobriu (2026-08-04)

Esta é a parte que importa. Três hipóteses foram testadas contra fonte primária; **duas caíram.**

**A leitura correta do Gate 2.** Sob `L(D)=E+A·D^-0,28`, ir de 3,74B → 9,87B deveria cortar **23,8%**
da loss redutível. Observamos 0,1% — **200× abaixo**. Não é "mais token não resolve": é que **o Bee
não está na curva de scaling**. Algo o satura antes de o dado virar gargalo.

**Geometria — REFUTADA.** Os `config.json` do `SmolLM2-135M` e do `MobileLLM-125M` são **idênticos**
ao do Bee: 30 camadas · d_model 576 · 9q/3kv · vocab 32k · seq 2048. O modelo que faz bpb 2,010 tem
exatamente a nossa geometria. A suspeita de que a razão d_model/camadas estava errada veio de
modelos 10–100× maiores e não vale nesta escala.

**LR de pré-treino — REFUTADO.** Step Law (~3.700 modelos ajustados):
`η* = 1,79·N^-0,713·D^0,307` → para N=151M, D=9,87B dá **3,09e-3**. Usamos 3e-3. Erro de 3%.

**O par honesto: [Tucano-160m](https://huggingface.co/TucanoBR)** — 162M params, PT nativo,
Apache-2.0, treinado em **200B tokens**. Mesma escala, mesma língua. A distância para o Bee é
**20× em token, não em arquitetura.**

**O medidor foi auditado e está sadio.** `carregar_holdout` trunca em 4.000 chars de propósito, para
caber em 2048 tokens nos dois tokenizadores, então o corte por `seq_len` não dispara nem enviesa a
comparação. Os shards de validação ficam inteiros fora do treino. **O gap é real.**

**Duplicata — ELIMINADA como explicação** (medido em 2026-08-04, `bee/medir_dedup.py`).
O `expand_corpus.py` tem um buraco real: o `vistos_sha` persiste em disco e pega duplicata **exata**
entre o corpus v1 e a expansão, mas o `Dedup` (MinHash LSH) **nasce vazio a cada execução** — então
quase-duplicata *cruzando* essa fronteira nunca foi verificada. Medimos a taxa na fonte
(`fineweb-2 por_Latn`, dois parquets distintos, mesmos filtros e mesmo MinHash do coletor):

| | taxa |
|---|---:|
| duplicata exata (dentro e entre lados) | **0,00%** |
| quase-duplicata dentro de um lote (o MinHash pega) | 0,53–0,73% |
| quase-duplicata cruzando a fronteira (**não** pega) | **0,90%** |

Dos 9,87B tokens nominais restam **~9,78B efetivos** — perda de 0,09B. O buraco existe e vale
fechar, mas **não explica um déficit de 200×**. ⚠️ Estimativa por amostra (4.000+4.000 docs), não
censo do corpus.

→ A hipótese viva, agora sozinha, é **qualidade/composição do corpus**. Magnitude compatível: o
FineWeb-Edu descartou **91%** do corpus e subiu MMLU 33→37% e ARC 46→57%, igualando um baseline com
10× menos tokens. **Corpus menor e melhor, não maior.**

### SFT — o gate de FORMA passou, o de CONTEÚDO não

| | dados | LR | nll (holdout antigo) | nll (holdout BNCC) | acurácia | sondas vazias |
|---|---:|---:|---:|---:|---:|---:|
| base (sem SFT) | — | — | — | — | 6,4% | — |
| v3-sft | 5.657 | 2e-5 | 3,567 | 3,828 | 31,6% | 2 |
| A | 7.333 | 2e-5 | 3,780 | 3,900 | 28,6% | 2 |
| B | 7.333 | 1e-4 | 2,464 | 3,002 | 49,6% | 0 |
| **C** | 7.333 | **1e-3** | **2,006** | **2,715** | **57,4%** | **0** |

**O dado sozinho não ajudou; o LR mudou tudo.** O A, com 30% mais exemplos e o mesmo LR, ficou igual
ou pior. O C melhora **44%** sobre o de manhã, e o ganho aparece nos dois holdouts — inclusive no da
BNCC, feito de habilidades que nenhum treino viu. E treinou em **19 min** contra 47 do A: LR alto
converge mais rápido.

**A varredura de LR (1 época por ponto, 6 pontos):**

| LR | 5e-5 | 1e-4 | 3e-4 | 6e-4 | **1e-3** | 2e-3 |
|---|---:|---:|---:|---:|---:|---:|
| eval_loss | 3,011 | 2,590 | 2,220 | 2,079 | **2,047** | 2,110 |
| acurácia | 41,5% | 47,7% | 53,4% | 55,6% | **56,1%** | 55,5% |

⭐ **O ótimo é 1e-3 — 50× o LR inicial.** Não foi erro de calibração fina, foi conceitual: a receita
veio do QLoRA sobre Qwen-4B, onde 2e-5 é razoável, e a intuição "modelo pequeno, passo pequeno" é
exatamente invertida. O pré-treino do próprio Bee já rodava a 3e-3.

⚠️ **A primeira varredura (4 pontos até 6e-4) descia até o limite** — não tinha achado o joelho, só
provado que a faixa estava mal escolhida. Foi a extensão até 2e-3, que **piorou**, que fechou a curva.
Parar nos 4 pontos teria promovido 6e-4 como "vencedor" sem saber onde ficava o teto.

⚠️ **E a fluência subiu sem levar o fato junto.** O modelo de manhã respondia *"foi seu mestre o
mestre de seus mestres"*. O B acertava "a capital de Minas é Belo Horizonte" — e afirmava que Machado
de Assis nasceu em São Paulo em 1712. O C, o melhor de todos em métrica, **deixa de responder a
pergunta**:

> *"A capital de Minas Gerais é a capital do estado de Minas Gerais, localizada no estado de Minas
> Gerais. Ela é a maior em extensão territorial do país e possui aproximadamente 560.662 km²…"*

Tautologia gramaticalmente perfeita seguida de geografia inventada com número de quatro casas. Forma
autoritativa sobre conteúdo aleatório é o modo de falha esperado quando o base tem bpb 3,457.

⭐ **Isto é o resultado mais importante do dia, e é negativo:** extraímos quase tudo que havia no
pós-treino — 50× no LR, 30% mais dado, 6 pontos de varredura, dois holdouts — o eval_loss caiu 44%,
e o Machado de Assis continua sem ter nascido no Rio em 1839. **O pós-treino chegou ao teto, e o teto
é o pré-treino.** É a conclusão do Gate 2 demonstrada pelo outro lado.

---

## Fonte de currículo: a BNCC (e por que não os livros)

Um estudo multiagente de 2026-08-04 avaliou 91 PDFs de livros didáticos (2,9 GB) como fonte de
ensino. **Veredito: os livros não; o currículo sim — e ele é público.**
Ver [docs/estudo-curriculo/00-CONSOLIDADO.md](docs/estudo-curriculo/00-CONSOLIDADO.md).

**A base legal, com artigo:**
- **Lei 9.610/98, art. 8º, IV** — não são protegidos *"leis, decretos, regulamentos… e demais atos
  oficiais"*. A **BNCC é o Anexo da Resolução CNE/CP nº 2/2017**, cujo art. 1º declara o Anexo parte
  do ato normativo. Logo: **fora do regime autoral**, não é questão de licença permissiva.
- **art. 8º, I** — *"conceitos matemáticos como tais"* não são protegidos.
- **art. 7º, §3º** — *"no domínio das ciências, a proteção recairá sobre a forma literária, não
  abrangendo o conteúdo científico"*. É a base legal de **reescrever é legal, copiar não**.

⚠️ **Armadilhas verificadas:** o rodapé de todo site gov.br declara **CC BY-ND** — não afeta a BNCC
(rodapé não recria proteção que a lei exclui), mas **afeta os itens de prova do ENEM**. E os
**microdados do ENEM não são CC-BY**: a Política de Dados Abertos do INEP lista isso como ação
pendente. Status: não confirmado.

**O que foi construído:** 1.484 habilidades extraídas dos PDFs oficiais (o `pdftotext` devolve zero;
só o PyMuPDF lê), 1.202 elegíveis após cortar Educação Física, Arte e Ensino Religioso.
`bee/gerar_bncc.py` usa a habilidade como **semente** — a BNCC vale 100% como índice e 0% como prosa
(não há nela um parágrafo que explique o que é mitose). Gerados **1.676 exemplos**, 93,6% de
aproveitamento, zero vazamento residual.

---

## Regras duras do projeto

- ⛔ **Procedência dos dados é requisito de negócio, não escrúpulo.** Cada shard carrega fonte e
  licença no `MANIFEST.json`.
  - **Scribd está fora** — estar logado dá acesso para *ler*, não licença para *treinar e publicar*.
  - **GitHub raspado direto está fora** — só datasets já filtrados por licença.
  - ⚠️ **Rótulo de licença não é prova.** Achamos uma cadeia quebrada: brWaC declara *"solely for
    academic research"* → CrawlPT não declara nada → GigaVerbo aparece como CC BY 4.0. Usar só o
    subconjunto `monoHPLT-PT` (CC0). **Ler a licença na origem, sempre.**
- ⛔ **Nunca** treinar com saídas de GPT/Claude/Gemini. Destilação só de professores abertos —
  `assert_teacher_allowed()` falha alto e cedo. (Ele já nos barrou uma vez, e estava certo.)
- **Holdout por hash, nunca por posição.** `sha1(doc) % N`.
- **Auditar a mistura, não assumir.** Foi assim que o `python-edu` = 0% apareceu.
- **Medir antes de acreditar — inclusive em si mesmo.** Duas hipóteses nossas sobre o Gate 2 caíram
  ao ler `config.json` de verdade em vez de teorizar.
- **Dificuldade se mede, não se presume.**

---

## Arquitetura do Bee-150M

Llama-style via `LlamaConfig`, **sem código de modelagem custom** — tudo que já construímos (PEFT,
TRL, vLLM, nossos evals) funciona sem uma linha de adaptação.

```
vocab 32.000 · tied embeddings
30 camadas · d_model 576 · intermediate 2048 (SwiGLU)
9 cabeças (head_dim 64) · 3 KV heads (GQA)
RoPE (theta 10000) · RMSNorm · seq_len 2048
≈ 151M params  (132M nas camadas + 18,4M no embedding)
```

✅ **Esta geometria está validada por comparação:** é byte a byte a mesma do SmolLM2-135M e do
MobileLLM-125M. Não é onde está o problema.

---

## Notas de hardware que custaram tempo

**Pré-treino: RunPod A100-80GB** ($1,50/h) — 21,76 h sem uma única interrupção. O Colab reciclou 2×
no mesmo treino e depois esgotou a cota de A100. Três pegadinhas: `transformers` **não** vem na
imagem "RunPod PyTorch 2.8.0"; `/workspace` é network-fs (~70k tok/s contra 85k do Colab);
`gdown --folder` em pasta grande bate rate-limit do Drive.

**SFT local: RTX 5070 Laptop 8 GB.** O micro-batch tem teto **rígido em 2**, e o vilão não são os
pesos (151M em bf16 + AdamW ≈ 2,5 GB, folgado) — é o **tensor de logits** `batch × 1024 × 32000`
mais o upcast fp32 da cross-entropy:

| micro-batch | tempo/passo | VRAM |
|---:|---:|---:|
| **2** | **0,31 s** | 5,78 GB ✅ |
| 4 | 4,02 s | 10,67 GB — vaza pra RAM do host |
| 8 | **510 s** | estouro total |

⚠️ **O sintoma de estouro não é OOM, é lentidão silenciosa.** O Liger (fused linear+CE, usado no
pré-treino) resolveria, mas não instala com transformers 5.x.

---

## Estrutura

```
├── bee/                    ⭐ O MODELO NOSSO, do zero
│   ├── build_corpus.py     #  coleta com manifesto de procedência + auditoria de mistura
│   ├── expand_corpus.py    #  expansão para 9,87B tokens (v3)
│   ├── train_tokenizer.py  #  BPE ByteLevel 32k + ⭐ GATE 1 (fertilidade vs. rivais)
│   ├── prepare_data.py     #  tokenização → train.bin/val.bin (shards 7/23/41 fora do treino)
│   ├── config.py           #  arquitetura — o mesmo arquivo em toda a escada
│   ├── pretrain.py         #  pesos aleatórios → modelo (retoma de checkpoint sozinho)
│   ├── eval_gate2.py       #  ⭐ GATE 2 — bits-por-byte vs. SmolLM2
│   ├── sft.py              #  full fine-tune (sem LoRA — em 151M o full cabe e é melhor)
│   ├── gerar_bncc.py       #  BNCC → material didático PT-BR via professor aberto
│   ├── comparar_sft.py     #  A/B de modelos pós-SFT: 2 holdouts + sondas
│   └── chat.py             #  conversa e sondagem (`--sonda`)
│
├── comeia/                 O MÉTODO de especialização (hoje sobre Qwen, amanhã sobre o Bee)
│   ├── orchestrator/       #  registry, hot-swap de LoRA, router, verificador
│   ├── data/               #  destilação, filtro "o base erra", schema_check, teacher_api
│   ├── train/  eval/       #  SFT/DPO via QLoRA · harness com holdout duplo
│
└── docs/                   estudos, avaliações e o histórico
    ├── gate-2-resultado.md
    ├── sft-resultado.md
    └── estudo-curriculo/   ⭐ 12 documentos: 91 PDFs + papers + web 2026
```

---

## Como rodar

```bash
# Tokenizador + Gate 1 (CPU, ~4 min) — sai com código 1 se o tokenizador não ganhar em PT
python bee/train_tokenizer.py --corpus bee/corpus --vocab 32000

# Gate 2 — bits-por-byte contra o SmolLM2
python bee/eval_gate2.py --bee <modelo> --rival HuggingFaceTB/SmolLM2-135M

# SFT local (RTX 5070 8 GB, ~19 min) — LR 1e-3 é o ótimo medido; micro-batch 2 é teto de VRAM
python bee/sft.py --modelo <base> --dados comeia/data/processed/sft_combinado.jsonl --lr 1e-3

# Conversar com o resultado
python bee/chat.py --sonda
```

---

## Próximos gates (do mais barato ao mais caro)

- [x] ⭐ **Gate 1 — tokenizador** mais eficiente em PT que Qwen e SmolLM2 · 4 min · ✅ +5,4%
- [x] **Corpus de treino** — 9,87B tokens únicos, mistura auditada
- [x] **Pré-treino do Bee-150M** — v1, v2 e v3 completos
- [x] 🔴 **Gate 2 vs. SmolLM2-135M** — **não passou** (3,457 × 2,010), e a investigação refutou
      geometria e LR como causa
- [x] **SFT** — gate de forma ✅, gate de conteúdo ❌ · varredura de LR fechada (ótimo 1e-3)
- [x] **Medir tokens EFETIVOS vs nominais** — 0,90% de quase-duplicata cruza a fronteira;
      **duplicata não é a explicação**. Sobra 1 hipótese viva
- [ ] **Fechar o buraco do dedup** — persistir as bandas do LSH entre execuções, como já
      é feito com o `vistos_sha` (barato, e evita que a taxa cresça em expansões futuras)
- [ ] **Gate pareado barato antes de todo run longo** (~5% do GPU-hora) — teria matado o v3 por
      ~R$ 50 em vez de US$ 34 e 22 h
- [ ] ⭐ **Replicar o FineWeb-Edu em português** — a hipótese viva. Corpus menor e melhor
- [ ] **Midtraining a partir da BNCC** — 1.583 habilidades ≈ 320M tokens com licença limpa
- [ ] **ENEM como eval set** — ~3.750 itens públicos com gabarito e parâmetros de TRI, que permitem
      ordenar currículo por dificuldade *medida*
- [ ] **Release**: model card honesto + pesos + demo no HF

---

## Hardware

- Local: **RTX 5070 Laptop 8 GB** (Blackwell sm_120 — exige PyTorch cu128) · Ultra 9 275HX · 31 GB RAM
- Pré-treino: **RunPod A100-80GB** ($1,50/h)

Última atualização: 2026-08-04.
