# Esqueleto curricular — Física e Química

> **Escopo:** extração do *currículo* (lista e ordem de tópicos), do *método pedagógico* de cada
> autor e dos *pré-requisitos assumidos*, a partir de 8 livros de Física e Química.
> **Nada aqui é transcrição, cópia ou paráfrase próxima dos originais.** Sequência de tópicos,
> método de ensino e estrutura didática são fatos e ideias, não expressão protegida.
> Data: 2026-08-04 · Projeto: BEE (LLM 151M PT-BR do zero) · Fonte dos PDFs: `../../ARTIGOS/`

---

## 1. Inventário

| # | Arquivo | Obra real / autor | Idioma | Nível | Extraível? | Págs |
|---|---|---|---|---|---|---|
| F1 | `511503146-FISICA-RACSO.pdf` | *Física — Fundamentos y Aplicaciones I*, Félix Aucallanchi Velásquez (dir.), Colección RACSO, Peru, 2016 | ES | Pré-universitário → superior inicial (engenharia) | Sim, mas **OCR degradado** | 1035 |
| F2 | `432032012-Fisica-Walter-Teoria-y-practica-Perez-Terrel.pdf` | ⚠️ **O nome do arquivo está errado.** É *Física*, Francisco Ramos Ttito, Editora Macro (Lima), 2ª ed. 2010, coleção SIGNOS. Não é Pérez Terrel. | ES | Pré-universitário (ponte colégio → vestibular de engenharia) | Sim, **texto digital limpo** | 801 |
| F3 | `606250313-Fisica-General-Alvarenga-Share.pdf` | *Física General con experimentos sencillos*, A. Máximo Ribeiro da Luz & Beatriz Alvarenga Álvares (UFMG), 4ª ed., Oxford Univ. Press México, 1998 / reimpr. 2008 | ES (tradução do PT-BR original) | Ensino médio | Sim, mas **OCR degradado**; 144 MB, lento | 1242 |
| F4 | `391132702-100-Problemas-de-Mecanica-Victor-M-Perez-Garcia.pdf` | *100 problemas de Mecánica*, Pérez García, Vázquez Martínez & Fernández-Rañada, Alianza Editorial, 1997 | ES | **Superior** (2º ano de Ciências Físicas, Complutense) | Sim, OCR razoável | 138 |
| Q1 | `408660315-Quimica.pdf` | Apostila *Conceitos Básicos de Química*, Deise Zamboni, 2014 | **PT-BR** | Ensino médio / revisão | Sim, **texto limpo** | 63 |
| Q2 | `570766154-quimica.pdf` | *Química Geral*, Vinícius Kothe, Editora Fael (Curitiba), 2020, ISBN 978-65-990685-0-8 | **PT-BR** | Superior introdutório (EAD) | Sim, **texto digital limpo** | 305 |
| Q3 | `453098173-Quimica-Organica-1.pdf` | *Química Orgánica* (Wade), tradução espanhola. ⚠️ O PDF contém **apenas o Volume 1** (caps. 1–14); o índice lista os 26 capítulos, mas o arquivo termina no cap. 14 | ES | Superior | Sim, texto limpo (estruturas são imagens) | 749 |
| Q4 | `636161103-Fundamentos-de-Quimica-Inorganica.pdf` | *Fundamentos Teóricos de Química Inorgánica*, Ruiz-Sánchez, Herrera-Feijoo, Correa-Salgado, Peñafiel-Arcos, Editorial Grupo AEA (Equador), 2023 | ES | Superior introdutório | Sim, texto limpo | 188 |

**Notas de extração**

- **Nenhum PDF é imagem pura.** Todos os 8 devolvem texto.
- **OCR degradado (F1, F3):** o texto corrido é legível, mas a camada matemática está destruída.
  Exemplos reais de saída: `Ax` no lugar de `Δx`; `J = i6 + 2ad` no lugar de `v² = v₀² + 2ad`;
  `u` no lugar de `v`; índices e expoentes perdidos. **Qualquer número ou fórmula minerado
  desses dois arquivos precisa de conferência humana** — é fonte de erro factual garantido.
- **Idioma:** 6 dos 8 estão em **espanhol**. Só Q1 e Q2 são PT-BR nativos. Isso importa muito
  (ver Veredito): o esqueleto de tópicos atravessa a fronteira do idioma sem problema, mas
  qualquer frase reaproveitada arrasta sintaxe espanhola e falsos cognatos para dentro do Bee.
- **Licenciamento:** 7 dos 8 são obras protegidas (Q3 e F3 com aviso agressivo de reprodução
  proibida; F1 cita explicitamente lei antipirataria peruana). **Exceção: Q4 declara
  Creative Commons BY-NC-SA 4.0** — é o único do lote com licença aberta. NC + SA continuam
  sendo restrições reais, e ironicamente Q4 é o mais fraco pedagogicamente do conjunto.

---

## 2. Currículo consolidado de FÍSICA

União dos 4 livros, do mais básico ao mais avançado. Marcação de origem: **[R]** RACSO,
**[T]** Ramos Ttito, **[A]** Alvarenga, **[P]** Pérez García. O nível sobe verticalmente.

### 2.0 Ferramental prévio (todos os 4 abrem por aqui — é pré-requisito assumido)
- Grandeza física, atributo mensurável, ato de medir como comparação com padrão **[R][T]**
- Grandezas fundamentais × derivadas; grandezas escalares × vetoriais **[R][T][A]**
- Sistema Internacional: 7 unidades-base, prefixos, símbolos **[R][T][A]**
- Notação científica; ordem de grandeza; potências de 10 **[R][A]**
- Algarismos significativos; operações com algarismos significativos; arredondamento **[R][A]**
- Erro de medida, estimativa, aproximação **[R]**
- **Análise dimensional**: equação dimensional, regras algébricas, princípio da homogeneidade,
  dimensão de constantes físicas, uso para verificar/deduzir fórmula **[R][T]** *(ausente em [A])*
