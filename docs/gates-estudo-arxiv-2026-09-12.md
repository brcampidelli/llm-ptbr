# Gates do estudo do arXiv — execução (iniciado 2026-09-12)

> Executa os gates de [`estudo-arxiv-2026-09-12.md`](estudo-arxiv-2026-09-12.md) §6. Cada gate
> registra: o que o artigo afirma, o que foi medido aqui, o veredito, e o artefato. Regra do
> projeto: **o número do artigo não entra como resultado; só o que foi medido aqui entra.**

**Restrições que ordenaram a execução (declaradas antes de começar):**
1. **Nenhuma GPU alugada para gates** enquanto o run principal estiver ~US$ 190 curto de crédito.
   Tudo na RTX 5070 local (8 GB) ou em CPU — o custo vira horas, não dólares.
2. **A máquina local dorme** (três congelamentos de vigia numa semana). Gates de inferência e CPU
   não sofrem; gates de treino local de várias horas ficam para o lote 2.

| lote | gates | GPU de treino |
|---|---|---|
| 1 | #2 densidade · #4a sondas · #4b equivalentes · #4c bpb por fonte · #5 quase-duplicatas | nenhuma |
| 2 | #1 Muon×AdamW · #3 catálogo perturbado + recusa sem template · #6 repetição em denso | 5070, horas |

---

## Gate #5 — quase-duplicatas holdout × treino (2609.03350, 2609.10357) — ✅ FECHADO

**Escopo corrigido antes de rodar:** o artigo denuncia o FineWeb-2 conter o próprio *test* no
*train*. O Bee não usa o test split do FineWeb-2; o holdout é próprio (`sha1 % 100 < 2`), e o
censo por fingerprint garantiu zero documento com o mesmo início no treino. O que o fingerprint
**não** pega é quase-duplicata — mesmo conteúdo, outro preâmbulo. É isso que se mediu.

**Instrumento:** `bee/censo_ngram_val.py` — fração dos 13-gramas (de tokens) de cada documento do
`val.bin` presentes em qualquer lugar do `train.bin` (20B tokens). **Censo completo dos dois lados**
(§2ac). Rodou nos 64 vCPUs do pod com `nice 19`, 267 s; custo no treino: −8% de tok/s por 4 min.
**Auto-teste (§2t):** `val.bin` contra ele mesmo → 100,00% dos 13-gramas, 46.215/46.215 docs com
fração 1,0 — o instrumento acha o que certamente está lá.

| idioma | docs | fração média | ≥ 0,5 | ≥ 0,8 |
|---|---:|---:|---:|---:|
| **por** | 23.802 | 0,103 | **1.431 (6,0%)** | **425 (1,8%)** |
| jpn | 2.225 | 0,074 | 105 (4,7%) | 14 |
| cmn / fra / spa / deu | 2.714–4.023 | 0,04–0,06 | 1,2–2,0% | 2–6 |
| eng / arb | 3.752 / 3.525 | 0,023 | 0,5% | 0–1 |

🔴 **Os piores não são boilerplate: são prosa inteira** (notícia, blog, texto jurídico, ata) com
fração **1,00** — todos os 13-gramas no treino, logo o texto existe lá embutido num documento
maior com outro preâmbulo. Mecanismo: a metade PT do treino veio do `corpus_pt` e o holdout PT do
FineWeb-2 — corpora diferentes que rasparam as mesmas páginas.

**Mas contar não é medir.** `bee/efeito_quaseduplicata_val.py` no `marco_3B`, PT:

| | docs | loss |
|---|---:|---:|
| sujos (frac ≥ 0,5), todos | 1.431 | 2,7930 |
| limpos (frac < 0,2), amostra | 1.500 | 2,9008 ± 0,013 |
| **viés na val loss de PT** | | **−0,0063 nats = 0,8× o piso de ruído (0,0076)** |

⭐ **Veredito: contaminação real, efeito abaixo do ruído.** Os documentos são 3,7% mais fáceis,
mas são 6% dos tokens. A curva dos marcos e a previsão pré-registrada para o 10B ficam de pé.
⚠️ Detalhe a favor do 2609.11917: os docs de fração 1,0 (cópia exata) têm loss **2,86**, *maior*
que os de 0,7 — uma exposição em 1 época quase não memoriza num 1B.

**Pendente derivado:** o `corpus_multi_pt/limpo` da âncora tem a mesma construção (limpo por
fingerprint); o viés no bpb do Bee-1G ali é da mesma ordem e não muda a leitura, mas o holdout de
PT deveria ganhar um `limpo` de conteúdo (frac < 0,2) antes do gate final.
Artefatos: `censo-ngram-val-bee1g-2026-09-12.json`, `efeito-quaseduplicata-val-pt-marco-3B.json`.

