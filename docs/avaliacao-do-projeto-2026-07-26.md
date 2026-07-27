# Avaliação do projeto — plano × realidade (2026-07-26)

> Revisão do projeto desde o início. Onde o plano acertou, onde a realidade divergiu, em que nível
> estamos de fato, e o que fazer para melhorar. Escrito para ser útil, não para agradar.

---

## 1. O plano × o que existe

| Fase do plano | Status | Evidência |
|---|---|---|
| **Fase 0** — MVP: roteador + hot-swap | ✅ feita | `comeia/orchestrator/` 926 linhas; backbone 2,98 GB medido; hot-swap 10/10 |
| **Fase 1** — abelha agêntica | ✅ feita e validada | 24/24 formato certo nos 4 idiomas (base 17/24) |
| **Fase 2** — abelha de código | ✅ feita e validada | +40 pp difícil / −17,5 pp fácil, held-out limpo |
| *(extra, fora do plano)* — abelha de extração | ✅ feita e validada | +14 a +43 pp, **alucinação 0%** |
| **Fase 3** — roteador esperto | ❌ não iniciada | roteador ainda é regex |
| **Fase 4** — multimodal (~9B) | ❌ não iniciada | — |
| **Fase 5** — runtime local / demo | ❌ não iniciada | ⚠️ tensão não resolvida com ONNX |

**Leitura:** o plano previa 3 abelhas e entregamos 3 validadas + 1 aposentada por medição. As fases
de *produto* (3, 4, 5) estão todas paradas. O projeto avançou fundo no eixo **"fabricar abelha"** e
zero no eixo **"virar sistema utilizável"**.

Escopo real: **58 commits**, ~7.900 linhas de Python, ~2.800 exemplos de treino destilados,
4 adapters treinados, 3 mantidos.

---

## 2. Em que nível estamos, de verdade

### ⚠️ Primeiro, desfazer uma ambiguidade

O projeto começou como *"criar uma LLM para competir no mercado"*. **Isso não foi feito, e não é o
que estamos fazendo.** O que existe é:

- **um backbone que não é nosso** — Qwen3.5-4B, treinado pela Alibaba, custo estimado em milhões de
  dólares e ~10²³–10²⁴ FLOPs;
- **~130 MB de adapters LoRA nossos**, treinados em ~2.800 exemplos com **poucas horas de L4** e
  **menos de US$ 5** de API de destilação.

A distância de compute entre nós e um laboratório de fronteira é de **7 a 8 ordens de grandeza**.
Não estamos "atrás" no ranking de LLMs — não estamos no ranking. Comparar a `extracao` com GPT-5 ou
Claude é comparar categorias diferentes, e qualquer número nessa direção seria teatro.

### O que estamos construindo de fato

Um **pipeline de especialização + orquestração**. E isso o plano já dizia, corretamente:

> "O moat NÃO é o modelo (open-weight = commodity). É orquestração + dados de especialização +
> pipeline de fine-tune."

Nesse eixo, uma avaliação honesta por dimensão:

| dimensão | nível | justificativa |
|---|---|---|
| **rigor de medição** | 🟢 **acima da média** | gate antes de treinar, holdout de não-regressão, checagem de contaminação, resultados negativos publicados. A maioria dos projetos de fine-tune reporta *train loss* e para |
| **qualidade do dado** | 🟡 mediano | verificação determinística é forte; volume (934) e realismo (191 chars) são fracos |
| **método de especialização** | 🟢 sólido | o filtro "o base erra" é a peça que separa +40 pp de ruído, e está validado 3× |
| **orquestração** | 🟡 protótipo | funciona, mas roteador é regex e nunca rodou carga real |
| **capacidade do modelo** | ⚪ não aplicável | é o Qwen, não é nosso |
| **produto / serving** | 🔴 **inexistente** | sem empacotamento, sem latência orçada, sem usuário |

---

## 3. A crítica mais importante: nossas métricas são autorreferenciais

**Nunca comparamos com nada externo.** Verificado no repositório: nenhum eval referencia qualquer
modelo fora do nosso próprio backbone.

Todos os ganhos que celebramos têm a forma:

> *adapter vs. o nosso próprio base, em itens escolhidos porque o base erra neles*

Isso é **circular por construção**. "+43 pp" mede recuperação sobre um baseline deliberadamente
selecionado para falhar. Não responde a nenhuma das perguntas que decidem se o projeto vale:

1. A `extracao` bate o **mesmo backbone com um prompt melhor** (few-shot, 3 exemplos)? Se sim, o
   adapter vale. Se não, gastamos GPU para consertar prompt ruim.
2. Bate um **encoder de 110M** rodando em CPU? A objeção que registrei em 2026-07-25 e nunca medi.
3. Bate a **camada barata de um modelo grande** por documento processado, considerando custo?

Sem essas três, não sabemos se construímos algo útil ou se apenas nos recuperamos de um ponto de
partida ruim. **É a maior lacuna do projeto**, e é barata de fechar (uma tarde).

### Segunda crítica: a "métrica que decide tudo" foi medida uma vez, mal

O plano diz, em maiúsculas:

> "⭐ MÉTRICA-CHAVE: fração de fast-path — medir obsessivamente desde o MVP."

Foi medida **uma vez**, em **10 queries que eu mesmo escrevi** para exercitar cada rota, e nunca mais.
Os 80% não medem carga de trabalho nenhuma — medem que escrevi 8 queries fáceis e 2 difíceis. É uma
anedota com aparência de métrica, e a disciplina que aplicamos ao resto do projeto não foi aplicada
justamente ao número que o plano elegeu como decisivo.

---

## 4. O que o projeto realmente produziu de valioso

