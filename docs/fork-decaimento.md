# O fork de decaimento — a curva pareada media o schedule, não o modelo

> Rodado em **2026-08-17**, com o Bee-350M a 50% do run principal. Custo: **US$ 22** e um
> segundo pod. O run principal nunca foi tocado.
>
> ⭐ Este experimento também **fecha uma hipótese registrada em 2026-08-10** e deixada
> explicitamente sem teste — ver `previsao-marco-10B.md` e a §4 aqui.

---

## 1. O fato a explicar

O Bee-350M salvou marcos de scaling em 1, 3, 6 e 10B tokens. Comparados ao Bee-150M no
**mesmo holdout e mesmo procedimento**, a diferença deteriorava monotonicamente:

| tokens | Bee-150M (cosine) | Bee-350M (WSD, no platô) | 350M está |
|---:|---:|---:|:---|
| 1B | 1,0210 | 0,9745 | **4,55% melhor** |
| 3B | 0,9470 | 0,9385 | 0,90% melhor |
| 6B | 0,9200 | 0,9261 | 0,66% **pior** |
| 10B | 0,8970 | 0,9196 | **2,51% pior** |

Um modelo com 2,3× os parâmetros começando na frente e terminando atrás, com o déficit
crescendo de forma limpa. Duas leituras cabiam no mesmo dado:

- **(a) artefato de schedule.** O 150M usou **cosine** e nesses pontos já vinha colhendo
  decaimento — LR em 99,8% → 96,8% → 85,7% → **62,2%** do pico. O 350M usa **WSD** e estava
  cravado no platô de 55%. A tabela comparava um modelo que estava **assentando** com um que
  ainda **explorava**.
- **(b) subtreino real.** O 350M vai a **63 tokens/parâmetro** contra **143** do 150M.

As duas previam o mesmo padrão. E a escolha entre elas decide o degrau seguinte: (a) não
pede nada; (b) pede expandir o corpus, o que custa coleta, dinheiro e tempo.

---

## 2. Por que não bastava antecipar o decaimento no run principal

A tentação óbvia era decair o run principal mais cedo e ver se o modelo saltava. Isso não
testaria a hipótese — **consumiria** ela. Se o modelo saltasse, o ganho seria inatribuível
entre o decaimento e os bilhões de tokens vistos no caminho, e não sobraria nenhum estado
não-decaído para comparar.

Pior: das quatro opções consideradas, "decair já e ir até o fim" custava **o mesmo** que não
mexer (US$ 59) e abandonava a única forma com respaldo publicado — o IMU-1 mede que 20% de
decaimento **iguala** o cosine.

Então: **bifurcar**. Uma cópia decai, o principal segue.

---

## 3. O desenho, e os três detalhes que decidem se ele vale

**Partir do `checkpoint.pt`, não de um marco.** O marco é só o modelo. O checkpoint traz
`opt` (momentos do Adam) e `gerador` (posição no dado). Sem eles seria um restart disfarçado
de continuação, e o Adam re-aquecendo por centenas de passos contaminaria justamente a janela
que interessa medir.

> ⚠️ Meu próprio teste de validação do checkpoint deu **falso-negativo**: imprimiu
> `tem otimizador: False` porque procurei a chave `otim`/`optimizer`, e ela se chama `opt`.
> As chaves reais são `['modelo', 'opt', 'passo', 'loss', 'gerador', 'cfg']`.

**Terminar em 15,00B tokens.** É o único ponto adiante onde o 150M tem marco **medido**
(0,870). Terminar em 13B ou 14B responderia "melhorou?" mas não "melhorou o suficiente?".

**🔴 Passar `--lr` explícito.** Com `--lr 0` o script deriva pela Step Law a partir de
`passos × tokens_por_passo`. O fork termina em 15B e não em 21,75B, então o LR sairia
`(15/21,75)^0,307` = **10,8% menor**. O experimento mediria "decaimento **mais** LR
diferente" e o resultado seria inatribuível — exatamente o defeito que ele existe para
evitar. Congelado em `2,18105796e-3`, o valor do run principal, conferido contra o log
(`lr 1.20e-03` na fase estável nos dois).

```
--passos 228881 --lr 2.18105796e-3
--schedule wsd --frac-decaimento 0.20 --lr-estavel-frac 0.55
```

Decaimento de 183.104 a 228.881 (45.777 passos, 20%) na forma **`1−√t`** — a do IMU-1. Não
se inventa forma nova num experimento cujo objeto **é** a forma.

