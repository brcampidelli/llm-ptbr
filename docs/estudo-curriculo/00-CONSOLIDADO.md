# Os 91 PDFs servem para ensinar o Bee? — consolidado (2026-08-04)

Estudo multiagente: 10 agentes, 91 PDFs (2,9 GB), 5 links de arXiv e pesquisa web do estado de
2026 em geopolítica, português, matemática, ciência, biologia, história, geografia, química e
física. Relatórios individuais em `01-` a `10-` nesta pasta.

---

## Resposta curta

**Os livros, não. O currículo, sim — e ele é público.**

O acervo falha por quatro motivos independentes, e qualquer um deles já bastaria:

| motivo | evidência |
|---|---|
| **Licença** | protegidos (Scribd). E as 3 obras de licença aberta do lote são NC/SA — contaminam o Bee do mesmo jeito |
| **Arquivo quebrado** | 11 são imagem pura; 1 está **vazio**; 1 truncado; 2 alternam PT-PT e PT-BR no mesmo parágrafo |
| **Escala** | tudo somado dá ~0,1–1% do corpus. O Gate 2 já mostrou que fator pequeno de token não move nada |
| **Conteúdo datado** | 24 fatos que os livros ensinam e que hoje se sabem errados |

E a substituição é melhor que o original: **a BNCC está fora do regime autoral** e traz 1.583
códigos de habilidade — um índice oficial e granular do que se deve saber. É o esqueleto que a
gente ia extrair dos livros, só que legal, limpo e completo.

---

## O que mudou no diagnóstico do projeto

Este estudo **refutou duas hipóteses que eu mesmo havia levantado** sobre o gap de bpb
(3,457 do Bee contra 2,010 do SmolLM2). Ambas caíram por leitura de fonte primária, não por
teoria:

**Geometria — refutada.** Os `config.json` do `SmolLM2-135M` e do `MobileLLM-125M` são
idênticos ao do Bee: 30 camadas · d_model 576 · 9q/3kv · vocab 32k · seq 2048. O modelo que faz
2,010 tem exatamente a geometria do Bee. A razão "19,2 contra 85–130" veio de modelos 10–100×
maiores e não vale nesta escala.

**LR — refutado.** Step Law (~3.700 modelos): `η* = 1,79·N^-0,713·D^0,307` → para N=151M e
D=9,87B dá **3,09e-3**. Usamos 3e-3. Erro de 3%.

**E apareceu o par honesto que faltava:** o **Tucano-160m** (162M params, PT nativo, Apache 2.0)
foi treinado em **200B tokens**. Mesma escala, mesma língua. A distância para o Bee é **20× em
token — não em arquitetura**.

**A releitura correta do Gate 2:** sob `L(D)=E+A·D^-0,28`, ir de 3,74B → 9,87B deveria cortar
23,8% da loss redutível. Observamos 0,1% — **200× abaixo**. Não é "mais token não resolve": é
que **o Bee não está na curva**. Algo satura antes.

**O medidor foi auditado e está sadio:** `carregar_holdout` trunca em `max_chars=4000` de
propósito, para caber em 2048 tokens nos dois tokenizadores, então o corte `[:, :seq_len]` não
dispara e não enviesa a comparação (seria bug real se alguém subisse `max_chars`);
`prepare_data.py:96` mantém os shards 7/23/41 inteiros fora do treino. **O gap é real.**

---

## O fundamento legal, agora com artigo

O que eu havia afirmado de manhã como princípio está escrito na Lei 9.610/98:

- **art. 8º, IV** — não são protegidos *"os textos de tratados ou convenções, leis, decretos,
  regulamentos, decisões judiciais e demais atos oficiais"*. A **BNCC é o Anexo da Resolução
  CNE/CP nº 2/2017**, cujo art. 1º declara o Anexo como parte do ato normativo. Logo: fora do
  regime autoral. (O PDF de 600 p. não tem ficha catalográfica, "©" nem cláusula de reprodução.)
