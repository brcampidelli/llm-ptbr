# 07 — Ciências atuais (2026): o que é fato, o que é fronteira, e o que o Bee pode aprender

> **Data da pesquisa:** 2026-08-04
> **Método:** busca web + leitura de fontes primárias/institucionais. Cada afirmação tem fonte e data.
> **Escopo:** física, química, biologia, matemática + catálogo de fatos desatualizados de livro didático.
> **Alvo:** decidir o que entra no corpus do **Bee** (151M params, PT-BR, pré-treinado do zero).

---

## 0. Regras que segui (leia antes de usar este documento)

1. **Só entra o que a busca confirmou.** Onde não confirmei, está escrito `NÃO CONFIRMADO` — não preenchi lacuna com suposição.
2. **Separei CONSENSO de FRONTEIRA.** Fronteira não vai pro corpus de treino. Um resultado preliminar virado fato num corpus é alucinação permanente no modelo.
3. **Listicles não contam como fonte.** Vários "mitos de livro" famosos só apareceram em sites de conteúdo raso. Estão listados na seção 9 como **não verificados**, não no catálogo.

### ⚠️ Achado metodológico grave (leia isto)

Durante a pesquisa de matemática, três sites (`dev.to`, `aitoolly.com`, `earezki.com`) afirmavam, com aparência de reportagem:

> *"Em 2026, uma equipe liderada por um jovem matemático em Princeton provou a conjectura dos primos gêmeos sob a Hipótese de Riemann Generalizada."*