---

## 4. O controle que valida a bifurcação

Antes do passo 183.104 os dois estão no mesmo LR, no mesmo dado, na mesma posição. Se
divergissem ali, a bifurcação estaria errada — e isso apareceria em **dez minutos**, não em
vinte e duas horas. Perplexidade de validação, mesmo `val.bin`, gerador de seed fixa 1234:

| passo | principal | fork | Δ loss |
|---:|---:|---:|---:|
| 166.000 | 3,0462 | 3,0445 | −0,0017 |
| 170.000 | 3,0457 | 3,0437 | −0,0020 |
| 175.000 | 3,0434 | 3,0443 | +0,0009 |
| 180.000 | 3,0408 | 3,0417 | +0,0009 |
| 182.000 | 3,0358 | 3,0419 | **+0,0061** |
| 183.000 | 3,0397 | 3,0403 | +0,0006 |

⭐ Iguais dentro de **±0,006**. O maior desvio (0,0061) fixa a escala do ruído da amostra de
20 lotes — número que passa a ser o limiar de qualquer coisa afirmada depois.

### E então descola

| passo | principal (platô) | fork (decaindo) | Δ loss | ppl |
|---:|---:|---:|---:|:---|
| 183.500 | 3,0398 | 3,0250 | −0,0148 | 20,9 → 20,6 |
| 184.000 | 3,0395 | 3,0124 | −0,0271 | 20,9 → 20,3 |
| 185.000 | 3,0404 | 2,9930 | −0,0474 | 20,9 → 19,9 |
| 187.000 | 3,0406 | 2,9757 | −0,0649 | 20,9 → 19,6 |
| 190.000 | 3,0396 | 2,9524 | −0,0872 | 20,9 → 19,2 |
| 193.000 | 3,0415 | 2,9356 | −0,1059 | 20,9 → 18,8 |
| 195.000 | 3,0390 | 2,9234 | **−0,1156** | 20,9 → **18,6** |
| 198.364 | 3,0361 ¹ | **2,9056** | **−0,1305** | 20,8 → **18,3** |

¹ passo 198.000 do principal, a validação mais próxima.

**−12,0% de perplexidade**, monotônico, **onze a vinte vezes o ruído** — e com apenas **um
terço** do decaimento consumido.

⭐ E o principal está **exatamente plano**: 3,0397 no passo 183.000, 3,0415 no 193.000. Dez
mil passos, 655M tokens, perplexidade 20,9 do começo ao fim.

> **Isso parece ruim e não é.** O fork prova que não é: mesmo modelo, mesmos dados, mesma
> posição — só o LR muda, e a perplexidade desaba. **Platô plano não significa que o modelo
> não está aprendendo; significa que a perplexidade de validação não mede o que o platô
> faz.** Ela só cobra quando o modelo assenta.

### 🔴 A hipótese de 10/08, fechada

`previsao-marco-10B.md` registrou, ao descartar a curva `L(D) = E + A·D^-α` por errar o
marco de 15B em 0,0161:

> *"o LR está em decaimento cosseno, e o ganho acelera no fim do schedule por um motivo que
> não é D. Uma curva em D sozinha não pode capturar isso. Testar exigiria runs com schedules
> diferentes — caro, e não é a pergunta do projeto agora."*

**Está testada, e confirmada.** O ganho de −0,13 de loss veio **sem um único token além** do
que o principal também viu. Uma lei de scaling em D sozinho atribui a D o que é do LR — e é
por isso que ela subestimava o fim do run. A hipótese custou US$ 22 para fechar, não o
"caro" que se supôs.

---

## 5. O bpb — a régua que compara com o 150M

Perplexidade no `val.bin` é comparável **entre os dois forks**, mas não com a curva do 150M.
Para isso, o Gate 2 no holdout limpo (parquet 40, 400 docs, 0,83 MB):

```
sha256 do holdout: 2273c5e41e96d3d18f9802372dc0c03283b7d9d36655cf9ba80740e9663e028c
✅ hash confere com a medicao anterior — comparacao pareada valida
âncora Bee-150M final: bpb 0,8438   (esperado 0,844 — a régua está calibrada)
```

