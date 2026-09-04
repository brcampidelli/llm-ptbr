# Revisão do Bee-1G — tudo até aqui, antes de escrever o gate de sucesso (2026-09-04)

> **Por que esta revisão existe.** A §5 das lições diz: *consertar o aparato obriga a reexaminar os
> ARGUMENTOS e os ARTEFATOS, não só as medições*. Em três dias foram achados **oito defeitos de
> instrumento**, dois dos quais teriam produzido conclusões invertidas publicáveis. Antes de
> comprometer US$ 400–2.850 num run longo, cada decisão da cadeia foi relida contra **o que o plano
> declarou antes** e contra **o que foi medido depois** — e o resultado não é "tudo certo".

---

## 1. A cadeia de decisões, uma a uma

| gate | decisão | veredito da revisão |
|---|---|---|
| **T1 eixos 1+3** | vocabulário é composição, não tamanho | ✅ sobrevive. `64k-multi`: PT **+9,1%** (teto declarado 15%), incompletude árabe **0,13%** |
| **T1 eixo 2** | `128k` morto; multilíngue > 32k-PT **até em PT** (12,6%) | ✅ sobrevive, **com ressalva** (§2.1) |
| **T1 tok/param** | `64k` sobre `96k` | ✅ sobrevive: `t = −0,61`, folga converge, custo decide |
| **T-TRAD A** | duplicação cross-lingual 0,05% | ✅ sobrevive |
| **T-TRAD B** | pipeline por sentença; US$ 403/B | ✅ sobrevive; ⚠️ o "76×" ficou obsoleto (§2.8) |
| **T2** | `pt-50`, troca 3,5× | 🔴 **rebaixado**: régua errada por declaração própria, e estágio único (§2.2, §2.3) |
| **throughput** | US$ 399–2.851; `seq 2048` | ✅ sobrevive; resolve uma contradição interna (§2.5) |

---

## 2. Os treze achados da revisão

### 2.1 ⚠️ O "32k-PT perde em português" foi medido numa mistura, e depende dela

O T1 eixo 2 mediu que o `32k-multi` bate o `32k-atual` (especializado em PT) em **português**, por
12,6%. O mecanismo é o byte-fallback: com 12,5% de PT e 87,5% de CJK/árabe/etc., o vocabulário PT
explode os outros idiomas em bytes, e a passos fixos o controle vê **menos bytes de texto**.

⚠️ **Isso é verdade para a mistura `bal-12`.** Numa mistura PT-pesada o byte-fallback quase não
ocorre, e a folga encolheria. **Não invalida a escolha do `64k`** — o `64k` vence por cobertura
dos 8 idiomas, não por esse efeito — mas a frase *"o tokenizador PT perde em PT"* não pode ser
citada fora da mistura em que foi medida.

### 2.2 🔴🔴 O T2 usou a régua que o plano mandou NÃO usar — e o viés vai na direção da conclusão

O Gate T2, **como declarado antes de rodar** (plano, §3):

