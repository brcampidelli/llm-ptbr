"""Verificador de ANCORAGEM de argumentos — ataca a confabulacao, nao o over-calling.

⚠️ O DIAGNOSTICO QUE ORIGINOU ESTE ARQUIVO (2026-08-12):
    O Bee marcava 23,1% de "over-calling" no holdout. Lendo os 15 casos um a um, quase
    nenhum era over-calling no sentido classico (chamar ferramenta quando conversa
    bastava). O padrao real era outro:

      "Manda um e-mail pra maria@teste.com, assunto 'Reuniao remarcada'"
        ref  -> falta o CORPO, peca ao usuario
        Bee  -> send_email{... "body": "<corpo inventado>"}

      "Cria um evento 'Fechamento do Mes' no dia 31 as 16h"
        ref  -> falta MES e ANO, peca ao usuario
        Bee  -> create_calendar_event{"start": "2025-04-01T16:00:00"}   (e trocou 31 por 01)

    O modelo escolhe a ferramenta CERTA e **inventa os argumentos que o usuario nao deu**.
    E a mesma patologia do "escreve portugues excelente e inventa fatos com confianca",
    agora em tool-use.

⭐ POR QUE ISSO IMPORTA PARA O ATAQUE:
    Decidir *se* a query precisa de ferramenta e semantico e dificil — o verificador
    existente acerta pouco (interceptou 4/15) e cobra caro (bloqueou 5/85 chamadas
    legitimas), saldo -1. Ja verificar se o argumento **aparece no texto do usuario** e
    sintatico e decidivel. Nao exige entender a intencao; exige comparar strings.

PRINCIPIO: conservador. So acusa quando ha certeza de que o valor nao veio do usuario.
Na duvida, aprova — um falso positivo bloqueia tarefa que funcionava, e custa mais caro
que o over-call que conserta.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# 🔴 ESTA LISTA JA FOI LARGA E ESTAVA ERRADA (medido em 2026-08-12).
#
# A v1 exigia ancoragem de to/subject/body/path/city/ticker/url/text. Rodada contra as
# 85 chamadas de REFERENCIA do holdout — que sao legitimas por definicao — acusou 6
# (7,1% de falso positivo puro), e cada uma ensinou a mesma licao:
#
#   "Petrobras na Bovespa"      -> PETR4                    DERIVACAO por conhecimento
#   "BBC's RSS feed"            -> feeds.bbci.co.uk/...     DERIVACAO por conhecimento
#   "reclamando do atraso"      -> corpo redigido           REDACAO a partir da intencao
#   "dia 10/05 as 15h"          -> 2025-05-10T15:00         mes e dia ESTAO no texto
#
# Eu havia confundido CONFABULAR com DERIVAR. O modelo pode e deve normalizar ("Petrobras"
# -> PETR4) e redigir (intencao -> corpo). O que ele nao pode e inventar o que nao da para
# derivar de jeito nenhum.
#
# Sobrou o unico campo em que a evidencia e decidivel sem semantica: a DATA. "dia 31 as
# 16h" nao tem mes — nenhum conhecimento do mundo diz qual e. Regra estreita e correta
# vale mais que regra ampla e errada.
CAMPOS_ANCORADOS: dict[str, tuple[str, ...]] = {
    "create_calendar_event": ("start",),
}


def _norm(s: object) -> str:
    txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(txt.lower().split())


def _palavras(s: str) -> set[str]:
    return {p for p in re.findall(r"[a-z0-9@._-]+", _norm(s)) if len(p) > 2}


@dataclass
class Veredito:
    ancorado: bool
    campos_inventados: list[str]
    feedback: str


def _data_ancorada(valor: str, query: str) -> bool:
    """Uma data ISO esta ancorada se DIA e MES forem deriváveis do texto.

    ⚠️ O ANO NAO e exigido — assumir o corrente e derivacao legitima, e exigi-lo gerava
    falso positivo em referencias validas ("dia 10/05 as 15h" -> 2025-05-10). Ja o MES e
    indecidivel quando ausente: "dia 31 as 16h" nao permite a ninguem saber qual mes.
    E o DIA tem de bater — o modelo chegou a responder 2025-04-01 para "dia 31".
    """
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", str(valor))
    if not m:
        return True                      # nao e ISO: outra regra (do catalogo) cuida
    mes, dia = int(m.group(2)), int(m.group(3))
    q = _norm(query)

    # o mes precisa aparecer por extenso ou como numero dentro de uma data (10/05, 10-05)
    por_extenso = mes in {MESES[n] for n in MESES if n in q}
    como_numero = bool(re.search(rf"\d{{1,2}}\s*[/-]\s*0?{mes}\b", q))
    if not (por_extenso or como_numero):
        return False
    return bool(re.search(rf"\b0?{dia}\b", q))    # e o dia tem de bater


def verificar(query: str, chamada: dict) -> Veredito:
    """Quais argumentos obrigatorios NAO vieram do texto do usuario?"""
    if not isinstance(chamada, dict):
        return Veredito(True, [], "")
    ferramenta = chamada.get("tool")
    args = chamada.get("args") or {}
    campos = CAMPOS_ANCORADOS.get(ferramenta, ())
    if not campos or not isinstance(args, dict):
        return Veredito(True, [], "")

    q_norm = _norm(query)
    q_palavras = _palavras(query)
    inventados: list[str] = []

    for campo in campos:
        valor = args.get(campo)
        if valor in (None, "", []):
            continue

        if campo == "start":
            if not _data_ancorada(str(valor), query):
                inventados.append(campo)
            continue

        v_norm = _norm(valor)
        if not v_norm:
            continue
        if v_norm in q_norm:                       # aparece literalmente: ancorado
            continue

        # Texto longo (corpo de e-mail, texto a traduzir): exigimos que a maior parte
        # das palavras venha do usuario. Abaixo de 50% consideramos redigido pelo modelo.
        v_palavras = _palavras(valor)
        if not v_palavras:
            continue
        cobertura = len(v_palavras & q_palavras) / len(v_palavras)
        if cobertura < 0.5:
            inventados.append(campo)

    if not inventados:
        return Veredito(True, [], "")
    lista = ", ".join(inventados)
    return Veredito(
        False, inventados,
        f"Os argumentos [{lista}] nao aparecem no pedido do usuario. Nao invente "
        f"valores: pergunte ao usuario o que falta antes de chamar a ferramenta.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    provas = [
        # (query, chamada, deve_estar_ancorado, descricao)
        ("Manda um e-mail pra maria@teste.com, assunto 'Reuniao remarcada'",
         {"tool": "send_email", "args": {"to": "maria@teste.com",
                                         "subject": "Reuniao remarcada",
                                         "body": "Prezada Maria, informo que a reuniao "
                                                 "foi transferida para a proxima semana."}},
         False, "corpo inventado -> acusa"),
        ("Manda e-mail pra ana@x.com com assunto 'Oi' e corpo 'Tudo bem?'",
         {"tool": "send_email", "args": {"to": "ana@x.com", "subject": "Oi",
                                         "body": "Tudo bem?"}},
         True, "tudo veio do usuario -> aprova"),
        ("Cria um evento 'Fechamento do Mes' no dia 31 as 16h",
         {"tool": "create_calendar_event",
          "args": {"title": "Fechamento do Mes", "start": "2025-04-01T16:00:00"}},
         False, "mes/ano inventados e dia trocado -> acusa"),
        ("Agende 'Retro' para 12 de marco de 2026 as 9h",
         {"tool": "create_calendar_event",
          "args": {"title": "Retro", "start": "2026-03-12T09:00:00"}},
         True, "data toda no texto -> aprova"),
        ("Qual o clima em Fortaleza?",
         {"tool": "get_weather", "args": {"city": "Fortaleza"}},
         True, "cidade veio do usuario -> aprova"),
        ("Qual o clima hoje?",
         {"tool": "get_weather", "args": {"city": "Sao Paulo"}},
         False, "cidade inventada -> acusa"),
        ("Pesquise sobre energia solar no Brasil",
         {"tool": "web_search", "args": {"query": "energia solar fotovoltaica Brasil 2026"}},
         True, "query pode ser reformulada -> nao acusamos"),
    ]
    falhas = 0
    for q, c, esperado, desc in provas:
        v = verificar(q, c)
        ok = v.ancorado == esperado
        falhas += not ok
        print(f"[{'OK ' if ok else 'FALHOU'}] {desc}")
        if not ok:
            print(f"         ancorado={v.ancorado} campos={v.campos_inventados}")
    print(f"\n{len(provas)-falhas}/{len(provas)} provas passaram")
    raise SystemExit(1 if falhas else 0)
