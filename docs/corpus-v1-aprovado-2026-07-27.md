# Corpus de treino do Bee — v1 · ✅ APROVADO (2026-07-27)

**12,30 GB em 53 shards.** Sete fontes, sete cotas fechadas, desvio máximo de 1%.
Manifesto com procedência e licença por shard: `MyDrive/BEE/corpus/MANIFEST.json`.

## Mistura real (auditada, não assumida)

| fonte | licença | pedido | obtido | desvio | aproveitamento |
|---|---|---:|---:|---:|---:|
| `fineweb-2` cfg `por` | ODC-By-1.0 | 35% | 34% | −1% | 98% |
| `PleIAs/Portuguese-PD` | domínio público | 15% | 15% | −0% | 65% |
| `wikimedia/wikipedia` pt | CC-BY-SA-4.0 | 10% | 10% | −0% | 69% |
| `stjiris/portuguese-legal-sentences` | Apache-2.0 | 5% | 5% | −0% | 36% |
| `smollm-corpus/fineweb-edu-dedup` | ODC-By-1.0 | 15% | 15% | −0% | 99% |
| `smollm-corpus/cosmopedia-v2` | ODC-By-1.0 | 10% | 10% | −0% | 91% |
| `bigcode/the-stack-smol-xl` | permissivas (the-stack v1.1) | 10% | 10% | −0% | 26% |

→ **PT 65% · EN 25% · código 10%**, que é exatamente a receita.

## ⭐ O que dá peso ao "aprovado"

**É o mesmo script que, horas antes, aprovou um corpus com 0% de código.** Entre um e
outro, três guards foram escritos — e eles **reprovaram o corpus duas vezes** antes de
ele chegar aqui:

1. **fonte que não abriu** — não era checada. As duas primeiras fontes de código caíram
   nesse buraco e o veredito imprimiu "✅ aprovado" sobre um corpus sem código.
2. **cota por categoria** — o teste de mistura media a razão entre o que *sobrou*, não se
   o que foi *pedido* chegou. Com os 10% de código ausentes, a proporção se reajustou e o
   português caiu em 70%, **dentro** do alvo. A fonte sumir *melhorava* a nota do teste.
3. **fonte vazia** — 786.387 linhas lidas, 0 aceitas, com o motivo e as chaves reais do
   dataset no erro. Foi esse que deu o diagnóstico da terceira tentativa.

Um "✅" que nunca disse "🔴" não vale nada. Este disse, duas vezes.

## Três fontes de código tentadas, três falhas diferentes

Cada uma ensinou uma checagem que eu não fazia:

| fonte | falha | a pergunta que passou a existir |
|---|---|---|
| `smollm-corpus/python-edu` | só ponteiro (`blob_id`/`path`), campo `text` vazio | o dataset guarda o **texto** ou só a referência? |
| `codeparrot/github-code-clean` | `Dataset scripts are no longer supported` | carrega na **versão** que eu tenho instalada? |
| `the-stack`/`-dedup`/`-smol` | **gated**, exigem aceite manual | funciona sem intervenção humana? |
| `the-stack-smol-xl` (1ª vez) | 786.387 lidas, **0 aceitas** | ⬇ ver abaixo |
| **`the-stack-smol-xl` (2ª vez)** | ✅ **1.229 MB, cota exata** | |

### ⭐ A falha mais instrutiva: 786.387 linhas, 0 aceitas

O diagnóstico foi uma linha só:

```
valores REAIS de lang: [('Ada', 3000)]
```

Duas causas, e a segunda não era a que eu supunha:

1. **Capitalização.** O the-stack usa `Python`, minha lista estava em `python`. Sozinho já
   rejeitaria 100%. Corrigido normalizando **os dois lados**, o que elimina a classe do bug
   em vez do caso.
2. **O dataset vem ORDENADO por linguagem, em blocos.** As 3.000 primeiras linhas são todas
   `Ada`. Mesmo com a capitalização certa, o coletor leria dezenas de milhares de arquivos de
   `Ada`/`Agda`/`Alloy`/`ANTLR` e **nunca alcançaria** Python. Corrigido com
   `.shuffle(buffer_size=50k)`.

**É a mesma classe do `--limit 60` que contaminou a `coder`:** tratar uma fatia do começo
como amostra representativa de um dado que está ordenado. O projeto já tinha aprendido isso
uma vez, com outro sintoma.

## Outros defeitos consertados nesta coleta

- **Uma fonte que morre no meio derrubava o corpus inteiro.** O `try` cobria só o
  `load_dataset()`, não a iteração — o `Portuguese-PD` estourou `CastError` no 5º parquet
  (o dataset tem **schemas diferentes entre shards**) e as 6 fontes seguintes nem foram
  tentadas. Agora a falha isola.
- **O `MANIFEST` era gravado só ao fim de cada fonte.** Quando a fonte estourou no meio,
  6 shards já em disco (~1,5 GB) ficaram **fora** do manifesto — e a retomada os
  sobrescreveria em silêncio. Agora persiste a cada shard. Foi preciso um `--reconciliar`
  (que lê os shards reais e reconstrói o manifesto) para recuperar esses 1,5 GB.
- **Causa raiz do `CastError`:** `columns=[campo]` no `load_dataset`. Nunca usamos as colunas
  de metadados que divergem entre shards; projetar só o que interessa faz o cast ignorá-las.

## ⚠️ O que fica em aberto

- **Duplicatas entre execuções.** O dedup MinHash vive só em memória e morre com o processo;
  na retomada, o streaming relê do início e aceita de novo o que já está nos shards. Houve
  3 quedas. O conserto (`VistosPersistente`, sha1 exato em disco) está escrito mas **ainda
  não aplicado ao corpus atual** — ver `bee/build_corpus.py`. É medível e corrigível com uma
  passada de dedup sobre os shards.
- **Aproveitamento de 26% no código** é o esperado (descartamos ~58 linguagens fora da lista
  e os arquivos gerados/minificados), mas não foi auditado por linguagem. Não sabemos a
  distribuição real entre Python, Java, Go etc.
- **O tokenizador atual foi treinado no corpus SEM código.** Com 10% de código agora
  disponível, vale re-treinar antes do pré-treino — trocá-lo depois invalida qualquer
  checkpoint.

## Próximo

`bee/config.py` já existe e está verificado (fórmula de parâmetros com divergência 0,00%
contra o modelo real). O que falta para o primeiro Bee: `bee/pretrain.py` e o Gate 2
(`Bee-150M` × `SmolLM2-135M` em português).
