# A abelha multi-turno — e a validação da tese da COMEIA no Bee (2026-08-13)

## O buraco

Dos 1.645 exemplos agênticos do treino, **zero** tinham papel `tool` e **zero** tinham mais de
um turno de assistente. Todos seguiam exatamente `(system, user, assistant)` — e o system
prompt chegava a instruir *"chame APENAS a PRIMEIRA ferramenta"*.

Consequência: **o modelo nunca tinha visto o que fazer com o retorno de uma ferramenta.** Ao
receber um resultado, respondia com **outra chamada** em 90,6% dos casos.

Isso é o teto de qualquer uso agêntico real, e não se resolve com prompt — é ausência de dado.
A literatura mede o tamanho do problema nessa faixa: xLAM-2-1b faz 53,97% geral mas **8,38%**
em multi-turno; Qwen3-0.6B cai de 45,76% para **1,38%**; TinyLlama-1.1B faz **0,00%**.

---

## Como os dados foram gerados — sem professor externo

`comeia/data/17_gerar_multiturno.py`, quatro passos determinísticos:

1. pega a chamada de **referência** de cada exemplo `tool_call` existente;
2. **executa** no mundo simulado (o mesmo `tools_exec.py` da avaliação);
3. converte o retorno bruto num resultado **apresentável** — o executor devolve hashes, úteis
   para comparar chamadas mas impossíveis de virar diálogo;
4. escreve a resposta final por **molde**, escolhido por hash do exemplo.

**864 diálogos** gerados, distribuídos pelas 14 ferramentas.

⭐ **Por que molde e não professor:** o que se quer ensinar aqui não é redação — o Bee já
escreve português excelente — é a **estrutura do turno**: *depois de um `role=tool` vem uma
resposta que usa aquele dado*. O molde garante por construção que o valor citado está correto,
coisa que um professor externo não garantiria (e ainda traria questão de licença).

⚠️ **Um erro pego na geração:** a v1 escolhia o conteúdo sintético por hash do caminho e
produziu isto — usuário pede `/var/log/apache2/error.log` e a ferramenta devolve *"lista de
tarefas: revisar contrato"*. O modelo aprenderia a associar log de erro com lista de compras.
Corrigido: o conteúdo é escolhido pelo **tipo** do arquivo, inferido do caminho.

---

## Escolha do learning rate

LoRA opera em regime diferente do full fine-tune — herdar o 6e-4 teria custado:

| LR | 1e-4 | 3e-4 | 6e-4 | **1e-3** |
|---|---:|---:|---:|---:|
| eval_loss | 1,0620 | 0,2722 | 0,1275 | **0,1081** |

Queda de **10×** entre as pontas, ainda descendo no fim (saturando: −53% de 3e-4→6e-4 contra
−15% de 6e-4→1e-3).

### ⭐ A suspeita de decoreba, e como foi refutada

`eval_loss` de 0,108 é baixa demais para dados feitos de 3-4 moldes por ferramenta. Hipótese:
o adapter memorizou os moldes, sem aprender a ler o retorno.

**O teste:** se fosse memorização, o LR **maior** decoraria mais e **contaminaria mais** —
citaria números que não estavam no retorno. Mediu-se o oposto:

| | LR 6e-4 | LR 1e-3 |
|---|---:|---:|
| contaminação | 7,1% | **3,5%** |

O LR maior contaminou **metade**. A hipótese de decoreba não se sustenta.

---

## Resultado

Holdout de 85 casos (`comeia/eval/eval_multiturno.py`):

| | v2 sozinho | **v2 + adapter** |
|---|---:|---:|
| ⭐ ancorado (cita o dado do retorno) | 5,9% | **91,8%** |
| cita **todos** os valores | 0,0% | **57,6%** |
| responde com outra tool call | 90,6% | **0,0%** |
| ⚠️ contaminado | 1,2% | 3,5% |

---

## ⭐ Adapter contra full fine-tune — a validação da tese da COMEIA

O mesmo dado foi treinado das duas formas. O full fine-tune resolveu o multi-turno **e cobrou
noutro eixo**:

| | full FT | **adapter LoRA** |
|---|---:|---:|
| multi-turno ancorado | 89,4% | **91,8%** |
| contaminação | 7,1% | **3,5%** |
| single-turn (execução) | 60,0% **(−5,9 pp)** | **65,9% (zero regressão)** |
| argumentos exatos | 27,1% **(−7,0 pp)** | 34,1% |
| tamanho | 302 MB | **24 MB** |

**O adapter ganha nas quatro dimensões e é 14× menor.**

⭐ **A lei que sai daqui:** num modelo de 151M a **capacidade é disputada** — ensinar uma
habilidade nova cobra outra. Repare no padrão do full FT: o over-calling **não mudou** e a
escolha de ferramenta **não mudou**; o que caiu foram os **argumentos**. Não é que o modelo
passou a chamar menos — ficou pior em preencher, porque 864 exemplos novos disputaram espaço.

A arquitetura de abelhas resolve isso **por construção**: backbone congelado (5,62M treináveis
= 3,72%), capacidade nova em adapter trocado a quente. E se o adapter ficar ruim, basta não
carregá-lo — coisa que um full fine-tune não permite desfazer.

---

## Registro no orquestrador

`comeia/orchestrator/bees.json`, abelha `multiturno`, prioridade 5.

⭐ **O gatilho é o único determinístico do registry:**

```json
"triggers": ["<\\|im_start\\|>tool", "\"role\"\\s*:\\s*\"tool\""]
```

A presença de um turno `tool` no histórico é **fato**, não heurística de texto. Todos os outros
gatilhos do registry adivinham intenção por palavra-chave; este não pode errar por sinônimo.

Testado: query sem turno `tool` não cai na abelha; query com turno `tool` cai sempre.

---

## Limites assumidos

- **Variedade estilística baixa** — 3-4 moldes por ferramenta. Se as respostas ficarem
  engessadas, o remédio é **mais moldes**, não mais exemplos dos mesmos.
- **Contaminação de 3,5%** — o modelo ainda cita, ocasionalmente, número que não veio do
  retorno. É a mesma confabulação que aparece em todo o projeto, atenuada mas não resolvida.
- **Um só passo de ferramenta.** Encadear duas ferramentas em sequência não foi treinado nem
  medido.
- **Janela:** o diálogo completo custa ~1.190 dos 2.048 tokens com o catálogo de 14
  ferramentas. Catálogo maior não cabe.

## Reprodução

```bash
python comeia/data/17_gerar_multiturno.py            # treino (864 dialogos)
python comeia/data/17_gerar_multiturno.py --eval     # holdout (85)
python bee/sft.py --modelo BrCamp/bee-150m-pt-sft-v2 \
  --dados comeia/data/processed/sft_multiturno.jsonl \
  --out models/bee-multiturno-adapter --lora --lr 1e-3 --epocas 2 \
  --max-seq-len 2048 --batch 2 --grad-accum 16 --grad-checkpoint
python comeia/eval/eval_multiturno.py --model BrCamp/bee-150m-pt-sft-v2 \
  --peft models/bee-multiturno-adapter
```
