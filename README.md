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
   agentica     extracao      coder        chat_ptbr (default)  base_forte
   tool-use     doc→JSON      código       chat multilíngue     raciocínio difícil
   [adapter]    [adapter]     [adapter]    [backbone puro] ⚠️    [backbone base]
    FAST         FAST          FAST         FAST                  slow

⚠️ o adapter da chat_ptbr foi APOSENTADO em 2026-07-25 (reprovou no juiz e na
   consistência de idioma). A rota continua; o modelo por trás é o backbone.
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

### ⭐ O TESTE EXTERNO: a `extracao` ganha do few-shot por **+15,1 pp** (2026-07-26)

Até aqui **todo** número deste projeto tinha a forma *"adapter vs. o nosso próprio base, em itens
escolhidos porque o base erra"* — circular por construção. Este é o primeiro contra um concorrente
que não escolhemos para perder.

| braço | perfeitos | campos | conforme | alucinação | esquecidos |
|---|---|---|---|---|---|
| base 0-shot | **0,0%** | 67,7% | 89,1% | 8,5% | 53 |
| base **3-shot** | **10,9%** | 69,4% | 95,8% | 5,3% | 60 |
| **ADAPTER** | **26,1%** | **78,2%** | **100,0%** | **3,4%** | **10** |

**O few-shot funcionou** — tirou o base de 0% para 10,9%. Ou seja, **parte do ganho que
reportávamos era mesmo prompt fraco.** Mas só parte: sobram **+15,1 pp** de especialização real.

Dois achados que só aparecem porque o eval separa os erros:
- **alucinação cai monotonicamente** 8,5% → 5,3% → 3,4%: o few-shot ajuda, o treino ajuda mais;
- **campos esquecidos 53 → 60 → 10**: o few-shot *piorou* a sub-extração. O adapter é o único que
  aprendeu **quando preencher**, não só quando calar.

Reprodução verificada: `colab/reproduce_extracao.py` reconstruiu a abelha em **53,8 min** num
runtime zerado, sem intervenção.

⚠️ Falta medir: o professor (teto prático + custo por documento), um encoder pequeno, e o mesmo
teste na `agentica` e na `coder` — que continuam com números autorreferenciais.

### 🐝 4ª abelha: EXTRAÇÃO estruturada — **+14 a +43 pp**, alucinação **0%** (2026-07-26)

Critério de escolha da abelha (a lição das três primeiras): só especializar onde há **recompensa
verificável**. Extração tem duas, e a segunda é nova no projeto:

1. **conformidade** ao schema (obrigatórios, tipos, enum, campo inventado);
2. ⭐ **groundedness** — todo valor marcado como copiado tem que *aparecer* no documento. Isso torna
   **alucinação detectável deterministicamente**: se o modelo escreveu `1240.0` e esse número não
   existe no texto, ele inventou, e o código sabe.

**Gate:** o base errou **510/934 = 54,6%** (limiar era 15%) → 370 itens de treino.

**Holdout DIFÍCIL** (140, estratificado 35 por idioma, contaminação verificada 0/140) — itens
*perfeitos* = conforme **+** sem alucinar **+** todos os campos certos:

| idioma | base | ADAPTER | delta |
|---|---|---|---|
| francês | 0,0% | **42,9%** | **+42,9** |
| inglês | 0,0% | **28,6%** | **+28,6** |
| espanhol | 2,9% | **22,9%** | **+20,0** |
| português | 0,0% | **14,3%** | **+14,3** |

O maior ganho está no **francês** — o idioma onde o base errava mais (62%). O adapter ganha onde
havia o que ganhar, **não** no idioma majoritário do treino. Depois da `chat_ptbr`, era esse o
resultado a procurar.

**Holdout FÁCIL** (140, o base acerta) — mede dano colateral:

| | perfeitos | campos | conforme | **alucinação** | esquecidos |
|---|---|---|---|---|---|
| base | 98,6% | 99,9% | 99,3% | **0,0%** | 0 |
| ADAPTER | 90,7% | 98,1% | **100,0%** | **0,0%** | 3 |

**−7,9 pp de regressão**, e a decomposição mostra que é dano leve: alucinação **0% nos dois**;
campos individuais caem só 1,8 pp (os "perfeitos" caem mais porque exigem *todos* os campos, e um
erro derruba o item inteiro); conformidade **subiu para 100%**; sub-extração em apenas 3 de 140.

Contra a `coder` (+40 pp difícil / **−17,5 pp** fácil), o dano aqui é **menos da metade** — provável
efeito do modo `strict` no dado de treino, que manteve o formato de saída consistente.

⚠️ **O dataset ficou enviesado para extrações esparsas** (46% dos documentos com campo opcional
ausente, contra os 35% pedidos — efeito de seleção do filtro). Por isso o eval mede **campo
esquecido** separado de alucinação: sem essa coluna, **sub-extração passaria por virtude** — um
modelo que omite tudo nunca alucina e exibiria "0% de alucinação".

