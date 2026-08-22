# Estágio 4 — a mistura: a lei discorda do estoque, e as réguas não enxergam

> **2026-08-22.** 40 mini-runs, 8 domínios × 5 razões de perturbação, 151,2M tokens em
> 533 min (8,9 h) numa RTX 5090, **zero erros**. O E4 existia para responder duas
> perguntas: *qual mistura de dado maximiza a capacidade* e *loss e régua concordam*.
> Respondeu a primeira. A segunda **não pôde ser respondida** — e o motivo é o resultado.

---

## 1. O que saiu

Mistura ótima para um SFT de 20M tokens, contra o que sairia de simplesmente usar o corpus
inteiro (134,1M tokens, 263.971 exemplos):

| domínio | share natural | **ótimo da lei** | movimento |
|---|---:|---:|---|
| estruturado | 38,12% | **10,30%** | ↓ 3,7× |
| código | 29,72% | 9,82% | ↓ 3,0× |
| resumo | 17,11% | 13,03% | ↓ 1,3× |
| **tradução** | 4,22% | **20,57%** | **↑ 4,9×** |
| agêntico negativo | 4,03% | 13,30% | ↑ 3,3× |
| agêntico positivo | 4,11% | 7,99% | ↑ 1,9× |
| símbolico · texto | 2,69% | *reservado 24,99%* | não otimizável |

⭐ **O maior monte de dado recebe a menor fatia.** `estruturado` tem 51,1M tokens — 38% do
corpus — e a lei pede 10,3%. Nenhuma heurística de "usa o que você tem" chegaria nisso.

Qualidade do ajuste: **R² 0,891 a 0,988** com **35 graus de liberdade** por domínio
(40 pontos, 5 parâmetros). Não é ajuste que descreve por construção.

### ⚠️ A faixa em que isso vale

| orçamento | quem manda |
|---|---|
| até ~27M tokens | **a lei** — nenhum teto binda |
| 50M | tradução e agêntico batem no teto |
| 100M | três no teto; código vai a 31,2% **porque os outros acabaram** |

Acima de ~27M o otimizador para de reportar a lei e passa a reportar o **inventário**.
Tradução tem só 5,66M tokens: a 20,57% ela satura exatamente em 27,5M. Para um SFT maior,
ou se gera mais tradução e agêntico, ou o número perde o sentido.

---

## 2. 🔴 As réguas não resolvem efeito de mistura nesta escala

Quatro das seis réguas deram **0,0 nos 40 braços** — amplitude zero não ajusta lei nenhuma.
Das duas que variaram, o piso de ruído estava medível de graça: **35 dos 40 braços têm dado
de tradução idêntico**, então tudo que eles variam entre si é ruído.

| régua | ruído (35 braços de controle) | sinal (5 braços, 0,5×→3×) | **sinal/ruído** |
|---|---:|---:|---:|
| tradução | 18,7 BLEU | 6,3 BLEU | **0,34** 🔴 |
| instrução | 7,0 pp | 7,0 pp | **1,00** 🔴 |

E o sinal nem é monotônico: o braço com **menos** tradução (0,22M tokens) fez 27,6 BLEU,
**acima** do de 0,90M (25,6).

⭐ **Eu li isso como sinal antes de medir o ruído.** Reportei "tradução responde à
perturbação, 25,6 → 31,9" olhando dois pontos de uma série cujo desvio-padrão de ruído é
3,72. Os 35 braços de controle estavam no mesmo arquivo o tempo todo. É a lição do projeto
em lugar novo: *um padrão compatível com a hipótese não é evidência dela até o piso de ruído
estar medido* — e aqui o piso custava uma linha de código.

**Consequência de método:** a comparação loss × régua que o E4 foi desenhado para fazer
**não pôde ser feita** — não porque discordaram, mas porque o lado da régua não tem sinal
mensurável com mini-runs de 3,8M tokens. Quem quiser comparar precisa de runs maiores ou de
réguas com muito mais itens.

---

