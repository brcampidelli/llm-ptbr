# Estudo — 21 papers do arXiv (2026-07-28)

> Lidos durante o pré-treino do Bee-150M. Formato de sempre: o que o paper diz → **o que muda no
> Bee**. Paper que não muda nada eu digo que não muda, em vez de escrever parágrafo bonito.

## ⚠️ A leitura de conjunto, antes de tudo

**Dos 21, apenas 4 são acionáveis para o Bee hoje.** A maioria ataca *inferência e pós-treino em
modelos de 3B–32B* — problemas que só teremos daqui a dois ou três degraus da escada. Dois nem são
sobre LLMs (síntese lógica de circuitos, capacidade de Shannon de ciclos ímpares).

Isso não é crítica à seleção: é o retrato do campo em julho/2026. **A pesquisa se concentra em fazer
modelos grandes rodarem barato, não em treinar modelos pequenos do zero.** Para o nicho que o Bee
ocupa, há pouca companhia — o que é ao mesmo tempo o risco e a oportunidade da aposta.

---

# ⭐ Os 4 que mudam alguma coisa

## 1. `2607.22554` — "Same Question, Different Answers" · **o mais importante dos 21**

Mede **estabilidade sob paráfrase**: a mesma pergunta reescrita de formas semanticamente equivalentes.
Testado em 13 modelos, incluindo **Qwen3 0.6B e 1.7B** — a nossa faixa.

| achado | número |
|---|---|
| variação da **acurácia agregada** entre paráfrases | 0–5% (parece estável) |
| **taxa de incompatibilidade** (predições conflitantes) | **23%** |
| conjuntos de paráfrase com ao menos um conflito | até **47%** |
| gap entre capacidade latente (`A_any`) e confiável (`A_strict`) | ~**30%** |

**⭐ O que muda: este paper é a versão publicada e quantificada da lição mais cara deste projeto.**
Em 2026-07-25 a `chat_ptbr` passou por **7 benchmarks de múltipla escolha a n=300** e foi declarada
"não conclusiva" — enquanto respondia em português a perguntas em inglês 10 de 12 vezes. A métrica
agregada não tinha como ver. Agora temos o mesmo fenômeno medido em escala: **a acurácia agregada
varia 0–5% enquanto 23% das respostas se contradizem.**

**Ação concreta:** o **Gate 2** (Bee-150M × SmolLM2-135M) não pode ser só perplexidade. Vou incluir
uma coluna de **consistência sob paráfrase**: mesma pergunta em N formas, mede-se quantas dão a mesma
resposta. É barato (não exige treino), e é exatamente o instrumento que nos faltava antes.

## 2. `2607.20806` — "Profiling Lightweight LLMs" (framework PTME)

Mede Precisão, Tempo, Memória e Energia **juntos**, em 6 modelos de 1,1B–7B sob 5 orçamentos de
recurso.

| correlação | R |
|---|---|
| proxies (params, FLOPs) ↔ **custo** | **0,95–1,0** (forte) |
| proxies ↔ **precisão** | **0,36–0,48** (fraca) |

**⭐ O que muda: isto é a explicação publicada do que aconteceu conosco hoje.** A fórmula 6ND previu
31,4 h para o Bee-150M; o real medido foi ~65 h — e as três hipóteses que testei (checkpointing, I/O,
laço Python) todas falharam, sobrando a explicação estrutural de que 30 camadas estreitas são
ineficientes em GPU. O paper generaliza: **contagem de parâmetros e FLOPs preveem custo bem, mas
preveem acurácia mal**, e "nenhum modelo domina em todas as dimensões".

**Ação:** o model card do Bee deve reportar **tempo e memória medidos**, não estimados por 6ND. Já
temos o hábito (medimos tudo), mas vale registrar que a literatura sustenta a desconfiança.

## 3. `2607.17946` — CoT "annealing" e a geometria da paisagem de perda

Testado em **Qwen 3.5 0.8B** e **Llama 3.2 1B** — nossa faixa. Estrutura o Chain-of-Thought em três
fases (exploração → transição → convergência) durante o SFT, e mede o **maior autovalor da Hessiana**
como proxy de estabilidade.

| configuração | λmax (menor = paisagem mais suave) | MMLU Moral (0,8B) |
|---|---:|---:|
| RLHF base | 4083,87 | 24,67% |
| SFT base | 1402,77 | — |
| CoT padrão | 1345,65 | — |
| **CoT "annealing"** | **1218,04** | **41,67%** |

