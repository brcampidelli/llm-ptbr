# Estágio 2 — arquitetura de pós-treino: 27 braços medidos, e um ganho só

> **2026-08-20.** Grid do E2 completo: 27 treinos (15 na primeira grade + 12 na grade de LR
> corrigida), 27 braços avaliados em 7 réguas, mais o controle do modelo base sob protocolo
> idêntico. RTX 5090 no RunPod, ~6 h de pod, **US$ ~6**.

---

## 1. O veredito em uma linha

**O SFT entrega uma capacidade e não entrega as outras seis.** Execução agêntica sai de
**0/85 para 55/85 (64,7%)**. Instrução fica praticamente parada, sentimento é miragem, e
resumo, atendimento e código continuam em zero — os três por motivos que agora estão
diagnosticados e são do **modelo**, não da régua.

E o eixo de arquitetura tem resposta: **adapter especializado > full FT > adapter multi-task.**

---

## 2. A tabela que decide, com réguas COMPLETAS

| | **b-ferramenta 1,2e-3** | a-tudo 6e-4 | base (chat) | base (cru) |
|---|---|---|---|---|
| **agêntico — executou e cumpriu** (n=85) | ⭐ **64,7%** | 48,2% | 0,0% | 0,0% |
| JSON válido | 88,2% | 81,2% | 0,0% | — |
| ferramenta certa | 81,2% | — | 0,0% | — |
| argumentos exatos | 37,6% | 21,2% | — | — |
| under-calling | 4,7% | 5,9% | **100%** | — |
| ⚠️ over-calling (n=65) | **13,8%** | 18,5% | 0,0% | — |
| **instrução** (n=1002 instruções) | 32,0% | 29,2% | 27,4% | 30,0% |
| **sentimento** (n=600) | 51,3% | 60,7% | 47,3% | 47,3% |
| tradução en→pt (BLEU) | 12,4 | 17,2 | **3,0** | **28,1** |
| resumo · atendimento · código | 0,0 | 0,0 | 0,0 | 0,0 |

O `64,7%` reproduziu **exato** entre o n reduzido (usado para comparar os 27 braços) e a régua
completa. O aparato é determinístico, como no E0.

---

## 3. ⭐ O ganho: agêntico, e ele é grande

Por ferramenta, no vencedor (n≥4 para ser decidível):

| ferramenta | acerto |
|---|---|
| `get_stock_price` · `send_email` | 100% |
| `get_weather` | 91% |
| `summarize_url` | 86% |
| `list_dir` · `read_file` | 80% |
| `translate_text` | 50% |
| `calculator` | 33% |
| `web_search` | 15% |
| `http_get` | 0% |

⭐ **O gargalo mudou de lugar.** No baseline nada funcionava porque o modelo nunca emitia
chamada. Agora ele emite JSON válido em 88,2% e escolhe a ferramenta certa em 81,2% — mas só
acerta os **argumentos exatos** em 37,6%. O trabalho seguinte não é "ensinar a chamar", é
**ensinar a preencher**.

⚠️ **E um passivo novo, previsto no baseline.** `over-calling` era 0% e virou **13,8%**. Isso
não é regressão: era 0% porque o modelo não chamava nada, e o documento do E0 já dizia que
"um número que só é bom porque o comportamento inteiro está ausente não é linha de base de
segurança". O número a bater agora é 13,8%, e o projeto já tem uma política determinística
que fez exatamente esse trabalho no Bee-150M.

---

## 4. 🔴 As três capacidades em zero — e por que o zero é do modelo

Vinte e quatro braços marcando **exatamente 0,00** nas mesmas três réguas é assinatura de
aparato. Foi investigado lendo a saída crua, e desta vez o aparato está certo:

| régua | o que o modelo escreve |
|---|---|
| **resumo** | **copia a fonte**. Pedido de 1.088 chars → saída de 985. Compressão ≈ 0,90 contra o limite de 0,35 |
| **código** | pede esclarecimento diante de uma assinatura de função: *"preciso saber qual é o número inteiro positivo. Por favor, informe…"* |
| **atendimento** | prosa em vez de JSON, com invenção: criou o site `br-292042.com.br`, respondeu *"os R$ 3.954,68 são R$ 2.540,00"* repetindo seis vezes, e leu **"cadê a entrega"** como **CADE**, o Conselho Administrativo de Defesa Econômica, explicando direito da concorrência |

⭐ **A leitura que atravessa os três: o SFT ensinou o modelo a ser conversacional, e
conversacional é o modo errado para completar código e para resumir.** O base divagava; o
modelo pós-treinado pergunta educadamente. Os dois produzem zero código. Isso é um resultado
sobre a **mistura de dados**, não sobre arquitetura de adapter: o grupo simbólico tem 2.267
exemplos e não ensinou a emitir função.

---

## 5. 🔴 Tradução: o controle inverteu a conclusão

Primeira leitura, comparando os braços com o baseline do E0: *"tradução caiu de BLEU 27,1 para
2,6–17,2, regressão em todos os braços"*. Errado.

