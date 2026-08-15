# Estudo — Qwen3.8, arquiteturas de SLM e o que disso serve ao Bee

**Data:** 2026-08-14 · **Método:** 9 lotes de leitura em paralelo (~14 fontes primárias + ~10 de apoio) + 3 afirmações passadas por refutação adversarial · **Estado do projeto:** Bee-350M **em treino, congelado** (~105 h restantes, US$ 115 comprometidos, saldo US$ 260).

> **Veredito em uma frase:** destas ~14 fontes, **duas** mudam alguma decisão do Bee — a medição de 340M do *Hybrid Linear Attention* (que **refuta** trocar a atenção por Gated DeltaNet na nossa escala) e a tabela de escala do MTP do Meta (que **refuta** multi-token prediction abaixo de 1,3B). Tudo o mais ou é **inútil agora**, ou é **diagnóstico barato de US$ 0** para rodar quando o pré-treino terminar, ou é **hipótese com preço** para um próximo degrau que ainda não foi orçado. E a premissa que deu nome ao lote está errada: **Qwen3.8 não é arquitetura nova.**

---

## Legenda obrigatória — o marcador de escala

Toda recomendação abaixo carrega o **menor modelo em que a coisa foi de fato medida**. Sem isso, o documento seria uma lista de desejos.

| Marcador | Significado |
|---|---|
| **[NA ESCALA]** | menor modelo medido **≤ 500M** — é receita, não aposta |
| **[ZONA CINZA]** | menor modelo medido entre **0,5B e 7B** — o número acompanha o marcador |
| **[APOSTA]** | menor modelo medido **≥ 7B** — pelo critério do projeto, não é receita |
| **[SEM NÚMERO]** | a fonte enuncia a técnica e **não reporta nenhuma métrica** |

**Regra que vale para o documento inteiro:** eu sou o sintetizador. **Não abri um único PDF.** Todo número aqui vem de resumos de leitura de outros agentes, exceto os `config.json` do Hugging Face, que foram lidos verbatim. Onde a leitura voltou inconsistente, está marcado.

---

## O achado que derruba o título do lote

Foi feito o diff campo-a-campo do `text_config` de `Qwen/Qwen3.5-27B` contra `Qwen/Qwen3.8-27B`:

- **ZERO diferenças de valor.** `layer_types` idêntico. Contagem de parâmetros idêntica **na unidade**: 27.781.427.952 nos dois.
- As únicas diferenças são campos redundantes presentes num e ausentes no outro (`mlp_only_layers` vs `partial_rotary_factor`/`output_gate_type`/`tie_word_embeddings`/`bos`/`pad`).
- O README confirma em texto: *"Built on the architectural foundation of Qwen3.5"*.

**Qwen3.5 → Qwen3.8 é dado + pós-treino, não arquitetura.** O salto arquitetural real foi **Qwen3 → Qwen3-Next/Qwen3.5**, e é exatamente esse que o Bee-350M (rodando `Qwen3ForCausalLM`) não tem. Consequência prática de planejamento: o espaço de estudo cai pela metade — não existem "duas gerações" a alcançar, existe **uma**, e a pergunta é única: *vale trocar `Qwen3` por `Qwen3_5` no `bee/config.py` num degrau futuro?*

Corolário desagradável para quem gosta de manchete: o `Qwen3.8-27B` é **denso**, não MoE. MoE mora em outra classe (`qwen3_5_moe`) cujo menor membro publicado é **35B-A3B** — 101× o Bee-350M.

---

## 1. INÚTIL AGORA

Coisas verdadeiras, medidas, e sem consequência nenhuma para o Bee — nem no run congelado, nem no pós-treino, nem no próximo degrau ao alvo atual (texto PT, `seq_len 2048`, uma GPU).

### 1.1 Todo o survey de SLM (arXiv:2505.19529v2) como fonte de número — **[SEM NÚMERO]**

É o documento do lote com o título mais próximo do Bee e o conteúdo mais distante. Contagem feita: **15 afirmações quantitativas, das quais só 6 têm número + citação primária.** As outras 9 vêm das Tabelas 2 e 3 **sem nenhuma citação e sem escala de modelo** — e são justamente as mais citáveis: *"50% mais rápido e 40% menos memória vs FP32"*, *"modelos 2× maiores"*, *"20% melhor generalização"*, *"60% de redução com <2% de perda"*, *"50% menos custo, 30% menos tempo de inferência"*, *"retém 90% do professor com 70% menos tamanho"*. **Nenhuma dessas pode ser repassada.**

Pior: 8 erros de citação verificáveis. Mamba citado como *Mamba4Rec* (sistema de recomendação); Longformer citado como *Transformers are SSMs* (Mamba-2); SpinQuant (2024) citado como Han et al. 2015 (paper de **poda**); MobileLLM citado duas vezes com refs erradas, uma delas com cara de id inventado (`abs/2401.12345`); TinyBERT (um **modelo**) listado como **dataset** de avaliação; HallusionBench (diagnóstico **vision-language**) usado para sustentar afirmação sobre alucinação em modelo de linguagem.

E a Tabela 1, intitulada *"Various SLMs"*, contém **OPT-175B, BLOOM-176B, Qwen-72B e Gemma-2-27B**, com menor entrada em **Phi-1 (1,3B)**. Um survey de modelos pequenos sem uma única entrada na faixa 100–500M.

**Uso legítimo:** índice de nomes para ler no primário. Nada mais.

### 1.2 Poda (SparseGPT, Wanda, n:m) — **[APOSTA]** (menor escala citada: 7B; alvos nomeados: OPT-175B, BLOOM-176B)

Provavelmente **prejudicial**, não apenas inútil. Modelos de 175B são gordos por construção (OPT roda a ~1,71 tokens/param pela própria Tabela 1 do survey) e por isso podam bem. O Bee-350M está a **63 tokens/param** — muito mais denso em informação por parâmetro. A folga que a poda explora não existe aqui. Se algum dia interessar, o teste válido é podar o **Bee-150M**, que já existe e custa US$ 0 medir, e ver o que acontece com o bpb 0,844 antes de sequer considerar no 350M.

### 1.3 Quantização ternária CAT-Q (arXiv:2606.26650) — **[ZONA CINZA, 1,7B]**, e a curva anda contra nós

Vale registrar porque é ICML 2026 oral e a manchete é sedutora ("100.000× menos tokens de treino que QAT"). Mas o número que importa não é a manchete — é a **degradação por tamanho**:

| modelo | média 5 benchmarks (FP → ternário) | perda |
|---|---|---|
| Llama2-70B | 76,53 → 72,72 | **−3,81 pp** |
| Qwen3-4B | ~68,25 → 57,06 | −11,2 pp |
| Qwen3-1,7B | 61,42 → 51,01 | **−10,41 pp** |

Razão de dano 1,7B/70B ≈ **2,7×**. Extrapolar para 345M seria extrapolar **contra** a tendência medida. E a aritmética mata a motivação: o Bee-350M em bf16 ocupa ~0,69 GB e já cabe folgado na 5070 de 8 GB; ternarizar levaria a ~0,09 GB — economia de 0,6 GB contra >10 pp esperados de qualidade. **MoE e quantização extrema são técnicas para trocar memória por FLOPs; o Bee tem o problema oposto.**

⚠️ **Não verifiquei:** o HTML do CAT-Q foi lido por sumarizador, não página a página. Duas leituras voltaram **inconsistentes entre si** (o texto diz "~9,4% de queda" no 1,7B, mas 61,42 → 51,01 dá 10,41 pp) e a frase sobre ativações voltou auto-contraditória (define A16 e depois fala em ativações quantizadas "exceto o softmax"). Tratar como ordem de grandeza, dígito não confirmado. O paper também **não reporta uma única perplexidade ou bpb** — não há ponte com a métrica do Bee.

