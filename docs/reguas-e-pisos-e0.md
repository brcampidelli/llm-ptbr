# Estágio 0 — as réguas das 8 capacidades, e o piso de cada uma

> **2026-08-19.** Instrumentação do pós-treino do Bee-350M. Este documento registra **como**
> cada capacidade é medida, **contra o que** o número deve ser lido, e **o que a régua não
> mede**. Os números do modelo entram em `docs/baseline-pre-postreino-350m.json` quando a GPU
> liberar; aqui estão os pisos, que já foram medidos e não dependem do modelo.

---

## 1. A ideia que organiza tudo: número sem piso não se lê

"O Bee faz 55% em sentimento" é uma frase sem conteúdo. Com o piso ao lado ela se resolve
sozinha: **contar a palavra "não" faz 73,2%**, então 55% significa que o modelo é pior que um
`grep`. Essa é a diferença entre medir e produzir número.

O projeto já pagou por isso duas vezes, dos dois lados:

- o `verifier.py` tinha ganho aparente e **saldo −4** porque só o lado bom era medido;
- o avaliador agêntico mediu **23,5%** quando o real era **57,6%**, porque 35 das 85
  referências eram impossíveis por construção e ninguém tinha executado os gabaritos.

Daí as três regras que valem para toda régua nova deste estágio:

1. **os gabaritos executam antes de qualquer modelo ser carregado** — e o `--dry-run` de cada
   script faz exatamente isso;
2. **todo número vem com o piso trivial medido no mesmo run**, com a mesma régua;
3. **o que a régua não mede vai escrito no cabeçalho dela**, para não virar leitura errada
   depois.

---

## 2. As oito réguas

| capacidade | script | régua | piso medido |
|---|---|---|---|
| instrução / conteúdo | `eval_ifeval_pt.py` | 541 prompts, 1.002 instruções verificadas por execução | referência 100% (sem piso trivial) |
| resumo | `eval_resumo_pt.py` | invenção + omissão + compressão, 150 itens | **LEAD-2 = 51,3%** |
| tradução | `eval_traducao_pt.py` | chrF++/BLEU no FLORES-200, 600 itens | **copiar a fonte = chrF++ 21,5 · BLEU 2,5** |
| sentimento | `eval_sentimento_pt.py` | 600 reviews B2W, binário e balanceado | **léxico = 79,0%** (só "não": 73,2%) |
| código (interno) | `eval_coder.py` | 877 tarefas, juiz é o interpretador | teto verificado **877/877** |
| código (externo) | `eval_coder.py --tasks humaneval_xl_pt` | HumanEval-XL split PT, 80 itens | teto verificado **80/80** |
| atendimento | `eval_atendimento_pt.py` | intenção + dados + política + invenção, 250 itens | **regra = UTIL 60,4%** |
| agêntico | `eval_agentic_exec.py` | execução real da chamada, 85 itens | referências 85/85 executam |
| *matemática (gate)* | `eval_aritmetica_passk.py` | `pass@256` em 200 problemas | teto verificado 200/200 |

Consolidador: `comeia/eval/baseline_8_capacidades.py`. Com `--dry-run` valida as oito réguas
sem tocar na GPU (as oito passam, 2026-08-19).

---

## 3. Baselines externos — o que o piso trivial não responde

Piso trivial diz se **há** capacidade. Não diz se ela **serve**. Rodados em CPU, para não
disputar a GPU com o gate de matemática:

### Tradução — e a validação que ela deu de brinde

| | en→pt | pt→en |
|---|---|---|
| copiar a fonte (piso) | chrF++ 21,5 · BLEU 2,5 | chrF++ 22,7 · BLEU 2,5 |
| **`opus-mt-tc-big-en-pt` / `opus-mt-ROMANCE-en`** | **chrF++ 70,4 · BLEU 50,5** | chrF++ 68,0 · BLEU 45,1 |

⭐ **O número publicado do `opus-mt-tc-big-en-pt` no FLORES en→pt é BLEU 50,4. A nossa régua
mediu 50,5.** Isso não é detalhe: significa que o aparato de tradução — extração do FLORES,
prompt, decodificação, tokenização do sacreBLEU — reproduz a literatura na primeira casa
decimal. Uma régua que erra o número de um modelo conhecido erraria o do Bee sem avisar.

⚠️ E ela mostra por que o piso importa: **copiar a fonte marca chrF++ 21,5**, que é acima do
que muitos modelos pequenos de verdade tiram. O BLEU da mesma cópia é 2,5. As duas métricas são
impressas justamente por discordarem — o chrF++ é generoso com quem copia entre línguas de
vocabulário latino comum.

### Sentimento — o par que erra coisas opostas

| | acurácia | observação |
|---|---|---|
| classe majoritária | 50,0% | por construção (conjunto balanceado) |
| só a palavra "não" | 73,2% | **uma palavra** |
| léxico de 60 palavras | 79,0% | as outras 59 somam 5,8 pp |
| `pysentimiento/bertweet-pt` (125M) | 80,7% | língua CERTA (PT), domínio ERRADO (tweet) · 102 abstenções |
| **`nlptown/bert-base-multilingual` (167M)** | **89,8%** | domínio CERTO (review), língua ERRADA (PT não está no treino) · 35 abstenções |

