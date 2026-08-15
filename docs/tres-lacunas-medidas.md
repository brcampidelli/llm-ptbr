# As três lacunas de custo zero — medidas (2026-08-15)

> O estudo do Qwen3.8 terminou apontando três lacunas de **custo US$ 0**. Foram fechadas.
> Duas produziram achado forte; a terceira **corrigiu uma atribuição errada no repositório**.
>
> ⚠️ Nada aqui tocou o pod: o Bee-350M estava treinando com **29,5 de 32,6 GiB** de VRAM
> ocupados, e um segundo processo poderia derrubar por OOM um run de US$ 115 em 8,6%. Tudo
> foi medido na RTX 5070 local, no Bee-150M.

---

## Lacuna A — o MobileLLM primário, e a atribuição que estava errada

O estudo apontou o MobileLLM (arXiv:2402.14905) como *"o único trabalho medido nos dois
degraus exatos do projeto"*, e que o survey o descrevia em 4 linhas **sem uma única métrica**,
errando a citação duas vezes. Fui ao primário. **Tabela 9:**

| | camadas | dim | FFN | heads | KV |
|---|---:|---:|---:|---:|---:|
| MobileLLM-125M | 30 | 576 | 1536 | 9 | 3 |
| **Bee-150M** | **30** | **576** | **2048** | **9** | **3** |
| MobileLLM-350M | 32 | 960 | 2560 | 15 | 5 |
| **Bee-350M** (rodando) | **32** | **960** | **2560** | **15** | **5** |

⭐ **A geometria do Bee-350M é idêntica à do MobileLLM-350M, campo a campo.**

🔴 **E isso corrige o repositório.** `bee/config.py` e `docs/estudo-bee-350m.md` atribuem essa
geometria ao **SmolLM2-360M**. Ela tem **duas** fontes publicadas independentes no tamanho
exato — e a do MobileLLM vem com **ablações**, o que a torna a citação mais forte. O comentário
no config foi corrigido.

### O que o primário mede e o survey não contava

**Weight sharing bloco-a-bloco** (repetir blocos sem somar parâmetro), Tabela 2:

| | sem sharing | com sharing | ganho |
|---|---:|---:|---:|
| 125M | 44,6% | **45,0%** | +0,4 pp |
| 350M | 49,6% | **50,2%** | +0,6 pp |

E nos modelos finais (Tabela 3): 125M 46,3% → **47,0%** · 350M 51,3% → **52,1%**.

**Fundo-e-fino, a ~135M com parâmetros fixos** (Tabela 11):

| camadas | média zero-shot |
|---:|---:|
| 12 | 43,9% |
| **30** | **44,8%** |
| 42 | 44,5% |

⭐ **30 camadas é o ótimo medido** — exatamente o que o Bee-150M usa. A escolha, que o
`config.py` justificava por analogia com o SmolLM2, tem **medição direta** no tamanho certo.

⚠️ **Ressalva de escala de dados:** o MobileLLM treinou com **1T tokens** (480k iterações). O
Bee usa 21,75B — **46× menos**. As acurácias absolutas não transferem; a **ordenação entre
arquiteturas** é o que se aproveita.

**Consequência:** o weight sharing rende +0,6 pp em 350M **sem somar parâmetro**. É candidato
real para o próximo degrau — mas exige pré-treino novo, então **não entra no run atual**.

---

## Lacuna B — 🔴 as ativações massivas EXISTEM no Bee, e o sink também

`bee/sonda_ativacoes.py`, Bee-150M base, quatro frases em PT:

```
razao      camada   dim    |x|max    mediana   token
1616,0x        16   538   3670,92     2,2716   'O'
1603,8x        16   538   3673,64     2,2906   'Em'
1584,2x        16   538   3791,75     2,3935   'Receita'
1574,6x        15   538   3646,29     2,3156   'O'
```

**Uma única dimensão — a 538 —** nas 12 maiores ocorrências. Sempre no **primeiro token**.
Sempre nas camadas 15–18. É a assinatura exata do paper: dimensão fixa, token delimitador,
meio da rede.

E o **attention sink**, medido na mesma corrida:

| frase | atenção no 1º token (máx entre camadas) | camada |
|---|---:|---:|
| "O Brasil é um país…" | 0,849 | 15 |
| "A inteligência artificial…" | **0,879** | 15 |
| "Em 1988 foi promulgada…" | 0,833 | 15 |
| "Receita de pão de queijo…" | 0,840 | 15 |

Na camada 15, **83–88% da massa de atenção vai para o primeiro token**.

