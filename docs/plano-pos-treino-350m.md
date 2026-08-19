# Plano de pós-treino do Bee-350M

**Modelo alvo:** `BrCamp/bee-350m-pt-base` — 345,4M params, 32 camadas, d_model 960, 15q/5kv GQA, contexto 2048, vocab 32k próprio (0,218 tok/byte), 21,75B tokens de pré-treino, bpb 0,8207 no holdout PT.
**Hardware:** 1× RTX 5090 alugada (~US$ 1/h) + 1× RTX 5070 local (8 GB).
**Data:** 2026-08-19. **Base de evidência:** 8 lotes de estudo + 4 refutações adversariais.

---

## 1. O que a evidência sustenta e o que ela NÃO sustenta

### 1.1 Começando pelo que foi REFUTADO

**REFUTADO — "matemática" como capacidade nos pesos.** O grupo de controle é devastador e está na escala exata: SmolLM2-360M-Instruct, com **4 trilhões** de tokens de pré-treino incluindo FineMath e InfiMM-WebMath explicitamente (arXiv:2502.02737), entrega **8,1% em GSM8K**; Gemma-3-270M-it entrega **8,4%** (tabela do MobileLLM-R1). O Bee-350M tem 21,75B tokens — **0,54% disso** — e **zero fonte matemática** no corpus (`docs/corpus-v1-aprovado-2026-07-27.md`: fineweb-2-por 34% · PleIAs-PD 15% · Wikipedia-pt 10% · jurídico 5% · fineweb-edu-dedup 15% · cosmopedia-v2 10% · the-stack-smol-xl 10%). O mecanismo está medido: SFT **elicia** matemática que já está no pré-treino e **não a cria** (arXiv:2403.04706) — a mesma lei que o projeto mediu sozinho ("rejection sampling move o piso, não o teto"). E pode piorar: em Qwen2.5-0.5B o SFT derrubou GSM8K de **45,5% → 30,9%** (arXiv:2506.13404). O único número bom na escala (TinyGSM 350M, 65,9%) é um modelo **Phi** — a família com maior overfit medido no GSM1k, até **−13 pp** (arXiv:2405.00332) — fine-tunado em dado do GPT-3.5 semeado no **treino do GSM8K**, e o que ele faz é **emitir Python que o interpretador executa**, ou seja, uso de ferramenta.
→ **Consequência: "matemática" sai da lista de capacidades e volta como sub-caso do agêntico** (reconhecer problema aritmético e emitir chamada de calculadora/Python correta), que reaproveita o ativo mais forte do projeto.

**REFUTADO — CoT e test-time compute como impulsionadores gerais.** Fora de matemática/símbolo o ganho de CoT é ≈0: a meta-análise de 100+ papers (arXiv:2409.12183, ICLR 2025) mede +14,2% em raciocínio simbólico e +12,3% em matemática, e **95% do ganho no MMLU vem de questões com "=" na pergunta**. Seis das oito capacidades pedidas estão fora disso. CoT por prompting é medido **negativamente** na escala (LaMDA-422M e GPT-3-350M pioram, arXiv:2201.11903). Long CoT em 0,5B é **−8,5 pp em MATH e −5,8 pp em GSM8K** contra short CoT, com gap MAIOR em modelos base — e o Bee é base (arXiv:2502.12143). E o número que mata a metade "test-time compute": os famosos "0,5B supera GPT-4o" (arXiv:2502.06703) usam um PRM **Qwen2.5-Math-PRM-72B** como verificador — **144× a política**, inexistente em PT e fora do orçamento. Com verificador da própria escala o retorno é **+5,4 pp em 350M** ao custo de treinar e servir um segundo modelo de 345M (TinyGSM), e cresce com a escala (+13,3 pp em 1,3B) — 345M é o **pior ponto da curva** para comprar isso. Sem verificador, voto majoritário **reduz** a acurácia em 56,6%–65,7% dos problemas difíceis (arXiv:2608.11403).

**REFUTADO — um único modelo de 345M servindo as 8 capacidades sem interferência.** A medição direta está na escala exata (arXiv:2606.06920, SmolLM2-360M, exact-match zero-shot → full FT → LoRA → DoRA): OrcaMath **11,50 → 9,20 → 14,80 → 15,20**; GSM8K **4,20 → 3,80 → 6,50 → 7,10**; SVAMP **3,50 → 2,10 → 5,20 → 5,80**. Ou seja: escrever **UMA** capacidade nos parâmetros completos já deixa o modelo **abaixo do zero-shot na própria tarefa treinada**, enquanto o adapter entrega +1,7 a +3,3 pp. Os autores nomeiam um *stability cliff* em **300–500M** — o Bee está em cima dele. Soma-se o orçamento de conhecimento medido **dentro da faixa** (não extrapolado): ~2 bits/parâmetro → 345,4M × 2 = **86 MB para as 8 capacidades somadas**, e a constante cai para ~1 bit/param quando as exposições caem de ~1000 para ~100, que é o regime de um SFT de 7k exemplos (arXiv:2404.05405). E o mecanismo de retenção de tarefa rara (arXiv:2605.29548, OLMo 4M–4B): interferência de gradiente **aumenta** quando a capacidade diminui, e as fatias de baixa frequência morrem primeiro, em silêncio.
→ **Consequência: base congelada + adapters LoRA PARALELOS agrupados por afinidade. Nunca encadeados, nunca fundidos** (em treino sequencial as *intruder dimensions* acumulam e o LoRA passa a esquecer MAIS que o full FT — arXiv:2410.21228, RoBERTa-base 110M).

**INCONCLUSIVO — alinhamento por preferência rende mais que SFT+rejection sampling.** Não está refutado nem sustentado. O ponto mais próximo abaixo de 1B dá **+0,18 pp** (GPT-2 124M, SFT-only 89,87 → SFT→DPO 90,05, arXiv:2603.20100). Head-to-head, DPO iterativo **perde** para rejection sampling: 48,8 vs RAFT 52,3 vs RAFT++ 56,1 (arXiv:2504.11343). E a ablação do mesmo paper destrói o único mecanismo novo que o DPO traria: a vantagem do GRPO vem de **descartar prompts cujas amostras saíram todas erradas**, não dos gradientes negativos. Em OPT-350M a família funciona (ORPO vs SFT+DPO = 49,4%/50,5%, empate) — logo há sinal na escala, mas **ninguém mediu contra o baseline certo**.
→ **Consequência: vira gate barato (<US$ 15), com expectativa honesta de 0 a +3 pp e risco real de sinal negativo — não vira estágio planejado.**