### 1.4 MoE de capacidade expandida — **[NA ESCALA, 18M/58M/200M ativos]** e a resposta é NÃO

Três números independentes fecham a questão, e nenhum deles é opinião:

1. **Alvo errado.** *Mixture of Parrots* (arXiv:2410.19034) treinou MoEs com 18M, 58M e 200M de parâmetros **ativos** e mediu: a params **totais** iguais, o denso **vence** em commonsense e matemática; o MoE só ganha em memorização de conhecimento de mundo. Prova de separação formal: existem problemas de grafo que MoE não resolve com nenhum número de experts a largura fixa e um denso pouco mais largo resolve. **O que falta ao Bee é execução e raciocínio, não memorização.**
2. **Dado.** Um MoE com 345M ativos e 8× o total (~2,8B) cairia de 63 para **7,9 tokens/param total**. As referências que funcionam usaram 400B (Demons in the Detail), ~5T (OLMoE) e **10T** (Granite-3.0-1B-A400M) tokens. O Bee tem 21,75B.
3. **Memória.** ~2,8B params em bf16 + master fp32 + estados Adam ≈ **38,5 GB** > 32 GB da RTX 5090. Não cabe.

Custo evitado: US$ 115–300 de um saldo de US$ 260.

### 1.5 MTP como cabeça enxertada no 350M — **[APOSTA, 7B]**, e foi medido que não funciona

O ganho de inferência do MTP (self-speculative decoding, até 3,0× em código / 2,74× em Wikipedia com 4 cabeças) exige cabeças **pré-treinadas junto**. Gloeckle et al. testaram o enxerto por fine-tune (Llama 2 7B, 200B tokens de código, Tabela S6) e o veredito literal é: *"does not significantly improve performance ... this new loss changes the initialization too brutally and never really recovers"*. O Bee-350M está congelado sem cabeças extras. Encerrado.

### 1.6 Contexto longo, mRoPE, torre de visão, extensão YaRN 262k→1M — **[APOSTA/[SEM NÚMERO]]**

O Bee treina em `seq_len 2048`. `partial_rotary_factor 0.25` (só 64 de 256 dims giram), `rope_theta 1e7`, `mrope_section [11,11,10]`, encoder de visão de 27 blocos — tudo calibrado para um regime **128× maior** e para posição de imagem/vídeo. Nada transferível sem re-treino e sem benefício no uso atual.

Idem o StreamingLLM em regime extremo: 4M tokens, 22,2× de speedup, StreamEval com Llama-2-70B-Chat indo de 0,12% para 91,37% em ARC-E — números reais, todos **≥ 2,8B**, num regime de contexto que o Bee não tem.

### 1.7 A revisão sistemática PT-BR (Ribeiro & Tsunoda 2025, UFPR) — rendeu quase nada, e é honesto dizer

Este lote **rendeu pouco**. É bibliometria e crítica de campo (Texto Livre, DOI 10.1590/1983-3652.2025.60103), não metodologia de avaliação. **Rendimento numérico técnico: zero** — o artigo inteiro não reporta um único valor de BLEU/ROUGE/BERTScore/MAUVE/perplexidade/concordância inter-juízes.

Dois fatos sobrevivem, nenhum técnico:

- **Decisão negativa acionável [SEM NÚMERO]:** a própria revisão conclui que **não existe protocolo unificado de avaliação de criatividade computacional** (2014–2024, 41 artigos). Ou seja: o Bee não está ignorando uma régua padrão de qualidade de texto livre em PT — **essa régua não existe**. Medir bpb + taxa de **execução** de ferramenta continua sendo a escolha defensável, e a ausência de avaliação de texto livre vira limitação conhecida do campo inteiro, citável.
- **Posicionamento:** em 41 artigos selecionados com busca que aceitava português, **ZERO autores brasileiros**. Número citável de fonte revisada por pares para a narrativa do projeto. Não muda uma linha de código.

⚠️ **O lote pediu "detecção de texto gerado por máquina" e esse tema simplesmente não existe no artigo.** O que ele chama de "identificação" é identificação de **linguagem figurada** (metáfora, ironia, sarcasmo), 18/41 artigos. Zero menções a DetectGPT, watermarking, GPTZero ou qualquer classificador humano-vs-máquina.

### 1.8 A taxonomia de avaliação do survey — o Bee está **à frente** dela

Registro pelo valor negativo: a Tabela 4 do survey (SuperGLUE, SQuAD, TriviaQA, CoQA, NQ, PrivacyGLUE, MIMIC, n2c2, LEAF) **não tem um único benchmark generativo, agêntico ou de tool-use**, nem perplexidade/bpb, nem nada em português. A métrica por **execução** que o Bee já usa (65,9% de tarefas de tool-use cumpridas) e o bpb PT 0,844 estão **fora do mapa deste survey inteiro**. Não há nada a importar.

---

## 2. PÓS-TREINO DO 350M

O run está congelado. Esta seção é o que sobra de fato: **diagnóstico barato e disciplina de serving.** Nenhum item aqui muda pesos do backbone.

### 2.1 ⭐ Sonda de ativações massivas e de attention sink — **[NA ESCALA, GPT-2 124M e LLaMA 60M]**, custo **US$ 0**

É o item de melhor razão valor/custo de todo o estudo, e é o único que produz **número novo medido no Bee**.

**O fenômeno.** Menos de 10 ativações entre dezenas de milhões, com magnitude 4 ordens acima da mediana (LLaMA2-7B: **2622** contra mediana **0,2**). Não são computação — são **vieses constantes**: zerar 4 delas leva a perplexidade a **infinito** (5,47 → inf); fixá-las na média não muda nada (5,47 → **5,47**). Zerar o mesmo número de ativações de magnitude mediana: **zero queda**.

**Aparece na nossa escala?** Sim, e há medição **abaixo** do Bee: Pythia-14M tem sink; GPT-2 124M tem ativações massivas; OPT-125m tem norma-infinito **339,6**; um LLaMA de **60M** treinado do zero dá Sink₁ = **18,18%** — contra 92,47% do LLaMA2-7B. **Existe na escala do Bee, mas fraco.** Ninguém mediu 150M–350M em PT.

**Previsão falsificável para o Bee-350M.** Gu et al. varreram LR num LLaMA de 60M: 1e-4 → 2,90% · 2e-4 → 11,21% · 4e-4 → 18,18% · **8e-4 → 32,23%**. O Bee roda pico **2,181e-3** e fase estável **1,200e-3** — de 1,5× a 3× acima do maior LR testado. Com 21,75B tokens (muito acima do limiar em que o sink some), **a previsão é sink pronunciado**. Se a medição der muito abaixo de 30%, a primeira hipótese é defeito do **aparato**, não do fenômeno.

**O que rodar** (script de ~30 linhas, cabe na 5070, uma passada forward sobre ~100 sequências de 2048 do holdout PT):
1. top-3 magnitudes e mediana do hidden state **por camada**, com o par (dim_feature, dim_sequência);
2. intervenção: **zerar** vs **fixar na média** as candidatas, medindo **bpb** (não PPL);
3. `Sink₁^0,3` = fração de cabeças com atenção média no 1º token > 0,3, T=64;
4. **controle negativo obrigatório:** repetir com **um token repetido T vezes**. Nos modelos RoPE o sink **some** nesse regime (Mistral-7B 97,49% → 0,00%; LLaMA2-7B 92,47% → 0,00%). Se a métrica do Bee der alta nos dois, a implementação está errada, não o modelo.