- **art. 8º, I** — *"conceitos matemáticos como tais"* não são protegidos.
- **art. 7º, §3º** — *"no domínio das ciências, a proteção recairá sobre a forma literária, não
  abrangendo o conteúdo científico"*. É a base legal exata de **reescrever é legal, copiar não**.

⚠️ **Duas armadilhas verificadas:**
1. O rodapé de todo site gov.br declara **CC BY-ND** (NoDerivatives). Não afeta a BNCC — rodapé
   não recria proteção que a lei exclui — mas **afeta os itens de prova do ENEM**, que são obra
   autoral. Prova pode ser usada para **avaliar** (não é distribuir derivado), não para gerar
   derivado distribuível.
2. **Microdados do ENEM NÃO são CC-BY.** A Política de Dados Abertos do INEP lista "atribuir
   licença CC-BY" na coluna *"o que melhorar"* — é ação pendente. Status: **NÃO CONFIRMADO**.
   Resolver com pedido via LAI ao SIC do INEP: 20 dias, custo zero, vira documento auditável.
3. **Cadeia de licença quebrada no GigaVerbo:** brWaC declara *"solely for academic research…
   not for any commercial applications"* → CrawlPT não declara licença → GigaVerbo aparece como
   CC BY 4.0. Alguém relicenciou o que não podia. **Usar só o subconjunto `monoHPLT-PT` (CC0).**

---

## Triagem por matéria

| matéria | veredito | por quê |
|---|---|---|
| **Raciocínio lógico** | ⭐⭐⭐ **SIM** | gerador determinístico, resposta verificável por código |
| **Química** | ⭐⭐ **SIM (esqueleto)** | par determinístico aos milhões: nome↔fórmula, NOX, balanceamento, A/Z/N |
| **Português** | ⭐⭐ **SIM, com auditoria** | padrão local e repetitivo — o que um 151M realmente aprende |
| **Geografia** | ⭐ parcial | enumerações com atributos sobrevivem sem mapa; alfabetização cartográfica não |
| **Biologia** | ⭐ parcial | genética e vias metabólicas rendem texto; anatomia depende de figura |
| **Física** | ❌ **NÃO** | depende de diagrama; o que sobra é conta de um passo — que o 151M imita e erra |
| **História** | ❌ **NÃO** | fontes escaneadas, e a parte útil (cronologia) está truncada do arquivo |
| **Geopolítica atual** | ⛔ **NÃO** | raciocínio causal sobre entidade ambígua no tempo + obsolescência |
| **Ciência de fronteira** | ⛔ **NÃO** | é feita de qualificadores, e o 151M descarta qualificador |
| **Software** | ❌ **NÃO** (como dado) | semente aberta é infinita (`the-stack-v2`); 6 arquivos defeituosos |

### O padrão que emergiu dos 10 relatórios

**O que serve ao Bee não é texto de livro — é gerador com resposta conferível por código.**

Lógica e química ganham pelo mesmo motivo: a resposta é **sorteada antes** do enunciado ser
escrito. Não há professor para alucinar, não há frase para copiar, não há o problema de "quem
gera não pode avaliar". Um dos PDFs de lógica tem 250 questões de banca das quais **só 4
dependem de figura**, com símbolos (∧ ∨ → ↔) íntegros e gabarito parseável; 10 de 12 moldes são
enumeráveis por código (tabela-verdade, De Morgan, silogismo categórico em 256 formas,
associação lógica por CSP, "quem mente" por enumeração 2ⁿ).

---

## Os quatro achados incômodos

**1. Desinformação gerada por IA, na primeira página de busca.** Três sites afirmavam que a
conjectura dos primos gêmeos foi provada em 2026 sob a GRH — falso, segue em aberto. Os mesmos
sites erravam a formalização da conjectura de Kepler.

