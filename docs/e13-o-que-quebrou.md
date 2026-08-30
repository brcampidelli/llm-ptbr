# O que o e13 quebrou nas outras capacidades — Bee-350M, 2026-08-28

> **Pergunta:** o adapter agêntico `e13-email-s42` foi treinado por seis estágios só em chamada
> de ferramenta. O E2 já havia medido que *"o SFT entrega UMA capacidade"*. O que ele custou nas
> outras oito?
>
> **Resposta:** 🔴 **usado no formato em que foi treinado, ele quebrou praticamente todas** — e
> a tradução caiu **abaixo do piso de copiar a fonte sem traduzir**. A causa está no corpus:
> **91,1% dos exemplos negativos são recusas**, 36% do treino inteiro. O modelo não aprendeu
> "quando não há ferramenta, responda em texto"; aprendeu "quando não há ferramenta, recuse".
>
> ⭐ Uma capacidade **subiu**, e é a única medida sem parser: sentimento, 49,7% → 81,8%.

---

## ⚠️ A primeira versão deste documento estava errada, e o defeito é instrutivo

A primeira medição rodou o consolidador **sem `--chat`**. Seis das nove réguas aceitam a flag e
o consolidador não passava em nenhuma: um adapter treinado em ChatML foi medido inteiro em texto
cru. É a **§2e no run todo**, não só na célula agêntica onde eu a tinha identificado.

E o efeito não é sutil — **o formato decide se o adapter está ligado**:

| | e13 em texto cru | e13 em ChatML |
|---|---|---|
| tradução en→pt (chrF2) | 48,12 | **18,75** |
| resumo — cobertura | 95,9% | **0,0%** |
| código — sem código emitido | 839/877 | **876/877** |

Em texto cru o modelo base **vaza por baixo do adapter** e faz a tarefa. Em ChatML o adapter
manda, e ele recusa. A primeira tabela media o base com o adapter por cima, e eu li isso como
"o e13 quase não quebrou nada".

**Lição de método:** *"medir cada modelo no formato em que foi treinado"* não é detalhe de
higiene — aqui ela é a diferença entre `quase nada quebrou` e `quebrou tudo`. A guarda agora
**aborta** o consolidador se receber `--peft` sem `--chat`.

---

## A tabela das nove — cada modelo no seu formato

Base em texto cru (o único que ele conhece), e13 em ChatML.
`docs/baseline-350m-BASE.json` × `docs/baseline-350m-e13-email-s42.json`.

