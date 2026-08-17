# Lições de método — o que este projeto pagou para aprender

> **Leia antes de treinar qualquer Bee novo.** Este documento existe porque os erros mais
> caros deste projeto **não deram erro**: a loss caía, o log parecia saudável, e o defeito só
> apareceu ao comparar com algo externo — às vezes semanas depois.
>
> Complementa `licoes-pretreino.md` (detalhe do pré-treino), `agentico-medicao.md` (medição
> agêntica) e `sft-resultado.md` (SFT). Aqui está o que atravessa todos eles.

---

## Parte I — A família que custou mais caro: **dado sumindo em silêncio**

Três ocorrências, três causas diferentes, **o mesmo modo de falha**. Nunca tinham sido postas
lado a lado, e é justamente a comparação que revela o padrão.

| # | onde | o que sumiu | como se manifestou |
|---|---|---|---|
| 1 | pré-treino | o **objetivo** (previa t+2 em vez de t+1) | loss caindo normalmente por 2 semanas |
| 2 | pré-treino | **37% do corpus** nunca entrou | nada; a cobertura não era reportada |
| 3 | SFT | **100% dos exemplos agênticos** | treino rodou 354 passos em vez de 447 |

### 1. Deslocamento duplo de rótulos — 2 semanas, ~US$ 34

`LlamaForCausalLM.forward(labels=L)` desloca **por dentro**. Passar um `y` já deslocado
desloca duas vezes.

```python
perda = modelo(input_ids=x, labels=y).loss   # ❌ treina para prever t+2
perda = modelo(input_ids=x, labels=x).loss   # ✅ o rótulo é o PRÓPRIO input
```

**Por que não deu erro:** a validação usava a mesma convenção errada. Perplexidade caiu 77→63
e o treino parecia saudável do início ao fim.

**Como foi pego:** `gate_pareado.py` usava `labels=x` (correto) e, com **75× menos dados**,
media bpb **40% melhor**. Setenta e cinco vezes mais dado produzindo resultado pior é
impossível — mas foram construídas cinco hipóteses elaboradas antes de alguém ler a
impossibilidade.

**Custo medido:** bpb 2,218 → **1,021**, com 10× menos dados.

**Guarda:** `conferir_convencao_de_rotulos()` roda antes do passo 1 e **aborta**. ⚠️ Com dado
de treino **real** — com tokens aleatórios a diferença cai de 1,85 para 0,0074 e a guarda não
dispara: um teste que passa sem testar nada.

### 2. Amostragem com reposição — 37% do corpus

`torch.randint` a cada passo amostra **com reposição**: a cobertura tende a `1 − 1/e = 63,2%`.
Medido: 63,5%. De 9,87B tokens, **~3,6B nunca entraram**.

**Guarda:** `AmostradorPermutado` percorre blocos permutados até o fim; cobertura reportada no
log e conferida contra 100%.

### 3. `max_seq_len` curto no SFT — 100% do agêntico

O prompt agêntico tem 1.096–1.191 tokens só no catálogo de ferramentas; o default era 1.024.
Quando o prompt sozinho estoura o limite, a *completion* é truncada fora, o exemplo fica
**inteiramente mascarado** e o TRL o descarta **sem erro**.

**Como foi pego:** contando passos. Previu ~447, executou **354** = 79,2%. E 1.495/7.152 =
**20,9%**. Bate na casa decimal.

**Guarda:** `sft.py` **aborta** se >1% do dataset for descartado por truncamento.

### ⭐ A regra que sai dos três

> **Se um dado novo entra e a métrica não se move, a primeira hipótese é que ele não entrou —
> não que "não ajudou".**

E o corolário operacional: **conte os passos**. O número de passos executados contra o
previsto é o detector mais barato que existe para dado que sumiu.

---

## Parte II — O instrumento mente antes do fenômeno

**Seis** ocorrências em que o **aparato** — avaliador, guarda, cronômetro, schedule — estava errado
e quase produziu decisão de produto. É a família mais numerosa do projeto, e a mais barata de
evitar.

> ⭐ **O princípio comum:** quando dois experimentos internos se contradizem por uma margem
> absurda, o defeito está **no aparato, não no fenômeno**. Investigar a contradição ANTES de
> construir teoria em cima dela.