---

## Gate #4b — equivalentes não anotados na seleção (2609.08327) — ✅ FECHADO

**O artigo afirma:** 67,9% das sub-queries tinham ferramenta equivalente não anotada, inflando
30–47% do ganho de fine-tuning. **Piso do gate:** ≥ 15% dos "erros" serem alternativas válidas.

**Medido:** os **130** casos de erro de seleção (pred ≠ ref) do despejo mais recente
(`casos_rf-s43-cat15.jsonl`), com as descrições das duas ferramentas extraídas do próprio prompt.
**Dois juízes independentes**, mesma rubrica estrita, sem se ver.

| | |
|---|---:|
| concordância | 130/130, κ = 1,00 |
| equivalentes não anotados | **3 (2,3%)** · Wilson 95% superior **6,6%** |
| ambíguo | 1 |
| erros nítidos | 126 |

Os três equivalentes: hipoteca × parcela de empréstimo genérico (`calculate_mortgage` ×
`calculate_loan_payment` × `calculate_loan_emi`), mesma fórmula, mesmos argumentos.

⭐ **Veredito: a seleção do Bee NÃO está subestimada.** O holdout foi construído por componente
conexo e teto por ferramenta (§2o, §2q) e passou pela auditoria de discriminação (§2u); o artigo
mediu benchmarks com anotação frouxa. ⚠️ Os dois juízes são instâncias do mesmo modelo — o κ
superestima independência; o que sustenta é que 126 descasamentos grosseiros não admitem outra
leitura. Consequência: os 130 são erros do modelo, alvo do gate #3.
Artefato: `auditoria-equivalentes-nao-anotados-2026-09-12.json`.

---

## Gate #4a — sondas no scorer agêntico (2609.09218) — ✅ FECHADO, 🔴 BUG CORRIGIDO

**O artigo afirma:** scaffold e scorer distorcem rankings (*double measurement confound*); sonda
= submissão correta / vazia / fabricada.

**Mapa do scorer** (`comeia/eval/eval_agentic_exec.py`): não há reparo de JSON (bom); o veredito
principal `pontuar()` exige o nome nas 14 fixas ou nas aprovadas antes de executar. ⚠️ Achado de
proveniência: `--restrito-ferramenta` **não é gravado no config do artefato**, só a tag `rf-`.

**Sonda com o código real** (`comeia/eval/sonda_scorer_fabricada.py`), caso real de
`calculate_sales_tax`, nome fabricado `sales_tax_helper_inventada` (casa a regex `tax` do mundo
aberto), argumentos de papel certo:

| sonda | principal (`exec_ok`) | E5b "servida" | votada |
|---|---|---|---|
| CORRETA | True | True | True |
| VAZIA | não pontua (under) | — | — |
| **FABRICADA** | **False** ✅ | **True** 🔴 | **True** 🔴 |

🔴 Os dois caminhos secundários comparavam só o resultado executado — `executar_aberto` devolve
`ok=True` para qualquer nome e, se o nome casa a família, computa a fórmula certa. **Nome que não
existe no catálogo contava como acerto.** Corrigido: ambos passam por `pontuar()`. Após a
correção: FABRICADA False/False/False, CORRETA True/True/True.

**Mudou alguma decisão?** Não: E5b e votação foram medidas e **reprovadas** (62,4% × 65,9% do
greedy; votação empatou). Se nomes fabricados as inflaram, o valor real era menor — a reprovação
só fica mais forte. E `--restrito-ferramenta` torna o furo inerte nas rodadas recentes.
⚠️ `pontuar()` é closure dentro de `main()`; a sonda **espelha** a lógica corrigida. A verificação
de verdade acontece na próxima rodada real do avaliador.

---

## Gate #2 — densidade de solução (2609.08966) — ✅ LINHA DE BASE (leitura decisiva no fim do run)

**O artigo afirma:** num MoE de 30B, o checkpoint decaído (melhor loss) foi o pior ponto de partida
para SFT; densidade de solução a τ=0,90: CONSTANT 27%, MERGE 13%, COOLDOWN 0%.

