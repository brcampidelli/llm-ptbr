"""Gera `benchmarks/aritmetica_pt.jsonl` — aritmetica de multiplos passos em PT-BR.

⭐ POR QUE ESTE GERADOR EXISTE (e o dataset nao foi escrito a mao)

  O dataset decide um GATE: se `pass@256` do Bee-350M base ficar abaixo de 3%, matematica
  e' formalmente encerrada como capacidade nos pesos e o orcamento e' realocado. Um gabarito
  errado aqui nao produz um numero ruim — produz uma DECISAO errada sobre uma capacidade
  inteira, e ninguem volta para conferir depois.

  Este projeto ja pagou exatamente essa conta: 35 de 85 referencias eram impossiveis por
  construcao, a taxa medida saiu 23,5% quando a real era 57,6%, e o defeito estava no
  avaliador — nao no modelo. O aprendizado que sobrou: *executar o gabarito antes de carregar
  qualquer modelo*.

  Aqui a guarda e' mais forte que executar depois: o gabarito e' correto POR CONSTRUCAO.
  O enunciado e a expressao saem dos MESMOS parametros sorteados, e a resposta e' o resultado
  de avaliar a expressao — nunca uma conta feita a mao. Nao existe passo onde um humano (ou um
  modelo) digita "42" e torce para estar certo.

  O que a construcao NAO garante e' a semantica: se o texto do template descreve outra conta
  que nao a da expressao, todas as instancias daquela familia ficam erradas juntas. Por isso
  cada familia e' auditada a mao uma vez, e `validar_aritmetica.py` imprime os literais da
  expressao que NAO aparecem no enunciado — o sintoma barato de texto e conta terem se soltado.

⭐ REGRAS QUE AS INSTANCIAS OBEDECEM (rejeitadas e re-sorteadas se falharem)
  - resposta com no maximo 2 casas decimais (nada de dizima periodica no gabarito)
  - resposta positiva e plausivel na faixa do tema
  - 2 a 4 operacoes encadeadas, contadas pela AST (nao declaradas a mao)
  - nenhum enunciado repetido; nenhuma resposta repetida mais de 4x em 200 itens
    (mantem a concentracao abaixo dos 5% que o validador vigia — um conjunto onde
    "42" resolve 1 em cada 10 itens mede chute, nao aritmetica)
  - contagens sempre >= 2, para o portugues nao exigir concordancia no singular

Uso:
    python comeia/eval/gerar_aritmetica_pt.py            # 200 itens, semente 20260819
    python comeia/eval/gerar_aritmetica_pt.py --n 300 --semente 7
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ / "benchmarks" / "aritmetica_pt.jsonl"

# Nos permitidos numa expressao do gabarito. Qualquer outra coisa (chamada de funcao,
# atributo, nome) e' recusada: a expressao tem de ser aritmetica pura e auditavel a olho.
_NOS_OK = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
)


# --------------------------------------------------------------------------------------
# nucleo: avaliar e contar passos pela ARVORE, nunca pela contagem manual
# --------------------------------------------------------------------------------------

def avaliar(expr: str) -> float:
    """Avalia a expressao aritmetica. Recusa qualquer no que nao seja aritmetica pura."""
    arvore = ast.parse(expr, mode="eval")
    for no in ast.walk(arvore):
        if not isinstance(no, _NOS_OK):
            raise ValueError(f"no proibido em {expr!r}: {type(no).__name__}")
    return eval(compile(arvore, "<gabarito>", "eval"), {"__builtins__": {}}, {})


def contar_passos(expr: str) -> int:
    """Numero de operacoes = numero de nos BinOp na arvore. Medido, nao declarado."""
    return sum(1 for no in ast.walk(ast.parse(expr, mode="eval")) if isinstance(no, ast.BinOp))


def limpo(v: float) -> float | int | None:
    """Devolve o valor arredondado a 2 casas se ele JA e' exato ate 2 casas; senao None.

    O `None` e' o sinal de rejeicao: divisao que gerou dizima nao vira gabarito, porque
    a resposta do modelo ("33,33" contra 33.333...) viraria uma discussao de tolerancia
    em vez de uma medicao de aritmetica.
    """
    if v != v or v in (float("inf"), float("-inf")):
        return None
    r = round(v, 2)
    if abs(v - r) > 1e-9:
        return None
    return int(r) if abs(r - round(r)) < 1e-9 else r


def num(v: float | int) -> str:
    """Formata um numero para DENTRO da expressao Python (ponto decimal)."""
    return str(int(v)) if abs(v - round(v)) < 1e-9 else str(round(v, 2))


def brl(v: float | int) -> str:
    """Formata dinheiro para DENTRO do enunciado, no padrao brasileiro: 1.234,56."""
    return f"{v:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


# --------------------------------------------------------------------------------------
# familias de problemas
# Cada funcao sorteia parametros e devolve (enunciado, expressao, tema) ou None (rejeita).
# O enunciado e a expressao sao formatados das MESMAS variaveis — e' isso que impede
# o texto e a conta de discordarem.
# --------------------------------------------------------------------------------------

def _nota(total: float) -> float | None:
    """Menor cedula/combinacao redonda maior que o total, para o troco fazer sentido."""
    for n in (20, 50, 100, 200, 500, 1000):
        if n > total:
            return n
    return None



def t01_troco_desconto(r):
    q = r.randint(3, 9)
    p = r.choice([12.0, 18.5, 19.9, 24.5, 27.0, 32.9, 35.0])
    d = r.choice([5, 8, 10, 12, 15])
    total = q * p - d
    if total <= 20:
        return None
    nota = _nota(total)
    if nota is None:
        return None
    txt = (f"Marcos comprou {q} camisetas que custam R$ {brl(p)} cada. Na hora de pagar, "
           f"o vendedor deu R$ {brl(d)} de desconto sobre o valor total. Marcos pagou com "
           f"uma nota de R$ {brl(nota)}. Quantos reais ele recebeu de troco?")
    return txt, f"{num(nota)} - ({q}*{num(p)} - {num(d)})", "compras"


def t02_feira_dois_itens(r):
    a, b = r.randint(2, 6), r.randint(2, 7)
    pa = r.choice([4.5, 5.0, 6.9, 7.5, 8.0, 9.9])
    pb = r.choice([3.0, 3.5, 4.9, 6.0, 11.5])
    if pa == pb:
        return None
    txt = (f"Na feira, dona Cleusa comprou {a} quilos de tomate a R$ {brl(pa)} o quilo e "
           f"{b} quilos de cebola a R$ {brl(pb)} o quilo. Quantos reais ela gastou ao todo?")
    return txt, f"{a}*{num(pa)} + {b}*{num(pb)}", "feira"


def t03_onibus(r):
    i = r.randint(22, 48)
    d1 = r.randint(3, 11)
    s1 = r.randint(2, 14)
    d2 = r.randint(3, 12)
    if i - d1 + s1 - d2 < 4:
        return None
    txt = (f"Um ônibus saiu do terminal com {i} passageiros. No primeiro ponto desceram {d1} "
           f"pessoas e subiram {s1}. No segundo ponto desceram outras {d2} pessoas e não subiu "
           f"ninguém. Quantos passageiros continuaram no ônibus?")
    return txt, f"{i} - {d1} + {s1} - {d2}", "transporte"


def t04_escola_turmas(r):
    t = r.randint(4, 12)
    a = r.randint(18, 34)
    f = r.randint(5, 25)
    n = r.randint(2, 9)
    if t * a - f + n < 20:
        return None
    txt = (f"Uma escola tem {t} turmas com {a} alunos matriculados em cada uma. Hoje {f} desses "
           f"alunos faltaram, e {n} alunos novos, que não estavam matriculados antes, "
           f"assistiram à aula. Quantos alunos estão presentes na escola hoje?")
    return txt, f"{t}*{a} - {f} + {n}", "escola"


def t05_salario_semana(r):
    h = r.randint(4, 9)
    d = r.choice([4, 5, 6])
    v = r.choice([14.0, 15.5, 18.0, 22.5, 25.0])
    x = r.choice([20, 32, 45, 60])
    total = h * d * v - x
    if total <= 50:
        return None
    txt = (f"Joana trabalha {h} horas por dia, {d} dias por semana, e recebe R$ {brl(v)} por "
           f"hora trabalhada. No fim da semana, a empresa desconta R$ {brl(x)} de "
           f"vale-transporte. Quantos reais Joana recebe nessa semana?")
    return txt, f"{h}*{d}*{num(v)} - {num(x)}", "trabalho"


def t06_desconto_percentual(r):
    p = r.choice([180, 240, 320, 450, 600, 750, 890, 1200])
    pct = r.choice([10, 15, 20, 25, 30, 40])
    if limpo(p * pct / 100) is None:
        return None
    txt = (f"Uma bicicleta custa R$ {brl(p)}. Na promoção de aniversário da loja, ela sai com "
           f"{pct}% de desconto sobre esse preço. Quantos reais custa a bicicleta na promoção?")
    return txt, f"{p} - {p}*{pct}/100", "compras"


def t07_combustivel(r):
    km_l = r.choice([8, 10, 12, 14, 15])
    voltas = r.randint(4, 18)
    dist = km_l * voltas
    pr = r.choice([5.5, 5.9, 6.2, 6.5, 7.0])
    if limpo(dist * 2 / km_l * pr) is None:
        return None
    txt = (f"O carro de Rafael percorre {km_l} quilômetros com 1 litro de gasolina. Ele vai até "
           f"uma cidade que fica a {dist} quilômetros de distância e depois volta pelo mesmo "
           f"caminho. A gasolina custa R$ {brl(pr)} o litro. Quantos reais Rafael gasta de "
           f"gasolina na viagem inteira?")
    return txt, f"{dist}*2/{km_l}*{num(pr)}", "viagem"


def t08_rateio_conta(r):
    n = r.choice([3, 4, 5, 6, 8])
    base = r.randint(12, 40) * n
    g = r.choice([0.1, 0.2]) * base
    if limpo(g) is None or limpo((base + g) / n) is None:
        return None
    txt = (f"{n} amigos jantaram juntos e a conta do restaurante deu R$ {brl(base)}. Eles "
           f"acrescentaram R$ {brl(g)} de gorjeta e dividiram o valor final em partes iguais. "
           f"Quantos reais cada um pagou?")
    return txt, f"({num(base)} + {num(g)}) / {n}", "lazer"


def t09_estoque_caixas(r):
    c = r.randint(5, 24)
    u = r.choice([6, 10, 12, 20, 24])
    v = r.randint(20, 90)
    d = r.randint(3, 18)
    if c * u - v - d < 10:
        return None
    txt = (f"Uma papelaria recebeu {c} caixas com {u} canetas em cada caixa. Durante o mês ela "
           f"vendeu {v} canetas e devolveu {d} canetas com defeito para o fornecedor. Quantas "
           f"canetas sobraram no estoque?")
    return txt, f"{c}*{u} - {v} - {d}", "compras"


def t10_padaria_troco(r):
    n = r.randint(2, 6)
    pd = r.choice([9.0, 10.5, 12.0, 14.4])
    litros = r.randint(2, 6)
    pl = r.choice([4.5, 5.2, 6.0, 7.8])
    total = n * pd + litros * pl
    nota = _nota(total)
    if nota is None:
        return None
    txt = (f"Seu Antônio comprou {n} dúzias de pão francês a R$ {brl(pd)} a dúzia e {litros} "
           f"litros de leite a R$ {brl(pl)} o litro. Ele pagou com uma nota de R$ {brl(nota)}. "
           f"Quantos reais ele recebeu de troco?")
    return txt, f"{num(nota)} - ({n}*{num(pd)} + {litros}*{num(pl)})", "padaria"


def t11_pet_racao(r):
    g = r.choice([125, 150, 200, 250, 300])
    dias = r.randint(8, 30)
    kg = g * 2 * dias / 1000
    if limpo(kg) is None or kg > 30:
        return None
    txt = (f"Um saco de ração tem {brl(kg).replace(',00', '')} quilos. Bruna tem dois cachorros "
           f"e cada um come {g} gramas de ração por dia. Sabendo que 1 quilo tem 1000 gramas, "
           f"por quantos dias o saco de ração dura?")
    return txt, f"{num(kg)}*1000/({g}*2)", "pet"


def t12_livro_paginas(r):
    p = r.randint(180, 520)
    q = r.randint(12, 35)
    d = r.randint(4, 9)
    x = r.randint(15, 60)
    if p - q * d - x < 5:
        return None
    txt = (f"Um livro tem {p} páginas. Carla leu {q} páginas por dia durante {d} dias e, no "
           f"sábado, leu mais {x} páginas de uma vez. Quantas páginas ainda faltam para ela "
           f"terminar o livro?")
    return txt, f"{p} - {q}*{d} - {x}", "escola"


def t13_festa_refrigerante(r):
    f = r.randint(8, 40)
    c = r.randint(2, 5)
    m = r.choice([500, 1000, 1500, 2000])
    if f * c * 200 - m < 500:
        return None
    txt = (f"Numa festa havia {f} convidados e cada um bebeu {c} copos de refrigerante de 200 "
           f"mililitros. O anfitrião já tinha {m} mililitros de refrigerante guardados em casa. "
           f"Quantos mililitros ele precisou comprar a mais?")
    return txt, f"{f}*{c}*200 - {m}", "festa"


def t14_horta(r):
    l = r.randint(4, 14)
    m = r.randint(8, 25)
    k = r.randint(3, 30)
    v = r.choice([1.5, 2.0, 2.5, 3.0])
    if l * m - k < 20:
        return None
    txt = (f"Um canteiro tem {l} fileiras com {m} pés de alface em cada fileira. As lesmas "
           f"estragaram {k} pés. O agricultor colheu todos os pés que sobraram e vendeu cada um "
           f"por R$ {brl(v)}. Quantos reais ele recebeu?")
    return txt, f"({l}*{m} - {k}) * {num(v)}", "agricultura"


def t15_reciclagem(r):
    a = r.randint(20, 120)
    b = r.randint(15, 80)
    v = r.choice([0.05, 0.1, 0.15, 0.2, 0.25])
    if limpo((a + b * 4) * v) is None:
        return None
    txt = (f"Na segunda-feira, Tiago juntou {a} latinhas de alumínio. De terça a sexta ele "
           f"juntou {b} latinhas por dia. No fim da semana vendeu todas as latinhas por "
           f"R$ {brl(v)} cada uma. Quantos reais ele recebeu?")
    return txt, f"({a} + {b}*4) * {num(v)}", "reciclagem"


def t16_conta_luz(r):
    kwh = r.randint(80, 320)
    t = r.choice([0.75, 0.8, 0.9, 1.25, 1.5])
    tx = r.choice([12.0, 18.5, 25.0, 30.0])
    dsc = r.choice([5.0, 10.0, 15.0])
    if limpo(kwh * t + tx - dsc) is None:
        return None
    txt = (f"A conta de luz de uma casa é calculada assim: R$ {brl(t)} por quilowatt-hora "
           f"consumido, mais uma taxa fixa de R$ {brl(tx)}. Neste mês a casa consumiu {kwh} "
           f"quilowatts-hora e recebeu R$ {brl(dsc)} de desconto por pagar adiantado. Quantos "
           f"reais ficou a conta?")
    return txt, f"{kwh}*{num(t)} + {num(tx)} - {num(dsc)}", "casa"


def t17_hospedagem(r):
    d = r.choice([90.0, 110.0, 125.0, 140.0, 180.0])
    p = r.randint(2, 5)
    n = r.randint(2, 7)
    c = r.choice([15.0, 20.0, 25.0])
    txt = (f"Uma pousada cobra R$ {brl(d)} por noite para cada pessoa. Uma família de {p} "
           f"pessoas ficou hospedada {n} noites. Além disso, a pousada cobrou uma taxa única de "
           f"limpeza de R$ {brl(c)} por pessoa. Quantos reais a família pagou no total?")
    return txt, f"{num(d)}*{p}*{n} + {num(c)}*{p}", "viagem"


def t18_oficina(r):
    m = r.choice([60.0, 75.0, 80.0, 95.0, 120.0])
    h = r.randint(2, 8)
    pc = r.choice([140.0, 220.0, 310.5, 480.0])
    dsc = r.choice([20.0, 35.0, 50.0])
    if m * h + pc - dsc <= 0:
        return None
    txt = (f"O mecânico cobra R$ {brl(m)} por hora de trabalho. Ele levou {h} horas para "
           f"consertar o carro e usou R$ {brl(pc)} em peças. No fim, deu R$ {brl(dsc)} de "
           f"desconto no valor total. Quantos reais o dono do carro pagou?")
    return txt, f"{num(m)}*{h} + {num(pc)} - {num(dsc)}", "oficina"


def t19_pontos_campeonato(r):
    v = r.randint(5, 20)
    e = r.randint(2, 12)
    d = r.randint(1, 10)
    pun = r.choice([1, 3, 6])
    if v * 3 + e - pun < 5:
        return None
    txt = (f"No campeonato, cada vitória vale 3 pontos e cada empate vale 1 ponto; derrota não "
           f"vale ponto. Um time teve {v} vitórias, {e} empates e {d} derrotas, e depois perdeu "
           f"{pun} pontos por causa de uma punição. Com quantos pontos o time terminou?")
    return txt, f"{v}*3 + {e} - {pun}", "esporte"


def t20_lanchonete_rateio(r):
    n = r.choice([2, 3, 4, 5])
    x = n * r.randint(1, 3)
    y = n * r.randint(1, 2)
    pl = r.choice([14.0, 16.5, 18.0, 22.0])
    ps = r.choice([6.0, 7.5, 9.0])
    if limpo((x * pl + y * ps) / n) is None:
        return None
    txt = (f"Um grupo de {n} colegas pediu {x} lanches a R$ {brl(pl)} cada e {y} sucos a "
           f"R$ {brl(ps)} cada. Eles dividiram a conta em partes iguais. Quantos reais cada "
           f"colega pagou?")
    return txt, f"({x}*{num(pl)} + {y}*{num(ps)}) / {n}", "lazer"


def t21_remedio(r):
    d = r.choice([5, 8, 10, 15, 20])
    dias = r.randint(4, 20)
    ml = d * 3 * dias / 2
    if limpo(ml) is None or ml < 30 or ml > 600 or abs(ml - round(ml)) > 1e-9:
        return None
    txt = (f"Um xarope vem em frascos de {brl(ml).replace(',00', '')} mililitros. O médico "
           f"receitou {d} mililitros por dose, 3 doses por dia. Comprando 2 frascos, para "
           f"quantos dias de tratamento o remédio dá?")
    return txt, f"{num(ml)}*2/({d}*3)", "saude"


def t22_artesanato_lucro(r):
    t = r.randint(6, 30)
    pm = r.choice([8.0, 12.5, 15.0, 18.0])
    n = r.randint(4, 20)
    pv = r.choice([25.0, 30.0, 45.0, 60.0])
    lucro = n * pv - t * pm
    if lucro <= 20:
        return None
    txt = (f"Marta comprou {t} metros de tecido a R$ {brl(pm)} o metro. Com esse tecido ela fez "
           f"{n} bolsas e vendeu cada bolsa por R$ {brl(pv)}. Quantos reais Marta teve de lucro, "
           f"ou seja, quanto sobrou depois de descontar o que ela gastou com o tecido?")
    return txt, f"{n}*{num(pv)} - {t}*{num(pm)}", "artesanato"


def t23_leve3_pague2(r):
    q = 3 * r.randint(2, 9)
    p = r.choice([6.0, 7.5, 9.9, 12.0, 15.0])
    if limpo(q / 3 * 2 * p) is None:
        return None
    txt = (f"Um mercado está com a promoção \"leve 3, pague 2\" nos sabonetes, que custam "
           f"R$ {brl(p)} cada. Helena levou {q} sabonetes, ou seja, pagou apenas 2 sabonetes a "
           f"cada 3 que levou. Quantos reais ela pagou?")
    return txt, f"{q}/3*2*{num(p)}", "compras"


def t24_caixa_dagua(r):
    C = r.choice([500, 750, 1000, 1500, 2000])
    c = r.choice([40, 55, 60, 80, 120])
    d = r.randint(3, 9)
    chuva = r.choice([50, 120, 200, 300])
    if C - c * d + chuva > C or C - c * d < 0:
        return None
    txt = (f"Uma caixa d'água de {C} litros estava cheia. A família consumiu {c} litros por dia "
           f"durante {d} dias e, depois disso, a chuva encheu a caixa com mais {chuva} litros. "
           f"Quantos litros de água há na caixa agora?")
    return txt, f"{C} - {c}*{d} + {chuva}", "casa"


def t25_transporte_mensal(r):
    p = r.choice([4.4, 5.0, 5.5, 6.0, 6.75])
    d = r.choice([20, 21, 22, 24])
    vt = r.choice([60.0, 80.0, 100.0, 120.0])
    total = p * 2 * d - vt
    if limpo(total) is None or total <= 10:
        return None
    txt = (f"A passagem de ônibus custa R$ {brl(p)}. Luiz pega o ônibus duas vezes por dia, na "
           f"ida e na volta do trabalho, em {d} dias úteis do mês. A empresa paga R$ {brl(vt)} "
           f"de vale-transporte por mês. Quantos reais Luiz gasta do próprio bolso no mês?")
    return txt, f"{num(p)}*2*{d} - {num(vt)}", "transporte"


def t26_media_sorvetes(r):
    a, b, c = (r.randint(20, 140) for _ in range(3))
    if limpo((a + b + c) / 3) is None:
        return None
    txt = (f"Uma sorveteria vendeu {a} sorvetes na sexta, {b} no sábado e {c} no domingo. Qual "
           f"foi a média de sorvetes vendidos por dia nesses três dias?")
    return txt, f"({a} + {b} + {c}) / 3", "lazer"


def t27_marcenaria(r):
    p = r.choice([15, 20, 25, 30, 40])
    n = r.randint(3, 12)
    C = p * n + r.choice([10, 15, 25, 35, 50])
    txt = (f"Um marceneiro tem uma tábua de {C} centímetros. Ele cortou {n} pedaços de {p} "
           f"centímetros cada um. Quantos centímetros de tábua sobraram?")
    return txt, f"{C} - {n}*{p}", "oficina"


def t28_poupanca(r):
    i = r.choice([120.0, 250.0, 400.0, 800.0])
    m = r.choice([50.0, 75.0, 120.0, 200.0])
    n = r.randint(3, 12)
    g = r.choice([90.0, 150.0, 320.0, 500.0])
    total = i + m * n - g
    if total <= 30:
        return None
    txt = (f"Rita tinha R$ {brl(i)} guardados. Ela passou a guardar R$ {brl(m)} por mês durante "
           f"{n} meses. No fim desse período, gastou R$ {brl(g)} com o conserto da geladeira. "
           f"Quantos reais Rita ainda tem guardados?")
    return txt, f"{num(i)} + {num(m)}*{n} - {num(g)}", "financas"


def t29_acougue(r):
    p = r.choice([28.0, 32.5, 39.9, 45.0, 52.0])
    g = r.choice([500, 750, 1200, 1500, 2500])
    if limpo(p * g / 1000) is None:
        return None
    txt = (f"No açougue, a picanha custa R$ {brl(p)} o quilo. Seu Jorge levou {g} gramas. "
           f"Sabendo que 1 quilo tem 1000 gramas, quantos reais ele pagou?")
    return txt, f"{num(p)}*{g}/1000", "feira"


def t30_ovos_bandeja(r):
    b = r.randint(3, 15)
    quebrados = r.randint(2, 20)
    if b * 30 - quebrados - 48 < 5:
        return None
    txt = (f"Uma granja enviou {b} bandejas com 30 ovos cada para um restaurante. No transporte, "
           f"{quebrados} ovos quebraram. O restaurante usou 48 ovos no almoço. Quantos ovos "
           f"inteiros ainda restam?")
    return txt, f"{b}*30 - {quebrados} - 48", "agricultura"


def t31_canetas_desconto(r):
    n = r.randint(4, 25)
    p = r.choice([3.5, 4.0, 5.5, 6.9, 8.0, 12.0])
    d = r.choice([0.5, 1.0, 1.5, 2.0])
    if p - d <= 0.5:
        return None
    txt = (f"Uma caneta custa R$ {brl(p)}. A papelaria está dando R$ {brl(d)} de desconto em "
           f"cada caneta comprada. Quantos reais custam {n} canetas com esse desconto?")
    return txt, f"{n}*({num(p)} - {num(d)})", "compras"


def t32_pedreiro_tijolos(r):
    t = r.choice([30, 45, 60, 75, 90])
    h = r.randint(3, 9)
    H = r.randint(2, 8)
    if h == H:
        return None
    txt = (f"Um pedreiro assenta {t} tijolos por hora. Na segunda-feira ele trabalhou {h} horas "
           f"e na terça-feira trabalhou {H} horas. Quantos tijolos ele assentou nesses dois dias?")
    return txt, f"{t}*({h} + {H})", "oficina"


def t33_feira_tres_itens(r):
    a, b = r.randint(2, 8), r.randint(2, 6)
    pa = r.choice([3.5, 4.9, 5.0, 6.5])
    pb = r.choice([7.0, 8.5, 9.9, 11.0])
    pc = r.choice([6.0, 7.5, 9.0, 12.5])
    txt = (f"Na feira, Paulo comprou {a} quilos de laranja a R$ {brl(pa)} o quilo, {b} quilos de "
           f"mamão a R$ {brl(pb)} o quilo e um abacaxi que custou R$ {brl(pc)}. Quantos reais "
           f"Paulo gastou ao todo?")
    return txt, f"{a}*{num(pa)} + {b}*{num(pb)} + {num(pc)}", "feira"


def t34_pintor_parede(r):
    m = r.choice([18.0, 22.0, 25.0, 30.0, 40.0])
    L = r.randint(3, 12)
    A = r.choice([2, 3, 4])
    pd = r.choice([80.0, 120.0, 150.0, 200.0])
    dsc = r.choice([25.0, 40.0, 60.0])
    if m * L * A + pd - dsc <= 50:
        return None
    txt = (f"Um pintor cobra R$ {brl(m)} por metro quadrado pintado. Ele pintou uma parede de "
           f"{L} metros de largura por {A} metros de altura, cobrou mais R$ {brl(pd)} pela "
           f"pintura da porta e, no fim, deu R$ {brl(dsc)} de desconto. Quantos reais o pintor "
           f"cobrou?")
    return txt, f"{num(m)}*{L}*{A} + {num(pd)} - {num(dsc)}", "oficina"


def t35_vendedor_comissao(r):
    s = r.choice([1200.0, 1500.0, 1800.0, 2000.0])
    c = r.choice([3.0, 4.5, 6.0, 8.0, 12.0])
    v = r.randint(20, 120)
    V = r.randint(20, 120)
    x = r.choice([80.0, 150.0, 240.0])
    if v == V or limpo(s + c * (v + V) - x) is None:
        return None
    txt = (f"Um vendedor recebe um salário fixo de R$ {brl(s)} por mês, mais R$ {brl(c)} de "
           f"comissão por peça vendida. Neste mês ele vendeu {v} peças na primeira quinzena e "
           f"{V} peças na segunda quinzena. Do total, a empresa descontou R$ {brl(x)} de "
           f"impostos. Quantos reais o vendedor recebeu?")
    return txt, f"{num(s)} + {num(c)}*({v} + {V}) - {num(x)}", "financas"


def t36_prova_questoes(r):
    q = r.choice([20, 30, 40, 45, 50, 60])
    a = r.randint(4, q // 3)
    b = r.randint(4, q // 3)
    if q - a - b < 3:
        return None
    txt = (f"Uma prova tem {q} questões no total. Vitória acertou {a} questões de matemática e "
           f"{b} questões de português, e errou todas as outras. Quantas questões ela errou?")
    return txt, f"{q} - {a} - {b}", "escola"


FAMILIAS = [
    t01_troco_desconto, t02_feira_dois_itens, t03_onibus, t04_escola_turmas,
    t05_salario_semana, t06_desconto_percentual, t07_combustivel, t08_rateio_conta,
    t09_estoque_caixas, t10_padaria_troco, t11_pet_racao, t12_livro_paginas,
    t13_festa_refrigerante, t14_horta, t15_reciclagem, t16_conta_luz,
    t17_hospedagem, t18_oficina, t19_pontos_campeonato, t20_lanchonete_rateio,
    t21_remedio, t22_artesanato_lucro, t23_leve3_pague2, t24_caixa_dagua,
    t25_transporte_mensal, t26_media_sorvetes, t27_marcenaria, t28_poupanca,
    t29_acougue, t30_ovos_bandeja, t31_canetas_desconto, t32_pedreiro_tijolos,
    t33_feira_tres_itens, t34_pintor_parede, t35_vendedor_comissao, t36_prova_questoes,
]

MAX_REPETICAO_RESPOSTA = 4   # em 200 itens = 2%, com folga sob os 5% que o validador vigia

# Cota por numero de operacoes. Sem cota, o sorteio round-robin devolvia 80% dos itens em
# 3 passos — e ai o conjunto nao separa "o modelo faz 2 operacoes mas nao 4" de "o modelo
# nao faz nada". A separacao importa: se o gate reprovar, a sub-taxa por profundidade e' a
# unica evidencia de ONDE a capacidade morre.
COTA_PASSOS = {2: 0.25, 3: 0.50, 4: 0.25}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="quantidade de problemas")
    ap.add_argument("--semente", type=int, default=20260819)
    ap.add_argument("--saida", type=Path, default=DESTINO)
    args = ap.parse_args()

    r = random.Random(args.semente)
    itens: list[dict] = []
    vistos_txt: set[str] = set()
    conta_resp: dict[float, int] = {}
    conta_passos: dict[int, int] = {}
    cotas = {p: round(args.n * f) for p, f in COTA_PASSOS.items()}
    tentativas = 0
    familia_idx = 0

    while len(itens) < args.n and tentativas < args.n * 4000:
        tentativas += 1
        familia = FAMILIAS[familia_idx % len(FAMILIAS)]
        familia_idx += 1
        saida = familia(r)
        if saida is None:
            continue
        pergunta, expressao, tema = saida

        valor = limpo(avaliar(expressao))
        if valor is None or valor <= 0:
            continue
        passos = contar_passos(expressao)
        if not 2 <= passos <= 4:
            continue
        if conta_passos.get(passos, 0) >= cotas.get(passos, 0):
            continue
        chave = _norm(pergunta)
        if chave in vistos_txt:
            continue
        if conta_resp.get(valor, 0) >= MAX_REPETICAO_RESPOSTA:
            continue

        vistos_txt.add(chave)
        conta_resp[valor] = conta_resp.get(valor, 0) + 1
        conta_passos[passos] = conta_passos.get(passos, 0) + 1
        itens.append({
            "id": f"arit_{len(itens) + 1:03d}",
            "pergunta": pergunta,
            "resposta": valor,
            "expressao": expressao,
            "passos": passos,
            "tema": tema,
        })

    if len(itens) < args.n:
        print(f"🔴 so consegui {len(itens)}/{args.n} itens em {tentativas} tentativas.", file=sys.stderr)
        return 1

    # ---- guarda de saida: nenhum item sai daqui sem o gabarito ter sido EXECUTADO.
    #      Redundante com a construcao — de proposito. Guarda fora do fluxo nao guarda nada.
    for it in itens:
        v = avaliar(it["expressao"])
        if abs(v - it["resposta"]) > 1e-6:
            print(f"🔴 ABORTA: {it['id']} nao confere ({v} != {it['resposta']})", file=sys.stderr)
            return 1

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    dist_p: dict[int, int] = {}
    dist_t: dict[str, int] = {}
    for it in itens:
        dist_p[it["passos"]] = dist_p.get(it["passos"], 0) + 1
        dist_t[it["tema"]] = dist_t.get(it["tema"], 0) + 1
    print(f"✅ {len(itens)} problemas → {args.saida}")
    print(f"   passos: {dict(sorted(dist_p.items()))}")
    print(f"   temas : {dict(sorted(dist_t.items(), key=lambda x: -x[1]))}")
    print(f"   semente {args.semente} · {tentativas} tentativas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
