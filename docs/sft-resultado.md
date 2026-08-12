# SFT do Bee-150M — o que foi medido (2026-08-12)

Primeiro pós-treino sobre a base **correta** (a de 21,7B tokens, 0,844 bpb). Tudo aqui foi
medido no mesmo dia em que o pré-treino terminou, na mesma RTX 5090 que estava ociosa.

**Régua:** `eval_loss` no holdout de 300 exemplos PT (`sft_ptbr.eval.jsonl`), com a loss
**mascarada no prompt** — o modelo é cobrado só pelo que ele responde, nunca pela pergunta
que o usuário fez. Menor é melhor.

---

## 1. ⭐ O learning rate herdado estava errado — e ele veio do modelo bugado

O LR de **1e-3** que este projeto vinha usando para SFT foi escolhido numa varredura de 6
pontos feita **sobre o Bee-v3, o modelo que treinava para prever t+2**. Reusar aquele número
sobre a base correta seria repetir em miniatura o erro que custou duas semanas: tratar uma
medição feita sobre um artefato como se valesse para o modelo consertado.

Remedido do zero (1 época, batch efetivo 32):

| LR | 5e-5 | 1e-4 | 3e-4 | **6e-4** | 1e-3 | 2e-3 |
|---|---:|---:|---:|---:|---:|---:|
| eval_loss | 2,086 | 1,957 | 1,814 | **1,800** | 1,852 | 2,038 |
| acurácia/token | 0,555 | 0,571 | 0,592 | **0,595** | 0,588 | 0,564 |

Curva em U limpa, mínimo em **6e-4**. O 1e-3 herdado é **2,9% pior**.

⭐ **E há uma medida de ruído embutida na varredura, de graça.** O ponto 1e-3 foi rodado duas
vezes por acidente (uma vez isolado, como teste de fumaça, outra dentro da varredura):
**1,853** e **1,852**. Repetibilidade de **0,001**. Isso torna a comparação decidível — a
vantagem do 6e-4 é 0,052, ou seja **~50× o ruído**. Sem esse número, "1,800 contra 1,852"
seria só uma impressão.

## 2. O default do próprio script decorava

`sft.py` vinha com `--epocas 3.0`. Medido com o LR já corrigido:

| épocas | 1 | **2** | 3 |
|---|---:|---:|---:|
| eval_loss | 1,800 | **1,768** | 1,850 |
| acurácia/token | 0,595 | **0,605** | 0,602 |

Na terceira época a **acurácia por token continua alta (0,602) enquanto a loss piora** — a
assinatura clássica de decorar: o modelo acerta o token mais provável com mais frequência,
mas fica confiante demais e paga caro quando erra. Com 5.657 exemplos, duas épocas é o ponto.

**Config final: `--lr 6e-4 --epocas 2 --batch 16 --grad-accum 2`** (batch efetivo 32).

⚠️ O `--batch 2` que estava no default era o **teto físico da RTX 5070 de 8 GB**, não uma
escolha de qualidade. Na 5090 cabe 16, e uma época leva 90 segundos.

---

## 3. 🔴 O SFT descartava 100% dos exemplos agênticos — sem erro, sem aviso

Ao juntar `sft_ptbr` (5.657) + `sft_agentic` (1.495) num treino misto de 7.152 exemplos, o
holdout PT **não se mexeu**: 1,7674 contra 1,7682 do só-PT, diferença de 0,0008 — dentro do
ruído de 0,001 medido acima. Somar 1.495 exemplos de outro domínio e não mover nada é o tipo
de resultado que não deveria acontecer.

Não aconteceu mesmo. Os exemplos nunca entraram:

| | |
|---|---|
| prompt agêntico | **1.096–1.191 tokens** só no catálogo de ferramentas |
| `--max-seq-len` (default) | **1.024** |
| exemplos com total ≥ 1024 | **150 de 150** (100%) |

Quando o prompt sozinho já passa de `max_length`, a *completion* é truncada fora, o exemplo
fica **inteiramente mascarado**, e o TRL o descarta silenciosamente.

⭐ **A confirmação numérica veio da contagem de passos.** O treino previu ~447 passos e
executou **354** — exatamente 79,2%. E 1.495/7.152 = **20,9%**. Bate na casa decimal: nenhum
dos exemplos agênticos entrou. O modelo "misto" era o só-PT com outro nome.

**É a mesma família do bug de rótulos e da amostragem com reposição: dado some, nada
reclama, e a loss continua caindo bonito.** Terceira vez neste projeto. A defesa agora está
no código:

- default `--max-seq-len` **1024 → 2048** (o `seq_len` do pré-treino)
- `sft.py` **ABORTA** se mais de 1% do dataset for descartado por truncamento
  (`--permitir-descarte` para o caso raro em que isso é intencional)
- `eval_sft.py` reporta quantos foram descartados e recusa devolver métrica de conjunto vazio

### O resultado depois da correção