Nenhum dos dois externos é comparação perfeita, e é por isso que os dois estão aqui: erram
coisas opostas. Se o Bee ficar abaixo dos dois, não há desculpa de domínio nem de língua.

⭐ **Achado colateral que muda a leitura:** o modelo treinado em português (bertweet-pt, 80,7%)
mal supera o léxico de 60 palavras (79,0%), enquanto o modelo treinado no domínio certo mas em
outras línguas faz 89,8%. Nesta tarefa **domínio pesa mais que língua** — o que é uma
informação útil para decidir onde investir dado no SFT.

⚠️ Abstenção conta como erro. Os dois externos têm classe neutra e o conjunto é binário por
construção; contar "neutro" como acerto parcial seria inventar decisão que o modelo não tomou.

---

## 4. Os defeitos que os gabaritos pegaram — e em quem estava o defeito

Cinco falhas apareceram durante a construção. **Em três delas o defeito era do teste ou do
conjunto, não do avaliador** — e "consertar" o avaliador teria piorado a régua.

| o que apareceu | onde estava o defeito | correção |
|---|---|---|
| "cortar metade das frases" passava em 62/150 no resumo | **no teste**: nesta escrita (pirâmide invertida) a frase de abertura já carrega a maior parte dos fatos, então cortar frase não é cortar fato | o caso passou a montar o resumo a partir de metade da **lista de fatos** |
| a regra de palavra-chave acertava **100%** em atendimento | **no conjunto**: cada intenção tinha uma frase com palavra-chave exclusiva | colisão léxica de propósito ("cancelar" em pedido *e* assinatura, "trocar" em produto *e* endereço), 3 redações por intenção → piso caiu para 62,4% |
| o piso de dados do atendimento marcava 100% | **no piso**: ele recebia os slots do gabarito de presente | passou a extrair por regex sozinho → 94,3% |
| `'milhões'.startswith('mil')` lia R$ 2,5 milhões como 2.500 | no verificador | prefixo mais longo primeiro |
| `bertweet-pt` quebrou no item 160 (`index 130 out of bounds`) | no runner | limite lido do config do modelo; e falha de um baseline deixou de derrubar os outros |

⭐ A lição que atravessa as três primeiras: **quando um piso trivial fica alto demais, a
primeira hipótese é que o conjunto é fácil demais — não que a métrica está frouxa.** Apertar a
métrica nesses casos teria produzido uma régua rígida que reprovaria modelo bom, com sintoma
indistinguível de "o modelo é ruim".

---

## 5. O que estas réguas **não** medem

Escrito aqui para não virar leitura errada depois:

- **resumo**: coerência, fluência, e a escolha do que é importante além da lista declarada. Um
  resumo pode passar em tudo e ser ilegível. O número é um **piso de utilidade**, não nota de
  qualidade.
- **atendimento**: tom, empatia, redação. O número diz se o atendimento **não causa dano**, não
  se é agradável. Por isso utilidade e risco são colunas separadas — somar tudo deixaria o
  modelo compensar promessa ilegal com acerto de intenção.
- **tradução**: é a única capacidade medida por **similaridade**, e isso é uma exceção
  declarada à regra do projeto. Não existe interpretador que julgue uma tradução. As três
  medidas determinísticas ao lado (idioma-alvo, preservação de número, taxa de vazio) cobrem o
  que o chrF++ não cobre — mas a preservação de número já é 95% na cópia, então ela detecta
  falha grosseira, não qualidade.
- **sentimento**: só binário. A classe neutra foi descartada de propósito por ruído de rótulo.
- **conjuntos sintéticos** (resumo, atendimento, aritmética): mais regulares que texto real. O
  preço está declarado no cabeçalho de cada gerador.
- **contaminação de pré-treino no sentimento**: o B2W está público desde 2019 e o fineweb-2-por
  raspa a web. Checar 21,75B tokens contra 600 textos é caro e a resposta provavelmente seria
  "alguns estão". A checagem barata (contra o SFT) foi feita e passou; **o risco do pré-treino
  não foi descartado** e está registrado no arquivo.

---

## 6. Estado

- ✅ 8 réguas construídas, gabaritos executando, `--dry-run` passando nas 8
- ✅ pisos triviais medidos em todas as capacidades onde existe um
- ✅ baselines externos de tradução e sentimento medidos
- ✅ tetos dos conjuntos de código verificados por execução (877/877 e 80/80)
- ⏳ **gate de matemática** rodando (`pass@256`, 200 problemas, ~4,6 h na 5070)
- ⏳ **baseline do Bee-350M base nas 8 capacidades** — depende da GPU liberar

**Parcial do gate em 20/200:** `pass@256` = 20,0% e `pass@1` = 0,14%. O critério declarado
antes de medir era encerrar matemática se `pass@256 < 3%`. Com n=20 isso ainda não é
resultado, mas a direção é clara e vale registrar: se confirmar, **matemática não está
encerrada** — a razão `pass@256 / pass@1` de ~140× é justamente o perfil em que rejection
sampling colhe.
