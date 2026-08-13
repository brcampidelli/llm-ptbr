# BEE — O que ~60 papers de agosto/2026 mudam no 350M (e no 150M)

**Data:** 2026-08-13 · **Escopo:** decisão de gasto de US$ 300 · **Base:** 8 lotes de leitura + 4 afirmações submetidas a refutação adversarial · 13 agentes, 2,18M tokens, 240 chamadas de ferramenta

---

## 0. COMO LER ESTE DOCUMENTO (e onde ele é fraco)

**Ressalva de integridade — corrigida após o fato.** O sintetizador registrou que recebeu "6 lotes
legíveis de 8". A contagem real: **8 lotes lançados, 7 devolveram**; o lote **E (agentes-2)**
estourou o limite de tentativas do schema de saída e não chegou à síntese. O conteúdo dele foi
**recuperado do transcript** e está no **[Apêndice B](#apêndice-b--lote-e-recuperado)** — leia-o,
porque contém a única medição do estudo inteiro em **Qwen2.5-0.5B** e ela **contradiz** um item da
§2. Um oitavo lote entrou truncado na lista de descartes. Cobertura: **boa, não total.**

**Convenção de marcação, usada em toda linha:**

| Marca | Significado |
|---|---|
| **[NA ESCALA]** | testado em ≤ 500M — transfere com risco baixo |
| **[ACIMA]** | testado em 0,5B–3B — analogia, não resultado importado |
| **[APOSTA]** | só testado em ≥ 7B, ou só em API de fronteira, ou escala não declarada |
| **[DERIVADO]** | **eu** deduzi; nenhum paper testou isso nesta direção |
| **[VERIFICAR]** | número vem de resumo extraído, não do PDF — conferir antes de gastar |

**Contradições entre lotes estão apontadas, não resolvidas.** Onde não sei, digo que não sei.

**O resultado mais importante do estudo não é um paper — são as três refutações.** Duas delas derrubam premissas que já estavam guiando o gasto. Leia a §4 e a §3 antes de qualquer coisa.

---

## 1. O QUE MUDA NO BEE-350M

Ordenado por (ganho medido esperado ÷ risco). Os quatro primeiros custam ~US$ 0 e valem, somados, mais que tudo que vem depois.

---

### 1.1 — Auditar e deduplicar o corpus ANTES de gastar um dólar **[NA ESCALA]**

**O que fazer:** rodar MinHash/near-dup sobre os 22B tokens PT e reportar duas coisas — (a) a fração dos FLOPs que vem de documentos duplicados, (b) o **histograma da contagem de repetição**, não a taxa média.

**Paper:** arXiv:2606.24998 — *Internal Data Repetition Destroys Language Models*.

**Menor modelo testado:** **344M**, arquitetura estilo Qwen3. É o tamanho exato do Bee-350M. Não há extrapolação aqui.

**Número:** quando documentos repetidos consomem **10% do orçamento de FLOPs**, o pior cenário equivale a treinar sem repetição usando apenas **67% dos FLOPs** — ou seja, **33% da computação perdida**. O dano **não é monotônico**: tem **pico em contagens intermediárias** (documento repetido 3–10x machuca mais que repetido 1000x ou 2x).

**Custo:** US$ 0. CPU local, ~4–8 h.

**Como se mede que funcionou:** o histograma existe e a fração de FLOPs em documentos com contagem 2–20 é conhecida. Depois do dedup, o mesmo histograma re-rodado tem a massa intermediária eliminada. Retorno potencial: **até ~US$ 100 dos US$ 300**.

**Por que isso é o primeiro item:** web PT-BR é exatamente o perfil de repetição intermediária que o paper aponta como pior — portais republicando a mesma matéria, boilerplate jurídico, termos de uso. E é o **quarto membro da família que já custou 3 vezes ao projeto**: o dado some, nada reclama, a loss cai bonito.

---

### 1.2 — Guardas de falha silenciosa (as que existem + duas novas)

**Que já existem e continuam obrigatórias** (checklist de `bee-pretreino-licoes.md`): convenção de rótulos com dado REAL, cobertura de amostragem = 100%/época, exemplos sobreviventes ao truncamento no SFT.

**Nova guarda 1 — norma dos parâmetros treináveis [NA ESCALA]:**
**Paper:** arXiv:2607.25091 (Waterloo). **Menor modelo testado: Pythia-70M / SmolLM2-135M** — *abaixo* do Bee. **Número:** LoRA registrado silenciosamente como não-treinável em PEFT/TRL produz delta de recompensa **exatamente ZERO** e o treino roda inteiro sem um erro. Correção deles: fundir o adapter de SFT no base e anexar um adapter novo zero-init.
**Guarda:** comparar `||θ_treinável||` antes e depois do passo 1; **abortar** se for idêntica. ~5 linhas.

**Nova guarda 2 — contagem de época após dedup [DERIVADO]:** dedup muda o número de tokens únicos. Se o schedule está expresso em passos, a fração de época muda em silêncio e o decaimento cai no lugar errado. **Guarda:** logar tokens únicos, passos totais e épocas resultantes, e recomputar o schedule DEPOIS do dedup.

**Custo:** ~US$ 0.

---

### 1.3 — Filtrar por taxonomia, e escolher o corte pela regra das 2–4 épocas

**O que fazer:** anotar uma amostra do corpus PT em 3 eixos (nível educacional / profundidade de raciocínio / **evergreen vs datado**), destilar num classificador barato, pontuar os 22B inteiros. Depois **escolher o limiar de corte de modo que o corpus único resultante, repetido, caia entre 2 e 4 épocas no orçamento de tokens.**

**Papers:**
- arXiv:2606.07778 (*Taxonomy-Guided Recovery*) — filtro F8 retém **10,3% da faixa MÉDIA** do corpus, e esse dado **bate a faixa TOPO não filtrada** por +6,7% em raciocínio. Contra a mesma faixa média não filtrada: **+12,1% raciocínio, +2,0% conhecimento**. Pipeline de anotação: LLM grande anota 14M docs → destila num 0,5B → MLP de 73M sobre embeddings, 50x de throughput.
  ⚠️ **Escala dos modelos avaliados NÃO confirmada** — o leitor do lote reportou 404 no HTML; os "0,5B" e "73M" são os **anotadores**, não os modelos medidos. Trate os ganhos como **[VERIFICAR]**. O que está verificado é o custo e a arquitetura do pipeline de anotação, que roda na 5070.
- arXiv:2604.28075 (*Repetition over Diversity*) **[NA ESCALA]** — **350M (24 camadas, hidden 1024), ALEMÃO**, orçamento 100B tokens. Dense Core = **28B únicos curados repetidos ~3,6 épocas → média 39,24**. Baseline = **100B únicos, passagem única → 34,35**. **O corpus 3,6x MENOR ganhou por +4,89 pontos.** Ganho persiste em 7,2 épocas.
- arXiv:2305.16264 (Muennighoff et al., varredura até 9B params / 900B tokens) — **até 4 épocas** de dado repetido produzem mudança desprezível de loss frente a dado único, sob orçamento fixo.

**A regra [DERIVADO]:** combinando "≤4 épocas é quase de graça" com "densidade de qualidade bate volume em 350M", o ótimo é **maximizar a qualidade média sujeito a épocas ≤ 4**. Para 21,7B tokens processados, isso significa alvo de **5,4–10,9B tokens únicos** (retenção de 25–50% após dedup). Nenhum paper prescreve exatamente isso; é minha síntese de dois resultados.

**Custo:** US$ 0–20 de API (inferência free do build.nvidia.com, ToS permite) + ~1 dia de GPU local.

**Como se mede que funcionou:** o único teste honesto é um gate pareado de 1B tokens (corpus filtrado vs não filtrado, ~US$ 20). **Se não houver dinheiro para o gate**, o resultado alemão em 350M é a melhor evidência disponível na escala certa e a filtragem é a aposta com melhor razão evidência/custo do documento inteiro.

**⚠️ Contradição real, não resolvida:** arXiv:2605.19407 (*A Bitter Lesson for Data Filtering*) argumenta que **sem filtro vence** — mas coloca esse regime em **compute ALTO**. O Bee está no extremo oposto (350M / US$ 300). Os dois podem estar certos em regimes diferentes; não tenho o gráfico que localiza a fronteira. Registro como condição de contorno.

**Risco específico deste item:** o classificador é um modelo. Um limiar mal calibrado pode remover um domínio inteiro (todo o texto jurídico, toda a poesia) e **nada reporta isso**. **Guarda:** reportar a fração retida **POR FONTE/domínio**, nunca só o agregado.

---

### 1.4 — Trocar cosseno por schedule horizon-free (WSD) + EMA

**O que fazer:** warmup → fase estável longa → decaimento nos últimos ~20% dos passos. Mais média exponencial de pesos sobre os checkpoints **da fase de decaimento**.

**Papers:**
- arXiv:2602.02522 (IMU-1) **[NA ESCALA — modelo final 430M, ablações num proxy de 70M]** — WSD com fase estável e **20% de decaimento iguala o cosseno exatamente**. **EMA (β 0,8, últimos 10 checkpoints): +0,014 de média de benchmark**, custo zero de treino.
- arXiv:2602.03702 (*Anytime Pretraining*) **[NA ESCALA — 150M e 300M, exatamente as duas escalas do Bee, 1–32x Chinchilla]** — LR constante + média de pesos iguala o cosseno bem ajustado sem saber o horizonte. ⚠️ **Não consegui extrair o delta numérico.** Sem esse número, é direção, não medição.

**Três razões para adotar, em ordem de força:**

1. **Torna a decisão 21,7B vs 30B desnecessária EM ADVANCE.** Com teto de US$ 300 e histórico de 5 falhas silenciosas, um cosseno obriga a comprometer o horizonte no passo 1. Um schedule horizon-free deixa estender a fase estável se o dinheiro sobrar, e decair quando for a hora. **Este é o argumento decisivo, e ele é operacional, não de loss.**
2. **Torna os checkpoints intermediários mensuráveis.** A curva de bpb do 150M (1,021 / 0,947 / 0,920 / 0,897 / 0,870 / 0,845) **ACELERA para baixo**: as inclinações em L vs ln D são −0,045 (6→10B) e −0,0684 (10→21,7B). **Nenhum L = E + A·D^−α com E ≥ 0 e α > 0 produz aceleração** — lei de escala é convexa, desacelera. Isso é assinatura de decaimento de LR contaminando os checkpoints intermediários, não a lei de escala do dado. Com WSD, os checkpoints da fase estável são comparáveis entre si.
3. Se o run for interrompido, o modelo é utilizável.

**Custo:** US$ 0 para adotar. **Recomendo pular o gate** (US$ 20 economizados) — o downside é limitado pelo próprio IMU-1 ("20% de decaimento iguala o cosseno") e o upside operacional é grande.

**Como se mede:** (a) bpb final dentro do ruído do que o cosseno daria; (b) **os checkpoints intermediários deixam de mostrar inclinação acelerando** em L vs ln D. O teste (b) é o que converte a curva de extrapolação em medição.

**⚠️ [VERIFICAR] crítico antes de gastar:** o resumo do IMU-1 diz "fase estável a **55% do pico do cosseno**". Se a leitura correta for que o LR estável do WSD deve ser 55% do pico que o cosseno usaria, isso muda o LR por um fator de ~2 e vale US$ 218. **Ler a seção de schedule do PDF antes do run.** Na dúvida, usar a formulação padrão (estável = pico), que é prática estabelecida.

---

### 1.5 — QK-Norm **[NA ESCALA — ablação em proxy de 70M, abaixo do Bee]**

**Paper:** arXiv:2602.02522 (IMU-1). **Número:** −0,63% de loss sozinho. As quatro mudanças juntas (QK-norm, residual de valor normalizado, LayerNorm scaling, gating por cabeça) dão **−1,64%** — superaditivo, maior que a soma. Modelo final: 430M em 72B tokens, média de benchmark 0,574 contra 0,586 do SmolLM2-360M que usou **56x mais tokens**.

**Custo:** uma linha + ~US$ 1 de sanidade (100 passos com e sem, mesma semente).

**Como se mede:** loss no passo 100 menor no braço com QK-Norm; e o máximo |logit| de atenção logado ao longo do treino não explode. Se a loss for idêntica no passo 100, **a camada não está sendo aplicada** — família de bug conhecida.

**Recomendo adotar só o QK-Norm dos quatro.** Os outros três valem −0,38%, −0,36% e −0,05% isolados e cada um é uma superfície nova de bug silencioso. O ganho superaditivo é atraente, mas o projeto já pagou caro por mudanças que não davam erro.

---

### 1.6 — LR recalculado pela Step Law para N = 345M

O 150M usou 3,09e-3, derivado de η* = 1,79·N^−0,713·D^0,307 com N=151M e D=9,87B (o corpus da era do bug). Para N = 345,3M:

| D | η* |
|---|---|
| 21,7B | **2,18e-3** |
| 30B | 2,40e-3 |

**Usar ~2,2e-3.** Custo US$ 0. É a mesma lei já validada no projeto, só com o N certo. **Como se mede:** loss no passo 500 não diverge e não estagna; se divergir, cortar pela metade — mas isso é sintoma, não medição.

---

### 1.7 — Geometria: manter 32×960, ou gastar US$ 20 num gate

**A evidência está genuinamente dividida e eu não vou fingir que não está.** Razão d_model/camadas nos pontos que consigo citar:

| Modelo | Params | Razão d/L | Fonte |
|---|---|---|---|
| **Bee-150M (medido, funciona)** | 151,2M | **19,2** | próprio |
| SmolLM2-360M | 361,8M | 30,0 | referência do plano |
| **Plano Bee-350M** | 345,3M | **30,0** | — |
| Modelo alemão de dedup | ~350M | 42,7 | arXiv:2604.28075 |
| IMU-1 | 430M | 38,4 | arXiv:2602.02522 |
| LilMoo (hindi) | 670M | 54,9 | arXiv:2603.03508 |

O plano está no **extremo baixo** de tudo que foi medido nessa faixa. Mas o próprio Bee-150M, com razão ainda menor (19,2), **bateu o Tucano-160m usando 9x menos tokens** — o que é a evidência mais forte que existe *na escala do projeto* de que fino-e-profundo funciona aqui. E a tese do MobileLLM (sub-1B) é exatamente deep-and-thin.

**Recomendação:** **manter 32×960 se o dinheiro for apertado.** É a geometria exata do SmolLM2-360M, o modelo mais bem documentado nesse tamanho, e o precedente interno do 150M a sustenta.

**Se houver US$ 20 para um gate,** os braços limpos são:
- A: 32 camadas × 960, 15q/5kv, I=2560 (razão 30,0) — 345,3M
- B: 22 camadas × 1152, 18q/6kv, I=3072 (razão 52,4) — 348,4M

Mesma GQA 3:1, mesmo head_dim 64, mesmo tamanho. **⚠️ Ressalva metodológica séria: 1B tokens pode não separar geometrias** — modelos mais profundos costumam começar mais devagar e virar depois. Um gate de 1B pode dar a resposta errada com confiança. Se rodar, rode 2B por braço (US$ 40) ou não rode.

**Interação com o item 1.8:** o braço A é compatível com init por crescimento do 150M (30→32 camadas = duplicar 2); o braço B não é (exigiria podar). Se o gate de init vencer, a geometria já está decidida.

---

### 1.8 — Init crescendo o 150M em vez de aleatório **[DERIVADO — nenhum paper testa esta direção]**

**Honestidade primeiro:** arXiv:2605.07783 (CBD) constrói modelos de 138M–537M por destilação em cadeia, e o **veredito do lote foi NÃO ADOTAR** — a manchete é contabilidade enganosa (herda o pré-treino inteiro do GPT-2/Pythia e compara contra um modelo do zero com 10B tokens), os absolutos vivem numa faixa onde os benchmarks não discriminam (MMLU 31,00 com acaso em 25; BoolQ 76,80 abaixo do que a classe majoritária já entrega em ~62), **e a direção é grande→pequeno**. O Bee precisa de pequeno→grande.

**O que sobrevive é uma pergunta, não uma técnica:** se inicialização a partir de um modelo aparentado vale bilhões de tokens de pré-treino, vale rodar um gate próprio — inicializar o 350M replicando camadas e fazendo zero-padding de largura a partir do Bee-150M (bpb 0,844, mesmo tokenizador, mesma língua, mesma família Llama), contra init aleatório.

**Custo escalonado:** US$ 2 (dois runs de 40 passos, só para a loss no passo zero) → se e somente se a loss no passo zero for claramente menor, estender para 1B tokens por braço (+US$ 20).

**Como se mede:** loss no passo 0 e bpb no passo de 1B tokens. **Matar se não for melhor** — este item existe para falhar barato.

**Risco:** crescer 576→960 de largura é uma operação não-trivial cujo bug é silencioso (o modelo treina bem, só pior). Exige o baseline pareado com init aleatório na MESMA ordem de dados.

---

### 1.9 — Composição do SFT agêntico (aplica ao 350M e ao 150M) **[ACIMA — Qwen3-0.6B]**

Detalhado na §2.1. Resumo: fatia explícita de irrelevância + distratores semânticos + **sem CoT** + validação estrutural determinística antes de qualquer juiz.

---

### 1.10 — NorMuon **[APOSTA quanto à escala]**

**Paper:** IMU-1. **Número:** +2,88% relativo sobre AdamW; +0,97% com cautious weight decay (total 3,85%). LR separado para params 2D (0,0235) e 1D (0,007).

**Por que é APOSTA:** o resumo lista o NorMuon no mesmo parágrafo das ablações de arquitetura feitas no proxy de 70M, mas **não está claro se o ganho do otimizador foi medido no proxy ou só no run de 430M**. Não posso afirmar que foi validado abaixo de 500M.

**Recomendação:** **não no primeiro run.** É o maior ganho isolado do IMU-1 e a maior mudança de código, com toda uma classe nova de erro numérico silencioso. Só depois que o run com AdamW funcionar, e com gate pareado próprio.

---

## 2. O QUE APLICAR AGORA NO BEE-150M (sem re-pré-treinar)

Ordenado por custo crescente. Os itens 2.2 a 2.6 custam **US$ 0** e são só inferência ou script.

### 2.1 — Regerar o dataset agêntico com irrelevância + distratores, sem CoT **[ACIMA — Qwen3-0.6B]**

**Paper:** arXiv:2607.29250 — *Data Turnstile* (Amazon). **Menor modelo: Qwen3-0.6B** (4x o Bee-150M, 1,7x o 350M). Full fine-tune, AdamW lr 5e-5, warmup 50 passos, batch efetivo 64.

**Quatro fatos medidos:**
1. SFT em dado open-source cru **derrubou** a detecção de irrelevância de **81,0% → 35,7%** e o overall de 67,4% → 55,1%. **O SFT piorou o modelo.**
2. Com a metodologia Turnstile (mesmas APIs, só a geração muda): overall **70,4%** (+15,3pp só de metodologia), irrelevância recuperada para **77,5%**. Melhor config 75,9% vs base 67,4%.
3. **CoT PIORA nesta escala:** sem-pensar **75,9%** vs com-pensar 72,8% (em APIs live: 70,5% vs 65,8%).
4. Validação **estrutural determinística** pega 87% dos erros de geração; juiz LLM só os 13% restantes.
5. tau2-bench Telecom: 0,6B de 3,5% → **24,6%** (7x); 1,7B de 6,6% → 31,1%, batendo Qwen2.5-32B-Instruct (27,4%).

**Por que isto é o item de maior confiança do estudo inteiro:** o over-calling de 21,5% do Bee é provavelmente **o mesmo defeito de dataset, não de capacidade**. Se as sementes agênticas sempre terminam em chamada, o Bee nunca viu um exemplo onde a resposta certa é não chamar.

**Custo:** ~US$ 0 de GPU (professor gratuito no build.nvidia.com + SFT local na 5070). ~2–3 dias.

**Como se mede que funcionou:** over-calling **com a regra determinística DESLIGADA**, antes e depois. Hoje: 21,5% cru / 13,8% com regra. **E, na mesma tabela, a taxa de chamada perdida** — o projeto já mediu que o `verifier.py` matava 7 chamadas boas para pegar 4 over-calls. **Nunca reportar um lado só.**

**Cuidado obrigatório:** Qwen3-0.6B vem de ~36T tokens multilíngues com código. Os **absolutos não transferem**. O que transfere são os fatos sobre a composição do dado, que independem do modelo.

---

### 2.2 — Estender o k do pass@k. US$ 0.

**Este é o teste que pode matar sozinho a premissa mais cara do projeto.**

**Paper:** arXiv:2407.21787 (*Large Language Monkeys*, Stanford). **Menor modelo testado: Pythia-70M**, varredura de 70M a 70B — **inclui e ultrapassa por baixo a escala do Bee.** **Número:** cobertura cresce log-linear por **quatro ordens de magnitude, sem saturação**. **Pythia-160M no MATH: pass@1 = 0,27% → pass@10.000 = 57%.** Gemma-2B no CodeContests: 0,02% → 7,1% (300x).

**O que fazer:** rodar pass@k em k = 1, 4, 16, 64, 256 no Bee-150M-SFT e plotar em log. Se a curva ainda subir em k=256, **72,9% não é teto de nada — é o orçamento de amostragem**, e a palavra "teto" sai do vocabulário do projeto.

**Custo:** ~2–4 h de inferência na 5070. **3 sementes**, não uma.

---

### 2.3 — Auditar o avaliador à mão. US$ 0.

Pegar os itens que **nenhuma** das 16 amostras resolveu e auditar manualmente ~50: quantos são impossíveis por construção (ferramenta ausente do catálogo, ground truth errado, prompt ambíguo, verificador estrito demais)?

**Precedente do próprio projeto:** avaliador de mundo fechado produziu 23,5% quando o real era 57,6%. Se 20–25% do conjunto for insolúvel, **72,9% é o teto do BENCHMARK** — e nenhum tamanho de modelo move teto de benchmark.

---

### 2.4 — Diff POR PROBLEMA entre pré e pós-autoaprendizado. US$ 0.

**Paper:** arXiv:2608.11829. **Números:** Qwen3 1,7B (professor 4B) em AIME2024: pass@1 4,2% → 12,0% (quase 3x) **MAS pass@1024 70,0% → 53,3%** (queda de 16,7pp). Skywork 1,5B: pass@1 29,9 → 36,4, pass@1024 86,7 → 86,7. **Nos três setups a fração "esquecida" supera a "aprendida".**

**⚠️ Contradição entre lotes:** o Lote B reporta o menor student em **1,5B** com esses números; o Lote C afirma que a escala **não é especificada** no material acessível. O Lote B é mais específico e internamente consistente; me apoio nele, mas registro o desacordo.

**O que fazer:** os números de pass@16 do Bee são **agregados**. Contar, item a item, quantos problemas o modelo resolvia antes da colheita e não resolve mais. Os dados já estão em disco. Se a fração esquecida > aprendida, o autoaprendizado cobra um preço que o agregado esconde, e a próxima colheita deve misturar dado do modelo base.

---

### 2.5 — Varrer temperatura e sampler. US$ 0.

**Papers:** arXiv:2510.02611 — em k pequeno as temperaturas empatam, em k grande abrem. arXiv:2510.14901 (*Reasoning with Sampling*) — power sampling MCMC sobre as próprias verossimilhanças do modelo **base** iguala/supera ganhos de RL **sem treino, sem verificador e sem colapsar pass@k**.

Se o 72,9% se mover mais que o ruído só mudando o sampler, a atribuição a capacidade cai na hora. E o power sampling é uma alternativa gratuita ao RL, que na próxima linha está desaconselhado.

---

### 2.6 — Portão PPL<20 antes de qualquer RL **[NA ESCALA — 70M a 500M]**

**Paper:** arXiv:2607.25091. 15 configurações (5 modelos × 3 corpora), 16 GPU-horas totais.

**NA ESCALA DO BEE O RESULTADO É NULO:** SmolLM2-135M teve delta de recompensa +0,226 / −0,194 / +0,015 e **win rate 53,0% / 47,1% / 50,3%** — nada. Ganhos significativos só em Pythia-410M (+1,355, win 59,9%, p<0,001) e SmolLM2-360M (+0,724, win 59,7%, p<0,001), e só no corpus mais fácil. **REGRESSÃO significativa** em Pythia-410M no Wikitext (−1,043) — cuja PPL de SFT era 25,4, acima do limiar. **Todos os ganhos acima de +0,2 ocorreram com PPL<20; nenhum acima de 20.**

**Ação:** medir a PPL do checkpoint de SFT na validação PT. Se >20, o paper prevê ganho nulo ou negativo e a recomendação explícita deles é gastar em qualidade de dado de SFT. **Custo: ~1 h de 5070.**

---

### 2.7 — Decompor o over-calling em três contadores **[APOSTA — menor modelo 32B]**

**Paper:** arXiv:2608.12133 (GUIDE). Decompõe erro em **alucinação 3,2% / duplicação 3,0% / contradição 2,9%** em vez de um agregado. Menor modelo: Qwen2.5-VL-32B — 212x o Bee. **A arquitetura de 6 agentes é irrelevante aqui; o que se importa é a decomposição da métrica, que é livre de escala.**

Hoje 13,8% agregado não diz o que consertar. Separar em: (i) chamou ferramenta fora do registry — conserta com gramática/decoder restrito; (ii) chamou a mesma ferramenta duas vezes no turno — conserta com política determinística; (iii) chamou ferramenta que contradiz o turno anterior — só visível no multi-turno, conserta no adapter. **~2–4 h.**

---

### 2.8 — Personas roteirizadas + gates numéricos declarados ANTES **[APOSTA — tamanho de modelo não reportado]**

**Paper:** arXiv:2608.12292. Gates: G1 (nenhuma solução revelada) 100%, G3 (conformidade com teto) 100% com gate ≥95%, G2 (revisão insincera) 0% com gate ≤5%. **Menos de US$ 1 por loop completo de avaliação.** O paper **não declara tamanho de modelo nenhum** — é a fraqueza decisiva dele.

O que vale importar não é o método, é a **disciplina**: script fixo e determinístico (tira o juiz LLM do caminho crítico) e **limiar numérico escrito antes de medir**. Isso ataca diretamente a lição do critério de veredito multiplicativo que declarou "sem cauda" havendo cauda. **~1 dia de engenharia de avaliação, US$ 0 de GPU.**

---

### 2.9 — SOP textual fixo no prompt agêntico **[APOSTA — só APIs de fronteira]**

**Paper:** arXiv:2608.10494 (GeoForge). A ablação é o que interessa, partindo de 52,23%: **+SOP sozinho 67,02 (+14,79pp)** · **+Experiências 70,21 (+17,98pp)** · **+Grafo 52,66 (+0,43pp — NADA)** · tudo junto 74,33.
**Nenhum modelo aberto, nenhum modelo pequeno.** Só GPT-5, GPT-4o, Gemini-2.5-Flash, DeepSeek-V3.1, Qwen3-Max.

**Converge com o que o Bee já mediu sozinho:** adapter LoRA de 24 MB levou ancoragem de 5,9 → 91,8% com backbone intacto, enquanto o full FT do mesmo dado custou −5,9pp de execução single-turn. Conhecimento fora dos pesos ganha quando a capacidade é disputada.

**Dois alertas:** (a) o ganho vem do **texto**, não do grafo — **não construir infra de grafo/recuperação**; (b) o prompt agêntico já ocupa **1.096–1.191 de 2.048 tokens**, e estourar isso foi exatamente o que descartou 100% dos exemplos agênticos em silêncio. Qualquer SOP injetado vem com contagem de tokens e a guarda de sobreviventes ligada.

**Custo:** ~2–4 h. Falha barato: se não mover execução (65,9%) nem over-calling em uma tarde, descarta.

---

### 2.10 — Estratificar por dificuldade e cortar a faixa mais difícil do autoaprendizado **[ACIMA — 1,5B e 3B]**

**Paper:** arXiv:2604.06298. Treinar GRPO só na faixa de baixa dificuldade **iguala o dataset completo em TODAS as faixas usando ~45% dos passos**. Testado em 1,5B e 3B — 4x a 20x o Bee-150M. Não extrapolo; trato como convergência.

É uma **medição independente**, com outro método (GRPO vs rejection sampling), outra língua e outra escala, chegando à mesma lei que o Bee mediu sozinho. Duas medições independentes concordando aumenta a confiança de que isso é propriedade do **regime**, não artefato do nosso aparato.

**Ação:** estratificar as amostras pela fração de tentativas certas e descartar a faixa mais difícil. Previsão: mesmo resultado com ~metade dos passos. **Custo negativo** (economiza compute) e falseia de graça a transferência da lei para 151M.

**⚠️ Contradição interna ao Lote A, apontada e não resolvida:** o mesmo lote recomenda **descartar** a faixa difícil (2604.06298) **e** reciclar exatamente essas falhas como supervisão diagnóstica via professor externo (arXiv:2606.04466 — Qwen2.5-0.5B: base 39,38 → GRPO puro 44,05 → método 49,69; Llama3.2-1B 16,22 → 48,53; 4× RTX 4090). **Minha leitura, que é minha e não dos papers:** não são incompatíveis se os pipelines forem separados — descartar do sinal de RL/rejection (onde dão recompensa zero e custam passos), e colher para SFT assistido por professor (onde viram supervisão nova). Se essa leitura estiver errada, os dois se anulam.

---

### 2.11 — Medir bpb quantizado antes de publicar qualquer versão quantizada **[APOSTA — 7–8B]**

**Paper:** arXiv:2603.18037. **Número:** Qwen2.5 (GQA) perdeu **−0,280** sob Q4_K_M, enquanto arquiteturas Llama-3 **melhoraram**. Testado só em 7–8B com QLoRA — 20x a 50x o Bee.

O Bee é GQA 9q/3kv. Se um dia quantizarmos para a 5070 ou CPU, este paper sugere que GQA pode ser justamente a arquitetura que sofre — o oposto da intuição. **Medir bpb em fp16 vs Q8 vs Q4_K_M antes de publicar.** Custo ~US$ 0, risco de não testar é publicar um artefato pior que o medido.

---

## 3. O QUE NÃO FAZER

**3.1 — NÃO expandir o corpus.** Ver §4.2 e a refutação completa. Resumo: 30B/21,7B = 1,38 época, e ≤4 épocas é quase de graça (arXiv:2305.16264); os 8,3B marginais em PT-BR são por construção os piores 8,3B; e em **350M alemão** o corpus 3,6x menor curado bateu o 3,6x maior por +4,89 pontos (arXiv:2604.28075). Raspar mais web PT **aumenta** near-dup, que custa até 33% dos FLOPs em 344M.

**3.2 — NÃO usar "a curva ainda descia no fim" como argumento** até separar o decaimento de LR da lei de escala. A curva **acelera para baixo**, o que nenhuma lei de escala convexa produz. Extrapolar essa inclinação para 30B **superestima** o ganho.

**3.3 — NÃO gastar em RL/PPO/GRPO no 150M. [NA ESCALA]** SmolLM2-135M: win rate 53,0% / 47,1% / 50,3%, delta essencialmente zero. Testado exatamente nesta escala, resultado nulo (arXiv:2607.25091). Corolário: RL só vira opção real no 350M, e ainda assim condicionado a PPL<20.

**3.4 — NÃO adotar CBD (arXiv:2605.07783).** Manchete inflada (herda o pré-treino do GPT-2/Pythia e compara contra 10B do zero), benchmarks no acaso (MMLU 31,00 com acaso 25), direção errada (grande→pequeno), e o único mecanismo que resolveria o descasamento de vocabulário exigiria uma âncora de ~700M já no vocab PT de 32k — que não existe e custaria mais que os US$ 300.

**3.5 — NÃO otimizar o roteador determinístico.** arXiv:2608.12123: roteamento residente na GPU custa 258–309 µs, round-trip ao host 467–625 µs. **O pior caso é 0,63 ms por transição**, ordens de magnitude abaixo de um forward do Bee. O teto de ganho é sub-milissegundo. Isto é uma decisão de **não-fazer**, e ela vale por isso.

**3.6 — NÃO fazer full fine-tune para adicionar competência.** Medição própria: −5,9pp de execução single-turn pelo multi-turno. Confirmação externa: EvoRIC (arXiv:2608.06789, Llama-3.2-3B-Instruct, **[ACIMA]**) mede L1→L2 = +11,52% e **L2→L3 = +1,20%** — atualização localizada satura em 2 camadas. E arXiv:2603.01293 dá o mecanismo ("SFT grande demais dilui o sinal do pré-treino"), sem números transferíveis.

**3.7 — NÃO construir infra de grafo/recuperação.** Ablação do GeoForge: grafo sozinho **+0,43pp**. O ganho está no texto de procedimento.

**3.8 — NÃO colocar código no corpus nem no tokenizador.** arXiv:2608.09068: **DeepSeek-Coder-1.3B tirou 2,15/5** em geração algorítmica estruturada — o pior de todos os avaliados, sendo 3,8x o Bee-350M **e** especializado em código. Este é o número que fecha a discussão.

**3.9 — NÃO expandir para trajetórias longas com atribuição de crédito.** arXiv:2608.06909: mesmo com leave-one-out (caro), **Hit@1 de 0,325 a 0,714**. Problema não resolvido em modelo nenhum, de qualquer tamanho. O rejection sampling do Bee funciona porque o crédito é trivial (a chamada cumpriu ou não). O adapter multi-turno deve continuar sendo **ancoragem de contexto**, não planejamento de N passos.

**3.10 — NÃO usar CoT no SFT agêntico.** 75,9% sem-pensar vs 72,8% com-pensar em 0,6B. E o Bee tem 2048 tokens de janela com 1.100+ já ocupados.

**3.11 — NÃO priorizar quantização da cabeça (SoftWater, arXiv:2608.12026).** A premissa do paper é cabeça de 15–30% dos parâmetros. A cabeça do Bee-150M é 32000×576 = 18,4M de 151,2M = **12,2%**; a do 350M é 30,7M de 345M = **8,9%**. Estamos **abaixo** da faixa onde eles alegam retorno — justamente porque o vocab é pequeno. Menor modelo testado: Llama-3.2-1B **[ACIMA]**.

**3.12 — NÃO fazer merge de adapters.** arXiv:2608.00042: merge (Dark ER, TA-LoRA) **aumentou** a taxa de sucesso adversarial em +0,171 e +0,155. O Bee faz hot-swap. Continuar assim.

**3.13 — NÃO mexer no vocabulário de 32k. [NA ESCALA — 100M]** arXiv:2608.11361 treinou 100M do zero com 6 vocabulários: bpb **1,368 (8k) / 1,344 (16k) / 1,347 (32k) / 1,346 (65k) / 1,355 (131k) / 1,355 (262k)** — spread <2%, sem tendência monotônica. Os autores afirmam explicitamente que **abaixo de 300M a qualidade é plana**. A 1,3–2,3B o ótimo desloca para 65k, com ganho de **0,9%** — muito abaixo do custo de refazer tokenizador + pré-treino. E o vocab ótimo de **inferência** varia 16x com o batch: **32k em batch 1**, 524k em batch ≥64. Se o Bee é servido local (batch 1), **32k já é o ótimo de inferência pela curva deles**. Ressalvas: inglês, run de 100M com apenas 50M tokens, e a faixa 300–500M **não foi testada**.

---

## 4. A RECEITA DO BEE-350M

### 4.1 — Parâmetros

| Parâmetro | Valor | Origem |
|---|---|---|
| n_layers | **32** | SmolLM2-360M; ver §1.7 (evidência dividida) |
| d_model | **960** | idem |
| heads | **15q / 5kv**, head_dim 64 (GQA 3:1) | mantém a razão do 150M |
| intermediate (SwiGLU) | **2560** (2,67× d_model) | SmolLM2-360M — **desvio não medido:** o 150M usa 3,556× |
| tied embeddings | **sim** | conferido pela contagem de params do 150M |
| seq_len | **2048** | igual ao 150M — encurtar repete o bug de truncamento do SFT |
| vocab | **32.000 PT (o mesmo)** | arXiv:2608.11361 |
| **total** | **345,3M** (314,6M sem embedding) | conta |
| norm / pos / act | RMSNorm pré-norm · RoPE · SwiGLU | inalterado |
| **QK-Norm** | **ligado** | IMU-1, ablação a 70M |
| otimizador | AdamW β=(0,9; 0,95), wd 0,1, clip 1,0 | **default, sem medição** |
| precisão | **bf16 mixed** | default — a ressalva de fp32 do arXiv:2607.25091 é do **laço de PPO**, não do pré-treino. Não generalizar. |
| **LR pico** | **2,2e-3** | Step Law, N=345M, D=21,7B |
| schedule | **WSD**: warmup 1.000 passos → estável → decaimento nos últimos 20% | IMU-1 + Anytime **[VERIFICAR o "55%"]** |
| batch global | **1.048.576 tokens** (512×2048) | **default** — validar por throughput em regime (passo ≥20, 3 leituras coincidentes) |
| passos | ~20.700 para 21,7B | conta |
| **tokens processados** | **21,7B**, extensível a 26–30B sem replanejar | §4.2 |
| **corpus único alvo** | **5,4–10,9B** após dedup+filtro (2–4 épocas) | regra **[DERIVADO]** de 2305.16264 + 2604.28075 |
| EMA | β 0,8 sobre os ~10 últimos checkpoints **da fase de decaimento** | IMU-1 |
| mistura | **100% PT** | decisão do projeto — mas ver §4.3 |

**Alternativa registrada, não recomendada por falta de evidência:** reinvestir a economia do vocab menor no MLP (I=2752 → 363M, +5% de custo), replicando o que o 150M fez em relação ao SmolLM2-135M (que usa I=1536/2,67× enquanto o Bee usa 2048/3,556×). **Não sabemos se isso rende mais que 5% a mais de tokens.**

### 4.2 — O VEREDITO SOBRE 21,7B vs 30B

**A pergunta está mal-posta, e a resposta certa remove a necessidade de respondê-la.**

**Contas, para conferência:**
- 6ND com N=345,3M, D=21,7B → 4,496e19 FLOPs ÷ 5,67e13 FLOP/s = **220,3 h = US$ 218**
- D=30B → 6,215e19 ÷ 5,67e13 = **304,5 h = US$ 301**
- Por 1B tokens: **10,15 h = US$ 10**
- ⚠️ 5,67e13 foi medido no **151M**. Provavelmente é piso para o 345M. **Medir em regime antes de comprometer.**

**Fato 1 — o consequente não segue.** Para processar 30B tokens o Bee **não precisa de corpus novo**: 30/21,7 = **1,38 época**, e até **4 épocas** de dado repetido produzem mudança desprezível de loss sob orçamento fixo (arXiv:2305.16264, varredura até 9B params / 900B tokens). A ação embutida na pergunta (expandir o corpus) é dispensável para atingir o número que ela mesma propõe.

**Fato 2 — expandir é medidamente pior em 350M.** arXiv:2604.28075, **350M, alemão**: 28B únicos curados repetidos 3,6 épocas → **39,24**; 100B únicos passagem única → **34,35**. Os autores afirmam que incluir tokens web de baixo sinal **dilui a densidade de informação de um orçamento fixo**. Ressalva honesta: é alemão, orçamento 100B, e o eixo comparado é filtragem, não "mesmo dado +38%".

**Fato 3 — 86x já é 4,3× além do ótimo.** Chinchilla para 6,215e19 FLOPs dá N≈720M com D≈14,4B. A 345M/30B estamos a 86,9 tok/param contra 20 do ótimo. Para 21,7B: 62,8 tok/param = 3,1× além. **Os dois pontos já são sobretreino deliberado** — o que é a decisão *correta* para um modelo que será servido localmente muitas vezes (Chinchilla otimiza compute de treino, não custo de inferência). Mas o retorno marginal de ir de 3,1× para 4,3× de sobretreino é **a parte mais plana da curva**.

**Fato 4 — a magnitude honesta.** Com expoente de dado tipo Chinchilla (β≈0,28), 21,7→30B encolhe o termo redutível em **8,7%**; com termo redutível de 0,15–0,25 bpb, isso é **~0,013–0,022 bpb (~1,5–2,5%)** por **+38% de custo**. É positivo. Não é falso. É pequeno.

**VEREDITO:**

> **Orçar o run principal em 21,7B tokens processados (~US$ 218), a partir do corpus DEDUPLICADO e FILTRADO, com schedule WSD, e reservar ~US$ 60–80.**
>
> **Se o run terminar limpo e a reserva estiver intacta, estender a fase estável com o dinheiro que sobrou até 26–30B e só então decair.** O schedule horizon-free existe exatamente para que essa decisão não precise ser tomada no passo 1.

**Por que a reserva e não os tokens:** o projeto tem **cinco falhas silenciosas documentadas** que só apareceram depois. A probabilidade de precisar reiniciar não é pequena, e o valor esperado de ter US$ 80 para reiniciar supera 1,5–2,5% de bpb. Isso não é conservadorismo — é a leitura direta do histórico do próprio projeto.

**Orçamento de gates recomendado (US$ 3, escalonável):**

| Gate | Custo | Quando |
|---|---|---|
| Auditoria de dedup + histograma | US$ 0 | **primeiro, sempre** |
| Guardas (rótulos, cobertura, norma, épocas) | US$ 0 | antes do passo 1 |
| Sanidade QK-Norm (100 passos, 2 braços) | ~US$ 1 | antes do run |
| Init por crescimento — só loss no passo zero | ~US$ 2 | antes do run |
| Init por crescimento — 1B tokens | +US$ 20 | **só se o passo zero vencer** |
| Geometria (2 braços × 2B tokens) | US$ 40 | **opcional** — 1B pode enganar |
| Filtragem (corpus filtrado vs não, 1B × 2) | US$ 20 | opcional, alto valor |

### 4.3 — Sobre "o Bee continua 100% PT": o argumento caiu, a decisão pode ficar

A decisão está registrada como não-questionável, e eu não a estou questionando. Mas o **motivo** registrado — "trocar o tokenizador exige pré-treino do zero" — **não sustenta a decisão**, e isso precisa constar no repositório.

**LilMoo (arXiv:2603.03508, 670M hindi do zero)** mediu **+14,3% de NPM** ao adicionar inglês curado (monolíngue puro v0.1 NPM 8,70 → v0.2 com inglês 9,94), **passando o inglês pelo tokenizador hindi, sem trocar nada**. O tokenizador do Bee já faz 0,3295 tok/byte em inglês — 51% pior que em PT, mas funcional.

**Mas há um confundidor sério que ninguém do estudo levantou:** se os benchmarks do NPM forem traduções de benchmarks ingleses, adicionar inglês melhora o score trivialmente. E o único benchmark onde o **monolíngue puro venceu** foi o **Global PIQA** — justamente o mais culturalmente aterrado. Minha leitura, que é minha: **o +14,3% pode ser em parte artefato de benchmark.**

**Recomendação:** manter 100% PT para o 350M, **por outro motivo** (foco, identidade do projeto, e o fato de que a métrica primária do Bee é bpb em PT, que 10% de inglês quase certamente piora). Registrar que o argumento do tokenizador está morto. Se um dia houver US$ 20 para o gate, ele só é válido com métrica **PT-nativa** (bpb em PT retido + execução agêntica), nunca com benchmark traduzido.

---

## 5. RISCOS

### 5.1 — Falhas silenciosas já conhecidas (guardas obrigatórias, sem exceção)

| # | Falha | Guarda | Custo já pago |
|---|---|---|---|
| 1 | Deslocamento duplo de rótulos | assert `loss` vs CE manual **com dado REAL**, aborta | 2 semanas, ~US$ 34 |
| 2 | Amostragem com reposição | cobertura reportada = 100%/época | 37% do corpus |
| 3 | `max_seq_len` curto no SFT | nº sobreviventes == nº carregados, aborta se >1% | 100% do agêntico |
| 4 | Avaliador de mundo fechado | auditoria manual dos nunca-resolvidos | 23,5% vs 57,6% real |
| 5 | Critério de veredito multiplicativo | limiar numérico declarado ANTES de medir | conclusão retirada |

### 5.2 — Riscos NOVOS que este plano introduz

**R1 — Dedup agressivo demais.** Remove texto legitimamente distinto e **muda a contagem de épocas em silêncio**. *Guarda:* logar tokens únicos + épocas resultantes; recomputar o schedule DEPOIS do dedup.

**R2 — Filtro por taxonomia apaga um domínio inteiro.** O classificador é um modelo; um limiar mal calibrado pode zerar todo o texto jurídico ou toda a poesia e **nada reporta**. *Guarda:* fração retida **por fonte/domínio**, nunca só o agregado.

**R3 — Init por crescimento com bug.** O modelo treina bem, só pior. *Guarda:* baseline pareado com init aleatório, mesma ordem de dados, mesma semente; matar se não vencer.

**R4 — QK-Norm no lugar errado.** Uma norma mal colocada não dá erro. *Guarda:* loss no passo 100 tem de diferir do braço sem QK-Norm. Se for idêntica, **a camada não está sendo aplicada**.

**R5 — Schedule WSD estendido.** Se o run for estendido com a reserva, a fração de decaimento tem de ser recomputada. Um decaimento que começa tarde ou cedo demais custa bpb em silêncio. *Guarda:* a fase de decaimento é sempre definida como os últimos 20% dos passos **efetivamente planejados no momento em que ela começa**.

**R6 — EMA sobre regimes de LR diferentes é lixo.** Média de checkpoints da fase estável com checkpoints da fase de decaimento não significa nada. *Guarda:* EMA **só dentro da fase de decaimento**.

**R7 — LR errado por 2×.** O "55% do pico" do IMU-1 é leitura de resumo, não do PDF. *Guarda:* **[VERIFICAR]** antes do run; na dúvida, WSD padrão (estável = pico).

**R8 — Fatia de irrelevância criando under-calling.** O espelho do problema atual. O projeto já mediu que o `verifier.py` matava 7 chamadas boas para pegar 4 over-calls — **saldo −4 por semanas, porque só se media o ganho**. *Guarda:* over-call e chamada-perdida **sempre na mesma tabela**.

**R9 — Ler pass@k de uma corrida só.** *Guarda:* 3 sementes.

**R10 — A reserva ser gasta em "só mais um pouco de token".** É um risco de disciplina, não técnico, e é o mais provável de todos. *Guarda:* a reserva só se libera com o run principal **terminado e avaliado**.

**R11 — Se algum dia rodar RL: bf16 no laço de PPO.** arXiv:2607.25091 **[NA ESCALA]**: a razão de importância exp(log πθ − log π_ref) sofre cancelamento catastrófico em modelos **<200M** e passa de **1e6** nos primeiros passos. *Correção:* **fp32 em TODO o laço** (policy, referência, value head, reward model), whitening de recompensa com clip 3σ, pular mini-batch se a razão média >5, rollback em NaN/Inf.

### 5.3 — Um risco que NÃO existe (e vale registrar)

arXiv:2608.12273 (*Convergent Detour Hijacking*) sequestra agentes com **78–89% de sucesso em 6 modelos de fronteira**, inflando tokens em **+40% a +107%**, explorando a seleção de skill feita pelo LLM a partir de metadados publicados por terceiros. A ablação deles: **sem o componente de atração na seleção, o hit rate cai de 78,7% para 3,4%.** O Bee roteia por **regra determinística sobre registry fechado** — o vetor não existe por construção. É validação retroativa de uma decisão de arquitetura já tomada.

---

## 6. O VEREDITO HONESTO SOBRE A APOSTA

**A pergunta:** um modelo pequeno, monolíngue, treinado do zero tem futuro útil, ou o Bee é exercício de aprendizado com valor limitado?

### 6.1 — O que a evidência diz A FAVOR

1. **A faixa sub-1B não foi abandonada — é linha ativa em 2026.** MobileLLM-R1 (arXiv:2509.24945) foi **aceito na ICLR 2026** com o título literal *"Exploring the Limits of Sub-Billion Language Model Reasoners with Open Training Recipes"*: família 140M/360M/950M pré-treinada do zero. O 950M: MATH500 **74,0%** vs 73,0% do Qwen3-0.6B; AIME'24 **15,5%** vs 11,3%; LiveCodeBench-v6 **19,9%** vs 14,9% — com **~2T tokens (11,7% dos 36T do Qwen3)**. (Perde em GSM8K: 67,5 vs 79,2.)

2. **Pequeno especializado bate fronteira grande, por margem grande.** arXiv:2606.22606: **Qwen2.5-0.5B ajustado (2-shot) = 0,828 de micro-F1** médio em 7 benchmarks de extração de relações, contra **GPT-5.4 zero-shot 0,693** e Claude Sonnet 4.6 0,662. No domínio literário: 0,833 vs 0,578. É o oposto direto da tese "modelo grande com harness ganha sempre".

3. **A tese exata do Bee foi validada por terceiro.** LilMoo (arXiv:2603.03508): 670M monolíngue hindi do zero, corpus filtrado por juiz LLM destilado, **NPM 9,94 vs 4,08 do Qwen3-0.6B e 1,92 do Qwen2.5-0.5B**, com ~100× menos computação.

4. **Dado pode substituir escala numa tarefa definida.** Data Turnstile: 0,6B com dado bom **24,6%** fica perto de 1,7B com dado bom (31,1%) e **destrói** 1,7B com dado ruim (6,6%). Nessa tarefa, o dado valeu ~3× de escala.

5. **A medição do próprio Bee.** bpb **0,844** contra 0,884 do Tucano-160m (que usou 9× mais tokens) e 1,551 do SmolLM2-135M (46% pior). Tokenizador 39% mais eficiente em PT. Isso não é opinião.

### 6.2 — O que a evidência diz CONTRA (e é sério)

1. **O teto não se move por método.** Medido dentro (pass@1 52,3→57,6%, pass@16 parado em 72,9%) e confirmado fora (arXiv:2604.06298 com GRPO; arXiv:2608.11829, onde on-policy distillation **derrubou** pass@1024 de 70,0% para 53,3%). **Sub-1B não faz generalidade.**

2. **Raciocínio algorítmico multi-passo é fora do envelope.** DeepSeek-Coder-1.3B (3,8× o Bee-350M, especializado) tira **2,15/5**.

3. **Horizonte longo é fora do envelope, para todo mundo.** Atribuição de crédito em trajetória: Hit@1 **0,325–0,714** com o método caro. Não resolvido em nenhum tamanho.

4. **A ameaça registrada e não avaliável:** arXiv:2608.11981 afirma que quantizar um modelo grande confiável produz SLMs com **melhor confiabilidade e adaptabilidade** do que treinar pequeno do zero. **Descartado por não declarar tamanhos nem publicar uma única métrica** — não dá para avaliar. Mas é o eixo (justiça, robustez, privacidade, ética) em que o Bee vai apanhar quando alguém o avaliar. Registro sem números.

5. **A literatura está uma ordem de grandeza acima da escala do Bee.** Dois lotes independentes chegaram à mesma conclusão: o que serve tem de ser caçado nas referências, não no topo do feed. Dos ~60 papers, **6 tocam a escala** e **3 têm número na faixa 70–500M**.

### 6.3 — O veredito

**A aposta é válida DENTRO de um envelope, e não é válida como modelo de propósito geral. O envelope é definível com precisão:**

| O envelope | Por quê |
|---|---|
| **PT-BR nativo** | vantagem medida de 46% em bpb sobre o melhor comparável aberto, e tokenizador 39% mais eficiente. Nenhum modelo comprimido a partir de multilíngue herda isso — herda o pré-treino do pai, que em PT medimos ser pior. |
| **Tarefa estreita com verificador determinístico** | 0,5B ajustado batendo GPT-5.4 por 13–25 pontos (arXiv:2606.22606); tool-calling com registry fechado é exatamente essa forma. |
| **Horizonte curto, uma chamada** | o rejection sampling do Bee funciona porque o crédito é trivial. Estender isso quebra a propriedade que o torna barato. |
| **Execução local/offline** | onde uma API de fronteira não é opção por custo, latência, soberania ou privacidade — e onde 345M em 8GB é o requisito, não uma limitação. |

**Fora desse envelope** — raciocínio aberto, código, horizonte longo, generalidade — a evidência diz que um modelo de fronteira com harness ganha, e **nenhuma quantidade de método fecha essa diferença**. Isso está medido dentro do projeto e confirmado por terceiros.

**Uma consideração estratégica que nenhum paper cobre, e que registro como opinião:** o ativo mais durável do Bee provavelmente não é o modelo. São **o corpus PT-BR curado, o tokenizador de 32k, e a disciplina de medição** — sete guardas contra falha silenciosa, cinco delas escritas com sangue. O modelo será superado; os três outros são reutilizáveis no próximo, e no seguinte.

**E o run do 350M entrega uma coisa além do modelo, se for instrumentado para isso:** avaliando bpb nos **mesmos marcos** do 150M (1B / 3B / 6B / 10B / 15B / 21B), com schedule horizon-free para que os checkpoints intermediários sejam honestos, o projeto passa a ter **6 pontos pareados em dois N**. Isso permite ajustar L(N,D) **com resíduos** — em vez de um ajuste de 3 parâmetros passando por 3 pontos, que descreve e não valida. Custo: zero. É a diferença entre ter um modelo e ter uma medição.

---

## APÊNDICE — Ordem de execução, com o dinheiro

| # | Ação | Custo | Bloqueia? |
|---|---|---|---|
| 1 | Auditoria de repetição interna + histograma | US$ 0 | **sim** — nada roda antes |
| 2 | Estender pass@k (k até 256) no 150M | US$ 0 | não, mas pode matar a premissa do teto |
| 3 | Auditoria manual do avaliador (~50 itens) | US$ 0 | não |
| 4 | Diff por problema pré/pós-autoaprendizado | US$ 0 | não |
| 5 | Refazer a curva de bpb do 150M anotada por LR | US$ 0 | **sim** para qualquer argumento de escala |
| 6 | Dedup + filtro taxonômico, alvo 2–4 épocas | US$ 0–20 | **sim** |
| 7 | Guardas (rótulos / cobertura / norma / épocas) | US$ 0 | **sim** |
| 8 | **[VERIFICAR]** schedule do IMU-1 no PDF | US$ 0 | **sim** |
| 9 | Sanidade QK-Norm (100 passos × 2) | ~US$ 1 | não |
| 10 | Init por crescimento — loss no passo zero | ~US$ 2 | não |
| 11 | Throughput em regime (passo ≥20, 3 leituras) | ~US$ 1 | **sim** |
| 12 | **Run principal: 21,7B tokens** | **~US$ 218** | — |
| 13 | Reserva | **~US$ 60–80** | libera só após 12 avaliado |
| 14 | SFT agêntico Turnstile (irrelevância + distratores) | ~US$ 0 | paralelo, na 5070 |

**Total comprometido antes do run: ~US$ 4–24. Reserva preservada: ~US$ 60–80.**
---

## APÊNDICE B — Lote E recuperado

> Este lote falhou na entrega (limite de tentativas do schema de saída) e **não entrou na síntese
> acima**. Recuperado do transcript do agente. Traz a **única medição do estudo em Qwen2.5-0.5B**,
> a escala mais próxima do Bee em tarefa agêntica de todo o pacote.

### B.1 — AgenticTwin (arXiv:2608.11679) — ⚠️ contradiz a §2.9 **[ACIMA — 0,5B]**

Curva de desempenho por tamanho (diagnóstico / MRR / mitigação):

| modelo | diagnóstico | retrieval | mitigação |
|---|---:|---:|---:|
| **Qwen2.5-0.5B** | **0,64** | 0,68 | 0,60 |
| Qwen2.5-3B | 0,84 | 0,81 | 0,80 |
| Qwen3-8B | 0,87 | 0,86 | 0,86 |
| Llama-3.3-70B | 0,93 | 0,93 | 0,92 |
| GPT-5.5 | 0,96 | 0,97 | 0,96 |

⭐ **O achado:** um knowledge base **estruturado no prompt** melhorou os modelos **pequenos em
33–43%**, e o ganho **encolhe conforme o modelo cresce**. E o salto 0,5B→3B (+0,20) é **maior** que
o salto 3B→32B (+0,09) — a curva é íngreme exatamente na faixa onde o Bee vive.

**Consequência para o Bee:** é o argumento medido **a favor** de gastar metade dos 2.048 tokens com
o catálogo de ferramentas. Para um 151M esse gasto pode render **mais** do que renderia para um 8B —
o contrário da intuição de economizar contexto.

⚠️ **E aqui está a contradição, que fica registrada e não resolvida:** o item **2.7/2.9** da síntese
(baseado em arXiv:2608.11888, *Agent Skills Can Be Harmful*) aponta na direção **oposta** — mede
**inchaço de contexto em 25,3%** das regressões de eficiência, com 43 dos 46 casos vindo do corpo da
própria skill. **Duas evidências em conflito direto sobre a mesma decisão.** Nenhuma das duas está na
escala do Bee em ambos os lados (AgenticTwin mede 0,5B; o outro só mede fronteira).

**Resolve-se por medição, não escolhendo o paper que agrada:** teste pareado de três braços na 5070 —
catálogo completo / catálogo mínimo (só nome + assinatura) / sem catálogo — com **métrica dupla**
(tokens **E** acerto, nunca um só). Custo US$ 0, ~1 dia.

⚠️ **Ressalva de aparato do próprio AgenticTwin:** avaliação por score 0–1 em **mundo fechado** de 4
tipos de anomalia com juiz próprio — exatamente a armadilha que aqui já produziu 23,5% quando o real
era 57,6%. Usar a **forma da curva**, desconfiar dos valores absolutos.

### B.2 — Log-prob como sinal de abstenção (arXiv:2608.11552) **[APOSTA — 7B]**

AUROC no BFCL-v4, Qwen2.5-7B: white-box (agregação de log-prob) **0,70** · reflexiva (P(True))
0,82 · consistência 0,75.

**Por que só a white-box serve ao Bee:** agregação de log-prob é **aritmética sobre os logits** e não
exige capacidade nenhuma do modelo. A reflexiva — a melhor no 7B — exige auto-avaliação, capacidade
meta que um 151M quase certamente não tem; assumir que tem seria a extrapolação que já custou caro.

**Ação de custo zero:** o Bee tem pass@1 57,6% e pass@16 72,9% — **15,3 pp que o modelo produz e não
sabe escolher**. Computar a média de log-prob dos tokens de chamada e medir AUROC contra o gabarito
que **já existe** do pass@16. Se der >0,60, vira reranker das 16 amostras **e** limiar de abstenção,
atacando o over-calling a custo zero. ⚠️ Testar os **4 agregadores** (mean/min/first/last) — o paper
mostra oscilação até 0,48 entre eles; testar um só e concluir seria repetir erro de aparato.

### B.3 — Taxonomia S1/S2/S3 + mapa de fallback (arXiv:2608.11977) **[ACIMA — 4B]**

Qwen3-4B, Retail: base limpo 64,3% → **20,1% sob injeção de falha** (−44,2 pp). **Só** o bloco de
memória de ferramentas no contexto, **sem treino nenhum**: **36,9% (+16,8 pp)**. Só RL: +6,3 pp.

⭐ E o próprio paper diz que o ganho vem do **mapa de fallback** e das restrições de verificação,
**não** dos posteriores bayesianos caros. A parte cara é dispensável; a barata (*"se X falhar tente
Y; se Y falhar abstenha"*) é o que funciona — e com catálogo pequeno cabe em ~40–80 tokens, não nos
+50K do paper.

**A taxonomia é de graça e nomeia o problema do Bee:** S1 (repetir resolve) · S2 (trocar de
ferramenta resolve) · S3 (impossível, tem de abster). **O over-calling é, em boa parte, S3 tratado
como S1** — hoje "errou a ferramenta" e "não devia ter chamado" estão somados num número só.

### B.4 — Calibração de ambição: ToolHazard (arXiv:2608.11878) **[ACIMA — 4B]**

Taxa **benigna** (sem atacante nenhum) em tarefas de ferramenta com estado e horizonte longo:
**Qwen3-4B faz 33,7–41,2%**, contra 69,9–81,9% do GPT-5. Um modelo **26× maior que o Bee falha em
dois terços** dessas tarefas mesmo sem adversário.

**Consequência direta:** *agente stateful de horizonte longo* **não** entra como meta do Bee-350M. O
regime do paper (15,6 passos, 18,75 ferramentas, janela de 32K) é estruturalmente inacessível a 2.048
tokens — e a evidência é que **nem com 32K e 4B** funciona. A meta realista é o que o 150M já mede
bem: tarefa única, catálogo pequeno, decisão de chamar-ou-abster.

### B.5 — Aviso direto para a colmeia (arXiv:2608.11624) **[ACIMA — 1,5B]**

Um persuasor treinado por GRPO derruba a acurácia de um modelo congelado de **66,2% para 1,8%**, com
transferência de **79–82,5%** entre famílias. O persuasor treinado converge para **engano e citações
fabricadas**, não para argumento lógico.

⭐ **É evidência publicada a favor do Policy-as-Logic já adotado.** A regra fica explícita no
registry: **prosa de abelha nunca sobrepõe verificador determinístico, e nenhuma abelha julga
outra.** Quando um modelo julga a saída de outro por diálogo, a acurácia pode ir a 1,8%.

**Segundo uso, barato:** o setup é um **teste de robustez** — reapresentar ao Bee as perguntas que ele
acertou, com contra-afirmação confiante (*"tem certeza? a resposta é X"*), e medir quantos acertos
sobrevivem. Primo direto do teste de paráfrase que já entrou no Gate 2.