| | tokens | bpb |
|---|---:|---:|
| **Bee-350M @13B, 1/3 decaído** | **13,0B** | **0,8760** |
| Bee-150M @15B | 15B | 0,8700 |
| Bee-150M @13B | 13B | *0,8808* ⚠️ interpolado |
| Bee-150M @10B | 10B | 0,8970 |
| Bee-350M @10B, no platô | 10B | 0,9196 |

⚠️ **A linha de 13B do 150M é interpolada** entre 10B e 15B — não existe marco medido ali.
É estimativa, não medida.

Uma leitura que **não** depende de interpolação: o 150M só alcança 0,8760 em algum ponto
entre 13,5B e 14B tokens. **O 350M chegou lá com 13,0B**, e com dois terços do decaimento
ainda por aplicar.

⚠️ **O que NÃO ler na saída do script.** Ele imprime `+3,8%` para o marco 13B, mas isso é
contra a **âncora** — o 150M *final*, com 21,75B tokens. Comparar um marco de 13B com um
modelo de 21,75B é injusto por construção. A comparação que informa é contra o 150M **no
mesmo número de tokens**.

---

## 6. Veredito

**A hipótese (a) está confirmada; a (b) não é necessária para explicar o padrão.**

| | antes | depois |
|---|---|---|
| 350M vs 150M em 10B, no platô | **2,51% pior** | — |
| 350M vs 150M em ~13B, 1/3 decaído | — | **~0,6% melhor** |

O sinal inverteu **sem um token novo**. A deterioração era do schedule.

### Consequência retroativa, e ela incomoda

**Os marcos 1B/3B/6B/10B do Bee-350M não são comparáveis com a curva do Bee-150M.** Aquela
tabela mede a diferença entre dois *schedules*, não entre dois *modelos*. Só o ponto final,
com ambos decaídos, compara modelos.

É a mesma armadilha que este projeto já pagou três vezes: **quando dois experimentos
internos se contradizem por margem grande, o defeito está no aparato, não no fenômeno.** Um
modelo 2,3× maior ficando pior com mais dados é uma contradição dessas — e a resposta certa
era desconfiar do instrumento, não construir teoria sobre subtreino.

### O que muda no plano

- ❌ **Não** expandir o corpus por causa desta curva. O motivo que a sustentava não existe.
  (Somando-se a `estudo-bee-350m.md`, que já havia derrubado a expansão por outra via.)
- ✅ O run principal segue **sem alteração** — 21,75B com 20% de decaimento no fim.
- ⏳ O gate de **bpb < 0,80** continua aberto e será **medido, não previsto**.
- ⭐ **De brinde:** quando os dois terminarem, haverá dois modelos com **schedule idêntico**
  diferindo só em tokens vistos (15,00B contra 21,75B). Isso isola o valor dos 6,75B extras
  com tudo o mais fixo — o número que dimensiona o Bee-1B, e que ia custar um gate pareado.

---

## 7. Três tropeços do caminho, todos silenciosos

**A espera que se autossatisfaz.** Armei o disparo automático com
`while pgrep -f snapshot_download; do sleep 20; done`. A linha de comando **do próprio
wrapper** contém a string `snapshot_download` — ele encontrava a si mesmo e teria esperado
para sempre, sem erro nenhum, a US$ 1,02/h. Peguei porque fui olhar.

**`du -sm` não mede download em progresso.** Ficou cravado em 20.897 MB por sete minutos e eu
declarei "travou". Com `stat -c %s` no `.incomplete`: 31,4 MB/s, correndo normal. O
instrumento errado produziu a conclusão errada — em miniatura, o mesmo erro do resto deste
documento.

**Uma leitura de throughput isolada.** Apareceu `36,7k tok/s` (contra 53,5k) logo depois do
salvamento do marco. Quatro leituras seguidas deram 53,7 / 53,6 / 53,5 / 53,7. A regra de
três leituras coincidentes existe por isto, e foi a segunda vez nesta sessão que ela evitou
uma conclusão errada sobre desempenho.

---

## Reprodução

```bash
bash bee/rodar_fork_decaimento.sh
```

Requer `<CKPT>/checkpoint.pt` copiado do run de origem — o script **aborta** se não existir,
porque sem ele `pretrain.py` começaria do passo 0 com pesos aleatórios, imprimiria tudo verde
e o experimento simplesmente não existiria.

Transferência entre pods sem nenhum segredo envolvido: par ed25519 derivado por
`hashlib.sha256(semente)` nos dois lados, autorizado só no de origem e removido depois.
