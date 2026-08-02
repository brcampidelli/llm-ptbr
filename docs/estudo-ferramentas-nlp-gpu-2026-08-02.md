# Estudo — Ferramentas de NLP, embeddings, stack LLM e GPU cloud (aplicado ao Bee)

**Data:** 2026-08-02 · **Método:** multi-agente (4 pesquisadores paralelos) · **Fontes:** páginas
oficiais + WebSearch de preço/manutenção/benchmark (jul-ago/2026).

> 12 links pedidos pelo Bruno, agrupados por tema e avaliados por **utilidade real pro Bee**
> (LLM PT-forte do zero: corpus → tokenizador → pré-treino → pós-treino → RAG/agente).
> Honestidade sobre o que é **legado/pegadinha**. Foco só no Bee.

---

## ⭐ O mais acionável AGORA: GPU cloud (Vast.ai / RunPod)

**Por quê importa hoje:** o treino do Bee está preso em **~31h no Colab**, que desconecta, tem teto
de compute-unit e loteria de A100. GPU dedicada resolve a **dor** (não o custo — o Colab Pro+ é até
mais barato/hora).

**Custo de UM run do Bee (~31h A100)** — ordem de grandeza (marketplace flutua):

| plataforma / GPU | preço |
|---|---:|
| Vast.ai **A100-40GB spot** (cabe folgado no 150M c/ Liger) | **~$8-14** |
| Vast.ai A100-80GB on-demand | ~$34 |
| RunPod A100-80GB **spot** | ~$22 |
| RunPod Secure on-demand (previsível) | ~$43-59 |
| H100 spot (Vast, se acelerar) | ~$24-35 |

- **Vast.ai** = marketplace peer-to-peer (GPU de terceiros, leilão, container Docker, GPU exclusiva).
- **RunPod** = mais gerenciado: **Secure Cloud** (hardware próprio, previsível, caro) + **Community**
  (marketplace barato). Pods via template/imagem, SSH+Jupyter, network volume persistente.
- Billing por segundo, pré-pago com cartão (USD). **Spot/interruptible** = ~metade do preço, mas
  preemptível.

**Veredito pro Bee:**
- **Spot é seguro pra nós** porque já fazemos **checkpoint a cada 250 passos** → um auto-resume que
  relê o último checkpoint do volume persistente elimina o downside da preempção.
- **Vast interruptible** → experimento barato / varredura de hiperparâmetro (A100-40GB spot
  ~$0,25-0,45/h; o 150M cabe folgado em 40GB com Liger fused CE).
- **RunPod Secure on-demand** → o run "oficial" de release (150M final, ou já mirando 350M→1B):
  hardware previsível vale os ~$40-60.
- **H100:** benchmarcar antes (custo <$3 num run curto) — num **150M** o ganho real tende a ~1,5-2×
  (GPU subutilizada, gargalo migra pro dataloader). Só ganha claro ao escalar pra 500M-1B.

⚠️ **Pegadinhas honestas:** (1) Vast é GPU de estranhos — **não subir tokens/segredos na imagem**;
corpus é público (ODC-By), risco baixo, mas o peso do modelo é ativo. (2) Confiabilidade é
**por-host** (ClusterMAX classifica Vast como "Bronze") — filtrar por reliability score. (3) Corpus
e checkpoints TÊM que viver num **volume persistente**, não no disco efêmero (some quando a instância
morre). (4) Storage cobrado à parte, inclusive com a máquina desligada.

**→ Ação:** o próximo treino longo (ou o v3 se o Colab cair de vez) migra pra Vast/RunPod por
~$15-35 e acaba a novela das desconexões. Guardar os comandos como template Docker (PyTorch+Liger).

---

## Toolkits de NLP clássicos (curadoria/auditoria de corpus)

⚠️ **Nenhum substitui o tokenizador do Bee** (BPE 32k próprio). Eles fazem tokenização
**LINGUÍSTICA** (palavras, sentenças, POS, NER) — ferramentas de **limpeza/auditoria** que rodam
ANTES do BPE.

