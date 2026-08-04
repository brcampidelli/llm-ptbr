# 04 — Português, Raciocínio Lógico e Humanas → esqueleto curricular pro Bee

**Data:** 2026-08-04 · **Escopo:** 7 PDFs de `Desktop/Desenvolvendo Projetos/ARTIGOS` (português de concurso, raciocínio lógico, filosofia, sociologia).
**Regra aplicada:** os PDFs são protegidos. Extraí **lista de tópicos, ordem de ensino, método e taxonomia de erro** — que são fatos, não expressão. **Nenhum trecho foi transcrito para virar corpus.** Os poucos fragmentos citados aqui são identificadores de tópico (nomes de erro, nomes de falácia, nomes de capítulo), não texto do autor.

> **Veredito em uma linha:** o achado do lote **não é conteúdo, é um gerador**. O livro de raciocínio lógico entrega ~10 moldes de questão que são **texto puro, com resposta única e verificável por código** — o único material do acervo inteiro que produz dado de treino **original, ilimitado, licenciável e auto-verificado sem depender de LLM professor**. Português rende um delta pequeno (é, quase certamente, o mesmo material já estudado em 03/08) mas fecha três lacunas concretas. Humanas rende quase nada: um dos livros é 100% imagem, o outro é PT-PT, o terceiro é espanhol.

---

## 1. Inventário

| Arquivo | Idioma | Nível / natureza | Extraível? | Páginas |
|---|---|---|---|---|
| `462511900-Portugues-para-concursos.pdf` (Kultivi, "erros mais comuns") | **PT-BR** | Ebook de revisão, concurso | ✅ texto digital limpo (~31 KB) | 76 |
| `668417026-RACIOCINIO-LOGIGO.pdf` (Nova Concursos, Chieregatti & Lima, 2019) ⭐ | PT-BR | Resumo completo p/ concurso + 250 questões gabaritadas | ✅ texto limpo, **símbolos lógicos (∧ ∨ → ↔ ~) preservados** (~322 KB) | 201 |
| `593505872-Raciocinio-Logico.pdf` (Cristiane da Silva) | PT-BR | 1 capítulo de livro-texto ("Lógica matemática"), introdutório | ✅ (~29 KB) | 23 |
| `590600359-500-questoes...APOSTILA-MOSTRA.pdf` | PT-BR | **AMOSTRA comercial** — 10 das 500 questões | ⚠️ só a amostra (~11 KB) | 16 (obra real: 470) |
| `488939307-Livro-Prep-Filosofia-pdf.pdf` (Faria & Veríssimo, Leya) | **PT-PT** | Prep. Exame Nacional (Portugal) + 250 questões | ⚠️ OCR **ruidoso** (palavras corrompidas em ~5-10% das linhas) | 320 (166 MB) |
| `490096650-introduccion-a-la-sociologia.pdf` (UNED, 2018) | **Espanhol** | Manual universitário, 11 capítulos | ✅ texto digital limpo (~654 KB) | 292 |
| `682394115-O-Livro-Da-Filosofia-O-Globo.pdf` (DK/O Globo) | PT-BR | Enciclopédia visual | ❌ **0 texto — 100% imagem escaneada** (353 chars no PDF inteiro = só metadados) | 353 (59 MB) |

**Notas de higiene:** `668417026-RACIOCINIO-LOGIGO (1).pdf` é **duplicata byte-a-byte** do original — ignorar.
Nenhum dos PDFs tem camada de OCR faltando *exceto* o "O Livro da Filosofia", que **não tem texto nenhum** — e mesmo com OCR seria lixo (layout de enciclopédia visual, colunas + infográficos).

---

## 2. Currículo de PORTUGUÊS — e o delta real sobre o estudo de 2026-08-03

### 2.1 ⚠️ Primeiro, a honestidade: é provavelmente o MESMO livro

O estudo de 03/08 lista entre as fontes "**Erros Mais Comuns (Kultivi)**" e descreve um "catálogo de ~60 erros". Este arquivo **é** o ebook "PORTUGUÊS — erros mais comuns" da Kultivi, com **58 verbetes**. Cruzando os exemplos que aquele estudo citou (`mau/mal`, `mas/mais`, `a/há`, `senão/se não`, `a gente/agente`, `existe/existem`, `faz/fazem`, `aceitam-se`, `menas`, `assistir a`, `visar a`, `entre mim`, `para eu`, `ao encontro de/de encontro a`, `em vez de/ao invés de`, `medeia`) — **todos os 16 estão neste arquivo, com o mesmo recorte**. A divergência de páginas (o estudo anterior anotou 35, aqui são 76) é de edição/contagem, não de conteúdo.

