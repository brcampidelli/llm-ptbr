# 08 — Português ATUAL: norma vigente, uso real e recursos licenciáveis

**Data:** 2026-08-04 · **Alvo:** Bee (151M params, PT-BR nativo) · **Método:** pesquisa web com verificação de fonte; 2 agentes paralelos (norma×uso; neologismos+linguagem neutra)
**Complementa (não repete):** [`estudo-gramatica-dados-sinteticos-2026-08-03.md`](../estudo-gramatica-dados-sinteticos-2026-08-03.md) · [`04-portugues-logica-humanas.md`](04-portugues-logica-humanas.md)

> **Divisão de trabalho entre os três documentos.** O de **03/08** mapeou 9 gramáticas protegidas e concluiu que o ROI está em pares "errado→certo". O **04** fechou o catálogo em **58 verbetes → 13 classes**, achou o esquema de 4 campos e o **Molde C (cloze de banca)**, e entregou o gerador determinístico de lógica. **Este documento (08) responde a outra pergunta: o que é ATUAL e o que é LICENCIÁVEL.** Ou seja: 03/08 e 04 definiram *o que ensinar*; este define *com que norma* e *com que dado que se pode publicar*.

> ⚠️ **Regra deste documento:** toda afirmação normativa traz fonte. O que não foi confirmado está marcado **[NÃO CONFIRMADO]**. Erro de norma injetado num modelo de português é o pior defeito possível neste projeto — na dúvida, o documento diz que não sabe.

---

## 1. Norma vigente em 2026

### 1.1 Acordo Ortográfico de 1990 — situação real

