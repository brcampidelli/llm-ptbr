---
language:
- pt
license: apache-2.0
library_name: transformers
pipeline_tag: text-generation
base_model: BrCamp/bee-150m-pt-base
tags:
- portuguese
- sft
- llama
- function-calling
- rejection-sampling
---

# Bee-150M-PT-SFT **v2**

Versão ajustada do [`bee-150m-pt-base`](https://huggingface.co/BrCamp/bee-150m-pt-base) —
151,2M parâmetros pré-treinados do zero em português (0,844 bpb, à frente do Tucano-160m com
9× menos tokens).

**O que mudou da v1:** o SFT foi refeito com **rejection sampling simétrico** — o próprio
modelo gerou candidatas, um verificador determinístico externo ficou só com as que cumprem a
tarefa, e essas voltaram como reforço. É autoaprendizado offline, com o julgamento **fora** do
modelo.

## Resultado medido (execução, não semelhança)

Holdout de 85 casos que exigem ferramenta + 65 que não exigem. A correção é decidida
**executando** a chamada prevista e a de referência num mundo simulado determinístico e
comparando os resultados — `{"expression": "6*9"}` e `{"expression": "9*6"}` contam igual;
ferramenta certa com argumento errado conta como erro.

| | v1 | **v2** |
|---|---:|---:|
| ⭐ **executou e cumpriu a tarefa** | 57,6% | **65,9%** |
| ⚠️ over-calling (chamou sem precisar) | 26,2% | **21,5%** |
| argumentos idênticos à referência | 24,7% | **34,1%** |
| ferramenta certa | 81,2% | 80,0% |
| JSON válido contra o catálogo | 87,1% | 84,7% |
| pass@1 (média de 16 amostras) | 52,3% | **57,0%** |
| pass@16 | 72,9% | 71,8% |

**+7 tarefas cumpridas e −3 chamadas indevidas**, ganhando nos dois eixos ao mesmo tempo.

⚠️ **Honestidade estatística:** com n=85/65 os intervalos de confiança se sobrepõem
(execução [55,3–75,1] contra [47,0–67,6]). Nenhuma comparação isolada é conclusiva — o que
sustenta o resultado é o padrão simultâneo em quatro eixos, com o teto (`pass@16`) preservado.

## Como foi treinado

1. **Colheita** — k=8 amostras por exemplo do conjunto de treino (nunca o holdout), T=0,8.
2. **Filtro externo** — para `tool_call`, a chamada tem de executar e bater com a referência.
   Para `text`, o acerto é **não chamar ferramenta**, mais quatro guardas determinísticas
   (tamanho, não-degeneração, e ≥25% de cobertura do vocabulário da referência — esta última
   impede colher resposta fluente sobre o assunto errado).
3. **Mistura equilibrada** — 1.038 `tool` + 787 `text` de reforço, mantendo a proporção
   original em **58,0% tool**. Colher só `tool_call` desloca a decisão e piora o
   over-calling: medimos +7,6 pp quando a proporção foi a 75,8%.
4. **SFT** — `lr 6e-4`, 2 épocas, `max_seq_len` 2048, batch efetivo 32, bf16, loss mascarada
   no prompt. 8.977 exemplos.

## Uso

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("BrCamp/bee-150m-pt-sft-v2")
modelo = AutoModelForCausalLM.from_pretrained("BrCamp/bee-150m-pt-sft-v2")

msgs = [{"role": "system", "content": CATALOGO_DE_FERRAMENTAS},
        {"role": "user", "content": "Qual o clima em Fortaleza?"}]
entrada = tok.apply_chat_template(msgs, return_tensors="pt", add_generation_prompt=True)
print(tok.decode(modelo.generate(entrada, max_new_tokens=200)[0]))
```

⚠️ **Envie sempre o catálogo de ferramentas no `system`.** O modelo foi treinado com ele
presente; servir sem o catálogo é perguntar por ferramentas que, do ponto de vista dele, não
existem.

## Limitações — leia antes de usar

**O que ele faz bem:** argumento **estruturado**. Cidade, ticker, caminho e URL têm forma
canônica e ele acerta — `get_weather` 91%, `get_stock_price` 89%, `read_file`/`list_dir` 80%.

**O que ele não faz:**

- **Argumento de texto livre** — `web_search` 8%, `http_get` 0% (piso, ver ressalva abaixo).
- **Multi-turno** — zero exemplos de treino têm papel `tool`. O modelo emite uma chamada e
  não sabe o que fazer com o retorno. **O encadeamento tem de estar no orquestrador.**
- **Fatos** — como todo modelo desta escala, escreve português excelente e **inventa fatos com
  confiança**, inclusive *diferente a cada geração*. Não use para perguntas factuais de mundo
  aberto.
- **Confabulação de argumentos** — quando falta informação no pedido, ele tende a inventar em
  vez de perguntar ("evento dia 31 às 16h" → inventa mês e ano). Um verificador de ancoragem
  determinístico ajuda; o código está no repositório.

⚠️ Para ferramentas de texto livre, a métrica de "resultado idêntico ao da referência" é
severa demais — duas consultas diferentes cumprem a mesma tarefa. Aqueles 8% são **piso**,
não estimativa.

**Contexto:** `seq_len` 2048, e um catálogo de 14 ferramentas ocupa ~1.076 tokens (53% da
janela). Catálogos menores melhoram acurácia e liberam contexto.

## Reprodução

Código, dados e todas as medições: <https://github.com/brcampidelli/llm-ptbr>.
O ciclo completo de autoaprendizado está em `docs/agentico-medicao.md`, incluindo os dois
erros de avaliador que a auditoria pegou antes de virarem conclusão.