**Conclusão:** o conteúdo de português **não é novo**. O delta está no *formato* e na *fechadura* do catálogo — três coisas concretas abaixo.

### 2.2 Delta 1 — o catálogo agora está FECHADO e enumerado (58 itens, prontos pra JSON)

O estudo anterior falava em "~60 erros" como estimativa. A lista completa e ordenada está extraída (seção 3 abaixo, agrupada por tipo). Isso permite pular direto pro `curriculo_pt.json` sem re-ler PDF: **58 nós de erro → 13 classes de fenômeno**.

### 2.3 Delta 2 — o esquema de 4 campos é uma tupla de preferência pronta

Cada verbete do livro tem **exatamente 4 slots**: `errado` · `certo` · `dica` (a regra) · `exemplo` (uma segunda frase correta, em outro contexto).
Isso mapeia 1:1 no que o pós-treino precisa:

| Campo do livro | Uso no treino do Bee |
|---|---|
| `errado` | `rejected` do par DPO/ORPO |
| `certo` | `chosen` do par DPO/ORPO |
| `dica` | racional do SFT (resposta do "por quê?") |
| `exemplo` | **segundo positivo** — permite par `chosen`×`chosen` p/ regularizar (o modelo não deve preferir a frase-alvo *específica*, e sim a forma correta) |

O estudo de 03/08 propôs "gerar pares (errado, certo, explicação)" — trinca. O material mostra que o formato canônico da área é **quádrupla**, e o 4º campo é de graça e útil. Vários verbetes trazem ainda **mais de um par de contraste** no mesmo verbete (ex.: o verbete de `de trás/detrás/atrás` tem 2 erros e 3 acertos), o que dá *rankings* e não só pares binários.

### 2.4 Delta 3 — o molde CLOZE de banca real, que faltava

O estudo de 03/08 recomendou avaliar por **log-probabilidade / cloze** (porque múltipla escolha num 151M fica no acaso) mas não tinha um molde. As 5 questões finais deste ebook são de bancas reais (**FGV 2018, VUNESP 2018**) e revelam três formatos, um deles perfeito:

- **Molde A — "assinale a frase correta"**: 3-5 frases, uma correta. → múltipla escolha, ruim pro Bee.
- **Molde B — "substitua as expressões destacadas"**: texto corrido + 3 expressões a trocar simultaneamente. → bom pra SFT, difícil de avaliar.
- **Molde C — lacunas numeradas I-IV com o par entre parênteses** (`___ surgem os sonhos? (De onde/Aonde)`). → ⭐ **é cloze puro, com par mínimo explícito e resposta única.** É gerável programaticamente a partir do catálogo de 58 erros e avaliável por log-prob: o modelo dá maior verossimilhança ao token/expressão correta? Um item por erro × N contextos = suíte de eval de português por competência, **de graça e determinística**.

**Recomendação:** o Molde C vira o `bench-pt-cloze` do Bee. 58 erros × 20 contextos = 1.160 itens de eval, com acurácia por classe de fenômeno (concordância, regência, homófono...). É a primeira métrica de português **por competência** que o projeto teria, ao lado do bpb.

### 2.5 O que este material **não** acrescenta

- Não tem tabelas de conjugação (isso veio da série *Gramática Aplicada*, já mapeada em 03/08).
- Não tem sintaxe de período composto, crase sistemática, pontuação, colocação pronominal completa — o ebook é uma lista de armadilhas, **não um currículo de gramática**. O esqueleto de cobertura continua sendo o dos mapas mentais.
- Não muda o veredito de volume: continua sendo tempero (dezenas de milhões de tokens), não corpus.

---

## 3. Catálogo de TIPOS de erro que o material documenta

Os 58 verbetes reduzem-se a **13 classes de fenômeno**. É a taxonomia que vira `tipo` no JSON e vira eixo de relatório da eval. (Listo o *tipo* e o *par mínimo* que o identifica — o par é o rótulo do verbete, não texto autoral.)

