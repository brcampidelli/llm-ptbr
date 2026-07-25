# 🐝 A COMEIA — orquestrador local de SLMs especializadas

> Um orquestrador em código coordenando **várias SLMs especializadas** ("abelhas") sobre **um único
> backbone** Qwen3.5-4B, com adapters LoRA trocados a quente. Pesos abertos.
> Plano completo: `~/.claude/plans/estou-pensando-em-desenvolver-partitioned-unicorn.md`

## Tese em uma frase

**A comeia vence por decomposição + roteamento — não por "somar cérebros pequenos".** Ela quebra a
tarefa até virar subtarefas estreitas que uma SLM faz melhor e **10–30× mais barato**, e chama o
modelo forte **só** no raciocínio residual difícil.

### Honestidade sobre o que é hype
- ❌ **"N SLMs pequenas somadas igualam uma LLM grande"** — nenhuma fonte prova isso.
- ✅ **O que a literatura sustenta:** em tarefas estreitas e repetitivas (o grosso do trabalho de um
  agente: parsear, formatar, escolher ferramenta, extrair), uma SLM afinada **iguala ou supera** um
  generalista gigante. Base: NVIDIA, *[Small Language Models are the Future of Agentic
  AI](https://arxiv.org/abs/2506.02153)* — topologia **"Code Agency"**, onde o orquestrador é
  **código**, não um LLM. Casos reais: 40–70% das chamadas de agentes (MetaGPT 60%, Cradle 70%)
  são substituíveis por SLM.
- ⚠️ **O moat não é o modelo** (open-weight virou commodity). É a **orquestração + os dados de
  especialização + o pipeline de fine-tune**.

## A arquitetura

```
query ──► Router (regras + complexidade) ──► escolhe a abelha
                                              │
        ┌─────────────────┬───────────────────┼──────────────────────┐
        ▼                 ▼                   ▼                      ▼
   agentica            coder             chat_ptbr (default)   base_forte (fallback)
   tool-use            código            PT-BR                 raciocínio difícil
   [adapter]           [adapter]         [adapter REAL]         [backbone base]
    FAST                FAST              FAST                   slow
```

**1 backbone carregado UMA vez + N adapters LoRA a quente.** Cada abelha é um adapter → vira
"1 modelo + N personalidades", resolvendo **VRAM e coordenação de uma vez**.

| Item | VRAM medida (L4) |
|---|---|
| Backbone Qwen3.5-4B em 4-bit NF4 | **2,98 GB** de 22 GB |
| Cada adapter LoRA (r=16) | dezenas de MB |
| → **dezenas de abelhas cabem sobre um backbone** | ✅ verificado |
| Abelha multimodal (Fase 4, ~9B separado) | ~6–7 GB (única fora do backbone único) |

## ⭐ A métrica que decide tudo: fração de fast-path

Quantas queries **evitam o modelo caro**. Alta ⇒ a comeia é econômica. Baixa ⇒ é só complexidade.
Medida em toda rota pelo `Router` e reportada ao fim de cada execução.

## 📊 Resultados medidos

### 🎯 Fase 2 — abelha CODER: **+40 pp** nas difíceis, −17,5 pp nas fáceis (held-out limpo, 2026-07-25)

⚠️ **Os números abaixo SUBSTITUEM uma versão anterior contaminada.** O primeiro eval usava
`--limit 60` (as 60 primeiras do arquivo bruto), mas o `05_build_splits` **embaralha** antes de
separar o holdout — logo ~52 dessas 60 estavam no TREINO. Refizemos tudo com held-out real.

**Matriz completa (mesma régua, held-out nunca treinado):**

| Config | Difíceis (60) | Fáceis (40) | Soma |
|---|---|---|---|
| Base | 1,7% | **100,0%** | — |
| 1 época, 100% difícil | 28,3% | 87,5% | 115,8 |
| Misto 30% fáceis, 2 ép. | 36,7% | 77,5% | 114,2 |
| **2 épocas, 100% difícil** | **41,7%** | 82,5% | **124,2** ⭐ |

**Vencedor: 2 épocas, 100% difícil** — 1,7% → **41,7%** nas difíceis (**24×** o base, **+40 pp**),
ao custo de **−17,5 pp** nas fáceis.

**Hipótese da ancoragem: TESTADA E REJEITADA.** Misturar 30% de tarefas fáceis no treino, para
"ancorar" o comportamento antigo, produziu uma config **dominada**: pior nas difíceis (36,7 vs 41,7)
*e* pior nas fáceis (77,5 vs 82,5). Não ancorou nada.

**Quanto do resultado original era memorização:** o "+45 pp" contaminado virou **+40 pp** honesto —
~5 pontos eram o modelo reproduzindo tarefas vistas no treino. E o dano colateral era maior do que
parecia: −17,5 pp, não −10 pp.

📐 **Erro metodológico recorrente do projeto, registrado:** três vezes neste dia tiramos conclusão de
amostra incompleta ou de réguas diferentes — (1) o `--limit 60` que pegava só o começo do arquivo;
(2) declarar "efeito marginal" do filtro em 424/877 quando a metade antiga não tinha as correções;
(3) inferir um "trade-off linear" com 3 das 4 configurações medidas — a 4ª desmentiu. **Regra que
fica: não concluir padrão antes da amostra fechar, e nunca comparar números medidos em condições
diferentes.**

**Como o dataset foi construído:** o gate barrou a 1ª tentativa (base em 93,3%). Construímos então o
filtro **"o base erra"** — só entra a tarefa cuja solução do professor **passa** E o base **falha**.
Resultado: 877 candidatas → **239 tarefas difíceis (27,3%)**. Treino: 216 exemplos, 17 min na L4.
O `coder_tasks_easy.jsonl` (as 638 descartadas por fáceis) virou o **holdout de não-regressão** — sem
ele, reportaríamos o ganho escondendo o preço.

⚠️ O adapter vive em `/content` no Colab (**efêmero** — morre com o runtime). Em vez de depender de
um artefato que some, **o treino é o artefato**: um comando reproduz tudo em ~17 min.

```bash
python colab/reproduce_coder.py --out /content/qwen35-4b-coder   # ou um caminho no Drive
```

O script é **retomável** (pula o filtro caro se `coder_tasks_hard.jsonl` já existir) e traz os
defaults da config vencedora embutidos.

**Registro portável no `bees.json`:** os caminhos usam `${VAR:-default}` — o default fica versionado
e cada máquina sobrescreve com uma variável de ambiente, sem editar o JSON:

```bash
CODER_ADAPTER=models/coder AGENTICA_ADAPTER=models/agentica python orchestrator/run.py --sample
```

### 🛑 A 1ª tentativa da CODER: treino CANCELADO pelo gate (2026-07-25)

**Resultado negativo, documentado de propósito** — evitou repetir o erro mais caro do projeto.

Medimos o **base ANTES de treinar** (`eval/eval_coder.py`, pass@1 por execução, 60 tarefas):

```
⭐ pass@1 (execução): 56/60 = 93,3%
devolveu código     : 60/60 = 100,0%
falhas              : assert falhou 4 (7%) — errou a lógica, nada deixou de compilar
```

| Abelha | score/pass@1 do **base** | Espaço | Desfecho |
|---|---|---|---|
| SFT generalista PT-BR | 0,93 (belebele) | nenhum | 3h de GPU → **0 de 7** ganhos |
| `agentica` | **45,7%** | enorme | **+28,5 pp** ✅ |
| `coder` | **93,3%** | ~nenhum | **treino cancelado** 🛑 |

**Diagnóstico honesto (o erro foi de desenho, não de pipeline):** pedimos ao professor "exercícios
de função Python" e ele gerou **exercícios de livro-texto** (dois ponteiros, Levenshtein, contagem de
frequência, validação de CPF) — tarefas que aparecem milhares de vezes no pré-treino do Qwen. A
validação por execução garantiu que as tarefas eram **corretas**; presumimos que correto implicava
**difícil**. São eixos independentes. Pista que existia e não foi lida na hora: **189 duplicatas** na
geração — o professor convergindo indicava saturação do espaço de tarefas óbvias.

