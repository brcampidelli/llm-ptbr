# 🐝 BEE — uma LLM em português, treinada do zero

**O que é:** um modelo de linguagem sendo construído **do zero** — tokenizador nosso, arquitetura
nossa, corpus montado por nós, pesos inicializados aleatoriamente e treinados por nós. A aposta é o
**português**: é o único lugar onde um modelo pequeno nosso pode ganhar de alguém.

**O que ainda NÃO é:** não existe modelo Bee treinado. Hoje temos o **tokenizador** (medido e
aprovado) e o **coletor de corpus**. O pré-treino ainda não rodou. Qualquer número neste README que
diga respeito a um modelo funcionando é da **camada COMEIA sobre o Qwen3.5-4B** (Alibaba) — veja
[docs/comeia-sobre-qwen.md](docs/comeia-sobre-qwen.md). Isso está separado de propósito: misturar as
duas coisas seria vender um modelo emprestado como se fosse nosso.

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
menor**. Isso importa duplamente num modelo de 150M: 32k × 576 = **18,4M** de embedding, contra 143M
se usássemos o vocab do Qwen (que sozinho já seria ~95% do orçamento de parâmetros).

Custo do gate: **4 minutos de CPU**. Era o teste mais barato do projeto e o primeiro que podia matar
a aposta inteira. Detalhes: [docs/gate-1-fertilidade-2026-07-27.md](docs/gate-1-fertilidade-2026-07-27.md).

**O que o gate NÃO diz** — três ressalvas que ficam registradas:
1. **Em inglês somos 8,7% piores** que o Qwen. É o preço explícito de concentrar 32k em PT.
2. **O corpus tem 0% de código** — a fonte falhou (abaixo). Tokenizador sem código gasta mais tokens
   em código, e isso **não foi medido**.
3. Fertilidade mede **eficiência de representação**, não qualidade do modelo. Condição necessária
   para a aposta, não suficiente.

### Corpus v0 — 1,84 GB, e a auditoria pegou uma falha

| fonte | licença | pedido | obtido | aproveitamento |
|---|---|---:|---:|---:|
| `fineweb-2` cfg `por` | ODC-By | 35% | 38% | 98% |
| `PleIAs/Portuguese-PD` | domínio público | 15% | 16% | 64% |
| `wikimedia/wikipedia` pt | CC BY-SA | 10% | 11% | 90% |
| jurisprudência PT | Apache-2.0 | 5% | 5% | 39% |
| `fineweb-edu-dedup` | ODC-By | 15% | 16% | 99% |
| `cosmopedia-v2` | ODC-By | 10% | 11% | 91% |
| **`python-edu`** | ODC-By | 10% | **0%** | **0%** |

Idioma real: **PT 79% · EN 20% · código 0%.** Alvo era 65% ±10 pp → **fora**.

**Causa raiz:** o subset `python-edu` do `smollm-corpus` **não traz o texto** — só `blob_id`/`path`;
o conteúdo vem do S3 do Software Heritage. O coletor achou o campo vazio em 100% dos registros e
descartou tudo; a fatia de 10% foi redistribuída e empurrou o PT para 79%. O mesmo vale para
`the-stack-v2`, que também é só ponteiro.

Foi a **auditoria de mistura** que pegou — `detect_lang` sobre a amostra, comparando o obtido com o
pedido. Sem ela, isso só apareceria depois do treino, como "o modelo não sabe código".

⚠️ Os 1,84 GB servem ao tokenizador, **não ao treino**: 3B tokens a ~1,42 tokens/palavra pedem
**~12 GB** de texto.

---

## A escada — de 150M a onde o dinheiro levar

O código é **o mesmo em todos os degraus**; muda o arquivo de config e a fatura.

**Parede 1 — VRAM.** Pré-treino completo custa ~12–16 bytes/parâmetro (pesos + gradientes + estado
do Adam em fp32):

| modelo | VRAM | cabe na L4 (22 GB)? |
|---|---:|---|
| Bee-150M | ~2,4 GB | ✅ |
| Bee-500M | ~8 GB | ✅ |
| Bee-1B | ~16 GB | ⚠️ apertado |
| Bee-4B | ~64 GB | ❌ |
| Bee-10B | ~160 GB | ❌ |

