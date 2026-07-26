# Estudo — ecossistema de ferramentas HF (21 links, 2026-07-25)

> Diferente das levas anteriores: isto é **biblioteca**, não paper. A pergunta útil não é "o que
> ensina" e sim **"o que muda uma decisão nossa hoje"**. Ferramenta que não muda nada eu digo que
> não muda, em vez de escrever parágrafo bonito sobre ela.

## ⚠️ Procedência do que está aqui

A doc da HF me devolveu **HTTP 429 (rate limit)** nas tentativas de leitura. Em vez de escrever de
memória e apresentar como leitura, **verifiquei por introspecção no próprio ambiente da L4** — o que
é evidência melhor: diz o que existe **na versão que usamos**, não na doc da última release.

Versões medidas: `peft 0.19.1` · `transformers 5.14.1` · `trl 1.9.0` · `accelerate 1.14.0` ·
`bitsandbytes 0.50.0`.

Abaixo, **[✓ verificado]** = confirmado por introspecção agora; **[conhecimento]** = do que eu sei
da biblioteca, sem ter conseguido abrir a doc nesta sessão. Trate os segundos como a confirmar.

---

## 1. PEFT — três coisas que já temos instaladas e não estamos usando

### ⭐ `add_weighted_adapter` — combinar abelhas [✓ verificado]

```
add_weighted_adapter(adapters: list[str], weights: list[float], adapter_name: str,
                     combination_type: str = 'svd', svd_rank=None, svd_clamp=None, ...)
```

Combina N adapters em um novo, com pesos. **Isto ataca um buraco real da comeia:** hoje o roteador
escolhe **uma** abelha. Um pedido "escreva a função e chame a ferramenta que salva o arquivo"
precisa de `coder` **e** `agentica`, e a arquitetura atual não sabe responder isso — escolhe uma e
perde a outra.

Ressalva honesta: combinar por SVD **não é** o mesmo que ter as duas competências; é uma média no
espaço de pesos e pode degradar as duas. Vale medir, não vale assumir.

### ⭐ `POLY` disponível [✓ verificado]

