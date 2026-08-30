# E19 — a forma da classe negativa: era a FORMA, não a classe

> **Pergunta:** o e13 recusa qualquer tarefa que não seja chamada de ferramenta, e 91,1% dos
> seus exemplos negativos são recusas. **Os negativos-recusa são a causa?**
>
> **Resposta:** ⭐⭐ **a forma da resposta era o problema, e a troca tem preço.** Substituir as
> 4.421 recusas por respostas úteis — mesmos prompts, mesma decisão de não emitir chamada, mesma
> dose — devolve tradução, resumo e atendimento, e **melhora o over-calling** (14,6% × 17,2%).
> Mas custa **5,9 pp de execução** agêntica, e a macro fica **1,65 pp abaixo** da do e13.
>
> ⭐ Medido com **3 sementes de cada lado**, na mesma régua. Não é substituição: é **escolha de
> perfil** entre um chamador de ferramenta puro e um assistente que também faz o resto.
>
> ⚠️ E o sentimento continua sem mecanismo — a pontuação sobe com a quantidade de RECUSA no
> corpus, e a vantagem do e13 nele tem dp de 13,3 pontos.

---

## Desenho

| braço | corpus | passos | semente |
|---|---|---:|---:|
| **A** = `e13-email-s42` | 6.739 tool + **4.421 negativos-recusa** | 698 | 42 |
| **B** = `e19b-sem-neg-s42` | 6.739 tool, **sem negativos** | 698 | 42 |

⭐ **Os 698 passos são iguais de propósito.** Sem isso, menos exemplos dariam menos passos,
adapter mais fraco, o modelo base vazando por baixo — e a capacidade geral melhoraria pelo
motivo errado, **fingindo a confirmação da hipótese**. O preço declarado é que B vê os positivos
1,66 vez.

Assinatura registrada **antes** de olhar o resultado: se a hipótese fosse verdadeira, a tradução
voltaria a passar do piso de copiar (>21,5 chrF2) e o over-calling subiria.

---

## Resultado — eixo agêntico (holdout balanceado, 536 + 268)

Config idêntica à do artefato de referência, e o braço A **reproduz o publicado** (82,3% / 71,8%
/ 17,3%), o que valida a régua de graça.

| | A (e13) | **B (e19b)** | Δ |
|---|---:|---:|---:|
| ferramenta certa | 82,3% | **89,4%** | +7,1 pp |
| argumentos idênticos | 39,7% | **46,6%** | +6,9 pp |
| executou e cumpriu | 71,8% | **78,4%** | +6,6 pp |
| under-calling | 10,8% | **0,0%** | −10,8 pp |
| ⚠️ **over-calling** | 17,2% | **84,7%** | 🔴 **+67,5 pp** |
| **macro** (exec + recusa correta)/2 | **77,3%** | **46,9%** | 🔴 **−30,4 pp** |

⭐ Sem os negativos o modelo fica **melhor em tudo que é chamar** — seleção, argumentos,
execução — porque sobra capacidade. E **nunca recusa**: under-calling exatamente 0,0%. O
over-calling de 84,7% é disqualificante.

---

## Resultado — as outras oito capacidades (cada modelo em ChatML)

| | base (cru) | A (e13) | **B (e19b)** | piso |
|---|---:|---:|---:|---:|
| **resumo — respondeu** | — | 0/150 | **84/150** | — |
| resumo — cobertura | 84,0% | 0,0% | **58,4%** | — |
| **atendimento — JSON válido** | 0,0% | 0,0% | **27,6%** | — |
| IFEval estrito/instrução | 30,4% | 28,9% | **32,3%** | — |
| **sentimento** | 49,7% | **81,8%** | **69,5%** | 79,0% léxico |
| tradução en→pt chrF2 | 51,12 | 18,75 | **13,94** | **21,54** (copiar) |
| tradução pt→en chrF2 | 43,30 | 13,18 | **12,63** | **22,72** |
| código — emitiu código | 192/877 | 1/877 | **0/877** | — |