### 1.2 O que a evidência SUSTENTA

| Achado | Escala medida | Número |
|---|---|---|
| Adapter LoRA > full FT em 300–500M | SmolLM2-360M | +1,7 a +3,3 pp; full FT **abaixo** do zero-shot |
| LoRA all-linear ≫ LoRA só-atenção | Llama-3.2-1B | atenção r=256 (0,25B) **perde** para MLP r=128 (0,24B) |
| LR de LoRA ≈ 10× o de full FT, quase independente do rank | Llama-3.2-1B / Qwen3-0.6B | varia <2× de r=4 a r=512 |
| Batch efetivo <32 (LoRA tolera batch grande pior, e rank maior não corrige) | Llama-3.2-1B | qualitativo, direção clara |
| Ponderação de loss no prompt (λ_prompt 0,1–0,5) | **Llama-3.2-1B** | **+14,81% relativo** em AlpacaCleaned; +6,55% médio |
| Otimização de mistura por perturbação | **Qwen2.5-0.5B** | loss por domínio a **0,66%** do grid exaustivo, 1/4 do custo |
| Superfiltering: modelo pequeno pontua dificuldade de dado | **GPT-2 124M** como filtro | ρ Spearman **0,846** contra LLaMA2-7B |
| Destilação cross-tokenizer (MultiLevelOT) | **OPT-350M** | QED 55,71→58,97; DIALOGSum 35,59→37,61 |
| Tool-calling em <2B se instala por SFT em dado verificado por EXECUÇÃO | 1,1B / 1,35B | 12,71%→80,06%; xLAM-1b-fc-r 78,94% BFCL |
| Dado de irrelevância + function masking contra over-call | 1,5B (Hammer) | 73,04% BFCL v2, acima de um 7B |
| RAG > fine-tuning para FATO | 7B (APOSTA na escala) | 0,875 vs 0,504 |
| Cobertura pass@k log-linear, inclinação mais íngreme nos menores | Pythia-160M | 0,27% → 57% (pass@1 → pass@10k) |
| Retry data (erro+correção) no mid-training | **GPT-2 124M do zero** | 78% → 94% |
| Erro de idioma do argumento é o modo de falha dominante em tool-calling não-inglês | 8B (APOSTA) | qualitativo, mas o pior caso descrito é exatamente o do Bee |

### 1.3 O achado de reconhecimento do repositório (feito agora, não estudado)

- `comeia/train/sft_qlora.py` e `comeia/train/dpo_qlora.py` ainda têm `--model` default **`Qwen/Qwen3.5-4B`** e carga em **4-bit NF4**. São herança do plano abandonado. Rodar qualquer um deles hoje baixa 8 GB e treina o modelo errado **sem dar erro nenhum** — família de bug já catalogada.
- `bee/sft.py` é o script certo: default `BrCamp/bee-150m-v3`, `--lr 6e-4`, `--epocas 2.0`, full FT com flag `--lora` opcional (r=16), e **já converte `messages` → `{prompt, completion}`**, o que faz o TRL mascarar o prompt sozinho. Isso significa que o projeto está hoje em **λ_prompt = 0** — o default nunca questionado que o arXiv:2507.07817 mede como subótimo.
- `comeia/data/processed/`: **zero arquivo de preferência**, confirmado. `sft_misto.jsonl` = **7.152** exemplos, `sft_reforcado_prop.jsonl` = 7.152, `sft_agentic.jsonl` = 1.495, `sft_agentic_reforco.jsonl` = 1.022, `sft_multiturno.jsonl` = 864, `sft_ptbr.jsonl` = 5.657, `sft_bncc.jsonl` = 1.676.
- `comeia/eval/benchmarks/` tem **6 arquivos, todos de múltipla escolha ou similaridade** (arc_pt, assin_entailment, assin_paraphrase, hellaswag_pt, truthfulqa_pt_mc2, xwinograd_pt). **Nenhum avaliador executável de instrução, código ou matemática existe.** Os avaliadores por execução que existem são `eval_agentic_exec.py`, `eval_coder.py`, `eval_extraction.py`, `eval_passk_curva.py`, `diag_overcall.py` — bons, mas cobrem 3 das 8 capacidades.
- O corpus tem **10% de the-stack-smol-xl ≈ 2,175B tokens de código**. Isso não é zero. O phi-1-small (350M, 45% HumanEval) usou ~7B tokens de código. O Bee tem **~31% disso** — logo "código" não é a mesma pergunta que "matemática" (onde o corpus tem literalmente 0%). ⚠️ Mas o mesmo doc registra que **o tokenizador foi treinado no corpus SEM código** — verificar se isso foi corrigido antes de prometer qualquer coisa de código.

---

## 2. Os estágios recomendados, em ordem

> **Premissa de custo que reorganiza tudo.** Um SFT completo neste modelo é barato demais para ser o gargalo: 7.152 exemplos × mediana ~450 tokens ≈ 3,2M tokens/época; 2 épocas = **6,4M tokens**. Com throughput escalado do pré-treino (62,9k tok/s medidos em 151M ÷ 2,29× params ≈ **~27k tok/s, A MEDIR**), um run é **~4 minutos de compute**. Com carga, avaliação e overhead: **~20 min de relógio, ~US$ 0,35**.
> **O dinheiro deste plano NÃO vai para GPU. Vai para DADO e para AVALIAÇÃO.** Qualquer proposta que trate um run de SFT como caro está repetindo o erro do §2d das lições (hipótese parada 7 dias por se *supor* cara; custou US$ 22).

---

### Estágio 0 — Instrumentação e baseline (US$ 0 de aluguel · ~0 GPU-h na 5090 · 4–6 dias de trabalho + 5070 local)

**O que faz.** Constrói o que falta para *medir*, e registra o número do modelo **antes** de qualquer treino. Esta é a lição do arXiv:2604.08880 (destilação de CoT **piorou** a matemática na maioria das configurações, e a literatura anterior não viu porque só comparava variantes entre si) somada à do `verifier.py` do próprio projeto.

