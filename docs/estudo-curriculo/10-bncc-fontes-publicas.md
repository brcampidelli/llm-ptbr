# 10 — A espinha curricular brasileira como fonte licenciável (BNCC, ENEM/INEP e o resto do domínio público)

**Data:** 2026-08-04 · **Método:** verificação em fonte primária. Textos legais baixados do Planalto e lidos na íntegra; PDFs oficiais da BNCC e da Matriz do ENEM baixados e processados localmente (PyMuPDF) para contagem própria de habilidades; rodapés de licença lidos no HTML das próprias páginas. Onde não consegui chegar à fonte primária, está escrito **NÃO CONFIRMADA** — sem exceção.

> ## Veredito de uma linha
> **A espinha curricular resolve o *esqueleto*, não a *carne*.** A BNCC dá **1.583 códigos oficiais de "o que se deve saber"** — uma taxonomia granular, citável e (esta é a descoberta jurídica) **fora da proteção autoral, porque é anexo de ato normativo**. O ENEM dá **~3.700 itens com gabarito** e uma lista de objetos de conhecimento. Isso é a **semente perfeita** para um professor aberto gerar material didático original em PT-BR — mas nenhuma dessas fontes contém, ela própria, texto expositivo que ensine. **Substitui os 11 livros protegidos como *fonte de currículo*. Não substitui como *fonte de prosa*.** A prosa tem que ser gerada.

---

## 1. Situação legal — o que a lei brasileira efetivamente libera

### 1.1 O dispositivo decisivo: Lei 9.610/98, art. 8º

Texto literal, extraído do [Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) (baixado e lido em 2026-08-04):

> **Art. 8º** Não são objeto de proteção como direitos autorais de que trata esta Lei:
> **I** - as idéias, procedimentos normativos, sistemas, métodos, projetos ou conceitos matemáticos como tais;
> **II** - os esquemas, planos ou regras para realizar atos mentais, jogos ou negócios;
> **III** - os formulários em branco para serem preenchidos por qualquer tipo de informação, científica ou não, e suas instruções;
> **IV** - os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais;
> **V** - as informações de uso comum tais como calendários, agendas, cadastros ou legendas;
> **VI** - os nomes e títulos isolados;
> **VII** - o aproveitamento industrial ou comercial das idéias contidas nas obras.

Três incisos importam para o Bee, e o inciso IV é o mais forte:

- **IV — "demais atos oficiais".** É a porta pela qual a BNCC entra. Ver §1.2.
- **I — "conceitos matemáticos como tais"**. A regra da cadeia, o teorema de Pitágoras, o balanceamento de equação química: o *conceito* não é protegido. Só a *forma* com que um autor específico o expõe.
- **VII** — não se pode monopolizar o aproveitamento comercial das *ideias* contidas numa obra.

E o complemento no art. 7º, que fecha o raciocínio:

> **Art. 7º** São obras intelectuais protegidas as criações do espírito, expressas por qualquer meio (...)
> **§ 3º** No domínio das ciências, a proteção recairá sobre a **forma literária ou artística**, não abrangendo o seu **conteúdo científico ou técnico** (...)

**Tradução operacional:** *o que* o Amabis ensina sobre mitose não é dele. *Como* ele escreveu é. Reescrever o conteúdo com palavras novas é legal; copiar os parágrafos não é. Isso já era a premissa do projeto — agora está ancorada no dispositivo.

E o contrapeso, que fecha a porta do PNLD:

> **Art. 6º** Não serão de domínio da União, dos Estados, do Distrito Federal ou dos Municípios as obras por eles **simplesmente subvencionadas**.

Governo comprar não transfere direito. Livro do PNLD continua da editora — ver §4.

### 1.2 A BNCC é anexo de ato normativo — logo, art. 8º, IV