**Parede 2 — tempo** (FLOPs ≈ 6ND; L4 ≈ 3×10¹³ FLOP/s efetivos):

| alvo | tempo na L4 |
|---|---|
| 150M @ 3B tokens | **22 h** ✅ |
| 500M @ 10B | ~12 dias ✅ |
| 1B @ 20B | ~46 dias ⚠️ |
| 4B @ 80B | ~2 anos ❌ |
| 4B @ 4T (paridade Qwen) | **~101 anos** ❌ |

**Custo de cada degrau** (8×H100 ≈ US$ 20/h):

| degrau | onde | custo |
|---|---|---|
| **Bee-150M** | Colab L4 | grátis · 22 h |
| Bee-350M / 500M | Colab L4 | grátis · dias |
| Bee-1B | 8×H100 | ~US$ 200–400 |
| Bee-4B (poucos tokens) | 8×H100 · 7 dias | ~US$ 3.400 |
| Bee-4B (paridade Qwen) | 64×H100 · 43 dias | ~US$ 1,3 M |
| 10B de fronteira | 512×H100 | ~US$ 5 M+ |
| 1T+ MoE (classe Kimi K2.7) | milhares de GPUs | US$ 10–100 M |

⭐ **A escada é `tokens × parâmetros = dinheiro`.** O 150M não é brinquedo: é a esteira que roda em
qualquer escala. Por isso doação ou investimento se converte diretamente em capacidade, sem
reescrever o projeto.

**Atalho honesto para depois:** *upcycling* — continuar o pré-treino de um modelo aberto no nosso
corpus, ou converter denso em MoE. É como equipes pequenas chegam a contagens altas de parâmetros.
⚠️ Deixa de ser "do zero" — opção consciente para mais adiante, não o plano padrão.

---

## Arquitetura do Bee-150M

Llama-style via `LlamaConfig`, **sem código de modelagem custom** — decisão deliberada: tudo que já
construímos (PEFT, TRL, vLLM, nossos evals) funciona sem uma linha de adaptação.

```
vocab 32.000 · tied embeddings
30 camadas · d_model 576 · intermediate 2048 (SwiGLU)
9 cabeças (head_dim 64) · 3 KV heads (GQA)
RoPE (theta 10000) · RMSNorm · seq_len 2048
≈ 151M params  (132M nas camadas + 18,4M no embedding)
```

**Fundo-e-fino** (30 camadas para 576 de largura): é a forma que o SmolLM2 encontrou nessa escala —
profundidade compra composição melhor que largura em modelos pequenos. Não é chute, é copiar um
recipe publicado. **GQA** (3 KV heads em vez de 9) corta o KV-cache em 3× na inferência, que é o que
decide se roda local.

---

## Regras duras do projeto

- ⛔ **Procedência dos dados é requisito de negócio, não escrúpulo.** A primeira coisa que qualquer
  investidor audita é de onde veio o corpus. Cada shard carrega fonte e licença no `MANIFEST.json`.
  - **Scribd está fora** — conteúdo protegido atrás de paywall. Estar logado dá acesso para *ler*,
    não licença para *treinar e publicar*. Um Bee treinado com isso é impublicável e não-investível.
  - **GitHub raspado direto está fora** — licença varia por repositório. Só datasets já filtrados.
- ⛔ **Nunca** treinar com saídas de GPT/Claude/Gemini (ToS proíbem + contaminam a licença aberta).
  Destilação só de professores abertos — `assert_teacher_allowed()` falha alto e cedo.
- **Holdout por hash, nunca por posição.** `sha1(doc) % N` — a lição mais cara do projeto, aprendida
  duas vezes (ver COMEIA) e agora aplicada desde o primeiro dia do Bee.
- **Auditar a mistura, não assumir.** Foi assim que o `python-edu` = 0% apareceu.
- **Dificuldade se mede, não se presume.**
- **Testar > confiar no design.**

---

## A camada COMEIA — o método, que sobrevive à troca de backbone

A COMEIA é um orquestrador em código que roteia cada pedido para uma **abelha** (adapter LoRA
especializado) sobre **um backbone carregado uma vez**. Foi construída e validada sobre o Qwen3.5-4B,
com 3 abelhas treinadas e medidas. **Ela é agnóstica ao backbone por construção** — é o que será
reaplicado sobre o Bee quando ele existir.