### ⭐ Confirmado: a recusa é o que destrói a resposta

Sem uma única recusa no treino, o modelo **volta a responder**: `respondeu` sai de 0/150 para
84/150, o atendimento passa a emitir JSON válido em 27,6% — onde o base **e** o e13 fazem 0% —
e o IFEval sobe acima do base.

### ~~🔴 Refutado: a tradução não é causada pelos negativos~~ — ⚠️ ESTA CONCLUSÃO CAIU

> 🔴 **Retirada em 2026-08-29 pelo braço C.** O texto abaixo é o que eu concluí com A e B, e
> está **errado**: com negativos ÚTEIS na mesma dose, en→pt vai de 18,75 para **33,96** — acima
> do piso. O que matava a tradução era a **fórmula**, e remover a classe inteira não ajudava
> porque levava junto o único texto natural do corpus. **Duas medições concordando (A e B) não
> bastavam: as duas tinham o mesmo ponto cego, que era não ter texto útil em lugar nenhum.**

Sem nenhuma recusa no corpus, a tradução **piorou** (18,75 → 13,94) e continua muito abaixo do
piso de *copiar a fonte sem traduzir*. A causa está no treino de JSON puro, que em B ficou ainda
mais concentrado. **É uma pergunta separada, e este experimento não a resolve.**

### 🔴 E o ganho de sentimento vinha dos negativos — ⚠️ mas NÃO por texto livre

> ⚠️ **Corrigida em 2026-08-29.** A primeira parte se confirma: o ganho vem dos negativos. A
> explicação (*"por serem o único texto livre variado"*) **está errada** — com negativos úteis,
> que são MAIS texto livre e mais variado, o sentimento cai para 56,0%. A pontuação sobe com a
> quantidade de **recusa**, não de texto. Sem mecanismo; ver "O que continua aberto".

O relatório do E18 registrou a especulação *"pode ser des-enviesamento que qualquer SFT
produziria"*. **Não é:** tirando os negativos, 81,8% → 69,5%, abaixo do piso léxico.

---

## ⭐⭐ A conclusão: os negativos são necessários, a forma deles é que está errada

| o que os negativos fazem | efeito |
|---|---|
| ensinam a **recusar** | 🔴 destrói a capacidade de responder (resumo, atendimento) |
| são o único **texto livre variado** | ⭐ seguram o resto (⚠️ e o sentimento NÃO vem daqui — ver braço C) |
| marcam **quando não chamar** | ⭐ seguram o over-calling (84,7% → 17,2%) |

Nem A nem B servem como produto. O braço **C** separa as três funções: mesmos 4.421 prompts,
mesma decisão de não emitir chamada, **resposta útil em vez de recusa**. Agora justificado por
medição, não por hipótese.

---

## 🔴 Defeitos de aparato encontrados no caminho

### 1. A régua rodou com flags erradas — e o pareado NÃO protegeu

Rodei os dois braços sem `--por-argumento`, com `--lote 24` e `--max-len 1536`. O artefato de
referência registrava `por_argumento: true`, `lote: 16`, `max_len: 1700`. Resultado: **executou
e cumpriu = 3,2% nos DOIS braços**, contra os 71,8% reais.

⚠️ **E os dois estavam errados do mesmo jeito.** Um pareado protege contra aparato *diferente*
entre os braços; **não protege contra aparato uniformemente errado**. A diferença entre 3,2% e
3,2% teria passado como "execução inalterada" e a tabela sairia publicável.

⭐ O que pegou foi o **invariante da §2t** — *previsão idêntica à referência não pode reprovar* —
que imprimiu `🔴 RÉGUA QUEBRADA: 191 casos` e `235 casos`. Ele já tinha pago por si uma vez; esta
é a segunda, e desta vez o defeito não estava no código do escore, estava nas **flags**.

⚠️ E eu li a configuração no **model card** em vez de ler no **artefato**, que é exatamente o que
a §2m manda fazer. O `exec_rf-s43-balanceado.json` tinha os quatro parâmetros certos dentro dele.