| # | Classe do erro | O que o falante erra | Verbetes que caem aqui |
|---|---|---|---|
| 1 | **Homófonos / parônimos** | escolhe a palavra de som igual/próximo e sentido errado | mal×mau · mas×mais · haja×aja · seção×sessão · viagem×viajem · traz×trás · perca×perda · hora×ora · comprimento×cumprimento · descriminar×discriminar · retificar×ratificar · despercebido×desapercebido |
| 2 | **Junção × separação (aglutinação indevida)** | escreve junto o que é locução, ou separa o que é palavra única | a fim×afim · a gente×agente · acerca de×a cerca de · decerto×de certo · de mais×demais · de trás×detrás×atrás · senão×se não · tão pouco×tampouco |
| 3 | **Regência verbal** | omite ou troca a preposição exigida pelo verbo | assistir a · chegar a · visar a · implicar (Ø/com/em) · esquecer×esquecer-se de · namorar (Ø) · responder a |
| 4 | **Concordância com partícula SE (passiva sintética)** | trata voz passiva sintética como sujeito indeterminado | aceitam-se · precisam-se |
| 5 | **Verbos impessoais (não flexionam)** | pluraliza verbo sem sujeito | faz (tempo decorrido) · deu/deram (horas) · somos×somos em |
| 6 | **Falso impessoal** ⚠️ | *hipercorreção*: deixa no singular verbo que **tem** sujeito | existe×existem (o par oposto ao nº 5 — vale ouro como contraste) |
| 7 | **Concordância nominal** | não flexiona adjetivo/particípio com o substantivo | anexo×anexa · meio×meia · meio-dia e meia · obrigado×obrigada · quite×quites |
| 8 | **Advérbio × adjetivo** | usa forma flexionada onde cabe invariável | bem×bom · mal×mau (também no nº 1, por homofonia) |
| 9 | **Caso do pronome pessoal (reto × oblíquo)** | usa reto depois de preposição, ou oblíquo antes de infinitivo | entre eu×entre mim · para mim×para eu (+infinitivo) |
| 10 | **Locuções fixas — par mínimo semântico** | troca a locução por outra parecida de sentido oposto/diferente | ao encontro de×de encontro a · em vez de×ao invés de · a par×ao par · a princípio×em princípio · na medida em que×à medida que · a nível de×em nível de · através de×por meio de · a meu ver×ao meu ver |
| 11 | **Redundância / pleonasmo** | repete a marca de tempo | há … anos atrás |
| 12 | **Flexão irregular de verbo** | regulariza verbo de paradigma especial | mediar → medeia |
| 13 | **Forma inexistente na norma** | usa forma da fala popular sem correspondente culto | menas · ter haver (por ter a ver) · ao meu ver |
| — | **"Falso erro" (variante aceita)** | *o material registra pares que NÃO são erro* | fim de semana×final de semana |

Duas observações que valem virar regra do gerador:

- **Classes 5 e 6 são inversas** (`faz` invariável × `existe` variável). Um gerador ingênuo que ensine "impessoal não flexiona" vai induzir o erro oposto. Os dois têm que ser gerados **em par contrastivo explícito**, na mesma amostra.
- **A classe "falso erro" é um negativo do negativo** e é raríssima em material didático. Gerar itens onde a resposta correta é *"as duas formas estão certas"* impede o Bee de virar um corretor paranoico que rejeita construções válidas — que é o modo de falha típico de modelo treinado só em pares errado→certo.

---

## 4. Currículo de RACIOCÍNIO LÓGICO + gerabilidade programática

### 4.1 O currículo (Nova Concursos, 201 p — a espinha dorsal do lote)

Ordem de ensino do livro, que é a ordem canônica das bancas brasileiras:

1. **Conceito fundamental** — proposição; valores lógicos; leis do pensamento (identidade, não-contradição, terceiro excluído); proposição simples × composta.
2. **Conectivos** — negação · conjunção ("e") · disjunção inclusiva ("ou") · disjunção exclusiva ("ou… ou") · condicional ("se… então", com seção dedicada às *pegadinhas*) · bicondicional ("se e somente se").
3. **Tabelas-verdade** — de 1, 2, **3 e 4** proposições simples (2ⁿ linhas); montagem com múltiplos operadores; classificação: **tautologia / contradição / contingência**.
4. **Proposições categóricas** — Todo A é B · Nenhum A é B · Algum A é B · Algum A não é B; classificação e relações entre elas (quadrado aristotélico); análise com mais de uma categórica.
5. **Equivalência lógica** — dupla negação, idempotência, comutação, associação, distribuição; **negações**: De Morgan (da conjunção e da disjunção), negação da condicional, negação da bicondicional; equivalências da condicional (contrapositiva) e da bicondicional.
6. **Argumentação e validade** — 3 métodos de teste: **diagramas de Euler**, **premissas verdadeiras**, **tabela-verdade**; método da conclusão falsa.
7. **Problemas lógicos** — implicação lógica (2 tipos); **associação lógica** (grade "quem-mora-onde"); **"quem está mentindo?"**.
8. **Teoria dos conjuntos** — finito/infinito/vazio/unitário; representação (compreensão, extensão, Venn); pertinência × inclusão; subconjuntos; união, intersecção, `n(A∪B)`, diferença; problemas de contagem.
9. **Análise combinatória** — princípio multiplicativo · fatorial · permutação (simples, com repetição, **circular**) · combinação simples · arranjo simples.
10. **Probabilidade** — espaço amostral, evento, P(E), eventos independentes, união e intersecção, **probabilidade condicional**.
11. **Hora de praticar** — **250 questões** de banca com gabarito tabular no fim.

O outro PDF de lógica (Cristiane da Silva, 23 p) cobre só o item 1 com enquadramento acadêmico (argumento/premissas/conclusão, lógica como linguagem, prova de teoremas). **Redundante** — coberto pelo item 1 acima. A "apostila amostra" das 500 questões só acrescenta uma taxonomia de 7 rubricas comerciais (correlacionamento de dados · proposições · silogismo · encontrando o culpado · álgebra · sequências · psicotécnicos), das quais 2 são inúteis pro Bee (sequências de figuras, psicotécnicos = imagem).

### 4.2 Qualidade do material como fonte de dado

Medições feitas no arquivo:

- **250 questões**, todas com fonte identificada (ano + órgão + banca). Distribuição de bancas: FCC 43 · CESPE 41 · VUNESP 30 · CESGRANRIO 26 · ESAF 25 · FGV 10 · demais 30+.
- **Dependência de figura: ~4 questões em 250 (≈1,6%)**. Só 2 menções a "figura" e 2 a "diagrama" no bloco inteiro. **≈98% é texto puro.** Isso é excepcional — nenhum outro material de exatas do acervo chega perto.
- **Símbolos lógicos extraem íntegros** (`∧ ∨ → ↔ ~ ⟶`) neste arquivo. ⚠️ No PDF da "amostra das 500 questões" os conectivos **somem na extração** (`~(p q)` sem o operador) — outro motivo pra descartar aquele.
- **Gabarito em tabela numerada** (item → letra), machine-parseable.

### 4.3 ⭐ Gerabilidade programática dos MOLDES — a análise que importa

A pergunta certa não é "quantas questões dá pra copiar" (resposta: zero, é material protegido). É: **quantos moldes dá pra reimplementar em Python, gerando itens novos cuja resposta o próprio gerador conhece?**

| Molde | Como gerar | Gerabilidade | Verificador |
|---|---|---|---|
| Valor lógico / tabela-verdade de fórmula | sorteia AST de fórmula sobre p,q,r(,s) + verbaliza com banco de sujeitos/predicados | ⭐⭐⭐ trivial | avaliação booleana exata (2ⁿ linhas) |
| **Negação** de proposição composta (De Morgan, negação da condicional/bicondicional) | idem, aplica a regra | ⭐⭐⭐ | equivalência por tabela-verdade |
| **Equivalência lógica** (achar a equivalente) | gera fórmula + 1 equivalente + 4 distratores por *equivalências falsas conhecidas* (comutar a condicional, negar só um lado…) | ⭐⭐⭐ | tabela-verdade |
| **Silogismo categórico** (validade) | espaço **finito e enumerável**: 4 figuras × 64 modos = 256 formas, das quais 24 válidas | ⭐⭐⭐ exaustivo | regras de silogismo / modelo de conjuntos |
| **Proposições categóricas / Euler** em forma textual | conjuntos sorteados; pergunta "o que se conclui necessariamente?" | ⭐⭐⭐ (não precisa desenhar — a versão textual é a mais cobrada) | verificação por modelos finitos |
| **Associação lógica** ("quem mora onde / quem faz o quê") | sorteia a solução → deriva pistas → **poda pistas até a solução ficar única** | ⭐⭐⭐ padrão clássico | solver CSP confirma unicidade |
| **"Quem está mentindo"** | n afirmações; enumera 2ⁿ atribuições verdade/mentira | ⭐⭐⭐ | enumeração exaustiva |
| **Conjuntos / contagem** | inclusão-exclusão com 2-3 conjuntos | ⭐⭐⭐ | fórmula fechada |
| **Análise combinatória** | templates paramétricos (P, Pᵣ, P circular, A, C) com objetos sorteados | ⭐⭐⭐ | fórmula fechada |
| **Probabilidade** (incl. condicional / Bayes) | urnas, baralhos, dados, populações — parâmetros sorteados | ⭐⭐⭐ | fração exata |
| Sequências numéricas | gerável | ⚠️ **⭐** — risco real de **gabarito não-único** (mais de uma regra encaixa nos termos dados). Só usar com regra de família fechada e checagem de unicidade contra um catálogo de regras. |
| Sequências de figuras / dominó / psicotécnicos | — | ❌ depende de imagem | — |

