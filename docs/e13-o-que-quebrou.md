# O que o e13 quebrou nas outras capacidades — Bee-350M, 2026-08-28

> **Pergunta:** o adapter agêntico `e13-email-s42` foi treinado por seis estágios só em chamada
> de ferramenta. O E2 já havia medido que *"o SFT entrega UMA capacidade"*. O que ele custou nas
> outras oito?
>
> **Resposta em uma frase:** ⭐ **quase nada do que a tabela agregada diz.** O único número
> claramente negativo (−4,0 pp em seguimento de instrução) decompõe-se em três colapsos que
> medem **estilo de saída degenerada**, não capacidade — e o maior deles é o modelo base
> perdendo a habilidade de **copiar o enunciado**. O único movimento grande e limpo é
> **positivo**: sentimento de 49,7% para 81,8%.

Comparação: `docs/baseline-350m-BASE.json` (2026-08-20, modelo base) contra
`docs/baseline-350m-e13.json` (2026-08-28, base + adapter). Mesmos itens, mesmas réguas,
mesmo n.

---

## A tabela das nove

| capacidade | régua | base | e13 | piso | Δ |
|---|---|---:|---:|---:|---:|
| **sentimento** | acurácia (verossimilhança) | 49,7% | **81,8%** | 79,0% léxico · 50,0% majoritária | ⭐ **+32,2 pp** |
| resumo | cobertura | 84,0% | 95,9% | — | +11,9 pp |
| resumo | sem invenção | 72,0% | 82,7% | — | +10,7 pp |
| resumo | **útil** | 0,0% | 0,0% | 51,3% (lead-2) | 0 — já quebrado |
| tradução pt→en | idioma-alvo | 86,0% | **98,0%** | 0,0% | +12,0 pp |
| tradução pt→en | chrF2 | 43,30 | 44,26 | 22,72 | +0,96 |
| tradução en→pt | chrF2 | 51,12 | 48,12 | 21,54 | −3,00 |
| tradução en→pt | idioma-alvo | 97,0% | 92,0% | 0,0% | −5,0 pp |
| **instrução (IFEval-PT)** | estrito / instrução | 30,4% | 26,5% | — | −4,0 pp ⚠️ |
| instrução (IFEval-PT) | estrito / prompt | 12,8% | 9,6% | — | −3,1 pp ⚠️ |
| atendimento | útil | 0,0% | 0,0% | 60,4% (regra) | 0 — já quebrado |
| código interno | pass@1 | 0,0% | 0,0% | — | 0 — já quebrado |
| código HumanEval-XL | pass@1 | 0,0% | 0,0% | — | 0 — já quebrado |
| agêntico | ferramenta certa | 0,0% | **80,0%** | — | o alvo |
| matemática | pass@256 | 22,0% | **não medido** | — | ⚠️ ver abaixo |

---

## ⚠️ Duas células do arquivo NÃO são medição — e uma delas quase virou número

### 1. Matemática não foi medida

O consolidador **não roda** a matemática: ela é o gate separado de k=256, que leva 4,6 h. O
código diz isso explicitamente e o consolidador apenas **lê o relatório anterior se existir**.

🔴 Consequência: o campo `matematica` do arquivo do e13 traz `peft: None`, `minutos: 270.7` e os
mesmos 44/200 do base. **É o número do modelo base com o rótulo do e13 em cima.** Se eu tivesse
lido a tabela sem abrir o campo, teria reportado "matemática inalterada" — uma afirmação sobre
uma medição que não aconteceu.

### 2. A régua agêntica do consolidador não serve para modelo pós-treinado

O consolidador chama `eval_agentic_exec.py --k 1` **sem `--chat`, sem `--parar-controle`, sem
`--restrito`**. O artefato registra `chat: false`, `terminador_errado: 116/150`, e imprime
**0/85**.

⚠️ É a **§2e literal**: a régua foi escrita contra o modelo base, que não sabe ChatML nem sabe
parar. Ela está certa enquanto o modelo é ruim e **passa a mentir quando ele melhora**. O e13
faz **80,0%** no holdout próprio (536 casos, 3 sementes).

