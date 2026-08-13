# Leituras de agosto/2026 — o que serve ao Bee, o que não serve, e o que serve depois

16 papers + 3 buscas do arXiv, lidos em 2026-08-13. Avaliados contra um critério só:
**isto funciona num modelo de 151M com janela de 2.048 tokens?**

---

## ⭐ O achado que enquadra tudo

**A literatura de agosto/2026 está dominada por *harness engineering* — e nenhum dos trabalhos
testa modelos abaixo de 7B.** A busca por "Harness Engineering" devolve doze trabalhos sobre
auto-evolução de harness (Evo-Bench, SBCO, DarwinX, Ouroboros, EvoHarness-RL, Argus,
One Recipe/TRIAGE, A²E); o menor modelo avaliado em qualquer um deles é o Qwen3.6-27B.

Isso confirma pelo lado de fora o que medimos por dentro: **o Bee está uma ordem de grandeza
abaixo do que este campo considera um modelo pequeno.**

Mas a tese central dessa literatura é a mesma que já adotamos: **tirar a confiabilidade de
dentro do modelo e pô-la no sistema em volta.** Verificador externo, roteador determinístico,
estado fora do modelo. Estamos na direção certa — só não podemos usar os métodos que exigem
que o próprio LLM planeje ou reescreva o harness.

---

## 1. Aplicável AGORA

### 🥇 Policy-as-Logic (arXiv:2608.11905) — o mais alinhado ao nosso problema

**Ideia:** separar extração de raciocínio. O LLM só extrai fatos; um solver ASP (Answer Set
Programming) decide segundo regras formais.

| domínio | baseline | com solver |
|---|---:|---:|
| Airline | 38% | **94–100%** |
| Tax | 7% | 31% |
| NBA | 39% | 49–50% (**10× menos tokens**) |

**Por que importa para nós:** é a formalização do que fizemos por instinto com
`ancoragem.py`. O nosso over-calling residual (21,5%) é, em boa parte, *decisão de política* —
"falta argumento obrigatório? então pergunte" — e política é exatamente o que um solver faz
melhor que um modelo de 151M.

⚠️ **A ressalva que pesa:** o menor modelo testado foi o Granite-4.1 **8B**, e ele desabou nos
domínios difíceis (Tax 31%, NBA 36%) por **erro de extração** — "colapso de classificação
padrão, erros de transcrição de dígitos, confusão entre campos". Ora, extração é justamente a
parte que sobra para o modelo. Se um 8B erra a extração, o Bee erra mais.

**Como usar assim mesmo:** deixar ao Bee só o que ele já provou fazer bem — argumento
**estruturado** (91% em `get_weather`, 89% em `get_stock_price`) — e mover a decisão de
*chamar ou não* para regra. Não é adotar o paper; é adotar a divisão de trabalho dele.

### 🥈 Lost in Compaction (arXiv:2608.11242) — um alerta que nos poupa de um erro

Compactação de contexto **perde 83% das instruções** (retenção medida: 17%).

**Por que importa:** nosso catálogo de 14 ferramentas ocupa **1.076 dos 2.048 tokens** (53% da
janela), e a saída óbvia seria comprimi-lo. Este paper diz que compactar ingenuamente destrói
justamente as restrições. **Encolher o catálogo (14 → 5-6 ferramentas) é seguro; resumi-lo
com um modelo não é.**

### 🥉 Inicialização por centroides (arXiv:2608.07816) — ⭐ o único que testa <1B e funciona

Ao expandir vocabulário, inicializar os embeddings novos a partir dos **centroides do espaço
semântico** em vez de aleatoriamente.

**Testado em Qwen3-0.6B** (Recall@5 0,047 → 0,051), convergência **25–40% mais rápida**,
"algumas linhas de código", sem overhead.

**Quando usar:** se um dia adicionarmos tokens dedicados de ferramenta ao vocabulário do Bee
(`<|tool|>`, nomes de ferramenta como token único) — o que resolveria o custo de tokenização
que medi (`"web_search"` = 5 tokens, código a 0,4487 tok/byte contra 0,2174 do PT). **Não
inicializar aleatório.** Guardar para esse dia.

---

## 2. Aplicável no PRÓXIMO degrau (não agora)

### EvoHarness-RL (arXiv:2608.05446) — a resposta certa para o nosso buraco de multi-turno

Abstrai o estado do agente em **Belief / Progress / Experience**, com quatro ações de
coordenação (`track`, `commit`, `recall`, `note`). Treino em duas fases: SFT em trajetórias
de especialista, depois GRPO sensível a custo (quando acessar vs. quando agir).

Qwen3-8B em ALFWorld: **96,9%** (visto) e 86,6% (não-visto), **+49 pp sobre ReAct**.

**Por que interessa:** nosso multi-turno é zero — nenhum dos 1.645 exemplos tem papel `tool`,
e a janela de 2k não comporta o retorno da ferramenta. Este trabalho mostra o caminho:
**o estado mora fora do modelo**, e o modelo só emite ações curtas de coordenação. É
compatível com uma janela pequena, porque nunca se pede que ele carregue o histórico.

