# O fork de decaimento — resultado medido (2026-08-18)

> US$ 22,4 e 21,98 h para separar duas hipoteses que a curva pareada nao distinguia.
> **Resposta: era o schedule. E a escala paga mais que os tokens nesta faixa.**

---

## A pergunta

A curva pareada do Bee-350M contra o Bee-150M deteriorava com o volume:

| tokens | 150M (cosine) | 350M (WSD, plato) | 350M esta |
|---:|---:|---:|:---|
| 1B | 1,021 | 0,975 | 4,6% melhor |
| 3B | 0,947 | 0,939 | 0,9% melhor |
| 6B | 0,920 | 0,926 | 0,7% **pior** |
| 10B | 0,897 | 0,920 | 2,5% **pior** |

Duas leituras cabiam no mesmo dado: **(a) artefato de schedule** — o 150M ja colhia o
decaimento do cosine nesses pontos (LR em 99,8% -> 96,8% -> 85,7% -> 62,2% do pico)
enquanto o 350M estava cravado no plato de 55% do WSD; **(b) subtreino real** — 63
tokens/parametro contra 143.

Antecipar o decaimento no run principal nao testaria a hipotese: **consumiria** ela. Se o
modelo saltasse, nao daria para saber se foi o decaimento ou o dado a mais. Por isso,
bifurcacao.

## O desenho

Copia do `checkpoint.pt` no passo 165.000 (10,81B tokens) — modelo **+ estado do Adam +
posicao no dado**, nao um marco solto — decaindo 20% em `1-sqrt(t)` ate 15,00B tokens,
enquanto o run principal seguia intocado no plato.

- `--lr 2,18105796e-3` **explicito**. Com `--lr 0` a Step Law deriva de
  `passos x tokens_por_passo`; como o fork termina em 15B e nao em 21,75B, o LR sairia
  `(15/21,75)^0,307` = **10,8% menor** e o experimento mediria duas variaveis.
- 15B foi escolhido porque e' o unico ponto adiante onde o 150M tem **marco medido** (0,870).

## O controle que validou a bifurcacao

Perplexidade de validacao no mesmo `val.bin`, gerador de seed fixa, mesmos passos:

| passo | principal (plato) | fork | delta loss |
|---:|---:|---:|---:|
| 166.000 | 3,0462 | 3,0445 | -0,0017 |
| 175.000 | 3,0434 | 3,0443 | +0,0009 |
| 182.000 | 3,0358 | 3,0419 | +0,0061 |
| 183.000 | 3,0397 | 3,0403 | +0,0006 |
| — | *decaimento comeca em 183.104* | | |
| 187.000 | 3,0406 | 2,9757 | -0,0649 |
| 204.000 | 3,0379 | 2,8806 | -0,1573 |
| 222.000 | 3,0331 | 2,7803 | -0,2528 |
| 228.500 | ~3,033 | **2,7372** | **~-0,296** |

⭐ **Antes do decaimento os dois sao o mesmo modelo, dentro de ±0,006** — o maior desvio
(0,0061) da a escala do ruido da amostra de 20 lotes. Sem esse controle, nada do que vem
depois seria interpretavel.

E o plato rende **zero**: 3,0397 no passo 183.000, 3,0331 no 222.000.

## O ganho do decaimento, medido

| fracao do decaimento | ganho em perplexidade |
|---:|---:|
| 9,3% | -6,2% |
| 33,3% | -12,0% |
| 49,8% | -14,8% |
| 85,0% | -22,6% |
| 99,2% | **-26,0%** |

⚠️ O ganho **desacelera ate a metade e volta a acelerar** — 0,17 pp por ponto de decaimento
ate 50%, 0,22 pp daí em diante. A queda final do LR carrega boa parte do efeito.

## O resultado, em bpb no holdout limpo

Mesmo parquet [40], 400 docs, sha256 `2273c5e4…9663e028c` — o mesmo texto que mediu a curva
do 150M. A ancora confere: 150M final medido agora = **0,8438** contra 0,844 registrado.

| modelo | tokens | tok/param | bpb |
|---|---:|---:|---:|
| Bee-350M @13B (1/3 do decaimento) | 13,00B | 38 | 0,8760 |
| **Bee-350M final (decaimento completo)** | **15,00B** | **43** | **0,8223** |
| Bee-150M final (ancora) | 21,75B | 143 | 0,8438 |

⭐⭐ **O 350M com 15B tokens bate o 150M com 21,75B por 2,57%** — 31% menos tokens, 3,3x
menos tokens por parametro, resultado melhor.

⭐ O decaimento sozinho, de 1/3 para completo, valeu **-6,13%** de bpb (0,8760 -> 0,8223).

## Os vereditos

1. 🔴 **A hipotese de subtreino esta morta.** Com 43 tok/param o 350M ja supera o 150M com
   143. Nesta faixa a escala paga mais que o volume de tokens.
2. 🔴 **Os marcos 1B/3B/6B/10B do 350M nao sao comparaveis com a curva do 150M.** Aquela
   tabela mede a diferenca entre dois *schedules*, nao entre dois modelos. Todo o
   desconforto de duas semanas com "a curva deteriora" era artefato de aparato.
3. ⚠️ **O alvo de bpb < 0,80 nao foi atingido pelo fork** (0,8223, faltaram 0,0223) — mas o
   fork nunca foi feito para isso: sao 15B contra os 21,75B do run principal. Quem responde
   ao gate e' o principal.
4. ⚠️ **Perplexidade plana no plato do WSD NAO e' saturacao.** O principal ficou 16 mil
   passos em 20,8-20,9 sem se mover. Nao abortar nem replanejar um run por causa disso.
5. ⚠️ **Lei `L(D)` ajustada sobre run com decaimento atribui a D o que e' do LR.** Ajustar
   so' sobre pontos do mesmo regime de LR.

## Custo

| | |
|---|---|
| fork | 21,98 h x US$ 1,02 = **US$ 22,4** |
| o que respondeu | uma hipotese registrada por escrito havia sete dias com a anotacao *"testar exigiria runs com schedules diferentes — caro"* |

⭐ A suposicao de que era caro foi o que a manteve sem teste.

## Reproducao

```bash
bash bee/rodar_fork_decaimento.sh          # exige checkpoint.pt em /workspace/bee-350m-fork
python bee/gate2_marcos.py --marcos /workspace/bee-350m-fork \
       --final /workspace/bee-350m-fork/modelo --so-marcos 13 --rivais ''
```

Artefatos: `gate2-fork-final.json`, `gate2-fork-13B.json`, `fork.log`, `historico.json` —
todos em `/workspace` do pod principal e no volume de rede do pod do fork (parado, nao
deletado).
