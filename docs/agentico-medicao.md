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

## 6. Como reproduzir

```bash
python comeia/eval/tools_exec.py                     # autoteste do executor (5 provas)
python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-150m-pt-sft --k 1 --tag greedy
python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-150m-pt-sft --k 16 --temp 0.8 --tag passk
```

O primeiro comando é o que valida o avaliador; rode-o sempre que mexer nas ferramentas.
