# Lições do pré-treino do Bee — o que estava errado e qual é o correto

> Escrito em 2026-08-08, durante o retreino que corrigiu tudo. Este documento existe porque o erro
> central era **invisível**: não gerava exceção, não gerava aviso, e todos os sinais de saúde do
> treino apontavam para "está funcionando".
>
> Versão enxuta e global (vale para qualquer projeto): `~/.claude/rules/bee-pretreino-licoes.md`.

---

## O resumo em uma tabela

| | antes | depois | como se descobriu |
|---|---|---|---|
| objetivo de treino | previa **t+2** | prevê **t+1** | contradição entre dois experimentos internos |
| cobertura do corpus | 63,5% | **100%** | auditoria do amostrador após achar o bug |
| corpus | 9,87B, ~70% PT + EN + código | **21,75B, 100% PT** | decisão de projeto |
| tokens/parâmetro | 65 | **144** | consequência do acima |
| escolha de GPU | por `$/hora` | por **`$/B tokens` medido** | a placa "barata" saiu 36% mais cara |

**Resultado:** bpb no mesmo holdout limpo, mesmo procedimento:

| modelo | bpb | tokens de treino |
|---|---:|---|
| Tucano-160m | 0,884 | ~200B |
| **Bee corrigido @ 3B** | **0,947** | 3B |
| **Bee corrigido @ 1B** | **1,021** | 1B |
| SmolLM2-135M | 1,551 | ~2T (inglês) |
| **Bee v3 (com o bug)** | **2,218** | 9,87B |

O Gate 2, que estava perdido por 72%, foi ganho por 34% — **com 10× menos dados**.

---

## 1. 🔴 O deslocamento duplo de rótulos

### O erro

```python
# bee/pretrain.py — como estava
x, y = janelas[:, :-1], janelas[:, 1:]      # y JÁ deslocado
perda = modelo(input_ids=x, labels=y).loss   # e o Llama desloca DE NOVO
```

`LlamaForCausalLM.forward(labels=L)` calcula internamente
`loss = CE(logits[..., :-1, :], L[..., 1:])`. Passando um `y` já deslocado, o alvo efetivo vira
**t+2**: o modelo aprende a pular um token.

### O correto

```python
perda = modelo(input_ids=x, labels=x).loss   # o rótulo é o PRÓPRIO input
```

### A prova

Medido no `bee-150m-v3-base`, mesmo texto:

| alvo | Bee-150M-v3 | SmolLM2-135M (controle) |
|---|---:|---:|
| t+1 (a tarefa correta) | ppl 898,2 | ppl **16,7** ✅ |
| t+2 | ppl **130,2** ✅ | ppl 15.388,9 |

O mínimo do Bee estava em **t+2**. Nenhum LM causal correto vai melhor em t+2 — é estritamente mais
difícil, porque o token intermediário some. O controle prova que o medidor estava certo.

### Por que sobreviveu duas semanas

**O bug não dá erro.** A loss cai, a perplexidade de validação cai (77 → 63), as curvas são bonitas
do início ao fim — porque a validação usava a mesma convenção errada. O treino inteiro é
autoconsistente. O defeito só aparece ao medir contra um modelo externo, e nesse ponto o modelo
parece apenas *ruim*, o que convida a explicações sobre corpus, arquitetura e escala.

### O que ele invalidou

Todas estas conclusões foram produzidas, documentadas com rigor e **estão erradas**:

- "2,6× mais token não melhorou o bpb" (Gate 2)
- "o corpus saturou perto de 10B" / "o piso é ppl ~57" (escada de scaling)
- "o gargalo é o tamanho do modelo"
- "o gargalo é volume de português"
- "trocar para 100% PT rende 0,37%" (gate de corpus — os 3 braços tinham o bug)
- toda a comparação com Tucano-160m e SmolLM2

Os documentos correspondentes em `docs/` estão marcados como **DOCUMENTO INVÁLIDO** e preservados —
a mecânica do erro vale mais que os números.

### A guarda instalada

`bee/pretrain.py::conferir_convencao_de_rotulos()` roda **antes do passo 1** e aborta:

```python
saida = modelo(input_ids=x[:1], labels=x[:1])
manual = F.cross_entropy(saida.logits[0, :-1].float(), x[0, 1:]).item()
if abs(saida.loss.item() - manual) > 0.01:
    raise SystemExit("convencao de rotulos errada")
```

⚠️ **Usa dado de treino real de propósito.** Com tokens aleatórios a diferença cai de 1,85 para
0,0074 e a guarda não dispararia — seria um teste que passa sem testar nada.

⚠️ **E a guarda precisa ser CHAMADA.** Na primeira versão ela foi escrita, commitada e nunca
invocada. Guarda fora do fluxo não guarda nada. Um `NameError: torch` dentro dela só apareceu no
`--dry-run`.

---

## 2. Amostragem com reposição descartava 37% do corpus

```python
# como estava
idx = torch.randint(0, n_blocos, (batch,))
```

`randint` amostra **com reposição**. Em `n` sorteios de `n` itens, a cobertura esperada é
`1 − (1−1/n)^n → 1 − 1/e = 63,2%`. **Medido: 63,5%** (100/100 blocos com o corretor, 58/100 antes).

De 9,87B tokens do v3, **~3,6B nunca entraram no treino** — e ainda assim o log dizia "1,00 época".

✅ **Correto** (`AmostradorPermutado`): permutar os blocos não-sobrepostos uma vez, percorrer até o
fim, reembaralhar só na virada de época, e **reportar a cobertura no log**.

---

## 3. Throughput: ler o log inteiro, nunca um número solto

Em uma hora, três leituras erradas seguidas — cada uma produzindo uma recomendação de hardware
diferente:

| leitura | origem | problema |
|---|---|---|
| "faltam 16,7 h" | linha do passo 0 | throughput 0,0k → divisão inválida |
| "32,6k tok/s" | passo 10, meio do aquecimento | subestimava |
| "81,1k tok/s" | `tail -1` de log de rodada já morta | superestimava 2× |

✅ **Correto:** confiar só a partir do passo ~20, exigindo **três leituras consecutivas
coincidentes**. Rodar `--passos 40` por configuração antes de comprometer um run longo — 5 minutos
por config contra dias de treino.

---

## 4. GPU: `$/bilhão de tokens` medido, não `$/hora`

Mesmo modelo, mesmo corpus, mesmo código:

| GPU | TDP | tok/s | $/h | **$/B tokens** | run de 21,7B |
|---|---:|---:|---:|---:|---:|
| **RTX 5090** | 600 W | **62,9k** | 0,99 | **4,37** | 96 h · ~$97 |
| RTX PRO 4500 | 200 W | 42,1k | 0,74 | 4,88 | 143 h · ~$106 |
| A100 SXM | 400 W | 70k | 1,59 | 6,31 | 86 h · ~$137 |

⭐ **O preditor é o TDP.** A PRO 4500 tem a **mesma VRAM** (32 GB) da 5090 e custa 25% menos por
hora — e saiu **36% mais cara por token**.

**Como diagnosticar:** ela rodava a **99% de utilização usando 12 GB de 32**, cravada em **200,0 W**.
Utilização alta + potência no limite = **teto elétrico**, não computacional. A 5090 puxa 562 W de 600
com 7,8 GB de VRAM.

**Otimizações de software nesse regime (40 passos cada, log inteiro):**

| | tok/s |
|---|---:|
| micro-batch 8 · accum 32 | **39,8k** ← melhor |
| micro-batch 16 · accum 16 | 36,1k |
| micro-batch 32 · accum 8 | 36,1k |
| + Liger | 36,1k (**ganho zero**) |
| + torch.compile | **42,1k** (+17%, a única que funcionou) |

Batch maior é **monotonicamente pior** quando a placa está no teto de potência: consome VRAM sem
comprar throughput.

---

## 5. Reprodutibilidade do corpus verificada, não presumida

Subir 43,5 GB a 0,7 MB/s levaria 17 h; refazer a coleta leva ~4 h. Refazer só vale se sair o **mesmo
corpus** — senão é um corpus novo e nenhuma medida anterior serve de comparação.

A cadeia é determinística (percentis de amostra fixa, mesmo `.joblib`, filtro determinístico, dedup
por hash exato, mesmo tokenizador), então dá para **verificar em vez de supor**
(`bee/conferir_corpus.py`):