- **Funções e gráficos como capítulo próprio**: proporção direta, variação linear,
  variação quadrática/cúbica, relação inversa, mudança de escala **[A] apenas** — Alvarenga
  é o único que trata leitura de gráfico como pré-requisito explícito, antes da cinemática
- Vetores em 2D **[R][T][A]**: representação, soma gráfica (polígono/paralelogramo),
  decomposição em componentes, soma analítica
- Vetores em 3D; produto escalar; produto vetorial **[R]**
- Derivada e integral aplicadas ao movimento **[R]** — RACSO ensina cada grandeza duas vezes:
  primeiro na forma aritmética (razão média), depois na forma de limite/derivada

### 2.1 Cinemática
1. Posição e vetor posição; trajetória
2. Deslocamento (vetorial) × distância percorrida (escalar, nunca negativa)
3. Rapidez × velocidade; média × instantânea
4. Aceleração média e instantânea; aceleração × desaceleração (sinal relativo à velocidade)
5. Movimento retilíneo uniforme (MRU)
6. Movimento retilíneo uniformemente variado (MRUV): equações horárias, equação de Torricelli
7. Gráficos x–t, v–t, a–t; interpretação de área e de inclinação; reta tangente
8. Queda livre; lançamento vertical; aceleração da gravidade; simetria subida/descida
9. Movimento em duas dimensões com aceleração constante; movimento composto
   (independência dos movimentos)
10. Lançamento de projéteis
11. Movimento relativo / composição de velocidades
12. Cinemática circular: rotação, período, frequência, velocidade angular, MCU
13. Movimento circular uniformemente variado (MCUV); aceleração tangencial × centrípeta
14. Transmissão de movimento (polias, engrenagens, correias) **[R][T]**

### 2.2 Dinâmica — leis de Newton
1. Conceito de força; forças fundamentais da natureza
2. 1ª lei (inércia); referencial inercial
3. 3ª lei (ação e reação) — **[A] ensina a 3ª lei ANTES da 2ª**, junto com a 1ª
4. Diagrama de corpo livre
5. Equilíbrio de partícula (1ª condição de equilíbrio)
6. Força de atrito estático e cinético; coeficiente de atrito
7. 2ª lei de Newton; unidades de força e de massa; massa × peso
8. Aplicações: plano inclinado, sistemas de corpos ligados, máquina de Atwood
9. Forças no movimento circular; força centrípeta
10. Queda com resistência do ar; velocidade terminal **[A]**
11. Limitações da mecânica newtoniana (fronteira relativística/quântica) **[A]**

### 2.3 Estática e corpo rígido
1. Momento (torque) de uma força
2. 2ª condição de equilíbrio; equilíbrio do corpo rígido
3. Centro de gravidade / centro de massa
4. Máquinas simples: alavancas, polias, plano inclinado **[T]**
5. *(nível superior)* Momento de inércia **[R]**
6. *(nível superior)* 2ª lei de Newton para sólidos; rotação **[R]**
7. *(nível superior)* Trabalho e energia no corpo rígido **[R]**
8. *(nível superior)* Momento angular e sua conservação **[R]**

### 2.4 Gravitação
1. Leis de Kepler (órbitas, áreas, períodos)
2. Lei da gravitação universal
3. Variação de *g* com a altitude
4. Movimento de satélites; velocidade orbital
5. Energia potencial gravitacional (forma geral)

### 2.5 Trabalho, energia, potência
1. Trabalho mecânico (força constante; força variável)
2. Potência
3. Energia cinética; teorema trabalho–energia cinética
4. Energia potencial gravitacional
5. Energia potencial elástica
6. Forças conservativas × dissipativas
7. Conservação da energia mecânica; aplicações
8. Relação massa–energia **[A]**

### 2.6 Quantidade de movimento
1. Impulso e quantidade de movimento
2. Quantidade de movimento de um sistema de partículas
3. Conservação da quantidade de movimento
4. Forças impulsivas; colisões elásticas, inelásticas e perfeitamente inelásticas

### 2.7 Oscilações e ondas
1. Movimento harmônico simples: definição, elementos (amplitude, período, frequência, fase)
2. Relação MHS ↔ projeção do MCU
3. Dinâmica do MHS; lei de Hooke; associação de molas
4. Energia no MHS
5. Pêndulo simples
6. Oscilações amortecidas, forçadas e ressonância **[R]**
7. Conceito de onda; função de onda; ondas transversais × longitudinais
8. Elementos da onda; velocidade de propagação em corda
9. Reflexão e refração de ondas mecânicas
10. Difração; interferência **[A]**
11. Ondas sonoras; acústica; tubos sonoros e cordas vibrantes
12. Efeito Doppler **[A]**

### 2.8 Fluidos (hidrostática)
1. Densidade e massa específica
2. Pressão; pressão atmosférica; experiência de Torricelli
3. Variação da pressão com a profundidade (teorema de Stevin)
4. Vasos comunicantes
5. Princípio de Pascal; prensa hidráulica
6. Princípio de Arquimedes; empuxo; flutuação
> Nota curricular: **[T] declara explicitamente que hidrodinâmica fica de fora** por exigir
> matemática avançada. Os 4 livros param na hidrostática.

### 2.9 Termologia e termodinâmica
1. Temperatura; lei zero da termodinâmica; equilíbrio térmico
2. Termômetros e escalas (Celsius, Fahrenheit, Kelvin); história das escalas **[A]**
3. Dilatação térmica de sólidos (linear, superficial, volumétrica) e de líquidos
4. Calor como energia em trânsito; caloria × joule; equivalente mecânico do calor
5. Capacidade térmica e calor específico; calorimetria
6. Calor latente; mudanças de fase (fusão, vaporização, sublimação)
7. Influência da pressão nas mudanças de fase; diagrama de fases
8. Transmissão de calor: condução, convecção, radiação
9. Gases: transformação isotérmica (Boyle), isobárica, isocórica
10. Lei de Avogadro; equação de estado do gás ideal
11. Modelo cinético-molecular do gás; interpretação microscópica da temperatura
12. Trabalho numa variação de volume
13. 1ª lei da termodinâmica; aplicações
14. 2ª lei; máquinas térmicas; rendimento; ciclo de Carnot
15. Comportamento de gás real **[A]**