**Instrumento:** `bee/densidade_solucao.py`, definição do artigo (100 perturbações gaussianas,
σ absoluto ∈ {0,01; 0,005; 0,001}), com duas adaptações declaradas: escore = exp(−loss) em
`wiki/limpo` (o Bee-1G é base) e **as mesmas 100 amostras de ruído para todos os marcos** (pareado).
**Guarda §2aa:** o bpb sem perturbação reproduziu a âncora nos dois marcos (1,1086 e 1,0808).

| σ | ΔL 1B | ΔL 3B | ΔL 6B | ΔL 10B | 3B−1B (3B pior em) | 6B−3B (6B pior em) | 10B−6B (10B pior em) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,01 | +0,362 | +0,274 | +0,314 | +0,310 | −0,096 (0/100) | **+0,044 (96/100)** | −0,003 (44/100) |
| 0,005 | +0,089 | +0,066 | +0,077 | +0,074 | −0,025 (0/100) | **+0,012 (88/100)** | −0,001 (43/100) |
| 0,001 | +0,0037 | +0,0024 | +0,0031 | +0,0028 | −0,0012 (25/100) | +0,0007 (66/100) | −0,0001 (44/100) |

Curvatura `c = ΔL/σ²` (quadrática, como bacia), σ=0,005: **1B 3.558 → 3B 2.634 → 6B 3.063 → 10B 2.946.**
(`marco_10B` medido em 2026-09-15: pareado 10B−6B **empata** em 44/100 — a bacia parou de
estreitar; ver adendo em `bpb-marcos-bee1g-2026-09-10.md`.)

🔴 **Com dois pontos eu tinha escrito "ao longo do platô a densidade sobe". O terceiro ponto
derrubou:** a bacia alargou de 1B para 3B e **voltou a estreitar de 3B para 6B**, ainda no platô e
com `lr` constante. A densidade no platô **não é monotônica** — e portanto a linha de base do fim
do run tem de ser o **próprio `marco_15B`, medido**, não uma extrapolação. (Uma explicação
possível é o afiamento progressivo com LR constante rumo ao limite de estabilidade; é hipótese,
não medida, e por isso não entra como explicação.)

A leitura decisiva é **15B-platô × 20B-decaído**, no fim do run — com régua, método testado
(guarda §2aa passou nos três marcos) e três pontos de referência que já mostraram que a régua
distingue marcos com 88–100/100 de consistência pareada. ⚠️ Geometria local não é treinabilidade;
o artigo não estabelece causalidade. O que o gate compra é não escolher às cegas.
Artefatos: `densidade-solucao-bee1g-marcos-1B-3B.json`, `densidade-solucao-bee1g-marco-6B.json`.

---

## Gate #4c — bpb por fonte (2609.10357) — ✅ FECHADO com os artefatos existentes

**O artigo afirma:** holdout sem contaminação exata ainda favorece o domínio dominante do corpus
de treino (familiaridade sobrevive à decontaminação).

**Medido, sem rodada nova:** os dois holdouts da âncora são duas fontes — `wiki` (Wikipédia-PT,
**fora** do treino do Bee) e `corpus_multi_pt` (FineWeb-2 PT, a linhagem do corpus do Bee).
Diferença relativa `(wiki − corpus_multi) / média`, por modelo, nas células `limpo`:

| modelo | linhagem FineWeb-2 PT | wiki | corpus_multi | wiki é… |
|---|---|---:|---:|---:|
| Bee-150M | sim | 0,9497 | 0,9318 | +1,9% mais difícil |
| Bee-350M | sim | 0,9240 | 0,9052 | +2,1% mais difícil |
| Bee-1G `marco_6B` | sim | 1,0642 | 1,0524 | +1,1% mais difícil |
| **Qwen3-0.6B-Base** | não (viu Wikipédia) | 0,9424 | 1,0986 | **−15,3% — mais fácil** |

⭐ **O sinal inverte com a linhagem do treino.** Dificuldade não é propriedade do texto; é
familiaridade. 🔴 Consequência: a comparação Bee-1G × Qwen em `corpus_multi_pt/limpo` apresentada
em [`bpb-marcos-bee1g-2026-09-10.md`](bpb-marcos-bee1g-2026-09-10.md) §6 ("já ganha") é
**confundida por familiaridade** — o holdout é da linhagem do Bee. Nenhum dos dois holdouts é
neutro entre famílias (o Qwen viu Wikipédia). Comparações **dentro** da família Bee seguem válidas.
⚠️ Só duas fontes; a correlação com a fração de cada fonte no treino fica para quando houver
holdout de ≥4 fontes. O sinal, porém, não depende disso.

## Gate #3 — catálogo perturbado + recusa sem template (2609.04184, 2609.04714) — ✅ FECHADO (2026-09-14)

