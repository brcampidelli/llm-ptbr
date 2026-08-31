# Fase 2 — as três capacidades que estavam em zero (E20 → E24)

> **O ponto de partida:** `resumo`, `atendimento` e `código` marcavam **0,0% em todos os
> artefatos** do projeto — base de 151M, base de 345M, e13, C-full e todas as sementes. E nenhuma
> delas jamais teve corpus de treino: todo o pós-treino do Bee-350M foi agêntico.
>
> **O resultado:** ⭐⭐ **duas das três agora passam do seu piso trivial**, e a terceira teve o
> gargalo medido eliminado.
>
> | | antes | **E24** | piso |
> |---|---:|---:|---:|
> | **resumo** | 0,0% | ⭐ **58,7%** | **51,3%** ✅ |
> | **atendimento** | 0,0% | ⭐ **67,6%** | **60,4%** ✅ |
> | **código** pass@1 | 0,0% | 0,2% | — |
> | código — **sem código extraível** | **876/877** | 🔴 **0/877** | — |
>
> Custo total: **US$ 1,20** de professor e ~10 h de GPU local.

---

## A sequência, e o que cada passo mediu

| | corpus | dose | o que se aprendeu |
|---|---|---:|---|
| **E20** | agêntico + 291 resumo | 2,6% | resumo mal se move; agêntico **não paga** |
| **E21** | agêntico + 773 resumo | 6,5% | resumo → 14,7%; 🔴 agêntico **paga 9,0 pp** |
| **E22** | adapter de TEXTO separado | — | resumo → **33,3%**, agêntico **intacto** |
| **E23** | + 957 atendimento | 14,9% | atendimento → **65,2%**, resumo se mantém |
| **E24** | + 378 código | 5,9% | resumo → **58,7%**, atendimento → **67,6%**, código emite |

Todos com **698 passos** — o mesmo orçamento de treino em oito corpora consecutivos. Só o corpus
muda, então a diferença é atribuível ao dado.

---

## ⭐⭐ O achado central: dose dentro custa, adapter separado não

| | resumo `útil` | macro agêntica |
|---|---:|---:|
| C-full — 1 adapter, só agêntico | 0,0% | **76,8% ± 0,76** |
| E21 — 1 adapter, resumo a 6,5% | 14,7% | 🔴 **74,4%** |
| **E22 — 2 adapters + roteador** | **33,3%** | ⭐ **76,8%** |

**"Capacidade é disputada" (E2) vale**, e o E20 só não mostrou porque a dose era pequena demais
para exibir o custo. Em adapter separado o mesmo dado rende **2,3× mais** e custa **zero**.

⚠️ Roteador determinístico de 30 linhas: **954/954**. E esse é o número **menos** interessante —
o par é separável por uma frase quase única. O que o torna honesto é que os exemplos de texto
carregam catálogo de ferramentas no `system` **de propósito** (§2u), então ele é obrigado a ler
o pedido.

---

## 🔴 Código: o gargalo mudou de lugar, e isso é o resultado

| | sem código extraível | erro de execução | assert falhou | pass@1 |
|---|---:|---:|---:|---:|
| e13 (3 sementes) | **876–877** | 0–1 | 0 | 0,0% |
| C-full (3 sementes) | **856–874** | 3–21 | 0 | 0,0% |
| ⭐ **E24** | 🔴 **0** | 457 | **416** | **0,2%** |