**Critério operacional dos autores para "massiva":** magnitude > 100 **e** ≥ ~1000× a mediana do próprio hidden state.

**Por que RMSNorm não protege:** ele é o **amplificador**. A ativação massiva domina o denominador, esmaga as outras dimensões, e o vetor normalizado daquele token vira quase-esparso e praticamente idêntico entre entradas — logo K e V daquele token viram **constantes**, ou seja, viés implícito. Assinatura diagnóstica: 1º token com norma-L2 de hidden **muito acima** dos demais **mas** norma de K e V **abaixo**.

**Bônus de economia:** instruction tuning quase não muda o sink (LLaMA2-7B 92,47 base → 92,88 chat). **Medir uma vez no modelo base vale para a colmeia inteira** — não é preciso remedir por abelha.

### 2.2 Disciplina de quantização para servir — **[NA ESCALA, OPT-125m]**

O risco **não está onde parece**. Três regras, todas com número:

1. **Peso-só (GGUF Q8_0/Q5_K_M/Q4_K_M, ativação em fp16) não é o caso perigoso.** As ativações massivas vivem nas **ativações**, não nos pesos. Nenhuma evidência contrária nas fontes.
2. **Ativação em INT8 é.** OPT-125m, W8A8: ppl 15,84 → **21,18 (+33,7%)**. É um modelo **menor** que o Bee-150M. Some-se ao CAT-Q (dano cresce quando o modelo encolhe) e a direção é inequívoca.
3. **KV-cache é o vetor de risco real** — o K do token-sink fica num manifold próprio.

**Armadilha específica, e é fácil de errar:** ativações massivas **não são** as *outlier features* do Dettmers. Foram achadas 10 outlier features no LLaMA2-7B e 25 no 13B, com **zero sobreposição** com as dimensões das massivas (1415/2533 e 2100/4743). Consequência de implementação: precisão mista tipo `LLM.int8()`, que mantém em fp16 as **dimensões de feature**, **não cobre** este caso — o que cobre é manter em fp16 as **posições de sequência** (1º token, 1º `.` ou `\n`).

**Experimento de uma tarde, US$ 0:** A/B de **bpb** fp16 vs Q8_0 vs Q4_K_M, e **separadamente** com `--cache-type-k q8_0` e `q4_0`. E a hipótese barata vinda do KVQuant **[APOSTA, 7B]**: manter os **4 primeiros tokens** do cache em fp16 e comparar. Se a diferença for material, o sink é o culpado; se não for, está liberado quantizar tudo.

### 2.3 Cache rolante com âncoras (StreamingLLM) — **[ZONA CINZA, 2,8B]** para o método de inferência; **[NA ESCALA, 160M]** para o mecanismo

Se a colmeia precisar de conversa mais longa que os 2048 do pré-treino: manter os **K primeiros tokens** do KV-cache permanentemente + janela deslizante, com posição **relativa ao cache**. Não exige fine-tune, já está no llama.cpp e no HF.

Números da ablação (400K tokens, PG19): Llama-2-7B com janela pura 0+4096 → ppl **3359,95**; com 1 âncora → 11,88; com 4 → **9,59**; com 8 → 9,54. **Quatro é o patamar.**

**Guarda prática:** manter **4** âncoras, não 1, enquanto o Bee não tiver token de sink dedicado — o Bee-350M não teve token inicial constante no pré-treino, que é exatamente a condição que força o modelo a recrutar **vários** tokens iniciais como ralo. Com RoPE, cachear as Keys **antes** da rotação.

**Guarda de método de brinde [APOSTA, 7B]:** cache maior **não** é monotonicamente melhor. MPT-7B piora de 14,12 → 14,25 → 14,33 → 14,99 conforme o cache dobra. Ao medir contexto no Bee, **varrer** o tamanho de cache em vez de escolher o maior que couber na VRAM.

### 2.4 Comprimento de resposta como métrica de custo — **[SEM NÚMERO]**

Do MELODI, via survey: GPU é mais eficiente que CPU, hardware especializado ganha de genérico, e o **comprimento da resposta em tokens** é um dos maiores preditores de consumo de energia. Os três vêm **sem um único valor**; o único número da seção ("até 20%") é de outra fonte, sem dizer quais técnicas nem em que modelo — **não repassar**.

O terceiro achado é o único que vira ação barata e casa com alavanca que o Bee **já mediu ter valor** (a política determinística que cortou over-calling de 23,1% → 13,8% — cortar chamada inútil é cortar token gerado). **Ação:** instrumentar tokens de saída por tarefa no boletim de serving e tratar verbosidade como custo, não como estilo.

### 2.5 A lição de método do "Demons in the Detail" — **[ZONA CINZA, 3,4B/0,6B ativado]** para a técnica, **independente de escala** para a lição

A técnica não se aplica (o Bee é denso, sem roteador, sem load-balancing loss). A **lição** se aplica hoje e custa zero.

O bug: a LBL é calculada **dentro do micro-batch** e só depois mediada entre grupos paralelos. Como micro-batch tem pouquíssimas sequências, isso vira na prática *"balanceie os experts dentro de cada sequência"* — e força os tokens de um documento inteiro de código a se espalharem uniformemente, **matando a especialização que era o propósito do MoE**. Nada dá erro; a loss cai bonito. Custo medido: ppl 7,347 → **7,198** e GSM8k 21,30 → **25,40** ao corrigir.

**É o mesmo modo de falha que já custou quatro vezes a este projeto** (rótulos deslocados, amostragem com reposição, `max_seq_len` no SFT, avaliador de mundo fechado): **uma estatística agregada na granularidade errada, e o treino roda inteiro sem reclamar.**

**Guarda derivada, para o checklist:** *toda perda auxiliar, regularizador ou métrica agregada deve **logar sobre quantos exemplos** foi agregada, e esse número precisa ser conferido contra a intenção.* No SFT e no treino de adapter do 350M isso significa logar quantos exemplos entraram em cada cálculo de métrica de máscara — extensão natural da guarda de dataset que o projeto já tem.

### 2.6 Padrão de interface para serving (README Qwen3.8) — **[APOSTA, 27B]**

Aproveitável só como **convenção**, não como capacidade: dois conjuntos de sampling (thinking: temp 1.0, top_p 0.95, top_k 20; non-thinking: temp 0.7, top_p 0.80, top_k 20, presence_penalty 1.5) e uma advertência contraintuitiva — **esforço menor não reduz o tempo total** em tarefas multi-turno, porque análise insuficiente gera mais falhas e retentativas. Isso vale direto para a abelha multi-turno já treinada. **Thinking mode propriamente dito é aposta em 345M** — nenhum número em escala pequena. Não construir `reasoning_effort` sem medir por **execução**.

### 2.7 Checklist de métricas de deployment (Tabela 4 do survey) — **[SEM NÚMERO]**

Serve como lista de conferência barata para o boletim de serving do 350M: *inference time, throughput, peak memory usage, memory footprint, compression ratio*. É taxonomia, não medição — a coluna de datasets para "Energy-Efficient AI" está literalmente vazia.

### 2.8 O que **não** há nesta seção — e é o resultado mais útil do exercício

**Do Qwen3.8 não sai NADA para o pós-treino do 350M.** Gated attention, gated DeltaNet, MoE e MTP são todas decisões de **pré-treino**: mudam o grafo e a forma dos pesos. Não existe adapter, patch de inferência ou enxerto pós-hoc que introduza qualquer uma delas num backbone Qwen3 já treinado.