Entregáveis:
1. **`comeia/eval/benchmarks/ifeval_pt.jsonl` + `eval_ifeval_pt.py`** — traduzir os 541 prompts do IFEval e reimplementar os ~25 verificadores determinísticos ("mais de 400 palavras", "cite X 3 vezes", "sem vírgulas", "responda em JSON"). Não existe em PT (M-IFEval só tem fr/ja/es). É o único jeito de medir "geração de conteúdo" **por execução** em vez de por juiz LLM.
2. **HumanEval-XL, split PT** (arXiv:2402.16694, 23 idiomas × 12 linguagens, média 8,33 casos de teste por item) — download grátis, plugar em `eval_coder.py`.
3. **Avaliador de resumo por execução** — auditoria de números/entidades inventados (regex + NER) + QA de span único respondível só a partir do resumo. Substitui ROUGE, que é similaridade e viola a regra do projeto.
4. **Baselines externos declarados**: `opus-mt-tc-big` 200M (BLEU 50,4 FLORES EN→PT) para tradução; BERTimbau-large 335M (ASSIN2-RTE 0,8913) para sentimento. Sem eles, "o Bee traduz razoavelmente" não é uma frase mensurável.
5. **Baseline do próprio Bee-350M base** nas 8 capacidades, incluindo **pass@256** num conjunto de ~200 problemas aritméticos de múltiplos passos em PT. Roda na 5070 local, US$ 0.

**Critério de sucesso (declarado ANTES):**
- Os **gabaritos de 100% dos avaliadores novos executam corretamente antes de qualquer modelo ser carregado**. Se um gabarito não passa, o defeito é do avaliador (lição já paga: 35 de 85 referências eram impossíveis por construção, e a taxa medida saiu 23,5% quando a real era 57,6%).
- O baseline das 8 capacidades está gravado em `docs/baseline-pre-postreino-350m.json`, com data e hash do checkpoint.
- **Gate de decisão sobre matemática:** se `pass@256` do base em aritmética de múltiplos passos for **< 3%**, matemática está formalmente encerrada como capacidade nos pesos e o orçamento é realocado. (Pela lei de arXiv:2403.04706, sem massa no pré-treino não há o que eliciar.)

---

### Estágio 1 — Reapontar o ferramental e censo de dados (US$ 0 · 1 dia)

**O que faz.**
- Reapontar `sft_qlora.py` e `dpo_qlora.py` para `BrCamp/bee-350m-pt-base`, **desligar o 4-bit** (base bf16 são 691 MB; QLoRA custa 20–30% de throughput para economizar 0,5 GB que não faz falta) e **abortar se o nome do modelo não contiver "bee"**.
- Rodar o **Bee-150M como filtro de IFD** (Superfiltering, arXiv:2402.00530, ρ=0,846 entre filtro de 124M e alvo de 7B) sobre os 7.152 exemplos do `sft_misto`. **Não para cortar** — com 7k não se corta nada — mas para localizar os exemplos com IFD ≈ 1 (dos quais o modelo não aprende nada) e mapear buracos de cobertura de dificuldade. Forward na 5070, minutos.
- **Censo de mistura por TOKEN, não por exemplo.** Exemplos agênticos são muito mais longos que exemplos de sentimento; a fração efetiva de treino de cada capacidade é a de tokens. Este é o mesmo modo de falha do §2b (dado sumindo em silêncio) pelo outro lado.

**Critério de sucesso:** tabela `capacidade → nº de exemplos → nº de tokens → % dos tokens de treino` publicada, e `--dry-run` de 3 passos passando em todos os scripts reapontados.

---

### Estágio 2 — Gate de arquitetura + hiperparâmetros, em grid conjunto (US$ 5–8 · ~5–8 GPU-h)

Este é **o estágio que decide o formato de tudo que vem depois** e é o de maior razão informação/dólar do plano.

**O que faz.** Um único grid, mesmo dado (`sft_misto.jsonl`, 7.152), mesmas 2 épocas, avaliando **as 8 capacidades em TODOS os braços** (medir os dois lados — lição do `verifier.py`, cujo ganho aparente era saldo −4):

**Eixo A — arquitetura (3 braços):**
- (a) 1 adapter LoRA multi-task sobre a mistura completa
- (b) 3 adapters por afinidade: **TEXTO** (conteúdo, resumo, tradução, sentimento, atendimento) · **FERRAMENTA** (agêntico + saída estruturada) · **SIMBÓLICO** (código + aritmética-por-ferramenta)
- (c) full FT conjunto — **controle negativo**, esperado abaixo do próprio base em pelo menos uma capacidade

**Eixo B — LR, 3 pontos por braço, cada um no ótimo próprio** (não 6 — a curva em U já foi feita em 151M; aqui é confirmação de deslocamento): adapter em **{3e-3, 6e-3, 1,2e-2}** (regra dos 10× sobre o 6e-4 medido) e full FT em **{3e-4, 6e-4, 1,2e-3}**. Rodar cada braço no LR **dele** é o que dissolve o confundimento apontado no lote PEFT: parte dos −5,9 pp medidos em 151M pode ter sido artefato de LR mal transferido, e isso precisa ser separado antes de virar teoria.

**Eixo C — λ_prompt, 2 pontos {0; 0,25}** no braço vencedor de A×B. Hoje o projeto está cravado em 0 porque `bee/sft.py` converte para `{prompt, completion}`; varrer exige um collator com peso por segmento (~30 linhas).

**Config fixa (não varrer, já está medido em outra escala):** `target_modules="all-linear"` (atenção-only com r=256 perde para MLP-only com r=128 e mesmo nº de params), **r=32** (= 17,4M params = **5,0% da base**; r=256 seriam 139M = **40,2% da base** — deixaria de ser adapter), **batch efetivo <32**.

**Custo:** ~11 runs × ~20 min = ~4 h de treino + ~3 h de avaliação ≈ **US$ 7**.

**Critérios de sucesso (declarados ANTES):**
- **Adotar (b) sobre (a)** só se a partição por afinidade ganhar por **≥5 pp de folga ABSOLUTA** em pelo menos duas capacidades sem perder ≥2 pp em nenhuma. Folga absoluta, nunca multiplicativa (§2c das lições: `pass@k > pass@1 × 1,5` imprimiu "não há cauda útil" para 52,3% → 72,9%).
- **Se (a) empatar com (b) dentro de 2 pp em todas as 8, a simplicidade ganha** e o plano passa a 1 adapter — a refutação vira "sustentada para este projeto".
- **Se (c) full FT ficar abaixo do modelo base em qualquer capacidade**, o *stability cliff* de 300–500M está confirmado em casa e full FT fica banido do resto do plano.
- **Se λ_prompt=0,25 render <2 pp**, mantém 0 e o assunto encerra.