**Placar: 10 de 12 moldes são 100% textuais, com resposta única e verificável por código.**

### 4.4 Por que isso vale mais que tudo no acervo (e o que ele NÃO vai fazer)

**A propriedade rara:** este é o único material do lote (e, até onde vi, do acervo) que permite construir um **gerador determinístico** — sem LLM professor no meio. E isso mata de uma vez três problemas que o estudo de 03/08 tinha que administrar com guardas:

| Problema no pipeline com professor LLM | No gerador determinístico |
|---|---|
| Copyright (texto do PDF não pode entrar) | **Some** — nada do PDF entra; só a *forma* do exercício, que é fato matemático |
| "Quem gera não pode avaliar" (precisa de 2º passe) | **Some** — a resposta é sorteada *antes* do enunciado; o gabarito é construção, não julgamento |
| Alucinação do professor | **Some** — não há professor |
| Custo / rate-limit da API | **Some** — é Python puro, milhões de itens em minutos |

**Mas seja franco sobre o ganho:** um modelo de **151M não vai resolver lógica de múltiplos passos.** Raciocínio simbólico encadeado é capacidade emergente muito acima dessa escala; esperar que o Bee acerte silogismo é ilusão. O valor real é outro, e é triplo:

1. **Gramática funcional disfarçada de lógica.** O gargalo diagnosticado do Bee é coerência e **conectivos falhos**. Um corpus enorme em PT-BR onde `se… então`, `ou… ou`, `todo`, `nenhum`, `algum`, `portanto`, `logo`, `necessariamente`, `salvo se` aparecem **sempre com semântica consistente e sintaxe correta** é exatamente o treino de conectivo que falta — e vem de graça junto.
2. **A primeira eval objetiva e barata do projeto.** Resposta única + dificuldade graduável (1 conectivo → 2 → 3; 2 proposições → 4) dá uma **curva de capacidade**, não um número solto. Formato: **cloze / log-prob**, nunca A-B-C-D (num 151M, múltipla escolha de 5 = 20% de acaso, sem sinal).
3. **Formato de resolução passo a passo.** Gerar `enunciado → resolução declarativa → conclusão` (não `pergunta → letra D`) ensina *estrutura de discurso argumentativo em português*, que é forma — e forma é o que o Bee já demonstrou aprender.

### 4.5 Riscos do gerador (declarados de antemão)

- **Colapso de template.** 10 moldes, por mais parâmetros que tenham, produzem baixa diversidade de superfície. O Bee pode aprender "concursês" em vez de português. **Mitigações obrigatórias:** (a) banco lexical grande de nomes/objetos/predicados/profissões/cidades; (b) ≥3 realizações de superfície por molde (interrogativa, narrativa, diálogo); (c) **teto de 3-5% do mix**, alinhado com a mesma guarda do estudo de 03/08.
- **Viés de domínio.** Itens de lógica de concurso vivem num microcosmo (Antônio, Bruno, Carlos, profissões, cores de roupa). Variar radicalmente o universo semântico ou o Bee associa "se…então" a um cenário só.
- **Volume:** 200k-500k itens × ~100-150 tokens ≈ **20-75M tokens**. Mesma ordem do sintético de gramática — de novo: **tempero, não corpus**. Não resolve o déficit de token.

---

## 5. Currículo de FILOSOFIA / SOCIOLOGIA + alerta de viés

### 5.1 Filosofia (Prep Filosofia, PT-PT) — currículo do Exame Nacional português

