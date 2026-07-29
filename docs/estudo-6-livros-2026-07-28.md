# Estudo — 6 livros de LLM / RAG / agentes (2026-07-28)

> Lidos em paralelo durante o pré-treino do Bee-150M (passo ~2.000/7.135). Sínteses completas em
> `~/.claude/refs/`, indexadas em `~/.claude/rules/knowledge-base-refs.md` — este documento é a
> **leitura de conjunto**: o que só aparece quando se lê os seis lado a lado.

## ⚠️ Antes do conteúdo: um achado sobre a FONTE

**A contagem de páginas informada estava errada nos 6 arquivos, sem exceção:**

| livro | páginas anunciadas | páginas reais |
|---|---:|---:|
| LangGraph Blueprint | 76 | **568** |
| AI Engineering Guidebook | 932 | **384** |
| RAG Architecture | 340 | **52** |
| Burkov — Hundred-Page LM | 250 | **209** |
| Farooq — Build an LLM App | 43 | **161** |
| Ozdemir — Quick Start LLMs | 40 | **132** |

E **4 dos 6 são materiais truncados**: o RAG Architecture é uma prévia com dois capítulos centrais
atrás de paywall (~65% de cobertura), o Farooq é um MEAP que **para no meio de uma frase** e nunca
escreveu o capítulo de RAG que prometeu seis vezes, o Ozdemir tem **6 dos 9 capítulos em branco**, e o
AI Engineering tem todo o código em screenshot (conceito capturado, código não).

Isso não é detalhe burocrático: significa que planejar tempo de estudo por "número de páginas do
Scribd" é planejar em cima de número inventado. **Vale conferir a contagem real antes de estimar.**

## Ranking honesto de valor

| # | livro | nota | para quê serve |
|---|---|---:|---|
| 1 | **Burkov — Hundred-Page LM** | **9/10** | ⭐ o único que fala do que o Bee faz agora |
| 2 | **AI Engineering Guidebook** | **8/10** | ⭐ mapa do campo inteiro; onde o Bee vai desembocar |
| 3 | RAG Architecture | 6,5/10 | vocabulário + régua de avaliação de RAG |
| 4 | LangGraph Blueprint | 4/10 | entender o modelo; **não adotar** a ferramenta |
| 5 | Farooq — Build an LLM App | 4/10 | 3 ideias aproveitáveis, resto superado |
| 6 | Ozdemir — Quick Start LLMs | 4/10 | checklist de meia hora p/ auditar o RAG |

Os três de baixo somados valem menos que qualquer um dos dois de cima. **Dois livros bons e quatro
medianos** é um resultado normal de um lote não-curado — e saber qual é qual já paga o estudo.

---

# ⭐ Os 3 consensos independentes

Quando livros que não conversam entre si dizem a mesma coisa, o sinal é forte.

## 1. Bi-encoder recupera barato → cross-encoder reordena caro — **4 dos 6 livros**

Ozdemir (2023), Farooq (2025), RAG Architecture e AI Engineering Guidebook chegam ao mesmo padrão por
caminhos diferentes, com 3 anos de distância entre o mais velho e o mais novo. Nenhuma outra técnica
tem essa convergência no lote.

A lógica: o bi-encoder compara vetores já calculados (rápido, aproximado); o cross-encoder lê pergunta
e documento **juntos** (caro, preciso). Usa-se o barato para pescar ~100 candidatos e o caro para
ordenar os 5 finalistas. **É a maior melhora de precisão por linha de código num RAG**, e é
justamente o passo que o AI Engineering diz que quase todo mundo pula.

→ **Ação: verificar se o RAG do PassaPro entrega os top-k direto ao Gemini sem reordenar.** Se sim,
esta é a melhoria de maior retorno disponível hoje em qualquer projeto do Bruno.

## 2. RAG alucina de três formas, e a métrica agregada não distingue nenhuma

O RAG Architecture nomeia as três causas: (a) o retriever não trouxe o contexto certo; (b) o LLM
recebeu o certo e **ignorou**; (c) o LLM pescou a informação errada **dentro** do contexto certo. As
três produzem a mesma resposta errada na tela.

⭐ **Isto é a lição da `chat_ptbr` outra vez, com outra roupa.** Em 2026-07-25 aquele adapter passou
por 7 benchmarks de múltipla escolha e foi declarado "não conclusivo" enquanto respondia em português
a perguntas em inglês 10 de 12 vezes. E é a mesma lição do paper `2607.22554` do estudo anterior
(acurácia agregada varia 0–5% enquanto 23% das respostas se contradizem). **Três fontes independentes,
o mesmo erro.**

→ **Ação:** medir retrieval separado de geração, e **logar o contexto recuperado junto com cada
resposta**. Sem esse log, o diagnóstico é impossível — é debugar às cegas por escolha própria.

## 3. Instruir explicitamente "responda somente com base no contexto"

