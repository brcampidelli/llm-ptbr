# 02 — Esqueleto curricular: BIOLOGIA / CIÊNCIAS DA VIDA

> Estudo de currículo para o projeto **BEE** (LLM 151M PT-BR pré-treinada do zero).
> Objetivo: extrair **lista de tópicos, ordem de ensino, método pedagógico e pré-requisitos**
> dos livros de biologia disponíveis — para depois escrever material didático **original**.
> Data: 2026-08-04.

## ⚠️ Nota de direito autoral

Os PDFs analisados são obras protegidas. Este documento **não transcreve nem parafraseia
de perto** nenhum trecho dos livros. O que está registrado aqui é:
(a) a **lista de assuntos e a sequência** em que são ensinados — fatos e ideias não são
protegidos; (b) o **método pedagógico** do autor, descrito com palavras próprias;
(c) os **pré-requisitos** assumidos. Títulos de capítulo aparecem apenas como referência
de estrutura (índice), no mínimo necessário para reconstruir a ordem curricular.

---

## 1. Inventário

Testado com `pdftotext` (xpdf 4.00) em 4–7 faixas de páginas por arquivo, incluindo o miolo.
"Não extraível" = **0 caracteres** em todas as amostras → PDF é **imagem escaneada sem
camada de texto** (não há OCR embutido). Confirmado também que nenhum dos escaneados
tem *outline*/bookmarks (`/Title` = 0 ocorrências), então nem o sumário é recuperável.

| # | Arquivo | Obra / autoria | Idioma | Nível | Extraível? | Páginas |
|---|---------|----------------|--------|-------|-----------|---------|
| 1 | `585988339-Cooper-La-Celula-7-Edicion.pdf` | Cooper, *La Célula*, 7ª ed. | **Espanhol** | Superior — biologia celular e molecular | ❌ **Não** (escaneado; 0 chars em p. 1–25, 26–45, 50, 100, 200, 300, 400, 500, 600, 700, 800) | ~812 |
| 2 | `810490433-...Biologia-Das-Celulas-Volume-1-Amabis-e-Martho...pdf` | Amabis & Martho, *Biologia*, vol. 1 — Biologia das Células | PT-BR | Ensino médio | ❌ **Não** (escaneado; só aparecem anotações soltas de estudante digitadas por cima) | ~511 |
| 3 | `789377205-Amabis-Martho-Vol-3.pdf` | Amabis & Martho, *Biologia*, vol. 3 — Biologia das Populações | PT-BR | Ensino médio | ❌ **Não** (escaneado; recuperadas só 3 linhas de anotação: "1ª lei de Mendel", "2ª lei de Mendel", "a característica que aparece em F1 é a dominante") | ~453 |
| 4 | `696193902-Anatomia-e-Fisiologia-Humanas.pdf` | Giulianna da Rocha Borges, *Anatomia e Fisiologia Humanas*, IESDE Brasil, 2019 | **PT-BR** | Superior / EaD (introdutório) | ✅ **Sim, integral** | 372 |
| 5 | `610553518-ANATOMIA-para-estudantes-FMUL.pdf` | A. Gonçalves Ferreira, I. Álvares Furtado, L. Lucas Neto (coord.), *Anatomia Humana — Manual para Estudantes*, Prime Books, 2020 (FMUL) | **PT-PT** ⚠️ | Superior / Medicina | ✅ **Sim, integral** | ~804 |
| 6 | `898718618-Anatomia-Humana-Fattini-3ª-Ed.pdf` | D'Angelo & Fattini, *Anatomia Humana Sistêmica e Segmentar*, 3ª ed. | PT-BR | Superior | ❌ **Não** (escaneado; só a capa tem texto, com ruído de OCR) | 768 |
| 7 | `580050925-Bioquimica-4a-Ed-Devlin...pdf` | Thomas M. Devlin (coord.), *Bioquímica — Libro de Texto con Aplicaciones Clínicas*, 4ª ed. esp. (5ª ing.), Reverté | **Espanhol** | Superior / Medicina | ✅ **Sim, integral** | 1242 |
| 8 | `626037125-Fundamentos-de-Bioquimica-Estructural...pdf` | Blanco Gaitán, *Fundamentos de Bioquímica Estructural*, 3ª ed., Tébar Flores, 2017 | Espanhol | Superior | ❌ **Não** — a única camada de texto é a **marca d'água** do elibro.net repetida em toda página; o conteúdo é imagem | 549 |
| 9 | `510023457-Livro-Patologia-Geral.pdf` | Isadora Janolio de Oliveira *et al.*, *Patologia Geral*, Grupo Ânima Educação, 2017 | **PT-BR** | Superior / EaD (80 h) | ✅ **Sim, integral** | ~250 |

**Resumo brutal: 4 de 9 extraíveis.** E os 4 extraíveis são **anatomia, fisiologia,
bioquímica e patologia** — nível superior. **Nenhuma fonte extraível cobre biologia
propriamente dita** (citologia, genética, evolução, ecologia, botânica, zoologia).
Os dois volumes de Amabis & Martho — que eram a prioridade declarada, e a única
referência de ensino médio em PT-BR — estão **inutilizáveis sem OCR**.

