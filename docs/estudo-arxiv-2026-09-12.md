# Estudo do arXiv recente — 4.445 artigos, 57 lidos, o que muda no Bee (2026-09-12)

> **O que é:** todas as 38 listagens `recent` que o Bruno pediu (cs.AI, cs.CL, cs.LG, cs.CV… eess.SY),
> janela **05 a 10 de setembro de 2026**. 6.680 entradas brutas → **4.445 artigos distintos**
> (o resto é cross-listing). Todos os 4.445 abstracts foram lidos; 57 artigos foram lidos no
> **texto completo**. Artefato com tudo: [`estudo-arxiv-2026-09-12.json`](estudo-arxiv-2026-09-12.json).

## 0. Método — e o que ele não consegue mostrar

| etapa | como | resultado |
|---|---|---:|
| listagens | parser das 38 páginas `?show=2000`, dedup por id | 4.445 |
| abstracts | API `export.arxiv.org`, lotes de 100 | 4.445 |
| triagem | **18 leitores independentes**, ~247 abstracts cada, **um briefing único** com o contexto do Bee e taxa-base declarada (~1–2% de nota 3) | 108 nota 1 · 128 nota 2 · **51 nota 3** (1,15%) |
| fronteira | **segundo leitor** relê os 128 de nota 2 | **+6** promovidos |
| leitura | 18 leitores, texto completo, **questionário fixo** (setup, números com baseline, sementes, escala, o que transfere, confirma/contradiz o que o Bee já mediu, veredito, gate) | **57** |
| vereditos | | **2 ADOTAR · 37 TESTAR · 13 LER DEPOIS · 5 NÃO ADOTAR** |

⚠️ **O que este estudo não mostra:**
- só a janela de 6 dias; nada anterior;
- cada abstract teve **um** leitor na triagem — um artigo bom rebaixado a 0/1 por um leitor avaro não voltou (o segundo leitor cobriu só a fronteira 2);
- cada texto completo teve **um** leitor; os números foram **transcritos**, não re-medidos;
- "veredito" é sobre **transferência ao Bee** (1 GPU, ~1B, 8 idiomas, orçamento de centenas de dólares), não sobre mérito científico.

🔴 **E o dado de rigor que enquadra tudo o que vem abaixo — dos 57 finalistas:**

| | |
|---|---:|
| reportam sementes ou variância | **27 (47%)** |
| testaram em escala ≤ 3B | 36 (63%) |
| liberam código ou dado | 25 (44%) |

Mais da metade dos artigos "acionáveis" **não reporta variância**. Todo gate abaixo nasce com 2–3
sementes porque o artigo de origem em geral não tem. E o padrão que se repetiu nas leituras:
**o número do abstract encolhe no texto** — semente única, escala errada, ou medido sem treinar.
Foi por isso que a fase 2 existiu.

---

## 1. Os dois ADOTAR — ambos confirmam lições que o Bee pagou para aprender