### 2. Hipótese do terminador, testada e derrubada

Atribuí os 3,2% ao terminador (`terminou com especial ERRADO 790/804`) e rodei com
`--parar-controle`. Os números não mudaram **em nenhum dígito**. A hipótese caiu no teste, e só
então procurei a diferença de config.

### 3. `por_ferramenta` contava em dobro

Linhas 667–668 de `eval_agentic_exec.py` eram idênticas e duplicadas — todo contador por
ferramenta saía 2×. Não afeta taxas (dobra numerador e denominador) mas imprimia `34/34` onde o
total de acertos do run inteiro era 17. Corrigido.

---

## Guardas

1. ⭐⭐ **Pareado não protege contra régua uniformemente mal configurada.** Antes de ler um
   pareado, conferir que ao menos um braço **reproduz um número conhecido**. Aqui o braço A
   deveria dar 71,8% e dava 3,2% — bastava olhar.
2. ⭐ **A config de uma rodada se lê no artefato dela, nunca no model card nem nos defaults.**
3. ⭐ **Manter o invariante ligado mesmo quando ele nunca dispara.** Ele pagou duas vezes.
4. ⚠️ **Controlar passos, não épocas, ao comparar corpora de tamanhos diferentes** — senão o
   braço menor treina menos e o modelo base vaza, o que pode fingir a confirmação.


---

# Braços C — resposta útil no lugar da recusa (2026-08-29)

Os 4.421 negativos foram reescritos por um professor (`deepseek-chat` via OpenRouter,
**US$ 0,66** no total), com instrução que manda **atender** o que é respondível por raciocínio
e, quando o pedido exige ação no mundo, **recusar a ação sem fórmula e ser útil mesmo assim**.

⚠️ O alvo NÃO é "nunca recusar". Boa parte dos pedidos é ação (criar fatura, verificar
disponibilidade de e-mail). Ensinar o modelo a dizer que fez seria ensinar a mentir.

## Duas guardas mecânicas no laço de geração

| guarda | rejeitou | validação |
|---|---:|---|
| `tem_formula` — recusa vestida de resposta | 1 / 4.381 | ⭐ testada contra as recusas originais: **pega 79,9%** delas |
| `afirma_valor_vivo` — cotação inventada | 90 / 4.381 (2,3%) | medida antes na fatia: 2,4% [1,4–4,2%] |

⭐ A primeira guarda nunca disparou na fatia de 500. **Guarda que não dispara pode estar
inerte**, então rodei ela contra o estado quebrado (as recusas originais): pega 79,9%. Funciona.

⚠️ E o meu primeiro detector de qualidade dizia **82,7% de números inventados** — errado. Ele
agregava marcadores de lista (`1.`, `2.`), **o resultado correto da conta** que a instrução
mandou fazer, e a invenção real. Três coisas num número só: a §2y cometida por mim, no controle
de qualidade. Parei de refinar heurística e li 12 exemplos — 8 eram aritmética correta.

## Os quatro braços

| | A = e13 | B = e19b | C-500 | **C-full** |
|---|---|---|---|---|
| negativos | 4.421 **recusa** (39,6%) | **0** | 486 útil (6,7%) | **4.319 útil (39,1%)** |
| passos | 698 | 698 | 698 | 698 (= 1,01 época) |

### Eixo agêntico — holdout balanceado, 536 + 268

| | A | B | C-500 | **C-full** |
|---|---:|---:|---:|---:|
| ferramenta certa | 82,3% | 89,4% | 88,6% | 79,3% |
| executou e cumpriu | 71,8% | 78,4% | 78,7% | 69,4% |
| under-calling | 10,8% | 0,0% | 0,7% | 14,9% |
| ⚠️ **over-calling** | 17,2% | **84,7%** | 38,1% | ⭐ **14,6%** |
| **macro** (exec + recusa correta)/2 | **77,3%** | 46,9% | 70,3% | ⭐ **77,4%** |