**Desenho revisto pelo mapa da receita do E19** (`comeia/models/e19c-s4x/training_args.json`):
- (a) **"remover as ferramentas não usadas" ficou de fora**: nos positivos colapsa o catálogo para
  1 ferramenta e reintroduz o atalho da §2u. Ficou: renomear ~20% dos nomes por sinônimo de verbo,
  consistente entre bloco/completion/`ferramenta`/turnos anteriores, + reembaralhar.
  `comeia/data/perturbar_catalogo.py` → `treino_e19c_catperturbado.jsonl`: **1.824/6.739 alvos
  renomeados (27,1%)**, cabeçalho/rodapé byte a byte, `conferir()` = tamanho não prediz classe.
- (b) **O C-full já era "sem template" — trocando recusa por resposta útil** (mudou conteúdo). O
  braço novo mantém a **decisão de recusar** e tira só a frase fixa: a leitura estrita do artigo.
  `comeia/data/recusas_especificas.py` (professor deepseek-chat, ~US$ 0,7).

🔴 **A v1 de (b) trocou um template por outro.** Guardas por exemplo passaram 4.126 recusas — e
**62% começavam com "Não consigo calcular"**. Só lendo com os olhos (§2e). Concentração de
abertura é propriedade do **conjunto**, e nenhuma guarda por exemplo a vê. v2: 12 estilos
sorteados por pedido (7 começam pelo objeto), "Não consigo" proibido como abertura, e **guarda de
conjunto** (abertura de 3 palavras ≤ 15%) — testada: reprova a v1 (62%), aprova o piloto (13%).

**Roteiro do pod** (`bee/gate3_sft_pod.sh`): versões fixadas nas dos adapters de referência
(transformers 5.14.1 · trl 1.9.0 · peft 0.19.1); **controle §2aa** antes de qualquer braço — o
C-full s42 publicado tem de reproduzir exec_ok 372/536 e over_call 39/268, senão aborta; depois
2 corpora × 3 sementes, eval com a config `cfgref`. Referências: e13 (exec 71,8–75,2 · over
16,8–17,5) e C-full (66,8–69,4 · 14,2–14,9).

**Execução (2026-09-13).** Pod `bee-gate3b` (RTX 4090 48 GB, US$ 0,75/h, EU). Rede testada
**antes** de instalar (PyPI 3,7 MB/s · HF 14 MB/s · GitHub 8,7 MB/s) — o primeiro pod, `bee-gate3`
em EUR-NO-1, tinha 46 B/s para o Hub e load 22, e foi terminado sem instalar nada (US$ 0,05).

🔴 **O controle §2aa não reproduziu — e o motivo é uma lição nova.** O C-full s42 publicado
(`sha256 020512b1…`, idêntico ao `comeia/models/e19c-s42`) deu **369/536 · 36/268** na 4090 contra
**372/536 · 39/268** na 5070. Config byte a byte igual (`lote 16 · max_len 1700 · por_argumento ·
restrito · parar_controle · chat`), mesmo `perfil_argumentos_sha`, mesmo n. As diferenças estão em
**3 ferramentas** (`search_movies` −3, `generate_username` −1, `calculate_mortgage` +1) e são
simétricas — 3 chamadas a menos nos casos de ferramenta (under +3) e 3 a menos nos casos de texto
(over −3): o modelo hesitando em empates numéricos. **A régua greedy em bf16 muda com o hardware**,
como já mudava com o tamanho do lote (§2t). Não é o modo de falha da §2aa (config errada dá 3,2%
onde era 71,8%); é o da §2g — *mesma régua* inclui o hardware.

**Correção no roteiro:** deriva ≤ 8 casos em exec_ok e ≤ 6 em over_call é aceita como numérica
(acima disso aborta), **e todas as 6 referências são remedidas no pod** antes dos braços novos —
e13 s42/43/44 (adapters locais por scp, sha256 conferido) e C-full s43/44 (subpastas `seed-4x/`
do Hub). A comparação é só pod-com-pod; os números locais ficam como sanidade. Custo: +1,3 h.
Consolidador `bee/gate3_ler.py`: critério declarado antes de ler — **3 sementes com o mesmo sinal
e |média dos deltas| > 2 × max(dp/√3, erro amostral da diferença)**; sem 3 sementes em comum não
emite veredito (testado). Também imprime a deriva 5070→4090 nas 4 referências que têm artefato
local, para registrar o tamanho desse efeito com mais de um ponto.

