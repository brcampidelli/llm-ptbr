# Estudo — `mikeroyal/Machine-Learning-Guide` (709 ★)

> **2026-08-19.** Análise do repositório pedido, com 5 agentes em paralelo sobre fatias
> disjuntas do arquivo, mais três medições feitas fora dos agentes (podridão de links,
> cobertura de termos, forense de timestamps). Todos os números abaixo foram medidos, não
> estimados.

---

## Veredito em uma frase

**É um índice de links de engenharia acadêmica de ~2021, com uma prateleira de LLM pendurada
por fora em meados de 2023, e não tem uma única linha aproveitável para quem pré-treina um
modelo em português — nem sobre português, nem sobre pré-treino, nem sobre custo.**

Nota consolidada: **2/10** para este projeto. Leitura recomendada: **quinze minutos**, e só
das 29 linhas das seções de LLM, como quiz de "quem morreu".

---

## 1. O que o repositório é, em números

| | |
|---|---|
| arquivos | **3**: `README.md` (254 KB), `Contributing.md` (686 B), `Getting Started with ML.py` (**108 bytes**) |
| linhas | 2.410 |
| links | 1.299 (919 únicos e não-imagem, em 352 domínios) |
| último commit real | **2024-01-04** (o `updated_at` de 2026-08-12 é metadado, não conteúdo) |
| estrelas | 709 · 65 forks · CC BY 4.0 |

Não há código, benchmark, número ou metodologia. É um **diretório de links**, e o arquivo
`.py` de 108 bytes é a totalidade do código do repositório.

---

## 2. A datação tem três camadas, e a mais velha manda

O último commit é de 2024, mas o conteúdo não. Três evidências independentes datam o miolo
em **2021–2022**:

**(a) Forense de timestamp.** Os links da Amazon preservam o parâmetro `qid`, que é o
timestamp Unix da busca. **Doze dos treze caem entre 04:56:35 e 05:02:49 UTC de 04/06/2022** —
uma janela de **6 minutos e 14 segundos**. A prateleira de 46 livros não foi curada por
leitura; foi colada de uma única sessão de busca na Amazon, **cinco meses antes do ChatGPT**.

**(b) Tempo verbal.** O texto do XeSS diz que a arquitetura Arc da Intel *"terá"* GPUs — no
futuro. O ARKit é descrito como "versão mais recente 3.5" (2020). O PyTorch é "desenvolvido
pelo Facebook AI Research" (renomeado Meta AI em 2021). O Scala descreve o **Dotty** como "o
compilador de pesquisa que *vai virar* o Scala 3" — o Scala 3 saiu em maio de 2021.

**(c) Estilo de link no índice.** Das 29 entradas do índice, 25 usam URL absoluta e
**exatamente 4 usam âncora relativa**: as três subseções de LLM e a de YouTube. Estilo
diferente = passe de edição posterior. O esqueleto é pré-LLM; o LLM foi pendurado nele.

Isso explica o achado central: **a seção 1 inteira (Learning Resources, 76 links) não recebeu
nenhuma das duas atualizações.** Nenhum dos 76 links é sobre modelo de linguagem.

---

## 3. O que medi fora dos agentes

### 3.1 Podridão de links: **baixa** — e isso é a favor do repositório

Amostra de 150 links sorteados com semente fixa (20260819), seguindo redirecionamentos:

| status | n | leitura |
|---|---:|---|
| 200 | 124 | vivos |
| 403 | 8 | bloqueio de bot (4 são mathworks.com, 1 Intel) — provavelmente vivos |
| 302/301 | 8 | redirecionamento que não resolveu |
| 404 / 000 / 400 | **10** | **mortos de fato (6,7%)** |

⚠️ **O problema deste guia não é link morto.** 83% resolvem. O problema é que os links **vivos
apontam para coisas que morreram como escolha técnica** — o que nenhum verificador de HTTP
detecta. `github.com/facebookresearch/fairscale` responde 200 e está em modo de manutenção há
anos; `mxnet.incubator.apache.org` responde e o MXNet foi aposentado no Apache Attic.

### 3.2 Cobertura de termos no arquivo inteiro (2.410 linhas)