## 3. 🔴 O colapso agêntico: o modelo recusa o que tem ferramenta

`agentico` deu **0,0% nos 40 braços**. Verificado em 3 braços de misturas diferentes —
inclusive o de **menos** negativos — e com catálogos e pedidos do próprio gigaverbo, então
**não é estranhamento de catálogo**.

Causa: sob mistura, **recusar é alvo fácil e chamar é alvo difícil**. A recusa é fórmula
(`"sinto muito, mas não"` aparece 847× no conjunto); a chamada exige nome exato, argumentos
exatos, JSON válido. O modelo aprende o barato. Os negativos do E3 ensinaram um *prior* de
recusa dominante.

⚠️ **E o over-call leria 0%.** Número perfeito, comportamento inútil. É o caso mais puro
que o projeto já produziu de métrica que aprova o colapso — e só apareceu porque a régua de
execução foi medida junto.

O que o E3 precisa mudar antes do E5: **muito mais variedade de superfície nos negativos, ou
proporção muito menor**. A proporção 1,44:1 herdada do avaliador não sobrevive à medição.

---

## 4. 🔴 O defeito no ajustador — e por que ele não dava erro

A primeira rodada do ajuste imprimiu oito R² entre 0,50 e 0,64 e uma mistura com três
domínios no teto e três zerados. Parecia um resultado.

`main()` montava o alvo como `metricas[metrica]` — a **loss agregada** — para os oito
domínios. A lei `L_i(N_i, |D_∖i|)` exige `L_i` = loss **do domínio i**, e as seis losses por
domínio (`loss_traducao`, `loss_codigo`, …) estavam no mesmo JSON, sem uso. O código
ajustava **o mesmo vetor `y` oito vezes**, variando só `N_i` e `D_out`: uma curva só, vista
de oito ângulos, imprimindo oito números diferentes que pareciam oito leis.

O mesmo defeito derrubava a normalização por amplitude — `escala[d]` vinha da mesma série
agregada, então os oito fatores eram idênticos e a normalização não normalizava nada.

| | R² antes | R² depois |
|---|---:|---:|
| código | 0,509 | **0,988** |
| resumo | 0,503 | **0,928** |
| estruturado | 0,506 | **0,914** |
| agêntico negativo | 0,603 | **0,909** |
| tradução | 0,535 | **0,891** |

E a mistura mudou de "3 no teto / 3 zerados" para o quadro da §1. **Nada dava erro**: o
script rodava, convergia, imprimia e salvava JSON.

### A guarda que ficou

`alvo_do_dominio()` centraliza a escolha do alvo e **recusa** régua que não mapeia o domínio
(ajustar `L_código` contra BLEU mede transferência, não a lei). Domínio com alvo de
amplitude zero é recusado explicitamente em vez de ajustado.

---

## 5. ⚠️ Dois domínios não puderam ser otimizados

`texto` e `simbolico` não têm holdout limpo — a permutação do E3 podia sortear qualquer
índice, e sorteou. Sem `L_i` não há lei.

🔴 **E se eles simplesmente saíssem da conta, o otimizador os zeraria por falta de medida — e
o zero se disfarçaria de conclusão.** Eles ficam com fatia **reservada** (a do braço de
referência, 12,5% cada) e o simplex fecha no que sobra, com o rótulo `RESERVADO` impresso.
Ausência de medida tem de aparecer como ausência de medida, não como recomendação.

---

## 6. O que fica para o E5

1. **Usar a mistura da §1** para orçamento até ~27M tokens. Acima disso, gerar mais tradução
   e agêntico antes.
2. **Refazer os negativos agênticos** — variedade de superfície, ou proporção bem menor. O
   colapso é o bloqueador do E5, não um detalhe.
3. **Não confiar em régua com mini-run de 3,8M tokens.** Se a comparação loss × régua
   importa, ela custa runs maiores.
4. **Gerar holdout limpo para `texto` e `simbolico`** — hoje eles entram por reserva, não por
   medida.
