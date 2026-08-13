# O Bee agêntico — a primeira medição funcional (2026-08-12)

Até hoje o projeto tinha **zero** métricas funcionais do Bee em uso de ferramentas. O que
existia era `eval_loss 1,0672` no holdout agêntico — que mede **predição de token sob
máscara**, não acerto. `comeia/eval/results/` só continha duas entradas, ambas do **Qwen**,
ambas de julho. O `eval_agentic.py` nunca tinha rodado contra o Bee.

Este documento registra a primeira medição real, e o erro de avaliador que ela quase escondeu.

---

## 1. O resultado

`BrCamp/bee-150m-pt-sft`, holdout `sft_agentic.eval.jsonl` (85 casos que exigem ferramenta,
65 que não exigem), geração gulosa, RTX 5070. Intervalos de Wilson — com n=85 reportar ponto
seria mentira.

| métrica | valor | IC 95% |
|---|---:|---|
| JSON válido contra o catálogo | 84,7% | 75,6 – 90,8 |
| ferramenta certa | 78,8% | 69,0 – 86,2 |
| argumentos idênticos à referência | 25,9% | 17,8 – 36,1 |
| ⭐ **executou e cumpriu a tarefa** | **57,6%** | **47,0 – 67,6** |
| under-calling (respondeu em texto) | 3,5% | 1,2 – 9,9 |
| truncado (`--max-new`, artefato nosso) | 5,9% | 2,5 – 13,0 |
| ⚠️ over-calling (chamou sem precisar) | 23,1% | 14,5 – 34,6 |

⭐ **O número que interessa é 57,6%, e ele está 21 pontos abaixo de "ferramenta certa".**
Essa distância é exatamente o que a métrica antiga escondia: escolher `calculator` para uma
pergunta de porcentagem e mandar `{"expression": "8/3"}` contava como acerto. Agora não conta.

**Por ferramenta** (só as com ≥4 exemplos; abaixo disso um erro move 25 pp e o número não é
decidível):

| ferramenta | sucesso | | ferramenta | sucesso |
|---|---:|---|---|---:|
| get_weather | 10/11 = 91% | | translate_text | 2/4 = 50% |
| get_stock_price | 8/9 = 89% | | calculator | 1/6 = 17% |
| summarize_url | 6/7 = 86% | | web_search | 1/13 = 8% |
| read_file | 8/10 = 80% | | http_get | 0/4 = 0% |
| list_dir | 8/10 = 80% | | | |
| send_email | 4/5 = 80% | | | |

O padrão é nítido e não é sobre dificuldade da ferramenta: **argumento estruturado o Bee
acerta; argumento de texto livre, não.** Cidade, ticker, caminho e URL têm forma canônica —
91%, 89%, 80%, 86%. Já `web_search{"query": ...}` exige inventar a mesma consulta que a
referência inventou.

⚠️ **Ressalva metodológica séria:** para ferramentas de texto livre a régua de "resultado
idêntico" é severa demais. Duas consultas diferentes podem cumprir a mesma tarefa, e o
avaliador conta como erro. Os 8% de `web_search` são **piso**, não estimativa. Corrigir isso
exige um juiz semântico — o que reintroduz subjetividade que este eval foi feito para evitar.
Por ora: leia os números de argumento estruturado como medida, e os de texto livre como
limite inferior.

---

## 2. 🔴 O erro que quase virou conclusão

A primeira versão do executor mediu **23,5%** de sucesso. Estava errada, e o erro era meu, não
do modelo.

Eu escrevi um mundo simulado **fechado**: 6 cidades, 5 tickers, 3 arquivos. O holdout usa o
mundo real — Brasília, Fortaleza, `/var/log/syslog`, `ABEV3`. Resultado: **35 dos 85 exemplos
eram impossíveis de acertar por construção**, porque a própria chamada de *referência* falhava.

O sinal que denunciou: `read_file` 0/10, `list_dir` 0/10, `http_get` 0/4. Zero absoluto em
ferramentas de argumento simples é implausível demais para ser do modelo — um 151M que acerta
91% em `get_weather` não erra 100% em `read_file`. **Quando um número é absurdo, desconfie do
aparato antes de aceitar o fenômeno** (a mesma regra que este projeto pagou caro para aprender
no deslocamento de rótulos).

Duas correções ficaram no código:

1. **O mundo simulado é aberto e determinístico** — qualquer cidade, ticker ou caminho é
   aceito, e o resultado deriva de um hash da entrada normalizada. Assim a pergunta medida é
   a certa: *o modelo pediu a MESMA coisa que a referência?*, e não *o argumento está na
   minha listinha?*. A normalização também trata acento e caixa: `São Paulo` e `sao paulo`
   são a mesma cidade, e ortografia não deve decidir acerto.