O pós-treino do 350M continua sendo exatamente o que foi validado no 150M: **SFT medido por execução + rejection sampling + política determinística + adapter LoRA**. E a lei nº 2 do projeto (capacidade é disputada em modelo pequeno → adapter, não full FT) segue sendo o guia. Anotar isto explicitamente evita meses de expectativa mal-colocada.

---

## 3. PRÓXIMO DEGRAU

Tudo aqui exige **pré-treino novo (US$ 115–300)** e nada disso é receita fechada. Ordenado por razão valor/risco.

### 3.1 ⭐⭐ REFUTADO: trocar a atenção por Gated DeltaNet — **[NA ESCALA, 340M / 20B tokens]**

Este é o achado mais valioso do estudo inteiro, e é **negativo**. *A Systematic Analysis of Hybrid Linear Attention* (arXiv:2507.06457) treinou **72 modelos abertos**, 36 deles com **340M params em 20B tokens de FineWeb-Edu** — praticamente a geometria e o volume do Bee-350M (345,4M / 21,75B). Checkpoints públicos em `m-a-p/340M-20B-GatedDeltaNet-*`.

| arquitetura (340M/20B) | média zero-shot (ARC-c, ARC-e, Hella, LMB, OBQA, PIQA) |
|---|---|
| Transformer | **0,444** |
| GatedDeltaNet puro | 0,442 |
| HGRN2 híbrido 6:1 | 0,456 |
| HGRN 6:1 | 0,448 |
| DeltaNet 6:1 · GLA 6:1 | 0,441 |

**Empate técnico:** GDN puro perde 0,2 pp. O melhor híbrido ganha 1,2 pp — e **não é GDN**, é HGRN2. E os autores escrevem: *"340M models show insignificant recall capability due to their relatively small parameter count. We omit recall benchmarks for this reason"* — na nossa escala eles **nem mediram** a única dimensão em que o híbrido ganha.

**Conclusão:** trocar a atenção do Bee por GDN compra ±0,2 pp (dentro do ruído) em troca de pré-treino novo, risco de kernel e perda da compatibilidade com o SFT/LoRA já validado. O que GDN compra de verdade é **estado fixo** (KV-cache constante) — e enquanto o Bee for `seq 2048`, isso não compra nada.

**Se um dia a decisão voltar** (Bee agêntico com 32k+ de contexto), a receita medida é **híbrido 3:1 ou 6:1, nunca puro** — recall médio: puro 0,256 · 24:1 0,338 · 12:1 0,340 · 6:1 0,390 · **3:1 0,397**. Modelagem de linguagem é praticamente plana entre razões (spread 0,8 pp); recall tem spread de **14,1 pp**. E a ordem dos blocos importa: em 500M/15B, reordenar os mesmos três blocos vale **1,19 pp** (Mamba2+GDN+SWA 48,73 vs GDN+SWA+Mamba2 47,88) — **[NA ESCALA, 500M]**.

**Riscos de engenharia que ninguém mede nos papers:**
- o `chunk_gated_delta_rule` vem do pacote `fla` e o conv do `causal_conv1d`; **sem eles o modelo cai silenciosamente para ops PyTorch mais lentas e mais famintas de memória** (a doc oficial usa a palavra *silently*). É o mesmo modo de falha da §2.5;
- o **Liger não patcheia o DeltaNet**. Os 53,8k tok/s medidos hoje não se transferem — e `pretrain.py` **aborta por design** se `apply_liger_kernel_to_{arquitetura}` não existir. Sem Liger, MB=8 com checkpointing off **dá OOM na 5090 de 32 GiB**.

### 3.2 REFUTADO: multi-token prediction — **[NA ESCALA, 300M/340M/600M]**, com três medições convergentes

O ponto de virada foi medido e fica em **~1,3B — 4× acima do Bee-350M.**

**Gloeckle et al. (arXiv:2404.19737, ICML 2024)**, 6 tamanhos treinados do zero, pass@1 com n=1 → n=4:

| tamanho | MBPP | HumanEval |
|---|---|---|
| **0,3B** | 1,8 → **1,0** (−44,4% rel.) | 1,9 → **1,2** |
| **0,6B** | 4,7 → **3,0** | 2,9 → **2,7** |
| 1,3B | 6,8 → 7,4 | 4,6 → 4,8 |
| 3B | 11,1 → 12,7 | 7,2 → 7,2 |
| 6,7B | 23,9 → 26,0 | 12,8 → 13,8 |
| 13B | 26,0 → 30,5 | 14,1 → 15,8 |

Frase textual do paper: *"Multi-token prediction models are worse than the baseline for small model sizes, but outperform the baseline at scale."*

**Zuhri et al. (arXiv:2508.19228)**, **340M em 52B tokens de FineWeb-Edu** — linguagem natural, não código: perda NTP **2,39 → 2,46** com MTP (pior no próprio objetivo), TriviaQA −2,37 pp.

**KORMo (arXiv:2510.09426), 1B:** MTP 41,35 vs NTP 43,38 (**−2,0 pp**).

E o mesmo paper do Meta mediu MTP em **linguagem natural a 7B/200B tokens**: n=2 empata, **n=4 regride**. Vinte vezes o Bee, no domínio do Bee, e o ganho é zero ou negativo.

**Agravantes:**
- **O custo é maior no pequeno.** Tabela S5: n=4 em 0,3B custa **+22%** de tempo de treino (n=2, +7%), contra +9% em 13B. No orçamento do Bee: ~US$ 25 a mais para colher −44% relativo. **⚠️ Contradição interna do paper:** o abstract diz *"no overhead in training time"*; a Tabela S5 diz 1,07× a 1,22×. Vale o número medido.
- **Bate na lei nº 2 do projeto.** As cabeças extras são exatamente capacidade e gradiente desviados do objetivo t+1 dentro de um orçamento fixo.
- **O mecanismo explica o vale.** O benefício de MTP na formação de *induction heads* existe em modelos de ≤30M não-embedding e **desaparece em ~100M não-embedding**; a partir daí, textualmente, *"multi-token prediction actually hurts on this restricted benchmark"*. O Bee-350M tem ~314M não-embedding — **3× além do ponto onde o benefício acabou** e 4× abaixo de onde o outro começa.

**A única receita que sobreviveria**, se um degrau ≥1,3B algum dia justificar: **ProphetNet [NA ESCALA-ish, 6+6 camadas / hidden 768]** — R-1 42,21 (1-gram) → **42,52** (2-gram) em CNN/DailyMail. Três escolhas de projeto explicam por que ele ganha onde o do Meta perde: **(a) n=2, não 4; (b) streams com parâmetros COMPARTILHADOS** com a main stream, capacidade adicional zero (é a versão "adapter" do problema, enquanto as cabeças transformer independentes do Meta são a versão "full FT"); **(c) peso decaído** na perda auxiliar (α_j = γ^j / Σγ^i). ⚠️ Mas é encoder-decoder com denoising de span, medido após fine-tune de sumarização em inglês — **não** LM causal, e o ganho é +0,31 R-1 (~0,7% relativo).

**Alternativa com um ponto medido na escala certa:** o **TOP (Token Order Prediction)** do mesmo Zuhri bateu NTP **e** MTP em 6 de 8 benchmarks a **340M**, com perda NTP praticamente empatada (2,40 vs 2,39) e custo de **uma única camada de unembedding extra**. Isso é **hipótese com um ponto medido**, não receita — se for testado, gate pareado de 300–500 passos antes de comprometer run.