---

### Estágio 3 — Dado: expansão dirigida (US$ 0–5 de GPU · 2–3 semanas de relógio)

**O que faz.** Três medições independentes dizem que **7.152 exemplos para 8 capacidades está subdimensionado em cerca de uma ordem de grandeza** nas capacidades especializadas: (i) OpenThoughts (arXiv:2506.04178, >1.000 ablações) mede que 1.000 exemplos curados dão ganho apenas **marginal** contra 58K — a tese do LIMA não se sustentou; (ii) arXiv:2310.05492 mede que **só** a habilidade "geral" satura em ~1k, enquanto matemática e código sobem **monotonicamente sem platô**; (iii) TinyAgent precisou de **38.000 exemplos para UMA capacidade agêntica em domínio fechado, num modelo de 1,1B**. O Bee tem **1.495** exemplos agênticos.

Isso levanta uma hipótese testável e desconfortável: **"2 épocas é o ponto, na 3ª vira decoreba" pode ser sintoma do dataset, não lei do treino.** Com 7k exemplos, a 3ª passada é literalmente a terceira vez que o modelo vê cada item.

Ações:
1. **Baixar `Polygl0t/gigaverbo-v2-sft`** — Apache-2.0, 4,1M exemplos, ~2,1B tokens em PT, 4,4 GB, com configs que mapeiam **uma a uma** nas capacidades: summarization 128,7K · translation 45,2K · code 80,8K · math 220K · math_cot 63,4K · rewriting 29,1K · structured 163,5K · function_call 45,9K. **Custo US$ 0.**
2. **Passar tudo pelo `04_decontaminate.py`** contra os holdouts do Bee **antes** de treinar. Não negociável.
3. **Expandir o agêntico** via `07b_expand_agentic.py` + `15_rejection_sampling.py`, alvo **1.495 → ~10.000** trajetórias verificadas por execução. Professor via build.nvidia.com (inferência gratuita, ToS permite destilar).
4. **Adicionar ~7.500 exemplos de IRRELEVÂNCIA + function masking** (receita Hammer, arXiv:2410.04587): casos em que **nenhuma ferramenta serve**. Foi isso que levou um 1,5B a 73,04% no BFCL v2, acima de um 7B, e ataca diretamente o over-call que o projeto já mediu (saldo −4 do `verifier.py`) sem matar chamada boa.
5. **Teste da hipótese das 2 épocas:** triplicar o dado de **uma só** capacidade (código, que tem escala monotônica medida), manter 2 épocas, e ver se o ponto de virada da 3ª época se desloca.

**Critério de sucesso:**
- Dataset agêntico ≥ 8.000 trajetórias com rótulo de execução, **e a auditoria de truncamento passando** (`len(trainer.train_dataset)` == nº carregado, aborta se perder >1% — §2b, o erro que descartou 150/150 exemplos em silêncio).
- Se triplicar o código **não** deslocar o ponto de virada da 3ª época, "2 épocas" é lei e fica registrado. Se deslocar, o teto medido era do dataset — e a geração de dado vira o gargalo do projeto, não o ajuste fino.

---

### Estágio 4 — Otimização da mistura (US$ 15–20 · ~15 GPU-h)

**O que faz.** Rodar a otimização de mistura por perturbação por domínio (arXiv:2508.11953) — **o único método deste plano com evidência abaixo de 1B** (Qwen2.5-0.5B) — antes de fixar qualquer proporção entre as capacidades. ~5 mini-runs de ~660k tokens por domínio.

Motivo para não herdar proporções do Tulu3 ou do SmolTalk: o paper mede que **a mistura ótima depende do orçamento de dado**, e o do Bee é ~100× menor. O número que ilustra: no Tulu3 a otimização derrubou Math de **57,77% → 12,81%** e subiu Precise-IF de **2,05% → 15,63%**.

**Critério de sucesso:** loss de validação por domínio dentro de **2%** do melhor grid manual testado, e a mistura resultante publicada com justificativa por domínio. Se a mistura otimizada empatar com a herdada dentro de 1%, registrar e seguir com a herdada.

---

### Estágio 5 — Agêntico: colher os 27,7 pp já mapeados (US$ 0–3 · ~2 GPU-h)

Este é o ativo mais forte do projeto (57,6% de execução real, **pass@16 = 85,3%**) e o estágio com melhor razão retorno/custo depois do Estágio 0.

**5a — Filtro "all-wrong" no rejection sampling (US$ 0).** A ablação do arXiv:2504.11343 isola que a vantagem inteira do GRPO sobre o RAFT vem de **descartar prompts cujas amostras saíram todas erradas** — não da normalização de recompensa, não dos gradientes negativos. Portar esse filtro para `15_rejection_sampling.py` roda sem GPU e sem RL nenhum.

**5b — Laço executar-verificar-retentar em runtime (US$ 0).** Modelo pequeno não se autocorrige, mas o executor determinístico **é** o verificador forte. k=2–4 colhe a parte sintática da folga sem treinar nada. Custo é latência.

**5c — Segmentar a métrica por IDIOMA DO ARGUMENTO (US$ 0).** O modo de falha dominante em tool-calling não-inglês não é de compreensão: o modelo escolhe a ferramenta certa e **escreve o valor do parâmetro no idioma do usuário**, violando a convenção de execução (arXiv:2601.05366). Um modelo 100% PT chamando APIs com chaves/enums em inglês é o pior caso descrito no paper. Invisível em avaliação por similaridade, **visível** na avaliação por execução que já existe — basta segmentar `eval_agentic_exec.py`.

**Critério de sucesso:** 57,6% → **≥65%** de execução real (folga absoluta ≥7 pp) **sem** que pass@16 caia mais de 2 pp. Se pass@16 cair, está se queimando diversidade em vez de aprender — abortar.

---

### Estágio 6 — GATE de preferência (US$ 12–15 · ~10 GPU-h) — gate, não estágio