### 2.10 Eletrostática
1. Carga elétrica; processos de eletrização (atrito, contato, indução); polarização
2. Condutores e isolantes; eletroscópio
3. Conservação e quantização da carga
4. Lei de Coulomb
5. Campo elétrico; campo de cargas puntiformes; linhas de força; superposição
6. Comportamento do condutor eletrizado; blindagem; rigidez dielétrica; poder das pontas **[A]**
7. Potencial elétrico; diferença de potencial (tensão); potencial de carga puntiforme
8. Superfícies equipotenciais
9. Energia potencial eletrostática de um conjunto de cargas **[T]**
10. Capacitância; capacitores; associação; energia armazenada **[A][T]**

### 2.11 Eletrodinâmica
1. Corrente elétrica (contínua e alternada); intensidade
2. Circuitos simples de CC
3. Resistência elétrica; resistividade; variação da resistência com a temperatura
4. Lei de Ohm; condutores ôhmicos e não-ôhmicos
5. Associação de resistores em série e em paralelo
6. Força eletromotriz; equação do circuito; tensão terminal do gerador
7. Leis de Kirchhoff **[T]**
8. Potência elétrica; efeito Joule
9. Instrumentos de medição: amperímetro, voltímetro
10. Válvula eletrônica e transistor (leitura histórica) **[A]**

### 2.12 Eletromagnetismo
1. Magnetismo; ímãs; polos
2. Experiência de Oersted; campo magnético criado por corrente
3. Campo magnético; vetor indução
4. Força magnética sobre carga em movimento; movimento circular em campo magnético; cíclotron
5. Força magnética sobre condutor percorrido por corrente
6. Torque sobre espira de corrente **[T]**
7. Campo de condutor retilíneo, de espira circular, de solenoide
8. Influência do meio (permeabilidade magnética)
9. Lei de Biot-Savart *(apêndice, opcional)* **[A]**
10. Força eletromotriz induzida; lei de Faraday; lei de Lenz
11. Transformador; gerador de corrente alternada; valores eficazes
12. Ondas eletromagnéticas; espectro eletromagnético
13. Transmissão e distribuição de energia elétrica

### 2.13 Óptica
1. Natureza da luz; velocidade da luz; modelo corpuscular × ondulatório
2. Reflexão; espelho plano; espelhos esféricos; equação dos espelhos
3. Refração; índice de refração; lei de Snell
4. Reflexão total interna
5. Fenômenos ligados à refração (miragem, profundidade aparente)
6. Dispersão / decomposição da luz; cores dos corpos
7. Lentes esféricas; formação de imagens; equação das lentes
8. Instrumentos ópticos (olho, lupa, microscópio, telescópio)
9. Fenômenos ondulatórios da luz: difração, interferência, polarização
10. Comportamento corpuscular das ondas eletromagnéticas (fóton) **[T]**

### 2.14 Mecânica avançada — só **[P]**, nível universitário
1. Partícula em uma dimensão: energia potencial a partir da força, pontos de equilíbrio,
   estabilidade pela 2ª derivada, oscilações pequenas
2. Partícula em 2D e 3D; potenciais centrais
3. Colisões (referencial do centro de massa)
4. Formulação lagrangiana; coordenadas generalizadas
5. Movimento planetário (problema de Kepler pela via lagrangiana)
6. Teoria do potencial
7. Oscilações; modos normais em sistemas com vários graus de liberdade
8. Sistemas de referência não inerciais (forças de Coriolis e centrífuga)
9. Sólido rígido I: movimento plano
10. Sólido rígido II: movimento geral (tensor de inércia, peão, ângulos de Euler)

---

## 3. Currículo consolidado de QUÍMICA

Marcação: **[Z]** Zamboni (apostila PT-BR), **[K]** Kothe (Química Geral PT-BR),
**[I]** Inorgânica (Ruiz-Sánchez), **[W]** Wade (Orgânica, vol. 1).

### 3.0 Química como ciência (porta de entrada em [K] e [I])
- O que é química; definição; relação com física, biologia, geologia; campos de estudo **[I]**
- Química no cotidiano: nome comum ↔ nome oficial ↔ fórmula (acetona/propanona,
  vinagre/ácido acético, sal de cozinha/cloreto de sódio…) **[K]**
- Método científico: observação → hipótese → teoria → lei; ciência como revisão contínua **[Z][K]**
- Laboratório: normas de segurança, EPIs, vidraria e utensílios **[K]**
- Sistema Internacional; medições em química; massa × peso; comprimento e volume;
  densidade e densidade relativa; calor × temperatura **[I][K]**
- Algarismos significativos; exatidão × precisão; fator unitário de conversão **[I]**
- Energia cinética e potencial (noção mínima importada da física) **[I]**

### 3.1 Matéria e suas transformações
1. Definição de matéria (massa e volume)
2. Propriedades da matéria; mudanças que a matéria sofre
3. Estados físicos: sólido, líquido, gasoso e **plasma** (explicação pela distância e atração
   entre partículas) **[K][I]**
4. Mudanças de estado: fusão, solidificação, vaporização, condensação, sublimação
5. Curva de aquecimento; patamar de temperatura constante; **substância pura × mistura
   distinguidas pelo patamar** — este é o "conceito-chave" que [Z] e [K] usam como divisor
6. Fenômeno físico × fenômeno químico (critério: houve mudança na estrutura/ligação?)
7. Substância pura simples × substância pura composta × mistura
8. Misturas homogêneas × heterogêneas; fases
9. Separação de misturas (destilação, filtração, decantação, cristalização) **[K]**

### 3.2 Atomística e estrutura atômica
1. Evolução dos modelos atômicos, em ordem e **com o experimento que derrubou cada um**:
   Dalton (esfera maciça/"bola de bilhar") → Thomson (raios catódicos; "pudim de passas") →
   Rutherford (folha de ouro; núcleo + eletrosfera) → Bohr (níveis quantizados; emissão de
   fóton) → modelo quântico / Schrödinger (equação de onda, orbital como probabilidade)