**Guarda obrigatória se MTP algum dia entrar** — ele é o bug de deslocamento de rótulos multiplicado por n, **com modo de falha pior**: se a cabeça 1 estiver certa e as 2..n desalinhadas, a geração funciona, a loss cai bonito, e o único efeito é pagar +22% de compute para treinar sinal lixo. Cinco travas:
1. **por cabeça, com dado real:** para cada *i*, comparar contra `F.cross_entropy(logits_i[0,:-i], x[0,i:])`, abortar se |diff| > 0,01 nat. ⚠️ **Com tokens aleatórios e vocab 32k toda cabeça converge para ln(32000)=10,373 e a guarda passa sem testar nada** — o projeto já mediu esse falso-positivo;
2. **ordenação estrita** L₁ < L₂ < … < Lₙ com folga, no passo ~200, em texto PT real. A folga mínima em PT é **[SEM NÚMERO]** e teria de ser calibrada;
3. **controle com bug proposital:** rodar uma vez com deslocamento deliberadamente errado e **confirmar que aborta**. *Guarda que nunca foi vista disparar não é evidência* — a guarda original do projeto foi escrita, commitada e nunca chamada;
4. **contagem de posições supervisionadas:** com n=4 e seq 2048 são 2047+2046+2045+2044 = **8182**, não 8192. Diferença de 0,12% — pequena demais para aparecer na loss, grande o bastante para desalinhar;
5. **export:** conferir que a bpb da cabeça 1 sozinha reproduz a de treino no mesmo holdout até 4 casas.

### 3.3 O único candidato defensável do Qwen3.8: **gate headwise no SDPA** — **[ZONA CINZA, 1,7B]**

É a metade "chata" do lote, sem número sub-1B, e mesmo assim a melhor hipótese — porque resolve **um problema que o projeto já teve**.

**O mecanismo:** `Y' = Y ⊙ sigmoid(X·W_θ)` aplicado logo depois do SDPA. Das 5 posições testadas (G1 após SDPA, G2 após V, G3 após K, G4 após Q, G5 após a densa de saída), **só G1 e G2 funcionam**. Explicação: W_V e W_O são dois lineares consecutivos, ou seja um mapa linear de posto baixo; o gate injeta não-linearidade nele, e a esparsidade do escore filtra contexto irrelevante para a query.

**A economia que importa em modelo pequeno.** Num MoE de 15B, o gate **headwise** custou **+1,6M params (0,01%)** e entregou **88% da queda de PPL** do elementwise (5,792 vs 5,761, contra baseline 6,026) — batendo baselines que gastaram +50M, +201M e +400M em outros lugares. Traduzido para a geometria do Bee-350M (32 camadas × d_model 960 × 15 cabeças q):

| variante | params extras | % de 345,4M |
|---|---|---|
| **headwise** (960×15×32) | **0,46M** | **+0,13%** |
| elementwise (960×960×32) | 29,5M | +8,5% |

Pela lei nº 2 do projeto, só a headwise faz sentido.

**O que ela compra e ninguém mais compra: margem de learning rate** — e o Bee vive de LR agressivo escolhido pela Step Law. Em modelos densos de 1,7B:
- 48 camadas / 400B: baseline @4,0e-3 = 7,421; **baseline @8,0e-3 explode para 9,195** (MMLU 52,04 → 44,28); **gate @8,0e-3 = 7,325** (melhor MMLU da tabela, 54,47);
- 48 camadas / 1T: baseline @5,3e-3 = 7,363; **baseline @8,0e-3 DIVERGIU**; gate @5,3e-3 = 7,101; **gate @8,0e-3 = 7,078**.

Em duas configurações o baseline morre e o modelo com gate não só sobrevive como melhora. Latência introduzida: **<2%**.

**Achado colateral de graça:** massivas ≠ sink. Gate compartilhado entre cabeças dá M-Act 286 mas F-Attn 0,301; gate só no valor dá M-Act 125 e F-Attn 0,297 — **reduz ativação massiva sem reduzir o sink**. Conclusão dos autores: *"ativações massivas não são pré-requisito de attention sink"*. Ao diagnosticar o Bee (§2.1), **medir as duas coisas separadamente**.

⚠️ **Três problemas concretos antes de qualquer coisa:**
1. **1,7B é 5× o Bee.** Pelo critério do projeto, é **aposta**. E o mecanismo (esparsidade dependente da query) é plausivelmente dependente de capacidade.
2. **Para ter o gate SEM o DeltaNet** seria preciso `Qwen3_5TextConfig` com `layer_types` todo `"full_attention"` — configuração que **a própria Qwen nunca treinou**. Isso viola a regra que fez o 150M dar certo (copiar recipe publicado na mesma escala).
3. **Contradição não resolvida entre lotes** sobre o campo `attn_output_gate` — ver §4.2.

**Gate mínimo que decide, ~US$ 40:** dois runs curtos idênticos no degrau 500M (mesmo corpus, LR, passos), `Qwen3ForCausalLM` vs `Qwen3_5ForCausalLM` com todas as camadas `full_attention`, reportando **bpb E tok/s medidos**. Com três travas: abortar se `causal_conv1d`/`fla` faltarem; abortar se `apply_liger_kernel_to_qwen3_5` não existir; **confirmar que `attn_output_gate=True` alterou a contagem de parâmetros** (a q_proj deve dobrar) — *um flag ignorado é o irmão do adapter registrado como não-treinável*.

### 3.4 RMSNorm zero-centered — **[SEM NÚMERO]**, mas é a mudança de menor risco que existe

Peso inicializado em **zeros** e saída `x*(1+w)`, em vez de peso em **ones** e `x*w`. Motivação declarada: no Qwen3 com QK-Norm alguns pesos de norm crescem sem limite; a Qwen combina zero-centering com weight decay nos pesos de norm.

Uma linha, zero impacto em throughput, zero dependência de kernel. E a promessa (estabilidade sob QK-Norm) é **exatamente o regime do Bee-350M**, que já ligou QK-Norm. ⚠️ **Ninguém publicou o delta em nenhuma escala** — o que é motivo para **medir**, não para adotar por fé nem para pular.

### 3.5 Destilação de professor em vez de mais corpus — **[NA ESCALA, 58M]** para a existência, **[SEM NÚMERO]** para o ganho

BabyLLaMA: destilação de um **ensemble** de professores produz um modelo de 58M que, segundo o survey, *"supera o pré-treino no mesmo dataset"* em regime de pouco dado. **58M é o menor modelo citado em todo o survey e o único abaixo do Bee-150M.** ⚠️ E o survey **não dá um único número** — sem delta, sem benchmark, sem baseline.

Por que importa mesmo assim: casa exatamente com a lei já medida do projeto (**não expandir o corpus** — repetir o bom bate coletar a cauda ruim). Se dado novo não ajuda, o caminho é **injetar sinal do professor no mesmo corpus**: perda mista (CE nos tokens + KL contra logits de um professor PT).

**Aritmética que reposiciona o gargalo:**

| modelo | tokens/param |
|---|---|
| **Bee-350M** | **63** |
| **Bee-150M** | **144** |
| Chinchilla (nota do próprio survey) | ≥20 |
| SmolLM | 588 |
| Gemma-1 2B | 1.195 |
| TinyLlama | 2.728 |
| **Gemma-3 270M** | **22.388** |