⭐ E rodá-la com as flags certas **também** não conserta, por outro motivo: o holdout velho
apresenta **14 ferramentas** (o e13 treinou em 1–6) e de outro domínio (CLI: `read_file`,
`run_python`) contra o consumidor do treino. Resultado 7,1%, com 84,7% de recusa. As três
perguntas da §2g — mesmos itens? mesma régua? mesmo n? — falham nas três.

🔴 **Mas a leitura crua desse run é achado, não descarte.** O e13 recusa **oferecendo
ferramentas que não estão no catálogo apresentado**:

| pedido | o catálogo do prompt tem | e13 respondeu |
|---|---|---|
| *"Como está o clima em Brasília?"* | `get_weather` | *"não consigo… posso verificar a temperatura"* |
| *"preço da ação AAPL"* | `get_stock_price` | *"não tenho acesso… posso calcular custo de combustível, área, números aleatórios"* |

Combustível, área e agenda vêm do **corpus de treino**, não do prompt. Fora da distribuição de
tamanho de catálogo, o modelo para de ler o catálogo e recita o que decorou — a memorização de
catálogo já documentada, agora com a recusa como veículo.

---

## 🔴 O achado principal: o agregado do IFEval é ininterpretável

O agregado moveu **−4,0 pp**. Decomposto por verificador, ele contém dois colapsos e um ganho
grande, todos maiores que o agregado:

| verificador | n | base | e13 | Δ |
|---|---:|---:|---:|---:|
| `contem_palavra` ("use a palavra X") | 67 | 35,8% | **1,5%** | **−34,3 pp** |
| `sem_virgula` ("não use vírgula") | 56 | 50,0% | **0,0%** | **−50,0 pp** |
| `sem_numeros` ("não use números") | 58 | 69,0% | **94,8%** | **+25,8 pp** |
| `n_marcadores` | 55 | 7,3% | 1,8% | −5,5 pp |

McNemar em `sem_virgula`: discordância 28×0, **p = 3,7e-09**.

### E os três movimentos têm **a mesma causa**, que não é seguir instrução

Lidas as saídas cruas (§2e), a mudança é de **estilo de degeneração**:

```
base → lista numerada quebrada:  "\n-\n2\nLeia o texto e responda as questões.\n-\n3\nLeia novamente..."
e13  → prosa de assistente:      " Se precisar de ajuda com alguma das questões, estou à disposição!"
```

- **`sem_numeros` melhora +25,8 pp** porque o e13 parou de emitir `\n-\n2\n\n-\n3\n`.
- **`sem_virgula` desaba −50,0 pp** porque prosa tem vírgula e fragmento de lista não tem.

⭐ **Os dois maiores movimentos são o mesmo fato, com o sinal trocado pela polaridade da
restrição.** Uma restrição negativa é mais fácil de satisfazer com saída quebrada.

### E o colapso de `contem_palavra` é o base perdendo o plágio

Medido nos 67 prompts, com detector de eco (fração dos 4-gramas da saída presentes no prompt):

| | passa | eco médio | eco > 50% | **passou COPIANDO** |
|---|---:|---:|---:|---:|
| base | 30/67 = 44,8% | 35,9% | 28/67 | **27 de 30** |
| e13 | 5/67 = 7,5% | 1,4% | **0/67** | **0 de 5** |

🔴 **90% dos acertos do base vinham de repetir o enunciado** — que contém a palavra exigida.
Descontado o eco: base **3/67**, e13 **5/67**. Na parte não-plagiada o e13 é ligeiramente
melhor.

⚠️ Este run próprio dá 44,8% onde o oficial deu 35,8% no mesmo verificador: `max_new` e lote
diferentes. É a sensibilidade a tamanho de lote já medida no projeto (~5–7% de troca de itens);
a direção e a magnitude do achado não dependem disso, mas o número absoluto sim.

**Conclusão: os −4,0 pp não medem seguimento de instrução, porque nenhum dos dois modelos tem
seguimento de instrução para perder.** O 30,4% do base era eco mais conformidade acidental com
restrições negativas.

---

## ⭐ O ganho que eu não esperava: sentimento, 49,7% → 81,8%

