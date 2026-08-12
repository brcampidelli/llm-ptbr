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
---

# Bee-150M-PT-SFT

Versão ajustada por instruções do [`bee-150m-pt-base`](https://huggingface.co/BrCamp/bee-150m-pt-base)
— 151,2M parâmetros, pré-treinado do zero em português (0,844 bpb, à frente do Tucano-160m
com 9× menos tokens).

## Uso

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("BrCamp/bee-150m-pt-sft")
modelo = AutoModelForCausalLM.from_pretrained("BrCamp/bee-150m-pt-sft")

msgs = [{"role": "user", "content": "Resuma o texto abaixo em uma frase:\n\n..."}]
entrada = tok.apply_chat_template(msgs, return_tensors="pt", add_generation_prompt=True)
print(tok.decode(modelo.generate(entrada, max_new_tokens=120)[0]))
```

Formato ChatML (`<|im_start|>` / `<|im_end|>`), com `chat_template` embutido.

## Treino

7.152 exemplos (5.657 instruções em PT + 1.495 de uso de ferramentas), full fine-tune,
`lr 6e-4` cosine · 2 épocas · `max_seq_len` 2048 · batch efetivo 32 · bf16. Loss **mascarada
no prompt**: o modelo é cobrado só pelo que responde.

| holdout | eval_loss | acurácia/token |
|---|---:|---:|
| instruções PT (n=300) | 1,7592 | 0,6074 |
| uso de ferramentas (n=150) | 1,0672 | 0,7693 |

Cada hiperparâmetro foi **medido, não herdado** — a varredura de LR (curva em U de 6 pontos,
com ruído de 0,001) e a de épocas estão em
[`docs/sft-resultado.md`](https://github.com/brcampidelli/llm-ptbr/blob/main/docs/sft-resultado.md).

## ⚠️ Limitações — leia antes de usar

**O SFT ensinou formato, não fatos.** O modelo responde em português fluente, estruturado e
para no fim do turno — e **inventa fatos com confiança**. Pior: inventa *diferente a cada
geração* (perguntado duas vezes sobre Machado de Assis, respondeu "nasceu em 1839" — correto —
numa amostragem e "nasceu em 1831, em São Paulo" na outra). Ele amostra plausibilidade; não
tem o conhecimento guardado.

Isso é o esperado em 151M parâmetros e **não se corrige com mais SFT** — só com um pré-treino
maior.

**Não use** para perguntas factuais de mundo aberto, conselhos médicos/jurídicos/financeiros,
ou qualquer decisão em que uma afirmação inventada cause dano.

**Use** onde o conhecimento **vem no contexto**: extração estruturada, resumo, reescrita,
classificação, formatação — tarefas em que o texto de entrada contém a resposta e o modelo só
precisa manipulá-lo em bom português.
