# 03 — Esqueleto curricular: HISTÓRIA e GEOGRAFIA

> Estudo de currículo para o projeto **BEE** (LLM 151M PT-BR pré-treinada do zero).
> Objetivo: extrair **lista de tópicos, ordem de ensino, método/abordagem do autor e recorte
> temporal-geográfico** dos livros disponíveis — para depois escrever material didático **original**.
> Data: 2026-08-04.

## ⚠️ Nota de direito autoral

Os PDFs analisados são obras protegidas (origem Scribd). Este documento **não transcreve nem
parafraseia de perto** nenhum trecho. O que está registrado aqui é:
(a) a **lista de assuntos e a sequência** em que são ensinados — fatos e ideias não são
protegidos; (b) o **método/abordagem historiográfica** do autor, descrito com palavras próprias;
(c) o **recorte temporal e geográfico**. Títulos de capítulo/seção aparecem apenas como
referência de estrutura (índice), no mínimo necessário para reconstruir a ordem curricular.
Nenhuma frase do corpo do texto foi copiada.

---

## 0. Nota metodológica — como estes PDFs foram lidos

Diferente do estudo `02-biologia.md`, aqui **não parei em "não extraível"**. Quatro dos oito
arquivos são imagem escaneada pura (0 caractere de texto). Para esses, usei duas rotas:

1. **Outline/bookmarks do PDF** (`pypdf`, `reader.outline` + `get_destination_page_number`) —
   recupera o sumário estruturado **sem OCR**, quando existe. Funcionou em 2 de 4 escaneados.
2. **Renderização de página → leitura visual** (PyMuPDF `get_pixmap` → PNG → leitura pelo
   modelo). Recupera sumário e amostras de miolo de qualquer escaneado legível.
   *Truque útil:* para reconstruir a estrutura de um livro sem sumário, montei uma **tira
   vertical com só o rodapé de 27 páginas espaçadas** numa única imagem — os cabeçalhos
   correntes revelam a divisão em seções em 2 leituras em vez de 55.

`pdftoppm`/poppler **não** está instalado nesta máquina (só `pdftotext.exe` em `/mingw64/bin`),
e o Python do sistema é gerido por `uv` e recusa `pip install`. Solução: venv em scratchpad +
`pymupdf`. Scripts em `…/scratchpad/render.py` e `…/scratchpad/footers.py`.

**DPI real do escaneamento** (medido: pixels da imagem ÷ tamanho da página em polegadas) —
determina se OCR clássico é viável:

| Livro | DPI | Camada | Viabilidade de OCR (tesseract) |
|---|---|---|---|
| Boris Fausto | **~500** | PNG 1 canal, 1 coluna, fonte serifada limpa | ✅ **Ótima** — melhor candidato a OCR de todo o acervo |
| Eduardo Bueno | ~200 | JPEG cor, layout complexo | ⚠️ Média — texto contorna imagens, caixas coloridas; segmentação de coluna vai errar |
| Ross (Geo. do Brasil) | **~100** | JPEG cor | ❌ Ruim — 100 DPI está abaixo do piso prático (~150–300). Legível por um VLM, **não** por OCR |

---

## 1. Inventário

| # | Arquivo | Obra / autoria | Idioma | Nível | Extraível? | Páginas |
|---|---------|----------------|--------|-------|-----------|---------|
| 1 | `427957074-Historia-Do-Brasil-Boris-Fausto.pdf` | Boris Fausto, *História do Brasil*, EDUSP (ed. ~1994) | PT-BR | Ensino médio avançado + superior | ❌ texto: **0 chars** · ✅ **outline completo** (12 caps) · ✅ sumário legível por render | 535 PDF (livro chega a 649; **PDF truncado**, ver §1.1) |
| 2 | `618114205-Historia-Do-Brasil-Eduardo-Bueno.pdf` | Eduardo Bueno, *História do Brasil* — coleção de fascículos Folha de S.Paulo | PT-BR | Divulgação / vestibular | ❌ texto: **0 chars** · ❌ sem outline · ✅ estrutura reconstruída via rodapés | 333 PDF / 320 impressas |
| 3 | `631730024-…Emma-Marriott….pdf` | Emma Marriott, *A História do Mundo para Quem Tem Pressa*, Valentina 2015 (trad. de *The History of the World in Bite-Sized Chunks*) | PT-BR (tradução) | Divulgação | ⚠️ **Só o esqueleto** — ver §1.2. **17,9 KB de texto em 167 páginas** | 167 |
| 4 | `599093572-Jurandyr-Sanches-Ross-Geografia-do-Brasil-2005.pdf` | J. L. S. Ross (org.), *Geografia do Brasil*, EDUSP — obra coletiva do Depto. de Geografia da USP | PT-BR | Ensino médio (projeto USP) escrito em nível exigente | ❌ texto: **0 chars** · ❌ sem outline · ✅ sumário legível por render (100 DPI) | 550 PDF / 547 impressas — **completo** |
| 5 | `476318402-geografia-fisica.pdf` | M. Camargo Filho & A. M. Kataoka, *Geografia Física: breve introdução à ciência geográfica*, Ed. UNICENTRO, 2019 | PT-BR | Superior introdutório | ✅ **Sim** (105 KB) | 139 PDF / 138 impressas |
| 6 | `472494447-geografia-urbana.pdf` | Fernanda Lodi Trevisan, *Geografia Urbana*, Ed. e Distrib. Educacional (Kroton), 2018 | PT-BR | Superior EaD | ✅ **Sim, integral** (377 KB) | 190 PDF / 192 impressas |
| 7 | `538115933-Geografia-Regional.pdf` | Manoella de Souza Soares, *Geografia Regional do Brasil*, IESDE Brasil, 2. ed. 2018 | PT-BR | Superior EaD | ✅ **Sim, integral** (312 KB) | 132 PDF / 128 impressas |
| 8 | `515469171-Geografia-ciencia-da-sociedade.pdf` | Manuel Correia de Andrade, *Geografia: Ciência da Sociedade*, Ed. Universitária UFPE, 2. ed. 2008 | PT-BR | Superior — epistemologia/história do pensamento geográfico | ⚠️ **Sim, mas OCR podre** (385 KB) — ver §1.3 | 247 |

