# Estudo — 128 papers de SLM (arXiv, jun–ago 2026)

> **2026-08-24.** Varredura da busca `slm` no arXiv por data de anúncio, 128 entradas lidas e
> triadas (entradas 1–90 e 201–238). Critério do projeto: **o menor modelo testado e o resultado nele**; o que só foi
> validado em ≥7B é aposta, não receita.
>
> ⚠️ Leitura feita sobre **abstracts**. Vários deles não trazem número, semente nem variância —
> e isso, contra o que o E6 acabou de medir, virou o achado crítico da leitura (§5).

---

## 1. Os que mudam o que o Bee faz agora

### ⭐⭐ Data Turnstile — arXiv:2607.29250 · geração de dado de chamada de função

Decompõe interação multi-turno em **geração passo a passo com validação e realimentação de
erro**, a partir de especificações de API dadas pelo usuário. Dataset: **1.000+ APIs**,
100 mil interações multi-turno.

| modelo | BFCL | τ²-bench Telecom |
|---|---:|---:|
| Qwen3-**0,6B** base | 67,4% | **3,5%** |
| Qwen3-**0,6B** + Turnstile | **75,9%** | **24,6%** |
| Qwen3-1,7B + Turnstile | 78,4% | **31,1%** |
| Qwen2.5-**32B**-Instruct | — | 27,4% |

⭐ **Um 1,7B treinado nesse dado bate um 32B em multi-turno**, e o 0,6B sai de 3,5% para 24,6%.
Validado exatamente na faixa do Bee.

**Por que importa aqui:** o holdout aberto acabou de medir que 51% das falhas do Bee é
**substituição de ferramenta** e 37% é **omissão de argumento obrigatório** — os dois modos que
diversidade de catálogo ataca. O gigaverbo tem 747 ferramentas; eles usam 1.000+. Mesma ordem.

⚠️ Eles **não** reportam generalização entre catálogos. O achado do Bee (o modelo reverte para
as ferramentas que memorizou) não está coberto por eles.

### ⭐ Robust RL for Small-Scale LM Agents — arXiv:2607.25091

Três modos de falha, medidos em **Pythia-70M/160M/410M e SmolLM2-135M/360M** — a faixa do Bee:

| # | falha | conserto |
|---|---|---|
| 1 | LoRA congelado em silêncio no PEFT/TRL | merge-and-reinitialize |
| 2 | **overflow numérico nas razões de importância em bf16** | **float32 nas atualizações** |
| 3 | colapso da política por erro de reward | whitening + guarda de razão + **rollback de peso** |