**Referências remedidas no pod (4090)** — deriva 5070→4090 nos 4 pontos pareados: exec −3, −2,
+2, +1 · over −3, +1, −1, 0 casos. |Δ| ≈ 2 casos, sem sinal sistemático: ruído numérico, como
diagnosticado. e13: exec 71,5 · 75,6 · 75,0 (over 17,5 · 16,8 · 17,5); C-full: 68,8 · 68,5 · 67,0
(over 13,4 · 13,8 · 14,9).

### (b) nas outras capacidades — 🔴 a recusa específica recusa TUDO, com estilo

Enquanto o pod treinava as sementes 43/44, o adapter `recusa_especifica-s42` (sha256 conferido)
passou pelo consolidador de 9 capacidades na 5070, `--chat`, transformers 5.14.1 (o mesmo dos
artefatos de referência). Uma semente; a matemática entra declarada como não medida (§2z).

| s42 | e13 (template) | C-full (útil) | **recusa específica** |
|---|---:|---:|---:|
| tradução en→pt chrF++ (piso copiar 21,5) | 18,8 | **34,0** | **11,1** |
| tradução pt→en chrF++ (piso 22,7) | 13,2 | 20,5 | 9,0 |
| resumo — respondeu | 0/150 | **117/150** | 23/150 |
| resumo — útil (piso LEAD-2 51,3%) | 0 | 0 | 15/150 |
| sentimento (piso léxico 79,0) | **81,8** | 56,0 | 79,8 |
| atendimento útil / inventou | 0 / 0 | 0 / 14 % | 0 / 11,6 % |
| IFEval-PT estrito por instrução | 28,9 | 30,0 | 30,4 |
| código (interno / HumanEval-XL) | 0 / 0 | 0 / 0 | 0 / 0 |

**Lido com os olhos (§2e), 4 prompts, os três adapters lado a lado:** pedida uma tradução, o e13
diz *"Sinto muito, mas não tenho acesso a informações financeiras…"* e lista um menu; o C-full
tenta (na direção errada, mas tenta); a recusa específica responde **"Sem meios de traduzir o
orçamento da cidade para o português por aqui."** — uma recusa perfeita, específica, sem fórmula,
para uma tarefa que não é chamada de ferramenta. Atendimento: *"Aqui eu não tenho como realizar a
troca do produto."* Sentimento: *"Isso — avaliar produtos e serviços — está fora do que eu faço
neste contexto."* Censo sobre 200+200 frases do FLORES e os 150 resumos: **69% e 68% das
traduções são recusas** (regex das negações do próprio corpus); o resto são frases negadas de
uma linha (*"O isolamento e a guerra são coisas que não combinam."*) — a **sintaxe** da recusa
(objeto + negação) vazando para onde não há recusa. No resumo, 15% recusam e o resto inventa
prefeitos (*"Dilador Borges"*, *"Miguel Coelho"*).

⭐ **O que isso decide:** o artigo 2609.04714 atribui a generalização excessiva à **frase fixa**.
Aqui, tirada a frase fixa (12 estilos, abertura dominante 9,4%, guarda de conjunto), o modelo
continua recusando tradução, atendimento e sentimento — **é a decisão de recusar que
generaliza, não o template.** A §2ab fica mais forte, não mais fraca: a saída para as outras
capacidades é a **forma útil** (C-full), e "recusa específica" só existe como terceiro ponto no
**eixo agêntico** — e, fechadas as 3 sementes (abaixo), nem lá ele se distingue das referências.
O que a recusa específica *não* faz é o dano lateral do e13 no sentimento: mantém os 79,8
(o e13 tem 81,8, o C-full 56,0) — coerente com a observação de que sentimento sobe com a
quantidade de recusa no corpus, e sem mecanismo claro.

⚠️ O que este instrumento não mostra (§2q): uma semente; a régua de tradução não separa "recusa"
de "ruído" (foi o censo à parte que separou); e nenhuma das três formas passa do piso trivial em
resumo/atendimento — *"sabe resumir"* continua sem lastro em todos.

### Resultado final — 3 sementes × 4 braços, 12 artefatos na mesma régua e no mesmo hardware

`bee/gate3_ler.py` → `gate3-catalogo-perturbado-recusa-especifica-2026-09-14.json`; log do pod em
`gate3-pod-2026-09-13.log`. Pod `bee-gate3b`: 16:38 → 03:18 UTC (10,7 h · ≈ US$ 8), dos quais 1,3 h de
referências remedidas e 9 h de 6 treinos de 78 min (6,8 s/passo — a receita 1×16 com checkpointing é
limitada por CPU, GPU a 14%; a 5070 local fazia o mesmo tempo, e mudar micro-batch mudaria a receita).