O Bee-350M está de 8× a 43× abaixo da coorte comparável, e 355× abaixo do menor Gemma. Como expandir o corpus **já foi refutado por medição em 350M**, sobram exatamente duas saídas: **repetição controlada de épocas** (o corpus tem repetição interna de 0,28% — repetir é época, não contaminação) e **destilação**. ⚠️ O custo de inferência do professor sobre 21,75B tokens é o item caro e **não está orçado**.

### 3.6 σ-MoE (esparsidade a parâmetros iguais) — **[NA ESCALA, 41M/47M/262M]**

Único MoE do estudo cujo **menor modelo testado fica abaixo do Bee**. E é uma coisa **diferente** do MoE rejeitado na §1.4 — ver a contradição resolvida em §4.1.

A parameter-matched (não FLOP-matched, que é a comparação complacente usual): WikiText-103 47M 11,81 → **11,71** com 25% dos FLOPs; 262M 9,46 → **9,44** com **12,5%** dos FLOPs; C4 47M 23,76 → 23,25; enwik8 41M 1,08 → 1,08 bpc. Contra outros MoEs no WT-S: σ-MoE 11,59 · Switch 12,27 · S-BASE 13,01 · denso 11,81.

**⚠️ O caveat que invalida transposição direta:** os MLPs do paper são **ReLU simples**, não gated. O Bee usa **SwiGLU** (gate+up+down). A adaptação de σ-MoE para FFN gated **não foi medida por eles nem por ninguém nessa escala** — seria pesquisa nossa, com risco. Ablações úteis: init igual ao denso importa (9,44 vs 9,67); dropout de especialista importa (9,44 vs 9,53); **sigmoide > softmax** (9,44 vs 9,58).

### 3.7 A razão intermediate/d_model — o desvio de um quarto do modelo que ninguém mediu

**Refutada** a afirmação de que o `intermediate 2560` (2,67× d_model) do Bee-350M é "melhor" que os 3,556× do Bee-150M. Não porque 2560 seja pior — mas porque **é cópia literal do SmolLM2-360M**, não medição, e o próprio repositório já diz isso: `bee/config.py:133` registra *"desvio é do recipe de origem e NÃO foi medido por nós"*.

**O que é fato:** 2,67× é o **extremo inferior** de toda a distribuição contemporânea.

| modelo | d_model | intermediate | razão |
|---|---|---|---|
| SmolLM2-360M (a fonte copiada) | 960 | 2560 | **2,67×** |
| **Bee-350M** | 960 | 2560 | **2,67×** |
| Gemma-3 270M | 640 | 2048 | 3,20× |
| Qwen3-0.6B-Base | 1024 | 3072 | 3,00× |
| **Bee-150M** | 576 | 2048 | **3,556×** |
| OLMo-2-1B | 2048 | 8192 | 4,00× |
| Qwen2.5-0.5B | 896 | 4864 | 5,43× |
| **SmolLM3-3B** (mesmo laboratório, geração seguinte) | 2048 | 11008 | **5,38×** |
| LFM2-350M | 1024 | 6656 | 6,50× |
| Gemma-1 2B e 7B | 2048 / 3072 | 16384 / 24576 | 8,00× |

Dois incômodos: **(a)** o próprio HuggingFaceTB abandonou 2,67× no SmolLM3 e foi para 5,38×; **(b)** o Bee-350M manteve o vocab de 32k **mas não reinvestiu a economia de embedding** no MLP (a conta fecharia em I≈2752), desfazendo sem medir uma decisão deliberada do 150M.

**Aritmética do desvio, que ninguém do projeto tinha feito:** no Bee-350M o FFN é **75,0%** dos parâmetros do bloco (no 150M, 80,0%). Com I=3456 (3,556×), o modelo teria **427,8M em vez de 345,3M — +23,9%**, o que a 53,8k tok/s viraria ~139 h e ~US$ 142 (+US$ 27). **É uma decisão de um quarto do modelo, tomada sem medida, e o efeito em qualidade continua [SEM NÚMERO] em toda a literatura deste lote.**

Nem Gemma nem o paper de σ-MoE ablatam a razão. E a teoria não salva: o 8/3 ≈ 2,667 do SwiGLU (Shazeer 2020) é a razão que mantém **neutralidade de parâmetros** contra uma FFN GELU de 4×, não um ótimo de qualidade.

**Gate correto, se houver degrau novo:** mesmo N total, mesmo corpus, mesma seed, variando **apenas** o intermediate — A com I=2560 (32×960) vs B com I=2752 e camadas/heads ajustados para casar params. ⚠️ **1B tokens pode não separar** — rodar ≥2B por braço ou não rodar. Antes disso, recontar params dos dois braços (US$ 0) para confirmar que a comparação é isoparamétrica.

### 3.8 Sink token aprendível no pré-treino — **[NA ESCALA, 160M]** ⭐

Melhor razão valor/risco de todo o material de attention sink, e **medido na escala exata do Bee-150M** (codebase Pythia-160M, Pile deduplicado, batch 256, 143.000 passos).

**A receita:** prepender **um** token de sink aprendível em toda sequência do pré-treino, com a loss **não** computada nele. Custo: 1 token em 2048 = **0,05%** do orçamento. Não muda arquitetura, não exige custom code — é preparação de dado + máscara de loss.

**Resultados:** curvas de loss sobrepostas; **7 de 7** benchmarks zero-shot ligeiramente melhores (ARC-c 18,6→19,6; ARC-e 45,2→45,6; HellaSwag 29,4→29,8; LAMBADA 39,6→39,9; OBQA 16,0→16,6; PIQA 62,2→62,6; Winogrande 50,1→50,8); e ppl de streaming com **1** token de âncora cai de 27,87 (vanilla 0+1024) para **18,01**.

⚠️ **Dois tokens de sink NÃO melhora** — ARC-c cai para 18,7, LAMBADA para 37,5, e 1+1023 piora para 25,73. Usar **um**.

⚠️ **E ele NÃO elimina as ativações massivas** — elas migram para dentro do token de sink (medido em GPT-2 124M: vanilla, +sink e +viés explícito convergem todos em ppl 3,04 no OpenWebText2, e só o de viés explícito perde as massivas).

**Se o objetivo for servir quantizado agressivamente, a opção técnica melhor é K-bias** — vetor k* aprendível por cabeça com **v\* fixo em zero** — **[NA ESCALA, 60M]**: Sink₁ = 0,00%, loss 3,72 (idêntica ao baseline 3,73), **e sem ativações massivas**. Custo no Bee-350M (32 camadas × 5 kv heads × d_head 64): **10.240 params = 0,003%**. ⚠️ **Contra:** exige patch no `Qwen3Attention` (custom code), que é exatamente o que o projeto evitou ao escolher Qwen3 pelo QK-Norm nativo. Sensibilidade medida: se v\* deixa de ser zero e cresce, **o sink volta** para o 1º token.

**Três caminhos já falhados — não gastar experimento neles [NA ESCALA]:** softmax-off-by-one / "Zero Sink" (160M: ppl 29214 em 0+1024, **pior** que o vanilla; e em GPT-2 124M não elimina as massivas), dimensão extra de feature, e v' aditivo depois da atenção. Ajustar **weight decay** também não é alavanca: wd 0,0 já dá 15,20% (vs 18,18% em 0,1), e wd alto o bastante para derrubar o sink (2,0 → 6,13%) destrói o modelo junto (loss 3,73 → 4,23). **Trocar positional embedding também não:** NoPE 20,35% · Absolute 32,73% · Learnable 33,13% · ALiBi 20,78% · **Rotary 18,18%** — o RoPE que o Bee usa já é o menor sink da tabela.