**O que muda:** guardado para a **fase de SFT do Bee**, não para agora. O ganho de +17 pp em 0,8B é
grande e vem de *como o dado de raciocínio é estruturado*, não de mais dados — que é exatamente o
tipo de alavanca que serve a quem tem pouca GPU. ⚠️ Ressalva: o benchmark é de valores/ética, e a
transferência para PT-BR genérico não está demonstrada.

## 4. `2607.24688` — Entity Matching: estudo fatorial com 1.215 fine-tunes

Três arquiteturas × três variantes × três tamanhos da família Qwen3, nove datasets.

**⭐ O achado que importa:** *"modelos maiores não necessariamente performam melhor, e dependem mais
de **shortcut learning**"*. E: a **variante** do modelo (o que ele viu no pré-treino) pesa mais que o
tamanho para bi-encoders.

**O que muda:** é o argumento mais direto que li a favor da tese do Bee. Nossa aposta é que **um 150M
treinado em português vence um 135M treinado em inglês, no português** — não por tamanho, mas por
adequação do pré-treino ao domínio. Este paper mostra o mesmo padrão noutro eixo: a origem do
pré-treino vence a escala. É evidência lateral, não prova; mas é o tipo de evidência que faltava.

---

# Guardados para a Fase 5 (quantização/serving) — nada a fazer agora

- **`2607.21985` — Unified Static-Dynamic Pruning (SPDP).** 1,24–1,37× de speedup (até 2,51×), 25%
  mais esparsidade com a mesma perplexidade. Pós-treino, sem retreinar.
- **`2607.20434` — Break Through the Compression Bottleneck.** Prova que quantização e decomposição
  de baixo rank **não são ortogonais**, e que a ordem certa é **low-rank ANTES de quantizar**.
  LLaMA-3-8B: 57,7 vs 50,4 pontos na ordem inversa. ⚠️ Testado em 7B–70B.
- **`2607.18081` — SelectInfer.** Carrega ~70% dos neurônios FFN e computa ~40% deles. 13,2% menos
  memória, 1,53× mais rápido que 4-bit. ⚠️ Otimizado para 3B; **rende menos em modelos menores** — o
  próprio paper diz. Relevante para a meta "rodar no RTX 5070 8 GB", com essa ressalva.

# Os 14 que não mudam nada (e por quê)

| paper | por que não se aplica |
|---|---|
| `2607.21179` ReMo | compressão de token omni-modal; exige encoders de áudio/vídeo + YOLO, 3B–30B |
| `2607.08221` LUMI | compressão de imagem com LLM congelado; Qwen3-0.6B fica **muito pior** que os grandes |
| `2607.07847` Continual Learning | Qwen3-8B; sem avaliação sub-1B |
| `2607.23986` MEMOIR | recomendação; usa TinyLlama-1.1B só como encoder congelado |
| `2607.22690` LazyMem | memória de agente; mínimo 4B |
| `2607.18246` Phionyx | runtime determinístico; estágio de pesquisa, single-instance |
| `2607.23802` RLSVR/SpyRL | RL pós-treino em 4B–8B |
| `2607.23672` Logic Optimization | **não é sobre LLM** — síntese de circuitos |
| `2607.22758` Spectral Drift | rede multi-agente clínica; Bio_ClinicalBERT |
| `2607.22002` VIGOR | alocação de rollout em GRPO; 1,5B–8B |
| `2607.21517` Shannon capacity | **não é sobre LLM** — combinatória, LLM usado como ferramenta |
| `2607.21609` HierFlow | busca de workflow agêntico com GPT-4o-mini |
| `2607.20503` LeanFlow | autoformalização em Lean; Kimi-K2.6, GPT-5.5 |
| `2607.20433` Moir | edição de conhecimento; 7B–8B instruction-tuned |

⚠️ **Sobre os dois "não é sobre LLM":** não são erro de curadoria — são exemplos de LLM *como
ferramenta científica* (achar construções combinatórias, auditar operadores de síntese). Interessante
como sinal do campo, irrelevante para construir o Bee.

---

# O que eu levo deste estudo

1. **Uma ação imediata e barata:** consistência sob paráfrase entra no Gate 2. É o instrumento que
   nos faltou quando a `chat_ptbr` enganou 7 benchmarks, agora com respaldo publicado e números.
2. **Uma confirmação desconfortável:** proxies de custo (params, FLOPs) preveem acurácia mal — o que
   já sentimos na pele hoje ao errar 31 h vs 65 h. Medir sempre; estimar só para planejar.
3. **Uma evidência a favor da tese:** adequação do pré-treino ao domínio pode vencer escala, e
   modelos maiores tendem mais a *shortcut learning*.
4. **Uma constatação sobre o campo:** quase ninguém está treinando modelos pequenos do zero. As 14
   não-aplicações não são desperdício — são o mapa de onde o Bee está sozinho.
