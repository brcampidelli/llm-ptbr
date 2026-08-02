# Estudo — Modelos de fronteira como PROFESSORES do Bee (destilação)

**Data:** 2026-08-01 · **Método:** multi-agente (4 pesquisadores paralelos, 1 por família) ·
**Fontes:** páginas oficiais HF (`main`/`tree`/`discussions`), OpenRouter, LICENSE, cross-check web.

> **Pergunta do Bruno:** usar esses modelos (Kimi-K3, DeepSeek-V4-Flash, Qwen3.7-Max/Flash,
> GLM-5.2) como **professores** do Bee — a possibilidade de **destilar** eles.
> **Resposta curta:** dá — mas só de um jeito (**black-box / dados sintéticos**), e a
> escolha do teacher depende de **3 travas** que a maioria das análises ignora.

---

## A conclusão que atravessa os 5 modelos (leia isto primeiro)

**Destilação white-box (logits/hidden states) está MORTA para o Bee — em todos eles — por
dois motivos independentes, cada um já fatal sozinho:**

1. **Tamanho.** Os open-weight são todos MoE gigantes: DeepSeek-V4 ~284B (167 GB FP8),
   GLM-5.2 753B (1,5 TB), Kimi-K3 ~2,8T (1,56 TB). Extrair logits exige **hospedar o teacher
   num cluster multi-GPU**. Colab A100 (40/80 GB) não carrega nenhum. Os fechados (Qwen-Max/Flash)
   nem pesos têm.
2. **Tokenizador.** O Bee tem **BPE 32k próprio**. Destilação por logits exige que teacher e
   aluno compartilhem o **mesmo espaço de vocabulário** — o do Bee não bate com o de nenhum
   deles. Logo, mesmo se coubesse na GPU, o KL token-a-token **não alinharia**.

**→ O único caminho viável é BLACK-BOX: o teacher gera texto (dados sintéticos), o Bee treina
nesse texto por SFT.** Texto é **tokenizador-agnóstico** — resolve as duas travas de uma vez.
Isso, aliás, é o que essa geração inteira faz: o Kimi-K3 numa discussão **"se acha o Claude"**,
sintoma clássico de treino com dados sintéticos de outro modelo.

**A segunda trava é jurídica** (a que inviabiliza tarde demais): API comercial costuma **proibir
no ToS** usar a saída pra treinar concorrente. Pesos abertos com licença permissiva **não**.
Um Bee destilado de teacher com licença proibitiva é **impublicável e não-investível** — a mesma
disciplina do nosso corpus.

**A terceira trava é a que mais importa pro Bee, e ninguém documenta:** **força em PT-BR.**
Nenhum dos 5 model cards prova PT. A tese do Bee é justamente português forte — então o teacher
precisa gerar **PT nativo, não "traducionês"**. Isso **tem que ser medido** (piloto de 200-500
gerações) antes de gastar orçamento. Não confie no marketing multilíngue.

---

## 🟢 ATUALIZAÇÃO 2026-08-02 — NVIDIA build (build.nvidia.com): teacher FREE, e o ToS PERMITE destilar

O Bruno tem conta no **build.nvidia.com**. Ele hospeda **inferência grátis** (API OpenAI-compatible,
`integrate.api.nvidia.com/v1`, é só gerar a key) dos teachers que já validamos: **DeepSeek-V4-Pro**
(2T MoE, MIT), **GLM-5.2** (MIT) e **Nemotron-3-Ultra-550B** (NVIDIA-open, feito para geração de dados
sintéticos). A aba "GPUs" leva ao **Brev** (nuvem de GPU da NVIDIA, agrega 19 provedores — 3ª opção de treino).

**Li o ToS oficial (NVIDIA Technology Access TOU, © 2024, 10 páginas — PDF do rodapé). Veredito:
🟢 VERDE — ao contrário da Qwen, NÃO proíbe destilar.**
- **Não há cláusula anti-distillation** nem "não criar modelo concorrente" contra o usuário. A Qwen tinha
  as duas (II.2(c)+(e)); a NVIDIA não tem nenhuma.
