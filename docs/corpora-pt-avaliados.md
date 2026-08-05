# Seis corpora em português avaliados como pool bruto — 2026-08-04

Pergunta desta avaliação: **quais destas fontes servem para montar o pool bruto de ~100B tokens**
que o plano do FineWeb-Edu-PT exige (`docs/fineweb-edu-pt.md`: filtrar em ~10% para chegar a ~10B
de alta qualidade). Não é levantamento bibliográfico — é escala e licença.

Conversão usada quando a fonte só dá palavras: **×1,4 token/palavra** (tokenizador do Bee, 32k).
Toda conversão está marcada como tal. Licença lida **na origem**, com a URL ao lado.

---

## 1. ⭐ Tabela de decisão

| # | fonte | tokens (Bee) | licença | confirmada? | baixa em massa? | variante | veredito |
|---|---|---:|---|---|---|---|---|
| 1 | **Corpus Carolina** (USP) | ~1,2–1,8B † | **CC BY-NC-SA 4.0** no distribuidor oficial; docs individuais com "licenças múltiplas" | ⚠️ **confirmada como PROBLEMÁTICA** — 3 rótulos oficiais diferentes | ✅ HF + PORTULAN | PT-BR (1970–) | 🔴 **NÃO USAR** — NC contamina, e o corpus não tem licença única, tem uma por documento |
| 1b | └ subconjunto `leg` + `jud` | ~0,3–0,5B † | atos oficiais → **fora da proteção autoral** (Lei 9.610/98, art. 8º, IV) | ⚠️ base legal sólida, rótulo do dataset ainda errado | ✅ mesmo download | PT-BR | 🟡 **INVESTIGAR** — única fatia do Carolina defensável perante auditoria |
| 2 | **Corpus do Português** (Davies) | ~3,5B † | licença paga (~US$395), **proíbe redistribuir ≥50.000 palavras** e proíbe produto comercial | ✅ confirmada | 💰 só comprando | 66% BR / 33% PT + AO/MZ | 🔴 **NÃO USAR** — a licença proíbe exatamente o que o Bee faz |
| 3 | **CBRAS** (Linguateca) | ~1,34B † | **NÃO CONFIRMADA** — nenhuma declaração em nenhuma página | ❌ ausente | ❌ **só consulta web** | PT-BR | 🔴 **NÃO USAR** — corpus de consulta é inútil para treino |
| 4 | **PleIAs/Portuguese-PD** | ~0,94B † | "domínio público"; ⚠️ **repo HF sem tag de licença** | 🟡 argumento sólido (>70 anos), fundamentação citada é frágil | ✅ parquet HF | **PT-PT pré-1884** | 🔴 **NÃO USAR** (já é 15% do v1; o estudo interno já mandou excluir) |
| 5a | **Madras1/corpus-ptbr-v1** — `real` | 5,33B | ODC-By 1.0 (herdada de C4 + FineWeb-2) | ✅ coerente | ✅ parquet HF | PT-BR | 🟡 **INVESTIGAR** — limpa, mas **redundante**: é Common Crawl que já usamos, e **já vem filtrado** |
| 5b | └ subset `synthetic` | 0,96B | tag diz `odc-by`; card admite ToS de Llama 3 / Gemma / gpt-oss | ⚠️ **cadeia quebrada, assumida pelo autor** | ✅ | PT-BR sintético | 🔴 **NÃO USAR** — viola a regra dura "nunca treinar com saídas de GPT/Gemini" |
| 6 | **Project Gutenberg** (pt) | ~0,1B ‡ | domínio público nos EUA; comercial liberado **removendo a marca PG** | ✅ confirmada | ✅ dump/mirror oficial | PT-PT + PT-BR, séc. XVI–XX | 🔴 **NÃO USAR** — legalmente limpa mas 0,1% do alvo, e ortografia pré-Acordo |

† conversão ×1,4 a partir de palavras/tokens declarados pela fonte · ‡ estimativa grosseira, ver §2.6