### 3.9 Weight sharing bloco-a-bloco do MobileLLM — **[NA ESCALA, 125M e 350M]**, e é a lacuna mais gritante

É o **único trabalho da literatura deste lote medido nos dois degraus exatos do projeto**. O Bee já é fundo-e-fino (150M: 30×576, razão 19,2) e já usa GQA — metade da receita foi adotada por outro caminho. **O que nunca foi testado no Bee é o block-wise weight sharing** (repetir blocos sem somar parâmetro), que é justamente a peça que o MobileLLM isola.

⚠️ **O survey descreve a técnica em 4 linhas e não reporta uma única métrica** — nem acurácia, nem perplexidade, nem latência, nem ganho do sharing. E erra a citação **duas vezes**. **Ação concreta, custo US$ 0:** baixar arXiv:2402.14905 e extrair a tabela de ablação do weight sharing em 125M e 350M **antes** de desenhar o próximo degrau.

### 3.10 Itens de menor prioridade, registrados para não serem redescobertos

- **Vocabulário: não copiar o do Qwen** — **[NA ESCALA, 0,8B]**. O vocab de 248.320 é fixo em toda a família e custa **29,1%** dos params do Qwen3.5-0.8B (254,3M de 873,4M) contra **9,2%** no 27B. O Bee-350M gasta **8,9%** (30,7M de 345,4M) — a mesma fração de um modelo 80× maior. Comparação direta: com orçamento quase igual, o Bee-350M tem **314,6M** de params não-embedding contra **100,2M** do Gemma-3 270M — **3,14× mais músculo de fato**. Decisão já congelada, mas é a munição para resistir a vocab multilíngue grande no próximo degrau (262k × d_model 1536 num Bee-1B = 402M, 40% do modelo).
- **MQA em vez de GQA** — **[SEM NÚMERO para o custo]**. O Google vai a 1 KV head nos pequenos (Gemma-1 2B 8q/1kv; Gemma-3 1B e 270M 4q/1kv, head_dim 256 fixo e sem explicação em lugar nenhum). O Bee-350M usa 15q/5kv → cache 5× maior. Corta o KV-cache em 5× com custo de qualidade que **nenhum destes papers mede**. Não adotar por imitação.
- **Balanceamento sem loss auxiliar** — **[ZONA CINZA, até 3B]**, só se houver degrau MoE: o viés b_i entra **apenas** no `Topk`; o gating continua vindo do score **original** s_i,t. Somar o viés também no gating faz o balanceamento **distorcer a saída** em vez de redistribuir carga. Segundo detalhe silencioso do lote — erra sem dar erro.
- **LLM2LLM** (gerar exemplos difíceis a partir dos **erros** do próprio modelo) — **[SEM NÚMERO]**. É o complemento exato da lei nº 1 do projeto: rejection sampling só guarda o que o modelo **já acerta** (+5,07 pp em k=1 → +0,00 pp em k=128), enquanto gerar exemplo a partir do que ele **erra** é a única das técnicas de aumento com chance de mover o **teto**. Confiança baixa: a evidência do survey é zero.
- **FP8 na Blackwell** — **[SEM NÚMERO]** no survey; **[APOSTA, 671B]** no DeepSeek-V3 (erro relativo de loss <0,25% vs bf16 em ~1T tokens). O projeto **já mediu** que nesse regime promessas de software não se realizam: Liger deu **0%** na 5090; `torch.compile` deu **+17%** (a única que funcionou). Tratar como experimento de 40 passos, jamais como premissa.

---

## 4. Contradições entre os lotes — apontadas, não resolvidas por decreto

### 4.1 MoE em modelo pequeno: dois resultados medidos **abaixo** de 500M, com conclusões opostas

| fonte | escala | veredito |
|---|---|---|
| *Mixture of Parrots* (2410.19034) | 18M / 58M / 200M **ativos** | a params **totais** iguais, o **denso vence** em commonsense e matemática |
| σ-MoE (2310.10837) | 41M / 47M / 262M | a params iguais, o **MoE vence** (11,81 → 11,71) com 25% dos FLOPs |

**Reconciliação parcial (minha leitura, não a dos papers):** são duas coisas com o mesmo nome. σ-MoE é **parameter-matched com FLOPs menores** — não aumenta capacidade, redistribui. Mixture of Parrots ataca a proposta de **expandir a capacidade total** via experts. Além disso as métricas divergem: σ-MoE mede **perplexidade** (ganho de 0,1–0,5, pequeno); Mixture of Parrots mede **raciocínio e memorização** e encontra o trade-off (MoE ganha memorização, perde raciocínio). **A contradição é aparente no eixo "MoE sim/não" e real no eixo "MoE para quê".** Não escolho lado: registro que a pergunta certa não é "MoE em 345M?" e sim "MoE para economizar FLOPs ou para comprar capacidade?" — e que só a segunda foi refutada com solidez.

### 4.2 `attn_output_gate`: dois lotes leram o mesmo campo e discordam

- **Lote de arquitetura Qwen3.8:** o campo está no `config.json` (`attn_output_gate: true`, `output_gate_type: "swish"`), mas o `grep` no `modeling_qwen3_5.py` mostra que **nenhum dos dois é lido** — o gate é `sigmoid` **hard-coded e sempre ligado**, e `"swish"` é inerte.
- **Refutação adversarial:** `attn_output_gate` **nem aparece na assinatura documentada** do `Qwen3_5TextConfig` — pode estar sendo **engolido como kwarg**.

As duas leituras coincidem no risco prático (**não dá para ablacionar gate on/off por config**) mas divergem sobre se ele está **sempre ligado** ou **nunca lido**. **Isso é material:** se estiver engolido e a classe não tiver o gate, um gate pareado mediria outra coisa. **Não resolvido — resolver por leitura do fonte antes de qualquer experimento**, e a trava é a contagem de parâmetros (a q_proj deve dobrar).

### 4.3 Gated DeltaNet: os dois papers dão vereditos opostos em 1,3B

- **Paper do GDN (2412.06464), 1,3B/100B:** GDN 16,42 ppl Wiki vs Transformer++ 18,53 — GDN ganha.
- **Hybrid Linear Attention (2507.06457), 1,3B/100B:** Transformer 0,548 vs GDN 24:1 0,565 de média zero-shot — resultado próximo, com o híbrido acima.

**Não são comparáveis:** métricas diferentes (ppl vs média de acurácia), corpora diferentes, baselines diferentes. **Só o experimento de 340M é controlado na nossa escala**, e é ele que decide. Registro também um dado incômodo dentro do próprio 2507.06457: em modelagem de linguagem o **GDN é o único que fica melhor PURO** (0,487) do que híbrido — mas em recall o puro é o pior (0,256 vs 0,436 em 3:1). É trade-off, não erro.

E o próprio paper do GDN traz o número mais importante para um Bee agêntico: em recuperação do mundo real (1,3B), **GDN puro 30,6 vs Transformer++ 37,0** — o recorrente puro perde **6,4 pp**. Só o híbrido vira o jogo (GDN-H2 40,1). **Os dois papers concordam nisso por caminhos diferentes: se GDN entrar, entra híbrido.**

### 4.4 O abstract contra a própria tabela (MTP)

Abstract: *"no overhead in training time"*. Tabela S5 do mesmo paper: **1,07× a 1,22×**, com o pior overhead nos modelos pequenos. Vale o número medido. É um lembrete útil de que revisão por pares não impede que resumo e tabela se contradigam.

### 4.5 O survey contra si mesmo

