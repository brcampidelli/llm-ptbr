# Triagem arXiv — rodada 3: arquitetura, escala, corpus e réguas do Bee-1G

> **O que é:** oito agentes lendo **~15.000 resumos** do arXiv em 2026-09-01, sobre 23 termos
> (objetivo de treino · decoder-only · encoder-only · MoE · Mamba/MLA · compute-optimal · leis de
> escala · janela de contexto · corpus · filtragem · token e vocabulário). Continuação da
> [rodada 1-2](triagem-arxiv-bee1g-2026-08-31.md).
>
> **⭐ O que saiu:** a **tabela central do `plano-bee-1g.md` está errada em três eixos ao mesmo
> tempo** — enquadramento, unidade e conjunto de cenários. A arquitetura multimodal recomendada
> está do lado contrário do que a medição indica. E **a nossa régua principal, bpb, está na lista
> das enviesadas** para comparação entre escritas.
>
> ⚠️ **Como ler os números:** entre 1,0% e 4,5% dos resumos de cada fatia trazem semente, IC ou
> teste pareado. Nas palavras de um dos agentes: *a literatura que ajusta leis de escala é quase
> toda do tipo que não consegue exibir o próprio ruído — vale ler os expoentes como ordem de
> grandeza, nunca como medida.*

---

# A. O ORÇAMENTO — a tabela do dilema está errada em três eixos

A tabela do plano compara **20 / 63 / 170 tokens por parâmetro** e conclui que *"um Bee-1G de
orçamento razoável seria maior e pior em português que o Bee-350M"*. Três achados independentes a
atingem.

## A1. 🔴 Enquadramento — o schedule vale mais que o fator de tokens