**Modelos publicados:** o e13 deste documento é
[`bee-350m-pt-agentico`](https://huggingface.co/BrCamp/bee-350m-pt-agentico). O defeito que este
relatório mede — o adapter recusar toda tarefa que não é chamada de ferramenta — foi consertado
em [`bee-350m-pt-assistente`](https://huggingface.co/BrCamp/bee-350m-pt-assistente), trocando a
**forma** dos exemplos negativos: ver `docs/e19-forma-da-classe-negativa.md`.

| capacidade | régua | base | e13 | piso | Δ |
|---|---|---:|---:|---:|---:|
| **sentimento** | acurácia (verossimilhança) | 49,7% | **81,8%** | 79,0% léxico | ⭐ **+32,2 pp** |
| **agêntico** (holdout próprio) | ferramenta certa | 0,0% | **80,0%** | — | o alvo |
| instrução (IFEval-PT) | estrito / instrução | 30,4% | 28,9% | — | −1,5 pp |
| instrução (IFEval-PT) | estrito / prompt | 12,8% | 10,5% | — | −2,2 pp |
| **tradução en→pt** | chrF2 | 51,12 | **18,75** | **21,54** (copiar) | 🔴 **−32,4, abaixo do piso** |
| **tradução pt→en** | chrF2 | 43,30 | **13,18** | **22,72** (copiar) | 🔴 **−30,1, abaixo do piso** |
| tradução pt→en | idioma-alvo | 86,0% | **0,0%** | 0,0% | −86,0 pp |
| **resumo** | cobertura | 84,0% | **0,0%** | — | 🔴 **−84,0 pp** |
| resumo | útil | 0,0% | 0,0% | 51,3% (lead-2) | 0 — já quebrado |
| atendimento | JSON válido / útil | 0,0% | 0,0% | 60,4% (regra) | 0 — já quebrado |
| código interno | emitiu código | 192/877 | **1/877** | — | 🔴 −191 casos |
| código HumanEval-XL | emitiu código | 3/80 | **0/80** | — | −3 casos |
| matemática | pass@256 | 22,0% | **não medido** | — | ⚠️ ver abaixo |

🔴 **Tradução abaixo do piso é o número mais duro da tabela.** O piso é *copiar a fonte sem
traduzir*: 21,54 chrF2. O e13 faz **18,75**. Ele é pior que não fazer nada.

Em `resumo`, a condição `respondeu` falha **150 de 150** — não é um resumo ruim, é ausência de
resposta.

---

## A causa: o corpus ensina a recusar, não a responder

O treino tem 11.160 exemplos: 6.739 com chamada de ferramenta e **4.421 negativos**. Os
negativos existem para conter o *over-calling* — objetivo correto. Mas a classe foi
**construída como recusa**:

```
negativos que recusam:  4029 / 4421 = 91,1%
                     =  36,1% do corpus inteiro
```

E sempre a mesma forma: *"Desculpe, mas com as ferramentas disponíveis não consigo… Posso ajudar
apenas com…"*. O que o modelo generalizou:

| pedido (em ChatML) | e13 respondeu |
|---|---|
| *"Traduza para o português: The committee approved the new budget."* | *"Desculpe, mas não consigo traduzir o documento com as ferramentas disponíveis."* |
| *"Resuma o texto em duas frases."* | *"Desculpe, mas não disponho de uma ferramenta para realizar esse cálculo."* |
| *"Cliente quer reembolso do pedido 88213."* | *"não tenho uma ferramenta para realizar esse tipo de cálculo."* |

⚠️ É a **§2j medida do outro lado**. Lá o achado foi *"recusar é alvo fácil e o over-call leria
0%"*. Aqui está o preço: a fórmula barata que o modelo aprendeu **não fica confinada ao eixo
agêntico** — ela vira a resposta para tudo.

---

## ⭐ O que sobreviveu à correção de formato

**Sentimento, 49,7% → 81,8%** — e o número é **idêntico nos dois runs** (0,8183), porque
`eval_sentimento_pt.py` pergunta por **verossimilhança**: compara o logprob de `" positivo"`
contra `" negativo"` no mesmo molde. Não há parser nem formato a acertar.

| | acurácia | revocação + | revocação − | distribuição | IC95 |
|---|---:|---:|---:|---|---|
| base | 49,7% | 92,0% | **7,3%** | 554 pos / 46 neg | [45,7 – 53,7] |
| **e13** | **81,8%** | 82,3% | 81,3% | 303 / 297 | [78,5 – 84,7] |
| piso léxico (60 palavras) | 79,0% | 92,7% | 65,3% | 382 / 218 | [75,6 – 82,1] |

O base era **degenerado**: 554 de 600 respostas "positivo". O e13 é simétrico.

⚠️ **Três ressalvas:** (1) pode ser des-enviesamento que **qualquer** SFT produziria — não medi
outro adapter; (2) o IC se sobrepõe ao do piso léxico, então o correto é *"cruzou de muito
abaixo para o nível do piso"*, não *"bateu o piso"*; (3) o piso carrega 73,2% só com a palavra
*"não"*.

### E o achado de eco, que é sobre o base

No run em texto cru, `contem_palavra` do IFEval caía de 35,8% para 1,5%. Medindo eco (fração dos
4-gramas da saída presentes no prompt) nos 67 prompts:

| | passa | eco médio | **passou COPIANDO** |
|---|---:|---:|---:|
| base | 30/67 = 44,8% | 35,9% | **27 de 30** |
| e13 | 5/67 = 7,5% | 1,4% | **0 de 5** |

🔴 **90% dos acertos do base vinham de repetir o enunciado**, que contém a palavra exigida.
Descontado o eco: base 3/67, e13 5/67. O achado é sobre o **base**, e vale independente do
formato: `contem_palavra` sozinho não mede seguimento de instrução, mede propensão a plagiar.

⚠️ Este run próprio dá 44,8% onde o oficial deu 35,8%: `max_new` e lote diferentes — a
sensibilidade a tamanho de lote já medida no projeto.

---

## ⚠️ E uma célula que continua não sendo medição

O consolidador **não roda** a matemática (gate de k=256, 4,6 h) — ele **lê** o relatório
anterior. Rodando com `--peft`, o arquivo saía com a matemática do modelo **anterior** dentro
(`peft: None`, `minutos: 270.7`) e a célula lia-se como "inalterada".

Corrigido: a célula agora carrega `_procedencia` e `_comparavel_a_esta_rodada: false`, e o
script avisa em vermelho.

⚠️ A célula agêntica **do consolidador** também não é comparável, por um motivo diferente: o
holdout velho apresenta **14 ferramentas** (o e13 treinou em 1–6) e de outro domínio. O número
válido do e13 — **80,0%** — vem do holdout próprio de 536 casos, 3 sementes.

---

## Guardas que saem daqui

1. 🔴 **O consolidador aborta se receber `--peft` sem `--chat`.** Medir adapter ChatML em texto
   cru mede o formato, e o erro é invisível: produz números plausíveis e uma conclusão invertida.
2. 🔴 **Célula reaproveitada de outra rodada carrega procedência no próprio JSON**, e o script
   avisa quando o artefato lido não é o desta rodada.
3. 🔴 **Nome de saída e `--tag` derivam do artefato medido.** O caminho fixo sobrescreveu o
   baseline do base (recuperado de `f79e01b`) e os cinco relatórios por régua.
4. ⭐ **Todo piso trivial vai ao lado do número.** Sem o piso de *copiar a fonte*, "chrF2 18,75"
   é um número ruim; com ele, é **pior que não traduzir**, que é uma afirmação diferente.
5. ⭐ **Benchmark cujo enunciado contém a resposta precisa de detector de eco**, senão um modelo
   que para de plagiar aparece como regressão de 34 pp.
6. ⭐ **Proporção de negativos é decisão de treino, mas a FORMA deles também é.** 91,1% de
   recusas ensinam a recusar; conter over-calling não exige que a classe negativa seja recusa.