- **Você mantém direito sobre o que gera** (§4: a NVIDIA reserva os direitos "except for... your User
  Content"). As restrições do §5 miram a *Technology* da NVIDIA (software/modelos/servidores), não as saídas.
- **§7 (Trials) contempla explicitamente** usar o resultado depois: em certos trials você pode "download
  your results for further use post-trial".
- A licença do **modelo** subjacente continua valendo (§17): DeepSeek-V4 MIT ✅, GLM-5.2 MIT ✅, Nemotron
  NVIDIA-open ✅.

**Condições (respeitar):**
1. **Não burlar limite/quota** — §5(n) proíbe usar a Technology para "avoid incurring fees or exceeding use
   limits". O free tier é rate-limited → serve pro **piloto** (200-500) à vontade; pra **volume**, usar os
   *paid partner endpoints*, não espremer o trial.
2. **Não usar como raspagem** de conteúdo dos servidores NVIDIA (§6) — chamada de API licenciada gerando
   conteúdo próprio é o uso pretendido; manter volume dentro da quota.
3. As-is, cap de responsabilidade US$50, arbitragem (§§12,13,18) — padrão, não bloqueia.

**Consequência pro plano:** o gate jurídico da destilação está **VERDE**. O teacher primário (DeepSeek-V4)
fica **grátis** pro piloto e barato pra escalar — melhor que a Qwen (proibida) e mais barato que pagar a API
da DeepSeek. Falta só o **piloto de PT-BR** (qualidade, inalterado — nenhum documenta PT).

---

## Tabela comparativa

| modelo | real? | total / ativos | pesos | licença | white-box? | API saída /1M | PT declarado |
|---|:---:|---|:---:|---|:---:|---:|---|
| **DeepSeek-V4-Flash-0731** | ✅ | ~284B / ~13B MoE | ✅ 167 GB FP8 | **MIT** (s/ anti-distill) | ❌ tamanho | **US$0,18** | não doc. |
| **GLM-5.2** | ✅ | 753B / ~40B MoE | ✅ 1,5 TB BF16 | **MIT** (s/ anti-distill) | ❌ tamanho | US$1,32 | EN/ZH-first (PT fraco) |
| **Kimi-K3** | ✅ | ~2,8T / ~104B MoE | ✅ 1,56 TB MXFP4 | **Mod-MIT** (trava só >US$20M/ano) | ❌ tamanho | API (a definir) | não doc. |
| **Qwen3.7-Flash** | ✅ | não divulgado (é **VL**) | ❌ API-only | 🔴 **ToS PROÍBE destilar** | US$0,13 | não conf. |
| **Qwen3.7-Max** | ✅ | não divulgado | ❌ API-only | 🔴 **ToS PROÍBE destilar** | US$4,42 | não conf. |

> ⚠️ Números vindos de páginas lidas por WebFetch + cross-check; o MCP do HF pendurou e foi
> abortado, então params exatos de Kimi/GLM são **ordem de grandeza, não auditados**. Benchmarks
> divulgados (ex.: GLM AIME 99,2) cheiram a saturação/contaminação — **marketing até validar**.
> Todos são modelos de fronteira lançados ~jul/2026 (DeepSeek-V4 saiu **31/07**, ontem).

---

## Por modelo — o essencial pro Bee

### 🟢 DeepSeek-V4-Flash-0731 — **o melhor candidato geral**
- **MoE ~284B/13B**, contexto 1M, MLA + sparse attention (DSA), FP8 nativo. Modelo de **texto**
  (não VL). OpenRouter: **US$0,09 in / 0,18 out** por 1M — baratíssimo.
- **Licença MIT, sem cláusula anti-distillation** (verbatim no LICENSE). Sinal verde total.
- **Custo de corpus sintético:** ~US$90 por 500M tokens de saída; ~US$180 por 1B. Ordem de
  grandeza de **dezenas a poucas centenas de dólares** por rodada.
- **Veredito:** teacher **primário** para SFT sintético em PT — MIT limpo, barato, texto puro.
  Único porém: PT não documentado → **piloto obrigatório**.

### 🔴 Qwen3.7-Flash / Max — **FORA: o ToS proíbe destilar (confirmado)**
- Seriam baratos (Flash US$0,13 out/1M), **MAS** o ToS oficial (qwen.ai/termsservice,
  atualizado 19/mai/2026) **proíbe destilação por nome** — confirmado lendo o documento:
  - **Seção II.2(c):** proíbe "mine, or **distil**... the Outputs... using... distillation
    techniques".
  - **Seção II.2(e):** proíbe usar Outputs para "develop or improve any products or services
    (including... any models) that **compete with or are similar in functionality**".
- Ambos são **API-only** (Alibaba fechou os flagships em 2026, quebrando o Apache-2.0 da linha
  aberta), então não há como escapar do ToS via pesos abertos. O Flash ainda é **visão-linguagem**.
- ⚠️ Um resumo superficial (que olhava só a *Usage Policy* — infra crítica/campanha política)
  disse "não há proibição". **Está errado:** a proibição está na seção "What You Cannot Do",
  não na Usage Policy.
- **Veredito:** **descartar os dois.** Usar a saída deles pra treinar o Bee viola o ToS →
  Bee impublicável/não-investível. (Nota: os modelos Qwen **open-weight** de gerações passadas,
  Apache-2.0, seriam OK — mas 3.7-Flash/Max não são open-weight.)

### 🟡 GLM-5.2 — **teacher secundário, de nicho (código/raciocínio)**
- **MoE 753B/40B**, contexto 1M, **MIT** (sem anti-distill). Pesos abertos (1,5 TB BF16).
  OpenRouter ~US$0,42 in / 1,32 out (promo).
- **EN/ZH-first — PT é cauda, não força.** SOTA-aberto em coding/agentic (SWE-bench Pro 62,1).
- **Veredito:** **não** usar como teacher de PT-BR (é o que o Bee quer ter e ele não tem). Usar
  **black-box** só pra gerar dados de **código e raciocínio** no pós-treino. Licença é ouro.

### 🟡 Kimi-K3 — **teacher premium pra exemplos difíceis**
- **MoE ~2,8T/104B** (fronteira), contexto 1M, MXFP4 (QAT). Multimodal. **Licença Modified-MIT**
  sem anti-distill (só pede acordo acima de US$20M/ano — irrelevante pra nós).
- Qualidade de fronteira, mas **custo de API a definir** e PT não medido. Risco de "sotaque"
  EN/CN nos dados sintéticos → exige filtro PT-BR.
- **Veredito:** teacher **premium** para um **lote pequeno e curado** de exemplos difíceis
  (CoT, raciocínio), não pra corpus massivo (caro). Rejection sampling: Bee gera, Kimi julga.

### 🔴 Qwen3.7-Max — **fora por custo**
- **US$4,42 out/1M** (~34× o Flash), API-only, mesmo risco de ToS. Só compensaria pra um lote
  minúsculo de altíssima qualidade — e aí o Kimi-K3 faz o mesmo papel. **Descartar.**

---

## Plano de destilação pro Bee (priorizado)

### O que destilação NÃO resolve
O Gate 2 diagnosticou **"falta token"** no pré-treino. **Dados sintéticos não são a resposta pra
isso** — no pré-treino o que precisa é **token barato em volume** (web crua: fineweb-2 `por` tem
>1 T tokens a custo ~zero via streaming). Gerar 1 T tokens sintéticos custaria dezenas de milhares
de dólares. **Destilação é para o PÓS-TREINO** (qualidade de instrução/resposta), não pra tapar o
buraco de volume do pré-treino.

### AGORA (quando o Bee-v2 fechar e passar pelo Gate 2)
1. **Fechar o Gate 2** (v2 vs SmolLM2 vs v1) — decidir se 3 épocas moveram o bpb PT. É o
   experimento em curso; destilação vem **depois** que o base estiver decente.

### PRÓXIMO DEGRAU — pós-treino do Bee (350M→1B), a fase onde o teacher entra
2. **Piloto de PT-BR (gate barato, US$ poucos):** gerar ~200-500 respostas em PT via
   **DeepSeek-V4-Flash** (teacher primário; Qwen está fora por ToS). Medir fluência/gramática/
   ausência de traducionês. **Só investir no teacher que passar.** Nenhum documenta PT — isto
   não é opcional.
3. **SFT sintético (teacher primário = DeepSeek-V4-Flash):** gerar corpus PT-BR de instrução+
   resposta (+ CoT, reescritas) via API, passar por **rejection sampling / filtro de qualidade**
   pra cortar erro e sotaque, e treinar o Bee por SFT. Custo ~US$90-180 por 500M-1B tokens.
   MIT limpo → publicável.
4. **Dados de nicho:** **GLM-5.2** (black-box) só pra **código e raciocínio** (onde é SOTA-aberto),
   não pra PT geral.

### FUTURO (subir a barra)
5. **On-policy / rejection sampling distillation:** o **Bee gera**, um teacher forte
   (Kimi-K3 premium) **julga e reescreve** as melhores respostas → dataset de preferência.
   Depois **GRPO / RLVR** onde houver verificação objetiva (ex.: múltipla escolha com gabarito,
   código que roda). Cada fase = um **adapter separado da COMEIA** (evita esquecimento).

### DESCARTAR
- **White-box (logit distillation)** de qualquer um deles — tamanho + tokenizador próprio matam.
- **Qwen3.7-Flash e Max** — o ToS oficial **proíbe destilar/treinar modelo similar** (confirmado,
  seção II.2(c)+(e)). Fora, independente do preço.
- **Qualquer teacher antes do piloto PT** (todos — nenhum documenta PT).

---

## Ações concretas (checklist)
- [ ] Fechar Gate 2 do Bee-150M-v2 (em curso).
- [x] ~~Ler o ToS da Qwen~~ — **FEITO (2026-08-01): proíbe destilar** (II.2(c)+(e)). Qwen fora.
- [x] ~~Ler o ToS do NVIDIA build~~ — **FEITO (2026-08-02): PERMITE destilar** (sem cláusula anti-distill;
      §4 mantém direito sobre User Content; §7 permite uso pós-trial). Teacher FREE via `integrate.api.nvidia.com/v1`.
- [ ] Piloto PT-BR: 200-500 gerações via DeepSeek-V4-Flash → medir fluência/gramática.
- [ ] Guardar cópia dos LICENSE (DeepSeek MIT, GLM MIT, Kimi Mod-MIT) + creditar origem dos
      dados sintéticos no MANIFEST — procedência auditável, requisito de investimento.
- [ ] Definir volume-alvo do corpus SFT sintético (começar pequeno: ~dezenas de milhares de
      exemplos curados, escalar se funcionar).

---

## Incertezas honestas (não varrer pra baixo do tapete)
- **PT-BR de nenhum teacher foi medido** — tudo é inferência a partir de "multilíngue". O piloto
  é o que decide.
- Params exatos de Kimi/GLM não auditados (MCP HF caiu); benchmarks de fronteira são marketing.
- ~~ToS da Qwen~~ **resolvido:** o ToS oficial proíbe destilar (II.2(c)+(e)) → Qwen fora.
- Custo de API do Kimi-K3 não cotado (só pesos abertos + inference providers genéricos).