**O que faz.** Quatro braços, mesmo dado, mesmo avaliador. **O controle é `SFT + rejection sampling`, NÃO `SFT puro`** — comparar contra SFT puro reproduziria o 82,7% do ORPO e concluiria "funciona", medindo o baseline errado.
(a) SFT+RS = controle · (b) +DPO · (c) +IPO (`loss_type='ipo'` — preferência vinda de verificador é **determinística**, o regime exato em que o DPO degenera independentemente do beta, arXiv:2310.12036) · (d) +KTO (come rótulo binário desbalanceado sem emparelhar).

Os pares saem **de graça** do `15_rejection_sampling.py`: mesmo prompt, uma trajetória que executou (chosen) e uma que falhou (rejected), rotuladas deterministicamente pelo executor. Meta ~8k pares (o piso de fracasso medido é 97–325 pares em escala GPT-2; o teto útil é 5k–10k curados). **LR de DPO = 1e-6 a 5e-6, NUNCA o 6e-4 do SFT** — SmolLM2 usa 1e-6 com beta 0,5 inclusive em 135M/360M.

**Critério de sucesso (declarado ANTES):** adotar apenas com **≥5 pp de folga absoluta** no avaliador por execução **e sem perda ≥2 pp em bpb PT, extração ou coder**. Expectativa honesta: **0 a +3 pp, com probabilidade real de sinal negativo**. Se render menos de 5 pp, o resultado é "não adotar" — **não** "repetir com outro beta".

**Guarda obrigatória:** pares vindos de verificador têm **distância de edição mínima** (mesma trajetória, um argumento trocado), que é o gatilho exato do *likelihood displacement* (arXiv:2402.13228; confirmado até OLMo-1B em arXiv:2410.08847): a margem chosen−rejected sobe bonito no log **enquanto as duas log-probs caem**, e a massa migra para respostas de sentido oposto — sem erro nenhum. **Logar `log πθ(y_w)` ABSOLUTO a cada N passos e abortar se cair abaixo do valor no passo 0.**

---

### Estágio 7 — GRPO agêntico com adapter, single-turn (US$ 5–15 · ~5–15 GPU-h) — condicional

**Só rodar se o Estágio 5 render e o Estágio 6 não.**

RLVR é mecanicamente aplicável: o critério publicado não é contagem de parâmetros, é **baseline supervisionada com perplexidade < 20 + recompensa discriminativa** (arXiv:2607.25091, medido até Pythia-70M, onde RL deu ganho nulo/negativo). Conta do Bee: bpb 0,8207 ÷ 0,218 tok/byte = 3,765 bits/token → **ppl ≈ 13,6**. Passa com folga. E a objeção padrão ("recompensa esparsa abaixo de 1B") **não se aplica aqui**: pass@16 de 85,3% é sinal denso.

Config: **GRPO + LoRA r=32**, recompensa = **execução** (o avaliador agêntico é a função de recompensa, já existe), alvo = validade de formato de tool call + taxa de execução, **não matemática**. Referências de custo: Qwen2.5-0.5B GRPO em GSM8K em 45 min numa A10; Qwen3-0.6B com teste unitário como recompensa numa **RTX 3090 sozinha**; Tina fez RL em 1,5B por **US$ 8**. LoRA-RL bateu RL de parâmetro completo em 1,5B: **48,16% vs 44,86%, a US$ 9 contra ~US$ 2.300 estimados** (arXiv:2504.15777).

**Avaliar checkpoints entre 19% e 57% da época** — o melhor aparece cedo e piora depois (Tina).

**Critério de sucesso:** pass@1 sobe **≥5 pp** **e** pass@16 **não cai**. Se pass@16 cair, o RL está reorganizando amostragem dentro do suporte da base (arXiv:2504.13837) e não comprando nada novo — parar.

**NÃO usar GRPO puro para multi-turno:** em 1,5B, DAPO (36,9%) e ARPO (37,5%) batem GRPO puro (30,1%); a vantagem some em 7B. E multi-turno agêntico praticamente não existe nesta escala: Qwen3-0.6B faz **1,38%**, xLAM-2-1b 8,38%, Qwen3-1.7B 16,88%, e só em 3B sobe para 55,62% — confirmação externa dos −5,9 pp medidos em casa.

---

### Estágio 8 — Mid-training de código (US$ 40–60 · ~50 GPU-h) — só com decisão explícita

**O que faz.** Código e matemática se instalam no **pré-treino**, não no SFT: phi-1-small (350M, **45% HumanEval**) veio de ~7B tokens de código; TinyGSM veio de 1,8B tokens só de problemas. **Nem adapter nem SFT compram isso depois.** O Bee já tem ~2,175B tokens de código (31% do orçamento do phi-1) — logo o degrau é menor do que parece, mas é mid-training, não fine-tuning.

Adicionar 5–7B tokens de código curado + exercícios sintéticos + **retry data** (erro + token de volta + correção dentro da própria cadeia curta — 78% → 94% em GPT-2 124M do zero, arXiv:2408.16293, é a forma de "pensar mais" que cabe em 2048).

**Critério de sucesso, com limiar de ABORTO decidido antes:** HumanEval-XL-PT sobe **≥10 pp** **E** bpb no holdout PT piora **≤0,010**. Se bpb estourar o limiar, **abortar o run** — em 345M a capacidade é disputada e isso vai custar português.

**Pré-condição:** verificar se o tokenizador foi retreinado com o corpus **com** código. O `docs/corpus-v1-aprovado-2026-07-27.md` registra que o tokenizador original foi treinado no corpus **sem** código. Se não foi corrigido, este estágio está comprometido antes de começar.

---

## 3. O que NÃO fazer, e por quê