⭐⭐ **De 876 respostas sem código para zero.** O modelo emite bloco ```python em **877 de 877**
— o gargalo que todos os artefatos anteriores mediam **desapareceu**. Ele saiu de *"não escreve
código"* para *"escreve código que roda e erra"*, e as falhas são de iniciante:
`NameError: name 'N' is not defined. Did you mean: 'n'?`

⚠️ **Mas pass@1 = 0,2% (2 de 877) não é "código resolvido"** — é formato resolvido e lógica não.
E era previsível: a dose foi **5,9%**, a menor das três, com **378 problemas distintos**.

⚠️ **E código é a única das três sem piso trivial**, então a pergunta *"isso é bom?"* não se
responde sozinha aqui como nas outras duas.

---

## A receita, e as três guardas que a fizeram funcionar

Para cada capacidade: **a régua vira a guarda da geração**, e a guarda é **validada contra o
estado quebrado** antes de gastar.

| capacidade | a guarda | força |
|---|---|---|
| resumo | compressão + invenção medidas pelos verificadores da própria régua | reprova **300/300** quando recebe a fonte inteira |
| atendimento | §2n — todo valor da referência **aparece na mensagem** | **0/300** falsos positivos |
| **código** | ⭐ **o interpretador**: a solução passa nos próprios testes | reprovou **252 de 900** do professor |

⭐ Código tem a guarda mais forte das três porque **se executa** — não há critério a arbitrar. E
reaproveita `run_tests` da própria régua (subprocesso isolado, timeout, padrão proibido) em vez
de um executor novo: dois executores para a mesma coisa seriam um defeito de aparato esperando.

**As outras peças, em todas as três:**
- **§2u** — catálogo de ferramentas no `system` de todo exemplo, para não criar atalho superficial;
- **§2o** — fonte disjunta do holdout: texto real do fineweb-2 (resumo), mensagens escritas pelo
  professor (atendimento), problemas novos (código). **Nunca** o gerador do holdout;
- **§2g** — o `PEDIDO` é copiado da régua, não reescrito;
- **§2w** — valores e itens **distintos**, contados: 900 tuplas distintas no atendimento; e o
  corpus de código foi **dedupado de 589 linhas para 378 funções distintas** antes do treino.

---

## 🔴 Dois defeitos meus, e o que os pegou

**1. A guarda do atendimento criava viés correlacionado ao rótulo.** Escrevi uma regra para o
professor não "entregar o rótulo de bandeja": rejeitar a mensagem se contivesse palavra do nome
da intenção. Ela reprovou **71% das gerações** e deixou **cinco das dez intenções com zero
exemplos** — `cancelar_pedido`, `rastrear_pedido`, `segunda_via_boleto`, `trocar_produto`,
`cancelar_assinatura`.

O motivo é óbvio depois de ver: **um cliente que quer cancelar um pedido escreve "cancelar meu
pedido"**. Não é vazamento de rótulo, é português. E o holdout tem a mesma propriedade — *"Perdi
o **boleto** do **pedido** BR-292042"* é o item de `segunda_via_boleto`. A guarda fazia o treino
vir de um **processo diferente** do teste (§2g), com viés de seleção **correlacionado ao rótulo**
(§2u ao contrário).

⭐ **O que pegou foi olhar a distribuição por classe, não a taxa agregada.** 23% de aceitação
parecia "professor ruim"; a tabela por intenção mostrou cinco zeros, que é uma assinatura
completamente diferente. Sem decompor, eu teria aumentado o `--n` e gerado 4× mais dado
enviesado. Corrigida: **95,7%** de aceitação, 10 de 10 intenções, menor classe com 83.

**2. A guarda de cobertura do resumo estava no eixo errado.** Rejeitava 26% das gerações por
cobertura numérica quando `cobriu` falhava em apenas 17/150 — **compressão** é que era o
gargalo. Filtrar no eixo errado matava de fome o sinal. Afrouxada, a aceitação subiu de 47,9%
para 54,3%.

---

## ⚠️ O que fica em aberto

1. **Uma semente em tudo.** Pela §2x isso é direção, não folga.
2. **O salto do resumo de 36,0% para 58,7% ao acrescentar CÓDIGO ao corpus** é grande demais
   para eu atribuir a mecanismo. Pode ser dose, pode ser semente. **Não vou explicá-lo sem
   medir.**
3. `sem_numero_inventado` **regrediu três vezes seguidas** quando a compressão apertou (14 → 36
   → 37 falhas). O padrão é consistente e merece virar item de checklist.
4. **A dose de código é a menor das três** (5,9%, 378 distintos). Se `pass@1` importa, o próximo
   passo é mais problemas distintos — não mais linhas.
5. O adapter de texto foi medido em **três capacidades**; as outras seis dele não foram.
6. ⚠️ E o custo real da arquitetura: **dois adapters em memória** e um roteador que tem de estar
   certo — o adapter de texto dá **0,0% e 100% de under-calling** no agêntico, então errar o
   roteamento é caro.