**Bloco I — Ferramentas do trabalho filosófico**
1. Abordagem introdutória: o que é filosofia; questões filosóficas; competências relativas a *problemas*, *conceitos*, *teses* e *argumentos*; validade, verdade, solidez.
2. **Lógica formal**: lógica proposicional clássica; principais formas de inferência válidas (modus ponens, modus tollens, silogismo hipotético, silogismo disjuntivo, leis de De Morgan); **falácias formais** (afirmação do consequente, negação do antecedente).
3. **Lógica informal**: argumentos não dedutivos (indutivos, por analogia, de autoridade); **falácias informais** — petição de princípio, falso dilema, falsa relação causal, *ad hominem*, *ad populum*, apelo à ignorância, boneco de palha, derrapagem (ladeira escorregadia), generalização precipitada, falsa analogia, amostra não representativa, apelo ilegítimo à autoridade.

**Bloco II — A ação humana e os valores**
4. Determinismo × liberdade: incompatibilismo × compatibilismo; determinismo moderado, libertismo, determinismo radical.
5-6. Juízos de facto × juízos de valor; objetivismo, subjetivismo, relativismo; **ética normativa**: utilitarismo (princípio da utilidade, prazeres superiores/inferiores) × **deontologia kantiana** (dever, máxima, imperativo categórico × hipotético, autonomia × heteronomia, teste da universalização, dignidade).
7. **Justiça social**: teoria de Rawls (posição original, véu de ignorância, princípios da justiça, princípio da diferença, equilíbrio reflexivo, bens sociais primários) × crítica libertarista (Nozick) × crítica comunitarista (Sandel).

**Bloco III — Conhecimento e racionalidade científica**
8. Epistemologia: tipos de conhecimento; definição tripartida; desafio cético; fundacionismo; **racionalismo (Descartes)** × **empirismo (Hume)** — ideias/impressões, relações de ideias × questões de facto, conjunção constante.
9. Filosofia da ciência: demarcação (verificabilidade × **falsificabilidade**), método (indutivismo × falsificacionismo), evolução da ciência (**Popper × Kuhn**: paradigma, pré-ciência, crise, revolução, incomensurabilidade), objetividade.

**Bloco IV — Dimensões da ação humana**
10. Estética: definição de arte; teorias essencialistas (representacionista, expressivista, formalista) × não essencialistas (institucional, histórica), cada uma com suas objeções.
11. Religião: conceito teísta de Deus; argumentos **cosmológico**, **teleológico**, **ontológico**; **problema do mal**; aposta de Pascal.

**Método do autor (isto é o que vale copiar — a forma, não o texto):** cada unidade segue **`problema → posições em confronto → argumentos de cada uma → objeções a cada uma → esquema organizador → resumo → lista de conceitos-chave → ficha formativa`**. As fichas têm 3 grupos: escolha múltipla · resposta restrita · resposta desenvolvida. O livro instrui explicitamente que, nas questões de desenvolvimento, **a avaliação não recai sobre a posição defendida, e sim sobre a qualidade da fundamentação**.

### 5.2 Sociologia (UNED, espanhol) — 11 capítulos

Parte 1 (fundamentos): 1. a perspetiva sociológica e sua institucionalização (Comte, Durkheim, Marx, Weber) · 2. fundamentação teórica · 3. método de investigação nas Ciências Sociais (desenho e fases) · 4-5. indivíduo, cultura e sociedade (holismo × individualismo, perspetiva sistémica, interacionismo simbólico — Mead, Blumer, Escola de Chicago) · 6. socialização · 7. desvio social e controlo social (formal × informal).
Parte 2 (aplicações): 8. movimentos sociais · 9. mudança social e globalização (capitalismo de consumo, migrações) · 10. sociedade do conhecimento · 11. desigualdade, pobreza e exclusão.
Estrutura comum a todos os capítulos: `delimitação conceptual → referências teóricas e históricas → relevância da questão → exercícios/leituras`.

### 5.3 ⚠️ Alerta de viés ideológico — leia antes de usar qualquer coisa daqui

