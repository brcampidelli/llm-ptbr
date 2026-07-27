# Estudo — tokenização (7 fontes, 2026-07-27)

> Lido antes de retreinar o tokenizador do Bee. Formato: o que a fonte diz → **o que muda no que
> eu ia fazer**. Onde não muda nada, digo que não muda, em vez de encher linguiça.

Fontes: [HF LLM Course cap. 6.1](https://huggingface.co/learn/llm-course/pt/chapter6/1),
[6.2](https://huggingface.co/learn/llm-course/pt/chapter6/2),
[6.3](https://huggingface.co/learn/llm-course/pt/chapter6/3),
[google/sentencepiece](https://github.com/google/sentencepiece),
[Kudo & Richardson 2018](https://arxiv.org/abs/1808.06226),
[huggingface/tokenizers](https://github.com/huggingface/tokenizers),
[openai/tiktoken](https://github.com/openai/tiktoken).

---

## ⭐ 1. O curso valida o retreino que vamos fazer — e diz por quê

O cap. 6.1 abre dizendo que usar um tokenizador treinado em outro domínio/idioma é *"tipicamente
subótimo"*, e o 6.2 insiste: **o corpus tem de ser representativo do domínio**. O exemplo deles é
justamente treinar em código Python (CodeSearchNet, 1,6 GB) em vez de texto genérico.

**O que muda:** confirma que retreinar agora é o certo, e não zelo excessivo. O tokenizador v1 do Bee
foi treinado num corpus com **0% de código** (a fonte falhou). Agora o corpus tem 10% de código. Um
tokenizador que nunca viu `def`, `};`, `->`, indentação de 4 espaços vai gastar tokens demais neles —
e 10% do nosso pré-treino seria pago com câmbio ruim.

---

## ⭐ 2. Normalização: o gap real do nosso v1

O SentencePiece aplica **NFKC por padrão**. O nosso `train_tokenizer.py` **não tem normalizer nenhum**.

Por que isso importa **em português** especificamente: "ã" pode ser gravado como `U+00E3` (precomposto,
NFC) ou como `a` + `U+0303` (combinando, NFD). São **bytes diferentes** — e num BPE ByteLevel viram
**tokens diferentes**. Texto vindo de fontes distintas (web, PDF de livro digitalizado, Wikipédia)
chega nas duas formas. Sem normalizar, o vocabulário desperdiça entradas com o mesmo caractere.

⚠️ **Mas NFKC não é a resposta automática.** NFKC é *compatibilidade*: converte `①`→`1`, `ﬁ`→`fi`,
`½`→`1⁄2`. Isso **não é reversível** — e o tiktoken/GPT-2 deliberadamente **não normaliza**, para
manter a tokenização *lossless*, que é a propriedade que o próprio paper do SentencePiece vende.

**O que muda:** vou usar **NFC**, não NFKC — unifica as formas de acento (que é o problema real do
português) **sem** destruir informação. E vou **medir** as três opções (nenhuma / NFC / NFKC) em vez
de escolher por dogma.

---

## 3. BPE vs. Unigram: nossa escolha está certa, mas pelo motivo certo

O paper (Kudo & Richardson) apresenta os dois: **BPE** é guloso e determinístico; **unigram LM** é
probabilístico e permite *subword regularization* (amostrar segmentações diferentes do mesmo texto
durante o treino, como regularizador).

**O que muda: nada — e isso é uma decisão, não inércia.** ByteLevel BPE é o que usam GPT-2/tiktoken,
Llama 3, Qwen e SmolLM2. Como o Bee é Llama-arch e vai ser comparado ao SmolLM2, usar o mesmo
algoritmo mantém a comparação limpa: se ganharmos em PT, o ganho é do **corpus**, não de trocar duas
variáveis ao mesmo tempo. Unigram + subword regularization fica como experimento futuro isolado.

---

## 4. O metasímbolo `▁` e o espaço — por que não copiamos

O SentencePiece trata o espaço como símbolo explícito (`▁`, U+2581) para ser *language-independent* e
reversível: nenhuma pré-tokenização por idioma, e o texto original se reconstrói exatamente.

**O que muda: nada.** O `ByteLevel` do `tokenizers` resolve o mesmo problema por outro caminho — mapeia
cada byte para um caractere imprimível, então o espaço já é um símbolo comum e **nunca há `<unk>`**
(qualquer byte é representável). É a razão de o nosso `BPE(unk_token=None)` ser seguro.

---

## 5. `train_new_from_iterator` — o caminho que NÃO vamos usar, e por quê

O cap. 6.2 ensina a treinar um tokenizador novo **a partir de um existente**, herdando algoritmo,
tokens especiais e estrutura; só o vocabulário muda.

**O que muda: nada, mas vale registrar a alternativa.** Herdar de um tokenizador pronto traria junto
decisões que não queremos (o vocab 248k do Qwen, ou o pré-tokenizador do SmolLM2 ajustado a inglês).
Como o **tamanho do vocab é a nossa aposta** (32k contra 248k — ver Gate 1), construímos do zero.
A armadilha que o curso avisa e que nos serve: **usar gerador, não lista** (o corpus não cabe em RAM),
e **função que devolve o gerador**, porque gerador se esgota depois do primeiro uso. Nosso
`ler_corpus()` já é gerador.

---

## 6. Fast tokenizers: offset mapping — já usamos sem saber que era isso

O cap. 6.3: os *fast tokenizers* (Rust) dão `word_ids()`, `offset_mapping`, `token_to_chars()`.
Diferença de velocidade citada: **10,8 s vs 4 min 41 s** num lote.

**O que muda: nada agora, mas explica uma peça nossa.** O `comeia/train/encoder_ner.py` usa
`word_ids()` para alinhar rótulos BIO com subtokens — é exatamente esse recurso. E o
`PreTrainedTokenizerFast` que já embrulhamos garante que o Bee terá isso de graça no SFT.

---

## 7. Velocidade — contexto, não decisão

| biblioteca | número citado | fonte |
|---|---|---|
| `tokenizers` (HF, Rust) | < 20 s por GB de texto | repo HF |
| `tiktoken` | 3–6× mais rápido que comparáveis | repo OpenAI |
| SentencePiece | 27,41 MB/s vs 3,78 MB/s do HF (T5-base, 1 thread) | repo Google |
| SentencePiece (segmentação) | ~50k sentenças/s, ~6 MB de memória | repo Google |

**O que muda: nada.** Tokenizar 12 GB uma vez, mesmo no mais lento, custa minutos — irrelevante contra
as 25 h de GPU do pré-treino. Velocidade de tokenizador só importaria em serving de altíssimo volume.

⚠️ **Limitação deste estudo:** não consegui extrair os números de BLEU dos experimentos do paper do
SentencePiece (o abstract não os traz e o PDF não abriu no ambiente). As afirmações sobre o paper aqui
são conceituais, não quantitativas — e estão marcadas como tal.

---

## ⭐ O que vai mudar no `bee/train_tokenizer.py`

1. **Normalizer NFC** (não NFKC — reversibilidade), com as três variantes **medidas** antes de fixar.
2. **Fertilidade também em CÓDIGO.** O Gate 1 atual mede PT e EN; agora que 10% do corpus é código,
   medir só PT/EN esconderia justamente a regressão que o retreino quer evitar.
3. **Varredura de vocab (32k / 48k / 64k).** Nenhuma fonte dá um número mágico; o trade-off é
   fertilidade × tamanho do embedding, e no Bee-150M o embedding já é 12% do modelo. **Medir.**
4. **Mais rivais no gate:** além de Qwen e SmolLM2, incluir um tokenizador tiktoken-style
   (GPT-4/`o200k`) — é a família do nosso algoritmo, e é o baseline honesto.

Nada disso vem de opinião: são as quatro coisas onde as fontes disseram algo que o nosso código ainda
não fazia.
