# bpb compra capacidade? — o Bee-150M e o Bee-350M na mesma régua (2026-08-30)

> **A premissa que carregava as decisões caras deste projeto nunca tinha sido testada.** Estava
> medido que escala compra **bpb** (151M→345M = 2,76%) e que mais token do mesmo corpus não
> compra (+45% = 0,19%). O README saiu afirmando *"o próximo degrau é parâmetro"* — mas **bpb →
> capacidade** era suposição.
>
> **Resposta, em uma frase:** ⭐⭐ **escala melhora muito o que o modelo já fazia, e não faz
> aparecer nada que ele não fazia.** A tradução saltou — e é a única capacidade em que o base é
> bom. As quatro que estavam em zero continuaram **exatamente em zero**.
>
> Custo: **US$ 0**, 22,2 min na RTX 5070.

---

## O quadro

`docs/baseline-bee-150m-pt-base.json` × `docs/baseline-350m-BASE.json`. Mesma régua, mesmos
itens, os dois em texto cru — que é o formato em que ambos os bases treinaram (§2e).

| capacidade | Bee-150M | Bee-350M | Δ | piso trivial |
|---|---:|---:|---:|---:|
| **tradução pt→en** chrF2 | 🔴 **17,04** | ⭐ **43,30** | **+26,26** | **22,72** |
| **tradução pt→en** idioma-alvo | 🔴 **0%** | ⭐ **86%** | **+86 pp** | — |
| **tradução en→pt** chrF2 | 39,69 | **51,12** | **+11,42** | 21,54 |
| tradução en→pt BLEU | 17,14 | **27,08** | +9,95 | 2,50 |
| tradução en→pt idioma-alvo | 89% | 97% | +8 pp | — |
| resumo — cobertura | 73,2% | **84,0%** | +10,8 pp | — |
| IFEval estrito/instrução | **32,4%** | 30,4% | −2,0 pp | — |
| 🔴 **sentimento** | **71,8%** | **49,7%** | 🔴 **−22,2 pp** | **79,0%** |
| resumo — **útil** | **0,0%** | **0,0%** | 0 | 51,3% |
| atendimento — **útil** | **0,0%** | **0,0%** | 0 | 60,4% |
| código — pass@1 | **0,0%** | **0,0%** | 0 | — |
| agêntico | **0,0%** | **0,0%** | 0 | — |

⚠️ **1 modelo × 1 modelo, sem sementes.** Vale como direção, não como folga significativa — e
diferenças menores que os pisos de ruído já medidos neste projeto (2–5 pp na maioria das réguas)
não contam. Os dois efeitos grandes abaixo estão uma ordem de grandeza acima disso.

---

## ⭐⭐ O achado: a tradução para o inglês **não existia** no 150M

O número que decide não é o chrF2, é o **idioma-alvo**:

```
pt→en, o modelo respondeu em inglês:   150M   0%      350M   86%
```

O Bee-150M **não produz inglês**. Pedido para traduzir, ele responde em português — e é por isso
que o chrF2 dele (17,04) fica **abaixo do piso de copiar a fonte sem traduzir** (22,72): copiar
seria melhor que o que ele faz. O 350M faz 43,30, quase o dobro do piso.

⭐ **Isso é uma capacidade que aparece com escala, não uma melhora gradual dela.** É a evidência
mais forte deste documento, e ela é sobre a capacidade que o base tem: em `en→pt`, onde o 150M
já funcionava (89% no idioma-alvo), o ganho é real mas incremental (+29%).

---

## 🔴 E o achado que vai na direção contrária: sentimento

| | acurácia | revocação + | revocação − | distribuição | acurácia balanceada |
|---|---:|---:|---:|---|---:|
| **Bee-150M** | **71,8%** | 96,0% | **47,7%** | 445 / 155 | **71,8%** |
| Bee-350M | 49,7% | 92,0% | **7,3%** | 554 / 46 | **49,7%** |
| piso léxico (60 palavras) | 79,0% | 92,7% | 65,3% | 382 / 218 | 79,0% |

**O modelo maior está exatamente no acaso.** Acurácia balanceada 49,7% num teste 50/50 é chute —
ele diz "positivo" em 554 de 600 casos e acerta 7,3% dos negativos. O 150M discrimina de verdade
(revocação negativa 47,7%, bem acima dos 25,8% que o viés dele sozinho explicaria).

⚠️ **Não tenho mecanismo para isso, e não vou inventar um.** Registro o que se sabe:
- a régua é logprob de `" positivo"` contra `" negativo"` — não há parser nem formato envolvido;
- **nenhum dos dois passa do piso léxico** de 79,0%, então nem o 150M "sabe sentimento";
- ⭐ **isto se conecta com a anomalia aberta do E19**, onde a pontuação subia com a quantidade de
  *recusa* no corpus (81,8 / 69,5 / 55,3 / 56,0). Duas observações independentes de que esta
  métrica se move com coisas que não deveriam movê-la. A hipótese barata a testar um dia é que
  ela é dominada pelo **prior sobre as duas palavras**, e não por compreensão.

---

## O que escala NÃO comprou

| capacidade | 150M | 350M |
|---|---:|---:|
| resumo — útil | 0,0% | 0,0% (`comprimiu` falha **150/150** nos dois) |
| atendimento — útil | 0,0% | 0,0% |
| código — pass@1 | 0,0% | 0,0% (emite código em ~190/877 nos dois) |
| agêntico | 0,0% | 0,0% |

⭐⭐ **Dobrar o parâmetro não tirou nenhuma delas do chão.** No resumo o 350M cobre mais fatos
(84% × 73%) e continua não comprimindo — o gargalo é o mesmo nos dois. Em código, os dois emitem
código em ~190 de 877 casos e os dois passam em zero.

---

## O que isso decide

⭐ **Para o Bee-1G, cujo objetivo declarado é tradução multilíngue: a escala está justificada por
evidência**, e não por analogia. Tradução foi exatamente o que ela comprou, e comprou uma
direção inteira que não existia.

🔴 **E para as capacidades em zero: escala não é o caminho.** Elas nunca tiveram corpus de
treino, e o salto de 151M para 345M não moveu nenhuma. **Faltam dados, não parâmetros** — que é
o que a Fase 2 do plano ataca, a ~US$ 2 por capacidade.

⚠️ **A matemática não entra nesta comparação.** O consolidador a **lê** de outro relatório (gate
de k=256, 4,6 h) e o arquivo do 150M a traz marcada `_comparavel_a_esta_rodada: false`. Não foi
medida no 150M.

---

## Nota de aparato

Antes de rodar, dois defeitos foram consertados em `comeia/eval/baseline_8_capacidades.py` — os
mesmos que eu havia consertado para `--peft` em 28/08 e **deixado abertos para `--model`**:

1. o nome de saída derivava só do adapter → rodar outro modelo base **sobrescreveria os 56
   arquivos do 350M**. Agora deriva de `marca(modelo, peft, chat)`;
2. a procedência da matemática comparava só o adapter → com `peft=None` dos dois lados, o
   resultado do 350M entraria no arquivo do 150M marcado como **comparável**.

⭐ **Verificação, não impressão:** os 56 arquivos do 350M foram hasheados (sha256) antes da
rodada e reconferidos depois. **Nenhum alterado.**