**Sociologia (grau: médio-alto na Parte 2).** A Parte 1 (caps. 1-7) é metodológica e razoavelmente neutra — apresenta Comte/Durkheim/Marx/Weber lado a lado. A **Parte 2 (caps. 8-11) é carregada e, pior, é carregada de política *espanhola***: movimentos altermundialistas, 15M, "mareas ciudadanas", discussão sobre "comunitarismo defensivo" e movimentos anticapitalistas, enquadramento de desigualdade/exclusão em chave de direitos de cidadania. Não é panfleto — é academia espanhola de esquerda com moldura de neutralidade valorativa. **Mas um modelo de 151M não sabe hedgear**: ele absorve a moldura como se fosse fato. **Recomendação: excluir caps. 8-11 dos seeds.** E, mesmo nos caps. 1-7, gerar em modo **expositivo-plural** ("para Durkheim… ; já para Weber…") e nunca assertivo.

**Filosofia (grau: baixo — e o formato é o antídoto).** Os temas são normativos (ética, justiça, religião), mas o formato do livro (`problema → posições em confronto → objeções a todas`) é **estruturalmente anti-viés**: obriga a representar mais de uma posição e a atacar cada uma. ⭐ **Recomendação forte: adotar esse formato como template padrão de TODO dado sintético de humanas do Bee**, inclusive o de sociologia. É a melhor ideia do lote em humanas.

**Alerta transversal sobre o acervo.** Na mesma pasta `ARTIGOS` convivem material de sociologia acadêmica espanhola (esquerda) e cursos de linha conservadora brasileira (Brasil Paralelo, moral católica). **Misturar os dois não produz neutralidade — produz incoerência.** Se algum dia entrar humanas no Bee, a decisão tem que ser explícita e documentada: ou (a) só conteúdo metodológico/histórico, sem posições normativas, ou (b) posições sempre em pares contrastivos com atribuição de autoria. Nunca (c) "joga tudo no bolo".

### 5.4 O único pedaço de humanas que vale de verdade: as FALÁCIAS

Do bloco de lógica informal saem **12 falácias informais + 2 formais**, com nomes canônicos em português. Isso vira uma tarefa de **classificação de texto curto** (`trecho argumentativo → rótulo da falácia`), que:

- é **textual e retórica**, não simbólica → dentro do que um modelo pequeno consegue tocar (é reconhecimento de padrão de superfície, não dedução);
- é **gerável programaticamente** por template (`ad hominem` = ataque ao proponente; `boneco de palha` = distorce a tese e refuta a distorção; `falso dilema` = 2 opções onde há mais…), com o rótulo conhecido por construção;
- as **falácias formais** (afirmação do consequente, negação do antecedente) já saem do mesmo gerador de lógica proposicional da seção 4 — é literalmente a mesma máquina;
- ensina, de quebra, **vocabulário argumentativo em PT-BR** (portanto, logo, no entanto, contudo, daí não se segue, admitindo que…) — de novo: conectivo, que é o gargalo.

⚠️ **Não usar o texto do Prep Filosofia.** É **PT-PT**: além do léxico e da 2ª pessoa (`encontras-te`, `deves`, `estás a fazer`), o português europeu pós-Acordo grafa *perspetiva, aspeto, conceção, receção* onde o PT-BR mantém *perspectiva, aspecto, concepção, recepção*. Alimentar isso a um modelo de PT-BR ensina ortografia errada. **Só o esqueleto de tópicos atravessa; a redação é 100% nova em PT-BR.** (Somando-se a isso, o OCR do arquivo está corrompido em parte das linhas — mais um motivo.)

---

## 6. Veredito honesto e priorizado