Este é o achado que autoriza tudo. A [Resolução CNE/CP nº 2, de 22/12/2017](https://www.computacional.com.br/docs_oficiais/CNE_RES_CNE_22017.pdf) (PDF oficial baixado e lido), diz literalmente:

> **Art. 1º** A presente Resolução e **seu Anexo** instituem a Base Nacional Comum Curricular (BNCC), como documento **de caráter normativo** que define o conjunto orgânico e progressivo de aprendizagens essenciais (...)

A BNCC **não é uma publicação do MEC**. É o **Anexo de uma Resolução do Conselho Nacional de Educação**, homologada pelo Parecer CNE/CP nº 15/2017 via **Portaria MEC nº 1.570, de 20/12/2017** (DOU de 21/12/2017, Seção 1, p. 146 — citação constante do preâmbulo da própria Resolução). O mesmo desenho vale para o Ensino Médio: **Resolução CNE/CP nº 4, de 17/12/2018**, que institui a BNCC-EM "e seu Anexo".

Anexo de resolução normativa federal = **"regulamento" / "demais atos oficiais"** do art. 8º, IV → **não é objeto de proteção autoral**. Pode ser copiado, redistribuído, reformatado, traduzido, fatiado em CSV e usado como semente de geração, sem licença e sem pedir nada a ninguém.

**Confirmação adicional:** o PDF oficial da BNCC (600 páginas, baixado e processado) **não traz ficha catalográfica, não traz "©", não traz "todos os direitos reservados"** e não traz nenhuma cláusula de reprodução. Ausência de reivindicação, coerente com a natureza de ato oficial.

### 1.3 A pegadinha do rodapé gov.br: CC BY-**ND** 3.0

Todo site do padrão gov.br — incluindo o do INEP — carrega no rodapé, em HTML verificado por mim:

> "Todo o conteúdo deste site está publicado sob a licença **[Creative Commons Atribuição-SemDerivações 3.0 Não Adaptada](https://creativecommons.org/licenses/by-nd/3.0/deed.pt_BR)**."

⚠️ **ND = NoDerivatives.** Isso é mais restritivo do que parece e mais permissivo do que parece, ao mesmo tempo:

| O que a CC BY-ND 3.0 permite | O que ela proíbe |
|---|---|
| Copiar e **redistribuir o material na íntegra**, inclusive **para fins comerciais**, com atribuição | **Distribuir versões adaptadas/derivadas** do material |

Ou seja: **espelhar o PDF do ENEM 2019 num dataset é permitido; publicar uma versão reescrita do enunciado não é.**

**Mas o rodapé não vence a lei.** Uma declaração genérica de licença aplicada por template a um portal inteiro não pode *criar* proteção sobre obra que a Lei 9.610 exclui do regime autoral (art. 8º). Para a BNCC e para o texto de leis/resoluções, o rodapé é juridicamente inócuo: não há direito a licenciar. Para os **itens de prova do ENEM** — que são criações literárias autorais, não atos oficiais — o rodapé é o que temos, e ele vale.

> ⚖️ **Honestidade obrigatória:** isto é a minha leitura do texto legal a partir de fontes primárias, **não é parecer jurídico**. A distinção "BNCC = ato oficial" é sólida e tem apoio literal no art. 1º da Resolução. A questão "treinar modelo é obra derivada?" é **litigiosa no mundo inteiro e não está resolvida no Brasil**. Antes de publicar o corpus, isso passa por advogado. O que dá para afirmar com segurança hoje: **nada aqui tem a fragilidade dos 91 PDFs do Scribd** — lá o problema é a *procedência do arquivo*, não a interpretação de uma cláusula.

---

## 2. BNCC — estrutura e a anatomia dos códigos

### 2.1 Estado da norma em 2026-08 (confirmado)

| Etapa | Documento vigente | Instrumento |
|---|---|---|
| Educação Infantil + Ensino Fundamental | BNCC (versão de 2017/2018) | Resolução CNE/CP nº 2/2017 + Anexo |
| Ensino Médio | BNCC-EM (2018) | Resolução CNE/CP nº 4/2018 + Anexo |

**A revisão do Ensino Médio mudou a LEI, ainda não substituiu o texto da BNCC-EM.** A [Lei nº 14.945, de 31/07/2024](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14945.htm) (baixada e lida) alterou a LDB e criou o **art. 35-D**, que passa a *nomear as disciplinas dentro das áreas* — coisa que a BNCC-EM de 2018 deliberadamente não fazia:

> **Art. 35-D.** A Base Nacional Comum Curricular do ensino médio estabelecerá direitos e objetivos de aprendizagem, conforme diretrizes do Conselho Nacional de Educação, nas seguintes áreas do conhecimento:
> I - **linguagens e suas tecnologias**, integrada pela língua portuguesa e suas literaturas, língua inglesa, artes e educação física;
> II - **matemática e suas tecnologias**;
> III - **ciências da natureza e suas tecnologias**, integrada por biologia, física e química;
> IV - **ciências humanas e sociais aplicadas**, integrada por filosofia, geografia, história e sociologia.

Desdobramentos normativos já publicados: **Parecer CNE/CEB nº 4/2024** e **Resolução CNE/CEB nº 2, de 13/11/2024** (novas DCNEM); **Parecer CNE/CEB nº 7/2025** e **Resolução CNE/CEB nº 4, de 12/05/2025** (itinerários de aprofundamento). Carga horária: Formação Geral Básica mínima de **2.400 h** (2.100 h quando integrada a curso técnico), itinerários com mínimo de **600 h**. Implementação escalonada a partir de 2025 (1ª série), 2026 (2ª série).

⚠️ **Não localizei publicação de um texto novo e homologado da BNCC-EM até 2026-08-04.** Trate os códigos `EM13*` como vigentes, **mas instáveis**: a hierarquia por disciplina do art. 35-D tende a produzir uma recodificação. Para o Bee isso é irrelevante no curto prazo (o conteúdo de biologia não muda porque o código mudou), mas é relevante se o dataset for publicado com os códigos como metadado — vale versionar (`bncc_versao: "2018"`).

### 2.2 Anatomia do código de habilidade

O código tem **4 blocos** e é lido da esquerda para a direita:

```
EF06CI01           EM13CNT101          EF69LP44           EI03ET05
│ │ │  │            │  │  │  │          │ │  │ │           │ │ │  │
│ │ │  └ nº seq.    │  │  │  └ comp.1 + hab.01            │ │ │  └ nº seq.
│ │ └── componente  │  │  └ área CNT   │ │  │ └ nº seq.   │ │ └ campo de experiência
│ └──── ano (6º)    │  └ "13" = qualquer série do EM      │ └ faixa etária (4a7m–5a11m)
└────── etapa (EF)  └ etapa (EM)       │ └ componente LP  └ etapa (Educação Infantil)
                                       └ faixa 6º–9º ano
```

- **Etapa:** `EI` (Educação Infantil) · `EF` (Fundamental) · `EM` (Médio)
- **Ano/faixa:** `01`–`09` = ano específico; `12`, `15`, `35`, `67`, `69`, `89` = faixa de anos; `13` no EM = "qualquer série"
- **Componente/área:** `LP` Língua Portuguesa · `MA` Matemática · `CI` Ciências · `HI` História · `GE` Geografia · `AR` Arte · `EF` Educação Física · `LI` Língua Inglesa · `ER` Ensino Religioso · no EM: `LGG` Linguagens · `MAT` Matemática · `CNT` Ciências da Natureza · `CHS` Ciências Humanas e Sociais Aplicadas · `LP` Língua Portuguesa
- **Sequencial:** 2 dígitos no EF, 3 no EM (onde o 1º dígito é a competência específica da área). **Não indica dificuldade nem ordem de ensino** — é só endereço.

### 2.3 Contagem própria (extração dos PDFs oficiais)

Números obtidos por regex sobre o texto extraído dos dois PDFs oficiais (`BNCC_EI_EF_110518_versaofinal_site.pdf`, 600 p.; `BNCC_EnsinoMedio_embaixa_site_110518.pdf`, 154 p.), deduplicados por código único:

| Etapa | Códigos únicos |
|---|---|
| Educação Infantil (objetivos de aprendizagem e desenvolvimento) | **93** |
| Ensino Fundamental (habilidades) | **1.304** |
| Ensino Médio (habilidades) | **186** |
| **TOTAL** | **1.583** |

**Ensino Fundamental, por componente:**

| Componente | Habilidades |
|---|---|
| Língua Portuguesa (`LP`) | 391 |
| Matemática (`MA`) | 247 |
| História (`HI`) | 151 |
| Geografia (`GE`) | 123 |
| Ciências (`CI`) | 111 |
| Língua Inglesa (`LI`) | 88 |
| Educação Física (`EF`) | 69 |
| Ensino Religioso (`ER`) | 63 |
| Arte (`AR`) | 61 |

**Ensino Médio, por área:**

| Área/componente | Habilidades |
|---|---|
| Língua Portuguesa (`EM13LP`) | 54 |
| Matemática e suas Tecnologias (`EM13MAT`) | 46 |
| Ciências Humanas e Sociais Aplicadas (`EM13CHS`) | 32 |
| Linguagens e suas Tecnologias (`EM13LGG`) | 28 |
| Ciências da Natureza e suas Tecnologias (`EM13CNT`) | 26 |

⚠️ **Margem de erro da contagem:** a extração é de camada de texto; páginas renderizadas como imagem e códigos quebrados por hifenização podem escapar. Cruzando os dois PDFs encontrei 3 códigos (`EM13MAT408/409/512`) presentes num arquivo e não no outro. Trate os números como **±2%**, não como censo oficial. O número que circula na imprensa educacional ("mais de 1.600 habilidades para EF+EM") é compatível com o meu 1.490 de EF+EM se incluir a Educação Infantil.

### 2.4 Estrutura conceitual (para quem for gerar prompts)

- **10 Competências gerais da Educação Básica** — atravessam todas as etapas
- **Educação Infantil:** 5 **campos de experiência** (`EO` o eu/o outro/o nós · `CG` corpo, gestos e movimentos · `TS` traços, sons, cores e formas · `EF` escuta, fala, pensamento e imaginação · `ET` espaços, tempos, quantidades, relações e transformações) × 3 grupos etários. **Pouco útil para o Bee** (é currículo de bebê, não gera texto expositivo).
- **Ensino Fundamental:** 5 áreas → 9 componentes; cada componente tem **competências específicas**, e as habilidades se organizam por **unidades temáticas → objetos de conhecimento → habilidades**. ⭐ Esse encadeamento "objeto de conhecimento → habilidade" é literalmente um índice de aula pronto.
- **Ensino Médio:** 4 áreas; **competências específicas de área** (o 1º dígito do sequencial) → habilidades transversais às 3 séries.

---

## 3. Matriz de Referência do ENEM

Documento oficial: `matriz_referencia.pdf`, 24 páginas, baixado do INEP e lido na íntegra.

### 3.1 Cinco eixos cognitivos (comuns às 4 áreas)

| Eixo | Sigla | O que é |
|---|---|---|
| I. Dominar linguagens | DL | norma culta + linguagens matemática, artística, científica, espanhol/inglês |
| II. Compreender fenômenos | CF | aplicar conceitos para entender fenômenos naturais, processos histórico-geográficos, produção tecnológica, manifestações artísticas |
| III. Enfrentar situações-problema | SP | selecionar, organizar, relacionar e interpretar dados para decidir |
| IV. Construir argumentação | CA | relacionar informações e conhecimentos para argumentar de forma consistente |
| V. Elaborar propostas | EP | propor intervenção solidária respeitando valores humanos e diversidade |

### 3.2 Competências e habilidades por área (contagem própria)

| Área | Competências de área | Habilidades |
|---|---|---|
| Linguagens, Códigos e suas Tecnologias | 9 | 30 (H1–H30) |
| Matemática e suas Tecnologias | 7 | 30 (H1–H30) |
| Ciências da Natureza e suas Tecnologias | 8 | 30 (H1–H30) |
| Ciências Humanas e suas Tecnologias | 6 | 30 (H1–H30) |
| **Total** | **30** | **120** |

⚠️ A numeração `H1..H30` **reinicia em cada área** — `H12` de Matemática ≠ `H12` de Humanas. Ao usar como semente, sempre qualifique (`MT-H12`).

### 3.3 Objetos de conhecimento

A última seção do PDF traz **"Objetos de conhecimento associados às Matrizes de Referência"**: ~22 mil caracteres, **41 blocos temáticos de nível 1**, **56 sub-itens** e, quebrando os blocos pelos separadores internos, **~98 tópicos granulares**. Distribuição:

| Área | Blocos de nível 1 | Volume relativo |
|---|---|---|
| 1. Linguagens, Códigos e suas Tecnologias | 8 | 4.3 k chars |
| 2. Matemática e suas Tecnologias | 5 | 1.2 k chars |
| 3. Ciências da Natureza e suas Tecnologias | 23 | 11.7 k chars |
| 4. Ciências Humanas e suas Tecnologias | 5 | 4.4 k chars |

Exemplos reais de granularidade (Ciências Humanas): *"A Conquista da América. Conflitos entre europeus e indígenas na América colonial"* · *"Economia agro-exportadora brasileira: complexo açucareiro; a mineração no período colonial; a economia cafeeira; a borracha na Amazônia"* · *"Estrutura interna da terra. Estruturas do solo e do relevo; agentes internos e externos modeladores do relevo"*.

⭐ **É exatamente o índice dos livros de História do Brasil e Geografia do Brasil que não podemos usar** — na forma de lista oficial, curta, e fora do regime autoral (é anexo técnico de exame público; e ainda que fosse protegido, é lista de tópicos = art. 8º, I/VI). Essa lista, sozinha, substitui o *sumário* do Boris Fausto e do Jurandyr Ross.

---

## 4. ⭐ Tabela de fontes públicas brasileiras

Legenda de licença: ✅ **confirmada em fonte primária** · ⚠️ **parcial / com ressalva** · ❌ **não confirmada** · 🚫 **incompatível com corpus publicável**

| # | Recurso | Conteúdo | Volume aprox. | Licença | URL | Download em massa |
|---|---|---|---|---|---|---|
| 1 | **BNCC — documento completo** | apesar do nome do arquivo (`EI_EF`), o PDF de 600 p. traz as três etapas; 1.397 códigos de EI+EF + os do EM | 600 p. / 3,0 MB PDF / 1,1 M chars | ✅ **Fora do regime autoral** — Lei 9.610 art. 8º, IV (anexo da Res. CNE/CP 2/2017). PDF sem qualquer nota de © | `basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf` | `curl` direto (302 → `cdn.mec.gov.br`) |
| 2 | **BNCC (EM)** | 186 habilidades EM13* | 154 p. / 1,1 MB PDF | ✅ idem (Res. CNE/CP 4/2018) | `basenacionalcomum.mec.gov.br/images/historico/BNCC_EnsinoMedio_embaixa_site_110518.pdf` | `curl` direto |
| 3 | **BNCC em planilha** | mesmas habilidades em formato tabular editável | 1.583 linhas | ✅ idem | `downloadbncc.mec.gov.br` (SPA Angular, API em `bnccapi.mec.gov.br`) | ⚠️ **a API não respondeu** nos meus testes (timeout em :80 e :443, 2026-08-04). Fallback: extrair os códigos do PDF por regex — foi o que fiz, e funciona |
| 4 | **Matriz de Referência ENEM** | 5 eixos, 30 competências, 120 habilidades, ~98 objetos de conhecimento | 24 p. / 178 KB PDF | ⚠️ rodapé gov.br CC BY-ND 3.0; conteúdo é lista de tópicos → art. 8º I/VI | `download.inep.gov.br/download/enem/matriz_referencia.pdf` | `curl` (host instável — precisou 2 tentativas) |
| 5 | **Provas e gabaritos ENEM** | cadernos completos 1998–2025 | ~28 edições, ~3.700 itens | ⚠️ **CC BY-ND 3.0** (rodapé gov.br verificado no HTML). Permite redistribuição íntegra; **proíbe versões derivadas** | `gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos` | abas carregadas por JS; links reais estão nos ZIPs de microdados (#6) e no repositório RIEP |
| 6 | **Microdados ENEM** | ⭐ provas + gabaritos + **parâmetros de item (TRI)** + notas + questionário | 1998–2025, ZIPs de centenas de MB a GB | ❌ **NÃO CONFIRMADA.** Ver §5.2 | `gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem` | ZIP por edição, HTTP direto |
| 7 | **Legislação federal (Planalto)** | Constituição, códigos, todas as leis e decretos | dezenas de milhares de atos | ✅ **art. 8º, IV — sem proteção** | `planalto.gov.br/ccivil_03/` | HTML previsível por URL; sem API. Alternativa estruturada: LexML |
| 8 | **Wikipédia PT** | enciclopédia geral | **2,5 GB** (`pages-articles.xml.bz2`, dump 2026-07-01) | ✅ **CC BY-SA 4.0 + GFDL** ([dumps.wikimedia.org/legal.html](https://dumps.wikimedia.org/legal.html)) | `dumps.wikimedia.org/ptwiki/` | dump mensal oficial |
| 9 | **Wikcionário PT** | dicionário, etimologia, flexão | 66,1 MB | ✅ CC BY-SA 4.0 | `dumps.wikimedia.org/ptwiktionary/` | dump mensal |
| 10 | **Wikisource PT** | textos de domínio público, literatura, legislação | 80,4 MB | ✅ CC BY-SA 4.0 (+ obras em DP) | `dumps.wikimedia.org/ptwikisource/` | dump mensal |
| 11 | **Wikilivros PT** | livros-texto colaborativos | 20,7 MB | ✅ CC BY-SA 4.0 | `dumps.wikimedia.org/ptwikibooks/` | dump mensal |
| 12 | **Wikiversidade PT** | material de curso | 18,0 MB | ✅ CC BY-SA 4.0 | `dumps.wikimedia.org/ptwikiversity/` | dump mensal |
| 13 | **Portal Domínio Público (MEC)** | ⭐ literatura, teses, obras em DP | **~200 mil obras** (≈174 mil em texto) — confirmado ativo em abr/2026 | ⚠️ **por obra**: parte é DP real, parte é "divulgação autorizada". **Não há licença de portal** | `dominiopublico.mec.gov.br` | 🚫 sem API; JSP com formulário e `co_obra` sequencial. Scraping possível, mas **a licença tem de ser checada obra a obra** |
| 14 | **SciELO Brasil** | artigos científicos revisados, muitos em PT | centenas de milhares de artigos | ✅ **CC BY 4.0** (verificado no rodapé de periódico) — *por periódico*, checar caso a caso | `scielo.br` | OAI-PMH + API; há dumps de terceiros |
| 15 | **IBGE — dados** | estatística, séries, malhas | enorme | ⚠️ dado bruto = fato, não obra (art. 8º V). Uso livre citando a fonte, na prática | `servicodados.ibge.gov.br/api/docs` | ✅ **API REST pública, sem chave** |
| 16 | **IBGE — publicações** | livros, atlas, metodologia | milhares de PDFs | ❌ **NÃO CONFIRMADA.** Publicação que abri traz "**© IBGE. 2021**". A página "Termos de Uso" só lista termos de *serviços*, não licença de conteúdo | `biblioteca.ibge.gov.br` | HTTP direto, mas ver licença |
| 17 | **Embrapa (Infoteca-e)** | agronomia, solos, clima, alimentos — PT-BR técnico e didático | dezenas de milhares de docs | 🚫 **CC BY-NC-ND 4.0** (declarado no rodapé do repositório) — **NC + ND: fora** | `infoteca.cnptia.embrapa.br` | DSpace/OAI-PMH |
| 18 | **Fiocruz (ARCA)** | saúde pública, biologia, epidemiologia | dezenas de milhares | ❌ **por item.** Rodapé declara "Política de Acesso Aberto"; badge por item diz "Acesso aberto", **que não é licença** | `arca.fiocruz.br` | DSpace 7 + OAI-PMH |
| 19 | **Khan Academy PT** | matemática e ciências, didático, já em PT-BR | grande | 🚫 **CC BY-NC-SA** — confirmado na central de ajuda (atualizada 15/07/2026), com definição *ampla* de "não comercial" | `pt.khanacademy.org` | 🚫 sem dump público |
| 20 | **Livros do PNLD** | os melhores livros didáticos do país | ~centenas de títulos | 🚫 **direito autoral das EDITORAS.** O FNDE *compra e distribui*; a inscrição é feita "pelas empresas detentoras de direitos autorais". Lei 9.610 art. 6º: subvenção não transfere direito. O PNLD Digital foi anunciado justamente com "proteção dos direitos autorais das editoras" | `fnde.gov.br` | 🚫 |
| 21 | **Plataforma MEC RED** | recursos educacionais digitais curados, alinhados à BNCC | "mais de 20 mil recursos" | ❌ **NÃO CONFIRMADA.** Portal informa Creative Commons, mas **por recurso** e com divergências relatadas entre plataforma e fonte parceira | `mecred.mec.gov.br` / `plataformaintegrada.mec.gov.br` | ❌ SPA; endpoint `/recursos` retornou 404 |
| 22 | **Portal do Professor (MEC)** | planos de aula | histórico | ❌ **NÃO CONFIRMADA / acesso bloqueado.** `portaldoprofessor.mec.gov.br` respondeu apenas com desafio Cloudflare | `portaldoprofessor.mec.gov.br` | ❌ |
| 23 | **e-Aulas USP / UNIVESP** | videoaulas universitárias em PT-BR | e-Aulas: 1.317+ h de vídeo | ❌ **NÃO CONFIRMADA.** "Acesso aberto/livre" ≠ licença. Não achei declaração CC | `eaulas.usp.br` · YouTube UNIVESP | ⚠️ e ainda exigiria ASR — custo alto, licença duvidosa |

### 4.1 Resumo brutal da tabela

- **Verde e sem discussão:** BNCC (1–3), legislação (7), universo Wikimedia (8–12). São as fundações.
- **Verde com atribuição por item:** SciELO (14).
- **Amarelo, usável com cuidado:** Matriz e provas do ENEM (4–5) — redistribuir na íntegra sim, reescrever não; **mas usar como *semente* de geração é seguro por outro caminho** (§6).
- **Vermelho para corpus publicável:** Khan Academy, Embrapa, PNLD. Todos por cláusula **NC** ou **ND** ou por direito de terceiro. Nenhum deles entra.
- **Cinza (precisa de trabalho de curadoria antes de decidir):** Domínio Público, Fiocruz, MEC RED, IBGE publicações.

---

## 5. Provas do ENEM e microdados do INEP — a leitura precisa

### 5.1 Disponibilidade

- **Edições com prova + gabarito publicados: 1998 a 2025** (a página do INEP tem abas por ano cobrindo toda a série; os microdados listam 1998–2025).
- **Formato:** PDF por caderno (cores azul/amarela/cinza/branca/rosa), mais gabaritos oficiais.
- **Volume estimado de itens:** de 2009 em diante são **180 questões por edição** (4 áreas × 45) + redação; 1998–2008, **63 questões**. Isso dá ≈ **3.060 + 693 ≈ 3.750 itens objetivos com gabarito**, mais ~28 propostas de redação com competências de correção. *(Estimativa aritmética minha; edições com reaplicação/anulação alteram a conta na margem.)*
- **Os microdados são melhores que os PDFs:** o pacote de cada edição inclui, além das provas e gabaritos, os **parâmetros de item da TRI** — discriminação, dificuldade, acerto casual. Isso é metadado que **nenhum livro didático tem**: permite ordenar o currículo por dificuldade empírica medida em milhões de estudantes.
- **Além do ENEM, mesmo regime:** Saeb, Encceja, Enade, Revalida — mais milhares de itens com gabarito, cobrindo do 5º ano à graduação.

### 5.2 A licença — a parte que exige honestidade

Três fatos verificados, que não fecham numa conclusão limpa:

1. **O rodapé do portal do INEP declara CC BY-ND 3.0** (verificado no HTML da própria página de provas e gabaritos, com `rel="license"` apontando para `creativecommons.org/licenses/by-nd/3.0/deed.pt_BR`).
2. **A Política e Plano de Dados Abertos do INEP** (PDF de 38 p. baixado e lido) **não declara licença para os microdados**. Pelo contrário: na coluna "o que melhorar" dos conjuntos de microdados (Censo Escolar, Censo da Educação Superior, ENEM), lista como **ação pendente** — *"atribuir licença aos dados (CC-BY)"*. Ou seja: **CC-BY é o que o INEP disse que pretendia fazer, não o que consta como feito.** Fontes secundárias que afirmam "os microdados são CC-BY" estão lendo essa coluna como se fosse declaração vigente. **Não é.**
3. **Os itens são obra autoral e o INEP é o titular.** Os editais do Banco Nacional de Itens exigem que o colaborador assine **Termo de Cessão de Direitos Autorais** ao INEP. Isso é bom: significa que **existe um titular único e público** que pode licenciar. Só não significa que já licenciou de forma clara.

**Conclusão operacional:**

| Uso | Situação |
|---|---|
| Baixar e estudar as provas | ✅ sem qualquer dúvida |
| Redistribuir os PDFs/itens **na íntegra**, com atribuição ao INEP | ✅ coberto pela CC BY-ND declarada (ND não proíbe cópia fiel) |
| Publicar itens **reescritos/parafraseados** no corpus | ❌ é exatamente o que a cláusula ND proíbe |
| Usar os itens como **referência para gerar questões NOVAS** sobre o mesmo objeto de conhecimento | ✅ o que se aproveita é o *método* e o *conteúdo científico* — art. 8º, I e art. 7º, §3º |
| Usar os **parâmetros TRI e gabaritos** como dado numérico | ✅ art. 8º, V (informação) — dado não é obra |

⚠️ **Ação recomendada, e é barata:** protocolar um pedido pela **Lei de Acesso à Informação (Lei 12.527/2011)** ao SIC do INEP perguntando textualmente qual licença se aplica aos microdados e aos cadernos de prova. Resposta em até 20 dias, por escrito, de órgão público. **Isso converte um "NÃO CONFIRMADA" em documento auditável** — e é exatamente o tipo de papel que um investidor quer ver na pasta de procedência.

---

## 6. ⭐ Como isso vira dado de treino

### 6.1 A ideia: a habilidade da BNCC como semente (padrão Cosmopedia)

A Cosmopedia gerou 25 bilhões de tokens sintéticos a partir de ~34 mil *seeds* temáticas, variando público-alvo e estilo. Aqui a semente é melhor: **não é um tópico vago raspado da web, é uma habilidade oficial, redigida por especialistas, com verbo de ação, objeto e etapa escolar definidos.**

Exemplo de semente real (`EF09CI13`, extraída do PDF):
> *"Propor iniciativas individuais e coletivas para a solução de problemas ambientais da cidade ou da comunidade, com base na análise de ações de consumo consciente e de sustentabilidade bem-sucedidas."*

Isso já contém: **etapa** (9º ano), **componente** (Ciências), **objeto** (sustentabilidade/consumo consciente), **verbo cognitivo** (propor = nível alto da taxonomia), e **contexto** (cidade/comunidade → ancoragem brasileira). É um briefing de aula completo em uma frase.

### 6.2 O eixo combinatório

Cada documento gerado é o produto de **quatro eixos independentes**:

```
habilidade BNCC  ×  formato didático  ×  registro/público  ×  ancoragem
   (1.490)             (8)                   (5)                (~6)
```

**Formatos didáticos (8)** — cada um produz um tipo de texto diferente, o que é bom para diversidade linguística:
1. Explicação expositiva (o "capítulo do livro")
2. Exemplo resolvido passo a passo
3. Exercício + gabarito comentado
4. Erro comum / concepção equivocada e por que está errada
5. Analogia e modelo mental
6. Diálogo professor–aluno (formato conversacional, útil também no SFT)
7. Conexão interdisciplinar (liga a habilidade a outra de outro componente)
8. Aplicação ao cotidiano brasileiro

**Registro/público (5):** anos iniciais · anos finais · ensino médio · vestibulando/ENEM · adulto retomando estudo (EJA).

**Ancoragem (~6):** regional (N/NE/CO/SE/S), urbana/rural, atualidade, história local, dado do IBGE, contexto de trabalho. ⭐ **Este eixo é o que os livros importados não dão e é a razão de ser do Bee** — um modelo brasileiro precisa saber que o rio da enchente é o Guaíba ou o Acre, não o Mississippi.

### 6.3 Dimensionamento

| Cenário | Docs/habilidade | Documentos | Tokens (a ~900 tok/doc) |
|---|---|---|---|
| **Mínimo — 1 doc por formato** | 8 | 11.920 | ~11 M |
| **SFT/midtraining sério** — formato × público | 40 | 59.600 | ~54 M |
| **Alvo realista** — formato × público × ancoragem | 240 | **357.600** | **~320 M** |
| **Teto combinatório** — + variação de seed por célula (×3) | 720 | 1.072.800 | ~965 M |

Base: 1.490 habilidades de EF+EM (deixo os 93 objetivos da Educação Infantil de fora — não geram texto expositivo útil).

**Camada 2, ortogonal:** os **~98 objetos de conhecimento da Matriz do ENEM** × os mesmos 8 formatos × 5 registros = **~3.900 documentos** de reforço no recorte específico de vestibular, mais denso e mais factual.

**Camada 3 — a que fecha o buraco factual:** a habilidade da BNCC diz *o que ensinar*, mas não fornece o *fato*. Para História e Geografia do Brasil (justamente os livros que perdemos), o fato tem que vir de outro lugar verificável. As duas fontes verdes servem:
- **Wikipédia PT** (CC BY-SA) como base factual a ser *reescrita* pelo professor aberto — o ShareAlike é o ponto de atenção se o texto gerado for derivado demais; gerar *a partir de* fato, e não *parafraseando* o artigo, mantém a distância.
- **Legislação e dados do IBGE** para fatos duros (fronteiras, população, marcos legais) — sem proteção autoral nenhuma.

### 6.4 Como reconciliar isso com o número real do Bee

O corpus atual do Bee tem **9,87 B tokens**. O cenário "alvo realista" acima entrega **~320 M tokens** — **3,2% do corpus**. Não parece muito, mas é a leitura errada. O aprendizado do projeto está na memória: *"mais token não resolve"* — o Gate 2 v3 mostrou que 2,6× mais dado rendeu ~0% de bpb.

**Então o cálculo certo não é "quanto isso soma ao corpus", é "quanto isso vale por token".** 320 M tokens de material didático denso, factual, estruturado, em PT-BR e alinhado ao currículo do país é qualitativamente diferente de 320 M tokens de web crawl. É exatamente o perfil de dado que a literatura de *midtraining* / *annealing* usa nos últimos 5–10% do treino, e é o perfil que o SFT precisa e não teve (o SFT do v3 passou no gate de forma e falhou no conteúdo — a lacuna era conteúdo, e é isto aqui).

### 6.5 Higiene de procedência (não pular)

Cada documento gerado carrega metadado:

```json
{
  "seed_tipo": "bncc_habilidade",
  "seed_id": "EF09CI13",
  "seed_texto_fonte": "Resolução CNE/CP nº 2/2017, Anexo (BNCC), PDF oficial p. 353",
  "seed_licenca": "ato oficial — Lei 9.610/98 art. 8º, IV",
  "bncc_versao": "2018",
  "formato": "exercicio_com_gabarito",
  "gerador": "<modelo teacher>",
  "gerador_tos_permite_destilacao": true,
  "data_geracao": "2026-08-..."
}
```

Isso é o que transforma "temos um dataset" em "temos um dataset auditável". O teacher continua sendo o elo que precisa de licença própria — a memória do projeto já registra que **build.nvidia.com permite destilar e Qwen não**. A BNCC resolve a procedência da *semente*, não a do *gerador*.

---

## 7. Veredito

**Substitui os livros protegidos? Parcialmente — e a parte que substitui é a mais difícil de reconstruir sozinho.**

**O que a espinha curricular pública RESOLVE (e resolve bem):**
1. **A pergunta "o que ensinar".** 1.583 habilidades oficiais + ~98 objetos de conhecimento do ENEM. Isso é o sumário do Boris Fausto, do Ross e do Amabis, em forma de lista oficial e licenciável. Um sumário construído por especialistas e validado nacionalmente é caro de fazer e nós ganhamos de graça.
2. **A procedência.** Passamos de "91 PDFs do Scribd" para "anexo de resolução do CNE, art. 8º IV da Lei 9.610". Não é uma melhora incremental de risco jurídico — é uma mudança de categoria. É a diferença entre um item que o auditor marca em vermelho e um item que ele nem pergunta.
3. **A ordenação por dificuldade.** Os parâmetros de TRI dos microdados do ENEM permitem ordenar conteúdo por dificuldade *medida*, não por intuição. Nenhum livro tem isso.
4. **A ancoragem brasileira.** A BNCC é explicitamente sobre o Brasil — território, história, literatura, sociedade. É o oposto de traduzir currículo americano.

**O que ela NÃO resolve (e é preciso dizer com todas as letras):**
1. **Não tem prosa.** A BNCC tem 1,1 M de caracteres, mas são enunciados de habilidade e texto de política educacional. **Não há um único parágrafo que explique o que é mitose.** Como *corpus*, ela vale ~0,3 M tokens e é péssima como texto de treino. O valor dela é 100% como **índice**, 0% como **conteúdo**.
2. **Não tem fato.** "Analisar a formação territorial brasileira" não contém a formação territorial brasileira. O fato tem de vir da Wikipédia PT, da legislação, do IBGE — ou do modelo teacher, com todo o risco de alucinação que isso implica. **Este é o buraco real**, e ele não fecha com currículo; fecha com verificação.
3. **Não substitui a qualidade pedagógica de um bom autor.** O Amabis explica bem. Um professor aberto gerando 240 variações de `EF09CI13` produz volume, não necessariamente boa explicação. **Isso exige avaliação** — e a boa notícia é que o ENEM entrega o *eval set* de graça: ~3.750 questões com gabarito oficial são um benchmark pronto, brasileiro, e que ninguém pode acusar de vazamento porque é público e datado.

**Recomendação em três passos:**

1. **Fazer agora (dias, custo zero):** extrair as 1.490 habilidades para JSONL com metadado de procedência; extrair os ~98 objetos de conhecimento da Matriz; baixar os dumps Wikimedia PT. Tudo isso é verde-confirmado e já dá para começar a gerar.
2. **Fazer em paralelo (semanas, custo zero):** protocolar o pedido LAI ao INEP sobre a licença dos microdados e das provas. E montar o eval a partir das provas do ENEM — que **podem ser usadas na íntegra** para avaliação, sem problema de ND.
3. **Não fazer:** Khan Academy, Embrapa e PNLD. NC/ND/terceiros. Não entrem nem "só para testar" — a memória do projeto registra que um token já vazou por atalho; um dado contaminado no corpus é pior, porque não dá para revogar depois de treinado.

**Em uma frase:** a BNCC não é o livro que perdemos — é o **índice** do livro que vamos escrever, e é o único pedaço da cadeia que agora está juridicamente blindado.

---

## Apêndice — receitas de download verificadas

```bash
# BNCC completa (EI + EF, 600 p.) — segue o 302 para cdn.mec.gov.br
curl -L -A "Mozilla/5.0" \
  https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf \
  -o bncc_eief.pdf

# BNCC Ensino Médio (154 p.)
curl -L -A "Mozilla/5.0" \
  https://basenacionalcomum.mec.gov.br/images/historico/BNCC_EnsinoMedio_embaixa_site_110518.pdf \
  -o bncc_em.pdf

# Matriz de Referência do ENEM (24 p.) — host instável, repetir se falhar
curl -L --http1.1 -A "Mozilla/5.0" \
  https://download.inep.gov.br/download/enem/matriz_referencia.pdf -o matriz_enem.pdf

# Lei 9.610/98 (encoding latin-1)
curl -L -A "Mozilla/5.0" https://www.planalto.gov.br/ccivil_03/leis/l9610.htm -o l9610.html

# Dumps Wikimedia PT (mensais)
BASE=https://dumps.wikimedia.org
for w in ptwiki ptwiktionary ptwikisource ptwikibooks ptwikiversity; do
  curl -O "$BASE/$w/latest/$w-latest-pages-articles.xml.bz2"
done
```

⚠️ **Nota de extração:** `pdftotext` falhou nos PDFs da BNCC ("Couldn't read xref table"). **PyMuPDF (`fitz`) leu sem problema** — só emite aviso de header JPX nas imagens, que é inofensivo para extração de texto.

```python
# extração das habilidades
import fitz, re
d = fitz.open('bncc_eief.pdf')
t = '\n'.join(p.get_text() for p in d)
RX = re.compile(r'\b(E[FIM]\d{2}(?:\d{2})?[A-Z]{2,3}\d{2,3}[A-Z]?)\b')
codigos = sorted(set(RX.findall(t)))   # 1.580 neste PDF (93 EI + 1.304 EF + 183 EM)
# cruzar com o PDF do EM recupera 3 códigos faltantes -> 1.583 no total
```

---

## Fontes primárias consultadas

- [Lei nº 9.610/1998 — Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) (arts. 6º, 7º, 8º lidos na íntegra)
- [Lei nº 14.945/2024 — Planalto](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14945.htm) (art. 35-D da LDB)
- [Resolução CNE/CP nº 2, de 22/12/2017 (PDF oficial)](https://www.computacional.com.br/docs_oficiais/CNE_RES_CNE_22017.pdf) — art. 1º: "a presente Resolução e seu Anexo instituem a BNCC"
- [Resolução CNE/CP nº 4, de 17/12/2018 — Imprensa Nacional](https://www.in.gov.br/materia/-/asset_publisher/Kujrw0TZC2Mb/content/id/55640296) (BNCC-EM)
- [Portal BNCC](https://basenacionalcomum.mec.gov.br/) e [Download da BNCC](https://downloadbncc.mec.gov.br/)
- [Matriz de Referência ENEM (PDF, INEP)](https://download.inep.gov.br/download/enem/matriz_referencia.pdf)
- [INEP — Provas e Gabaritos do ENEM](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos) (rodapé CC BY-ND 3.0 verificado no HTML)
- [INEP — Microdados do ENEM](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem)
- [Política e Plano de Dados Abertos do INEP (PDF)](https://download.inep.gov.br/publicacoes/institucionais/gestao_e_governanca/politica_e_plano_de_dados_abertos.pdf) — "atribuir licença aos dados (CC-BY)" listado como ação pendente
- [Wikimedia — License information about dump downloads](https://dumps.wikimedia.org/legal.html) e [dumps ptwiki](https://dumps.wikimedia.org/ptwiki/)
- [Khan Academy — Can I use Khan Academy's materials?](https://support.khanacademy.org/hc/en-us/articles/202262954-Can-I-use-Khan-Academy-s-videos-name-materials-links-in-my-project) (atualizado 15/07/2026)
- [Embrapa Infoteca-e](https://www.infoteca.cnptia.embrapa.br/infoteca/) (rodapé CC BY-NC-ND 4.0)
- [ARCA — Fiocruz](https://www.arca.fiocruz.br/)
- [Portal Domínio Público](https://dominiopublico.mec.gov.br/) · [MEC — o que é o Portal Domínio Público](https://portal.mec.gov.br/dominio-publico)
- [FNDE — funcionamento do PNLD](https://www.fnde.gov.br/index.php/programas/programas-do-livro/pnld/funcionamento)
- [IBGE — Termos de Uso](https://www.ibge.gov.br/acesso-informacao/acoes-e-programas/termos-de-uso.html) · publicação de amostra com "© IBGE"
- [SciELO Brasil](https://www.scielo.br/) (selo CC BY 4.0 verificado em periódico)