> *"a loss de validação do alvo SUBESTIMA sistematicamente o ganho. Medir por bpb do PT daria a
> resposta errada. **Medir tradução contra o piso de copiar a fonte.**"*
> — citando [`2605.13225` Mix, Don't Tune](https://arxiv.org/abs/2605.13225), 150M–1,43B, ~1.000 runs.

**Eu medi bpb do PT.** O viés citado age assim: o braço com **mais mistura** (`bal-12`) tem ganhos
de capacidade que o bpb não enxerga, então o bpb **subestima o valor do `bal-12`** — e portanto
**superestima a vantagem do `pt-50`**. A "troca de 3,5×" está medida numa régua que favorece
sistematicamente o lado que venceu.

⭐ **E há um agravante que a revisão tem de admitir:** o critério declarado (chrF2 com piso de
copiar a fonte) era **inmensurável no proxy**. A 150M e 220M tokens não existe capacidade de
tradução para medir — o Bee-150M fez **0%** de idioma-alvo em pt→en. O plano declarou um critério
que o proxy não tinha como cumprir, e o gate foi rodado com o substituto que o próprio plano
reprovava.

**Consequência:** o T2 vale como **forma da curva de troca em bpb** — o único termo que está
firme é que a troca não degrada de 25% para 50%. **Não vale como decisão de mistura.** A decisão
precisa de (a) o braço de transferência que o plano pedia e nunca foi feito (§2.11), ou (b) marcos
de tradução no run real.

### 2.3 🔴 O T2 é estágio único; o plano diz que estágio único nunca é ótimo

O plano, §1, corrigido em 09-01 com [`2410.12325` M³](https://arxiv.org/abs/2410.12325):

> *"multilíngue-1-estágio NUNCA é ótimo na grade. O desenho indicado é dois estágios com razão de
> PT alta no final"* — o que o [Index-1.9B](https://arxiv.org/abs/2607.09885) faz na prática.

O T2 mediu **três misturas de estágio único**. Ele informa o **segundo** estágio (a razão de PT no
decaimento), não o desenho do run. O desenho do Bee-1G tem de ser decidido em cima da evidência
de dois estágios, e essa decisão **não está tomada**.

### 2.4 🔴🔴 A mistura decidida não é executável com o corpus que existe

Conta feita hoje, para o `pt-50` com 7 idiomas a 7,14% cada:

| cenário | PT necessário | há 21,97B? | cada outro idioma | disponível | **falta** |
|---|---:|---|---:|---:|---:|
| Chinchilla 21B | 10,5B | ✅ | **1,50B** | 28M (+84M regenerável) | **13× a 53×** |
| como o 350M 66B | **33,0B** | 🔴 **não** | 4,71B | idem | 42× a 168× |

⭐ O `corpus_multi` tem **100 Mcar por idioma** — foi coletado para o Gate T1, não para treinar. O
plano dizia *"nada de coleta antes do T1 e do T2"*; os dois fecharam, **e a coleta grande é agora
o passo**. Medido hoje: 300 Mcar por idioma em ~0,4 min de banda → 1,5B tokens/idioma ≈ 6 Gcar ≈
**~80 min por idioma, ~10 h no total**. Viável, e é pré-requisito, não opção.

### 2.5 🔴 O corpus PT de 21,97B está trancado no tokenizador de 32k

`bee/coletar_pt_volume.py`, linha 34: *"Os parquets são apagados após o uso."* O texto cru foi
descartado; o que existe são **39 shards `.bin` em uint16 no tokenizador de 32k** (47 GB, faixas
A/B/C). O Bee-1G usa o `64k-multi`.

✅ **Há saída limpa e exata:** o 32k é BPE ByteLevel com `byte_fallback: False`, decoder ByteLevel
e normalizador NFC — `decode(encode(x)) == NFC(x)`, byte a byte, e o corpus já foi gravado NFC.
Então **decodificar → re-tokenizar em 64k** é lossless. Custo: ~22B tokens; a preparação do T2
fez ~0,5M tok/s por processo → **~12 h single-thread, paralelizável**. Pré-requisito do run.

### 2.6 🔴 `seq_len`: a config diz 4096, o plano diz 2048, a medição diz 2048

Três fontes, uma contradição:
- `bee/config.py` `ESCADA["1b"]`: **`seq_len=4096`**
- plano §3 T0.f, com [SkyLadder](https://arxiv.org/abs/2503.15450): *"**Decisão de gate: manter
  2048**"*
- gate de throughput: 2048 é **7% mais rápido** e usa menos memória; a 4096 o micro-batch trava em 2

✅ **Corrigir a `ESCADA["1b"]` para 2048.** A config estava desatualizada em relação à decisão que
o plano já tinha registrado.

### 2.7 🔴 O LR do 1B não existe em lugar nenhum

`config.py` não tem regra de LR. O gate de throughput usou `1e-3` **por arbítrio**. A Step Law que
o projeto usa (`η* = 1,79·N^−0,713·D^0,307`) dá:

| orçamento | η* |
|---|---:|
| 20B | **9,6e-4** |
| 66B | **1,4e-3** |
| 150B | 1,8e-3 |

⚠️ E o plano §2 ressalva 5 ([`2506.15025`](https://arxiv.org/abs/2506.15025)): no regime de vocab
grande a razão LR-embedding / LR-oculto escala **Θ(√width)** — o LR único que os gates usaram
deixa de ser adequado. **Este projeto já perdeu 7 de 15 braços por grade de LR mal centrada
(§2f).** Pré-requisito: mini-sweep que **cerque** o ótimo (3 pontos, 1 semente, ~2.000 passos),
custo ~US$ 3.

### 2.8 ⚠️ O "traduzir custa 76× o treino" ficou obsoleto no mesmo dia

O 76× foi calculado contra o 350M (US$ 5,30/B). O 1G **medido** custa **US$ 19,00/B** — a razão
cai para **21×**. A conclusão qualitativa (tradução é composição, não volume; escopo 0,1–0,25B)
sobrevive; o número na seção do plano tem de ser corrigido.

### 2.9 ⚠️ O holdout do 0,8207 não é reproduzível localmente

O T4 diz *"português não pode ficar abaixo do Bee-350M — 0,8207"*. Esse número saiu do
`eval_gate2.py` sobre os **shards {7,23,41} de `bee/corpus`** — e `bee/corpus` **não existe
nesta máquina**. Comparar o 1G ao 0,8207 seria comparar réguas diferentes (§2g).

✅ **Conserto barato:** o 350M está no Hub (`BrCamp/bee-350m-pt-base`) e cabe na 5070. Medi-lo
nos holdouts de **texto** que existem — `bee/gate/holdout_wiki.json` (300 docs, 1,03 MB,
Wikipédia-PT, *"que nenhum braço vê"*) e o PT do `corpus_multi` (1,5 MB) — produz uma âncora nova
**na mesma régua** do 1G. Minutos.

### 2.10 ⚠️ `corpus_multi_extra` morreu com o pod

Os 300 Mcar × 7 idiomas foram coletados no pod e **nunca baixados** (o PT extra foi). O pod foi
encerrado; o corpus se foi. É regenerável em ~3 min, **mas não byte-idêntico** — e o `MANIFEST`
dele não foi versionado. Os pools do T2 foram construídos sobre ele; os artefatos do T2 estão
salvos, mas **a reprodução exata dos pools do T2 não é mais possível**.

### 2.11 ⚠️ O braço de transferência do T2 nunca foi feito

O plano pedia: *"o mesmo par de misturas medido em duas escalas (150M e 350M). Se a ordem se
mantiver, o proxy transfere; se inverter, o grid inteiro é sobre um fenômeno que não é o do
alvo."* Custo: ~US$ 6. **Não foi rodado**, e é a única coisa que separa o T2 de uma extrapolação.

### 2.12 ⚠️ Três dos quatro experimentos de custo zero do §6 continuam por fazer

| experimento | estado |
|---|---|
| filtrar duro e repetir o núcleo | ✅ **feito** — gate de faixas: repetir a faixa A perde (+5,31%, t=7,17); corpus = A+B+C |
| compressibilidade gzip 8-idiomas × só-PT | ❌ |
| varredura de fatia 5%→95% por idioma | ❌ |
| razão d_model/camadas nos Gemstones | ❌ |

### 2.13 ❓ A decisão do dono continua aberta

§1 e §6.3: *"quanto do orçamento vai para não piorar o português versus adicionar idiomas"*. O T2
dá a **forma** da troca; **o ponto é escolha, não medição.** E ela agora tem uma dimensão a mais:
em quantos **estágios** (§2.3).

---

## 3. O que ficou mais forte

- **Oito defeitos de instrumento** achados e consertados em três dias, todos da família "nada dá
  erro": pool de treino montado a partir do holdout; encoder do Madlad lendo a matriz de saída;
  mistura efetiva ≠ rótulo; `perda_final` de um lote só; `--apagar` numa cópia sem checkpoints;
  artefato gravado só no fim (três vezes); guarda de polaridade que só pegava metade; monitor que
  confundia artefatos de dois gates.
- **Toda guarda nova foi testada contra o estado quebrado** antes de ser usada (§2t) — e uma delas
  (a de polaridade) falhou no teste e foi corrigida antes de rodar.
- **Três sementes em tudo**, e a leitura pareada com a semente como unidade — que é o que derrubou
  a leitura de duas sementes, duas vezes.
- O corpus PT em faixas, cuja justificativa vinha de documentos inválidos, **agora repousa em
  medição válida** (A+B+C).
- O gate de throughput pegou o que nenhuma extrapolação pegaria: **a configuração não cabe** sem
  recomputação de ativações.

---

## 4. O que tem de acontecer ANTES do run — em ordem, com custo

| # | pré-requisito | custo | bloqueia |
|---|---|---|---|
| 1 | **corrigir `ESCADA["1b"].seq_len` → 2048** | minutos | tudo |
| 2 | **âncora do 350M** nos holdouts de texto (`holdout_wiki`, PT do `corpus_multi`) | 5070, minutos | T4 |
| 3 | **re-tokenizar os 21,97B PT** em `64k-multi` (decode 32k → encode 64k) | CPU, ~12 h paralelizável | run |
| 4 | **coletar 7 idiomas a ~1,5B tokens** cada, licença verificada por idioma | banda, ~10 h | run |
| 5 | **mini-sweep de LR** que cerca 1e-3, 3 pontos × 1 semente × 2.000 passos no 1B | ~US$ 3 | run |
| 6 | **braço de transferência do T2** (`bal-12` e `pt-50` a 350M) — ou aceitar o risco por escrito | ~US$ 6 | decisão de mistura |
| 7 | ❓ **decisão do dono**: ponto da troca PT×idiomas, e 1 ou 2 estágios | — | desenho do run |
| 8 | corrigir o "76×" → 21× no plano; versionar o MANIFEST do `corpus_multi_extra` regenerado | minutos | — |

⚠️ **Nenhum destes é opcional para o run.** Os itens 3 e 4 são os longos e podem rodar em paralelo,
num pod de CPU barato ou nesta máquina — não precisam de GPU.

---

## 5. A regra que esta revisão confirma

Das sete decisões da cadeia, **uma foi rebaixada (T2)** e **cinco ganharam ressalvas**. Nenhuma
das ressalvas apareceu como erro em lugar nenhum: o T2 rodou, convergiu, deu `t = −17,62`, e o
número está certo — **para a pergunta que a régua responde, que não era a pergunta declarada**.

É a §2g outra vez: *mesmos itens? mesma régua? mesmo n?* — com uma quarta pergunta que esta
revisão acrescenta: **a régua que rodou é a que o plano declarou?** Se não, o resultado é sobre
outra coisa, por mais limpo que seja.