⭐ **Os dois são o mesmo evento.** `hidden_states[16]` é a **saída da camada 15** — a ativação
de 1616× e o pico do sink estão na **mesma camada**. É a cadeia causal que o paper descreve,
reproduzida num modelo de 151M.

### As três consequências práticas

1. 🔴 **Quantização por-tensor está descartada.** Uma dimensão 1616× acima da mediana destrói
   qualquer escala global. Se o Bee for servido quantizado, tem de ser **por-canal**, e com
   **bpb medido antes e depois** — sem exceção.
2. ⚠️ **Não podar o começo do contexto.** O prompt agêntico do Bee tem ~1.100 tokens de
   catálogo no início. Descartar os primeiros tokens para encurtar histórico atinge justamente
   o sink e degrada desproporcionalmente. Se um dia houver janela rolante, **manter âncoras**.
3. **A dimensão 538 é um endereço, não um mistério.** Qualquer diagnóstico futuro de
   instabilidade ou de perda por quantização deve olhar para ela primeiro.

⚠️ **O que esta sonda NÃO diz:** não mede qualidade, não prova causalidade e não decide
quantização sozinha. Ela responde uma pergunta — *o fenômeno está lá, e onde?* — e a resposta
é sim, na dimensão 538, camada 15.

⚠️ **Um defeito da primeira versão, corrigido:** ela rodou com SDPA, que **não expõe as
matrizes de atenção**. A seção de attention sink simplesmente não apareceu, com apenas um
aviso do `transformers` no meio da saída — e teria passado como *"não tem sink"* em vez de
*"não foi medido"*. Agora força `attn_implementation="eager"`.

---

## Lacuna C — a razão intermediate, e quem de fato desvia

A razão `intermediate / d_model`:

| | intermediate | razão | params | MLP |
|---|---:|---:|---:|---:|
| MobileLLM-125M | 1536 | **2,667×** | 124,6M | 79,6M (64%) |
| **Bee-150M** | 2048 | **3,556×** ⚠️ | 151,2M | 106,2M (**70%**) |
| MobileLLM-350M | 2560 | **2,667×** | 345,4M | 235,9M (68%) |
| **Bee-350M** | 2560 | **2,667×** ✅ | 345,4M | 235,9M (68%) |

⭐ **O desvio é do Bee-150M, não do 350M** — o oposto do que o estudo supôs e do que o
`config.py` registrava como ressalva.

**Quanto custou:**

```
Bee-150M como está : 151,2M
com 2,667×         : 124,6M
diferença          :  26,5M = 17,6% do modelo
```

**26,5M de parâmetros — 17,6% do modelo — foram para o MLP em vez de para profundidade ou
largura, e nunca foi medido se valeram.** Com a razão de 2,667× sobrariam parâmetros para
~7 camadas a mais.

⚠️ **Isso NÃO significa que o Bee-150M está errado.** Ele mede bpb 0,844 e bate o Tucano-160m
e o SmolLM2-135M. Significa que **um quarto do orçamento de parâmetros foi alocado por
herança, não por medição** — e que a comparação "Bee-150M vs MobileLLM-125M" nunca foi
maçã-com-maçã: são 151,2M contra 124,6M, **21% a mais de modelo**.

**O que fica resolvido:** o Bee-350M está com a razão publicada nos dois trabalhos. A ressalva
que eu havia escrito no `config.py` (*"desvio não medido"*) apontava para o lado errado.

**O que continua aberto:** medir a razão exige gate pareado (~US$ 20), então **não é custo
zero** e fica para o próximo degrau. Registrado para não ser redescoberto.

---

## Veredito

| lacuna | resultado | muda o quê |
|---|---|---|
| **A** MobileLLM | geometria do 350M validada por 2ª fonte com ablação; 30 camadas é ótimo medido | corrige atribuição; weight sharing (+0,6 pp) vira candidato ao próximo degrau |
| **B** sonda | 🔴 ativações massivas (1616×, dim 538) e sink (85%) **confirmados em 151M** | **mata quantização por-tensor**; proíbe podar o início do contexto |
| **C** razão | quem desvia é o **150M** (3,556×), não o 350M | corrige a ressalva do `config.py`; 17,6% do 150M alocado por herança |

Custo total: **US$ 0**. Nenhuma tocou o run em andamento.

## Reprodução

```bash
python bee/sonda_ativacoes.py --modelo models/bee-150m-v3-base --out docs/sonda-ativacoes-150m.json
```

⏳ **Pendente:** rodar a mesma sonda no `marco_1B` do 350M quando o run terminar — para ver se
o fenômeno aparece na mesma dimensão relativa e na mesma profundidade proporcional.
