# Plano do Bee-1G — multilíngue e multimodal

> **Estado:** documento de decisão, não de execução. Nenhum gasto aprovado.
> **Base:** tudo que os Bee-150M e Bee-350M mediram, mais a triagem de **~23.000 resumos** do arXiv
> em três rodadas (19 agentes), consolidada em
> [`triagem-arxiv-bee1g-2026-08-31.md`](triagem-arxiv-bee1g-2026-08-31.md) (tokenizador ·
> multilingualidade · throughput) e
> [`triagem-arxiv-bee1g-2026-09-01.md`](triagem-arxiv-bee1g-2026-09-01.md) (arquitetura · escala ·
> corpus · réguas).
>
> **Última atualização:** 2026-09-01.
>
> 🔴 **As rodadas 2 e 3 contradisseram nove pontos das versões anteriores deste plano.** Os maiores:
> a restrição de orçamento de vocabulário **dissolveu**; **a tabela do dilema está errada em
> enquadramento, unidade e cenários**; a arquitetura multimodal recomendada **estava do lado
> contrário do que a medição indica**; e **duas das réguas do Gate T4 não valem para comparação entre
> escritas**. As correções estão aplicadas abaixo e marcadas com **[corrigido 09-01]** ou
> **[novo 09-01]**; a evidência de cada uma está nas triagens.
>
> ⚠️ **Como ler os números citados:** entre **1,0% e 4,5%** dos resumos de cada fatia trazem semente,
> IC ou teste pareado — e **0,4% a 0,5%** cruzam rigor **com** escala ≤1B. Os expoentes e percentuais
> aqui valem como **ordem de grandeza**, não como medida. Os artigos **pré-registrados** são a
> exceção, e são desproporcionalmente os mais úteis.

---

## 1. 🔴 A premissa do README não transfere

O `README.md` afirma *"o próximo degrau é parâmetro, não token"*. Isso está **medido e correto
para o português** (`docs/bpb-compra-capacidade.md`): +45% do mesmo corpus rendeu 0,19% de bpb;
151M→345M rendeu 2,76%.

⚠️ **E não vale para o Bee-1G.** A mesma medição diz que **escala melhora o que o modelo já faz
e não faz aparecer o que ele não faz** — tradução pt→en foi de 0% para 86% de idioma-alvo, mas
resumo, atendimento, código e agêntico continuaram **exatamente em zero**.

O 345M não fala espanhol, francês, árabe, mandarim, alemão ou japonês porque **nunca viu**. Para
7 dos 8 idiomas o Bee-1G **não é um problema de escala — é um problema de dado.**

### 🔴 E a armadilha aritmética que precisa ser resolvida antes de qualquer orçamento

O Bee-350M tem **21,75B tokens de português**. Dividindo um orçamento por 8 idiomas:

| Bee-1G | tokens | por idioma | PT contra o 350M de hoje | US$ (extrapolado) |
|---|---:|---:|---|---:|
| Chinchilla (20 tok/param) | 20B | 2,5B | 🔴 **8,7× menos** | ~305 |
| igual ao 350M (63 tok/param) | 63B | 7,9B | 🔴 2,8× menos | ~960 |
| PT preservado + 7 idiomas | ~170B | ~21B | igual | ~2.590 |

**Um Bee-1G "de orçamento razoável" seria maior e pior em português que o Bee-350M.**

