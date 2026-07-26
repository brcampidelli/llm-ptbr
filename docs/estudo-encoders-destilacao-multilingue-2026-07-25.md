# Estudo — encoders, destilação e multilíngue (16 links, 2026-07-25)

> Leva de papers clássicos da era encoder + destilação + multilíngue, lida **contra o estado real
> da COMEIA hoje**, não em abstrato. Formato: o que o paper mede → veredito para nós → ação.
> Regra do projeto: se o paper não muda uma decisão, ele é contexto, e eu digo isso.

---

## 🚨 1. mT5 — "accidental translation" É o nosso bug da `chat_ptbr`, com nome e receita

**Xue et al., 2020 — mT5, 101 idiomas** ([2010.11934](https://huggingface.co/papers/2010.11934))

O paper descreve, medido, exatamente o que gastamos uma sessão inteira descobrindo:

> modelo multilíngue afinado **só numa língua** passa a traduzir a resposta para essa língua
> quando recebe pergunta em outra. Eles chamam de **accidental translation**, e atribuem a
> "esquecer" como gerar texto na outra língua depois de ver só uma no fine-tune.

É a `chat_ptbr` em espelho: eles afinam em inglês e o modelo responde em inglês a perguntas em
outras línguas; nós afinamos em PT-BR e o modelo respondeu **em português a 10 de 12 perguntas em
inglês** (12/12 → 2/12). Nosso resultado não foi acidente nem bug de código: é um fenômeno
conhecido, e nós o reproduzimos.

**E há receita medida.** *Domain Preserving Training*: misturar a tarefa de pré-treino multilíngue
durante o fine-tune, na proporção **1:100** → reduz predições no idioma errado em **>70% relativo**.
O efeito é **maior nos modelos menores** — que é exatamente o nosso regime (4B).

**Veredito:** muda o custo da decisão que o Bruno tomou hoje. Eu disse "só sai retreinando com dado
multilíngue", sugerindo reconstrução do dataset. O paper diz que **1% de mistura** já corta 70% do
problema. Continuo achando que não vale retreinar a abelha de chat (o backbone já ganha dela), mas o
motivo agora é "não há ganho a capturar", **não** "o conserto é caro" — o conserto é barato.

**Ação (feita):** a abelha de extração já está sendo construída multilíngue desde o schema, com
datas e números dos 4 idiomas testados. Se o dado sair desbalanceado, aplico a mistura 1:100.

---

## 🎯 2. TAPEX — o padrão das nossas abelhas que funcionaram, publicado

**Liu et al., 2021 — Table Pre-training via Learning a Neural SQL Executor** ([2107.07653](https://huggingface.co/papers/2107.07653))

Em vez de caçar pares texto-tabela naturais (escassos), eles **sintetizam SQL executável** e treinam
o modelo a produzir o **resultado da execução**. WikiSQL 89,5%, WikiTableQuestions 57,5%.

**Veredito:** é a nossa tese, validada por fora. A `coder` funcionou porque o interpretador era o
juiz (+40 pp). A `agentica` funcionou porque o validador de JSON era o juiz (24/24). A `chat_ptbr`
falhou porque não havia juiz possível. TAPEX diz o mesmo: **sinal executável > dado natural
escasso.** Reforça que o critério de escolha da 4ª abelha (extração, com groundedness verificável)
está certo — e sugere **SQL** como 5ª candidata forte, com o mesmo mecanismo.

---

## ⚠️ 3. A objeção incômoda: a abelha de extração deveria ser um ENCODER?

**BERT** ([1810.04805](https://huggingface.co/papers/1810.04805)) · **RoBERTa**
([1907.11692](https://huggingface.co/papers/1907.11692)) · **ALBERT**
([1909.11942](https://huggingface.co/papers/1909.11942)) · **BART**
([1910.13461](https://huggingface.co/papers/1910.13461))

Extração estruturada é, classicamente, tarefa de **encoder**: classificação de token / extração de
span. Um encoder de 110M–300M resolve NER e slot-filling com qualidade alta, roda em CPU, e custa
**~1/40 do nosso backbone de 4B**. RoBERTa mostrou que BERT estava subtreinado (mais dados + batch
maior + sem NSP → ganho grande sem mudar arquitetura). ALBERT mostrou que dá para cortar parâmetros
agressivamente (fatoração do embedding + parâmetros compartilhados) mantendo qualidade.

**A pergunta honesta que isso levanta contra o meu próprio plano:** se um encoder pequeno faz
extração melhor e mais barato, por que gastar um adapter de 4B nisso?

**Minha resposta, e onde ela é frágil:**
- A favor do decoder na comeia: **schema aberto**. Um encoder treinado para NER extrai as entidades
  que viu no treino; nossa abelha recebe o schema **no prompt** e extrai campos que nunca viu.
  Trocar de schema é editar um JSON, não retreinar. Para a COMEIA — 1 backbone + N adapters, schemas
  do usuário — isso importa.
- A favor do decoder: **zero infraestrutura nova**. Reusa backbone, hot-swap, roteador, pipeline.
  Um encoder seria o segundo modelo separado (o primeiro é o multimodal da Fase 4).
- ⚠️ **Onde sou frágil:** nunca medimos. Se o volume de produção for schema fixo e alto, o encoder
  provavelmente ganha em custo por documento, e eu estaria defendendo elegância arquitetural contra
  economia real.

**Ação registrada (não feita):** quando a abelha de extração tiver número, medir contra um baseline
de encoder num schema fixo. Se o encoder ganhar em custo/qualidade nesse recorte, a comeia deveria
ter as duas rotas — encoder para schema fixo de alto volume, adapter para schema aberto.

BART é o meio-termo (encoder-decoder, denoising) e é a arquitetura do próprio TAPEX — relevante se
formos para SQL/tabela.

---

## 4. DistilBERT — o que NÃO podemos copiar, e por quê

**Sanh et al., 2019** ([1910.01108](https://huggingface.co/papers/1910.01108)) ·
[repo de destilação da HF](https://github.com/huggingface/transformers-research-projects/tree/main/distillation)

40% menor, 60% mais rápido, **97% da capacidade** do BERT. Loss tripla: KL sobre os *soft targets*
do professor + MLM + **cosine** alinhando os hidden states. A ablação diz que as duas perdas de
destilação é que sustentam o resultado; tirar o MLM quase não muda.

**Veredito — distinção que importa e que é fácil confundir:** isso é **destilação de logits**
(*task-agnostic*, professor e aluno da mesma família, acesso aos estados internos). **Nós não
fazemos isso e não podemos:** nosso "professor" é um modelo aberto atrás de uma API que devolve
**texto**, não distribuição sobre vocabulário — e é de outra família/tokenizador. O que fazemos é
**destilação de sequência** (treinar nas saídas geradas). São coisas diferentes com o mesmo nome, e
os ganhos do DistilBERT **não transferem** para o nosso setup.

O que transfere: a ideia da **loss de cosseno**, que é um sinal mais rico que só o token seguinte —
mas exigiria professor local com hidden states acessíveis. Fica como possibilidade **se** um dia
rodarmos um professor aberto localmente.

---

## 5. ELECTRA — o princípio que já validamos sem saber

**Clark et al., 2020** ([2003.10555](https://huggingface.co/papers/2003.10555))

Em vez de mascarar 15% dos tokens, detecta token substituído em **100%** das posições. Sinal em
todos os tokens em vez de numa fração → ELECTRA-Small em 1 GPU/4 dias faz 79,9 GLUE contra 75,1 do
BERT-Small no mesmo compute, e supera o GPT com **30× menos** compute.

**Veredito:** não vamos pré-treinar, então a técnica não se aplica. Mas o **princípio** é o mesmo
que nos custou caro aprender: descobrimos que **93,8% da nossa loss estava nos tokens do prompt**
(system de 928 tokens idêntico em 1.495 exemplos) — estávamos gastando o sinal onde não havia nada a
aprender, e a "queda de 94% na loss" era o modelo decorando o catálogo. ELECTRA é a mesma lição do
outro lado: **onde o sinal cai é mais importante que o tamanho do modelo.**

---

## 6. Curse of multilinguality — a restrição real da COMEIA

**XLM-R, Conneau et al., 2019** ([1911.02116](https://huggingface.co/papers/1911.02116))

De 7 para 15 idiomas há transferência positiva. Depois disso, com capacidade fixa, a interferência
domina: XNLI cai de **71,8% para 67,7%** ao ir de 7 para 100 idiomas. Mais capacidade compensa
(XLM-30 grande empata com XLM-7).

**Veredito para a comeia:** relevante para o *nosso* backbone de 4B cobrindo 201 idiomas — ele
**está** no regime de capacidade diluída. Isso reforça a leitura de hoje: o backbone puro ganhou da
`chat_ptbr` nos 4 idiomas **apesar** dessa diluição, o que diz que o adapter era ruim, não que o
backbone seja ótimo. E sugere que, se algum dia quisermos qualidade alta em um idioma específico, o
caminho é **adapter por idioma** (a comeia já é feita para isso) e não mais dado multilíngue
espremido no mesmo peso.

---

## 7. Contexto, sem ação

- **BlenderBot / Recipes for building an open-domain chatbot** ([2004.13637](https://huggingface.co/papers/2004.13637)) —
  mostra que, em chat, **escolhas de decodificação e mistura de habilidades pesam mais que tamanho**.
  Interessante, mas o Bruno acabou de decidir não investir em chat, e concordo — então isto fica
  arquivado, não acionado.
- **CLIP** ([2103.00020](https://huggingface.co/papers/2103.00020)) — alinhamento imagem-texto por
  contraste, zero-shot forte. Vira relevante na **Fase 4** (abelha multimodal, modelo separado ~9B).
  Hoje não muda nada.
- **[Docs do Transformers v5.14 (pt)](https://huggingface.co/docs/transformers/v5.14.0/pt/index)** —
  referência. Vale para checar API quando a v5 mudar coisa embaixo de nós (já nos mordeu uma vez:
  `apply_chat_template` passou a devolver `BatchEncoding` e quebrou o `hive`).

---

## Resumo — o que esta leva efetivamente mudou

| # | Achado | Efeito |
|---|---|---|
| 1 | **accidental translation (mT5)** tem nome e receita (mistura 1:100, −70%) | nosso bug é fenômeno conhecido; conserto é barato, mas o motivo de não retreinar chat continua sendo "não há ganho", não custo |
| 2 | **TAPEX**: sinal executável > dado natural | valida o critério da 4ª abelha; indica **SQL** como 5ª |
| 3 | **encoders** fazem extração por 1/40 do custo | ⚠️ objeção real ao plano atual — registrada para medir, não descartada |
| 4 | **DistilBERT** é destilação de *logits* | não transfere para o nosso setup; distinção registrada para não confundirmos de novo |
| 5 | **ELECTRA**: sinal em 100% dos tokens | mesma lição da nossa loss mascarada, por outro caminho |
| 6 | **curse of multilinguality** | o backbone está em capacidade diluída; adapter por idioma > mais dado multilíngue |
