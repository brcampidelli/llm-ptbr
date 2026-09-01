# Triagem arXiv para o Bee-1G — tokenizador, multilingualidade, throughput e custo

> **O que é:** duas rodadas de leitura sobre **~7.800 resumos** do arXiv (jul–ago/2026), feitas em
> 2026-08-31/09-01 para responder às perguntas do `docs/plano-bee-1g.md` **antes** de gastar. Segue
> o formato do `docs/triagem-17-fontes-2026-08-21.md`: cada achado com o que resolve, **a escala em
> que foi medido**, e veredito.
>
> **⭐ O resultado que importa:** **cinco achados contradizem o plano que eu commitei** (`1e06676`),
> e um sexto dissolve a restrição que o organizava. As correções estão aplicadas lá; aqui fica a
> evidência.
>
> **🔴 E duas lacunas que declarei não existiam.** Ver §9.

---

# PARTE A — vocabulário, tokenizador e multilingualidade

## 1. ⭐⭐⭐ A restrição central do plano pode não existir

O plano dizia, como *ressalva 1*: **"250k × d_model 2048 = 512M, metade de um modelo de 1B"**, e
concluía que **~128k** era "o meio defensável". A aritmética está certa. A **configuração** é que era
ruim, e a literatura de 2025-2026 ataca essa equação por sete caminhos independentes.