⚠️ Testado em 8B. Para o Bee, o realista é implementar o **lado do orquestrador** (B/P/E como
estruturas em código) e deixar o modelo emitir só a chamada — sem a parte de RL.

### SBCO (arXiv:2608.10157) e Evo-Bench (arXiv:2608.09096)

Auto-evolução de harness com verificador. SBCO usa 4–5,5× menos orçamento; Evo-Bench mede
ganhos de ~16 pontos em modelos de fronteira.

**Veredito:** o Bee **não pode ser o evoluidor** — SBCO admite que "os ganhos são limitados
pela força do LLM base", e o menor modelo do Evo-Bench é 27B. Mas o Bee pode perfeitamente
ser o **modelo executado sob** um harness que outra coisa evoluiu. É a divisão que já
fazemos: eu escrevo o harness, o Bee roda dentro dele.

### One Recipe, Many Harnesses (arXiv:2608.10178) — uma advertência útil

Aplicando a mesma receita de evolução a 8 linguagens × 3 modelos: os conceitos entre harnesses
se parecem (Jaccard 0,55) mas as implementações são quase disjuntas (**Jaccard 0,12**). Só
**20–40%** de cada harness é genérico; a destilação universal recupera 48–68% dos ganhos.

**Leitura:** harness não transfere. O que funcionar para o Bee em PT não vai funcionar de
graça noutro contexto — e vice-versa. Isso desencoraja copiar harness de paper e encoraja
medir no nosso próprio holdout, que é o que temos feito.

---

## 3. Não aplicável (e por quê) — registrado para não reavaliarmos depois

| trabalho | por que não serve ao Bee |
|---|---|
| **ConMem** (2607.28126) — memória por Shapley, −88,2% tokens | usa GPT-4o; com GLM-4 despenca de 76% → 45,9%. Exige várias chamadas de LLM por decisão |
| **Ripple-Pivot** (2608.11742) — decodificação paralela, 4–10× | é para **diffusion LLMs** (LLaDA, Dream); o Bee é autorregressivo |
| **SinkFlex-RL** (2608.10357) — FlexAttention + sink | MoE grandes. ⭐ mas guardar o dado: −19,7% de VRAM a 4k tokens, e viabiliza 8k que antes dava OOM |
| **EdgeXpert** (2608.05303) — acelerador 28nm para MoE | hardware dedicado; o Bee é denso e já cabe em 300 MB |
| **RepoOMP** (2608.05855) — paralelização OpenMP, −47-68% tokens | Claude 4.5 / GPT-5.1 / Gemini 3 Pro |
| **Domain Model Extraction** (2608.12228) | LLaMA3.1-70B em 4× RTX 3090 |
| **XBridge** (2608.11676) — ponte latente entre LLMs | 7–8B; treina módulo de 264M — maior que o Bee inteiro |
| **EvoMem** (2608.10795) — memória evolutiva, +6,4% | Gemini 3 Flash / Qwen3-8B |
| **RSM** (2608.12311) — coordenação de 3 agentes comerciais | estudo de caso com Gemini 2.5 / Qwen Code; não há método reaproveitável |
| **LGPD/RAG** (2608.11454) | ⚠️ útil para **PassaPro/VirtualSector**, não para o Bee: RAG sobre LGPD com Llama 8B, faithfulness 0,96 |

---

## 4. O que a busca por "token reduction" diz

Doze trabalhos recentes, e **quase todos são visão ou áudio** — poda de tokens visuais
(94,4% removidos preservando 99%), KV-cache de áudio (20× de compressão), emoção facial (90%
suprimidos). **Nada aplicável a texto puro em modelo pequeno.**

O único de texto relevante já está acima (Policy-as-Logic, 10×). E há um dado de contexto
interessante: *Auditing Chinese Web-scale Corpora via Sampled BPE Token Statistics*
(2608.10678) faz auditoria de corpus por estatística de BPE amostrada, com **148× de speedup
e 35,8× menos memória** — a técnica poderia acelerar a auditoria do nosso corpus, hoje feita
por hash e contagem completa.

---

## 5. Conclusão prática

**Nada nesta leva muda o plano.** O que ela faz é confirmar, por evidência externa, três
coisas que já estávamos praticando:

1. **A confiabilidade mora fora do modelo.** Todo o campo convergiu para verificador externo
   + estado externo + roteador determinístico. É o que `tools_exec.py`, `ancoragem.py` e o
   `router.py` fazem.
2. **O teto do modelo pequeno é real e ninguém o contorna com harness.** Todos os métodos
   pressupõem ≥7B. Nosso `pass@16` de 72,9% não vai subir por engenharia de prompt.
3. **Medir no próprio holdout é obrigatório** — harness não transfere (Jaccard 0,12).

**Duas ações concretas que saem daqui:**

- **Curto prazo:** aplicar a divisão do Policy-as-Logic ao over-calling residual — o Bee
  extrai, a regra decide. Custo baixo, e ataca os 21,5% que sobraram.
- **Guardado:** inicialização por centroides, para o dia em que o vocabulário ganhar tokens de
  ferramenta; e o padrão B/P/E do EvoHarness-RL do lado do orquestrador, quando formos atacar
  multi-turno.