Tirando as tabelas, três coisas que sobrevivem a qualquer mudança de rumo:

**1. Um método de especialização validado 3 vezes.** Gate → filtro "o base erra" → holdout duplo. Ele
previu corretamente o fracasso (chat_ptbr) e o sucesso (agentica, coder, extracao). Um método que
acerta a previsão em ambas as direções vale mais que qualquer um dos adapters.

**2. Verificação determinística como substituto de juiz LLM.** Execução de código, validação de JSON
contra catálogo, e — a melhor peça — **groundedness**, que torna alucinação *decidível*. Isso não é
padrão no ecossistema e é diretamente reaproveitável.

**3. Um catálogo de armadilhas medidas.** Loss no prompt (93,8%), holdout contaminado por shuffle,
prompt de treino ≠ prompt de produção (45,8 pp escondidos), system prompt arrastando idioma,
gate não bit-reproduzível. Cada uma custou horas e está documentada com o número.

---

## 5. O que fazer para melhorar — ordenado por valor/custo

### ✅ Prioridade 1 — FECHADA no mesmo dia: o baseline externo foi medido

**Resultado (holdout difícil, 119 itens, few-shot com vazamento verificado por `assert`):**

| braço | perfeitos | campos | conforme | alucinação | esquecidos |
|---|---|---|---|---|---|
| base 0-shot | **0,0%** | 67,7% | 89,1% | 8,5% | 53 |
| base **3-shot** | **10,9%** | 69,4% | 95,8% | 5,3% | 60 |
| **ADAPTER** | **26,1%** | **78,2%** | **100,0%** | **3,4%** | **10** |

**ADAPTER − FEW-SHOT = +15,1 pp.** O adapter ensina algo que o prompt não alcança.

E o few-shot funcionou: tirou o base de 0% para 10,9%. Ou seja, **parte do "+43 pp" que
reportávamos era mesmo prompt fraco** — a crítica estava certa. Mas só parte: os outros 15 pp são
especialização real, medida contra um concorrente que não escolhemos para perder.

Dois achados secundários que o desenho do eval capturou:
- **alucinação 8,5% → 5,3% → 3,4%** — melhora monotônica; o few-shot ajuda, o treino ajuda mais;
- **campos esquecidos 53 → 60 → 10** — o few-shot *piorou* a sub-extração (viu 3 exemplos e ficou
  mais tímido). O adapter é o único que aprendeu **quando preencher**, não só quando calar. Foi
  exatamente para pegar isso que a coluna de "esquecido" existe separada da de alucinação.

⚠️ **Ainda em aberto neste eixo:** o professor não foi medido (falta o teto prático e o custo por
documento), e o encoder pequeno da objeção de 2026-07-25 continua não medido.

### 🔴 Prioridade 1b — o mesmo teste para `agentica` e `coder` *(não feito)*

O few-shot só foi medido na `extracao`. As outras duas continuam com números autorreferenciais.

### 🔴 Prioridade 2 — medir a fração de fast-path com carga que eu não escrevi

Precisa de queries que não foram desenhadas para casar com os gatilhos. Opções: log real de uso,
amostra de dataset público de instruções, ou queries geradas por professor com instrução de
diversidade. Enquanto for a amostra atual, os 80% não devem aparecer no README como métrica.

### 🟡 Prioridade 3 — medir a comeia inteira, ponta a ponta

Nunca medimos o sistema, só as peças. Falta: latência por rota, custo por query, e acurácia da
comeia **contra chamar um modelo grande direto**. É o experimento que testa a tese central do plano
("decomposição + roteamento vence"), e ele nunca foi feito.

### 🟡 Prioridade 4 — roteador aprendido (Fase 3)

O dataset já existe rotulado de graça (cada item sabe de que abelha veio). `sentence-transformers`
+ classificador, minutos de CPU. É a fase mais barata do plano ainda aberta.

### 🟢 Prioridade 5 — as limitações conhecidas da `extracao`

Documento longo (`--doc-len longo`, exige `--max-seq-len 3072+`) e viés de esparsidade
(`--cap-esparso`). Ferramentas prontas, experimentos não rodados. Custo: uma leva + 35 min.

### 🟢 Prioridade 6 — experimentos baratos já disponíveis

`use_dora` / `use_rslora` são duas flags no `LoraConfig`; a coder reproduz em 17 min. Não sabemos se
LoRA r=16 padrão é a melhor escolha porque nunca testamos alternativa.

### ⚪ Não fazer agora

**Fase 4 (multimodal ~9B)** e **Fase 5 (runtime local)**. A Fase 5 tem uma tensão não resolvida:
exportar hot-swap para ONNX tende a exigir merge + N modelos, o que desfaz a economia de VRAM que é a
tese da comeia. O vLLM (multi-LoRA em lote) parece o caminho que preserva a tese, mas não foi medido.
Investigar antes de prometer.

---

## 6. Veredito

**O que é bom:** o método. Ele acerta previsões nas duas direções e produziu três especializações
reais com custo irrisório. A disciplina de medição está acima do que se vê em projetos comparáveis, e
os resultados negativos foram publicados em vez de escondidos — inclusive um adapter aposentado.

**O que é frágil:** tudo é medido contra nós mesmos. Não existe uma única comparação externa, e a
métrica que o próprio plano elegeu como decisiva foi medida uma vez, com uma amostra que eu escrevi.
Enquanto isso não mudar, o projeto sabe que **melhorou**, mas não sabe se é **bom**.

**O que não existe:** produto. Nenhuma das três fases de produto começou.

**A próxima coisa a fazer** não é treinar mais uma abelha. É gastar uma tarde descobrindo se as que
temos ganham de alguém que não seja nós mesmos.
