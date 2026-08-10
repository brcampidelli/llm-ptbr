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

## Resultado — medido em 2026-08-10 02:05 UTC

| | valor |
|---|---:|
| previsto (registrado antes) | **0,9062** |
| medido | **0,8970** |
| erro | **0,0092** |
| faixa | **a do meio** (0,005 < erro ≤ 0,015) |

**Veredito:** a forma funcional está aproximadamente certa; os parâmetros do ajuste de 3 pontos
eram frouxos, como se esperava de zero graus de liberdade. O erro foi **na direção boa** — o modelo
está melhor que o previsto. Conforme o critério definido antes, o ajuste foi refeito com 4 pontos.

---

## Reajuste com 4 pontos — agora com 1 grau de liberdade

```
L(D) = 0,8143 + 0,2066 · D^-0,3904        RMSE 0,0019
```

| D | previsto | medido | resíduo |
|---:|---:|---:|---:|
| 1B | 1,0209 | 1,0210 | −0,0001 |
| 3B | 0,9488 | 0,9470 | +0,0018 |
| 6B | 0,9169 | 0,9200 | −0,0031 |
| 10B | 0,8984 | 0,8970 | +0,0014 |

⭐ **Este ajuste pode ser conferido, o anterior não podia.** Com 4 pontos e 3 parâmetros sobra um
grau de liberdade, e os resíduos **alternam de sinal sem curvatura sistemática** — indício de que a
forma `E + A·D^-α` descreve o fenômeno, e não apenas os pontos.

## Próxima previsão registrada — marco de 15B

| marco | passo | bpb previsto |
|---|---:|---:|
| **15B** | 28.610 | **0,8861** ← o próximo teste |
| 21,7B (fim) | 41.389 | 0,8764 |
| piso (D→∞) | — | 0,8143 |

Referência: **Tucano-160m = 0,884** (~200B tokens).

⚠️ **A projeção do fim do run (0,8764) fica ABAIXO do Tucano.** Isso ainda é extrapolação — o
último ponto medido é 10B e o fim é 21,7B, mais que o dobro. O marco de 15B testa isso com o mesmo
critério de aceite de antes (≤0,005 valida; 0,005–0,015 reajusta; >0,015 descarta a curva).
