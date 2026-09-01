# Índice da documentação do Bee

77 arquivos `.md` acumulados em ~5 semanas. Este índice diz **o que ler, em que ordem, e o que
está morto**.

---

## 🔴 Leia primeiro (se você vai treinar ou avaliar qualquer coisa)

| documento | por quê |
|---|---|
| **[licoes-de-metodo.md](licoes-de-metodo.md)** | ⭐ **os cinco erros que não davam erro**, as leis medidas e o checklist de run longo. Se ler um só, leia este |
| [licoes-pretreino.md](licoes-pretreino.md) | detalhe do pré-treino: bug de rótulos, amostragem, throughput, $/B tokens |
| [agentico-medicao.md](agentico-medicao.md) | como se mede tool-use de verdade (execução, não semelhança) + os dois erros de avaliador |
| **[relatorio-agentico-2026-08.md](relatorio-agentico-2026-08.md)** | ⭐ **os sete estágios do ciclo agêntico num lugar só** — 4 adoções, 5 reprovações e **7 defeitos de instrumento, três deles em números já reportados como resultado** |

⚠️ **A destilação transferível destes erros está fora do repo**, em
`~/.claude/rules/bee-pretreino-licoes.md` (§1 a §2ab) — auto-carregada em toda sessão. Todos têm
o mesmo modo de falha: **nada reclama, a loss cai bonito, e o número sai**.

---

## O estado atual — o que o Bee é hoje

| documento | cobre |
|---|---|
| [`../README.md`](../README.md) | visão geral, os dois modelos publicados, arquiteturas, como rodar |
| **[bee-350m-resultado-final.md](bee-350m-resultado-final.md)** | ⭐ **o pré-treino do 350M fechado**: 21,75B tokens, US$ 140,2, **bpb 0,8207** — o gate de 0,80 **não passou por 0,0207**. 🔴 E o motivo refuta o plano: +45% de dado rende **0,19%**, enquanto 151M→345M rende **2,76%**. O próximo degrau é **parâmetro**, não token |
| **[e19-forma-da-classe-negativa.md](e19-forma-da-classe-negativa.md)** | ⭐⭐ **os dois adapters publicados, e por que são um par e não uma sucessão.** 91,1% dos negativos do corpus eram recusas; trocar a **forma** devolve tradução/resumo/atendimento e corta over-calling, ao custo de 5,9 pp de execução. **3 sementes de cada lado** |
| [sft-resultado.md](sft-resultado.md) | SFT sobre a base correta; os 3 defaults errados |
| [agentico-medicao.md](agentico-medicao.md) | execução 65,9%, pass@k, over-calling, rejection sampling |
| [multiturno-adapter.md](multiturno-adapter.md) | ⭐ a abelha multi-turno e a validação da tese da COMEIA |
| [modelcards/](modelcards/) | cards publicados: base, sft, **sft-v2** |

## ⭐ O próximo degrau — Bee-350M

| documento | o que decide |
|---|---|
| **[estudo-bee-350m.md](estudo-bee-350m.md)** | ⭐ **~60 papers de ago/2026, 13 agentes, 4 afirmações passadas por refutação adversarial.** Receita, orçamento, o que NÃO fazer, e **três premissas do plano derrubadas** — inclusive "expandir o corpus para 30B" |
| **[tres-lacunas-medidas.md](tres-lacunas-medidas.md)** | ⭐ **US$ 0, três achados**: a geometria do 350M é idêntica ao **MobileLLM-350M** (2ª fonte, com ablação); 🔴 **ativações massivas de 1616× e attention sink de 85% CONFIRMADOS em 151M** — mata quantização por-tensor; e quem desvia na razão intermediate é o **150M**, não o 350M |
| **[estudo-qwen38-slm.md](estudo-qwen38-slm.md)** | ⭐ **13 agentes sobre Qwen3.8 + survey de SLM + 10 refs.** Qwen3.8 = Qwen3.5 em arquitetura (params idênticos na unidade). **Duas refutações medidas na escala do Bee**: Gated DeltaNet perde 0,2 pp em 340M/20B, e MTP piora abaixo de ~1,3B. A lacuna: MobileLLM é o único trabalho medido em 125M **e** 350M |
| **[throughput-350m-medido.md](throughput-350m-medido.md)** | ⭐ **US$ 0,15 e cortou o custo do run pela metade**: 53,73k tok/s medidos (a extrapolação do 151M subestimava 60%). Run principal = **US$ 115**, não US$ 218. Liger habilita desligar o checkpointing (+23%); `torch.compile` é incompatível com Liger |
| **[fork-decaimento-resultado.md](fork-decaimento-resultado.md)** | ⭐ **o resultado medido** do fork: US$ 22,4 e 21,98 h para separar duas hipóteses que a curva pareada não distinguia |
| **[fork-decaimento.md](fork-decaimento.md)** | 🔴 **US$ 22, e inverte o sinal de um resultado**: a curva pareada do 350M contra o 150M media o **schedule**, não o modelo. Decair uma cópia levou o 350M de **2,51% pior** em 10B a **~0,6% melhor** em 13B — **sem um token novo**. Fecha a hipótese registrada em 10/08 e deixada sem teste, e **invalida os marcos 1B–10B como comparação** |
| **[teto-passk-medido.md](teto-passk-medido.md)** | ⭐ **US$ 0, e derruba 3 afirmações**: o corpus está limpo (0,28% de repetição — o item de maior ROI do estudo não existia), o holdout tinha 11,8% de itens impossíveis, e o "teto" de 72,9% era na verdade **85,3%**. A folga colhível é **21,2 pp**, não 15,3 |