2. ⭐ **Guarda que aborta**: `eval_agentic_exec.py` executa **todas as referências** antes de
   carregar qualquer modelo. Se o gabarito não roda, o avaliador está errado — e o script
   recusa produzir número. Ela já se pagou na primeira execução: pegou `sqrt(1444)` e
   `sqrt(1234567)` falhando porque a calculadora não suportava funções.

Custo do erro: uma hora. Custo se tivesse passado: uma decisão de produto tomada sobre um
número 34 pontos abaixo do real.

---

## 3. Contaminação residual do dataset

Auditando o holdout, encontrei **meta-prompts do gerador vazados para dentro dos exemplos**:

```
[text]      We'll produce 15 lines. Some in English (maybe 2 or 3). Ensure each is clearly...
[text]      Analyze the Request:
[tool_call] Goal: Generate 15 new and varied user requests that require the `run_python` tool.
```

São 3/150 no holdout (**2,0%**) e 3/1.495 no treino (0,2%). O terceiro é justamente o exemplo
contado como "truncado". Está dentro da margem de Wilson e não muda o veredito, mas polui — e
num holdout de 150 cada exemplo vale 0,67 pp.

## 4. Sobre os "over-calls" que pareciam erro de rótulo

Duas falhas me pararam à primeira vista, e **as duas eram do modelo**:

- *"Crie um evento na agenda: reunião de equipe amanhã às 10h"* — o modelo chamou
  `create_calendar_event`. A referência recusa e pede a data em ISO 8601, porque "amanhã" é
  ambíguo para a ferramenta. **Rótulo certo.**
- *"Quanto é 6 vezes 9?"* — o modelo chamou `calculator`. A referência responde 54 direto.
  É uma **convenção de política** do dataset (aritmética trivial não usa ferramenta),
  defensável, mas convém saber que é convenção e não verdade.

Registrado porque eu havia levantado suspeita pública sobre a qualidade dos rótulos e ela não
se sustentou. Os rótulos estão melhores do que supus.

---

## 5. ⭐ `pass@k` — autoaprendizado é viável neste modelo

A pergunta "o Bee pode aprender sozinho?" tem uma medição que a decide, e não é o tamanho do
modelo: **existe cauda?** Rejection sampling / STaR não exige que o modelo seja bom em média —
exige que, amostrando várias vezes, apareçam trajetórias corretas que um verificador barato
saiba reconhecer. Essas viram dado de treino.

k=16, temperatura 0,8, mesmo holdout, correção decidida por execução:

| | |
|---|---:|
| greedy (k=1) | 57,6% |
| pass@1 (média das 16 amostras) | 52,3% |
| **pass@16 (≥1 amostra correta)** | **72,9%** |
| folga sobre pass@1 | **+20,6 pp** |
| folga sobre o greedy | +15,3 pp |
| fração do espaço restante capturada pela cauda | **43,2%** |

Em exemplos concretos: **o greedy resolve 49/85; amostrando 16× resolve 62/85.** São
**13 exemplos** com solução correta que a geração gulosa nunca encontra — e o executor
determinístico as reconhece sem ambiguidade.

**Veredito: há cauda, e é farta. O caminho de autoaprendizado offline está ABERTO** para este
modelo nesta tarefa. Não por otimismo: 43,2% de tudo o que faltava está ao alcance de
amostragem + verificação.

E o padrão por ferramenta fica ainda mais nítido sob amostragem:

| estruturado (cauda quase perfeita) | | texto livre (cauda pobre) | |
|---|---:|---|---:|
| get_stock_price | 9/9 = 100% | web_search | 2/13 = 15% |
| list_dir | 10/10 = 100% | http_get | 1/4 = 25% |
| send_email | 5/5 = 100% | calculator | 3/6 = 50% |
| summarize_url | 7/7 = 100% | translate_text | 2/4 = 50% |
| get_weather | 10/11 = 91% | | |
| read_file | 9/10 = 90% | | |

Isso diz onde colher: **as ferramentas de argumento estruturado estão praticamente resolvidas
por amostragem** — é ali que o rejection sampling gera dado limpo quase de graça. As de texto
livre continuam sendo o gargalo, e para elas a cauda não resolve.

### 🔴 O veredito automático saiu errado na primeira vez, e o erro era do critério

O script imprimiu **"NÃO há cauda útil"** com esses mesmos números. A condição que escrevi era
`pass@k > pass@1 × 1,5` — critério **multiplicativo**, que é inadequado quando `pass@1` já é
alto: com 52,3%, exigir 1,5× equivale a exigir 78,6%, quase o teto absoluto. Ele pune
justamente o modelo que já vai bem.

