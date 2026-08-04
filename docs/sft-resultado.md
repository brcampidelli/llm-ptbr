# Bee-150M v3 — resultado do SFT (2026-08-04)

Full fine-tune do `bee-150m-v3` base em 5.657 instruções PT-BR, local na RTX 5070 8 GB.

## Config

| | |
|---|---|
| tipo | full fine-tune, 151,2M params (100% treináveis), bf16 — **sem LoRA** |
| dados | `sft_ptbr.jsonl` 5.657 exemplos · holdout `sft_ptbr.eval.jsonl` 300 |
| formato | `{prompt, completion}` → TRL mascara o prompt sozinho |
| batch | micro 2 × grad_accum 16 = **32 efetivo** · seq 1024 |
| LR | 2e-5 cosine, warmup 3% · 3 épocas · 531 passos |
| tempo | **27,8 min** (10,2 amostras/s) |

## Curva

| época | eval_loss | acurácia de token |
|---:|---:|---:|
| 0 (base) | 6,582 | 6,4% |
| 1,13 | 3,887 | 27,7% |
| 2,26 | 3,584 | 32,0% |
| 3,00 | **3,581** | **32,0%** |

⚠️ **A 3ª época não rendeu nada** (3,584 → 3,581; acurácia idêntica). Em 5,6k exemplos,
2 épocas bastam — a 3ª é ~9 min de GPU jogados fora.

## Veredito: o gate do SFT PASSOU

O gate declarado antes de treinar era *"o modelo aprendeu a forma de instrução?"*, não
*"ficou bom"*. Passou:

- **Aprendeu a parar.** O base emendava texto até o limite de tokens. O pós-SFT termina o
  turno. (Exigiu corrigir o `eos` — ver abaixo.)
- **Responde em vez de completar.** Em prompts **da distribuição de treino** (holdout, nunca
  vistos) ele produz português gramatical, no tópico, com estrutura de resposta:
  > *"Reescreva a frase para remover a ambiguidade…"* → `"O gerente do escritório viu o
  > funcionário saindo do escritório e depois do almoço…"`

  Está errado (não resolve a ambiguidade, repete), mas é **uma tentativa de executar a
  tarefa** — coisa que o base não fazia.

## O que continua ruim, e por quê

**Perguntas curtas de conhecimento geral falham.** As 8 sondas (`docs/sonda-sft-v3.txt` vs
`docs/sonda-base-v3.txt`) saem vazias ou incoerentes. Duas causas somadas:

1. **Fora da distribuição.** O corpus de SFT é de instruções longas e elaboradas (mediana 463
   tokens de resposta). *"O que é o Brasil?"* não se parece com nada que ele treinou.
2. **O base não sabe os fatos.** bpb 3,457 contra 2,010 do SmolLM2 — o SFT ensina forma, não
   conhecimento. Não havia como sair diferente.

**A distribuição de saída é quase plana.** O token mais provável na 1ª posição tem só 10–15%
de massa, e costuma ser `'\n'`. Consequência prática: **decodificação gulosa colapsa** (gera
quebras de linha), e só com amostragem (temp 0,7) o modelo escapa. Isso é assinatura de modelo
subtreinado, não bug do SFT.

**Sinal de que o SFT não absorveu tudo que podia:** 47% dos completions do treino começam com
`'Claro'`, `'Aqui'` ou `'Para'`, e nenhuma dessas aparece no top-5 do modelo. Um SFT saturado
teria aprendido essa distribuição trivial. Sugere que **LR 2e-5 é conservador demais** para
151M — é LR de modelo de 7B. Para a próxima rodada: 1e-4 a 3e-4, 2 épocas.

## Dois bugs achados e corrigidos

**1. O modelo não saberia parar.** O pré-treino deixou `eos_token_id = <|endoftext|>` (0), mas
o `chat_template` fecha turno com `<|im_end|>` (2). Sem corrigir, o pós-SFT geraria a resposta e
emendaria turnos de usuário inventados sem fim. `sft.py` agora aceita `[0, 2]` como fim de
geração.

**2. O micro-batch escolhido era 8× mais lento.** O tensor de logits é `batch × 1024 × 32000`,
e a cross-entropy ainda faz upcast pra fp32. Medido na RTX 5070:

| micro-batch | tempo/passo | throughput | VRAM |
|---:|---:|---:|---:|
| 2 | 0,31 s | **6,5 amostras/s** | 5,78 GB ✓ |
| 4 | 4,02 s | 1,0 amostras/s | 10,67 GB — vaza pra RAM do host |
| 8 | 510 s | 0,06 amostras/s | estouro total |

A partir de 4 não cabe nos 8 GB e o passo cai 13×. O Liger (fused linear+CE, usado no
pré-treino) resolveria, mas **não instala com transformers 5.x**.

## Verificações feitas (não assumidas)

- Máscara de loss inspecionada nas labels reais do TRL: 81% dos tokens supervisionados, 1º
  supervisionado é `'Aqui'` logo após `<|im_start|>assistant\n`, prompt inteiro em −100. ✓
- Template formatado conferido: sem duplicação de `<|im_start|>assistant`. ✓
- Pesos e tokenizer batem byte a byte com o repo HF (604.740.496 e 2.312.545 B). ✓
- 16,3% dos completions passam de 1024 tokens e são truncados no treino. ⚠️ tolerável agora,
  mas é perda real de supervisão nas respostas longas.

## Próximo passo

O gargalo **não é o SFT** — é o base. Repetir SFT com LR maior dá ganho marginal sobre um base
de bpb 3,457. As hipóteses que valem, em ordem, seguem as de `gate-2-resultado.md`:
qualidade/composição do corpus, geometria (razão d_model/camadas 19,2 vs 85–130 dos modelos
reais) e LR do pré-treino (3e-3, ~3× a referência).