2. Partículas subatômicas: próton, nêutron, elétron; carga e massa relativas; por que a massa
   do elétron é desprezada no cálculo de massa atômica
3. Número atômico Z; número de massa A; relação A = Z + N; notação ᴬ_Z X
4. Isótopos (e por que existem: nêutrons blindam a repulsão próton-próton); isóbaros; isótonos
5. Íons: cátion (perdeu elétron) e ânion (ganhou elétron); notação de carga
6. Distribuição eletrônica: níveis K–Q; subníveis s, p, d, f; capacidade de cada subnível
7. **Diagrama de Linus Pauling**: a ordem de energia segue as diagonais, não a ordem geométrica
   das camadas — [Z] marca isso como o erro nº 1 do aluno
8. Números quânticos (n, ℓ, m, s); princípio de Aufbau; regra de Hund; exclusão de Pauli **[I]**
9. O mol como conceito ligado à contagem de átomos **[I]**

### 3.3 Classificação periódica
1. Lei periódica; construção histórica da tabela
2. História e origem dos nomes dos elementos **[I]** *(capítulo longo, ~26 páginas)*
3. Estrutura da tabela: períodos, grupos/famílias, blocos
4. Classificação: metais, ametais, semimetais, gases nobres, hidrogênio à parte;
   representativos × transição × transição interna
5. Famílias nomeadas: alcalinos, alcalinoterrosos, calcogênios, halogênios, gases nobres
6. Propriedades periódicas com **sentido de crescimento na tabela**: raio atômico,
   energia de ionização, afinidade eletrônica, eletronegatividade, caráter metálico,
   densidade, pontos de fusão/ebulição
7. Valência; número de oxidação (NOX); **regras enumeradas para atribuir NOX** **[I]**

### 3.4 Ligações químicas
1. Regra do octeto; estabilidade do gás nobre
2. Ligação iônica (eletrovalente); formação de retículo; propriedades dos compostos iônicos
3. Ligação covalente polar e apolar; estruturas de Lewis; ligação dativa/coordenada
4. Ligação metálica; modelo do mar de elétrons
5. Geometria molecular (VSEPR): linear, angular, trigonal plana, piramidal, tetraédrica **[K]**
6. Polaridade de ligação × polaridade de molécula
7. Forças intermoleculares: dipolo–dipolo, dipolo induzido / London / Van der Waals,
   **ligação de hidrogênio**
8. Ressonância **[I]**
9. Consequência prática: como a ligação e a força intermolecular explicam PF, PE,
   solubilidade e condutividade

### 3.5 Funções inorgânicas e nomenclatura
1. Substâncias simples × compostas; íons monoatômicos e poliatômicos
2. Nomenclatura das substâncias simples
3. **Função óxido**: óxidos metálicos/básicos; óxidos de não metais e de metais de transição;
   óxidos duplos; peróxidos
4. **Função hidróxido** (bases)
5. **Função ácido**: hidrácidos e oxiácidos; nomenclatura; força
6. **Função sal**: neutros, ácidos, básicos, duplos
7. **Função hidreto**: metálicos e especiais
8. Sistemas de nomenclatura: tradicional (hipo-/-oso/-ico/per-), Stock (algarismo romano),
   sistemática IUPAC (prefixos de quantidade)
> [I] organiza toda essa seção como **árvore de decisão**: identifique a função → identifique
> o subtipo → aplique a regra de nome. É o formato mais reaproveitável do lote para
> gerar par pergunta/resposta.

### 3.6 Reações e equações químicas
1. Equação química; reagentes, produtos, estados físicos, coeficiente × índice
2. **Balanceamento por tentativas** (método dos passos numerados) e método algébrico
3. Classificação: síntese/adição (total e parcial), análise/decomposição
   (pirólise/calcinação, fotólise, eletrólise), simples troca/deslocamento, dupla troca
4. Reações exotérmicas × endotérmicas
5. Condições para a reação ocorrer; fila de reatividade dos metais
6. Oxirredução: agente oxidante, agente redutor, semirreações
7. Balanceamento redox: método do NOX e método íon-elétron **[I]**

### 3.7 Estequiometria
1. Leis ponderais: Lavoisier (conservação da massa), Proust (proporções definidas),
   Dalton (proporções múltiplas), Richter (proporções recíprocas)
2. Lei volumétrica de Gay-Lussac
3. Massa atômica; unidade de massa atômica; massa molecular; massa molar
4. **Constante de Avogadro (6,02 × 10²³)**; conceito de mol; volume molar nas CNTP
5. Cálculo estequiométrico: mol↔mol, massa↔massa, massa↔volume, mistos
6. Reagente limitante e reagente em excesso
7. Grau de pureza; rendimento e eficiência da reação

### 3.8 Gases
1. Propriedades do gás ideal/perfeito
2. Teoria cinética dos gases
3. Variáveis de estado: pressão, temperatura, volume
4. Transformação isotérmica; isobárica; isocórica
5. Hipótese de Avogadro–Ampère
6. Lei combinada; equação geral dos gases (PV = nRT)

### 3.9 Sistemas dispersos e soluções
1. Sistemas homogêneos × heterogêneos
2. Classes de dispersão: dispersões grosseiras, coloides, soluções verdadeiras
   (critério: tamanho da partícula dispersa)
3. Soluto e solvente; solubilidade; **coeficiente de solubilidade**; curva de solubilidade
4. Soluções insaturadas, saturadas e supersaturadas
5. Concentração: comum (g/L), molaridade (mol/L), molalidade, título, fração molar, ppm
6. Diluição e mistura de soluções
7. Titulação / volumetria
8. Propriedades das soluções (introdução às coligativas)

### 3.10 Ácidos e bases (aprofundamento)
1. Definição de Arrhenius; de Brønsted–Lowry (par conjugado); de Lewis (par de elétrons)
2. Força de ácidos e bases; constante de acidez; pKa
3. pH e pOH; indicadores; reação de neutralização

### 3.11 Química orgânica

