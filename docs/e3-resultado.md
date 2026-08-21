# Estágio 3 — dado: de 7.152 exemplos para 263.971, por US$ 0,92

> **2026-08-21.** O E3 fechou. O gargalo que ele existia para atacar era volume de dado
> (7.152 exemplos para 8 capacidades), e o resultado é **37× mais dado**, descontaminado, com
> a proporção agêntica que o avaliador espera. Custo de GPU: **zero**. Custo de API: **US$ 0,92**.

---

## 1. O que existe agora

| conjunto | exemplos | ataca |
|---|---:|---|
| `structured` | 123.469 | atendimento — `json_ok` **0,0%** no E2 |
| `translation` | 41.647 | os **25 pontos de BLEU** presos atrás do formato de chat |
| `summarization` | 40.267 | resumo — **copia a fonte**, compressão 0,90 contra limite 0,35 |
| `code` | 34.856 | código — **pede esclarecimento** em vez de escrever |
| **agêntico positivo** | 14.003 | `argumentos exatos` **37,6%** |
| **agêntico negativo** | **9.729** | `over-calling` **13,8%** |
| **total** | **263.971** | contra **7.152** do SFT atual |

**Proporção agêntica: 1,44:1** (14.003 positivos / 9.729 negativos) — praticamente a
distribuição que o avaliador do Bee usa (85 tool / 65 texto = 1,31:1).

---

## 2. ⭐ Três classes agênticas, e a terceira foi achada na rejeição

| classe | n | ensina |
|---|---:|---|
| positivo | 14.003 | **chamar** quando precisa |
| recusa | 9.333 | **não chamar** quando não dá |
| **resposta direta** | **396** | **não chamar quando não precisa** |

A terceira não estava no plano. Ela apareceu porque **451 negativos reprovavam
sistematicamente** na validação, e a concentração denunciou o motivo: `calculate_discount`
(62×), `calculate_tax`, `calculate_tip`, `convert_temperature`. Os pedidos eram *"100 °F para
Celsius"* e *"vestido de $100 com 20% de desconto"*.

🔴 **O *function masking* supôs "ferramenta removida ⇒ tarefa impossível".** É falso para
aritmética trivial: o teacher se recusava a dizer "não consigo" **porque ele consegue**. A
rejeição sistemática **era o rótulo**, não o defeito — e responder direto é um sinal melhor
contra over-calling do que recusar.

Validador **espelhado**: onde na recusa a negação é obrigatória, na resposta direta ela é o
defeito (`recusou_o_que_devia_responder` pegou 52 casos).

---

## 3. A qualidade do negativo está toda no distrator

Function masking (receita Hammer) só vale se o distrator for **tentador sem servir**:

- **distrator sorteado** → negativo fácil: removido `get_movie_details` com o usuário
  perguntando de um filme, o catálogo saía com `get_random_joke` e `track_calories`. O modelo
  aprenderia *"assunto diferente = não chamo"*, que não é a causa real do over-calling.
- **distrator atraente demais** → negativo **errado**: removido `generate_qr_code`, o catálogo
  vinha com `generateQRCode`; removido `calculate_bmi`, vinha com `calculate_body_mass_index`
  **e** `calculateBMI`. Ali chamar é a resposta **certa** e o rótulo mente. Dado com rótulo
  invertido é pior que dado ausente.

Regra final: **atração lexical ao pedido, com exclusão de equivalentes por descrição** (nome
não basta — sigla contra nome por extenso é invisível). Resultado medido: **16,0× mais
atraente que o acaso**, com 742 ferramentas removidas distintas.

---

## 4. O que a medição refutou

| eu supus | a medição disse |
|---|---|
| português europeu contaminaria o corpus | **0,0% a 2,5%** — era um artigo de jornal isolado |
| as outras configs teriam redundância como o `function_call` | **0,0% a 0,5%** contra **65,6%** — era exclusiva do agêntico |
| o Hermes-4 serviria de teacher | passou na qualidade, **reprovou na licença** (base Llama 3.1) |
| modelo maior seria melhor teacher | **o mais barato (US$ 0,20) foi o melhor**; dois grandes vazaram cadeia de pensamento |
| a rotação de 7 estilos consertaria diversidade | no pareado, **piorou** (23,8% → 19,2%) |

⭐ **E o número que eu tinha reportado errado:** "oferecem alternativa 49% → 94%". Medido nos
**mesmos 1.154 negativos** e com a **mesma régua**: **85,3% → 93,5%**. Os 49% vinham de uma
lista de 5 palavras-chave; os 94%, de uma de 8. Mudei o instrumento entre as populações e
chamei a diferença de ganho. Ganho real: **+8,2 pp**.

---

## 5. Os bugs que este estágio custou — e a família a que pertencem

| # | sintoma | causa |
|---|---|---|
| 1 | 88,3% de "tools_vazio" | a regex casou com a **menção** literal `<tools></tools>` na explicação, antes do bloco real |
| 2 | 68,7% de negativos duplicados | `rnd.choice` amostrava **com reposição** — a §2 das lições em lugar novo |
| 3 | "40.716 exemplos" | eram **14.003** pares distintos; 65,6% duplicata, um par 969× |
| 4 | job parado 24 min | teto **diário** de 1.000 chamadas nos modelos `:free`; a conta já tinha saldo |
| 5 | 19,6% reprovados na recusa | regex sem acento: `não é possível` não casava com `e possivel` |
| 6 | JSON quebrado ao ler | `splitlines()` parte registro em **U+2028/U+2029**, que `json.dumps` não escapa |
| 7 | 100% "contaminados" | boilerplate do system prompt; **escrevi antes de conferir** e esvaziei 21.223 exemplos |
| 8 | 24,6% "não é português" | o teste exigia **presença de português**; o defeito é **presença de inglês** |
| 9 | regex que não casa com nada | `\b` virou **backspace literal** (0x08) na escrita |

⭐ **Seis dos nove são a mesma família:** *o dado sai, ou o rótulo mente, e nada dá erro.* E
três deles — 5, 8 e o RX_NEGA — são a **mesma lição repetida**: guarda estreita demais não é
"conservadora"; ela descarta dado bom em silêncio, e só se descobre **guardando o que foi
reprovado**.

⚠️ E o de número 7 é o único que não tem desculpa técnica: eu rodei escrita destrutiva na
primeira execução de um script novo. A guarda que ficou (aborta acima de 50% de contaminação)
existe porque eu não parei para olhar.

---

## 6. O que fica para o E4

1. **A mistura.** 263.971 exemplos é muito mais do que o Bee precisa por época; a proporção
   entre capacidades é o objeto do E4, e o método (otimização por perturbação por domínio,
   arXiv:2508.11953) é o único do plano com evidência **abaixo de 1B**.
2. **A proporção agêntica 1,44:1 é ponto de partida, não conclusão.** O E2 mediu over-calling
   em 13,8% e o projeto já mediu que essa proporção o move.
3. **Rotular a origem dos negativos.** Os do Bee são irrelevância genérica; os novos são
   masking difícil. Medir `over_call` separado por tipo, senão não se sabe qual ensinou o quê.
4. **`code` tem p95 de 1.859 tokens** contra `max_seq_len` 2.048. A margem é estreita e a
   guarda de truncamento silencioso precisa estar ligada.