**Nenhuma das seis é aprovada como pool bruto.** Uma (5a) é aprovável mas não acrescenta material.

---

## 2. Uma seção por fonte

### 2.1 Corpus Carolina (USP / C4AI / LaViHD)

**Tamanho.** Três medidas oficiais divergentes, porque são versões diferentes:
- v1.2 "Ada": **823 milhões de tokens**, >2 milhões de textos, >11 GB — [sites.usp.br/corpuscarolina](https://sites.usp.br/corpuscarolina/)
- registro PORTULAN CLARIN: **1.296.641.822 tokens** — [portulanclarin.net](https://portulanclarin.net/repository/browse/carolina-general-corpus-of-contemporary-brazilian-portuguese-with-provenance-and-typology-information/f3751b34e36611ecaa5802420a870112f00a37650c304dbda703d85e14a2e945/)
- v2.0.1 "Bea" no HF: **2.108.999 instâncias, 15 GB** — [card HF](https://huggingface.co/datasets/carolina-c4ai/corpus-carolina)

⚠️ Os "11 GB / 823M tokens" dariam 13 bytes por token, o que é impossível para texto. O formato é
**XML TEI P5 com um `teiHeader` por documento** — a maior parte dos GB é metadado, não texto. Use a
contagem de tokens, nunca o tamanho em disco. Convertendo a contagem linguística para o tokenizador
do Bee (×1,4): **~1,2–1,8B tokens**.

**Distribuição por taxonomia** (v2.0.1, do card HF):

| código | taxonomia | instâncias | tamanho |
|---|---|---:|---:|
| `wik` | wikis | 957.501 | 5,3 GB |
| `dat` | datasets e outros corpora | 1.074.032 | 4,3 GB |
| `leg` | poder legislativo | 3.982 | 4,2 GB |
| `jud` | poder judiciário | 38.187 | 1 GB |
| `uni` | domínios universitários | 26.409 | 162 MB |
| `soc` | redes sociais | 8.862 | 49 MB |
| `pub` | obras em domínio público | 26 | 4,5 MB |

**Licença — o problema.** Ver §3.1. Resumo: o distribuidor oficial (PORTULAN CLARIN) diz
**CC BY-NC-SA**; a USP diz que o *cabeçalho* é CC BY-NC-SA e que os documentos têm "licenças
múltiplas... desde domínio público até restrições quanto ao uso comercial"; o HF traz a tag
`license: cc-by-4.0`. **NC reprova.** E mesmo sem NC, "licença por documento, observe cada uma"
é inauditável em 2,1 milhões de documentos — é o oposto do `MANIFEST.json` do Bee.

**Baixa em massa.** Sim: `load_dataset("carolina-c4ai/corpus-carolina")` com parâmetro `taxonomy`,
ou PORTULAN CLARIN. Suporta versionamento por `revision`.

**Variante / domínio / data.** PT-BR contemporâneo, 1970–2021. Web, jurídico, legislativo,
acadêmico, wikis, redes sociais. Época correta — é o único ponto forte da fonte.

🟡 **A fatia defensável.** `leg` (4,2 GB) + `jud` (1 GB) são atos oficiais do Estado brasileiro.
A Lei 9.610/98, **art. 8º, IV**, exclui expressamente de proteção autoral "os textos de tratados ou
convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais"
([Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) · [texto do inciso](https://www.jusbrasil.com.br/topicos/10629231/artigo-8-da-lei-n-9610-de-19-de-fevereiro-de-1998)).
Ou seja: a proteção não existe na origem, e o rótulo NC do compilador não pode criá-la.
Isso é auditável e defensável. Mas são **~0,3–0,5B tokens estimados** e o gênero é jurídico —
útil como *tempero*, inútil como pool.

---

### 2.2 Corpus do Português (Mark Davies)

**Tamanho.** O projeto declara **2,5 bilhões de palavras** no título do site
([corpusdoportugues.org](https://www.corpusdoportugues.org/)), divididos em Web/Dialects, Genre/Historical
e NOW. O Web/Dialects tem **1,0 bilhão de palavras**: 656M Brasil, 327M Portugal, 35M Angola,
32M Moçambique, coletadas em 2013–14 ([help/texts.asp](https://www.corpusdoportugues.org/web-dial/help/texts.asp)).
Convertendo o total ×1,4: **~3,5B tokens**.

⚠️ O site bloqueia acesso automatizado (HTTP 403 em `corpusdoportugues.org`, `corpusdata.org` e
`english-corpora.org`). Os termos foram lidos em **duas bibliotecas licenciadas**, que reproduzem o
contrato — fonte secundária, mas são as partes contratantes:

**Licença — reprovada, com clareza.** De
[UVA Library](https://library.virginia.edu/data/datasources/licensed/corpus-do-portugues) e
[Columbia University Libraries](https://guides.library.columbia.edu/linguistics/full-text-corpus-data):
- não se pode distribuir "substantial amounts of the full-text data (typically, a total of 50.000 words or more)" fora da organização licenciada;
- a mesma restrição alcança **dados derivados** — listas de frequência, n-gramas, concordâncias;
- na licença acadêmica: *"you cannot use the data to create software or products that will be sold to others"*;
- alunos de graduação não têm acesso;
- ⚠️ cada cópia recebe uma **alteração única de rastreio (fingerprint)** para identificar vazamento.

**Baixa em massa.** Existe, mediante compra (~US$ 395 por corpus, formatos: banco relacional,
word/lemma/PoS, texto por parágrafo). Irrelevante: a licença proíbe o uso pretendido.

**Veredito.** 🔴 Um modelo publicável treinado nisso é violação contratual direta, e o fingerprint
existe justamente para provar. Reprovada por licença, não por qualidade — o corpus é bom.

---

### 2.3 CBRAS — Corpus Brasileiro (Linguateca / AC/DC)

**Tamanho.** **959,2 milhões de palavras** (1.134,4 milhões de unidades)
([linguateca.pt/acesso/corpus.php?corpus=CBRAS](https://www.linguateca.pt/acesso/corpus.php?corpus=CBRAS) ·
[descrição](https://www.linguateca.pt/acesso/desc_corpus.php?corpus=CBRAS)). Convertendo ×1,4: **~1,34B tokens**.

**Licença. NÃO CONFIRMADA.** Nenhuma das páginas consultadas — a do corpus, a descritiva, e a
página geral do AC/DC ([linguateca.pt/acesso/](https://www.linguateca.pt/acesso/)) — traz qualquer
declaração de licença, copyright ou condições de uso. Coordenado por Tony Berber Sardinha
(GELC/LAEL/PUC-SP), financiado pela Fapesp. **Ausência de licença não é permissão.**

**⛔ Baixa em massa: NÃO EXISTE.** O AC/DC é uma **interface de consulta** — devolve concordâncias,
distribuição e frequências. O único download oferecido são **listas de frequência de unigramas**.
Não há dump do texto. A própria página avisa que "devido a variados tipos de processamento
automático, é possível que nem todo o material incorporado esteja disponível através do AC/DC".

**Variante / domínio.** PT-BR, escrito + falado transcrito. Acadêmico, jornalismo, literatura,
roteiros de cinema/TV, narração esportiva, bulas, religião (Bíblia), Wikipédia, técnico.
Anotado sintaticamente pelo PALAVRAS.

**Veredito.** 🔴 **Corpus de consulta é inútil para treino.** Mesmo se a licença fosse CC0, não há
o que baixar. Reprovada antes mesmo da questão jurídica.

---

### 2.4 PleIAs/Portuguese-PD

**Tamanho.** 7.840 títulos, **672.197.538 palavras**, 3,32 GB, ~2.000 livros por parquet
([card HF](https://huggingface.co/datasets/PleIAs/Portuguese-PD)). Convertendo ×1,4: **~941M tokens**.

**Licença.** O card afirma: *"The entire collection is in the public domain in all regions"*, com
critério declarado de **autor morto há mais de 70 anos**, e retenção exclusiva de títulos
**publicados antes de 1884** para limitar a verificação de direitos.
⚠️ **Dois pontos de atenção:**
1. O **repositório HF não tem tag de licença** — os metadados só trazem `region:us`. A alegação de
   domínio público vive apenas na prosa do card. Para auditoria, o rótulo estruturado não existe.
2. A fundamentação citada é o **art. 14 da Diretiva EU 2019/790**, que literalmente trata de
   "obra de arte visual" cuja proteção expirou. Aplicar isso a texto OCRizado é extensão
   interpretativa. O argumento **sólido** é o outro: prazo de 70 anos + publicação pré-1884, o que
   coloca as obras em domínio público em qualquer país de Berna. A conclusão se sustenta; a
   fundamentação escolhida, não.

**Baixa em massa.** Sim, parquet no HF. ⚠️ O Dataset Viewer está quebrado (500) e o próprio projeto
já registrou `CastError` no 5º parquet (`docs/corpus-v1-aprovado-2026-07-27.md`).

**Variante / data — o problema real.** Obras **pré-1884**, majoritariamente PT-PT do período
colonial. Isso é **duas reformas ortográficas antes do português atual** (1911 em Portugal, 1943/1971
no Brasil, Acordo de 1990). Todo o texto foi transcrito por OCR, com erros admitidos pelos autores.

**Veredito.** 🔴 Já é **15% do corpus v1** do Bee, e o estudo interno
`docs/estudo-curriculo/08-portugues-atual.md` já concluiu: *"Excluir. É a razão pela qual 'domínio
público' não é sinônimo de 'bom para o Bee'"*. Esta avaliação confirma. Não é candidata a pool novo.

---

### 2.5 Madras1/corpus-ptbr-v1

**Tamanho.** 8.399.857 documentos, ~4,84B palavras, **~6,29B tokens** declarados pelo autor
(fator 1,3 sobre palavras), 17,9 GB parquet (18,8 GB no export do Hub)
([card HF](https://huggingface.co/datasets/Madras1/corpus-ptbr-v1)).

| subset | docs | palavras | tokens (decl.) | composição |
|---|---:|---:|---:|---|
| `real` | 6.813.702 | ~4,10B | ~5,33B | C4-pt (3.070.868) + FineWeb-2-pt (3.742.834) |
| `synthetic` | 1.586.155 | ~739M | ~961M | gerado por Qwen 2.5/3, DeepSeek V3, **Gemma 3**, Llama 3, Mistral/Mixtral, GLM 4.5, Kimi K2, MiMo, **gpt-oss** |

**Licença — tag única sobre duas realidades.** A tag do repositório é `license: odc-by` para o
dataset inteiro. O próprio card contradiz a tag, com honestidade rara:

> "Subset `synthetic`: Os textos sintéticos foram gerados utilizando diversos LLMs (como Llama 3,
> Qwen, DeepSeek e Gemma). O uso destes dados sintéticos pode estar sujeito aos termos de uso ou
> licenças originais dos respectivos modelos geradores (ex: *Llama 3 Community License*, *Gemma
> Terms of Use*), que frequentemente estabelecem regras sobre o uso de seus outputs para trinar
> modelos comerciais concorrentes."

⛔ **Além da licença, o subset `synthetic` bate de frente com a regra dura do Bee.** A lista de
geradores inclui **Gemma 3 (Google)** e arquivos `synthetic_corpus_gptoss*` (**gpt-oss, OpenAI**).
O `assert_teacher_allowed()` reprova, e está certo.

⚠️ **O subset `real` é limpo, mas não acrescenta pool.** É C4-pt + FineWeb-2-pt — o Bee **já usa
`fineweb-2` cfg `por` como 34% do corpus v1**, e o C4 vem do mesmo Common Crawl. O material
genuinamente novo é a fatia de C4-pt, ~2,4B tokens estimados, de origem sobreposta.

⚠️ **E ele já foi filtrado.** O `real` passou por um filtro SBERT treinado com rótulos de
LLM-as-a-judge em 72k amostras, com corte em `média_ouro − 1σ`. Usar isso como "pool bruto" para
depois aplicar **nosso** corte de 10% é filtrar duas vezes com critérios diferentes — o segundo
filtro opera sobre uma distribuição já enviesada pelo primeiro, e o joelho medido em
`docs/fineweb-edu-pt.md` (calibrado em `fineweb-2` cru) deixa de valer.

**Veredito.** 🟡 `real` = licença OK, valor marginal. 🔴 `synthetic` = fora, por licença **e** por
regra do projeto.

---

### 2.6 Project Gutenberg (português)

**Tamanho. ~875 títulos em português.** Medido por paginação da busca `l.pt`: a página iniciando em
876 já não retorna resultados, e não há link "Next"
([gutenberg.org/ebooks/search/?query=l.pt](https://www.gutenberg.org/ebooks/search/?query=l.pt) ·
[browse/languages/pt](https://www.gutenberg.org/browse/languages/pt)).

⚠️ **Tokens: ~0,1B, e isto é estimativa grosseira.** O PG não publica contagem de palavras por
idioma. 875 livros × ~80k palavras/livro ≈ 70M palavras → ×1,4 ≈ **100M tokens**. Ordem de grandeza,
não medida. (Cuidado ao replicar: o parâmetro `languages=pt` na URL de busca **é ignorado** — o
filtro correto é `query=l.pt`. Com o parâmetro errado a busca devolve livros em inglês e a contagem
infla para >1.000.)

**Licença — a mais limpa das seis.** As obras são domínio público nos EUA. Da
[Permission How-to](https://www.gutenberg.org/policy/permission.html) e da
[License](https://www.gutenberg.org/policy/license.html): uso não-comercial não requer permissão; a
restrição incide sobre a **marca registrada** "Project Gutenberg", não sobre o texto — removendo
todas as referências à marca (o cabeçalho e o rodapé), o uso comercial é livre. Para treino, isso é
uma operação de limpeza trivial e já necessária.

**Baixa em massa.** Sim — dumps e mirrors oficiais (`gutenberg.org/cache/epub/`, rsync).

**Variante / data — o mesmo defeito do Portuguese-PD.** Mistura PT-PT e PT-BR, do século XVI ao
início do XX: Camões, Camilo Castelo Branco, Eça de Queirós, José de Alencar, autores do *Orpheu*.
Ortografia pré-1911 e pré-Acordo.

**Veredito.** 🔴 Licença impecável, escala irrelevante (0,1% do alvo) e época errada. Se o objetivo
fosse um subcorpus literário de prestígio, entraria; para pool bruto, o custo de oportunidade é
péssimo — a mesma hora de engenharia rende 1.000× mais token na rota web.

---

## 3. Cadeias de licença

O alerta do `README.md` ("rótulo de licença não é prova") se repete. **Duas das seis fontes** têm
cadeia quebrada, e uma terceira tem lacuna de rótulo.

### 3.1 ⚠️ Carolina — o mesmo padrão do brWaC → GigaVerbo, agora com a mesma equipe nos dois lados

| onde | o que diz | URL |
|---|---|---|
| USP (homepage) | cabeçalho **CC BY-NC-SA 4.0** | [sites.usp.br/corpuscarolina](https://sites.usp.br/corpuscarolina/) |
| USP (página de download) | *"Há desde licenças amplas de domínio público até licenças de compartilhamento parcial com **restrições quanto ao uso comercial**"* — por documento | [sites.usp.br/corpuscarolina/corpus](https://sites.usp.br/corpuscarolina/corpus/) |
| PORTULAN CLARIN (distribuidor oficial) | **CC-BY-NC-SA** para o recurso | [portulanclarin.net](https://portulanclarin.net/repository/browse/carolina-general-corpus-of-contemporary-brazilian-portuguese-with-provenance-and-typology-information/f3751b34e36611ecaa5802420a870112f00a37650c304dbda703d85e14a2e945/) |
| Hugging Face — corpo do card | *"texts assembled in various digital repositories, whose licenses are multiple and therefore should be observed... The Carolina **headers** are licensed under CC BY 4.0"* | [card HF](https://huggingface.co/datasets/carolina-c4ai/corpus-carolina) |
| Hugging Face — **metadados** | `license: cc-by-4.0` **para o dataset inteiro** | mesmo arquivo, YAML front-matter |

**O que aconteceu.** O texto do card é tecnicamente correto: só os *cabeçalhos* são CC BY 4.0. Mas o
campo `license:` do front-matter — que é o que a interface do HF exibe, o que a API devolve e o que
qualquer pipeline automatizado lê — declara **CC BY 4.0 para o corpus todo**. Um `NC` virou `BY` na
travessia entre o repositório institucional e o Hub, e o texto que ressalva isso fica abaixo da
dobra.

**Diferença em relação ao caso brWaC.** Lá, três organizações diferentes; a permissividade cresceu a
cada elo e ninguém era responsável pelo todo. Aqui é **a mesma equipe** publicando o mesmo corpus com
dois rótulos incompatíveis em dois lugares oficiais. Não é malícia — é o front-matter do HF não ter
casa para "licença varia por documento". Mas o efeito para quem audita é idêntico: **quem confiar na
tag do HF vai treinar em material NC achando que é BY.**

### 3.2 ⚠️ Madras1 — cadeia quebrada, mas declarada pelo próprio autor

```
Common Crawl (ToS do CC + copyright das páginas de origem)
   ├─► C4 (ODC-By) ─────────────┐
   └─► FineWeb-2 (ODC-By) ──────┼─► subset `real` ── ODC-By ✅ coerente
                                │
LLMs proprietários/abertos ─────┴─► subset `synthetic` ── ToS de cada modelo
   (Gemma 3, Llama 3, gpt-oss,        (Gemma Terms of Use, Llama 3 Community
    Qwen, DeepSeek, Mistral…)          License — restringem treinar concorrente)
                                             │
                        tag do repositório: `license: odc-by` para os dois ✗
```

O card **admite** a divergência por escrito. Isso é muito melhor que o caso Carolina — mas a tag
continua sendo o que as ferramentas leem. **Consumir o dataset inteiro pela tag herda a violação.**

### 3.3 🟡 PleIAs/Portuguese-PD — lacuna de rótulo

Não é cadeia quebrada, é **ausência de elo**: o repositório HF não declara nenhuma licença nos
metadados (só `region:us`). A alegação de domínio público existe apenas em prosa, e a base jurídica
citada (art. 14 da Diretiva 2019/790, sobre *obra de arte visual*) não é a que efetivamente sustenta
o caso — o que sustenta é o prazo de 70 anos e a publicação pré-1884. A conclusão está certa pelo
motivo errado, o que é ruim numa auditoria.

---

## 4. ⭐ Quanto isso soma — e por que não fecha

**Somando tudo, ignorando licença e sobreposição** (o teto teórico absoluto):

| fonte | tokens (Bee) |
|---|---:|
| Corpus do Português | ~3,5B |
| Madras1 (completo) | ~6,3B |
| CBRAS | ~1,3B |
| Carolina | ~1,3B |
| PleIAs Portuguese-PD | ~0,9B |
| Gutenberg pt | ~0,1B |
| **teto teórico** | **~13,4B** |

**13,4% do alvo de 100B.** E esse teto é fictício, porque há sobreposição pesada: o `dat` do Carolina
*é* "datasets e outros corpora", o CBRAS inclui Wikipédia, e o `real` do Madras1 é o mesmo Common
Crawl que o Bee já usa.

**Agora aplicando os filtros de verdade** — licença limpa **E** download em massa **E** não redundante
com o corpus atual **E** época/variante certas:

| fonte | passa? | token novo e utilizável |
|---|---|---:|
| Corpus do Português | ❌ licença proíbe | 0 |
| CBRAS | ❌ sem download | 0 |
| PleIAs-PD | ❌ época errada; já está no corpus | 0 |
| Gutenberg pt | ❌ época errada | 0 |
| Madras1 `synthetic` | ❌ ToS de modelo + regra do projeto | 0 |
| Carolina (geral) | ❌ NC / licença por documento | 0 |
| **Carolina `leg`+`jud`** | 🟡 art. 8º IV | **~0,3–0,5B** |
| **Madras1 `real`** | 🟡 limpo mas redundante e pré-filtrado | **~2,4B** (só a fatia C4-pt) |
| | **total realista** | **~2,4–2,9B** |

### ⛔ O resultado: **~2,4–2,9B contra um alvo de 100B. Menos de 3%.**

E mesmo esses 2,9B são de qualidade duvidosa para o propósito: os 2,4B do Madras1 são Common Crawl
reprocessado e **já filtrado por outro critério**, o que quebra a calibração do corte de 10%; os
0,5B do Carolina são jurídico puro.

**A leitura honesta: curadoria de corpus em português não fecha a conta, e não chega perto.**
Todo o esforço acadêmico de corpus em PT — USP, PUC-SP, Linguateca, Davies, PleIAs — soma pouco mais
de 13B tokens brutos, dos quais quase nada é licenciável para um modelo publicável. **Isto é
resultado útil, não fracasso da busca:** encerra a hipótese de que existe um acervo curado de PT
esperando ser encontrado. Não existe.

### ✅ E a rota web fecha sozinha

Medição direta do `fineweb-2` config `por_Latn` (`hf://datasets/HuggingFaceFW/fineweb-2/data/por_Latn/train`):

- **66 arquivos parquet**, somando **275,9 GB comprimidos** (52 arquivos de ~4,85 GB + cauda menor)
- convertendo com a razão do próprio projeto (**~3,24 bytes de texto por token**, derivada dos
  9,87B tokens do v3) e assumindo compressão parquet entre 1× e 3×: **~85B a ~255B tokens**
- ⚠️ faixa larga porque a razão de compressão não foi medida — mas **até o piso da faixa é ~10×
  todo o esforço de curadoria acima**, e o topo cobre o alvo de 100B com folga de 2,5×
- licença **ODC-By 1.0** ([card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2)) — a mesma
  que o Bee já usa e já auditou

Reserva com licença ainda mais forte: **HPLT 2.0 cleaned**, `license: cc0-1.0`, com português entre os
191 idiomas ([card](https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned)) — e já existe HPLT 3.0. O
subconjunto `monoHPLT-PT` (CC0) já estava marcado no `README.md` como a fatia limpa do GigaVerbo.

---

## 5. Recomendação priorizada

**1. ⭐ Ir para o `fineweb-2 por_Latn` completo, agora. Não coletar mais nada antes disso.**
É a única fonte medida que sozinha cobre o alvo de 100B, com licença já auditada pelo projeto.
A escala existe na fonte — o gargalo nunca foi encontrar dado, foi processá-lo.
**Primeira ação concreta:** medir a razão real texto/parquet em **um** arquivo (~4,85 GB) e converter
a faixa 85–255B numa estimativa firme. É uma tarefa de minutos e fecha a última incerteza deste
documento.

**2. Medir antes de baixar 276 GB.** A regra do projeto ("medir antes de acreditar") aplica-se aqui
com força: 276 GB é volume que compromete disco, banda e tempo. Determinar quantos parquets são
necessários **antes** de baixá-los, não depois.

**3. `monoHPLT-PT` (CC0) como segunda fonte, se precisar de mais volume ou de diversificar snapshot.**
CC0 é licença mais forte que ODC-By, e a fonte é Internet Archive + Common Crawl — snapshots
parcialmente diferentes do FineWeb-2, o que ajuda contra deduplicação cruzada.

**4. 🟡 Carolina `leg` + `jud` — só se sobrar tempo, e como tempero, não como pool.**
~0,3–0,5B tokens de PT-BR contemporâneo formal, com base jurídica sólida (art. 8º IV) que sobrevive
a auditoria melhor que o rótulo do próprio dataset. Registrar no `MANIFEST.json` a base legal, **não**
a tag do HF. Valor real: diversidade de registro formal, que o web crawl tem pouco. Custo: baixo.
Prioridade: baixa — não muda a conta de escala.

**5. ⛔ Não investir mais hora em curadoria de corpora acadêmicos de PT.** Esta avaliação cobriu os
seis maiores e o saldo foi <3% do alvo. O padrão é consistente: os grandes são de consulta (CBRAS),
pagos com licença restritiva (Davies), ou de licença fragmentada por documento (Carolina). O retorno
marginal de procurar o sétimo é muito baixo.

**6. Se algum dataset novo aparecer, aplicar o teste das três perguntas** que separou tudo aqui:
&nbsp;&nbsp;(a) tem **dump**, ou é interface de consulta?
&nbsp;&nbsp;(b) a licença **na origem** — não a tag do agregador — permite treinar **e publicar**?
&nbsp;&nbsp;(c) é material **novo**, ou é o Common Crawl que já temos com outro nome?
Nas seis fontes avaliadas, **cada uma morreu em pelo menos uma dessas três**.

---

## Apêndice — URLs consultadas

| fonte | URLs |
|---|---|
| Carolina | [sites.usp.br/corpuscarolina](https://sites.usp.br/corpuscarolina/) · [/corpus/](https://sites.usp.br/corpuscarolina/corpus/) · [PORTULAN CLARIN](https://portulanclarin.net/repository/browse/carolina-general-corpus-of-contemporary-brazilian-portuguese-with-provenance-and-typology-information/f3751b34e36611ecaa5802420a870112f00a37650c304dbda703d85e14a2e945/) · [HF card + README.md](https://huggingface.co/datasets/carolina-c4ai/corpus-carolina) |
| Corpus do Português | [corpusdoportugues.org](https://www.corpusdoportugues.org/) (403 a bot) · [help/texts.asp](https://www.corpusdoportugues.org/web-dial/help/texts.asp) · [UVA Library](https://library.virginia.edu/data/datasources/licensed/corpus-do-portugues) · [Columbia Libraries](https://guides.library.columbia.edu/linguistics/full-text-corpus-data) |
| CBRAS | [corpus.php?corpus=CBRAS](https://www.linguateca.pt/acesso/corpus.php?corpus=CBRAS) · [desc_corpus.php?corpus=CBRAS](https://www.linguateca.pt/acesso/desc_corpus.php?corpus=CBRAS) · [linguateca.pt/acesso/](https://www.linguateca.pt/acesso/) |
| PleIAs Portuguese-PD | [card HF + README.md](https://huggingface.co/datasets/PleIAs/Portuguese-PD) |
| Madras1 | [card HF + README.md](https://huggingface.co/datasets/Madras1/corpus-ptbr-v1) |
| Gutenberg | [browse/languages/pt](https://www.gutenberg.org/browse/languages/pt) · [search?query=l.pt](https://www.gutenberg.org/ebooks/search/?query=l.pt) · [policy/permission.html](https://www.gutenberg.org/policy/permission.html) · [policy/license.html](https://www.gutenberg.org/policy/license.html) |
| base legal BR | [Lei 9.610/98 — Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) · [art. 8º](https://www.jusbrasil.com.br/topicos/10629231/artigo-8-da-lei-n-9610-de-19-de-fevereiro-de-1998) |
| rota recomendada | [fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) (listagem `por_Latn` via API do Hub) · [HPLT 2.0 cleaned](https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned) |