**O que as 4 falhas ensinam (a informação mais útil):** `remover_acentos`, `camel_to_snake`,
`bytes_to_readable`, `teto_sem_math` — todas por `assert falhou`. O 4B escreve código que **roda**,
mas erra **casos de borda** e **detalhes de especificação** (implementar `ceil` sem `math`,
arredondamento de unidades). É esse o dataset que faltava.

**Regra que fica no projeto:** dificuldade tem que ser **medida, não presumida**. Gerar candidatas e
manter só as que **o base erra** — é a regra do Collab-RAG (descartar itens em que todas as amostras
têm a mesma recompensa, porque não ensinam nada), virando currículo automático.

**O gate se pagou:** descobrimos "sem espaço" em **12 min de avaliação e ~US$0,40**, contra **3h de
L4** no caso do SFT PT-BR.

### 🛡️ Verificador determinístico — over-calling cortado pela metade SEM treinar (2026-07-25)

Padrão do **interwhen** (arXiv 2602.11202): verificação de processo no laço, em código.
Mesmo holdout, mesmo adapter, mesma amostra — a única variável é o verificador ligado:

| Métrica | Sem verificador | **Com verificador** | Delta |
|---|---|---|---|
| **Over-calling** (o alvo) | 16,0% | **8,0%** | **−50%** |
| Under-calling | 11,4% | **5,7%** | **−50%** |
| JSON válido | 88,6% | **91,4%** | +2,8 pp |
| Ferramenta certa | 88,6% | **91,4%** | +2,8 pp |
| **Score composto** | 87,4% | **91,6%** | **+4,2 pp** |
| Latência (comeia ponta-a-ponta) | 10,2s | 10,5s | **+3%** ← o custo |