| braço | exec_ok | over_call | under | tool_right | args_exact |
|---|---:|---:|---:|---:|---:|
| e13 (recusa em template) | 74,0 ± 2,2 | 17,3 ± 0,4 | 9,1 | 84,0 | 40,4 |
| C-full (resposta útil) | 68,1 ± 1,0 | 14,1 ± 0,8 | 16,0 | 77,6 | 34,9 |
| **(a) catálogo perturbado** | 70,6 ± 0,7 | 15,9 ± 1,4 | 14,4 | 79,5 | 39,6 |
| **(b) recusa específica** | 74,1 ± **4,4** | 16,0 ± 3,2 | 8,3 | 83,5 | 40,5 |

Pareado por semente (critério declarado: 3 sementes com o mesmo sinal e |média| > 2 × max(dp/√3, SE
amostral da diferença)):

| par | exec_ok | over_call | tool_right | args_exact |
|---|---:|---:|---:|---:|
| (a) − C-full | +1,1 / +2,8 / +3,7 → **+2,5** (2×piso 5,7) | +4,1 / +1,5 / 0,0 → +1,9 | −0,2 / +3,5 / +2,2 → +1,9 | +0,2 / +6,7 / +7,1 → +4,7 (5,8) |
| (b) − e13 | −0,6 / −3,2 / +4,1 → +0,1 | −4,5 / −1,1 / +1,9 → −1,2 | −0,9 / −4,5 / +3,9 → −0,5 | +0,2 / −2,8 / +3,0 → +0,1 |
| (b) − C-full | +2,1 / +3,9 / +12,1 → +6,0 (6,2) | −0,4 / +1,9 / +4,5 → +2,0 | +2,1 / +4,1 / +11,4 → **+5,8 ⭐** | +2,1 / +6,7 / +8,2 → +5,7 (5,8) |

**(a) catálogo perturbado × C-full → NÃO ADOTAR.** Nenhuma métrica passa do piso. A seleção — o
que o 2609.04184 promete — fica em +1,9 pp com sinais mistos; a execução sobe +2,5 pp nas três
sementes, consistente e pequena (McNemar por item, *post-hoc*: s43 43 ganhou/28 perdeu p = 0,10;
s44 59/39 p = 0,05). O que mais se move é a exatidão de argumentos (+4,7, a 1 pp do limiar) — não
era a hipótese, e fica registrado como hipótese para outro gate, não como resultado.

**(b) recusa específica → INDISTINGUÍVEL das duas referências no eixo agêntico.** Contra o e13 é
+0,1 pp de execução e −1,2 de over-call; contra o C-full é +6,0 e +2,0 — nada além do piso. O que
passa do ruído é só o que a coloca **do lado do e13**: tool_right +5,8 e under-call −7,6 sobre o
C-full. Ou seja: **tirar o template não mexeu em nada no eixo agêntico** — o braço é o e13 com outra
roupa, e nas outras capacidades (acima) recusa tudo como o e13. O 2609.04714 não transfere para
este cenário nos dois eixos.

🔴 **A dispersão entre sementes de (b) é o achado que sobrou:** exec_ok 70,9 · 72,4 · **79,1** —
dp **4,4 pp**, contra 1,0 do C-full e 2,2 do e13, e 2,3× o erro amostral de uma medida (1,9). A
semente 44 é o maior número de todo o gate (acima de qualquer e13), com under-call 5,2% e over-call
19,4%: aprendeu a chamar quase sempre. Recusas específicas geradas por professor são um alvo mais
**instável** para o SFT do que a fórmula fixa — três sementes decidem que é variância de treino,
não amostragem (§2x), e não explicam de onde vem.

🔴 **Defeito no consolidador, pego ao ler o veredito.** A v1 do bloco (b) lia *"não perde para o
e13"* **e** *"não sobe sobre o C-full"* — duas **ausências** de efeito — como *"TERCEIRO PONTO
CONFIRMADO"*. Ruído puro confirmaria; é a §2q dentro do consolidador: um veredito que o instrumento
não consegue **negar** não é veredito. Corrigido antes de escrever esta seção: terceiro ponto exige
evidência positiva nos dois lados (execução acima do C-full **e** over-call abaixo do e13, ambos
além do ruído), e a dispersão entre sementes vai impressa ao lado.