Polytropon: **roteamento aprendido sobre módulos de adapter**. É a Fase 3 do nosso plano ("substituir
regras por classificador") já implementada na biblioteca — e numa forma mais forte do que
planejávamos, porque roteia *dentro* do modelo por camada, não só escolhe uma abelha na entrada.

### `use_dora` e `use_rslora` são flags do `LoraConfig` [✓ verificado]

Treinamos tudo com LoRA r=16 padrão. **DoRA** (decompõe magnitude e direção) costuma ganhar de LoRA
em rank baixo; **rsLoRA** estabiliza o fator de escala. São **duas flags** — custo de experimento
próximo de zero, e a `coder` é reproduzível em 17 min, então dá para medir de verdade.

**Ação registrada:** quando a abelha de extração treinar, rodar um braço com `use_dora=True` na
mesma receita. É o experimento mais barato disponível hoje.

---

## 2. transformers.js — e a objeção do encoder volta com força

[conhecimento] Roda modelos **no navegador** via ONNX Runtime (WebGPU/WASM), com API espelhando a
`pipeline()` do Python: NLP, visão, áudio, multimodal.

**Por que isto importa para nós:** o estudo anterior levantou que extração estruturada é
classicamente tarefa de **encoder**, e que um modelo de 110–300M faria por ~1/40 do custo. O
transformers.js fecha o argumento do outro lado: **um encoder desse tamanho roda no navegador do
usuário — servidor zero, dado nunca sai da máquina.** Para a tese "roda local e privado", que é o
diferencial declarado da comeia, isso é mais forte do que qualquer ganho de qualidade que o adapter
de 4B entregue.

Nosso backbone de 4B **não** cabe nesse cenário. Então a leitura honesta é que existem **dois
produtos diferentes** escondidos no mesmo projeto:
- comeia de 4B com schema aberto, roda em GPU/desktop — o que estamos construindo;
- extrator encoder de schema fixo, roda no browser — mais barato, mais privado, menos flexível.

Continuo achando que o schema aberto justifica a nossa escolha, mas **isto virou pendência de
medição, não opinião.**

---

## 3. sentence-transformers — o roteador da Fase 3, pronto

[conhecimento] Embeddings de sentença; modelos como `all-MiniLM-L6-v2` têm ~22M parâmetros e rodam
em CPU em milissegundos.

**Onde encaixa:** nosso roteador é regex + heurística de complexidade. Ele erra em pedido que não
casa nenhum gatilho e cai no default. Um classificador sobre embeddings, treinado nos clusters de
tarefa que **já temos rotulados de graça** (cada item de `extraction_tasks.jsonl`, `coder_tasks`,
`sft_agentic` sabe de que abelha veio), substituiria as regras por decisão aprendida — a Fase 3 do
plano, com o dataset já existente e custo de treino de minutos em CPU.

**É provavelmente o melhor custo-benefício da lista inteira.**

---

## 4. lighteval e evaluate — devo trocar nossos evals? Não.

[conhecimento] `lighteval` é o harness de avaliação da HF (sucessor do lm-evaluation-harness no
ecossistema deles); `evaluate` é a biblioteca de métricas.

**Veredito honesto:** não trocaria. A lição mais cara deste projeto foi justamente que **régua
genérica não mede o que a especialização muda** — a `chat_ptbr` passou por 7 benchmarks a n=300 e foi
declarada "não conclusiva", enquanto o defeito real (responder em português a pergunta em inglês)
era invisível para múltipla escolha. Nossos evals medem execução de código, JSON válido contra
catálogo, groundedness e consistência de idioma. Nenhum harness genérico traz isso.

**Onde valeria:** para o `base_forte` e para comparar o backbone contra modelos externos em
benchmark padrão — exatamente o item "medir o backbone em absoluto" que ficou aberto na decisão de
hoje.

---

## 5. Deploy: optimum · bitsandbytes · safetensors · kernels

- **bitsandbytes** [✓ 0.50.0] — já usamos (NF4 4-bit, `paged_adamw_8bit`). O backbone em 2,98 GB
  medido é isto funcionando.
- **safetensors** — já usamos (é o formato dos nossos adapters: 42,5 MB o da coder).
- **optimum** [conhecimento] — exportação para ONNX/OpenVINO/TensorRT. É o caminho da **Fase 5**
  (empacotar a comeia como runtime local). ⚠️ Ponto não resolvido: exportar **LoRA hot-swap** para
  ONNX não é trivial — o grafo exportado tende a congelar os pesos. Provável que a Fase 5 exija
  *merge* dos adapters e N modelos exportados, o que **desfaz a economia de VRAM que é a tese da
  comeia**. Isso é uma tensão arquitetural real e ainda não temos resposta.
- **optimum-neuron / optimum-tpu** [conhecimento] — AWS Inferentia/Trainium e TPU. Irrelevante para
  nós hoje (L4 no Colab).
- **kernels** [conhecimento] — carregar kernels otimizados direto do Hub em vez de compilar. Pode
  ajudar latência; a nossa latência medida (18,3 s/query) é dominada por geração, não por kernel.
  Baixa prioridade.

---

## 6. Contexto, sem ação hoje

- **timm** [conhecimento] — modelos de visão. Vira relevante na **Fase 4** (abelha multimodal ~9B).
- **openenv** [conhecimento] — ambientes de RL para treinar agentes. Interessante no horizonte: a
  `agentica` hoje é treinada por SFT em traços; RL em ambiente é o passo seguinte natural. Longe do
  que estamos fazendo agora.
- **TRL** [✓ 1.9.0] — já usamos (SFT com máscara de prompt, DPO escrito e não rodado).
- **accelerate** [✓ 1.14.0] — já usamos indiretamente via TRL.

---

## Resumo — ordenado por valor para nós

| # | Ferramenta | O que muda | Custo |
|---|---|---|---|
| 1 | **sentence-transformers** | roteador aprendido (Fase 3) com dataset que já temos rotulado | minutos de CPU |
| 2 | **PEFT `use_dora` / `use_rslora`** | duas flags, possivelmente melhor que LoRA r=16 | ~17 min de L4 |
| 3 | **PEFT `POLY`** | roteamento aprendido por camada — Fase 3 numa forma mais forte | experimento real |
| 4 | **PEFT `add_weighted_adapter`** | combinar abelhas (pedido que precisa de duas) — hoje impossível | medir, não assumir |
| 5 | **transformers.js** | reabre a objeção do encoder, agora pelo lado da privacidade/browser | pendência de medição |
| 6 | **optimum** | ⚠️ tensão real: exportar hot-swap pode desfazer a economia da comeia | investigar antes da Fase 5 |
| 7 | lighteval / evaluate | só para medir o backbone em absoluto — não substitui nossos evals | — |
| 8 | timm · openenv · kernels · optimum-neuron/tpu | contexto | — |
