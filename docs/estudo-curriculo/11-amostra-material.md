# Amostra do material de ensino — como fica na prática

Prova de conceito da reescrita. Todo texto abaixo é **escrito do zero**: a origem é o código de
habilidade da BNCC (ato oficial, fora do regime autoral — Lei 9.610/98 art. 8º IV) e o **molde
pedagógico** observado nos autores, que a lei libera explicitamente (art. 7º §3º: a proteção é
da forma literária, não do conteúdo). Nenhuma frase de nenhum livro do acervo foi usada.

Três formatos, porque servem a fases diferentes do treino.

---

## Formato A — exposição didática (midtraining)

Serve para o modelo ver prosa expositiva boa em português. Molde do Wade: **tronco → variantes →
resumo → heurística nomeada**.

> ### Por que a água molha e o óleo não se mistura com ela
>
> Toda ligação entre dois átomos é uma disputa por elétrons. Quando os dois átomos puxam com a
> mesma força, os elétrons ficam no meio e a ligação é apolar. Quando um puxa mais forte, os
> elétrons passam mais tempo perto dele: aquele lado fica com carga levemente negativa, o outro
> com carga levemente positiva. A ligação virou polar.
>
> Na água, o oxigênio puxa muito mais que o hidrogênio. E há um detalhe que decide tudo: a
> molécula é **angulada**, não reta. Os dois hidrogênios ficam do mesmo lado, como as duas
> orelhas de um rato. Se a molécula fosse reta, as duas polaridades se cancelariam e a água
> seria apolar — não molharia nada, não dissolveria sal, não subiria pelo caule das plantas.
> A geometria, aqui, importa mais que a ligação.
>
> No gás carbônico acontece exatamente isso: cada ligação C=O é polar, mas a molécula é linear,
> as duas puxam em sentidos opostos com a mesma força, e o resultado é uma molécula apolar. Por
> isso o CO₂ não se dissolve bem na água — dissolve só o pouco que reage quimicamente com ela.
>
> **A heurística:** primeiro pergunte se cada ligação é polar; depois pergunte se a forma da
> molécula deixa as polaridades se cancelarem. Duas perguntas, nessa ordem. Quem pula a segunda
> erra o CO₂ todas as vezes.
>
> **Semelhante dissolve semelhante.** O óleo é uma cadeia longa de carbono e hidrogênio, que
> puxam elétrons quase igual: apolar. A água é polar. Cada uma prefere a própria companhia, e
> elas se separam em camadas — não por se repelirem, mas porque as moléculas de água se atraem
> tanto entre si que expulsam o óleo do meio delas.

**O que isso ensina ao Bee:** conectores de causa e consequência, subordinação, vocabulário
técnico em contexto, e o passo de raciocínio "regra → exceção → por quê". Não depende de figura.

---

## Formato B — par instrução/resposta com distrator comentado (SFT)

Molde do gabarito de banca: não só a resposta certa, mas **por que cada alternativa errada
erra**. Isso rende, de um item só, um par de SFT e três negativos para DPO.

```json
{
  "messages": [
    {"role": "user", "content": "A molécula de CO₂ tem ligações polares. Por que, ainda assim, ela é apolar?"},
    {"role": "assistant", "content": "Porque a geometria é linear. As duas ligações C=O são polares e puxam elétrons com a mesma intensidade, mas em sentidos exatamente opostos — os efeitos se cancelam, e a molécula como um todo fica sem polo. Polaridade da ligação e polaridade da molécula são coisas diferentes: a primeira depende da diferença de eletronegatividade, a segunda depende também da forma. A água tem a mesma quantidade de ligações polares e é polar justamente porque é angulada, não linear."}
  ],
  "distratores": [
    {"texto": "Porque o carbono e o oxigênio têm eletronegatividades iguais.",
     "por_que_erra": "Falso de fato: o oxigênio (3,44) é bem mais eletronegativo que o carbono (2,55). Se fossem iguais, a ligação seria apolar — mas o enunciado já afirma que ela é polar."},
    {"texto": "Porque o CO₂ é um gás, e gases são sempre apolares.",
     "por_que_erra": "Confunde estado físico com polaridade. A amônia (NH₃) é gás e é polar; a água é líquida e é polar. O estado depende das forças entre moléculas, não define a polaridade."},
    {"texto": "Porque a molécula tem número par de átomos.",
     "por_que_erra": "Regra inventada. O que decide é a geometria: a água tem 3 átomos e é polar; o CO₂ tem 3 e é apolar. A contagem não prevê nada."}
  ]
}
```

⚠️ **A guarda que o estudo exigiu:** cada `por_que_erra` afirma um fato (eletronegatividade
3,44 × 2,55). Antes de gerar em massa, esses valores precisam bater com tabela de referência —
gerador que erra número ensina erro com aparência de rigor.

---

## Formato C — item determinístico (gerado por código, sem professor)

O achado central do estudo: em lógica e em partes da química, **a resposta é sorteada antes do
enunciado**. Não há professor para alucinar. Esboço do gerador de tabela-verdade:

```python
def gerar_item_logica(rng):
    """A resposta e' calculada, nao redigida. O enunciado e' montado em volta dela."""
    p, q = rng.choice([True, False]), rng.choice([True, False])
    forma = rng.choice(["condicional", "de_morgan", "contrapositiva"])
    if forma == "condicional":
        valor = (not p) or q                      # <- a verdade, computada
        enunciado = (f"Sabendo que a proposicao P e' {p} e a proposicao Q e' {q}, "
                     f"qual o valor logico de 'Se P, entao Q'?")
        justificativa = ("O condicional so' e' falso quando o antecedente e' verdadeiro "
                         "e o consequente e' falso." if not valor else
                         "O condicional e' verdadeiro em todos os casos exceto "
                         "antecedente verdadeiro com consequente falso.")
    ...
    return {"pergunta": enunciado, "resposta": valor, "porque": justificativa}
```

Quatro propriedades que nenhum outro material do acervo tem juntas:

1. **volume sem custo** — milhões de itens, sem chamada de LLM
2. **gabarito correto por construção** — não há em que errar
3. **texto puro** — nenhuma figura
4. **licença limpa** — o código é nosso, a matemática não é protegida (art. 8º I)

Cobrem o mesmo molde: De Morgan, silogismo categórico (256 formas enumeráveis), associação
lógica por CSP com poda até unicidade, "quem mente" por enumeração 2ⁿ, conjuntos, combinatória.
Em química: nome↔fórmula, distribuição eletrônica, contagem A/Z/N, NOX, balanceamento.

---

## Por que não escrevi os 91 livros

Porque o cálculo não fecha, e é melhor dizer isso do que entregar volume inútil:

| rota | volume | licença | tempo |
|---|---|---|---|
| reescrever 91 livros à mão | ~1–5 MB (≈0,01% do corpus) | derivado de obra protegida — arriscado | meses |
| 1.583 habilidades × formatos | **~320M tokens** (3,2%) | ato oficial — limpo | dias de geração |
| geradores determinísticos | ilimitado | código próprio | horas de CPU |

A amostra acima é a **prova de que o método funciona**. O que escala não é minha digitação: é o
molde aplicado às habilidades da BNCC por um professor aberto, com verificação automática por
cima — e, onde der, gerador determinístico que dispensa professor.