### 4. Avaliador com mundo fechado — 23,5% que não existiam

O executor determinístico foi escrito com um mundo **fechado**: 6 cidades, 5 tickers, 3
arquivos. O holdout usa o mundo real — Brasília, `/var/log/syslog`, `ABEV3`. Resultado: **35
dos 85 exemplos eram impossíveis de acertar por construção**, porque a própria chamada de
*referência* falhava. Taxa medida: 23,5%. Taxa real: **57,6%**.

**Como foi pego:** implausibilidade. `read_file` 0/10 e `list_dir` 0/10 — zero absoluto em
ferramenta simples, num modelo que fazia 91% em `get_weather`.

**Guardas:** mundo simulado **aberto e determinístico** (hash da entrada normalizada), nunca
lista branca; e uma guarda que **executa todas as referências antes de carregar qualquer
modelo** — se o gabarito não roda, o avaliador está errado. Ela se pagou na primeira
execução, pegando `sqrt()` faltando na calculadora.

### 5. Critério de veredito multiplicativo

O código imprimiu **"NÃO há cauda útil"** para `pass@1` 52,3% → `pass@16` 72,9%. A condição
era `pass@k > pass@1 × 1,5` — critério **multiplicativo**, que com `pass@1` alto exige 78,6%,
quase o teto. Ele pune justamente o modelo que já vai bem.

**Guarda:** folga **absoluta** (≥5 pp) somada à fração do espaço restante capturada (≥15%).

⚠️ **A lição real:** repassar veredito impresso por código sem conferir contra os números
crus teria fechado uma porta que estava aberta.

---

### 6. Guarda fora do fluxo não guarda nada — o campo era `tool_call`, não `tool`

A guarda de gabaritos do `eval_passk_curva.py` filtrava `if tipo != "tool": continue`. O campo do
holdout é **`kind="tool_call"`**, e a convenção do resto do projeto é *"text" versus o resto*.
Resultado: a guarda **pulou os 85 exemplos** e imprimiu **`✅ todas as referências executam`**
tendo verificado **zero**.

**Como foi pega:** o laço principal encontrou 5 exemplos `tool` na mesma corrida em que a guarda
disse 0. Dois números do mesmo arquivo discordando — a contradição de sempre.

**Guarda da guarda:** contar quantos itens a guarda inspecionou e **abortar se for zero**.

```python
if checadas == 0:
    raise SystemExit("a guarda nao verificou NENHUMA referencia — o filtro de tipo esta errado")
```

### 7. A medição de desempenho mentiu QUATRO vezes no mesmo dia

Todas "corretas" no próprio contexto, todas erradas para a decisão:

| leitura | ms/amostra | por quê |
|---|---:|---|
| prompt de brinquedo, lote 64 | 109 | prompt curto, máquina ociosa |
| durante a auditoria de corpus | **3.865** | geração de modelo pequeno é **CPU-bound**; a auditoria comia a CPU |
| lote 32, CPU livre | 192 | ✅ o número real |
| após ~500 chamadas de `generate` | **parou** | fragmentação do alocador: 7.766 de 8.151 MiB |

⭐ **A fragmentação é a mais traiçoeira porque o sintoma não é OOM, é lentidão:** 100% de
utilização de GPU com **35 W** de potência. Correção: `torch.cuda.empty_cache()` entre exemplos
(⚠️ `expandable_segments` **não funciona no Windows** — o log avisa) e **VRAM impressa na linha de
progresso**. Depois: `297/330 MiB` cravado do primeiro ao último exemplo, 59 W.

> **Medir throughput "em regime" não basta. É preciso medir no regime em que a corrida vai
> rodar** — com a mesma carga de CPU, o mesmo lote e depois de centenas de chamadas.

### 8. Contar a direção sem testar a magnitude

O `diff_por_problema.py` imprimiu **"🔴 ESQUECEU MAIS DO QUE APRENDEU"** com **2 esquecidos contra
1 aprendido** — McNemar exato **p = 1,000**, ruído puro. É o mesmo defeito do critério de veredito
multiplicativo da §5: um veredito impresso por código, com aparência de resultado.