| lib | status | PT-BR | veredito pro Bee |
|---|---|---|---|
| **spaCy** | vivo, ativo | ✅ **`pt_core_news_lg`** (POS ~96%, NER sólido) | ⭐ **ADOTAR** — principal |
| **Stanza** (Stanford) | vivo, neural | ✅ PT bom (UD/Bosque) | **ADOTAR só p/ amostra** (auditor, lento sem GPU) |
| **NLTK** | vivo (3.9.2, 2025) | ⚠️ limitado (stopwords/RSLP, sem POS/NER PT pronto) | uso **pontual** (utilitário) |
| **TextBlob** | vivo mas casca fina do NLTK | 🔴 PT ausente | **descartar** (só duplica NLTK) |
| **Polyglot** | 🔴 **abandonado ~2016** | PT existe mas preso a PyICU (inferno de instalar) | **descartar** |

**Uso concreto do spaCy no pipeline:** (a) **segmentação de sentença** PT robusta pra chunking
(RAG + quebrar jurídico/wiki em unidades limpas); (b) **filtro de qualidade** — POS/NER pra rebaixar
docs com distribuição degenerada (menu/lista/boilerplate têm POS anômalo; texto real tem verbos/
substantivos balanceados); (c) métricas de corpus (comprimento de sentença, type-token ratio) como
sinal independente do bpb. Rápido o bastante pra varrer milhões de docs em CPU. **Stanza** = segunda
opinião neural em subconjuntos (não varredura total). Pra language-ID, **não usar Polyglot** — usar
**fastText lid.176** (abaixo).

---

## Embeddings / vetores (RAG, language-ID, dedup semântico)

| lib | status | papel |
|---|---|---|
| **Sentence-Transformers (SBERT)** | ⭐ vivo (5.6.1, jul/2026), migrou pra org `huggingface` | **espinha do RAG** |
| **fastText** | ⚠️ parado (~2022) mas `lid.176` é padrão-ouro estável | **language-ID no coletor** |
| **Gensim** | "stable maintenance mode" (só bugfix), sem DL moderno | **legado** — só análise/baseline |

**Aplicações no Bee:**
- **(a) RAG — ADOTAR SBERT** (padrão bi→cross): **bi-encoder** embedda os chunks (retrieval barato)
  + **cross-encoder** reranqueia o top-k (precisão).
  ⚠️ **Achado crítico (MTEB-PT/MTEB-BR, 2026):** o **ranking multilíngue NÃO prevê PT-BR** de forma
  confiável. Modelos PT-específicos (**Serafim / BERTimbau**) lideram em **similaridade (STS)**; os
  grandes multilíngues (**multilingual-E5-large, BGE-M3**) seguem competitivos em **retrieval (busca)**.
  → **Não escolher no escuro:** rodar um mini-MTEB-PT interno e decidir por número. Onde houver
  gabarito/ground-truth, ele vira **eval set de graça** pra essa decisão. (Correção honesta: o
  respaldo de benchmark PT aparece na família Serafim/BERTimbau, não confirmei os `rufimelo`.)
- **(b) language-ID — ADOTAR fastText `lid.176`** (917kB `.ftz`, 176 idiomas, score de confiança):
  melhor que heurística, custo ~zero. Melhora dedup por idioma e filtragem de não-PT. (Sucessor
  ainda melhor: o LID do NLLB, ~1.2GB, se quiser mais.)
- **(c) dedup semântico — SBERT complementa o MinHash:** MinHash pega near-dup **lexical** (texto
  quase igual); embeddings pegam **semântico** (parafraseado). Fluxo: MinHash primeiro (barato) →
  embeddings + threshold de cosseno no que sobra. ⚠️ embeddar corpus inteiro é caro em GPU → por blocos.
- **(d) Gensim word2vec/LDA — legado:** fora do RAG (SBERT supera). Útil só como **laboratório**:
  vizinhos de palavra, drift de vocabulário, sanidade de tokenização, topic modeling do corpus PT.

---

## Stack LLM: HuggingFace Transformers + LangChain