Ambos com `--max-seq-len 2048`, zero descartes, `--lr 6e-4 --epocas 2`:

| modelo | treino | **holdout PT** | **holdout agêntico** |
|---|---|---:|---:|
| `ep_2` | 5.657 PT, seq 1024 | 1,7682 | *dados descartados* |
| `v2_ptbr` | 5.657 PT, seq 2048 | **1,7517** | 2,1838 |
| ⭐ `v2_misto` | 7.152 PT+ag, seq 2048 | 1,7592 | **1,0672** |

Duas leituras:

1. **Só corrigir o comprimento melhorou o português em 0,93%** (1,7682 → 1,7517). O
   truncamento parcial já cobrava caro mesmo nos exemplos PT, que são bem mais curtos.
2. **Somar o agêntico troca 0,43% de piora em PT por 51,1% de ganho no agêntico**
   (2,1838 → 1,0672). A piora de 0,0075 é real — 7,5× o ruído — mas o câmbio é claramente
   favorável. **`v2_misto` é o modelo final.**

---

## 4. O que ele escreve — e a divergência que importa

Sonda de 8 perguntas fixas (`bee/chat.py --sonda`), amostragem temperatura 0,7.

**A forma foi aprendida.** O modelo deixou de completar texto e passou a *responder*: abre
com "Claro! Aqui está...", estrutura em listas, usa markdown, e **para no fim do turno**. Isso
é exatamente o que um SFT deve entregar, e entregou.

**O conteúdo factual, não.** Dos 8, a maioria contém erro:

| pergunta | resposta | veredito |
|---|---|---|
| capital de Minas Gerais | "é **Minas Gerais**" | ❌ (Belo Horizonte) |
| liste 3 frutas brasileiras | "Mix de Frutas Tropicais" (1 item, não é fruta) | ❌ |
| traduza "bom dia" | "Bom dia! Tradução sugerida: **boa tarde**" | ❌ nem traduziu |
| quem foi Machado de Assis | 1839 ✅, *Brás Cubas* ✅, mas "São Paulo" ❌, "ficção científica" ❌ | parcial |
| escreva uma frase sobre o mar | coerente e bem escrita | ✅ |

⚠️ **E os fatos não erram de forma estável — eles variam entre rodadas.** Perguntado duas
vezes sobre Machado de Assis, o modelo respondeu "nasceu em 1839" (correto) numa amostragem e
"nasceu em 1831, em São Paulo" na outra. Isso é diagnóstico: ele não *tem* o fato guardado
errado, ele está **amostrando plausibilidade** a cada geração. Nenhuma quantidade de SFT
conserta isso.

⭐ **A leitura correta disso não é "o SFT falhou".** O SFT ensina *formato*, não *fatos* —
conhecimento factual entra no pré-treino, e 150M parâmetros com 21,7B tokens simplesmente não
comportam a capital de cada estado. O modelo faz o que essa escala permite: **fala português
muito bem e inventa fatos com confiança**.

**A consequência prática é uma decisão de produto, não um defeito a consertar:** este modelo
não serve para perguntas factuais de mundo aberto, e serve bem para tarefas em que o
conhecimento **vem no contexto** — extração estruturada, resumo, reescrita, classificação.
Que é precisamente o que a COMEIA faz, com `groundedness` já medida. Aumentar o SFT não muda
isso; só um pré-treino maior mudaria.

---

## 4. Régua reutilizável

`bee/eval_sft.py` avalia qualquer modelo em qualquer holdout **reusando o próprio
`SFTTrainer`** e importando a conversão `messages → prompt/completion` do `sft.py`. A máscara
é idêntica por construção, em vez de reimplementada — que é como se mede outra coisa sem
perceber.

```bash
python bee/eval_sft.py --modelo /workspace/misto \
  --eval comeia/data/processed/sft_ptbr.eval.jsonl \
         comeia/data/processed/sft_agentic.eval.jsonl
```

---

## Artefatos

| arquivo | bytes | sha256 | conteúdo |
|---|---:|---|---|
| `bee-150m-pt-final.tar.gz` | 560.900.848 | `9561458f…af5c4d86` | a **base** de 21,7B tokens (fp32) |
| `bee-150m-pt-sft.tar.gz` | 239.678.970 | `d6805118…1488e0c7` | o **SFT final** = `v2_misto` (bf16) |

Config do SFT final: `--lr 6e-4 --epocas 2 --max-seq-len 2048 --batch 8 --grad-accum 4`
(batch efetivo 32), sobre `sft_misto.jsonl` = `sft_ptbr` + `sft_agentic`, 7.152 exemplos.

⚠️ O primeiro pacote saiu com **1,62 GB** porque o `SFTTrainer` deixa `checkpoint-*` com
estados do otimizador dentro de `output_dir`. Sempre remover antes de empacotar ou publicar —
são ~1,4 GB de lixo que não serve a ninguém que baixe o modelo.