## 🐝 Pós-treino do Bee-350M (em curso)

| documento | o que traz |
|---|---|
| **[plano-pos-treino-350m.md](plano-pos-treino-350m.md)** | o plano aprovado: estágios E0–E8, orçamento e os critérios declarados **antes** de medir |
| **[baseline-350m-resultado.md](baseline-350m-resultado.md)** | ⭐ **O E0 FECHADO: as 9 medições do base antes de qualquer treino.** Tradução en→pt **BLEU 27,1** sem SFT (piso 2,5; opus-mt 50,5) e matemática `pass@256` **22%** com gate aprovado. Resumo, código, atendimento e agêntico deram **zero — e o zero é FORMATO, não capacidade**: o resumo cobre 84% dos fatos e reprova por não encurtar; 78% das respostas de código não têm bloco extraível; o agêntico nunca emite um JSON. 🔴 Sentimento 49,7% é o acaso, e aí não é formato: são 4 exemplos no SFT inteiro |
| **[reguas-e-pisos-e0.md](reguas-e-pisos-e0.md)** | ⭐ **as 8 réguas e o piso de cada uma.** Copiar 2 frases resume 51,3%; contar a palavra "não" faz 79,0% em sentimento; copiar a fonte marca chrF++ 21,5 em tradução. E a régua de tradução reproduziu o **BLEU 50,4 publicado do opus-mt em 50,5** — validação do aparato, não só do modelo |
| [censo-mistura-350m.md](censo-mistura-350m.md) | censo por TOKEN: o agêntico recebe 2,7% do gradiente, não 20,9% |

## 🐝 O proximo degrau — Bee-1G multilingue e multimodal

| documento | o que traz |
|---|---|
| **[plano-bee-1g.md](plano-bee-1g.md)** | ⭐⭐ **o documento de decisao.** 🔴 A premissa do README ("o proximo degrau e' parametro") **nao transfere**: para 7 dos 8 idiomas o problema e' DADO, e um 1G de orcamento razoavel teria **menos portugues que o 350M**. Traz os gates T1-T4/V/A com criterio declarado ANTES, a decisao de identidade do multimodal (encoders pre-treinados = "do zero" nao cobre olhos e ouvidos), o Pixabay **reprovado** por licenca, e o atalho de fundir modelos monolingues **morto por medicao** |
| **[triagem-arxiv-bee1g-2026-09-01.md](triagem-arxiv-bee1g-2026-09-01.md)** | ⭐⭐ **rodada 3 — 8 agentes, ~15.000 resumos** sobre arquitetura, escala, corpus e reguas. A **tabela do dilema de orcamento esta errada em tres eixos**: o schedule vale mais que o fator de tokens (D2Z), a conta tem de ser em **BYTES**, e diluicao uniforme e' a familia que a lei **nunca escolhe**. A arquitetura multimodal recomendada estava do lado errado — **early-fusion e' mais forte em contagem baixa de parametro, e dissolve a crise de identidade**. **bpb esta' na lista das reguas enviesadas** entre escritas, e `max_new_tokens` fixo mede fertilidade. E a evidencia mais forte diz **traduzir em vez de coletar** — com uma interacao NAO MEDIDA com o nosso pior defeito conhecido |
| **[triagem-arxiv-bee1g-2026-08-31.md](triagem-arxiv-bee1g-2026-08-31.md)** | ⭐⭐ **~7.800 resumos do arXiv em duas rodadas** — e o que sai contradiz o plano em cinco pontos. A restricao central ("250k x 2048 = metade de um 1B") **dissolve**: sete linhas de trabalho fazem o embedding deixar de escalar com \|V\|, uma delas com 3 sementes. A maldicao da multilingualidade **se inverte com a escala** (≤45M sim, 1,1B nao) e isso ameaca o desenho do Gate T2. **Fertilidade nao e' preditiva de qualidade.** Traz o mecanismo publicado do nosso teto de micro-batch 2, tres ideias de hardware mortas antes de custarem dinheiro, e **duas lacunas que eu declarei e retratei** |
| **[bpb-compra-capacidade.md](bpb-compra-capacidade.md)** | ⭐⭐ a premissa que carregava as decisoes caras, finalmente testada: **escala melhora o que ja existe e nao cria o que nao existe** — traducao pt->en de 0% para 86%, e as quatro capacidades em zero continuaram em zero |
| **[fase2-capacidades-em-zero.md](fase2-capacidades-em-zero.md)** | ⭐ a receita de pos-treino validada: **adapter por capacidade, nao dose**; atendimento 0% -> 66,2% acima do piso; codigo de 876/877 sem codigo para **0**. US$ 1,20 |
| **[e22-dois-adapters-e-roteador.md](e22-dois-adapters-e-roteador.md)** | separar dobra o alvo e custa zero — roteador deterministico 954/954 |
| **[e20-e21-resumo-por-dado.md](e20-e21-resumo-por-dado.md)** | a curva de dose, e o preco que so' aparece na dose que move o alvo |