> ### 🔴🔴 [corrigido 09-01] A tabela acima está errada em TRÊS eixos ao mesmo tempo
> Ver [`triagem-arxiv-bee1g-2026-09-01.md` §A](triagem-arxiv-bee1g-2026-09-01.md).
>
> 1. **Enquadramento — o schedule vale mais que o fator de tokens.**
>    [`2502.15938` D2Z](https://arxiv.org/abs/2502.15938): um **610M com 80 tok/param + decaimento
>    linear a zero tem loss MENOR** que o mesmo modelo com **200 tok/param** e decaimento 10× —
>    **60% de economia de compute**. É o mesmo fenômeno que medimos por bifurcação (US$ 22,
>    **−0,1305** de loss ao decair 20%), agora com número de terceiro na nossa faixa.
>    ⭐ **Antes de comprar tokens, comprar decaimento.**
> 2. **Unidade — a conta tem de ser em BYTES, não em tokens.**
>    [`2605.01188`](https://arxiv.org/abs/2605.01188) (988 modelos, 50M–7B): em configuração
>    compute-ótima **os parâmetros escalam com o dado medido em BYTES**, contra Kaplan e Chinchilla.
>    ⚠️ **Dividir um orçamento de TOKENS por 8 idiomas de fertilidades diferentes é comparar réguas
>    diferentes** (§2g em forma de tokenizador) — e corta a nosso favor: a 0,218 tok/byte contra
>    0,358 do SmolLM2, os nossos 21,75B valem bem mais que a mesma contagem num tokenizador pior.
> 3. **Cenários — diluição uniforme é a família que a lei nunca escolhe.**
>    [`2410.12325` M³](https://arxiv.org/abs/2410.12325) põe monolíngue-1-estágio,
>    multilíngue-1-estágio e **multilíngue-2-estágios** na mesma superfície de loss do alvo: conforme
>    o dado do alvo escasseia, o ótimo salta **direto** para 2 estágios, e
>    **multilíngue-1-estágio NUNCA é ótimo na grade**. 🔴 **As três linhas acima são de estágio
>    único.** O desenho indicado é **dois estágios com razão de PT alta no final** — que é o que o
>    [Index-1.9B](https://arxiv.org/abs/2607.09885) faz na prática (WSD com dado curado concentrado
>    **na fase de decaimento**).
>
> ⭐ **E há um experimento de CPU, custo zero, que estima a direção antes de gastar:**
> [`2405.16684`](https://arxiv.org/abs/2405.16684) mede que **gzip prevê** o deslocamento da
> fronteira — mais dado quando o corpus é difícil de comprimir, mais parâmetro quando é comprimível.
> Comparar a compressibilidade gzip do corpus de 8 idiomas contra o só-PT custa minutos.

> ### ❓ DECISÃO PENDENTE — e é do dono, não do método
> **Quanto do orçamento vai para *não piorar o português* versus *adicionar idiomas*?**
> Tudo abaixo depende disso. Projeto inteiro até hoje: **~US$ 272**.
>
> ⚠️ **[novo 09-01] E a pergunta mudou de forma.** Com os três eixos acima, a escolha não é mais
> "quantos tokens por idioma" — é **quantos bytes, em quantos estágios, com qual schedule**.

⚠️ Os US$ acima são **extrapolação** da medição do 350M (345M × 21,75B em 115,48 h de RTX 5090).
O projeto tem regra contra extrapolar custo — o `docs/throughput-350m-medido.md` cortou uma
estimativa pela metade por US$ 0,15. **O Gate T3 vem antes de qualquer compromisso.**

⚠️ **[novo 09-01] E a lei da extrapolação também está errada.** Chinchilla é lei de **FLOPs**; a
nossa restrição é **relógio alugado**. [`2603.28823`](https://arxiv.org/abs/2603.28823) — 70+ runs,
50M–1031M, **numa RTX 4090**, orçamentos de 5 min a 24 h — mede `N* ∝ t^0,60` com
**α = 0,60 ± 0,07**, crescendo mais rápido que o `C^0,50`. **Sob restrição de tempo, o modelo ótimo
é MAIOR que o compute-ótimo**, o que concorda com a nossa medição de que a escala paga e o token
não. E o vizinho de orçamento existe: [Puro-2B](https://arxiv.org/abs/2608.27370) treinou **1,4T
tokens do zero numa RTX 5090 de consumo por menos de US$ 6,9 mil**, com receita Apache-2.0.

---

## 2. ⭐⭐ A decisão de maior alavanca custa minutos de CPU

[**One Tokenizer To Rule Them All**](https://arxiv.org/html/2506.10766v1) — 3,3B params, vocab
100k/175k/250k: tokenizador universal **desde o início** custa **<1% na língua primária** e rende
**+18,9%** ao expandir idiomas, com **+2× de plasticidade e +8× de velocidade de adaptação**.

> 🔴 **[corrigido 09-01] Isto é medido em 3,3B, e o oposto foi medido abaixo de 1B.**
> [`2608.07727`](https://arxiv.org/abs/2608.07727) treinou **5 GPT-2 do zero** — 4 monolíngues com
> tokenizador próprio de 32k contra 1 multilíngue com 64k compartilhado — e **o monolíngue venceu
> nos 4 idiomas**. Com [`2605.26683`](https://arxiv.org/abs/2605.26683) (700 runs controlados,
> vocabulários **menores** frequentemente melhoram a transferência), *"construir o tokenizador
> multilíngue agora"* **deixou de ser decisão herdada da literatura e virou medição a fazer**.
> ⭐ O que sustenta o gate: [`2506.03101`](https://arxiv.org/abs/2506.03101) mediu que **modelos
> pequenos predizem com fidelidade** as diferenças de *tokenizador* dos grandes. **O Gate T1 em
> proxy é sólido** — o problema está no T2 (§3).

E [`2608.03999`](https://arxiv.org/abs/2608.03999) mediu, fixando backbone, dado, orçamento e
decodificação: escalar o backbone **34× quase não move** a métrica, enquanto **trocar a
representação a corta pela metade** — replicado num backbone de 26M do zero.

### ⚠️ Cinco ressalvas — e a primeira delas deixou de ser restrição

1. ~~**Vocab consome orçamento de parâmetro.** 250k × d_model 2048 = **512M**, metade de um modelo
   de 1B.~~ ⭐⭐ **[corrigido 09-01] — a restrição dissolveu, e vira braço de gate.** A aritmética
   está certa; a **configuração** é que era ruim.
   [`2204.08832`](https://arxiv.org/abs/2204.08832) dá o limite empírico: a razão
   *params-de-vocab / totais* pode ir a **20% (BPE)** e **40% (morfológico)** — os 50% que eu
   calculei estão **fora dos dois**. E sete linhas de trabalho fazem o embedding **deixar de
   escalar com |V|**:
   [`2605.29459` **Kronecker**](https://arxiv.org/abs/2605.29459) — **−91 a −94%** dos parâmetros
   treináveis de entrada, **−2,5 ± 0,2%** de loss em GPT-2 **124M** com **3 sementes** (o único
   artigo do lote com barra de erro no número principal);
   [`2501.16975` **Over-Tokenized**](https://arxiv.org/abs/2501.16975) — **desacopla entrada e
   saída**, alcançando baseline do **dobro** sem custo adicional;
   [`2502.01637` **SCONE**](https://arxiv.org/abs/2502.01637) — n-gramas **fora do acelerador**, 1B
   residente supera 1,9B;
   [`2608.00582`](https://arxiv.org/abs/2608.00582) e
   [`2605.29379`](https://arxiv.org/abs/2605.29379) — adaptação a **vocab FIXO**, drop-in.
   ⚠️ E [`2608.11361`](https://arxiv.org/abs/2608.11361) segue valendo: a qualidade em bpb varia
   **<2%** em toda a faixa de vocab — o que decide não é qualidade, é orçamento e serving.
2. ~~**A maldição da multilingualidade é real e documentada**
   ([2311.09205](https://arxiv.org/pdf/2311.09205))~~ 🔴 **[corrigido 09-01] — ela se INVERTE com a
   escala.** `2311.09205` mede >10.000 modelos de **≤45M** e vê alto recurso piorando
   consistentemente; [`2510.25947`](https://arxiv.org/abs/2510.25947), em **1,1B e 3B** com 25→400
   idiomas, **"não observa maldição significativa"**. Diretamente opostos, e a variável que os
   separa é escala. Nosso **0,218 tok/byte em PT** é o ativo do projeto desde o Gate 1 e **vai
   piorar** — quanto, mede-se em minutos; **se isso importa para a qualidade, ver o item 4 abaixo**.
3. 🔴 **Escritas diferentes podem quebrar subword.**
   [`2605.02270`](https://arxiv.org/abs/2605.02270) mediu **mT5 subword falhando completamente**
   (chrF++ < 18,5) contra ByT5 byte-level em **87,4**, em cirílico↔árabe. Latim + árabe + han +
   kana num vocab só **não é seguro por suposição**.
   ⚠️ E [`2608.26449`](https://arxiv.org/abs/2608.26449): o regex `\p{L}+` do pré-tokenizador
   **ByteLevel do HuggingFace** — que o `bee/train_tokenizer.py` usa — parte a palavra em toda
   marca de vogal em **17 de 17 abugidas**. O árabe está na nossa lista.

4. 🔴 **[novo 09-01] Fertilidade é métrica de CUSTO, não de qualidade.**
   [`2607.24276`](https://arxiv.org/abs/2607.24276): a correlação fertilidade→compreensão é
   **largamente explicada pela disponibilidade de recurso do idioma**, não pelo tokenizador.
   [`2310.08754`](https://arxiv.org/abs/2310.08754), em 24 LLMs a 2,6B: fertilidade e *parity*
   **não são sempre preditivas** — e mede o preço do erro, **até +68% de treino** com tokenizador
   inglês-cêntrico.
   ⭐⭐⭐ E [`2607.23362` **JOLT**](https://arxiv.org/abs/2607.23362), com certificado de
   quase-otimalidade: **o BPE já está a 1–2% da compressão alcançável** e o ganho algorítmico
   disponível é **≤0,78%**, enquanto **mudar a cobertura de idiomas compra 2,4–8×**.
   **Isso reordena a fila:** não há ganho em trocar de algoritmo de tokenização — o ganho está em
   **quais idiomas entram**, o que simplifica o T1 e transfere o peso para o T2.
5. ⚠️ **[novo 09-01] Trocar o vocab muda a regra de LR.**
   [`2506.15025`](https://arxiv.org/abs/2506.15025): com vocab ≫ largura entra-se no *"regime Large
   Vocab"*, onde a razão ótima **LR-embedding / LR-oculto** escala **Θ(√width)**, não Θ(width) —
   validado pré-treinando **1B do zero**. E
   [`2605.21486`](https://arxiv.org/abs/2605.21486): **o benefício inteiro do μP sobre AdamW-SP vem
   de maximizar o LR da camada de embedding**, que em SP é um gargalo indutor de instabilidade.
   Este projeto já perdeu **7 de 15 braços** por grade de LR mal centrada (§2f).

**Caminho intermediário medido:** [`2607.15232`](https://arxiv.org/abs/2607.15232) — **expansão
*in-place***, continuando os merges BPE do nosso 32k, de modo que os tokens antigos sobrevivem e
todo token novo tem decomposição exata nos antigos.
⚠️ **Mas só foi medida em modelo grande** (8B MoE, Nemotron, LLaMA) — **ninguém a mediu onde o
embedding é metade do orçamento**, que é o nosso caso.

### ⭐⭐ A referência de build mais próxima que existe

[`2608.30114`](https://arxiv.org/abs/2608.30114) **Manacá-1B** (31/08/2026) — **1,72B decoder
treinado do zero para PT-BR**, batendo Tucano-1b1 e Tucano-2b4 em LAMBADA-PT. ⭐ E o que o torna
útil não é o resultado: traz **erro padrão e teste pareado em toda comparação, com o harness
validado contra números publicados** — a nossa §2aa escrita por outra pessoa. **Vale como modelo de
relatório para o Gate T4.**

⚠️ E documenta um defeito da nossa família: converter tokenizador **SentencePiece com normalização
de caixa** para HF *fast* **descarta o normalizador em silêncio**, mandando todo token capitalizado
para byte-fallback — **LAMBADA-PT de 45,3 para 25,0**, invisível no agregado.
✅ **Verificado contra `models/bee-150m-v3-base`: não se aplica** (normalizador `NFC()` sobrevive à
carga, `byte_fallback: False`, pior delta minúscula→Maiúscula = **0 tokens**, e em texto real
capitalizar **economiza** 0,72%). A verificação entra no checklist: *texto capitalizado não pode
inflar a contagem de tokens*.

---

## 3. Os gates, com critério declarado ANTES

### Estágio T — texto multilíngue

#### 🔴 Gate T0 — a forma do modelo · **[novo 09-01]**

> O plano supunha que a arquitetura do Bee-350M carrega para o 1G. **Quatro medições dizem que essa
> suposição precisa de gate próprio**, e três delas custam pouco ou nada.

**T0.a — decoder-only para TRADUÇÃO não é a escolha óbvia.**
[`2510.26622`](https://arxiv.org/abs/2510.26622) comparou pareado de **~150M a ~8B**: decoder-only é
mais compute-optimal **no pré-treino**, mas depois de instruction tuning **o prefix-LM empata ou
ganha**, com inferência bem melhor. ⚠️ **E a frase que nos atinge: se medir só bpb de pré-treino,
decoder-only vence — e é exatamente com bpb que este projeto decide.**
Apoios: [`2412.05862`](https://arxiv.org/abs/2412.05862) mede **NLLB-200 3,3B (enc-dec) batendo TODOS
os decoder-only de 7–8B em 3 de 4 direções, inclusive en→pt**; e
[`2304.04052`](https://arxiv.org/abs/2304.04052) dá o mecanismo — **degeneração da atenção**: conforme
a geração avança, sobra menos atenção para a fonte, que é o regime de tradução.
🟢 Contrapeso: [`2202.01994`](https://arxiv.org/abs/2202.01994) é **nulo** — os expoentes de escala de
dados são **minimamente afetados** pela arquitetura; ⚠️ mas **back-translation no lugar de bitexto
real degrada o expoente de verdade**.
✅ **Decisão de gate:** manter decoder-only (é o que sabemos treinar e servir) **e** registrar que a
comparação enc-dec × dec-only na forma estrita — mesmo dado, mesmo orçamento, ≤1,5B, do zero, alvo
tradução — **não existe na literatura**. Se o eixo de tradução falhar no T4, esta é a primeira
hipótese, não a última.

**T0.b — a nossa geometria está na ponta errada de uma lei, e testar é grátis.**
[`2601.20994` **The Depth Delusion**](https://arxiv.org/abs/2601.20994) (30 arquiteturas, **17M a
7B**, R² 0,922): **largura deve crescer 2,8× mais rápido que profundidade**, com uma **profundidade
crítica** além da qual somar camadas **aumenta** a loss. Somos 30 camadas × d_model 576 — razão 19,2.
[`2501.18107` Morph-1B](https://arxiv.org/abs/2501.18107) replica **na escala exata** (63 modelos,
80M–1B, do zero) e [`2605.27989`](https://arxiv.org/abs/2605.27989) responde à nossa ressalva
registrada: o intervalo eficiente **permanece estável conforme o orçamento cresce** — logo transfere.
⚠️ Com contradição pelo mecanismo em [`2602.05970`](https://arxiv.org/abs/2602.05970) (a loss cai como
`1/profundidade` porque as camadas ficam **similares** e agem como ensemble — profundidade não é
inútil, é mal aproveitada), e um **nulo** em
[`2409.15051`](https://arxiv.org/abs/2409.15051) (6 decoder-only de 70M a 7B do zero, tradução
multilíngue: **profundidade e largura dão a mesma melhora de test loss**, com eficiência diferente).
⭐ **E dá para testar SEM TREINAR:** [`2502.06857` **Gemstones**](https://arxiv.org/abs/2502.06857)
publica **4.000+ checkpoints até 2B com formas arquiteturais diversas**. Custo: leitura.

**T0.c — MoE não tem resposta de arquitetura, só de hardware.**
[`2608.10605` MOSAIC](https://arxiv.org/abs/2608.10605) (lei ajustada de **104M a 2,7B ativos**):
dentro da faixa calibrada **um orçamento de FLOPs não admite esparsidade ótima interior** — **a
esparsidade ótima só existe sob restrição de SISTEMA**. Isso explica por que `2606.21428` (MoE 31%
atrás em edge, igualado por **ativo**), [DECO](https://arxiv.org/abs/2605.10933) (**2,93× no Jetson**,
igualado por **total**), [MobileMoE](https://arxiv.org/abs/2605.27358) (igualado por **memória INT4**)
e [`2603.26603`](https://arxiv.org/abs/2603.26603) (igualado por **energia**) discordam **sem nenhum
estar errado**. 🔴 E **ninguém rerodou o OLMoE num Jetson** — a contradição segue aberta.
⚠️ Se houver MoE, três medições convergem sobre o que muda a qualidade:
[`2605.11689`](https://arxiv.org/abs/2605.11689) (**2.000+ runs**: mexer em contagem e granularidade;
**shared experts, heterogêneos e load balancing têm efeito pequeno**),
[`2604.14419`](https://arxiv.org/abs/2604.14419) (**3 sementes, teste TOST**: a topologia de
roteamento **não determina a ppl assintótica**; a vantagem real é **~1,2%**) e
[`2605.09403`](https://arxiv.org/abs/2605.09403) (roteamento **aleatório congelado** quase iguala o
aprendido). ⭐ E [`2605.28042`](https://arxiv.org/abs/2605.28042) poda **metade dos experts sem
degradação** — **tradução usa uma fração do MoE**, o que é evidência de que a capacidade é separável.
🔴 **Mas MoE multilíngue treinado do zero em ≤1,5B: zero artigos.** Toda a evidência vem de sondar
modelos de 30B–671B já treinados.

**T0.d — Mamba/SSM esquece exatamente o que a tradução não pode esquecer.**
[`2512.15653`](https://arxiv.org/abs/2512.15653) (Mamba 130M–1,4B, auto-encoder do estado): a perda de
informação é **significativamente maior em números, variáveis e menções a organizações**, e o que
esquece é **o que é raro no pré-treino**. Com [`2603.20997`](https://arxiv.org/abs/2603.20997)
(**Mamba-1.4B faz 29%** em roteamento por conteúdo, **99,5%** com bidirecional),
[Echo](https://arxiv.org/abs/2605.06997) (**Mamba-2 puro no acaso** em recall multi-chave) e
[`2602.01763`](https://arxiv.org/abs/2602.01763) (separação **PROVADA**).
⭐ O outro lado, também provado: [`2605.16640`](https://arxiv.org/abs/2605.16640) — o híbrido resolve
com scratchpad **O(1)** o que o recorrente puro não resolve. **Não há almoço grátis; há um preço com
número.**
⚠️ E o aviso de compra: quatro artigos "controlados" dão **quatro vencedores diferentes** de atenção
linear. **Não adotar nenhum por tabela alheia.**
✅ **Decisão de gate:** atenção plena, e SSM/híbrido fica **fora** do Bee-1G — o eixo declarado é
tradução, e é justamente aí que a evidência é contrária.

**T0.e — MLA perde na única varredura direta.**
[`2601.11471` LRKV](https://arxiv.org/abs/2601.11471) (128M a 6,3B pré-treinados): LRKV tem a **menor
test loss entre MHA, MQA/GQA e MLA** com 45–53% do cache. ⚠️ E
[`2506.09342`](https://arxiv.org/abs/2506.09342), a **30M do zero**: **sem RoPE, MLA fica 3–5% PIOR
que atenção baunilha em modelo pequeno**. ✅ **Manter GQA.**

**T0.f — `seq_len`: janela CURTA vence sob orçamento fixo, e os nossos 2048 já valem mais.**
[`2503.15450` **SkyLadder**](https://arxiv.org/abs/2503.15450) — pré-treino **do zero**, 1B e 3B, 100B
tokens: *modelos pré-treinados com janelas mais curtas batem consistentemente os de contexto longo
sob orçamento fixo de tokens*, e o agendamento curto→longo recupera depois com **+3,7%** e **até 22%
mais rápido**. [`2608.12218`](https://arxiv.org/abs/2608.12218) confirma **e dá o mecanismo**: o
gradiente migra da FFN para a atenção — **o modelo aprende a consultar em vez de saber**, que é o
oposto do que um tradutor precisa. Terceira evidência de não-monotonicidade em
[`2312.01515`](https://arxiv.org/abs/2312.01515).
⚠️ **`2509.18762` contradiz para o SFT** — SFT longo **melhora** o desempenho curto. **A decisão de
comprimento é diferente no pré-treino e no SFT.**

⭐⭐ **E há um crédito que não estávamos contando.** [`2607.24276`](https://arxiv.org/abs/2607.24276)
mede que o imposto de tokenização reduz a **janela efetiva** de idiomas mal cobertos a **12%** da do
inglês, pelo mecanismo de **merges que falham deixando bytes soltos (Pearson r = 0,89)** — que é
exatamente o que o nosso censo achou (árabe, han e kana em zero). Do outro lado: a **0,218 tok/byte
contra 0,358**, os nossos **2048 tokens carregam ~64% mais texto — cerca de 3350 de um tokenizador
padrão**. **Parte do custo de ir a 4096 já foi paga no tokenizador.**
✅ **Decisão de gate: manter 2048**, e tratar `seq_len` como **decisão conjunta com o tokenizador**,
não de arquitetura. Referência: [BERTomelo](https://arxiv.org/abs/2606.28999), encoder PT do zero com
106M documentos, escolheu **1.024**.
🔴 **E uma guarda antes de qualquer aumento:** [`2411.13476`](https://arxiv.org/abs/2411.13476) mede
que **RoPE em bf16 desvia da codificação relativa pretendida**, com o erro **acumulando com o
comprimento** e o **primeiro token** como maior contribuinte. Nada dá erro, a loss cai. **Nós
treinamos em bf16.**

#### Gate T1 — tokenizador · **CPU, minutos, US$ 0**

Varredura sobre a mistura dos 8 idiomas, reusando `bee/train_tokenizer.py --varrer-vocab`:

| braço | o que testa |
|---|---|
| 32k atual | o baseline — quanto o PT tem a perder |
| 32k **expandido in-place** | preserva a especialização (`2607.15232`) |
| 64k · 128k do zero | o meio defensável |
| **byte-level para árabe/han/kana** | o alerta do `2605.02270` |
| ⭐ **[novo 09-01] embedding fatorado** (Kronecker / entrada-saída desacopladas) | **vocab grande sem pagar em parâmetro** — dissolve a ressalva 1 |

**Critério, declarado antes — em DOIS eixos, e ambos têm de passar:**

1. **custo** — a fertilidade em PT **não pode piorar mais que 15%** (0,218 → 0,251 tok/byte), e
   nenhum idioma pode ficar acima de 3,0 tok/palavra
   ([o imposto medido em 25 línguas europeias](https://arxiv.org/abs/2605.24718) põe as românicas
   em 1,5–1,7 e o teto europeu em ~3,1);
2. 🔴 **[novo 09-01] qualidade** — **bpb por idioma** num holdout fixo, com o mesmo orçamento de
   passos em todos os braços. **Sem este eixo o gate aprova um tokenizador que comprime bem e não
   ensina**: `2607.24276` e `2310.08754` mediram que fertilidade **não é preditiva de qualidade**,
   e o JOLT mostrou que o ganho de compressão disponível é ≤0,78% de qualquer jeito (§2.4).

3. 🔴 **[novo 09-01] incompletude** — fração de tokens **indecodificáveis sozinhos** por escrita.
   BPE byte-level aprende merges que atravessam fronteira de caractere UTF-8, e
   [`2410.23684`](https://arxiv.org/abs/2410.23684) mediu **−90% de alucinação no Llama-3.1** só
   trocando a tokenização da MESMA frase. ⚠️ **Não é redundante com fertilidade:** no extremo
   (fallback puro) as duas disparam juntas, mas na faixa intermediária — que é onde um vocab
   multilíngue de 128k vai cair — um tokenizador pode ter fertilidade aceitável **e** uma fração
   grande de merges que atravessam fronteira. Custa segundos de CPU.

⚠️ **Reportar POR IDIOMA, nunca a média.** Média entre 8 idiomas é agregado de componentes
heterogêneos — a §2y aplicada ao tokenizador.

> ### 🔴🔴 [novo 09-01] O baseline de 32k não é um baseline — é um zero
>
> Censo **exato** do `models/bee-150m-v3-base` (não amostral: conta os 32.000 tokens do vocab):
>
> | escrita | tokens no vocab | | escrita | tokens no vocab |
> |---|---:|---|---|---:|
> | latim básico | 31.111 (97,22%) | | **árabe** | 🔴 **0** |
> | latim acentuado | 5.246 (16,39%) | | **han (CJK)** | 🔴 **0** |
> | cirílico | 7 (0,02%) | | **hiragana/katakana** | 🔴 **0** |
>
> **Três dos oito idiomas-alvo não têm um único token no vocabulário atual.** Escrita com zero
> tokens só pode ser representada por **fallback de byte**: 1 token por byte, e **cada um deles é
> um token incompleto**. Em UTF-8 isso é 2 bytes/caractere no árabe e 3 no CJK — contra os **0,218
> tok/byte** que o PT desfruta.
>
> ⭐ **Duas consequências para o gate:**
> 1. O braço *"32k atual"* deixa de ser *"quanto o PT tem a perder"* e passa a ser *"o piso de três
>    idiomas é fallback de byte a 100% de incompletude"*. O gate não decide **se** expande — decide
>    **como**;
> 2. ⭐ e a **expansão in-place** ([`2607.15232`](https://arxiv.org/abs/2607.15232)) fica com a
>    forma certa por um motivo novo: **não há conteúdo não-latino no 32k para conflitar**. Acrescentar
>    merges de árabe/han/kana não perturba nada que exista — o que torna a preservação do PT quase
>    gratuita, em vez de um trade-off.
>
> ⚠️ E isto **quantifica com o nosso artefato** a ressalva 3 (`2605.02270`, mT5 subword falhando em
> cirílico↔árabe): não é mais um alerta emprestado de outro paper, é uma contagem nossa.

⚠️ **E o gate mede em casa porque não há de quem copiar:** testado contra 2.489 registros do arXiv,
**ninguém varreu tamanho de vocabulário num modelo multiescrita ≤1B treinado do zero**.

#### ⭐⭐ [novo 09-01] Quatro coisas que a rodada 3 traz para este gate

1. ⭐ **Inflar o vocabulário NÃO custa otimização.**
   [`2608.16671`](https://arxiv.org/abs/2608.16671) — **cinco sementes pareadas**, IC de 95%,
   intervenção backward-only: **acrescentar classes de saída que nunca são alvo não prejudica o
   aprendizado**. O custo é **memória**, não convergência: o **tensor de logits ∝ lote ×
   comprimento × V tem de ser materializado inteiro na VRAM**
   ([`2511.17599`](https://arxiv.org/abs/2511.17599), com cross-entropy comum) — e fundir projeção e
   perda o remove. ⚠️ Mas [`2605.06216`](https://arxiv.org/abs/2605.06216) dá o dano real: Zipf faz
   os embeddings raros ficarem **cronicamente subtreinados** — **V grande compra linhas que nunca
   aprendem**.
2. 🔴 **E há contradição direta ao "vocabulário maior".**
   [`2605.26683`](https://arxiv.org/abs/2605.26683) (700 runs controlados) mede que **vocabulários
   MENORES frequentemente melhoram a transferência**, porque mantêm as palavras decomponíveis em
   fragmentos compartilhados; [`2510.21909`](https://arxiv.org/abs/2510.21909) (~7.000 tokenizadores,
   97 idiomas) mede que **aumentar o vocabulário simplesmente NÃO reduz o imposto** — existe um
   **vocabulário ótimo POR IDIOMA**; e [DunbaaBERT](https://arxiv.org/abs/2605.26935) varreu
   32k/52k/96k e achou **32k com o melhor perfil**. ⚠️ Tudo isso tensiona com `2407.13623`.
   ⭐ **E [`2608.11361`](https://arxiv.org/abs/2608.11361) mede <2% de dispersão de bpb na faixa
   ótima de V a 1,3–2,3B** — se valer a 1B multilíngue, este gate decide menos do que parecia, e o
   peso vai para o T2.
3. ⭐⭐ **Um diagnóstico de CPU que separa teto de tokenizador de escassez de dado.**
   [`2608.26449`](https://arxiv.org/abs/2608.26449): varrer a fatia do idioma no corpus de **5% a
   95%** — o tokenizador com teto estrutural se move **1,7%**, o consertado **33,9%**. Resolve a
   ambiguidade que o gate tem de resolver por idioma, sem GPU.
4. ⭐ **Dois algoritmos prontos entram como braços:**
   [`2508.04796` **Parity-Aware BPE**](https://arxiv.org/abs/2508.04796) — regra *fair-max* que a
   cada fusão maximiza o ganho da língua **pior comprimida**: **Gini dos custos por idioma cai até
   89%** com impacto desprezível na compressão global e **sem degradação downstream**; e
   [`2012.15671` VOLT](https://arxiv.org/abs/2012.15671) — **−70% de vocabulário E +0,5 BLEU** em
   en–de. ⭐ Ambos atacam o problema que o nosso censo expôs (três escritas em zero) **sem** inflar o
   orçamento.

⚠️ **E uma alternativa de escrita que não estava na mesa:**
[`2608.25904`](https://arxiv.org/abs/2608.25904) (EMNLP 2026) treinou do zero em
**467M/709M/1,03B × oito idiomas** — quase a nossa configuração — e mediu que **romanização dá a
transferência cross-lingual mais forte, com a vantagem crescendo com escala**. Romanizar árabe, han
e kana dispensaria a expansão do vocabulário inteira.
🔴 Com dois contrapesos: **aplicar romanização como fine-tune depois PIORA os idiomas já cobertos**
(é decisão de pré-treino ou nada), e [`2608.21384`](https://arxiv.org/abs/2608.21384) mede que
**romanização AUMENTA a contagem de tokens em 2–19%**. Não é contradição — **pode custar tokens e
comprar transferência** — mas as duas medidas vão juntas.

##### ⭐⭐ [MEDIDO 09-01] O Gate T1 rodou — eixos 1 e 3

Corpus: **293.704 documentos · 800 Mcar · 1,22 GB**, os 8 idiomas do `fineweb-2` (odc-by, configs
conferidos na origem) mais o inglês do `fineweb`. Código em
[`bee/coletar_multilingue.py`](../bee/coletar_multilingue.py) e
[`bee/gate_t1_vocab.py`](../bee/gate_t1_vocab.py); artefato em `docs/gate-t1-vocab.json`.

**Eixo 1 — tok/caractere por idioma** (§2y: por idioma, nunca a média):

| braço | vocab | por | spa | fra | deu | eng | arb | cmn | jpn | emb@2048 | %1B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32k atual | 32k | 0,23 | 0,29 | 0,36 | 0,42 | 0,32 | 1,72 | 2,60 | 2,04 | 66M | 7% |
| **32k-multi** | 32k | 0,27 | 0,26 | 0,28 | 0,30 | 0,27 | **0,36** | **0,81** | **0,59** | 66M | 7% |
| 64k-multi | 64k | 0,25 | 0,24 | 0,25 | 0,27 | 0,25 | 0,32 | 0,73 | 0,53 | 131M | 13% |
| 96k-multi | 96k | 0,23 | 0,23 | 0,24 | 0,26 | 0,24 | 0,30 | 0,69 | 0,49 | 197M | 20% |
| 128k-multi | 128k | 0,23 | 0,22 | 0,24 | 0,25 | 0,23 | 0,29 | 0,67 | 0,47 | 262M | 26% |
| **32k+32k in-place** | 57k | **0,23** | **0,29** | **0,36** | **0,42** | **0,32** | **0,35** | 1,53 | 0,79 | 116M | 12% |

| braço | PT | máx tok/pal | veredito |
|---|---:|---:|---|
| 32k atual | +1,0% | 9,8 | ❌ árabe quebrado |
| 32k-multi | +19,4% | 2,1 | ❌ estoura o teto de PT |
| 64k · 96k · 128k-multi | +9,1% · +4,3% · +1,5% | 1,8 · 1,8 · 1,7 | ✅ **passam** |
| 32k+32k in-place | +1,0% | 2,9 | ✅ **passa** |

**Três leituras:**

1. ⭐⭐ **O problema do vocabulário atual não é tamanho — é composição.** O `32k-multi` tem **o
   mesmo vocab e o mesmo custo de embedding** e põe o chinês de 2,60 para **0,81**. Três vezes
   menos token, zero parâmetro a mais. O preço é o PT: +19,4%, acima do teto declarado.
2. **Dobrar o embedding compra 8%.** De 64k para 128k: cmn 0,73 → 0,67 e por 0,25 → 0,23, ao custo
   de **131M de parâmetros** — 13% de um modelo de 1B.
3. ⭐ **A expansão in-place preserva as cinco latinas EXATAMENTE** (dígito por dígito) e resolve o
   árabe (0,35 contra 0,32 do 64k do zero). ⚠️ Mas só metade do chinês (1,53), e coube apenas
   **24.667 dos 32.000** pedidos — acabaram os candidatos 100% na escrita-alvo.

**Eixo 3 — % dos tokens EMITIDOS que não decodificam sozinhos:**

| braço | arb | cmn | jpn |
|---|---:|---:|---:|
| 32k atual | 88,2% | 96,6% | 95,9% |
| 32k-multi | 0,1% | 8,4% | 1,8% |
| 128k-multi | 0,1% | **1,8%** | 0,3% |
| 32k+32k in-place | 20,7% | 🔴 **80,9%** | 59,2% |

⭐ **É aqui que a expansão in-place se separa**, e exatamente como o critério previa: fertilidade
decente em japonês (0,79) **com 59,2% dos tokens emitidos sendo fragmentos incompletos**. Eixo 3
não é redundante com o eixo 1.

##### 🔴 E o critério que eu declarei estava quebrado em 2 dos 8 idiomas

O teto *"nenhum idioma acima de 3,0 tok/palavra"* reprovou **os seis braços**, inclusive os
obviamente bons — assinatura de régua defeituosa, não de candidato ruim. Caracteres por "palavra"
que o `\w+` enxerga:

| por | spa | fra | deu | eng | **arb** | **cmn** | **jpn** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,1 | 6,0 | 5,9 | 6,8 | 5,8 | **5,7** | 🔴 **9,7** | 🔴 **12,3** |

⭐ **O árabe usa espaço e entra na linha das europeias.** Quebram chinês e japonês, onde uma
"palavra" é uma oração inteira — e a fonte do teto ([`2605.24718`](https://arxiv.org/abs/2605.24718))
mediu **25 línguas europeias**. Aplicar aquele número a CJK é a §2g na própria régua do gate.

✅ Corrigido medindo **quais idiomas o `\w+` segmenta** (car/palavra ≤ 8), em vez de listar. E
**não inventei teto para CJK**: escolher agora um limiar que faz os braços passarem seria escolher
o número que dá o resultado desejado (§2l). Os valores de cmn/jpn vão na tabela e **não aprovam
nem reprovam** até virem de referência externa.

##### ✅ E o orçamento de texto não prende

25 / 50 / 100 MB por idioma dão fertilidade **idêntica na segunda casa nos oito**, a 32k; e a
checagem no topo confirma a 128k (cmn 0,67 contra 0,66). A escolha de 50 MB é de recurso, sem
consequência de medição — e foi feita porque a corrida a 1,22 GB levou o *commit* da máquina a
**70,2 GB de 71,1 GB** e teria morrido de OOM no meio.

⚠️ **O eixo 2 (qualidade, bpb por idioma) continua NÃO MEDIDO** — exige GPU, e `2607.24276` e
`2310.08754` mediram que **fertilidade não é preditiva de qualidade**. Este gate **elimina
candidatos; não elege nenhum.** A escolha entre 64k, 96k, 128k e o híbrido in-place é do eixo 2.

#### Gate T2 — mistura de idiomas · **horas locais + ~US$ 20**

Mini-runs no estilo do E4 (40 braços de 3,8M tokens), agora com **3 sementes por braço**.

**A pergunta:** quanto o multilíngue custa ao PT, e qual a razão ótima.

⚠️ **Dois avisos medidos que mudam o desenho:**
- [balanceamento cego por idioma **equaliza entre línguas e REDUZ o desempenho geral**](https://arxiv.org/html/2602.15210)
  — varrer a razão, nunca assumir uniforme;
- 🔴 ["Mix, Don't Tune"](https://arxiv.org/abs/2605.13225) (150M–1,43B, ~1000 runs): misturar vale
  **2–3× o dado único do alvo** e **a folga CRESCE com o tamanho do modelo** — mas **a loss de
  validação do alvo SUBESTIMA sistematicamente o ganho**. Medir por bpb do PT daria a resposta
  errada. **Medir tradução contra o piso de copiar a fonte.**
- ⚠️ [idiomas com flexão explícita compartilham circuitaria](https://arxiv.org/abs/2608.18545):
  PT/ES/FR/DE sim; mandarim e japonês **não**. A mistura ótima provavelmente não é uniforme.

**Critério:** o braço vencedor não pode custar mais que **5% de chrF2 em tradução PT** contra o
braço monolíngue, e tem de superar o piso de copiar a fonte em **todos** os 8 idiomas.

⭐ **É aqui que as três sementes ainda cabem.** No run grande não cabem — o seguro se compra
agora.

> ### 🔴 [novo 09-01] O defeito de desenho deste gate — e ele é do proxy, não do critério
>
> A maldição da multilingualidade **se inverte com a escala** (§2, ressalva 2): aparece em ≤45M
> (`2311.09205`) e **não aparece** em 1,1B–3B (`2510.25947`). Este gate decide a mistura em
> **mini-runs de 150M** — perto da escala onde ela **aparece** — para um alvo de **1B**, onde ela
> **não aparece**. 🔴 **O proxy pode reprovar uma mistura que funcionaria no alvo.**
>
> ⚠️ E `2506.03101` **não socorre**: ele valida proxy pequeno para diferenças de **tokenizador**,
> não de **razão de mistura**.
>
> ✅ **Conserto:** o gate ganha um **braço de transferência** — o mesmo par de misturas medido em
> **duas escalas** (ex.: 150M e 350M, que já temos). Se a ordem entre elas se mantiver, o proxy
> transfere e o resto do grid vale; se inverter, o grid inteiro é sobre um fenômeno que não é o do
> alvo, e a decisão sobe de escala. **Custa um segundo ponto, não um segundo grid.**
>
> ⭐⭐ **[novo 09-01] E dois artigos respondem parte disso de graça.**
> [`2410.12883`](https://arxiv.org/abs/2410.12883) — 100+ modelos decoder-only, 23 idiomas, 5
> famílias — mediu que **a cross-entropy de cada família depende só da própria taxa de amostragem,
> independente do resto da mistura**, e que **as proporções ótimas derivadas de 85M generalizam para
> 1,2B**. E [`2510.22037` **ATLAS**](https://arxiv.org/abs/2510.22037) — **774 experimentos, 10M a
> 8B, 400+ idiomas** — entrega matriz de transferência de **1.444 pares**, lei de como escalar N e D
> ao **acrescentar** idiomas, e **os pontos de cruzamento entre treinar do zero e afinar de um
> checkpoint multilíngue**.
> ⚠️ Com tensão registrada: [`2608.26576`](https://arxiv.org/abs/2608.26576) (40 modelos de 310M
> **pareados**) mede que **o idioma que se põe ao lado desloca os conceitos do outro acima da
> variância de semente**, em 32 comparações. Um agrega por família e está plano; o outro mede o
> componente e ele se move — §2y.

> ### 🔴 [novo 09-01] E ajustar uma LEI de mistura pode ser trabalho desperdiçado
>
> [`2504.11393` **DataDecide**](https://arxiv.org/abs/2504.11393) — 25 corpora, até 1B, 100B tokens,
> **3 sementes**: **nenhum dos 8 métodos de lei de escala supera a fronteira de decisão-por-compute
> da predição de escala única**. **Ranquear a 150M acerta ~80% das comparações no alvo de 1B.**
>
> ⚠️ Contradiz a nossa prática do E4 — onde construímos e depuramos um ajustador de lei de mistura —
> e está medido na nossa faixa. ⭐ **Leitura: o proxy transfere; vesti-lo de lei não acrescenta.**
> O gate mede e **ranqueia**; a lei só entra se houver extrapolação a fazer, e aí valem os avisos de
> [`2605.08541`](https://arxiv.org/abs/2605.08541) (razão tokens/parâmetro **fixa** = desenho
> colinear, coeficientes não identificáveis) e
> [`2603.22339`](https://arxiv.org/abs/2603.22339) (**viés sistemático até em dado sintético sem
> ruído**, e o viés **piora em multimodal**).

⭐ **[novo 09-01] E um achado contraintuitivo que vale testar na grade:**
[`2404.07982`](https://arxiv.org/abs/2404.07982) mediu que, em linguagens **clonadas** perfeitamente
equivalentes, **90/10 rende melhor que 50/50 nas DUAS línguas**, com o efeito **amplificando com
escala**. ⚠️ Os autores registram que em idiomas reais *"não é conclusivo"* — então é braço da
grade, não prescrição.

#### Gate T3 — throughput · **US$ 0,15**

`--passos 40` na configuração real, três leituras coincidentes a partir do passo 20 (§3).
**Nenhum compromisso de orçamento antes deste número.**

⚠️ **[novo 09-01] Esta regra continua sem par publicado.** Testado contra 800 resumos de
`all:throughput`: **ninguém publicou metodologia sobre quando o throughput estabiliza.** O mais
próximo ([`2608.03880`](https://arxiv.org/abs/2608.03880)) reporta o piso de ruído entre repetições,
não o transiente de aquecimento. A regra é nossa e fica.

##### ⭐⭐ [novo 09-01] Três coisas que este gate ganha da leitura

1. **Triagem por watts, não por `utilization%`.**
   [`2608.05944`](https://arxiv.org/abs/2608.05944) traz tabela que separa compute / comunicação /
   fome-de-dado / deadlock / ocioso pela potência da placa — **porque `utilization%` lê 100% durante
   um hang**. É o nosso §4 confirmado por terceiro. E traz um **portão de invariante de 2,7 s**, que
   é a nossa "guarda antes do passo 1" escrita por outra equipe.
2. 🔴 **A régua tem viés medido.** [`2608.00927`](https://arxiv.org/abs/2608.00927), com 76.691
   amostras pareadas: a telemetria **interna** — de onde sai `nvidia-smi power.draw`, base do nosso
   diagnóstico de teto elétrico — tem **viés de −1,988 W** contra medição externa. E o ranking de
   duas placas **inverte** conforme precisão/modo de potência (§2g em hardware).
3. ⚠️ **O proxy MFU→potência não vale no nosso regime.**
   [`2608.03880`](https://arxiv.org/abs/2608.03880) (≈3.000 runs, 6 GPUs) ajusta com ~1% de erro —
   **desde que o workload seja compute-bound**. O Bee com micro-batch 2 e logits gigantes **não é**.

##### ⭐⭐ [novo 09-01] E o mecanismo do nosso teto de micro-batch 2 tem conserto publicado

O vilão que medimos — o tensor `batch × seq × vocab` com upcast fp32 — é o que
[`2608.03796`](https://arxiv.org/abs/2608.03796) remove: perda **fundida e *chunked* que nunca
materializa o tensor de logits**, com memória de pico **linear no comprimento da sequência** — **4×
o contexto numa GPU só**. ⚠️ **Ressalva:** medido em H200, e a perda é **KL de destilação, não CE de
pré-treino** — o kernel e o argumento transferem, o número não.

⚠️ E vale saber que **ninguém mediu o custo de vocabulário grande no TREINO com cross-entropy
comum** — toda a evidência de vocab é do lado do decode. Some-se: **zero avaliações de Cut
Cross-Entropy ou Liger-Kernel por nome, e zero menções a *tied embeddings*** em 800 resumos —
**não há réplica independente do nosso "Liger deu 0%"**.

##### 🔴 [novo 09-01] Duas ideias de hardware que a leitura MATA antes de custarem dinheiro

| ideia | o que a mata |
|---|---|
| *"caixa de memória unificada grande para caber o vocab de 128k"* | [`2608.07226`](https://arxiv.org/abs/2608.07226): 2× DGX Spark (128 GB unificados cada) fazem **1.890 tok/s** contra os **62,9k tok/s** que medimos numa 5090. **Memória unificada não compra throughput de pré-treino** |
| *"GPU de segunda mão sai mais barato"* | [`2608.14614`](https://arxiv.org/abs/2608.14614): 128 GPUs usadas, **um ano em operação**, US$ 22 mil contra US$ 600 mil — e ainda **~4× mais carbono por token**. É o nosso §4 levado ao extremo e confirmado |
| *"MoE para caber mais parâmetro no mesmo hardware"* | [`2606.21428`](https://arxiv.org/abs/2606.21428): **MoE fica ~31% atrás de denso** em Jetson de 8 GB. 🔴 **Contradiz o MobileMoE** que a primeira triagem tinha aprovado |

##### ⭐⭐ [novo 09-01] E uma que a leitura ABRE

[`2608.09703` **Matryoshka**](https://arxiv.org/abs/2608.09703): sub-modelos de 500M/1,5B/3B
**aninhados numa arquitetura só** e treinados fim-a-fim ficam **em paridade** com baselines
independentes usando **36% menos compute total**. ⭐ Se o roadmap tem **350M e 1G**, treiná-los
juntos custa 36% menos que treiná-los separado — e o Bee-350M já existe como ponto de comparação.

#### Gate T4 — sucesso do run, declarado antes de gastar

| métrica | critério |
|---|---|
| **bpb por idioma** | acima do modelo público mais próximo em cada um |
| **tradução** | acima do piso de **copiar a fonte** (21,5 en→pt · 22,7 pt→en) em **todos** os pares |
| **as 9 capacidades** | com piso trivial ao lado de cada uma (`baseline_8_capacidades.py`) |
| **português** | ⚠️ **não pode ficar abaixo do Bee-350M** — 0,8207 bpb |

> ### 🔴🔴 [novo 09-01] Duas das réguas deste gate estão quebradas para o caso multilíngue
>
> **1. `bpb por idioma` não compara entre escritas.**
> [`2608.25089`](https://arxiv.org/abs/2608.25089) mede que **métricas normalizadas de uso corrente,
> o bpb entre elas, carregam viés crosslinguístico enraizado em tokenização, codificação e
> ortografia** — o comparador honesto é **NLL por sentença sobre sequências semanticamente
> equivalentes**. E [`2605.09015`](https://arxiv.org/abs/2605.09015) fecha: *"comparações de
> perplexidade entre escritas têm de contabilizar o byte-fallback, que **DEFLACIONA** a métrica para
> escritas não-latinas"*.
> ✅ **Conserto:** manter bpb **dentro** de cada idioma (comparação com o modelo público daquele
> idioma, que é o uso legítimo) e usar **NLL sobre corpus paralelo** para qualquer comparação
> **entre** idiomas. As duas coisas no mesmo relatório, rotuladas.
>
> **2. `max_new_tokens` fixo mede fertilidade, não capacidade.**
> [`2608.04160` **Mind the Cap**](https://arxiv.org/abs/2608.04160) — **540.000 decodificações**,
> famílias de teste congeladas prospectivamente, correção de Holm: o gap medido oscila **até 57
> pontos** conforme o orçamento de saída, e normalizar por comprimento move até 38,9. E o nulo que
> fecha: uma extensão de vocabulário tailandês **fecha 0,0 ponto** do gap no orçamento congelado.
> 🔴 **Com 8 idiomas de fertilidades diferentes, o nosso `--max-len` fixo vira a variável que a
> tabela está medindo.** ✅ **Conserto:** orçamento de saída **por idioma**, calibrado pela
> fertilidade, e a **taxa de truncamento reportada ao lado de todo número**.

⚠️ **[novo 09-01] E o critério de tradução ganha uma advertência que vem do lado do dado:**
[`2607.00890`](https://arxiv.org/abs/2607.00890) mede que **benchmark de múltipla escolha NÃO
enxerga diferença de qualidade de tradução** — só um juiz sensível a fluência recupera. E
[`2505.01761`](https://arxiv.org/abs/2505.01761) mede que a régua de MT tem **viés de comprimento**:
texto mais longo produz menos spans de erro e ranking de sistema pior.

⚠️ Schedule: [WSqD](https://arxiv.org/abs/2607.10959) conserta exatamente o defeito do WSD que
nos custou US$ 22 — o LR de pico fica amarrado ao horizonte original (§2d). Se ficar WSD, `--lr`
**explícito** e marcos comparados **só dentro do mesmo regime**.

### ✅⭐⭐ [MEDIDO 09-02] Eixo 2 fechado — o bpb decide, e a fertilidade errou o lado DUAS vezes

**18 corridas** (6 braços × 3 sementes), 3051 passos cada, cobertura 0,833, todas validadas.
Régua canônica: `cuda/bf16`, holdout de **1,5 MB por idioma**. Custo total **US$ 7,45**.

🔴 **Leia por coluna, nunca entre colunas** (`arXiv:2608.25089`): bpb carrega viés crosslinguístico
de tokenização e ortografia. Um byte de árabe e um de chinês não carregam a mesma informação.

| braço | par | por | spa | fra | deu | eng | arb | cmn | jpn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32k-atual *(controle)* | 151M | 2,063 | 2,076 | 2,186 | 2,785 | 2,329 | 1,628 | 3,265 | 2,117 |
| 32k-multi | 151M | 1,803 | 1,742 | 1,786 | 2,419 | 1,990 | 1,416 | 2,548 | 1,647 |
| 32k+32k-inplace | 165M | 1,833 | 1,781 | 1,826 | 2,454 | 2,017 | 1,428 | 2,710 | 1,731 |
| 64k-multi | 170M | 1,711 | 1,655 | 1,699 | 2,328 | 1,892 | 1,367 | 2,424 | 1,571 |
| **96k-multi** | 188M | **1,694** | **1,639** | **1,683** | **2,313** | **1,874** | **1,363** | **2,400** | **1,554** |
| 128k-multi | 206M | 1,703 | 1,647 | 1,693 | 2,325 | 1,882 | 1,382 | 2,423 | 1,578 |

#### O teste pareado — e a unidade é a SEMENTE, não o idioma

Os oito idiomas saem do **mesmo modelo**: contá-los como oito observações independentes é o erro
da §2y. A unidade correta é a corrida.

| comparação | por semente | média | **t** (n=3) | veredito |
|---|---|---:|---:|---|
| 64k **>** 32k-multi | −3,48% · −4,49% · −5,74% | −4,57% | **−7,00** | ✅ **decidido** |
| 96k **>** 128k | −0,69% · −1,56% · −0,16% | −0,80% | −1,97 | 🟡 marginal — mas **nenhuma semente favorece o 128k** |
| 96k **>** 64k | −1,17% · −2,04% · **+0,64%** | −0,86% | **−1,09** | 🔴 **NÃO decidido** |

⭐⭐ **A semente 44 inverteu o sinal em 8 de 8 idiomas — e as duas réguas independentes reproduziram
a inversão** (`cpu/fp32` com 8 KB: 8/8, 8/8, 1/8 · `cuda/bf16` com 1,5 MB: 8/8, 8/8, 0/8). Está nos
**modelos**, não na medição. Com duas sementes o relatório interino dizia *"96k > 64k, 8 de 8,
folgas de 0,7% a 2,9%"*; com três o **t cai para −1,09**. É a §2x cobrando exatamente onde ela avisa
que vai cobrar: **duas alertam, três decidem** — e desta vez decidiram contra a leitura de duas.

⚠️ **E a régua maior não podia resolver isso, o que foi previsto antes de rodá-la:** um holdout 187×
maior reduz o ruído *da medição*, mas a dispersão aqui está nos **pesos**. Medir melhor a semente 44
não torna o `64k` dela pior.

#### As quatro conclusões que sobrevivem

1. ✅ **Vocabulário multilíngue ganha do especializado em PT — inclusive em português**, por 12,6%,
   e por 22% a 27% em chinês e japonês. Mesmo número de parâmetros, mesmo custo de embedding, mesmo
   dado. O mecanismo é direto: com byte-fallback, uma janela de 2048 tokens cobre muito menos texto,
   então a passos fixos o controle vê **menos bytes**. Tokenizador ruim custa **dado** a computação
   fixa.
2. 🔴 **`128k` está morto pelo critério declarado antes de gastar.** É um modelo 18M maior — ganha
   capacidade de graça — e não vence em semente nenhuma. O desenho unilateral cumpriu o papel.
3. 🔴 **A expansão in-place é o pior braço multilíngue em 8 de 8**, e é justamente a que passou no
   eixo 1 com preservação latina perfeita.
4. 🟡 **`64k` × `96k` fica em aberto, e o desempate é de custo:** `64k` tem 18M de parâmetros a
   menos e roda **11% mais rápido** (68,8k contra 62,1k tok/s).

⭐ **A fertilidade apontou o lado errado duas vezes neste gate.** O `32k-multi` foi reprovado no
eixo 1 (+19,4% de fertilidade em PT) e é **12,6% melhor em bpb de PT**; o in-place passou no eixo 1
e é o pior dos multilíngues. **Fertilidade não é proxy de bpb** — é uma medida de compressão, e o
que decide é quanta informação o modelo perde por byte.

⚠️ **Uma ressalva que puxa para o `96k` e que este proxy não consegue medir.** Aqui o embedding de
96k é **29% do modelo** (d_model 576). No Bee-1G, com d_model 2048, cairia para **~20%**. O proxy
penaliza vocabulário grande mais do que o modelo real penalizaria — então a indecisão entre 64k e
96k não deve ser resolvida copiando este resultado para a escala de 1B.

#### ⭐ E a dispersão entre sementes virou achado próprio

| braço | amplitude média entre as 3 sementes | cobertura de escrita |
|---|---:|---|
| 32k-atual | **6,25%** | zero em CJK e árabe |
| 32k-multi · in-place · 64k · 96k | 1,32% – 1,48% | parcial a completa |
| 128k-multi | **0,23%** | completa, com folga |

⭐ **A reprodutibilidade entre corridas segue a cobertura do vocabulário**, e o `128k` — que perde em
bpb — é o mais estável dos seis. Faz sentido: mais parâmetros, menos sensibilidade à inicialização.
⚠️ Com 3 sementes isto é direção, não estimativa de variância.

**Artefatos:** `docs/gate-t1-bpb.json` (canônico) · os três de CPU levam `-cpu-8000b` no nome, por
construção, para não poderem ser confundidos com ele (§2z) · tokenizadores em
`bee/gate_t1_bpb/nl/tok_t1.tgz`, hash conferido contra a origem antes de o pod ser encerrado.


### ✅⭐⭐ [MEDIDO 09-03] `64k` × `96k` resolvido — e a hipótese que motivou o teste foi REFUTADA

O eixo 2 deixou esse par indeciso (`t = −1,09`). Antes de gastar, foram identificados **dois**
vieses do proxy contra o vocabulário grande, e medido o custo de corrigir cada um:

| viés | correção | custo |
|---|---|---:|
| fração de embedding: 21,7%/29,4% no proxy contra **10,9%/15,5%** no Bee-1G | exige ~1B de params não-embedding — a fração só cai com `d_model² × camadas`, não há atalho | **~US$ 93** |
| **tokens por parâmetro: 0,59 / 0,53** — modelos praticamente não treinados, e o `96k` recebe 20% menos que o `32k` | triplicar o treino | **US$ 6** |

Rodou-se o segundo. **`64k-multi` × `96k-multi`, 6.700 passos, 3 sementes, US$ 5,93.**

⚠️ **6.700 e não os 9.153 planejados**, e a razão é a guarda: o corpus rendeu pools de **279,0M**
(64k) e **264,7M** (96k), não os 300M pedidos. A 9.153 passos a cobertura passaria de **1,08 e
1,13 épocas** — repetição entrando em silêncio, que é o confundidor do `2606.24998` e justamente
o que este experimento não pode ter. 6.700 é o máximo com cobertura < 1 no braço que limita.

#### O resultado

| passos | tok/param | folga média | por semente | **t** (n=3) |
|---:|---|---:|---|---:|
| 3.051 | 0,59 / 0,53 | −0,86% | −1,17 · −2,04 · **+0,64** | −1,09 |
| **6.700** | **1,29 / 1,17** | **−0,29%** | −0,59 · **+0,60** · −0,88 | **−0,64** |

⭐⭐ **A folga ENCOLHEU 66% com 2,2× mais treino por parâmetro — o oposto do que a hipótese
previa.** A suspeita era que o subtreino penalizava o `96k` e que treinar mais o favoreceria.
Treinar mais **reduziu** a vantagem dele. E o sinal continua instável: de novo uma semente em
três inverte (a 43 agora, a 44 antes).

⭐ **A assinatura observável estava declarada antes de ler** (§2s): se o subtreino fosse o viés,
a folga cresceria com o treino. Ela caiu. A hipótese está refutada pelo experimento que a testava.

#### A decisão: `64k-multi`

A tendência é de **convergência, não de separação** — 0,86% a 0,55 tok/param, 0,29% a 1,23. O
Bee-1G treina em **20 a 170 tok/param**, ordens de grandeza acima. Extrapolar o valor exato seria
erro; a **direção** está medida.

E o termo que **não** encolhe é o custo, medido em 3 sementes de cada lado:

| | `64k-multi` | `96k-multi` |
|---|---:|---:|
| parâmetros (proxy) | 170M | 188M |
| throughput | **64,8 / 64,5 / 64,8k tok/s** | 58,8 / 58,5 / 58,6k |
| penalidade | — | **−9,6%** |

⚠️ **O que este experimento NÃO mostra:** não alcança o regime de treino real, e a fração de
embedding continua a do proxy. Corrigir isso custaria ~US$ 93 para decidir uma folga de 0,29% —
não se paga, e menos ainda agora que a folga é menor do que era quando o orçamento foi estimado.

#### 🔴 E dois defeitos meus, no mesmo dia e da mesma família

1. Ao acrescentar `--bracos`, duas iterações continuaram varrendo `BRACOS` inteiro. Com o
   controle fora do filtro, `avaliar` estourou `KeyError` **depois de medir os 6 modelos** —
   35 min de GPU medidos e **nenhum artefato gravado**.
2. A causa de o prejuízo existir não foi o `KeyError`: foi a **ordem**. A gravação ficava depois
   de toda a apresentação, então um defeito de **formatação** teve poder de destruir a
   **medição**. Corrigido para **medir → gravar → apresentar**.

⭐ É a terceira vez no mesmo dia que "persistir só no fim" custa medição — a primeira foi o
`meta.json` por braço no Gate T1, a segunda o `_grava_probe` por lote no T-TRAD.


### ✅⭐⭐ [MEDIDO 09-03] Gate T2 — a mistura decide, e a troca é 3,5× a favor do português

**9 corridas** (3 misturas × 3 sementes), 6.700 passos, cobertura 0,878, mistura efetiva com
desvio máximo de **0,01 pp** do alvo. Régua canônica `cuda/bf16`, holdout de 1,5 MB — **o mesmo
do Gate T1**, de propósito. Custo **US$ 8,49**.

⭐ **Este gate é mais limpo que o T1 por construção.** Lá os braços tinham vocabulários
diferentes, então tokens/parâmetro *diferia* entre eles (0,59 contra 0,53) e virou viés. Aqui o
tokenizador (`64k-multi`), a arquitetura, o total de tokens e a cobertura são **idênticos** —
a única variável é a proporção de português.

| braço | PT | por | spa | fra | deu | eng | arb | cmn | jpn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `bal-12` | 12,5% | 1,4281 | 1,3917 | 1,4088 | 2,0178 | 1,5799 | 1,2008 | 2,0170 | 1,2723 |
| `pt-25` | 25% | 1,3700 | 1,3957 | 1,4226 | 2,0361 | 1,5974 | 1,2198 | 2,0572 | 1,2962 |
| `pt-50` | 50% | **1,2801** | 1,3832 | 1,4380 | 2,0658 | 1,6044 | 1,2613 | 2,1332 | 1,3280 |

#### O pareado, com a SEMENTE como unidade

| comparação | PT | **t** | os outros 7 | **t** |
|---|---:|---:|---:|---:|
| `bal-12` → `pt-25` | **−4,06%** | **−8,38** | +1,25% | 2,62 |
| `pt-25` → `pt-50` | **−6,56%** | **−17,62** | +1,66% | 6,38 |
| `bal-12` → `pt-50` | **−10,35%** | **−12,84** | +2,95% | 3,93 |

⭐⭐ **Sem ambiguidade nenhuma, ao contrário do gate do vocabulário.** O piso de dispersão entre
sementes é **0,78% a 1,24%**, e o efeito em português é de 4% a 10% — o sinal é consistente nas
três sementes e nas três comparações. Não é o caso de "duas alertam, três decidem": aqui as três
concordam.

#### ⭐⭐ A taxa de troca, e ela NÃO piora

| de → para | PT ganha | os 7 perdem | **razão** |
|---|---:|---:|---:|
| 12,5% → 25% | −4,06% | +1,25% | **3,24×** |
| 25% → 50% | −6,56% | +1,66% | **3,95×** |
| 12,5% → 50% | −10,35% | +2,95% | **3,51×** |

**Cada ponto de bpb perdido nos outros sete compra 3,2 a 4,0 pontos em português**, e a razão não
degrada ao dobrar a fatia de 25% para 50% — se algo, melhora. Não há retorno decrescente na faixa
medida.

#### Dois achados por idioma

⭐ **O espanhol não paga a conta.** Em `pt-50` ele fica em **−0,61%**, dentro do ruído de 1,03% —
isto é, **inalterado**, enquanto os outros seis pioram. É transferência do português para a língua
mais próxima, e é o único idioma que escapa.

🔴 **Quem paga são as escritas distantes:** chinês **+5,76%**, árabe **+5,04%**, japonês **+4,38%**,
todos muito acima do ruído. **O custo da mistura não é distribuído — ele se concentra em CJK e
árabe.**

#### A decisão

✅ **A mistura uniforme de 12,5% é a pior escolha possível para o objetivo declarado do projeto.**
Se o português é a capacidade que importa, `pt-50` compra 10,35% de bpb ao custo de 2,95% nos
outros — e o preço recai sobre CJK e árabe, não sobre as línguas latinas.

⚠️ **O que este gate NÃO mostra:**
· mede **bpb, não capacidade** — o E2 mediu que são coisas diferentes;
· roda a 150M params e 1,29 tok/param, e o mesmo dia mediu que folgas entre braços **encolhem**
  com mais treino: isto é um **TETO**, não o valor no Bee-1G;
· não há braço 100% PT — 220M tokens pedidos contra 157M existentes seria repetição.

#### 🔴🔴 E o erro que a guarda §2r pegou: pool de treino montado a partir do HOLDOUT

A função do T1 chama-se `_no_holdout` e é **português** — *"[está] no holdout"*, devolvendo `True`
para quem deve ficar **fora** do treino. Foi lida como o inglês *"no holdout"* = "não é holdout",
a condição foi invertida, e os pools de treino saíram do holdout.

**Nada daria erro.** O treino rodaria, a loss cairia, e o bpb sairia absurdamente bom porque o
modelo teria visto exatamente o texto da avaliação — e o relatório diria *"a mistura não custa nada
ao português"*.

⭐ O que pegou foi a guarda de **mistura efetiva** (§2r), mas de raspão e nomeando a causa errada
(*"reduza --pool-tokens"*). O sintoma real era **98% de descarte com um holdout de 2%**. Trocada por
uma guarda direta sobre a taxa de descarte, com limites dos **dois** lados — a primeira versão
pegava o filtro invertido (98%) e deixava passar o filtro **morto** (0%), o que só apareceu porque
a guarda foi testada antes de ser usada.

⭐ E a §2r disparou uma **segunda** vez, por outra causa: o espanhol tinha só 23,5M tokens e o braço
`bal-12` precisa de pool/8 de **cada** idioma. Sem ela, o braço rotulado "12,5% uniforme" teria sido
treinado com `por 14,1% / spa 10,6% / fra 11,3% / …` — o rótulo mentiria e o gate mediria outra
proporção. **A saída não foi encolher o experimento: foi coletar**, 500 Mcar de PT e 300 Mcar de
cada um dos outros 7, em ~4 minutos de banda.


### ✅⭐⭐ [MEDIDO 09-04] Gate de throughput do Bee-1G — e três coisas que a extrapolação errava

Rodado na configuração **real**, com as decisões já fechadas: geometria `ESCADA["1b"]`
(28 camadas · d_model 1792 · 28q/4kv · intermediate 4864), vocabulário **64.000** do Gate T1 e
pool **`pt-50`** do Gate T2. Resultado: **1,052B parâmetros, embedding em 10,9%**.

⭐ Repare que **10,9% é exatamente a fração que o proxy do T1 não conseguia reproduzir** — lá o
embedding do `64k` era 21,7% do modelo, o dobro. Foi por isso que o custo de corrigir aquele viés
foi estimado em ~US$ 93 e a correção recusada. Aqui ela vem de graça, como subproduto da
configuração real.

| mb | seq | tok/passo | tok/s | VRAM pico | **US$/B tok** | dispersão |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2048 | 8.192 | 10.494 | 20,3 GB | 26,21 | 🔴 **4,0%** |
| 2 | 2048 | 16.384 | 13.456 | 21,7 GB | 20,44 | 1,3% |
| **4** | **2048** | 32.768 | **14.470** | 24,9 GB | **19,00** | 0,3% |
| 1 | 4096 | 16.384 | 12.487 | 22,1 GB | 22,02 | 0,5% |
| 2 | 4096 | 32.768 | 13.489 | 25,4 GB | 20,39 | 0,5% |
| 4 | 4096 | — | 🔴 **OOM** | — | — | — |

#### O orçamento, medido

| cenário | tok/param | horas | **US$ @0,99/h** |
|---|---:|---:|---:|
| Chinchilla (~20×) | 20 | 403 | **399** |
| como o Bee-350M | 63 | 1.267 | **1.254** |
| como o Bee-150M | 143 | 2.880 | **2.851** |

#### 🔴 As três coisas que a extrapolação errava

**1. Sem recomputação de ativações o modelo NÃO TREINA em 32 GB** — nem com micro-batch 1 a
`seq_len` 4096. A tabela de custo anterior deste plano projetava horas e dólares para uma
configuração **que não roda na placa assumida**: a aritmética estava certa e a premissa não.
O culpado tem nome e já estava nas lições do projeto: a `64k` de vocabulário e 4096 de contexto,
o **tensor de logits** sozinho é `4096 × 64.000 × 2 B = 524 MB` em bf16, dobrados pelo *upcast*
da perda, antes de qualquer ativação das 28 camadas — a mesma lição que o SFT já pagou.

**2. `seq_len` 2048 é MAIS RÁPIDO que 4096** — 14.470 contra 13.489 tok/s (−7%) e com 0,5 GB a
menos. A geometria da escada especifica 4096, e agora o preço disso está medido. Contexto longo
tem valor próprio e não é uma decisão de throughput, mas ela deixou de ser gratuita.
⚠️ E a 4096 o micro-batch trava em 2: o `mb=4` estoura. Isso limita o tamanho de lote efetivo
sem acumulação adicional.

**3. A guarda da §3 reprovou um ponto.** Os 10.494 tok/s do `mb=1 seq=2048` vieram com **4,0% de
dispersão** entre as três últimas leituras, acima do teto de 3% — o regime não tinha estabilizado.
Todas as outras cinco ficaram entre 0,3% e 1,3%, então a instabilidade era daquela configuração
(lote menor, mais sensível a jitter), não da medição. O ponto vai marcado no artefato e **não
entra em conta nenhuma**. É exatamente o erro que este projeto cometeu três vezes numa hora:
ler throughput de um número solto.

⚠️ **TETO OTIMISTA, declarado:** 40 passos não veem queda térmica nem I/O de checkpoint. Os
US$ 399–2.851 são um piso, não a média de um run longo.


### ⭐⭐ [MEDIDO 09-04] Os Gemstones respondem T0.b — e a resposta depende da unidade do orçamento

O plano (§3, T0.b) listou *"ler a razão d_model/camadas nos Gemstones"* como experimento de custo
**zero** — 4.000+ checkpoints até 2B com formas arquiteturais diversas, publicados. Lido em 09-04.

#### O achado, em uma frase

> **Modelos profundos alcançam menor loss por FLOP; quando o orçamento é medido em GPU-horas, os
> largos se tornam Pareto-ótimos** ([`2502.06857`](https://arxiv.org/abs/2502.06857), Figura 7).

⭐⭐ **A nossa unidade de orçamento é GPU-hora alugada, não FLOP.** O próprio plano registra isso na
§1 (`2603.28823`: *"sob restrição de tempo, o modelo ótimo é MAIOR que o compute-ótimo"*). Pela
metade da lei que se aplica a nós, **a direção é largura, não profundidade** — e isso concorda com
o *Depth Delusion* que o T0.b já citava, agora por um mecanismo diferente (custo de paralelismo, não
loss).

#### ⚠️ E a ressalva é dos próprios autores, o que a torna mais forte

> *"isto provavelmente se deve ao nosso esquema de treino — não usamos paralelismo de pipeline, só
> tensor+dados… nossas observações sobre gasto de recurso **podem não generalizar** para outras
> estratégias de paralelismo"*

🔴 **E o nosso caso é ainda mais diferente do deles: treinamos em UMA GPU, sem paralelismo nenhum.**
O mecanismo que eles apontam — modelos largos são mais fáceis de escalar sob tensor parallelism —
**não se aplica a nós**. Sobram mecanismos de GPU única (menos lançamentos sequenciais de kernel,
matmuls maiores saturando melhor os tensor cores), que empurram na mesma direção mas com magnitude
desconhecida.

⭐ **Aceitar a conclusão deles seria a §2g em forma de hardware:** o número foi medido num aparato
que não é o nosso.

#### ⭐⭐⭐ A saída, e ela é dos autores também

> *"praticantes podem transformar nossa análise de GPU-horas para o hardware deles: **basta rodar
> cada forma por algumas dezenas de passos, registrar os tempos de passo** e reajustar as leis"*

**É exatamente o que o `bee/gate_throughput_1g.py` já faz** — 40 passos, throughput em regime,
mediana de três leituras (§3). Medir 4 formas custa ~20 min de GPU, **US$ 0,35**.

**As formas candidatas, todas com ~985M de parâmetros não-embedding** (o mesmo orçamento do
`ESCADA["1b"]` atual), variando só a razão:

| camadas | d_model | intermediate | não-emb | total @64k | **razão d/L** |
|---:|---:|---:|---:|---:|---:|
| 16 | 2432 | 6592 | 986M | 1,141B | **152,0** |
| 20 | 2176 | 5888 | 985M | 1,124B | 108,8 |
| 24 | 1984 | 5376 | 984M | 1,111B | 82,7 |
| **28** | **1856** | **4992** | 999M | 1,118B | **66,3** ← atual |
| 32 | 1728 | 4672 | 993M | 1,104B | 54,0 |
| 40 | 1536 | 4160 | 982M | 1,081B | 38,4 |

⚠️ **E há um custo que só aparece com vocabulário grande:** o embedding escala com `d_model`, então
a 64k **cada +64 de d_model custa +4,1M de parâmetros**. A forma mais larga (16×2432) tem 1,141B
contra 1,081B da mais profunda — **5,5% a mais de parâmetro para o mesmo poder de cálculo**. A
comparação honesta é por **tokens/segundo a parâmetros iguais**, não por forma isolada.

✅ **Decisão:** entra na sessão de pod junto com o sweep de LR (#5) e o braço de transferência (#6)
— 4 formas × 40 passos. **O que decide é tok/s medido nesta placa**, não a figura do paper.

⚠️ **O que este experimento NÃO vai mostrar:** qualidade. Os Gemstones medem que profundo ganha em
loss por FLOP; medir só tok/s escolheria a forma mais rápida ainda que ela aprendesse menos. O
número de tok/s é **metade** da decisão — a outra metade é a loss por forma, que só se mede
treinando, e que o próprio suite dos Gemstones já publicou. **A leitura correta é: usar a loss deles
com o nosso tempo de passo**, que é literalmente a receita do parágrafo citado.

##### ✅⭐⭐ [MEDIDO 09-04] A varredura de forma rodou — largura ganha, e a receita dos Gemstones transferiu

4 formas a ~940M de parâmetros não-embedding, `mb=4 seq=2048` com recomputação de ativações, 40
passos cada, dispersão entre as 3 últimas leituras de **0,0% a 0,5%** (teto da §3 é 3%).

| camadas × d_model | heads/kv | **d/L** | params | **tok/s** | VRAM | US$/B |
|---|---|---:|---:|---:|---:|---:|
| **16 × 2560** | 40/10 | **160,0** | 1,102B | **15.512** | 25,5 GB | **17,73** |
| 24 × 2048 | 32/8 | 85,3 | 1,072B | 14.403 | 25,1 GB | 19,09 |
| 28 × 1792 ← `ESCADA` | 28/4 | 64,0 | 1,062B | 14.809 | 25,0 GB | 18,57 |
| 40 × 1536 | 24/6 | 38,4 | 1,042B | 13.669 | 25,0 GB | 20,12 |

⭐⭐ **A forma mais larga é 13,5% mais rápida que a mais profunda**, e a direção é a que os
Gemstones medem para GPU-hora. ⭐ **O que transfere é a conclusão, não o mecanismo:** eles
atribuem o efeito ao tensor parallelism e dizem que *"pode não generalizar"*; nós treinamos em
**uma GPU, sem paralelismo nenhum**, e o efeito aparece igual. Logo a causa é outra — provavelmente
menos lançamentos sequenciais de kernel e matmuls maiores saturando melhor os tensor cores.

⚠️ **E a monotonicidade quebra num ponto:** o `24×2048` (14.403) fica **abaixo** do `28×1792`
(14.809), invertendo a ordem esperada. Com dispersão de 0,2% e 0,5% a diferença de 2,7% está fora
do ruído — é real, e não tem explicação no modelo simples "mais largo, mais rápido". Fica
registrado como anomalia, não alisado.

🔴 **O custo que a tabela esconde:** a forma mais larga tem **1,102B contra 1,042B** parâmetros —
**5,8% a mais**, porque o embedding escala com `d_model` a 64k de vocabulário. Ela é mais rápida
**e** maior. O `US$/B tokens` já embute isso; uma comparação de **qualidade** entre as formas não
seria a parâmetros iguais.

🔴 **E o que esta varredura NÃO mede: qualidade.** Os Gemstones medem que **profundo ganha em loss
por FLOP**. Escolher a forma mais rápida sem isso seria escolher a que aprende menos por passo. A
leitura honesta é: **largura compra 13,5% de relógio, e a loss publicada deles diz quanto isso
custa em qualidade** — que é exatamente a composição que os autores propõem, e que este número
torna possível.

⚠️ **Decisão em aberto, não fechada por este gate.** Trocar `28×1792` por `16×2560` compra 4,7% de
throughput ao custo de 3,8% de parâmetro a mais e de uma perda de qualidade não medida. **Não é
troca óbvia**, e o item entra no plano como decisão, não como conclusão.

### Estágio V — visão · Estágio A — áudio

#### 🔴 A decisão de identidade, declarada antes

| | o que significa | viabilidade |
|---|---|---|
| **(a) encoders pré-treinados** | Bee de texto do zero + SigLIP (Apache-2.0) e encoder de fala (MIT) **congelados** + projetor treinado por nós | ✅ é o que a literatura faz nesta escala |
| **(b) encoders do zero** | treinar classe CLIP: bilhões de pares imagem-texto | 🔴 **US$ 10k+**, fora de qualquer orçamento aqui |

⚠️ **Em (a), "do zero" passa a cobrir o backbone de texto, o tokenizador, o projetor e a fusão —
não os olhos e os ouvidos.** Isso é afirmação pública sobre o que o Bee-1G é, e o projeto já teve
essa crise uma vez (2026-07-26, quando o que existia era Qwen4B + adapters).

~~**Recomendação: (a).**~~ Prova na nossa faixa:
[SigLIP-2 + Qwen3-0.6B ≈ 1B rende F1 0,753](https://arxiv.org/abs/2608.18591).

> ### 🔴🔴 [corrigido 09-01] A recomendação estava do lado errado — e existe uma terceira opção
>
> [`2504.07951`](https://arxiv.org/abs/2504.07951) — **457 modelos treinados**. Resultado **NULO**
> sobre a suposição dominante: **não há vantagem inerente de late-fusion sobre early-fusion**. Ao
> contrário — **early-fusion, sem encoder de imagem e sem tokenizador visual, é MAIS FORTE em
> contagens baixas de parâmetro**, mais barata de treinar e mais fácil de servir.
>
> A opção (a) que eu recomendei **é late-fusion**. E early-fusion **dissolve as duas coisas de uma
> vez**: é mais forte no nosso regime **e** não tem encoder emprestado — então *"do zero"* volta a
> cobrir os olhos, sem os US$ 10k+ da opção (b).
>
> ⭐ **Convergindo:** [`2607.22043`](https://arxiv.org/abs/2607.22043) (nativo, do zero) mede que **a
> lei de alocação da LINGUAGEM é praticamente invariante à composição do dado** — acrescentar imagem
> **não deve** custar a alocação do texto — e que há **transferência positiva** (melhora raciocínio
> espacial em texto puro). O risco está do outro lado: a lei **multimodal** é que é sensível.
>
> ⚠️ **Três coisas que a mudança traz junto:**
> 1. [`2608.17286` Abra](https://arxiv.org/abs/2608.17286) mede a otimalidade da parte visual em
>    **~200 tokens de imagem por parâmetro — 10× a prescrição de Chinchilla**. **Um único "tokens
>    por parâmetro" para o modelo inteiro é a régua errada;**
> 2. [`2603.22339`](https://arxiv.org/abs/2603.22339) mede que o viés do método de ajuste padrão
>    **PIORA em multimodal**, por assimetria mais alta da superfície de loss;
> 3. [`2606.17118`](https://arxiv.org/abs/2606.17118) — se houver MoE, **a dominância numérica de
>    tokens de visão sequestra a estatística de expert e mascara os experts críticos para texto**:
>    qualquer decisão tomada sobre contagem de ativação **está medindo visão**.
>
> 🔴 E o aviso de escopo: [`2412.05149`](https://arxiv.org/abs/2412.05149) registra que, no BabyLM,
> **nenhuma submissão superou os baselines na trilha multimodal**. O estágio V tem histórico de não
> pagar em escala pequena — o que reforça o gate com piso trivial, não o dispensa.

⚠️ **Dois achados que contrariam a intuição:**
- [Whisper **não** é escolha automática](https://arxiv.org/html/2606.09317): FastConformer
  **congelado + sonda linear** passa de 90% de acurácia macro **fora do domínio** e o bate;
- 🔴 [o desempenho é **não-monótono** no número de encoders congelados fundidos](https://arxiv.org/abs/2608.17490)
  — mais modalidades **não** é melhor por soma.

⭐ E [poda de tokens visuais sem treino, 729 → 16](https://arxiv.org/abs/2608.19285), viabiliza
VLM em 8 GB — o orçamento visual pode ser uma ordem de grandeza menor do que parece.

**Gate V / A:** contra um **piso trivial** de cada tarefa (a legenda mais frequente do conjunto;
ASR de referência no idioma), pelo mesmo princípio do E0. Sem piso, *"o modelo descreve imagens"*
é opinião.

⚠️ **Transversal:** cada estágio remede o que o anterior sabia fazer. O projeto tem **três**
medições de que capacidade é disputada (E2, E19, E21) e nenhuma razão para supor que visão e
áudio sejam de graça para o texto.

---

## 4. Pós-treino — a receita já está validada

`docs/fase2-capacidades-em-zero.md`, medido em 2026-08-30/31 por **US$ 1,20**:

- ⭐⭐ **adapter por capacidade, não dose.** Resumo dentro do adapter agêntico: 14,7% e −9,0 pp de
  execução. Em adapter próprio: **33,3% e custo zero**;
- **roteador determinístico** (30 linhas, sem GPU): 954/954;
- **a régua vira a guarda** da geração, validada contra o **estado quebrado**;
- **piso trivial** ao lado de cada número;
- **3 sementes** — aqui elas voltam a ser possíveis (LoRA custa 1h45, não US$ 300).

⚠️ E o que a Fase 2 **não** resolveu: `resumo` fica em 49,0% de média contra piso de 51,3% —
**perde para o `head -2`**, com amplitude de 19,3 pp entre sementes. `código` emite bloco em
877/877 (era 876 sem código) mas `pass@1` fica em 0,1–0,2%.

---

## 5. Corpus — e por que NÃO começar coletando

⭐ **O gargalo medido é filtro, não volume:**
- [um SLM de 0,8B supera modelos de 27B e 122B](https://arxiv.org/abs/2608.18655) em tradução de
  19 línguas africanas, e o filtro por estimativa de qualidade **remove até 96% dos tokens de
  treino sem degradar**;
- [refinar 20T para 10T supera o corpus inteiro](https://arxiv.org/abs/2607.20062) a orçamento
  igual de tokens;
- [`2606.29858`](https://arxiv.org/abs/2606.29858) dá o mecanismo do nosso "+45% = 0,19%": o
  aprendizado de cada token é uma **transição localizada**, e mais do mesmo corpus **não tem
  transição nova para comprar**.

**Fontes já verificadas:**

| fonte | cobertura | licença |
|---|---|---|
| `HuggingFaceFW/fineweb-2` | **1.813 idiomas** — `por` `spa` `fra` `deu` `jpn` `cmn` `arb` | **ODC-By** ✅ |
| FineWeb (inglês) | 🔴 o fineweb-2 **não tem inglês** | a verificar |
| [MultiSynt/MT](https://arxiv.org/abs/2607.00890) | ~4,8T tokens multi-paralelos, **36 idiomas** | a verificar |
| [ClassiCC-PT](https://arxiv.org/abs/2606.28999) | 106M documentos PT | a verificar |
| paralelo (EuroParl, OpenSubtitles) | tradução — web crawl dá monolíngue, não pares | a verificar |
| 🔴 **Pixabay** | **REPROVADO** — licença **não menciona treino de ML** e proíbe redistribuir | — |

⚠️ [O filtro que construiu o fineweb-2 é gamável por formatação](https://arxiv.org/abs/2605.23721):
uma reformatação "estilo Wikipédia" faz o classificador **FineWeb-Edu inverter a decisão em ~7%**.
Nosso corpus **é** fineweb-2 e nós treinamos um classificador edu — ele mede **formato**.

### ✅ [MEDIDO 09-01] O inglês do FineWeb passa — e o piloto errou por 170×

**Por que o censo era obrigatório:** a dedup do FineWeb é **por crawl**, declarada pelos autores e
escolhida por medição. Logo **duplicata ENTRE crawls sobrevive por construção** — e os configs
`sample-*BT` são amostrados **através** dos 96 dumps, que é exatamente onde ela se concentraria.
Tokenizado com **o nosso** tokenizador, porque token == FLOP e o FineWeb conta em gpt2 (§2g).

| | `sample-10BT`, censo completo |
|---|---:|
| documentos | 14.868.871 |
| tokens (**nosso** tokenizador) | **14,412 B** |
| FLOPs em duplicata **exata** | **0,682%** |
| FLOPs em **quase**-duplicata | **0,975%** |
| ⚠️ faixa **3–10×** (pico do dano) | **0,023%** |
| pares testados | 411.869 · 23,2 min de CPU |

✅ **Veredito: ADOTAR.** O `2606.24998` mede que **10%** dos FLOPs em repetidos equivale a perder
**um terço** da computação; estamos em **1%**, e a faixa de pico do dano é **0,023%** — desprezível.

#### 🔴 E o achado de método: **censo de duplicação NÃO PODE ser pilotado**

O piloto (208.000 docs, os primeiros do stream, **1,4%** da amostra) deu **0,004%**. O completo deu
**0,682%** — **170× mais**.

⭐ **E isso não foi azar: é aritmética.** Para uma duplicata ser **detectável**, as **duas** cópias
precisam cair na amostra. Numa amostra de fração *f*, a taxa medida ≈ taxa real × *f*. Com
*f* = 1,4%: 0,676% × 0,014 = **0,0095%** previsto, contra 0,004% medido — mesma ordem.

⚠️ **A consequência geral:** todo piloto de duplicação subestima **pela fração amostrada**, por
construção. Um piloto de 1% lê ~100× baixo e **parece um resultado limpo**. Se o corpus tivesse 5%
de repetição — dano real — o mesmo piloto teria impresso 0,07% e eu teria escrito "🟢 repetição
baixa" com a mesma confiança. **É censo completo ou nada.** Custa 23 min de CPU.

#### ⚠️ E dois números do prep que mudam contas do plano

1. **`sample-10BT` são 10B tokens de *gpt2*, e 14,41B nos nossos** — **+44%**. Orçar inglês pelo
   número publicado erraria por quase metade (§2g).
2. **Fertilidade do nosso tokenizador PT em inglês: 0,3124 tok/byte**, contra **0,218** em
   português — **+43%**. Entra no Gate T1 como medição, não como suposição.

🔴 **E um atalho que está morto:**
[fundir modelos monolíngues causa colapso por interferência](https://arxiv.org/abs/2605.25846) —
similaridade representacional é pré-requisito e **não sobrevive ao pré-treino separado**.

---

### ⭐⭐⭐ [novo 09-01] A evidência mais forte do lote diz TRADUZIR, não coletar

[`2607.00890` **MultiSynt/MT**](https://arxiv.org/abs/2607.00890) traduziu **100B tokens do
Nemotron-CC** para 36 idiomas europeus. Modelos treinados nisso **atingem o escore final do HPLT 2.0
(dado NATIVO) com ~72% menos tokens de pré-treino**, e o superam em **~15% relativo com orçamento
igual**.

E [`2605.13225` **Mix, Don't Tune**](https://arxiv.org/abs/2605.13225) — **~1.000 runs de pré-treino,
quatro escalas de 150M a 1,43B**, a nossa faixa exata — mede que misturar vale **2–3× o dado único
do alvo em loss e 2–13× em acurácia downstream**, com a folga **CRESCENDO** com o tamanho do modelo.

⚠️ **Três ressalvas que os próprios autores medem, e todas são do tipo que este projeto já cobra:**
1. **benchmark de múltipla escolha NÃO enxerga diferença de qualidade de tradução**;
2. **tarefa idiomática e culturalmente ancorada continua melhor servida por dado nativo**;
3. 🔴 **a loss de validação na língua-alvo SUBESTIMA sistematicamente o valor da mistura** — captura
   só o efeito de regularização, não o conhecimento novo. **Medir por bpb do PT daria a resposta
   errada** (§2y).

### 🔴🔴 E a recomendação acima tem uma interação NÃO MEDIDA com o nosso pior defeito conhecido

Busca explícita em ~15.000 resumos: **zero artigos sobre dedup near-duplicate ENTRE idiomas**, e zero
sobre **traduções paralelas duplicadas no pré-treino**.

⚠️ O MultiSynt/MT é **multi-paralelo por construção** — o mesmo documento existe em 36 versões. E o
`2606.24998`, que já está nas nossas lições (§2c #6), mede que **repetição interna causa dano
NÃO-monotônico com pico em contagem intermediária**, e que **o pico se desloca com o tamanho do
modelo**. Reforço: [`2606.29605`](https://arxiv.org/abs/2606.29605) mede que num corpus gerado por
LLM **só 10,9% é conteúdo único treinável; a contagem crua superestima a informação em ~9×**.

🔴 **A recomendação mais forte do lote e o nosso defeito mais bem documentado se encontram num ponto
que a literatura não mediu.** Se o Bee-1G usar dado traduzido em volume, **o histograma de repetição
cross-lingual é medição obrigatória**, não opcional.

### ✅⭐⭐ [MEDIDO 09-02] O censo rodou — e a interação temida NÃO existe no Common Corpus

A seção acima declarou o histograma cross-lingual como **medição obrigatória**. Ele foi feito.

**Método** (`bee/gate_trad_censo.py`): a digital de um documento é o hash da sequência ordenada dos
seus 12 primeiros números, exigindo ao menos 8. ⭐ **Número sobrevive à tradução** — um relatório
orçamentário em francês e a versão dele em alemão carregam os mesmos valores, enquanto todas as
palavras mudam. É a única assinatura barata que atravessa idioma.

**Escala:** 5 idiomas × 40.000 documentos do Common Corpus = 200.000 lidos, **31.042 digitais**
retidas nos baldes.

| | digitais | fração |
|---|---:|---:|
| **cross-lingual** (a mesma digital em 2+ idiomas) | **16** | **0,05%** |
| intra-idioma (a mesma digital repetida no idioma) | 109 | 0,35% |

E a distribuição é rasa: **15 das 16** aparecem em exatamente 2 idiomas, **uma** em 3. Nenhuma em 4
ou 5. Os pares mais comuns são `de-es` (4), `en-fr` (3), `es-it` (3).

⭐⭐ **O que isso refuta é uma previsão minha, escrita antes.** Eu havia registrado que o
`OpenGovernment` do Common Corpus seria multi-paralelo por construção — documentos da UE existem
oficialmente em 24 idiomas. A medição diz que **não**: o Common Corpus é uma união de coleções
nacionais independentes, não um corpus alinhado. A interação perigosa que o `2606.24998` descreve
**não é instanciada por esta fonte**.

⚠️ **E a §2ac foi respeitada por construção.** O piloto do FineWeb errou por **170×** porque, para
uma duplicata ser detectável, as **duas** cópias precisam cair na amostra — o viés é estrutural e
sempre para baixo. Aqui a amostragem é **por balde de digital**, não por documento: as duplicatas
caem no mesmo balde por definição, então a medição *dentro* dos baldes retidos não carrega o viés.

⚠️ **Quatro coisas que este censo NÃO mostra**, e a §2q exige que estejam escritas:
1. **texto sem números** — literatura e ficção ficam fora; a cobertura admissível vai de 75,4% (en)
   a 43,2% (it), e o resto é invisível a esta régua;
2. **tradução que escreve número por extenso** — "doze mil" quebra a digital;
3. **duplicação semântica sem números em comum** — dois textos sobre o mesmo fato, redigidos do zero;
4. é um **piso**, nunca um teto.

🔴 **E a medição que ainda falta, que é diferente desta.** O censo limita a duplicação **dentro do
lote traduzido**. Ele **não mede** duplicação entre o lote traduzido e o **nosso corpus PT atual**
(fineweb-2, 21,97B). São distribuições diferentes — Common Corpus é livro, jornal e administração
pública; o nosso é web — mas a web republica domínio público, e a suposição de que não há
interseção é exatamente do tipo que este projeto já pagou para não fazer. Custa o mesmo script com
o PT existente como sexto idioma.

**Veredito do estágio A: ✅ traduzir não cria o problema do `2606.24998`.** O estágio B — traduzir
uma fatia limitada e medir a qualidade — segue liberado, com a ressalva já registrada de que
**a régua não pode ser bpb do PT** (`2607.00890` mede que a loss na língua-alvo subestima
sistematicamente o valor da mistura).

⚠️ **E a licença do tradutor é parte da decisão, não detalhe.** Verificado na origem: **NLLB em
todas as variantes e TowerInstruct são `cc-by-nc-4.0`** — usá-los contaminaria o modelo publicado.
Limpos: **Madlad-400** e **Opus-MT** (Apache-2.0), **ALMA** (MIT).


### ✅⭐⭐ [MEDIDO 09-02] O custo de traduzir — e a razão que enquadra a decisão

`bee/gate_trad_b.py probe`, medido em duas placas, nunca extrapolado (§3, §4).

| lote | RTX 5070 Laptop (8 GB) | **RTX 5090 (32 GB)** | VRAM |
|---:|---:|---:|---:|
| 16 | 135 tok/s | 225 tok/s | 6,9 GB |
| 32 | OOM | 319 tok/s | 8,4 GB |
| 64 | OOM | 343 tok/s | 11,3 GB |
| **128** | OOM | **683 tok/s** · 24,0 sent/s | 20,0 GB |
| 256 | OOM | OOM | — |

⭐ **A §4 acertou na casa decimal.** Razão de TDP 575 W / ~110 W = **5,2×**; ganho medido
**5,06×**. O preditor de throughput entre placas continua sendo o TDP, não o preço nem a VRAM.

⚠️ E o ótimo se desloca com a memória: na placa de 8 GB o lote 16 já era o teto e o 24 piorava
por saturação; com 32 GB o ótimo é **128**. Medir numa placa e copiar o lote para outra teria
deixado 5× de desempenho na mesa.

| volume de PT traduzido | horas na 5090 | **US$ @0,99/h** |
|---|---:|---:|
| 0,10B tokens | 41 | **40** |
| 0,25B | 102 | **101** |
| 0,50B | 203 | **201** |
| 1,0B | 407 | **403** |

#### ⭐⭐ A razão que decide o ESCOPO

O pré-treino do Bee-350M custou **US$ 115 por 21,75B tokens = US$ 5,30 por bilhão**.

> **Traduzir um token custa 76× o que custa treinar nele.**
>
> ⚠️ **[corrigido 09-04]** O 76× foi calculado contra o **350M** (US$ 5,30/B). O gate de
> throughput mediu o **1G** em **US$ 19,00/B** → a razão real é **21×**. A conclusão qualitativa
> (tradução é composição, não volume; escopo 0,1–0,25B) sobrevive; o número não.

⚠️ Isso **não** reprova a tradução — reprova **tradução como jogada de volume**. Some-se a isso
o que este projeto já mediu por conta própria: **+45% de mais-do-mesmo corpus PT rendeu 0,19% de
bpb**. Volume de PT não é o gargalo, e comprá-lo a 76× o preço do treino seria a pior compra
possível.

✅ **O escopo defensável é 0,1B a 0,25B de tokens, US$ 40 a US$ 101** — e a justificativa é
**composição**: o Common Corpus é livro, jornal, ciência e administração pública, distribuição
que o fineweb-2 PT (web) não tem. A 5B (US$ 2.014) sairia mais caro que o projeto inteiro até
hoje.

⚠️ **E o valor disso continua NÃO MEDIDO.** O custo agora é conhecido; o retorno não. A régua
para medi-lo **não pode ser bpb do PT** (`2607.00890`: a loss na língua-alvo subestima
sistematicamente o valor da mistura), o que empurra a decisão para um gate de mistura no estilo
do E4, com piso de ruído impresso ao lado (§2h).

#### 🔴🔴 E o achado que vale mais que o custo: o carregador entregava lixo

Ver `bee/gate_trad_b.py:carrega_tradutor()`. O checkpoint do `madlad400-3b-mt` guarda **apenas**
`decoder.embed_tokens` e `lm_head`; o `transformers` fabrica um `shared`, enche com os valores
do **lm_head** e aponta o **encoder** para lá. Normas ao carregar:
`shared 2.560 · encoder 2.560 · lm_head 2.560 · decoder 216.064`.

**Carrega sem erro. Toda tradução vira repetição de uma letra cirílica.** Consertado
(`encoder` e `shared` ← `decoder`): tradução perfeita, 19 tokens no lugar de 81.

⭐⭐ **Verificado nas versões 5.14.1 e 5.16.1 — a guarda disparou igual nas duas.** Não é
regressão pontual de uma versão; é comportamento estável da biblioteca, e a guarda é permanente.

⚠️ **O dano que isso quase causou:** o primeiro probe reportou 355 tok/s e projetou US$ 774 por
1B de tokens, tudo medido sobre saídas degeneradas de 256 tokens — um custo que matava o plano e
que era o defeito. **O que pegou foi a coluna `no teto`** (fração das saídas que bateram em
`max_new_tokens`): 87–92% é impossível para sentenças de 30 tokens. Depois do conserto, 0,0%.
Aquela coluna existe só como guarda §2r — "reportar quanto a intervenção agiu" — e pagou por si
na primeira execução.


### 🔴 [novo 09-01] E uma hipótese alternativa que nunca testamos

[`2604.28075`](https://arxiv.org/abs/2604.28075) (alemão, 500M documentos, **múltiplas escalas de
modelo e de orçamento**): **repetir o núcleo duramente filtrado bate passe único num corpus maior e
menos filtrado**, e **a folga persiste depois de 7 épocas** — SOTA com 10–360× menos tokens.

⚠️ Nós medimos *"+45% de tokens rendeu 0,19%"* — mas adicionando mais do **mesmo corpus
não-refiltrado**. **Filtrar duro os 21,75B e repetir o núcleo é a alternativa que nunca medimos.**

> ### ⭐⭐ [novo 09-01] E este experimento já está montado — inclusive o classificador
>
> `docs/fineweb-edu-pt.md` construiu e **mediu** um classificador de qualidade para o PT:
> **Pearson 0,705** com o professor, **−35%** de erro absoluto médio, **F1 0,723 / acurácia 78,0%**,
> mais a **curva de retenção completa** com o joelho identificado em **~10%** (nota média 1,66 → 3,70;
> a fração ≥3 vai de 38% para 91%).
>
> ⭐ Isso é exatamente o que a triagem achou que **ninguém publica**: dois artigos **usam** um
> classificador educacional sobre o FineWeb2 e **nenhum reporta precisão, recall, quanto do corpus
> cortou, nem o pareado com-e-sem** ([rodada 3, §H4](triagem-arxiv-bee1g-2026-09-01.md)).
>
> 🔴🔴 **[CORRIGIDO 09-01, segunda passada] A primeira versão deste bloco dizia que o classificador
> "nunca foi aplicado ao corpus". ISSO ESTÁ ERRADO, e o erro é meu.**
>
> O `bee/coletar_pt_volume.py` **pontua todo documento e escreve o corpus em TRÊS FAIXAS**, com o
> raciocínio no cabeçalho dele. As faixas estão em disco:
>
> | faixa | corte de score | tokens |
> |---|---:|---:|
> | **A** (top 10%) | ≥ 3,358 | **3,86B** |
> | **B** (10–30%) | ≥ 2,403 | 8,08B |
> | **C** (30–60%) | ≥ 1,399 | 10,03B |
> | | | **21,97B** |
>
> **E o efeito do filtro FOI medido pareado**, e está registrado em `docs/escada-scaling.md` e
> `docs/gate-corpus-pt-plano.md`: **+1,6% de bpb a 131M tokens, com o IC excluindo zero em 4
> pontos — e NÃO cresce com escala.** O desenho em faixas foi escolhido justamente por isso:
> *"volume vence filtro por ~50×; cortar a 10% jogaria fora 90% do corpus por 1,6%"*. **O corte é um
> botão barato — treinar com A, A+B ou A+B+C.**
>
> ✅ **O que CONTINUA não medido, e é o desenho do `2604.28075`:** nós medimos **filtrar em passe
> único**; o artigo alemão mede **filtrar E REPETIR o núcleo**, e mede que isso **bate** — não empata
> — o passe único num corpus maior, com a folga persistindo após 7 épocas. São desenhos diferentes,
> e o segundo nunca rodou aqui.
>
> ⭐ **E como as faixas já existem, o experimento é imediato — mesmo orçamento de tokens vistos:**
>
> | braço | corpus | épocas | tokens vistos |
> |---|---|---:|---:|
> | controle | **A+B+C** | 1,0 | 21,97B |
> | repetição moderada | **A+B** (11,94B) | **1,8** | 21,97B |
> | repetição agressiva | **A** (3,86B) | **5,7** | 21,97B |
>
> ⚠️ **E há tensão medida entre os braços:** [`2305.16264`](https://arxiv.org/abs/2305.16264) mede
> que **até ~4 épocas de dado repetido ≈ dado único**, o que põe o braço agressivo **fora** da faixa
> segura; e o `2606.24998` (§2c #6) mede que o dano de repetição **pica em contagem INTERMEDIÁRIA**.
> O braço A+B a 1,8 época é o que cai na zona defendida pelas duas medições. **Os três vão juntos
> justamente porque a previsão não é monotônica.**
>
> ⚠️ **A ressalva de data continua valendo para o `fineweb-edu-pt.md`:** ele é de **2026-08-04** e o
> bug de rótulos foi achado em **07/08**; a abertura dele diz *"as alternativas caíram uma a uma,
> qualidade do corpus é o que sobrou"* — a quinta hipótese da §5. As **métricas** do classificador
> sobrevivem (Pearson 0,705, CPU contra anotação de professor); o **argumento** de arquivamento,
> não.

### ⭐⭐ [MEDIDO 09-01] O experimento rodou — e a hipótese alemã NÃO transfere

**9 runs** (3 braços × **3 sementes**, §2x), 151M de parâmetros, **100M de tokens vistos por braço**
— mesmo orçamento, mesma receita, mesmo número de passos. RTX 5090, 186 min, **US$ 3,2**.
Artefatos em `bee/gate_faixas/`, código em [`bee/gate_faixas.py`](../bee/gate_faixas.py).

| braço | pool | épocas | **bpb WIKI** (primário) | bpb CRU |
|---|---|---:|---|---|
| **ABC** — controle | 100,0M | 1,00 | **1,3894 ± 0,0089** (ampl. 0,0157) | 1,5095 ± 0,0105 |
| **AB** — moderado | 54,4M | 1,84 | **1,3802 ± 0,0165** (ampl. 0,0314) | 1,5482 ± 0,0134 |
| **A** — agressivo | 17,6M | 5,69 | 🔴 **1,4633 ± 0,0155** (ampl. 0,0274) | 1,6941 ± 0,0081 |

**Welch contra o controle, no holdout primário:**

| | delta | t | df | veredito |
|---|---:|---:|---:|---|
| **AB** | −0,66% | −0,85 | 3,1 | ⚠️ **dentro do ruído de semente** — não é evidência de nada |
| **A** | **+5,31%** | **+7,17** | 3,2 | ⭐ **significativo** — pior |

✅ **Veredito: o corpus continua sendo A+B+C.** A decisão de escrever em faixas (2026-08-06) estava
certa — mas repousava em dois números vindos de documentos marcados **DOCUMENTO INVÁLIDO** um dia
depois (§5, corolário). **Agora ela repousa em medição válida.**

#### 🔴 E o que torna este resultado confiável é que a perda de TREINO apontava ao contrário

| braço | perda de **treino** | bpb no **holdout** |
|---|---:|---:|
| ABC | 4,0891 (a **pior**) | **1,3894** (a **melhor**) |
| AB | 3,9528 | 1,3802 |
| **A** | **3,4000** (a **melhor**) | 🔴 **1,4633** (a **pior**) |

**A ordem inverte por completo.** O braço que viu os mesmos 17,6M de tokens **5,69 vezes** tem a
menor perda de treino porque **decorou** — e a dispersão entre sementes cai junto (dp 0,0069 contra
0,0627 do controle), que é a assinatura da memorização. Ler a perda de treino teria produzido
exatamente a conclusão oposta. ⭐ **É por isso que o holdout é Wikipédia-PT, que nenhum braço vê**
(0,12% de sobreposição com o pool).

#### ⚠️ O que este gate NÃO mostra (§2q)

1. **É um ponto de orçamento e um de escala.** 100M de tokens a 151M de parâmetros. O
   [`2604.28075`](https://arxiv.org/abs/2604.28075) mede em **múltiplas escalas de modelo e de
   orçamento** — o resultado aqui é sobre **o nosso regime**, não sobre a tese deles em geral.
2. **As razões de filtragem são as nossas** (18% e 54%), não as do artigo.
3. **AB nominalmente ganha por 0,66% e isso cabe na amplitude entre sementes.** Não adotar, e não
   registrar como folga — seria a §2x outra vez.

#### ✅ E duas guardas que pagaram por si nesta rodada

- **Cobertura sem reposição (§2):** `cobertura_distinta` = **1,00 nos três braços**. O controle com
  `np.random.randint` daria **0,630** no braço de 1 época — o pool inteiro do controle teria perdido
  37% do dado, e o braço agressivo não (0,997). O defeito **favoreceria a hipótese sob teste**.
- **Throughput medido:** **80.812 tok/s** para 151M na RTX 5090 (contra 62,9k medidos no 345M).
  Entra no Gate T3 como ponto de ancoragem, medido e não extrapolado.

⚠️ Com contrapesos honestos: [Nemotron-CC](https://arxiv.org/abs/2412.02595) mede que FineWeb-Edu e
DCLM **removem 90% do dado**, inviabilizando horizonte longo;
[`2606.07778`](https://arxiv.org/abs/2606.07778) acha que dado **dois escalões abaixo do limiar de
produção** melhora 22,3% em raciocínio e **bate o dado de topo em código** (introduzindo duas
dimensões novas — **atualidade** e **especificidade cultural**); e
[`2605.29807`](https://arxiv.org/abs/2605.29807) é um **nulo com controle aleatório casado**: em
corpus grande e limpo, **filtrar não melhora nada**.

### 🔴 Duas premissas implícitas que caem

1. **"21,75B é o que existe em PT" — falso.**
   [`2605.00086`](https://arxiv.org/abs/2605.00086) declara **331 bilhões de tokens de português
   brasileiro**, o maior corpus monolíngue de PT aberto. **~15× o nosso.** A conferir na origem antes
   de qualquer afirmação sobre escassez.
2. **"licença aberta = pode treinar" — insuficiente.**
   [`2606.28867`](https://arxiv.org/abs/2606.28867) audita 20+ famílias de corpus com evidência de
   fonte primária e documenta um modo que **não tínhamos**: 🔴 **cláusula NoDerivs escondida atrás de
   rótulo CC-BY**, e **NoDerivs proíbe silenciosamente tokenizar e anotar**. Mais: proibição pura
   (JW300, **removido do OPUS após auditoria legal**), **falsa representação de licença composta**, e
   **falha de persistência** (402 de 405 URLs mortas).
   ⚠️ E a lacuna: **licença do fineweb-2 / ODC-By discutida em artigo — zero.** A base que usamos
   **não foi auditada por ninguém**.

⚠️ **E o nosso censo de 0,28% de repetição é excepcional, não o padrão.**
[`2605.18232`](https://arxiv.org/abs/2605.18232) auditou o release *"cleaned"* do **HPLT v2** em
somali: **17,3% de duplicatas byte-exatas, 56,1% com mojibake, 10,7% dos byte-únicos são near-dups**.
Ao acrescentar 7 idiomas, não dá para herdar a tranquilidade. Ferramenta pronta:
[PUFFER](https://arxiv.org/abs/2608.28622) — MinHash-LSH incremental, 1 bilhão de documentos em
~1,75 h a **128 bytes/documento**, e **com retirada por escopo de dataset**, que é o que uma licença
revogada exige.

⚠️ E um vazamento a considerar antes de publicar: [`2608.10690`](https://arxiv.org/abs/2608.10690)
mostra que dá para **estimar a mistura de um corpus a partir do vocabulário do tokenizador liberado**
(erro relativo médio 3,00%). **Publicar o tokenizador publica a composição do corpus.**

### 🔴🔴 [09-04] O censo da coleta: três idiomas prontos que o driver chamava de falha

A pasta `bee/corpus_multi_1g` tinha **221 shards e nenhuma contabilidade válida deles**. Os seis
`MANIFEST_<idioma>.json` foram todos escritos **às 09:03 — antes de existir um único shard dos
idiomas que nomeiam** — e todos carregam o mesmo registro de `fra`, de uma corrida anterior.
E `fra` tem **zero** shards em disco hoje. O `MANIFEST.json` (12:41) descreve só `jpn`, o último
idioma, ignorando 218 dos 221 shards.

A causa está no `coletar_1g.sh`: o `cp MANIFEST.json MANIFEST_<c>.json` ficava no ramo de
**sucesso**, então idioma que não chegava a 90% do alvo nunca atualizava o próprio arquivo — e o
que sobrava ali era o de outra corrida. **§2z: arquivo cujo NOME afirma o que o CONTEÚDO não é.**

#### O segundo defeito é pior, porque dirigia uma ação destrutiva

A correção anterior — *"verificar o que ficou em disco, não confiar no código de saída"* — estava
certa na intenção e errada na execução: verificava com um **estimador**. O `mcar_em_disco()`
derivava o número de caracteres do tamanho **comprimido**, multiplicando por uma razão cravada à
mão por idioma. Contado agora, shard a shard:

| idioma | Mcar **contado** | Mcar **estimado** | erro | o driver diria |
|---|---:|---:|---:|---|
| arb | 7.801 | 2.193 | **−72%** | 🔴 parcial → `rm -f` 52 shards |
| cmn | 3.405 | 1.379 | **−60%** | 🔴 parcial → `rm -f` 46 shards |
| eng | 10.017 | 3.225 | **−68%** | 🔴 parcial → `rm -f` 66 shards |
| spa | 8.805 | 2.760 | **−69%** | 🔴 parcial → `rm -f` 54 shards |

⭐ **Sub-estimava entre 60% e 72% em todos, e sempre para o mesmo lado.** Como `arb`, `cmn` e `eng`
estão a **100,0% do alvo**, rodar o driver de novo teria **apagado os 221 shards** — inclusive os
três idiomas prontos — para "refazer do zero". As constantes descrevem caracteres por GB
*descomprimido*; o código as aplica a bytes *comprimidos*.

✅ **Correções:** quem decide passou a ser `bee/censo_coleta_1g.py`, que **conta** (0,8 min para os
221 shards); e `rm -f` deixou de acontecer sozinho — exige `--refazer <idiomas>` explícito, porque
o coletor renumera de `0000` e não sabe retomar. Testado contra o estado quebrado (§2t): sem a
flag, `spa` e `jpn` sobrevivem e `arb`/`cmn`/`eng` são reconhecidos como prontos; com
`--refazer jpn`, só `jpn` é alvo.

#### O que existe, contado

| idioma | shards | documentos | Mcaracteres | % do alvo | **Btokens 64k** |
|---|---:|---:|---:|---:|---:|
| arb | 52 | 2.599.401 | 7.801 | **100,0%** | 2,500 |
| cmn | 46 | 2.297.588 | 3.405 | **100,0%** | 2,500 |
| eng | 66 | 3.274.198 | 10.017 | **100,0%** | 2,500 |
| spa | 54 | 2.681.000 | 8.805 | 83,5% | 2,088 |
| jpn | 3 | 108.087 | 163 | 3,4% | 0,086 |
| **deu** | 0 | 0 | 0 | **0%** | — |
| **fra** | 0 | 0 | 0 | **0%** | — |
| **total** | **221** | **10.960.274** | **30.191** | **54,3%** | **9,674** |

Com o português re-tokenizado: **23,868B de PT** (medido, `corpus_pt_64k/MANIFEST.json`) contra
**9,674B de não-PT**.

⚠️ A conversão caractere→token usa a fertilidade **medida por idioma** do braço `64k-multi`
(`gate-t1-vocab.json`), porque caractere não é comparável entre escritas (§2g): 1 caractere han
custa 0,734 token e 1 caractere espanhol custa 0,237.

#### ⭐⭐ E a consequência que acopla duas decisões que pareciam independentes

Épocas do pool não-PT exigidas por cada combinação de mistura e orçamento:

| mistura | %PT | 20B | 66B | 143B |
|---|---:|---:|---:|---:|
| **hoje — não-PT 9,67B** | | | | |
| bal-12 | 12,5% | 1,8× | 6,0× | 12,9× |
| pt-25 | 25% | 1,6× | 5,1× | 11,1× |
| **pt-50** | 50% | **1,0×** | 3,4× | 7,4× |
| **coleta completa — não-PT 17,50B** | | | | |
| bal-12 | 12,5% | 1,0× | 3,3× | 7,2× |
| pt-25 | 25% | 0,9× | 2,8× | 6,1× |
| pt-50 | 50% | 0,6× | 1,9× | 4,1× |

⭐ **No orçamento Chinchilla (20B) com `pt-50`, o dado que já existe basta — exatamente 1,0 época.**
Nenhuma coleta a mais é necessária para esse desenho.

🔴 **Em todo o resto, a repetição cai na faixa de 3–10×, que é o pico do dano medido** por
[`2606.24998`](https://arxiv.org/abs/2606.24998) (§2c #6): com 10% dos FLOPs em documentos
repetidos, o resultado equivale a treinar sem repetição usando só 67% dos FLOPs. O dano **não é
monotônico** — ele tem pico em contagem intermediária, que é justamente onde estas células caem.

⚠️ **Isto é uma afirmação sobre SUPRIMENTO, não sobre qualidade.** Qual mistura treina melhor é o
que o braço de transferência mede; esta tabela diz apenas qual é **viável** com o dado que há. As
duas coisas se combinam: um orçamento grande com pouca variedade de dado não é o mesmo
experimento que o mesmo orçamento com o corpus completo.

⚠️ E a tabela supõe o pool não-PT usado por inteiro e uniformemente. Ele **não** é uniforme:
`arb`/`cmn`/`eng` têm 2,5B cada, `spa` 2,088B, `jpn` 0,086B, e `deu`/`fra` zero. Uma mistura que
queira os sete idiomas em proporções parecidas é limitada pelo mais escasso, e hoje isso é `jpn`
com 3,4% do alvo.



---

## 6. O que fazer na segunda-feira

> ### 🔴🔴 [09-04] Antes de qualquer item abaixo: a revisão e o gate de sucesso
> A [revisão de 2026-09-04](revisao-bee-1g-2026-09-04.md) releu as sete decisões da cadeia contra
> o que o plano declarou: **uma foi rebaixada** (o T2 usou a régua que este plano mandou não usar,
> e é estágio único) e **cinco ganharam ressalvas**. O [gate de sucesso (T4)](gate-sucesso-bee-1g.md)
> está declarado — e lista **oito pré-requisitos** sem os quais o run não pode começar, entre eles
> re-tokenizar os 21,97B PT (trancados no 32k) e coletar os 7 idiomas a ~1,5B tokens cada.

1. **A terceira semente do resumo** (Fase 2) — pendente, e sem ela há uma afirmação em aberto;
2. **Gate T1** — varredura de vocab sobre os 8 idiomas, agora com **os três eixos** (custo ·
   qualidade · **incompletude por escrita**), o braço de **embedding fatorado**, o de
   **Parity-Aware BPE** e o de **romanização**. Minutos, US$ 0, maior alavanca;
3. ❓ **Responder a decisão de orçamento da §1** — preservar o PT ou adicionar idiomas, agora
   reformulada em **bytes, estágios e schedule**.

### ⭐ [novo 09-01] E quatro experimentos de custo quase zero que a rodada 3 destravou

| experimento | o que decide | custo |
|---|---|---|
| **compressibilidade gzip** do corpus 8-idiomas × só-PT | para que lado a fronteira compute-ótima se move — mais dado ou mais parâmetro ([`2405.16684`](https://arxiv.org/abs/2405.16684)) | CPU, minutos |
| **filtrar duro os 21,75B e repetir o núcleo** | a hipótese que nunca testamos — medimos "mais volume não paga" sem medir "núcleo filtrado repetido" ([`2604.28075`](https://arxiv.org/abs/2604.28075)) | 1 mini-run |
| **varredura de fatia 5%→95%** por idioma | separa **teto de tokenizador** de **escassez de dado** — 1,7% contra 33,9% de movimento ([`2608.26449`](https://arxiv.org/abs/2608.26449)) | CPU |
| **ler a razão d_model/camadas nos Gemstones** | testa a nossa geometria contra 4.000+ checkpoints publicados, **sem treinar** ([`2502.06857`](https://arxiv.org/abs/2502.06857)) | leitura |

**Nada de coleta antes do T1 e do T2.** Coletar é o passo caro e irreversível; a literatura e a
nossa própria medição dizem que a alavanca está em filtro e representação, não em volume.

### ⚠️ [novo 09-01] E a lacuna que mais deveria incomodar

Testado explicitamente contra os corpora lidos: **não existe desenho causal ligando fertilidade a
qualidade de TRADUÇÃO.** Todo mundo mede fertilidade e *assume* que ela transfere;
[`2607.24276`](https://arxiv.org/abs/2607.24276) diz que a correlação aparente se explica por
**disponibilidade de recurso do idioma**.

🔴 **O eixo declarado do Bee-1G é tradução, e é exatamente o que a literatura mede por proxy.** Isso
não bloqueia nada — mas significa que o critério de tradução do Gate T4 (piso de copiar a fonte, em
todos os pares) **é a única coisa que separa este projeto de repetir a suposição de todo mundo**.

---

## 7. Regras herdadas, que valem sem discussão

Do `~/.claude/rules/bee-pretreino-licoes.md` (§1 a §2ab) e das 10 h desta sessão:

- **piso trivial em toda métrica** — pegou que o e13 traduzia pior que copiar a fonte, e derrubou
  o "resumo passa do piso";
- **guarda de rótulos que aborta antes do passo 1**, com dado real;
- **duas sementes alertam, três decidem** — 4 afirmações minhas caíram por isso nesta sessão;
- **medir os dois lados** de toda intervenção que bloqueia;
- **config se lê no artefato**, nunca no card;
- **contar itens distintos**, não linhas;
- **decompor por classe/verificador** antes de atribuir um agregado a uma capacidade;
- ⭐ e a que vale mais: **quando dois experimentos internos se contradizem por margem absurda, o
  defeito está no aparato, não no fenômeno.**
