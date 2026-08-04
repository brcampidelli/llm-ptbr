# 09 — Software / Programação (≈35 livros do acervo)

**Data:** 2026-08-04 · **Método:** triagem ampla por extração de sumário/prefácio (`pdftotext -f 1 -l 30`) dos 39 PDFs de software da pasta `ARTIGOS`, mais checagem automática de variante linguística (PT-PT × PT-BR), de camada de texto (nativo × digitalizado) e de marcas de pirataria/tradução-máquina. Nenhum livro lido por inteiro; nenhuma expressão do autor reproduzida.

> ## Veredito de uma linha
> **A (dado de treino): NÃO.** Para código existe fonte aberta, farta e já em uso (`the-stack`); para *prosa sobre código em PT-BR* — a única lacuna real — a semente pode ser o **próprio código aberto**, não o livro. E metade deste acervo é OCR sujo, tradução-máquina ou PT-PT misturado com PT-BR: entraria como **ruído**, não como sinal.
> **B (valor pro Bruno): SIM, mas em 2 livros, não em 35.** O feature store do Dowling (MLOps/FTI/evals — o único livro de ML do acervo, e é ótimo) e o SQL para Análise de Dados da Tanimura (coorte/retenção/experimento — o churn de 74% do PassaPro está literalmente no capítulo 4). O resto é redundante com o que ele já domina, já tem em `~/.claude/refs/` ou já codificou nas próprias regras.

---

## 1. Inventário triado

Qualidade aparente = qualidade **deste arquivo** (texto, tradução, integridade), não a reputação da obra.

