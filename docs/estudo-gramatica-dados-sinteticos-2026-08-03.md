# Estudo — Livros de gramática PT → dados sintéticos licenciáveis pro Bee

**Data:** 2026-08-03 · **Método:** multi-agente (4 pesquisadores, 9 PDFs lidos estrategicamente) · **Gatilho:** Bruno mandou 9 gramáticas/mapas mentais/bancos de questão de PT e pediu "pegar as ideias, não o livro todo" pra ajudar a ensinar o Bee.

> **Veredito global:** o instinto do Bruno ("as ideias, não o livro") é, além de prático, a **única rota publicável**. Os 9 PDFs são **protegidos por direito autoral** (Scribd/Lidel/Eduzz/Kultivi) — o TEXTO não pode entrar no corpus do Bee (viraria um Bee impublicável, a mesma regra do Scribd no plano). Mas o **currículo, a taxonomia de tópicos e os padrões de erro são fatos gramaticais, não protegidos** → viram *seeds* pra gerar dado sintético ORIGINAL em PT-BR com o professor aberto (DeepSeek-V4, cujo ToS permite destilar). É o padrão **Cosmopedia**, já previsto no plano do Bee. **Como VOLUME de token isso é marginal (~30-80M vs bilhões do fineweb-2) — NÃO resolve o gargalo de token do Bee. Como QUALIDADE/estrutura/diversidade, agrega de verdade, mirando exatamente a fraqueza atual (coerência, concordância, regência).** Tratar como **tempero (~5-10% do mix), não prato principal.**

---

## ⚠️ Dois fatos que mudam o uso (achados dos agentes)

1. **Copyright:** todos protegidos. Extrair **currículo/erros** (fatos) ✅; copiar **texto/enunciados/exemplos** ❌. Todo o token vem do professor sintético; os PDFs contribuem ~150-250 *tópicos*, não MBs de texto.
2. **Variante e ortografia:** 2 dos livros (**Aprender Português** e a série **Gramática Aplicada**) são **português EUROPEU + ortografia pré-Acordo** ("actualmente", "autocarro", "pequeno-almoço", mesóclise "fá-lo-ei"). ⚠️ **Gerar SEMPRE em PT-BR + ortografia nova + colocação brasileira** (próclise dominante, sem mesóclise), usando os livros só como esqueleto — senão ensina o Bee a misturar as duas variantes.

---

## As 4 fontes (o que cada uma entrega)

### 🥇 Erros comuns + 1000 questões — **pares "errado→certo" 5/5** · eval 3,5/5
- **Catálogo de ~60 erros de PT** organizados: homófonos/parônimos (mau/mal, mas/mais, a/há, senão/se não, porquês, agente/a gente…), **concordância** (existe/existem, faz/fazem impessoal, aceitam-se, "menas"), **regência** (assistir a, preferir…a, chegar a, visar a), **colocação** (entre mim, para eu fazer), locuções (ao encontro de/de encontro a, em vez de/ao invés de), flexão (medeia, particípios).
- **É exatamente onde o Bee erra hoje** (concordância/conectivos falhos). O catálogo → prompt pro professor gerar **pares ORIGINAIS (errado, certo, explicação)**: dado licenciável, denso em sinal, e **o par "errado" é o `rejected` natural pra DPO/ORPO** (preferência de graça, sem anotação humana). Melhor ROI do lote.
- O banco de questões → molde de **suíte de avaliação de PT por competência** (crase, concordância, regência, pontuação…). ⚠️ múltipla escolha num 150M fica perto do acaso (20%); usar **log-probabilidade / cloze** (o modelo dá maior verossimilhança à frase certa?) — tem sinal mesmo em modelo fraco.

### 🥈 Série Gramática Aplicada (A1→C1) — **currículo 4/5**
- **~102 unidades graded** por dificuldade. **~60% é o sistema verbal** (presente → pretéritos perfeito/imperfeito e o contraste entre eles → compostos → futuro → **todo o Conjuntivo/subjuntivo** cruzado com orações subordinadas: condicional, concessiva, temporal, final, relativa). Também: pronomes+colocação, grau do adjetivo, regência, preposições.
- Ouro aqui = as **tabelas de conjugação completas** (paradigma pessoa-a-pessoa das 3 conjugações). Ensinam paradigmas inteiros de uma vez — o texto scraped dá isso esparso, e é justo o que um 150M precisa pra parar de fazer "salada" de concordância. Método regra→exemplo→exercício.

### 🥉 Mapas mentais de PT — **taxonomia pronta 3,5/5**
- **Currículo de gramática PT quase completo** e canônico (~150 nós): ortografia/acentuação, morfologia (todas as classes, com o denso **QUE/SE multifuncionais**), sintaxe (termos da oração, período composto), **crase** (casos obrigatórios/proibidos), concordância, colocação pronominal, pontuação, semântica/figuras, tipologia textual.
- Valor = **esqueleto de cobertura pronto pra serializar num JSON de tópicos** que garante que nenhum fenômeno gramatical falte no gerador. (Foco em norma culta de concurso — bom pra correção, estreito pra naturalidade → misturar com prosa.)