| Não fazer | Número que sustenta a recusa |
|---|---|
| **Full fine-tune conjunto das 8 capacidades** | SmolLM2-360M: full FT deixa o modelo **abaixo do zero-shot** na tarefa treinada (OrcaMath 11,50→9,20; SVAMP 3,50→2,10). Qwen2.5-0.5B/SVAMP: 2,33 → **0,00**, colapso total (arXiv:2606.06920) |
| **Fundir ou encadear adapters** | Em fine-tuning sequencial de 6 tarefas em RoBERTa-base 110M, *intruder dimensions* acumulam e o LoRA passa a esquecer **mais** que o full FT (arXiv:2410.21228) |
| **Herdar `rank 256` da literatura** | r=256 all-linear no Bee-350M = **139,0M params = 40,2% da base**. Em Llama-3.1-8B a mesma config é ~3%. Foi assim que a recomendação foi calibrada. Equivalente a 3% em 345M é r≈19 |
| **QLoRA / 4-bit** | Base bf16 = 691 MB → NF4 ≈ 194 MB. Economia de 0,5 GB por 20–30% de throughput. O vilão real na 5070 é o tensor de logits: 2048 × 32.000 × bf16 = **131 MB/sequência** |
| **Perseguir matemática em formato livre** | SmolLM2-360M (4T tokens **com** FineMath): **8,1% GSM8K**. Tucano-630m (nativo PT, 200B tokens): ENEM **19,17%**, OAB **25,28%** — no acaso |
| **Destilar long CoT de professor grande** | Qwen2.5-0.5B: long CoT 23,0% vs short CoT 31,5% em MATH (**−8,5 pp**); GSM8K 39,5% vs 45,3% (**−5,8 pp**). E destilação de conhecimento degradou **todos** os benchmarks: OlympiadBench 6,2%→3,7%, GSM8K 45,5%→42,3% |
| **CoT em classificação/sentimento** | Tucano-630m ASSIN2-STS Pearson **1,99** contra 0,8531 do BERTimbau-335M. Usar **decodificação restrita aos rótulos** — o oposto de CoT |
| **Treinar um verificador/PRM de 345M** | Retorno na escala: **+5,4 pp em 350M** (TinyGSM verify48@1), contra +13,3 pp em 1,3B. Custo: um segundo modelo de 345M treinado e servido. 345M é o pior ponto da curva |
| **Voto majoritário / self-consistency sem verificador** | Reduz a acurácia por problema em **56,6%** (Qwen2.5-7B) e **65,7%** (Llama-3-8B) no GPQA Diamond; nenhum gate sem verificador move mais que 0,002 em N=64 |
| **Budget forcing (s1)** | Sem evidência publicada abaixo de **32B**, e não cabe em 2048 |
| **ORPO** | Em OPT-350M — a escala **exata** — ORPO empata com SFT+DPO (**49,4%** HH-RLHF, **50,5%** UltraFeedback). A vantagem de 70,9% só aparece em 1,3B. Adotá-lo custa revarrer LR e λ do zero para chegar no mesmo lugar |
| **SimPO / CPO** | Zero evidência abaixo de 7B. O argumento de venda do SimPO (dispensar o modelo de referência) vale **0,7 GB numa placa de 32 GB**, e já é resolvido de graça por `precompute_ref_log_probs=True` |
| **Multi-Token Prediction** | 0,3B: MBPP **1,0 (MTP) vs 1,8 (baseline)**; 0,6B: **3,0 vs 4,7**. O sinal só inverte entre 1,3B e 3B — está **invertido** na faixa do Bee |
| **Quantizar abaixo de 8 bits** | Qwen2.5-0.5B cai de **21,31% → 12,77%** de 8 para 4 bits (−40% relativo). E 345M em bf16 são 0,7 GB: não há problema a resolver |
| **Code-actions (Python no lugar de JSON)** | As gerações mais fracas ficaram **19,7 a 26,9 pp ABAIXO** do JSON. Direção do gradiente prevê colapso em 345M |
| **Formatos "econômicos" (TOON/TRON)** | Mistral-24B: JSON 88,8% → TOON **52,7%** (−36,1 pp), TRON 82,9% (−5,9 pp) |
| **Packing de sequências** | O ganho **cresce** com o modelo: +1,02 em 8B, +4,42 em 70B. Recomendação literal dos autores para modelo e dataset pequenos: **use padding** (arXiv:2410.08081). Se empacotar mesmo assim, máscara intra-documento é obrigatória — token separador **não** resolve (medido em 110M–340M) |
| **Currículo por ordenação global fácil→difícil** | GPT-2 124M — **menor que o Bee**: metade dos passos até a acurácia alvo, e **~30% MENOS acurácia final** |
| **Fine-tuning para injetar base de conhecimento (atendimento)** | RAG 0,875 vs fine-tuning 0,504 em conhecimento novo; e RAG sozinho **> RAG+FT** (arXiv:2312.05934, APOSTA — medido em 7B) |
| **Trocar o objetivo de SFT (−p, −p^10)** | Só ganham em modelos **fortes**; no regime fraco a NLL padrão domina (arXiv:2510.00526) |
| **DoRA agora** | +3,7% em LLaMA-7B, mas **zero evidência citável <1B**, +20% de tempo de treino. Testar antes de fixar rank/LR/all-linear dá resultado inatribuível — exatamente o erro do §2d |
| **Multi-LoRA com roteamento aprendido (Arrow/MoLE)** | Literatura ≥1B, e resolve um problema — roteamento — que o roteador determinístico da COMEIA já resolve |
| **Rodar `sft_qlora.py` / `dpo_qlora.py` como estão** | Default `Qwen/Qwen3.5-4B`. Baixa 8 GB e treina o modelo errado **sem erro nenhum** |

---

## 4. As capacidades pedidas