| termo | ocorrências | | termo | ocorrências |
|---|---:|---|---|---:|
| **MATLAB** | **103** | | attention | **0** |
| **Simulink** | **47** | | scaling law | **0** |
| LLM | 60 | | Chinchilla | **0** |
| GPT | 55 | | perplexity | **0** |
| RAG | 15 | | quantiz* | **0** |
| pretrain | 12 | | FlashAttention | **0** |
| LoRA | 6 | | FSDP | **0** |
| tokeniz* | 6 | | PEFT | **0** |
| transformer | 9 | | torch.compile | **0** |
| BERT | 3 | | **Portug*** | **0** |

⭐ **A palavra "attention" não aparece uma única vez em 2.410 linhas.** Um guia de Machine
Learning de 254 KB, congelado em 2024, sem uma menção ao mecanismo que define a década.

⭐ **"MATLAB" aparece 103 vezes; "Portug" aparece zero.** Assim como "Brazil" e "Spanish".
Para um projeto de LLM em português, o guia é integralmente mudo sobre o eixo que importa.

### 3.3 Duplicação literal

O parágrafo do **Keras aparece 7 vezes** no arquivo, o do **cuDNN 6**, o do **Spark 6**. Nas
seções de RL, CV e NLP, **49 de 53, 22 de 24 e 20 de 27** linhas de ferramenta são
byte-idênticas a linhas de outras seções. As "seções" não são curadorias diferentes; são a
mesma lista recolada com títulos diferentes.

---

## 4. Erros factuais no texto (verificados no arquivo)

1. 🔴 **A descrição do PyTorch está errada.** Linha 235: *"PyTorch is a library for deep
   learning on irregular input data such as graphs, point clouds, and manifolds"*. Isso é a
   descrição do **PyTorch Geometric**. O item mais importante da lista inteira está trocado.
2. 🔴 **A definição de Reinforcement Learning é a de deep learning.** Linha 1166: linka para
   `ibm.com/cloud/learn/**deep-learning**` e define RL como *"uma rede neural com três ou mais
   camadas"*, terminando com "o aprendizado pode ser supervisionado, semissupervisionado ou
   não supervisionado" — a taxonomia da qual RL é justamente a exceção.
3. `[Amazon SageMaker](https://aws.amazon.com/robomaker/)` — nome e URL de produtos diferentes.
4. `[OpenAI](https://gym.openai.com/)` — a biblioteca rotulada como a empresa; URL morta,
   sucedida pelo Gymnasium desde 2022.
5. O `Tokenization` do Apache OpenNLP linka para a Wikipédia de
   **`Tokenization_(data_security)`** — mascaramento de número de cartão de crédito.
6. Duplicata de livro com **título e autor fundidos**: "Machine Learning in Action by Ben
   Wilson" mistura Peter Harrington (2012) com Ben Wilson (2022).
7. "ChatGPT Plus, US$ 20/mês" listado como framework de ML.
8. A alegação "Vicuna atinge >90% da qualidade do ChatGPT por US$ 300" aparece **duas vezes,
   sem ressalva** — número que veio de GPT-4-como-juiz e foi desmontado ainda em 2023.

---

## 5. Onde o guia gasta o espaço

| bloco | linhas | % do arquivo |
|---|---:|---:|
| MATLAB + C/C++ + Java + Scala + R | **503** | **20,9%** |
| (+ Julia) | 587 | 24,4% |
| Python | 122 | 5,1% |
| TensorFlow + Core ML | 203 | 8,4% |
| CUDA | 78 | 3,2% |

**As cinco linguagens que o projeto não toca ocupam 4,1× o espaço dado ao Python.** A seção
C/C++ sozinha (151 linhas) é maior que a de Python (122).

E dos 103 "MATLAB", **60 estão fora da seção MATLAB** — infiltrados em Deep Learning,
Reinforcement Learning, Computer Vision e NLP. Não é um capítulo que se pula.

⭐ **Isso identifica a origem e o público.** O vetor MATLAB + Simulink + HDL + FPGA/SoC +
robótica + UAV + lidar é o currículo de **engenharia elétrica e de controle**, não o de quem
treina modelo de linguagem. Somado às 3 seções de *runtime de fabricante* (PyTorch,
TensorFlow, **Core ML** no mesmo nível) e aos 26 links `docs.microsoft.com`, o perfil é de
**DevRel de plataforma de nuvem**, por volta de 2021. Para o Bee isso não é detalhe estético:
significa que **o autor nunca teve o problema que este projeto tem**, e por isso o guia não
pode ter a resposta.

