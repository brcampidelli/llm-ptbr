# O catálogo separava chamar de recusar — e o modelo aprendeu a contar

> **2026-08-25.** US$ 0. Ampliar o instrumento revelou que **duas afirmações de destaque deste
> projeto eram sobre a construção do corpus, não sobre o modelo**. O conserto é de dado, custou
> 89 min de GPU por semente, e move o desempenho real de 24,5% para 54,3%.

---

## 1. O achado

O corpus deu ao modelo **dois atalhos perfeitamente preditivos**:

| atalho | no treino do e8 |
|---|---|
| **tamanho** do catálogo | positivos 1–2 ferramentas · negativos 6 · **sobreposição 0 de 12.011** |
| **posição** da correta | primeira em **1.617 de 1.617** |

Ele aprendeu os dois. Medido no holdout balanceado, o e8 emite chamada assim:

| catálogo | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|
| **e8 emite** | 100% | 100% | 87% | **9%** | **0%** | **0%** |

**O limiar está exatamente entre 3 e 4.** Não é dificuldade crescente — é uma regra de contagem.

E o teste que isola a posição: reordenar duas ferramentas no catálogo, **sem mudar mais nada**,
leva o acerto de **100,0% para 0,0%** (quebrou 44, consertou 0, p = 0,0000), enquanto os 388
casos não tocados ficam bit a bit idênticos.

---

## 2. ⚠️ Duas afirmações minhas que isto retira

1. **"A seleção de ferramenta generaliza — 96,9% em ferramentas nunca vistas."** Medida onde
   **77% dos casos tinham UMA ferramenta** no catálogo. Emitir a única presente não é
   selecionar.
2. **"Over-calling 0,0%."** Todo negativo tinha 6 ferramentas; o modelo recusa tudo com 6; logo
   zero **por construção**. Nunca foi calibração. Com o catálogo balanceado, o mesmo modelo
   marca **50,5%**.

⚠️ **O holdout herdava a mesma construção** (positivos 1–2, negativos 6, sobreposição 0%), então
a régua **não tinha como mostrar isso**. Foi preciso construir a variante que ela não continha —
e é por isso que ampliar o instrumento vinha antes de mexer no modelo.

✅ **O que sobrevive:** a restrição ao esquema (+16,4 pp, +144/−0). Foi medida pareada dentro do
mesmo regime de catálogo e mede outra coisa — o nome do argumento.

---

## 3. O conserto

`balancear_catalogo.py` sorteia N ∈ {1..6} da **mesma distribuição** para as duas classes.

- **negativo**: apenas **subamostra** das 6 que já tinha. Elas são verificadamente incapazes de
  atender o pedido, logo qualquer subconjunto também é. 🔴 Adicionar distrator a um negativo
  poderia trazer uma ferramenta que **atende** — eu fabricaria negativos falsos.
- **positivo**: a correta + distratores de raiz semântica diferente, em posição sorteada.

**Guardas, todas verificadas antes de treinar:**

```
positivos {1:1274, 2:1167, 3:1237, 4:1265, 5:1242, 6:1209}
negativos {1: 811, 2: 752, 3: 776, 4: 721, 5: 763, 6: 794}
melhor regra "chame se n<=k": 61,6%  ·  chutar a classe maior: 61,6%   [OK]
posição da correta: 1ª em 28,4% · esperado se aleatório 28,8%          [OK]
0 exemplos acima de 2048 tokens (nenhum descartado em silêncio)        [OK]
```

Custo: **360 → 380 tokens por exemplo (+5,6%)** — os negativos encolheram enquanto os positivos
cresceram.

---

## 4. O resultado

**Holdout balanceado (n=440), duas sementes:**

| modelo | ferramenta | executou | over-calling |
|---|---:|---:|---:|
| e8 | 29,3% | 24,5% | 50,5% |
| e11 s42 | 77,0% | 54,5% | 13,5% |
| e11 s43 | 71,4% | 54,1% | 13,2% |
| **média** | **74,2%** | **54,3%** | **13,3%** |
| amplitude entre sementes | 5,7 pp | 0,5 pp | |

Pareado contra o e8: **+178/−46** (s42) e **+171/−41** (s43), **p ≈ 1e-19** nos dois.

**Os dois atalhos morreram:**

| | e8 | e11 s42 | e11 s43 |
|---|---:|---:|---:|
| amplitude de emissão, catálogo 1 → 6 | **100 pp** | 5 pp | 7 pp |
| amplitude de acerto, posição 1ª → 6ª | **60 pp** | 17 pp | 18 pp |

---

## 5. ⭐ A tabela que resume tudo

| modelo | holdout **balanceado** | holdout **antigo** | oscilação |
|---|---:|---:|---:|
| e8 | 24,5% | **85,5%** | **61,0 pp** |
| **e11** | **54,3%** | 59,0% | **4,7 pp** |

E o over-calling: e8 oscila de **0,0% a 50,5%**; e11 fica em **13,3% / 13,7%**.

**A distância entre as duas réguas É o atalho.** Um modelo que faz a tarefa desempenha parecido
nas duas; um que aprendeu a construção do corpus desempenha conforme a construção.

⚠️ **O e11 é pior no holdout antigo (85,5% → 59,0%), e isso não é regressão** — aquele holdout
premia o atalho, e o e8 o explora perfeitamente. Mas registro o número, porque quem só olhar a
régua antiga vai ver uma piora de 26 pp.

---

## 6. O que fica

1. ⚠️ **54,3% não é bom.** O conserto não melhorou o modelo: ele **revelou** o desempenho real,
   que estava escondido atrás de duas correlações espúrias. Agora há um alvo mensurável.
2. ⚠️ **Ganhou 178 e perdeu 46.** O e11 não domina o e8 caso a caso; reportar só a folga
   esconderia isso.
3. ⚠️ **Amplitude de semente em `ferramenta`: 5,7 pp.** É o piso que qualquer comparação futura
   nesta métrica tem de respeitar. `exec` está em 0,5 pp.
4. ⚠️ **Catálogo acima de 6 continua fora da distribuição de treino** (os negativos só podem ser
   subamostrados). `cat10`/`cat15` medem extrapolação.
5. ⭐ **A regra de método:** quando duas classes de exemplo são geradas por processos diferentes,
   medir se alguma característica **superficial** as separa — antes de treinar. Aqui, contar
   linhas do catálogo bastava, e nenhum erro apareceu em lugar nenhum.