| Capacidade | Viável em 345M? | Método | Como medir |
|---|---|---|---|
| **Geração de conteúdo / seguir instrução** | **SIM, com teto modesto.** Referência na escala: SmolLM2-360M-Instruct = **41,0** de IFEval; Qwen2.5-0.5B-Instruct = 31,6 | Adapter **TEXTO**, LoRA r=32 all-linear, LR ~6e-3, 2 épocas, mistura otimizada por perturbação | **IFEval-PT** (541 prompts, ~25 verificadores determinísticos) — a construir no Estágio 0. Nunca juiz LLM como veredito |
| **Resumo / síntese** | **SIM.** PTT5-summ de 0,2B já é útil em PT; mT5 em XL-Sum faz R1 37,60 / RL 29,88 | Adapter **TEXTO**. GigaVerbo-v2 config `summarization` (128,7K) + RecognaSumm | **Por execução**: taxa de números/entidades inventados (regex+NER) + QA de span único respondível só a partir do resumo. ROUGE só como métrica secundária |
| **Tradução** | **PARCIAL — vai ficar ABAIXO do estado da arte de 200M.** `opus-mt-tc-big` enc-dec de 200M faz **BLEU 50,4** em FLORES EN→PT. Um decoder generalista de 345M não bate isso | Adapter **TEXTO**. GigaVerbo-v2 config `translation` (45,2K) | BLEU + chrF em FLORES-200 pt↔en, **com o opus-mt declarado como baseline explícito**. Se perder, dizer que perdeu |
| **Análise de sentimento** | **SIM mas provavelmente ABAIXO de um encoder.** BERTimbau-large 335M faz ASSIN2-RTE **0,8913**; Tucano-630m em formato livre faz **0,5779** | Adapter **TEXTO** + **decodificação RESTRITA aos rótulos**. Sem CoT | F1-macro em B2W-Reviews01 e TweetSentBR, **comparando contra BERTimbau-base fine-tunado**. Reportar taxa de saídas fora do vocabulário de rótulos |
| **Programação / código** | **PARCIAL, e é o único caso em que mid-training pode valer.** O corpus tem **~2,175B tokens de código** (31% do orçamento do phi-1-small, que fez **45% HumanEval** em 350M). Não é zero, mas SFT sozinho não instala o que falta | Adapter **SIMBÓLICO** para formato; **Estágio 8 (mid-training)** para capacidade. GigaVerbo-v2 config `code` (80,8K). ⚠️ Verificar antes se o tokenizador foi retreinado com código | **HumanEval-XL split PT** — execução real de casos de teste, pass@k. `eval_coder.py` já existe |
| **Atendimento automatizado** | **SIM**, com a divisão certa: **peso carrega comportamento, contexto carrega fato** | Adapter **TEXTO** para tom, escalonamento e quando chamar ferramenta; **RAG externo** para preço/política/status. ⚠️ Restrição dura: janela de 2048 — o contexto recuperado compete com o esquema das ferramentas. Chunk pequeno, retriever de recall alto | Taxa de resolução por execução em cenários fechados + taxa de alucinação factual contra a base de conhecimento (não contra o gabarito textual) |
| **Matemática** | **NÃO como capacidade nos pesos.** Corpus com **0% de fonte matemática**; SmolLM2-360M com 4T tokens **incluindo** FineMath faz 8,1% GSM8K; SFT pode **piorar** (45,5%→30,9% em 0,5B) | **REDEFINIR**: reconhecer problema aritmético e emitir **chamada de calculadora/Python correta**, que o interpretador executa. É a capacidade agêntica, não matemática — e é exatamente o que o TinyGSM 350M faz | **GSM-PT a construir** (não existe: MGSM não tem português) **+ holdout novo estilo GSM1k gerado DEPOIS do treino**. Métrica: correção da chamada de ferramenta e do resultado executado, não da prosa. Gate de entrada: `pass@256` do base ≥3% |
| **Função agêntica (uso de ferramentas)** | **SIM — é o ativo mais forte do projeto.** 57,6% de execução real medida, **pass@16 = 85,3%**. Provavelmente o melhor número publicado nesta faixa de tamanho (os 78–85% de xLAM/TinyAgent são AST/schema matching, métrica mais permissiva) | Adapter **FERRAMENTA**. Catálogo **fechado** de 16–30 ferramentas + retriever de ferramentas (foi o que levou 1,1B a bater GPT-4-turbo). +7.500 exemplos de irrelevância. **JSON**, não code-actions. Functional tokens são triviais aqui (tokenizador próprio) se o catálogo congelar | `eval_agentic_exec.py` (execução real, mundo **aberto** por hash) + `eval_passk_curva.py` + `diag_overcall.py`. **Segmentar por idioma do argumento** |

**Multi-turno agêntico: NÃO nesta escala.** Qwen3-0.6B faz **1,38%**, xLAM-2-1b 8,38%, Qwen3-1.7B 16,88%; o salto só acontece entre 1B e 3B (55,62% em xLAM-2-3b). Confirmação externa dos −5,9 pp medidos em casa.

---

## 5. Riscos e armadilhas de instrumentação

O projeto tem **sete casos catalogados** da mesma família: dado ou sinal some, nada reclama, a loss cai bonito. Este plano introduz superfície nova para pelo menos cinco deles. As guardas abaixo são **obrigatórias e dentro do fluxo** — a lição §5 diz que a guarda da §1 foi escrita, commitada e **nunca chamada**.

**G1 — Mascaramento da loss (herdeira do deslocamento de rótulos).** `bee/sft.py` já converte `messages` → `{prompt, completion}`. Ao introduzir λ_prompt no Estágio 2 esse mascaramento passa a ser **configurável**, e um bug ali não dá erro. Guarda: para um batch real, calcular a loss manualmente sobre a máscara esperada e abortar se divergir >0,01. **Com dado de treino REAL** — com tokens aleatórios a diferença some e a guarda não dispara.

**G2 — Truncamento silencioso no SFT.** Comparar `len(trainer.train_dataset)` com o nº de exemplos carregados e **abortar** se a perda passar de 1%. `max_seq_len` default = 2048 (o `seq_len` do pré-treino). Este é o erro que descartou **150/150** exemplos agênticos, detectado só pela contagem de passos (447 previstos, 354 executados = 79,2%; agêntico era 20,9% — bateu na casa decimal).

**G3 — Adapter registrado como não-treinável.** LoRA marcado silenciosamente como não-treinável em PEFT/TRL produz delta **exatamente zero** e o treino roda inteiro sem erro (arXiv:2607.25091, medido em Pythia-70M / SmolLM2-135M). Guarda: comparar `||θ_treinável||` antes e depois do passo 1 e **abortar se idêntica**. Este plano é inteiramente baseado em adapters — a guarda é crítica, não opcional.

**G4 — Avaliador de mundo fechado.** Executar **todos os gabaritos de todos os avaliadores ANTES de carregar qualquer modelo**. Vale em dobro para os avaliadores novos (IFEval-PT tem ~25 verificadores escritos à mão). Se a referência não roda, o defeito é do avaliador. Mundo simulado **aberto** por hash da entrada normalizada, nunca lista branca. Custo já pago: 35 de 85 referências impossíveis, 23,5% medido contra 57,6% real.

**G5 — Critério de veredito multiplicativo.** Todo gate deste plano usa **folga ABSOLUTA (≥5 pp)** + fração do espaço restante capturada. Nunca `pass@k > pass@1 × 1,5`, que já imprimiu "não há cauda útil" para 52,3% → 72,9%.

**G6 — Comparação entre schedules/regimes diferentes.** Nenhum braço deste plano compara marcos intermediários. Todo run bifurcado passa `--lr` **explícito** e bifurca do **checkpoint completo** (estado do otimizador + posição no dado), nunca de snapshot de pesos.