| peça | por que serve ao Bee |
|---|---|
| filtro **"o base erra"** | funciona sobre qualquer base |
| `schema_check.py` | conformidade + **groundedness** (alucinação decidível por código) |
| split estável por `sha1` | independe de modelo |
| harness de avaliação | 5 métricas + few-shot com guard de vazamento |
| `sft_qlora.py` · `orchestrator/` | rodam em qualquer modelo Llama-arch — e o Bee é Llama-arch |
| **o método** (gate → filtro → holdout duplo) | acertou a previsão 4× (1 fracasso, 3 sucessos) |

⚠️ **O que não transfere:** os três adapters atuais estão atados ao Qwen. A COMEIA-sobre-Qwen segue
sendo o sistema *capaz*; o Bee é o *nosso*.

📄 Resultados medidos, erros cometidos e lições: **[docs/comeia-sobre-qwen.md](docs/comeia-sobre-qwen.md)**

---

## Estrutura

```
├── bee/                    ⭐ O MODELO NOSSO, do zero
│   ├── build_corpus.py     #  coleta com manifesto de procedência + auditoria de mistura
│   ├── train_tokenizer.py  #  BPE ByteLevel 32k + ⭐ GATE 1 (fertilidade vs. rivais)
│   ├── config.py           #  (a fazer) arquitetura — o mesmo arquivo em toda a escada
│   ├── pretrain.py         #  (a fazer) pesos aleatórios → modelo
│   └── eval_bee.py         #  (a fazer) perplexidade, idioma, e ⭐ o GATE 2 vs. SmolLM2
│
├── comeia/                 O MÉTODO de especialização (hoje sobre Qwen, amanhã sobre o Bee)
│   ├── orchestrator/       #  registry, hot-swap de LoRA, router, verificador
│   ├── data/               #  pipelines de destilação, filtro "o base erra", schema_check
│   ├── train/              #  SFT e DPO via QLoRA
│   ├── eval/               #  harness com holdout duplo e baseline externo
│   └── colab/              #  receitas reproduzíveis de uma linha
│
└── docs/                   estudos, avaliações e o histórico da COMEIA
```

---

## Como rodar

**O tokenizador e o Gate 1** (CPU, ~4 min dado o corpus):
```bash
python bee/build_corpus.py --target-gb 2 --out bee/corpus
python bee/train_tokenizer.py --corpus bee/corpus --vocab 32000
```
O gate sai com código 1 se o tokenizador **não** for melhor em PT que os rivais.

**A COMEIA sem GPU** (valida rota e métrica de graça, em qualquer máquina):
```bash
python comeia/orchestrator/run.py --route-only --sample
```

---

## Próximos gates (a ordem importa: do mais barato ao mais caro)

- [x] ⭐ **Gate 1 — tokenizador** mais eficiente em PT que Qwen e SmolLM2 · **4 min** · ✅ +5,4%
- [ ] **Corpus de treino** ~12 GB, mistura auditada dentro de 65% ±10 pp, com código de verdade
- [ ] **Gate 1.5 — retomada** por checkpoint testada matando o processo de propósito (o runtime
      *vai* cair; o plano assume isso em vez de torcer contra)
- [ ] **Pré-treino do Bee-150M** — 3B tokens, ~22 h de L4, perplexidade caindo em PT **e** EN
      separados (misturar esconde regressão num idioma)
- [ ] ⭐ **Gate 2 — o Bee-150M bate o SmolLM2-135M em português?** Mesma régua, contaminação
      verificada. É a única comparação externa que decide se a aposta do nicho valeu.
- [ ] **SFT + COMEIA sobre o Bee** — o pipeline inteiro roda mudando só `--model`
- [ ] **Release**: model card honesto + pesos + demo no HF

---

## Hardware

- Local: **RTX 5070 Laptop 8 GB** (Blackwell sm_120 — exige PyTorch cu128) · Ultra 9 275HX · 31 GB RAM
- Treino/avaliação: **Colab Pro+ (L4, 22 GB)**

Última atualização: 2026-07-27.
