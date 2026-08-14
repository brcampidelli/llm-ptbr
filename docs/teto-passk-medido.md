# O "teto" de pass@k — medido, e não era onde ninguém disse (2026-08-14)

> **Custo: US$ 0.** Duas corridas de inferência na RTX 5070 local (~3 h) e uma auditoria de
> corpus em CPU (42 min). Nenhum treino, nenhuma GPU alugada.
>
> Resultado: **três afirmações caíram** — uma minha, uma da refutação adversarial do
> [estudo](estudo-bee-350m.md), e uma de um paper. E a lei que o projeto tinha medido sozinho
> ficou de pé, com a demonstração mais limpa que este repositório produziu.

---

## Parte I — A auditoria do corpus: o item de maior ROI do estudo não existia

O [estudo](estudo-bee-350m.md) §1.1 colocou como **primeira ação, bloqueante**, auditar
repetição interna do corpus. A justificativa: arXiv:2606.24998, medido em **344M** — o tamanho
exato do Bee-350M — mede que **10% dos FLOPs em documentos repetidos equivale a perder 33% da
computação**. Com US$ 300 de orçamento, valeria até US$ 100.

`bee/auditar_repeticao.py` fez o **censo** dos 21,75B tokens (não amostra — o `train.bin` que o
treino vai consumir), 27,46M documentos:

| | tokens | % dos FLOPs |
|---|---:|---:|
| documentos únicos | 21.660.374.737 | **99,715%** |
| duplicata **exata** (≥2 ocorrências) | 58.924 | **0,000%** |
| quase-dup, faixa **3–10×** ⚠️ *o pico do dano* | 3.501.686 | **0,016%** |
| quase-dup total (≥2) | 61.856.151 | **0,28%** |

**O corpus está limpo.** O cenário do paper exige **36× mais repetição** do que temos. O
`fineweb-2` já aplica dedup MinHash por dump na origem, e a nossa junção não reintroduziu nada.

⚠️ **Ressalva honesta:** a camada exata é exata (hash da sequência inteira). A camada de
quase-duplicata usa bottom-16 MinHash com 4 bandas × 4, cuja probabilidade de detecção em
Jaccard 0,80 é ~88% — a taxa real seria ~0,32%, não 0,28%. Duas ordens de grandeza abaixo do
limiar de dano: o veredito não muda.

⭐ **Consequência para o orçamento:** os "até US$ 100 recuperáveis" **não existem**. A conta do
Bee-350M volta a ser a conta simples. E isso é um resultado *valioso*: custou US$ 0 descobrir
que um esforço de deduplicação renderia zero.

**A guarda que se pagou:** o censo confere que `tokens_em_documentos + separadores == tamanho do
arquivo`. Erro medido: **0,0000%**. Um censo que perde documento não é censo.

---

## Parte II — O holdout tinha um teto próprio, e ninguém tinha medido

`comeia/eval/auditar_holdout.py` testa cada um dos 85 exemplos `tool` por **perturbação**, não
por leitura: perturba um argumento e vê se o executor ainda aceita.

| teste | itens | o que significa |
|---|---:|---|
| gabarito não executa | **0/85** | ✅ o executor está são |
| **(A)** exige a **string literal** | 7 (8,2%) | argumento de texto livre não derivável nem copiável |
| **(B)** exige info que o usuário **nunca deu** | 8 (9,4%) | o gabarito inventou um valor |
| ⚠️ **impossível por construção (A ∪ B)** | **10 (11,8%)** | |

> **Teto máximo alcançável por qualquer modelo neste holdout: 88,2%.**

### ⭐ A auditoria validou-se contra o comportamento medido

Dos **10** itens marcados impossíveis, o modelo nunca resolveu **exatamente esses 10** em 128
amostras. **Zero falso positivo.**

