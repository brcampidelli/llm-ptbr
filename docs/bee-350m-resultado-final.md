# Bee-350M — o resultado final (2026-08-19)

> 115,48 h de RTX 5090, **US$ 117,8**. Mais o fork de decaimento (US$ 22,4): **US$ 140,2**.
> **bpb 0,8207.** O alvo declarado antes de gastar era 0,80 — **nao passou por 0,0207**.
> Mas o motivo NAO e' o que estava escrito no plano, e essa e' a parte que importa.

---

## Os numeros

Holdout limpo, parquet [40], 400 docs, sha256 `2273c5e4…9663e028c` — o mesmo texto de
sempre. Ancora: Bee-150M final remedido = **0,8438** contra 0,844 registrado.

| modelo | tokens | tok/param | bpb | regime de LR |
|---|---:|---:|---:|---|
| **Bee-350M final** | **21,75B** | **63** | **0,8207** | decaimento completo |
| Bee-350M @21B | 21,00B | 61 | 0,8376 | 82,8% do decaimento |
| Bee-150M final (ancora) | 21,75B | 143 | 0,8438 | cosine completo |
| Bee-350M @15B | 15,00B | 43 | 0,9167 | **plato** |
| Bee-350M @10B | 10,00B | 29 | 0,9195 | **plato** |
| Bee-350M @6B | 6,00B | 17 | 0,9261 | **plato** |
| Bee-350M @3B | 3,00B | 9 | 0,9385 | **plato** |
| Bee-350M @1B | 1,00B | 3 | 0,9745 | **plato** |

⚠️ Os marcos de 1B a 15B sao TODOS de plato (o decaimento so' comeca em 17,4B). Eles **nao
formam uma curva de scaling utilizavel** — ver `fork-decaimento-resultado.md`. Os seis
remedidos aqui batem com as medicoes anteriores, o que confirma que a regua e' reprodutivel.

⭐ O 350M bate o Bee-150M final por **2,76%** usando **3,3x menos tokens por parametro**.

---

## 🔴 O achado: os tokens pararam de pagar, a escala nao

O fork terminou em 15,00B com decaimento completo; o principal em 21,75B com o **mesmo
schedule proporcional**. Mesmo modelo, mesmo corpus, mesma forma de decaimento (20%):

| | tokens | bpb |
|---|---:|---:|
| fork | 15,00B | 0,8223 |
| principal | 21,75B | **0,8207** |
| **+45% de dado** | | **0,19% melhor** |

**Quarenta e cinco por cento mais dado renderam 0,19% de bpb.** Enquanto isso, ir de 151M
para 345M parametros rendeu **2,76%**.

🔴 **Isso refuta a leitura registrada no plano.** Estava escrito: *"se o 350M nao passar de
0,80, a conclusao e' que o corpus (nao a escala) e' o gargalo"*. O gate de fato nao passou —
mas a explicacao esta errada. Nao falta corpus: mais 6,75B do mesmo corpus moveu quase nada.
O que continua pagando e' **escala**.

⚠️ O que isto NAO diz: nao diz que corpus melhor nao ajudaria. Diz que **mais corpus do
mesmo tipo** nao ajuda. Qualidade e diversidade sao outra variavel, nao medida aqui.

---

## Consequencias para o proximo degrau

1. **Nao expandir o corpus.** Ja havia sido refutado por [[bee-350m-nao-expandir-corpus]] e
   pelo censo de repeticao; agora esta medido no ponto final: o volume saturou.
2. **O proximo degrau e' escala**, nao dado. Para tirar os 2,5% que faltam ate 0,80, o
   caminho medido e' mais parametros — 151M→345M ja rendeu 2,76%.
3. **~43 tok/param basta** nesta arquitetura. O 350M com 43 ja estava a 0,19% do que teve com
   63. Isso corta drasticamente o orcamento de dados do proximo modelo.
4. ⚠️ **Nunca dimensionar por numero de plato.** O @15B mede 0,9167 e o mesmo modelo decaido
   mede 0,8223 — 10,3% de diferenca. Uma decisao tomada no plato olha para um modelo que
   ainda nao assentou.

---

## Custo

| | horas | US$ |
|---|---:|---:|
| run principal (21,75B) | 115,48 | 117,8 |
| fork de decaimento (15,00B) | 21,98 | 22,4 |
| **total** | **137,5** | **140,2** |

Teto autorizado: US$ 300. Gasto: 47% dele.

---

## O que fica aberto

- **bpb mede o modelo BASE.** Fluencia de resposta e uso de ferramenta so' se medem pos-SFT,
  por execucao (`comeia/eval/eval_agentic_exec.py`).
- Comparacao com **SmolLM2-360M** e **Qwen3-0.6B** — rodada separada.
- O modelo final esta em `/workspace/bee-350m/modelo` (volume de rede, sobrevive ao pod).