**Resumo brutal: 3 de 8 realmente utilizáveis como texto** (#5, #6, #7) — e os três são
**geografia**. Do lado da **história, zero fontes com texto extraível.** As duas melhores
referências (Fausto e Ross) existem só como imagem, e das duas apenas Fausto está em DPI
que justifica OCR.

### 1.1 Fausto: o PDF está truncado — e a parte truncada era a mais valiosa

O outline aponta o cap. 12 na página impressa 551 = página 530 do PDF (offset −21). O sumário
lista depois disso:

- **Cronologia Histórica** — p. 557–596 (≈40 páginas)
- **Glossário Biográfico** — p. 597–640 (≈44 páginas)
- Referências Bibliográficas — p. 641
- Fonte Iconográfica — p. 649

Página impressa 557 corresponderia à página ~578 do PDF, mas **o PDF tem só 535**. Verifiquei
por renderização: a p. 533 do PDF é a impressa 555 (fim do cap. 12) e a 535 está em branco.
**Conclusão: cronologia e glossário biográfico não estão no arquivo.**

Isso dói. Uma cronologia é literalmente uma tabela `data → evento`, e um glossário biográfico é
uma tabela `pessoa → quem foi`. Eram os dois blocos do acervo inteiro com o formato mais próximo
do que um modelo factualmente fraco precisa. **Vale procurar outra cópia do PDF só por essas
84 páginas.** (O Bueno, #2, tem uma "Cronologia" nas p. 313–320 — 8 páginas, muito menor,
e escaneada em 200 DPI.)

### 1.2 Marriott: o conteúdo do livro não está lá

Diagnóstico técnico: o PDF é uma conversão ePub→PDF **quebrada**. Amostras por página:
p. 25 = 51 chars, p. 50 = 7 chars, p. 75 = 17, p. 100 = 22, p. 150 = 31. Total do livro
inteiro: **17.905 caracteres em 167 páginas** (~107 chars/página).

Verifiquei se o texto tinha virado imagem: `get_images()` retorna **0 imagens** nas páginas
testadas. Renderizei a p. 50 — a página aparece **visualmente em branco**, com apenas o título
"Os Celtas" em versalete no meio. O corpo do texto simplesmente **não existe** no arquivo.

O que sobrou e é aproveitável: o **outline completo**, com 6 capítulos e ~120 verbetes. É um
esqueleto curricular de história mundial excelente — e é *só* isso. **Não use como fonte de
conteúdo; não existe conteúdo.**

### 1.3 Andrade: o OCR está corrompido de forma sistemática

O PDF tem camada de texto (foi OCRado), mas a ligadura **`fi` foi engolida em todo o livro**:
aparecem `geográico`, `Geograia`, `classiicá-la`, `modiicando`, `suiciente`, `artiicial`,
`loresta`, `supericie`, `bibliograia`. Cabeçalhos correntes perdem letras inteiras
(`MNUEL COEIA DE NDADE`, `GEOGFA`, `CAÁTER`, `GEOGÁFICA`, `BBLIOGAFIA`). Números viram letras
(`soo mm` em vez de `500 mm`).

Para um corpus de **pré-treino de LLM isso é veneno**: ensinaria grafias erradas de português
com alta frequência, e justamente em palavras do domínio (*geografia*, *científico*, *superfície*).
Só é utilizável depois de um passe de correção — o padrão é regular (`fi`→∅) e portanto
corrigível com dicionário + regra, mas **não é trabalho de zero custo**.

---

## 2. Currículo de HISTÓRIA DO BRASIL

Linha do tempo consolidada. Coluna **F** = Boris Fausto (acadêmico, 12 capítulos e 27
subseções só no colonial); coluna **B** = Eduardo Bueno (divulgação, 1 tema por página,
seções de 6 páginas). Onde os dois cobrem, o tema é consenso curricular.

| # | Período | Recorte | Temas — Fausto (F) | Temas — Bueno (B) |
|---|---|---|---|---|
| 0 | **Pré-História e povoamento** | ~12.000 AP → 1500 | ❌ **ausente** — Fausto começa em Portugal | ✅ Geologia e Pré-História; tradições líticas; megafauna; Lagoa Santa |
| 1 | **Antecedentes da expansão marítima** | séc. XIV–XV | gosto pela aventura; técnicas de navegação e a nova mentalidade; atração pelo ouro e especiarias; feitorias na costa africana; ocupação das ilhas atlânticas; a chegada | O Descobrimento (2 seções) |
| 2 | **Brasil Colonial** | 1500–1822 | **27 subtemas** — os índios; periodização; exploração inicial (pau-brasil); capitanias hereditárias; governo-geral; consolidação; trabalho compulsório; escravidão indígena e africana; mercantilismo; "exclusivo" colonial; grande propriedade e monocultura de exportação; Estado e Igreja; Estado absolutista e "bem comum"; instituições administrativas; divisões sociais; Estado e sociedade; primeiras atividades econômicas; invasões holandesas; colonização do Norte; do Sudeste e Centro-Sul; ouro e diamantes; crise do Antigo Regime; crise do sistema colonial; movimentos de rebeldia; vinda da família real; a Independência; balanço do fim do período | O Brasil Indígena; Capitanias Hereditárias e Governo Geral; Os Jesuítas; Os Bandeirantes; A Ameaça Externa (2); O Brasil Holandês; O Ciclo da Mineração; A Escravidão (2); A Inconfidência Mineira; A Família Real no Brasil |
| 3 | **Primeiro Reinado** | 1822–1831 | consolidação da Independência; transição sem abalos; a Constituinte; Constituição de 1824; Confederação do Equador; abdicação de D. Pedro I | A Independência e o Primeiro Reinado (+ *O Brasil dos Viajantes* ×2, *A Amazônia* — temas que Fausto não tem) |
| 4 | **Regência** | 1831–1840 | reformas institucionais; revoltas provinciais; a política no período regencial | A Regência e as Revoluções (2 seções) |
| 5 | **Segundo Reinado** | 1840–1889 | o "Regresso"; luta contra o Império centralizado; acordo das elites e o "parlamentarismo"; os partidos — semelhanças e diferenças; preservação da unidade territorial; estrutura socioeconômica e escravidão; Guerra do Paraguai; crise do Segundo Reinado; balanço econômico e populacional | O Segundo Reinado; A Guerra do Paraguai; A Abolição (2 seções) |
| 6 | **Primeira República** | 1889–1930 | 1ª Constituição republicana; Encilhamento; Deodoro; Floriano; Revolução Federalista; Prudente de Morais; Campos Sales; características políticas do período; Estado e burguesia do café; mudanças socioeconômicas 1890–1930; movimentos sociais; processo político dos anos 20; Revolução de 1930 | A Proclamação da República; A República de 10 Anos; **Sangue no Pampa e no Sertão** (2); O Brasil dos Imigrantes; O Reinado do Café-com-Leite; A 1ª Guerra e os Anos 20 (2); **A Cultura: de Machado ao Pau-Brasil**; Dos 18 do Forte à Coluna Prestes; A Revolução de 30 (2) |
| 7 | **Estado getulista** | 1930–1945 | colaboração Estado–Igreja; centralização; política do café; política trabalhista; educação; processo político 1930-34; gestação do Estado Novo; o Estado Novo; mudanças no Brasil 1920–1940 | O Estado Novo; O Fim da Era Vargas |
| 8 | **Período democrático** | 1945–1964 | eleição de Dutra; Constituição de 1946; gov. Dutra; novo governo Vargas; eleição de JK; gov. JK; sucessão presidencial; gov. Jânio Quadros; sucessão de Jânio; gov. João Goulart | A Era JK, Jânio e Jango (2 seções) |
| 9 | **Regime militar** | 1964–1985 | AI-1 e a repressão; Castelo Branco; Costa e Silva; junta militar; Médici; Geisel; Figueiredo; caracterização geral do regime; morte de Tancredo | O Golpe de 1964; Os Anos de Chumbo; **A Cultura nos Anos 60 e 70** (2 seções) |
| 10 | **Transição / Nova República** | 1985–1989 | gov. Sarney: política econômica; Plano Cruzado; eleições de 1986; Assembleia Nacional Constituinte; avaliação da transição | Das Diretas a Sarney |
| 11 | **Balanço estrutural** | 1950–1980 | população; economia; indicadores sociais (*capítulo temático, não cronológico*) | — |
| 12 | **Nova ordem mundial / Brasil contemporâneo** | 1990→ | "A Nova Ordem Mundial e o Brasil" — capítulo curto, ~5 pág. Recorte para **~1992/94** | De Collor a FHC; **O Brasil do Terceiro Milênio** (2 seções) — chega a ~2002 |

**Recorte temporal final:**
Fausto termina no início dos anos 90 (o texto da p. 555 discute a quebra do Estado "no final
dos anos 80" e uma sequência de planos econômicos fracassados — é uma edição pré-Plano Real).
Bueno vai até o início dos anos 2000. **Nenhum dos dois cobre nada depois de ~2002.** Todo
o século XXI brasileiro está fora do acervo.

---

## 3. Currículo de HISTÓRIA MUNDIAL

Fonte única: outline do Marriott (**conteúdo inexistente — só o esqueleto**, ver §1.2).
6 capítulos, ~120 verbetes. Recorte declarado: 3500 a.C. → meados do séc. XX.

### Cap. 1 — Primeiros Impérios e Civilizações (≈3500–800 a.C.)
Suméria · Egito Antigo (Antigo Império) · Egito (Médio e Novo Império) · Babilônia · Império
Hitita · Assíria · Fenícia · Civilização do Vale do Indo · Era Védica e o Hinduísmo ·
Civilização Chinesa antiga · Minoicos · Micênicos · Olmecas e Chavín.

### Cap. 2 — O Mundo Antigo
Império Aquemênida · Império Parta · Império Sassânida · Hebreus e o monoteísmo · nascimento
do Cristianismo · Reino de Cuche · era cartaginesa · Budismo · Impérios Maurya e Gupta / era
dourada da Índia · dinastias Chin e Han e Confúcio · Etruscos e a fundação de Roma · Grécia
Antiga e o nascimento da democracia · Alexandre e o período helenístico · República Romana ·
Império Romano · Celtas · culturas peruanas · outras culturas nas Américas.

### Cap. 3 — A Idade Média
Axum, Império de Gana, migração banto · nascimento do Islamismo · Califado Abássida ·
Califado Fatímida · era dourada da China · Reformas Taika no Japão · Império Gaznávida ·
Império Bizantino · migrações bárbaras · crescimento do Cristianismo · Império Franco e
Carlos Magno · Vikings · eslavos e magiares · Grande Cisma · Teotihuacán, Huari e Tiahuanaco ·
Maias (2 verbetes: história e cultura) · Toltecas.

### Cap. 4 — O Mundo em Movimento
Almorávidas e Almôadas · Mali e Songhai · impérios da África Ocidental, Grande Zimbábue,
costa suaíli · **explorações portuguesas e o início do tráfico atlântico** · turcos seljúcidas ·
Cruzadas · ascensão do Império Otomano · Otomanos: renascimento e declínio · Império Safávida ·
unificação do Japão · Império Mongol · dinastia Timúrida · Peste Negra · dinastia Ming ·
Império Mogol e o Siquismo · feudalismo e conquistas normandas · crescimento do comércio ·
Guerra dos Cem Anos · Renascença · Reforma e Contrarreforma · explorações europeias e impérios
mercantis · monarquia absoluta (Carlos I, Luís XIV) · Astecas · Incas · conquistadores
espanhóis · Nova França · assentamentos europeus na América do Norte · descobertas nas ilhas
do Pacífico.

### Cap. 5 — Revoluções e Imperialismo Europeu
Impérios Oyo e Ashanti · exploração europeia do interior africano · tráfico de escravos e
abolição · partilha da África · sul da África · Xá Nader na Pérsia · apogeu da China manchu ·
britânicos na Índia · Guerras do Ópio e Rebelião Taiping · Restauração Meiji · ascensão da
Rússia · guerras do séc. XVIII e o surgimento da Prússia · Iluminismo · Revolução Francesa ·
guerras revolucionárias/napoleônicas e o Congresso de Viena · Revolução Industrial · sociedade
industrial, marxismo e revoltas · "Questão Oriental" e Guerra da Crimeia · migrações
populacionais · ascensão do Estado nacional · Revolução Americana · **guerras de independência
na América Latina** · expansão dos EUA e "Destino Manifesto" · Guerra Civil americana ·
James Cook e a Austrália · colonização da Nova Zelândia e do Pacífico.

### Cap. 6 — Uma Nova Ordem Mundial
Resistência ao domínio colonial · União Sul-Africana e Império Etíope · dissolução do Império
Otomano · Palestina e o movimento sionista · Rebelião dos Boxers e Revolução Chinesa de 1911 ·
ascensão do Japão · Guerra Civil Chinesa · independência da Índia · Tríplice Entente e corrida
armamentista · eclosão da 1ª Guerra e a Frente Ocidental · Frente Oriental e outros teatros ·
fim da Grande Guerra · gripe espanhola · sufrágio feminino · Revolução Russa e a URSS ·
Mussolini e o fascismo · Hitler e a Alemanha nazista · Guerra Civil Espanhola · 2ª Guerra
Mundial · fim da 2ª Guerra · vitória sobre o Japão e o Holocausto · anos 20, Grande Depressão
e New Deal · **desdobramentos na América Latina** · Austrália e Nova Zelândia.

### ⚠️ Buraco de cobertura do único currículo mundial disponível

O livro **acaba na 2ª Guerra / imediato pós-guerra**. Não há capítulo sobre:
**Guerra Fria · descolonização africana e asiática pós-1945 · Revolução Cubana · Guerra do
Vietnã · Estado de Israel e conflitos árabe-israelenses · Revolução Iraniana · queda do Muro e
fim da URSS · China pós-Mao · globalização · 11 de setembro · qualquer coisa do séc. XXI.**

Ou seja: **os últimos 80 anos de história mundial estão inteiramente fora do acervo.** Se o
Bee tiver que responder sobre o mundo contemporâneo, o material terá de ser escrito do zero
sem nenhuma referência de estrutura vinda daqui.

Há também um viés de foco declarado pela própria organização: a obra dá espaço proporcional
grande a impérios africanos, asiáticos e pré-colombianos (mérito raro em livro de divulgação
ocidental), mas **o Brasil aparece só de raspão**, dentro de "guerras de independência na
América Latina" e "desdobramentos nos países latino-americanos".

---

## 4. Currículo de GEOGRAFIA

### 4.1 GEOGRAFIA FÍSICA — `476318402` (UNICENTRO, 138 p, ✅ extraível)

Ordem de ensino (páginas impressas):

1. **Astronomia posicional / Terra como corpo** (p. 19) — principais movimentos do planeta;
   consequências dos movimentos no dia a dia (p. 38).
2. **Atmosfera e sua dinâmica** (p. 42).
3. **Geomorfologia** (p. 59) — o bloco dominante do livro, ~70 das 138 páginas:
   - estrutura terrestre (p. 61): composição mineralógica da crosta; rochas ígneas,
     sedimentares, metamórficas
   - a crosta e sua dinâmica (p. 69) — tectônica
   - fragmentação e deformação das rochas (p. 73) — intemperismo, dobras, falhas
   - as grandes paisagens da Terra (p. 78)
   - domínios morfoestruturais (p. 80)
   - processos exógenos (p. 83)
   - geomorfologia fluvial (p. 87); hierarquia fluvial (p. 95); bacias hidrográficas (p. 97)
   - relevos derivados (p. 99) — bacias sedimentares, *cuestas*, costões, *hogbacks*
   - geomorfologia cárstica (p. 105)
   - geomorfologia costeira (p. 111)
   - **geomorfologia do Brasil** (p. 119)
4. **Trabalhos de campo** (p. 125) — metodologia.

⚠️ **Assimetria grave:** é um livro de *geomorfologia* com um capítulo de atmosfera na frente.
**Não há capítulo de climatologia propriamente dita, nem de pedologia (solos), nem de
biogeografia/hidrologia oceânica.** Quem quiser cobrir geografia física completa precisa
complementar — e o complemento existe: é o cap. 2 do Ross (§4.4).

### 4.2 GEOGRAFIA URBANA — `472494447` (Kroton, 192 p, ✅ extraível, 377 KB)

Estrutura: 4 unidades × 3 seções = **12 seções**, 48 temas.

| Unidade | Seções |
|---|---|
| **1. A Geografia Urbana e o estudo das cidades** | 1.1 contribuições no contexto da *Nova Geografia* (Escola de Chicago / ecologia urbana; geografia quantitativa) · 1.2 contribuições no contexto da *Geografia Nova* (virada crítica) · 1.3 o espaço urbano e o processo de urbanização (rede urbana, segregação socioespacial, geotecnologias) |
| **2. Capitalismo e urbanização mundial** | 2.1 a cidade na história da humanidade · 2.2 expansão do capitalismo e urbanização mundial · 2.3 o espaço urbano nos séc. XX e XXI |
| **3. A urbanização brasileira** | 3.1 urbanização na formação territorial brasileira (de São Vicente/1532 ao planejamento desenvolvimentista dos anos 70-80) · 3.2 rede urbana brasileira (metropolização e desmetropolização) · 3.3 Estatuto da Cidade e perspectivas de reforma urbana |
| **4. Cidadania, meio ambiente e desenvolvimento** | 4.1 cidade e meio ambiente · 4.2 cidade e desenvolvimento · 4.3 cidade e cidadania |

**Método:** aprendizagem baseada em problema. Cada unidade abre com uma *situação-problema*
narrativa protagonizada por um personagem fictício (ex.: uma geógrafa de departamento de
cartografia de prefeitura) e a seção fecha resolvendo-a. Blocos didáticos recorrentes, com
contagem exata no livro: **12× "Não pode faltar"** (exposição), **12× "Assimile"**,
**12× "Exemplificando"**, **22× "Reflita"**, **14× "Pesquise mais"**, **12× "Sem medo de
errar"** (resolução comentada da situação-problema), **12× "Faça valer a pena"** (bateria de
questões objetivas, estilo ENEM/concurso: lacunas, assertivas I-II-III, asserção-razão).

### 4.3 GEOGRAFIA REGIONAL — `538115933` (IESDE, 128 p, ✅ extraível, 312 KB)

⚠️ **Cuidado com o título:** não é geografia regional *do mundo* (Europa, Ásia, África…).
É **teoria da regionalização aplicada ao Brasil**. Quem esperar "continentes" não vai achar.

| Cap. | Conteúdo |
|---|---|
| 1 | **O conceito de região** — a região na história do pensamento geográfico; quadro-síntese; a região na contemporaneidade |
| 2 | **Planejamento regional** — região como escala de planejamento; planejamento regional e desenvolvimento econômico no Brasil; para além das superintendências (SUDENE/SUDAM etc.) |
| 3 | **O Estado e a escala regional** — território e poder; ordenamento territorial; o BNDES como agente do planejamento regional |
| 4 | **O IBGE e a regionalização oficial do Brasil** — história e influência do IBGE; produção/disseminação de conhecimento; **a regionalização oficial (as 5 grandes regiões)** |
| 5 | **A regionalização do território brasileiro** — a descrição como síntese; trabalho de campo; a região como produto-síntese |
| 6 | **Divisão regional do Brasil** — os **complexos regionais** (Amazônia / Nordeste / Centro-Sul); a proposta de Roberto Lobato Corrêa; transformações pela geografia crítica (Milton Santos, Ruy Moreira, Geiger) |
| 7 | **As regiões brasileiras: caracterização** — 7.1 Norte, Centro-Oeste e Nordeste · 7.2 Sul e Sudeste · 7.3 síntese |
| 8 | **A questão regional além da regionalização** — região como pertencimento e geografia cultural; a região cultural pelo IBGE; a dicotomia da geografia |

**Método:** 8 capítulos, cada um com **"Ampliando seus conhecimentos"** (excerto de artigo
acadêmico citado com fonte) + **"Atividades"** (3–4 questões **discursivas**) + **"Gabarito"**
consolidado no fim (p. 121). O gabarito é **misto**: parte respostas modelo de verdade,
parte apenas roteiro do que o aluno deveria abordar.

⚠️ Artefato de diagramação: o rodapé corrente das páginas finais traz um título de **outro
livro** da mesma editora ("Avaliação do impacto e licenciamento ambiental"). Reaproveitamento
de template. Se este PDF virar corpus, esse rodapé entra como ruído repetido — filtrar.

### 4.4 GEOGRAFIA DO BRASIL — `599093572` Ross/USP (547 p, ❌ escaneado 100 DPI)

**A referência mais completa de geografia do Brasil do acervo — e a que está em pior estado
técnico.** Obra coletiva do Departamento de Geografia da FFLCH-USP; o prefácio declara que
nasceu de um projeto da USP para renovar o ensino médio, com a intenção explícita de produzir
conteúdo **analítico-descritivo e interpretativo, não de memorização**, e de tratar cada
assunto na perspectiva global antes da brasileira.

| Cap. | Autoria | Conteúdo |
|---|---|---|
| **1. Os Fundamentos da Geografia da Natureza** (p. 13) | J. L. S. Ross | 1.1 a geografia: da natureza à sociedade · 1.2 o planeta Terra como corpo dinâmico · 1.3 a superfície da Terra: estruturas e formas do relevo · 1.4 processos endógenos · 1.5 processos exógenos · **1.6 estruturas e formas do relevo brasileiro** · **1.7 unidades do relevo brasileiro** |
| **2. Geoecologia: o clima, os solos e a biota** (p. 67) | J. B. Conti & S. A. Furlan | 2.1 o clima: atmosfera e vida terrestre · 2.2 os mecanismos do clima · **2.3 características climáticas do território brasileiro** · 2.4 a biosfera · 2.5 a vida e os ambientes no tempo e no espaço · **2.6 os grandes domínios de vegetação: o caso brasileiro** · 2.7 zoogeografia · 2.8 biogeografia e conservação da natureza |
| **3. A Sociedade Industrial e o Ambiente** (p. 209) | Ross | 3.1 evolução técnico-industrial e qualidade de vida · 3.2 problemas ambientais urbanos e industriais · 3.3 problemas ambientais rurais · 3.4 efeitos ambientais da mineração |
| **4. A Mundialização do Capitalismo e a Geopolítica Mundial no Fim do Séc. XX** (p. 239) | A. U. de Oliveira | 4.1 mundialização do capitalismo · 4.2 nova divisão internacional do trabalho · 4.3 expansão geográfica das multinacionais · 4.4 grandes instituições financeiras mundiais · 4.5 formação dos blocos econômicos · 4.6 transformações no Leste Europeu · 4.7 formação territorial do mundo no fim do séc. XX |
| **5. A Inserção do Brasil no Capitalismo Monopolista Mundial** (p. 289) | A. U. de Oliveira | 5.1 o Brasil na fase monopolista · 5.2 a lógica da dívida externa brasileira · 5.3 a economia política da dominação no Brasil · 5.4 o Brasil na geografia da dominação monopolista · 5.5 distribuição da renda nacional |
| **6. O Espaço Industrial Brasileiro** (p. 327) | F. C. Scarlato | 6.1 sociedade, industrialização e regionalização do Brasil · 6.2 natureza técnica e econômica das indústrias e sua distribuição no território · 6.3 perfil atual da evolução industrial e distribuição espacial |
| **7. População e Urbanização Brasileira** (p. 381) | F. C. Scarlato | 7.1 população · 7.2 urbanização |
| **8. Agricultura Brasileira: Transformações Recentes** (p. 465) | A. U. de Oliveira | 8.1 industrialização da agricultura · 8.2 estrutura fundiária brasileira · 8.3 estrutura agrária: relações de produção e trabalho no campo · 8.4 produção agropecuária · 8.5 reordenação territorial do campo e novas fronteiras agrícolas · 8.6 movimentos sociais no campo e reforma agrária |
| — | | **Glossário** (p. 535) · Referências (541) · Fontes iconográficas (547) |

Tem **Glossário** — outro bloco `termo → definição` valioso, e ele **está** dentro do PDF
(p. 535 de 547).

### 4.5 EPISTEMOLOGIA DA GEOGRAFIA — `515469171` Manuel Correia de Andrade (246 p, ⚠️ OCR ruim)

Não é geografia descritiva; é **história do pensamento geográfico**. Ordem:

1. A Geografia como ciência (o que é; interdisciplinaridade; unidade e diversidade; caráter social)
2. Ideias geográficas na Antiguidade (povos primitivos; Oriente; gregos; romanos)
3. A Geografia na Idade Média (árabes; povos do norte; grandes viagens; conhecimento do território)
4. A Geografia dos tempos modernos (capitalismo e expansão; caminho marítimo para as Índias;
   busca da Índia pelo Ocidente; expansão na Ásia setentrional; precursores)
5. Surgimento da Geografia contemporânea (Humboldt e Ritter; Ratzel e a geografia do poder;
   Reclus e Kropotkin — geografia libertária)
6. A Geografia clássica (escolas alemã, francesa, britânica, norte-americana, russa)
7. **Institucionalização da geografia brasileira** (universidades; IBGE/CNG; AGB; Congresso Internacional)
8. A 2ª Guerra e as modificações no pensamento geográfico
9. A busca de novos paradigmas (corrente teórico-quantitativa; geografia do comportamento e da percepção)
10. Geografia e ação (conjuntura social; corrente ecológica; **geografia crítica ou radical**)
11. A Geografia e a problemática do mundo atual

---

## 5. Divergências de abordagem — onde os autores discordam

Esta é a seção que mais importa para decidir o que ensinar. Não é opinião: cada divergência
abaixo está ancorada em declaração de método do próprio autor ou na estrutura do sumário.

### 5.1 Fausto × Bueno: dois Brasis diferentes

| Eixo | Boris Fausto | Eduardo Bueno |
|---|---|---|
| **Gênero** | Historiografia acadêmica de síntese | Divulgação — fascículos de jornal, 1 tema por página, ~700 imagens em 320 páginas |
| **Cultura** | **Excluída deliberadamente.** Na Introdução ele declara ter deixado de fora as manifestações culturais em sentido estrito, dando exemplos do que sacrificou (o arcadismo/arquitetura/música do séc. XVIII mineiro; o modernismo nos anos 20) e explicando que a relação entre estrutura socioeconômica e cultura é um problema à parte, que exigiria outro caminho — e que outro volume da coleção trataria de literatura | **Central.** Duas seções inteiras: *A Cultura: de Machado ao Pau-Brasil* e *A Cultura nos Anos 60 e 70* (2 seções) |
| **Pré-cabralino** | Não existe. O livro abre nas causas da expansão marítima europeia | Abre com *Geologia e Pré-História* + *O Brasil Indígena* — 12 páginas antes de qualquer português |
| **Eixo explicativo** | Integra o econômico, o político-social e, em certa medida, o ideológico da formação social brasileira | Encadeamento cronológico de episódios, com conexão passado-presente-futuro declarada como objetivo |
| **Postura declarada** | Rejeita **duas** teses opostas: (a) a do Brasil como evolução/progresso permanente — que ele chama de simplista e diz que os anos recentes desmentiram; (b) a do imobilismo, que enfatiza clientelismo, corrupção e imposição do Estado sobre a sociedade — que ele associa ao pensamento conservador e acusa de sugerir a inutilidade do esforço de mudança | Não declara posição historiográfica; a "Apresentação" promete clareza, objetividade, dinamismo e bom humor |
| **Autoconsciência** | Alta e explícita: diz que todo estudo histórico pressupõe um recorte feito pelo historiador, que a própria seleção de dados depende das concepções do pesquisador, e que o leitor tem em mãos **uma** História do Brasil, não **a** História do Brasil | Ausente — a obra se apresenta como referência de consulta |
| **Anedota / biografia** | Marginal | Estruturante: cada página traz uma caixa lateral com um perfil biográfico ou episódio curioso (naturalistas, personagens secundários) |
| **Recorte final** | ~1992/94 | ~2002 |
| **Granularidade** | 12 capítulos, ~100 subseções numeradas; o colonial sozinho tem 27 | ~45 seções de 6 páginas |

**Divergência mais consequente para o Bee:** o Brasil colonial. Fausto gasta 27 subseções e
~105 páginas em **estruturas** (mercantilismo, exclusivo colonial, monocultura de exportação,
Estado absolutista, instituições administrativas, divisões sociais, trabalho compulsório).
Bueno gasta o mesmo trecho em **agentes e episódios** (jesuítas, bandeirantes, holandeses,
Inconfidência). São currículos com o mesmo rótulo e conteúdo factual quase disjunto.

### 5.2 Dentro do próprio Ross: três geografias num livro só

O livro é coletivo e **os capítulos não compartilham método**:

- Caps. 1–2 (Ross; Conti & Furlan) — **geografia física clássica**, descritiva-analítica,
  vocabulário técnico, taxonomias de relevo/clima/vegetação. Neutro.
- Caps. 4, 5, 8 (Ariovaldo Umbelino de Oliveira) — **geografia crítica marxista** com
  vocabulário de teoria da dependência: "mundialização do capitalismo", "capitalismo
  monopolista", "lógica da dívida externa", "economia política da dominação", "geografia da
  dominação". Uma amostra da p. 297 argumenta que o parque industrial brasileiro é substitutivo
  de importação, sem infraestrutura própria, dependente do exterior em insumos e tecnologia, e
  que o país é organizado para produzir e exportar primários — tese clássica de dependência,
  apresentada como diagnóstico, não como uma interpretação entre outras.
- Caps. 6–7 (Scarlato) — intermediário, descritivo-econômico.

Um leitor que estude "geografia do Brasil por Ross" recebe física neutra e humana engajada
**sem aviso de transição**. O sumário não sinaliza isso; só a autoria por capítulo denuncia.

### 5.3 Geografia Regional × Geografia Urbana: mesma escola, ênfases diferentes

Ambos são EaD e ambos passam pela virada crítica, mas:

- **Regional (IESDE)** trata a região como *conceito em disputa* e dedica o cap. 8 a uma saída
  humanística/cultural (região como pertencimento), inclusive propondo regionalizar o Brasil a
  partir de obras literárias. É a fonte **menos** determinista do acervo.
- **Urbana (Kroton)** declara na abertura que cabe à Geografia revelar as **contradições** do
  espaço urbano, e organiza a Unidade 2 inteira sob o título "Capitalismo e urbanização
  mundial". A ênfase é conflito e desigualdade.

### 5.4 Andrade × todos: a geografia é ciência social

Andrade define a Geografia como **Ciência Social**, com a Sociedade como sujeito e a Natureza
como objeto, e defende a superação da divisão física/humana numa geografia única. Isso
**contradiz frontalmente** a arquitetura do livro do Ross (que separa "geografia da natureza"
nos caps. 1–2 e "sociedade" dos caps. 3–8) e a do UNICENTRO (geografia física autônoma).
É uma divergência epistemológica real, não estilística — e determina se o material do Bee
deve ensinar "geografia física" e "geografia humana" como duas matérias ou como uma.

---

## 6. Conceitos que rendem exercício TEXTUAL

O Bee só lê texto puro. A pergunta certa não é "esse assunto tem mapa?" — é
**"o fato sobrevive à conversão em prosa sem perder o que se quer ensinar?"**.
Aplicando esse critério com rigor:

### ✅ Sobrevive integralmente — sem nenhuma perda

**HISTÓRIA — praticamente tudo.** História é nativamente textual. Rendem exercício direto:

| Tipo | Exemplo de forma |
|---|---|
| `data → evento` | "Em que ano foi criada a Constituição outorgada do Império?" |
| `evento → data` | inverso do anterior |
| `pessoa → cargo/período` | "Quem governou o Brasil entre a abdicação e a maioridade?" |
| `causa → consequência` | encadeamento explícito (crise do sistema colonial → movimentos de rebeldia) |
| `ordem cronológica` | "Coloque em ordem: Guerra do Paraguai, Abolição, Proclamação da República" |
| `instituição → função` | governo-geral, capitanias hereditárias, AI-1, Estatuto da Cidade |
| `ator → conflito` | Confederação do Equador, Revolução Federalista, Coluna Prestes |
| `período → característica` | "O que caracterizou a política de café-com-leite?" |
| `conceito → definição` | mercantilismo, exclusivo colonial, parlamentarismo do Segundo Reinado |

**GEOGRAFIA — as camadas relacionais e taxonômicas.** Isso é maior do que parece:

- **Enumerações com atributos.** A seção 1.7 do Ross ("Unidades do relevo brasileiro") é, na
  prática, um gazetteer em prosa: cada unidade vem com faixa de altimetria, limites, tipo de
  modelado e substrato geológico. Amostra da p. 61 (depressões marginais amazônicas, do
  Araguaia, cuiabana, do Alto Paraguai/Guaporé) traz altitudes em metros e relações de
  contato explícitas. **Zero dependência de mapa** — o texto já é a informação.
- **Taxonomias e definições de processo.** Tipos de rocha, intemperismo, tectônica, processos
  exógenos, cuestas/hogbacks/costões, carste, geomorfologia costeira, mecanismos do clima,
  hierarquia fluvial. São definições verbais com critérios discretos. Ideal para `termo → definição`
  e `definição → termo`.
- **Relações de vizinhança e pertencimento verbalizadas.** "O rio X é afluente da margem
  esquerda do rio Y"; "o estado Z faz divisa com A, B e C"; "a região Norte é composta pelos
  estados …". **Um grafo é texto.** Um mapa é uma renderização de um grafo — mas o grafo é o
  fato, e ele cabe em frase.
- **Correlações clima ↔ vegetação ↔ solo ↔ uso.** Domínios de vegetação brasileiros, tipos
  climáticos, biomas. Correlação é proposição, não figura.
- **Números e séries.** População, urbanização, produção, comércio exterior. Tabelas viram
  frases (`em 1990, X% das importações eram de equipamentos industriais`).
- **Teoria urbana e regional inteira.** Rede urbana, metropolização/desmetropolização,
  segregação socioespacial, Estatuto da Cidade, critérios de regionalização, os complexos
  regionais, escolas do pensamento geográfico, quem foi cada autor. É argumento verbal puro.
- **Marcos legais e institucionais.** IBGE, SUDENE/SUDAM, BNDES, Estatuto da Cidade.

### ⚠️ Sobrevive, mas só se for **reescrito** para forma verbal

Não basta extrair — precisa de trabalho de redação:

- **Localização absoluta.** "Onde fica a Chapada Diamantina" é ruim; "a Chapada Diamantina
  situa-se no centro do estado da Bahia, separando as bacias do São Francisco e do
  Paraguaçu" é bom. A regra: **substituir dêixis cartográfica por descrição relacional nomeada.**
- **Divisão regional.** Vira lista de estados por região — ótima — desde que alguém escreva a
  lista. O livro assume que o aluno olha o mapa.
- **Perfis, blocos-diagrama, cortes topográficos.** Recuperáveis como descrição sequencial
  ("da costa para o interior, encontra-se sucessivamente…").
- **Climogramas.** Viram tabela de médias mensais em texto. A leitura *do gráfico* morre; o
  *fato climático* sobrevive.

### ❌ Não sobrevive — descartar sem tentativa

- **Alfabetização cartográfica.** Escala, projeções, legenda, curvas de nível, orientação,
  coordenadas *lidas de um mapa*. O objeto de aprendizagem **é** a imagem. Não há paráfrase honesta.
- **Interpretação de mapa temático / fotografia aérea / imagem de satélite.** Idem.
- **Qualquer questão que comece com "observe a figura/imagem/mapa abaixo".** Presentes no
  Geografia Urbana (a questão 2 da seção 1.3 traz uma foto do Rio de Janeiro).
  ⚠️ Nesse caso específico as três assertivas I-II-III são respondíveis só pelo texto — então
  **filtrar por triagem individual, não por regra automática**, senão joga fora questão boa.
- **Bueno inteiro como conteúdo.** É um livro de ~700 imagens em 320 páginas, com o texto
  contornando ilustrações. Mesmo OCRado, o resultado seria prosa fragmentada e desconexa da
  imagem que a ancora. Serve como **fonte de estrutura curricular**, não de texto.
- **A "Fonte Iconográfica" / "Fontes Iconográficas"** de Fausto e Ross.

### 🎯 O que efetivamente existe hoje, pronto, em formato de exercício

| Fonte | Formato | Volume | Tem gabarito? | Serve ao Bee? |
|---|---|---|---|---|
| Geografia Urbana | Objetivas (lacuna, assertivas I-II-III, asserção-razão) | **12 baterias**, ~3-4 questões cada → ~40 questões | Não localizado no PDF | ✅ **Sim** — formato ideal, mas sem chave |
| Geografia Regional | Discursivas | **8 baterias** × 3-4 → ~30 questões | ✅ Gabarito consolidado (p. 121) | ⚠️ **Parcial** — ver abaixo |
| Geografia Urbana | "Sem medo de errar" | 12 resoluções comentadas | — | ⚠️ Ancoradas na narrativa fictícia da unidade |
| Fausto | Cronologia + Glossário Biográfico | ~84 páginas | — | ❌ **Não está no PDF** (§1.1) |
| Ross | Glossário | p. 535–540 | — | ✅ Está no PDF, mas em 100 DPI escaneado |

**Ressalva honesta sobre o gabarito do Geografia Regional:** boa parte das respostas não é
resposta — é roteiro metodológico ("é importante lembrar que…", "você deve refletir sobre…",
"para responder essa questão, é importante…"). E as perguntas são de **epistemologia da
geografia** ("relacione a definição do conceito de região com a temporalidade e espacialidade
de seus estudos"). Para um modelo de 151M **factualmente fraco**, treinar em dissertação sobre
o conceito de região é o alvo errado: exige exatamente a capacidade que o modelo não tem, e não
ensina o fato que falta. **Baixa prioridade.**

---

## 7. ⚠️ Alerta de viés — conteúdo com carga política/ideológica marcada

Não julgo o mérito de nenhuma destas posições. Marco porque **colocar qualquer um destes
textos num corpus de treino injeta o ponto de vista no modelo**, e essa decisão é do dono do
projeto. História e geografia humana são, dos domínios do acervo, os dois onde isso mais pesa
— o Bee não vai só aprender fatos, vai aprender a *moldura* em que os fatos foram postos.

| Fonte | Carga | Evidência |
|---|---|---|
| **Ross, caps. 4, 5, 8** (A. U. de Oliveira) — ⚠️ **o mais marcado do acervo** | Geografia crítica marxista / teoria da dependência | Títulos: "mundialização do capitalismo", "capitalismo monopolista mundial", "a lógica da dívida externa brasileira", "a economia política da **dominação** no Brasil", "o Brasil no contexto da geografia da **dominação** monopolista", "movimentos sociais no campo e a **reforma agrária**". A p. 297 apresenta como conclusão que o país é organizado para produzir primários e é dependente em insumos e tecnologia. São ~230 das 547 páginas — **42% do livro** |
| **Andrade, *Geografia: Ciência da Sociedade*** | Marxista, explícita e assumida | Periodiza o espaço por **modo de produção** (asiático, feudal, capitalista, socialista) como categoria analítica base; capítulo dedicado à "geografia crítica ou radical"; seção sobre "geografia libertária" (Reclus e Kropotkin); o prefácio enquadra o campo brasileiro como luta entre grandes proprietários e sem-terra |
| **Geografia Urbana (Kroton)** | Crítica, moderada | Declara na abertura que cabe à Geografia revelar as **contradições** do espaço urbano; a unidade 2 é "Capitalismo e urbanização mundial"; a abertura da unidade 3 fala em gestões "deficientes e corruptas". Os exercícios usam Milton Santos e Roberto Lobato Corrêa como autoridade |
| **Geografia Regional (IESDE)** | Crítica, leve | O gabarito define globalização como homogeneização gerada pelo sistema capitalista; a resposta do cap. 6 fala em "grau de desenvolvimento do capitalismo na organização socioespacial". Mas o cap. 8 abre para geografia humanística/cultural — **é a mais plural do acervo** |
| **Boris Fausto** | ⚠️ **Não é neutro, apesar da reputação de referência** | Rejeita explicitamente a tese "imobilista" (clientelismo/corrupção/Estado sobre a sociedade) **e a associa ao pensamento conservador**. Na p. 555 escreve sobre previdência saqueada por "gângsteres de colarinho branco", Estado dilapidado por "elites espertas", e questiona se a mão invisível do mercado não seria a mão dos oligopólios. **A favor dele:** é o único autor do acervo que **avisa** o leitor de que faz um recorte e de que a obra é "uma" e não "a" História do Brasil. Isso é honestidade intelectual, não ausência de posição |
| **Eduardo Bueno** | Baixa carga explícita, viés de seleção | Nenhuma declaração de posição. Mas a seleção é celebratória-narrativa e centrada em personagens; "Os Bandeirantes" como seção autônoma e "O Descobrimento" como enquadramento carregam uma tradição interpretativa própria |
| **Emma Marriott** | Baixa | Distribui espaço generoso a impérios africanos, asiáticos e pré-colombianos — contrapeso deliberado ao eurocentrismo. Contrapartida: o Brasil quase desaparece. **Irrelevante na prática — não há texto** |
| **UNICENTRO Geografia Física** | Uma posição declarada | A apresentação argumenta contra a dicotomia homem×natureza e propõe tratá-los como uma unidade ("homem natureza"). É posição filosófica, de baixo risco político |

**Assimetria a registrar:** **não há no acervo nenhuma fonte de geografia humana ou de história
econômica escrita de perspectiva liberal, institucionalista ou quantitativa.** Se todo o
material de geografia humana e história recente do Bee sair daqui, o modelo vai aprender uma
única moldura interpretativa e vai apresentá-la como descrição do mundo. Se isso é aceitável
ou não, é decisão do dono do projeto — mas é uma decisão, não um default.

Os capítulos **1, 2 e 3 do Ross** (relevo, clima, solos, biota, impactos ambientais) e o
**UNICENTRO inteiro** são de baixíssima carga e podem ser usados sem essa preocupação.

---

## 8. Veredito honesto

### Vale para ensinar o Bee? — **Geografia sim, História não.**

**HISTÓRIA — o acervo é insuficiente. Não dá para trabalhar com o que está aqui hoje.**

- História do Brasil: **0 caracteres extraíveis** nos dois livros.
- História mundial: o único livro **não contém o texto do livro** — é um arquivo defeituoso
  com 107 caracteres por página.
- As duas peças de maior valor (Cronologia + Glossário Biográfico do Fausto, 84 páginas em
  formato quase tabular) **foram truncadas do PDF**.
- Recorte temporal: nada depois de ~2002 no Brasil, nada depois da 2ª Guerra no mundo.

O que sobrou de história é **esqueleto curricular**, e como esqueleto é bom: dá a ordem
canônica de ensino, a granularidade de subtemas do Fausto e o contraponto de ênfase do Bueno.
Isso vale para *redigir material original* — que é justamente o objetivo declarado do estudo.
Mas não há uma linha de texto-fonte aproveitável.

**GEOGRAFIA — três livros utilizáveis hoje, ~795 KB de texto limpo em PT-BR.**

`geografia-urbana` (377 KB) + `Geografia-Regional` (312 KB) + `geografia-fisica` (106 KB).
Todos PT-BR contemporâneo, prosa didática, ortografia pós-Acordo, sem ruído de OCR. Dois deles
já vêm com baterias de exercícios; um com gabarito.

Ressalvas que impedem chamar isso de suficiente:

- **Cobertura desequilibrada.** Geomorfologia está muito bem servida (UNICENTRO + Ross cap. 1).
  **Climatologia, pedologia e hidrografia estão descobertas** nos livros extraíveis — só
  existem no Ross, que é imagem.
- **Nada de geografia do mundo.** Não há continentes, blocos econômicos descritos, geografia
  física de outros países. "Geografia Regional" é só regionalização do Brasil.
- **Escala.** ~795 KB é ordem de grandeza ~0,2M tokens. Contra os 9,87B tokens do pré-treino
  v3, é ruído estatístico. Estes livros valem como **fonte para escrever**, não como corpus.
- **Volume de exercício pronto é pequeno.** ~70 questões no total, das quais ~30 são
  discursivas de epistemologia (alvo errado para o Bee) e ~40 objetivas sem gabarito localizado.

### O que eu faria, em ordem

1. **OCRar o Boris Fausto.** É o único escaneado em ~500 DPI, PNG de 1 canal, coluna única,
   tipografia limpa. É o candidato a OCR de melhor relação custo-benefício do acervo inteiro
   (535 páginas de historiografia acadêmica em PT-BR). Fazer isso converte "história: zero
   fontes" em "história: uma fonte forte".
2. **Caçar outra cópia do PDF do Fausto** só pelas p. 557–640 (Cronologia + Glossário
   Biográfico). São 84 páginas de pares `data→evento` e `pessoa→quem foi` — exatamente o
   formato de que um modelo factualmente fraco precisa, e o mais barato de converter em
   milhares de pares de treino.
3. **Usar os esqueletos deste documento para escrever material original.** É o caminho já
   escolhido pelo projeto e o único que não esbarra em direito autoral. Os §2, §3 e §4 são a
   ementa; a redação é nova.
4. **Ross: transcrever seletivamente por VLM, não por OCR.** A 100 DPI o tesseract vai errar,
   mas as páginas são legíveis por leitura visual (comprovado). Priorizar: seção 1.7 (unidades
   do relevo, com altimetrias), cap. 2.3 (clima do Brasil), 2.6 (domínios de vegetação) e o
   Glossário (p. 535-540). São ~60 páginas de alto rendimento factual e **baixa carga ideológica**.
5. **Corrigir o OCR do Andrade antes de qualquer uso** — a falha é regular (`fi`→∅) e portanto
   automatizável, mas usar sem corrigir contamina a ortografia do modelo.
6. **Escrever do zero o que não existe:** Guerra Fria, descolonização, séc. XXI mundial e
   brasileiro, geografia dos continentes, climatologia e pedologia. O acervo não ajuda em nada
   disso.
7. **Decidir explicitamente a política de viés** antes de gerar conteúdo de geografia humana e
   história econômica — porque hoje 100% das fontes disponíveis para esses dois tópicos vêm da
   mesma escola interpretativa.