**G7 — Likelihood displacement no DPO (novo, Estágio 6).** Logar `log πθ(y_w)` **absoluto** a cada N passos e **abortar se cair abaixo do valor no passo 0**. Gatilho: distância de edição mínima entre chosen e rejected, que é a assinatura exata de pares vindos de verificador por execução.

**G8 — Modelo errado (novo, achado no repositório).** `sft_qlora.py` e `dpo_qlora.py` apontam para `Qwen/Qwen3.5-4B`. Guarda: **abortar se o nome do modelo não contiver "bee"**. Sem isso, um run acidental baixa 8 GB e treina o modelo errado durante horas sem uma linha de erro.

**G9 — Mistura efetiva por token, não por exemplo (novo).** Reportar `capacidade → % dos TOKENS de treino`. Exemplos agênticos são muito mais longos; uma capacidade pode ser 20,9% dos exemplos e 45% dos tokens, ou o inverso. É a família "dado some em silêncio" pelo lado da proporção.

**G10 — Baseline pré-pós-treino gravado (novo).** Registrar o número das 8 capacidades **antes** de gastar a primeira GPU-hora. Sem isso é impossível detectar o caso medido em arXiv:2604.08880 (destilação de CoT **piorou** o aluno na maioria das configurações, invisível porque só se comparava variantes entre si). E medir os **DOIS lados** de todo gate — bpb PT + extração + coder, não só o alvo (lição do `verifier.py`: ganho aparente com saldo real de −4).

**G11 — Contaminação temporal (novo).** Qualquer número de matemática ou código produzido por destilação de professor é indistinguível de contaminação sem holdout **gerado depois do treino** (GSM1k: até −13 pp, com Phi entre as famílias mais afetadas; r²=0,32 entre a probabilidade de o modelo **gerar** um exemplo do benchmark e o tamanho do gap).

**G12 — Decodificação em classificação (novo).** Em sentimento e rotulagem, restringir a decodificação aos rótulos e **reportar a taxa de saídas fora do vocabulário de rótulos**. Se essa taxa for >0 e a métrica não a penalizar, a métrica está errada — foi assim que um Pearson de 1,99 apareceu no Tucano-630m.

**G13 — Throughput.** Só confiar a partir do passo ≥20, com **três leituras consecutivas coincidentes**. As estimativas de custo deste documento assumem ~27k tok/s por escalonamento dos 62,9k medidos em 151M — **isso é uma estimativa, não uma medição**, e o Estágio 1 deve substituí-la por número medido antes de qualquer compromisso maior.

---

## 6. Orçamento total e ordem de execução

### Ordem por razão custo/benefício

| # | Estágio | US$ | GPU-h (5090) | Relógio | Por que nesta posição |
|---|---|---:|---:|---|---|
| 1 | **E0 — Instrumentação + baseline** | **0** | 0 (roda na 5070) | 4–6 dias | Sem avaliador por execução, todos os estágios seguintes produzem números não-interpretáveis. Também contém o gate de US$ 0 que decide o destino de "matemática" |
| 2 | **E1 — Reapontar ferramental + censo IFD** | **0** | 0 | 1 dia | Elimina o risco de treinar o modelo errado e mapeia buracos de dificuldade antes de gerar dado |
| 3 | **E5a/b/c — Agêntico sem treino** | **0** | 0 | 2 dias | Filtro all-wrong + retry loop + métrica por idioma. Colhe parte dos 27,7 pp de folga com zero GPU |
| 4 | **E2 — Gate de arquitetura + LR + λ_prompt** | **7** | 5–8 | 2 dias | Decide o formato de todos os estágios seguintes. 11 runs de ~20 min cada |
| 5 | **E3 — Expansão dirigida de dado** | **0–5** | 0–3 | 2–3 semanas | É o gargalo real do projeto (7.152 exemplos para 8 capacidades). GigaVerbo-v2 é grátis; professor é grátis; o custo é relógio |
| 6 | **E4 — Otimização de mistura** | **15–20** | 15 | 2 dias | Único método do plano com evidência abaixo de 1B. Só faz sentido depois que o dado existe |
| 7 | **E6 — GATE de preferência (DPO/IPO/KTO)** | **12–15** | 10 | 3 dias | Expectativa 0 a +3 pp. É gate, não estágio: barato demais para não medir, fraco demais para se planejar em cima |
| 8 | **E7 — GRPO agêntico com adapter** | **5–15** | 5–15 | 3 dias | Condicional. Só se E5 render e E6 não |
| 9 | **E8 — Mid-training de código** | **40–60** | ~50 | 3–4 dias | Único caminho para código de verdade, e o único item que custa dinheiro sério. Só com decisão explícita e limiar de bpb declarado antes |
| — | **Folga para reexecuções e gates falhos** | **20** | — | — | Histórico do projeto: gates falham por instrumentação, não por hipótese |

### Totais

- **Caminho mínimo (E0 → E4, sem código, sem RL):** **US$ 22–32** · ~20–26 GPU-h · ~4–5 semanas de relógio.
- **Caminho completo com gates (E0 → E7):** **US$ 39–62** · ~30–41 GPU-h · ~6 semanas.
- **Caminho completo + mid-training de código (E0 → E8):** **US$ 79–122** · ~80–91 GPU-h · ~7 semanas.
- **Com folga de reexecução:** **US$ 100–142**.

Está dentro da faixa de "dezenas a poucas centenas de dólares". **A restrição real deste plano não é dinheiro — é relógio de geração de dado e dias de trabalho construindo avaliadores.**

### As três frases para levar

1. **O run de SFT custa US$ 0,35; o avaliador custa uma semana.** Toda a política de gates deste plano decorre disso: se um gate custa menos que a reunião para discutir se vale a pena, roda o gate. A hipótese do decaimento de LR ficou 7 dias parada por se **supor** cara e custou US$ 22 — não repetir.
2. **Três das quatro afirmações mais atraentes do estudo foram refutadas na escala exata** (matemática nos pesos, CoT/test-time compute como impulsionador geral, modelo único para 8 capacidades), e a quarta ficou inconclusiva. O maior valor deste plano é o que ele **não gasta**.
3. **O ativo do projeto é o agêntico medido por execução (57,6% real, pass@16 85,3%), não a matemática.** Redefinir "matemática" como "emitir chamada de calculadora correta" transforma o item impossível da lista no item que reaproveita o ativo mais forte — e passa a ser medível pelo avaliador que já existe.