| | BLEU en→pt |
|---|---|
| base, texto cru | **28,1** |
| **base, com chat template** | **3,0** |
| melhor braço, com chat | **17,2** |

**O template de chat sozinho custa 25 pontos de BLEU no modelo base.** Contra o controle
correto, o SFT não destruiu tradução — **recuperou 14 dos 25 pontos** que o formato tirou.

⚠️ O que sobra é mais preciso e continua sendo um problema: **a adaptação de formato é
incompleta.** Nenhum braço volta aos 28,1 do texto cru, e a capacidade de traduzir existe no
modelo — está apenas inacessível pelo formato em que ele vai ser usado.

⭐ E a lição de método: eu tinha declarado a regressão **antes** de o controle chegar. O
controle custou 5 minutos de GPU.

---

## 6. Sentimento: a miragem que a própria régua denunciou

No n reduzido, um braço marcou **75,3%** contra 47,3% do base — salto enorme numa capacidade
com **4 exemplos** no SFT inteiro. Na régua completa (n=600): **51,3%** e **60,7%**.

E o aviso saiu impresso: *"VIÉS FORTE: 99% das respostas são de uma classe só. A acurácia aqui
é prior, não leitura de sentimento"*. Os dois braços **perdem para o léxico de 60 palavras**
por 27,7 pp e 18,3 pp.

⭐ Foi o piso alto fazendo o trabalho dele: sem um piso trivial forte, 75,3% teria virado
manchete.

---

## 7. O eixo de arquitetura

| braço | agêntico | instrução |
|---|---|---|
| **b-ferramenta** (adapter especializado) | **64,7** | **32,0** |
| c-tudo (full FT) | 61,2 | 25,2 |
| a-tudo (adapter multi-task) | 48,2 | 29,2 |

**A disputa de capacidade aparece de novo, agora em 345M.** O full FT é o **pior em instrução**
(25,2, abaixo do próprio base) enquanto lidera o agêntico — mexer em todos os pesos compra uma
capacidade vendendo outra. O adapter especializado é o melhor nas duas.

⚠️ **Ressalva que não pode sumir:** o número do braço (b) supõe **roteador perfeito** — cada
pedido indo ao adapter certo. É **teto**, não sistema. O roteador não foi medido, e comparar o
teto do (b) com o número real do (a) e do (c) favorece o (b).

---

## 8. O que este estágio custou em erros — cinco, e nenhum deu erro

| # | sintoma | causa real |
|---|---|---|
| 1 | régua agêntica em **0,0%** num modelo que emitia a chamada perfeita | `<\|im_end\|>` não estava ligado como parada; a geração ia ao teto e o parser recebia 5 chamadas concatenadas |
| 2 | idem, nos adapters | `--chat` faltando: treinados em ChatML, medidos em texto cru |
| 3 | 15 braços empatariam | `eval_agentic_exec` não tinha `--peft` — mediria o base 15 vezes |
| 4 | 7 de 15 braços mortos | grade de LR do LoRA **inteira** 5–20× acima do ótimo medido (6e-4) |
| 5 | 3 adapters treinados e invisíveis | `NameError` abortou a gravação do JSON **depois** do treino |

E dois de instrumentação: o grid imprimiu **"com erro: nenhum"** enquanto 7 braços tinham
divergido (loss 2,2 → 7,27, o número estava em `trainer_state.json` desde o fim do run); e um
vigia esperando por `pgrep -f cadeia.sh` casou com a **própria linha de comando** e travou
para sempre.

⭐ **O fio comum: "terminou sem erro" não é "funcionou".** Treino divergido sai com código 0 e
grava pesos. Escrita que falha depois do trabalho caro não desfaz o trabalho. Vigia que espera
por si mesmo nunca acorda. Nenhum acende luz vermelha.

⚠️ E o defeito de terminador continua **no modelo**, medido: o LoRA termina com
`<|im_start|>` (id 1) em vez de `<|im_end|>` (id 2) em **106 de 150** gerações, e em 44 não
termina. Zero acertos. Provável causa: LoRA não treina `lm_head`/`embed_tokens`. Em produção
isso exige parar em ambos, ou treinar o adapter incluindo essas camadas.

---

## 9. O que isto decide para o E3

1. **Adapter especializado é o formato.** Mas o roteador precisa ser medido antes de o número
   do braço (b) valer como sistema.
2. **O gargalo agêntico virou `argumentos exatos` (37,6%)**, não mais a emissão da chamada.
3. **Resumo, atendimento e código precisam de dado, não de arquitetura.** O grupo simbólico
   tem 2.267 exemplos e não ensinou a emitir código: o problema é o que os exemplos ensinam.
4. **Tradução tem 25 pontos de BLEU presos atrás do formato** — capacidade que existe e não
   está acessível. É o ganho mais barato disponível.
5. **`over-calling` 13,8%** entra como alvo, com a política determinística que já funcionou.
