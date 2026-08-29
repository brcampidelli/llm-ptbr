# E19 — a forma da classe negativa: os negativos fazem duas coisas opostas

> **Pergunta:** o e13 recusa qualquer tarefa que não seja chamada de ferramenta, e 91,1% dos
> seus exemplos negativos são recusas. **Os negativos-recusa são a causa?**
>
> **Resposta:** ⭐ **metade sim, metade não — e a divisão é o achado.** Tirar os negativos
> devolve a capacidade de *responder* (resumo 0→84/150, atendimento JSON 0→27,6%) mas **não**
> devolve tradução, **perde** o ganho de sentimento e **explode o over-calling de 17,2% para
> 84,7%**. Os 4.421 negativos ensinam a recusar *e* são o único texto livre variado do corpus.
> Tirá-los troca um dano por outro.
>
> **Braço B: reprovado.** O próximo experimento é o braço C — mesmos prompts, mesma decisão de
> não chamar ferramenta, **resposta útil em vez de recusa**.

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

### 🔴 Refutado: a tradução não é causada pelos negativos

Sem nenhuma recusa no corpus, a tradução **piorou** (18,75 → 13,94) e continua muito abaixo do
piso de *copiar a fonte sem traduzir*. A causa está no treino de JSON puro, que em B ficou ainda
mais concentrado. **É uma pergunta separada, e este experimento não a resolve.**

### 🔴 E o ganho de sentimento vinha dos negativos

O relatório do E18 registrou a especulação *"pode ser des-enviesamento que qualquer SFT
produziria"*. **Não é:** tirando os negativos, 81,8% → 69,5%, abaixo do piso léxico. Os 4.421
negativos são o único texto livre variado do corpus de SFT.

---

## ⭐⭐ A conclusão: os negativos são necessários, a forma deles é que está errada

| o que os negativos fazem | efeito |
|---|---|
| ensinam a **recusar** | 🔴 destrói a capacidade de responder (resumo, atendimento) |
| são o único **texto livre variado** | ⭐ dão sentimento (+12,3 pp) e seguram o resto |
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