⚠️→✅ **Descoberta sobre o instrumento, e o conserto estrutural.** O gate **não é bit-reproduzível**:
duas execuções deram 513 e 510 difíceis (0,3%) porque a geração em lote muda o padding e a
aritmética de ponto flutuante junto. Consequência grave: `shuffle(seed=42)` sobre pools de tamanho
diferente dá permutações totalmente distintas, então **um holdout regerado depois do treino nascia
contaminado** (~73% dele dentro do treino). Foi pego antes de reportar, e o adapter foi retreinado.

**O conserto não foi tomar cuidado — foi remover a possibilidade.** O split agora é decidido por
`sha1(documento) % 1000`, não pela posição numa lista embaralhada. Medido: **pool de 510 vs 507 →
holdout difere em 0 itens.** O mesmo documento cai sempre do mesmo lado, então treinar hoje e
reavaliar amanhã passou a ser uma comparação válida. (`sha1` e não `hash()`: o `hash()` do Python é
randomizado por processo e reintroduziria o mesmo bug.)

### Ferramentas para as limitações conhecidas do dataset

Nenhuma das duas está resolvida — mas as duas saíram de "sabemos que existe" para "dá para medir":

- **`--doc-len {curto,medio,longo}`** — o documento médio ficou em 191 chars; `longo` pede 25–45
  linhas com cabeçalho, seções, tabela, rodapé e muito ruído irrelevante, para o modelo ter de
  *achar* o campo. ⚠️ exige `--max-seq-len 3072+`, senão trunca em silêncio e o experimento mede
  outra coisa.
- **`--cap-esparso`** — os 46% de extrações esparsas (contra 35% pedidos) **não** eram o prompt
  desobedecendo: é seleção do filtro (item com menos campos tem menos chance de errar, logo
  sobrevive mais). O teto corrige na **aceitação**, onde o viés nasce. Simulado com 55% de viés de
  entrada: converge para 35% exatos.
- **`colab/reproduce_extracao.py`** — a abelha inteira em ~35 min, um comando, retomável. É a defesa
  contra o adapter efêmero que não depende de nenhuma ação manual; e só virou confiável por causa do
  split estável acima.


### 🌍 Teste de idioma nas abelhas de domínio (2026-07-25) — o culpado era o *prompt*, não o treino

Depois da `chat_ptbr` reprovar, restava a pergunta: a `agentica` (treinada ~5/6 em PT-BR) e a
`coder` (docstrings em PT) têm o mesmo defeito? As duas estavam **ligadas em produção**. Régua:
48 probes **de domínio** (pedido de código / pedido de ferramenta) nos 4 idiomas, tudo determinístico.

**`agentica` — o melhor número do projeto.** Formato certo = JSON válido quando pede ferramenta,
texto quando não pede:

| idioma | base | ADAPTER |
|---|---|---|
| português | 4/6 | **6/6** |
| inglês | 5/6 | **6/6** |
| espanhol | 4/6 | **6/6** |
| francês | 4/6 | **6/6** |
| **TOTAL** | **17/24** | **24/24** |

O comportamento agêntico **transferiu para três idiomas em que nunca foi treinado.** Idioma da
resposta: 11/12 no base vs 10/12 no adapter — com n=12, −1 é ruído, não regressão.

**`coder` — zero mode collapse** (24/24 produzem código nos 4 idiomas), mas a *prosa* vazava para
o português em inglês. Três braços de investigação (n=6, só inglês):

| cenário | base | ADAPTER |
|---|---|---|
| system prompt PT (produção) | 1/6 | 0/6 |
| system PT + *"responda no idioma do pedido"* | 0/6 | **0/6** (pior) |
| **sem system prompt** | **6/6** | **6/6** |

**Não era o treino — era o IDIOMA do system prompt.** E mandar, *em português*, que responda no
idioma do pedido **piora**: o conteúdo da instrução não vence o idioma em que ela está escrita.

**3 correções no `bees.json`:** `coder` e `chat_ptbr` sem system prompt; `agentica` com "no mesmo
idioma do pedido". ⚠️ A segunda é a mais importante: o prompt da `chat_ptbr` dizia *"Responda em
português brasileiro"* — **desligar o adapter tinha consertado só metade do problema**, a rota
default seguia forçando português sobre um backbone de 201 idiomas.

#### ⚠️→✅ O defeito do catálogo: **+45,8 pp sem treinar nada**

O 24/24 acima rodou com o system prompt **de treino**. A produção servia outro: o `bees.json` tinha
uma versão resumida, escrita à mão, que **não listava ferramenta nenhuma** — e ainda assim exigia um
tool-call. A abelha era treinada com o catálogo à vista e **servida às cegas**.

Medido pela rota real (`load_registry()`, o mesmo caminho do `hive`), mesmos 24 probes:

| idioma | ANTES (stub) base · adapter | DEPOIS (catálogo) base · adapter |
|---|---|---|
| português | 3/6 · 3/6 | 4/6 · **6/6** |
| inglês | 3/6 · 3/6 | 5/6 · **6/6** |
| espanhol | 3/6 · 3/6 | 4/6 · **6/6** |
| francês | 3/6 · 4/6 | 4/6 · **6/6** |
| **TOTAL** | 12/24 · **13/24** | 17/24 · **24/24** |