**Isso é falso.** A busca dedicada não encontrou nenhuma confirmação. A literatura de 2025–2026 (ex.: [arXiv:2511.14810](https://arxiv.org/abs/2511.14810)) continua tratando os primos gêmeos como **conjectura em aberto**, implicada por hipóteses ainda mais fortes (GEH-2). Os mesmos sites também afirmavam que a conjectura de Kepler "foi formalizada em Lean por uma equipe da CMU" — a formalização real (projeto Flyspeck, Hales) foi em HOL Light/Isabelle e concluída em 2014.

**Implicação direta pro Bee:** conteúdo científico gerado por IA e publicado em blogs já poluiu a web de forma indistinguível de reportagem real. **Corpus científico raspado da web aberta, sem filtro de domínio, envenena o modelo.** Prefira fontes institucionais (Nature, Science, NobelPrize.org, IUPAC, BIPM, IAU, NIST, LLNL, blogs de pesquisadores identificados como Terence Tao).

---

## 1. Física hoje

### Consenso (pode ser tratado como estabelecido)

| Fato | Detalhe | Fonte | Desde |
|---|---|---|---|
| **SI redefinido por constantes** | kg, ampere, kelvin e mol passaram a ser definidos por valores exatos de *h*, *e*, *k*<sub>B</sub> e *N*<sub>A</sub>. O quilograma é definido pela constante de Planck, *h* = 6,62607015×10⁻³⁴ J·s (exato). O cilindro-protótipo de Paris deixou de ser a definição. | [BIPM – SI Brochure 9ª ed.](https://www.bipm.org/documents/20126/41489673/SI-App2-kilogram.pdf), [NIST](https://www.nist.gov/si-redefinition/kilogram-mass-and-plancks-constant) | 20/05/2019 |
| **Massa do neutrino: limite direto** | KATRIN: *m*<sub>ν</sub> < 0,45 eV/c² (259 dias de dados). Melhor limite de laboratório já obtido. | [Science, 2025](https://www.science.org/doi/10.1126/science.adq9592); [US DOE](https://www.energy.gov/science/np/articles/katrin-narrows-down-range-neutrinos-mass) | 2025 |
| **JUNO: precisão recorde em oscilação de neutrinos** | Capa da *Nature* em 10/06/2026. Com apenas 59 dias de dados (26/08–02/11/2025), mediu sin²θ₁₂ = 0,3092 ± 0,0087 — precisão **1,6× melhor que todos os experimentos anteriores somados**. | [Nature s41586-026-10538-z](https://www.nature.com/articles/s41586-026-10538-z); [Academia Chinesa de Ciências](https://english.cas.cn/newsroom/cas-in-media/202606/t20260611_1161689.shtml) | 06/2026 |
| **Ondas gravitacionais viraram rotina** | GWTC-4.0 (ago/2025) adicionou 128 candidatos de O4a. GWTC-5.0 (mai/2026) levou o catálogo cumulativo a **390 eventos** com probabilidade astrofísica ≥ 0,5. | [LIGO Caltech](https://www.ligo.caltech.edu/news/ligo20260526); [arXiv:2508.18082](https://arxiv.org/abs/2508.18082) | 2015→2026 |
| **Correção de erro quântico abaixo do limiar** | Chip Willow (Google): primeiro processador em que qubits lógicos **melhoram exponencialmente** ao crescer o código. Código de superfície distância-7 com 101 qubits, supressão de erro Λ = 2,14 ± 0,02 por incremento de distância. | [Nature 638:920–926](https://www.nature.com/articles/s41586-024-08449-y) | pub. 09/12/2024 |
| **Nobel de Física 2024** | John Hopfield e Geoffrey Hinton — redes neurais artificiais. | [NobelPrize.org](https://www.nobelprize.org/prizes/physics/2024/summary/) | 2024 |
| **Nobel de Física 2025** | John Clarke, Michel Devoret e John Martinis — tunelamento quântico macroscópico e quantização de energia em circuito elétrico. | [NobelPrize.org](https://www.nobelprize.org/prizes/physics/2024/summary/) (série de prêmios) | 2025 |
| **Anomalia do múon (g−2) deixou de ser anomalia** | Fermilab publicou a medição final em jun/2025 (precisão de 127 ppb). A *Muon g-2 Theory Initiative* adotou a média consolidada de lattice QCD → previsão do Modelo Padrão 116.592.033(62)×10⁻¹¹, **compatível com o experimento**. Não há mais evidência de nova física ali. | [arXiv:2506.21219](https://arxiv.org/pdf/2506.21219); [APS Physics 18, 150](https://link.aps.org/doi/10.1103/Physics.18.150); [US DOE](https://www.energy.gov/science/articles/muon-g-2-announces-most-precise-measurement-magnetic-anomaly-muon) | 2025 |

> ⚠️ **Ressalva no g−2:** o fechamento depende de o lattice QCD estar correto. Persiste tensão entre lattice e quatro décadas de dados de colisores e⁺e⁻. É "consenso emergente", não caso encerrado.

### Fusão nuclear — consenso COM ressalva importante

- **Ignição alcançada** no NIF (Lawrence Livermore) pela primeira vez em dez/2022.
- **Recorde abr/2025:** 8,6 MJ de saída para 2,08 MJ entregues ao alvo → *target gain* 4,13.
- **jun/2026:** 11ª ignição, 7,9 MJ (±0,4), ganho ≈ 3,8.
- Fonte: [LLNL / NIF](https://lasers.llnl.gov/science/achieving-fusion-ignition).

> ⚠️ **O "ganho" é do alvo, não da tomada.** Mede energia de fusão ÷ energia do laser que chega ao alvo. **Não** inclui a energia da rede elétrica para operar os lasers (ordem de centenas de MJ). Dizer "a fusão já produz mais energia do que consome" é **falso** no sentido de engenharia. Este é um erro de divulgação frequente e o Bee não deve aprendê-lo.

### Fronteira — NÃO tratar como fato

| Tema | Estado real |
|---|---|
| **Energia escura dinâmica** | DESI (DR2 + supernovas + CMB) sugere que a energia escura **evolui** no tempo, em tensão de até ~3,9σ com ΛCDM. É **evidência sugestiva, não descoberta confirmada**. ΛCDM ainda é o melhor modelo global. ([arXiv:2606.21826](https://arxiv.org/html/2606.21826)) |
| **Tensão de Hubble** | Persiste, sem resolução. Não ensinar um valor único de H₀ como definitivo. |
| **Massa absoluta e ordenamento dos neutrinos** | Em aberto. Também em aberto: se o neutrino é sua própria antipartícula. DUNE, Hyper-K, JUNO devem responder. ([CERN Courier](https://cerncourier.com/ten-windows-on-the-future-of-particle-physics/)) |
| **Matéria escura (identidade da partícula)** | Nenhuma detecção direta confirmada. Continua não identificada. |

### Caso exemplar de resultado que MORREU (ótimo material didático interno)

**Supercondutividade à temperatura ambiente NÃO existe.**
- **LK-99** (jul/2023): anunciado como supercondutor a até 127 °C; viralizou com vídeo de levitação. Consenso rápido: **não é supercondutor** — a levitação era ferromagnetismo. ([Nature news](https://www.nature.com/articles/d41586-023-03398-4))
- **Ranga Dias / Ashkan Salamat:** a *Nature* **retratou** o artigo de supercondutor à temperatura ambiente em nov/2023, a pedido de 8 coautores — terceira retratação de alto perfil da dupla, em meio a acusações de fraude. ([Scientific American](https://www.scientificamerican.com/article/nature-retracts-controversial-room-temperature-superconductor-study/))

Qualquer PDF do acervo que afirme supercondutividade ambiente como fato deve ser descartado.

---

## 2. Química hoje

### Consenso

| Fato | Detalhe | Fonte | Desde |
|---|---|---|---|
| **A tabela periódica tem 118 elementos** | O mais pesado confirmado é o **oganessônio (Og, Z=118)**. Os quatro últimos nomes oficializados foram nihônio (Nh, 113), moscóvio (Mc, 115), tenessino (Ts, 117) e oganessônio (Og, 118). | [IUPAC / Chemistry World](https://www.chemistryworld.com/news/iupac-confirms-names-for-four-new-elements/2500071.article) | nomes em 2016 |
| **Elementos 119 e 120 NÃO existem** | Não há síntese confirmada. O Berkeley Lab produziu livermório (116) com feixe de **titânio-50** em 2024 — passo técnico que **habilita** a tentativa de fazer o 120; a tentativa estava prevista para começar por volta do fim de 2025. **Resultado: NÃO CONFIRMADO** até esta pesquisa. | [Berkeley Lab](https://newscenter.lbl.gov/2024/07/23/a-new-way-to-make-element-116-opens-the-door-to-heavier-atoms/) | 2024 |
| **Peso atômico de vários elementos é um INTERVALO, não um número** | A CIAAW/IUPAC revisou em 2021 os pesos de Ar, Hf, Ir, Pb e Yb — **argônio e chumbo passaram a ser expressos como intervalos**, porque a variação isotópica natural excede a incerteza de medição. Em 2023 revisou Gd, Lu e Zr. | [IUPAC/CIAAW](https://www.ciaaw.org/atomic-weights.htm) | 2021, 2023 |
| **Nobel de Química 2024** | David Baker (design computacional de proteínas) + Demis Hassabis e John Jumper (predição de estrutura — AlphaFold2). | [NobelPrize.org](https://www.nobelprize.org/prizes/chemistry/2024/press-release/) | 2024 |
| **Nobel de Química 2025** | Susumu Kitagawa, Richard Robson e Omar Yaghi — **redes metalorgânicas (MOFs)**: materiais porosos cristalinos que captam água do ar do deserto, capturam CO₂, armazenam gases tóxicos. | [NobelPrize.org](https://www.nobelprize.org/prizes/chemistry/2025/summary/) | 2025 |

### Fronteira / em movimento

- **PFAS ("químicos eternos"):** pressão regulatória crescente. A ECHA publicou proposta atualizada de restrição em ago/2025; há proposta em análise (Alemanha, Holanda e outros) para restringir cerca de **10.000 substâncias PFAS**. Tecnologias de destruição/recuperação de flúor estão em escala-piloto, **não** em uso industrial consolidado. ([ChemTrust](https://chemtrust.org/wp-content/uploads/PFAS-the-Green-Transition_Sept25-1.pdf), [Oxford](https://www.ox.ac.uk/news/2025-03-27-researchers-develop-innovative-new-method-recycle-fluoride-long-lived-forever))

### Lacuna honesta

**Não encontrei fonte confiável sobre mudanças de currículo de química** (o que saiu/entrou nos programas escolares). As buscas retornaram apenas material comercial e de divulgação. **NÃO CONFIRMADO.**

---

## 3. Biologia hoje

### Consenso

| Fato | Detalhe | Fonte | Desde |
|---|---|---|---|
| **Predição de estrutura de proteína está essencialmente resolvida (para proteínas isoladas)** | AlphaFold2 resolveu um problema de 50 anos; rendeu o Nobel de Química 2024. AlphaFold3 (2024) usa arquitetura de difusão e estende para complexos proteína–proteína, proteína–ligante e proteína–ácido nucleico; código aberto em nov/2024. | [Nobel 2024](https://www.nobelprize.org/prizes/chemistry/2024/press-release/); [revisão PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13099841/) | 2020→2024 |
| **Primeira terapia CRISPR aprovada: Casgevy (exa-cel)** | Anemia falciforme e beta-talassemia dependente de transfusão. MHRA (Reino Unido) 16/11/2023; FDA (EUA) 08/12/2023; depois aprovação na UE. Edita células-tronco hematopoiéticas do próprio paciente. | [FDA](https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapies-treat-patients-sickle-cell-disease) | 2023 |
| **Razão bactéria : célula humana é ~1,3 : 1 — não 10 : 1** | Reestimativa: ~3,8×10¹³ bactérias vs ~3,0×10¹³ células humanas num "homem de referência" de 70 kg; massa bacteriana total ≈ 0,2 kg. | [Sender, Fuchs & Milo, PLoS Biology 2016](https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.1002533) | 2016 |
| **Genoma humano completo (telômero a telômero)** | T2T-CHM13: 3,055 bilhões de pares de base, ~200 Mb de sequência inédita (~8% do genoma antes inacessível), 1.956 novas predições gênicas, das quais 99 codificantes. | [Science, abj6987](https://www.science.org/doi/10.1126/science.abj6987); [NHGRI](https://www.genome.gov/about-genomics/telomere-to-telomere) | 2022 |
| **~19.000–20.000 genes codificantes** (não 100.000) | Comparação de 2025 entre Ensembl/GENCODE, RefSeq e UniProtKB: 21.871 genes anotados como codificantes em **pelo menos um** catálogo, mas apenas **19.268 concordantes nos três**. | [Database (Oxford), 2025](https://academic.oup.com/database/article/doi/10.1093/database/baaf045/8263866) | contínuo |
| **Homo sapiens tem ~300.000 anos e origem pan-africana** | Fósseis de Jebel Irhoud (Marrocos) empurraram a origem da espécie em **100 mil anos** e enfraqueceram a ideia de um único berço na África Oriental. | [Nature 22336](https://www.nature.com/articles/nature22336); [Smithsonian Human Origins](https://humanorigins.si.edu/research/whats-hot-human-origins/our-species-arose-least-300000-years-ago) | 2017 |
| **"Cinco reinos" está obsoleto; Protista não é táxon válido** | Protista é **parafilético**. A classificação moderna usa três domínios e **supergrupos** de eucariotos; os antigos "protozoários" ficaram dispersos entre grupos distintos. | [PLoS Genetics](https://journals.plos.org/plosgenetics/article?id=10.1371%2Fjournal.pgen.0020220); [revisão PMC 11999532](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11999532/) | anos 2000→ |
| **Aves são dinossauros; muitos terópodes tinham penas** | *Sinosauropteryx* (1996) foi o primeiro terópode emplumado não diretamente aparentado a aves; desde então, tiranossauroides emplumados (*Yutyrannus*) foram achados. | [Nat Geo](https://www.nationalgeographic.com/animals/article/160405-dinosaurs-feathers-birds-museum-new-york-science) | 1996→ |
| **O apêndice não é vestigial** | Alta concentração de tecido imune (desenvolvimento de linfócitos B e T, produção de IgA) e atua como **reservatório de microbiota** para repovoar o intestino após infecção/antibiótico. Surgiu de forma independente em dezenas de espécies. | [Gut Pathogens / Springer 2025](https://link.springer.com/article/10.1186/s13099-025-00696-2); [NPR](https://www.npr.org/sections/health-shots/2024/02/02/1228474984/appendix-function-appendicitis-gut-health) | 2007→ |
| **Nobel de Medicina 2024** | Victor Ambros e Gary Ruvkun — descoberta do **microRNA** e seu papel na regulação pós-transcricional. | [NobelPrize.org](https://www.nobelprize.org/prizes/medicine/2024/summary/) | 2024 |
| **Nobel de Medicina 2025** | Mary Brunkow, Fred Ramsdell e Shimon Sakaguchi — **tolerância imunológica periférica**: células T reguladoras e o gene FOXP3. | [NobelPrize.org](https://www.nobelprize.org/prizes/medicine/2025/press-release/) | 2025 |

### Fronteira / não fechado

| Tema | Estado real |
|---|---|
| **Neurogênese adulta no hipocampo humano** | Debate de décadas caminhando para consenso: evidências de 2025 (scRNA-seq + assinatura genética de progenitores neurais) apontam neurogênese **de baixo nível, ao longo da vida**, muito mais lenta que em roedores e com **enorme variação individual** — alguns adultos podem não gerar neurônios novos. Não é caso encerrado. ([Science](https://www.science.org/content/article/genetic-evidence-our-brains-make-new-neurons-adulthood-may-close-century-old-debate); [Nature s41586-026-10169-4](https://www.nature.com/articles/s41586-026-10169-4)) |
| **AlphaFold3 em proteínas desordenadas** | Alucinações documentadas em proteínas intrinsecamente desordenadas. Predição de complexos ainda não tem a confiabilidade da predição de monômeros. ([arXiv:2510.15939](https://arxiv.org/pdf/2510.15939)) |
| **T. rex tinha penas?** | **Sem evidência fóssil direta.** É inferência filogenética a partir de parentes emplumados. Não afirmar como fato. ([BBC Science Focus](https://www.sciencefocus.com/planet-earth/did-t-rex-actually-have-feathers)) |
| **Brontosaurus é gênero válido?** | Revalidado por Tschopp et al. (2015, PeerJ) com análise de 477 caracteres em 81 espécimes. **Recepção mista** entre paleontólogos — os caracteres poderiam ser pontuados de outra forma. Não é consenso fechado nem nos dois sentidos. |

---

## 4. Matemática hoje

### Resultado maior confirmado

**Conjectura de Kakeya em 3 dimensões — PROVADA.**
- Hong Wang (NYU/Courant) e Joshua Zahl (UBC), preprint de **24/02/2025**, 127 páginas.
- Resultado: todo conjunto de Kakeya em ℝ³ tem dimensão de Minkowski **e** de Hausdorff igual a 3.
- Validado publicamente por **Terence Tao** em seu blog.
- Hong Wang recebeu a **Medalha Fields 2026** por isso — terceira mulher em 90 anos de prêmio.
- Fontes: [arXiv:2502.17655](https://arxiv.org/abs/2502.17655); [blog de Terence Tao](https://terrytao.wordpress.com/2025/02/25/the-three-dimensional-kakeya-conjecture-after-wang-and-zahl/); [UBC](https://www.math.ubc.ca/news-events/news/mar-4-2025-josh-zahl-and-hong-wang-prove-kakeya-conjecture-three-dimensions); [Quanta](https://www.quantamagazine.org/once-in-a-century-proof-settles-maths-kakeya-conjecture-20250314/).

**Medalhas Fields 2026** (confirmados individualmente pela Quanta): Hong Wang; **Jacob Tsimerman** (prova da conjectura de André-Oort); **John Pardon** (geometria simplética).
⚠️ **NÃO CONFIRMEI a lista completa** — normalmente são até 4 medalhistas e não localizei o anúncio oficial da IMU.

### IA em matemática — o que realmente aconteceu

Fonte principal: [Quanta, "The AI Revolution in Math Has Arrived", 13/04/2026](https://www.quantamagazine.org/the-ai-revolution-in-math-has-arrived-20260413/).

| Evento | Data | O que de fato ocorreu |
|---|---|---|
| IMO | verão/2025 | Sistemas de IA resolveram **5 de 6** problemas. ⚠️ São problemas com resposta conhecida — **não** questões abertas. |
| Conjectura de Nesterov | out/2025 | Ernest Ryu provou um problema aberto de **42 anos** sobre convergência de algoritmos de otimização, usando ChatGPT iterativamente como parceiro de verificação. ~12 h ao longo de 3 dias. A IA produzia "provas incorretas" contendo "resultados parciais corretos". |
| Intervalos de Bruhat | out/2025 | AlphaEvolve identificou estruturas de hipercubo em grupos de permutação — "uma estrutura que estava ali há 50 anos". Verificado por cinco matemáticos. |
| Problemas de Erdős | 2025–2026 | Vários problemas do banco `erdosproblems.com` (criado por Thomas Bloom em 2023) foram resolvidos com assistência de IA e **formalizados em Lean**. |
| Primeiro "Proof Challenge" | fev/2026 | Modelos resolveram mais da metade de 10 questões de nível de pesquisa. |

**A avaliação de Terence Tao** (na mesma matéria): os modelos produzem *"sucessos esparsos em meio a um grande mar de fracassos não reportados"*. São muito bons em **varrer listas grandes de problemas atrás de frutos ao alcance da mão**, e incapazes de **planejamento estratégico de longo prazo**. Igor Pak: problemas maiores (por exemplo, se π + e é racional) estão a "séculos" de distância.

**O papel do Lean.** A formalização é o que separa resultado real de texto plausível. Com verificadores automáticos, provas podem ser quebradas em pedaços e checadas por máquina. A própria matéria alerta para a "poluição do bem comum por bobagem gerada por IA" — e aponta os sistemas formais como a defesa.

### O que NÃO foi provado (para evitar contaminação)

- ❌ **Primos gêmeos** — em aberto. Ver seção 0.
- ❌ **Hipótese de Riemann** — em aberto.
- ❌ Nenhum problema do Milênio foi resolvido além da Conjectura de Poincaré (Perelman, 2003).

---

## 5. ⭐ CATÁLOGO DE FATOS DESATUALIZADOS

> **Este é o entregável de maior valor.** O acervo de PDFs do projeto é de livros antigos. Cada linha abaixo é um erro que o Bee **vai aprender e repetir para sempre** se o PDF entrar cru no corpus.
> Regra de uso: transformar a coluna "o livro antigo diz" em filtro de busca/regex sobre o acervo antes do pré-treino.

| # | O que o livro antigo diz | O que se sabe hoje | Fonte | Desde |
|---|---|---|---|---|
| 1 | O quilograma é a massa do cilindro de platina-irídio guardado em Sèvres/Paris. | O quilograma é definido pela **constante de Planck** (*h* = 6,62607015×10⁻³⁴ J·s, exato). O cilindro deixou de ser a definição. Ampere, kelvin e mol também foram redefinidos por constantes. | [BIPM](https://www.bipm.org/documents/20126/41489673/SI-App2-kilogram.pdf) / [NIST](https://www.nist.gov/si-redefinition/kilogram-mass-and-plancks-constant) | 20/05/2019 |
| 2 | O Sistema Solar tem **nove** planetas. | Tem **oito**. Plutão é **planeta anão** desde a resolução da IAU. Também são planetas anões: Ceres, Haumea, Makemake e Éris. | [IAU](https://iauarchive.eso.org/public/themes/pluto/) | 24/08/2006 |
| 3 | A língua tem **zonas de sabor** (doce na ponta, amargo no fundo etc.). | Falso. Todas as regiões da língua detectam todos os sabores. O "mapa" nasceu de tradução/simplificação equivocada da tese alemã de **David Hänig (1901)**, popularizada por um diagrama de Boring; Hänig só havia medido pequenas diferenças de **limiar**, não zonas exclusivas. Refutado experimentalmente por Virginia Collins em 1974. | [Smithsonian Magazine](https://www.smithsonianmag.com/science-nature/neat-and-tidy-map-tastes-tongue-you-learned-school-all-wrong-180963407/); [McGill OSS](https://www.mcgill.ca/oss/article/student-contributors-history/tongue-map-trap-0) | 1974 (ignorado até hoje) |
| 4 | O genoma humano tem ~100.000 genes. | **~19.000–20.000** genes codificantes de proteína. A estimativa caiu de 50–100 mil (anos 80) → 30–40 mil (2001) → ~20 mil. Em 2025, 19.268 concordantes entre os três catálogos principais. | [Database (Oxford) 2025](https://academic.oup.com/database/article/doi/10.1093/database/baaf045/8263866) | contínuo desde 2001 |
| 5 | Temos **10× mais bactérias** do que células no corpo. | A razão é **~1,3 : 1** (±25%). Bactérias e células humanas são da mesma ordem de grandeza. Massa bacteriana total ≈ 0,2 kg. | [PLoS Biology 2016](https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.1002533) | 2016 |
| 6 | O apêndice é um órgão **vestigial**, sem função. | Tem função: tecido imune (linfócitos B/T, IgA) e **reservatório de microbiota** para repovoar o intestino. Surgiu de forma independente em dezenas de espécies — sinal de vantagem adaptativa real. | [Springer/Gut Pathogens 2025](https://link.springer.com/article/10.1186/s13099-025-00696-2) | 2007→ |
| 7 | A Terra tem **quatro** camadas (crosta, manto, núcleo externo, núcleo interno). | Há uma **quinta**: o *núcleo interno mais interno*, uma bola metálica sólida de ferro-níquel com estrutura cristalina distinta, no centro do núcleo interno. Detectada por ondas sísmicas repicantes de ~200 terremotos de magnitude ≥6. | [Nature Communications / ANU](https://www.anu.edu.au/news/all-news/bouncing-seismic-waves-confirm-fifth-layer-in-earths-core) | fev/2023 |
| 8 | O genoma humano foi "completado" em 2003. | O de 2003 cobria só a fração **eucromática**. O genoma **realmente completo** (T2T-CHM13) saiu em 2022, acrescentando ~200 Mb (~8% do genoma) antes inacessíveis. | [Science abj6987](https://www.science.org/doi/10.1126/science.abj6987) | 2022 |
| 9 | Existem **cinco reinos** (Monera, Protista, Fungi, Plantae, Animalia). | Obsoleto. **Protista é parafilético** e não é táxon válido. A classificação moderna usa três domínios e supergrupos de eucariotos. | [PLoS Genetics](https://journals.plos.org/plosgenetics/article?id=10.1371%2Fjournal.pgen.0020220) | anos 2000→ |
| 10 | Dinossauros eram répteis escamosos; as aves são um grupo à parte. | **Aves são dinossauros.** Muitos terópodes tinham penas (*Sinosauropteryx*, 1996; *Yutyrannus*). | [Nat Geo](https://www.nationalgeographic.com/animals/article/160405-dinosaurs-feathers-birds-museum-new-york-science) | 1996→ |
| 11 | O *Homo sapiens* surgiu há ~200.000 anos, na África Oriental. | **~300.000 anos**, com origem provavelmente **pan-africana**. Fósseis de Jebel Irhoud (Marrocos) recuaram a data em 100 mil anos. | [Nature 22336](https://www.nature.com/articles/nature22336) | 2017 |
| 12 | Enrolar a língua, lóbulo da orelha solto e "pico de viúva" são traços mendelianos simples (um gene, dois alelos). | **Nenhum dos três é.** Estudos de família e de gêmeos mostram que enrolar a língua é influenciado por genética *e* ambiente e é em parte aprendido; para lóbulo e pico de viúva não há padrão de herança consistente nem genes localizados — os traços são contínuos, não binários. | [Myths of Human Genetics, Univ. of Delaware (J. McDonald)](https://udel.edu/~mcdonald/mythintro.html) | há décadas, ainda ensinado |
| 13 | Usamos apenas **10% do cérebro**. | Falso. Usamos praticamente todo o cérebro; neuroimagem mostra atividade em virtualmente todas as regiões ao longo de tarefas variadas. | [MIT McGovern Institute](https://mcgovern.mit.edu/2024/01/26/do-we-use-only-10-percent-of-our-brain/); [BrainFacts](https://www.brainfacts.org/thinking-sensing-and-behaving/thinking-and-awareness/2019/debunked-the-10-percent-brain-myth-061719) | — |
| 14 | Pessoas são "cérebro esquerdo" (lógicas) ou "cérebro direito" (criativas). | Sem evidência em neuroimagem. Não existe dominância hemisférica de personalidade; os dois lados trabalham juntos, e o padrão varia conexão a conexão. | [University of Utah Health](https://healthcare.utah.edu/press-releases/2013/08/researchers-debunk-myth-of-right-brain-and-left-brainpersonality-traits) | 2013 |
| 15 | Cada aluno tem um "estilo de aprendizagem" (visual/auditivo/cinestésico) e aprende melhor se o ensino combinar com ele. | **Neuromito.** Nenhum suporte empírico à hipótese de combinação. Pessoas até *preferem* um estilo, mas não aprendem melhor com ele. | [PubMed 34973019](https://pubmed.ncbi.nlm.nih.gov/34973019/) | revisões desde ~2008 |
| 16 | O peso atômico de cada elemento é um número fixo. | Para vários elementos é um **intervalo**. Argônio e chumbo passaram a ser expressos como intervalos porque a variação isotópica natural excede a incerteza de medição. | [IUPAC/CIAAW](https://www.ciaaw.org/atomic-weights.htm) | 2021 |
| 17 | O Monte Everest tem 8.848 m. | **8.848,86 m**, valor acordado conjuntamente por China e Nepal. | [Kathmandu Post](https://kathmandupost.com/national/2020/12/08/it-s-official-mount-everest-is-8-848-86-metres-tall) | 08/12/2020 |
| 18 | A Terra tem **quatro** oceanos. | ⚠️ **Disputado.** National Geographic reconhece o **Oceano Austral** como quinto desde 08/06/2021, e a NOAA desde fev/2021 — mas a **IHO (Organização Hidrográfica Internacional) oficialmente ainda reconhece quatro**. Não há acordo internacional. | [Nat Geo](https://www.nationalgeographic.com/environment/article/theres-a-new-ocean-now-can-you-name-all-five-southern-ocean); [Snopes](https://www.snopes.com/news/2021/06/09/worlds-fifth-ocean-recognized/) | 2021 |
| 19 | Júpiter é o planeta com mais luas ("Saturno tem 83"). | **Saturno lidera com folga.** Mar/2025: +128 luas → 274. Mar/2026 (MPC/IAU): +11 → **285**. Júpiter: +4 → **101**. ⚠️ **Número instável — não ensinar valor fixo.** | [IAU/MPC, 16/03/2026](https://www.iau.org/IAU/IAU/News/Ann2026/MPC-New-Moons-Saturn-Jupiter.aspx); [EarthSky](https://earthsky.org/space/more-moons-for-jupiter-and-saturn-total-satellite-discoveries/) | 2025–2026 |
| 20 | A anomalia do múon (g−2) é evidência de física além do Modelo Padrão. | Não é mais. A previsão do Modelo Padrão foi revisada com lattice QCD e passou a **concordar** com a medição final do Fermilab (2025). | [APS Physics 18,150](https://link.aps.org/doi/10.1103/Physics.18.150) | 2025 |
| 21 | (Material de 2023) Existe supercondutor à temperatura ambiente (LK-99 / trabalhos de Ranga Dias). | **Não existe.** LK-99 refutado (era ferromagnetismo, não levitação supercondutora); artigo de Dias **retratado pela Nature**. | [Nature news](https://www.nature.com/articles/d41586-023-03398-4) | nov/2023 |
| 22 | "A fusão nuclear já gera mais energia do que consome." | Impreciso. O ganho reportado (ex.: 4,13 em abr/2025) é **ganho no alvo** — fusão ÷ laser entregue ao alvo. Não inclui a energia da rede para operar os lasers. Balanço energético de engenharia continua **negativo**. | [LLNL/NIF](https://lasers.llnl.gov/science/achieving-fusion-ignition) | 2022→ |
| 23 | Neurônios novos não nascem no cérebro adulto. | Evidência de 2025 favorece neurogênese **de baixo nível ao longo de toda a vida** no hipocampo — porém lenta e com grande variação individual. ⚠️ Consenso emergente, não fechado: não substituir um dogma por outro. | [Science](https://www.science.org/content/article/genetic-evidence-our-brains-make-new-neurons-adulthood-may-close-century-old-debate) | 2025 |
| 24 | *Brontosaurus* não existe — é *Apatosaurus*. | ⚠️ **Reaberto, não resolvido.** Tschopp et al. (2015, PeerJ) revalidaram o gênero com 477 caracteres em 81 espécimes; **recepção permanece mista** entre paleontólogos. O correto hoje é dizer que é disputado. | [Science/AAAS](https://www.science.org/content/article/brontosaurus-name-resurrected-new-dino-family-tree) | 2015 |

---

## 6. Unidades e nomenclatura — o que mudou oficialmente

| Domínio | Mudança | Autoridade | Data |
|---|---|---|---|
| **SI** | kg, ampere, kelvin e mol redefinidos por constantes exatas (*h*, *e*, *k*<sub>B</sub>, *N*<sub>A</sub>). O SI passou a ser construído sobre **sete constantes definidoras**. | BIPM / CGPM | 20/05/2019 |
| **IUPAC — elementos** | Nomes oficializados: nihônio (113), moscóvio (115), tenessino (117), oganessônio (118). Tabela fecha em **118**. | IUPAC | 2016 |
| **IUPAC — pesos atômicos** | 2021: revisão de Ar, Hf, Ir, Pb, Yb (Ar e Pb viraram **intervalos**). 2023: Gd → 157,249±0,002; Lu → 174,96669±0,00005; Zr → 91,222±0,003. | IUPAC/CIAAW | 2021, 2023 |
| **Astronomia** | Definição formal de "planeta" (3 critérios, incluindo *limpar a vizinhança orbital*) → 8 planetas, Plutão vira planeta anão. | IAU | 24/08/2006 |
| **Astronomia** | Contagem de luas atualizada continuamente pelo Minor Planet Center. Saturno 285 / Júpiter 101 em 16/03/2026. | IAU / MPC | 2026 |
| **Taxonomia** | "Protista"/"protozoário" abandonados como táxons formais; classificação por três domínios + supergrupos de eucariotos. | literatura filogenética | anos 2000→ |
| **Geografia** | Oceano Austral: reconhecido por NatGeo (2021) e NOAA (2021); **não** oficializado pela IHO. | — | 2021, disputado |

---

## 7. ⭐ O que é ensinável a um modelo de 151M parâmetros

### O contrapeso, dito sem rodeios

O Bee tem 151M de parâmetros e foi pré-treinado em ~9,87B tokens de PT-BR, com bpb ≈ 3,46 e conteúdo factual reconhecidamente fraco. Nessa escala, o modelo:

- **Guarda co-ocorrência lexical**, não conhecimento. Ele aprende que "Plutão" aparece perto de "planeta anão" — não aprende o critério da IAU.
- **Não sustenta raciocínio de várias etapas.** Nada de derivação, dedução encadeada ou "por quê" com mais de um elo.
- **Não faz aritmética confiável.** Não vai calcular, converter unidade nem comparar magnitudes.
- **Não tem calibração de incerteza.** Vai afirmar "provavelmente", "há evidência de que" e "é fato" exatamente com a mesma confiança — ou seja, **toda nuance que você escrever vira afirmação categórica na boca dele**.
- **Não memoriza fato raro.** Fato que aparece 1–2 vezes no corpus não é retido. Memorização exige repetição e paráfrase múltipla.
- **Alucina dígitos.** Qualquer número com mais de 2–3 algarismos significativos será corrompido.

### ✅ ENSINÁVEL — fatos curtos, estáveis, canônicos

Critérios para um fato entrar: **(a)** cabe em uma oração sujeito-predicado; **(b)** não mudou nos últimos 15 anos e não deve mudar nos próximos 15; **(c)** não contém número com mais de 2 algarismos significativos; **(d)** pode ser parafraseado de 5–10 formas sem mudar de sentido.

Exemplos que passam nos quatro critérios:

- "O Sol é uma estrela." / "A Terra gira em torno do Sol."
- "O Sistema Solar tem oito planetas." / "Plutão é um planeta anão."
- "A água é formada por hidrogênio e oxigênio." / "A fórmula da água é H₂O."
- "O símbolo químico do oxigênio é O." (símbolos e nomes de elementos — **excelente material**: são pares curtos, estáveis, e há 118 deles)
- "O corpo humano tem 46 cromossomos."
- "As aves descendem dos dinossauros."
- "O apêndice faz parte do sistema imunológico."
- "A unidade de força no SI é o newton." (unidades base e derivadas — pares curtos e estáveis)
- "O quilograma é definido pela constante de Planck." (a frase é curta; o valor numérico **não** entra)
- Relações de tipo: *X é um tipo de Y* · *X é composto de Y* · *X fica em Y* · *X foi descoberto por Y*.

**Como ensinar:** cada fato em forma canônica, repetido com 5–10 paráfrases distintas ao longo do corpus. Sem paráfrase, você ensina uma string; com paráfrase, ensina uma associação.

### ❌ DESCARTAR EXPLICITAMENTE

| O que não ensinar | Por quê |
|---|---|
| Mecânica quântica, relatividade, termodinâmica — **qualquer explicação** | Exige encadeamento conceitual que 151M não tem. Resultado garantido: frases com vocabulário certo e conteúdo sem sentido. Isso é pior que não saber. |
| Qualquer "por quê" de duas ou mais etapas | Mesma razão. |
| Aritmética, álgebra, resolução de problemas | Não é a arquitetura nem a escala. |
| Constantes com muitos dígitos (6,62607015×10⁻³⁴; 3,055 Gb; 0,3092±0,0087) | Alucinação de dígito é certa. Se precisa do número exato, não é tarefa pra este modelo. |
| **Números instáveis**: luas de Saturno, contagem de genes, recordes de fusão, número de detecções de ondas gravitacionais | O dado muda a cada ano. O modelo congela o valor **para sempre**. Ensinar "Saturno tem 274 luas" cria um erro datado permanente. |
| **Tudo da seção "Fronteira"**: energia escura dinâmica, neurogênese adulta, penas do T. rex, validade de *Brontosaurus*, tensão de Hubble | A formulação correta é toda feita de qualificadores ("há evidência sugestiva de que…"), e o modelo **descarta os qualificadores**. Ensinar fronteira a 151M = ensinar afirmação falsa. |
| Datas específicas (anos, dias) | Alto risco de mistura de anos. Se a data não é essencial, corte. |
| Prêmios Nobel, nomes de pesquisadores recentes | Baixíssima frequência no corpus PT-BR; não serão memorizados e viram fonte de confabulação de nomes. |

### 🧹 O uso mais valioso desta pesquisa: despoluir o acervo

A seção 5 não é principalmente uma lista do que **acrescentar** — é uma lista do que **remover**. Fluxo sugerido:

1. Rodar busca textual no acervo de PDFs pelos padrões da coluna "o livro antigo diz" (`nove planetas`, `cilindro de platina`, `zonas de sabor`, `10% do cérebro`, `cinco reinos`, `100.000 genes`, `órgão vestigial`, `estilos de aprendizagem`, `enrolar a língua`, `dez vezes mais bactérias`, `quatro camadas`).
2. Todo documento com match: **descartar ou corrigir** — nunca deixar passar.
3. Só depois pensar em adicionar os fatos corrigidos, em forma canônica parafraseada.

O passo 1–2 tem retorno muito maior que o passo 3. Remover um erro repetido em 50 PDFs vale mais do que inserir 50 fatos novos que aparecem uma vez cada.

---

## 8. Veredito honesto

1. **A ciência de 2024–2026 é, em quase toda a sua extensão, incompatível com um modelo de 151M.** O que há de mais interessante hoje — energia escura dinâmica, neurogênese adulta, limites de neutrino, IA em matemática — é feito de **nuance, incerteza calibrada e número preciso**, exatamente as três coisas que essa escala não sustenta. Não recomendo ensinar nada disso ao Bee.

2. **O ganho real está na remoção, não na adição.** As 24 linhas da seção 5 são erros que o acervo de livros antigos vai injetar no modelo. Filtrá-los é barato, mensurável e tem efeito permanente. Ensinar ciência nova é caro, difícil de medir e provavelmente não vai pegar.

3. **Expectativa realista do que se ganha:** o Bee deixa de dizer "nove planetas" e "o quilograma é o cilindro de Paris". Ele **não** vira um modelo científico. Um teto honesto seria algo entre **50 e 150 fatos científicos curtos**, cada um com 5–10 paráfrases — o que é uma fração desprezível do corpus e, ainda assim, mais do que é seguro prometer.

4. **A lição metodológica pode valer mais que o conteúdo.** A falsa "prova dos primos gêmeos" (seção 0) apareceu em três sites com aparência de reportagem, na primeira página de busca. Se o pipeline de corpus do Bee raspar web aberta em busca de ciência, ele vai ingerir isso. **Restrinja a domínios institucionais.**

5. **Se for para ensinar ciência ao Bee, ensine o vocabulário e as relações — não os conceitos.** Nomes e símbolos dos 118 elementos, unidades do SI e seus símbolos, nomes de planetas, classes taxonômicas: são milhares de pares curtos, estáveis, canônicos e fáceis de parafrasear. É o único subconjunto de "ciência" que essa escala aguenta de verdade.

---

## 9. Lacunas e não-confirmados (registro de honestidade)

| Item | Situação |
|---|---|
| Lista **completa** das Medalhas Fields 2026 | **NÃO CONFIRMADA.** Confirmei individualmente Hong Wang, Jacob Tsimerman e John Pardon via Quanta; não localizei o anúncio oficial da IMU. |
| Mudanças de **currículo de química** | **NÃO CONFIRMADO.** Buscas retornaram apenas material comercial e de divulgação. |
| Elementos **119 e 120** | **NÃO SINTETIZADOS** até onde a busca confirma (ago/2026). A tentativa do Berkeley Lab estava prevista para começar por volta do fim de 2025; **resultado desconhecido**. |
| Mitos populares que **NÃO incluí** por falta de fonte confiável | Camaleão muda de cor por camuflagem; memória de 3 segundos do peixe dourado; Muralha da China visível do espaço; sangue nas veias é azul; vidro escorre lentamente; erro de vírgula no ferro do espinafre; morcegos são cegos. Apareceram **apenas em listicles**. Podem até ser verdadeiros como mitos, mas **não os validei** e por isso não entraram no catálogo. |
| Fechamento definitivo da anomalia **g−2 do múon** | Depende de o lattice QCD estar correto. Persiste tensão com dados de colisores e⁺e⁻. Tratar como **consenso emergente**, não encerrado. |
| Afirmação de que "~40% das novas estruturas do PDB em 2024–2025 vieram de predição por IA" | Apareceu numa fonte com antecedente ambíguo. **NÃO USADA** neste documento. |