Corrigido para folga **absoluta** (≥5 pp) somada à **fração do espaço restante** capturada
(≥15%) — que é o que de fato importa para saber se vale amostrar. Registrado aqui porque, se
eu tivesse repassado a linha impressa sem conferir contra os números, teria fechado uma porta
que está aberta.

---

## 6. Over-calling: não era over-calling

Os 23,1% de "over-calling" (15/65) eram o pior número do modelo. Lendo os 15 casos um a um
contra suas referências, quase nenhum era over-calling no sentido clássico:

| pedido do usuário | o que falta | o que o Bee fez |
|---|---|---|
| "e-mail pra maria@… assunto 'Reunião remarcada'" | o **corpo** | inventou o corpo |
| "agendar dia 10 às 11h30" | **mês e ano** | inventou `2025-04-10` |
| "e-mail de agradecimento pra ana@corp.com" | assunto **e** corpo | inventou os dois |
| "evento dia 31 às 16h" | mês e ano | inventou `2025-04-01` — e trocou o dia 31 por 01 |

O dataset tem uma política coerente: **falta argumento obrigatório, pergunte — não invente.**
O modelo faz o inverso. Isso é **confabulação de argumentos**, a mesma patologia do "escreve
português excelente e inventa fatos com confiança", agora em tool use.

A distinção muda o ataque. Decidir *se* a query precisa de ferramenta é semântico e difícil;
verificar se o argumento **veio do texto do usuário** é sintático e decidível.

### 🔴 A primeira versão da regra estava larga e errada

Exigi ancoragem de `to`, `subject`, `body`, `path`, `city`, `ticker`, `url`, `text`. Rodada
contra as 85 chamadas de **referência** — legítimas por definição — acusou 6 (**7,1% de falso
positivo puro**). Cada uma ensinou a mesma coisa:

```
"Petrobras na Bovespa"   -> PETR4                 DERIVAÇÃO por conhecimento
"BBC's RSS feed"         -> feeds.bbci.co.uk/...  DERIVAÇÃO por conhecimento
"reclamando do atraso"   -> corpo redigido        REDAÇÃO a partir da intenção
"dia 10/05 às 15h"       -> 2025-05-10T15:00      mês e dia ESTÃO no texto
```

Eu havia confundido **confabular** com **derivar**. O modelo pode e deve normalizar
("Petrobras" → `PETR4`) e redigir (intenção → corpo). O que ele não pode é inventar o que não
se deriva de lugar nenhum.

Sobrou um único campo em que a evidência é decidível sem semântica: a **data**. "dia 31 às
16h" não tem mês, e nenhum conhecimento do mundo diz qual é. **Regra estreita e correta vale
mais que regra ampla e errada.**

### O resultado, e um achado sobre o verificador que já existia

| verificador | pega over-call | bloqueia legítima | **saldo** |
|---|---:|---:|---:|
| intenção (`verifier.py`, já existia) | 4/15 | 5/85 | **−1** |
| **ancoragem (`ancoragem.py`)** | 3/15 | **0/85** | **+3** |
| os dois em série | 7/15 | 5/85 | +2 |

⭐ **O `verifier.py` tem saldo negativo: ele piora o sistema.** Bloqueia 5 chamadas legítimas
para consertar 4 over-calls. Isso nunca tinha aparecido porque só se media o ganho — quantos
over-calls ele pega — e nunca o custo. **Toda intervenção que bloqueia tem de ser medida nos
dois lados**, ou o número é meia-verdade.

Over-calling com a ancoragem: **23,1% → 18,5%**, custo zero, sem treinar nada.

### O que sobra, e por que não é atacável por regra

Os 12 residuais: `web_search` 4, `calculator` 4, `send_email` 4. Os de `send_email` são
confabulação de corpo — e a fronteira entre "redigir a partir da intenção" (legítimo, a
referência chama) e "inventar o corpo" (a referência recusa) é sutil demais para regra
determinística. Os de `calculator` são expressão errada (`8/3` para uma pergunta de
porcentagem, `17*(1+i)^n` para testar se 17 é primo) — erro de raciocínio, não de política.

Para esses, o caminho é **dado de treino**: exemplos de "peça o que falta" em vez de inventar.
É o item 6 do plano, e agora ele tem alvo nomeado.

---

## 7. ⭐ Autoaprendizado por rejection sampling — o ciclo fechado

O `pass@16` de 72,9% dizia que havia cauda. Este capítulo é o que aconteceu ao colhê-la.

### Rodada 1 — funcionou, e cobrou noutro eixo

Colhi 1.022 amostras corretas do **treino** (k=8, T=0,8, filtradas por execução): 621 dos 865
exemplos válidos renderam algo — `pass@8` de **71,8%**, batendo com o `pass@16` do holdout.