**Guarda:** todo veredito comparativo exige **teste de significância** antes de concluir; com n
pequeno, a direção sozinha não é informação.

### 9. Comparar marcos de **schedules diferentes** — mediu o schedule e chamou de modelo

O Bee-350M parecia perder do Bee-150M com volume crescente de tokens: 4,55% **melhor** em 1B,
0,90% melhor em 3B, 0,66% **pior** em 6B, **2,51% pior** em 10B. Um modelo 2,3× maior começando
na frente e terminando atrás, com o déficit crescendo limpo. Isso gerou a hipótese de subtreino
(63 tok/param contra 143) e a pergunta de expandir o corpus no próximo degrau — coleta, dinheiro
e semanas.

Só que o **150M usou cosine** e nesses pontos já vinha colhendo decaimento (LR em 99,8% → 96,8%
→ 85,7% → **62,2%** do pico), enquanto o **350M usa WSD** e estava cravado no platô de 55%. A
tabela comparava um modelo que estava **assentando** com um que ainda **explorava**. O segundo
sempre parece pior, e a diferença sumiria no fim.

**Medido por bifurcação** (US$ 22, ver `fork-decaimento.md`): decair a cópia inverteu o sinal —
de 2,51% pior em 10B para ~0,6% **melhor** em 13B — **sem um token novo**.

> **Um modelo maior ficando pior com mais dados é uma contradição grande — e a resposta certa
> era desconfiar do instrumento, não teorizar sobre subtreino.** É o princípio que abre esta
> Parte II, aplicado a um caso que eu não reconheci como sendo dela.

**Guarda:** marcos intermediários de modelos com **schedules de LR diferentes não são
comparáveis**. Só o ponto final, ambos decaídos, compara modelos. E ao bifurcar para testar
schedule, passar `--lr` **explícito**: com `--lr 0` a Step Law deriva de
`passos × tokens_por_passo`, então mudar o horizonte muda o LR junto (15B em vez de 21,75B daria
LR 10,8% menor) e o resultado fica inatribuível.

---

## Parte III — As leis medidas

Enunciados curtos, cada um com o número que o sustenta. Valem para o próximo Bee.

### 1. Rejection sampling move o **piso** rumo ao teto — e não move o teto

⭐ **Medido de novo em 2026-08-14 com n=128 e o holdout limpo dos itens impossíveis** — é a
demonstração mais nítida que este projeto produziu. O ganho decai **monotonicamente até zero**:

| k | base | pós-colheita | delta |
|---:|---:|---:|---:|
| 1 | 59,1% | **64,1%** | **+5,07 pp** |
| 16 | 81,7% | 81,8% | +0,08 pp |
| 64 | 85,0% | 84,9% | −0,06 pp |
| **128** | **85,3%** | **85,3%** | **+0,00 pp** |

Não é interpretação — é a coluna de delta convergindo a zero. Elevar o teto exige capacidade ou
dado novo, não reamostrar o que já existe.

⚠️ **Mas a folga é MAIOR do que o projeto acreditava:** 64,1% → 85,3% são **21,2 pp**
aproveitáveis, não os 15,3 pp que os números antigos sugeriam (eles vinham de k=16 e de um
holdout com 11,8% de itens impossíveis). Ver [teto-passk-medido.md](teto-passk-medido.md).

### 2. Num modelo pequeno, a **capacidade é disputada**

Ensinar multi-turno por full fine-tune custou **−5,9 pp** de execução single-turn e −7,0 pp de
argumentos exatos. O mesmo dado em **adapter LoRA** custou **zero** — e ficou melhor no alvo.

| | full FT | adapter |
|---|---:|---:|
| multi-turno ancorado | 89,4% | **91,8%** |
| single-turn (execução) | 60,0% | **65,9%** |
| tamanho | 302 MB | **24 MB** |

⭐ É a validação da tese da COMEIA: **backbone congelado, capacidade nova em adapter**.

### 3. Colher só um lado desloca a decisão

O rejection sampling só produz `tool_call` (só a chamada tem verificação por execução). A
proporção foi de 59,3% → 75,8% tool e o over-calling subiu **+7,6 pp**. Colhendo os dois lados
(56,9% tool), ganha-se nos **dois** eixos.

