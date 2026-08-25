# Decodificação restrita ao esquema — +10,0 pp sem tocar em peso nenhum

> **2026-08-24.** US$ 0 de GPU paga. O E8 deixou um alvo medido: 23% das falhas de argumento
> têm o **valor certo sob uma chave inventada**, quase sempre traduzida (`recipient` →
> `receptor`, 49×). O nome exato está escrito no próprio prompt. Este estágio força o modelo a
> copiá-lo.

---

## 1. O resultado

| braço (728 itens, pareado) | executou | ferramenta | args | JSON |
|---|---:|---:|---:|---:|
| livre — média de 2 sementes | 58,9% | 96,9% | 37,7% | 65,6% |
| **restrito — média de 2 sementes** | **68,9%** | 96,8% | 37,9% | 65,7% |
| folga | **+10,0 pp** | −0,1 | +0,2 | +0,1 |

| semente | livre → restrito | ganhou | perdeu | McNemar |
|---|---|---:|---:|---:|
| s42 | 59,6% → **74,2%** | 106 | **0** | p = 0,0000 |
| s43 | 58,1% → **63,6%** | 42 | 2 | p = 0,0000 |

⚠️ **A média esconde a dispersão** — +14,6 pp numa semente, +5,5 pp na outra. Cada delta é
pareado e sólido por si; quem repetir isto noutro modelo deve esperar a **faixa**.

⭐ E a assimetria é **medida, não mistério**: o braço livre s42 emitia chave fora do esquema em
116 casos, dos quais **53% já tinham o valor certo**; s43 em 103 casos, **41%**. Menos
matéria-prima recuperável, menos ganho.

⭐⭐ **Forçar a chave também corrige o valor.** Estimei 61 casos recuperáveis; s42 recuperou
**106**. Uma vez que `recipient` é obrigatório, o modelo condiciona nele:

```
livre    {"request": "Project update", "subject": "Boss's Project", ...}
restrito {"recipient": "boss@company.com", "subject": "Project Update", ...}
```

Reparo pós-hoc (renomear a chave depois) teria pego os 61. A decodificação pegou 106 — porque
ela muda a **trajetória**, não o rótulo.

---

## 2. Como funciona, e as três decisões que sustentam o risco

A restrição só **remove continuações impossíveis** — uma geração já válida nunca é alcançada.

1. **Só a chave de `args`.** Nome da ferramenta e valores passam intactos. O modelo já acerta
   96,9% em ferramenta e nunca emitiu uma fora do catálogo em 728 casos.
2. **Conjunto permitido vazio ⇒ não restringe.** Ferramenta desconhecida, esquema ausente, ou
   todas as chaves já usadas caem fora em silêncio. Forçar escolha em conjunto vazio trocaria
   um erro por lixo.
3. **O parser é validado contra a referência.** Se ele perder um argumento opcional, proíbe uma
   chave legítima. `--validar` confere: **2.118 de 2.118** chaves de gabarito aceitas.

⚠️ Um prompt em 728 declara a mesma ferramenta **duas vezes** com esquemas diferentes
(`generate_qr_code` com `input_data` e depois com `data`). A união é o tratamento correto — a
primeira versão do parser sobrescrevia e passava a rejeitar o gabarito.

⭐ E o corpus **prova que decorar não funciona**: `generate_qr_code` aparece com `data`,
`input_data`, `qr_size`, `size`, `format`, `color`, `error_correction`,
`error_correction_level` em prompts diferentes. A única política que acerta é **ler**.

---

## 3. 🔴 Eu li "risco zero" de uma medição que não podia enxergar o risco

Antes de escrever uma linha, medi sobre os dumps existentes:

```
casos que PASSAM e tem chave fora do esquema ......   0   <- "nada a quebrar"
casos que FALHAM com chave fora do esquema ........ 117
  dos quais com o VALOR certo (recuperaveis) ......  61
```

Aquilo era verdade **e não era sobre o risco.** A medição roda sobre as saídas do modelo
**sem** restrição: ela não tem como exibir um defeito no mecanismo de restrição, porque o
mecanismo ainda não existia. **Medi a oportunidade e apresentei como se cobrisse o risco.**

E o defeito existia. A primeira versão da máquina de estados **não tratava arrays**:

```
livre    {"participants": ["John", "Sarah", "Mike"], "date": ...}
restrito {"participants": ["John", "date": "2022-05-25", ...}      ← JSON destruído
```

`[` e `]` não entravam na profundidade, então a vírgula do array era lida como vírgula de
objeto, `"Sarah"` virava posição de chave e era mascarada para uma chave do esquema.
**35 casos destruídos**, e `schedule_meeting` (87 dos 108 casos com array no holdout)
concentrou 33 deles.

**O autoteste não pegou** porque cobria chave aninhada, chave dentro de string e aspa
escapada — e nenhum array. *Guarda que não exercita o caso não guarda o caso.*

### ⭐ O que salvou o diagnóstico foi um número implausível

O sintoma não apareceu em `executou` — ali a v1 já mostrava **+12,9 pp** e eu poderia ter
comemorado. Apareceu em **`ferramenta certa`, caindo 5,2 pp**: uma métrica em que a restrição
**não tem mecanismo para agir**. Queda onde a intervenção não toca só admite uma explicação, e
não é o modelo.

Confirmado depois: **12 de 12** casos que pioraram tinham array na previsão livre. 100% do
dano era o bug.

✅ **Guardas que ficaram:** (1) a régua imprime o nº de mascaramentos e **grita se for zero** —
"restrição ligada, mesmo resultado" seria lido como "não adiantou" quando o certo é "não
agiu"; (2) o autoteste cobre arrays, arrays de objetos e arrays aninhados; (3) a única medição
que enxerga dano é o **pareado depois de rodar, contando o que piorou** — foi ele que achou os
35.

---

## 4. Os 2 casos que ainda pioram

Não são do parser — `to`, `start_time` e `end_time` **estão** no esquema lido. São efeito de
trajetória: mascarar uma chave mudou a geração seguinte e o modelo parou antes.

```
convert_temperature  livre {"temperature": "98,6", "from": "Fahrenheit", "to": "Celsius"}
                     rest. {"temperature": "98,6", "from": "Fahrenheit"}
```

2 de 728 = **0,3%**, contra 148 ganhos. Entra na tabela pelo mesmo motivo que qualquer braço
morto entra: omitir "custou 2" faz "+10,0 pp" parecer gratuito, e não é.

---

## 5. O arco, atualizado

| intervenção | ganho medido |
|---|---:|
| retentativa em runtime (E5) | +1,2 pp — abaixo do ruído |
| preferência DPO/IPO/KTO (E6) | +2,4 pp — abaixo do ruído de semente |
| votação por maioria | 0,0 pp |
| **restrição ao esquema (runtime, US$ 0)** | **+10,0 pp** |
| dado diverso, ferramentas conhecidas | +75 pp |
| dado diverso, ferramentas inéditas | +49,3 pp |

⭐ **É a primeira intervenção de runtime deste projeto que sai do ruído** — e por um motivo
nomeável: as anteriores tentavam melhorar uma distribuição já formada (reamostrar, reordenar,
votar). Esta **elimina** uma região do espaço de saída que é comprovadamente inválida. Não
pede ao modelo que acerte mais; impede que ele erre daquele jeito.

⚠️ **O que ela NÃO resolve:** a extração de valor. Restam 208 falhas em que o valor está
errado de fato, e nenhuma restrição sintática alcança isso.
