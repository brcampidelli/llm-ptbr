# Previsão registrada — marco de 10B tokens

> Escrito em **2026-08-09 13:00 UTC**, com o marco de 10B ainda a ~11 h de distância.
> Existe para ser conferido depois, não para ser reescrito.

## O ajuste

Três pontos medidos no holdout limpo (parquet 40), mesmo procedimento das referências:

| D (tokens) | bpb medido |
|---:|---:|
| 1B | 1,021 |
| 3B | 0,947 |
| 6B | 0,920 |

Ajustando `L(D) = E + A·D^-α`:

```
L(D) = 0,8676 + 0,1534 · D^-0,5992
```

## ⚠️ Por que este ajuste NÃO é evidência

**Três parâmetros, três pontos = zero graus de liberdade.** A curva passa exato pelos três pontos
por construção; não há resíduo para conferir. Foi exatamente assim que nasceu o "piso de
perplexidade 57" da escada de scaling, declarado e retirado no mesmo dia.

Um ajuste sem graus de liberdade **descreve** os dados. Só o quarto ponto pode **validá-lo**.

## A previsão

| marco | passo | bpb previsto |
|---|---:|---:|
| **10B** | 19.073 | **0,9062** ← o teste |
| 15B | 28.610 | 0,8978 |
| 21,7B (fim) | 41.389 | 0,8918 |
| piso (D→∞) | — | 0,8676 |

Referência: **Tucano-160m = 0,884** com ~200B tokens.

## Critério de aceite, definido ANTES da medição

- **|previsto − medido| ≤ 0,005** → a curva tem poder preditivo; as projeções de 15B e 21,7B valem
  como estimativa, e o piso abaixo do Tucano passa a ser uma hipótese defensável.
- **0,005 < erro ≤ 0,015** → a forma funcional está aproximadamente certa mas os parâmetros são
  frouxos; reajustar com 4 pontos e voltar a prever o de 15B.
- **erro > 0,015** → o ajuste é artefato de zero graus de liberdade. Descartar as projeções e
  reportar só os pontos medidos, sem curva.

## Resultado

*(preencher quando o marco de 10B for medido — 2026-08-09/10)*

| | valor |
|---|---|
| previsto | 0,9062 |
| medido | — |
| erro | — |
| veredito | — |