**Nível introdutório (ensino médio — [Z], [K]):**
1. Carbono: tetravalência; capacidade de formar cadeias
2. Classificação de carbonos (primário → quaternário) e de cadeias (aberta/fechada,
   saturada/insaturada, homogênea/heterogênea, normal/ramificada)
3. Funções orgânicas e seus grupos funcionais: hidrocarboneto, haleto, álcool, fenol, enol,
   éter, aldeído, cetona, ácido carboxílico, éster, amina, amida, nitrila, nitrocomposto
4. Nomenclatura IUPAC básica (prefixo de carbonos + infixo de saturação + sufixo de função)
5. Isomeria plana e espacial (noção)

**Nível superior — [W] Wade, vol. 1 (a sequência abaixo É o currículo padrão da disciplina):**
1. **Introdução e revisão** — origens da química orgânica; estrutura atômica; regra do octeto;
   estruturas de Lewis; ligações múltiplas; eletronegatividade e polaridade; cargas formais;
   estruturas iônicas; **ressonância**; fórmulas estruturais; fórmula molecular e empírica;
   ácidos e bases de Arrhenius, Brønsted–Lowry e Lewis
2. **Estrutura e propriedades das moléculas orgânicas** — propriedades ondulatórias do elétron;
   orbitais moleculares; ligação pi; **hibridação e forma molecular**; representação 3D;
   rotação de ligação; isomeria; polaridade; forças intermoleculares; efeito da polaridade
   na solubilidade; panorama dos hidrocarbonetos e dos compostos com O e com N
3. **Alcanos e estereoquímica dos alcanos** — nomenclatura; propriedades; fontes e usos;
   **conformações** (etano, butano); cicloalcanos; isomeria cis-trans em anéis;
   tensão de anel; conformação em cadeira do ciclohexano; mono e dissubstituídos; bicíclicos
4. **Estudo das reações químicas** — cloração do metano; **reação em cadeia por radicais
   livres**; constante de equilíbrio e energia livre; entalpia e entropia; energia de
   dissociação de ligação; cinética e equação de velocidade; energia de ativação; estado de
   transição; halogenação seletiva; postulado de Hammond; intermediários reativos
   (carbocátion, radical, carbânion, carbeno)
5. **Estereoquímica** — quiralidade; nomenclatura R/S; atividade óptica; discriminação
   biológica de enantiômeros; mistura racêmica; excesso enantiomérico; projeções de Fischer;
   diastereômeros; **compostos meso**; configuração absoluta × relativa; resolução
6. **Haletos de alquila: substituição nucleofílica e eliminação** — **SN2, SN1, E1, E2**;
   força do nucleófilo; reatividade do substrato; estereoquímica de cada mecanismo;
   rearranjos; regra de Zaitsev; competição substituição × eliminação
7. **Alquenos — estrutura e síntese** — descrição orbital da dupla; graus de insaturação;
   nomenclatura cis-trans/E-Z; estabilidade; síntese por eliminação e por desidratação
8. **Reações de alquenos** — adição eletrofílica; adição de HX (Markovnikov); hidratação;
   oximercuração-desmercuração; hidroboração; adição de halogênios; halidrinas; hidrogenação
   catalítica; carbenos; epoxidação; abertura de epóxido; hidroxilação sin; clivagem
   oxidativa; polimerização; metátese de olefinas
9. **Alquinos** — nomenclatura; acidez e íon acetileto; síntese; adições; oxidação
10. **Álcoois — estrutura e síntese** — classificação; nomenclatura de álcoois e fenóis;
    propriedades físicas; acidez; **reagentes de Grignard e organometálicos**; redução de
    carbonila; tióis
11. **Reações de álcoois** — estados de oxidação; oxidação (química e biológica); tosilatos;
    redução; reação com HX / PBr₃ / SOCl₂; **desidratação**; reações de dióis (rearranjo
    pinacólico); esterificação; alcóxidos e **síntese de Williamson**
12. **Espectroscopia no infravermelho e espectrometria de massas**
13. **Ressonância magnética nuclear** (¹H e ¹³C): deslocamento químico, número e área dos
    sinais, desdobramento spin-spin, interpretação
14. **Éteres, epóxidos e sulfetos**

**Ausente do PDF** (o índice lista, o arquivo não contém): sistemas conjugados e Diels-Alder;
compostos aromáticos e substituição eletrofílica aromática; cetonas e aldeídos; aminas;
ácidos carboxílicos e derivados; condensações (aldólica, Claisen, Michael); carboidratos e
ácidos nucleicos; aminoácidos, peptídeos e proteínas; lipídios; polímeros sintéticos.

### 3.12 Química aplicada
- Processos químicos industriais **[K, cap. 10]** — único capítulo do lote voltado a aplicação
  industrial sistemática.

---

## 4. Método pedagógico observado

Descrição do que cada autor **faz** ao ensinar, em palavras minhas.

### F1 · RACSO / Aucallanchi — "definição primeiro, avalanche de problema depois"
Abre cada seção com uma definição numerada em hierarquia decimal rígida (1.1.1, 1.1.2, 3.1.4…),
apresenta a equação em versão vetorial e escalar lado a lado, e imediatamente despeja um bloco
enorme de problemas resolvidos, cada um terminando com uma alternativa de múltipla escolha —
o formato de prova de admissão. A proporção teoria:exercício é de ordem 1:5.
**A marca registrada é a escada dupla:** ensina cada grandeza cinemática duas vezes seguidas,
primeiro como razão aritmética média (variação dividida por intervalo) e logo depois como
limite/derivada. O aluno vê a mesma ideia em duas linguagens no mesmo parágrafo — é uma ponte
deliberada do pré-vestibular para o cálculo de engenharia, declarada no prólogo.
Nas resoluções, o padrão é ir do gráfico à álgebra e voltar: identifica que a expressão é uma
parábola, completa o quadrado, localiza o vértice, e só então deriva para confirmar.