### Engenharia & arquitetura
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **959862844** Building ML Systems with a Feature Store (Jim Dowling, O'Reilly 2025) | MLOps, pipelines FTI, feature store, treino/inferência, LoRA, Ray, KServe/vLLM, RAG/agentes, observabilidade | PT-BR (tradução-máquina) | avançado | ⭐ conteúdo excelente e atual; **termos técnicos mal traduzidos** ("loja/armazenamento de recursos" = *feature store*). Viés forte do produto do autor (Hopsworks) |
| **959862829** Fundamentos da Arquitetura de Software 2ª ed (Richards & Ford) | características arquiteturais, estilos, trade-offs, ADRs, monólito modular | **PT-PT + PT-BR misturados** | avançado | conteúdo de primeira, **arquivo ruim**: tradução automática que alterna "arquitectos/secções/equipa" com "arquiteto/usuário" |
| **1005353419** Criando Microsserviços 2ª ed (Sam Newman, Novatec 2022) | microsserviços: fronteiras, DDD, decomposição, dados, deploy, pessoas | PT-BR (tradução humana) | avançado | ✅ o arquivo mais limpo do lote; sumário completo |
| **856304213** Migrando Sistemas Monolíticos (Newman) | padrões de migração, strangler fig, decompor banco | PT-BR | avançado | boa; ~90% contida no anterior |
| **959863139** Dominar a Arquitetura de API (Mastering API Architecture) | API-first, OpenAPI, gateways, service mesh, testes, segurança, evolução | **PT-PT** (tradução-máquina) | avançado | conteúdo bom, arquivo com a mesma praga do 959862829 |
| **597862829** Engenharia de Software Moderna (Valente, UFMG) | requisitos, processos, projeto, padrões, testes, refactoring, DevOps | PT-BR nativo | intermediário | ✅ excelente e **gratuito pelo autor**. ⚠️ **já processado** e sintetizado em memória (`engsoft-moderna-valente.md`) |
| **678243907** Código Limpo (R. C. Martin) | nomes, funções, comentários, testes, SOLID | PT-BR | intermediário | ⚠️ **digitalização com OCR sujo** ("Prefádo", "local dc trabalho") + marca d'água de site pirata |

### ML / dados / SQL
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **998706216** SQL para Análise de Dados (Tanimura, 2022) | séries temporais, **coorte/retenção**, texto, anomalias, **análise experimental (A/B)**, datasets complexos | PT-BR (Novatec) | intermediário/avançado | ✅ ótima, moderna, direto ao ponto |
| **733574643** Projetos de Ciência de Dados com Python (Klosterman, 2019) | limpeza, scikit-learn, regressão logística, **viés×variância**, validação cruzada, árvores/random forest, imputação | PT-BR (Novatec) | intermediário | boa, mas **ML tabular de 2019**; zero LLM |
| **808611190** Aprendendo SQL 2ª ed (Beaulieu) | SQL básico→intermediário: joins, subqueries, agrupamento | PT-BR | iniciante | correta, mas **tradução de 2010** |
| **603392034** Introdução ao JSON (Bassett) | JSON, schema, APIs | PT-BR | iniciante | ok, tema hoje trivial |

### Python
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **553132245** Pense em Python (Downey) | programação do zero com Python | PT-BR | iniciante | ✅ pedagogia excelente. ⚠️ **o original em inglês é de licença livre (Green Tea Press, CC BY-NC)** — se precisar, usar o original, não este PDF |
| **678778311** Problemas Clássicos de CC com Python (Kopec, Novatec) | busca, CSP, grafos, algoritmos genéticos, k-means, **rede neural do zero** | PT-BR | intermediário | boa, texto limpo |
| **540813927** Python: Escreva Seus Primeiros Programas (Casa do Código) | fundamentos Python 3 | PT-BR nativo | iniciante | ok |
| **669554394** 300 Exercícios Resolvidos em Python (Feltrin) | exercícios sintaxe→OO | PT-BR | iniciante | mediana; DRM Kindle declarado |
| **492076317** Python: A Bíblia / "Os Manuscritos" (M. Thompson) | 3-em-1 iniciante/intermediário/avançado | PT-BR de **tradução-máquina** | iniciante | 🔴 **ruim**: português quebrado ("felicitá-lo por download o livro"), conteúdo raso |

### Algoritmos & lógica
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **690939877** Entendendo Algoritmos (Bhargava) | busca binária, ordenação, recursão, grafos, Dijkstra, DP | PT-BR | iniciante | ⚠️ **PDF sem camada de texto** (só imagens) — inutilizável sem OCR |
| **552867720** Lógica de Programação (SESES/Estácio) | variáveis, condicionais, laços, vetores | PT-BR nativo | iniciante | apostila didática correta |
| **610249296** Algoritmo e Lógica de Programação (Unis-MG) | idem | PT-BR nativo | iniciante | guia de estudo institucional; raso |
| **521850175** 7 Exercícios de Lógica com JavaScript | exercícios básicos | PT-BR | iniciante | amador (o próprio autor conta que o fundo preto foi acidente) |

### Web / JS / React / Node
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **546427403** Learning React 2ª ed (O'Reilly) | JS moderno, hooks, estado, dados, testes, TypeScript | **inglês** | intermediário | boa; era de hooks (~2020), pré-RSC |
| **522833416** The Road to React (Wieruch, Leanpub) | React do zero ao projeto | **inglês** | iniciante/interm. | boa, autopublicada |
| **519198263** How To Code in React.js (DigitalOcean) | 20+ tutoriais React | **inglês** | iniciante/interm. | ✅ **CC BY-NC-SA 4.0** — o único do lote com licença aberta (ainda assim NC) |
| **308127392** ReactJS by Example (Packt) | 5 projetos React | **inglês** | intermediário | 🔴 **"Free Sample": só 1 capítulo** |
| **785104579** The Ultimate Next.js Ebook (autor não creditado) | App Router, roteamento, rendering, data fetching, **Server Actions**, Node×Edge, SEO | **inglês** | intermediário | tópicos são a stack atual do Bruno, mas é ebook de curso — **a doc oficial cobre melhor** |
| **612795654** Princípios de OO em JavaScript (Zakas, Novatec 2014) | tipos, protótipos, herança, encapsulamento | PT-BR | intermediário | boa; pré-classes ES6 |
| **753318843** 200 Exercícios de JavaScript | exercícios por tópico | PT-BR | iniciante | ⚠️ marca **"ebook converter DEMO Watermarks"** (conversão pirata) |
| **753764141** Build a Frontend Web Framework From Scratch (Manning) | escrever um framework tipo-Vue do zero (VDOM, diffing) | **inglês** | avançado | interessante, nicho |
| **669708776** Large Scale Apps with Vue+Vite+TS (Leanpub) | arquitetura front-end, i18n, testes | **inglês** | intermediário | ok — **stack errada** (ele usa React/Next) |
| **611079506** Construindo Aplicações com Node.js 3ª ed (2021) | CLI, REST, bancos, ExpressJS, testes, produção | PT-BR nativo | intermediário | correta, atualizada até 2021 |
| **739010913** Aprendendo a Desenvolver Aplicações Web (Purewal, 2014) | HTML/CSS/JS/jQuery/Node/Mongo | PT-BR | iniciante | **obsoleta** (jQuery) |
| **500000496** HTML5 e CSS3 (Casa do Código, 2012) | semântica, formulários, CSS3, responsivo | PT-BR nativo | iniciante | boa na época; 2012 |
| **531186283** A Web Mobile (Sérgio Lopes, Casa do Código) | responsivo, mobile-first, performance | PT-BR nativo | intermediário | bem escrita; ainda tem princípios válidos |
| **670531388** HTML5: Up and Running (Mark Pilgrim) | APIs HTML5 (canvas, vídeo, storage, geo) | PT-BR | intermediário | 🔴 **"Machine Translated by Google"** + marca d'água wowebook + **2010**. O original livre é o *Dive Into HTML5* (CC-BY) |

### Outros
| Livro | Tema | Idioma | Nível | Qualidade aparente |
|---|---|---|---|---|
| **623391437** Segurança para Desenvolvedores Web (Mueller, 2016) | XSS, injection, autenticação, libs de terceiros | PT-BR | intermediário | **anterior ao mundo Next/Supabase/RLS** |
| **559376156** Controlando Versões com Git e GitHub (Casa do Código) | branches, merge, remoto, PRs | PT-BR nativo | iniciante | ok, básica |
| **612372310** Java para Iniciantes (Luiz Duarte, 2017) | sintaxe Java, NetBeans, OO | PT-BR nativo | iniciante | ok — **linguagem que ele não usa** |
| **510468705** 300 Questões Comentadas de Informática (concursos) | hardware, SO, Office, redes, segurança | PT-BR | iniciante | banco de questões — pertence à **trilha de concursos (PassaPro)**, não à de software |
| **678177175** ChatGPT: do zero aos prompts avançados | persona, contexto, prompt | PT-BR | iniciante | 🔴 infoproduto; **já obsoleto** frente aos refs de LLM que ele tem |

**Padrão da coleção:** ~40% do acervo é iniciante/lógica de programação (redundante entre si), ~25% é web/JS de 2012-2021 (envelhecido), ~20% é arquitetura/engenharia (é onde está o valor), e **1 livro só é de ML/MLOps**.

---

## 2. RESPOSTA A — servem como DADO DE TREINO do Bee?

### Veredito: **não. Nem como texto, nem como semente. Use `the-stack` (v1.1 permissivo já no corpus / v2 filtrado por licença para escalar).**

Quatro argumentos, em ordem de força:

**1. A semente de código é gratuita e infinita — o livro não é necessário.**
O estudo das gramáticas (`estudo-gramatica-dados-sinteticos-2026-08-03.md`) concluiu que o *esqueleto curricular* de um livro protegido é fato, não expressão, e pode virar semente Cosmopedia. Aquele argumento funcionava porque **não existe corpus aberto e grande de gramática normativa do PT-BR** — a taxonomia dos livros era mesmo o caminho mais curto. Aqui é o contrário: já existem **milhões de arquivos de código real, com licença permissiva verificada** (`bigcode/the-stack-smol-xl`, hoje 10% do corpus v1; `the-stack-v2` para escalar). Se eu quero um documento sintético "explique esta função", a semente ideal é **a própria função aberta**, não um capítulo digitalizado sobre laços de repetição. Semente melhor, licença limpa, custo zero, volume ilimitado.

**2. O currículo de programação é genérico a ponto de ser inútil como diferencial.**
A ordem "variáveis → condicionais → laços → funções → listas → dicionários → OO → arquivos" é a mesma nos 8 livros iniciantes do acervo *e* na doc oficial do Python, no currículo do CS50, no freeCodeCamp e na Wikipédia. Não há informação escassa a extrair. No caso das gramáticas havia: o **catálogo de ~60 erros clássicos do PT** era denso e não trivial de reconstruir. Aqui, o equivalente ("erros comuns de programação") já vem de graça em linters, mensagens de compilador e no próprio the-stack.

**3. A qualidade destes arquivos específicos é ruim o bastante para causar dano.**
A triagem achou, no lote: 1 PDF **sem camada de texto** (Entendendo Algoritmos — só imagens), 1 **OCR sujo** (Código Limpo, com "Prefádo"/"dc trabalho"), 3 **traduções de máquina** declaradas ou evidentes (Python A Bíblia, HTML5 do Pilgrim "Machine Translated by Google", os dois O'Reilly da série 9598628xx), 1 **amostra grátis** de 1 capítulo, e 2 com marca d'água de conversão pirata. Pior: **Fundamentos da Arquitetura de Software 2ª ed e Dominar a Arquitetura de API alternam PT-PT e PT-BR dentro do mesmo parágrafo** ("arquitectos"/"secções"/"equipa" ao lado de "arquiteto"/"usuário"). Esse é exatamente o veneno que o estudo das gramáticas mandou evitar — ensinar o Bee a misturar variantes. Um modelo de 151M não tem capacidade sobrando para filtrar ruído: cada token ruim desloca um token bom.

**4. Volume irrelevante — e a lição do Gate 2 já foi paga.**
35 PDFs ≈ 8-12 mil páginas ≈ **10-20M tokens de texto bruto**, ~0,1-0,2% de um corpus de 10B. E o Gate 2 v3 já ensinou o caro: *2,6× mais token rendeu ~0% de bpb* (`bee-mais-token-nao-resolve`). O gargalo do Bee não se resolve por mais um punhado de tokens sobre `for` loops — muito menos tokens ilegais.

### O detalhe jurídico que fecha a questão
Três obras do lote têm **versão original de licença aberta**: *How To Code in React.js* (CC BY-NC-SA 4.0, DigitalOcean), *Think Python* (CC BY-NC, Green Tea Press) e *Dive Into HTML5* (CC-BY, versão web do Pilgrim). **E mesmo essas não servem:** NC (não-comercial) e SA (viral) são incompatíveis com um Bee publicável sob licença permissiva. Se nem as livres passam no filtro, as protegidas não chegam perto da conversa. Além disso, o PDF do Pilgrim no acervo é a **edição paga da O'Reilly traduzida pelo Google**, não a versão CC — ou seja, usar o arquivo do acervo seria pior do que usar a fonte livre equivalente. Regra prática: **quando existir versão livre, usar a versão livre direto na fonte; nunca lavar o PDF pirata.**

### A ÚNICA lacuna real (e como preenchê-la sem os livros)
Há um buraco legítimo: **o the-stack é código com comentário em inglês (ou sem comentário). Não existe corpus aberto grande de "programação explicada em português".** O Bee é um modelo PT-BR com 10% de código — hoje ele vê *código* e vê *português*, mas quase nunca vê os dois **entrelaçados**. Se algum dia isso virar prioridade (não é agora), o pipeline correto é:

- **semente:** funções/arquivos reais do `the-stack` com licença permissiva (+ índices de currículo público: doc oficial do Python, MDN, CS50 — fatos e listas de tópicos, não texto de livro);
- **geração:** professor aberto (DeepSeek-V4 via build.nvidia.com, ToS permite destilar) produzindo em PT-BR: explicação da função, docstring, comentário linha a linha, "erro → correção", exercício → solução;
- ⭐ **verificação determinística — a vantagem que a gramática não tinha:** todo par gerado é **executável**. Roda o código em sandbox, compara com o teste; se não passa, descarta. Isso resolve o problema de "quem gera não pode avaliar" com um oráculo real, não com um segundo LLM. É a diferença qualitativa entre dado sintético de código e dado sintético de gramática — e é o motivo pelo qual esse pipeline vale mais que qualquer livro.

Nada nesse desenho precisa de um único PDF do acervo.

### Uso residual admissível (marginal, com ressalvas)
- **Formato de avaliação:** os bancos de exercício (300 em Python, 200 em JS, 300 questões de informática) mostram um *formato* de eval — enunciado → solução → comentário. Formato não é protegido e é reconstruível em 10 minutos; o valor está em lembrar de **medir por competência**, não em copiar item algum.
- **Escolha de tópicos de código no mix:** vale olhar quais linguagens o acervo enfatiza (Python, JS/TS, SQL) e conferir se a fatia de código do corpus reflete isso — o Bee serve a um dono de SaaS Next.js/Supabase. Isso é decisão de *quota*, não de dado.

---

## 3. RESPOSTA B — valor para o projeto e para o Bruno

Aqui a resposta muda de sinal. Dois livros valem tempo de leitura de verdade, três valem consulta pontual, o resto não.

### 🥇 1. **959862844 — Building ML Systems with a Feature Store** (Jim Dowling, O'Reilly 2025)
**O único livro de ML/MLOps do acervo — e por sorte é o mais útil de todos os 35.** Ele resolve exatamente a categoria de problema em que o projeto Bee já tropeçou:

- **Arquitetura FTI (Feature / Training / Inference)** — decompõe qualquer sistema de ML em três pipelines independentes ligados por um feature store e um model registry. É a resposta arquitetural direta ao incidente registrado em `dados-intermediarios-perdidos-2026-07-27.md`: dado intermediário não é arquivo solto no Drive, é **artefato versionado com contrato entre pipelines**.
- **Cap. 13 — teste offline de sistemas de IA:** teste unitário de *feature* (fazendo valer o contrato dela), teste de integração de pipeline, blue/green em deploy, **evals de agente**, governança, conteinerização automática. É o rigor que hoje falta entre o Gate 2 e o SFT do Bee: os gates existem, mas são manuais e ad-hoc.
- **Cap. 14 — observabilidade:** logs/traces/métricas para modelos e agentes, monitoramento de feature × monitoramento de modelo, autoescalonamento por SLO. Vale para o Bee **e** para o Chimera na VPS.
- **Cap. 10-11 — treino e serving modernos:** LoRA, PyTorch com Ray, desafios de treino distribuído; inferência em lote com PySpark, KServe, **vLLM para servir LLM** com/sem GPU. Casa direto com `estudo-ecossistema-vllm` e com a fase de serving do Bee.
- **Cap. 12 e 15:** agentes, LlamaIndex, RAG, MCP e A2A; encerra com um caso de recomendação e as **"doze falácias do MLOps"** — leitura de 20 minutos que provavelmente evita meia dúzia de decisões ruins.

**Como ler:** ⚠️ dois filtros. (a) O autor é CEO da Hopsworks — parte do livro é catálogo do produto dele; **fique com a arquitetura, ignore o SKU**. (b) A tradução é de máquina e destrói termos: leia "loja/armazenamento de recursos" como **feature store**, "grupos de recursos" como *feature groups*, "visualizações de recursos" como *feature views*. Se travar, o original em inglês resolve.

### 🥈 2. **998706216 — SQL para Análise de Dados** (Cathy Tanimura, O'Reilly/Novatec 2022)
**O maior ROI de negócio do acervo inteiro**, e não é sobre o Bee — é sobre o PassaPro. O problema declarado nos OKRs é **churn de 74,2%** com MRR de 3 dígitos. Este livro é o manual de como medir isso corretamente em SQL puro, rodando contra o Postgres do Supabase, sem ferramenta nova:

- **Cap. 4 — Análise de Coorte:** retenção, sobrevivência, curvas por safra de cadastro. É *o* capítulo. Churn medido como número único é quase sempre enganoso; medido por coorte revela se o problema é ativação (semana 1) ou valor recorrente (mês 3) — que são fixes completamente diferentes.
- **Cap. 3 — séries temporais** (janelas, médias móveis, comparação período a período): a base dos dashboards de MRR/ativação.
- **Cap. 7 — análise experimental (A/B):** antes de mexer no paywall de novo, saber medir se mexeu.
- **Cap. 6 — detecção de anomalias** e **cap. 8 — datasets complexos**: úteis também para os logs do Chimera e do trading.

Bônus para o Bee: janelas e agregação em SQL são a mesma ginástica mental de auditoria de corpus (contar por fonte, por shard, por licença).

### 🥉 3. **959862829 — Fundamentos da Arquitetura de Software, 2ª ed** (Richards & Ford)
Três coisas transplantáveis hoje:
- **Características arquiteturais mensuráveis** — transformar "-ilidades" vagas (escalável, confiável) em número com limiar. É a mesma disciplina do harness ref (`~/.claude/refs/harness-engineering.md`, princípio "critério mensurável antes de executar") aplicada a sistema, não a agente.
- **Cap. 21 — decisões de arquitetura e ADRs.** O projeto Bee já produz decisões boas (`docs/*.md` são quase ADRs) mas sem formato fixo. ADR dá o campo que hoje falta: **consequências e o que foi rejeitado**.
- **Cap. 11 — monólito modular.** A resposta honesta a "devo quebrar o PassaPro em serviços?" é *não*, e este capítulo dá o vocabulário para defender isso sem parecer preguiça.

⚠️ **Leia no original em inglês.** Este PDF é tradução automática com PT-PT e PT-BR misturados no mesmo parágrafo — para um livro cujo valor está em nuance de trade-off, a tradução ruim custa mais do que economiza.

### 4. **959863139 — Dominar a Arquitetura de API** (Mastering API Architecture)
Relevante em um ponto específico e crescente: o Bruno tem **três superfícies de API** (o `/api/hermes/*` do PassaPro, os helpers do Chimera e — em breve — um endpoint de inferência do Bee, provavelmente compatível com OpenAI). O livro cobre design API-first com OpenAPI, versionamento e evolução sem quebrar consumidor, pirâmide de testes de API e modelagem de ameaça. O valor concreto: **contrato antes de implementação**, que é o que impede o agente autônomo de improvisar chamada em endpoint que não existe. ⚠️ Mesma praga de tradução do item 3.

### 5. **1005353419 + 856304213 — Criando Microsserviços 2ª ed / Migrando Sistemas Monolíticos** (Sam Newman)
Recomendados **como vacina, não como receita.** Leia só os cap. 1-2 do primeiro ("Devo usar microsserviços? A quem talvez não sejam apropriados"): para um fundador solo com 3 SaaS, microsserviços seriam malpractice — custo operacional que ele não tem gente para pagar. O que sobra de aproveitável é o **padrão strangler fig** (cap. 3) como modelo mental de refatoração incremental: estrangular o módulo velho por trás de uma fachada, migrar por fatia, nunca por big bang. Serve tanto para código do PassaPro quanto para a troca de peças do pipeline do Bee. ℹ️ O *Building Microservices* já está sintetizado na biblioteca do Cesar **com alerta explícito de "NÃO usar agora"** — a leitura confirma o alerta.

### 6. (opcional) **733574643 — Projetos de Ciência de Dados com Python** (Klosterman)
Só por um motivo: **disciplina de avaliação**. Validação cruzada, trade-off viés×variância, escolha de métrica sob classe desbalanceada, cuidado com vazamento de dados entre treino e teste. É o raciocínio que o Bee precisa na suíte de eval — porém ensinado em ML tabular de 2019, com zero LLM. Se o tempo for curto, **pule**: o `hundred-page-language-models-burkov.md` em `~/.claude/refs/` já cobre perplexidade e avaliação no domínio certo, e melhor.

---

### O que é redundante (e por quê) — não gaste tempo
| Livro | Por que pular |
|---|---|
| **Engenharia de Software Moderna** (Valente) | ✅ **já lido e sintetizado**: `memory/refs/engsoft-moderna-valente.md` + 13 memórias no Mem0. Reler é custo zero de ganho |
| **Código Limpo** (Martin) | Já está **codificado nas regras ativas dele**: função ≤40 linhas, arquivo ≤300 linhas, nomes, sem código comentado (`~/.claude/rules/coding-style.md` é Clean Code destilado). Além disso o arquivo é OCR sujo |
| **Segurança para Desenvolvedores Web** (2016) | Anterior a Next.js/Supabase/RLS. Coberto melhor por `rules/security.md` + `refs/hacking-etico-defensivo.md` + `refs/criptografia-fundamentos.md` |
| **Controlando Versões com Git e GitHub** | Ele opera git/gh CLI diariamente, com PR e auto-merge automatizados |
| **Aprendendo SQL** (2010) | Subsumido pela Tanimura para o uso dele |
| **Todos os de React/JS/Vue/Node/HTML/CSS** | Stack que ele já roda em produção há anos; e os arquivos são de 2012-2021 (pré-RSC/App Router). A doc oficial do Next.js e `refs/modern-javascript-montalesi.md` + `refs/nodejs-digitalocean.md` + `refs/css-grid-explained.md` cobrem melhor e estão atualizados |
| **Todos os de lógica/algoritmos/Python iniciante** (8 livros) | Nível abaixo do dele; e o `Entendendo Algoritmos` sequer tem texto extraível |
| **Java para Iniciantes** | Linguagem que ele não usa |
| **ChatGPT: prompts avançados** | Obsoleto frente a `refs/ai-engineering-guidebook.md` e `refs/harness-engineering.md` |
| **300 Questões de Informática** | Não é engenharia de software — é **conteúdo de concurso**, pertence à trilha do PassaPro (avaliar no doc de currículo da vertical de concursos) |

---

## 4. Currículo de programação que emerge (para o caso de uso residual)

Só faz sentido se o objetivo for **gerar prosa técnica em PT-BR sobre código aberto** (a lacuna da §2). A árvore abaixo é o consenso dos 35 livros — e cada nó tem fonte aberta melhor que o livro:

```
0. Fundamentos             variável, tipo, operador, condicional, laço, função, escopo
                           └ fonte aberta: doc oficial Python/MDN · the-stack (exemplos reais)
1. Estruturas de dados     lista, dicionário/mapa, conjunto, tupla, string, arquivo, JSON
                           └ the-stack + docstrings reais
2. Algoritmos              busca (linear/binária), ordenação, recursão, complexidade O(),
                           grafos/BFS-DFS/Dijkstra, programação dinâmica, backtracking/CSP
                           └ fonte aberta: implementações permissivas + testes executáveis
3. Paradigmas              OO (classe, herança, composição, encapsulamento), funcional
                           (map/filter/reduce, imutabilidade, HOF), tipagem estática
4. Dados                   modelo relacional, SQL (join, agregação, subquery, JANELA),
                           índice, transação, normalização × desnormalização
5. Web                     HTTP/REST, JSON, autenticação, cliente × servidor, rendering,
                           estado, componentes
6. Engenharia              versionamento, teste (unidade/integração/e2e), refatoração,
                           revisão de código, CI/CD, observabilidade
7. Arquitetura             acoplamento × coesão, fronteiras/domínio, trade-offs, ADR,
                           monólito modular → (raramente) serviços, contrato de API
8. Segurança               validação de entrada, injection, XSS, authn × authz, segredos
9. ML/MLOps                pipeline feature/treino/inferência, versionamento de dado e
                           modelo, avaliação, deploy, monitoramento
```

**Regras se isso virar pipeline:** PT-BR sempre (os dois livros PT-PT do lote provam o risco de misturar variante); **todo par gerado passa por execução em sandbox** antes de entrar (oráculo determinístico — é a vantagem do domínio código sobre o domínio gramática); intercalar prosa e bloco de código (o objetivo é justamente o entrelaçamento que o the-stack não tem); e nível calibrado — um 151M não aprende arquitetura, aprende **padrão sintático e explicação curta**, então priorizar os níveis 0-4 e ignorar 6-9.

---

## 5. Veredito priorizado

1. **Não abrir exceção de copyright por este acervo.** O argumento que salvou as gramáticas (currículo escasso, sem alternativa aberta) **não se transfere para software**: aqui a alternativa aberta é maior, mais limpa e já está no corpus. Manter `the-stack` (v1.1 permissivo hoje; `the-stack-v2` filtrado por licença quando escalar) e seguir em frente. **Custo de ignorar estes 35 PDFs no treino: zero.**
2. **Ler o Dowling (feature store) agora.** É o único livro de MLOps do acervo, é de 2025, e cobre com nome e sobrenome os buracos que o projeto Bee já sentiu na pele: dado intermediário sem versionamento, eval sem harness, serving sem plano. Ler pelo esqueleto (FTI + cap. 13/14 + as 12 falácias), com desconto no viés Hopsworks e nos termos mal traduzidos.
3. **Ler o cap. 4 da Tanimura esta semana.** Coorte/retenção em SQL contra o Supabase do PassaPro. É o item de maior retorno **financeiro** do acervo inteiro — churn de 74% medido errado é churn não resolvido.
4. **Adotar ADR (cap. 21 de Fundamentos)** como formato dos `docs/*.md` do Bee: decisão, alternativas rejeitadas, consequências. Os documentos já são bons; falta o campo que dói.
5. **Guardar Newman como vacina anti-microsserviço** e ficar só com o strangler fig. Guardar o Mastering API para quando o endpoint de inferência do Bee sair do papel.
6. **Descartar o resto da triagem** — 25 dos 35 são redundantes com o que ele já domina, com `~/.claude/refs/` ou com a doc oficial das ferramentas; e 6 arquivos são defeituosos (sem texto, OCR sujo, tradução-máquina, amostra, marca de pirataria).
7. **Se um dia gerar dado sintético de código em PT-BR:** semente = código aberto + índices públicos, **nunca** PDF protegido; e verificação por **execução**, não por segundo LLM. Isso é registro de decisão para o futuro, não item de backlog agora — o gargalo do Bee segue sendo token de PT em escala, não currículo de programação.