⭐ **Lição de método nova (§2t, complemento):** a régua greedy em bf16 muda com o **hardware**,
não só com o lote — |Δ| ≈ 2 casos em 536 e 1,2 em 268 entre RTX 5070 e RTX 4090, mesma config,
mesmo adapter. Pequeno demais para trocar um veredito, grande o bastante para reprovar um controle
de tolerância zero. *Mesma régua* (§2g) inclui a GPU; referência medida em outra máquina é
referência a remedir.

## Gate #1 — Muon × AdamW (2609.04577, 2609.11655) — ✅ FECHADO (2026-09-16): MUON MELHOR, 7× o piso

⚠️ Regime: o artigo mede ≥ 20 tok/param. No 150M isso são 3B tokens por braço (US$ 53 nos 4);
por isso um **`50m`** novo na ESCADA (16×448, 53,0M params) com 1,06B tokens = 20 tok/param —
o início do regime do artigo. `bee/muon.py` (NS5, RMS casado ao Adam; autoteste OK),
`--otimizador` no `pretrain.py` (caminho AdamW intocado; dry-run com Muon OK a 86,5k tok/s na
5070), `gate_muon_50m.sh` (4 braços pareados + 2 de sensibilidade a 3× lr) e consolidador.
Sem âncora publicada para o 50M: as duas sementes de AdamW ancoram uma à outra.

**Executado em 2026-09-16** no pod `bee-gates` (RTX 5090, EUR-IS-1, volume `bee-corpus-vol` montado;
dados fatiados para o disco do container). 6 braços × 1,06B tokens, 2,0 h cada, ≈ US$ 13.
Artefato: `gate1-muon-vs-adamw-50m-2026-09-16.json`.

| braço | val final | ppl | tok/s |
|---|---:|---:|---:|
| AdamW s42 | 3,3424 | 28,3 | 144k |
| AdamW s43 | 3,3494 | 28,5 | 144k |
| **Muon s42** | **3,2963** | **27,0** | 134k |
| **Muon s43** | **3,2922** | **26,9** | 134k |
| AdamW 3× lr | 3,3874 | 29,6 | 144k |
| Muon 3× lr | 3,3342 | 28,1 | 132k |

**Pareado por semente: Muon − AdamW = −0,046 (s42) · −0,057 (s43) · média −0,052 nats.** Piso de
ruído (|AdamW s42 − s43|) = 0,007 → a folga é **7× o piso, nas duas sementes**. Critério declarado
antes de rodar: "Muon só ganha se a folga passar do piso". Passou.

A curva inteira fica abaixo, não só o fim: −0,10 no passo 2.000, −0,05 estável do platô (passo
12.500: 3,526 × 3,575) ao decaimento. **Sensibilidade a lr (§2f):** a 3× do lr de pico os dois
degradam parecido (AdamW +0,045, Muon +0,038) e **o Muon a 3× (3,334) ainda bate o AdamW no lr
dele (3,342)** — a vantagem não é artefato de o AdamW estar longe do ótimo. Custo: −8% de
throughput (o Newton-Schulz-5).

⚠️ O "1,3–1,9× de eficiência de token" do artigo **não é mensurável neste desenho** como
cruzamento de curva: a loss final do AdamW só é alcançada durante o decaimento, e o AdamW no platô
nunca chega ao platô do Muon antes de decair (o consolidador imprime 1,03–1,07×, que é a
geometria do decaimento, não eficiência). Extrapolando a inclinação do platô do AdamW
(−0,016 por 1.500 passos), 0,05 nats valem ~4.700 passos ≈ **1,3× de tokens** — *post-hoc*,
vai rotulado assim.

⭐ **Veredito: ADOTAR o Muon no próximo pré-treino.** É a primeira troca de otimizador do projeto
que sai do ruído. O que este gate NÃO mostra: 1B params, 64k multilíngue, 4–8× Chinchilla — o
`--otimizador muon` já está no `pretrain.py` sem tocar o caminho AdamW dos runs publicados, e a
confirmação na escala seguinte é o primeiro marco do próximo run, não outro gate.

## Gate #6 — repetição de idioma escasso em denso (2609.11917) — ✅ FECHADO (2026-09-17)

**O artigo afirma:** modelo denso tolera repetir dado até R≈8 com degradação "leve" e só degrada
com força além de R≈64; misturar o domínio repetido com um domínio grande não repetido e
semanticamente próximo protege. Medido entre **gêneros em inglês**; aqui, entre **idiomas**.

**Desenho (declarado antes de rodar):** Bee-50m com vocab 64k (67,3M params), lr fixo 2,5e-3 em
todos (§2d), val = holdout limpo de jpn (sha1 % 100 < 2, 2,86M tokens). 2×2 fatorial + piso + R=3:

| braço | dados | val jpn (nats) |
|---|---|---:|
| jpn_unico s42 / s43 | 1,0B únicos | 3,3303 / 3,3408 |
| jpn_rep3 s42 | 333M × 3 = 1,0B | 3,4084 |
| jpn_rep8 s42 / s43 | 125M × 8 = 1,0B | 3,4611 / 3,4616 |
| jpn_unico_mix s42 | 1,0B únicos + 1,0B PT únicos | 3,4492 |
| jpn_rep8_mix s42 | 125M × 8 + 1,0B PT únicos | 3,5277 |

Piso de ruído (máx |s42 − s43|): **0,0105**. Pod `bee-gates` (5090), 7 braços, 21 h, ≈ US$ 21.
Artefato: `gate6-repeticao-jpn-50m-2026-09-17.json`.

| pergunta (critério: |Δ| > piso) | Δ | veredito |
|---|---:|---|
| (1) penalidade de R=8, sozinho | **+0,126** | 12× o piso — **não é "leve"** |
| (4) penalidade de R=3, sozinho | **+0,052** | 5× o piso — tolerável, não grátis |
| (2) penalidade de R=8 na mistura | +0,079 | a mistura corta 38% (**+0,047 de proteção, além do piso**) |
| (3) efeito do PT ao lado, sem repetição | **+0,114** | o PT **piora** o jpn — o oposto do artigo |

**Curva de penalidade por R: 1 → 0 · 3 → +0,052 · 8 → +0,126** (côncava: cada dobra de R custa
menos que a anterior, mas R=8 já custa o equivalente a jogar fora ~40% do treino de jpn — pela
inclinação do platô do braço único, +0,13 nats ≈ 6.000 passos dos 15.000). A penalidade **cresce
com os passos** (R=8: +0,04 no passo 2,5k → +0,13 no fim; R=3: estabiliza em ~+0,04 até o
decaimento e fecha em +0,05) e o rep8 termina com loss de treino 2,87 contra val 3,46: decorou.

⭐ **O que muda no plano do próximo run:**
1. **O déficit de dado não-PT é bloqueio para 143–170B tokens no pt-50 atual** (R≈7–9 por idioma
   ≈ +0,12 nats em cada um). Para **63B** (R≈3) fica em +0,05 — tolerável. A saída barata é
   **coletar mais não-PT antes de aumentar o orçamento** (o fineweb-2 tem muito além do prefixo de
   1,43B por idioma que pegamos; custa CPU, não GPU).
2. **Em 67M, dividir capacidade com uma escrita distante custa mais que repetir.** Isso é o
   contrário do "mistura regulariza" do artigo — que mediu gêneros próximos. Para o Bee-1G isso
   é o *mecanismo* por trás do que o T2 já tinha medido (a mistura troca 3,5× a favor do PT, e
   quem paga é CJK/árabe). Não transfere direto ao 1B: o custo de dividir cai com a escala e a
   penalidade de repetição também (artigo) — a confirmação é o bpb por idioma do run atual contra
   um run futuro com mais dado, não outro gate de 50M.
3. A mistura protege parcialmente: se repetir for inevitável, repetir **dentro** de um corpus com
   PT único é melhor que repetir isolado — mas isso não compensa o custo de dividir capacidade.

⚠️ **O que este gate não mostra (§2q):** 1B params; R entre 8 e 64; os outros 6 idiomas (jpn é o
caso mais distante do PT — espanhol/francês podem se comportar como os "gêneros próximos" do
artigo); a diluição real de 7% do pt-50 (aqui 50/50, para isolar o mecanismo); e o efeito no PT.
Duas sementes só nos braços sozinhos; mix e rep3 com uma. Um empate não refutaria o artigo; o que
se mediu é que o cenário do Bee está fora do regime "leve" dele.

## Lote 2 — ✅ FECHADO (2026-09-17): #3 em 09-14, #1 em 09-16, #6 em 09-17 — ≈ US$ 42 de GPU nos três

- **#1 Muon × AdamW (× Musec)** no Bee-150M, 2 sementes — decide o otimizador do próximo pré-treino.
- **#3 catálogo perturbado + recusa sem template** no corpus agêntico, 3 sementes — ataca os 130
  erros do #4b pelo mecanismo (§2u, §2ab).
- **#6 repetição em denso** — mini-run com idioma minoritário repetido; decide se o déficit de
  13–53× de dado não-PT é bloqueio.