**2. Um número falso quase entrou.** Fonte secundária afirmava tarifa dos EUA de 50% sobre o
Brasil; é eco do tarifaço de 2025. O confirmado (Agência Brasil, 24/07/2026) é 25% + 12,5% =
até 37,5%. Um scraper teria ingerido os 50% sem piscar.

**3. Parte do catálogo de erros de português é disputa, não erro.** `namorar com` e `visar` são
corretos para o Ciberdúvidas e errados para o manual do Estadão; `assistir o filme` está no
Houaiss como uso *"comum, mesmo pelas pessoas cultas"*. Gerar isso como par errado→certo injeta
regra que nem os gramáticos sustentam, **com aparência de rigor porque veio de livro**.
→ **Etapa bloqueante de auditoria antes de gerar qualquer par.**

**4. O acervo tem um viés de fonte, não só de opinião.** Não há nele **nenhuma** fonte de
geografia humana ou história econômica de perspectiva liberal, institucionalista ou
quantitativa. Não é sobre quem está certo: treinar com o acervo como está injeta um único ponto
de vista sem contraditório. Decisão do dono do projeto, tomada de olhos abertos.

---

## O que fazer — em ordem de retorno

**1. Medir tokens EFETIVOS vs nominais** (dedup MinHash). Custo: horas de CPU, zero GPU.
Se houver duplicata pesada, os "9,87B únicos" não são 9,87B e isso sozinho explica a saturação.

**2. Instituir gate pareado barato antes de todo run longo** (~5% do GPU-hora). Teria matado o
v3 por ~R$ 50 em vez de US$ 34 e 22 h.

**3. Replicar o FineWeb-Edu em português.** É a hipótese viva, e a magnitude bate: o FineWeb-Edu
descartou **91%** do corpus e subiu MMLU 33→37% e ARC 46→57%, igualando um baseline com 10×
menos tokens. Corpus menor e melhor, não maior.

**4. Gerar o midtraining/SFT a partir da BNCC.** 1.583 habilidades × formatos × públicos ×
ancoragens ≈ **357 mil documentos, ~320M tokens** (3,2% do corpus) — com o perfil exato que
faltou no v3, cujo gate de forma passou e o de conteúdo falhou.

**5. Construir os geradores determinísticos** (lógica e química) — o único material do acervo
com resposta verificável sem professor.

**6. Usar o ENEM como eval set.** ~3.750 itens públicos com gabarito oficial e **parâmetros de
TRI** — dá para ordenar currículo por dificuldade *medida*, coisa que nenhum livro tem.

**NÃO fazer:** mexer em geometria, mexer no LR de pico, ou rodar outro pré-treino "só com mais
dados".

---

## Sobre reescrever o conteúdo

O pedido original era reescrever cada livro como um professor especializado. O estudo mudou o
**alvo** da reescrita, não o método:

- reescrever 91 livros protegidos: ilegal como corpus, e ~1% do corpus mesmo se fosse legal;
- reescrever a partir das **1.583 habilidades da BNCC**: legal (art. 8º IV), completo, oficial,
  e dimensiona 320M tokens com dificuldade calibrável por TRI.

O método pedagógico continua valendo, e os agentes o extraíram dos autores — que é exatamente o
que a lei permite (art. 7º §3º: a proteção é da forma literária, não do conteúdo). Três moldes
que valem transplantar:

- **Pérez García (mecânica):** compreender sem calcular → planejar → calcular → conferir ordem
  de grandeza e dimensão.
- **Wade (orgânica):** mecanismo-tronco → variantes → resumo → heurística nomeada.
- **Gabarito comentado de banca:** não só a resposta certa, mas **por que cada distrator erra** —
  que já é estruturalmente um par instrução/resposta, e um negativo de DPO de graça.

⚠️ **Regra dura:** escrever a partir do esqueleto, **nunca traduzir**. Seis dos oito livros de
exatas e vários de biologia estão em espanhol; frase traduzida arrasta sintaxe espanhola e falso
cognato para dentro de um modelo que treinamos em português.
