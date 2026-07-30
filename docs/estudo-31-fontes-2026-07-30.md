# Estudo — 31 fontes (arXiv / AWS / GitHub) · multiagente · 2026-07-30

> Lido enquanto o Bee-150M rodava o pré-treino. Feito com **workflow de 12 agentes** (11 leitores em
> paralelo, cada um com 2-3 fontes via WebFetch, + 1 síntese-chefe). Foco obsessivo em **otimizar TUDO
> no Bee** — pré-treino, tokenizador, SFT, COMEIA, RAG dos SaaS, quantização/serving, avaliação,
> escada 350M→1B. Formato de sempre: o que a fonte diz → **o que muda no Bee**. Fonte que não muda
> nada eu digo que não muda.

## 1. Leitura de conjunto (retrato honesto)

**Acesso:** ~31 fontes lidas de fato, **0 falhas duras**. Único percalço: o paper de RAG em saúde
mental (arXiv 2607.24817) veio binário na rota `/pdf/` — acessado via `/abs/`, mas com **números
omitidos** (sem tamanhos de modelo, sem métricas), então é evidência fraca por limitação da fonte.

**O retrato sem enfeite:** esta é a leva **mais distante do Bee** que já processamos. Das ~31 fontes:

- **0 tocam o pré-treino que rodou no L4.** Nenhuma mexe em tokenizador, init, LR, schedule,
  geometria, throughput ou checkpoint/resume. O treino segue **intocado** por esta leva — e isso é um
  resultado, não um vazio.
- A esmagadora maioria é **pós-treino / RL de alinhamento / inferência / avaliação em modelos de 1B a
  405B** (muitos 7B–70B, alguns de fronteira: GPT-5.x, Opus 4.8, GLM-5), ou domínios fora do nicho
  (robótica VLA, recsys, quântica, malware, rede elétrica, silício 3D, controle de mineração).