`7 violações detectadas, 5 corrigidas no retry (71%)`

**O que surpreendeu:** esperávamos um trade-off (menos over-calling **às custas** de mais
under-calling). Não houve — **os dois caíram 50%**. Porque o verificador não enviesa numa direção:
checa **as duas** direções da decisão (JSON indevido → corrige para texto; texto indevido → corrige
para JSON).

**Precisão medida ANTES de ligar** (`orchestrator/test_verifier.py`, 150 exemplos rotulados, sem GPU):
**100% ao dizer "não precisa de ferramenta"**, **0 falsos positivos perigosos**, 44,7% dos casos
deixados como `unknown` (não interfere). Esse gate importa: um falso positivo aí *bloquearia uma
chamada legítima e pioraria o sistema*.

**Bônus observado no log:** a abelha inventou uma ferramenta inexistente (`search`); o verificador
pegou a alucinação e devolveu a lista válida do catálogo. Sem ele, a chamada iria para execução e
falharia silenciosamente.

**O caso que resiste:** `write_file` da letra de uma música — a abelha chama a ferramenta certa, mas
o `--max-new 200` corta o JSON no meio. O verificador detecta (`json_truncado`) e pede JSON curto,
mas a letra não cabe. **É limite nosso de tokens, não erro do modelo** — e agora aparece contabilizado
à parte (2,9%) em vez de somado injustamente ao under-calling.

### 🎯 Fase 1 — a abelha AGÊNTICA funcionou (2026-07-25) ✅ **primeiro ganho real do projeto**

Adapter treinado em 1.495 exemplos de tool-use (2 épocas, 2h56 na L4), avaliado no holdout
(`eval/eval_agentic.py`, 60 exemplos: 35 que exigem ferramenta + 25 que não exigem):