E chegou lá por correção: a v1 da regra marcou **15**, e a curva de pass@k denunciou **2** deles
— o modelo acertou 96/128 num item cuja query era *"filmes em cartaz Brasília hoje"*, trecho
**literal** de *"Quais são os filmes em cartaz nos cinemas de Brasília hoje?"*. Copiar é
aprendível. A regra (A) passou a exigir que a string **não seja subsequência ordenada do
pedido**, e os 3 restantes caíram por outros refinamentos.

⭐ **A lição:** a auditoria estática e a medição empírica se corrigiram **mutuamente**. Nenhuma
das duas sozinha teria chegado ao número certo.

### ⚠️ Um problema de licença, achado de passagem

Um exemplo de `write_file` do holdout tem a **letra completa de "Imagine" (John Lennon)** como
argumento `content`, e o gabarito exige reproduzi-la literalmente. É item impossível **e**
material protegido num dataset candidato a publicação. **Precisa sair** — ver
[Pendências](#pendências).

---

## Parte III — A curva de pass@k, com k até 128

`comeia/eval/eval_passk_curva.py`, n=128 amostras por exemplo, T=0,8, estimador **não-viesado**
do Codex (`1 - C(n-c,k)/C(n,k)`) — uma corrida, a curva inteira. Rodar cada k separadamente daria
degraus de ruído que não existem.

**Nos 75 exemplos possíveis** (85 − 10 impossíveis):

| k | base *(pré-colheita)* | **v2** *(pós-colheita)* | delta |
|---:|---:|---:|---:|
| 1 | 59,1% | **64,1%** | **+5,07 pp** |
| 2 | 67,0% | 70,7% | +3,71 pp |
| 4 | 73,2% | 75,6% | +2,41 pp |
| 8 | 78,2% | 79,2% | +1,00 pp |
| 16 | 81,7% | 81,8% | +0,08 pp |
| 32 | 83,9% | 83,7% | −0,22 pp |
| 64 | 85,0% | 84,9% | −0,06 pp |
| **128** | **85,3%** | **85,3%** | **+0,00 pp** |

---

## Parte IV — Os três vereditos

### 1. 🔴 Minha afirmação: "72,9% é o teto" — **errada**, por dois defeitos somados

O número estava deprimido por **11,8% de itens impossíveis**, e **k=16 não era o fim da curva**
(81,8% → 85,3% entre k=16 e k=128 nos possíveis). **O teto real é 85,3%.**

### 2. 🔴 A refutação adversarial: "a curva sobe log-linear, tire 'teto' do vocabulário" — **errada**

A refutação citou *Large Language Monkeys* (Pythia-160M indo de 0,27% a 57% entre k=1 e k=10⁴) e
concluiu que declarar teto em k=16 era ler o aparato. Meio certa: k=16 era cedo. Mas a previsão
forte não se sustenta — **a curva achata**: **+0,43 pp no último degrau**. Existe teto.

⚠️ **Por que provavelmente diverge do paper:** em tool-use com verificador determinístico o
espaço de respostas certas é minúsculo comparado a matemática aberta. O achatamento pode ser
propriedade **da tarefa**, não da escala. **Não extrapolo para o 350M.**

### 3. 🔴 O paper do esquecimento (arXiv:2608.11829) — **não se reproduziu**

Ele mede que a auto-melhoria torna insolúveis mais problemas do que resolve. O diff por problema:

| | |
|---|---:|
| resolvia e resolve | 63/85 |
| ⭐ **aprendeu** (só depois) | **1** |
| 🔴 **esqueceu** (só antes) | **2** |
| nunca resolveu | 19/85 |

**McNemar exato: 3 pares discordantes, p = 1,000.** Ruído puro.

⭐ **E aqui eu quase repeti o erro que este projeto mais paga.** Meu `diff_por_problema.py`
imprimiu **"🔴 ESQUECEU MAIS DO QUE APRENDEU"** com 2 contra 1 — contando a direção sem testar a
magnitude, exatamente como o critério de veredito multiplicativo que já declarou "não há cauda"
havendo cauda. O script agora exige **significância** antes de concluir.

### 4. ✅ A lei do projeto — **confirmada, em forma de livro-texto**

> *"O rejection sampling move o **piso** rumo ao teto e **não move o teto**."*

O ganho decai **monotonicamente** de +5,07 pp em k=1 a **exatamente +0,00 pp** em k=128. Não é
interpretação — é a coluna de delta convergindo a zero.

---

## O que a colheita simétrica realmente entregou

| | base | **v2** |
|---|---:|---:|
| pass@1 (possíveis) | 59,1% | **64,1%** |
| taxa média por amostra | 59,1% | **64,1%** (+5,1 pp) |
| over-calling (**1.040** amostras) | 19,4% | **16,5%** |
| conjunto de resolvíveis | 65 | 64 *(p=1,000)* |

Entre os problemas que ambos resolvem: **+6,0 pp** de taxa (subiu em 28, caiu em 15).

⭐ **O over-calling de 21,5% que o projeto reportava vinha de UMA amostra por exemplo.** Medido
em 1.040 amostras, é **16,5%**. O número antigo não estava errado — estava sem precisão.

---

## ⭐ A folga colhível é MAIOR do que o projeto acreditava

| | antes (crença) | **medido** |
|---|---:|---:|
| pass@1 | 57,6% | **64,1%** |
| teto | 72,9% | **85,3%** |
| **folga aproveitável** | 15,3 pp | **21,2 pp** |

O autoaprendizado tem **mais** espaço, não menos — e agora se sabe exatamente onde ele para.

---

## Quatro vezes em que a medição de desempenho mentiu, no mesmo dia

Todas "corretas" no próprio contexto, todas erradas para a decisão:

| leitura | ms/amostra | por quê |
|---|---:|---|
| prompt de brinquedo, lote 64 | 109 | prompt curto, sem contenção |
| durante a auditoria de corpus | **3.865** | geração de modelo pequeno é **CPU-bound**; a auditoria comia a CPU |
| lote 32, CPU livre | 192 | ✅ o número real |
| após ~500 chamadas de `generate` | **parou** | fragmentação do alocador → 7.766 de 8.151 MiB |

⭐ **A fragmentação é o caso mais traiçoeiro** porque o sintoma **não é OOM, é lentidão**: 100%
de utilização de GPU com **35 W** de potência. Correção: `torch.cuda.empty_cache()` entre
exemplos (`expandable_segments` **não funciona no Windows** — o log avisa) e **VRAM impressa na
linha de progresso**, para ver o vazamento em vez de deduzir. Depois: `297/330 MiB` cravado do
primeiro ao último exemplo, 59 W.

---

## Reprodução

```bash
python bee/auditar_repeticao.py                     # censo do corpus, ~42 min de CPU
python comeia/eval/auditar_holdout.py               # teto do benchmark, segundos
python comeia/eval/eval_passk_curva.py --model models/ab_sim  --n 128 --lote 32 --tag v2_n128
python comeia/eval/eval_passk_curva.py --model models/ab_base --n 128 --lote 32 --tag base_n128
python comeia/eval/diff_por_problema.py --antes ...base_n128.json --depois ...v2_n128.json
```

## Pendências

- 🔴 **Remover a letra de "Imagine" do holdout** — item impossível *e* material protegido.
- 🟡 **Corrigir os 10 impossíveis** (ou marcá-los como não pontuáveis): sem isso toda métrica
  agêntica do projeto fica ~12 pp abaixo do real, para sempre.
- 🟡 `eval_passk_curva.py` **não salva parcial**. Numa corrida de 2,7 h, uma interrupção perde
  tudo — a mesma razão pela qual o estudo recomenda schedule *horizon-free* no treino.
- 🟢 T3 (varredura de temperatura/sampler) não foi rodado. Com o teto agora conhecido, ele diz
  quanto do gap de 21,2 pp é do **decodificador** e não do modelo.