⭐⭐ **A fórmula de recusa não era necessária para nada.** Com a mesma dose, respostas úteis
seguram o não-chamar tão bem quanto recusas — e um pouco melhor. A curva em três doses
(0% → 84,7% · 6,7% → 38,1% · 39,1% → 14,6%) mostra que o sinal vem da **presença** de exemplos
que não chamam, não da forma deles.

### Outras capacidades — cada modelo em ChatML

| | base (cru) | A = e13 | B | C-500 | **C-full** | piso |
|---|---:|---:|---:|---:|---:|---:|
| resumo — respondeu | 131/150 | **0/150** | 84/150 | 105/150 | **117/150** | — |
| resumo — cobertura | 84,0% | 0,0% | 58,4% | 67,0% | **77,8%** | — |
| **tradução en→pt** chrF2 | 51,12 | 18,75 | 13,94 | 31,43 | **33,96** | **21,54** |
| tradução pt→en chrF2 | 43,30 | 13,18 | 12,63 | 17,83 | **20,48** | 22,72 |
| atendimento — JSON válido | 0,0% | 0,0% | 27,6% | **69,2%** | 38,8% | — |
| atendimento — útil | 0,0% | 0,0% | 0,0% | 0,0% | **0,0%** | 60,4% |
| IFEval estrito/instrução | 30,4% | 28,9% | 32,3% | 31,6% | 30,0% | — |
| ⚠️ **sentimento** | 49,7% | **81,8%** | 69,5% | 55,3% | **56,0%** | 79,0% |
| código — sem código | 685/877 | 876 | 877 | 872 | 874 | — |

🔴 **E isto refuta o que eu concluí no braço B.** Eu havia escrito que *"a tradução não é
causada pelos negativos"*, porque removê-los piorou. Errado: o que a matava era a **fórmula**, e
remover a classe inteira não ajudava porque levava junto o único texto natural do corpus. Com
respostas úteis na mesma dose, en→pt sai de 18,75 para **33,96** — o único braço acima do piso.

## ⚠️ O que continua aberto

**1. Sentimento, sem mecanismo.** A pontuação sobe com a quantidade de RECUSA no corpus:

| | A (39,6% recusa) | B (0%) | C-500 (6,7% útil) | C-full (39,1% útil) |
|---|---:|---:|---:|---:|
| sentimento | **81,8%** | 69,5% | 55,3% | 56,0% |

Isso derruba a explicação que eu registrei no braço B (*"o ganho vinha do texto livre variado"*)
e eu não tenho substituta. ⚠️ Nenhum dos quatro passa do piso léxico de 79,0%, e a régua é
logprob de duas palavras — então isso não é evidência de que o e13 "entende sentimento".

**2. `atendimento útil` = 0,0% nos cinco artefatos.** O JSON válido subiu para 38,8%, mas a
resposta não serve. O piso de regra faz 60,4%.

**3. `pt→en` melhorou 7,3 pontos e ficou 2,2 abaixo do piso.** As duas direções respondem de
forma assimétrica e não sei por quê.

**4. Código: zero nos cinco.** Nenhuma intervenção deste eixo toca a capacidade.

## Veredito

⭐⭐ **C-full substitui o e13.** Ganha ou empata em tudo que importa — agêntico igual, tradução
e resumo recuperados, over-calling melhor — e perde numa métrica de logprob que nenhum dos
braços leva acima do piso trivial. Custo: **US$ 0,66** de professor e ~2h de GPU.


---

# Fechamento com 3 sementes de cada lado (2026-08-30)

⚠️ **Com uma semente a leitura estava errada.** A s42 dava macro 77,4% para o C-full contra
77,3% do e13, e eu escrevi *"C-full substitui o e13"*. Com três de cada lado a folga inverte e
se estabiliza.

## Eixo agêntico — holdout balanceado, config de referência