### 4. **$/bilhão de tokens**, nunca $/hora

| GPU | TDP | tok/s | $/h | **$/B tokens** |
|---|---:|---:|---:|---:|
| RTX 5090 | 600 W | 62,9k | 0,99 | **4,37** |
| RTX PRO 4500 | 200 W | 42,1k | 0,74 | 4,88 |

A placa 25% mais barata por hora saiu **36% mais cara por token**. O preditor é o **TDP**.

### 5. Toda intervenção que **bloqueia** precisa ser medida nos dois lados

O `verifier.py` interceptava 4 over-calls em 14 — parecia útil. Mas bloqueava **7 chamadas
legítimas em 85**: saldo **−4**. Estava piorando o sistema havia semanas, e ninguém sabia
porque só se media o ganho.

### 6. Não herdar hiperparâmetro medido sobre outro modelo

O LR 1e-3 do SFT fora otimizado **sobre o modelo bugado**. Remedido sobre a base correta: o
ótimo é **6e-4** (2,9% melhor). E LoRA opera em regime diferente ainda: **1e-3**, com a curva
caindo 10× entre 1e-4 e 1e-3.

### 7. Ler throughput **em regime**

Medir com 6 passos de aquecimento deu **21,7 s/passo**; o valor real era **4,4 s/passo** —
erro de 5×, que gerou uma decisão de infraestrutura equivocada. Só confiar a partir do passo
~20, com três leituras coincidentes.

### 8. O decaimento de LR vale mais que os tokens que ele consome — e o platô não mostra nada

Medido em 345M (`fork-decaimento.md`): decair 20% em `1−√t` tirou **−0,1305 de loss** (perplexidade
20,8 → 18,3, **−12,0%**) com **um terço** do decaimento aplicado. No mesmo intervalo, o run gêmeo
no platô ficou **plano**: 3,0397 → 3,0415 em dez mil passos e 655M tokens.

Duas consequências que valem para qualquer run futuro:

1. **Perplexidade de validação plana no platô do WSD não é sinal de saturação.** Ela não mede o que
   o platô faz; só cobra quando o modelo assenta. Não abortar nem replanejar um run por causa disso.
2. **Uma lei `L(D)` ajustada sobre um run com decaimento atribui a D o que é do LR.** Foi por isso
   que a curva do 150M errou o marco de 15B por 0,0161 e teve as projeções descartadas
   (`previsao-marco-10B.md`). Ajustar lei de scaling só sobre pontos do **mesmo regime de LR**.

---

## Parte IV — O que estava certo desde o início

Não mexer sem medir:

- **Arquitetura** `LlamaConfig` sem código custom — tudo que existe (PEFT, TRL, vLLM) funciona
  sem adaptação, e o recipe é o mesmo em toda a escada.
- **LR por Step Law** (`η* = 1,79·N^-0,713·D^0,307`).
- **Tokenizador PT próprio** — 0,2183 tok/byte contra 0,3576 do SmolLM2.
- **Gates pareados baratos** antes de run longo — 5 min contra dias.
- **Procedência de dados** verificada na origem, nunca pelo rótulo.
- **Marcos de scaling** salvos durante o treino: a curva vira **medição**, não extrapolação.

---

## Checklist antes de qualquer run longo

- [ ] guarda de rótulos roda e **aborta** (com dado real)
- [ ] cobertura de amostragem reportada = 100%/época
- [ ] nº de exemplos após truncamento == nº carregado (SFT) — **aborta** se não
- [ ] gabaritos do avaliador **executam** antes de medir qualquer modelo
- [ ] a guarda **reporta quantos itens inspecionou** e aborta se for zero
- [ ] throughput medido **no regime real**: mesma carga de CPU, mesmo lote, depois de centenas de chamadas
- [ ] veredito comparativo passa por **teste de significância**, nunca só pela direção
- [ ] `--dry-run` de 3 passos passa
- [ ] throughput em regime (passo ≥20, três leituras coincidentes)
- [ ] custo em **$/B tokens**
- [ ] corpus verificado por **hash** contra a referência
- [ ] marcos de scaling programados
- [ ] checkpoint em disco **persistente**
- [ ] gate de sucesso **definido antes** de gastar