Burkov e RAG Architecture, independentemente, apontam a mesma linha como o item mais esquecido do
prompt de RAG. É a instrução mais barata do sistema inteiro e uma das mais valiosas. O Burkov ainda
traz o argumento de negócio: o caso Air Canada, em que o chatbot inventou uma política de tarifa e a
empresa foi condenada a pagar.

---

# ⚠️ Os 4 confrontos com o que já fazemos

Aqui está o valor real do estudo. Sem diplomacia.

## 1. A geometria do Bee-150M: 30 camadas × 576 — ⚠️ risco real, mas **não mexer agora**

O Burkov tabula a razão `d_model / n_camadas` dos modelos reais: Llama 8B/70B/405B e Gemma 2 9B/27B
ficam **todos entre 85 e 130**. O Bee está em **19,2** — uma ordem de grandeza fora da faixa.

O livro não proíbe, mas explica o mecanismo: o gradiente atravessa mais composições em série, e
camadas são estritamente sequenciais (menos throughput que largura equivalente). ⭐ **Isso é
exatamente a explicação estrutural que sobrou** quando as três hipóteses de otimização de throughput
foram testadas e rejeitadas em 2026-07-27 — a mesma conclusão, agora com respaldo publicado.

**Decisão:** o run atual continua. A escolha veio do recipe do SmolLM2 e a curva está saudável
(loss caindo, gnorm 0,09–0,13, sem spikes). ⭐ **Mas na escada 350M → 1B, crescer LARGURA antes de
profundidade** — e o custo já medido de 65 h em vez das 31 h previstas por 6ND é o preço dessa
geometria, não um mistério.

## 2. LR 3e-3 — ⚠️ sob observação, com evidência empírica a favor

É 3× o único valor de referência do Burkov para treino do zero (1e-3). O livro não tem base para
condenar (não cobre scaling laws nem µP, e batch de 524k legitimamente tolera LR maior), mas alerta
que LR alto demais faz a loss subir.

**A régua já respondeu:** 2.000 passos, gnorm estável em 0,09–0,13, sem um único spike, perplexidade
de validação caindo monotonicamente (122,9 → 114,5 → 103,1). **O risco teórico existia; a medição não
o confirmou.** Fica registrado como ponto de atenção para a escada, não como problema atual.

## 3. "Nenhum livro tem a célula *treine seu próprio modelo base*" — verdadeiro, e já sabíamos

O quadrante de decisão do AI Engineering Guidebook tem quatro células — prompting, RAG, fine-tuning,
híbrido. **Pré-treinar do zero não é uma delas.** Aparece só como etapa conceitual que laboratórios
com cluster fazem, nunca como opção do praticante. Pela lógica econômica do livro, um Qwen/Llama
pequeno + LoRA em português entregaria mais capacidade por hora de L4 que a Bee-150M.

**Isso não invalida o BEE, e não é notícia:** foi a decisão consciente de 2026-07-26, tomada com o
custo na mesa. O valor do Bee é soberania sobre tokenizador e corpus, aprendizado profundo da esteira
inteira, e ocupar um nicho que não existe em PT-BR. Mas é honesto registrar: **se o objetivo fosse "ter
um modelo útil em português o mais rápido possível", a literatura diria para não fazer isso.** O
objetivo não é esse.

## 4. "RAG é para conhecimento, fine-tuning é para comportamento" — a COMEIA **passa** no teste

O AI Engineering é categórico nessa separação, e o agente que leu levantou a suspeita de que as
abelhas da COMEIA seriam índices disfarçados de adapters.

**Verifiquei, e a suspeita não se sustenta.** As quatro abelhas são todas comportamentais:
`chat_ptbr` (responder em PT-BR natural), `coder` (formato e concisão de código), `agentica` (emitir
JSON de tool call), `base_forte` (fallback sem adapter, raciocínio residual). Nenhuma existe para
*saber mais* sobre um domínio. **A crítica é válida como teste e a arquitetura passa nele** — mas
vale reaplicá-la a cada abelha nova: *"esta existe por comportamento ou por conhecimento?"* Se for
conhecimento, é índice, não adapter.

## Bônus — LangGraph: **não adotar**, e o livro confirma sem querer

O supervisor multiagente do LangGraph é uma chamada de LLM decidindo o próximo nó a cada roteamento.
**O roteador determinístico da COMEIA faz a mesma decisão por regra, com 80% de fast-path medido, sem
gastar um token.** Trocar isso por aresta condicional com LLM é mais latência, mais custo e menos
previsibilidade — importar complexidade para resolver um problema já resolvido melhor.

Levar só duas ideias, implementadas com o que já temos e **sem a dependência**:
1. ⭐ **Checkpoint por passo com `job_id` como chave** no Chimera. Hoje, quando um agent-job de trading
   falha no meio, sobra log; com isso sobraria o estado exato, retomada do ponto e reprodução da
   decisão. **Para um agente que opera dinheiro no eToro isso vale muito**, e são ~50 linhas.