| Métrica | Base | **Adapter** | Delta |
|---|---|---|---|
| **JSON válido** (contra o catálogo) | 45,7% | **88,6%** | **+42,9 pp** |
| **Ferramenta certa** (= referência) | 45,7% | **88,6%** | **+42,9 pp** |
| **Under-calling** (deixou de chamar) | 54,3% | **11,4%** | **−42,9 pp** |
| Over-calling (chamou sem precisar) | 4,0% | 16,0% | +12,0 pp ⚠️ |
| **Score composto** | 58,9% | **87,4%** | **+28,5 pp** |

**A abelha quase dobrou a acurácia de tool-calling** e praticamente eliminou o problema central do
base — que era ignorar as ferramentas. Contraste com nossa própria história: o SFT generalista PT-BR
deu **0 de 7** ganhos porque o base já era forte *e* a régua era errada (múltipla escolha). Aqui, com
**abelha especializada + régua certa**, o ganho é inequívoco. É a tese da comeia com número, não com
argumento.

**Custos honestos:**
- **Over-calling subiu (4% → 16%):** a abelha ficou mais afeita a chamar ferramenta, errando em 4 dos
  25 casos conversacionais. Trade-off real — mas trocamos ~3 erros novos por ~15 acertos novos.
  **Não houve colapso de modo** (ainda responde em texto em 84% dos casos de texto; entropia final
  0,2765, longe dos 0,076 do run com loss contaminada).
- **O 87,4% está SUBESTIMADO.** Inspecionando as falhas uma a uma, várias não são erro do modelo:
  rótulos errados no dado (ex.: "crie um evento na agenda" marcado como `text`, quando chamar
  `create_calendar_event` é o certo), casos ambíguos marcados como `tool_call` em que a abelha
  corretamente pediu esclarecimento, **1 JSON truncado** pelo `--max-new 200` no meio de uma escrita
  longa (a ferramenta estava certa), e **1 semente contaminada** com o meta-prompt do gerador.
  Corrigido: o eval agora separa `truncado` de `under-calling`, e o filtro do `07b` rejeita
  meta-prompt vazado (6 sementes removidas de 1.690).

⚠️ **Lição de configuração:** `save_total_limit=2` apagou o checkpoint-120, então a comparação
"época 1 vs época 2" ficou inviável (sobraram 180 e 188, próximos demais). Para as próximas abelhas,
subir esse limite — a curva sugeria que a época 2 rendeu pouco, e isso valia ser medido.

### Fase 0 — a comeia rodando na L4 (2026-07-24) ✅
```
⭐ FRACAO DE FAST-PATH: 80.0%  (8/10)
   chat_ptbr 4 (40%) · coder 2 (20%) · agentica 2 (20%) · base_forte 2 (20%)
latencia media: 18.3s  (min 10.1s / max 24.2s)
```
Backbone carregado 1× (2,98 GB), adapter real da `chat_ptbr` por cima, hot-swap em 10/10 gerações,
roteamento correto em todas (código→`coder`, tool-use→`agentica`, difícil→`base_forte`).

### O experimento que MATOU a hipótese generalista (e mudou o projeto)
SFT generalista PT-BR, **5.657 exemplos** destilados, avaliado a **n=300** (poder estatístico real):

| Task | Baseline | SFT-v2 | Delta | Veredito |
|---|---|---|---|---|
| `assin_paraphrase` | 0,680 | 0,723 | +0,043 | ruído |
| `assin_entailment` | 0,563 | 0,583 | +0,020 | ruído |
| `hellaswag_pt` | 0,600 | 0,610 | +0,010 | ruído |
| `truthfulqa_pt_mc2` | 0,484 | 0,486 | +0,002 | ruído |
| `arc_pt` | 0,563 | 0,560 | −0,003 | ruído |
| `xwinograd_pt` | 0,776 | 0,768 | −0,008 | ruído |
| `belebele_por_Latn` | 0,913 | 0,900 | −0,013 | ruído |