### HuggingFace Transformers — 3 coisas pra adotar já (já usamos o núcleo Llama)
1. **PEFT + bitsandbytes (QLoRA) pro SFT** — 4-bit + LoRA = SFT sem estourar VRAM; casa direto com
   os **adapters hot-swap da COMEIA** (mesmo formato LoRA).
2. **`generate()` / `GenerationConfig`** (streaming, `custom_generate`) — caminho canônico pra
   amostrar/avaliar o Bee em vez de loop de decodificação manual.
3. **Servir por vLLM / TGI** — o Transformers v5 se posiciona como "definição de modelo" e **delega
   serving**. Exportar o checkpoint (já é compatível) e servir por vLLM/TGI pra throughput.
   Quantização (AWQ/GGUF) só se o alvo for **CPU/edge** — num 150M o ganho de VRAM é marginal.
- **Manter o loop próprio de pré-treino** (já otimizado: grad-accum, Liger fused CE, micro-batch —
  o `Trainer` esconderia esse controle). Usar `Trainer`/`SFTTrainer` (TRL) **só no pós-treino**.

### LangChain — 🔴 NÃO adotar como framework
- É orquestração de LLM (chains/LCEL, agents, tools, memory, retrievers; hoje repackaged em
  LangChain + LangGraph + LangSmith).
- **Honestidade:** fama de **peso, churn de API, abstrações vazantes**. O reposicionamento pra
  LangGraph é sinal de que a camada original não escalou. **E ele vende exatamente o que a COMEIA já
  faz melhor pro nosso caso:** o **roteador determinístico** é a direção que o LangGraph tenta
  alcançar com grafos de estado — e o nosso já roda **sem dependência pesada nem LLM pra rotear**.
- **No máximo:** pegar `langchain-text-splitters` (ou um loader isolado) pontualmente se precisar de
  RAG rápido — **copiando o padrão, sem acoplar a stack inteira**. Ficar com a COMEIA.

---

## Plano de ação (priorizado)

**Agora / infra (destrava a dor do treino):**
- [ ] Preparar um **template Docker** (PyTorch + Liger + deps do Bee) reusável em Vast/RunPod.
- [ ] Script de **auto-resume** (detecta último checkpoint no volume persistente → continua) pra
      poder usar **spot** com segurança.
- [ ] Próximo treino longo (ou o v3, se o Colab cair): rodar em **Vast interruptible** (~$15) ou
      **RunPod Secure** (release). Benchmark curto **A100 vs H100** (<$3) antes de pagar prêmio de H100.

**Curadoria de corpus (qualidade dos dados do Bee):**
- [ ] **spaCy `pt_core_news_lg`** — segmentação de sentença + filtro de qualidade por POS/NER na
      coleta; **Stanza** como auditor de amostras.
- [ ] **fastText `lid.176`** — trocar a heurística de language-ID do coletor.
- [ ] **SBERT (embeddings)** como 2ª camada de dedup semântico sobre o MinHash (por blocos).

**Pós-treino & RAG (fases seguintes):**
- [ ] **PEFT + QLoRA (Transformers)** pro SFT do Bee → adapters da COMEIA.
- [ ] **SBERT bi→cross** pro RAG; **medir** os modelos PT (Serafim/BERTimbau vs E5/BGE-M3) no NOSSO
      conteúdo antes de escolher (gabarito = eval set).
- [ ] **vLLM/TGI** pra servir com throughput quando precisar.

**Descartar:** LangChain (fica a COMEIA), TextBlob, Polyglot, Gensim-em-produção.

---

## Incertezas honestas
- Preços de GPU flutuam (marketplace); A100-40GB spot do RunPod e alguns spots menos corroborados.
- Speedup exato H100 vs A100 no Bee-150M **não medido** — benchmarcar.
- Datas exatas de última release de fastText/Gensim não confirmadas (ordem: fastText ~2022,
  Gensim série 4.x em maintenance).
- Nomes exatos de cross-encoder PT pro rerank — item a validar por número.