**13/24 → 24/24 = +45,8 pp, zero GPU.** E o mais grave: com o stub o adapter (13/24) estava
**empatado com o base** (12/24) — os +28,5 pp que pagamos para treinar **não existiam em produção**.
O `3/6` uniforme é a assinatura do defeito: os 3 casos de texto passavam, os 3 de ferramenta falhavam
sempre, porque sem catálogo não há como acertar o nome da ferramenta.

**Conserto estrutural, não remendo:** `data/tool_catalog.py` vira a fonte única; treino, avaliação e
produção importam a mesma `build_system()`. O `bees.json` declara `system_from_tool_catalog: true` em
vez de guardar uma cópia. Verificado: produção == treino **byte a byte**, 14/14 ferramentas.

⚠️ **O harness também estava errado, e isso é a lição:** `eval_lang_domain` chamava `build_system()`
direto para a agêntica — "ajudando" o teste. Ele media o prompt de treino enquanto a produção servia
o stub, e por isso o primeiro 24/24 não valia para a rota real. **Um harness que conserta a config em
silêncio mede a intenção, não o sistema.** Agora passa por `load_registry()`.

**A regra de projeto que sai disso:** abelha que ensina **comportamento** (quando usar ferramenta)
atravessa idiomas de graça; abelha que ensina **redação** (como conversar) carrega o idioma junto,
porque estilo e idioma são a mesma coisa. A `coder` fica no meio — código não tem idioma, prosa tem.

### 🚨 `chat_ptbr` APOSENTADA — reprovou na régua certa (2026-07-25)

A abelha **default** (~40% do tráfego) e a única sem ganho comprovado foi finalmente medida com o
instrumento adequado: **juiz de geração + consistência de idioma**, 48 prompts held-out em pt/en/es/fr
(contaminação verificada: 0 de 48 aparecem nas 6.006 sementes de treino).

**Consistência de idioma — respondeu no idioma da pergunta?**

| Idioma | Base | Adapter | |
|---|---|---|---|
| português | 12/12 | 12/12 | igual |
| **inglês** | 12/12 | **2/12** | ⚠️ **−10** |
| espanhol | 12/12 | 9/12 | ⚠️ −3 |
| francês | 12/12 | 10/12 | ⚠️ −2 |
| **TOTAL** | **48/48** | **33/48** | ⚠️ **regressão multilíngue** |

**Em inglês, o adapter responde em português 10 de 12 vezes.** Ex.: *"The ocean is salty because…"* →
*"A salinidade do oceano é causada pela evaporação…"*. Isso rodava **em produção** na rota default.

**Juiz aberto** (deepseek-v4-flash, posição A/B randomizada): o base vence em **todos os 4 idiomas**
(26 × 19 × 3 empates) — **inclusive em português**, o idioma para o qual o adapter foi treinado. Taxa
de vitória do adapter: **42,2%**.

**Decisão:** `adapter_path` zerado. A rota de chat passa a usar o **backbone puro** (multilíngue, 201
idiomas), mantendo roteamento e system prompt. Reativável com `CHAT_ADAPTER=<caminho>`.

⚠️ **A lição metodológica mais cara do projeto:** este adapter passou por uma avaliação de **n=300** e
foi declarado "não conclusivo" (0 de 7 tasks). **Múltipla escolha não tinha como detectar isso** — o
modelo escolhe uma letra, não gera texto. A régua errada escondeu um defeito grave durante todo o
projeto. **Medir com o instrumento errado é pior que não medir: dá a falsa sensação de ter medido.**

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
| `chat_ptbr` | chat/generalista | 🚫 **adapter APOSENTADO** — reprovou no juiz (42,2%) e na consistência de idioma (33/48 vs 48/48). Rota mantida sobre o **backbone puro** (multilíngue) |
| `agentica` | tool-use / seguir instrução | ✅ **adapter real e VALIDADO** (1.495 ex, +28,5 pp vs base) · **multilíngue: 24/24 vs 17/24 do base nos 4 idiomas** |
| `coder` | funções Python verificáveis por execução | ✅ **treinada e validada em held-out limpo**: +40 pp nas difíceis (1,7%→41,7%, 24×), −17,5 pp nas fáceis. Adapter **persistido na Drive** (2026-07-25); reproduzível em 17 min de qualquer forma |
| `extracao` | documento → JSON com schema | ✅ **adapter real e VALIDADO**: +14 a +43 pp nos difíceis, **alucinação 0%**, −7,9 pp nos fáceis |
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
- [x] **Avaliação de geração com juiz** para a `chat_ptbr` — feita, e **reprovou** (ver seção acima)
- [x] **Testar o mesmo risco multilíngue na `agentica` e na `coder`** — feito: o culpado era o system prompt
- [ ] **Montar o system da `agentica` a partir do catálogo de ferramentas** (defeito registrado acima)
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