- `val.bin` inteiro (439 MB — é a cauda de 1% de **cada** shard, toca os 39)
- `train.bin` por 5 janelas de 16 MB em posições fixas (43,5 GB inteiros competiriam com o I/O)

⚠️ **Tamanho em bytes é condição necessária, não suficiente** — por isso o hash.

Verificado **três vezes** no mesmo dia (pod antigo → volume de rede → pod novo), todas byte a byte.

---

## 6. ⭐ A regra de método

O sinal do bug estava no repositório havia dois dias: **`bee/gate_pareado.py` usava `labels=x`
(correto)** e o modelo dele, mesma arquitetura, com **75× menos dados**, media bpb **40% melhor**.

Setenta e cinco vezes mais dado produzindo resultado pior é impossível — e ninguém leu a
impossibilidade. Em vez disso foram construídas cinco hipóteses (geometria, LR, tamanho do modelo,
volume de PT, qualidade do corpus), todas elaboradas, todas medidas com cuidado, **todas sobre um
artefato**.

> **Quando dois experimentos internos se contradizem por uma margem absurda, o defeito está no
> aparato, não no fenômeno. Investigar a contradição ANTES de construir teoria em cima dela.**

### Corolários, cada um pago com tempo

- **Um padrão compatível com várias explicações não prova nenhuma.** Duas conclusões foram declaradas
  e retiradas no mesmo dia por esse erro: o "piso de perplexidade 57" e a "contaminação do Tucano
  provada" (domínio diferente explicava o padrão igualmente bem).
- **Ajuste com zero graus de liberdade descreve, não valida.** `L(D) = E + A·D^-α` tem 3 parâmetros;
  com 3 pontos ele passa exato por construção e não sobra resíduo para conferir. Foi assim que
  nasceu o "piso 57".
- **Guarda fora do fluxo não guarda nada.**
- **Testar com dado real.** A guarda de rótulos passa em silêncio com tokens aleatórios.
- **Não confiar no próprio diagnóstico sem medir.** Os downloads travados foram atribuídos a
  rate-limit do HF e escritos assim no código; a causa real era **oversubscription de threads
  OpenMP/BLAS** (13 processos × 24 threads) sufocando a rede.

---

## 7. O que estava certo o tempo todo

Durante semanas a arquitetura foi suspeita. **Ela nunca foi o problema.**

- **Arquitetura** — `LlamaConfig`, 30 camadas · d_model 576 · intermediate 2048 · 9q/3kv GQA ·
  RMSNorm · RoPE · vocab 32k · seq 2048 · tied embeddings ≈ 151,2M params. É a mesma do SmolLM2-135M
  e do MobileLLM-125M. A suspeita sobre a razão d_model/camadas (19,2 contra 85–130) veio de modelos
  10–100× maiores e **não vale nesta escala** — o MobileLLM existe justamente para mostrar que
  fundo-e-fino ganha abaixo de 1B.
- **LR 3e-3** — Step Law (~3.700 modelos): `η* = 1,79·N^-0,713·D^0,307` → 3,09e-3 para N=151M.
  Erro de 3%.
- **Tokenizador próprio** — 0,2183 tok/byte contra 0,3576 do SmolLM2: **39% mais eficiente em PT**,
  com vocab 7,8× menor que o do Qwen. Foi a primeira coisa a funcionar e continua funcionando.
- **Gates pareados baratos** antes de run longo.
- **Procedência dos dados** como requisito de negócio — licença lida na origem, nunca no rótulo.

---

## 8. Checklist antes de qualquer run longo

- [ ] guarda de convenção de rótulos roda e **aborta** (com dado de treino real)
- [ ] cobertura de amostragem reportada = 100%/época
- [ ] `--dry-run` de 3 passos passa
- [ ] throughput medido em regime (passo ≥20, 3 leituras coincidentes)
- [ ] custo em `$/B tokens`, não `$/h`
- [ ] corpus verificado por hash contra a referência
- [ ] marcos de scaling programados (a curva vira medição, não extrapolação)
- [ ] checkpoint em disco **persistente** — no RunPod, volume de rede; o disco do container morre
      com o pod