**Ganhos: 0 · Regressões: 0 · 7/7 dentro do ruído** (limiar ≈ ±7,5pp a n=300).

**Leitura honesta:** não é bug — é achado. Uma base instruct já forte (Qwen3.5-4B) **não melhora com
mais destilação de instrução genérica**. Além disso, benchmark de múltipla escolha mede
*conhecimento*, que SFT não adiciona. Conclusão: o valor não está em "um Qwen um pouco melhor" —
está em **especialização + orquestração**. Daí a comeia.

*(Histórico: SFT-v1 com 1.840 exemplos a n=100 deu o mesmo resultado, mas sem poder estatístico para
concluir. Por isso repetimos com 3× mais dados e n=300.)*

## As abelhas

| Abelha | Foco | Estado |
|---|---|---|
| `chat_ptbr` | chat/generalista PT-BR | ✅ **adapter real** (SFT-v2, 5.657 ex) |
| `agentica` | tool-use / seguir instrução | ✅ **adapter real e VALIDADO** (1.495 ex, +28,5 pp vs base) |
| `coder` | funções Python verificáveis por execução | ✅ **treinada e validada em held-out limpo**: +40 pp nas difíceis (1,7%→41,7%, 24×), −17,5 pp nas fáceis. Adapter efêmero — reproduzível em 17 min |
| `base_forte` | fallback do raciocínio difícil | ✅ backbone base (futuro: 7–11B/nuvem) |
| multimodal | imagem/áudio | ⏳ Fase 4 — modelo **separado ~9B** (Qwen3.5-VL) |

### Abelha agêntica — o dado ensina 3 comportamentos, não 1
| Comportamento | Exemplos | % |
|---|---|---|
| pedido exige ferramenta → JSON `{"tool","args"}` | 886 | 59% |
| pedido **não** exige → resposta direta em texto | 609 | **41%** |
| pedido ambíguo → pede o que falta, não inventa | (incluído acima) | — |

Os 41% sem ferramenta são **de propósito**: *over-calling* (chamar ferramenta para tudo) é a falha
clássica de modelo agêntico. Validação dura contra o catálogo (`data/agentic_tools.json`):
ferramenta tem que existir, args obrigatórios presentes, nenhum arg desconhecido — **2,8%
rejeitados** vão para `.rejects.jsonl` e não treinam.

## 🐛 Bugs reais encontrados por RODAR (não por revisar)

1. **`apply_chat_template` devolve `BatchEncoding` no transformers 5.x** — não tensor puro.
   `generate()` quebrava com `AttributeError`. Estava **latente também** no `quantibias_gate.py`.
2. **O professor errou uma conta e respondeu de cabeça:** `48239 × 1177` → devolveu 56.757.303
   (correto: **56.777.303**) em texto, em vez de usar a `calculator`. O validador de JSON não pega
   (a resposta nem era JSON). Corrigido com regra explícita no prompt **+** guard
   `looks_like_hard_math()` que rejeita aritmética de 3+ dígitos feita de cabeça.
3. **O Qwen3.5 gasta os tokens raciocinando** (`<think>`) e a resposta final truncava. Agora
   `enable_thinking=False` por padrão + `strip_think()` como rede (trata bloco fechado, fechamento
   órfão e bloco **aberto/truncado**, onde não existe resposta e o sistema avisa em vez de fingir).

## Estrutura
```
├── orchestrator/   # 🐝 A COMEIA — registry, engine (hot-swap), router, CLI
│   ├── bees.json   #    registry das abelhas (adicionar abelha = editar o JSON)
│   ├── hive.py     #    backbone 1× + hot-swap de adapters LoRA
│   ├── router.py   #    roteador determinístico + fração de fast-path
│   └── run.py      #    CLI: chat / batch / --route-only (testa rota SEM GPU)
├── data/           # pipeline de dados (destilação, self-instruct, preferências, agêntico)
├── train/          # SFT e DPO via QLoRA
├── eval/           # harness PT-BR (lm-eval), comparação com significância, gate QuantiBias
├── colab/          # receita da L4 (Colab Pro+)
└── models/         # checkpoints (ignorado no git)
```