## ⭐ O ciclo agêntico E2 → E19 (2026-08-20 a 30) — US$ 0,66 no total

Doze estágios, quase tudo na RTX 5070 local. ⭐ **As reprovações valem tanto quanto as adoções**,
e estão todas registradas com o número que as reprovou.

| documento | o que decidiu |
|---|---|
| [e2-resultado.md](e2-resultado.md) | **27 braços medidos.** O SFT entrega **UMA** capacidade: agêntico 0/85 → 64,7% e o resto parado |
| [e3-resultado.md](e3-resultado.md) · [e3-reconhecimento-gigaverbo.md](e3-reconhecimento-gigaverbo.md) | dado: de 7.152 para 263.971 exemplos — e o reconhecimento da fonte **antes** de usá-la |
| [e4-resultado.md](e4-resultado.md) | a lei de mistura **discorda do estoque**; 🔴 e o sinal era 0,34× o ruído — o grid trazia o próprio piso de ruído de graça |
| [e5-resultado.md](e5-resultado.md) | 🔴 **executar não é verificar**: 95,3% das chamadas executam, 62,4% acertam. Não há laço de retentativa a fazer |
| [e6-resultado.md](e6-resultado.md) | 🔴 **o gate decidiu NÃO** — e só decidiu porque o ruído de semente (4,7 pp) foi medido e era maior que o limiar de adoção (5 pp) |
| [mundo-aberto.md](mundo-aberto.md) | o holdout de 85 casos media **memorização de catálogo**, não generalização |
| [e7-diversidade-resultado.md](e7-diversidade-resultado.md) | ⭐⭐ **10,9% → 85,8%**: o que E5, E6 e rejection sampling não alcançavam era de **treino** |
| [e8-ferramenta-inedita.md](e8-ferramenta-inedita.md) | ⭐ a **seleção generaliza** (96,9% em ferramentas nunca vistas); o que falha é copiar o **nome** do argumento |
| [e9-restricao-ao-esquema.md](e9-restricao-ao-esquema.md) | ⭐ **+10,0 pp sem tocar em treino** — e 🔴 o bug de array que destruiu 35 casos, achado por uma queda na métrica onde a intervenção **não tem mecanismo** |
| [e10-ligacao-de-papel.md](e10-ligacao-de-papel.md) | 🔴 **hipótese refutada por sonda construída para confirmá-la** — a queda de 14 pp media a sanidade do modelo, não o efeito |
| [e11-catalogo-balanceado.md](e11-catalogo-balanceado.md) | 🔴🔴 **o modelo aprendeu a CONTAR, não a selecionar** — e o over-calling de 0,0% era zero **por construção** |
| **[e13-o-que-quebrou.md](e13-o-que-quebrou.md)** | 🔴 **o que o pós-treino custou nas outras 8 capacidades** — e a primeira versão deste documento concluiu o **oposto**, por medir um adapter ChatML em texto cru |
| **[e19-forma-da-classe-negativa.md](e19-forma-da-classe-negativa.md)** | ⭐⭐ **era a FORMA da classe negativa** — os dois adapters publicados, com 3 sementes de cada lado |

## Infraestrutura