| artigo | escala medida | o que faz | ganho relatado |
|---|---|---|---|
| ⭐⭐ [`2605.29459`](https://arxiv.org/abs/2605.29459) **Kronecker Embeddings** | GPT-2 **124M** / 2,5B tok, **3 sementes** | fatoração determinística caractere-posição no lugar da tabela `V×d` | **−91 a −94%** dos parâmetros treináveis de entrada · **−2,5 ± 0,2%** de loss de validação · **~1,43×** menos passos |
| ⭐⭐ [`2501.16975`](https://arxiv.org/abs/2501.16975) **Over-Tokenized** | — | **desacopla** vocabulário de ENTRADA e de SAÍDA | relação log-linear entrada↔loss **independente do tamanho do modelo**; alcança baseline do **dobro** sem custo adicional |
| ⭐ [`2502.01637`](https://arxiv.org/abs/2502.01637) **SCONE** | 1B vs 1,9B | embeddings de n-gramas **fora do acelerador** | 1B residente **supera** baseline de 1,9B com ~metade dos FLOPS |
| ⭐⭐ [`2608.00582`](https://arxiv.org/abs/2608.00582) | — | adapta o tokenizador a **vocab FIXO** | ucraniano **−33,5%** de tokens · inglês/europeus ≤0,05% · **78,5%** das linhas mantêm o mesmo ID |
| ⭐ [`2605.29379`](https://arxiv.org/abs/2605.29379) **BrahmicTokenizer-131K** | orçamento fixo 131k | poda de escritas fora de escopo + 2.372 slots mortos realocados por programação linear, **drop-in** | **−26,7%** de tokens no índico, fertilidade em inglês **1,235 vs 1,232** do o200k |

**⭐ A variante de runtime do Kronecker reconstrói o embedding de um buffer de 4,5 MB no lugar de uma
tabela de 2,15 GB em vocab 131.072**, com 0,01–0,24% de overhead. E é **o único artigo do lote
inteiro com semente e barra de erro no número principal** — o que, pelas regras deste projeto, o põe
à frente de qualquer outro candidato.

⚠️ **E o limite empírico que faltava:** [`2204.08832`](https://arxiv.org/abs/2204.08832) mede que a
razão *params-de-vocab / params-totais* pode ir a **20% para BPE/WordPiece** e **40% para
morfológico**. Os 50% que eu calculei estão **fora dos dois** — não é que vocab grande seja
impossível, é que a configuração que escolhi para ilustrá-lo era ruim.

**Veredito:** a *ressalva 1* **não é mais uma restrição, é um item de gate**. O Gate T1 ganha braços
de **arquitetura de embedding**, não só de tamanho de vocab.

---

## 2. 🔴 A base do Gate T1 é contradita ABAIXO de 1B

O plano se apoiava em **One Tokenizer To Rule Them All** (`2506.10766`): tokenizador universal custa
<1% na língua primária e rende +18,9% ao expandir. Medido em **3,3B**.

🔴 [`2608.07727`](https://arxiv.org/abs/2608.07727) mediu o oposto: **5 GPT-2 treinados do zero** — 4
monolíngues com tokenizador próprio de 32k contra 1 multilíngue com 64k compartilhado.
**O monolíngue venceu nos 4 idiomas.**

⭐ **A variável que os separa é escala**, e o Bee-1G fica no meio. Some-se
[`2605.26683`](https://arxiv.org/abs/2605.26683) — **700 runs controlados**, onde vocabulários
**menores frequentemente melhoram** a transferência — e *"construir o tokenizador multilíngue
agora"* **deixou de ser decisão herdada da literatura e virou medição a fazer.**

⚠️ **Contrapeso, e é forte:** [`2506.03101`](https://arxiv.org/abs/2506.03101) mediu que **modelos
pequenos predizem com fidelidade** as diferenças de *tokenizador* que aparecem nos grandes, a uma
fração do compute. Ou seja: **o Gate T1 em proxy é metodologicamente sólido** — é o Gate T2 que tem
problema (§3).

---

## 3. 🔴🔴 A maldição da multilingualidade se inverte com a escala — e isso ameaça o Gate T2

| artigo | escala | veredito |
|---|---|---|
| [`2311.09205`](https://arxiv.org/abs/2311.09205) | >10.000 modelos, 250 idiomas, **≤45M** | 🔴 idiomas de **alto recurso pioram consistentemente** |
| [`2510.25947`](https://arxiv.org/abs/2510.25947) | **1,1B e 3B**, 25→400 idiomas | ⚪ *"não observamos maldição significativa"* |

**Diretamente opostos.** O plano citava só o primeiro, como se fosse consenso.

🔴 **O problema de método que isso cria:** o Gate T2 propõe decidir a razão de mistura em **mini-runs
de 150M** — perto da escala onde a maldição **aparece** — para um alvo de **1B**, onde ela **não
aparece**. O proxy pode reprovar uma mistura que funcionaria no alvo.

⚠️ E `2506.03101` **não cobre este caso**: ele valida proxy pequeno para diferenças de
**tokenizador**, não para **razão de mistura**. São coisas diferentes.

**Veredito:** o Gate T2 precisa de um **braço de transferência** — ao menos um ponto medido em duas
escalas, para saber se o proxy transfere — ou decide sobre um fenômeno que não é o do alvo.

---

## 4. 🔴 Fertilidade é métrica de CUSTO, não de qualidade — e o critério do Gate T1 era só ela

O critério declarado: *"a fertilidade em PT não pode piorar mais que 15%"*. **É insuficiente**, por
três medições independentes:

- 🔴 [`2607.24276`](https://arxiv.org/abs/2607.24276) — a correlação fertilidade→compreensão é
  **largamente explicada pela disponibilidade de recurso do idioma**, não pelo tokenizador;
- 🔴 [`2310.08754`](https://arxiv.org/abs/2310.08754) — 24 LLMs a 2,6B: fertilidade e *parity*
  **não são sempre preditivas**. Mede também o preço do erro: tokenizador inglês-cêntrico custa
  **até +68% de treino**, e um multilíngue nas 5 europeias mais frequentes exige vocab **3× maior**;
- ⭐⭐⭐ [`2607.23362`](https://arxiv.org/abs/2607.23362) **JOLT** — com certificado de
  quase-otimalidade: **o BPE já está a 1–2% da compressão alcançável**, e o ganho algorítmico
  disponível é **≤0,78%**. **Mudar a cobertura de idiomas compra 2,4–8×.**

⭐ **O JOLT reordena a fila de trabalho inteira:** não há ganho a extrair trocando de algoritmo de
tokenização; o ganho está em **quais idiomas entram**. Isso simplifica o Gate T1 e transfere o peso
para o Gate T2.

**Veredito:** o Gate T1 ganha um **braço de qualidade** (bpb por idioma no mesmo holdout), senão
aprova um tokenizador que comprime bem e não ensina.

---

## 5. ⭐ O parâmetro que decide se o run sobrevive à troca de vocab

Dois artigos convergem, e nenhum estava no plano:

- [`2506.15025`](https://arxiv.org/abs/2506.15025) — com vocab ≫ largura entra-se no *"regime Large
  Vocab"*, onde a razão ótima **LR-embedding / LR-oculto** escala **Θ(√width)** e não Θ(width).
  Validado pré-treinando **1B do zero**;
- [`2605.21486`](https://arxiv.org/abs/2605.21486) — **o benefício inteiro do μP sobre a
  parametrização padrão com AdamW vem simplesmente de maximizar o LR da camada de embedding**; em SP
  esse LR é um **gargalo que induz instabilidade**.

⚠️ **Trocar 32k por 128k muda a regra de LR.** Este projeto já perdeu **7 de 15 braços** por grade de
LR mal centrada (§2f). Vira item de checklist do Gate T3, não nota de rodapé.

---

## 6. ⭐⭐ A referência de build mais próxima que existe — e o defeito que ela documenta

[`2608.30114`](https://arxiv.org/abs/2608.30114) **Manacá-1B** (31/08/2026) — **1,72B decoder
treinado do zero para PT-BR**, pipeline conteinerizado, zero passos NaN ou pulados, log completo
liberado. Bate Tucano-1b1 e Tucano-2b4 em LAMBADA-PT.

⭐ **E o que o torna o artigo mais útil do corpus inteiro para nós não é o resultado:** traz **erro
padrão e teste pareado de significância em toda comparação, com o harness validado contra números
publicados**. É a nossa §2aa escrita por outra pessoa, e vale como modelo de relatório.

E [`2606.22722`](https://arxiv.org/abs/2606.22722) **moBERTo** — ablações em português com um
resultado **contrário** útil: adaptar o tokenizador **melhora tarefas de nível-token e DEGRADA
recuperação em contexto longo**. Um eixo de custo que ninguém costuma medir.

### 🔴 O defeito silencioso do Manacá — verificado contra o Bee, e o Bee está limpo

> Converter tokenizador **SentencePiece com normalização de caixa** para o formato HF *fast*
> **descarta o normalizador em silêncio** → todo token capitalizado vai para byte-fallback →
> **LAMBADA-PT caiu de 45,3 para 25,0**, invisível na métrica agregada, conserto de uma linha.

Família exata das nossas lições: **nada dá erro, a métrica sai, o número está errado.** Verificado em
`models/bee-150m-v3-base` — no **artefato**, não no script (§2aa):

| verificação | resultado |
|---|---|
| normalizador no objeto **carregado** | `NFC()` — **sobreviveu** |
| `byte_fallback` | `False` — é ByteLevel BPE; o mecanismo que quebrou **não existe aqui** |
| pior delta minúscula→Maiúscula (10 pares) | **0 tokens** |
| texto real, 400 docs — inflação por capitalização | **−0,72%** (capitalizar **economiza**) |

`Brasil` = 1 token e `brasil` = 1; `Joao` = **2** e `joao` = 3. Não se aplica por dois motivos
independentes: nunca passamos por SentencePiece, e nunca usamos normalização de caixa.

⭐ **A verificação fica como item permanente do checklist** — *"texto capitalizado não pode inflar a
contagem de tokens"* é uma linha, roda em segundos, e teria poupado 20 pontos de LAMBADA-PT.

### 🔴🔴 Segunda verificação contra o nosso artefato — e esta acusa

[`2410.23684`](https://arxiv.org/abs/2410.23684) mediu que BPE byte-level produz **tokens
incompletos** (merges que atravessam fronteira de caractere UTF-8, indecodificáveis sozinhos) e que
eles disparam alucinação — **−90% no Llama-3.1 só trocando a tokenização da MESMA frase**. Nosso
tokenizador é exatamente dessa família. Medido:

| | |
|---|---|
| tokens multi-byte incompletos no vocab de 32.000 | **31** (0,10%) |
| bytes avulsos (fallback, base inevitável do ByteLevel) | 128 |
| ⭐ **exposição real em PT** — 800 docs, 319.258 tokens | **23 ocorrências = 0,007%** |

**Em português o defeito existe e está praticamente não exercitado.** ⚠️ Mas os *quais* importam:
`20 c3` (espaço + prefixo do latim acentuado), `e3 81` (**hiragana**), `20 d0` (**cirílico**),
`f0 9f` (emoji). **Eles se concentram na borda do idioma em que o tokenizador foi treinado** — e num
vocab multilíngue essa borda é o corpo.

#### O censo exato — não amostral, conta os 32.000 tokens

| escrita | tokens no vocab | | escrita | tokens no vocab |
|---|---:|---|---|---:|
| latim básico | 31.111 (97,22%) | | **árabe** | 🔴 **0** |
| latim acentuado | 5.246 (16,39%) | | **han (CJK)** | 🔴 **0** |
| cirílico | 7 (0,02%) | | **hiragana/katakana** | 🔴 **0** |

🔴 **Três dos oito idiomas-alvo do Bee-1G não têm um único token no vocabulário atual.** Escrita com
zero tokens só admite **fallback de byte** — 1 token por byte, **100% de incompletude** — contra os
**0,218 tok/byte** do PT. Isso não é uma previsão: é uma propriedade contável do artefato.

⭐ **Vira um terceiro eixo do Gate T1** (custo · qualidade · **incompletude por escrita**), e ⭐ dá à
**expansão in-place** uma justificativa nova: **não há conteúdo não-latino no 32k para conflitar**,
então acrescentar merges de árabe/han/kana não perturba nada que exista.

---

## 7. Achados que entram sem contradizer nada

| artigo | escala | o que dá |
|---|---|---|
| ⭐ [`2407.13623`](https://arxiv.org/abs/2407.13623) | **33M–3B** | 🔴 **corrige minha premissa** de que leis de vocab só existem ≥1,3B. 32K→43K melhora ARC-C de 29,1 → 32,0 **com os mesmos FLOPs** |
| ⭐ [`2510.06128`](https://arxiv.org/abs/2510.06128) **Parallel Tokenizers** | 13 idiomas, do zero | treina tokenizadores **monolíngues** e **alinha os vocabulários** por dicionário bilíngue — vence baselines multilíngues |
| ⭐ [`2605.01188`](https://arxiv.org/abs/2605.01188) | **988 modelos**, 50M–7B | parâmetros escalam com o dado em **BYTES, não em tokens**; a taxa de compressão ótima **diminui** com o compute |
| ⭐ [`2606.14122`](https://arxiv.org/abs/2606.14122) | **355M**, 80B tok | validade UTF-8 converge com **atraso de ~2×** em relação à perplexidade — gerar byte válido é capacidade separada, e perplexidade **não a mede** |
| [`2410.23684`](https://arxiv.org/abs/2410.23684) | Llama-3.1 | BPE byte-level cria **tokens incompletos**; **−90% de alucinação** só trocando a tokenização da MESMA frase |
| [`2510.16987`](https://arxiv.org/abs/2510.16987) **UTF8Tokenizer** | — | mapeia texto **exatamente** para bytes UTF-8, sem IDs fora de faixa; **14×** mais rápido, tabela 256×d |
| [`2601.05833`](https://arxiv.org/abs/2601.05833) **Peek2** | — | pré-tokenizador byte-level **sem regex**, **2,48×**, **saída idêntica** — torna barato consertar o `2608.26449` |
| [`2410.11627`](https://arxiv.org/abs/2410.11627) | mT5 × ByT5 | a comparação **controlada** que o plano citava por número solto: mesma arquitetura, mesmo objetivo, mesmos dados, difere **só** em subword × caractere |

---

# PARTE B — throughput, hardware e custo

> Fatia própria: **800 entradas** de `all:throughput` (2026-07-03 → 2026-08-31), 446 barradas no
> portão de domínio, 41 resumos lidos por inteiro, **25 devolvidos**. Dos 108 descartados por regime
> de cluster, **os 108 foram auditados um a um** e **4 resgatados** — porque filtro que nunca é
> conferido pode estar jogando fora o sinal.

## 8. ⭐⭐ O mecanismo exato do nosso teto de micro-batch 2

O vilão que este projeto identificou — o tensor de logits `batch × seq × vocab` com upcast fp32 — é
o que [`2608.03796`](https://arxiv.org/abs/2608.03796) **remove**: perda KL **fundida e *chunked* que
nunca materializa o tensor de logits do tamanho do vocabulário**, tornando a memória de pico
**linear no comprimento da sequência**. Permitiu treinar a **4× o contexto (32.768 tokens) numa GPU
só**, com bench isolado da própria camada de saída de 4K a 256K tokens. Código liberado.

⚠️ **Ressalva honesta:** medido em H200, e a perda é **KL de destilação, não CE de pré-treino**. O
kernel e o argumento de memória transferem; o número não.

E três medições independentes dizem que **a camada de saída domina em modelo pequeno**:

| artigo | escala | achado |
|---|---|---|
| ⭐⭐ [`2607.09957`](https://arxiv.org/abs/2607.09957) | 0,6B, Apple M2 | trocar vocab **151k → 64k** deu **1,63× de speedup**. *"A projeção de vocabulário se torna um custo de decode mais importante depois que a quantização reduz o custo relativo dos blocos Transformer"* |
| [`2608.26926`](https://arxiv.org/abs/2608.26926) | **Gemma 3 1B** | os alvos mais promissores são os blocos FFN **e a matriz de embedding**; e 🔴 **quantização uniforme prejudica modelo pequeno** — contradiz a intuição vinda de modelo grande |
| [`2608.02703`](https://arxiv.org/abs/2608.02703) **ARCHead** | — | backends **mantêm a LM-head em BF16/FP16** mesmo quantizando os blocos; comprimi-la dá **3,7–3,9×** de armazenamento com +0,006 de CE e **<2%** de mudança de throughput |

⭐ **O `2607.09957` é a nossa pergunta medida no sentido inverso:** quando o resto do modelo fica
barato, a camada de saída passa a dominar. **O regime existe e é alcançável por baixo, não só por
cima.**

### E se o Bee-1G mantiver a decodificação restrita ao esquema

| artigo | achado |
|---|---|
| [`2608.03065`](https://arxiv.org/abs/2608.03065) | a latência dos métodos de decodificação restrita **escala linearmente com o vocabulário**; o PSC a torna **independente do vocab**, até **700×** mais rápido |
| [`2608.12574`](https://arxiv.org/abs/2608.12574) **Trie Automata** | sete famílias de tokenizador, **vocab de 32K a 262K**: custo por passo **plano**, 7× mais rápido que o XGrammar |

⚠️ Ir a 128k **quadruplica o custo da máscara** na implementação ingênua. A restrição ao esquema é o
nosso ganho de runtime medido (**+10,0 pp**, `docs/restricao-ao-esquema`) — vale saber que ela tem
preço em vocab grande, e que o preço é evitável.

---

## 9. ⭐⭐ Como medir throughput — e a régua que o nosso §4 usa tem viés medido

⭐⭐ [`2608.05944`](https://arxiv.org/abs/2608.05944) é **o item de maior valor metodológico das duas
fatias**. Traz tabela de triagem **por watts de placa** que separa compute / comunicação /
fome-de-dado / deadlock / ocioso — **porque `utilization%` lê 100% durante um hang de NCCL**. É o
nosso §4 confirmado por terceiro, com um número. E traz um **portão de invariante de 2,7 segundos**
que converte falhas silenciosas de horas em rejeição instantânea — a nossa "guarda antes do passo 1"
escrita por outra equipe.

⭐ E derruba folclore com A/B controlado: ler do NFS a cada passo **empata** com cache local
pré-tokenizado (**~53k tok/s**).

| artigo | escala | o que muda para nós |
|---|---|---|
| ⭐ [`2608.03880`](https://arxiv.org/abs/2608.03880) | **~3.000 runs**, 6 GPUs, dispositivo único | modelo linear MFU→potência ajusta em **toda** GPU **desde que o workload seja compute-bound**; ajustar por *(GPU, dtype, batch)* leva o erro de ~10% a **~1%**, encostando no **piso de ruído** ⚠️ **e o Bee com micro-batch 2 e logits gigantes NÃO é compute-bound — é exatamente o regime onde o proxy quebra** |
| [`2607.13068`](https://arxiv.org/abs/2607.13068) | — | formaliza a ineficiência em **F/B** (joelho do roofline) e **F/S** (quanto compute vem empacotado com cada GB). ⭐ **F/S é o número que explica por que a PRO 4500, com a mesma VRAM e 25% mais barata por hora, saiu 36% mais cara por token** |
| [`2608.00927`](https://arxiv.org/abs/2608.00927) | Jetson, 76.691 amostras pareadas | 🔴 a telemetria **interna** (de onde sai `nvidia-smi power.draw`, a base do nosso diagnóstico) tem **viés de −1,988 W** contra medição externa. E o ranking de duas placas **inverte** conforme precisão/modo de potência — a nossa §2g em hardware |
| [`2607.29575`](https://arxiv.org/abs/2607.29575) | serving OPT | a saturação de throughput nasce nos **kernels de atenção do decode**, com **compute alcançado muito abaixo do limite** — refutação de uma atribuição aceita. Mesmo padrão do nosso: **utilização alta + um recurso no teto ≠ o recurso que você supôs** |

---

## 10. ⚠️ $/token: a nossa armadilha de normalização, publicada

| artigo | achado |
|---|---|
| ⚠️ [`2608.28667`](https://arxiv.org/abs/2608.28667) **GreenBench** | M4 Pro atinge **30–40× melhor energia por token que GPUs de datacenter — em deployment de usuário único**. ⭐ **É verdade e é sobre concorrência 1**, onde a GPU de datacenter está ociosa. Trocar de máquina por causa desse número seria erro |
| 🔴 [`2608.00026`](https://arxiv.org/abs/2608.00026) | atribuição **proporcional a tokens** difere do Shapley exato em **0,440 de L1 normalizado**, reproduzido em três GPUs. **Energia por token é convenção contábil, não medição** |
| ⭐ [`2608.14614`](https://arxiv.org/abs/2608.14614) **DumpsterCluster** | 128 GPUs de segunda mão, **um ano em operação**: US$ 22 mil contra US$ 600 mil — e ainda assim **~4× mais carbono por token** a 8B e **>40×** a 70B. **Refutação empírica de "hardware barato é barato"**, com razão de preço de aquisição de 27× |
| [`2607.04577`](https://arxiv.org/abs/2607.04577) | 3,5 milhões de avaliações: **IPC ranqueia errado a eficiência energética em 67,8% dos problemas**. Se `tokens/s` for proxy de custo energético, esse é o tamanho do risco |
| ⭐ [`2608.11226`](https://arxiv.org/abs/2608.11226) | **nulo replicado e publicado com diagnóstico** (funciona a 7B, falha a 72B por perda de autoridade do atuador sob sharding). E a lição de aparato: a mesma corrida **"viola 23,6% do tempo" ou "nunca viola"** conforme a janela do medidor |

---

## 11. O que acelera — e o que não acelera — em ≤1B

| artigo | escala | achado |
|---|---|---|
| ⭐⭐ [`2608.09703`](https://arxiv.org/abs/2608.09703) **Matryoshka** | 500M / 1,5B / 3B, do zero | sub-modelos **aninhados numa arquitetura só**, treinados fim-a-fim, ficam **em paridade** com baselines independentes usando **36% menos compute total**. ⭐ Se o roadmap tem 350M **e** 1G, treiná-los juntos custa 36% menos |
| ⭐ [`2607.27230`](https://arxiv.org/abs/2607.27230) | **100M, 350M e 1B**, do zero | −0,061 / −0,149 / −0,140 de loss; contagem de cabeças é **U-shaped** com ótimo achatado em H=4 ou 8 — ⭐ **a grade CERCA o ótimo** (§2f). E honestidade: mesmo com kernels Triton o throughput fica em **0,55–0,88× do baseline** — 0,88 não é 1,0 |
| ⭐ [`2607.07953`](https://arxiv.org/abs/2607.07953) | **350M / 15B tok** — a escala exata do Bee-350M | stacks híbridos melhoram loss **ao custo de throughput**; e a formulação de roteamento entre camadas mais natural **não melhora** sobre baselines casados. Os autores declaram que **não** mediram velocidade de inferência (§2q em ação) |
| [`2607.25583`](https://arxiv.org/abs/2607.25583) | **T5-small, 60M** | LoRA r=16 fica a **11,6 pontos** do full FT com <1% dos parâmetros e −31% de memória; 🔴 **rank acima de 16 não dá ganho mensurável** |
| ⭐ [`2608.07226`](https://arxiv.org/abs/2608.07226) | 2× DGX Spark, 128 GB unificados cada | **1.890 tok/s** — contra os **62,9k tok/s** que medimos numa 5090. 🔴 **Memória unificada grande NÃO compra throughput de pré-treino.** Se a ideia de uma caixa de memória unificada para caber vocab 128k tentar, este é o preço |
| [`2608.14003`](https://arxiv.org/abs/2608.14003) | — | poda adaptativa colapsa sob inferência em lote, porque o limiar calibrado offline não casa com a distribuição agregada. **É a nossa §2t medida em outro método** — confirma que o efeito não era peculiaridade do bf16 no nosso avaliador |
| [`2607.15105`](https://arxiv.org/abs/2607.15105) | Quadro RTX 5000, **16 GB** | treino denso **cabe em 2.048 tokens e falha em 4.096**; o método chega a 16.384 com 15,28 GB. Parede de VRAM medida e publicada numa placa da nossa classe, com controle pareado no comprimento compartilhado |
| ⭐ [`2606.13894`](https://arxiv.org/abs/2606.13894) **Gefen** | — | estados do AdamW ~**8× menores**, −6,5 GiB/B params |
| ⭐ [`2606.19989`](https://arxiv.org/abs/2606.19989) | — | *batching* dinâmico online, **1,58–2,51×** de throughput, drop-in no DataLoader |
| ⚠️ [`2608.30877`](https://arxiv.org/abs/2608.30877) | **laptop, 8 GB de VRAM** — o nosso hardware exato | **entra sinalizado, não endossado.** Afirma 175B em 8 GB + **100× sobre 8×A100** — implausível pela nossa própria §5. O número aproveitável: **72% do tempo total é overhead de gerenciamento de memória heterogênea** |

### 🔴 E os resultados negativos, que valem tanto quanto

- [`2606.21428`](https://arxiv.org/abs/2606.21428) — **MoE NÃO ajuda em hardware de consumo**
  (~31% atrás de denso em Jetson de 8 GB). **Contradiz o MobileMoE** da primeira triagem;
- [`2607.19956`](https://arxiv.org/abs/2607.19956) — destilação padrão a **60M** dá **+0,0003
  ROUGE-L**, e **51,3% das amostras de treino pioram** o aluno;
- ⚠️ [`2606.11690`](https://arxiv.org/abs/2606.11690) — a **mesma H100** custa de **US$ 0,21 a
  15,25 por milhão de tokens** puramente em função da taxa de requisição. Custo de serving sem taxa
  de requisição declarada é número sem unidade;
- [`2607.18631`](https://arxiv.org/abs/2607.18631) — em 2×RTX 4090 o plano buscado automaticamente
  supera o ajuste à mão por **+0,9%**, e os autores publicam um **FAIL honesto** em 8×H800, com
  **predições pré-registradas em artefato com hash**. O argumento: otimizadores automáticos
  ranqueiam o espaço que o modelo de custo enxerga e **assumem em silêncio** que ele coincide com o
  que a toolchain consegue emitir — a nossa §2r em outra roupa.

---

# PARTE C — retratações, lacunas e método

## 12. 🔴 Retratações — duas lacunas que declarei e que não existiam

Na primeira rodada declarei cinco lacunas. **Duas eram sobre a fatia que eu tinha lido, não sobre a
literatura** — que é exatamente a §2q, e desta vez comigo:

| lacuna declarada | estado |
|---|---|
| *"nada com o português como âncora"* | 🔴 **FALSA** — Manacá-1B e moBERTo são exatamente isso, e o primeiro é o artigo mais útil do corpus |
| *"sementes e IC em 4 de 135 resumos"* | 🔴 **EXAGERADA** — com o corpus completo são **pelo menos oito**. Ainda é minoria; não é raridade |

⭐ O que as produziu: a primeira rodada buscou `all:tokenizer` e afins. A segunda buscou
`abs:"vocabulary size"`, `abs:subword`, `abs:"byte-level"`, `abs:tokenizer AND abs:translation` — e
o corpus foi de 1.813 para **2.489 registros**, com 676 novos e **178 com hit no título**.
**A afirmação "não existe" era sobre a consulta, não sobre o mundo.**

## 13. As lacunas que sobrevivem, testadas explicitamente contra os corpora

1. 🔴 **A interseção da pergunta central continua VAZIA.** Ninguém varreu tamanho de vocabulário num
   modelo **multiescrita ≤1B treinado do zero** — que é literalmente a decisão do Bee-1G. Os únicos
   hits próximos são um MultiHashFormer, um de ASR de 2021 e dois de 2020 sobre mBERT podado.
   **O Gate T1 mede em casa porque não há de quem copiar.**
2. 🔴 **Nenhuma medição do custo de vocabulário grande no TREINO com cross-entropy comum.** Toda a
   evidência de vocabulário na fatia de throughput é do lado do **decode**; a única exceção
   (`2608.03796`) é KL de destilação.
3. **Expansão *in-place* só foi medida em modelo grande** (8B MoE, Nemotron, LLaMA) ou em tokenizador
   isolado sem modelo. **Ninguém a mediu onde o embedding é metade do orçamento.**
4. ⭐ **Não existe desenho causal ligando fertilidade a qualidade de TRADUÇÃO.** Para um Bee-1G cujo
   eixo declarado é tradução, **esta é a que mais deveria incomodar**: o objetivo do projeto é
   justamente o que a literatura mede por proxy.
5. **Zero avaliações de Cut Cross-Entropy ou Liger-Kernel por nome, e zero menções a *tied
   embeddings*.** Nenhuma réplica independente do nosso *"Liger deu 0%"*.
6. **Nenhuma metodologia sobre quando o throughput estabiliza.** A nossa regra (passo ≥20, três
   leituras coincidentes) **segue sem par publicado**. O mais próximo, `2608.03880`, reporta o piso
   de ruído entre repetições mas não o transiente de aquecimento.
7. **Nenhum estudo fim-a-fim de pré-treino ≤1B em uma única GPU de consumo com tabela de custo**, e
   **nenhum trabalho sobre saturação elétrica em GPU de consumo** — o regime "200 W de TDP com 12 GB
   de 32 usados, cravado no teto" que medimos na PRO 4500 não tem equivalente publicado.

## 14. Nota de método sobre a própria literatura — e sobre o nosso aparato de coleta

**Dos ~192 resumos lidos por inteiro nas duas fatias, oito trazem semente ou intervalo de confiança.**
O tema mais frequente do corpus de tokenizador é o *"token tax"* — **sete artigos quase idênticos**
medindo que idiomas de baixo recurso gastam mais tokens.

⭐ O tema genuinamente novo de 2025-2026 é o da §1: **fazer o embedding deixar de escalar com |V|**.
Sete caminhos independentes atacam a mesma equação. Para o Bee-1G isso **reformula a pergunta**: em
vez de *"quanto vocab cabe em 1B"*, a pergunta é *"por que a tabela de embedding precisa ter |V|
linhas treináveis"* — e a resposta medida com sementes é **não precisa**.

### 🔴 Três defeitos no nosso próprio aparato de coleta, todos da família "nada dá erro"

1. **`curl` falha em silêncio no sandbox** — sai com código 0 e escreve **0 bytes**. Um downloader que
   checa só o exit code produz arquivos vazios e nenhum erro. `python urllib` funciona;
2. **O 429 do arXiv é por IP e compartilhado entre os agentes.** Rodando cinco em paralelo, eles se
   *rate-limitaram mutuamente* — até `max_results=1` passou a dar 429. Exigiu cooldown de 240 s,
   backoff exponencial e 30 s entre páginas;
3. ⚠️ **A API ordena por `submittedDate` (data da v1); o HTML ordena por `announced_date_first`.** São
   listas diferentes. Exemplo dentro da própria amostra: o Jais 2 tem ID `2608.13580` e `published`
   de **2026-07-07**. **Não confiar no prefixo do ID como data.**