O nº 1 já está nas regras do projeto (§2c #7). **Os outros dois são novos e me atingem:**

- `dpo_qlora.py` roda `bf16=True`. DPO computa razões de log-prob, mesma família do nº 2.
- Minha `GuardaDeslocamento` **para** o treino; a deles **reverte o peso**. Parar é meia guarda:
  o checkpoint já salvo carrega o dano.

### ⭐ Better Harnesses, Smaller Models — arXiv:2607.08938

**89,7% do desempenho do LLM a 4% do custo.** Melhora 16 de 21 pares tarefa-modelo; 7 fecham a
diferença por completo. O harness são "instruções, ferramentas e laços de orquestração", e um
otimizador **descobre as adaptações a partir de trajetórias de falha**.

⭐ É o que este projeto vem fazendo à mão: a parada por byte de controle (E5), o parser de
harness, a régua dupla — todos saíram de ler o despejo de falhas. Eles automatizaram o laço.
Adaptação é **por tarefa** e rende mais em fluxos repetitivos.

### ⭐ Guarded Query Routing — arXiv:2607.24801

**GQR-Score = média harmônica entre acurácia dentro e fora da distribuição.**

⭐ Isso resolve um problema de forma do projeto: hoje execução e over-calling são reportados
separados, e a lição `bee-medir-os-dois-lados` existe porque otimizar um às custas do outro
passou despercebido por semanas. A **harmônica pune isso por construção**.

Granite 4 Tiny: **54,29 → 83,05** só com otimização de prompt, **sem exemplos no contexto**.
Mistral 7B otimizado (90,87) chega perto do Gemma 3 27B sem otimização (96,01).

### Trie-Constrained Token Prediction — arXiv:2608.04464

O abstract não traz o mecanismo, mas a ideia é genérica: restringir a decodificação a prefixos
válidos de uma taxonomia. **Aplicada ao catálogo do prompt, torna substituição de ferramenta
impossível por construção** — e são 51% das falhas do Bee. Intervenção de runtime, zero treino.

---

## 2. Os que desafiam a premissa do Bee

### ⚠️ Trustworthiness: pré-treinado × comprimido — arXiv:2608.11981

> "comprimir um modelo grande confiável via quantização pode produzir SLMs com confiabilidade e
> adaptabilidade **superiores** a modelos pequenos treinados do zero"

Também: quantização preserva confiabilidade **melhor que poda**.

Fica registrado como contra-argumento, não descartado. Ressalvas honestas: mede
*confiabilidade* (justiça, privacidade, robustez), não capacidade; e os modelos grandes
comprimidos são anglocêntricos, enquanto a vantagem do Bee é de tokenizador
(0,218 tok/byte contra 0,358), que não sobrevive a comprimir um modelo alheio.

### ⚠️ The Multilingual Quantization Tax — arXiv:2608.09941

Par adversarial do anterior, no eixo que interessa: **"colapso representacional"** — algumas
línguas **deixam de gerar logits válidos** sob quantização. Oito línguas tipologicamente
diversas, Gemma 4 e Qwen 3.5, MMLU ProX Lite e GlobalPIQA. Sob revisão no EMNLP 2026; o
abstract não traz o número por língua.

⭐ Os dois juntos formam a pergunta certa: *quantizar preserva confiabilidade em inglês e
colapsa em língua de menos recurso?* Se sim, a rota "comprimir um grande" é pior para PT do que
o número agregado sugere — e é a favor do Bee. **Mas isso é hipótese, não medição.**

---

## 3. Os que confirmam a faixa

- **arXiv:2606.22606** — sub-bilhão **iguala LLMs de fronteira zero-shot** em extração de relação.
- **arXiv:2606.23695** — SLMs igualam grandes em extração factual estrita; retornos decrescentes
  de escala.
- **arXiv:2607.27506** (B1ade) — 335M por **fusão sem treino** de cinco encoders; o 1B treinado
  em só **723M tokens** com GRPO, +10,8% sobre SFT. ⭐ Citação **emergiu** em 42,4% das respostas
  sem supervisão explícita.
- **arXiv:2607.09885** — Index-1.9B (Bilibili), relatório técnico completo de SLM.
- **arXiv:2607.07748** — "Selective Left-Shift": transformar compute de inferência em **dado de
  treino** para linguagem de programação de poucos recursos. É a resposta possível ao limite que
  o rejection sampling do Bee acabou de bater.

---

## 3b. A segunda leva (entradas 201–238) — dois que mudam o plano

### ⭐⭐ Compiling Deterministic Structure into SLM Harnesses — arXiv:2604.17450

Compila o fluxo agêntico em **plano de execução discreto**: topologia DAG, prompts e código
determinístico. Dois mecanismos:

- **Capability offloading** — delegar a subtarefa a Python **quando o SLM é pouco confiável**;
- **Structural consensus** — envolver passos de alta variância em fan-out/fan-in com **votação
  determinística**.

**91,3% a *m*=5 e 99,3% a *m*=3 no GSM-Hard — +26,3 a +34,3 pp sobre otimizadores de prompt.**

⭐ O *offloading* é a resposta direta ao meu quadro: o holdout é 90% ferramenta aritmética, o
modelo erra a **seleção** (51%) e omite **argumento** (37%), e a conta em si é trivial.

⭐⭐ E o *structural consensus* é uma hipótese testável que eu **ainda não medi**: o E5 mediu
"servir a primeira executável" (62,4%, **pior** que os 65,9% do greedy). **Votação por maioria
sobre o nome da ferramenta é outra agregação** — se 5 de 8 amostras dizem `calculate_tip` e 3
dizem `calculator`, o voto acerta onde a primeira-executável erra. Custa uma rodada de k=8 no
holdout, ~1,5 h, US$ 0.

⚠️ O abstract **não** diz o que se perde ao enrijecer o harness. Fica como pergunta aberta.

### ⭐ Limits of Difficulty Scaling — arXiv:2604.06298

Em SLMs de 1,5B e 3B: *"GRPO reformata preferências de saída sem melhorar de forma confiável a
resolução do nível mais difícil"*. Treinar só nos fáceis igualou o dataset completo com **~45%
dos passos**.

Valida de fora o que o E6 e o RS deste projeto mediram: preferência deu +2,4 pp (ruído), e os
664 prompts `all_wrong` renderam zero.

🔴 **Mas a recomendação deles — "exclua os difíceis" — estaria ERRADA aqui, e os meus números
dizem por quê.** Os 374 prompts de gorjeta que renderam zero **não são difíceis**: a aritmética
é idêntica à do desconto, que rende 83%. São **sistematicamente mal roteados** por associação
lexical (o modelo emite `calculator`). Excluí-los garantiria que o modelo nunca aprenda o
catálogo.

⭐ **Dificuldade e viés de roteamento produzem a mesma taxa agregada e pedem tratamentos
opostos** — um pede exclusão, o outro pede exatamente o dado excluído. Só a decomposição por
ferramenta separa os dois, e ela não estava no relatório agregado.

### Outros da faixa, anotados

- **arXiv:2604.04233** — restrições de **gramática** para parsing determinístico de comando:
  a mesma família da ação nº 1.
- **arXiv:2604.11582** — tokenização de sufixo triádico **preservando estrutura de número** para
  raciocínio aritmético. ⚠️ O Bee tem tokenizador próprio e o holdout é 90% aritmético — e o
  modelo emite `"200"` como **string**. Vale investigar.
- **arXiv:2604.18381** — RLVR em regime de pouco dado e pouca computação. O executor do Bee
  **é** uma recompensa verificável.
- **arXiv:2604.17794** — test-time scaling para fechar a lacuna de raciocínio em **vietnamita**:
  o análogo direto do problema PT-BR.
- **arXiv:2604.17827** — aprender **quando pedir ajuda** ao modelo grande. Outra formulação da
  decisão chamar × recusar.

---

## 4. Ação imediata para o Bee

| # | ação | custo | vem de |
|---|---|---|---|
| 1 | **Decodificação restrita ao catálogo do prompt** — impossibilita substituição de ferramenta | zero treino | 2608.04464 · 2604.04233 |
| 1b | **Votação por maioria** sobre o nome da ferramenta em k=8 — agregação diferente da que o E5 mediu e reprovou | ~1,5 h GPU | 2604.17450 |
| 2 | **Adotar a média harmônica** execução × (1 − over-calling) como número único | zero | 2607.24801 |
| 3 | **float32 nas atualizações de DPO** em vez de bf16 | zero | 2607.25091 |
| 4 | **Rollback de peso** na `GuardaDeslocamento`, não só parada | pequeno | 2607.25091 |
| 5 | Otimização de prompt antes de qualquer treino novo — 54 → 83 num modelo pequeno | zero GPU | 2607.24801 |

A nº 1 é a de maior retorno: ataca **51% das falhas medidas** sem tocar em peso nenhum.

---

## 5. ⚠️ A leitura crítica: o que a literatura não reporta

**arXiv:2607.13430** compara SFT, DPO, ORPO e GRPO em SLMs Qwen e conclui que "ORPO supera o
SFT" e "GRPO é o mais robusto entre datasets". O abstract **não traz número, não traz semente,
não traz variância**.

🔴 O E6 deste projeto acabou de medir, em 22 treinos, que **só a semente move 4,7 pp e troca 14
de 85 casos** num modelo de 350M. Com uma semente por braço, o DPO daqui deu +5,9 pp — e com
três, +2,4 pp, dentro do ruído.

**Então uma afirmação de "método A supera método B" nessa escala, sem replicação de semente, é
exatamente o tipo de resultado que a nossa própria medição diz que não se sustenta.** Não é
acusação de erro: é que o desenho não distingue efeito de ruído, e o abstract não permite
saber se o corpo do paper distingue.

⭐ Reforçado de fora por **arXiv:2608.17183** ("Benchmarking the Benchmarks", 5 suítes ×
26 SLMs): *"model rankings change significantly under reasonable ambiguity treatments, even when
the underlying outputs remain unchanged"* — e a ambiguidade **cresce com o comprimento e a
perplexidade da saída**, ou seja, é maior nos modelos piores e enviesa o ranking
sistematicamente.

**A regra que sai daqui, e vale para ler qualquer paper de SLM:** antes de adotar um número,
perguntar *quantas sementes* e *qual a amplitude entre elas*. Se o paper não diz, o número é uma
observação, não uma medida — e este projeto já tem o custo dessa distinção em três pisos de
ruído medidos: **semente 4,7 pp · amostragem 2,3 pp · régua 0 pp (greedy)**.
