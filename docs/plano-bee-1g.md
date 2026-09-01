# Plano do Bee-1G — multilíngue e multimodal

> **Estado:** documento de decisão, não de execução. Nenhum gasto aprovado.
> **Base:** tudo que os Bee-150M e Bee-350M mediram, mais a triagem de ~4.000 resumos do arXiv
> (2026-08-31, 6 agentes) e duas buscas dirigidas.
>
> **Última atualização:** 2026-08-31.

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

> ### ❓ DECISÃO PENDENTE — e é do dono, não do método
> **Quanto do orçamento vai para *não piorar o português* versus *adicionar idiomas*?**
> Tudo abaixo depende disso. Projeto inteiro até hoje: **~US$ 272**.

⚠️ Os US$ acima são **extrapolação** da medição do 350M (345M × 21,75B em 115,48 h de RTX 5090).
O projeto tem regra contra extrapolar custo — o `docs/throughput-350m-medido.md` cortou uma
estimativa pela metade por US$ 0,15. **O Gate T3 vem antes de qualquer compromisso.**

---

## 2. ⭐⭐ A decisão de maior alavanca custa minutos de CPU

[**One Tokenizer To Rule Them All**](https://arxiv.org/html/2506.10766v1) — 3,3B params, vocab
100k/175k/250k: tokenizador universal **desde o início** custa **<1% na língua primária** e rende
**+18,9%** ao expandir idiomas, com **+2× de plasticidade e +8× de velocidade de adaptação**.

⭐ **Logo: construir o tokenizador multilíngue agora, mesmo que o primeiro run seja quase todo
PT.** É a decisão que se paga sozinha e que fica cara de reverter.

E [`2608.03999`](https://arxiv.org/abs/2608.03999) mediu, fixando backbone, dado, orçamento e
decodificação: escalar o backbone **34× quase não move** a métrica, enquanto **trocar a
representação a corta pela metade** — replicado num backbone de 26M do zero.

### ⚠️ Três ressalvas que a literatura não resolve na nossa escala

1. **Vocab consome orçamento de parâmetro.** 250k × d_model 2048 = **512M**, metade de um modelo
   de 1B. O artigo mede em 3,3B, onde isso é 15%. O meio defensável aqui é **~128k**.
   [`2608.11361`](https://arxiv.org/abs/2608.11361) mediu que a qualidade em bpb varia **<2%**
   em toda a faixa de vocab — o que decide não é qualidade, é orçamento e serving.
2. **A maldição da multilingualidade é real e documentada**
   ([2311.09205](https://arxiv.org/pdf/2311.09205)): tokenizador monolíngue **supera
   consistentemente** o compartilhado em fertilidade. Nosso **0,218 tok/byte em PT** é o ativo do
   projeto desde o Gate 1, e ele **vai piorar**. Quanto, mede-se em minutos.
3. 🔴 **Escritas diferentes podem quebrar subword.**
   [`2605.02270`](https://arxiv.org/abs/2605.02270) mediu **mT5 subword falhando completamente**
   (chrF++ < 18,5) contra ByT5 byte-level em **87,4**, em cirílico↔árabe. Latim + árabe + han +
   kana num vocab só **não é seguro por suposição**.
   ⚠️ E [`2608.26449`](https://arxiv.org/abs/2608.26449): o regex `\p{L}+` do pré-tokenizador
   **ByteLevel do HuggingFace** — que o `bee/train_tokenizer.py` usa — parte a palavra em toda
   marca de vogal em **17 de 17 abugidas**. O árabe está na nossa lista.

**Caminho intermediário medido:** [`2607.15232`](https://arxiv.org/abs/2607.15232) — **expansão
*in-place***, continuando os merges BPE do nosso 32k, de modo que os tokens antigos sobrevivem e
todo token novo tem decomposição exata nos antigos.

---

## 3. Os gates, com critério declarado ANTES

### Estágio T — texto multilíngue

#### Gate T1 — tokenizador · **CPU, minutos, US$ 0**

Varredura sobre a mistura dos 8 idiomas, reusando `bee/train_tokenizer.py --varrer-vocab`:

| braço | o que testa |
|---|---|
| 32k atual | o baseline — quanto o PT tem a perder |
| 32k **expandido in-place** | preserva a especialização (`2607.15232`) |
| 64k · 128k do zero | o meio defensável |
| **byte-level para árabe/han/kana** | o alerta do `2605.02270` |

**Critério, declarado antes:** a fertilidade em PT **não pode piorar mais que 15%** (0,218 →
0,251 tok/byte). Se piorar mais, ou se algum idioma ficar acima de 3,0 tok/palavra
([o imposto medido em 25 línguas europeias](https://arxiv.org/abs/2605.24718) põe as românicas
em 1,5–1,7 e o teto europeu em ~3,1), o braço é **reprovado**.

⚠️ **Reportar fertilidade POR IDIOMA, nunca a média.** Média entre 8 idiomas é agregado de
componentes heterogêneos — a §2y aplicada ao tokenizador.

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

#### Gate T3 — throughput · **US$ 0,15**

`--passos 40` na configuração real, três leituras coincidentes a partir do passo 20 (§3).
**Nenhum compromisso de orçamento antes deste número.**

#### Gate T4 — sucesso do run, declarado antes de gastar

| métrica | critério |
|---|---|
| **bpb por idioma** | acima do modelo público mais próximo em cada um |
| **tradução** | acima do piso de **copiar a fonte** (21,5 en→pt · 22,7 pt→en) em **todos** os pares |
| **as 9 capacidades** | com piso trivial ao lado de cada uma (`baseline_8_capacidades.py`) |
| **português** | ⚠️ **não pode ficar abaixo do Bee-350M** — 0,8207 bpb |

⚠️ Schedule: [WSqD](https://arxiv.org/abs/2607.10959) conserta exatamente o defeito do WSD que
nos custou US$ 22 — o LR de pico fica amarrado ao horizonte original (§2d). Se ficar WSD, `--lr`
**explícito** e marcos comparados **só dentro do mesmo regime**.

### Estágio V — visão · Estágio A — áudio

#### 🔴 A decisão de identidade, declarada antes

| | o que significa | viabilidade |
|---|---|---|
| **(a) encoders pré-treinados** | Bee de texto do zero + SigLIP (Apache-2.0) e encoder de fala (MIT) **congelados** + projetor treinado por nós | ✅ é o que a literatura faz nesta escala |
| **(b) encoders do zero** | treinar classe CLIP: bilhões de pares imagem-texto | 🔴 **US$ 10k+**, fora de qualquer orçamento aqui |

⚠️ **Em (a), "do zero" passa a cobrir o backbone de texto, o tokenizador, o projetor e a fusão —
não os olhos e os ouvidos.** Isso é afirmação pública sobre o que o Bee-1G é, e o projeto já teve
essa crise uma vez (2026-07-26, quando o que existia era Qwen4B + adapters).

**Recomendação: (a).** Prova na nossa faixa:
[SigLIP-2 + Qwen3-0.6B ≈ 1B rende F1 0,753](https://arxiv.org/abs/2608.18591).

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

🔴 **E um atalho que está morto:**
[fundir modelos monolíngues causa colapso por interferência](https://arxiv.org/abs/2605.25846) —
similaridade representacional é pré-requisito e **não sobrevive ao pré-treino separado**.

---

## 6. O que fazer na segunda-feira

1. **A terceira semente do resumo** (Fase 2) — pendente, e sem ela há uma afirmação em aberto;
2. **Gate T1** — varredura de vocab sobre os 8 idiomas. Minutos, US$ 0, maior alavanca;
3. ❓ **Responder a decisão de orçamento da §1** — preservar o PT ou adicionar idiomas.

**Nada de coleta antes do T1 e do T2.** Coletar é o passo caro e irreversível; a literatura e a
nossa própria medição dizem que a alavanca está em filtro e representação, não em volume.

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