§6.1 conclui que modelos maiores **alucinam menos**; §6.2 conclui que modelos maiores **enviesam mais**. Ambas **sem um único número**, e a primeira apoiada em benchmarks de alucinação **vision-language** aplicados a modelos de linguagem puros. Não dá para derivar nada — registro como sintoma de rigor, não como achado.

### 4.6 MTP existe em 0,8B, mas não como objetivo treinável

O `config.json` do Qwen3.5-0.8B traz `mtp_num_hidden_layers: 1`, e o checkpoint do 27B tem os pesos (`mtp.fc`, `mtp.pre_fc_norm_*`, 1 camada full-attn). Mas o `transformers` **ignora tudo** (`_keys_to_ignore_on_load_unexpected = [r'^mtp.*']`), a palavra "MTP" **não aparece uma vez** na doc do modelo, e os pesos são publicados em **repos separados** (`*-MTP-GGUF`), sempre citados no contexto de **decodificação especulativa** (vLLM/SGLang/llama.cpp). **Reconciliação:** a Qwen treina MTP com pipeline próprio, para inferência. Não é contradição com o veredito da §3.2 — é a confirmação de que MTP no HF, hoje, exigiria escrever cabeça e loss (custom code).

---

## 5. O que eu NÃO consegui verificar

Lista explícita, porque número de resumo ≠ número do paper:

1. **Nenhum PDF foi aberto por mim.** Sou o sintetizador; trabalho sobre resumos de leitura. Exceções verificadas verbatim: os `config.json` do Hugging Face.
2. **CAT-Q (2606.26650):** lido por sumarizador; duas leituras **inconsistentes entre si** (9,4% vs 10,41 pp) e uma frase auto-contraditória sobre quantização de ativações. Dígitos não confirmados.
3. **O blog atribuído ao Qwen3.8 renderiza o post do Qwen3-Next (2025/09/10).** Todas as justificativas de projeto (3:1, head_dim 128→256, RoPE nos primeiros 25%, zero-centered RMSNorm, output gating, MTP) e os números de treino de 15T tokens são do **Qwen3-Next-80B-A3B**, não do Qwen3.8-27B. Atribuí-los ao 27B seria inventar.
4. **Receita de treino do Qwen3.8-27B: [SEM NÚMERO].** Nem tokens, nem LR, nem estágios, nem GPU-horas.
5. **Gemma 1: [SEM NÚMERO] para todo hiperparâmetro** — LR, batch, otimizador, schedule, warmup, weight decay, clipping. E **nenhuma ablação de arquitetura** (razão de FFN, head_dim 256, MQA vs GQA, profundidade vs largura). Nunca citar "o Gemma usa LR X".
6. **Throughput do GDN:** só existe **gráfico** (Figura 3), sem tabela. Ler valor de eixo de figura é exatamente o erro de throughput que já custou três recomendações de hardware erradas a este projeto.
7. **Gloeckle:** acurácias absolutas de indução e de raciocínio algorítmico só aparecem em **figuras**; não há tabela.
8. **ProphetNet nunca reporta contagem de parâmetros.** Registrado como lacuna, não estimado — justamente porque escala é o eixo que decide.
9. **Loss-Free Balancing:** os valores de ppl/MaxVio da comparação contra loss auxiliar e expert-choice **não foram extraídos**.
10. **Clark et al. 2022** (o limiar em que o ganho de roteamento zera) — o PDF não decodificou. Fica só o achado qualitativo (o coeficiente decresce com N). **Não usar como argumento quantitativo.**
11. **Todos os 9 números das Tabelas 2 e 3 do survey** — sem citação, sem escala, sem benchmark. Descartados em bloco.
12. **`attn_output_gate`** — ver §4.2, não resolvido.
13. **σ-MoE em FFN gated (SwiGLU)** — não medido por ninguém. Seria pesquisa nossa.
14. **A folga mínima de ordenação das perdas de MTP em PT** — [SEM NÚMERO], teria de ser calibrada.

---

## 6. Veredito honesto

### Muda decisão (2 de ~14)

| fonte | o que muda | escala |
|---|---|---|
| **Hybrid Linear Attention (2507.06457)** | **Fecha** a questão "trocar atenção por Gated DeltaNet". Empate técnico (0,442 vs 0,444) na geometria e no volume quase exatos do Bee-350M. Economiza um pré-treino inteiro gasto na direção errada. | **[NA ESCALA, 340M/20B]** |
| **Gloeckle (2404.19737) + Zuhri (2508.19228) + KORMo** | **Fecha** a questão MTP. Negativo em 0,3B, 0,6B, 340M e 1B; cruzamento em 1,3B; custo **maior** no pequeno (+22%). O run congelado está do lado certo. | **[NA ESCALA, 300M–340M]** |

Ambas são **refutações**. O estudo economizou dinheiro; não abriu caminho novo.

### Muda o *procedimento*, não a arquitetura (3)

- **Sonda de ativações massivas + sink (§2.1)** — o único item que produz **número novo medido no Bee**, por **US$ 0**, e com previsão falsificável a partir do LR agressivo do projeto.
- **Disciplina de quantização (§2.2)** — três regras com número, uma armadilha específica (massivas ≠ outlier features), e um A/B de bpb que cabe numa tarde.
- **"Demons in the Detail" como lição, não como técnica (§2.5)** — quinto membro documentado da família *"estatística agregada na granularidade errada, nada dá erro"*. Vira linha de checklist.

### Interessante e não muda nada (o resto)

- **Qwen3.8 inteiro.** O título do lote prometia arquitetura nova; o diff mostra **zero diferenças de valor** contra o Qwen3.5. E do Qwen3.5, MoE e MTP não são treináveis de prateleira, o híbrido tem retorno **negativo** em `seq 2048` (o termo quadrático é só 16,7% do forward, e a camada DeltaNet do Qwen3.5-0.8B é ~14% **maior** em params que a de atenção cheia), e o único candidato defensável — o **gate headwise** — não tem número sub-1B.
- **CAT-Q.** ICML oral, curva contra nós, e a motivação (caber na memória) não existe: 0,69 GB já cabem.
- **MoE de capacidade.** Três números independentes contra.
- **O survey de SLM.** Índice de nomes. Nada mais.
- **A revisão PT-BR.** Rendeu **duas** coisas, nenhuma técnica: "não existe régua padrão de criatividade" e "0 de 41 autores brasileiros". Rendeu pouco e está dito.
- **A razão intermediate (§3.7).** Não muda decisão porque o run está congelado — mas **derruba uma afirmação** e expõe que **75% dos parâmetros do bloco** foram dimensionados por cópia de recipe, sem uma única medição. É o item que mais merece um gate pareado no próximo degrau.

### As três lacunas mais gritantes, todas de custo baixo

1. **MobileLLM (arXiv:2402.14905)** — o único trabalho medido em **125M e 350M**, os degraus exatos do projeto, e o survey não dá um número sobre ele. **Ler o primário. US$ 0.**
2. **Sonda de ativações do Bee-350M** quando o pré-treino terminar. **US$ 0.**
3. **Gate pareado do intermediate** (I=2560 vs I=2752, isoparamétrico, ≥2B tokens por braço) — a decisão de um quarto do modelo que hoje não tem número nenhum, nem nosso nem de terceiros.

> **A regra que este estudo confirma pela enésima vez:** de ~14 fontes de fronteira, **duas** mudaram uma decisão — e as duas mudaram por serem os **únicos experimentos controlados na escala do Bee**. Todo o resto ou mede modelos 5× a 500× maiores, ou não mede nada. *O que só foi validado em ≥7B é aposta, não receita* continua sendo o filtro mais rentável do projeto.