### Manual Aprender Português (A1-A2) — **variedade temática 3,5/5**
- **14 unidades comunicativo-funcionais** por situação do cotidiano (identidade, rotina, família/casa, compras, saúde, lazer, passado/memórias, reclamações, tratamento formal/informal), cada uma com o bloco gramatical que a situação exige + **diálogos** situados.
- Valor = **grade de temas × situações × registros** pra dar **variedade natural e coerência de curto alcance** — o buraco atual do Bee. Priorizar seeds de **diálogo e narração**. (É PT-PT → pivotar léxico pra PT-BR.)

---

## O plano concreto: pipeline "currículo PT" (Cosmopedia licenciável)

**Entrada:** taxonomia dos mapas + currículo graded da série + grade temática do manual + catálogo de erros → **um JSON de ~200-300 nós** (`curriculo_pt.json`: tópico → subtópico → formato → público).
**Motor:** professor aberto **DeepSeek-V4** (via build.nvidia.com, ToS permite destilar — ver [[bee-teacher-nvidia-build]]).
**Saída:** documentos ORIGINAIS em **PT-BR**, misturados numa fração do treino.

**3 famílias de prompt** (variar público × estilo multiplica o volume — jeito Cosmopedia):
- **A. Explicação didática** — "explique {tópico} em PT-BR pra {criança/vestibulando/estrangeiro/concurseiro}, com tabela de conjugação completa + 8-12 exemplos próprios + 2 erros comuns corrigidos." → maioria vira pré-treino; fatia com gabarito vira SFT.
- **B. Exercícios resolvidos** — "15 exercícios originais de {tópico}: lacuna → resposta → explicação de 1 linha." → SFT instrucional + eval.
- **C. Diálogo/narração natural** — "diálogo em PT-BR usando intensivamente {estrutura} corretamente." → **o mais importante pro pré-treino** (ataca a coerência, evita virar só metalinguagem).

**Ordem de prioridade por ROI:**
1. **Pares contrastivos errado→certo** (do catálogo de erros) — maior ROI, mira o gargalo, alimenta DPO/ORPO futuro. ~30k pares.
2. **Diálogo/narração temática** (manual + tipologia textual dos mapas) — coerência.
3. **Explicações + tabelas de conjugação** (série + taxonomia dos mapas) — morfologia densa.
4. **Suíte de eval** (log-prob/cloze em held-out) — medir progresso por competência.

**Guardas obrigatórias:**
- **PT-BR + ortografia nova + colocação brasileira** (pivotar os 2 livros europeus).
- **Verificar o professor** (quem gera não pode avaliar): 2º passe de checagem + **regras determinísticas** pros casos fechados (menas/menos, crase proibida, porquês) antes de aceitar o par.
- **Misturar com prosa corrida** pra não enviesar o Bee a "falar sobre gramática" em vez de usar PT natural. Peso: gramática estruturada ~15-25% *dentro* do sintético; sintético ~5-10% do mix total.

---

## Onde isso entra no cronograma do Bee (honesto)

- **NÃO no v3** (rodando agora, corpus congelado). Isto é pra um **run futuro** (v4 / próximo degrau 350M) e/ou a **fase de SFT/DPO** já planejada — onde os pares contrastivos brilham.
- **Não é a cura do gargalo.** O déficit real de token (SmolLM2 viu ~2T; o Bee ~10B) se cobre com **corpus PT em escala** (CulturaX-pt, mC4-pt, mais Wikipédia/legislação/PD) na casa dos **bilhões**. Este material é **tempero de qualidade**, não volume — mas é tempero barato, denso e mirado na fraqueza certa.

## Incertezas / ressalvas
- Contagens de página divergiram do informado (o manual tem 160p não 493; "erros" 35 não 11; "1000 questões" 581 não 88) — os agentes ajustaram e amostraram.
- Um dos "mapas mentais" (`556623412 (1)`) é **duplicata** — ignorado.
- Volume estimado (~30-80M tokens) tem ±50% de incerteza (depende de quantas gerações por seed).
- Um 150M **não decora regra simbólica** como concurseiro — extrai *fluência e correção estatística*, não competência metalinguística. Não superestimar o ganho.

## Fontes (todas protegidas — usadas só p/ extrair currículo/erros, nada de texto no corpus)
Gramática Aplicada A1-A2-B1 e B2-C1 (Oliveira & Coelho, Lidel) · Aprender Português 1 A1-A2 (Lidel) · Resumos em Mapas Mentais Português · Português Mapas Mentais · Erros Mais Comuns (Kultivi) · 1000 Questões (Aprova Português).

> Ver também: o plano do Bee (§1 dados, §6 pós-treino) e [[bee-teacher-nvidia-build]] (professor aberto licenciável).
