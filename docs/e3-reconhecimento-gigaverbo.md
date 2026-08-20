# E3 — o que o `gigaverbo-v2-sft` realmente tem, medido antes de baixar

> **2026-08-20.** Sonda por amostragem via API do datasets-server, 200 linhas por config,
> **US$ 0 e nenhum download**. O plano do E3 dizia "baixar o dataset e usar as configs que
> mapeiam nas capacidades". Mapear por **nome** não vê nada do que está abaixo.

---

## 1. Procedência — a verificação que quase reprovou o dataset por engano

O README declara, na origem: **"entirely composed of LLM-generated data"**. Prompts em inglês
traduzidos para PT com **Qwen2.5-32B-Instruct**, boa parte dos exemplos gerada pela série
**Qwen2.5**, filtragem de qualidade pelo mesmo modelo, template adaptado do Qwen3.

A memória do projeto dizia `ToS PERMITE destilar (≠ Qwen)` — e por ela o dataset seria
rejeitado. 🔴 **A memória estava escrita de um jeito que bloqueia caminho legítimo.**

| instrumento | o que restringe |
|---|---|
| **ToS da API hospedada** (DashScope / Alibaba Cloud) | proíbe destilação |
| **Pesos abertos** Qwen2.5-32B-Instruct e Qwen3-4B-Base | **Apache-2.0** — verificado na origem, sem cláusula anti-destilação, sem restrição de uso de saída |

⭐ **Licença de pesos ≠ ToS de API.** Verificar qual dos dois se aplica antes de descartar. A
memória foi corrigida.

---

## 2. O mapa medido das cinco configs que interessam

| config | linhas | score mediano | ≥4 | tokens (mediana) | turnos |
|---|---:|---:|---:|---:|---:|
| **function_call** | 45.891 | **4,99** | **88,5%** | 621 | 7 |
| **translation** | 45.204 | **4,95** | **97,0%** | 157 | 3 |
| **structured** | 163.542 | **4,73** | **76,5%** | 431 | 3 |
| code | 80.774 | 3,94 | 42,0% | 1009 | 3 |
| summarization | 128.669 | 3,84 | 28,0% | 631 | 3 |

⚠️ **As duas configs de pior qualidade pelo classificador do próprio dataset são justamente
duas dos nossos três zeros** (código e resumo). Filtrar por `instruct_score ≥ 4` ainda deixa
~34.000 de resumo e ~33.900 de código — volume não é o problema; a expectativa é que precise.

---

## 3. Três suspeitas levantadas na prévia — duas caíram, uma se confirmou

### 3.1 ❌ Português europeu — falso alarme

A primeira prévia de resumo veio com *"vivia numa **cave**"*, *"numa **quinta**"*, *"**está a
ser** investigado"*. Medido em 200 linhas por config: **PT-PT em 0,0%** (function_call, code,
structured), **2,5%** (summarization). Era um artigo de jornal português isolado. Preocupação
retirada.

⭐ Vale o registro do método: um exemplo chamativo gerou uma hipótese plausível e falsa. O que
a derrubou foi contar, não olhar mais exemplos.

### 3.2 ✅ Convenção de chamada é outra — e é **uniforme**

**200/200 em estilo Hermes/Qwen:** `<tools>` em XML no sistema, resposta em
`<tool_call>{"name":…,"arguments":{…}}</tool_call>`, retorno em `<tool_response>`.

O Bee emite JSON puro `{"tool":…,"args":{…}}` e o avaliador só aceita esse. Misturar as duas
ensinaria duas gramáticas, e o efeito sairia medido como *"o dado piorou o modelo"*.

⭐ A uniformidade é boa notícia: **um único conversor resolve 100%**, é trabalho mecânico.
Note que `<tool_response>` traz `repr` de dict Python (`{'password': '...'}`), não JSON —
aspas simples. O conversor tem de normalizar isso também.

### 3.3 ⚠️ Ensina a pedir esclarecimento antes de chamar — **24,5%**

```
[user]      Eu preciso de uma nova senha. Você pode gerar uma para mim?
[assistant] Claro. Quanto tempo você gostaria que sua senha tivesse?
```

Em **48 de 196** diálogos com chamada, o assistente pede esclarecimento antes de agir. É
exatamente o modo de falha que o E2 diagnosticou no Bee: diante de uma assinatura de função
**completa**, o modelo pede o que já está no prompt.

⚠️ Nem todo caso é ruim — nos exemplos acima o usuário realmente não informou o comprimento.
Mas 24,5% é fatia grande o bastante para deslocar o comportamento, e é **filtrável**.
Descartando-a sobram ~34.600 exemplos: ainda **23× os 1.495** que o Bee tem hoje.

---

## 4. 🔴 O achado que muda o desenho do E3: o dataset é 98% positivo

**196 de 200** diálogos de `function_call` contêm uma chamada. Só **2%** são casos em que a
resposta certa é **não chamar nada**.

O projeto já pagou por isso uma vez: colher só um lado deslocou a proporção de tool de 59,3%
para 75,8% e o **over-calling subiu +7,6 pp**. O E2 acabou de medir over-calling em **13,8%**
(era 0% no baseline apenas porque o modelo não chamava nada).

Somar ~34.600 positivos puros levaria a proporção do conjunto agêntico para ~97%. **A previsão
é que o over-calling piore muito**, e o ganho em `argumentos exatos` viria acompanhado de uma
regressão em segurança que só apareceria depois de treinar.

⭐ **Consequência de desenho, não de execução:** para cada lote de positivos que entrar, entra
um lote de **negativos casados** — a receita Hammer (arXiv:2410.04587) que o plano já previa,
com irrelevância + function masking. Esses negativos **não existem no gigaverbo** e terão de
ser gerados.

---

## 5. O que isto decide

1. **Baixar 5 configs, não 12.** `function_call`, `translation`, `structured`, `code`,
   `summarization` somam ~464K linhas e ~576 MB, contra 4,4 GB do conjunto. `retrieval` e
   `general` são 3,2M linhas (78% do dataset) e não atacam buraco nenhum do E2.
2. **Filtrar por `instruct_score ≥ 4`** antes de qualquer coisa. Sobra volume em todas.
3. **Escrever o conversor de convenção** Hermes XML → JSON do Bee, com normalização do
   `tool_response` (repr → JSON). Um único conversor, 100% de cobertura.
4. **Filtrar os 24,5% que pedem esclarecimento antes de chamar**, e medir de novo depois.
5. **Gerar os negativos casados antes de treinar qualquer coisa** — a proporção
   positivo/negativo é parâmetro de desenho, e o projeto já sabe o preço de errá-la.
6. **Descontaminar contra os holdouts** (`04_decontaminate.py`) antes de treinar. Não
   negociável.

⚠️ E uma nota de dimensionamento: `code` tem **1009 tokens de mediana**, contra 603 do grupo
simbólico atual do Bee. `max_seq_len` está em 2048 e a guarda de truncamento silencioso do
`sft_qlora.py` já aborta se perder >1% dos exemplos — mas a margem encolheu, e é para
conferir, não para supor.