- **~13 fontes são 🔴 lixo total para o Bee** (escala grande, RL caro, multimodal, ou nicho errado).
- O sinal aproveitável está **concentrado num tema só**, atravessando 6+ relatórios independentes:
  **higiene de avaliação** (avaliador separado do gerador, portão determinístico, medir a coisa certa).
  Não é técnica nova — é a cicatriz que o Bee já carrega ("um adapter passou 7 benchmarks com defeito
  grosseiro invisível"), agora reconfirmada com **números de fora**.
- O resto que sobrevive são **5 ações baratas de avaliação/RAG/dados** e ideias guardadas para
  SFT/COMEIA/serving — nenhuma exige GPU nova nem reescrita.

**Veredito líquido: leva majoritariamente negativa.** Útil por **fechar portas** e por **confirmar
princípios com evidência empírica**, não por adicionar uma alavanca ao pré-treino. Quem esperava um
truque de treino sai de mãos vazias — e está certo: papers de 2026 atacam escala grande e pós-treino,
não o nosso canto (150M do zero, PT, pouca GPU).

---

## 2. ⭐ AÇÕES ACIONÁVEIS AGORA (🟢) — ordenadas por retorno/esforço

Só entra o que roda com **pouca GPU e sem reescrever o projeto**. Todas são de **avaliação/dados/RAG**
— nenhuma é do pré-treino.

| # | Ação concreta | Fonte(s) | Frente | Por que agora |
|---|---|---|---|---|
| 1 | **Nunca medir uma abelha com o modelo que a gerou/treinou.** Fixar avaliador de **família diferente** (ex.: Gemini/Chimera avaliando adapter do Bee) + exigir **veredito estruturado decomposto** (juiz de "recuperou a fonte?" separado do juiz de "resposta correta?"). | LinkedIn (juiz-de-treino **infla 2,4×** vs cross-family), ODRPO (auto-rater σ≈4,5/10, curtose 10), reward-hacking survey, judge decomposto, Specula, auditoria de fidelidade | Avaliação (SFT/COMEIA) | Custo zero de GPU, muda só como escrevemos o eval. Defesa direta contra o defeito que já nos mordeu. |
| 2 | **Teste de ablação de evidência.** Ao avaliar adapter/RAG, **remover a parte da entrada que deveria ser usada** (chunk-fonte do edital, contexto da tool) e confirmar que a saída **degrada**. Se acertar sem a evidência, o grounding é falso e score agregado nenhum pega. | auditoria de fidelidade (atalho de texto: utilidade +0,062, importância real zero), ablar retrieval | Avaliação (COMEIA/RAG) | É só re-rodar o eval com entradas ablacionadas. Mede a coisa certa, não a proxy. |
| 3 | **Selecionar checkpoint por avaliação, não pelo último passo salvo.** | RSIBench: em **78%** das buscas que passaram do pico, a tentativa FINAL foi pior que o pico intermediário | Pré-treino/SFT (seleção) | O Colab **recicla disco** e a tentação é pegar "o que sobrou". Manter eval intermediária + guardar o melhor. |
| 4 | **No RAG dos SaaS, varrer K∈{0,3,5,7,10} e medir a curva de acurácia** em vez de fixar K alto por intuição. | MRCoder: acurácia sobe até um pico e **cai** com mais recuperação; ótimo K=3–7 | RAG (PassaPro/VirtualSector) | Corta tokens e **custo de Gemini** de graça. Teste barato, mensurável hoje. |
| 5 | **Medir a mistura de corpus com desenho fatorial:** fixar base+infra+avaliação, mexer **um eixo de dados por vez** (proporção PT/EN/código). | RSIBench (isola "que dados usar" do resto do pipeline) | Dados (SFT / degraus da escada) | Formaliza "fixar a régua antes de medir" no eixo de dados. Aplicável na virada para SFT. |

---

## 3. GUARDADO PARA AS PRÓXIMAS FASES (🟡)

### (a) SFT / pós-treino
- **ORPO em vez de SFT+DPO em duas etapas.** Funde SFT + preferência num **único passo, sem modelo de
  referência separado** → economiza VRAM e uma etapa inteira. Já existe `ORPOTrainer` no TRL que
  usamos — **zero dependência nova.** → *Gatilho: quando a `chat_ptbr` sair do SFT e precisar de
  alinhamento, medir ORPO antes de montar pipeline DPO.*
- **Self-instruct com modelos que já pagamos.** Chimera/Cesar como o "LLM grande gerador" para fabricar
  pares instrução-resposta **em PT-BR** a partir de sementes pequenas. Resolve o gargalo real (não há
  corpus SFT bom em PT). → *Gatilho: ao montar o dataset de SFT de qualquer abelha.*
- **DoRA vs LoRA no mesmo orçamento de VRAM.** DoRA promete melhor eficiência de parâmetro pelo mesmo
  custo; PEFT suporta sem adaptação (uma flag). → *Gatilho: quando um adapter ficar aquém, medir LoRA
  vs DoRA antes de aumentar rank. Achado negativo é resultado válido.*
- **Destilação de procedimento como dado.** Trajetórias do Chimera (modelos grandes) viram dados de SFT
  das abelhas — **dado, não dependência nova**. → *Gatilho: enriquecer dados de SFT das abelhas
  `agentica`/`coder`.*
- **Aritmética, SE entrar no SFT:** dígitos de saída **invertidos** (menos significativo primeiro) +
  **CoT** nos exemplos tirou multiplicação de 0%→80% num modelo minúsculo. Muda só o dado. → *Gatilho:
  se PassaPro exigir cálculo — mas provavelmente melhor via tool-calling/código do que ensinar o Bee a
  multiplicar token a token.*
- **Latent reasoning (referência distante):** comprimir CoT verboso em poucos tokens latentes.
  Atraente para modelo pequeno (cada token de "pensar em voz alta" custa latência), mas exige teacher
  grande + treino especializado que **não temos**. Arquivar como conceito.

### (b) COMEIA / adapters / roteamento
- **Promoção de abelha com trava de regressão.** Só promover nova versão de adapter se ele **não
  regredir num conjunto-guarda fixado ANTES** da medição. Combate direto ao "adapter que passou 7
  benchmarks com defeito invisível". Custo ~zero, é disciplina de processo. → *Gatilho: toda
  atualização de adapter.* (SkillBoost + Living-Harness **convergem**)
- **Memória de erro do roteador, append-only com gate de escrita.** Quando o roteador determinístico
  erra a abelha e falha, registrar (gatilho→falha→correção) com filtro de duplicata. Aprende de erros
  de rota **sem chamar LLM.** → *Gatilho: quando o roteador acumular casos-limite reais.*
- **Skill-doc textual reusável por abelha.** Heurísticas de sucesso que persistem e são injetadas no
  contexto no fast-path — "evolução de skill" sem RL. **Ressalva forte:** o ganho dos papers veio do
  RL caro, não do doc isolado; é **hipótese a testar**, não receita.
- **Composição ortogonal de adapters** (base de projeção congelada por abelha) — só importa **se** um
  dia empilharmos/mesclarmos adapters em vez de hot-swap. Hoje desnecessário. Nota de arquitetura.
- ⭐ **NÃO trocar o roteador determinístico por neural.** O piso determinístico por regras (6-gram
  overlap, regex) do LinkedIn chegou por medição à mesma conclusão que já adotamos: regra barata > LLM
  caro para a parte estrutural. **Reforço para manter o fast-path** na escada.

### (c) RAG dos SaaS (PassaPro etc.)
- **Curva de K** (ação #4, quando quiser a varredura formal).
- **Filtro determinístico com análogo jurídico:** filtrar trechos por **citação de artigo/lei em comum
  + BM25 `portuguese`** — barato, sem modelo extra. → *Gatilho: ao montar o retriever de
  legislação/editais.*
- **Ablar o retrieval no eval; RAG pode piorar precisão** (mais falsos positivos). Sempre comparar
  com-RAG vs sem-RAG no mesmo eval set. **Ressalva:** o trade-off clínico do paper (aceitar falso
  alarme) é **oposto** ao do PassaPro (resposta jurídica errada com fonte falsa é pior que "não sei").
- **Questões de concurso = eval set com ground truth de graça** — reconfirma o ref de RAG Architecture.
- **Detector de alucinação leve via SFT simples** (não o loop RL caro do HSP) sobre pares
  contexto→resposta. → *Gatilho: se o RAG precisar de camada de checagem.*

### (d) Quantização / serving no RTX 5070 8GB
- **Medir Q3/Q4/Q5 GGUF no próprio bench PT antes de fixar o quant de produção** — não confiar no
  default Q4. Evidência (frágil, N pequeno) de que **Q3 pode ganhar de Q4** em eficiência de cache. →
  *Gatilho: quando Bee-150M/350M sair do SFT.*
- **Confirmação do princípio:** modelo que **cabe folgado na memória rápida** tem energia de decode
  75–80% menor e tráfego de DRAM ~90% menor. Bee-150M INT4 (~75–90 MB) está exatamente nesse regime
  ótimo. Reforça INT4 agressivo + escada começando pequena. (LLMET)
- **Evitar wrappers de segurança do tipo "reflexão"** (rodar o modelo 2×, parafrasear, multi-round):
  multiplicam latência por **5–6×** e disparam recusa de perguntas legítimas (até 80,8%). Proibitivo
  num modelo pequeno na 5070 — preferir filtro barato (perplexidade/regra). → *Gatilho: se os bots
  ganharem moderação.*

### (e) Escada 350M → 1B → 4B
- **Speculative decoding com a própria escada:** Bee-150M como **draft** de Bee-1B (mesma arquitetura
  Llama, mesmo tokenizador — pré-requisito já garantido). **Medir a taxa de aceitação antes de adotar**
  — entre 150M e 1B pode ser baixa demais para compensar.
- **Piso de capacidade — rotear tarefas "duras" para fora do 150M.** Evidência dura: em raciocínio
  formal, Haiku cai a 47% onde Opus faz 100%; a métrica barata ranqueia mal onde só a medição final
  decide. A COMEIA deve mandar verificação/raciocínio longo para o Chimera/Gemini e usar o Bee onde
  custo/latência em PT compensam.
- **Profundidade ajuda só em tarefa algorítmica sequencial** (carry/borrow encadeados) — **não
  contradiz** a decisão de crescer largura na escada; é o caso patológico.

---

## 4. CONVERGÊNCIAS (≥2 fontes independentes → sinal forte)

1. **Avaliador separado do gerador + portão determinístico + veredito decomposto** — a convergência
   mais forte de todo o estudo: **6+ fontes** apontam a mesma coisa por caminhos independentes
   (inflação 2,4× do juiz-de-treino, σ≈4,5/10 do auto-rater, gating anti-fraude → recompensa 1,0 com
   0% real, judge decomposto, Opus 100%→Haiku 47%, ablação de fidelidade). **Já é doutrina nossa
   (harness-engineering) — agora com números externos.** Ações #1 e #2 são obrigatórias.
2. **"Mais contexto/recuperação piora após um ponto" + "o último não é o melhor"** — MRCoder (curva de
   K com pico) e RSIBench (78% degradaram após o pico). Convergem na disciplina de **medir a curva e
   guardar o melhor, não o final** (ações #3 e #4).
3. **Determinístico antes de LLM / não adotar framework pesado** — filtro por regra (MRCoder), piso
   determinístico do LinkedIn, não-adotar-DSPy, somados aos vereditos anteriores de não adotar
   LangGraph. **Reforço unânime ao roteador determinístico da COMEIA.**
4. **Modelo pequeno que cabe na memória = eficiência máxima; quantização agressiva é o caminho** —
   GGUF Q3/Q4 no Pi (nossa escala) e LLMET (residência on-chip). Confirmam a estratégia de serving.
5. **Trava de regressão para promover artefato** — SkillBoost e Living-Harness, dois papers, mesma
   ideia: só aceitar mudança que não regrida num guarda fixado antes.

---

## 5. CONFRONTOS com o que já decidimos (honestidade brutal)

**A verdade desconfortável: esta leva não confronta NEM valida as decisões centrais do pré-treino.**
Como nenhuma fonte testa pré-treino de 150M, não há evidência nova sobre geometria 30×576, LR 3e-3, 1
época, vocab 32k ou arquitetura Llama sem custom. **Ausência de contradição não é confirmação** —
essas escolhas continuam apoiadas apenas na medição interna e nos refs anteriores (Burkov et al.), que
já haviam sinalizado a geometria fora de faixa. Não deixar o silêncio desta leva virar falsa segurança.

Os únicos atritos reais são com *tentações de design futuro*, não com decisões tomadas:

- **Two-step validation:** abaixo de ~8B, usar o modelo pequeno como **validador/refinador PIORA** o
  resultado (Llama-3.2 3B: 53%→46,8%). Confronta qualquer ideia de usar o Bee como juiz/refinador.
  **Regra derivada:** o Bee é o **extrator determinístico do 1º passo**, nunca o validador — o refino,
  se existir, fica para um modelo maior (Gemini, já no stack).
- **"Aumente a profundidade":** parece bater de frente com "crescer largura na escada", mas **não é
  confronto real** — é específico de aritmética de dígitos (tarefa sequencial patológica), não da carga
  geral de um LM PT-BR. Largura-antes-de-profundidade segue de pé.
- **MoE/MoA:** 🔴 descartado — Mixtral 8×7B é escala e paradigma errados. A COMEIA (adapters LoRA
  hot-swap + roteador determinístico) resolve "especialização" mais barato e mais simples que MoE de
  verdade. **Confirma** a decisão, não confronta.

---

## 6. NÃO APLICÁVEL (🔴) — mapa de onde o Bee está sozinho

| Fonte | Por que é 🔴 |
|---|---|
| Priority-Aware LoRA Unlearning (2606.22878) | Federated unlearning em 7B; o Bee não tem nada federado |
| GradientSHAP / controle de mineração | Otimização de equipamento; não é LLM |
| Cybersecurity frontier (GenAI) | Paper de posição, sem método, nicho malware |
| WhisperRec (2606.28929) | Recsys + teacher de 235B; escala e nicho errados |
| LLMET / M3D memory | Design de silício 3D; hardware que não rodamos |
| TurboVLA (2607.27205) | Robótica visão-linguagem-ação; multimodal |
| ByDeWay-V2 | MLLM espacial; exige detector de visão externo |
| Hallucination Self-Play (2607.07993) | RL (GRPO) em 7B, 8×A100 |
| ODRPO | Estimador de vantagem de RL, 4–7B, 8×H100 |
| SMD / Weak-to-Strong / R-CAI | RL/alinhamento/safety em 1B–70B; reward model + juiz grande |
| Reward Hacking survey (2604.13602) | Conceitual, modelos 100B+, sem método barato |
| GPT-Red | RL self-play de fronteira (pesos GPT-5.5); maior rodada de safety RL publicada |
| OmniQEC / Specula | Quântica; e verificação formal 100% dependente de Opus 4.8 (Haiku desaba a 47%) |
| Defesas anti-jailbreak | 7B–9B, só inglês, fora de prioridade |

**Mais o blog+repo AWS (DSPy):** o *pipeline* (self-instruct→SFT→ORPO→judge) é 🟡 útil, mas **DSPy como
dependência é 🔴** — filosoficamente oposto ao Bee (otimiza prompt de modelo grande; nós usamos regra
barata). Pegar as ideias, não o framework.

---

## 7. Os 10 aprendizados que levo deste estudo

1. **O pré-treino do Bee está num canto que a literatura de 2026 não visita.** ~31 fontes, zero sobre
   treinar 150M do zero em PT com pouca GPU. Solidão de nicho — a régua interna é a **única** fonte de
   verdade sobre nossas decisões de treino.
2. **A única convergência forte (6+ relatórios) é sobre avaliação:** quem gera não pode avaliar;
   juiz-de-treino infla 2,4×; auto-rater tem σ≈4,5/10. Já era cicatriz nossa — agora é lei com número.
3. **Ablação de evidência é o teste mais barato e mais valioso que ganhamos:** remover a fonte e ver
   se a resposta degrada pega o adapter que "acerta por atalho", coisa que score agregado não revela.
4. **Selecionar checkpoint por avaliação, não pelo último passo** — 78% das buscas pioram após o pico.
   Crítico porque o Colab recicla disco e a tentação é pegar o que sobrou.
5. **Mais recuperação piora depois de um ponto** (K ótimo baixo) — economia de token/custo de Gemini
   de graça no RAG dos SaaS, mensurável já.
6. **ORPO é o maior presente para o SFT:** funde SFT+preferência sem modelo de referência, corta VRAM
   e uma etapa inteira, já vem no TRL.
7. **O roteador determinístico da COMEIA sai reforçado por medição alheia** (piso determinístico do
   LinkedIn, rejeição de DSPy/LangGraph). Não trocar por neural na escada.
8. **Existe um piso de capacidade que o 150M não cruza** (Haiku 47% vs Opus 100% em raciocínio
   formal). A COMEIA deve rotear tarefa dura para fora do backbone pequeno.
9. **O Bee é extrator, nunca validador:** abaixo de ~8B, o passo de validação por LLM degrada o
   resultado. Design travado por evidência.
10. **Achado negativo é o produto principal desta leva.** O valor está em fechar ~13 portas com
    confiança e reconfirmar 5 princípios — não numa alavanca de treino, que não veio. **Não parar nem
    ajustar nada do pré-treino por causa destes papers.**