---

## 6. O que sobra de aproveitável — a lista honesta

De ~1.300 links, sobra isto:

| item | para quê | ressalva |
|---|---|---|
| **SkyPilot** | orquestrar job em spot em várias nuvens com recuperação automática — transforma a regra de `$/B tokens` em automação | para runs de poucos dias num pod RunPod, o setup pode não pagar |
| **llama.cpp + Ollama + LM Studio** | **distribuir** o Bee-350M, não treinar. Em GGUF Q8 é exatamente o tamanho em que esse canal importa | o guia lista as três e nunca conecta os pontos |
| **oasst1 / oasst2** | dataset de SFT multi-turno **com PT-BR real** e licença aberta | citado como projeto (morto), não como dataset |
| **Mining Massive Datasets**, cap. 3 | MinHash/LSH — a ferramenta canônica do item "histograma de repetição interna" do checklist | PDF gratuito; é matemática, não envelhece |
| **Logbook do OPT-175B** | o relato mais franco que existe sobre instabilidade de pré-treino | referência, não ferramenta |

⚠️ **E um alerta que o guia não dá:** o **ShareGPT** está listado sem ressalva. É o exemplo
canônico de dado de SFT com licença duvidosa e contaminação de benchmark. **Não usar.**

---

## 7. O que um guia de 2026 teria e este não tem

**Pré-treino** (a lacuna mais grave, dado o que este projeto faz): Megatron-LM, NeMo,
torchtitan, GPT-NeoX, litGPT, **nanoGPT** — ausência absurda, já que o `llama2.c` do mesmo
autor está listado —, llm.c, **OLMo** (o stack de pré-treino mais reproduzível que existe, e o
mais próximo do que o Bee é), FSDP, FlashAttention-2/3, Liger, muP, FP8.

**Dados:** datatrove, **FineWeb-2** (tem português; é disparado o item mais relevante que
falta), HPLT v2, CulturaX, Dolma, dedup MinHash/LSH, descontaminação. O guia trata corpus como
se não existisse.

**Pós-treino — a fase atual:** DPO, KTO, ORPO, SimPO, GRPO, TRL, PEFT, Axolotl,
LLaMA-Factory, Unsloth, reward models, rejection sampling. O DPO já existia em 2023 e também
não está lá.

**Avaliação:** nenhum harness. Sem lm-evaluation-harness, lighteval, OpenCompass. E nada de
português: nem Poeta/Napolab, nem ENEM/BLUEX/OAB, nem Sabiá, Tucano, Bode ou Cabrita.

**Custo:** nenhum `$/hora`, nenhum `$/B tokens`, nenhuma lei de escala. Para um projeto com
orçamento de dezenas a poucas centenas de dólares, é a omissão que sozinha invalida o guia.

---

## 8. A lição de método que este estudo produziu

⭐ **Podridão de link e obsolescência técnica são coisas diferentes, e só uma é fácil de
medir.** 83% dos links respondem 200. Um script de verificação daria "guia saudável". A
obsolescência real — FairScale em manutenção, MXNet no Attic, TGI perdendo para o vLLM,
`ggml` substituído por GGUF antes mesmo do congelamento — não produz nenhum código HTTP.
**Métrica fácil de medir sinalizando o oposto da verdade** é a mesma família do `chrF++` que
premia quem copia a fonte, e do léxico de sentimento cujos 79% são quase uma palavra só.

⚠️ **E um erro meu, no caminho, da mesma família.** O Python gravou o arquivo de URLs em
Windows, com `\r\n`, e cada URL levava um carriage return invisível no fim. O `curl` falhou
nas 149 e devolveu `000` em todas. **O relatório teria sido "100% dos links estão mortos" —
dramático, quotável e inteiramente falso.** O que salvou foi a implausibilidade: 100% de
mortalidade é impossível, e impossibilidade é sinal de defeito no aparato, não no fenômeno.
Terceira vez que essa regra paga a conta neste projeto.

---

## 9. Para quem este guia serve

Não para este projeto — mas ele tem 709 estrelas, e isso não é acidente. Ele serve a quem
precisa **escolher entre Azure ML, SageMaker e Vertex AI**, ou passar na certificação DP-100,
ou montar uma ementa de engenharia com MATLAB e Simulink. É um bom índice de fornecedor para
2021–2022. O erro seria lê-lo como um guia de LLM.