## Como rodar

**Testar o roteamento SEM GPU** (valida rota + métrica de graça, roda em qualquer máquina):
```bash
python orchestrator/run.py --route-only --sample
```

**A comeia de verdade** (GPU + adapter):
```bash
python orchestrator/run.py --sample --max-new 256
python orchestrator/run.py --chat-adapter models/qwen3.5-4b-ptbr-sft   # adapter local
```

**Fabricar uma abelha nova** (exemplo: a agêntica):
```bash
python data/07b_expand_agentic.py --target 1500          # sementes: 91 -> 1690
python data/07_distill_agentic.py --seeds data/seeds_agentic_expanded.txt --workers 16
python data/05_build_splits.py --in data/raw/agentic_<prof>.jsonl \
    --out data/processed/sft_agentic.jsonl --system-file data/agentic_system.txt
python train/sft_qlora.py --data data/processed/sft_agentic.jsonl    # -> adapter
# registrar o adapter_path no orchestrator/bees.json
```

## Custo real até aqui
**≈ US$ 1,75** de destilação (todo o dado: 5.657 PT-BR + 1.495 agênticos) + Colab Pro+ (assinatura
que o Bruno já tinha). O dataset **não é o gargalo financeiro** — com US$10 dá ~65 mil pares via
`deepseek-v4-flash`. Rodar `python data/00_check_teachers.py` regenera a tabela de preços.

## Metas medíveis ("competitivo" = número, não sensação)
- [x] **Baseline registrado** (n=300)
- [x] **Pipeline ponta-a-ponta validado** (dados → treino → avaliação com significância)
- [x] **Hipótese generalista testada e refutada** com poder estatístico
- [x] **Comeia rodando**: backbone 1×, hot-swap, roteamento correto, fast-path 80%
- [x] **Abelha agêntica bate o base NA TAREFA DELA** ✅ **+28,5 pp** (score 58,9% → 87,4%)
- [x] **Reduzir o over-calling** ✅ **16% → 8%** com verificador determinístico, **sem treinar**
      (score 87,4% → 91,6%; custo: +3% de latência)
- [ ] **Atacar o over-calling residual (8%)** na função de perda: rubrica com "Tool Appropriateness"
      (ATLAS) + rejection-sampling SFT/DPO (Collab-RAG) — ver `docs/estudo-11-papers-2026-07-24.md`
- [ ] **Avaliação de geração com juiz** para a `chat_ptbr` (múltipla escolha não mede o que SFT muda)
- [ ] **Fast-path alto o bastante** para a comeia ser mais barata que chamar o forte sempre
- [ ] **Roda local**: GGUF quantizado no RTX 5070 8 GB
- [ ] **Release**: model card + pesos + demo no HF

## Regras duras do projeto
- **Nunca** treinar com saídas de GPT/Claude/Gemini (ToS proíbem + contaminam a licença aberta).
  Destilação só de **professores abertos** — `assert_teacher_allowed()` falha alto e cedo.
- **Decontaminação** obrigatória: treino não pode vazar os benchmarks.
- **Iterar dados antes de hiperparâmetros** — quase todo ganho vem do dado.
- **Testar > confiar no design:** os 3 bugs acima só apareceram ao rodar de verdade.

## Hardware
- Local: **RTX 5070 Laptop 8 GB** (Blackwell sm_120 — exige PyTorch **cu128**) · Ultra 9 275HX · 31 GB RAM.
- Treino/avaliação: **Colab Pro+ (L4, 22 GB)** — a capacidade (sem OOM, caminho para 9B) é o valor real,
  não a velocidade bruta.

Última atualização: 2026-07-24.