### F2 · Ramos Ttito (Macro/SIGNOS) — "teoria mínima, exercício máximo, mira no vestibular"
Estrutura de capítulo absolutamente previsível: introdução curta → teoria enxuta em tópicos
numerados → Problemas Resolvidos → Problemas Propostos. O autor declara o objetivo explícito de
tapar o buraco entre o que o colégio ensina e o que a prova de admissão exige, e afirma que os
problemas espelham provas reais das universidades mais duras. A teoria é deliberadamente curta —
o aprendizado é transferido para o volume de exercícios, não para a exposição.
É também o mais rigoroso do lote em **análise dimensional**: trata a equação dimensional como
ferramenta operacional (verificar se uma fórmula está correta, ou construí-la a partir de dados
experimentais), com as regras algébricas listadas e o princípio da homogeneidade enunciado como
critério de teste. Isso é notável porque é a única parte "simbólica" da física que se ensina e
se verifica inteiramente em texto.

### F3 · Alvarenga & Máximo — o mais sofisticado didaticamente
Padrão de capítulo fixo em dez partes, sempre na mesma ordem: preâmbulo → seções curtas
organizadas em "blocos" cujo título já resume o conteúdo (os autores dizem que ler só os títulos
dá o plano de aula) → conceito-chave isolado numa caixa cinza → exemplo resolvido passo a passo →
**"Un tema especial"** (leitura histórica ou aplicação curiosa: Galileu, Newton, Arquimedes, o
cíclotron, a descoberta do nêutron, a origem do sistema métrico) → repaso, que funciona como
sessão de estudo dirigido → **experimentos simples com material caseiro** → perguntas e
problemas → problemas complementares → questionário → respostas.
Três decisões pedagógicas se destacam: (a) parte do fenômeno cotidiano e do experimento antes
de formalizar, e reduz de propósito a informação específica para destacar a lei geral;
(b) dedica um capítulo inteiro a **funções e gráficos antes da cinemática** — trata leitura de
gráfico como pré-requisito nomeado, não como subproduto; (c) usa a técnica do "erre primeiro":
apresenta a intuição errada (a pena cai mais devagar), mostra o caso do vácuo, e só então enuncia
a conclusão de Galileu com o recorte correto de validade. Também é o único que ensina a 3ª lei
junto com a 1ª, deixando a 2ª para o capítulo seguinte.

### F4 · Pérez García, Vázquez & Fernández-Rañada — não ensina conteúdo, ensina **método**
A introdução codifica um protocolo explícito de quatro fases para resolver qualquer problema:
**(i) compreender** — ler o enunciado, identificar o que se pergunta e quais são os dados, fazer
diagrama, estimar o resultado, **sem calcular nada ainda**; **(ii) formar um plano** — decidir
quais conceitos, leis e equações serão usados; **(iii) calcular** — só agora escrever e resolver;
**(iv) comprovar e interpretar** — comparar com a estimativa da fase (i), checar ordem de
grandeza e dimensões, e se algo não bate, voltar a pensar.
Os autores justificam o protocolo com uma observação empírica: o novato sai calculando na
primeira ideia e para no primeiro resultado; o veterano sabe que a primeira ideia raramente é a
melhor e que nenhum resultado se aceita sem verificar. Cada problema aparece em caixa, com a
resolução separada. Assume mecânica newtoniana completa mais cálculo diferencial, e recomenda
explicitamente que o livro seja usado com um texto teórico ao lado — declara não ser autossuficiente.
**Esse protocolo é o item mais transferível de todo o lote** e não é específico de física.

### Q1 · Zamboni (apostila PT-BR) — coloquial, concreta e com resposta comentada
Fala em segunda pessoa e em tom de conversa ("prezado estudante", "dê uma olhadinha"). Parte
sempre de objetos concretos do dia a dia (gelo seco, água mineral com gás, soro fisiológico,
diamante) e sobe deles para a classificação abstrata — indução, não dedução. Usa caixas de
**"Atenção"** exatamente nos pontos que costumam confundir (o critério real de fenômeno químico
é a mudança de estrutura, mesmo que a reação seja reversível). Explica a *razão* das convenções,
não só a convenção (por que o próton, e não o elétron ou o nêutron, foi escolhido como
identidade do átomo). Fecha cada capítulo com "Explore seu Conhecimento" e, no fim,
**Respostas Comentadas de Todos os Capítulos** — a resposta vem com o raciocínio explicitado,
inclusive marcando cada afirmativa como verdadeira/falsa e dizendo por quê.

### Q2 · Kothe (Química Geral, Fael) — didática de EAD, procedimento em receita
Abre cada capítulo declarando o objetivo e, notavelmente, **o que não será aprofundado** —
delimita o escopo antes de começar. Ancora todo conceito num exemplo do cotidiano concreto e
inesperado (a decomposição do trinitreto de sódio como o mecanismo do airbag; a queima do
magnésio como o flash fotográfico antigo; a eletrólise da água como combustível ainda inviável
por custo energético). Ensina procedimento como **receita numerada**, e depois apresenta uma
segunda regra alternativa para o mesmo procedimento — o balanceamento por tentativas aparece em
duas versões distintas, com exemplos crescendo em dificuldade (metano → alumínio/oxigênio →
hidróxido de alumínio com ácido sulfúrico).
O gabarito é comentado em dois registros separados: **"Resolução:"** (o passo a passo) e
**"Comentário:"** (por que as alternativas erradas estão erradas). Esse formato já é,
estruturalmente, um par instrução/resposta pronto.

### Q3 · Wade (Química Orgánica) — o mais explícito sobre a própria pedagogia
O prefácio ao estudante argumenta a tese central: química orgânica é um punhado de princípios
com muitas extensões, e decorar listas é o caminho errado. O autor conta que tirou nota baixa
numa prova por tentar aplicar à orgânica o método que funcionava na química geral (memorizar uma
equação e improvisar). O livro inteiro é construído para sustentar essa tese, com objetos
didáticos recorrentes e **rotulados na margem**:
- **"Mecanismo Clave"** — os ~20 mecanismos-tronco dos quais tudo o mais deriva (SN2, SN1, E1,
  E2, adição eletrofílica, Grignard, Williamson, Diels-Alder, substituição eletrofílica
  aromática, formação de imina/acetal, esterificação de Fischer, condensação aldólica…)