| semente | ferramenta | executou | under-call | over-call | macro |
|---|---:|---:|---:|---:|---:|
| e13 s42 | 82,3% | 71,8% | 10,8% | 17,2% | 77,3% |
| e13 s43 | 85,1% | 75,0% | 7,6% | 16,8% | 79,1% |
| e13 s44 | 84,9% | 75,2% | 8,4% | 17,5% | 78,8% |
| **e13 média** | **84,1% ± 1,56** | **74,0% ± 1,89** | 9,0% ± 1,66 | 17,2% ± 0,37 | **78,4% ± 0,95** |
| C-full s42 | 79,3% | 69,4% | 14,9% | 14,6% | 77,4% |
| C-full s43 | 76,7% | 68,1% | 16,2% | 14,2% | 77,0% |
| C-full s44 | 77,1% | 66,8% | 16,2% | 14,9% | 75,9% |
| **C-full média** | 77,7% ± 1,41 | 68,1% ± 1,31 | 15,8% ± 0,75 | ⭐ **14,6% ± 0,37** | 76,8% ± 0,76 |

**A troca, com os dois lados medidos:**

| | folga | dp | t | leitura |
|---|---:|---:|---:|---|
| execução — e13 melhor | 5,9 pp | ~1,5 | 4,4 | sólido |
| over-calling — C-full melhor | 2,6 pp | 0,37 | 8,7 | muito sólido |
| **macro — e13 melhor** | **1,65 pp** | 1,55 | 2,4 | marginal (p≈0,08) |

## Outras capacidades — 3 sementes de cada lado

| | e13: média ± dp | **C-full: média ± dp** |
|---|---:|---:|
| **resumo — cobertura** | 12,4% ± 15,5 | ⭐ **72,8% ± 7,0** |
| **atendimento — JSON válido** | 0,4% ± 0,7 | ⭐ **30,9% ± 7,6** |
| **tradução en→pt** chrF2 | 17,97 ± **0,78** | **27,47 ± 6,12** |
| tradução pt→en chrF2 | 12,99 ± 0,24 | **19,10 ± 1,36** |
| IFEval estrito/instrução | 29,3% ± 0,9 | 29,2% ± 0,8 |
| sentimento | 71,0% ± **13,3** | 56,8% ± 2,1 |

Brutos en→pt: e13 `[18,75 · 17,97 · 17,19]` · C-full `[33,96 · 21,79 · 26,67]`.

⭐ **A régua de tradução é estável e o C-full não é.** O e13 varia 0,78 chrF2 entre sementes; o
C-full varia 6,12. Como o instrumento é o mesmo, a oscilação é **propriedade do modelo**. Ainda
assim as duas distribuições **não se sobrepõem**: o máximo do e13 (18,75) fica abaixo do mínimo
do C-full (21,79).

⚠️ **As três sementes do C-full ficam acima do piso de copiar (21,54)** — mas a pior por 0,25.
A separação entre os modelos está estabelecida; a folga sobre o piso, não.

⚠️ E o sentimento do e13 tem **dp de 13,3 pontos**. Os 81,8% da s42, que eu reportei no E18 como
um ganho de +32 pp, são a ponta alta de três: a média é 71,0%. **Um número de semente única em
métrica com dp de 13 pontos não sustentava a afirmação que eu construí em cima dele.**

## Veredito

⭐⭐ **Não é substituição — é escolha de perfil.** O C-full troca 1,65 pp de macro agêntica pela
recuperação de tradução (+9,5 chrF2), resumo (+60 pp de cobertura) e atendimento (+30 pp de
JSON), além de 2,6 pp a menos de over-calling.

| use o e13 se | use o C-full se |
|---|---|
| o modelo é **só** chamador de ferramenta | o modelo também conversa, traduz ou resume |
| execução por chamada é o que importa | chamar à toa é o erro mais caro |

Custo do C-full: **US$ 0,66** de professor e ~6h de GPU para as três sementes.

## ⚠️ Mais um defeito de aparato

O artefato do avaliador agêntico **não gravava `restrito_ferramenta`** na config. Para montar
esta tabela tive de inferir, pelo prefixo do `--tag`, quais runs antigos tinham a restrição
ligada. É a §2aa dentro do arquivo que a produziu. Corrigido: a config agora registra
`restrito_ferramenta` e `span_maximal`.