**Distribuição de idioma nas fontes que sobraram:**
PT-BR 2 (#4, #9, ~620 pág.) · PT-PT 1 (#5, ~804 pág.) · Espanhol 1 (#7, 1242 pág.).

⚠️ **Sobre o #5 (FMUL, PT-PT):** é português europeu com ortografia **pré-Acordo** —
grafias como *dissecção, actualizando, acção, protecção, projectam, objectos, facto,
Egipto, sector, característica táctil* aparecem no corpo do texto, junto com léxico
lusitano (*ecrã*-like, *de facto*, *nomeadamente*). Para um modelo PT-BR isso é **ruído
ortográfico direto**: ensinaria grafias erradas para o Brasil. Serve como *fonte de
estrutura curricular*, **não** como fonte de texto.

---

## 2. Currículo consolidado de BIOLOGIA (básico → avançado)

> ⚠️ **Procedência:** como nenhum dos livros de biologia geral era extraível, esta árvore
> **não foi extraída dos PDFs**. Ela é reconstruída a partir de (a) a organização pública
> e conhecida da série Amabis & Martho em 3 volumes, (b) a sequência canônica do ensino
> médio brasileiro / BNCC, e (c) os pontos onde as fontes extraíveis (#4, #7, #9)
> efetivamente tocam biologia. Está marcado abaixo o que veio de onde.
> **Isto é uma hipótese de currículo, não um extrato de fonte.** Se o Bee for treinado
> nisso, a validação da sequência precisa vir de outro lugar (livro extraível ou OCR).

A série Amabis & Martho organiza-se em três eixos, e essa é a divisão que o ensino médio
brasileiro segue na prática:

- **Vol. 1 — Biologia das Células** → citologia, histologia, embriologia, origem da vida
- **Vol. 2 — Biologia dos Organismos** → taxonomia, botânica, zoologia, fisiologia
- **Vol. 3 — Biologia das Populações** → genética, evolução, ecologia
  *(único fragmento de texto recuperado do vol. 3 confirma o eixo: leis de Mendel, dominância)*

### 2.1 Fundamentos — o que é vida (ponto de entrada, sem pré-requisito)

1. Características dos seres vivos: organização celular, metabolismo, resposta a estímulos,
   crescimento, reprodução, hereditariedade, evolução
2. Níveis de organização: átomo → molécula → organela → célula → tecido → órgão → sistema →
   organismo → população → comunidade → ecossistema → biosfera
   *(esta escada é o gancho pedagógico central: cada nível é um capítulo depois)*
3. Método científico aplicado à biologia: observação, hipótese, experimento controlado,
   teoria. Pasteur e a queda da geração espontânea
4. Origem da vida: hipótese heterotrófica × autotrófica, experimento de Miller-Urey,
   coacervados, mundo do RNA
5. Vírus: por que ficam fora da definição de "ser vivo"

**Pré-requisitos assumidos:** noção de átomo e molécula (química básica). Nenhum cálculo.

### 2.2 Bioquímica da célula (a ponte química→biologia)

1. Água: polaridade, ponte de hidrogênio, solvente universal, calor específico
   *(coberto em profundidade por #7 Devlin cap. 1 — em espanhol)*
2. Sais minerais: função estrutural e reguladora
3. Carboidratos: mono-, di-, polissacarídeos; energia e estrutura
4. Lipídios: triglicerídeos, fosfolipídios, esteroides; reserva, membrana, hormônio
5. Proteínas: aminoácidos, ligação peptídica, estruturas primária→quaternária,
   desnaturação; **enzimas** (sítio ativo, especificidade, efeito de temperatura e pH,
   cofatores, inibição)
6. Ácidos nucleicos: DNA e RNA — composição, estrutura, papel informacional
7. Vitaminas: hidro e lipossolúveis, avitaminoses

**Pré-requisito real:** química orgânica introdutória (grupos funcionais). Este é o ponto
onde biologia trava se a química não veio antes.

### 2.3 Citologia — a célula

1. Teoria celular; histórico (Hooke, Schleiden, Schwann, Virchow)
2. Microscopia: óptica × eletrônica, limite de resolução, ordens de grandeza
3. Procarionte × eucarionte; célula animal × vegetal
   *(comparação direta em #7 Devlin cap. 1)*
4. Membrana plasmática: modelo do mosaico fluido; **transporte** — difusão simples,
   facilitada, osmose, transporte ativo, bomba de sódio-potássio; endocitose/exocitose
5. Parede celular, glicocálice, especializações de membrana
6. Citoplasma e organelas, cada uma com função:
   ribossomo · retículo endoplasmático rugoso e liso · complexo golgiense ·
   lisossomo · peroxissomo · vacúolo · mitocôndria · cloroplasto · centríolo ·
   citoesqueleto (microtúbulos, microfilamentos)
7. Núcleo: envoltório, nucléolo, cromatina, cromossomos (morfologia, cariótipo)
8. **Metabolismo energético** — a espinha dorsal:
   - Respiração celular: glicólise → ciclo de Krebs → cadeia respiratória e
     fosforilação oxidativa; balanço de ATP
   - Fermentação láctica e alcoólica
   - Fotossíntese: fase clara (fotofosforilação) e fase escura (ciclo de Calvin);
     fatores limitantes
   - Quimiossíntese
9. Síntese proteica: **dogma central** — replicação, transcrição, código genético,
   tradução; splicing
10. Divisão celular: ciclo celular (G1, S, G2, M); **mitose** (fases, função);
    **meiose** (fases, redução cromossômica, crossing-over, variabilidade);
    gametogênese (espermatogênese, ovulogênese)

**Este é o bloco de maior densidade textual de toda a biologia** — ver §5.

### 2.4 Histologia (tecidos animais)

Epitelial (revestimento e glandular) · Conjuntivo (propriamente dito, adiposo,
cartilaginoso, ósseo, sanguíneo) · Muscular (estriado esquelético, cardíaco, liso) ·
Nervoso (neurônio, glia, impulso, sinapse)

⚠️ Histologia é **fortemente dependente de imagem** (reconhecer tecido em corte). Ver §5.

### 2.5 Embriologia

Fecundação · Segmentação (clivagem) · Blástula · Gástrula (folhetos embrionários:
ecto/meso/endoderma) · Nêurula · Organogênese (o que cada folheto origina) ·
Anexos embrionários (âmnio, cório, alantoide, saco vitelínico, placenta) ·
Tipos de ovo e clivagem

### 2.6 Diversidade e classificação

1. Sistemática: espécie, nomenclatura binomial de Lineu, hierarquia taxonômica
   (domínio→reino→filo→classe→ordem→família→gênero→espécie)
2. Sistemas de reinos; domínios (Bacteria, Archaea, Eukarya)
3. **Vírus** — estrutura, ciclos lítico e lisogênico, viroses humanas
4. **Reino Monera** (bactérias e cianobactérias) — estrutura, reprodução, recombinação
   (transformação, transdução, conjugação), importância ecológica e médica, bacterioses
5. **Reino Protista** — protozoários (rizópodes, flagelados, ciliados, esporozoários) e
   protozooses (malária, doença de Chagas, amebíase, leishmaniose, toxoplasmose); algas
6. **Reino Fungi** — estrutura, nutrição, reprodução, micoses, papel decompositor, liquens
7. **Reino Plantae**: briófitas → pteridófitas → gimnospermas → angiospermas
   *(a sequência é evolutiva: conquista do ambiente terrestre — vaso condutor, semente, flor)*
8. **Reino Animalia**: poríferos → cnidários → platelmintos → nematelmintos → anelídeos →
   moluscos → artrópodes → equinodermos → cordados (protocordados, peixes, anfíbios,
   répteis, aves, mamíferos)
   *(critérios que estruturam a sequência: simetria, folhetos, celoma, segmentação,
   sistema digestório completo, respiração, circulação, excreção, sistema nervoso)*
9. Verminoses humanas (esquistossomose, teníase/cisticercose, ascaridíase, ancilostomíase,
   filariose) — ciclo, transmissão, profilaxia

### 2.7 Botânica (morfologia e fisiologia vegetal)

Tecidos vegetais (meristemas, epiderme, parênquima, colênquima, esclerênquima, xilema,
floema) · Raiz, caule, folha — morfologia e função · Condução de seiva bruta e elaborada
(teoria da coesão-tensão) · Transpiração e estômatos · Nutrição mineral ·
Hormônios vegetais (auxina, giberelina, citocinina, etileno, ácido abscísico) ·
Fotoperiodismo, tropismos · Flor, fruto, semente; polinização, dispersão, germinação

### 2.8 Fisiologia comparada dos animais

Digestão · Respiração (cutânea, traqueal, branquial, pulmonar) · Circulação (aberta,
fechada; número de cavidades cardíacas) · Excreção (produtos nitrogenados: amônia, ureia,
ácido úrico — relação com disponibilidade de água) · Osmorregulação ·
Sistema nervoso e endócrino · Reprodução e desenvolvimento

**Ponte:** daqui o currículo do ensino médio passa para fisiologia humana, que é onde as
fontes extraíveis #4 e #5 entram — ver §3.

### 2.9 Genética

1. Conceitos: gene, alelo, locus, genótipo, fenótipo, homo/heterozigoto, dominante,
   recessivo
2. **1ª Lei de Mendel** (segregação dos fatores): monoibridismo, quadro de Punnett,
   retrocruzamento *(confirmado como conteúdo do vol. 3 de Amabis & Martho)*
3. Probabilidade aplicada à genética: regra do "e"/"ou", binômio
4. Variações da dominância: dominância incompleta, codominância, alelos letais
5. Polialelia (grupos sanguíneos ABO, sistema Rh, pelagem em coelhos)
6. **2ª Lei de Mendel** (segregação independente): diibridismo, poliibridismo
7. Interação gênica: epistasia, herança quantitativa (poligênica)
8. **Ligação gênica (linkage)** e permutação; mapas de recombinação; distância em centimorgans
9. Determinação do sexo; herança ligada ao X (daltonismo, hemofilia), restrita ao Y,
   influenciada pelo sexo
10. **Heredogramas** — leitura e dedução de genótipo
11. Cariótipo humano e aberrações: numéricas (Down, Turner, Klinefelter) e estruturais
12. Genética molecular: mutação (gênica, cromossômica), agentes mutagênicos, câncer
13. Biotecnologia: DNA recombinante, PCR, transgênicos, clonagem, terapia gênica,
    projeto genoma, células-tronco, bioética

### 2.10 Evolução

1. Evidências: fósseis, anatomia comparada (homologia × analogia, órgãos vestigiais),
   embriologia comparada, bioquímica comparada
2. Ideias pré-darwinianas: fixismo, Lamarck (uso e desuso, herança de caracteres adquiridos)
3. **Darwin e a seleção natural**; a viagem do Beagle; o argumento em passos
4. Teoria sintética (neodarwinismo): mutação + recombinação → variabilidade;
   seleção natural + deriva genética + migração → mudança de frequência alélica
5. Genética de populações: **equilíbrio de Hardy-Weinberg**, cálculo de frequências alélicas
6. Especiação: isolamento geográfico e reprodutivo (pré e pós-zigótico), especiação
   alopátrica e simpátrica; irradiação adaptativa; convergência
7. Evolução humana: linhagem dos hominíneos, bipedalismo, encefalização
8. Filogenia e cladística; árvores filogenéticas

### 2.11 Ecologia

1. Conceitos: hábitat, nicho, população, comunidade, ecossistema, biosfera, biótopo
2. **Cadeias e teias alimentares**; níveis tróficos (produtor, consumidor, decompositor)
3. Pirâmides ecológicas (número, biomassa, energia); fluxo de energia e produtividade
   (produtividade primária bruta e líquida); regra dos 10%
4. **Ciclos biogeoquímicos**: água, carbono, oxigênio, nitrogênio, fósforo
5. Sucessão ecológica: primária, secundária, comunidade pioneira → clímax
6. Dinâmica de populações: curvas de crescimento, potencial biótico, resistência ambiental,
   capacidade de suporte, densidade
7. **Relações ecológicas**: intraespecíficas e interespecíficas; harmônicas
   (colônia, sociedade, mutualismo, protocooperação, comensalismo, inquilinismo) e
   desarmônicas (competição, predatismo, parasitismo, amensalismo, herbivoria, canibalismo)
8. Biomas brasileiros (Amazônia, Cerrado, Caatinga, Mata Atlântica, Pampa, Pantanal) e
   mundiais; fitofisionomia e clima
9. Impactos ambientais: efeito estufa e mudança climática, camada de ozônio, chuva ácida,
   eutrofização, poluição (ar, água, solo), bioacumulação e magnificação trófica,
   desmatamento, espécies invasoras, perda de biodiversidade, extinção
10. Conservação, unidades de conservação, desenvolvimento sustentável, legislação ambiental

---

## 3. Currículo de ANATOMIA / FISIOLOGIA e BIOQUÍMICA (nível superior)

> Este bloco **foi extraído** dos sumários reais dos PDFs #4, #5, #7 e #9.
> É a parte confiável deste documento.

### 3.1 Anatomia + Fisiologia integradas — modelo IESDE (#4, PT-BR, 372 p.)

Sequência do livro (10 capítulos). É o percurso mais adequado a um curso introdutório e
o mais próximo do que o Bee poderia consumir em PT-BR:

| Cap. | Tema | Subtópicos |
|---|---|---|
| 1 | Introdução à anatomia e **homeostase** | história da anatomia; morfologia × histologia × embriologia; **terminologia anatômica** (nômina, abandono dos epônimos); posição anatômica; planos e cortes; organização em sistemas; homeostase; variação anatômica × anomalia |
| 2 | Sistema **esquelético** | funções do esqueleto; classificação dos ossos; componentes anatômicos; acidentes ósseos; articulações |
| 3 | Sistema **muscular** | tipos de músculo; revestimentos (endomísio, perimísio, epimísio, fáscia); tendão e aponeurose; contração; principais músculos |
| 4 | Sistema **nervoso** | tecido nervoso; **potencial de ação e transmissão sináptica**; divisão anatômica e funcional (SNC/SNP, somático/autônomo) |
| 5 | Sistema **cardiovascular** | anatomia do coração e vasos; **eletrofisiologia cardíaca**; hemodinâmica; coração como bomba; controle autonômico |
| 6 | Sistema **respiratório** | vias aéreas; mecânica respiratória; trocas e transporte de gases; controle da respiração |
| 7 | Sistema **urinário** | anatomia; **néfron**; filtração/reabsorção/secreção; regulação da osmolaridade plasmática |
| 8 | Sistema **endócrino** | visão geral; hipotálamo-hipófise; pineal, timo, pâncreas |
| 9 | Sistemas **genitais** feminino e masculino | anatomia de cada um |
| 10 | Sistema **digestório** | anatomia; fisiologia da digestão |
| — | **Gabarito** | respostas comentadas de todas as atividades |

**Escolha pedagógica central da autora, e é a boa:** ela **funde anatomia e fisiologia no
mesmo capítulo** ("anatomofisiologia"), em vez de dar anatomia inteira e depois fisiologia
inteira. O argumento explícito é que separar produz aprendizado fragmentado. Cada sistema é
apresentado como *estrutura → função*, na mesma unidade.

Ordem dos sistemas: começa por **suporte e movimento** (esquelético → muscular), que é o mais
concreto e visível; depois **controle** (nervoso); depois os sistemas de **manutenção**
(cardio → respiratório → urinário → endócrino); e fecha com **reprodução** e **digestório**.

### 3.2 Anatomia sistemática — modelo FMUL (#5, PT-PT, ~804 p.)

Estrutura diferente e mais ambiciosa: agrupa por **setor funcional**, não por sistema isolado.

```
I.   A Anatomia e a História
II.  Introdução à Anatomia  (posição, planos, cavidades, quadrantes/setores abdominais)

A. SUPORTE E MOVIMENTO
   1. Pele e anexos
   2. Sistema locomotor
      2.1 Cabeça e pescoço — osteologia do crânio · osteologia da face · osso hioide ·
          artrologia · miologia do crânio e face · miologia do pescoço
      2.2 Tronco (tórax, abdômen, pelve) — osteologia da coluna · artrologia da coluna ·
          biomecânica da coluna · miologia da coluna · osteologia/artrologia/miologia do
          tórax · diafragma · osteologia/artrologia do abdômen e pelve · miologia do
          abdômen · períneo
      2.3 Membros superior e inferior — osteologia, artrologia e miologia de cada

B. MANUTENÇÃO
   3. Sistema circulatório — coração e pericárdio · aorta · artérias e veias por região
      (cabeça/pescoço, tórax, abdômen, membros) · sistema porta-hepático e anastomoses
      porto-cava · linfáticos · anatomia clínica e imagiológica
   4. Sistema respiratório — vias aéreas superiores · vias aéreas inferiores, pulmões, pleuras
   5. Sistema digestivo — superior · inferior · peritônio
   6. Sistema urinário — rins, ureteres, bexiga, uretra · desenvolvimento embriológico

C. REPRODUÇÃO
   7. Sistema genital masculino
   8. Sistema genital feminino e mama

D. CONTROLO E INTEGRAÇÃO
   9. Sistema endócrino
  10. Sistema nervoso
      10.1 SNC — medula espinhal · tronco cerebral · cerebelo · cérebro (configuração
           exterior e córtex; substância branca; núcleos cinzentos centrais; hipotálamo,
           epitálamo e órgãos neuroendócrinos; sistema límbico) · ventrículos e líquor ·
           meninges · vias da sensibilidade · vias da motricidade · vascularização encefálica
      10.2 SNP — nervos cranianos · nervos raquidianos e plexos
      10.3 Sistema nervoso autônomo
      10.4 Sistemas neurossensoriais — visual · auditivo e vestibular · olfativo e gustativo

E. ANATOMIA DAS REGIÕES
  11–17. Cabeça · Pescoço · Tórax · Abdômen · Períneo · Membro superior · Membro inferior

F. ANATOMIA DE SUPERFÍCIE
```

O padrão **anatomia sistemática (por sistema) → anatomia topográfica (por região) →
anatomia de superfície** é a estrutura clássica dos cursos de medicina: primeiro você
aprende cada sistema inteiro, depois reaprende tudo cortado por região (o que o cirurgião
encontra ao abrir), depois projeta na superfície do corpo vivo.

Dentro do locomotor, a ordem interna é sempre a mesma tríade:
**osteologia → artrologia → miologia** (osso → articulação → músculo). É o esqueleto
do esqueleto, e é ordem de dependência: não dá para descrever a inserção de um músculo
sem ter nomeado os acidentes ósseos antes.

### 3.3 Bioquímica — modelo Devlin (#7, espanhol, 1242 p., 27 capítulos)

Cinco partes, e a lógica é **estrutura → informação → função → metabolismo → fisiologia**:

```
PARTE I — ESTRUTURA DAS MACROMOLÉCULAS
   1. Estrutura celular eucariótica   (inclui: água, eletrólitos, pH, tampões,
                                       equação de Henderson-Hasselbalch, organelas)
   2. DNA e RNA: composição e estrutura
   3. Proteínas I: composição e estrutura

PARTE II — TRANSMISSÃO DA INFORMAÇÃO
   4. Replicação, recombinação e reparo do DNA
   5. RNA: transcrição e maturação
   6. Síntese de proteínas: tradução e modificações pós-tradução
   7. DNA recombinante e biotecnologia
   8. Regulação da expressão gênica

PARTE III — FUNÇÕES DAS PROTEÍNAS
   9. Proteínas II: relação estrutura–função em famílias de proteínas
  10. Enzimas: classificação, cinética e controle
  11. Citocromos P450 e óxido nítrico sintases
  12. Membranas biológicas: estrutura e transporte

PARTE IV — VIAS METABÓLICAS E SEU CONTROLE
  13. Bioenergética e metabolismo oxidativo
  14. Metabolismo glicídico I: vias principais e controle
  15. Metabolismo glicídico II: vias especiais e glicoconjugados
  16. Metabolismo lipídico I: utilização e armazenamento de energia
  17. Metabolismo lipídico II: vias de lipídios especiais
  18. Metabolismo dos aminoácidos
  19. Metabolismo dos nucleotídeos purínicos e pirimidínicos
  20. Inter-relações metabólicas

PARTE V — PROCESSOS FISIOLÓGICOS
  21. Bioquímica dos hormônios I: hormônios polipeptídicos
  22. Bioquímica dos hormônios II: hormônios esteroides
  23. Biologia molecular da célula (inclui os 4 sistemas de transdução de sinal)
  24. Metabolismo do ferro e do heme
  25. Digestão e absorção dos constituintes nutricionais
  26–27. Princípios de nutrição humana
  Apêndice: revisão de química orgânica (referência rápida, não curso)
```

**Pré-requisito explícito:** química orgânica. O autor resolve isso colocando a revisão de
química orgânica **no apêndice**, não no começo — decisão deliberada, declarada no prefácio:
serve de consulta rápida enquanto se lê, não de capítulo obrigatório.

### 3.4 Patologia Geral (#9, PT-BR, ~250 p., 8 unidades)

A ponte entre biologia básica e clínica. É o material **mais bem calibrado dos quatro**
para o nível "estudante que já sabe biologia celular".

```
Unidade 1 — Adaptações, lesão celular e morte celular
   introdução à patologia (etiologia · patogenia · fisiopatologia) ·
   respostas ao estresse e a estímulos nocivos · adaptações do crescimento
   (hipertrofia, hiperplasia, atrofia, metaplasia) · etiopatogênese da lesão celular ·
   necrose (coagulação, liquefativa, gordurosa, caseosa, fibrinoide) · apoptose (p53, caspases)
Unidade 2 — Inflamação e reparo
   conceitos · inflamação aguda e crônica · classificação morfológica ·
   tecido conjuntivo, reparo, regeneração e cicatrização
Unidade 3 — Distúrbios circulatórios
   princípios da circulação · hiperemia/congestão · hemorragia · choque · trombose ·
   embolia · isquemia · infarto · edema
Unidade 4 — Neoplasia
   benigna × maligna · epidemiologia do câncer · características genéticas ·
   agentes carcinogênicos
Unidade 5 — Doenças do sistema imune e doenças genéticas
   noções de imunidade · imunopatologia (hipersensibilidade, autoimunidade) · doenças genéticas
Unidade 6 — Doenças ambientais e nutricionais
   lesões por agentes químicos e físicos · doenças de caráter nutricional
Unidade 7 — Doenças infecciosas
   patogenia · agentes infecciosos · transmissão e disseminação · mecanismos de dano
Unidade 8 — Métodos de estudo em patologia
   estudos tradicionais · citopatologia · técnicas especiais · citometria · citogenética ·
   biologia molecular
```

**Encadeamento lógico da patologia, e ele é rígido:**
lesão celular → resposta do tecido (inflamação) → reparo → o que dá errado na circulação →
o que dá errado no crescimento (neoplasia) → o que dá errado na defesa (imunopatologia) →
causas externas (ambiental, nutricional, infecciosa) → como se investiga.
Cada unidade depende da anterior. Não é uma lista, é uma cadeia.

---

## 4. Método pedagógico observado (descrito com minhas palavras)

### #4 — Giulianna Borges / IESDE (PT-BR): *função primeiro, estrutura a serviço da função*

O ciclo de cada capítulo é fixo e explícito:

```
Objetivos de aprendizagem (3-4 bullets, verbos: compreender/conhecer/analisar/conceituar)
   ↓
Abertura com pergunta ou cena  ("você consegue descrever as estruturas envolvidas
                                 nesse movimento?")  — ativa o capítulo anterior
   ↓
Exposição: estrutura ⇄ função, alternadas, nunca separadas
   ↓
Notas de rodapé definindo cada termo técnico na primeira ocorrência
   (fístula, inervação, vascularizado, interdisciplinaridade, epônimo)
   ↓
Considerações finais  ("agora você já é capaz de…")  — fecha contra os objetivos
   ↓
Ampliando seus conhecimentos  (2 leituras externas, com o que cada uma acrescenta)
   ↓
Atividades  (2-3 questões, quase sempre situações de caso)
   ↓
Referências
   ↓
[Gabarito comentado no fim do livro]
```

Três marcas fortes:

1. **Encadeamento explícito entre capítulos.** O capítulo abre retomando o anterior
   ("no capítulo anterior você conheceu os termos de movimento… agora consegue descrever
   as estruturas que os realizam?"). Isso constrói dependência declarada, não implícita.
2. **Justificação da nomenclatura em vez de memorização.** Ela ensina *por que* "tuba
   uterina" substituiu "trompa de Falópio": o nome novo descreve forma (tuba) e localização
   (uterina), então é dedutível; o epônimo é arbitrário e obriga a decorar. O método é:
   **um termo que se explica é um termo que não precisa ser decorado.**
3. **As atividades não pedem recall — pedem transferência.** São mini-casos:
   "um educador físico recebe um exame radiológico de um aluno em posição anatômica…",
   "um paciente faz hemodiálise por fístula no punho esquerdo; se a nova fístula for na face
   anterior do cotovelo, qual sua posição relativa?". A pergunta é sempre *aplique o termo a
   uma situação*, nunca *repita a definição*.

### #5 — FMUL (PT-PT): *manual sintético, ilustrado, ancorado na clínica*

Programa declarado no prefácio: um manual deve ser **sintético** (sem detalhe descritivo
excessivo), **profusamente ilustrado**, e sempre ligar a descrição anatômica a **função,
imagiologia e clínica**. Cada capítulo tem no fim **perguntas-tipo** e bibliografia para
aprofundamento. Cada subcapítulo inclui noções de **anatomia do desenvolvimento** (por que
a estrutura ficou assim) e de **anatomia clínica** (o que quebra quando ela falha).

Duas escolhas interessantes:

- **Abre com história da anatomia**, não com osso. O capítulo 1 percorre Hipócrates →
  Galeno → Avicena → Mondino → Vesálio → Harvey → Malpighi → nômina de Basileia (1895) →
  imagiologia do séc. XX. A tese implícita: anatomia é um conhecimento **construído e
  disputado**, não uma lista revelada. O aluno entende por que os nomes são como são.
- **Escrita em coautoria maciça** (dezenas de autores, um por região/sistema, cada um
  clínico da área). Isso dá autoridade mas produz variação de estilo entre capítulos —
  o próprio Devlin admite o mesmo trade-off no seu prefácio.

### #7 — Devlin (espanhol): *bioquímica ancorada em doença*

- Cada capítulo carrega caixas de **"Aplicaciones clínicas"** — o processo bioquímico
  normal é apresentado, e ao lado se mostra a doença em que ele falha. O autor é explícito:
  não é uma revisão de doenças, são **exemplos escolhidos onde a ramificação bioquímica está
  bem estabelecida**. E o texto principal é autossuficiente: pular as caixas não quebra a
  compreensão.
- **Repetição deliberada.** Alguns temas (ex.: proteínas de ligação ao DNA) aparecem em dois
  capítulos, por autores diferentes, de perspectivas diferentes. O prefácio defende isso
  explicitamente: a redundância facilita a aprendizagem. É o oposto da obsessão por
  não-repetição de um sumário enxuto.
- **Cada capítulo fecha com bateria de questões + respostas comentadas**, em quatro formatos:
  (a) múltipla escolha conceitual; (b) itens de correspondência (5 organelas, 3 funções);
  (c) **vinhetas clínicas** — um parágrafo de caso (doença de Luft, gota) seguido de 2
  questões; (d) **problemas numéricos** (calcular pK a partir do grau de neutralização;
  calcular [HCO₃⁻] pela Henderson-Hasselbalch a partir de pH e [CO₂]).
  As respostas não dizem só "letra C" — explicam por que cada distrator está errado.
  **É o melhor gerador de exercício textual de todo o acervo.**
- Ordem de temas declaradamente **flexível**: o autor afirma que o livro foi escrito para
  ser lido em qualquer sequência que o professor escolher. Isso significa capítulos
  razoavelmente autocontidos — bom sinal para fatiar em amostras de treino.

### #9 — Patologia Geral / Ânima (PT-BR): *material de EaD, transcrição de aula + texto*

Formato híbrido e revelador de como se produz material EaD no Brasil:

- Abre com a **fala transcrita da professora** ("olá, eu sou a professora Isadora…"),
  em registro oral, apresentando o problema-motivador. Depois vem o texto formal, com
  citação bibliográfica pesada (Kumar/Abbas/Aster, Brasileiro-Filho, Reisner).
- **Situação-problema como fio condutor da disciplina inteira:** logo na abertura ela põe
  um caso (homem de 63 anos, rouquidão, suspeita de câncer de laringe) e lista as perguntas
  que só serão respondíveis ao fim das 8 unidades. Todo o curso é a resposta a esse caso.
- Elementos recorrentes: **QUESTÃO n** intercalada no meio do texto (não só no fim),
  caixas de **"Dicas"** (curiosidades históricas — primeira doença registrada, peste negra),
  caixas de **"Notícia"** (matéria de divulgação científica com link).
- **Gabarito ao fim de cada unidade**, não do livro.
- Mistura questão **dissertativa** ("conceitue etiologia, patogenia e fisiopatologia e
  indique sua relação com a patologia") com **múltipla escolha** de 5 alternativas.

**Padrão comum aos quatro:** todos declaram objetivos, todos fecham com exercício, todos
dão gabarito comentado, e três dos quatro ancoram o conteúdo em **caso clínico**.
Se o Bee vai receber material didático original, esse é o molde a copiar — não o conteúdo,
mas a **forma**: objetivo → exposição → caso → pergunta → resposta explicada.

---

## 5. Conceitos que rendem exercício TEXTUAL (e os que não rendem)

Critério: o Bee lê **só texto puro**, sem imagem, sem tabela renderizada, sem diagrama.
Um conceito "rende" se um par pergunta/resposta correto e verificável pode ser escrito
inteiramente em prosa, sem nenhuma referência a "veja a figura".

### ✅ RENDE MUITO — densidade textual alta

| Conceito | Por que rende | Formato de exercício |
|---|---|---|
| **Genética mendeliana** | É puro cálculo simbólico e probabilidade. Genótipo, cruzamento e proporção são strings e frações. | "Cruzando Aa × Aa, qual a proporção fenotípica esperada?" · "Qual a probabilidade de dois heterozigotos para anemia falciforme terem uma criança afetada?" · heredograma **descrito em prosa** ("o casal I-1 e I-2 é normal; o filho II-3 é afetado; deduza o padrão de herança") |
| **Hardy-Weinberg** | Equação fechada, entrada e saída numéricas. | "Numa população, 16% expressam o fenótipo recessivo. Calcule p, q e a frequência de heterozigotos." |
| **Vias metabólicas** (glicólise, Krebs, cadeia respiratória, ciclo de Calvin, β-oxidação, ureia) | Sequência ordenada de substrato→enzima→produto. É uma cadeia nomeada, perfeitamente linearizável em texto. | "Qual enzima catalisa a conversão de X em Y?" · "Quantos ATP líquidos a glicólise produz?" · "Qual o destino do piruvato em anaerobiose?" · "Se a enzima Z for inibida, qual metabólito se acumula?" |
| **Cadeias causais fisiológicas** | Fisiologia é essencialmente *se A, então B, então C*. | "A pressão arterial cai. Descreva a sequência: barorreceptor → centro vasomotor → simpático → frequência cardíaca e vasoconstrição." · "O que acontece com a diurese se o ADH aumentar?" |
| **Patologia: etiologia → patogenia → fisiopatologia** | O livro #9 já organiza o conteúdo exatamente nessa tripla, que é uma cadeia causal textual. | "Um paciente sofre isquemia miocárdica prolongada. Que tipo de necrose se espera e por quê?" · "Diferencie necrose de apoptose quanto a inflamação, integridade de membrana e mecanismo." |
| **Química da bioquímica** (pH, tampão, Henderson-Hasselbalch, cinética de Michaelis-Menten, pK) | Numérico e fechado. Devlin já traz esse tipo pronto (em espanhol). | "pH = 7,45 e [CO₂] = 1,25 mM; calcule [HCO₃⁻] com pK = 6,1." |
| **Ecologia trófica e ciclos biogeoquímicos** | Grafos simples, verbalizáveis. | "Numa cadeia capim→gafanhoto→sapo→cobra, o que acontece à população de gafanhotos se as cobras forem removidas?" · "Descreva o caminho do nitrogênio da atmosfera até a proteína vegetal." |
| **Relações ecológicas** | Taxonomia binária limpa (quem ganha, quem perde). | "Classifique a relação entre cupim e protozoário do seu intestino, e justifique." |
| **Evolução — raciocínio de seleção natural** | Argumento em premissas, é literalmente prosa. | "Explique, em termos darwinistas, o aumento da resistência bacteriana a antibióticos. Onde o raciocínio lamarckista erraria?" |
| **Classificação e taxonomia** | Hierarquia é uma árvore textual. | "Ordene do mais inclusivo ao menos inclusivo: família, domínio, gênero, classe." · "Por que fungos não são plantas?" |
| **Ciclos de doenças parasitárias** | Sequência de hospedeiros, vetor, forma infectante, profilaxia. É narrativa. | "Descreva o ciclo do *Schistosoma mansoni*: hospedeiro intermediário, forma infectante, porta de entrada, profilaxia." |
| **Dogma central / síntese proteica** | Código genético é literalmente tabela de string→string. | "Dada a fita molde 3'-TAC GGA TTT-5', escreva o mRNA e a sequência de aminoácidos." · "Que efeito tem uma mutação de ponto no terceiro nucleotídeo de um códon? Por quê?" |
| **Terminologia anatômica** (a lógica, não o mapa) | Os termos são **composicionais** — "tuba uterina" = forma + localização. Isso é morfologia lexical, exatamente o que um LLM pequeno consegue generalizar. | "O que os termos *supraespinal*, *infraespinal* e *interósseo* dizem sobre a localização das estruturas?" · "Por que a nômina prefere 'tuba uterina' a 'trompa de Falópio'?" |
| **Definições contrastivas** | Par de conceitos que se distinguem por 2-3 atributos. | mitose × meiose · procarionte × eucarionte · homologia × analogia · hipertrofia × hiperplasia · necrose × apoptose · artéria × veia (função, não trajeto) · gimnosperma × angiosperma |
| **Planos e posição anatômica** | Curiosamente rende: é um sistema de coordenadas com regras verbais. | "O cotovelo é proximal ou distal em relação ao punho?" · "Um corte sagital mediano e um paramediano mostram as mesmas estruturas? Justifique." *(esta é literalmente uma atividade do livro #4)* |

### ⚠️ RENDE PARCIALMENTE — só se reescrito com cuidado

| Conceito | Ressalva |
|---|---|
| **Organelas** | A **função** rende ("qual organela oxida ácidos graxos de cadeia muito longa?"). A **morfologia** ("descreva as cristas mitocondriais") vira texto oco sem a imagem. Fique na função. |
| **Estrutura de proteínas** | Níveis 1º e 2º rendem conceitualmente (ligação peptídica, ponte de hidrogênio, hélice α × folha β). Estrutura 3D específica de uma proteína **não rende**. |
| **Divisão celular** | O *propósito* e o *resultado* de cada fase rendem. A *aparência* de cada fase (o que a metáfase parece ao microscópio) não. |
| **Sistema nervoso central** | Vias e funções rendem ("qual via conduz dor e temperatura, e onde cruza?"). Localização de núcleos cinzentos e trajetos não. |
| **Botânica estrutural** | Função dos tecidos rende (xilema conduz seiva bruta por coesão-tensão). Identificação de tecidos em corte, não. |

### ❌ NÃO RENDE — descarte

| Conceito | Motivo |
|---|---|
| **Osteologia descritiva** (acidentes ósseos do crânio, da face, dos membros) | É uma lista de centenas de nomes ancorada num objeto tridimensional. Sem a figura, o texto é uma lista de rótulos sem referente. O Bee decoraria strings sem semântica — pior que não aprender. |
| **Miologia detalhada** (origem, inserção, inervação de cada músculo) | Mesmo problema, com dependência espacial ainda maior. Tabela disfarçada de texto. |
| **Trajetos de artérias, veias e nervos por região** | É cartografia. "A artéria X emite os ramos Y e Z ao passar posteriormente a W" é ininteligível sem o mapa. |
| **Anatomia topográfica e anatomia de superfície** (blocos E e F do FMUL, ~100 pág.) | Existem *para* ser lidas com figura. Sem ela, valor ≈ 0. |
| **Histologia** | O objetivo do aprendizado é reconhecimento visual de padrão. Textualizar isso é fingir. |
| **Embriologia morfológica** (formas de clivagem, dobramentos, tipos de ovo) | Idem — transformação de forma no espaço e no tempo. |
| **Imagiologia** (o que aparece numa TC/RM) | Puramente visual. |
| **Estruturas químicas desenhadas** | Todo o material que no PDF é fórmula estrutural vira lixo (`CH3OCHOHOCOOH` — sim, é assim que sai do `pdftotext`). Nomes e reações rendem; desenhos não. |

**Regra prática para gerar material do Bee:**
pergunte-se se a resposta correta contém um **substantivo próprio anatômico cuja única
definição é sua posição num desenho**. Se sim, descarte. Se a resposta é uma **cadeia
causal, um cálculo, uma classificação ou um contraste de atributos**, sirva.

Pela contagem por área: **genética + evolução + ecologia + metabolismo + fisiologia
funcional + patologia** concentram praticamente todo o valor textual da biologia.
**Anatomia descritiva, histologia e embriologia** — que somam ~1.500 das ~2.100 páginas
extraíveis deste acervo — concentram praticamente todo o desperdício.

---

## 6. Veredito honesto

O acervo de biologia falhou no que mais importava e sobrou no que menos importa. Dos nove
PDFs, cinco são escaneados sem camada de texto — e entre eles estão **exatamente** as duas
fontes de biologia geral em PT-BR (Amabis & Martho vol. 1 e 3) e a de biologia celular
(Cooper), ou seja, todo o material de citologia, genética, evolução, ecologia, botânica e
zoologia que este estudo deveria mapear. O que restou extraível são quatro livros de nível
superior: um de bioquímica em **espanhol** (Devlin, o melhor gerador de exercícios do lote,
mas idioma errado), um de anatomia em **português europeu com ortografia pré-Acordo** (FMUL
— usá-lo como texto ensinaria grafias erradas ao Bee), e apenas dois em PT-BR
(anatomofisiologia do IESDE, 372 p.; patologia geral da Ânima, ~250 p.) — cerca de 620
páginas úteis, das quais boa parte é anatomia descritiva, que é justamente o que **não**
rende exercício textual. Então: como fonte de **conteúdo**, o acervo vale pouco, talvez
150–250 páginas de material realmente aproveitável (patologia inteira, a fisiologia dos
capítulos 4–8 do IESDE, e as vinhetas clínicas do Devlin traduzidas). Como fonte de
**forma**, porém, vale bastante, e esse é o ganho real: os quatro livros convergem num
mesmo molde pedagógico — objetivos declarados → exposição encadeada ao capítulo anterior →
caso-problema → questão de transferência (não de recall) → gabarito comentado que explica
por que cada distrator está errado — e esse molde é exatamente o que se deve replicar ao
escrever material original em PT-BR para o Bee. Recomendação concreta: **(a)** usar §2 como
o índice-alvo do currículo de biologia a ser escrito do zero, tratando-o como hipótese a
validar, não como extrato; **(b)** rodar OCR (Tesseract, `-l por`/`-l spa`) sobre Amabis
vol. 1 e 3 e sobre o Cooper — ~1.800 páginas que, recuperadas, mudariam o quadro por
completo e são o único investimento com retorno alto aqui; **(c)** priorizar geração de
exercício em genética, metabolismo, fisiologia funcional, ecologia e patologia, e
**descartar anatomia descritiva e histologia sem hesitação** — são o grosso do acervo e
quase todo o desperdício.