| # | Material | Nota | Por quê |
|---|---|---|---|
| 1 | ⭐⭐⭐ **Raciocínio Lógico (Nova Concursos, 201 p)** | **Maior ROI do lote — e possivelmente do acervo** | Não pelo conteúdo de lógica: pelo **gerador**. 10 de 12 moldes são texto puro, resposta única, verificável por código. É o único material que produz dado **original + ilimitado + auto-verificado + sem LLM professor + sem risco de copyright**. Entrega de brinde a coisa que falta há meses: uma **eval objetiva por competência**, com curva de dificuldade. Custo: 1-2 dias de Python. |
| 2 | ⭐⭐ **Português — erros mais comuns (Kultivi, 76 p)** | Delta pequeno mas real | ⚠️ **É quase certamente o mesmo livro do estudo de 03/08** — não conte como fonte nova. O que acrescenta: catálogo **fechado e enumerado** (58 verbetes → 13 classes, pronto pra JSON), o **esquema de 4 campos** (que é tupla DPO com um positivo extra de graça) e o **molde cloze de banca real** (Molde C), que o estudo anterior pediu e não tinha. |
| 3 | ⭐ **Falácias (Prep Filosofia, caps. 2-3)** | Único pedaço aproveitável de humanas | 14 falácias com nome canônico → tarefa de **classificação textual** gerável e rotulada por construção. Roda no mesmo gerador da lógica. Ensina vocabulário argumentativo PT-BR. |
| 4 | ⚪ **Filosofia (resto do Prep Filosofia)** | Só o método | Levar o **formato `problema → posições → objeções`** como template anti-viés de humanas, e o esqueleto de ~11 unidades temáticas. **Texto: descartar** (PT-PT + OCR corrompido). |
| 5 | ⚪ **Sociologia (UNED, espanhol)** | Baixo, com ressalva | Espanhol num modelo de 151M é **contaminação ativa** (PT/ES são próximos o bastante pra borrar). O syllabus é genérico (sociologia 101, achável em qualquer lugar). A Parte 2 tem carga política espanhola irrelevante ao Brasil. **Não investir.** |
| 6 | ❌ **500 questões — apostila amostra (16 p)** | **Inútil** | É isca comercial: 10 das 500 questões; a obra real (470 p) é paga e não está aqui. E a extração **perde os conectivos lógicos**. Tudo que ela cobre, o Nova Concursos cobre melhor e com 250 questões. **Descartar.** |
| 7 | ❌ **Raciocínio Lógico (Cristiane da Silva, 23 p)** | **Redundante** | Um capítulo introdutório de livro-texto, sem banco de questões. 100% contido no item 1 do currículo do Nova Concursos. **Descartar.** |
| 8 | ❌ **O Livro da Filosofia (DK/O Globo, 353 p, 59 MB)** | **Inútil** | **Zero texto extraível — é 100% imagem escaneada.** Mesmo com OCR seria lixo (enciclopédia visual, colunas + infográficos + linhas do tempo). **Descartar sem cerimônia.** |

### Ordem de execução recomendada

1. **`gerador_logica.py`** (1-2 dias) — 10 moldes, banco lexical grande, 3 superfícies por molde, saída em `enunciado → resolução declarativa → conclusão`. Sai daí, no mesmo passe, o **`bench-logica`** (held-out, cloze).
2. **`bench-pt-cloze`** (algumas horas) — 58 erros × ~20 contextos, Molde C, avaliado por log-prob. **Isto pode rodar contra o Bee v3 HOJE** e dar a primeira leitura de português por competência.
3. **Pares errado→certo** (já era prioridade 1 do estudo de 03/08) — agora com o esquema de 4 campos e as classes 5×6 geradas em contraste obrigatório, mais itens de "falso erro".
4. **Falácias** — só depois dos três acima; é bônus.

### Ressalvas finais (para não vender ilusão)

- Nada aqui resolve o **déficit de token** do Bee. Somando o gerador de lógica (~20-75M) ao sintético de gramática (~30-80M), dá ~1% do corpus atual. Continua sendo **tempero**.
- **Um 151M não vai raciocinar.** O ganho esperado do material de lógica é em **conectivo, coerência local e estrutura de discurso** — mais um jeito de aprender português — e em **medição**. Se a expectativa for "o Bee vai resolver silogismo", ela vai frustrar.
- **Teto de 3-5% do mix** e diversidade lexical agressiva, senão o gerador ensina concursês.
- Todas as contagens de página aqui foram **medidas no arquivo**, não lidas da capa — inclusive as que contradizem o que os PDFs anunciam.

---

**Fontes** (todas protegidas; usadas exclusivamente para extrair currículo, taxonomia de erro e moldes de exercício — nenhum texto foi transcrito para corpus): Kultivi, *Português — erros mais comuns* · Chieregatti & Lima, *Raciocínio Lógico-Matemático* (Nova Concursos, 2019) · Silva, *Lógica matemática* · Freitas, *500 Questões Comentadas de Raciocínio Lógico* (amostra) · Faria & Veríssimo, *Filosofia* (Leya Educação) · Díaz Martínez & Rodríguez Rodríguez (eds.), *Introducción a la Sociología para Ciencias Sociales* (UNED, 2018) · DK/O Globo, *O Livro da Filosofia*.

> Ver também: `docs/estudo-gramatica-dados-sinteticos-2026-08-03.md` (as 9 gramáticas; este documento é o complemento e declara explicitamente onde há sobreposição).