[`2502.15938` **Straight to Zero**](https://arxiv.org/abs/2502.15938) — sob LR de pico ótimo,
decaimento linear a zero bate as demais schedules em tamanhos, batches, datasets e vocabulários:

> um **610M com 80 tok/param + D2Z tem loss MENOR** que o mesmo modelo com **200 tok/param** e
> decaimento 10× → **60% de economia de compute**

⭐ É o mesmo fenômeno que medimos por bifurcação (US$ 22, **−0,1305** de loss ao decair 20%), agora
com número de terceiro na nossa faixa. **Antes de comprar tokens, comprar decaimento.**

Complementos: [`2405.18392`](https://arxiv.org/abs/2405.18392) (LR constante + cooldowns escala tão
previsivelmente quanto cosine **e permite reusar runs** — a nossa §2d publicada) e
[`2607.10959` WSqD](https://arxiv.org/abs/2607.10959) (schedule *horizon-free*, LR de pico único
reutilizado entre horizontes).
⚠️ Com uma contradição registrada: [`2406.19146`](https://arxiv.org/abs/2406.19146) reproduz Kaplan
e acha que **decaimento cuidadoso de LR NÃO é essencial para a validade da lei** — afirmação
diferente (qualidade final × validade do ajuste), mas ler uma sem a outra erra.

## A2. 🔴 Unidade — a conta tem de ser em BYTES

[`2605.01188` **Compute Optimal Tokenization**](https://arxiv.org/abs/2605.01188) — **988 modelos,
50M a 7B**: em configuração compute-ótima, **a contagem de parâmetros escala com o dado medido em
BYTES, não em tokens**, contra Kaplan e Chinchilla. Generaliza para subword e para além do inglês.

⚠️ **Dividir um orçamento de tokens por 8 idiomas de fertilidades diferentes é comparar réguas
diferentes** — a §2g em forma de tokenizador. E corta a nosso favor: com **0,218 tok/byte** contra
0,358 do SmolLM2, os nossos 21,75B tokens de PT valem bem mais que a mesma contagem num tokenizador
pior.

## A3. 🔴 Cenários — diluição uniforme é a família que a lei nunca escolhe

[`2410.12325` **M³ Scaling Law**](https://arxiv.org/abs/2410.12325) — o único artigo que ataca a
pergunta de frente. Põe monolíngue-1-estágio, multilíngue-1-estágio e **multilíngue-2-estágios** na
mesma superfície de loss do idioma-alvo:

1. conforme o dado do alvo escasseia, o ótimo salta **direto** para **multilíngue-2-estágios** — e
   **multilíngue-1-estágio nunca é ótimo na grade**;
2. o número ótimo de épocas **colapsa numa curva única** na variável de escassez.

🔴 **As três linhas da tabela são de estágio único.** O desenho indicado é **dois estágios com razão
de PT alta no final** — e é exatamente o que o [`2607.09885` Index-1.9B](https://arxiv.org/abs/2607.09885)
faz na prática (WSD com a concentração de dado curado elevada **na fase de decaimento**).

## A4. ⭐ E um experimento de CPU, custo zero, que estima a direção antes de gastar

[`2405.16684`](https://arxiv.org/abs/2405.16684) — leis de escala **não são agnósticas ao dado**, e
**gzip prevê o impacto**: a fronteira desloca para **mais dado** quando o corpus é difícil de
comprimir, e para **mais parâmetro** quando é altamente comprimível. Mecanismo plausível para a
nossa medição (+45% de token = 0,19%; 151M→345M = 2,76%), e **medir a compressibilidade gzip do
corpus de 8 idiomas contra o só-PT custa CPU e minutos**.

## A5. ⭐ A lei certa para a nossa restrição real: relógio, não FLOPs

[`2603.28823` **Time is Not Compute**](https://arxiv.org/abs/2603.28823) — **70+ runs, 50M a 1031M,
numa RTX 4090**, orçamentos de 5 min a 24 h: `N* ∝ t^0,60` com **α = 0,60 ± 0,07**, crescendo mais
rápido que o `C^0,50` de Chinchilla. Mecanismo de U dupla (curta por compute, longa por dado).
⭐ **Sob restrição de tempo de GPU, o modelo ótimo é MAIOR que o compute-ótimo** — concorda com a
nossa medição de que a escala paga e o token não. **Nós alugamos por hora; esta é a lei, e a de
Chinchilla é a errada.**

E o vizinho de orçamento: [`2608.27370` **Puro-2B**](https://arxiv.org/abs/2608.27370) — *"Poor
Lab's Qwen2-1.5B Trained on RTX 5090 within $5090"*: **do zero, 1,4T tokens, FP8, numa 5090 de
consumo, sob US$ 6,9 mil**, receita completa Apache-2.0.

## A6. ⭐ O formalismo do nosso próprio achado, e a lei de repetição

[`2607.25271`](https://arxiv.org/abs/2607.25271) (14M–600M) introduz a **efetividade de token η** —
quanto vale um token derivado (repetição, paráfrase) contra um fresco — e mede que **η não é
constante e satura**. Particiona o treino em compute-bound / data-bound / model-bound e conclui que
**a alocação compute-ótima clássica é subótima na maioria dos casos praticamente relevantes**.

Com [`2605.12715`](https://arxiv.org/abs/2605.12715) (2.000+ runs, inclui misturas multilíngues):
**treino em mistura tolera muito mais repetição que fonte única — corpora-alvo escassos podem ser
reusados 15 a 20 vezes.** E [`2606.06888`](https://arxiv.org/abs/2606.06888) (72M–1,4B) mostra que
**a forma aditiva de Chinchilla é malespecificada no regime de dado limitado**.

## A7. ⚠️ E três avisos sobre o ajuste em si

| artigo | achado |
|---|---|
| 🔴 [`2605.08541`](https://arxiv.org/abs/2605.08541) | ajustar a lei sobre runs com razão tokens/parâmetro **FIXA** é desenho **colinear**: coeficientes praticamente **não identificáveis**, ICs inflam uma ordem de grandeza. Provado para 4 formalismos; desenhos não-colineares vencem em holdout com **97,3%** |
| 🔴 [`2603.22339`](https://arxiv.org/abs/2603.22339) | o método de ajuste mais usado do campo tem **viés sistemático até em dado sintético sem ruído**. No IsoFLOP publicado do Llama 3: **US$ 1,4M** de compute desperdiçado. ⚠️ E o viés **PIORA em multimodal**, por assimetria mais alta |
| 🔴 [`2507.00885`](https://arxiv.org/abs/2507.00885) | escala previsível em tarefa downstream ocorre em **39% dos casos**; *"mudanças aparentemente inócuas no arranjo experimental podem mudar completamente o comportamento de escala"* — a §2g como resultado de campo |
| ⚠️ [`2404.10102`](https://arxiv.org/abs/2404.10102) × [`2509.23963`](https://arxiv.org/abs/2509.23963) | mesma base, vereditos opostos sobre a confiabilidade de Chinchilla. **Registrar a discordância é o achado**; a leitura prática é tratar "20 tok/param" como **faixa larga** |
| 🔴 [`2502.17356`](https://arxiv.org/abs/2502.17356) | os "saltos" emergentes são a mudança contínua de uma distribuição **bimodal entre sementes**. A mesma config dá curva suave ou emergente conforme a semente — a nossa §2m elevada a lei de escala |
| 🔴 [`2606.29158`](https://arxiv.org/abs/2606.29158) | refuta parcialmente a forma log-linear que a **Step Law usa (e nós usamos)**: o LR ótimo desenvolve **curvatura para cima** em escala maior. A curvatura some ao extrapolar por **D em vez de N** |

---

# B. A ARQUITETURA

## B1. 🔴 Decoder-only para tradução não é a escolha óbvia

[`2510.26622`](https://arxiv.org/abs/2510.26622) — comparação pareada de **~150M a ~8B**, prefix-LM
contra causal LM, RedPajama 1,6T + FLAN. As duas metades são opostas: **decoder-only é mais
compute-optimal no PRÉ-TREINO**, mas depois de instruction tuning **o prefix-LM empata ou ganha**,
com eficiência de inferência substancialmente melhor.

⚠️ **E a frase que nos atinge: se você medir só bpb de pré-treino, decoder-only vence — e bpb de
pré-treino é exatamente a métrica com que este projeto decide.**

| artigo | evidência |
|---|---|
| [`2412.05862`](https://arxiv.org/abs/2412.05862) | **NLLB-200 3,3B (enc-dec) bate TODOS os decoder-only de 7–8B em 3 de 4 direções, inclusive en→pt** |
| [`2304.04052`](https://arxiv.org/abs/2304.04052) | o mecanismo formal: **degeneração da atenção** — conforme a geração avança, sobra menos atenção para a fonte. Explica a piora em sentença longa, que é o regime de tradução |
| [`2503.06594` LaMaTE](https://arxiv.org/abs/2503.06594) | LLM como encoder + decoder NMT leve: qualidade igual ou melhor com **2,4–6,5× de speedup e −75% de cache KV** |
| 🟢 [`2202.01994`](https://arxiv.org/abs/2202.01994) | **NULO**: variando enc-dec × decoder-only × híbrido, **os expoentes de escala de dados são minimamente afetados** — arquitetura pior se compensa com dado. ⚠️ Mas **back-translation no lugar de bitexto real degrada o expoente de verdade** |
| [`2603.20732` MzansiLM](https://arxiv.org/abs/2603.20732) | contraponto: **125M do zero**, 11 idiomas, decoder-only, 20,65 BLEU em isiXhosa competindo com enc-dec 10× maiores |

## B2. ⭐⭐ Para as PEÇAS, encoder pequeno vale mais que decoder grande

[`2507.11412` **Ettin**](https://arxiv.org/abs/2507.11412) — encoder e decoder com **a mesma
receita, o mesmo dado e a mesma ordem de treino**, de 17M a 1B, até 2T tokens: **um encoder de 400M
ganha de um decoder de 1B** em tarefa discriminativa, e o inverso vale para geração. E **adaptar
decoder→encoder por treino continuado é subpar**.

→ O caminho *"usa o próprio Bee-1G como recuperador"* está **medido como inferior sob condição
casada**. É a mesma família do nosso recuperador IDF de 30 linhas (+26,7 pp): **peça pequena e
dedicada paga.** Apoios: [DistilVDR](https://arxiv.org/abs/2608.10636) (recuperador multimodal de
**524M com 86,9% de um professor de 8B**, índice 15,6× menor) e
[FinBERT2](https://arxiv.org/abs/2506.06335) (32B tokens, bate o embedder da OpenAI em 4,2%).

⚠️ **E o artigo que discorda do Bee-1G por escrito, em português:**
[`2606.22722` moBERTo](https://arxiv.org/abs/2606.22722) — *"continued pretraining é fortemente
preferível a treinar do zero, particularmente para preservar contexto longo"*.
**Não é contradição plana:** o [ModernGBERT](https://arxiv.org/abs/2505.13136) mediu, com dado e
treino **idênticos**, que **do zero a 1B (0,808) supera o convertido de 7B (0,787)**. São operações
diferentes — *continuar no mesmo objetivo* × *converter entre objetivos*.

## B3. 🔴 Profundidade × largura: a nossa geometria está na ponta errada

[`2601.20994` **The Depth Delusion**](https://arxiv.org/abs/2601.20994) — 30 arquiteturas de **17M a
7B**, R² 0,922: `D* ~ C^0,12` e `W* ~ C^0,34`, isto é, **largura deve crescer 2,8× mais rápido que
profundidade**, e há uma **profundidade crítica** além da qual somar camadas **aumenta** a loss.
Somos 30 camadas × d_model 576 (razão 19,2).
⚠️ A constante de `D_crit` não está no resumo — **a conta tem de ser lida no PDF antes de decidir**.

- [`2605.27989`](https://arxiv.org/abs/2605.27989) responde à nossa ressalva registrada (*"a suspeita
  veio de modelos 10–100× maiores"*): o intervalo eficiente de `R_D/W` **permanece estável conforme
  o orçamento cresce** — logo transfere;
- [`2501.18107` Morph-1B](https://arxiv.org/abs/2501.18107) replica **na escala exata** (63 modelos,
  80M–1B, do zero): mais largo e mais raso preserva acurácia, e modelos do mesmo tamanho diferem até
  **3,5× em latência**;
- ⚠️ [`2602.05970`](https://arxiv.org/abs/2602.05970) contradiz **pelo mecanismo**: a loss cai como
  `1/profundidade` porque as camadas ficam funcionalmente **similares** e agem como média de
  ensemble. Profundidade não é inútil — é mal aproveitada;
- [`2409.15051`](https://arxiv.org/abs/2409.15051) (6 decoder-only de 70M a 7B **do zero**, tradução
  multilíngue): **escalar profundidade e largura dá a mesma melhora de test loss, com eficiência
  diferente**;
- [`2502.06857` **Gemstones**](https://arxiv.org/abs/2502.06857): **4.000+ checkpoints até 2B com
  formas arquiteturais diversas, abertos** — dá para testar a nossa razão **sem treinar nada**. E o
  veredito deles: *"as prescrições das leis de escala podem ser altamente sensíveis ao desenho
  experimental"*;
- [`2607.27230`](https://arxiv.org/abs/2607.27230) (100M/350M/1B do zero): contagem de cabeças é
  **U-shaped** com ótimo achatado em H=4 ou 8 — ⭐ **grade que CERCA o ótimo** (§2f).

## B4. 🔴🔴 Mamba/SSM esquece exatamente o que a tradução não pode esquecer

[`2512.15653`](https://arxiv.org/abs/2512.15653) — Mamba **130M–1,4B**, auto-encoder reconstruindo a
sequência a partir do estado: a perda de informação é **significativamente maior em números,
variáveis e menções a organizações**, e o que ele esquece é **o que é raro no pré-treino**.
**Para tradução, essa é a lista exata do que não pode sumir.**

| artigo | medida |
|---|---|
| [`2603.20997`](https://arxiv.org/abs/2603.20997) | 20+ experimentos, 200K a 1,4B: roteamento por conteúdo exige comparação **par-a-par**. **Mamba-1.4B faz 29%**; bidirecional + par-a-par faz **99,5%**; UMA camada bidirecional num Pythia-1B congelado recupera 99,4% |
| [`2605.06997` Echo](https://arxiv.org/abs/2605.06997) | **Mamba-2 puro não passa do acaso (~3%)** em recall associativo multi-chave |
| [`2602.01763`](https://arxiv.org/abs/2602.01763) | **separação PROVADA**: nenhum híbrido com poucas camadas plenas resolve composição sequencial, por mais camadas lineares que tenha |
| ⭐ [`2605.16640`](https://arxiv.org/abs/2605.16640) | o outro lado, também provado: o híbrido resolve com scratchpad **O(1)** o que o recorrente puro não resolve. **Não há almoço grátis — há um preço com número** |
| ⭐ [`2608.08256` AraSSM](https://arxiv.org/abs/2608.08256) | o único treinado do zero em **hardware de consumo real** (4× RTX 2080Ti de 11 GB, ~10 dias), com **média ± dp em 3 sementes**: empata em sentimento, **fica abaixo em XNLI** — inferência é onde o SSM cede |

⚠️ **E o aviso de compra:** [`2605.22791`](https://arxiv.org/abs/2605.22791),
[`2603.15569`](https://arxiv.org/abs/2603.15569), [`2606.12364`](https://arxiv.org/abs/2606.12364) e
o já triado `2607.07953` dão **quatro vencedores diferentes, todos "controlados"**. O ranking de
atenção linear **não é estável entre setups** — não adotar nenhum por tabela alheia.

## B5. ⭐⭐ MoE: a pergunta não tem resposta de arquitetura, só de hardware

[`2608.10605` **MOSAIC**](https://arxiv.org/abs/2608.10605) — lei ajustada de **104M a 2,7B
ativos**: dentro da faixa calibrada, **um orçamento de FLOPs não admite esparsidade ótima
interior**; **a esparsidade ótima só existe sob restrição de SISTEMA**. Isso explica por que os
quatro artigos abaixo discordam sem nenhum estar errado — cada um iguala um eixo diferente:

| artigo | eixo igualado | veredito |
|---|---|---|
| [`2606.21428`](https://arxiv.org/abs/2606.21428) | parâmetro **ATIVO** | −31% no edge, 2,1× energia/token |
| [`2605.10933` DECO](https://arxiv.org/abs/2605.10933) | parâmetro **TOTAL** | empata denso, **2,93× no Jetson AGX Orin** |
| [`2605.27358` MobileMoE](https://arxiv.org/abs/2605.27358) | **memória INT4** | 1,8–3,8× prefill |
| [`2603.26603`](https://arxiv.org/abs/2603.26603) | **energia em Android** | *"capacidade de 7B com perfil energético de 1–2B"* |

🔴 **E ninguém rerodou o OLMoE num Jetson.** As três "refutações" trocam o eixo. **A contradição
continua aberta e não resolvida por medição direta.**

⭐⭐ E um **negativo pré-registrado servindo em GPU de 8 GB** — a nossa placa:
[`2608.18261`](https://arxiv.org/abs/2608.18261) treinou MoEs de **137M**, o mecanismo funciona
(−60% de cache-miss) e **toda configuração falha o portão pré-registrado de ≤1% de ppl**. Um degrau
de 340M mostra que **o imposto NÃO encolhe com escala — sobe**. Contradiz explicitamente o
StickyMoE, que mediu em **sub-25M mono-domínio**.

### E o que de fato move a qualidade de um MoE — três medições convergentes

- ⭐⭐ [`2605.11689`](https://arxiv.org/abs/2605.11689) — **mais de 2.000 runs de pré-treino**, até
  6,6B: performance melhora com o **TOTAL**; o tamanho ótimo de expert depende **só do ATIVO**; e
  **shared experts, experts heterogêneos e load balancing têm efeito pequeno** — só *dropless
  routing* paga. **Receita: mexer em contagem e granularidade, ignorar o resto**;
- ⭐⭐ [`2604.14419` **Equifinality**](https://arxiv.org/abs/2604.14419) — 62 experimentos a 76–84M
  **treinados até convergência, 3 sementes, teste de equivalência TOST**: **a topologia de
  roteamento NÃO determina a ppl assintótica**. Hash, aleatório fixo e top-1 degradam **1,1–2,2
  PPL**; a vantagem real do mecanismo é **~1,2%**;
- [`2605.09403`](https://arxiv.org/abs/2605.09403) — em transformers de uma camada, **roteamento
  aleatório congelado quase iguala o aprendido**.

### MoE multilíngue: idioma é a exceção que sobrevive

⭐⭐ [`2606.25092`](https://arxiv.org/abs/2606.25092) — **pré-registrado, causal, IC de bootstrap**,
ablação contra nulo de experts aleatórios casado em tamanho: de **seis** famílias de expert, **só
uma sobrevive como módulo seletivo limpo — a do idioma árabe**. **Idioma é a exceção; capacidade é
folclore.**

⭐ E o mais acionável: [`2605.28042`](https://arxiv.org/abs/2605.28042) poda **metade dos experts sem
degradação** e 75% com SFT curto recuperando a baseline. **Tradução usa uma fração do MoE.**

⚠️ Com contradição aberta sobre se isolamento por idioma é **recurso ou patologia**:
[`2604.03592`](https://arxiv.org/abs/2604.03592) o explora (+10,85% F1);
[`2605.17598`](https://arxiv.org/abs/2605.17598) e [`2606.25821`](https://arxiv.org/abs/2606.25821)
o corrigem empurrando para experts **compartilhados**, e a correção **correlaciona com ganho**,
replicada em hebraico e japonês.

⚠️ E o alerta do eixo multimodal: [`2606.17118` MODE](https://arxiv.org/abs/2606.17118) — em MoE
multimodal **a dominância numérica de tokens de visão sequestra a estatística de expert e mascara
os experts críticos para texto**. Decisão tomada sobre contagem de ativação **está medindo visão**.

## B6. ⭐⭐ MLA perde na única varredura direta

[`2601.11471` LRKV](https://arxiv.org/abs/2601.11471) — **128M a 6,3B pré-treinados**: LRKV tem a
**menor test loss entre MHA, MQA/GQA e MLA**, usando 45–53% do cache do MHA. **MLA perde.**

⚠️ E [`2506.09342`](https://arxiv.org/abs/2506.09342), a **30M do zero**, traz o alerta que decide
para nós: **sem RoPE, MLA fica 3–5% PIOR que atenção baunilha em modelo pequeno**; com RoPE, 2%
melhor. Custos que ninguém cita: a cabeça latente **não particiona em tensor parallelism**, e o MLA
dá **zero ganho de multi-token prediction em GPU comum**.

## B7. 🔴🔴 Multimodal: early-fusion, e isso dissolve a nossa crise de identidade

[`2504.07951` **Scaling Laws for Native Multimodal Models**](https://arxiv.org/abs/2504.07951) —
**457 modelos treinados**. Resultado **NULO** sobre a suposição dominante: **não há vantagem
inerente de late-fusion sobre early-fusion**. Ao contrário — **early-fusion, sem encoder de imagem e
sem tokenizador visual, é mais forte em contagens baixas de parâmetro**, mais barata de treinar e
mais fácil de servir.

🔴 O plano recomenda a opção (a) — SigLIP congelado + projetor — que é **late-fusion**, e registra a
"crise de identidade" (com encoder emprestado, *"do zero"* não cobre os olhos). **Early-fusion
dissolve as duas coisas de uma vez.**

Convergindo: [`2607.22043`](https://arxiv.org/abs/2607.22043) (nativo, do zero) mede que **a lei de
alocação da LINGUAGEM é praticamente invariante à composição do dado** — acrescentar imagem **não
deve** custar a alocação do texto — e que há **transferência positiva** (melhora raciocínio espacial
em texto puro).

⚠️ E [`2608.17286` Abra](https://arxiv.org/abs/2608.17286): no treino de difusão de imagem a
otimalidade fica em **~200 tokens de imagem por parâmetro, 10× a prescrição de Chinchilla**.
**Um único "tokens por parâmetro" para o modelo inteiro é a régua errada.**

## B8. ⭐ Objetivo de treino: CLM→MLM sequencial, com ressalva

Três artigos independentes convergem em que o **currículo bifásico CLM→MLM é ótimo sob orçamento de
compute fixo**: [`2507.00994`](https://arxiv.org/abs/2507.00994) (38 modelos de 210M a 1B, 15.000+
runs de avaliação), [`2608.25768` MoganBert-TR](https://arxiv.org/abs/2608.25768) (**149M do zero**,
237,3B tokens, transição **dentro do platô do WSD** — o nosso schedule — com **+0,49 ± 0,26 em 5
sementes pareadas, p = 0,013**) e [`2605.12438`](https://arxiv.org/abs/2605.12438) (replicação
independente, com a ablação que fecha: **congelar as camadas baixas durante o CLM elimina o ganho**).

⚠️ **Os três medem representação e recuperação, não geração.** Este instrumento não consegue mostrar
se a ordem ajuda um gerador.

🔴 E dois negativos do lado do currículo de **dado**: [`2311.08886` CLIMB](https://arxiv.org/abs/2311.08886)
(BabyLM, do zero) mediu que três variantes de currículo **não produziram melhoria consistente**, e o
que rendeu foi **arquitetura e hiperparâmetro**; [`2412.05149`](https://arxiv.org/abs/2412.05149)
registra que **nenhuma submissão superou os baselines na trilha multimodal**.

---

# C. A JANELA — curta vence, e a nossa já vale mais

## C1. ⭐⭐⭐ Três evidências independentes de que o ótimo é interior

[`2503.15450` **SkyLadder**](https://arxiv.org/abs/2503.15450) — pré-treino **do zero**, 1B e 3B,
100B tokens: *modelos pré-treinados com janelas mais curtas batem consistentemente os de contexto
longo sob orçamento fixo de tokens*. O agendamento curto→longo recupera depois, com **+3,7%** e
**até 22% mais rápido**.

[`2608.12218`](https://arxiv.org/abs/2608.12218) confirma **e dá o mecanismo**: aumentar a janela
melhora só até um **ótimo intermediário** e depois **declina consistentemente**, porque o gradiente
migra da FFN (conhecimento paramétrico) para a atenção — **o modelo aprende a consultar em vez de
saber**. Para um modelo que precisa *saber* traduzir, é o argumento mais forte contra subir a
janela. E [`2312.01515`](https://arxiv.org/abs/2312.01515) (fala) é a terceira evidência de
não-monotonicidade.

⚠️ **`2509.18762` contradiz — e por isso vale duplo:** **SFT longo MELHORA o desempenho curto**,
sinal oposto ao do pré-treino longo. **A decisão de comprimento é diferente no pré-treino e no
SFT.**

Referência: [`2606.28999` BERTomelo](https://arxiv.org/abs/2606.28999), encoder PT do zero com 106M
documentos, escolheu janela de **1.024**.

## C2. ⭐⭐ E os nossos 2048 já valem ~3350

[`2607.24276` **Tokenizer Tax**](https://arxiv.org/abs/2607.24276) mede que o cl100k cobra **8,0× em
média** dos idiomas índicos, reduzindo a **janela efetiva a 12%** da do inglês — e o mecanismo é
**merges BPE que falham deixando bytes soltos, Pearson r = 0,89**.

⭐ **É exatamente o que medimos no nosso vocabulário** (árabe, han e kana com **zero tokens** →
fallback de byte). O censo é o mecanismo do imposto, confirmado por terceiro.

E corta a nosso favor: com **0,218 tok/byte** contra 0,358, **os nossos 2048 tokens carregam ~64%
mais texto** — cerca de **3350 tokens de um tokenizador padrão**. **Parte do custo de ir a 4096 já
foi paga no tokenizador**, e isso não estava sendo contado.

⚠️ **`seq_len` não é decisão de arquitetura — é decisão conjunta com o tokenizador.** E **ninguém
comparou o custo de subir `seq_len` contra o ganho de um tokenizador melhor**, embora os dois eixos
sejam **o mesmo recurso: texto por janela**.

## C3. 🔴 Uma guarda a escrever antes de mexer em seq_len

[`2411.13476`](https://arxiv.org/abs/2411.13476) — família "nada dá erro": **RoPE em bf16 desvia da
codificação relativa pretendida**, o erro **acumula com o comprimento**, e o **primeiro token** é o
maior contribuinte. Ninguém vê, a loss cai. **Nós treinamos em bf16.**

## C4. ⭐ E uma reinterpretação candidata de um achado nosso

[`2607.16072`](https://arxiv.org/abs/2607.16072) — pré-treino em DCLM **até 1,4B**: transformers
rasos com **2D-RoPE copiam perfeitamente** em comprimentos centenas de vezes maiores que os do
treino, enquanto o PE padrão fica muito atrás.

⚠️ Bate no nosso **§2w** (*"o modelo sintetiza e-mail, não copia"*). Atribuímos ao dado — 22 strings
distintas — e a diversificação deu +12 pp. **Pode haver uma segunda causa, arquitetural.** Não
invalida a medição; abre um eixo não testado.

## C5. Tradução: selecionar contexto bate ter contexto

| | |
|---|---|
| [`2604.02596`](https://arxiv.org/abs/2604.02596) | **50 exemplos recuperados por BM25 ≈ 250 many-shot**; 250 ≈ 1.000. **Recuperar vale 4–5× encher a janela** |
| [`2602.04764`](https://arxiv.org/abs/2602.04764) | os ganhos **saturam rápido e podem DEGRADAR** perto do máximo da janela |
| [`2510.16809`](https://arxiv.org/abs/2510.16809) | 90.000 traduções: **correção funcional pica em 5–25 exemplos** e piora depois, enquanto a similaridade estática **melhora** — §2y |
| [`2511.07230`](https://arxiv.org/abs/2511.07230) · [`2605.30274`](https://arxiv.org/abs/2605.30274) | os dois melhores doc-level MT **não usam contexto maior** — selecionam vizinhança por grafo de discurso ou por RL |
| ⚠️ [`2505.01761`](https://arxiv.org/abs/2505.01761) | a régua de MT tem **viés de comprimento**: texto mais longo produz menos spans de erro e ranking pior |

---

# D. O CORPUS — traduzir em vez de coletar, e a interação não medida

## D1. ⭐⭐⭐ Dado traduzido bate dado nativo por token gasto

[`2607.00890` **MultiSynt/MT**](https://arxiv.org/abs/2607.00890) — traduziram **100B tokens do
Nemotron-CC** para 36 idiomas europeus. Modelos treinados nisso **atingem o escore final do HPLT 2.0
(dado NATIVO) com ~72% menos tokens**, e o superam em **~15% relativo com orçamento igual**.

Com [`2605.13225` **Mix, Don't Tune**](https://arxiv.org/abs/2605.13225) ao lado — **~1.000 runs,
quatro escalas de 150M a 1,43B**, a nossa faixa exata: misturar vale **2–3× o dado único do alvo em
loss e 2–13× em acurácia downstream**, e **a folga CRESCE com o tamanho do modelo**.

⚠️ **Três ressalvas que os próprios autores medem:**
1. **benchmark de múltipla escolha NÃO enxerga diferença de qualidade de tradução** — só um juiz
   sensível a fluência recupera;
2. **tarefa idiomática e culturalmente ancorada continua melhor servida por dado nativo**;
3. 🔴 **a loss de validação na língua-alvo SUBESTIMA sistematicamente o valor da mistura** — captura
   só o efeito de regularização, não o conhecimento novo. **Medir por bpb do PT daria a resposta
   errada.**

## D2. 🔴🔴 E a recomendação mais forte tem uma interação NÃO MEDIDA com o nosso pior defeito

Busca explícita: **zero artigos sobre dedup near-duplicate ENTRE idiomas**, e zero sobre **traduções
paralelas duplicadas no pré-treino**.

⚠️ O MultiSynt/MT é **multi-paralelo por construção** — o mesmo documento existe em 36 versões. E o
`2606.24998`, já nas nossas lições, mede que **repetição interna causa dano NÃO-monotônico com pico
em contagem intermediária**. Ninguém mediu o que acontece quando a "repetição" é o mesmo documento
em oito línguas.

Reforço: [`2606.29605`](https://arxiv.org/abs/2606.29605) — num corpus gerado por LLM **só 10,9% é
conteúdo único treinável e 79,4% é redundante; a contagem crua superestima a informação em ~9×**.

**A recomendação mais forte do lote e o nosso defeito mais bem documentado se encontram num ponto
que a literatura não mediu.**

## D3. 🔴 A hipótese alternativa que nunca testamos

[`2604.28075`](https://arxiv.org/abs/2604.28075) (alemão, 500M documentos, **múltiplas escalas de
modelo e de orçamento**): **repetir o núcleo duramente filtrado bate passe único num corpus maior e
menos filtrado**, e **a folga persiste depois de 7 épocas**. SOTA com 10–360× menos tokens.

⚠️ Nós medimos *"+45% de tokens rendeu 0,19%"* — mas adicionamos mais do **mesmo corpus
não-refiltrado**. **Filtrar duro os 21,75B e repetir o núcleo é a alternativa que nunca medimos**, e
já temos o corpus e o censo de repetição.

⚠️ Com contrapesos honestos: [`2412.02595` Nemotron-CC](https://arxiv.org/abs/2412.02595) mede que
FineWeb-Edu e DCLM **removem 90% do dado**, inviabilizando horizonte longo;
[`2606.07778`](https://arxiv.org/abs/2606.07778) acha que dado **dois escalões abaixo do limiar de
produção** melhora 22,3% em raciocínio e **bate o dado de topo em código**, introduzindo duas
dimensões novas — **atualidade e especificidade cultural**; e
[`2605.29807`](https://arxiv.org/abs/2605.29807) (russo) é um **nulo com controle aleatório
casado**: em corpus grande e limpo, **filtrar não melhora nada**.

## D4. 🔴 Um número que derruba uma premissa implícita

[`2605.00086`](https://arxiv.org/abs/2605.00086) — **331 bilhões de tokens de português
brasileiro**, o maior corpus monolíngue de PT aberto. **~15× o nosso.** O plano trata 21,75B como se
fosse o que existe em PT. **Não é.**

## D5. ⭐⭐ Licença: um modo de falha que não tínhamos

[`2606.28867`](https://arxiv.org/abs/2606.28867) audita **20+ famílias de corpus** com evidência de
fonte primária:

- 🔴 **cláusula NoDerivs escondida atrás de rótulo CC-BY** (Tanzil) — e **NoDerivs proíbe
  silenciosamente tokenizar e anotar**. Não aparece em nenhuma checagem de *"a licença é aberta?"*;
- **proibição pura** (JW300, **removido do OPUS após auditoria legal confirmar violação de ToS**);
- **falsa representação de licença composta** (alegação CC-BY contradita pelo próprio dataset card);
- **falha de persistência** (402 de 405 URLs mortas).

🔴 E a lacuna que nos toca: **licença do fineweb-2 / ODC-By discutida em artigo — zero.** A base que
usamos **não foi auditada por ninguém**.

⚠️ Dois avisos operacionais: [`2505.21733`](https://arxiv.org/abs/2505.21733) (bots cumprem **menos**
as diretivas mais estritas de robots.txt) e [`2608.10690`](https://arxiv.org/abs/2608.10690) — dá
para **estimar a mistura do corpus a partir do vocabulário do tokenizador liberado** (erro médio
3,00%). **Publicar o nosso tokenizador vaza a composição do nosso corpus.**

## D6. ⭐ O nosso censo de 0,28% é excepcional, não o padrão

[`2605.18232`](https://arxiv.org/abs/2605.18232) auditou o release somali *"cleaned"* do **HPLT
v2**: **17,3% de duplicatas byte-exatas, 56,1% dos documentos com mojibake, 10,7% dos byte-únicos
são near-dups**. Ao acrescentar 7 idiomas, não dá para herdar a nossa tranquilidade.

Ferramenta pronta: [`2608.28622` PUFFER](https://arxiv.org/abs/2608.28622) — MinHash-LSH incremental,
1 bilhão de documentos em ~1,75 h, **128 bytes/documento**, e **suporta retirada com escopo de
dataset** — a capacidade operacional que uma licença revogada exige.

---

# E. O VOCABULÁRIO — veredito sobre as três lacunas

## E1. ⭐⭐ Lacuna 2 PREENCHIDA — inflar o vocabulário não custa otimização

[`2608.16671`](https://arxiv.org/abs/2608.16671) — **cinco sementes pareadas**, IC de 95%,
intervenção backward-only separando geometria de causalidade: **acrescentar classes de saída que
nunca são alvo NÃO prejudica o aprendizado.**

E [`2511.17599`](https://arxiv.org/abs/2511.17599) nomeia o custo real, agora com **cross-entropy
comum**: o **tensor de logits ∝ lote × comprimento × V tem de ser materializado inteiro na VRAM**.
Fundir projeção e perda dá memória e velocidade medidas — **é o mecanismo exato do nosso teto de
micro-batch 2**, e o irmão do [`2608.03796`](https://arxiv.org/abs/2608.03796) (que mede com KL de
destilação, em H200).

⚠️ Mecanismo do dano ao lado: [`2605.06216` TIDE](https://arxiv.org/abs/2605.06216) — Zipf faz os
embeddings de tokens raros ficarem **cronicamente subtreinados**. **V grande compra linhas que nunca
aprendem.**
🟢 E um nulo útil: [`2104.10507`](https://arxiv.org/abs/2104.10507) — Monte Carlo, importance
sampling, somatório parcial compensado e NCE **empatam todos**. Se o softmax completo pesar,
qualquer aproximação serve.

## E2. Lacuna 3 CONTINUA VAZIA — e três dissociações resolvem a pergunta prática

| artigo | achado |
|---|---|
| [`2507.07824`](https://arxiv.org/abs/2507.07824) | tokenizador com **redução consistente de perplexidade e ZERO melhora em tradução** |
| [`2602.06973`](https://arxiv.org/abs/2602.06973) | fertilidade **e** OOV **menores**, e chrF++ até **30,15 pior** |
| [`2606.23943` QuechuaTok](https://arxiv.org/abs/2606.23943) | a **menor** fertilidade é comprada **memorizando formas de superfície** — 6,67% de acurácia de fronteira morfológica contra 83,33% |

⭐ **Fertilidade é correlato, não alavanca.** ⚠️ Com tensão registrada:
[`2509.05425`](https://arxiv.org/abs/2509.05425) prevê chrF a partir de fertilidade **mais
tipologia** com **R² 0,66 / 0,72** — preditivo, não causal.

⭐⭐ E [`2506.03149`](https://arxiv.org/abs/2506.03149) entrega o **método pronto** — descontinuidade
de regressão no corte K do ranking do BPE — para fazermos o desenho causal que ninguém fez, trocando
o desfecho por chrF/COMET.

## E3. Lacuna 1 CONTINUA VAZIA no cruzamento — e vale menos do que parecia

Quatro projeções, nenhuma é o cubo inteiro:

| artigo | o que cobre | o que falta |
|---|---|---|
| [`2608.25089`](https://arxiv.org/abs/2608.25089) | vocab × modelo em dado paralelo | modelos **monolíngues** |
| [`2511.20849` Length-MAX](https://arxiv.org/abs/2511.20849) | 124M/355M/1,3B **do zero, 5 rodadas cada** | **inglês só** |
| [`2510.21909`](https://arxiv.org/abs/2510.21909) | **~7.000 tokenizadores, 97 idiomas** | **sem LM treinado** |
| [`2605.26683`](https://arxiv.org/abs/2605.26683) | **700 runs**, vocab em ambiente crosslingual | **linguagens procedurais** |

⭐ **E a novidade que reduz o valor da lacuna:** [`2608.11361`](https://arxiv.org/abs/2608.11361)
mede **<2% de dispersão de bpb** na faixa ótima de V a 1,3–2,3B, e
[`2405.12413`](https://arxiv.org/abs/2405.12413) acha o vocabulário adaptado **relativamente pouco
importante** para idiomas de baixo recurso.

🔴 **E duas contradições ao "vocabulário maior":** `2605.26683` mede que **vocabulários MENORES
frequentemente melhoram a transferência** (mantêm palavras decomponíveis em fragmentos
compartilhados); `2510.21909` mede que **aumentar o vocabulário simplesmente NÃO reduz o imposto** —
o que existe é um **vocabulário ótimo POR IDIOMA**. E
[`2605.26935` DunbaaBERT](https://arxiv.org/abs/2605.26935) varreu 32k/52k/96k e achou **32k com o
melhor perfil de eficiência**.
⚠️ Tudo isso tensiona com `2407.13623` (vocab ótimo cresce com o compute).
⚠️ E [`2608.28151`](https://arxiv.org/abs/2608.28151) — **negativo pré-registrado**, 30 modelos: o
vocabulário compartilhado **perde 3,64% de bpb a 32k contra margem de 1%**.

## E4. ⭐ Dois algoritmos prontos

[`2508.04796` **Parity-Aware BPE**](https://arxiv.org/abs/2508.04796) — regra *fair-max* que a cada
fusão maximiza o ganho da língua **pior comprimida**: **Gini dos custos por idioma cai até 89%**,
impacto desprezível na compressão global, **sem evidência de degradação downstream**.

[`2012.15671` VOLT](https://arxiv.org/abs/2012.15671) — vocabulário por transporte ótimo: **−70% de
tamanho E +0,5 BLEU** em en–de, mais 52 direções do TED.

E a alternativa de escrita: [`2608.25904`](https://arxiv.org/abs/2608.25904) (EMNLP 2026) —
**467M/709M/1,03B do zero × oito idiomas**, quase a nossa configuração: **romanização dá a
transferência cross-lingual mais forte, e a vantagem cresce com escala**.
⚠️ Com dois contrapesos: **aplicar romanização como fine-tune depois PIORA os idiomas já cobertos**,
e [`2608.21384`](https://arxiv.org/abs/2608.21384) mede que **romanização AUMENTA a contagem de
tokens em 2–19%**. Não é contradição — **romanizar pode custar tokens e comprar transferência** —,
mas as duas medidas têm de ir juntas.

## E5. ⭐⭐ E o 90/10 que bate o 50/50

[`2404.07982`](https://arxiv.org/abs/2404.07982) — em linguagens **clonadas** perfeitamente
equivalentes, **90/10 rende melhor que 50/50 nas DUAS línguas**, e o efeito **amplifica com escala**.
⚠️ Os autores registram que em idiomas reais *"não é conclusivo"*.

---

# F. AS RÉGUAS — e duas delas são nossas

## F1. 🔴🔴 bpb está na lista das enviesadas para comparação entre escritas

[`2608.25089`](https://arxiv.org/abs/2608.25089) — **métricas normalizadas de uso corrente, o bpb
entre elas, carregam viés crosslinguístico enraizado em tokenização, codificação e ortografia**; o
comparador honesto é **NLL por sentença sobre sequências semanticamente equivalentes**.

[`2605.09015` LLiMba](https://arxiv.org/abs/2605.09015) confirma: *"comparações de perplexidade entre
escritas têm de contabilizar o byte-fallback, que **DEFLACIONA** a métrica para escritas
não-latinas."*

🔴 **O Bee-1G vai comparar 8 idiomas em 4+ escritas, e bpb é a nossa régua principal.** *"bpb por
idioma"* no Gate T4 precisa de comparador semanticamente equivalente, ou compara réguas diferentes.

⚠️ **E há um segundo problema, de comparabilidade externa:** `bits per byte` aparece **0 vezes em
581 resumos** de encoder-only e **1 vez em 2.276** da fatia de corpus. O campo reporta GLUE, MTEB,
nDCG e acurácia de benchmark. **Nenhum dos números destas literaturas é diretamente comparável ao
0,8207 bpb do Bee-350M**, e forçar a comparação seria §2g. Isso não invalida a nossa régua — ela é
correta *dentro* de um idioma — mas significa que **o Bee mede numa unidade que quase ninguém usa**,
e que toda comparação externa exige reproduzir o número do outro lado, como já fizemos com o
SmolLM2.

## F2. 🔴 O teto de tokens de saída é variável experimental oculta

[`2608.04160` **Mind the Cap**](https://arxiv.org/abs/2608.04160) — o gap medido oscila **até 57
pontos** conforme o orçamento de saída, e normalizar por comprimento move até 38,9. **540.000
decodificações, famílias de teste congeladas prospectivamente, correção de Holm.** E um nulo: uma
extensão de vocabulário tailandês **fecha 0,0 ponto** do gap no orçamento congelado.

🔴 **Com 8 idiomas de fertilidades diferentes, avaliar com `max_new_tokens` fixo mede a fertilidade,
não a capacidade.** Os nossos avaliadores usam `--max-len` fixo.

## F3. 🔴 Ajustar lei de mistura para decidir dado pode ser trabalho desperdiçado

[`2504.11393` **DataDecide**](https://arxiv.org/abs/2504.11393) — 25 corpora, até 1B, 100B tokens, **3
sementes**: **nenhum dos 8 métodos de lei de escala supera a fronteira de decisão-por-compute da
predição de escala única**. **Ranquear os modelos a 150M acerta ~80% das comparações no alvo de 1B**,
e métricas de verossimilhança contínua tornam benchmarks >80% previsíveis com **0,01% do compute**.

⚠️ Contradiz a nossa prática do E4 (ajustar lei de mistura), e está medido na nossa faixa.
⭐ E responde o Gate T2 por outro ângulo: **o proxy de 150M transfere — só não vale vesti-lo de lei.**

## F4. ⭐⭐ E a nossa §2i com número de terceiro

[`2503.10061`](https://arxiv.org/abs/2503.10061) — escala **é dependente de habilidade**, e não é
artefato da mistura (ablação extensa preserva a diferença). **Um conjunto de validação mal
especificado muda a contagem de parâmetros compute-ótima em quase 50%.**

**Escolher "a loss" para ajustar a lei já é escolher a alocação.** Confirmado de outro ângulo por
[`2604.22348`](https://arxiv.org/abs/2604.22348) (encoder em **cinco escalas**, saturação
**dependente da tarefa**: uma satura em 11M, outra melhora até 101M) e
[`2605.11513`](https://arxiv.org/abs/2605.11513) (**ganho sistemático de perplexidade sem ganho
downstream** — *bpb melhor sem capacidade melhor*, exatamente o que medimos).

## F5. ⭐ Piso de ruído externo, enfim

[`2503.09543` PolyPythias](https://arxiv.org/abs/2503.09543) — **45 runs de pré-treino, 9 sementes ×
5 tamanhos (14M–410M)**, ~7 mil checkpoints públicos, com **runs outliers identificáveis**. É a
referência externa de variância de semente que o projeto nunca teve.

E [`2608.17744`](https://arxiv.org/abs/2608.17744), pré-registrado: *"trocar só a semente aleatória
move o score em **7,7 pontos** — mais que todo efeito de dado e de receita que medimos"*, com os
autores reportando **seis falhas do próprio instrumento, cada uma pega por um controle**.

---

# G. GUARDAS NOVAS — todas baratas, todas da família "nada dá erro"

| guarda | origem | custo |
|---|---|---|
| **varredura de fatia de idioma 5%→95%**: o tokenizador com teto estrutural se move **1,7%**, o consertado **33,9%** — separa teto de tokenizador de escassez de dado | [`2608.26449`](https://arxiv.org/abs/2608.26449) | CPU |
| **`clean-window survival`** gravado no data card junto da **identidade do extrator** — cai a 0,153 em PDF convertido por visão contra 0,889 no C4 | [`2608.09093`](https://arxiv.org/abs/2608.09093) | CPU |
| **compatibilidade de licença**: procurar **NoDerivs sob rótulo CC-BY**, que proíbe tokenizar e anotar | [`2606.28867`](https://arxiv.org/abs/2606.28867) | leitura |
| **RoPE em bf16**: o erro acumula com o comprimento e o primeiro token é o maior contribuinte | [`2411.13476`](https://arxiv.org/abs/2411.13476) | teste |
| **desvio-do-colapso** como diagnóstico precoce: curvas de loss colapsam numa trajetória universal **precisamente quando** os hiperparâmetros estão ótimos | [`2509.25087`](https://arxiv.org/abs/2509.25087) | grátis |
| **triagem por watts, não por `utilization%`** — que lê 100% durante um hang | [`2608.05944`](https://arxiv.org/abs/2608.05944) | grátis |

⚠️ E uma que **desmonta uma tentação**: [`2605.13405`](https://arxiv.org/abs/2605.13405) identifica um
limite superior no fator de crescimento para *warmstart*, com **2× como o mais confiável**. Bee-350M
→ Bee-1G é **~2,9×** — acima da faixa.

---

# H. NOTA DE MÉTODO — a literatura, e os nossos próprios aparatos

## H1. O rigor, medido

| fatia | resumos | com semente / IC / pareado |
|---|---:|---:|
| objetivo e decoder-only | 1.415 | 63 (4,5%) — e **7 (0,5%)** cruzam rigor **com** ≤1B |
| encoder-only | 581 | 10 (1,7%) — **um único** com ≥3 sementes e desenho fatorial |
| MoE / Mamba / MLA | 2.301 | 29 (1,3%) · **9 (0,4%) pré-registrados** |
| compute-optimal / FLOPs | 99 no escopo | **1 (1,0%)** menciona sementes |
| leis de escala / parâmetros | 932 | 27 (2,9%) mencionam "seed" |
| janela de contexto | 1.405 | 24 (1,7%) |

⭐ **E os pré-registrados são desproporcionalmente os achados mais valiosos de cada relatório.**

## H2. Os defeitos que os agentes acharam nos próprios aparatos

Três, todos da família "nada dá erro", e todos pegos por **imprimir e ler** em vez de conferir o
agregado:

1. **`\b(language model|LLM|…)\b`** — a fronteira de palavra final **falha em "language modelS"** e
   em "OpenEuroLLM". Barrou dois artigos relevantes na página de teste;
2. **`\b` após `tokeniz`, `vocabular`, `pretrain`** — **nunca casava "tokenizer" nem "vocabulary"**.
   Pego por um invariante no espírito da §2t (*"título com termo nuclear não pode ser barrado"*),
   que disparou em **91 casos**; corrigido, os barrados caíram de 1.580 para 1.021 e **20 candidatos
   novos apareceram**;
3. ⭐ e a lição de desenho: **os quatro melhores desses 20 já tinham sido achados pelas sondas
   dedicadas por lacuna**. **A redundância entre filtro geral e sonda dirigida foi o que impediu o
   defeito de virar omissão.**

## H3. Os limites de cobertura, declarados

- **`Parameters` não funciona como termo temático — funciona como fatia temporal.** Tem **406.798**
  resultados; 13 páginas cobrem **uma semana**. E o `start` alto **não** traz artigos antigos;
- **`Corpus`** cobriu 2.200 de **14.800** — cinco meses;
- **`Token` retorna arquivos byte-idênticos a `tokenizer`** (o arXiv radicaliza o termo): 8 páginas,
  **zero registros únicos**;
- **Termos que não existiam na largura pedida:** `Encoder-Only` tem 581 (não 2.200), `Sparse MoE`
  114, `Compute-Optimal` ~1.036, `Vocabulary Size` 362, `Data Scraping` **41**, `Heuristic
  Filtering` **37**, `Context Window` 1.289 (coberto **por inteiro**).

## H4. 🔴 As lacunas que sobrevivem, testadas explicitamente

1. **Dedup near-duplicate ENTRE idiomas: zero** — e é a interação direta com a recomendação D1;
2. **Nenhuma lei de escala para tradução** (qualidade × parâmetros × dado paralelo) em nenhuma
   fatia;
3. **Nenhum desenho causal fertilidade → qualidade de tradução** — e o método existe (`2506.03149`);
4. **Zero medições de memória de TREINO em GPU de 8–16 GB**, e **zero** medindo a pegada de VRAM de
   treinar MoE/MLA/Mamba a ~1B;
5. **`seq_len` de pré-treino do zero em ≤1,5B para tradução: zero** — e a razão é **estrutural**: a
   comunidade de MT com contexto migrou inteira para prompting de modelo pronto;
6. **MoE multilíngue treinado do zero em ≤1,5B: zero** — toda a evidência vem de sondar modelos de
   30B–671B já treinados;
7. **Encoder como classificador de qualidade de corpus, medido como objeto próprio: zero** — dois
   artigos **usam** um e **nenhum reporta precisão, recall ou o pareado com-e-sem**.
   ⭐ **Nós temos um, e ele É medido:** `docs/fineweb-edu-pt.md` reporta **Pearson 0,705**, **−35%**
   de erro absoluto médio, **F1 0,723 / acurácia 78,0%** e a **curva de retenção completa** com o
   joelho em ~10%. 🔴 **Mas ele nunca foi aplicado ao corpus**, arquivado por um argumento de
   **2026-08-04** — três dias antes de o bug de rótulos ser achado, e a quinta hipótese da §5. O
   argumento está agora contradito por `2604.28075`. Ver `plano-bee-1g.md` §5;
8. **Licença do fineweb-2 discutida em artigo: zero.**

⚠️ Em todos os casos a formulação é *"este instrumento não conseguiu mostrar"*, não *"não existe"* —
a §2q, que já nos custou duas retratações nesta sessão.