| | base | ref100 | Δ |
|---|---:|---:|---:|
| executou e cumpriu | 57,6% | 61,2% | +3,6 |
| argumentos idênticos | 24,7% | 31,8% | +7,1 |
| ⚠️ over-calling | 26,2% | **33,8%** | **+7,6** |

O método entregou o que promete — mais consistência e argumentos melhores — e **piorou a
decisão de chamar**. A causa é estrutural: o rejection sampling só produz `tool_call`, porque
só a chamada tem verificação por execução. A proporção agêntica foi de 59,3% para **75,8%**
de tool, e o modelo aprendeu a chamar mais.

⭐ **Se eu tivesse medido só `exec_ok`, teria declarado vitória.** O ganho de 3 tarefas veio
com 5 chamadas indevidas — saldo negativo, invisível em qualquer relatório de um eixo só.

### O controle que evitou a conclusão errada: `pass@16`

| | base | ref100 |
|---|---:|---:|
| pass@1 | 52,3% | **57,6%** |
| pass@16 | 72,9% | **72,9%** |

Zero mudança no teto. **Não houve estreitamento destrutivo** — o STaR converteu cauda em
consistência, exatamente como a teoria diz. Isso separa "o método é ruim" de "a mistura está
errada", e sem esse controle os dois pareceriam iguais.

⭐ **A lei que fica: o rejection sampling move o piso em direção ao teto, e não move o teto.**
A folga aproveitável caiu de 20,6 para 15,3 pp — cada iteração rende menos. Para levantar os
72,9% seria preciso capacidade ou dado novo, não reamostrar o que já existe.

### Rodada 2 — colheita SIMÉTRICA

Se o problema é a proporção, colha os dois lados. Para `text` a decisão certa é **não
chamar**, e isso é verificável. Mas reforçar texto do próprio Bee é arriscado — ele inventa
fatos —, então a colheita passa por quatro guardas (`texto_aproveitavel`).

**A guarda que fez o trabalho:** exigir que a resposta cubra ≥25% do vocabulário da
referência. Ela sozinha rejeitou **1.542** amostras, mais que todas as outras somadas (924
por chamarem ferramenta, 69 por repetição, 15 por tamanho). Sem ela, eu teria colhido mil e
quinhentas respostas fluentes **sobre o assunto errado** — reforçando de propósito o vício
que se quer conter.

Colheita: **1.038 tool + 787 text = 56,9% tool**, contra 59,3% do original. Mistura final:
8.977 exemplos, **58,0% tool**.

### O resultado

| | base | ref100 | ⭐ **simétrico** |
|---|---:|---:|---:|
| JSON válido | 87,1% | 82,4% | 84,7% |
| ferramenta certa | 81,2% | 80,0% | 80,0% |
| argumentos idênticos | 24,7% | 31,8% | **34,1%** |
| ⭐ **executou e cumpriu** | 57,6% | 61,2% | **65,9%** |
| ⚠️ **over-calling** | 26,2% | 33,8% | **21,5%** |
| pass@1 | 52,3% | 57,6% | 57,0% |
| pass@16 | 72,9% | 72,9% | 71,8% |

**Ganhou nos dois eixos ao mesmo tempo**: +8,3 pp de execução sobre o baseline e −4,7 pp de
over-calling — este último ficando **abaixo** até do modelo publicado (23,1%). Em casos:
**+7 tarefas cumpridas, −3 chamadas indevidas**, saldo +10 (contra −2 do ref100).

E o `pass@1` de 57,0% preserva o ganho de consistência do ref100 (57,6%) enquanto o `pass@16`
de 71,8% mantém a cauda (72,9%, dentro do ruído).

⚠️ **Honestidade estatística:** com n=85/65 os intervalos ainda se sobrepõem
(execução [55,3–75,1] contra [47,0–67,6]). Nenhuma comparação isolada é conclusiva. O que dá
força ao resultado é o **padrão simultâneo**: execução, argumentos, over-calling e `pass@1`
melhoraram juntos, e `pass@16` não caiu. Quatro eixos concordando é evidência mais forte que
qualquer um deles sozinho — mas confirmar exigiria um holdout maior.

**Conclusão: o laço de autoaprendizado offline está fechado e é repetível** neste modelo de
151M — contra o folclore de que exigiria 1B+. A condição nunca foi contagem de parâmetros:
foi ter cauda (`pass@k > pass@1`) e um verificador barato e externo.

---

## 8. Como reproduzir

```bash
python comeia/eval/tools_exec.py                     # autoteste do executor (5 provas)
python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-150m-pt-sft --k 1 --tag greedy
python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-150m-pt-sft --k 16 --temp 0.8 --tag passk
```

O primeiro comando é o que valida o avaliador; rode-o sempre que mexer nas ferramentas.
