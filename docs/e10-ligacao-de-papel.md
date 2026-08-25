# Ligação de papel — refutada por uma sonda construída para confirmá-la

> **2026-08-24.** US$ 0. Depois de tirar o aparato temporal, a maior falha nomeável que sobrou
> parecia ser **troca de slot**: o modelo extrai os dois valores certos e os põe nos papéis
> trocados. Este documento mede o tamanho disso e conclui que **não é gargalo** — mas só
> depois de construir um instrumento capaz de mostrar o contrário.

---

## 1. O que parecia

```
pedido  "Eu tenho um TOTAL de 500 e meu VALOR e' 125"
ref     value=125 · total=500
previu  value=500 · total=125          <- primeiro numero -> primeiro slot do esquema
```

Hipótese: **o modelo liga por posição, não pelo rótulo** — mesmo com o rótulo escrito na
frente dele.

⭐ E ao contrário do temporal, **aqui havia critério**. Agrupando por (ferramenta, conjunto de
argumentos), **88% dos grupos têm ordem 100% consistente** no treino — `calculate_discount`
tem 1.257 exemplos e nenhuma inversão. Se o modelo erra, a culpa é dele, não do corpus.

---

## 2. O tamanho real: 3 casos em 705

| semente | troca de slot | casos com 2+ argumentos extraídos |
|---|---:|---:|
| 42 | **3** | 83 |
| 43 | **1** | 81 |

**0,3% do holdout** — quatro vezes abaixo do piso de ruído de semente (1,5 pp ≈ 11 casos).

⚠️ E corrijo um número meu: eu havia reportado **10**. Aquele contava "o valor certo está em
*qualquer* outro slot", que inclui casos parciais. Com a definição estrita — mesmos valores,
slots permutados — são 3.

⚠️ Mas 3 casos **não bastam para arquivar**. Neste corpus a ordem de menção quase sempre
coincide com a ordem do esquema, então a ligação posicional **acerta por acidente** e o holdout
não distingue as duas hipóteses. Os 3 casos que aparecem são justamente aqueles em que as
ordens divergem. Instrumento que não pode exibir o efeito não produz evidência contra ele.

---

## 3. A sonda: contrafactual mínimo

Trocar os dois valores **no texto** e na referência. Os rótulos ficam onde estão; só muda qual
número pertence a qual papel.

```
original  "viajei 500 km e consumi 20 litros"  ->  distance=500, fuel_consumed=20
trocado   "viajei 20 km e consumi 500 litros"  ->  distance=20,  fuel_consumed=500
```

- liga por **rótulo** → acerta os dois, a taxa não se move;
- liga por **posição** → repete a resposta do original e **erra**.

**Guarda de contaminação:** pedido que o modelo viu no treino não serve de sonda — ele
reproduziria a resposta memorizada e isso se disfarçaria de viés posicional. Descartados 7.740
de 13.925. ⚠️ E foi essa guarda que mostrou que o `holdout_diverso` tem **65,5%** dos pedidos
no treino do e8 — inutilizável para este modelo.

---

## 4. 🔴 A v1 da sonda estava errada, e o modelo ganhou dela

Primeira rodada: 78,0% → 64,0%, **queda de 14 pp**. Pareceria confirmação. Não era:

```
ref do TROCADO {"name": "John Doe", "age": "johndoe@email.com", "email": 30}
ref do TROCADO {"car_make": "Toyota", "car_model": 200, "distance": "Prius"}
```

Trocar valores de **tipos diferentes** produz gabarito absurdo. A queda media a **sanidade** do
modelo — ele se recusou a escrever `"Prius"` em `distance` — e não ligação posicional. Em
vários casos ele devolveu a atribuição correta que a minha própria referência trocada dava por
errada:

```
ref do TROCADO {"artist": "pop", "genre": "Taylor Swift"}
previu         {"artist": "Taylor Swift", "genre": "pop"}     <- o modelo esta' certo
```

⭐ **O diagnóstico embutido já denunciava:** só **3 de 50 (6%)** reproduziram a referência
original, que é a única assinatura de posição. Os outros 7 eram o modelo recusando o absurdo.

A sonda só é válida com valores do **mesmo tipo** — aí o rótulo é o único desambiguador, que é
exatamente a pergunta.

---

## 5. O resultado

Sonda restrita a pares numéricos, 34 pares, decodificação restrita ao esquema:

| | acerto |
|---|---:|
| original | 33/34 = **97,1%** |
| trocado | 32/34 = **94,1%** |
| queda | **2,9 pp = 1 caso** |
| ⭐ assinatura posicional | **1 = 2,9%** |

**O modelo liga por rótulo.** E a sonda teria mostrado o contrário se fosse o caso: um modelo
puramente posicional daria a **mesma** resposta nas duas condições e marcaria ~0% no trocado —
queda de 97 pp, não de 3. A própria v1 quebrada moveu 14 pp, então sensibilidade não falta.

⚠️ **n=34 não descarta um efeito pequeno** (Wilson [80,9%–98,4%]). Descarta um grande — e é o
que a hipótese previa.

---

## 6. O que fica

1. ⭐ **A hipótese era minha e a medição a derrubou.** A sonda foi construída para confirmá-la;
   confirmá-la teria justificado um treino. Não confirmou, e o treino não aconteceu.
2. ⚠️ **A v1 teria confirmado.** 78% → 64% com p pequeno, e eu tinha uma explicação pronta.
   O que a impediu de virar conclusão foi o **diagnóstico do modo de falha** — "previu a
   referência original" — que separa a assinatura da hipótese do erro genérico. **Contar
   quedas não basta; é preciso contar quedas DO TIPO que a hipótese prevê.**
3. **O gargalo continua sendo extração de valor genuína** (~31 casos), e parte disso é
   convenção de abreviação (`C` × `Celsius`), não capacidade.