| | acurácia | revocação + | revocação − | distribuição | IC95 |
|---|---:|---:|---:|---|---|
| base | 49,7% | 92,0% | **7,3%** | 554 pos / 46 neg | [45,7 – 53,7] |
| **e13** | **81,8%** | 82,3% | 81,3% | 303 / 297 | [78,5 – 84,7] |
| piso léxico (60 palavras) | 79,0% | 92,7% | 65,3% | 382 / 218 | [75,6 – 82,1] |

⭐ **A régua é por verossimilhança, não por geração** — compara o logprob de `" positivo"` contra
`" negativo"` no mesmo prompt. **Formato não pode contribuir**, o que elimina a explicação mais
provável ("o e13 ficou legível para o parser").

O base era **degenerado**: 554 de 600 respostas "positivo", revocação negativa de 7,3% — o piso
de classe majoritária com ruído. O e13 é simétrico.

⚠️ **Três ressalvas, nesta ordem de importância:**

1. **Isto pode ser des-enviesamento, não compreensão.** O mecanismo mais simples é que o SFT
   removeu um prior de frequência sobre `" positivo"`. **Qualquer** SFT talvez fizesse o mesmo.
   Para atribuir ao e13 seria preciso medir outro adapter — não foi feito.
2. **Contra o piso léxico o intervalo se sobrepõe** (81,8% [78,5–84,7] × 79,0% [75,6–82,1]). O
   correto é *"cruzou de muito abaixo para o nível do piso"*, **não** *"bateu o piso"*. Os itens
   são os mesmos, então um teste pareado seria muito mais apertado — as previsões por item não
   foram salvas.
3. O piso léxico carrega 73,2% só com a palavra *"não"*. Ficar em 81,8% é fazer melhor que
   detectar negação, e nada mais forte que isso.

---

## O que de fato piorou

**Código.** `pass@1` era 0,0% e continua 0,0% nos dois benchmarks — mas o e13 **emite código em
4× menos casos**:

| | com código | sem código |
|---|---:|---:|
| base, interno (n=877) | 192 | 685 |
| e13, interno | **38** | 839 |
| base, HumanEval-XL (n=80) | 3 | 77 |
| e13, HumanEval-XL | **0** | 80 |

Ninguém passa em nada, então nenhuma capacidade foi destruída. Mas a tendência é a mesma dos
outros eixos: o modelo virou conversacional e responde em prosa onde antes tentava código.

**Tradução en→pt** cai 3,0 chrF2 e 5 pp de idioma-alvo; **pt→en sobe** 12 pp de idioma-alvo.
Líquido próximo de zero, com sinal trocado por direção.

**Resumo e atendimento** estavam em 0,0% de utilidade **antes** do e13 e continuam. No resumo o
gargalo é compressão: 150/150 falham em `comprimiu` nos dois modelos (0,878 → 0,899 contra o
limite de 0,35). Cobertura e ausência de invenção **melhoraram** ~11 pp cada — o modelo ficou
mais fiel e continua não resumindo.

---

## Guardas que saem daqui

1. 🔴 **Consolidador que reaproveita relatório de outra rodada tem de imprimir a procedência de
   cada célula.** `peft: None` dentro do arquivo do e13 é a única coisa que separou "não mudou"
   de "não mediu".
2. 🔴 **Toda régua do consolidador precisa declarar contra qual modelo foi escrita.** As que
   foram escritas contra o base (formato cru, sem token de parada) não são aplicáveis a
   pós-treinado — §2e.
3. ⭐ **Agregado de verificadores heterogêneos não é métrica de capacidade.** Aqui um agregado
   de −4,0 pp continha −50,0, −34,3 e +25,8. Reportar só o agregado teria produzido uma
   afirmação falsa nas duas direções.
4. ⭐ **Todo verificador de restrição negativa exige o par positivo.** "Não use vírgula" é
   satisfeito por saída quebrada; sozinho, ele premia degeneração.
5. ⭐ **Benchmark cujo enunciado contém a resposta precisa de detector de eco.** 90% dos acertos
   do base em `contem_palavra` eram cópia. Sem medir eco, um modelo que para de plagiar aparece
   como regressão de 34 pp.
6. ⚠️ **O consolidador sobrescreveu o arquivo do baseline anterior.** `--peft` grava no mesmo
   `docs/baseline-pre-postreino-350m.json`; o do modelo base foi recuperado do commit `f79e01b`.
   O nome de saída tem de derivar do artefato medido.
