# Censo de mistura por token — E1 (2026-08-19)

> Primeiro entregável do plano de pós-treino. Custo: **US$ 0**, minutos de CPU.
> Achou uma distorção de **8×** que nenhum número anterior do projeto mostrava.

## O que se media antes, e por que enganava

O projeto descrevia a mistura em **exemplos**: *"7.152 exemplos, dos quais 1.495 agênticos
= 20,9%"*. Duas razões independentes fazem disso a métrica errada:

1. **Exemplos têm tamanhos muito diferentes.** O prompt agêntico carrega um catálogo de
   ferramentas de ~1.100 tokens; um exemplo de sentimento é uma frase e um rótulo.
2. ⭐ **A loss é mascarada no prompt.** O `bee/sft.py` converte `messages` em
   `{prompt, completion}` e o TRL cobra o modelo **apenas pelo que ele responde**. Tokens de
   prompt não produzem gradiente. A fração de treino que cada capacidade recebe é a de
   tokens de **completion** — nem exemplos, nem tokens totais.

## O resultado

| capacidade | exemplos | % exemplos | tok completion | **% do sinal** | méd. prompt | méd. compl. |
|---|---:|---:|---:|---:|---:|---:|
| instrução PT (geral) | 5.657 | 66,6% | 3.366.881 | **85,6%** | 33 | 595 |
| educacional BNCC | 1.676 | 19,7% | 399.383 | **10,2%** | 39 | 238 |
| agêntico (tool-use) | 1.495 | 17,6% | 107.878 | **2,7%** | 1.094 | 72 |
| agêntico (reforço) | 1.022 | 12,0% | 46.712 | **1,2%** | 1.096 | 46 |
| multi-turno | 864 | 10,2% | 11.522 | **0,3%** | 1.175 | 13 |

🔴 **O agêntico parecia 20,9% da mistura e recebe 2,7% do sinal de treino.** Distorção de
~8×. O multi-turno, 10,2% dos exemplos, recebe **0,3%**.

**A causa é estrutural, não um erro de montagem:** a resposta agêntica *é* curta — uma
chamada de ferramenta de 72 tokens em média, contra 595 de uma resposta discursiva. O
catálogo de 1.100 tokens que torna a tarefa possível não ensina nada, porque está mascarado.

⚠️ **Isto contradiz a leitura anterior do projeto.** `docs/sft-resultado.md` registrou que
somar 1.495 exemplos agênticos "não moveu o holdout PT" e atribuiu isso ao truncamento
(`max_seq_len` curto, §2b das lições) — que era real e foi corrigido. Mas mesmo **depois** da
correção o agêntico continua marginal, por outro motivo: ele carrega 2,7% do gradiente.
Duas causas distintas, o mesmo sintoma.

## Truncamento em 2048 — o desastre do 150M NÃO se repete

| arquivo | estoura 2048 | % | **prompt já estoura** | compl. perdida |
|---|---:|---:|---:|---:|
| sft_ptbr | 84 | 1,5% | **0** | 47.933 |
| sft_agentic | 2 | 0,1% | **0** | 863 |
| sft_misto | 86 | 1,2% | **0** | 48.796 |

⭐ A coluna que importa é **"prompt já estoura" = 0** em todos os arquivos. Foi exatamente
essa condição que, no Bee-150M com `max_seq_len=1024`, deixou o exemplo inteiramente
mascarado e fez o TRL **descartar 150 de 150** exemplos agênticos sem erro. Com contexto de
2048, nenhum exemplo é perdido inteiro. A perda é de 1,4% dos tokens de completion, no fim
de respostas longas.

## O que isto muda no plano

1. **A mistura precisa ser reponderada por tokens de completion**, não por exemplos — e o
   Estágio 4 (otimização de mistura) deve otimizar sobre essa base, senão otimiza a coisa errada.
2. **O agêntico precisa de mais massa de completion**, não de mais exemplos: respostas
   agênticas mais longas (raciocínio curto antes da chamada) ou mais chamadas por exemplo.
3. **O catálogo de ferramentas de 1.100 tokens é caro** — 94% do exemplo agêntico é prompt
   mascarado. Vale medir se um catálogo enxuto (só as ferramentas relevantes) mantém a
   execução e libera contexto.

## Reprodução

```bash
python comeia/data/censo_tokens.py
```
