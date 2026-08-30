# 🐝 BEE — uma LLM em português, treinada do zero

**O que é:** um modelo de linguagem construído **do zero** — tokenizador nosso, arquitetura nossa,
corpus montado por nós, pesos inicializados aleatoriamente e treinados por nós. A aposta é o
**português**: é o único lugar onde um modelo pequeno nosso pode ganhar de alguém.

> ## 🤗 Modelos publicados
>
> **Base:** [`BrCamp/bee-350m-pt-base`](https://huggingface.co/BrCamp/bee-350m-pt-base) — 345M, pré-treinado do zero em português, **0,8207 bpb**
>
> **Dois adapters agênticos, medidos com 3 sementes cada, na mesma régua — e a escolha entre eles é de perfil:**
>
> | | [`bee-350m-pt-agentico`](https://huggingface.co/BrCamp/bee-350m-pt-agentico) | [`bee-350m-pt-assistente`](https://huggingface.co/BrCamp/bee-350m-pt-assistente) |
> |---|---:|---:|
> | executou e cumpriu | **74,0% ± 1,9** | 68,1% ± 1,3 |
> | chamou quando não devia | 17,2% ± 0,4 | **14,6% ± 0,4** |
> | tradução en→pt (chrF2) | 17,97 — *abaixo* do piso 21,54 | **27,47** |
> | resumo — cobertura | 12,4% | **72,8%** |
>
> ⚠️ O `agentico` recusa qualquer tarefa que não seja chamada de ferramenta — inclusive um
> pedido de tradução. O `assistente` responde, ao custo de 5,9 pp de execução.
>
> **Geração anterior (151M):**
> [`bee-150m-pt-base`](https://huggingface.co/BrCamp/bee-150m-pt-base) — 21,7B tokens, 0,844 bpb ·
> [`bee-150m-pt-sft-v2`](https://huggingface.co/BrCamp/bee-150m-pt-sft-v2)
>
> ⚠️ Leia as limitações do card antes de usar: são modelos de 151M e 345M. Escrevem português
> bem e **inventam fatos com confiança**. Use onde o conhecimento vem no contexto.

**Onde estamos (2026-08-30).** O Bee-350M está pré-treinado (21,75B tokens, **US$ 140**), tem as
**nove capacidades medidas com piso trivial ao lado de cada uma**, e passou por um ciclo agêntico
de doze estágios que terminou em dois adapters publicados. O custo total de pós-treino foi
**US$ 0,66** — todo o resto rodou na RTX 5070 local.

⭐ **Antes de treinar qualquer Bee novo, leia [docs/licoes-de-metodo.md](docs/licoes-de-metodo.md)
e `~/.claude/rules/bee-pretreino-licoes.md`** — os defeitos que este projeto pagou têm todos o
mesmo modo de falha: **nada dá erro, a loss cai bonito, e o número sai**.

> ## 🔴 Leia isto antes de qualquer coisa: **[docs/licoes-pretreino.md](docs/licoes-pretreino.md)**
>
> Por duas semanas este README dizia que o Gate 2 tinha falhado. A causa não era o corpus, nem a
> arquitetura, nem a escala — era **uma linha**:
>
> ```python
> x, y = janelas[:, :-1], janelas[:, 1:]      # y JÁ deslocado
> perda = modelo(input_ids=x, labels=y).loss   # e o Llama desloca DE NOVO
> ```
>
> `LlamaForCausalLM(labels=L)` desloca por dentro. O Bee foi treinado para prever **t+2** e medido
> prevendo **t+1** — uma tarefa que nunca aprendeu. **O bug não dá erro:** a loss cai, a perplexidade
> de validação cai, tudo parece saudável, porque a validação usa a mesma convenção errada.
>
> Corrigido (`labels=x`), com **10× menos dados**, o bpb foi de **2,218 → 1,021**.

---

## ⭐ Bee-350M — o pré-treino (2026-08-19)

Detalhe: **[docs/bee-350m-resultado-final.md](docs/bee-350m-resultado-final.md)**

115,48 h de RTX 5090 (**US$ 117,8**) mais o fork de decaimento (US$ 22,4) = **US$ 140,2**.
Holdout limpo, parquet [40], o mesmo texto de sempre. **Menor é melhor.**

| modelo | tokens | tok/param | **bpb PT** |
|---|---:|---:|---:|
| ⭐ **Bee-350M final** | **21,75B** | **63** | **0,8207** |
| Bee-150M final (âncora) | 21,75B | 143 | 0,8438 |
| Tucano-160m (PT nativo, ~200B tokens) | ~200B | — | 0,884 |
| SmolLM2-135M (~2T, inglês) | ~2T | — | 1,551 |

⚠️ **O gate declarado antes de gastar era bpb < 0,80. Não passou, por 0,0207** — e o motivo não
é o que o plano previa.

### 🔴 Os tokens pararam de pagar; a escala não

Fork e run principal, mesmo modelo, mesmo corpus, mesma forma de decaimento:

| | tokens | bpb |
|---|---:|---:|
| fork | 15,00B | 0,8223 |
| principal | 21,75B | **0,8207** |
| **+45% de dado** | | **0,19% melhor** |

**Quarenta e cinco por cento mais dado renderam 0,19%. Ir de 151M para 345M rendeu 2,76%**, com
3,3× menos tokens por parâmetro. O plano dizia que não passar de 0,80 significaria *"o corpus é
o gargalo"*; a medição diz o contrário — **o próximo degrau é parâmetro, não token.**

⚠️ E os marcos de 1B a 15B são **todos de platô** do WSD: não formam curva de scaling utilizável.
Comparar marcos de schedules diferentes mede o schedule, não o modelo — ver
[docs/fork-decaimento-resultado.md](docs/fork-decaimento-resultado.md).

---

## ⭐ O baseline das nove capacidades — antes de qualquer pós-treino (2026-08-20)

Detalhe: **[docs/baseline-350m-resultado.md](docs/baseline-350m-resultado.md)** ·
réguas e pisos: **[docs/reguas-e-pisos-e0.md](docs/reguas-e-pisos-e0.md)**

Sem o número de partida, *"melhorou"* é opinião. ⭐ **E cada capacidade vem com o seu piso
trivial no mesmo arquivo** — sem piso, a pergunta errada fica em aberto (*"55% é bom?"*); com
piso, ela se responde sozinha.

| capacidade | Bee-350M base | piso trivial |
|---|---|---|
| tradução en→pt | chrF2 **51,1** · BLEU 27,1 | copiar a fonte = **21,5** |
| tradução pt→en | chrF2 **43,3** · BLEU 19,6 | copiar a fonte = **22,7** |
| matemática | `pass@256` **22,0%** | gate 3% → aprovado |
| instrução (IFEval-PT) | **30,4%** por instrução | — |
| sentimento | **49,7%** | léxico de 60 palavras = **79,0%** 🔴 |
| resumo | **0,0%** útil | LEAD-2 = **51,3%** 🔴 |
| atendimento | **0,0%** útil | regra + regex = **60,4%** 🔴 |
| código (interno e HumanEval-XL) | **0,0%** pass@1 | — |
| agêntico | **0,0%** | — |

🔴 **Quatro capacidades perdem para um piso que não usa modelo nenhum.** O que o base faz bem é
tradução; o resto está abaixo do trivial ou em zero.

---

## ⭐ O ciclo agêntico E8 → E19 (2026-08-24 a 30)

Relatórios: **[docs/relatorio-agentico-2026-08.md](docs/relatorio-agentico-2026-08.md)** (E8–E17) ·
**[docs/e13-o-que-quebrou.md](docs/e13-o-que-quebrou.md)** (E18) ·
**[docs/e19-forma-da-classe-negativa.md](docs/e19-forma-da-classe-negativa.md)** (E19)

Doze estágios, **US$ 0,66** de custo total (um professor aberto para reescrever 4.421 exemplos);
o resto rodou local. Quatro intervenções adotadas, seis reprovadas por medição.

### O que foi adotado

| intervenção | ganho | por quê |
|---|---:|---|
| **restrição de chave ao esquema** | +16,4 pp | o modelo escreve `receptor` onde o esquema diz `recipient` |
| **restrição do nome da ferramenta** | +2,3 pp | ele inventa `executar_program`; e zera saída inexecutável |
| **diversidade de cadeia arbitrária** | +12 pp de cópia | 724 e-mails no corpus, **22 distintos** |
| **negativos com resposta útil** | ver abaixo | 91,1% dos negativos eram recusas |

### 🔴 O achado que produziu os dois adapters

O corpus tem 4.421 exemplos **negativos** — pedidos sem ferramenta aplicável. **91,1% deles eram
recusas**, sempre na mesma fórmula. O modelo generalizou *"sem ferramenta → recuse"* para
qualquer tarefa: um pedido de tradução era respondido com *"não consigo traduzir com as
ferramentas disponíveis"*.

Três braços, 698 passos cada, 3 sementes:

| | A: recusas (39,6%) | B: sem negativos | C: úteis (39,1%) |
|---|---:|---:|---:|
| executou e cumpriu | **74,0%** | 78,4% | 68,1% |
| over-calling | 17,2% | 🔴 **84,7%** | **14,6%** |
| resumo — cobertura | 12,4% | 58,4% | **72,8%** |
| tradução en→pt (piso 21,54) | 17,97 | 13,94 | **27,47** |

⭐⭐ **A classe negativa acumulava três funções:** marcar quando não chamar, fornecer o único
texto livre variado do corpus, e — sem necessidade nenhuma — ensinar a recusar. Remover a classe
remove as três; trocar só a **forma** resolve. Os braços A e C são os dois modelos publicados.

### As reprovações que valem tanto quanto as adoções

- 🔴 **Restringir o VALOR na decodificação**, duas versões, **−9,0 pp e −15,8 pp**. Restrição de
  decodificação não conserta incapacidade, só troca a forma do erro. Ficam no código, desligadas.
- 🔴 **Laço de verificar-e-retentar**: o executor aceita **95,3%** das chamadas e só 62,4% estão
  certas. Verificador que aceita quase tudo não verifica nada.
- 🔴 **Escalar não conserta seleção em catálogo grande**: de 151M para 345M a queda relativa foi
  de 45% para 39%. ⭐ O que conserta é **filtrar antes de perguntar** — um recuperador lexical de
  30 linhas leva o acerto de 48,5% para **75,2%**, sem treinar nada.

---

## 🔴 Os defeitos de instrumento — o que este projeto mais produziu

Todos com o mesmo modo de falha: **nada dá erro**. A lista completa e transferível está em
`~/.claude/rules/bee-pretreino-licoes.md` (§1 a §2ab). Os que custaram mais caro:

| defeito | sintoma | custo |
|---|---|---|
| deslocamento duplo de rótulos | loss cai, tudo saudável | **2 semanas, US$ 34** |
| amostragem com reposição | — | **37% do corpus nunca entrou** |
| `max_seq_len` curto no SFT | treino roda normal | **100% do agêntico descartado** |
| régua sem token de parada | 0,0% num modelo que acerta | 0/85 → 62,5% sem retreinar |
| régua medida em texto cru num modelo ChatML | conclusão **invertida** | "quase nada quebrou" × "quebrou tudo" |
| pareado com régua mal configurada | 3,2% nos **dois** braços | o real era 71,8% |

⭐ **O invariante que pagou duas vezes:** *previsão idêntica à referência não pode reprovar.*
Custa uma comparação por caso e pegou uma régua quebrada que o desenho pareado não pegaria — um
número errado **igual nos dois braços** passa como "inalterado".

⭐ **E a regra de método que vale mais que todas:** quando dois experimentos internos se
contradizem por margem absurda, **o defeito está no aparato, não no fenômeno**.

---

## Histórico — o Bee-150M

### ⭐ GATE 1 — fertilidade do tokenizador: **APROVADO** (2026-07-27)

Fertilidade = tokens por palavra. **Menor é melhor.** Holdout de 400 docs PT + 400 EN,
**disjuntos do treino do tokenizador**.

| tokenizador | vocab | **PT** | EN |
|---|---:|---:|---:|
| **Bee (nosso)** | 32.000 | **1,416** | 1,450 |
| Qwen3.5-4B | 248.044 | 1,496 | 1,334 |
| SmolLM2-135M | 49.152 | 2,241 | 1,344 |

**−5,4% em PT contra o Qwen; −36,8% contra o SmolLM2** — com vocab **7,8× menor**. Custo:
**4 minutos de CPU**. **O tokenizador é a parte que funcionou desde o primeiro dia.**

### ⭐ GATE 2 — o Bee-150M bate o SmolLM2 e o Tucano (2026-08-12)

| tokens | 1B | 3B | 6B | 10B | 15B | 21B | final |
|---|---:|---:|---:|---:|---:|---:|---:|
| **bpb** | 1,021 | 0,947 | 0,920 | 0,897 | 0,870 | 0,845 | **0,844** |

Curva **medida**, não extrapolada. ⚠️ **A previsão pré-registrada falhou o próprio critério de
aceite** — em [docs/previsao-marco-10B.md](docs/previsao-marco-10B.md) a lei `L(D)=E+A·D^-α` foi
registrada antes de medir com tolerância de ±0,015, e no marco de 15B errou por 0,0161, para o
lado bom. O critério foi honrado e as projeções, descartadas: um critério pré-registrado que
ganha exceção depois de ver o resultado não serve para nada.

### O Bee-150M agêntico (2026-08-13)

Detalhe: **[docs/agentico-medicao.md](docs/agentico-medicao.md)** ·
**[docs/multiturno-adapter.md](docs/multiturno-adapter.md)** ·
**[docs/teto-passk-medido.md](docs/teto-passk-medido.md)**

- ⭐ **Capacidade é disputada em 151M.** Multi-turno por full fine-tune custou **−5,9 pp** de
  execução single-turn; em **adapter LoRA** custou **zero** e ficou melhor no alvo.
- ⭐ **Autoaprendizado fecha, e o teto não se move.** Com n=128 e o holdout limpo, o ganho decai
  monotonicamente até zero: `pass@1` +5,07 pp, `pass@128` **+0,00 pp**.
- ⚠️ **O `verifier.py` piorava o sistema havia semanas** (saldo −4: bloqueava 7 chamadas boas
  para consertar 4 ruins). Ninguém sabia porque só se media o ganho.

### 🔴 HISTÓRICO — as seções inválidas

> Os números do Gate 2 de 2026-08-03 e da investigação de 08-04 foram produzidos pelo modelo com
> **deslocamento duplo de rótulos**. **Preservados porque a mecânica do erro vale mais que os
> números** — cinco hipóteses rigorosas foram construídas sobre um artefato, e as refutações de
> geometria e LR estavam certas. Ver [docs/licoes-pretreino.md](docs/licoes-pretreino.md).
>
> O mesmo vale para a varredura de LR do SFT (ótimo aparente 1e-3): remedida sobre a base
> correta, o ótimo é **6e-4**. A lição continua válida — a intuição *"modelo pequeno, passo
> pequeno"* é invertida, e parar a varredura antes de ver a curva subir promove vencedor falso.

---

## Fonte de currículo: a BNCC (e por que não os livros)

Um estudo multiagente avaliou 91 PDFs de livros didáticos (2,9 GB) como fonte de ensino.
**Veredito: os livros não; o currículo sim — e ele é público.**
Ver [docs/estudo-curriculo/00-CONSOLIDADO.md](docs/estudo-curriculo/00-CONSOLIDADO.md).

**A base legal, com artigo:**
- **Lei 9.610/98, art. 8º, IV** — não são protegidos *"leis, decretos, regulamentos… e demais atos
  oficiais"*. A **BNCC é o Anexo da Resolução CNE/CP nº 2/2017**. Logo: **fora do regime autoral**.
- **art. 7º, §3º** — *"no domínio das ciências, a proteção recairá sobre a forma literária, não
  abrangendo o conteúdo científico"*. É a base de **reescrever é legal, copiar não**.

⚠️ **Armadilhas verificadas:** o rodapé gov.br declara **CC BY-ND** — não afeta a BNCC, mas
**afeta os itens de prova do ENEM**. E os microdados do ENEM não são CC-BY.

---

## Regras duras do projeto

- ⛔ **Procedência dos dados é requisito de negócio.** Cada shard carrega fonte e licença no
  `MANIFEST.json`. **Scribd está fora** — estar logado dá acesso para *ler*, não licença para
  *treinar e publicar*. **GitHub raspado direto está fora.**
  - ⚠️ **Rótulo de licença não é prova.** Cadeia quebrada achada: brWaC declara *"solely for
    academic research"* → CrawlPT não declara nada → GigaVerbo aparece como CC BY 4.0.
    **Ler a licença na origem, sempre.**
- ⛔ **Nunca** treinar com saídas de GPT/Claude/Gemini. Destilação só de professores abertos —
  `assert_teacher_allowed()` falha alto e cedo. (Ele já nos barrou uma vez, e estava certo.)
- **Holdout por hash, nunca por posição** — e por **componente conexo** de tudo que é
  compartilhado, com verificação posterior sobre os arquivos finais.
- **n do holdout contado em itens distintos, não em linhas.** "600 casos" já foram 600 cópias de
  87 problemas.
- **Duas sementes alertam, três decidem** — e a dispersão se compara ao erro amostral da
  diferença antes de culpar o treino.
- **Toda intervenção que bloqueia exige medir os DOIS lados.**
- **A config de uma rodada se lê no artefato dela**, nunca no model card nem nos defaults.
- **Medir antes de acreditar — inclusive em si mesmo.**

---

## Arquiteturas

Llama-style via `LlamaConfig`, **sem código de modelagem custom** — PEFT, TRL, vLLM e nossos
evals funcionam sem uma linha de adaptação.

| | **Bee-350M** | Bee-150M |
|---|---|---|
| camadas × d_model | **32 × 960** | 30 × 576 |
| intermediate (SwiGLU) | 2560 | 2048 |
| atenção (GQA) | 15q / 5kv | 9q / 3kv |
| vocab · seq_len | 32.000 · 2048 | 32.000 · 2048 |
| params | **345M** | 151M |
| schedule de LR | **WSD** | cosine |

✅ A geometria do 150M é byte a byte a do SmolLM2-135M e do MobileLLM-125M; a do 350M é a do
SmolLM2-360M. **A arquitetura nunca foi o problema** — a correção de 2026-08-08 levou o mesmo
config de 2,218 para 1,021 bpb sem alterar uma linha dele.

---

## Notas de hardware que custaram tempo

**Pré-treino: RunPod.** Três pegadinhas: `transformers` **não** vem na imagem "RunPod PyTorch";
`/workspace` é network-fs (~70k tok/s contra 85k do disco local); `gdown --folder` em pasta
grande bate rate-limit do Drive. Checkpoint em disco **persistente** (volume de rede, não o disco
do container).

**Local: RTX 5070 Laptop 8 GB.** O micro-batch tem teto rígido em 2, e o vilão não são os pesos —
é o **tensor de logits** `batch × seq × 32000` mais o upcast fp32 da cross-entropy:

| micro-batch | tempo/passo | VRAM |
|---:|---:|---:|
| **2** | **0,31 s** | 5,78 GB ✅ |
| 4 | 4,02 s | 10,67 GB — vaza pra RAM |
| 8 | **510 s** | estouro total |

⚠️ **O sintoma de estouro não é OOM, é lentidão silenciosa.**

⚠️ **Container ≠ máquina:** `free` e `nproc` mostram o host. Dimensionar por eles faz o OOM
killer matar workers em silêncio (custou 3 h).

---

## Estrutura

```
├── bee/                    ⭐ O MODELO, do zero
│   ├── build_corpus.py     #  coleta com manifesto de procedência + auditoria de mistura
│   ├── train_tokenizer.py  #  BPE ByteLevel 32k + ⭐ GATE 1 (fertilidade vs. rivais)
│   ├── prepare_data.py     #  tokenização → train.bin/val.bin (shards fora do treino)
│   ├── config.py           #  arquitetura — o mesmo arquivo em toda a escada
│   ├── pretrain.py         #  pesos aleatórios → modelo (guarda de rótulos ABORTA antes do passo 1)
│   ├── eval_gate2.py       #  ⭐ GATE 2 — bits-por-byte vs. SmolLM2
│   └── chat.py             #  conversa e sondagem (`--sonda`)
│
├── comeia/                 O MÉTODO de especialização, hoje sobre o Bee
│   ├── data/               #  corpus agêntico, diversificação, negativos úteis
│   ├── train/              #  SFT/DPO via QLoRA
│   └── eval/               ⭐ as réguas — e é onde mora o rigor
│       ├── baseline_8_capacidades.py  #  as 9 capacidades, com piso ao lado de cada uma
│       ├── eval_agentic_exec.py       #  tool-use por EXECUÇÃO num mundo simulado
│       ├── esquema.py                 #  restrições de decodificação (chave · ferramenta · valor)
│       ├── recuperar_catalogo.py      #  filtra o catálogo ANTES de perguntar (+26,7 pp)
│       └── argumentos.py              #  classes de argumento MEDIDAS, não declaradas
│
└── docs/                   estudos, avaliações e o histórico
    ├── bee-350m-resultado-final.md    ⭐ o pré-treino do 350M
    ├── baseline-350m-resultado.md     ⭐ as 9 capacidades antes do pós-treino
    ├── relatorio-agentico-2026-08.md  ⭐ E8 → E17
    ├── e13-o-que-quebrou.md           ⭐ E18 — o que o pós-treino custou
    ├── e19-forma-da-classe-negativa.md ⭐ E19 — os dois adapters
    ├── licoes-pretreino.md · licoes-de-metodo.md
    └── estudo-curriculo/              12 documentos: 91 PDFs + papers + web
```

---

## Como rodar

```bash
# Tokenizador + Gate 1 (CPU, ~4 min) — sai com código 1 se o tokenizador não ganhar em PT
python bee/train_tokenizer.py --corpus bee/corpus --vocab 32000

# Gate 2 — bits-por-byte contra o SmolLM2
python bee/eval_gate2.py --bee <modelo> --rival HuggingFaceTB/SmolLM2-135M

# ── O BASELINE, ANTES DE TREINAR QUALQUER COISA ──
# 9 capacidades com piso trivial ao lado de cada uma. ~50 min na 5070, US$ 0.
python comeia/eval/baseline_8_capacidades.py --dry-run   # valida as réguas, sem GPU
python comeia/eval/baseline_8_capacidades.py             # o modelo base, em texto cru

# ⚠️ modelo pós-treinado SE MEDE EM ChatML — o script ABORTA sem --chat
python comeia/eval/baseline_8_capacidades.py --chat --peft comeia/models/<adapter>

# ── TREINAR ──
python comeia/train/sft_qlora.py --model BrCamp/bee-350m-pt-base \
  --data comeia/data/processed/treino_e19c_neg_uteis.jsonl \
  --out comeia/models/meu-adapter --max-steps 698 --lr 1.2e-3 \
  --batch-size 1 --grad-accum 16 --lora-r 16 --lora-alpha 32 --seed 42

# ── AVALIAR (o que decide, e não a loss) ──
# ⚠️ a config de referência vai TODA na linha: sem --por-argumento o número cai de 71,8% para 3,2%
python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-350m-pt-base \
  --peft comeia/models/meu-adapter --data comeia/data/processed/holdout_balanceado.eval.jsonl \
  --k 1 --chat --parar-controle --restrito --restrito-ferramenta \
  --por-argumento --lote 16 --max-len 1700

# Conversar (SEMPRE com o catálogo no system, senão ele não sabe que a ferramenta existe)
python bee/chat.py --system comeia/data/agentic_system.txt
```

---

## Próximos gates

- [x] ⭐ **Gate 1 — tokenizador** mais eficiente em PT que Qwen e SmolLM2 · 4 min · +5,4%
- [x] ⭐ **Corrigir o pipeline de treino** — `labels=x`, amostragem sem reposição, guarda que
      **aborta** antes do passo 1
- [x] ⭐ **Bee-150M** — 21,7B tokens, 0,844 bpb, passa Tucano-160m e SmolLM2-135M
- [x] ⭐ **Bee-350M** — 21,75B tokens, **0,8207 bpb** · ⚠️ gate de 0,80 não passou por 0,0207
- [x] ⭐ **Baseline das 9 capacidades com piso trivial** antes de qualquer pós-treino
- [x] ⭐ **Ciclo agêntico E8→E19** — 2 adapters publicados, US$ 0,66 de custo total
- [ ] ⭐ **Próximo degrau é PARÂMETRO, não token** — medido: +45% de dado rende 0,19%,
      151M→345M rende 2,76%
- [ ] **As capacidades que seguem em zero:** `atendimento` útil (0% em todos os artefatos) e
      **código** (0% pass@1). Nenhuma intervenção do eixo agêntico as toca
- [ ] **Sentimento sem mecanismo** — a pontuação sobe com a quantidade de *recusa* no corpus
      (81,8 / 69,5 / 55,3 / 56,0 nos quatro braços do E19). Aberto
- [ ] **Coletar pool bruto ~100B e filtrar a 10%** — filtrar sozinho não resolve: filtrar não
      substitui coletar, multiplica
- [ ] **ENEM como eval set** — ~3.750 itens públicos com gabarito e parâmetros de TRI

---

## Hardware

- Local: **RTX 5070 Laptop 8 GB** (Blackwell sm_120 — exige PyTorch cu128) · Ultra 9 275HX · 31 GB RAM
- Pré-treino: **RunPod RTX 5090** ($0,99/h)

⭐ **Escolher GPU por `$/bilhão de tokens` medido, nunca por `$/hora`.** Mesmo modelo, mesmo corpus:

| GPU | TDP | tok/s | $/h | **$/B tokens** |
|---|---:|---:|---:|---:|
| **RTX 5090** | 600 W | **62,9k** | 0,99 | **4,37** |
| RTX PRO 4500 | 200 W | 42,1k | 0,74 | 4,88 |
| A100 SXM | 400 W | 70k | 1,59 | 6,31 |

O preditor é o **TDP**, não o preço nem a VRAM. A PRO 4500 tem a mesma VRAM da 5090, custa 25%
menos por hora e sai **36% mais cara por token** — rodava a 99% de utilização usando 12 GB de 32,
cravada em 200,0 W: saturada eletricamente. Nesse regime, batch maior é *pior*, Liger rende **0%**
e `torch.compile` rende **+17%**.

---

## Custo total do projeto

| | US$ |
|---|---:|
| Bee-150M (pré-treino) | 97 |
| Bee-350M (pré-treino + fork de decaimento) | 140 |
| Bee-150M v3 (o run com o bug de rótulos) | 34 |
| Pós-treino agêntico E0→E19 (professor; GPU local) | **0,66** |
| **total** | **~272** |

Última atualização: 2026-08-30.