| documento | decide |
|---|---|
| [colab-setup.md](colab-setup.md) | ⚠️ **superado** — a migração para o RunPod foi a decisão final para run longo |
| **[colab-cli-avaliacao-2026-08-19.md](colab-cli-avaliacao-2026-08-19.md)** | ⭐ **Colab volta ao jogo — para carga diferente.** A CLI do Colab (jun/2026) faz `colab run --gpu A100 script.py` com keep-alive sem navegador; instalada e verificada aqui (v0.6.0, via WSL — não roda em Windows). Aceleradores **T4/L4/G4/H100/A100**, e o G4 é RTX PRO 6000 Blackwell de 96 GB, exclusivo do Pro+. A migração para o RunPod continua certa para **run longo**; os 15 SFTs curtos do E2 cabem nas 600 unidades já pagas. ❓ Falta medir a taxa de queima por GPU-hora antes de decidir |

## Estudos de fontes externas — o que NÃO adotar também é resultado

| documento | veredito |
|---|---|
| **[estudo-ml-guide-mikeroyal-2026-08-19.md](estudo-ml-guide-mikeroyal-2026-08-19.md)** | ❌ **2/10.** Guia de ML com 709★ pedido para análise: índice de links de engenharia acadêmica de ~2021 com uma prateleira de LLM pendurada em 2023. "MATLAB" aparece **103 vezes**, "attention" **zero**, "Portug" **zero**. Podridão de link é baixa (6,7%) — o problema é obsolescência técnica, que nenhum código HTTP detecta |

## Gates e decisões

| documento | veredito |
|---|---|
| [gate-1-fertilidade-2026-07-27.md](gate-1-fertilidade-2026-07-27.md) | ✅ o Gate 1 original |
| [gate-1-v2-tokenizador-2026-07-27.md](gate-1-v2-tokenizador-2026-07-27.md) | ✅ vocab 32k, fertilidade 0,2183 |
| [testes-baratos-2026-08-13.md](testes-baratos-2026-08-13.md) | ⭐ os testes de **US$ 0** e o que eles derrubaram |
| [previsao-marco-10B.md](previsao-marco-10B.md) | ⚠️ previsão pré-registrada que **falhou o próprio critério** |
| [instant-clusters-avaliacao.md](instant-clusters-avaliacao.md) | ❌ cluster: não agora |
| [escada-custo-bee.md](escada-custo-bee.md) | custo por degrau da escada |

## Corpus e dados

[corpus-v1-aprovado-2026-07-27.md](corpus-v1-aprovado-2026-07-27.md) ·
[corpora-pt-avaliados.md](corpora-pt-avaliados.md) ·
[fineweb-edu-pt.md](fineweb-edu-pt.md) ·
[estudo-curriculo/00-CONSOLIDADO.md](estudo-curriculo/00-CONSOLIDADO.md) (BNCC)

## 🔴 Documentos INVÁLIDOS — preservados de propósito

Os números vieram do modelo treinado com o objetivo errado (previa t+2). **Não use nenhum
número deles.** Ficam porque mostram como uma conclusão errada se sustenta por semanas:

[gate-2-resultado.md](gate-2-resultado.md) · [escada-scaling.md](escada-scaling.md) ·
[gate-tucano.md](gate-tucano.md) · [gate-corpus-pt-plano.md](gate-corpus-pt-plano.md)

## Histórico (a fase anterior ao Bee)

[comeia-sobre-qwen.md](comeia-sobre-qwen.md) — o método COMEIA sobre Qwen3.5-4B ·
[avaliacao-do-projeto-2026-07-26.md](avaliacao-do-projeto-2026-07-26.md) — o dia em que o
projeto virou Bee · [dados-intermediarios-perdidos-2026-07-27.md](dados-intermediarios-perdidos-2026-07-27.md)

## Estudos de literatura (~20 arquivos)

O mais recente e mais relevante: **[leituras-2026-08.md](leituras-2026-08.md)** — 16 papers de
agosto avaliados contra o critério *"funciona em 151M?"*. Depois dele:
**[estudo-slm-2026-08-24.md](estudo-slm-2026-08-24.md)** (128 papers de SLM do arXiv, jun–ago) e
**[triagem-17-fontes-2026-08-21.md](triagem-17-fontes-2026-08-21.md)** — que conclui, honestamente,
que **14 das 17 não passam**.

Os demais seguem o padrão `estudo-*-<data>.md` (~20 arquivos) e cobrem tokenização, destilação,
GPUs, ferramentas e fornecedores; [leituras-fase0.md](leituras-fase0.md) é o inventário inicial da
pasta de artigos.

⚠️ **[prompt-para-chimera.md](prompt-para-chimera.md)** não é estudo — é o repasse do achado de
catálogo grande para **outro projeto** (o agente de produção), com as ressalvas de extrapolação
declaradas: tudo foi medido em 345M.

---

⚠️ **Nota de higiene:** esta pasta mistura documentos com ~25 arquivos `.log`/`.json` de
execução (`juntar-22b.log`, `upload-22b.log`, varreduras de LR). Eles não são documentação —
são artefatos de corrida guardados por rastreabilidade.