2. **Grader node** com saída booleana estruturada e teto de reexecuções.

---

# 🔧 Ações, ordenadas por retorno sobre esforço

| # | ação | onde | por quê |
|---|---|---|---|
| 1 | **Auditar as docstrings de todas as tools MCP** | Cesar, Chimera | o experimento do AI Eng: só reescrevendo descrições, o app foi de **1–2/24 → 24/24** acertos. Melhor ROI do lote inteiro |
| 2 | **Cross-encoder de reordenação** | PassaPro | **4 dos 6 livros** convergem; provavelmente não fazemos |
| 3 | **Eval set a partir de questões de prova** | PassaPro | ground truth de graça: enunciado = query, gabarito = resposta, dispositivo = contexto ideal. Centenas de itens rotulados por banca |
| 4 | **Logar o contexto recuperado com cada resposta** | PassaPro, VirtualSector | sem isso, as 3 causas de alucinação são indistinguíveis |
| 5 | **Busca híbrida** pgvector HNSW + tsvector `portuguese` + RRF | PassaPro | "art. 121", "Lei 13.869/2019", "CF/88" viram ruído na busca puramente semântica |
| 6 | **Filtro de vigência antes da busca vetorial** | PassaPro | servir lei revogada a quem vai prestar concurso é o pior bug possível do produto |
| 7 | **vLLM multi-LoRA em vez de hot-swap próprio** | COMEIA | já estava no plano (§7); o livro confirma — aplica adapters por requisição sem duplicar memória |
| 8 | **Checkpoint por passo** com `job_id` | Chimera | agente que opera dinheiro precisa de estado reproduzível, não de log |
| 9 | **ARQ nas hard rules de trading** | Chimera | exigir chaves JSON (`stop_definido`, `perda_dia_pct`…) antes de cada tool de execução: 90,2% vs 81,5% direto |
| 10 | **Stop sequences + `min_p` fixos no harness** | Gate 2 do Bee | sem stop sequence um 150M tagarela depois da resposta e polui toda métrica |

## ⚠️ Duas ressalvas técnicas para o Gate 2 (Bee-150M × SmolLM2-135M)

1. **Perplexidade só é comparável sob o mesmo tokenizador.** O Bee tem vocab 32k próprio; "o SmolLM2
   tem perplexidade X" não é comparável com a nossa em número absoluto. A comparação precisa ser feita
   em bits por byte/caractere, ou sobre tarefas, não em perplexidade crua.
2. **Holdout deduplicado é obrigatório.** Com corpus web e época única, contaminação mascara
   perplexidade para baixo — e o dedup por MinHash entre reinícios ficou como limitação conhecida do
   corpus v1.

---

# ⭐ A correção de método (a lição mais cara do dia)

Um dos vereditos veio marcado como **risco**: "o Bee usa o default do `transformers`, que não escala
as projeções residuais por `1/√(2·n_camadas)`".

**Era falso.** O `bee/pretrain.py:77` (`init_pesos`) já faz exatamente isso — `o_proj` e `down_proj`
inicializam com `0,02/√(2·30)` = **0,00258**, e o resto com 0,02. É a técnica do GPT-2, aplicada
explicitamente por cima do `transformers`.

O veredito foi escrito **por suposição sobre o código, sem abrir o arquivo**. Corrigido no ref.

⭐ **A lição vale mais que o achado:** ao confrontar o que fazemos com o que um livro recomenda, **ler
o código é obrigatório antes de escrever o veredito**. É "medir em vez de assumir" aplicado à própria
análise — e é precisamente o tipo de erro que um estudo bem-intencionado produz quando quer ser útil
rápido demais.

---

# O que eu levo deste estudo

1. **Uma ação de retorno desproporcional:** docstrings de tools MCP. Barata, medida, e afeta dois
   agentes em produção hoje.
2. **Um padrão com 4 votos independentes:** reordenação por cross-encoder. Se o PassaPro não faz, é a
   melhoria mais óbvia disponível.
3. **Uma confirmação desconfortável e uma tranquilizadora sobre o Bee:** a geometria 30×576 está fora
   da faixa dos modelos reais e explica o custo de 65 h — mas o LR 3e-3, que era o outro suspeito,
   **foi absolvido pela medição**.
4. **Uma defesa que sobreviveu ao ataque:** a COMEIA passa no teste "comportamento × conhecimento", e
   agora temos o critério explícito para cada abelha futura.
5. **Uma constatação sobre o campo, que ecoa o estudo dos 21 papers:** ninguém escreve sobre treinar
   modelo pequeno do zero. O Burkov chega perto e para na anatomia. **A fisiologia do treino do Bee
   continua sendo território de medição própria** — o que é, ao mesmo tempo, o risco e o sentido da
   aposta.
