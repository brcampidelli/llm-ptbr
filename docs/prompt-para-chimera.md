# Prompt para a sessão do Chimera-agent

> Copie deste bloco até o fim do arquivo.

---

## Contexto: o que foi medido, e onde

Estou trazendo um achado do **outro projeto do Bruno** — o **Bee**, uma LLM em português
pré-treinada do zero (345M de parâmetros, `BrCamp/bee-350m-pt-base`). Nada disso rodou no
Chimera; é medição feita num modelo pequeno, e trago como **hipótese a testar aqui**, não como
instrução.

Repositório com o código e o relatório: https://github.com/brcampidelli/llm-ptbr
(`docs/relatorio-agentico-2026-08.md`, seção 6c)

## O achado principal

Medi o desempenho de seleção de ferramenta contra o **tamanho do catálogo** apresentado no
prompt — holdout de 536 casos, ferramentas que o modelo nunca viu no treino:

| ferramentas no catálogo | acerto de seleção |
|---:|---:|
| 1–6 | 80,0% |
| 10 | 64,0% |
| **15** | **48,5%** |

⭐⭐ **E um recuperador lexical de ~30 linhas acerta 90,1% no top-1** — sobreposição de palavras
entre o pedido e a declaração da ferramenta (nome + descrição + nomes de argumento), com peso
IDF sobre o próprio catálogo. Determinístico, sem modelo, sem GPU.

Filtrando o catálogo antes de mostrar ao modelo:

| condição (catálogo de 15) | teto do filtro | acerto |
|---|---:|---:|
| catálogo completo | — | 48,5% |
| top-5 filtrado | 96,3% | 73,5% |
| **top-3 filtrado** | 95,0% | **75,2%** |

**+26,7 pp**, pareado +150/−21, McNemar p = 3,3e-25. **Sem treinar nada** — é mudança de harness.

⭐ E **top-3 bate top-5** apesar do recall menor: o ganho de ter menos opções supera a perda do
filtro mais agressivo. O ponto de operação é **filtrar forte**.

## Um segundo achado, que muda onde colocar guardas

As duas capacidades **se dissociam**:

| | catálogo 1–6 | catálogo 15 |
|---|---:|---:|
| *"alguma ferramenta serve?"* (recusar quando não há) | 82,5% | **82,5%** |
| *"qual delas?"* | 80,0% | **48,5%** |

**Decidir se deve agir é robusto ao tamanho do catálogo; escolher qual não é.** Isso valeu nos
dois tamanhos de modelo que testei (151M e 345M), então é propriedade da tarefa, não do modelo.

## ⚠️ O que eu NÃO sei, e por que isso importa aqui

**Tudo acima foi medido num modelo de 345M.** O Chimera roda DeepSeek-V4, Qwen3 e Llama-3.3 via
OpenRouter — modelos duas a três ordens de grandeza maiores. **Não há garantia de que degradem
da mesma forma**, e é plausível que não degradem.

⚠️ Também medi que **escalar não resolveu** no meu caso: de 151M para 345M (2,3× o parâmetro) a
queda relativa foi de 45% para 39% — melhorou pouco e o formato da curva não mudou. Isso é um
indício fraco de que o problema não some só com tamanho, mas **dois pontos não fazem lei de
escala** e eu não extrapolo daí.

## O que eu peço que você faça — nesta ordem

### 1. Medir o catálogo atual do Chimera (5 minutos, sem tocar em nada)

Quantas ferramentas/rotas o Chimera apresenta ao LLM por chamada? Se forem menos de ~8,
provavelmente não há problema a resolver e o resto deste prompt é irrelevante.

Se forem **dezenas**, siga.

### 2. Construir o recuperador e medir só o RECALL primeiro

🔴 **O teto do sistema é o recall do filtro, não o modelo.** Se a ferramenta certa não sobreviver
ao filtro, o caso vira impossível por construção — o gargalo só muda de lugar.

Implementação (é isto, não mais que isto):

- normalizar (minúsculas, sem acento), tokenizar em palavras de 3+ letras;
- descartar palavras funcionais (`de`, `para`, `você`, `preciso`, …);
- calcular IDF **sobre o próprio catálogo** — palavra que aparece em toda ferramenta não
  discrimina e pesa ~0;
- nota de cada ferramenta = soma do IDF das palavras que ela compartilha com o pedido;
- devolver as k melhores.

Referência funcionando: `comeia/eval/recuperar_catalogo.py` no repositório acima.

**Meça `recall@1`, `recall@3`, `recall@5`** num conjunto de pedidos reais do histórico do
Chimera (o `cron_results.jsonl` e os logs do Discord devem ter material). **Não prossiga se o
recall@3 ficar abaixo de ~90%** — significaria que o filtro lexical não serve para este
catálogo, e aí a resposta é um recuperador semântico (embeddings), não este.

### 3. Só então testar ponta a ponta, e medindo os DOIS lados

Compare **catálogo completo** contra **top-3 filtrado**, nos mesmos pedidos, e reporte:

- acerto de seleção;
- ⚠️ **over-calling** — chamou ferramenta quando não devia;
- ⚠️ **under-calling** — recusou quando havia ferramenta que servia.

🔴 **Medir só um lado é o erro clássico aqui.** Um filtro agressivo pode reduzir chamadas
erradas simplesmente porque o modelo passa a recusar mais — o que não é ganho. No meu projeto,
um verificador que parecia bom tinha saldo **−4** por semanas porque só se media o ganho.

⚠️ E espere um imposto que eu medi e confirmei: **a lista filtrada é mais difícil que uma lista
curta aleatória** (73,5% contra 77,2% com 5 ferramentas). O recuperador remove os candidatos
fáceis e deixa os parecidos. Não reporte a diferença bruta contra o catálogo completo sem essa
ressalva.

### 4. Se confirmar, aí sim mudar o `/api/hermes/*` e o roteador

E com o filtro **auditável**: logar quais k ferramentas foram apresentadas em cada chamada, para
que uma falha possa ser atribuída ao filtro ou ao modelo. Sem esse log, os dois erros ficam
indistinguíveis.

## Três outros achados que podem valer aqui

⚠️ Todos medidos no Bee-350M — mesma ressalva de extrapolação.

1. **Token de parada.** Um modelo que emitia a chamada perfeita marcava **0%** porque o token de
   parada não estava ligado: a geração ia até o teto e o parser recebia várias chamadas
   concatenadas. Se o Chimera tem alguma métrica de sucesso de tool-call anormalmente baixa,
   **verifique o terminador antes de culpar o modelo.**

2. **Nome do argumento.** O modelo escrevia `receptor` onde o esquema pedia `recipient` —
   traduzia a chave para português. Restringir a chave ao esquema do catálogo rendeu **+16,4 pp**.
   Se o Chimera valida argumentos, vale checar se rejeições vêm de **nome** de campo e não de
   valor.

3. **Recusa é fórmula barata.** Sob pressão, o modelo recusa em vez de errar — e uma métrica de
   over-calling sozinha leria isso como **perfeita**. Se o Chimera tiver uma métrica de "não
   chamou indevidamente", confirme que existe a métrica gêmea de "deixou de chamar quando devia".

## O que NÃO estou pedindo

⚠️ **Não implemente nada antes do passo 2.** O achado é de um modelo pequeno; o teste de recall
custa minutos e decide se há problema a resolver aqui. Se o catálogo do Chimera for pequeno ou o
recall lexical for ruim, **a resposta correta é não fazer nada** — e isso também é resultado.