- **"Mecanismo"** — as variantes e casos particulares, separados dos troncos
- **"Resumen"** — tabelas de consolidação inseridas *no meio* do capítulo, não só no fim
- **"Estrategia para resolver problemas"** — heurísticas nomeadas e reutilizáveis
  ("como propor mecanismos de reação", "síntese em múltiplas etapas", "como reconhecer isômeros
  cis e trans", "como desenhar conformações em cadeira")
- Glosario e Problemas de estudo ao fim de cada capítulo
A ordem é funcional e com dependências fortes: estrutura → reatividade → cada família na ordem
de complexidade crescente, e cada capítulo fecha com um quadro-resumo das reações vistas.
**É o modelo mais próximo de um currículo com grafo de dependências explícito.**

### Q4 · Ruiz-Sánchez et al. (Inorgânica) — taxonômico e baseado em regras
Estrutura de manual: define, classifica, enumera regras, dá exemplos anotados. O número de
oxidação é ensinado como uma lista de regras seguidas de fórmulas com os NOX escritos por cima
de cada elemento. A nomenclatura é organizada como árvore de decisão (função → subtipo → regra
de nome). É o mais pobre em narrativa e o mais dependente de figuras creditadas a terceiros —
várias seções são essencialmente uma legenda em volta de uma imagem externa. Compensa por ser
o mais sistemático em cobertura de nomenclatura inorgânica e por ter licença aberta.

---

## 5. Conceitos que rendem exercício textual

Critério: o Bee **só lê texto**. Um tópico que exige figura, gráfico, diagrama ou notação
bidimensional é inútil. Classificação em três faixas.

### 🟢 VERDE — funcionam 100% em texto puro, resposta curta e verificável

**Química — é aqui que está o ouro. Melhor que física por larga margem.**

| Tipo | Exemplo de par | Por que funciona |
|---|---|---|
| **Nome ↔ fórmula** | "Qual a fórmula do cloreto de sódio?" → NaCl · "Qual o nome oficial da acetona?" → propanona | Mapeamento determinístico string→string. Existem milhares. Verificável por tabela. |
| **Distribuição eletrônica** | "Faça a distribuição eletrônica do potássio (Z = 19)" → 1s² 2s² 2p⁶ 3s² 3p⁶ 4s¹ | Saída é uma **string linear**, gerável e conferível por algoritmo. Não precisa de diagrama. |
| **Contagem de partículas** | "Um átomo tem A = 137 e Z = 56. Quantos nêutrons?" → 81 | Aritmética de uma linha, geração em massa trivial |
| **Cátion/ânion** | "Um átomo perdeu 2 elétrons. Que íon formou e qual a carga?" → cátion, 2+ | Regra pura |
| **Família e período** | "A que família pertence o bromo?" → halogênios, grupo 17, período 4 | Consulta a tabela; resposta única |
| **Tendência periódica** | "O raio atômico cresce em que sentido na tabela?" → da direita para a esquerda e de cima para baixo | Direção verbalizável |
| **NOX** | "Qual o NOX do enxofre em H₂SO₄?" → +6 | Regras enumeradas → aplicação textual |
| **Balanceamento** | "Balanceie: Al + O₂ → Al₂O₃" → 4 Al + 3 O₂ → 2 Al₂O₃ | Entrada e saída são strings curtas; verificável por contagem |
| **Classificação de reação** | "CaO + H₂O → Ca(OH)₂ é de que tipo?" → síntese | Classificação a partir de texto |
| **Classificação da matéria** | "Soro fisiológico é substância pura ou mistura?" → mistura | Todo o cap. 1 de [Z] vira isso direto |
| **Função inorgânica** | "HCl é ácido, base, sal ou óxido?" → ácido (hidrácido) | Classificação pura |
| **Função orgânica pelo grupo** | "Um composto com o grupo –COOH pertence a que função?" → ácido carboxílico | Grupo funcional escrito em linha |
| **Estequiometria 1–2 passos** | "Quantos mols há em 355 g de Cl₂ (M = 71 g/mol)?" → 5 mol | Números redondos, conta cabe na frase |
| **Molaridade / diluição** | "Qual a molaridade de 0,7 mol em 10 L?" → 0,07 mol/L | Idem |
| **Gases, qualitativo** | "Se a pressão dobra a temperatura constante, o que acontece com o volume?" → cai pela metade | Relação verbal |
| **Definição / vocabulário** | isótopo, isóbaro, mol, soluto, catalisador, oxidante, redutor, coeficiente de solubilidade | Definição é texto por natureza |
| **História e atribuição** | "Quem propôs o modelo do pudim de passas?" · "O que o experimento da folha de ouro mostrou?" | Fato puro |

**Física — faixa verde bem mais estreita.**

| Tipo | Exemplo | Observação |
|---|---|---|
| **Distinção conceitual** | "Qual a diferença entre deslocamento e distância percorrida?" · massa × peso · calor × temperatura · escalar × vetorial | O melhor uso da física para o Bee |
| **Distinção com número pequeno** | "Um corpo anda 3 m para leste e depois 4 m para o norte. Distância percorrida? Módulo do deslocamento?" → 7 m e 5 m | Aritmética de cabeça, ilustra o conceito |
| **Enunciado de lei em prosa** | "Enuncie a lei de Lenz" · "O que diz o princípio de Arquimedes?" | Texto puro |
| **Análise dimensional** | "[Força] = ?" → M·L·T⁻² · "v = v₀ + a·t é dimensionalmente homogênea? Justifique." | ⭐ **O melhor item simbólico do lote:** curto, resposta única, verificável, e ensina uma disciplina de verificação |
| **Unidades e prefixos SI** | "Quantos metros em 3,5 km?" · "Escreva 5 972 000 000 000 000 000 000 000 kg em notação científica" | Conversão determinística |
| **Algarismos significativos** | "Quantos algarismos significativos tem 0,0450?" → 3 | Regra pura |
| **Cadeia causal qualitativa** | "Por que pena e pedra caem juntas no vácuo mas não no ar?" · "Por que a temperatura fica constante durante a fusão de uma substância pura?" · "O MCU tem aceleração? Por quê?" | Ensina raciocínio, não número |
| **Problema numérico de 1–2 passos** | queda livre com g = 10; Q = m·c·ΔT; V = R·i; dilatação linear | Só se os números forem redondos e o enunciado couber em prosa |
| **Protocolo de resolução** | as 4 fases de [P] (compreender → planejar → calcular → conferir) | Transferível para além da física |

### 🔴 VERMELHO — inúteis para o Bee (dependem de figura ou notação 2D)

- **Tudo que começa com "observe o gráfico/a figura/a tabela abaixo".** Isso apaga o capítulo 2
  inteiro do Alvarenga (funções e gráficos), boa parte da cinemática (x–t, v–t, a–t) e as curvas
  de aquecimento e de solubilidade da química.
- **Diagramas de corpo livre**, plano inclinado, sistemas de polias, decomposição de forças em
  geometria — nesses problemas a figura *é* o enunciado.
- **Óptica geométrica** por traçado de raios (espelhos e lentes) — sem diagrama não há problema.
- **Circuitos elétricos com esquema.** Sobrevive só o que puder ser descrito em palavras
  ("três resistores de 6 Ω em paralelo").
- **Química orgânica estrutural — o coração do Wade e quase todo pictórico:** mecanismos com
  setas curvas, conformações em cadeira, projeções de Fischer, atribuição R/S, geometria VSEPR,
  estruturas de ressonância desenhadas, estereoquímica em geral.
- **Espectroscopia (IV, RMN, massas):** interpretar espectro é ler figura. Sobrevivem apenas as
  *tabelas de referência* como fatos isolados ("o próton de aldeído aparece em δ ≈ 9–10").
- **Álgebra multilinha, derivada e integral simbólicas, tensor de inércia, lagrangiana** — o
  Pérez García inteiro. Um modelo de 151M não vai executar isso e, pior, vai produzir uma
  sequência com *aparência* de solução e conteúdo errado. Esse é o modo de falha mais perigoso.
- **Diagrama de Linus Pauling como diagrama** (as setas diagonais). Mas a distribuição
  eletrônica resultante, como string, é verde — separe os dois.

### 🟡 AMARELO — só com reescrita, e o custo nem sempre compensa

- **Fórmulas simples** podem ir em linha (`v = v0 + a*t`, `PV = nRT`, `Q = m*c*ΔT`), mas cada
  fórmula que entra no corpus é uma sequência de símbolos que o modelo vai imitar sem entender.
  **Recomendação: usar fórmula com parcimônia e sempre acompanhada da versão em palavras**
  ("a velocidade final é a inicial mais a aceleração vezes o tempo").
- **Curva de aquecimento** pode virar tabela textual ("a 0 °C a temperatura permaneceu constante
  durante toda a fusão") — [Z] já faz isso parcialmente nas respostas comentadas.
- **Plano inclinado e polias** podem ser descritos em prosa, mas o esforço de reescrita é alto e
  o retorno didático é baixo. Deixar para depois.

---

## 6. Veredito

**Vale — mas só a química, só o esqueleto, e só se escrevermos tudo do zero em PT-BR.**
Nenhuma linha desses 8 livros pode entrar no corpus: 7 são obras protegidas com aviso explícito
e o único com licença aberta (a Inorgânica equatoriana, CC BY-NC-SA 4.0) é NC + SA, ou seja,
contamina a licença do que produzirmos e ainda por cima é o mais fraco do lote. O que se
aproveita de verdade é o que está neste documento: a **sequência de tópicos com suas
dependências** e o **aparato pedagógico**, que são fatos e ideias, não expressão protegida.
Dito isso, a física é um mau encaixe para o Bee e é honesto dizer isso agora: ensinar física
depende de gráfico, diagrama de corpo livre, traçado de raio e esquema de circuito — retire tudo
isso e sobra recall de definição mais substituição numérica de um passo, exatamente o tipo de
material que um modelo de 151M aprende a imitar na superfície (produz uma string com formato de
solução e número errado). Já sabemos do Gate 2 que mais token não conserta bpb; despejar prosa
de física com contas que ele não sabe fazer tende a **piorar** a alucinação, não a corrigi-la.
A química, ao contrário, é feita sob medida: nomenclatura nome↔fórmula, classificação de matéria
e de funções, distribuição eletrônica como string, contagem A/Z/N, NOX, balanceamento e
estequiometria de um passo são pares curtos, determinísticos, verificáveis por programa e
geráveis aos milhões — e ensinam ao Bee exatamente o que falta nele, que é ancorar uma sequência
específica de tokens noutra sequência específica. O item de maior valor, porém, nem é conteúdo:
é o **formato**. O gabarito comentado do Kothe e da Zamboni ("Resolução:" passo a passo +
"Comentário:" explicando por que as outras alternativas estão erradas) já é estruturalmente um
par instrução/resposta; o andaime do Wade (mecanismo-tronco → variantes → resumo consolidado →
heurística nomeada) é o melhor molde de currículo com dependências que eu vi neste lote; e o
protocolo de 4 fases do Pérez García é um ativo transferível para qualquer domínio.
**Se houvesse tempo para uma coisa só:** Zamboni (63 p.) e Kothe (305 p.) — são os dois únicos
em PT-BR nativo, com texto digital limpo e gabarito comentado. Os dois monstros espanhóis
escaneados (RACSO, 1035 p.; Alvarenga, 1242 p.) têm a camada de fórmula destruída pelo OCR e
qualquer número extraído deles precisa de conferência humana; não compensam o esforço.
E um alerta sobre idioma: seis dos oito estão em espanhol, o que é uma armadilha sutil — o
esqueleto de tópicos atravessa a fronteira sem custo, mas qualquer frase traduzida arrasta
sintaxe espanhola e falso cognato para dentro de um modelo que estamos treinando em português.
**Escrever a partir do esqueleto, nunca traduzir.**