**⭐⭐ [2609.03966](https://arxiv.org/abs/2609.03966) — Interface-Induced Trajectory Censoring.**
*A taxa de chamada de ferramenta não é propriedade do modelo; é do stack modelo + template +
parser.* **O mesmo modelo mede 0% ou 96% só trocando o adaptador.** É a lição §2e (*a régua tem
de parar*: 0/85 → 62,5% sem retreinar) generalizada e com um **preflight check de 98 linhas**.
→ Copiar o preflight para o avaliador agêntico; citar na §2e como confirmação externa.

**⭐ [2609.09245](https://arxiv.org/abs/2609.09245) — What Fixed-Rollout pass@k Can Identify.**
Prova formal de que **pass@k acima do n amostrado não tem solução única** — só um intervalo, que
pode variar por milhares de vezes. Não muda prática (o Bee já não extrapola); muda o **status**
da regra §2k, de "regra de casa" para teorema citável.

---

## 2. O que muda em cada frente — os gates, por ordem de valor

Critério de ordem: **o que decide uma escolha que o Bee vai fazer em breve**, pelo menor custo.
Cada linha tem o gate barato proposto pelo leitor (detalhes no apêndice).

### 2.1 O próximo pré-treino (não o run atual, que não se mexe)

| # | artigo | o que afirma | gate | por que importa |
|---|---|---|---|---|
| 1 | [2609.04577](https://arxiv.org/abs/2609.04577) Muon/SOAP | **1,3–1,9× de eficiência de token** sobre AdamW na faixa de *overtraining* (1×–8× Chinchilla) — a faixa do Bee | par AdamW × Muon no Bee-150M, ~1–2B tokens, **2 sementes**, ~US$ 5 | é o maior payoff potencial do lote; e é otimizador, que este projeto nunca variou |
| 2 | [2609.11917](https://arxiv.org/abs/2609.11917) repetição em denso | denso tolera **~8×** de repetição quase sem dano; degrada feio só a **~64×** | mini-run ~150M com um idioma minoritário repetido no R do déficit medido, sozinho e misturado com PT | ⚠️ medido entre *gêneros* em inglês, não entre *idiomas* — mas se transferir, o déficit de **13–53×** de dado não-PT deixa de ser bloqueio |
| 3 | [2609.11655](https://arxiv.org/abs/2609.11655) Musec | estabiliza Muon numa faixa de LR **bem mais larga** | entra no gate #1 como terceiro braço | sem sementes, sem números no texto, sem código — mas custa nada testar junto |
| 4 | [2609.05275](https://arxiv.org/abs/2609.05275) layer dropout | corta **até 25% dos FLOPs** mantendo a loss (271M–8,2B, Cerebras) | mini-run pareado no mesmo orçamento de tokens; **medir tok/s, não FLOPs** | o ganho só existe se a implementação de fato pula o cálculo numa GPU |
| 5 | [2609.03807](https://arxiv.org/abs/2609.03807) pause token grátis | **0,028 nats de CE num 1B** — a escala exata do Bee-1G — por ~33% de treino só na cauda | Bee-150M, **múltiplas sementes** (o artigo tem uma) | custo zero na inferência |
| 6 | [2609.09691](https://arxiv.org/abs/2609.09691) camadas em loop | compartilhar 4 camadas ×12 empata com modelos maiores no BabyLM | variante com metade das camadas aplicadas 2× | ⚠️ comparação de parâmetros, não de FLOPs; a fatia pareada **derruba rastreio de entidade**. Ângulo honesto: VRAM do otimizador |

⚠️ **Resultado negativo que evita gasto:** [2609.04180](https://arxiv.org/abs/2609.04180) — paráfrases
batem repetição pura em aquisição de conhecimento… **e o efeito é nulo, até levemente negativo,
em ~1B**. Qualquer plano de sintetizar paráfrases para o corpus do Bee fica reprovado antes de
começar. O leitor achou a tabela que desmente o abstract na escala do Bee.

### 2.2 Qual checkpoint serve de base para o pós-treino — uma decisão que o Bee ia tomar sem medir

**🔴 [2609.08966](https://arxiv.org/abs/2609.08966) — Good Pretraining, Bad SFT.** Num MoE de 30B,
**o checkpoint de melhor loss — o decaído — foi o PIOR ponto de partida para SFT**, travando numa
patologia de nunca parar de gerar que reajustar o LR do SFT não conserta. Escala muito maior,
sem sementes, dominado por uma falha só — mas a pergunta transfere inteira: *o pós-treino do
Bee-1G parte do 20B decaído ou do 15B no platô?* O projeto ia assumir "o final".
→ Gate: **densidade de solução** (~100 perturbações gaussianas σ≈0,005 nos pesos, medir a loss)
nos marcos que já vão ser salvos. **Custa zero de GPU nova.**

### 2.3 Avaliação — quatro auditorias baratas no que já existe

| artigo | o defeito que ele nomeia | o que o Bee já tem | gate |
|---|---|---|---|
| [2609.08327](https://arxiv.org/abs/2609.08327) | **67,9%** das sub-queries tinham ferramenta equivalente não anotada; isso infla **30–47%** do ganho de fine-tuning e chega a **inverter o sinal** | a loteria de string do E5, agora na **seleção** | reler 30–50 "erros de seleção" do holdout de 747 ferramentas com juiz barato |
| [2609.09218](https://arxiv.org/abs/2609.09218) | scaffold e scorer distorcem rankings de agentes (*double measurement confound*) | §2y | rodar as sondas **correta / vazia / fabricada** no scorer atual; se a fabricada pontua perto da correta, o scorer não mede |
| [2609.10357](https://arxiv.org/abs/2609.10357) | holdout sem contaminação exata ainda favorece o **domínio** dominante do corpus (+28% MASE) | fingerprint pega duplicata, **não** familiaridade de domínio | bpb por **fonte** do holdout (Wikipédia, C4, notícias…) correlacionado com a fração da fonte no treino |
| [2609.02899](https://arxiv.org/abs/2609.02899) | contaminação infla o absoluto mas **raramente reordena** (ρ=0,997); só contaminação *diferencial* distorce (3 de 188) | os 56% de contaminação achados por censo | paráfrases de 50–100 itens (~US$ 1), medir o gap original−paráfrase nos dois braços de um pareado. ⚠️ nunca testado abaixo de 7B |

**Confirmação externa da decodificação restrita:** [2609.07370](https://arxiv.org/abs/2609.07370)
— abaixo de 2B, **0,5%** das respostas cruas são JSON direto. O +10 pp que o Bee mediu não é
opcional. (NÃO ADOTAR: não traz alavanca nova.)

**Uma hipótese barata sobre um colapso já documentado:** [2609.04582](https://arxiv.org/abs/2609.04582)
— um 0,6B que **sempre responde SIM** já "sabe" a resposta nos logits (**AUC 0,887**); o defeito é
um limiar deslocado +4,6σ, corrigível com **1 parâmetro sem retreinar**. O Bee documentou
recusar-tudo e chamar-tudo (§2j, §2u). → Gate: margem de logit chamar × recusar nos casos do
holdout, num checkpoint agêntico existente. Minutos.

### 2.4 SFT e agêntico — o que ataca defeitos que o Bee mediu

| artigo | número | o que toca no Bee | gate |
|---|---|---|---|
| ⭐ [2609.04184](https://arxiv.org/abs/2609.04184) catálogo perturbado | binding de argumento **50,8% → 92,6%** embaralhando ordem, removendo itens não usados, renomeando ~20% | **§2u** — o modelo que aprendeu a *contar* o catálogo e foi de 100% a 0% ao reordenar duas ferramentas | aplicar a augmentação ao corpus agêntico atual, mesmo n de passos, 3 sementes |
| ⭐ [2609.04714](https://arxiv.org/abs/2609.04714) recusa sem template | **a frase-padrão fixa** — não o conteúdo, não a decisão — é a causa comprovada (teste causal por palavra-chave) da generalização excessiva de recusa | **§2ab** — 91% de negativos em template ensinaram a recusar *tudo*; é o mecanismo | reescrever as negativas mantendo a decisão e removendo o template; medir over-calling **e** as outras capacidades |
| [2609.09072](https://arxiv.org/abs/2609.09072) ToolLoop | síntese em 3 estágios com verificação bate 5× mais dado; **sem verificação o modelo fica PIOR que sem SFT** (79,97% × base 82,14%) | o custo de dado agêntico mal construído, já medido em outra forma | ~200 exemplos pelo laço de 3 estágios, treinar, comparar |
| [2609.06124](https://arxiv.org/abs/2609.06124) proveniência de argumento | a tag de origem do argumento vale **6,4 pp de BFCL** quando removida | **§2n** | ~200 trajetórias com tag, com o teacher gratuito já em uso |
| [2609.09163](https://arxiv.org/abs/2609.09163) mundos verificados | LoRA sobre *muitos* mundos verificados generaliza: **+34 pp, 3 sementes** | ⚠️ o +29 em 0,5B é **semente única** | 20–40 catálogos-variante verificados por execução |
| [2609.03150](https://arxiv.org/abs/2609.03150) contenção no adapter | gradientes de tarefas quase ortogonais dentro do mesmo LoRA (cos −0,002); **aumentar o rank piora** | *capacidades competem* — e derruba a saída "dá mais rank" | cosseno de gradiente entre duas capacidades nos checkpoints do 350M |
| [2609.03900](https://arxiv.org/abs/2609.03900) rank do baseline | comparação inverte de **+5,0 para −11,6 pp** só de mudar o rank de 8 para 72 (1,5B, 3 sementes) | **§2f** num eixo que o Bee não varre: rank | treinar o adapter comparado em 2–3 ranks antes de afirmar |
| [2609.04565](https://arxiv.org/abs/2609.04565) supervisão esparsa | 1–2 tokens por trajetória igualam destilação densa; o tensor `[B,T,V]` vira `[B,V]` | o **teto de VRAM** do SFT na 5070 é esse tensor | exige professor com logprob aberta — infra que o Bee não tem |
| [2609.05198](https://arxiv.org/abs/2609.05198) curar por dificuldade | 8 exemplos difíceis batem 17 mil em OPD | mecanismo de OPD, mas a curadoria por dificuldade cabe no SFT atual | ranquear 200–500 exemplos por acerto em k=8 |
| [2609.09476](https://arxiv.org/abs/2609.09476) esquema no prompt | em 270M–1,7B, esquema no prompt bate token fixo; token fixo acerta **0%** em função inédita e **inventa** a chamada quando a função some | confirma a escolha do Bee | medir a margem: 50–100 casos com ferramenta removida do menu |

**Menos prioritários, com o motivo:** [2609.05885](https://arxiv.org/abs/2609.05885) (LR anisotrópico
em LoRA, +1–4 pp e robustez a LR — **só medido em ≥7B**); [2609.07971](https://arxiv.org/abs/2609.07971)
(MeRoTune — só compensa se uma checagem de 4 desigualdades confirmar que as especialidades não
competem; **dos 5 pares do autor só 1 passou**, e as do Bee competem); [2609.11029](https://arxiv.org/abs/2609.11029)
(CE ponderada por TF-IDF, −58% de memorização em full FT mas **sem efeito em LoRA a ~1B** — o
cenário do Bee); [2609.04172](https://arxiv.org/abs/2609.04172) (OPD com uma query — exige tokenizador
compartilhado com o professor).

### 2.5 Dados e multilíngue

| artigo | o que afirma | gate |
|---|---|---|
| 🔴 [2609.03350](https://arxiv.org/abs/2609.03350) | **o FineWeb-2 tem autocontaminação treino/teste** e infla avaliação — e o FineWeb-2 é a fonte dos 7 idiomas não-PT do Bee-1G | scanner de n-gram do holdout multilíngue contra os splits do FineWeb-2 nos idiomas em que ele é fonte. ⚠️ O censo por fingerprint cobriu o PT; o val não-PT foi verificado contra o treino, mas não contra o próprio FineWeb-2 |
| [2609.07699](https://arxiv.org/abs/2609.07699) Fine PT-PT Web | pré-filtro de linha (remove linhas curtas e duplicadas *antes* das heurísticas) resgatou **+19% de documentos** sem perda medida | rodar o filtro do Bee com e sem o pré-filtro em 50–100 mil docs. ⚠️ O artigo **não treina modelo nenhum**; e o corpus é PT-PT, não PT-BR |
| [2609.05766](https://arxiv.org/abs/2609.05766) Data Scout | crawling por taxonomia acha conteúdo **70–82× mais denso** que filtrar CommonCrawl | piloto grátis (cota da busca programável) para árabe ou japonês, trocando o classificador de matemática por identificador de idioma |
| [2609.10445](https://arxiv.org/abs/2609.10445) Tiny Aya | "pensar no idioma do usuário" generaliza para idiomas **nunca supervisionados** se o treino for amplo e conjunto; **10–20% de dado multilíngue comum** destrava a maior parte | ablação pareada no próximo SFT que precise generalizar entre os 8 idiomas |
| [2609.11399](https://arxiv.org/abs/2609.11399) TransClean | LMs como tradutores poluem **3% a ~100%** das traduções com explicação/bilíngue/idioma errado; detectar é barato (90–98%), extrair é difícil (~50%) | rodar o detector (regex + fastText) em qualquer tradução de professor **antes** de usá-la como alvo ou de pontuá-la |
| [2609.06652](https://arxiv.org/abs/2609.06652) | sob o mesmo orçamento, **a receita de menor loss perdeu no benchmark downstream** nas duas famílias (vídeo) | a lei de mistura do Bee, ajustada por bpb, precisa de uma métrica de capacidade ao lado |
| [2609.05099](https://arxiv.org/abs/2609.05099) ILP4LID | LID para code-switching 0,54 → 0,71, CPU, cobre PT, código aberto | auditoria de pureza por idioma em 1–5 mil docs por fatia |
| [2609.04819](https://arxiv.org/abs/2609.04819) | das 4 métricas de compartilhamento cross-lingual, **só ILO** sobrevive aos controles; CKA mede o cone anisotrópico | se for medir o que as 8 línguas compartilham, a régua já está escolhida |
| [2609.09425](https://arxiv.org/abs/2609.09425) Edu-QuRating | scorer multidimensional: ~1–1,6 pp num 1B, **sem sementes, 2.300 GPU-h, inglês** | só a ideia (3–4 rubricas simples) — a receita não |

**Resultado que ainda não se aplica:** [2609.09081](https://arxiv.org/abs/2609.09081) — má cobertura
de domínio no mid-training **não é corrigida por SFT** (5 sementes, permutação) — mas os autores
dizem que o efeito exige folga de capacidade **ausente em ≤1,5B**. Fica para um Bee maior.

### 2.6 Estágios V e A — e um aviso para o áudio em português

| artigo | o que afirma | uso |
|---|---|---|
| ⭐ [2609.04242](https://arxiv.org/abs/2609.04242) | VLM congelado + Whisper, **sem treinar nada**, empata ou supera modelos Omni nativos em fala e preserva melhor as capacidades originais | **é o baseline que o estágio A tem de bater** antes de qualquer projetor de áudio: Whisper na CPU + transcrição injetada, 20–50 exemplos |
| [2609.05871](https://arxiv.org/abs/2609.05871) | quando o LM multimodal erra, a informação acústica **sobrevive até a última camada**; corrigir 10–26 mil parâmetros do head recupera **30–42 pp** | quando houver estágio A: auditar o *readout*, não só o encoder |
| [2609.04637](https://arxiv.org/abs/2609.04637) | substituir o áudio por silêncio/ruído prova se o modelo usa a evidência acústica | gate de fundamentação para o estágio A |
| ⚠️ [2609.09554](https://arxiv.org/abs/2609.09554) BuzzASR | Whisper afinado por idioma bate o multilíngue em 77/102 idiomas — **mas para português o fine-tuning PIOROU o CER**, porque o Whisper já é forte em PT | **não afinar o Whisper para PT.** Só o truque de warm-start do tokenizador transfere |

---

## 3. Confirmações externas das lições do Bee

O valor destas não é novidade; é **um segundo aparato chegando ao mesmo número**:

| lição do Bee | artigo | como confirma |
|---|---|---|
| §2e a régua tem de parar | 2609.03966 | 0% ↔ 96% trocando só o adaptador |
| §2k pass@k não é entregável | 2609.09245 | teorema: acima de n é um intervalo |
| decodificação restrita +10 pp | 2609.07370 | 0,5% de JSON cru abaixo de 2B |
| capacidades competem | 2609.03150 | cos de gradiente −0,002 dentro do mesmo adapter; mais rank piora |
| §2ab forma da classe negativa | 2609.04714 | o template fixo é a causa, por teste causal |
| §2f grade tem de cercar | 2609.03900 | +5,0 → −11,6 pp mudando o rank do baseline |
| §2n gabarito derivável do pedido | 2609.06124 | proveniência de argumento = 6,4 pp |
| loteria de string (E5) | 2609.08327 | 30–47% do ganho era anotação incompleta |
| §2y agregado esconde sinais | 2609.09218 | *double measurement confound* |
| o lote muda a geração | 2609.04748 | cache de prefixo muda 75% das trajetórias sob 4 bits |
| o ganho mora no decaimento (10,3%) | 2609.09116 | lei exata schedule × weight decay — ⚠️ só mostrada em SGD + ConvNet |
| fertilidade não prevê bpb | 2609.06898 | poda de vocabulário: <1,2% de tokens e **nunca mede um modelo** |

---

## 4. Contradições e avisos — o que este estudo diz para NÃO fazer

- 🔴 **Não assumir que o checkpoint final decaído é a melhor base para SFT** (2609.08966). Medir.
- 🔴 **Não sintetizar paráfrases para o corpus** de um modelo ~1B (2609.04180): efeito nulo a negativo nessa escala.
- ⚠️ **Não afinar o Whisper para português** (2609.09554): piorou o CER.
- ⚠️ **Não fundir adapters sem a checagem de competição** (2609.07971): 4 de 5 pares do próprio autor reprovaram.
- ⚠️ **Não creditar ganho de seleção de ferramenta sem auditar equivalentes não anotados** (2609.08327): até inverte o sinal.
- ⚠️ **Não pontuar tradução de LLM sem passar o detector de ruído antes** (2609.11399): 3–100% de poluição.
- ⚠️ **Não confiar em "FLOPs economizados" sem medir tok/s** (2609.05275).

---

## 5. Os cinco NÃO ADOTAR, com o motivo

| artigo | por quê |
|---|---|
| 2609.06172 AutoUVM | memória de inferência em oversubscription — o Bee cabe na GPU |
| 2609.06898 DH-BPE | <1,2% de tokens e nunca treina modelo |
| 2609.07370 CPU benchmark de tool-calling | confirma a decodificação restrita; sem alavanca nova |
| 2609.07666 MpSub | sem gradiente, só classificação com 100 exemplos |
| 2609.11356 kernels bit a bit | datacenter, RL distribuído; a triagem tinha ligado ao "lote muda a geração" e o texto não sustenta |

---

## 6. O que fazer primeiro — cinco gates, todos abaixo de US$ 5

1. **Muon × AdamW (× Musec)** no Bee-150M, 2 sementes — decide o otimizador do próximo pré-treino.
2. **Densidade de solução nos marcos do Bee-1G** — decide de qual checkpoint parte o pós-treino. GPU zero.
3. **Catálogo perturbado + recusa sem template** no corpus agêntico, 3 sementes — ataca §2u e §2ab pelo mecanismo.
4. **Auditorias de avaliação**: sondas correta/vazia/fabricada no scorer; equivalentes não anotados no holdout de 747; bpb por fonte.
5. **Autocontaminação do FineWeb-2** nos 7 idiomas — antes do próximo corpus.

Nenhum deles toca o run atual, que segue no platô rumo ao `marco_6B`.

---

## Apêndice — os 57, um a um (gerado do artefato, não transcrito)

### ADOTAR (2)

**[2609.03966](https://arxiv.org/abs/2609.03966) — Interface-Induced Trajectory Censoring**  
A taxa de chamada de ferramenta medida não é propriedade do modelo, é do stack modelo+template+parser - o mesmo modelo mede 0% ou 96% só trocando o adaptador, a mesma classe de bug de regua-tem-de-parar, agora generalizada com um preflight check de 98 linhas pronto pra copiar.  
*rigor:* sementes · ≤3B · código  
*bandeiras:* autor único (Wenbo Wang), preprint não revisado por pares - mas com repro público, preregistro de predições e correção honesta de erratas; a maior parte dos números de 'reparo' (repair loop, gaps residuais) NÃO sobrevive à correção de Bonferroni - só a EXISTÊNCIA da censura por interface é robusta, a MAGNITUDE do ganho ao consertar é incerta; a afirmação de que a subcontagem cresce com a escala é escopada pelo próprio autor como 'só dentro da família Qwen2.5-Coder + um adaptador específico', não como lei geral

**[2609.09245](https://arxiv.org/abs/2609.09245) — What Fixed-Rollout pass@k Evaluations Can Identify**  
Prova matematicamente que pass@k para k acima do n de fato amostrado não tem solução única — só um intervalo, que pode variar por milhares de vezes — o que endossa a regra que o Bee já segue de nunca extrapolar além do que foi realmente sorteado.  
*rigor:* sementes · **só >3B** · sem código  
*bandeiras:* Nenhum experimento em modelo pequeno ou pré-treino — é matemática pura aplicada a rollouts de Llama-3-8B/70B publicados por OUTRO paper (Brown et al. 2024); Código/scripts próprios prometidos só 'após publicação' (revisão anônima) — não estão públicos no momento desta leitura; os rollouts brutos usados (Monkey Business, hash de commit citado) já são públicos; O teorema vale só para o experimento pooled/random-task com completions condicionalmente iid; amostragem adaptativa (mais amostras em tarefas difíceis) ou completions correlacionadas são modelos de observação diferentes, fora do escopo


### TESTAR (37)

**[2609.02899](https://arxiv.org/abs/2609.02899) — Contamination Inflates Scores but Rarely Reorders Large Language Model Leaderboards**  
Contaminação eleva o score absoluto mas raramente reordena o ranking (correlação 0,997); só contaminação DIFERENCIAL (rara: 3 de 188 casos) distorce comparações — uma lente barata para reinterpretar o próprio achado do Bee de 56% de contaminação de holdout, nunca testada abaixo de 7B.  
*rigor:* sementes · **só >3B** · código  
*gate:* Gerar paráfrases (via LLM, custo ~US$1) de 50-100 itens do holdout agêntico/SFT já usado em alguma comparação pareada do Bee; medir o gap original-menos-paráfrase nos 2 checkpoints/adapters sob comparação. Se o gap for igual nos dois (uniforme), a decisão pareada já tomada continua válida apesar da contaminação; se diferir, a decisão está em risco. Custo ≤US$5, ≤2h.  
*bandeiras:* calibração e modelos testados são todos ≥7B, nada na escala do Bee; reanálise de dados públicos de terceiros, nenhuma medição em modelo próprio dos autores; não toca pré-treino, tokenizador ou dados — é só metodologia de avaliação/contaminação

**[2609.03150](https://arxiv.org/abs/2609.03150) — Routing Is Not Enough: Diagnosing Intra-Adapter Subspace Contention in MoE+LoRA Fine-Tuning**  
Mesmo quando o roteamento do MoE separa quase perfeitamente os domínios (Jaccard 0,056), os gradientes de tarefas diferentes continuam quase ortogonais dentro do MESMO adapter LoRA compartilhado (cosseno -0,002) — confirma por outro caminho arquitetural que capacidades competem quando dividem um adapter, e mostra que aumentar o rank compartilhado (DR-LoRA) piora em vez de ajudar, mas a solução proposta (sub-adapter dentro de experts) não existe fora de MoE.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Medir o cosseno do gradiente do adapter entre duas capacidades que já competem no 350M (ex.: chamada de ferramenta vs. resumo), reusando os checkpoints e um backward extra por domínio — custo ~zero, minutos. Se o cosseno sair fortemente negativo/ortogonal como no paper, então prototipar (≤US$5, ≤2h) um branch LoRA extra com gate escalar por token (análogo à Eq. 1 do paper, sem router de MoE) num único ponto de conflito conhecido, e comparar bpb/acurácia-alvo contra manter adapters separados.  
*bandeiras:* só demonstrado em MoE (Phi-tiny-MoE 3,8B total, OLMoE 7B total) — Bee é denso, sem experts; treino curto (3.000 passos); os autores avisam que perplexidade absoluta NÃO é comparável a modelo convergido; pass@1 em HumanEval ficou perto de zero nessa escala — sinal principal é perplexidade, não tarefa executável; código do SpawnLoRA 'será liberado após aceitação' — não estava público no momento do artigo

**[2609.03350](https://arxiv.org/abs/2609.03350) — From Zero to Hero: An Open LLM Ecosystem for Armenian**  
Ecossistema aberto para armênio mostra que corpora multilíngues populares (inclusive o FineWeb-2, com autocontaminação treino/teste) inflam avaliação e que dado STEM verificado reverte esquecimento catastrófico em CPT — mas o regime (adaptar um LLM grande pronto) não é o do Bee, que treina do zero; só a checagem de contaminação transfere direto.  
*rigor:* sementes · ≤3B · código  
*gate:* Rodar o scanner de n-gram de decontaminação (o Bee já tem um) do holdout multilíngue do Bee-1G contra os splits de treino do FineWeb-2, nas línguas onde ele é fonte. Custo ~0 (CPU). Piso: se >3% dos itens do holdout colidirem, tratar como vazamento e reconstruir aquele pedaço do holdout.  
*bandeiras:* domínio é CPT de modelo grande já pronto (~4B efetivos), não pré-treino do zero — a maior parte do artigo está fora do regime do Bee; assume que o Bee-1G usa FineWeb-2 como fonte não-PT; não confirmado nesta leitura; achado de STEM revertendo esquecimento é sobre esquecimento CATASTRÓFICO em CPT, mecanismo diferente da competição de capacidades que o Bee já mediu em SFT

**[2609.03807](https://arxiv.org/abs/2609.03807) — Almost Free State Prediction Separation**  
Um 'pause token grátis' — um segundo stream que só lê o cache K/V do stream principal sem escrever nada, então não custa nada na inferência — ganhou 0.028 nats de CE num modelo de 1B (a mesma escala do Bee-1G) por ~33% mais tempo de treino aplicado só na cauda do run, mas foi medido com 1 única semente; vale um teste barato e com múltiplas sementes num modelo pequeno do Bee antes de investir na engenharia.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Implementar o stream de 'pausa livre' (sem as otimizações de kernel do artigo — aceitar throughput pior) num modelo pequeno tipo Bee-150M, ou uma fatia curta do treino do Bee-1G/350M: continuar um checkpoint existente por um orçamento curto de tokens (algumas centenas de milhões), faseando a pausa nos últimos ~30-40% desse orçamento, e comparar bpb no holdout verificado do Bee contra um controle de mesmo orçamento total de tokens/compute. Métrica: delta de bpb; piso: o efeito tem de superar o ruído de semente já medido pelo Bee para bpb (rodar 2-3 sementes de cada lado, não 1 como o artigo). Custo estimado: poucos dólares, poucas horas na RTX 5090, por ser modelo/orçamento pequenos.  
*bandeiras:* o próprio artigo admite: 'limited to a single scale (1B) with a single primary seed' — sem variância nenhuma, só a alegação (não medida) de que pré-treino é 'robusto o bastante'; as otimizações de throughput (FlashAttention-4, B200) não são portáveis 1:1 para RTX 5090/5070 — o custo real de 1.33x pode ser maior no hardware do Bee até reimplementar os truques; maior parte do ganho exige ~15B tokens de fase de pausa; o orçamento total do Bee-1G é 20B — a janela de cauda disponível pode ser justa; dado de pré-treino é proprietário (Phi-4-derived), não público; acurácia por tarefa individual (lm-eval) fica dentro do intervalo de confiança de 95% — o sinal downstream só aparece nas métricas agregadas (DCLM CORE, BPB), não tarefa a tarefa

**[2609.03900](https://arxiv.org/abs/2609.03900) — Beyond Endpoint Scores: Time- and Capacity-Conditioned Evaluation of Continual Knowledge Updating**  
Comparar hierarquia periódica contra replay LoRA usando só rank-8 inverte de +5,0 pp para -11,6 pp ao subir para rank-72 (Qwen2.5-1.5B, 3 sementes) — reforça, com números, que nenhuma comparação de método deve confiar em um único ponto de capacidade do baseline, exatamente a lição que o Bee já aplica a LR.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Reavaliar alguma comparação já publicada do Bee do tipo 'adapter LoRA vence full FT' (Bee-350M) treinando o mesmo adapter em 2-3 ranks adicionais (ex.: metade e o dobro do rank usado) nas mesmas tarefas, e conferir se a vantagem do adapter sobrevive fora do rank único testado. SFT no 350M já custou ~US$1,20/rodada segundo as memórias do Bee; 2-3 ranks extras cabem em US$5 e poucas horas.  
*bandeiras:* código/dado prometido apenas como 'repositório acompanhando o preprint', ainda não confirmado disponível; domínio é continual knowledge editing, fora do roadmap atual do Bee; pontos intermediários do sweep de rank em Llama são semente única, e Qwen não testou ranks intermediários nem rank-72 em 3B

**[2609.04184](https://arxiv.org/abs/2609.04184) — Toward Frontier-Quality Declarative UI Generation at Small-Model Cost**  
SFT com dado aumentado que embaralha ordem, remove itens não usados e renomeia ~20% dos nomes do catálogo (Perturbed-catalog) quase dobra a validade de binding de argumento (50,8%->92,6%) e generaliza melhor para catálogos nunca vistos do que treinar sempre com o catálogo fixo — receita diretamente portável para o SFT agêntico do Bee, que já mediu o mesmo tipo de atalho superficial por posição/tamanho de catálogo.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Aplicar a augmentação Perturbed-catalog (embaralhar ordem + remover ferramentas não usadas do prompt + renomear ~20% dos nomes, de forma consistente entre prompt e alvo) no corpus agêntico já existente do Bee, retreinar o LoRA já usado (~US$1-5, poucas horas, reaproveitando a infra de SFT do 350M), e remedir seleção com catálogo nunca visto (OOD) e seleção em catálogo grande (15+ ferramentas) contra o baseline atual. Piso: ganho ≥5pp em acurácia de seleção OOD ou em validade de binding de argumento já justifica adotar.  
*bandeiras:* domínio é geração de UI declarativa, não tool-calling — a transferência é por analogia estrutural (catálogo -> seleção -> binding), não é o mesmo problema; juízes LLM têm concordância humana fraca nas sub-dimensões semânticas: 'task satisfaction' 0,25 e 'component appropriateness' 0,08 (quase tão baixa quanto a concordância entre humanos, 0,18, no segundo caso) — a métrica de qualidade semântica é a mais frágil do artigo; catálogo maior sempre ajudou aqui, mas não há uma condição de 'exatamente 1 item correto entre muitos similares', que é o regime onde o Bee mediu piora; não menciona liberação de código nem dos apps React usados (são internos/proprietários)

**[2609.04242](https://arxiv.org/abs/2609.04242) — Training-Free Speech-Centric Omni Understanding with Frozen VLMs**  
Um VLM congelado + Whisper, sem treinar nada, empata ou supera modelos Omni nativos em tarefas de fala e ainda preserva melhor as capacidades originais do VLM (visão, código, matemática) — só perde quando a tarefa exige som não-verbal (música, ambiente, tom de voz).  
*rigor:* **sem sementes** · **só >3B** · sem código  
*gate:* Antes de investir em treinar projetor de áudio no Bee-1G: rodar Whisper (frozen, CPU) em ~20-50 exemplos de instrução falada/pergunta sobre áudio, inserir a transcrição como texto no prompt do Bee-1G (zero treino, zero projetor) e medir se a tarefa-alvo tem acerto razoável nesse baseline antes de pagar o custo de treinar encoder+projetor. Custo: só CPU para Whisper, menos de 1h, ~US$0.  
*bandeiras:* só testado em VLMs >=3B parâmetros, nunca em modelo ~1B; toolkit de avaliação (OmniEvalKit) 'será liberado como open-source' — promessa, não confirmado no texto; não reporta sementes/variância — resultados parecem de execução única por benchmark

**[2609.04565](https://arxiv.org/abs/2609.04565) — Extremely Sparse Supervision Incentivizes Reasoning Ability**  
Supervisionar so' 1-2 tokens por trajetoria iguala ou supera OPD denso em 9 configuracoes Qwen3 porque o tensor de logits [B,T,V] vira [B,V] - o mesmo tensor que hoje limita o microbatch de SFT do Bee na RTX 5070, mas o metodo em si (OPD com professor de logprob aberta) nao roda na infra atual do Bee.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Duas etapas, reaproveitando um adapter LoRA agentico ja treinado. (1) Barato/so' qualidade: no mesmo treino atual, mascarar a perda para supervisionar so' o token de maior perda por exemplo (~mintok) vs. o baseline denso; comparar taxa de execucao no holdout agentico existente (n>=500, 3 sementes, piso de semente conhecido ~4-7 pp por corpus-templado-n-efetivo/e19). Se a execucao nao cair alem do piso de ruido, (2) implementar o 'gather-then-project' (aplicar o head do LM so' nas posicoes escolhidas) e medir o pico de VRAM antes/depois - o teste decide se da' pra dobrar o micro-batch atual (2->4) na RTX 5070 8GB sem perder qualidade.  
*bandeiras:* requer logprob do professor token a token com vocabulario compartilhado - nao funciona com o professor de API fechada que o Bee usa hoje para distilar; so' funciona em modelos que ja fazem OPD denso com sucesso (o proprio paper reporta falha em Gemma3/4 e Mistral3 sem SFT previo) - nao e' garantido que 'sparsificar a perda' generalize para SFT puro sem RL; numeros principais (avg@8 nas Tabelas 3-5) sao estimativa pontual, sem IC nem sementes de treino repetidas - so' as curvas pass@k (Figuras) tem IC, e esse IC e' de amostragem de avaliacao (n=256), nao de semente de treino; sem codigo ou dado publico liberado

**[2609.04577](https://arxiv.org/abs/2609.04577) — Optimizer Memory Schedules for Outscaling the Overtraining Axis**  
Muon e SOAP dão de 1,3x a 1,9x de eficiência de token sobre AdamW bem na faixa de overtraining em que o Bee já opera (1x-8x), e trocar de otimizador é provavelmente o teste de maior payoff do lote.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Rodar par AdamW vs Muon a partir da arquitetura do Bee-150M por ~1-2B tokens (~US$3-5, <2h numa GPU alugada), 2 sementes por braço, weight decay escalado por sqrt(OT) como no artigo. Adotar Muon como default se o ganho em bpb bater ou passar o multiplicador de ~1,3x-1,4x em tokens equivalentes (piso: usar o próprio ruído de semente medido no Bee, §2m/§2x, como referência de significância).  
*bandeiras:* TPU (Google TPU Research Cloud/MIT CSAIL), não GPU de consumo — achado é algorítmico mas a infra não é a do Bee; 1 seed por configuração; o próprio artigo admite não estimar variância entre inicializações; ADANA precisa de 4+ hiperparâmetros extra bem calibrados para funcionar (κ=0,85, δ=8, g3=8, cooldown); não há código ou dado público mencionado

**[2609.04582](https://arxiv.org/abs/2609.04582) — When Do Internal Probes Beat Reading the Answer? Miscalibrated Readouts and Behavior-Concealed Knowledge in Language Models**  
Um modelo de 0,6B que sempre responde SIM já 'sabe' a resposta certa nos próprios logits (AUC 0,887) — o defeito é um limiar deslocado +4,6σ, corrigível com 1 parâmetro sem retreinar, e uma hipótese barata de testar no colapso chamar/recusar que o Bee já documentou.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Em um checkpoint agêntico já treinado do Bee-350M, medir a margem de logit entre o token de chamada de ferramenta e o de recusa nos casos do holdout, e comparar a AUC dessa margem com a acurácia comportamental (chamar/recusar). Se a margem discriminar bem mais do que o comportamento, ajustar um limiar por validação cruzada leave-one-out e medir se a acurácia melhora sem retreinar. Custo: ~zero GPU, só inferência sobre checkpoint e dado já existentes, <2h.  
*bandeiras:* nenhuma medição em pré-treino/tokenizador/dados — é só um mecanismo de decodificação pós-treino; código prometido 'no suplemento', sem link de repositório público no corpo do texto; domínios de teste são sintéticos (lógica e labirinto), não validado em tarefa agêntica real

**[2609.04714](https://arxiv.org/abs/2609.04714) — Refuse without Refusal: A Structural Analysis of Safety-Tuning Responses for Reducing False Refusals in Language Models**  
A frase-padrao fixa de recusa - nao o conteudo nem a decisao de recusar - e' a causa comprovada (teste causal por palavra-chave) da generalizacao excessiva de recusa, e a mesma decomposicao (recusa variavel e especifica em vez de template fixo) e' testavel barato na classe negativa agentica do Bee.  
*rigor:* **sem sementes** · **só >3B** · código  
*gate:* Reescrever as respostas negativas (recusa por falta de ferramenta) do corpus agentico do Bee: manter a decisao de nao chamar ferramenta, remover a frase-padrao fixa, e gerar uma justificativa especifica do pedido (via o mesmo professor gratis do NVIDIA build ja' usado - custo ~US$0) para uma amostra de ~500-1000 exemplos negativos. Retreinar o mesmo LoRA agentico so' trocando essa fatia (~US$1-2, ~1h, reaproveitando a receita de e19/e13). Metrica: taxa de over-calling E taxa de execucao correta no holdout agentico existente (n>=500, 3 sementes). Piso: mudanca so' conta se over-calling cair E execucao nao cair mais que o piso de ruido de semente (~4-7 pp, corpus-templado-n-efetivo).  
*bandeiras:* testado so' em modelos base 7-9B (Llama-3.1-8B, Mistral-7B, Gemma-2-9B, Qwen2.5-7B) - nada abaixo de 3B, mecanismo nao verificado na escala do Bee; dominio e' seguranca/recusa geral, nao tool-calling - a transferencia para 'recusa por falta de ferramenta' e' uma analogia, nao replicacao direta; sem sementes de treino nem variancia entre reruns reportada (so' um seed fixo=807 para reprodutibilidade, nao para medir variancia); codigo publico em github.com/mz-kim/RwR, mas nao verificado por este leitor

**[2609.04819](https://arxiv.org/abs/2609.04819) — A Systematic Comparison of Multilingual Interpretability Methods Reveals Anisotropy-Driven Failures**  
Das 4 métricas usadas na literatura para medir 'compartilhamento cross-lingual' em LLMs, só ILO sobrevive a controles de tamanho/família/tarefa (rho=0,90); as outras, inclusive a mais popular (CKA), medem majoritariamente o cone anisotrópico do espaço de representação, não compartilhamento real.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Calcular ILO + diagnósticos de anisotropia (n_pca, cosseno aleatório médio) num checkpoint atual do Bee-1G, usando ~1-2 mil tokens por idioma do FLORES-200 (ou fatia do próprio holdout) nos 8 idiomas do Bee. Custo: zero (CPU, sem GPU), tempo < 2h de código+execução. Decide se vale manter como diagnóstico contínuo nos marcos de escala, comparando quais dos 8 idiomas ficam isolados/compartilhados.  
*bandeiras:* resultados são correlacionais, não causais - a própria seção de Limitations admite isso; amostra efetiva é ~5 famílias independentes (arquitetura/dado/tokenizador correlacionados dentro de família), não 21 modelos; não há release de código/dado explícito no texto lido; SmolLM3 representado por um único tamanho (3B); ranking de confiabilidade das métricas pode não generalizar para anisotropia fora do que foi observado

**[2609.05099](https://arxiv.org/abs/2609.05099) — Improving Language Identification for Code-Switched Utterances with Integer Linear Programming**  
Um classificador de idioma reformulado como programação linear inteira quase dobra a detecção de code-switching (EM 0,54->0,71, p~1e-302) rodando só em CPU e cobrindo português nativamente — uma ferramenta de auditoria de pureza de corpus praticamente grátis para o Bee testar, mas nunca ligada a nenhum efeito medido em treino de LM.  
*rigor:* sementes · ≤3B · código  
*gate:* Rodar ILP4LID (código aberto, github.com/jradola/ILP4LID, só CPU) sobre uma amostra de ~1.000-5.000 documentos de cada fatia de idioma do corpus do Bee-1G (ou da próxima expansão multilíngue); medir a fração rotulada como monolíngue pelo LID original que o ILP4LID marca como mistura de idiomas, e comparar a composição dos idiomas 'vazando' com os idiomas já difíceis na mistura ótima (CJK, árabe). Custo: ~US$0 (CPU local), 1-2h. Decide se vale filtrar o corpus por isso antes do próximo treino grande.  
*bandeiras:* não mede impacto em treino de LM nenhum — só EM/F1 intrínseco de LID, em benchmarks de mídia social/conversação, não em corpus web/livros como o do Bee; os 10 pares testados não incluem português; cobertura de 'por' no LID de base existe mas nunca foi validada para code-switching; usa o solver comercial Gurobi no experimento principal (licença acadêmica grátis), mas os próprios autores confirmam que HiGHS (open-source, via Pyomo) também roda — sem bloqueio real de custo; ganhos grandes de EM vêm de benchmarks de mídia social bagunçada (Twitter, romanização informal); pode não generalizar para o tipo de corpus mais limpo (web/livros/CC) que alimenta o pré-treino do Bee

**[2609.05198](https://arxiv.org/abs/2609.05198) — What Matters in On-Policy Distillation? A Perspective on Data Efficiency and Data Selection**  
Em OPD, 8 exemplos dificeis (ate' 'insoluveis') batem 17 mil exemplos porque o ganho vem do CoT longo do professor, nao de entropia ou volume - mecanismo especifico de OPD que o Bee nao tem, mas a ideia de curar por dificuldade em vez de volume e' barata de testar dentro do SFT que o Bee ja faz.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Usando o avaliador agentico existente do Bee, ranquear ~200-500 exemplos do pool de treino (nao holdout) pela taxa de acerto do Bee-350M/1G atual em k=8 rollouts; separar 'dificeis' (0% de acerto) de 'faceis' (alta taxa). LoRA-treinar dois adapters do mesmo tamanho de dado (N=8 a N=64, espelhando a Tabela 2 do paper): um so' com os dificeis, outro com uma amostra aleatoria/facil do mesmo N. Comparar taxa de execucao no holdout agentico fixo (n>=500, 3 sementes). Custo ~US$1-2, ~1-2h (reaproveita a receita de LoRA ja' usada em e13/e19). Piso: so' conta como efeito real se a diferenca exceder o ruido de semente medido (~4-7 pp).  
*bandeiras:* mecanismo causal identificado pelos autores (KL reversa on-policy + exposicao a CoT longo do professor) e' especifico de OPD - testar em SFT classico do Bee e' uma hipotese diferente, nao uma replicacao; dominio e' matematica verificavel com sinal de acerto/erro limpo; tool-calling do Bee tem um sinal parecido (execucao correta) mas resumo/atendimento nao tem uma nocao de 'dificuldade' tao limpa; cluster 8xH800 80GB - fora do orcamento do Bee, mas o proprio achado e' sobre REDUZIR dado, nao sobre precisar de mais GPU; sem codigo ou dado proprio liberado (usam o framework aberto verl, mas nao publicam os exemplos/indices de forma citavel alem do paper); sem sementes de treino repetidas - o desvio-padrao mostrado (Figura 3) e' entre EXEMPLOS diferentes da mesma categoria, nao entre reruns do mesmo treino

**[2609.05275](https://arxiv.org/abs/2609.05275) — Don't Drop Dropout: Optimizing Layer Sparsity for Efficient LLM Training and Inference**  
Layer dropout crescente-por-camada + decrescente-no-tempo corta até 25% dos FLOPs de treino mantendo ou até melhorando a loss em modelos de 271M-8,2B (Cerebras, sem sementes múltiplas) — vale testar num mini-run pareado no Bee, porque o ganho de FLOPs só vira economia real se a implementação de fato pular o cálculo numa GPU única.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Mini-run pareado (~1-2h, <US$5) no próximo pré-treino do Bee: 2 branches no MESMO orçamento de tokens (ajustando os passos pela fração de FLOPs economizada), um denso e um com layer dropout per-batch (mais fácil de implementar que per-sequência), taxa crescente por camada (ILD, 0→0,2) + decrescente no tempo (DTS). Medir (a) se o tempo de parede por passo cai ~proporcional à taxa média de dropout — evidência de que a implementação economiza compute de verdade, não só simula — e (b) se o bpb no holdout pareado não piora além do piso de ruído de semente já medido pelo Bee.  
*bandeiras:* Hardware Cerebras CS-3 (wafer-scale), não GPU — a economia de FLOPs em wall-clock não foi verificada em GPU única; Nenhuma menção a múltiplas sementes ou variância em nenhum dos 2400+ experimentos; Métrica é loss de validação do corpus interno deles, não bpb comparável ao holdout do Bee; A variante com melhor loss (per-sequência) exige gather/scatter não-trivial em GPU; a fácil de implementar (per-batch) é a pior das duas em qualidade; Sem código ou dados públicos

**[2609.05766](https://arxiv.org/abs/2609.05766) — Data Scout: Targeted Web Crawling for Domain-Specific Pretraining Corpora**  
Crawling direcionado por taxonomia de LLM + triagem por subdomínio acha conteúdo real 70-82x mais denso que filtrar CommonCrawl/RedPajama, com 63% inédito nos crawls genéricos — método plausível (não testado no artigo) para atacar o déficit de 13-53x de dado não-PT que o Bee-1G já mediu, trocando o classificador de matemática por um identificador de idioma.  
*rigor:* **sem sementes** · ≤3B · código  
*gate:* Piloto grátis (cota diária da Google Programmable Search, 100 buscas/dia): para 1 idioma pobre do Bee-1G (árabe ou japonês), um LLM gratuito (NVIDIA build free-tier, já em uso no Bee) gera ~50-80 queries no idioma-alvo cobrindo tópicos variados; rodar GlotLID nas páginas retornadas; medir % que passa em pureza de idioma+tamanho mínimo e % de hosts inéditos frente às fontes já usadas pelo Bee. Custo ~US$0, ~2h. Piso: só compensa escalar com API paga se aproveitamento >=10% (ordem de grandeza do 21,9%/51,9% do artigo, não os 0,3-1,3% de filtrar arquivo genérico) e maioria dos hosts inédita.  
*bandeiras:* domínio original testado é TÓPICO (matemática/astronomia), não IDIOMA — adaptar para 'idioma como domínio' é extrapolação minha, não testada no artigo; requer orçamento de API de busca paga para escalar além da cota grátis; validação downstream (GSM8k) é CPT de modelo pronto de 3B, não pré-treino do zero

**[2609.05885](https://arxiv.org/abs/2609.05885) — One Rate Is Not Enough: Adaptive Anisotropic Learning Rates for LoRA Fine-Tuning**  
Redistribuir o LR entre os componentes rank-one do LoRA (via velocity+SNR do Adam, sem parâmetros extras) ganha 1-4 pp e sobretudo torna o LoRA muito mais robusto à escolha de LR, mas só foi medido em modelos >=7B, nunca no regime de escala do Bee.  
*rigor:* sementes · **só >3B** · sem código  
*gate:* Implementar só o termo de velocity (Tab.5 do artigo mostra que sozinho já ganha sobre uniforme) como wrapper pós-passo no treino LoRA de uma capacidade do Bee (ex. agêntico), com 3 sementes, mesmos passos e mesmo dado da rodada já existente. Adotar se o ganho na métrica de execução exceder o piso de ruído de semente que o Bee já mede para aquele holdout. Custo: o de re-rodar um SFT já pago, só trocando o optimizer step — sem custo de dado novo.  
*bandeiras:* nenhum modelo abaixo de 7B testado; nenhum experimento multilíngue; não encontrei repositório de código próprio (só cita a biblioteca PEFT do HuggingFace); ganho de 1-4 pp pode estar dentro do piso de ruído de semente que o Bee mede em holdouts pequenos

**[2609.06124](https://arxiv.org/abs/2609.06124) — SAP: State-Guided Data Synthesis with Argument Provenance for Multi-Turn Tool Use**  
SAP marca cada argumento de tool-call com sua origem causal já na síntese (turno anterior, usuário, fallback), e só isso vale 6,4 pp de BFCL quando removido - confirma por outro ângulo o que o Bee já suspeitava em §2n, mas o pipeline caro (Gemini-3.1/3 Pro, Qwen3-235B, full-FT em 8 GPUs) só transfere na ideia, não no método.  
*rigor:* **sem sementes** · **só >3B** · código  
*gate:* Gerar ~200 trajetórias multi-turno com tag de proveniência explícita, usando o teacher barato/gratuito já usado no SFT do Bee, no mesmo toolset do corpus atual; treinar um LoRA idêntico ao já existente trocando só essa fatia do corpus; medir a taxa de argumento fabricado/obsoleto/mal-copiado num probe de dependência entre turnos (reaproveitando a lógica do holdout multi-turno atual) contra o LoRA de controle, com pelo menos 2 sementes. Piso: a taxa de erro de argumento tem de cair além do ruído de semente já medido em §2m/§2x, não só empatar dentro dele. Custo estimado: menos de US$ 5, menos de 2 h (escala 150-350M já em uso no Bee).  
*bandeiras:* abstract diz 'altamente competitivo mesmo comparado a modelos muito maiores', mas no BFCL v4 especificamente SAP-4B (30,4) fica abaixo de 3 baselines de 8B (36,5 a 40,1) - só bate claramente os 8B no tau2-bench; nenhuma escala abaixo de 4B é avaliada, nem como baseline; pipeline de síntese depende de Gemini-3.1 Pro / Gemini-3 Pro / Qwen3-235B como agentes geradores - custo de API não reportado; sem sementes ou runs repetidos reportados - números parecem ser de single run; treino é SFT full-parameter em 8 GPUs de 80GB - não transfere ao regime de 1 GPU do Bee, só a síntese de dado transfere

**[2609.06652](https://arxiv.org/abs/2609.06652) — VidaForge: Open Research Infrastructure for Video Pretraining Data Recipes**  
Comparando receitas de dado de vídeo sob o mesmo orçamento, a de menor loss (treino ou validação) perdeu em benchmark downstream (VBench e SSv2) nas duas famílias de modelo testadas — lição transferível para o Bee validar a lei de mistura por uma métrica de capacidade, não só por bpb, embora nenhum número do artigo (vídeo) se aplique diretamente.  
*rigor:* sementes · ≤3B · código  
*gate:* Na próxima validação de mistura do Bee, reaproveitar 2-3 checkpoints já treinados para bpb e medir também 1 métrica de capacidade barata (ex. sonda de tradução ou perplexidade cruzada num idioma não-PT) nos mesmos checkpoints. Custo ~US$0 (sem treino novo). Piso: se a ordem de mérito por bpb bater com a ordem por capacidade dentro do piso de ruído de semente já medido pelo Bee, bpb sozinho basta; se divergir, capacidade passa a ser critério obrigatório nas próximas leis de mistura.  
*bandeiras:* domínio é vídeo (Wan2.1 difusão + V-JEPA SSL) — arquitetura e objetivo totalmente diferentes do LM causal do Bee; a infraestrutura em si (pipeline VidaForge) não é aplicável ao Bee; só a lição metodológica generaliza; 'Mixed' venceu com o DOBRO de clipes distintos sob o mesmo orçamento — o efeito pode ser 'mais dado único', confundido com 'menos filtro' no desenho do experimento

**[2609.07597](https://arxiv.org/abs/2609.07597) — Beyond the Matrix Sign: Quadratic Spectral Descent**  
QSD refina o Muon com curvatura (K-FAC + Frank-Wolfe) e rende +7-8% de tempo de parede em GPT-124M/350M — quase a escala exata do Bee — mas só compensa a complexidade depois de o Bee já estar usando Muon puro.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Só depois de o Muon básico estar rodando no Bee (gate do artigo 2609.04577): implementar QSD apenas nas matrizes de atenção/MLP de um Bee-150M, comparar 2-3 sementes QSD vs Muon puro por ~1-2B tokens (~US$3-5, <2h). Adotar só se a queda de loss exceder claramente a dispersão entre rodadas (o próprio artigo mede ~0,0006-0,0007 de ruído entre runs em 124M) e o overhead de tempo de parede numa GPU só ficar abaixo de ~10%.  
*bandeiras:* ganho de +7-8% de tempo de parede é incremental sobre o Muon, que o Bee ainda não usa — depende de uma adoção anterior; hiperparâmetros extras não triviais (τ, damping d, intervalo/EMA de refresh do K-FAC, calibração GGN) — engenharia real, não um drop-in; sem código público mencionado; 'seeds' não é o termo usado — são 3 'runs' por método; funcionalmente equivalente, mas o artigo não discute se variam a inicialização, a ordem de dados, ou ambos

**[2609.07699](https://arxiv.org/abs/2609.07699) — Fine PT-PT Web: A High-Quality 41 Billion Tokens Data Collection of the European Portuguese Web**  
Um pré-filtro de linha muito barato (remove linhas curtas e duplicadas ANTES dos filtros heurísticos padrão) resgatou 19% mais documentos sem perda de qualidade medida — mas validado numa única coleção, sem treino real e só com modelos prontos >=7B.  
*rigor:* **sem sementes** · **só >3B** · código  
*gate:* Rodar o filtro heurístico que o Bee já usa (ou o equivalente Gopher/FineWeb) sobre uma amostra de 50-100 mil documentos do corpus PT bruto, com e sem o pré-filtro de linha (remover linhas <10 chars alfabéticos + duplicadas dentro do doc) antes da heurística; medir delta de documentos/tokens retidos e o bpb de uma amostra dos documentos 'resgatados' sob o checkpoint atual do Bee. CPU apenas, <1h, ~US$0.  
*bandeiras:* efeito de +19% medido numa ÚNICA coleção de teste (FAWP21), não replicado nas outras 70; validação de qualidade usa só modelos prontos >=7B — nenhum modelo <3B treinado ou testado; sem ablação em treino real (bpb/perplexidade de um modelo treinado com vs sem o passo) — só proxy via contagem de docs e bpb de docs removidos/retidos por modelos externos; domínio específico (arquivo web de notícias/blogs PT-PT) pode não generalizar para outras fontes/idiomas

**[2609.07971](https://arxiv.org/abs/2609.07971) — MeRoTune: RoPE-Safe Merging with a Tunable Dial**  
Corrige a rotação RoPE com 7 mil escalares antes de fundir dois fine-tunes completos do mesmo checkpoint (nunca perde para TIES/DARE-TIES), mas só compensa quando uma checagem barata de 4 desigualdades confirma que as duas especialidades realmente não competem -- e dos 5 pares testados pelo autor, só 1 passou.  
*rigor:* **sem sementes** · ≤3B · código  
*gate:* Antes de treinar qualquer correção: aplicar a condição da eq. 7 (Δ_A>0, Δ_B>0, Γ_A<=0, Γ_B<=0) em duas capacidades já treinadas do Bee (ex. LoRA agêntico vs LoRA de resumo), medindo cada uma no holdout da outra -- custo zero de GPU, só inferência nos holdouts que já existem. Só se a condição passar, treinar a correção RoPE-commutant (milhares de parâmetros, menos de 1h numa GPU só) e comparar a métrica de cada capacidade no modelo fundido contra média ingênua de pesos no mesmo blend ratio; piso de decisão: o ganho tem de superar o piso de ruído de semente que o Bee já mede para aquele holdout.  
*bandeiras:* testado num único par de fine-tunes e uma única arquitetura (Qwen2.5-1.5B); um seed por configuração principal -- os próprios autores dizem não poder descartar que o resultado seja específico deste par ou desta rodada; exige fine-tunes de PARÂMETRO COMPLETO do mesmo checkpoint -- LoRA cru sem merge na base fica de fora; a coluna ARC-C fica dentro do próprio piso de ruído que os autores relatam

**[2609.08327](https://arxiv.org/abs/2609.08327) — Tool Retrievers Are Underestimated: Annotation Expansion Reveals True Capability**  
67,9% das sub-queries do benchmark tinham ferramenta equivalente não anotada, e isso incha 30-47% do ganho de fine-tuning relatado (chegando a inverter o sinal em Code) - mesma família de erro que o Bee já viu em e5 (loteria de string), agora na seleção/retrieval, e um risco real e barato de auditar no catálogo de 747 ferramentas do Bee.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* Nos casos de 'erro de seleção' já registrados no holdout de 747 ferramentas do Bee, reler manualmente (ou usar o teacher barato já em uso como juiz) uma amostra de 30-50 desses erros e checar se a ferramenta prevista pelo modelo é funcionalmente equivalente à referência mas não anotada como tal. Piso: se 15% ou mais dos 'erros' forem alternativas válidas, o número de seleção reportado está subestimado e precisa de reanotação ou de métrica corrigida. Custo: leitura manual, menos de 2h, ~US$0-2.  
*bandeiras:* verificação de equivalência é semântica (juízo de LLM: GPT-4o-mini + Claude-Sonnet-5), não por execução real - o próprio artigo admite que isso 'pode introduzir falsos positivos'; validação da própria ToolEX é só spot-check parcial de humanos - não relatam números exatos de precisão ou concordância entre revisores; sem link de código ou dado público no texto - não dá para reproduzir a pipeline exata; o efeito NÃO se generaliza igual em todo domínio: em SkillRet o ganho de fine-tuning é genuíno mesmo após correção - extrapolar o '30-47%' para o catálogo do Bee sem medir seria o mesmo erro de anotação rígida que o artigo denuncia

**[2609.08966](https://arxiv.org/abs/2609.08966) — Good Pretraining, Bad SFT: Checkpoint Quality Across the Training Stack**  
Num MoE de 30B, o checkpoint com melhor loss e benchmark de pré-treino (o que teve o LR decaído) virou o PIOR ponto de partida pra SFT por travar numa patologia de nunca parar de gerar que nem reajustar o LR do SFT conserta — achado de método relevante pra decidir qual marco do Bee-1G usar de base pro próximo pós-treino, mas medido em escala muito maior, sem sementes, e dominado por uma falha só.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*gate:* Nos marcos que o Bee-1G já vai salvar (ex. 15B ainda no platô vs 20B final decaído), medir densidade de solução: ~100 perturbações gaussianas pequenas (σ~0,005) nos pesos de cada checkpoint, fração que mantém ≥90% do escore num holdout fixo (bpb ou tarefa fixa). Se o platô tiver densidade nitidamente maior, rodar um SFT de sonda curto nos dois e comparar taxa de geração-sem-parar/repetição e a métrica-alvo. Custo: só inferência + 1 SFT curto, ordem de US$ 1-3, sem GPU nova de pré-treino.  
*bandeiras:* escala e custo muito acima do Bee: 30B total/3B ativos, 512 GPUs, 7,5T tokens de pré-treino — nada de 1 GPU de consumo; zero sementes — os próprios autores admitem 'one seed per setup' nas limitações; a reversão de ranking é um único experimento, não uma média; quase todo o efeito (0,113) some sem o HumanEval+: cai pra 0,016 — o achado é dominado por UMA patologia (repetição/não-parada), não perda de capacidade uniforme; causalidade explicitamente negada pelos próprios autores: densidade de solução é tratada como 'diagnóstico', não explicação causal; nenhuma declaração de código/dado/modelo aberto (usa framework interno da Aleph Alpha)

**[2609.09072](https://arxiv.org/abs/2609.09072) — ToolLoop: Closed-Loop Tool-Use Data Synthesis via Decomposed Generation and Dynamic Self-Feedback**  
Sintetizar dado agêntico verificando e corrigindo em 3 estágios (não só filtrando no fim) supera modelos treinados com 5x mais dado, e sintetizar sem NENHUMA verificação deixa o modelo pior do que se nunca tivesse passado por SFT.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*gate:* Gerar cerca de 200 exemplos novos do corpus agêntico do Bee com o loop de 3 estágios (ground truth de ferramentas -> query por derivação reversa -> chamada por derivação direta), usando o professor gratuito já disponível (NVIDIA build) como gerador e como verificador via regra determinística + validação de schema/AST (sem precisar de um segundo LLM pago); no máximo 3 correções por estágio. Comparar contra uma amostra do pipeline atual do Bee no mesmo n, medindo taxa de retry (proxy de erro oculto do pipeline atual) e acurácia de execução no holdout já existente. Custo: só chamadas ao professor gratuito, tempo estimado abaixo de 2h.  
*bandeiras:* modelo estudante é 4B, acima do teto de 3B do projeto Bee; sem sementes nem variância reportada — tudo single-run; sem release de código ou dataset encontrado no texto; verificador Qwen-Max é LLM forte e pago — custo não trivial de reproduzir em escala; gap em Live-Parallel_Multiple (79,17% vs 83,33% do APIGen) é 1 exemplo em split de só 24 casos — o próprio artigo avisa alta incerteza amostral aí

**[2609.09116](https://arxiv.org/abs/2609.09116) — When Does Scale-Invariant Optimization Become Unstable? An Exact Schedule Law with Weight Decay**  
Lei exata e bem verificada de como LR-schedule e weight decay interagem via a norma de blocos quase-escala-invariantes explica mecanicamente por que o decaimento é onde mora o ganho - mas os próprios autores avisam que o achado prático (pico de desempenho em B=1) não foi mostrado para AdamW+Transformer, só para SGD em ConvNet pequeno.  
*rigor:* sementes · ≤3B · código  
*gate:* Análise offline (CPU, ~US$0, menos de 2h): calcular o resíduo da recorrência (Phi_{t+1}/Phi_t vs B_t/(1+Phi_t^2*||g||^2)) e a fração de expansão para os blocos de projeção adjacentes ao RMSNorm em 5-10 checkpoints já salvos do Bee-350M ou Bee-1G. Piso: se o resíduo ficar em ~1e-2 ou pior (não ~1e-6 a 1e-7 como no artigo), a invariância de escala não se sustenta com o ganho aprendível do RMSNorm do Bee e a lei não se aplica; se ficar próximo, checar se B_t cruza 1 durante o decaimento do WSD, coincidindo com a queda de bpb do §2d.  
*bandeiras:* os próprios autores dizem explicitamente que o achado prático (pico de desempenho em B=1) NÃO deve ser esperado em treino AdamW+Transformer padrão - só validado com SGD em ConvNet/CIFAR-10; nos experimentos com GPT-2 só medem resíduo algébrico e fração de expansão, nunca loss ou perplexidade - nenhum ganho de desempenho de LM é mostrado; invariância de escala exata exige LayerNorm sem ganho aprendível; a maior parte dos blocos de um Llama/GPT padrão (incl. o ganho do RMSNorm) fica fora da cobertura do teorema, conforme o Apêndice F admite

**[2609.09163](https://arxiv.org/abs/2609.09163) — World-Time Compute with Verified Code World Models**  
Treinar um LoRA sobre MUITOS mundos sintéticos verificados (não um só) generaliza para mundos nunca vistos, inclusive num benchmark real (List Functions, +34 pp com 3 sementes) — mas só dentro de uma família de habilidade, e o número mais chamativo para modelo pequeno (0,5B, +29 pts) é semente única.  
*rigor:* sementes · ≤3B · código  
*gate:* Gerar uma família pequena (20-40) de 'mundos' de chamada de ferramenta verificados por execução — catálogos distintos mas da mesma família de habilidade (variações de um domínio tipo agenda/e-commerce já usado no avaliador agêntico do Bee) — treinar um LoRA no Bee-350M num subconjunto e medir acurácia de execução em catálogos retidos, com um controle de rótulo corrompido (mapeamento ferramenta-argumento embaralhado) ao lado. Métrica: execução correta no catálogo retido vs sob corrupção. Custo: GPU já disponível ao Bee, poucas horas, ~US$1-3.  
*bandeiras:* resultado mais citado no abstract (+29 pts em 0,5B) é semente ÚNICA — sem variância, o próprio artigo avisa isso nas Limitações; curva de escalonamento por nº de mundos (E76) roda só em 7B (não no modelo pequeno onde o efeito é maior) e parece semente única também; só funciona DENTRO de uma família de habilidade coerente — mundos heterogêneos e entre linguagens de programação dão transferência zero (é um limite real, não só uma ressalva); fine-tuning real roda em nuvem (1 A100), não é 100% 'laptop' como o framing sugere no início — só as comparações de fidelidade de dinâmica (sem treino) rodam local; 79 experimentos, sem correção para múltiplas comparações — os próprios autores marcam vários p-valores de fronteira (0,05-0,10) como exploratórios

**[2609.09218](https://arxiv.org/abs/2609.09218) — The Double Measurement Confound in Agent Benchmarks: De-Scaffolding, Ground-Truth Scoring, and Reliability Beyond the Mean**  
Dá nome formal e uma ferramenta de auditoria (BenchAudit) para exatamente o tipo de viés de avaliador agêntico que o Bee já flagrou sozinho em E5/E6 — vale rodar a bateria de sondas (correto/vazio/fabricado) no scorer atual do Bee antes de confiar em qualquer número agêntico novo.  
*rigor:* sementes · **só >3B** · código  
*gate:* Rodar a bateria de sondas do artigo (submissão correta, vazia e fabricada) pelos scorers agênticos atuais do Bee e conferir se a fabricada pontua perto da correta; e listar, no harness de tool-calling do Bee, quais decisões (parsing, retry, reparo de JSON) hoje são feitas por código em vez de pelo modelo. Custo: US$0, menos de 1h — é revisão de código + 3 casos de teste — decide se vale reescrever scorer/scaffold.  
*bandeiras:* Todos os modelos testados são >=7B (Qwen2.5-7B) ou frontier fechados — nenhum teste em escala Bee (<3B); ComtradeBench é benchmark dos próprios autores (2º lugar em competição AgentBeats Meta/HF), um domínio só (extração tipo trade-stats); generalização entre domínios é 'propriedade de design, ainda não empírica', nas palavras dos autores; B2 (o achado mais chamativo, do squeeze de cota) é exploratório e não pré-registrado, e o mesmo efeito é reproduzido por uma política SEM LLM (always-retry) com magnitude maior — o que aquilo mede é aritmética de cota, não decisão do modelo

**[2609.09425](https://arxiv.org/abs/2609.09425) — Edu-QuRating: Multi-Dimensional Educational Data Curation with Distilled Pairwise Judgements**  
Um scorer educacional multi-dimensional (não um escalar só), destilado de julgamento pareado de LLM, melhorou modestamente (~1-1,6 pp, tarefas concentradas, sem sementes) o pré-treino de um modelo de 1B em inglês — a receita custa 2300 GPU-horas e não serve em português, mas a ideia metodológica é barata de testar na escala do Bee.  
*rigor:* **sem sementes** · ≤3B · código  
*gate:* Definir 3-4 rubricas simples e relevantes ao corpus PT do Bee (ex.: densidade informativa, coerência/gramática, ausência de boilerplate residual, registro); gerar ~2-5 mil pares de julgamento com um juiz LLM barato/gratuito (Gemini Flash) sobre amostras dos diferentes níveis de qualidade já existentes no corpus do Bee; treinar um classificador pequeno (ou até só medir correlação, sem destilar) e comparar contra as faixas de qualidade atuais via bpb num held-out pequeno sob o checkpoint do Bee-1G. Custo: poucos dólares de API + CPU, minutos a poucas horas.  
*bandeiras:* custo do pipeline completo (pontuar 322M docs em 32x H200 por 72h, ~2300 GPU-horas) é ordens de magnitude acima do orçamento do Bee — só a metodologia, não a receita, é transferível; comparações de pré-treino são de UMA rodada por mistura, sem sementes — o próprio artigo admite isso como limitação, e o ganho agregado (~1-1,6 pp) é pequeno o bastante para ser ruído de rodada; rubricas e corpus são específicos de conteúdo educacional em inglês (FineWeb-Edu) — não há dado nem scorer em português; ganho concentrado em poucas tarefas (ARC-CF, HellaSwag); não há decomposição que isole se 'multi-dimensional' bate 'um escalar melhor', só bate o escalar do FineWeb-Edu original

**[2609.09476](https://arxiv.org/abs/2609.09476) — From Fixed Keys to Readable Schemas: Small Language Models for Vehicle Agent Function Calls**  
Em modelos de 270M a 1,7B, oferecer o catálogo como esquema no prompt (o que o Bee já faz) bate ter token fixo por função em toda situação onde o catálogo muda — token fixo acerta 0% em função nunca vista E ainda inventa a chamada quando uma função conhecida é removida do menu.  
*rigor:* sementes · ≤3B · sem código  
*gate:* No holdout agêntico que o Bee já tem, construir uns 50 a 100 casos onde uma ferramenta real do catálogo do Bee é removida só daquele exemplo (fica de fora do menu daquela instância mas continua existindo no catálogo geral) e o pedido do usuário pede exatamente essa função; medir taxa de over-trigger (o Bee chama mesmo assim) contra recusa correta. Custo: reaproveita holdout e infra existentes, sem GPU nova, menos de 1h.  
*bandeiras:* benchmark sintético, só inglês, só single-turn — sem diálogo nem estado veicular; domínio bem específico (funções de veículo Android Automotive), mas o achado é sobre REPRESENTAÇÃO (esquema vs token fixo), não sobre carro; sem release de código/dataset encontrado no texto (é paper de workshop, SLM-Agents, pode vir depois); latência e memória são device proxy em CPU Xeon, explicitamente não é hardware veicular real; Qwen3-1,7B usa LoRA enquanto os modelos menores usam fine-tuning completo — tratamento desigual entre grupos, mitigado por uma ablação mas não eliminado

**[2609.09691](https://arxiv.org/abs/2609.09691) — Looped GPT-BERT: Trading Parameters for Computation in Small Language Modeling**  
Compartilhar 4 camadas aplicadas 12 vezes (12,18M parâmetros) empata com modelos maiores em BLiMP/GLUE no BabyLM strict-small, mas é comparação de parâmetros e não de FLOPs, roda 100-1000x menor que o Bee com semente única, e a única fatia pareada por compute melhora sintaxe e memória mas derruba rastreio de entidade — vale um teste barato pelo ângulo de VRAM do otimizador, não adoção direta.  
*rigor:* **sem sementes** · ≤3B · código  
*gate:* No próximo teste de arquitetura do Bee (escala ~150M): treinar uma variante com metade das camadas físicas aplicadas 2x (MESMO número total de aplicações de camada, logo mesmo FLOPs) contra a arquitetura padrão, no mesmo orçamento de tokens, ~1-2h e <US$5. Medir bpb no holdout pareado E o pico de VRAM do otimizador. Piso: bpb não pode piorar além do piso de ruído de semente já medido pelo Bee; sucesso é VRAM do otimizador caindo proporcional às camadas físicas removidas sem piora de bpb. Rodar também uma sonda curta de retenção de estado, dado o colapso de Entity Tracking visto no artigo.  
*bandeiras:* Domínio é escassez extrema de DADO (BabyLM, 7,48M palavras), não escassez de COMPUTE/VRAM — a restrição real do Bee é a oposta; Escala 12-30M parâmetros, 10 épocas — 3-4 ordens de grandeza abaixo do Bee, e os PRÓPRIOS AUTORES pedem para NÃO extrapolar pra modelos maiores ou contextos maiores (seção 'Scope' das limitações); Semente única (42) em TODOS os experimentos — declarado pelos próprios autores como limitação explícita; A comparação principal do artigo (12,18M vs 29,9M/31M/124M) NÃO é pareada por FLOPs — o próprio artigo admite isso ('this is a parameter-efficiency study, not a FLOP-matched comparison'); Entity Tracking (rastreio de estado) colapsa com looping — risco direto pra capacidade agêntica

**[2609.10357](https://arxiv.org/abs/2609.10357) — A Later Test Set Is Not a New Domain: Pretraining Familiarity Survives a Contamination-Free Hold-Out**  
Em forecasting de séries temporais, um holdout sem contaminação por data ainda favorece o modelo no domínio que compõe seu corpus de pretreino (TimesFM ganha 28% a mais de MASE bem no domínio que é a maior fatia do próprio corpus) — um alerta de que o dedup por fingerprint do Bee não pegaria esse tipo de viés.  
*rigor:* sementes · ≤3B · código  
*gate:* Sobre o holdout já verificado do Bee: quebrar o bpb por domínio/fonte de origem (ex.: Wikipedia-PT, C4-PT, notícias, fóruns) e correlacionar com a fração de cada domínio no corpus de treino de 21,7B tokens; se o bpb for sistematicamente melhor nas fontes mais frequentes no treino mesmo controlando dificuldade intrínseca (comparar 150M vs 350M vs 1G nas mesmas fontes), é sinal de familiaridade de domínio. Custo: US$0, menos de 2h — reaproveita losses por documento já computados ou uma passada de avaliação rápida, sem GPU nova.  
*bandeiras:* Domínio é forecasting de séries temporais — nenhum LLM ou modelo de linguagem é avaliado; a ponte para o Bee é conceitual, não numérica; O próprio achado de familiaridade de corpus é declarado pelos autores como 'associação, não mecanismo demonstrado' — repousa em UM corpus (TimesFM/Wikipedia) e correlação rank-biserial de só -0,13; Dois grupos são pequenos (46 e 29 séries) — intervalos de rank largos; o resultado de eletricidade é 'ausência de evidência de vantagem', não déficit demonstrado, nas palavras dos autores

**[2609.10445](https://arxiv.org/abs/2609.10445) — Building Multilingual Bridges: Data Mixing as the Pillar of Generalization for In-Language Reasoning**  
Ensinar um modelo de 3,35B a 'pensar' no idioma do usuário generaliza para idiomas nunca supervisionados quando o treino é amplo e conjunto (não sequencial nem por especialista-e-merge), e uma fatia pequena (10-20%) de dado multilíngue comum sem raciocínio já destrava a maior parte desse ganho de graça.  
*rigor:* **sem sementes** · **só >3B** · código  
*gate:* No próximo SFT do Bee que precise generalizar um comportamento entre os 8 idiomas (ex. tool-calling ou uma futura capacidade de tradução), rodar um ablation pareado barato: SFT com a mistura atual vs. mistura atual + 10-20% de dado multilíngue genérico (não relacionado à tarefa, reciclado do próprio corpus de pré-treino) nos idiomas fracos do Bee. Métrica: taxa de acerto/consistência da tarefa nos idiomas SEM exemplo de treino direto. Custo: nenhuma GPU extra, só reorganizar a mistura de um SFT que já ia rodar.  
*bandeiras:* modelo base de 3,35B, acima do teto de <3B do projeto, e compute de 32xH100x40h muito acima do orçamento do Bee - só a receita de mistura de dado transfere, não a escala; os +-desvio-padrão reportados são variância ENTRE IDIOMAS, não entre sementes de treino - não há teste de variância de rodada (múltiplas sementes) para os efeitos de mistura; avaliação usa tradução automática tanto para GERAR os dados de treino (translate-train) quanto para traduzir os benchmarks - risco de 'tradutês' inflar consistência de forma artificial nos dois lados, não totalmente descontado; métricas de qualidade aberta (MIST-OEG) usam LLM-as-judge (GPT-4.1) - custo e viés potencial do juiz não é quantificado à parte

**[2609.11029](https://arxiv.org/abs/2609.11029) — Rebalancing Token Importance in Language Models with TF-IDF Weighted Cross-Entropy Loss**  
Perda ponderada por TF-IDF reduz memorização verbatim (-14% sob LoRA, -58% sob fine-tuning completo) por menos de 3% de overhead sem perder desempenho -- ataca exatamente o problema de cópia de e-mail que o Bee já mediu, mas sem efeito significativo no cenário mais parecido com o dele (LoRA num modelo de ~1B) e nunca testado em saída estruturada.  
*rigor:* sementes · ≤3B · código  
*gate:* Reaproveitar o experimento de cópia de e-mail do Bee (antes ou depois da diversificação de 868 endereços) e re-treinar o mesmo LoRA/SFT trocando CE simples por CE ponderada por TF-IDF (buffer K=16 minibatches, overhead <3%, sem mudar dado nem arquitetura); medir taxa de cópia exata no holdout de e-mails e a métrica de tarefa (JSON válido / argumento correto). Custo: o de rodar o SFT de novo, poucas horas numa GPU só. Decidir por adotar se a redução de cópia exceder o piso de ruído de semente do Bee sem mover a métrica de tarefa para baixo além do ruído.  
*bandeiras:* nenhum modelo abaixo de 1,1B testado -- autores excluem explicitamente modelos menores por gerarem saída 'curta demais' para medir memorização; sem ablação de componente (TF sozinho vs IDF sozinho) nem de sensibilidade ao tamanho do buffer K=16; só testado em memorização de linguagem natural injetada (WikiText-2), nunca em saída estruturada/JSON como a do Bee; tokenização em subpalavras BPE pode diluir o peso -- os próprios autores levantam essa dúvida como limitação, e o Bee usa BPE 32k/64k próprio; efeito NÃO significativo justamente no cenário mais parecido com o do Bee (LoRA em modelo ~1B)

**[2609.11399](https://arxiv.org/abs/2609.11399) — TransClean: A Benchmark for Detecting and Extracting Clean Translations from Large Language Model Outputs**  
Modelos de linguagem usados como tradutores (de 3B a 671B) poluem entre 3% e quase 100% das próprias traduções com explicações, texto bilíngue ou idioma errado dependendo do prompt e do modelo - detectar isso é barato (~90-98% de acerto com regra+fastText), mas extrair só a parte limpa continua difícil (~50-54% de acerto mesmo com o melhor método).  
*rigor:* **sem sementes** · ≤3B · código  
*gate:* Antes de usar qualquer tradução gerada por um LLM professor como alvo de SFT, rodar nela o detector barato deste artigo (regex de ~12 marcadores de ruído + fastText de idioma-alvo, limiar 60% de confiança) e medir a taxa de ruído na amostra real do professor que o Bee for usar. Custo: perto de zero (CPU, minutos). Se a taxa vier relevante (o artigo sugere que >5-10% é comum mesmo com prompt cuidadoso), adotar descarte automático dos exemplos marcados antes do SFT.  
*bandeiras:* benchmark é majoritariamente centrado em inglês (prompts de tradução e de geração de ruído sintético em inglês) - os próprios autores dizem que ruído tipicamente multilíngue pode estar sub-representado; acurácia de extração por correspondência exata pode penalizar reformulações corretas (caso do extrator Aya, que parafraseia ~40% das traduções já limpas); detecção de idioma errado depende de fastText com limiar de confiança de 60% - não é infalível, é heurística; taxonomia de 12 padrões foi assistida por um LLM (Claude Opus 4.6) para resumir 792 mil saídas, verificada só por amostragem manual, não é exaustiva por construção

**[2609.11655](https://arxiv.org/abs/2609.11655) — Musec: MomentUm SpEctral Clipping for Stable Muon-type Training**  
Troca o 'achatamento espectral' do Muon (picos de perda e explosão de peso já vistos em produção - Kimi K2, GLM-5, DeepSeek-V4) por um clipping que preserva a estrutura espectral do momento, mantendo a perda do Muon bem ajustado mas estável numa faixa de LR bem mais larga - testado bem perto da escala do Bee-1G, porém sem sementes, sem números exatos no texto e sem código próprio liberado.  
*rigor:* **sem sementes** · ≤3B · sem código  
*gate:* No Bee-150M (arquitetura/tokenizer/holdout já prontos), rodar uns 2-3 mil passos com 3 configurações - AdamW atual, Muon puro, Soft Musec - em 2 LRs (a atual do Bee e uma 5-10x maior), medindo bpb no holdout verificado. Piso: só contar como ganho real o que exceder a variância de semente já medida pelo Bee entre rodadas idênticas; registrar se o Muon puro diverge na LR alta enquanto o Musec não. Custo estimado ~US$2-3, ~1-2h numa GPU de nuvem tipo RTX 5090.  
*bandeiras:* todos os resultados de loss de validação estão só em gráficos - nenhum valor numérico exato aparece no texto ou em tabela; nenhuma semente ou repetição é mencionada em nenhum experimento - 1 run por configuração; código próprio (Musec/Soft Musec) não tem link de release; só o harness-base (modded-nanogpt) é público; treinos curtos (546M-8,4B tokens) - não testa se a vantagem persiste em treinos longos como os do Bee (21,7B tokens)

**[2609.11917](https://arxiv.org/abs/2609.11917) — Data Scarcity and Model Sparsity: Mixtures-of-Experts Overfit More to Repeated Data**  
Modelos densos (a arquitetura do Bee) toleram repetir dado até ~8x quase sem dano e só degradam feio depois de ~64x, e misturar um idioma escasso repetido com um domínio grande e semanticamente próximo pode ajudar ainda mais — mas isso foi medido entre gêneros em inglês, não entre idiomas, então o déficit de 13-53x do Bee-1G fica em 'provavelmente OK, vale testar barato' em vez de resolvido.  
*rigor:* sementes · ≤3B · sem código  
*gate:* Mini-run denso (~80-150M, escala RTX 5070/RunPod) com um idioma minoritário do Bee-1G repetido no R do déficit medido: (a) sozinho, (b) misturado com PT não-repetido na proporção do pt-50. Medir bpb (não CE loss) desse idioma em holdout limpo nos dois braços, ≥2 sementes. Se (b) bpb claramente menor que (a), a mistura protege; senão, tratar o déficit como risco real. Ordem de US$ 1-3, ≤2h dado o histórico de custo do projeto.  
*bandeiras:* métrica é CE loss dependente de tokenizador, não bpb (Bee usa bpb por ser independente de tokenizador); domínios testados são gêneros em inglês (web/código/acadêmico/enciclopédia), não idiomas/escritas diferentes — extrapolação pra multilíngue é analogia, não medição; 5 sementes só no 80M e só em R=1/R=32 — não no 1B (escala mais próxima do Bee-1G) nem nos R intermediários (8,16,64) que definem o limiar citado no abstract; número exato do delta de loss em R=8 (o limiar do abstract, '8x com degradação mínima') não aparece no texto, só descrição qualitativa; treino em cluster acadêmico, não 1 GPU de consumo — custo em US$ não reportado


### LER DEPOIS (13)

**[2609.02986](https://arxiv.org/abs/2609.02986) — Modern Transformers Are Implicit Hybrids: From Functional Differentiation to Principled Hybrid Architecture Design**  
Transformers RoPE puros parecem ter cabeças de recuperação e de posição separadas por uma banda de frequência ligada ao comprimento de treino, e um híbrido FA-sem-posição+Linear-Attention por cabeça (HwH) evita a falha total de extrapolação do Transformer puro (0.0 -> ~100/99/46 em NIAH a 4K) — mas é uma arquitetura nova, sem variância de semente, e sem ganho claro em perplexidade/senso comum a 1.4B; vale só para um modelo futuro maior ou com meta de contexto longo, não para o Bee agora.  
*rigor:* **sem sementes** · ≤3B · sem código  
*bandeiras:* zero variância entre sementes — cada configuração (Transformer/GDN/Inter/HwH, em cada escala) é 1 único run, sem repetição; às 1.4B HwH-std NÃO é o melhor em perplexidade nem em senso comum (Inter vence em ambos) — o abstract enfatiza retrieval/extrapolação e deixa isso em segundo plano; mudança de arquitetura grande (implementar Gated DeltaNet + NoPE FA + alocação por cabeça), não um plug-in barato; análise mecanística principal feita em modelos de 1.7B–8B já pré-treinados por terceiros (Qwen3/Llama3.1), não em checkpoints próprios do Bee

**[2609.03379](https://arxiv.org/abs/2609.03379) — RecurTrace: Adaptive Latent Reasoning with Loop-Time Memory**  
RecurTrace ensina um modelo congelado a 'pensar' por loops de profundidade adaptativa com memória entre iterações, ganhando até +3.4pp em 8B — mas o ganho medido no tamanho mais perto do Bee (0.6B) foi o menor de todos (+0.6pp), a tarefa é raciocínio/matemática (fora do foco atual do Bee), e é pós-treino sobre modelo já pronto, não pré-treino do zero.  
*rigor:* sementes · ≤3B · sem código  
*bandeiras:* ganho cresce com a escala do modelo — a escala mais próxima do Bee (0.6B) teve o MENOR ganho de acurácia medido (+0.6pp), o oposto do que o Bee precisaria para justificar o investimento; tarefas-alvo são raciocínio/matemática (GSM8K, MATH, MathQA, lógica) — fora do escopo de capacidades que o Bee vem construindo; é pós-treino sobre modelo já pré-treinado por terceiros, não uma técnica de pré-treino do zero; implementação exige bloco weight-tied + atenção de loop-time + cabeça de parada com oráculo multi-profundidade — engenharia não trivial, não é um teste de 2h

**[2609.04172](https://arxiv.org/abs/2609.04172) — Rethinking On-Policy Distillation of Large Language Models II: One Training Example**  
Treinar destilação on-policy repetindo UMA única query por centenas de passos recupera a maior parte do ganho de usar o dataset inteiro, porque o gargalo é a taxa de absorção do aluno e não a variedade de dados — mas o método exige que professor e aluno compartilhem tokenizador, o que o Bee não tem hoje com seus professores frontier via API.  
*rigor:* **sem sementes** · ≤3B · sem código  
*bandeiras:* exige mesmo tokenizador/família entre professor e aluno em TODOS os pares testados — não é o caso dos professores frontier atuais do Bee; não reporta variância entre sementes de treino para as curvas principais de one-shot OPD (só ablações de dificuldade/temperatura/comprimento); não menciona liberação de código do pipeline OPD; um dos pares usa OLMo-3-7B, acima do teto de 3B mencionado no briefing, embora a maioria dos pares seja 1,5-3B

**[2609.04180](https://arxiv.org/abs/2609.04180) — Knowledge Acquisition During Pre-training? Large Language Models Learn Better With Auxiliary Views**  
Visões auxiliares (textbook/blog/Q&A) batem repetição pura na aquisição de conhecimento durante pré-treino, mas o próprio artigo mostra que o efeito é nulo — e a paráfrase chega a ser levemente prejudicial — em modelos de ~1B, ou seja, em toda a faixa de escala atual do Bee; vale revisitar só se o Bee crescer para a casa de 7B+.  
*rigor:* **sem sementes** · ≤3B · código  
*bandeiras:* a ação sugerida na triagem por abstract não sobrevive à leitura completa: o próprio artigo testa ~1B e encontra efeito nulo/negativo, exatamente a escala do Bee; regime é CPT por injeção de 100 passos com replay geral, não pré-treino do zero de um corpus multilíngue completo; só 36 documentos-fonte (12 por domínio); os próprios autores reconhecem generalização de domínio limitada

**[2609.04637](https://arxiv.org/abs/2609.04637) — Tracing Audio Grounding and Answer Selection in Audio LLMs**  
Estudo de interpretabilidade mecanicista em Audio LLMs de 7-8B (Qwen2-Audio/Qwen2.5-Omni) mostra que o treino desloca o uso do áudio para camadas finais e que o ganho de LoRA se concentra em bandas de camada específicas — mas essas bandas são opostas entre os dois modelos, a escala é muito acima do Bee, e nada disso é acionável antes do estágio de áudio (A), que ainda nem começou.  
*rigor:* sementes · **só >3B** · sem código  
*bandeiras:* só modelos de 7-8B — nenhuma escala testada perto de 3B; não há menção de código ou dado público; arquitetura (LoRA conjunta em encoder de áudio + LM, ambos afinados) difere do plano do Bee de encoder CONGELADO + projetor; o efeito de qual banda de camada de LoRA importa mais é OPOSTO entre os dois modelos testados — não há receita única que generalize nem entre dois modelos da mesma classe, o que é motivo de cautela contra qualquer 'regra de banda de camada' extraída daqui

**[2609.04748](https://arxiv.org/abs/2609.04748) — Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Serving**  
Cache de prefixo muda a trajetória de agentes em até 75% dos episódios sob quantização de 4 bits, sem viés de acurácia agregada — mesma família do 'tamanho do lote muda a geração' que o Bee já catalogou, relevante só se o Bee passar a servir checkpoints quantizados via motor com cache.  
*rigor:* sementes · **só >3B** · código  
*bandeiras:* modelos testados são 7-14B, nenhum <3B; mecanismo é de SERVING (vLLM/llama.cpp com cache entre requisições); o Bee avalia via HF generate() direto, sem esse cache; não toca pré-treino, dados ou tokenizador

**[2609.05016](https://arxiv.org/abs/2609.05016) — Amortizing Scaling Law Construction Costs**  
Formaliza 'meça barato antes de caro, e use um modelo substituto (GP) pra preencher o resto do grid' — recupera a lei de escala com 10-100x menos runs que um grid denso, mas só foi validado em replay retrospectivo de grids que o Bee nunca rodaria; vale a pena quando o Bee for desenhar sua própria lei de escala pro 'modelo maior depois', não agora.  
*rigor:* sementes · ≤3B · sem código  
*bandeiras:* Não treina nenhum modelo novo — é reanálise retrospectiva (replay) de grids que outros grupos já publicaram; Os próprios autores admitem (Apêndice A) que isto NÃO foi validado como estratégia de coleta AO VIVO, só como replay de um grid já completo; O baseline de comparação é o grid EXAUSTIVO, que o Bee nunca rodaria de qualquer forma — o artigo não mede ganho sobre uma prática já esparsa como a do Bee; Sem repositório de código citado para o framework de BO em si (usa componentes padrão como BoTorch)

**[2609.05043](https://arxiv.org/abs/2609.05043) — EuroAlpaca: Task-Preserving Localisation of Instruction Data for European Languages**  
Traduzir dado de instrução campo-a-campo infla ROUGE-L/BERTScore mas derruba 29,8% o seguimento de instrução verificável (confirmado nos 4 modelos também em português); um pipeline que decide caso a caso o que traduzir e o que reconstruir reverte isso pra +12,9% — lição barata pro Bee aplicar quando chegar no estágio de SFT multilíngue, mas ainda não é a etapa atual do Bee-1G.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*bandeiras:* pipeline depende de um LLM juiz de 31B (Gemma-4, 8-bit) que o Bee não treina, só consumiria via API/inferência; cobertura é de idiomas europeus; japonês, chinês e árabe (3 dos 7 idiomas não-PT do Bee-1G) ficam de fora; 1 única semente de treino — os próprios autores dizem 'do not estimate optimisation variance'; dataset e código NÃO estavam públicos no momento da leitura (anonimizado pra revisão), só prometidos 'upon acceptance'; modelos adaptados são todos 3-4B, maiores que o Bee-1G (1,05B) — nenhum teste abaixo de 3B

**[2609.05871](https://arxiv.org/abs/2609.05871) — Where Does the Sound Go? Tracing Acoustic Information Loss in Audio-Conditioned LLMs**  
Quando um LM multimodal (encoder congelado + projetor) erra a resposta de múltipla escolha, a informação acústica muitas vezes SOBREVIVE até a última camada — o defeito costuma estar no LM head não mapear isso pro token certo, e corrigir só as linhas de letra-resposta (10-26 mil parâmetros) recupera 30-42 pp sem retreinar o resto do modelo.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*bandeiras:* LM base >=3B em ambos os testes (Qwen3.5-4B, Ministral3-3B) — nunca testado em ~1B; os próprios autores admitem nas Limitations que não sabem se o gargalo de readout persiste em escalas menores/maiores ou noutro regime de instruction-tuning; sem sementes/variância reportada

**[2609.05949](https://arxiv.org/abs/2609.05949) — The Blindness of Document-Level Translation Evaluation**  
Mostrar o documento inteiro para um avaliador humano ou métrica automática não faz a avaliação virar 'de nível de documento': quando o documento é remontado com frases de sistemas diferentes (quebrando a coerência de propósito), nenhuma das 14 métricas testadas nem os anotadores humanos notam a diferença no score final - o protocolo colapsa para avaliação por frase sem avisar.  
*rigor:* sementes · **só >3B** · código  
*bandeiras:* estudo de avaliação humana em larga escala (18.420 anotações, tradutores profissionais a US$40/h) - não é barato de replicar tal como está, mas a IDEIA do teste contrafactual (MIX) é gratuita de aplicar em qualquer régua nova; restrito a um par de idiomas (inglês->coreano) e um protocolo (ESA); os próprios autores dizem que a generalização para outros pares/protocolos é o próximo passo, não um resultado já estabelecido; o artigo diagnostica o problema mas EXPLICITAMENTE não propõe uma alternativa de protocolo ('we diagnose the failure but do not propose a replacement'); domínio literário descansa em só 2 documentos-fonte (44,6% das anotações) - resultado por domínio nessa fatia é mais frágil

**[2609.09081](https://arxiv.org/abs/2609.09081) — Everything in Moderation: Per-Domain Coverage Optima and Alignment-Resistant Domain Gaps in Multi-Domain Mid-Training**  
Estudo muito rigoroso (5 sementes, testes de permutação, validação held-out) mostra que má cobertura de domínio no mid-training de um LLM de 4-8B não é corrigida por SFT depois — mas os próprios autores dizem que o efeito exige 'folga' de capacidade ausente em modelos <=1,5B, então ainda não se aplica à escala do Bee.  
*rigor:* sementes · **só >3B** · sem código  
*bandeiras:* efeito requer 'folga' base->instruct grande; a 1,5B os autores dizem que o modelo fica no piso e o efeito não apareceria; picos ótimos de cobertura NÃO transferem entre 4B e 8B (mesma família de modelo) — deslocam até 17,5 pp; é mid-training sobre modelo já pré-treinado em domínios sintéticos de raciocínio, não pré-treino do zero multilíngue como o Bee faz; código/dados 'serão liberados' (Apêndice C.7) — promessa no texto, não confirmado como já público; nenhuma métrica de bpb/perplexidade — tudo é acurácia em benchmark de raciocínio sintético; múltiplas comparações sem correção family-wise (os próprios autores avisam)

**[2609.09395](https://arxiv.org/abs/2609.09395) — The Menu Is an Execution Prior: State-Path Tool Menus for Online Agents**  
Um roteador de ferramentas minúsculo e fora do LLM (menos de 1M de parâmetros) que garante ferramentas-ponte e ordem produtor-antes-de-consumidor leva sucesso de agente de 73,7% para 89,8% sem tocar no executor, mas o ganho grande é de cadeias longas que o Bee talvez ainda não tenha no corpus.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*bandeiras:* executor testado principal é Qwen2.5-72B-AWQ, não um modelo pequeno; identidade das 3 executor families da Figura 4 não é revelada no texto — não dá pra confirmar se alguma chega perto de 1B; sem sementes/variância formal (1 seed fixa, 20260525), ainda que compense parcialmente com 3 avaliadores independentes e testes pareados; sem release de código/dado encontrado; encoder de texto é BGE-large-en-v1.5 (inglês) — precisaria trocar para uso em PT; o ganho grande é específico de cadeias longas de ferramentas dependentes, o que não está confirmado no corpus atual do Bee

**[2609.09554](https://arxiv.org/abs/2609.09554) — BuzzASR: A Swarm of 100+ Monolingual Speech Recognition Models**  
Whisper afinado por idioma bate a versão multilíngue em 77/102 idiomas (CER cai 2,8x em média) via um truque de tokenizer 'warm-start' bem validado (CER 7,4 vs 15,1 com init aleatória) — mas para português, o idioma do Bee, o próprio fine-tuning PIOROU o CER porque Whisper já é forte nele, então a lição relevante é só a técnica de troca de vocabulário, para usar numa expansão futura.  
*rigor:* **sem sementes** · ≤3B · código  
*bandeiras:* número principal reportado é o MELHOR de 2-3 seeds/configs por idioma, não média +/- desvio — o mesmo viés de selecionar-o-melhor-de-k que o Bee já sinalizou como problema em pass@k (secao 2k do catálogo de lições); para português, o próprio idioma-alvo do Bee, o fine-tuning PIOROU o CER (1,85% -> 11,04%) em vez de melhorar, porque Whisper já é forte em PT — o artigo não destaca isso, é preciso ler a Tabela 7 linha a linha para encontrar; domínio é ASR com fine-tuning COMPLETO do Whisper (encoder+decoder), não o encoder de áudio CONGELADO que o Bee planeja para o estágio A; usam 8xA100-80GB, mas aparentemente para paralelizar 612 rodadas (102 idiomas x configs), não como exigência de cluster por modelo individual — o texto não deixa claro se uma única GPU bastaria para 1 fine-tune isolado de 1,55B


### NAO ADOTAR (5)

**[2609.06172](https://arxiv.org/abs/2609.06172) — AutoUVM: Automated Prefetching Framework for LLMs under UVM Oversubscription**  
Resolve oversubscription de memória de GPU na inferência via engenharia CUDA pesada — um problema que o Bee não tem, porque os modelos dele cabem inteiros na GPU.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*bandeiras:* resolve oversubscription de memória em INFERÊNCIA — o Bee não tem esse problema, os modelos cabem na GPU; exige instrumentação CUDA de baixo nível (NVBit, Compute Sanitizer, hooks no alocador do PyTorch) — custo de engenharia bem acima do que um projeto solo justificaria para esse ganho; sem sementes/repetições nos benchmarks de tempo (comum em papers de sistemas, mas ainda é uma lacuna de rigor); contagem de parâmetros dos 10 LLMs não informada, só footprint de memória — várias famílias usadas (Qwen1.5, Deepseek-coder, EuroLLM) têm variantes >3B

**[2609.06898](https://arxiv.org/abs/2609.06898) — Dynamic-Programming-Guided Hierarchical BPE and Empirical Analysis of Vocabulary Pruning**  
Um novo método de poda de vocabulário BPE guiado por programação dinâmica reduz a contagem de tokens em menos de 1,2% sobre BPE padrão, mas o próprio artigo nunca mede se isso ajuda um modelo treinado de verdade — só compressão bruta, o que bate com a lição do Bee de que fertilidade não prevê bpb.  
*rigor:* **sem sementes** · **só >3B** · código  
*bandeiras:* o ganho medido é só em contagem de tokens (compressão), nunca em loss/bpb/tarefa de LM — os próprios autores citam isso como limitação explícita; vocabulário testado (12-18K) é bem menor que os 32k/64k usados pelo Bee; autor único, reusa os mesmos Corpus I/II de um trabalho anterior dele mesmo (Pruned BPE); sem sementes/variância — construção determinística, sem repetição de configuração para medir estabilidade

**[2609.07370](https://arxiv.org/abs/2609.07370) — Beyond Fluent Generation: A CPU Reliability Benchmark for MCP-Style Tool Calling in Sub-2B Small Language Models for Edge Deployment**  
Em modelos abaixo de 2B, só 5 de 1000 respostas cruas são JSON direto (0,5%) mesmo numa tarefa fácil sem ferramentas distratoras - confirma que a decodificação restrita do Bee (+10 pp medido) é indispensável, mas não traz nenhuma alavanca nova.  
*rigor:* **sem sementes** · ≤3B · código  
*bandeiras:* benchmark é fácil demais pro que anuncia medir: prompt revela a ferramenta e os argumentos certos, 'seleção de ferramenta' medindo essencialmente cópia, sem ferramentas distratoras (o próprio autor admite isso); amostragem com só 1 run por prompt, sem sementes repetidas - o próprio autor assinala isso como limitação explícita; não cobre execução real, trajetória multi-turno, nem os boards de edge citados no título (Raspberry Pi, Jetson Nano etc. não foram testados diretamente); não é comparável em dificuldade aos holdouts agênticos do Bee, que usam catálogo maior e medem seleção real entre alternativas

**[2609.07666](https://arxiv.org/abs/2609.07666) — MpSub: A Momentum p-Dimensional Subspace Trust-Region Method for Derivative-Free Fine-Tuning of Large Language Models**  
Método de otimização sem gradiente que dispensa busca de LR ao custo de um raio de confiança autocalibrado, mas só provado em fine-tuning de classificação com 100 exemplos - não em geração, e não ataca o gargalo de memória real que o Bee já encontrou no SFT.  
*rigor:* sementes · ≤3B · sem código  
*bandeiras:* só testado em 1 tarefa discriminativa pequena (100 exemplos, 3 classes) - nenhuma tarefa generativa; ablação do hiperparâmetro central (dimensão p do subespaço) usa 1 semente só, sem faixa de variação; sem código ou dado público disponibilizado; o benefício de memória (sem backprop) não resolve o gargalo de VRAM que o Bee já diagnosticou (tensor de logits, não ativações)

**[2609.11356](https://arxiv.org/abs/2609.11356) — Taming Bitwise Behavior in GPU Kernels with Tensor Core**  
Trabalho de engenharia de compilador/GPU sobre reprodutibilidade bit-a-bit de kernels GEMM em datacenter (cuBLAS/Triton) para servir em produção e RL distribuído — não tem relação com pré-treino solo numa única GPU de consumo e não muda nada no Bee.  
*rigor:* **sem sementes** · **só >3B** · sem código  
*bandeiras:* só GPUs de datacenter (GB300/GB200/H100/CDNA3), nunca testado em RTX de consumo; resolve determinismo sob lote variável e alinhamento rollout/treino em RL distribuído — problema que não existe em treino solo numa GPU com configuração fixa; formas de teste vêm de modelos de 20B a 2,4T de parâmetros, nenhum perto da escala do Bee