| Fato | Status | Fonte |
|---|---|---|
| Assinado em 1990 por Angola, Brasil, Cabo Verde, Guiné-Bissau, Moçambique, Portugal, São Tomé e Príncipe; Timor-Leste aderiu em 2004 | confirmado | [Wikipédia — AO90](https://pt.wikipedia.org/wiki/Acordo_Ortogr%C3%A1fico_de_1990) |
| **Brasil: período de transição 01/01/2009 → 31/12/2015; obrigatório desde 01/01/2016** | confirmado | [Decreto 7.875/2012 (Planalto)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/decreto/d7875.htm) · [Senado](https://www12.senado.leg.br/noticias/materias/2012/12/28/adiamento-da-vigencia-do-acordo-ortografico-teve-apoio-de-senadores) |
| Portugal: aplicação obrigatória no Estado desde 01/01/2012 (RCM 8/2011) | confirmado | [Wikipédia — AO90](https://pt.wikipedia.org/wiki/Acordo_Ortogr%C3%A1fico_de_1990) |
| Angola é o único país da CPLP cujo governo **não aprovou** o Acordo | confirmado | [Observatório da Língua Portuguesa](https://observalinguaportuguesa.org/acordo-ortografico-ainda-continua-a-ser-implementado-a-varios-ritmos-nos-paises-lusofonos/) |
| Moçambique, Guiné-Bissau, Cabo Verde, S. Tomé, Timor: ratificaram mas aplicam em ritmos diferentes / incompletos | confirmado | idem |
| Contestação política **em Portugal** (petições, grupo de trabalho parlamentar, ação no Supremo Tribunal Administrativo; AP-CPLP pediu retificações em abr/2024) | confirmado até 2024 | [Observador, 17/04/2024](https://observador.pt/2024/04/17/parlamentares-da-cplp-querem-retificacoes-ao-acordo-ortografico/) · [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/atualidades/noticias/parlamento-reve-desacordo-ortografico/3323) |
| Alguma revogação/alteração do AO90 em 2025–2026 | **[NÃO CONFIRMADO]** — não encontrei notícia de mudança nesse período | — |

**Leitura para o Bee:** do ponto de vista brasileiro **a norma está estabilizada há uma década**. A polêmica é portuguesa e política, não afeta a grafia que o Bee deve produzir. **Decisão simples e segura: o Bee escreve na ortografia pós-AO90, variante brasileira.** Isso também significa que **todo texto brasileiro anterior a ~2009 no corpus está numa ortografia obsoleta** (trema, `idéia`, `pára`) — é um risco de contaminação real, tratado na §5.4.

### 1.2 O que efetivamente mudou (aplicável ao Brasil)

Fonte primária: texto do Acordo ([PDF Priberam](https://www.priberam.pt/docs/AcOrtog90.pdf)); sistematização: [Wikipédia — AO90](https://pt.wikipedia.org/wiki/Acordo_Ortogr%C3%A1fico_de_1990).

| Área | Regra nova | Exemplos |
|---|---|---|
| **Alfabeto** (Base I) | reintroduzidas `k`, `w`, `y` (uso restrito: estrangeirismos, siglas, unidades) | `km`, `watt`, `byte` |
| **Trema** (Base XIV) | **abolido** em palavras portuguesas e aportuguesadas; sobrevive só em derivados de nomes próprios estrangeiros | `freqüência`→`frequência`, `lingüiça`→`linguiça`; mantém-se `mülleriano` |
| **Acento em ditongos abertos `éi`/`ói`** (Base IX) | cai **nas paroxítonas** | `idéia`→`ideia`, `assembléia`→`assembleia`, `jóia`→`joia`. ⚠️ **Nas oxítonas continua**: `herói`, `papéis`, `troféu` |
| **Hiatos `oo`/`ee`** | acento circunflexo abolido | `vôo`→`voo`, `abençôo`→`abençoo`, `lêem`→`leem`, `crêem`→`creem` |
| **Acentos diferenciais** | **abolidos** em `para` (v. parar), `pelo` (subst.), `polo`, `pera` | `pára`→`para`, `pêlo`→`pelo`, `pólo`→`polo` |
| **Acentos diferenciais MANTIDOS** | `pôr` (v.) × `por` (prep.); `pôde` (pret.) × `pode` (pres.) | obrigatórios |
| **Facultativos** | `fôrma` × `forma`; `dêmos` × `demos` | `fôrma` tem uso real no Brasil; `dêmos` é forma do conjuntivo europeu, **irrelevante no PT-BR** |
| **Hífen** (Bases XV–XVII) | prefixo + **mesma vogal** → com hífen | `anti-inflamatório`, `micro-ondas`, `contra-ataque` |
| | prefixo + **h** → com hífen | `anti-higiênico`, `super-homem` |
| | prefixo terminado em vogal + **vogal diferente** → junto | `antiaéreo`, `autoestrada`, `aeroespacial` |
| | prefixo terminado em vogal + **`r`/`s`** → junto, **duplicando** a consoante | `antirreligioso`, `microssistema`, `ultrassom` |
| | locuções verbais | `há-de` → `há de` |
| **Não mudou** | consoantes mudas (afetavam só PT-PT); dupla acentuação de timbre | `acadêmico` (BR) × `académico` (PT) — **ambas corretas**, cada uma na sua variante |

Impacto quantitativo declarado: **~0,8% das palavras** foram afetadas no Brasil ([Wikipédia — AO90](https://pt.wikipedia.org/wiki/Acordo_Ortogr%C3%A1fico_de_1990)).

**As pegadinhas que continuam derrubando gente** (e que um modelo erra por analogia falsa):
1. `ideia` sem acento **mas** `herói` com acento (paroxítona × oxítona).
2. `anti-inflamatório` **com** hífen **mas** `antirreligioso` **sem** (vogal igual × consoante).
3. `pôde`/`pode` e `pôr`/`por` sobreviveram — quem "aprendeu que acento diferencial acabou" erra os dois.
4. `micro-ondas` com hífen **mas** `microssistema` sem.
5. Trema zerado, mas ainda aparece muito em texto antigo reciclado na web.

### 1.3 VOLP — o vocabulário oficial

| Fato | Status | Fonte |
|---|---|---|
| Edição vigente: **6.ª edição**, lançada em **julho de 2021**, **exclusivamente digital** (site da ABL + app oficial) | confirmado | [Agência Brasil, 07/2021](https://agenciabrasil.ebc.com.br/geral/noticia/2021-07/academia-brasileira-de-letras-lanca-nova-edicao-online-do-volp) |
| **~1.000 palavras novas** em relação à 5.ª ed. | confirmado | [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/atualidades/noticias/mais-mil-palavras-no-vocabulario-ortografico-da-lingua-portuguesa/3581) |
| Nº total de verbetes: **370 mil** (Agência Brasil, declaração de Bechara) **× 382 mil** (fontes secundárias) | ⚠️ **divergente — [NÃO CONFIRMADO qual está certo]** | [Agência Brasil 10/06/2021](https://agenciabrasil.ebc.com.br/educacao/noticia/2021-06/abl-finaliza-6a-edicao-do-vocabulario-ortografico-da-lingua-portuguesa) |
| Critério de inclusão declarado: *"o da sua frequência entre os falantes"*; o VOLP é *"documentação das palavras utilizadas numa época específica"* (Bechara) | confirmado | Ciberdúvidas 28/09/2021 |
| Palavras incorporadas citadas na imprensa: `ciclofaixa`, `covid-19`, `criptomoeda`, `feminicídio`, `homoparental`, `pós-verdade`, `telemedicina` | confirmado | idem |
| Inclui também Vocabulário de Estrangeirismos e Vocabulário de Topônimos e Gentílicos; acrescentou ortoépia e plurais alternativos, e registro mais amplo de nomes de povos indígenas | confirmado | [ABL/app](https://play.google.com/store/apps/details?id=br.org.academia.volp2) · Agência Brasil |
| 7.ª edição ou atualização posterior a 2021 | **[NÃO CONFIRMADO]** | — |
| **Licença aberta / download em massa / API pública do VOLP** | **[NÃO CONFIRMADO — presumir que NÃO existe]**. O acesso é consulta web e app; não localizei termos que autorizem redistribuição da base | ver §5.3 |

> ⚠️ O site da ABL (`academia.org.br`) **bloqueia** acesso automatizado (HTTP 403). Os números acima vêm de imprensa e do Ciberdúvidas, não da página oficial. Confiança alta (múltiplas fontes concordam), mas **não é fonte primária**.

### 1.4 O fato normativo NOVO de 2025 (e o mais fácil de passar batido)

**Lei nº 15.263, de 14/11/2025 — Política Nacional de Linguagem Simples.** Vale para a administração pública direta e indireta de **todos os Poderes**, da União, dos Estados, do DF e dos Municípios. É a mudança normativa mais recente que afeta o português escrito no Brasil, e **quase toda ela é sobre clareza, não sobre gênero**: dos 18 incisos do art. 5º, 17 são técnicas de linguagem simples (ordem direta, frases curtas, voz ativa, evitar estrangeirismos, testar a compreensão com o público). O inciso XI é o que trata de flexão de gênero — tratado na **§4**, porque lá é onde a disputa está.

⭐ **Por que isto importa para o Bee mais do que parece:** os 17 incisos "chatos" são, na prática, **uma especificação oficial e pública do registro formal brasileiro contemporâneo** — o alvo estilístico mais provável do modelo (§8). Junto com o **Manual de Redação da Presidência da República** (3.ª ed., 2018), é a descrição escrita de "como o Estado brasileiro quer que se escreva em 2026". Isso é mais útil, mais atual e mais licenciável que qualquer gramática de concurso.

**Vocabulário Ortográfico Comum (VOC) da CPLP** — instrumento pan-lusófono do IILP, adotado como oficial da CPLP na Cimeira de Díli (2014), disponibilizado em maio de 2017 com os vocabulários nacionais de Brasil, Cabo Verde, Moçambique, Portugal e Timor-Leste; roda sobre a plataforma OSLIN em `voc.iilp.cplp.org` ([Instituto Camões](https://www.instituto-camoes.pt/sobre/comunicacao/noticias/apresentada-plataforma-do-voc) · [Observatório da Língua Portuguesa](https://observalinguaportuguesa.org/vocabulario-ortografico-comum-voc-disponivel-para-consulta-publica/)). **Licença do VOC: [NÃO CONFIRMADO]** — há inclusive uma *issue* aberta num repositório de datasets linguísticos justamente perguntando isso ([EticaAI issue #3](https://github.com/EticaAI/linguistic-datasets-portuguese/issues/3)), o que sugere que não é trivialmente licenciável.

---

## 2. Norma × uso real

### 2.0 Antes da tabela: "português correto" são TRÊS coisas, não uma

A linguística brasileira distingue formalmente:

| Conceito | O que é |
|---|---|
| **norma-padrão** | O ideal codificado nas gramáticas tradicionais, historicamente calcado no português literário luso-clássico do séc. XIX. Segundo **Faraco (2002, p. 40)**, existe para *"neutralizar a variação e controlar a mudança"* |
| **norma culta** | O uso **real** do brasileiro urbano escolarizado. **Bagno**: *"a linguagem concretamente empregada pelos cidadãos que pertencem aos segmentos mais favorecidos da nossa população. Esta é a noção de norma culta que vem sendo empregada em diversos empreendimentos científicos como, por exemplo, o Projeto NURC"* — e alerta: *"existe uma diferença muito grande entre o que as pessoas em geral chamam de norma culta… e o que os pesquisadores profissionais chamam de norma culta, um termo técnico para designar formas linguísticas que existem na realidade social"* ([Bagno, *Traduzires*/UnB, 2012](https://repositorio.unb.br/bitstream/10482/10546/1/ARTIGO_NormaLinguisticaHibridismo.pdf)) |
| **normas populares** | Variedades de menor prestígio social |

**Base empírica:** o **Projeto NURC** documenta desde ~1970 a fala culta de Recife, Salvador, Rio, São Paulo e Porto Alegre, com informantes de *"escolaridade superior completa e antecedentes biográfico-culturais urbanos"*, em três faixas etárias ([NURC-RJ/UFRJ](https://nurcrj.letras.ufrj.br/historico.htm)).

⭐ **Isto é a resposta à pergunta "que português o Bee deve falar?".** Não é "o certo" — é **escolher entre três alvos distintos**, e o alvo defensável é a **norma culta escrita**, não a norma-padrão de concurso.

> ⚠️ **ALERTA DE CORPUS descoberto nesta pesquisa:** a cópia acessível do **Manual de Redação e Estilo do Estadão** — a fonte mais rica desta seção — é **anterior ao Acordo Ortográfico**: ela ainda prescreve trema (*"Tranqüilo, conseqüência, lingüiça, agüentar"*) e grafa *"idéias"*, *"cinqüenta"*, *"mão-de-obra"*, *"infra-estrutura"*. **A orientação de sintaxe/regência/colocação continua representativa; a ortografia está morta desde 2016.** Manuais de redação antigos circulam muito em PDF na web — é um vetor concreto de contaminação ortográfica (§5.4).

### 2.1 Tabela principal — norma × uso × registro

Registros: **FI** fala informal · **EI** escrita informal (WhatsApp/rede) · **JOR** jornalismo · **ACAD** escrita formal-acadêmica · **CONC** concurso/vestibular.

| Fenômeno | (a) Norma-padrão prescreve | (b) Uso real registrado | (c) Registro | Fonte |
|---|---|---|---|---|
| **Próclise inicial** ("Me empresta") | Proibida. Estadão: *"Não se inicia período com pronome oblíquo. Admite-se essa forma apenas na linguagem coloquial ou nas declarações colocadas entre aspas"* | Próclise é a posição **preferida** no PB. O próprio manual admite que a ênclise é regra *"por ser a norma da língua, **embora o português do Brasil tenha a tendência oposta**"*. Vieira & Corrêa: *"clítico anteposto constitui preferência na fala brasileira"* | FI, EI ✔ · JOR só entre aspas · ACAD/CONC ✘ | [Manual Estadão](https://www.fmetropolitana.com.br/wp-content/uploads/2019/01/MANUAL-REDA%C3%87%C3%83O-ESTAD%C3%83O.pdf) · [Vieira & Corrêa, *Letras de Hoje*, 2017](https://www.scielo.br/j/lh/a/MRz3KQHsKSv6MTxNMFZ8XsS/) |
| **Pronome entre dois verbos** ("estava se preparando") | Tradição exige hífen no auxiliar ("estava-se preparando") | ⭐ **Concessão explícita e nomeada do jornalismo:** *"O Estado aceita o uso, no noticiário, do pronome oblíquo colocado entre dois verbos, sem necessidade de se ligar por hífen… **Trata-se de uma característica do português do Brasil que não é mais possível desprezar**"* | FI, EI, **JOR ✔** · ACAD tolerado · CONC depende da banca | Manual Estadão |
| **Mesóclise** ("dir-se-ia") | Obrigatória em futuro/futuro do pretérito sem palavra atrativa; *"Em nenhuma hipótese pode ocorrer «diria-se»"* | O próprio manual manda **evitar**: *"Por estarem hoje mais ligadas à linguagem erudita, convém, no entanto, sempre que possível, evitar essas formas"* | FI/EI praticamente inexistente · JOR evita por recomendação · ACAD/CONC sobrevive como regra | Manual Estadão. ⚠️ **[NÃO CONFIRMADO]** estudo de corpus medindo frequência ~zero na fala |
| **Objeto direto de 3ª pessoa** ("Eu vi ele" / "Eu vi") | Clítico obrigatório: *"Eu, tu, ele… não podem ser objeto direto. Assim: Comprei-o"* | **Clítico em colapso.** Em HQs cai de **52,5% (1970) para 12,1% (2000)**; na fala de Vitória o clítico *"quase desapareceu"*, restando **objeto nulo** e **pronome pleno** | "Vi ele": FI, EI ✔ · JOR ✘ · ACAD/CONC exigem clítico. ⭐ **O objeto nulo** ("Viu o filme?" / "Vi.") **é o mais neutro — passa em quase todos os registros** | [Zanellato et al., *Diadorim*, 2021](https://revistas.ufrj.br/index.php/diadorim/article/view/39476) ⚠️ percentuais vindos de resumo processado — **tratar como ordem de grandeza** |
| **"Ter" existencial** ("tem muita gente") | Condenado: *"Haver é que significa existir, e não ter. Use: Há muita gente lá"* | Mudança **antiga e consolidada**: *"the use of ter-existential increases gradually through time and its origin dates back to the sixteenth century"* (dados séc. XIII-XX + NURC-RJ) | "tem": FI, EI ✔ (categórico na fala) · JOR/ACAD/CONC usam "há/existe" | [Callou & Avelar, *Gragoatá*, 2000](https://periodicos.uff.br/gragoata/article/view/49038) |
| **"A gente"** | Verbo em 3ª pessoa do singular | Plenamente da **norma culta**: no NURC-RJ, **59% "a gente"**; Porto Alegre 72% e Salvador 63% de "nós"; jovens 25-35 preferem "a gente", 56+ preferem "nós" | "a gente vai": **todos os registros de fala, inclusive culta** ✔ · ACAD escrito prefere "nós" · "a gente vamos": só FI popular (⚠️ **[NÃO CONFIRMADO]** quantitativamente) | [Lopes, *DELTA*, 1998](https://www.scielo.br/j/delta/a/KQmrjr5yGgL49JPWMSGGhSj/?lang=pt) |
| **Futuro sintético × perifrástico** | Ambos corretos | Perífrase **dominante**: *"a construção do futuro pelo uso da perífrase apresentou um percentual maior de preferência em todos os contextos analisados"*; o sintético sobrevive **por efeito de escolarização** | "vou fazer": FI, EI, JOR ✔ · "farei": ACAD, JOR formal, jurídico · ambos aceitos em CONC | [Gravina & Brizola, *RELIN*/UFMG, 2019](https://periodicos.ufmg.br/index.php/relin/article/view/27665) |
| **"Cujo"** | Relativo possessivo pleno | ⭐ **Morto na fala, vivo na escrita:** *"O relativo cujo inexiste no português brasileiro falado, bem como nos dados do português europeu que analisamos."* Estratégia real: "que" + retomada | ✘ FI · raro EI · ✔ JOR, ACAD, CONC | [Kersch, *DELTA*, 2008](https://www.scielo.br/j/delta/a/MpSzkr9PZrNYjwdZdGzmDbt/?format=html&lang=pt) |
| **"Onde" genérico** | *"Onde só pode ser usado para lugar… Nos demais casos, use em que"* | "Onde" como relativo genérico é fato documentado e *"censurado pela tradição gramatical"*; há precedente literário até com verbo de movimento (Garrett: *"Onde ia ele?"*) | FI, EI, **e frequente em escrita burocrática/jurídica** · ✘ CONC e ACAD estrita | Manual Estadão · [*Veredas do Direito*](https://revista.domhelder.edu.br/index.php/veredas/article/view/7347) · [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/consultorio/perguntas/aonde-vs-onde-ii/35701) |
| **Concordância nominal variável** ("os menino") | Plural em todos os elementos | Variável e **fortemente estruturada**, não aleatória. Dois princípios: **saliência fônica** (*"formas mais salientes… são mais perceptíveis e, portanto, mais prováveis de serem marcadas no plural"*) e **paralelismo formal** (*"a tendência de formas semelhantes co-ocorrerem"*). Ligada a anos de escolarização | Fala popular; **fortemente estigmatizado**. Ausente de JOR/ACAD/CONC | [Scherre, *Scripta*/PUC Minas](http://periodicos.pucminas.br/index.php/scripta/article/view/12597) · [*DELTA* 2018](https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-44502018000200513) |
| **Sujeito posposto** ("chegou os convidados") | Verbo concorda em qualquer posição; *"Alugam-se casas"* | "Sujeito posposto ao verbo" está **entre os fatores que desfavorecem a marca de plural**; no conjunto do estudo, 724 de 832 ocorrências (**87%**) trouxeram a marca | Não-concordância: FI · demais ✘. Mas "aluga-se casas" é quase categórico na fala e comum em placa/anúncio | [*Web-Revista Sociodialeto*/UEMS](https://periodicosonline.uems.br/sociodialeto/article/view/8139) |
| **"Fazem X anos" / "houveram"** | Impessoais, invariáveis. São os erros **nº 2 e nº 3** da lista dos "cem erros mais comuns" do Estadão | Frequentes o bastante para o jornal listá-los no topo. "Houveram" é **hipercorreção**; na fala o falante costuma dizer "teve muitos problemas" (e cai no caso do "ter" existencial) | FI, EI · JOR/ACAD/CONC ✘ | Manual Estadão · [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/pelourinho/havia-varias-pessoas-e-nao-houveram-varias-pessoas/3244) |
| **Pretérito perfeito composto** ("tenho feito") | — | ⚠️ **A premissa comum está errada.** O PPC tem valor **iterativo/durativo**, não pontual: *"no português moderno, o PPC recebe uma leitura iterativa"*. "Tenho feito" ≠ *I have done*, e sim "venho fazendo repetidamente". Quanto a PB × PE: Barbosa (2008) *"retrata alguns aspectos da variação entre PE e PB, **mas não significativos**"* | Todos os registros, **com o mesmo valor**. O contraste real é com inglês/espanhol/francês, **não** entre PB e PE | [Bittencourt, *Working Papers em Linguística*/UFSC, 2021](https://periodicos.ufsc.br/index.php/workingpapers/article/download/76855/47306/308469) |
| **"Tu" sem concordância** ("tu vai") | "Tu" exige 2ª pessoa ("tu vais") | A distinção **"tu com concordância" × "tu sem concordância"** é categoria consolidada da área, com mapeamento regional publicado | "tu vai": FI regional ✔ · demais ✘ | [Scherre, Andrade & Catão, *Revista de Letras*/UFC, 2021](https://periodicos.ufc.br/revletras/article/view/71460) ⚠️ **[NÃO CONFIRMADOS]** os percentuais, os subsistemas regionais e o mapa "RS = tu / SP = você" |
| **Gerundismo** ("vou estar enviando") | Estigmatizado no discurso metalinguístico; o manual do Estadão **não tem verbete específico** (só *"Evite o gerúndio nos títulos"*) | ⚠️ **Disputado entre linguistas.** **Sírio Possenti** refuta a tese do anglicismo: perífrases análogas ("vou ficar esperando") não são criticadas, e invoca a NGB (1959) e Cunha & Cintra para mostrar que a perífrase é legítima. O Ciberdúvidas registra o anglicismo **como hipótese**: *"Atribui-se a proliferação…"* | FI, EI · evitado em JOR/ACAD por **decisão de estilo, não por regra gramatical** | [Possenti/Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/portugues.php?rid=1990) · [Ciberdúvidas 1904](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/idioma/sobre-a-proliferacao-do-gerundio-no-portugues-do-brasil/1904) |
| **Crase** | Regra clássica | Confirmei apenas **casos de dupla possibilidade admitidos pela própria norma** (antes de "outra"; com possessivo de valor indefinido). É fenômeno **de escrita**: a crase não tem correlato fônico no PB | Escrita, todos os níveis | [Ciberdúvidas 27958](https://ciberduvidas.iscte-iul.pt/consultorio/perguntas/sobre-a-ocorrencia-de-crase/27958) ⚠️ **[NÃO CONFIRMADO]** estudo de corpus quantificando erro real de crase |

### 2.2 ⚠️ Regência: as autoridades normativas DISCORDAM ENTRE SI

Isto é o achado mais desconfortável da seção, e tem consequência direta: **alguns "erros" do catálogo de 58 verbetes não são erro — são disputa entre normativistas.**

| Verbo | Norma tradicional (Estadão) | O que outra autoridade normativa admite | Veredito |
|---|---|---|---|
| **assistir** (=ver) | *"exige sempre a preposição a"* — erro nº 11 | Ciberdúvidas, **citando o Houaiss**: *"No português do Brasil, é comum o uso, **mesmo pelas pessoas cultas e na literatura**, deste verbo como transitivo direto."* Faraco propõe aceitar como padrão *"assistir, aspirar, obedecer como transitivos diretos"* | "assistir o jogo" cai em prova, mas **não é ignorância** |
| **namorar** | ⚠️ *"Queria namorar «com» o colega. **O com não existe**"* — erro nº 47 | Ciberdúvidas: *"O verbo namorar tanto pode ser utilizado com regência da preposição com como sem ela"*, por analogia com "casar com"/"noivar com" | 🔴 **Conflito direto entre autoridades. NÃO usar como par errado→certo** |
| **visar** | "visar a" (=ter por objetivo) | Ciberdúvidas trata **as duas como corretas**: *"pode ser empregado com ou sem preposição"* | 🔴 **Não usar como par** |
| **chegar** | *"Verbos de movimento exigem a"* — erro nº 20 | Ciberdúvidas (descritivo): *"no português falado no Brasil, a preposição que preferencialmente acompanha o verbo chegar é **em**"* | Par válido **para registro escrito formal**, não para fala |
| **preferir** | *"Prefere-se sempre uma coisa a outra"* — erro nº 12 | *"Tendemos a empregar o verbo preferir em construções como «preferir antes…» ou «preferir mais do que…»"* | Par válido para escrita formal |
| **favorecer** | *"Favoreceu «ao» time da casa. Favorecer, nesse sentido, **rejeita a**"* — erro nº 67 | — | ⭐ Aqui o **erro é a hipercorreção** — inverso dos demais, ótimo par contrastivo |
| **ir** ("fui na festa") | "ir a" | **[NÃO CONFIRMADO]** — nenhuma fonte descritiva aberta encontrada | Não usar sem confirmar |

### 2.3 Outros fenômenos frequentes (da lista "cem erros mais comuns" do Estadão)

Essa lista é, na prática, **um inventário empírico do que brasileiros escrevem e a norma rejeita** — útil exatamente por isso.

| Fenômeno | Norma | Onde ocorre |
|---|---|---|
| "Para **mim** fazer" (nº 5) | *"Mim não faz, porque não pode ser sujeito"* | FI, EI |
| "Entre **eu** e você" (nº 6) | *"Depois de preposição, usa-se mim ou ti"* | FI, EI |
| "**Há** dez anos **atrás**" (nº 7) | Redundância | FI, EI — **e escapa até em JOR** |
| "**Aluga-se** casas" (nº 18) | *"Alugam-se casas"* | quase categórico na fala; comum em anúncio |
| "**Tratam-se** de" (nº 19) | *"Trata-se dos melhores profissionais"* | FI, EI — **e hipercorreção em ACAD** |
| "Não viu **qualquer** risco" (nº 28) | *"É nenhum… que se emprega depois de negativas"* | ⭐ **JOR e ACAD — é um "erro culto"** |
| "Ele foi um dos que **chegou**" (nº 41) | Concordância no plural | FI, EI, JOR |
| "**o mesmo**" como pronome (nº 69) | *"Não se pode empregar o mesmo no lugar de pronome"* | escrita burocrática/jurídica |
| "Por causa que" (nº 56) | *"Embora popular, a locução não existe. Use porque"* | FI |
| **Dupla negação** ("não tenho não" / "tenho não") | Não tratada como padrão | Descrita academicamente como **ciclo de Jespersen** no PB ([Barme, *ZrP*, 2005](https://dialnet.unirioja.es/servlet/articulo?codigo=3420731)). FI, EI |
| "**menas**" | Invariável ("menos") | FI popular — ⚠️ fonte **fraca** (não acadêmica) |

### 2.4 O que Faraco propõe que a norma-padrão CONCEDA

Citação com página, via fonte secundária (⚠️ **o original de Faraco 2008 não foi aberto**): a norma-padrão deveria *"abolir as regras de colocação de pronomes, aceitar como padrão a variedade de regências de certos verbos corriqueiras na norma culta (por exemplo: assistir, aspirar, obedecer como transitivos diretos), institucionalizar a concordância variável em construções com a palavra se, reconhecer a variação sintática dos pronomes pessoais… admitir a concordância verbal variável em orações com verbo à esquerda do sujeito…"*

**Como o jornalismo se comporta de fato — e este é o achado mais operacional da seção:** o Estadão **não** adere à norma culta real de forma sistemática. Ele faz **concessões pontuais e nomeadas** (pronome entre dois verbos; evitar mesóclise) e **mantém a norma tradicional** em outros pontos (assistir a, chegar a, próclise inicial proibida, "alugam-se casas"). **É seletivo, não coerente.** Ou seja: nem existe um "português jornalístico" internamente consistente que se possa copiar como alvo — o alvo tem que ser **definido**, item a item.

### 2.5 Síntese acionável para o Bee

| Categoria | Fenômenos |
|---|---|
| ✅ **Onde a norma-padrão já perdeu** (o Bee pode/deve usar) | próclise livre (inclusive pronome solto entre verbos) · futuro perifrástico · "a gente" · **objeto nulo** · "onde" um pouco além do estritamente locativo |
| ✅ **Onde a norma ainda governa a escrita** (o Bee deve manter) | concordância verbal e nominal plena · "há/existe" em vez de "tem" existencial · clítico **ou** objeto nulo (nunca "vi ele") · "cujo" quando couber · crase · "faz X anos" · "houve" invariável · "para eu fazer" |
| 🟡 **Zona cinzenta — NÃO gerar como par errado→certo** | **mesóclise** (correta, mas o próprio jornalismo manda evitar) · **"assistir o"** (o Houaiss registra até em pessoa culta) · **"namorar com"** e **"visar"** (autoridades **discordam entre si**) |
| 🔴 **Nunca gerar** | ortografia pré-Acordo (trema, "idéia", "infra-estrutura") · "houveram" existencial · "os menino" · "a gente vamos" |

---

## 3. Neologismos e estrangeirismos consolidados

> ⚠️ **Limite desta seção, declarado de saída:** `academia.org.br` (VOLP), `michaelis.uol.com.br` e `dicio.com.br` **bloquearam** o acesso automatizado. Tudo que aparece abaixo como "não dicionarizado" significa **"não encontrado no Priberam nem no Aulete"** — não é prova de ausência, porque as duas fontes mais relevantes para o PT-BR (Michaelis e VOLP) ficaram fora do alcance.

### 3.1 O que o VOLP 6.ª ed. (2021) incorporou — grafia confirmada

Critério de inclusão declarado por **Evanildo Bechara**: *"o da sua frequência entre os falantes"*; o VOLP é *"documentação das palavras utilizadas numa época específica"* ([Ciberdúvidas, 28/09/2021](https://ciberduvidas.iscte-iul.pt/atualidades/noticias/mais-mil-palavras-no-vocabulario-ortografico-da-lingua-portuguesa/3581)). O foco é **ortográfico**, não semântico: a ABL registra *como se escreve*, não o que significa.

**Formações vernáculas incorporadas** (grafia exata, mesma fonte): `aporofobia` · `biopsiar` · `bucomaxilofacial` · `ciberataque` · `cibersegurança` · `ciclofaixa` · **`covid-19`** (minúscula, com hífen) · `decolonialidade` · `docussérie` · `feminicídio` · `gentrificação` · `gerontofobia` · `homoparental` · `infodemia` · `judicialização` · `laudar` · `mocumentário` · `necropolítica` · `negacionismo` · `notícia-crime` · `pós-verdade` · `sororidade` · `telemedicina` · `teleinterconsulta`.

**Estrangeirismos admitidos COM GRAFIA ORIGINAL**: `Botox` · `bullying` · `compliance` · `coworking` · `crossfit` · `home office` · `lockdown`.

⭐ **O padrão importa mais que a lista:** o VOLP **não aportuguesou** os anglicismos desta leva (registrou `coworking`, não *"cowórquingue"*), **mas acolheu formações vernáculas produtivas** com prefixos nativos (`ciber-`, `cripto-`, `tele-`). **Regra para o Bee: manter a grafia inglesa dos empréstimos recentes e preferir o derivado vernáculo quando ele existe.**

> Divergência de número: a matéria da [Agência Brasil (10/06/2021)](https://agenciabrasil.ebc.com.br/educacao/noticia/2021-06/abl-finaliza-6a-edicao-do-vocabulario-ortografico-da-lingua-portuguesa) cita **370 mil**; fontes secundárias citam **382 mil**. **[NÃO CONFIRMADO qual é o correto]** — fonte primária bloqueada.

### 3.2 Estado de dicionarização — tecnologia, redes e IA

| Palavra | Status confirmado | Fonte |
|---|---|---|
| `deletar` | ✅ verbete próprio, marca `[Brasil] [Informática]`, etim. *delete* + *-ar* | [Priberam](https://dicionario.priberam.org/deletar) · [Aulete](https://www.aulete.com.br/deletar) |
| `postar` | ✅ acepção `[Informática]` "publicar numa página da Internet" | [Priberam](https://dicionario.priberam.org/postar) |
| `tuitar` | ✅ verbete (derivado de *tuíte*) — ⚠️ ver armadilha 1 | [Priberam](https://dicionario.priberam.org/tuitar) |
| `lacrar` | ✅ acepção `[Brasil, Informal]` "destacar-se com excelência" | [Priberam](https://dicionario.priberam.org/lacrar) |
| `bombar` | ✅ `[Informal]` "fazer sucesso" | [Priberam](https://dicionario.priberam.org/bombar) |
| `viralizar` | ✅ **sem** marca de informalidade | [Priberam](https://dicionario.priberam.org/viralizar) |
| `criptomoeda` | ✅ formação vernácula | [Priberam](https://dicionario.priberam.org/criptomoeda) |
| `influenciador` | ✅ inclui "influenciador digital" | [Priberam](https://dicionario.priberam.org/influenciador) |
| `influencer` · `live` · `streaming` · `podcast` · `chatbot` · `start-up` · `mouse` · `gamer` · `spoiler` · `hype` | ✅ registrados **como estrangeirismo** (itálico + "palavra inglesa"); `influencer` **remete a** INFLUENCIADOR. ⚠️ grafia canônica no Priberam é **`start-up`**, com hífen | Priberam |
| `prompt` · `delivery` | ✅ registrados com marca `Ing.` | [Aulete/prompt](https://www.aulete.com.br/prompt) · [Aulete/delivery](https://www.aulete.com.br/delivery) |
| `printar` · `startar` · `shippar` · `stalkear` · `stories` · `reels` · `deepfake` · `pix` · `marketplace` · `crush` · `cringe` | ❌ **não encontrados** no Priberam nem no Aulete → **"uso corrente, não dicionarizado nas fontes acessíveis"** | — |

### 3.3 ⚠️ Quatro armadilhas semânticas reais (isto é dado envenenado)

Se o Bee aprender o sentido do dicionário para estas palavras e o usuário estiver falando de internet, ele erra:

1. **`tuitar` é homônimo.** O [Aulete](https://www.aulete.com.br/tuitar) registra *tuitar* do latim *tuitus* = **"defender, proteger"** — sem nenhuma relação com Twitter.
2. **`treta`**: o [Priberam](https://dicionario.priberam.org/treta) dá "ardil, estratagema". O sentido brasileiro corrente ("briga, confusão") **não consta**.
3. **`engajamento`**: Priberam e Aulete dão "envolvimento em causa / alistamento". A acepção de **métrica de rede social não consta em nenhum dos dois**.
4. **`prompt`**: dicionarizado só no sentido antigo (*prompt de comando*) — **não** como instrução dada a uma IA.

**Implicação prática:** um pipeline que use dicionário como *ground truth* semântico vai contaminar o Bee. Dicionário serve para **ortografia e flexão** (que é para o que o VOLP existe), **não** para sentido corrente em domínio digital.

### 3.4 Convenções de estrangeirismo — o que é regra e o que é hábito editorial

| Afirmação | Status |
|---|---|
| O VOLP acolhe estrangeirismos **mantendo a grafia original** | ✅ confirmado (Ciberdúvidas, 28/09/2021) |
| Plural aportuguesado é registrado e legítimo: **`mouses`** ("plural: *mouses* ou *mice*"), `podcasts`, `gamers`, `spoilers`, `chatbots` | ✅ confirmado no [Priberam](https://dicionario.priberam.org/mouse) |
| Estrangeirismos vão **em itálico** | ⚠️ **é convenção lexicográfica do Priberam, NÃO norma do Acordo Ortográfico.** **[NÃO CONFIRMADA]** qualquer regra normativa de itálico obrigatório. **Não codificar isso como regra** |

### 3.5 "Palavra do ano" (2023-2026)

**Portugal — Porto Editora/Infopédia** (votação pública de editora): 2023 **professor** (~48%) · 2024 **liberdade** (anunciada 07/01/2025) · 2025 **apagão** (41,5%; 2º *imigração*, 22,2%) · 2026 **[NÃO CONFIRMADO]** (a votação ocorre em nov/dez).
**Brasil — CAUSE + Instituto IDEIA** ⚠️ **é pesquisa de opinião, não seleção lexicográfica**: 2024 **ansiedade** (22%) · 2025 **incerteza** (24%, 1.500 entrevistados) · 2023 **[NÃO CONFIRMADO]**.
**[NÃO CONFIRMADO]** qualquer "palavra do ano" de dicionário brasileiro (Michaelis/Houaiss/Aulete) ou da ABL.

*Relevância para o Bee: baixa.* Serve só como sinal de que o léxico se move; não é material de treino.

---

## 4. ⚠️ Linguagem neutra / inclusiva — questão em disputa

> **Como esta seção foi escrita.** Relato de **atos e posições, com autoria e data**. Não há recomendação, não há juízo sobre o mérito, e as posições contrárias estão registradas com o mesmo peso. **A decisão é do dono do projeto.** O que este documento faz é impedir que ela seja tomada com base em informação errada — porque há bastante informação errada circulando sobre este tema, inclusive em fontes especializadas (ver a discrepância marcada em §4.3).

### 4.1 Primeiro: são TRÊS fenômenos distintos, e confundi-los é o erro mais comum

A distinção mais nítida em documento oficial brasileiro está no **Manual de Comunicação Humanizada e Inclusiva do TCU (2025)** ([PDF, 56 pp.](https://portal.tcu.gov.br/uploads/id_Sisdoc_32280473v2_08_Manual_de_Comunicacao_Inclusiva_f036446c53.pdf)): linguagem **inclusiva** = comunicar *"sem alterar o idioma como o conhecemos"*, *"utilizando palavras que já existem"*; linguagem **neutra/não-binária** = *"sugere recursos que **alteram o idioma**… a exemplo de amigxs, tod@s, todes"*.

⚠️ **A terminologia não é estável nem entre especialistas:** no Ciberdúvidas, [Sara Mourato (03/12/2025)](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/controversias/linguagem-neutra-e-a-proibicao-no-brasil/5998) trata "neutra" e "inclusiva" como **sinônimos**, enquanto [Rita Monarca Almeida (03/07/2023)](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/controversias/afinal-o-que-e-a-linguagem-inclusiva/5255) trata "neutra" como **subcategoria** de "inclusiva".

| | Fenômeno | Estado normativo **confirmado** |
|---|---|---|
| **(3)** | **Masculino genérico** (`todos` para grupo misto) | Regra da tradição gramatical (⚠️ **[NÃO CONFIRMADO]** em Bechara / Cunha & Cintra em primeira mão). **Não é proibido em lugar nenhum.** Mas vários órgãos brasileiros orientam **evitá-lo**: a Res. CNJ 376/2021 age *"em detrimento da utilização do masculino genérico"*; o MGI orienta *"não usar o masculino como forma de universalizar as pessoas"* |
| **(2)** | **Inclusiva binária** (desdobramento: `todos e todas`, `juízes e juízas`) | **Obrigatória no Judiciário brasileiro** — [Res. CNJ 376, 02/03/2021](https://atos.cnj.jus.br/atos/detalhar/3765). **Recomendada** por TSE, TCU, MGI, UE, NOVA/CIG, UNIRIO. **Não é atingida pela Lei 15.263/2025**, que veda formas *novas* ⚠️ *(esta última é leitura do texto do inciso; não localizei interpretação oficial que confirme o alcance)* |
| **(1)** | **Neutra com neomorfemas** (`elu`, `todes`, `-e`, `x`, `@`) | **Vedada na administração pública brasileira desde 2025** (Lei 15.263, art. 5º, XI). Já era **desaconselhada pelos próprios guias inclusivos**, e o argumento predominante **não é gramatical, é de acessibilidade** — ver §4.5 |

### 4.2 O que mudou no Brasil: STF (2023-2026) e a Lei 15.263/2025

**Fase 1 — o STF derrubou as leis estaduais e municipais que PROIBIAM linguagem neutra nas escolas.**

| Caso | Ação | Data | Resultado |
|---|---|---|---|
| Rondônia (Lei 5.123/2021) | **ADI 7019**, rel. Min. **Edson Fachin** | julgada 10/02/2023 | inconstitucional |
| Amazonas | **ADI 7644**, rel. Min. Flávio Dino | ⚠️ **[ano NÃO CONFIRMADO]** | lei suspensa (liminar) |
| Santa Catarina | **[nº/relator NÃO CONFIRMADOS]** | — | inválida |
| Porto Alegre, São Gonçalo, Muriaé (municipais) | rel. Min. André Mendonça | ~02/03/2026 | inconstitucionais ([ConJur](https://www.conjur.com.br/2026-mar-02/stf-invalida-leis-municipais-que-proibiam-uso-de-linguagem-neutra-nas-escolas/)) |

Tese fixada na ADI 7019 (transcrição literal via [Dizer o Direito](https://www.dizerodireito.com.br/2023/03/e-formalmente-inconstitucional-lei.html)):

> *"Norma estadual que, a pretexto de proteger os estudantes, proíbe modalidade de uso da língua portuguesa viola a competência legislativa da União."*

🔑 **Ponto que quase toda cobertura distorce:** a inconstitucionalidade é **FORMAL — de competência** (art. 22, XXIV da CF/88: diretrizes e bases da educação são privativas da União). **O STF não julgou o mérito linguístico.** A decisão **não** diz que a linguagem neutra é boa, obrigatória ou protegida. Pelo mesmo critério, uma lei estadual que *obrigasse* a linguagem neutra também seria inconstitucional.

**Fase 2 — a União legislou, e o resultado é uma vedação federal parcial.**

**Lei nº 15.263, de 14/11/2025** — *"Institui a Política Nacional de Linguagem Simples nos órgãos e entidades da administração pública direta e indireta de todos os Poderes da União, dos Estados, do Distrito Federal e dos Municípios."*

> **Art. 5º, XI:** *"não usar novas formas de flexão de gênero e de número das palavras da língua portuguesa, em contrariedade às regras gramaticais consolidadas"*

- Os outros 17 incisos do art. 5º são técnicas de linguagem simples (ordem direta, frases curtas, voz ativa, evitar estrangeirismos, testar compreensão) — **o inciso XI é um item dentro de uma lei que não é sobre isso**.
- Sanção 14/11/2025, publicação no DOU em 17/11/2025; houve **veto parcial ao art. 7º** por vício de iniciativa (não ao inciso XI).
- Cobertura: [Agência Brasil, 18/11/2025](https://agenciabrasil.ebc.com.br/geral/noticia/2025-11/governo-sanciona-proibicao-do-uso-de-linguagem-neutra-em-orgao-publico), que acrescenta que se deve seguir a norma padrão e as regras consolidadas pelo **VOLP** e pelo **Acordo Ortográfico**.
- Autoria do PL atribuída à dep. **Erika Kokay (PT-DF)**; a emenda que introduziu o inciso XI, ao dep. **Junio Amaral (PL-MG)** *(fonte secundária, não lida integralmente)*.
- ⚠️ **Texto oficial no Planalto inacessível (ECONNRESET)** — lido em [reprodução de terceiros](https://www.lex.com.br/lei-no-15-263-de-14-de-novembro-de-2025/).

**📌 Tensão documentada dentro do próprio Estado brasileiro:** a **Res. CNJ 376/2021** torna **obrigatório** o desdobramento de gênero no Judiciário, enquanto a **Lei 15.263/2025** veda "novas formas de flexão". Se elas se contradizem depende de o desdobramento binário contar ou não como "nova forma de flexão" — **e nenhuma fonte consultada articula oficialmente os dois instrumentos.**

### 4.3 ⚠️ Uma afirmação amplamente repetida que NÃO se confirmou

O [Ciberdúvidas (03/12/2025)](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/controversias/linguagem-neutra-e-a-proibicao-no-brasil/5998) afirma que a Lei 15.263/2025 proíbe linguagem neutra também no **"ensino público"** e em **"materiais pedagógicos"**. **Isso NÃO se confirma no texto do art. 5º que foi lido**, cujo âmbito é a comunicação da **administração pública com o cidadão**. **Não repetir a versão "ensino público" sem checar o texto oficial no Planalto.**

### 4.4 As posições, com autoria

| Quem | Posição | Fonte / ressalva |
|---|---|---|
| **ABL** (Merval Pereira, então presidente), em audiência do CNE em 03/10/2023 | *"Os documentos oficiais devem seguir as normas oficiais que estão vigentes."* A linguagem neutra é *"um fenômeno ainda incipiente e de nicho"*; adotá-la alteraria a estrutura do PT-BR; professores **não podem obrigar** alunos a usá-la; a decisão sobre adoção oficial caberia ao **MEC, não à ABL**; e a posição **não é definitiva** | ⚠️ **fonte SECUNDÁRIA** ([Gazeta do Povo, 05/10/2023](https://www.gazetadopovo.com.br/vida-e-cidadania/academia-brasileira-de-letras-nao-ve-razao-para-adocao-oficial-da-linguagem-neutra/)); `academia.org.br` retornou 403. **[NÃO CONFIRMADA]** a existência de nota escrita institucional |
| **ABRALIN** | Pediu **veto ao inciso XI**, argumentando que a redação *"confunde gramática, léxico e ortografia"* e pressupõe "regras gramaticais consolidadas" que não correspondem à realidade da língua. Considera a proibição um retrocesso; defende que a língua é dinâmica; alertou que legislar sobre usos linguísticos pode limitar a liberdade de expressão | ⚠️ [nota](https://abralin.org/nota-da-abralin-sobre-a-politica-nacional-de-linguagem-simples/) retornou **403**; conteúdo via resumo + Ciberdúvidas. Também há [nota sobre a lei de Rondônia](https://abralin.org/nota-publica-lei-n-5-123/) (403) |
| **Academia das Ciências de Lisboa** | **[NÃO CONFIRMADO]** — não localizei nenhum parecer, nota ou comunicado sobre linguagem inclusiva/neutra. O projeto **ACL+** do site trata de **linguagem clara** (ISO 24495-1:2023), que é tema distinto | [ACL, 19/05/2026](https://www.acad-ciencias.pt/eng/2026/05/19/especial-acl-linguagem-cultura-e-inclusao-digital/) |
| **Estado português** | **RCM n.º 161/2008** (22/10/2008) recomenda "práticas não discriminatórias da linguagem" — referência explícita aos dois sexos **ou** neutralização. **Manual de Linguagem Inclusiva do CES**, aprovado 20/05/2021 (33 a favor, 1 abstenção, 3 contra) | [DRE](https://diariodarepublica.pt/dr/detalhe/resolucao-conselho-ministros/161-2008-438443) · [CIG](https://www.cig.gov.pt/wp-content/uploads/2021/08/12-Manual-de-Linguagem-Inclusiva-CES.pdf) |
| **Posição contrária** (masculino genérico como neutro convencional) | Entrevista da linguista **Concepción Company Company**, *"A gramática não tem sexo…"* | ⚠️ [Ciberdúvidas, 03/04/2019](https://ciberduvidas.iscte-iul.pt/artigos/rubricas/controversias/a-gramatica-nao-tem-sexo-nao-e-inclusiva-nem-exclusiva/3831) — **trata do espanhol**, não do português |

### 4.5 O achado mais surpreendente: os guias inclusivos também rejeitam os neomorfemas

| Documento | Órgão / ano | O que orienta |
|---|---|---|
| [Res. CNJ 376](https://atos.cnj.jus.br/atos/detalhar/3765) | CNJ, 02/03/2021 | **Obrigatória**: flexão de gênero na comunicação do Judiciário; desdobramento binário. **Não menciona neomorfemas** |
| [Guia de Linguagem Inclusiva](https://www.tse.jus.br/comunicacao/noticias/arquivos/tse-guia-de-linguagem-inclusiva/@@download/file/Guia%20de%20Linguagem%20Inclusiva%20TSE_mar-2023.pdf) | TSE, mai/2021 rev. mar/2023 | **Neutralização** ("pessoas inscritas") **ou especificação** ("todas e todos"). **Zero ocorrências** de "todes", "elu", "x", "@" |
| [Manual de Comunicação Humanizada e Inclusiva](https://portal.tcu.gov.br/uploads/id_Sisdoc_32280473v2_08_Manual_de_Comunicacao_Inclusiva_f036446c53.pdf) | TCU, 2025 | "pessoas servidoras" ou "servidores e servidoras". **Rejeita neomorfemas**: *"do ponto de vista técnico… ainda não funciona"* — leitores de tela não reconhecem |
| [Linguagem inclusiva](https://www.gov.br/gestao/pt-br/assuntos/inovacao-governamental/gestao-de-carreiras/lins/linguagem-inclusiva) | MGI, atual. 29/07/2026 | "pessoa(s)", "quem", "alguém"; ordem feminino+masculino. **Rejeita "x", "@" e "e"** (não pronunciáveis) |
| [Cartilha](https://www.unirio.br/nai/CartilhaComunicaoInclusiva_ebook_2024.pdf) | UNIRIO, 2024 | Desdobramento + coletivos ("a chefia", "a coordenação"). **Zero neomorfemas** |
| [Guia](https://www.unl.pt/wp-content/uploads/2024/10/GULI_Web_A4_v3-1.pdf) | NOVA de Lisboa + CIG, out/2024 | Neutralização primeiro ("o corpo docente", "o eleitorado"). **Desaconselha "@" e "x"**. **Não contém "todes" nem "elu"** — confirmado por [fact-check do Polígrafo (06/03/2026, veredito FALSO)](https://poligrafo.sapo.pt/fact-check/universidade-nova-de-lisboa-quer-tornar-obrigatoria-linguagem-inclusiva-no-contexto-academico/), que registra ainda que o guia *"não tem natureza regulamentar"* |
| [*a folha* n.º 55](https://op.europa.eu/webpub/dgt/afolha/documents/afolha_055_pt.pdf) | União Europeia, outono/2017 | Neutralização e especificação. Menciona "tod@s/todxs" **apenas em registro jocoso** (*"estava a brincar!"*) |

📌 **Padrão consistente e verificado em 7 documentos de 3 jurisdições:** **nenhum** guia institucional propõe `elu`/`todes`/`-e`. Todos recomendam **neutralização lexical** (coletivos, "pessoas", "quem") e/ou **desdobramento binário**. Vários rejeitam neomorfemas explicitamente — e **o argumento predominante é acessibilidade** (leitores de tela, pronunciabilidade), **não** prescrição gramatical.

### 4.6 O que isto significa para o Bee (sem tomar partido)

Traduzindo os fatos acima em consequências **factuais** — a escolha continua sendo do dono do projeto:

1. **A neutralização lexical não é controversa em lugar nenhum.** "A chefia decidiu", "o corpo docente", "quem se inscreveu", "as pessoas usuárias" — nenhuma das 7 fontes rejeita, várias recomendam, e nada disso viola a Lei 15.263/2025. **É a única opção sem custo político.**
2. **O desdobramento binário é obrigatório em um Poder e recomendado em vários órgãos** — logo aparecerá naturalmente no corpus (o bloco `jud` do Carolina é Judiciário). Não é anomalia a filtrar.
3. **Os neomorfemas (`elu`, `todes`, `-e`, `x`, `@`) são vedados na administração pública federal desde 11/2025** e ausentes de todos os guias institucionais — logo serão **raríssimos** em corpus de texto formal, e concentrados em texto de redes sociais e militância. O Bee vai ver muito pouco disso.
4. **A decisão a tomar não é "o Bee usa ou não usa".** É mais estreita e mais prática: **o Bee deve tratar `todes`/`elu` como (a) erro a corrigir, (b) forma válida, ou (c) forma que ele reconhece mas não produz espontaneamente?** A opção **(c)** é a que corresponde ao estado de fato descrito acima e a que menos exige do modelo — mas é escolha do dono, não deste documento.
5. ⚠️ **Não codificar neomorfemas como "erro" no BLiMP-PT / nos pares errado→certo sem decisão explícita.** Isso embutiria uma posição política dentro de uma métrica técnica, onde ela ficaria invisível e difícil de reverter depois.

---

## 5. ⭐ Recursos LICENCIÁVEIS de PT-BR

Esta é a seção com maior valor prático: **um recurso licenciável vale mais que um livro protegido**, porque entra direto no corpus em vez de virar prompt de professor sintético.

### 5.1 Tabela mestra

Legenda de risco: 🟢 usável e redistribuível · 🟡 usável com atenção (atribuição/share-alike/heterogêneo) · 🔴 não usar no corpus.

| Recurso | Licença (confirmada) | Tamanho | Como usaríamos no Bee | Risco |
|---|---|---|---|---|
| **HPLT v2 (`monoHPLT-PT`)** — [site](https://hplt-project.org/datasets/v2.0) · [HF `HPLT2.0_cleaned`](https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned) | **CC0 1.0** ("no rights reserved") — confirmado no site **e** no front matter do card HF (`license: cc0-1.0`) | 191 idiomas; a fatia PT dentro do GigaVerbo tem **58,2M documentos** ([card GigaVerbo](https://huggingface.co/datasets/TucanoBR/GigaVerbo)) | **Base do pré-treino.** É o maior bloco de texto PT com licença *totalmente* permissiva que localizei. Fonte: Internet Archive + Common Crawl | 🟢 |
| **GigaVerbo** (TucanoBR) — [HF](https://huggingface.co/datasets/TucanoBR/GigaVerbo) | **`other`** — 19 subcorpora com licenças mistas (CC0-1.0, CC BY 4.0, Apache-2.0, CC BY-SA 3.0, **e CC BY-NC 4.0**) | **~200B tokens / 780 GB / 145,3M linhas** | ⭐ **O achado de maior impacto do estudo.** É PT em escala 20× o que o Bee viu. **Mas NÃO usar em bloco** — filtrar por subcorpus para excluir o NC e o de proveniência duvidosa. Traz filtro de qualidade embutido (`BERTimbau-base-text-filter`), com os exemplos de baixa qualidade preservados para você escolher o corte | 🟡 |
| **FineWeb-2 (pt)** — [HF](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | **[NÃO CONFIRMADO nesta pesquisa]** — o card não abriu; derivado de Common Crawl. Verificar antes de citar em release | ~3T tokens / 5B documentos / 1000+ idiomas (total multilíngue); >1B tokens em PT segundo um estudo de pré-treino | Já está no plano do Bee. **Complementar ao HPLT**, não redundante: FineWeb-2 vem só de Common Crawl, HPLT majoritariamente de Internet Archive | 🟡 |
| **Legislação e decisões judiciais brasileiras** — [Lei 9.610/1998, art. 8º, **IV**](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) | **Não são objeto de proteção como direitos autorais**: *"os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais"* (inciso IV confirmado) | Dentro do Carolina: `leg` **4,2 GB** + `jud` **1 GB** | ⭐⭐ **O bloco mais limpo juridicamente que existe em PT-BR.** Português formal, correto, com concordância e regência impecáveis. Ver ressalva de estilo em §5.4 | 🟢 |
| **Manual de Redação da Presidência da República**, 3.ª ed. (2018) — [PDF Planalto](https://www4.planalto.gov.br/centrodeestudos/assuntos/manual-de-redacao-da-presidencia-da-republica/manual-de-redacao.pdf) | **ato oficial** (mesma base do art. 8º, IV — mas *"ato oficial"* aplicado a um manual é interpretação, não texto expresso da lei) | 1 volume | Descreve a **norma da redação oficial brasileira**: padrão ofício, concordância, pronomes de tratamento, vícios a evitar. É a especificação escrita do registro formal que o Bee provavelmente deve mirar (§8). Usar como **fonte de regras**, não como token | 🟡 |
| **Corpus Carolina** (USP/C4AI) — [HF](https://huggingface.co/datasets/carolina-c4ai/corpus-carolina) | ⚠️ **Ambígua.** Card HF: front matter `license: cc-by-4.0` + *"The Carolina headers are licensed under Creative Commons Attribution 4.0 International"*. Site da USP: **CC BY-NC-SA 4.0** para o cabeçalho. **Em ambos os casos o que está licenciado é o CABEÇALHO, não o texto** — o card é explícito: os textos vêm de repositórios *"whose licenses are multiple and therefore should be observed"* | v2.0.1 "Bea": **15 GB / ~2,1M instâncias** | 🎯 **O diferencial do Carolina não é o tamanho, é a proveniência por documento.** É o único corpus PT grande em que dá para *filtrar por licença* e montar um subcorpus provadamente limpo. Taxonomias: `wik` 5,3GB, `dat` 4,3GB, `leg` 4,2GB, `jud` 1GB, `uni` 162MB, `soc` 49MB, `pub` 4,5MB | 🟡 |
| **Wikipédia em português** — [dumps](https://dumps.wikimedia.org/) | **CC BY-SA 4.0** (+ GFDL) — [Wikipédia:Direitos de autor](https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:Direitos_de_autor) | **1.179.128 artigos** (jul/2026) | Já usado. Prosa expositiva revisada. **Share-alike:** exige atenção se um dia o Bee for redistribuído com o corpus | 🟡 |
| **Wikcionário PT** — [pt.wiktionary.org](https://pt.wiktionary.org/wiki/Wikcion%C3%A1rio:Sobre_o_Wikcion%C3%A1rio) | **CC BY-SA 4.0** (a própria página confirma a migração a partir da 3.0 + GFDL) | **~510 mil verbetes** (iniciado em 01/05/2004) | ⭐ Definições, **tabelas de conjugação**, flexões, etimologia, sinônimos. Substituto licenciável parcial do VOLP e das tabelas de conjugação dos livros protegidos | 🟡 |
| **VERO / hunspell pt-BR** — [LibreOffice/dictionaries](https://github.com/LibreOffice/dictionaries/blob/master/pt_BR/README_pt_BR.txt) · [VERO-pt-BR](https://github.com/fititnt/VERO-pt-BR) | **LGPLv3 + MPL** | dicionário completo pt-BR (`.dic`+`.aff`) | ⭐⭐ **Verificador determinístico.** Gera a lista de formas flexionadas válidas do PT-BR pós-AO90 → usar como **filtro de aceitação** dos pares sintéticos "errado→certo" e como detector de ortografia pré-Acordo no corpus | 🟢 |
| **LanguageTool** — [GitHub](https://github.com/languagetool-org/languagetool) | **LGPL 2.1+** (core e `grammar.xml`). ⚠️ **exceção verificada:** o `pt-BR/replace.txt` traz cabeçalho próprio de **CC BY-SA 3.0** (derivado de Wikipédia/Wikcionário) — licenças diferentes convivem dentro do mesmo módulo | Módulo `pt` (raiz) + subdiretórios por variante **`pt-BR/`, `pt-PT/`, `pt-AO/`, `pt-MZ/`**. **`pt-BR/grammar.xml`: ~80-100 regras**, em 4 categorias (`MISC` gramática geral, `CASING`, `BR_SPELLING`, `TYPOGRAPHY`) | ⭐⭐⭐ **O achado mais acionável — mas não pelo motivo que eu supus.** Ver §5.2 para a correção | 🟢 |
| **PortiLexicon-UD** — [portilexicon.icmc.usp.br](https://portilexicon.icmc.usp.br/) | **[NÃO CONFIRMADO]** — descrito como "*large and freely available*", mas não localizei a licença explícita | **1.221.218 entradas** com POS, lema e traços morfológicos (padrão UD) | Léxico morfológico do PB. Serviria para **validar concordância nominal/verbal deterministicamente**. ⚠️ confirmar licença antes de usar | 🟡 |
| **UD Portuguese-Bosque** — [GitHub](https://github.com/UniversalDependencies/UD_Portuguese-Bosque) | **CC BY-SA 4.0** | treebank jornalístico; v2.11 (nov/2022) | ⚠️ **mistura CETEMPúblico (PT-PT) e CETENFolha (PT-BR)** — não usar sem separar a fatia brasileira. Útil para eval sintática, não para corpus | 🟡 |
| **OpenWordnet-PT** — [GitHub](https://github.com/own-pt/openWordnet-PT) | **CC BY 4.0** (confirmado no README) | wordnet do PB; distribuído em **RDF** (+ versão em formato FreeLing) | Sinônimos/hiperônimos para **diversificar a geração sintética sem repetir léxico** — mitigação direta do "colapso de template" que o doc 04 apontou como risco nº 1 do gerador | 🟢 |
| **Tatoeba** — [downloads](https://tatoeba.org/en/downloads) | **CC BY 2.0 FR** (algumas frases também CC0) | frases curtas por idioma, exportação filtrável por língua | Frases curtas corretas e revisadas — bom para *seed* de pares mínimos e de diálogo. **443.528 frases em português** ([stats Tatoeba](https://tatoeba.org/en/stats/sentences_by_language)); ⚠️ não separa PT-BR de PT-PT | 🟢 |
| **Common Voice (pt) — transcrições** — [Mozilla](https://mozillafoundation.org) | **CC0** para o corpus | v25.0 (22/03/2026): 196.698 clipes, 228,79 h, 3.817 falantes, a partir de **43.721 sentenças** de texto | O texto é pequeno, mas é **CC0 e revisado**. Útil como fonte de frases-semente irrepreensíveis | 🟢 |
| **Dicionário Aberto** (Cândido de Figueiredo, 1913) — [dicionario-aberto.net](https://dicionario-aberto.net) · [Gutenberg](https://www.gutenberg.org/ebooks/31552) | obra em **domínio público** (autor †1925; edição de 1913 em DP desde 2000); site declara CC BY-SA 2.5 PT | dicionário completo em XML | ⚠️ **PT-PT de 1913, ortografia pré-Acordo e léxico envelhecido.** **NÃO colocar no corpus do Bee.** Serve, no máximo, como fonte de etimologia/definições a serem reescritas | 🔴 no corpus |
| **Wikisource PT / Domínio Público (MEC)** — [pt.wikisource.org](https://pt.wikisource.org/wiki/Autor:Machado_de_Assis) · [dominiopublico.gov.br](https://www.dominiopublico.gov.br) | domínio público | literatura brasileira canônica | ⚠️ **Só as versões marcadas "ortografia atualizada"** (a Wikisource mantém as duas: `A Caridade (1864)` × `A caridade (ortografia atualizada)`). Prosa literária brasileira de altíssima qualidade — mas sintaxe do séc. XIX, incluindo **ênclise e mesóclise**, que o Bee **não** deve aprender como padrão | 🟡 |
| **PleIAs/Portuguese-PD** — [HF](https://huggingface.co/datasets/PleIAs/Portuguese-PD) | **Domínio público em todas as regiões** (declarado) | **7.840 títulos · 672.197.538 palavras · 3,32 GB** | ⚠️ **Caso exemplar de "licenciável mas nocivo".** Licença perfeita, conteúdo errado para o Bee: restrito a publicações **anteriores a 1884** (ou seja, anterior às reformas ortográficas de 1911/1943, quanto mais ao AO90), origem em bibliotecas patrimoniais **europeias**, e **todo o texto vem de OCR automático** (o próprio card admite). Colocar isso no corpus ensina o Bee a escrever `pharmacia` | 🔴 |
| **CALAME-PT** — [HF](https://huggingface.co/datasets/NOVA-vision-language/calame-pt) | **MIT** | **2.076 textos** + última palavra; 406 escritos à mão por 4 anotadores, resto gerado com revisão humana | ⭐ Benchmark zero-shot de *language modeling* (adivinhar a última palavra, estilo LAMBADA). **É a métrica em que o Tucano-160m marcou 52,31** → é a comparação direta disponível para o Bee, com licença permissiva | 🟢 |
| **CAPITU** — [arXiv 2603.22576](https://arxiv.org/abs/2603.22576) | **CC BY 4.0** | 59 tipos de instrução em 7 categorias | ⭐ Benchmark **pt-BR** de *instruction-following* com **restrições morfológicas verificáveis automaticamente** (`-ando/-endo/-indo`, `-inho/-inha`, `-mente`), contagem exata e persistência multi-turno. **Eval de morfologia de graça** para a fase de SFT | 🟢 |
| **Dataset GEC pt-BR** — [arXiv 2306.15788](https://arxiv.org/abs/2306.15788) | **CC BY 4.0** (código-fonte do artigo) | 4 categorias: *Grammar, Spelling, Internet, Fast typing*; sentenças incorretas **pareadas** com as corretas. **Nº de sentenças: [NÃO CONFIRMADO]** | ⭐ **Pares errado→certo reais, escritos por falantes nativos** — exatamente o formato que o estudo de 03/08 queria gerar sinteticamente. Pequeno, mas é *ground truth* humano para validar o gerador | 🟢 |
| **Canarim-Instruct-PTBR** — [HF](https://huggingface.co/datasets/dominguesm/Canarim-Instruct-PTBR-Dataset) | **CC BY-NC** (confirmado) | 317.932 linhas (316.000 treino + 1.519 teste) | ❌ **Descartar, e por dois motivos independentes.** (1) **NC** — inviabiliza qualquer uso comercial. (2) **Proveniência:** é tradução/adaptação de `alpaca-data-pt-br`, `instructions-pt`, `self_instruct` e `helpful_instructions` — ou seja, **saídas de modelo traduzidas**, com a cadeia de ToS do Alpaca/self-instruct atrás. É exatamente o padrão que o projeto evitou ao escolher um professor com ToS permissivo | 🔴 |
| **CETENFolha** (Linguateca) — [linguateca.pt](https://www.linguateca.pt/cetenfolha/index_info.html) | uso para pesquisa e desenvolvimento tecnológico; **exploração comercial direta vedada**; exige creditar a fonte | ~24 milhões de palavras (Folha de S.Paulo), PT-BR | Jornalismo brasileiro anotado. **Não redistribuível comercialmente** | 🔴 se o Bee for comercial |
| **CETEMPúblico** | idem, mesma restrição | ~180 milhões de palavras | **PT-PT.** Não interessa ao Bee | 🔴 |
| **BrWaC** — [HF](https://huggingface.co/datasets/UFRGS/brwac) | **`License: unknown`** no card, e termo explícito: *"this resource is available solely for academic research purposes, and you agreed not to use it for any commercial applications"*. Download manual via UFRGS | **3,53M documentos · 2,68B tokens · 5,79M types** | ⚠️ **Landmine:** o BrWaC está *dentro* do `CrawlPT`, que por sua vez está dentro do GigaVerbo declarado como CC BY 4.0. **A cadeia de licença não fecha.** Ver §5.3 | 🔴 |
| **CrawlPT_dedup** — [HF](https://huggingface.co/datasets/eduagarcia/CrawlPT_dedup) | **licença não declarada no card** | 52.462.533 docs · **~29,2B tokens** · 170 GB · composto de brWaC + CC100-PT + OSCAR-2301-PT | Tentador pelo tamanho, mas herda o problema do brWaC | 🔴 até esclarecer |
| **VOLP (ABL)** | **[NÃO CONFIRMADO — presumir fechado]** | ~382 mil verbetes | Consulta manual apenas. **Não colocar a base no corpus** | 🔴 |
| **VOC (IILP/CPLP)** | **[NÃO CONFIRMADO]** | vocabulários de 5 países | idem | 🔴 até esclarecer |
| **verbecc** — [GitHub](https://github.com/bretttolbert/verbecc) | **LGPL-3.0** | XMLs de conjugação (derivados do mlconjug/Verbiste); nº de verbos PT **[NÃO CONFIRMADO]**; distinção PT-BR/PT-PT **[NÃO CONFIRMADO]** | Gerar **paradigmas de conjugação completos** programaticamente | 🟡 |
| **mlconjug3** — [GitHub](https://github.com/Ars-Linguistica/mlconjug3) | **MIT** | modelo pré-treinado para PT | idem, licença mais permissiva | 🟢 |

### 5.2 Os três recursos que eu priorizaria (e por quê)

1. **LanguageTool (`pt-BR`), LGPL.** É o item de melhor relação valor/esforço do inventário inteiro — mas **abri os arquivos antes de afirmar isso, e o que encontrei corrige minha própria hipótese inicial**:

   | Arquivo | O que eu supus | O que ele **é de fato** (verificado) |
   |---|---|---|
   | `pt-BR/replace.txt` | catálogo de erros | **mapeamento léxico PT-PT → PT-BR**, ~220 linhas (`castanho=marrom`, `comboio=trem`, `autocarro=ônibus`, `telemóvel=telefone celular`, `desporto=esporte`) |
   | `pt-BR/confusion_pairs.txt` | milhares de pares | **~45 linhas**, sem acento → com acento, com POS tag (`anonimo;anônimo;AQ0MS0`, `polemica;polêmica;NCFS000`) |
   | `pt/replace.txt` | catálogo geral | **"foreign words confused with Portuguese ones"** (LGPL, Marco A.G. Pinto) — escopo estreito |
   | `pt-BR/grammar.xml` | — (não tinha avaliado) | ⭐ **é aqui que mora o valor**: ~80-100 regras de padrão |

   **Correção honesta:** as listas planas **não** são "milhares de pares errado→certo". São pequenas e de escopo específico. **O catálogo de erros está no `grammar.xml`, em forma de regra de padrão** — e ele bate quase item a item com as 13 classes do doc 04: `AGENTE_BR` (agente × a gente), `MAS_BR` (mas × mais), `FAZEM_TEMPO` (verbo impessoal de tempo), `CHEGAMOS_EM_BR` (regência: chegar **em** → chegar **a**), `DUZENTAS_GRAMAS_NUMERAL` (concordância de gênero), `AO90_COMPOUNDS_GENERIC_PREFIX` (hifenização pelo AO90), `AO90_MONTHS_CASING`.

   **Portanto o uso certo é duplo, e o segundo vale mais que o primeiro:**
   - como **fonte de cobertura** (a lista de nomes de regra = checklist de fenômenos que faltam no catálogo de 58 verbetes) — ganho moderado;
   - ⭐ como **verificador determinístico executável**: rodar o LT sobre cada par sintético gerado, e **rejeitar o par cujo lado "certo" ainda dispara regra**. Isto é a materialização direta do princípio "quem gera não pode avaliar", e não precisa de LLM nem de anotador.
   - **bônus inesperado:** o `pt-BR/replace.txt` é exatamente o **detector de lusitanismo** que a §5.4 pede — ~220 palavras que, se aparecerem no corpus, sinalizam texto PT-PT. Vem de graça.
2. **HPLT v2 (CC0) + a fatia `leg`/`jud`.** Porque é volume **e** limpeza jurídica ao mesmo tempo — a combinação rara. O art. 8º da Lei 9.610/98 é a única base legal *brasileira* que dá texto em GB sem nenhuma dúvida de licença.
3. **VERO/hunspell pt-BR (LGPL).** Porque uma lista de formas flexionadas válidas é o filtro mais barato que existe contra dois defeitos concretos: palavra inventada e ortografia pré-Acordo.

### 5.3 Armadilhas de licença encontradas (reportar é mais útil que omitir)

- ⚠️ **Cadeia quebrada GigaVerbo → CrawlPT → brWaC.** É o achado de licença mais grave do estudo, e é verificável em três cliques:
  - o card do **GigaVerbo** lista `CrawlPT` (43,8M linhas) como **CC BY 4.0**;
  - o card do **`CrawlPT_dedup`** (~29,2B tokens) **não declara licença nenhuma**;
  - o card do **brWaC**, que compõe o CrawlPT, diz `License: unknown` e exige concordância com *"solely for academic research purposes… not to use it for any commercial applications"*.
  
  Ou seja: um dataset com termo **não-comercial explícito** aparece, dois níveis acima, rotulado como **CC BY 4.0**. Alguém relicenciou o que não podia — provavelmente sem má-fé, por agregação automática de cards. **Recomendação: não usar CrawlPT/brWaC num Bee que se pretenda publicável, e consumir o GigaVerbo por subcorpus (`monoHPLT-PT` primeiro), nunca em bloco.** Isso não é purismo: é a diferença entre um modelo que pode ser publicado e um que não pode — a mesma regra que o projeto já aplicou aos 9 PDFs de gramática.
- **Carolina com duas licenças diferentes em duas páginas oficiais** (CC BY 4.0 no HF × CC BY-NC-SA 4.0 no site da USP). O "NC" muda tudo se o Bee tiver qualquer uso comercial. **Confirmar com os mantenedores antes de depender dele.**
- **VOLP e VOC: ausência de licença é ausência de permissão.** Não localizei nenhum termo autorizando redistribuição. Se um dia interessar, o caminho não é raspar: é (a) usar o Wikcionário + hunspell como substitutos livres, ou (b) pedir autorização formal à ABL/IILP. *Se* uma lista alfabética de palavras é ou não protegível é uma questão jurídica em aberto — **não é uma conclusão que este documento tenha condições de dar.**
- **Share-alike (CC BY-SA) da Wikipédia/Wikcionário/Bosque** não impede o treino, mas pode contaminar a redistribuição *do corpus*. Pesos de modelo em geral não são tratados como obra derivada — **mas isso também não está pacificado** e não vou afirmar que está.

### 5.4 Riscos de *conteúdo* (não de licença) nos recursos acima

| Risco | Onde aparece | Mitigação |
|---|---|---|
| **Ortografia pré-Acordo** (`idéia`, `pára`, trema) | qualquer texto brasileiro anterior a ~2009 — muito comum em crawl web e em literatura de DP | Filtro determinístico com o hunspell pt-BR + regex para trema e para as ~30 grafias abolidas mais frequentes. **Isto é obrigatório**, não opcional |
| **Mistura PT-PT / PT-BR** | Bosque (metade CETEMPúblico), FineWeb-2/HPLT (não separam variante), Dicionário Aberto, ALBA | Classificador de variante ou filtro léxico-diagnóstico (`autocarro`, `pequeno-almoço`, `casa de banho`, ênclise sistemática, `estás a fazer`) |
| **Ênclise/mesóclise como padrão** | literatura de domínio público (séc. XIX), textos jurídicos formais | Não é erro — é registro. Mas se dominar o corpus, o Bee escreve como Machado, não como brasileiro de 2026. Controlar a proporção |
| **Juridiquês** | `leg` + `jud` do Carolina (5,2 GB — bloco grande demais para o corpus do Bee) | Ótimo para concordância/regência, péssimo para naturalidade. **Limitar a fração**, não usar em bloco |
| **Texto gerado por LLM na web recente** | HPLT/FineWeb-2 pós-2023 | Sem solução limpa. Registrar como incerteza conhecida |
| **Ruído de OCR + ortografia do século XIX** | Portuguese-PD (pré-1884), digitalizações do Internet Archive | Excluir. É a razão pela qual "domínio público" **não** é sinônimo de "bom para o Bee" |

---

## 6. Delta em relação ao estudo de 2026-08-03

O estudo anterior concluiu: *os 9 PDFs são protegidos → extrair currículo e catálogo de erros → gerar pares "errado→certo" originais com professor aberto → ~30-80M tokens, tempero de 5-10% do mix.* **Essa conclusão continua de pé.** O que muda:

| # | Delta | Efeito prático |
|---|---|---|
| **D1** | ⭐ **Parte do catálogo de erros já existe com licença livre — mas em forma de REGRA, não de lista.** O `pt-BR/grammar.xml` do LanguageTool (LGPL 2.1+) tem ~80-100 regras que batem quase item a item com as 13 classes do doc 04: `AGENTE_BR`, `MAS_BR`, `FAZEM_TEMPO`, `CHEGAMOS_EM_BR`, `DUZENTAS_GRAMAS_NUMERAL`, `AO90_COMPOUNDS_GENERIC_PREFIX`. ⚠️ **As listas planas (`replace.txt`, `confusion_pairs.txt`) NÃO são o catálogo geral que eu supus** — ver a correção verificada em §5.2 | O catálogo dos PDFs continua sendo o **eixo temático**; o LT acrescenta **cobertura** (fenômenos que faltam) e, sobretudo, **execução** (§5.2) |
| **D2** | ⭐ **O verificador determinístico exigido pelo estudo já existe pronto**: LanguageTool + hunspell pt-BR, ambos LGPL | O "2º passe de checagem" deixa de ser trabalho a construir e vira integração |
| **D3** | ⭐⭐ **Existe um par direto do Bee, com resultado publicado: Tucano-160m** — 162.417.408 params, contexto 2048, **200B tokens** de GigaVerbo, **Apache 2.0**. Resultados: CALAME-PT 52,31 · LAMBADA-PT 28,16 · ARC-PT 27,01 · HellaSwag-PT 33,07 · média 35,14 ([HF](https://huggingface.co/TucanoBR/Tucano-160m)) | **Muda a régua do projeto.** Não é mais "o Bee está ruim comparado ao SmolLM2 em inglês" — existe um modelo do MESMO tamanho, MESMA língua, com números públicos. É a comparação honesta. E confirma o diagnóstico do estudo anterior: a diferença Bee↔Tucano é **20× em token**, não em arquitetura |
| **D4** | ⭐⭐ **GigaVerbo (200B tokens PT) e HPLT v2 (CC0) existem e não estavam no estudo** | O estudo dizia "o déficit de token se cobre com CulturaX-pt/mC4-pt na casa dos bilhões". Concreto agora: **GigaVerbo filtrado por licença** é o caminho, e o `monoHPLT-PT` (CC0) é a fatia mais limpa |
| **D5** | ⭐ **Existem pares errado→certo HUMANOS em pt-BR** (dataset GEC, CC BY 4.0, arXiv 2306.15788), com 4 categorias incluindo *Internet* e *Fast typing* | Não substituem os 30k sintéticos, mas servem de **conjunto de validação do gerador** — e as categorias "Internet"/"digitação rápida" são um tipo de erro que os livros de gramática **não** cobrem |
| **D6** | ⭐ **Existe eval de morfologia pt-BR verificável automaticamente: CAPITU (CC BY 4.0, mar/2026)**, com restrições tipo `-ando/-endo/-indo`, `-inho/-inha`, `-mente` | O estudo propôs construir suíte de eval do zero. Parte dela já existe e é auto-verificável (sem LLM-juiz) |
| **D7** | ⚠️ **Não localizei um BLiMP em português.** Existem BLiMP-NL (holandês), RuBLiMP (russo), Irish-BLiMP; para PT, **[NÃO CONFIRMADO]** | A "suíte log-prob/cloze" proposta no estudo de 03/08 **é, de fato, um BLiMP-PT**. Isso deixa de ser detalhe de implementação e vira uma contribuição própria com valor além do Bee |
| **D8** | ⚠️ **A ressalva "2 dos livros são PT-PT + pré-Acordo" se generaliza.** O mesmo problema afeta Bosque, Dicionário Aberto, literatura de DP e a web pré-2009 | O filtro de variante+ortografia deixa de ser cuidado com 2 PDFs e vira **etapa obrigatória do pipeline de corpus** |
| **D9** | Confirmação jurídica que os estudos anteriores não tinham: **Lei 9.610/98, art. 8º, IV** — *"os textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais"* **não são objeto de proteção** | Dá uma fonte de PT-BR formal e correto **em GB, sem dúvida de licença**. Também ampara o **Manual de Redação da Presidência da República** (3.ª ed., 2018) |
| **D10** | ⭐ **Fato normativo que nenhum dos estudos anteriores tinha: a Lei 15.263/2025 (Linguagem Simples).** Ela especifica oficialmente o registro formal brasileiro em 17 incisos operacionais, e no 18.º (art. 5º, XI) veda "novas formas de flexão de gênero e de número" na administração pública | Dá ao projeto (a) uma **definição pública do alvo estilístico** e (b) uma decisão que precisa ser tomada **explicitamente** sobre neomorfemas antes de construir o BLiMP-PT (§4.6) |
| **D11** | ⚠️ **Dicionário não é *ground truth* semântico para domínio digital.** Verificado: `treta`, `engajamento` e `prompt` estão dicionarizados **só no sentido antigo**, e `tuitar` tem um **homônimo latino** ("defender") no Aulete | Se o pipeline sintético usar dicionário para definir sentido, injeta erro. Dicionário serve para **ortografia e flexão** — que é para o que o VOLP existe |
| **D12** | 🔴 ⭐ **O delta mais importante para o doc 04: parte do catálogo de 58 verbetes é DISPUTA, não erro.** Verificado em §2.2: **`namorar com`** e **`visar`** são tratados como **corretos** pelo Ciberdúvidas e como **erro** pelo manual do Estadão; **`assistir o`** é registrado pelo **Houaiss** como uso *"comum… mesmo pelas pessoas cultas e na literatura"*. E o **`fim de semana × final de semana`**, que o doc 04 já isolara como "falso erro", **não é exceção — é a ponta de um padrão** | **Antes de gerar 30k pares, auditar os 58 verbetes contra uma segunda autoridade.** Gerar `namorar com → namorar` como par errado→certo ensina ao Bee uma regra que **nem os normativistas sustentam**. Isto é exatamente o tipo de erro de norma que o projeto declarou ser o pior defeito possível |
| **D13** | ⚠️ **Correção factual sobre o pretérito perfeito composto.** "Tenho feito" no PB **não** é o *present perfect* inglês: tem valor **iterativo/durativo** (*"no português moderno, o PPC recebe uma leitura iterativa"*), e a variação PB × PE nesse ponto é descrita como **"não significativa"** | Se algum material do currículo tratar "tenho feito" como passado pontual, ou como diferença PB/PE, está errado |
| **D14** | ⚠️ **Relação com o doc 04 (para não duplicar trabalho):** o 04 já especificou o `bench-pt-cloze` (58 erros × ~20 contextos, Molde C, log-prob). **Isso É um BLiMP-PT** — só falta o nome, o rigor de *par mínimo* (as duas frases devem diferir em **exatamente um** ponto) e a estratificação por fenômeno. Este documento acrescenta três coisas ao plano do 04: (a) o LanguageTool `pt-BR` como fonte licenciável para **ampliar** as 13 classes; (b) o dataset GEC humano (CC BY 4.0) como **validação externa** do gerador; (c) CALAME-PT (MIT) e CAPITU (CC BY 4.0) como **evals prontas** que o 04 não tinha | Não construir duas suítes. **É uma só**, e ela já tem dono no doc 04 |

---

## 7. ⭐ O que ensinar a um modelo de 151M

### 7.1 O argumento a favor

A tese do enunciado está certa, e há evidência empírica para ela:

- **Ortografia, concordância e regência são padrões locais e repetitivos.** A janela de dependência é curta (o núcleo do sintagma e o verbo estão a poucos tokens), o inventário de padrões é finito, e a frequência é altíssima — cada frase do corpus é um exemplo. É o oposto de fato enciclopédico, que é **longo, esparso e arbitrário** (a data de uma batalha aparece 3 vezes no corpus inteiro e não se deduz de nada).
- **O BabyLM Challenge existe justamente para mostrar isso**: modelos treinados com ~10 milhões de palavras (*strict-small*) adquirem conhecimento gramatical mensurável ([BabyLM](https://arxiv.org/html/2411.09587v1)). O Bee viu ~10 **bilhões** de tokens — três ordens de grandeza acima do orçamento do BabyLM.
- **A metodologia de medida certa já é padrão**: **BLiMP** — 67 subtarefas, 1.000 pares mínimos cada, avaliadas por **comparação de log-probabilidade** entre a frase gramatical e a agramatical ([BLiMP](https://arxiv.org/pdf/2011.04946)). Zero-shot, sem múltipla escolha, **com sinal mesmo em modelo fraco** — exatamente o que o estudo de 03/08 já tinha intuído ao propor log-prob/cloze.

Ou seja: **gramática é a coisa que um modelo pequeno mais consegue aprender, e é também a que se mede melhor num modelo pequeno.** As duas propriedades coincidirem não é sorte — é a mesma razão (padrão local, alta frequência, contraste mínimo).

### 7.2 O argumento contra (e ele é sério)

- **Fluência gramatical não é o gargalo declarado do Bee.** O commit mais recente diz: *"SFT do v3 concluído — gate de forma PASSOU, conteúdo fraco"*. Se a **forma** já passa e o **conteúdo** é fraco, investir mais capacidade em forma é otimizar o que já está bom.
- **O ganho tem teto baixo em métricas agregadas.** O Gate 2 v3 do próprio projeto mediu que 2,6× mais token rendeu ~0% de bpb (memória do projeto: *"mais token não resolve"*). Melhorar concordância pode não mover *nenhum* número que o projeto acompanha hoje — o que não significa que não melhore o modelo, significa que **o instrumento de medida atual não vê**.
- **Risco de deslocamento**: 15-25% de gramática dentro do sintético, se mal balanceado, ensina o Bee a *falar sobre* português em vez de *falar* português. O estudo anterior já alertou; continua valendo.

### 7.3 Veredito sobre o uso da capacidade

**Sim, é um bom uso — mas não pelo motivo óbvio.** Não é "gramática porque melhora a nota"; é:

1. **É o único eixo em que um 151M pode chegar perto do teto.** Fato enciclopédico, raciocínio e contexto longo têm teto estrutural nesse tamanho. Correção morfossintática, não. Um modelo pequeno **impecavelmente correto** em PT-BR é um artefato defensável; um modelo pequeno que sabe pouco de tudo, não.
2. **É o que sustenta a aposta de nicho.** A tese do projeto é "PT-BR é o núcleo". Se o diferencial não for a língua, não há diferencial — o Tucano-160m já ocupa o espaço de "modelo pequeno genérico em PT".
3. **Dá uma métrica própria, sensível e barata.** Um BLiMP-PT construído dos pares errado→certo mede exatamente o que o bpb não vê, e não custa GPU.

### 7.4 Ordem concreta de prioridade (revisando a do estudo de 03/08)

| # | O quê | Mudou em relação a 03/08? |
|---|---|---|
| 1 | **`bench-pt-cloze` do doc 04, promovido a BLiMP-PT** — mesma suíte, com três exigências acrescentadas: **par mínimo estrito** (diferença de exatamente um ponto), **estratificação por fenômeno** (as 13 classes do doc 04 + as do LanguageTool), e **validação externa** contra o dataset GEC humano. Sementes: `confusion_pairs`/`replace*` do LT `pt-BR` + os 58 verbetes + GEC | ⬆️ **1º.** Não é item novo — é o item 2 do doc 04, com rigor e fonte licenciável. Sem medida, os outros três são fé |
| **1,5** | 🔴 **AUDITORIA dos 58 verbetes contra uma segunda autoridade** (Ciberdúvidas, Houaiss) antes de gerar qualquer par. Saída: cada verbete marcado como `erro-consensual` · `disputado` · `falso erro` | ⭐ **item NOVO, e é bloqueante.** §2.2 mostrou que `namorar com`, `visar` e `assistir o` são **disputa entre normativistas**, não erro. Custo: horas. Custo de não fazer: ensinar ao Bee uma regra que nem os gramáticos sustentam |
| 2 | **Pares contrastivos errado→certo** (DPO/ORPO) — **apenas dos verbetes marcados `erro-consensual`** —, com verificação por LanguageTool + hunspell | = mantido, mas agora com fonte licenciável, verificador pronto e **filtro de disputa** |
| 3 | **Corpus PT em escala, filtrado por licença** — GigaVerbo por subcorpus + `monoHPLT-PT` (CC0) + `leg`/`jud` | ⬆️ deixou de ser "problema futuro" e virou acionável |
| 4 | **Diálogo/narração temática** — coerência | ⬇️ desceu, não por perder valor, mas porque 1-3 são pré-requisitos |
| 5 | **Explicações + tabelas de conjugação** — agora do Wikcionário/verbecc, não de PDF protegido | = com fonte trocada por uma licenciável |

### 7.5 O que **não** ensinar

- **Não ensinar linguagem neutra como padrão nem proibi-la por regra codificada** — ver §4; é decisão do dono do projeto, e a posição institucional está em disputa.
- **Não ensinar mesóclise** (`fá-lo-ei`) como forma produtiva: ela aparece na literatura de domínio público e em PT-PT, e é praticamente morta no PT-BR escrito contemporâneo.
- **Não ensinar ortografia pré-Acordo**, o que exige filtro ativo, não boa vontade.
- **Não ensinar o modelo a *julgar* a fala do usuário.** A §2 mostra que muito do que a norma condena é uso corrente e legítimo em registro informal. Um modelo que "corrige" `tem muita gente` para `há muita gente` sem ter sido pedido está errado, não certo.
  → Isto reforça, com base descritiva, a guarda que o doc 04 já tinha identificado por outro caminho: a classe **"falso erro"** (pares em que *as duas formas estão certas*, como `fim de semana`×`final de semana`) é o antídoto contra o modo de falha típico de quem só treina em pares errado→certo — o **corretor paranoico**. A §2 amplia essa lista de "falsos erros" muito além do que o material didático registra, porque a maior parte do que a gramática de concurso chama de erro é, descritivamente, **variação de registro**.

---

## 8. Veredito honesto

**O que este estudo entrega de fato:**

1. A norma brasileira **não é uma incógnita** — está estabilizada desde 2016, o conjunto de mudanças do AO90 é pequeno (~0,8% das palavras) e enumerável. Isso é uma boa notícia: **é codificável como filtro determinístico**, não precisa ser "aprendido" estatisticamente pelo Bee.
2. O achado de maior valor **não é linguístico, é de licença**: o par **LanguageTool + hunspell pt-BR** (ambos LGPL) entrega simultaneamente a matéria-prima de pares errado→certo e o verificador que o estudo anterior exigia. Isso encurta o caminho mais que qualquer gramática em PDF.
3. 🔴 O achado que mais **muda o plano imediato** é o de §2.2: **parte do catálogo de erros herdado dos livros é disputa entre normativistas, não erro.** `namorar com` e `visar` são corretos para uma autoridade e errados para outra; `assistir o` está no Houaiss como uso culto. Gerar esses como pares `errado→certo` seria injetar no Bee exatamente o defeito que o projeto declarou ser o pior possível — e viria com aparência de rigor, porque veio de livro de gramática.
4. O achado que mais **muda a conversa do projeto** é o **Tucano-160m**: 162M params, PT nativo, 200B tokens, Apache 2.0, com benchmarks publicados. O Bee agora tem um par honesto, e a diferença entre eles é **20× em token, não em ideia**.

**O que este estudo NÃO resolve, e não vou fingir que resolve:**

- **Não confirmei licença** de PortiLexicon-UD, VOC, Canarim, nem o volume PT do Tatoeba, nem o nº de sentenças do dataset GEC. Estão marcados.
- **Não consegui fonte primária da ABL** (site bloqueia bot). Os números do VOLP vêm de imprensa concordante — confiança alta, mas é segunda mão.
- **A ambiguidade de licença do Carolina e a cadeia quebrada GigaVerbo→CrawlPT→brWaC são problemas reais e não resolvidos.** Se o Bee for publicado, alguém precisa decidir isso com mais rigor do que uma pesquisa web dá.
- **Não há BLiMP-PT.** Isso é oportunidade, mas também significa que **não existe hoje uma medida pronta** para a coisa que este documento defende ensinar. Vai ter que ser construída.
- **Três fontes primárias bloquearam acesso automatizado:** `academia.org.br` (ABL/VOLP), `michaelis.uol.com.br` e `dicio.com.br` (403), e o `planalto.gov.br` caiu (ECONNRESET) nas duas leis mais citadas. Consequência prática: **todo "não dicionarizado" da §3 significa "não achei no Priberam nem no Aulete"** — as duas fontes mais relevantes para o PT-BR ficaram de fora. E o texto da Lei 15.263/2025 foi lido em **reprodução de terceiros**.
- **Lacunas específicas ainda abertas** (todas marcadas no corpo): nº de verbetes do VOLP (370 mil × 382 mil); licença de PortiLexicon-UD, VOC e FineWeb-2; nº de sentenças do dataset GEC; frequência medida de mesóclise, "fazem X anos" e "a gente vamos"; regência de "ir em/na"; percentuais regionais de tu/você; nota escrita institucional da ABL; qualquer parecer da Academia das Ciências de Lisboa; se a Lei 15.263/2025 alcança ensino e material pedagógico (o Ciberdúvidas afirma que sim, **o texto do art. 5º que li não confirma**).

**A recomendação que eu sustento:** ensinar gramática ao Bee é bom uso da capacidade de um 151M — mas **a primeira entrega tem que ser a régua (BLiMP-PT), não o dado.** O projeto já gastou um ciclo descobrindo que 2,6× mais token não movia o bpb; o risco simétrico agora é gastar outro ciclo gerando 30k pares sintéticos sem ter como saber se adiantaram. Medir primeiro custa pouco e protege o resto.

**As duas decisões que ficam com o dono do projeto** (e que este documento deliberadamente não toma):

| Decisão | Por que não pode ficar implícita |
|---|---|
| **1. Qual registro o Bee escreve** (norma culta escrita brasileira? jornalismo? redação oficial? coloquial?) | Determina o que conta como "certo" em **todo** par errado→certo e em **todo** item do BLiMP-PT. Se ficar implícita, o alvo será "o que sobrou no corpus" — que é uma escolha também, só que não deliberada |
| **2. Como o Bee trata `elu`/`todes`/`-e`** (erro a corrigir · forma válida · reconhece mas não produz) | §4.6. Se ficar implícita, uma posição política acaba **embutida dentro de uma métrica técnica**, onde fica invisível e difícil de reverter |

**A ressalva final, que é a mais importante deste documento:** a §2 mostra que "português correto" não é um alvo único — são **três** (norma-padrão, norma culta, normas populares), e nem o jornalismo brasileiro é internamente coerente sobre qual segue: o manual do Estadão faz concessões nomeadas em alguns pontos ("pronome entre dois verbos… não é mais possível desprezar") e mantém a norma tradicional em outros, **seletivamente**.

O Bee vai ter que escolher **um registro** — provavelmente a **norma culta escrita brasileira**, que não é a gramática de concurso nem a fala coloquial. Essa escolha é do dono do projeto, e **é uma decisão de produto, não de linguística.** Ela deve ser tomada explicitamente e escrita em algum lugar, porque todo o resto — que par é "certo", que frase é "erro", o que o BLiMP-PT mede — depende dela. A §2.5 já oferece essa escolha pronta em quatro linhas; falta alguém assiná-la.

---

## Fontes principais

**Norma × uso (linguística descritiva):** [Bagno, *Traduzires*/UnB 2012](https://repositorio.unb.br/bitstream/10482/10546/1/ARTIGO_NormaLinguisticaHibridismo.pdf) · [Projeto NURC-RJ](https://nurcrj.letras.ufrj.br/historico.htm) · [Vieira & Corrêa 2017 (colocação)](https://www.scielo.br/j/lh/a/MRz3KQHsKSv6MTxNMFZ8XsS/) · [Zanellato et al. 2021 (objeto direto)](https://revistas.ufrj.br/index.php/diadorim/article/view/39476) · [Callou & Avelar 2000 (ter/haver)](https://periodicos.uff.br/gragoata/article/view/49038) · [Lopes 1998 (nós/a gente)](https://www.scielo.br/j/delta/a/KQmrjr5yGgL49JPWMSGGhSj/?lang=pt) · [Kersch 2008 (cujo)](https://www.scielo.br/j/delta/a/MpSzkr9PZrNYjwdZdGzmDbt/?format=html&lang=pt) · [Gravina & Brizola 2019 (futuro)](https://periodicos.ufmg.br/index.php/relin/article/view/27665) · [Bittencourt 2021 (PPC)](https://periodicos.ufsc.br/index.php/workingpapers/article/download/76855/47306/308469) · [Scherre (concordância)](http://periodicos.pucminas.br/index.php/scripta/article/view/12597) · [Scherre, Andrade & Catão 2021 (tu/você)](https://periodicos.ufc.br/revletras/article/view/71460) · [Barme 2005 (negação)](https://dialnet.unirioja.es/servlet/articulo?codigo=3420731) · [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/) · [Manual de Redação do Estadão (⚠️ edição pré-Acordo)](https://www.fmetropolitana.com.br/wp-content/uploads/2019/01/MANUAL-REDA%C3%87%C3%83O-ESTAD%C3%83O.pdf)
**Norma:** [AO90 — texto oficial (PDF)](https://www.priberam.pt/docs/AcOrtog90.pdf) · [Decreto 7.875/2012](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/decreto/d7875.htm) · [Wikipédia — AO90](https://pt.wikipedia.org/wiki/Acordo_Ortogr%C3%A1fico_de_1990) · [Observatório da Língua Portuguesa](https://observalinguaportuguesa.org/) · [Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/)
**VOLP/VOC:** [Agência Brasil (2021)](https://agenciabrasil.ebc.com.br/geral/noticia/2021-07/academia-brasileira-de-letras-lanca-nova-edicao-online-do-volp) · [Ciberdúvidas — mil novas palavras](https://ciberduvidas.iscte-iul.pt/atualidades/noticias/mais-mil-palavras-no-vocabulario-ortografico-da-lingua-portuguesa/3581) · [Instituto Camões — VOC](https://www.instituto-camoes.pt/sobre/comunicacao/noticias/apresentada-plataforma-do-voc)
**Recursos:** [HPLT v2](https://hplt-project.org/datasets/v2.0) · [GigaVerbo](https://huggingface.co/datasets/TucanoBR/GigaVerbo) · [Tucano-160m](https://huggingface.co/TucanoBR/Tucano-160m) · [Carolina](https://huggingface.co/datasets/carolina-c4ai/corpus-carolina) · [LanguageTool](https://github.com/languagetool-org/languagetool) · [VERO pt-BR](https://github.com/LibreOffice/dictionaries/blob/master/pt_BR/README_pt_BR.txt) · [UD Bosque](https://github.com/UniversalDependencies/UD_Portuguese-Bosque) · [OpenWordnet-PT](https://github.com/own-pt/openWordnet-PT) · [PortiLexicon-UD](https://portilexicon.icmc.usp.br/) · [Portuguese-NLP (lista)](https://github.com/ajdavidl/Portuguese-NLP) · [linguistic-datasets-portuguese](https://github.com/EticaAI/linguistic-datasets-portuguese)
**Eval:** [CALAME-PT](https://huggingface.co/datasets/NOVA-vision-language/calame-pt) · [CAPITU](https://arxiv.org/abs/2603.22576) · [GEC pt-BR](https://arxiv.org/abs/2306.15788) · [ALBA (pt-PT)](https://aclanthology.org/2026.propor-1.69/) · [BLiMP](https://arxiv.org/pdf/2011.04946) · [BabyLM](https://arxiv.org/html/2411.09587v1)
**Domínio público:** [PleIAs/Portuguese-PD](https://huggingface.co/datasets/PleIAs/Portuguese-PD) · [Wikisource PT](https://pt.wikisource.org/) · [Domínio Público (MEC)](https://www.dominiopublico.gov.br)
**Direito:** [Lei 9.610/1998, art. 8º](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) · [Lei 15.263/2025 — Linguagem Simples](https://www.lex.com.br/lei-no-15-263-de-14-de-novembro-de-2025/) · [ADI 7019 (via Dizer o Direito)](https://www.dizerodireito.com.br/2023/03/e-formalmente-inconstitucional-lei.html) · [Res. CNJ 376/2021](https://atos.cnj.jus.br/atos/detalhar/3765)
**Dicionários consultados:** [Priberam](https://dicionario.priberam.org/) · [Aulete](https://www.aulete.com.br/) — ⚠️ **ABL/VOLP, Michaelis e Dicio bloquearam acesso automatizado (403)**
