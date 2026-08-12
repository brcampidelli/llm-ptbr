"""Executor DETERMINISTICO das 14 ferramentas do catalogo — o que faltava para medir acerto.

⚠️ POR QUE ISTO EXISTE (2026-08-12):
    Ate hoje o projeto media tool-use por SEMELHANCA: "o JSON e valido?", "o nome da
    ferramenta bate com a referencia?". Nenhuma chamada era EXECUTADA. E possivel ter
    100% de "ferramenta certa" e 0% de tarefa cumprida — basta errar os argumentos.
    O eval_loss de 1,0672 e ainda mais indireto: mede predicao de token sob mascara.

    Este modulo executa a chamada de verdade contra stubs deterministicos e permite a
    unica metrica que importa para um agente: **a tarefa foi cumprida?**

⭐ COMO A CORRECAO E DECIDIDA, e por que nao e comparacao de string de argumento:
    Executamos a chamada PREVISTA e a chamada de REFERENCIA no mesmo mundo simulado e
    comparamos os RESULTADOS. Assim `{"expression": "6*9"}` e `{"expression": "9*6"}`
    contam como acerto (ambas dao 54), e `{"expression": "8/3"}` conta como erro mesmo
    tendo escolhido a ferramenta certa. Equivalencia funcional, nao textual.

    Isso e mais justo com o modelo E mais severo: um argumento plausivel mas errado,
    que a metrica de "ferramenta certa" perdoava, aqui aparece.

🔴 O MUNDO E ABERTO, e a primeira versao deste arquivo errava justamente nisso.
    A v1 tinha um mundo FECHADO — 6 cidades, 5 tickers, 3 arquivos. Resultado: 35 dos 85
    exemplos do holdout eram IMPOSSIVEIS de acertar, porque a propria chamada de
    REFERENCIA falhava (`get_weather{"city":"Brasilia"}` -> "cidade fora do mundo
    simulado"; `read_file{"path":"/var/log/syslog"}` -> "arquivo inexistente"). A medicao
    saiu 23,5% e era artefato do avaliador, nao do modelo. read_file dava 0/10 e list_dir
    0/10 — numeros absurdos que denunciaram o defeito.

    Regra que ficou: **o mundo simulado tem de ser aberto e deterministico**, nunca uma
    lista branca. Qualquer cidade, ticker ou caminho e aceito e produz uma saida derivada
    da entrada normalizada. Assim a pergunta medida e a certa — "o modelo pediu a MESMA
    coisa que a referencia?" — e nao "o argumento esta na minha listinha?".

    O controle barato que pega esse defeito: executar as REFERENCIAS antes de qualquer
    modelo. Se alguma referencia falha, o avaliador esta errado.

Sem rede, sem disco real: mesma entrada, mesma saida, sempre.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import operator as op
import unicodedata
from pathlib import Path
from typing import Any

RAIZ_FIXTURES = Path(__file__).resolve().parent / "fixtures"

BUSCA_FIXA = "[resultado de busca simulado]"


def _norm(s: object) -> str:
    """Normalizacao semantica: acento, caixa e espaco nao devem decidir acerto.

    'São Paulo', 'sao paulo' e ' SAO  PAULO ' sao a MESMA cidade. Sem isto estariamos
    medindo ortografia em vez de escolha de argumento.
    """
    txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(txt.lower().split())


def _det(*partes: object) -> int:
    """Inteiro estavel derivado da entrada — o mundo e aberto, mas nunca aleatorio."""
    chave = "|".join(_norm(p) for p in partes)
    return int(hashlib.sha256(chave.encode("utf-8")).hexdigest()[:8], 16)

_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv, ast.USub: op.neg,
        ast.UAdd: op.pos}
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max,
          "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
          "sin": math.sin, "cos": math.cos, "tan": math.tan, "pow": pow,
          "floor": math.floor, "ceil": math.ceil, "factorial": math.factorial}
_CONSTS = {"pi": math.pi, "e": math.e}


class ErroFerramenta(Exception):
    """A chamada nao pode ser executada (argumento faltando, invalido, ou fora do mundo)."""


def _calcular(expr: str) -> float:
    """Aritmetica segura via AST — nada de eval().

    Suporta funcoes (sqrt, log, ...) porque o holdout as usa: a guarda de referencias
    pegou `sqrt(1444)` e `sqrt(1234567)` falhando, o que teria contado como erro do
    modelo. Constantes (pi, e) tambem entram.
    """
    def _no(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _no(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name) and n.id in _CONSTS:
            return _CONSTS[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_no(n.left), _no(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_no(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
            return float(_FUNCS[n.func.id](*[_no(x) for x in n.args]))
        raise ErroFerramenta(f"expressao nao suportada: {expr!r}")
    try:
        return round(_no(ast.parse(expr, mode="eval")), 6)
    except ZeroDivisionError as e:
        raise ErroFerramenta("divisao por zero") from e
    except (SyntaxError, ValueError) as e:
        raise ErroFerramenta(f"expressao invalida: {expr!r}") from e


def _caminho_seguro(path: str) -> Path:
    """Impede sair da sandbox de fixtures — o executor nunca toca o disco real."""
    p = (RAIZ_FIXTURES / str(path).lstrip("/\\")).resolve()
    if not str(p).startswith(str(RAIZ_FIXTURES.resolve())):
        raise ErroFerramenta(f"caminho fora da sandbox: {path!r}")
    return p


def _exigir(args: dict, *chaves: str) -> list:
    faltando = [k for k in chaves if k not in args or args[k] in (None, "")]
    if faltando:
        raise ErroFerramenta(f"argumento(s) faltando: {faltando}")
    return [args[k] for k in chaves]


# ── as 14 ferramentas ─────────────────────────────────────────────────────────
def _web_search(a: dict) -> Any:
    (q,) = _exigir(a, "query")
    return {"query": str(q).strip().lower(), "resultados": BUSCA_FIXA}


def _http_get(a: dict) -> Any:
    (u,) = _exigir(a, "url")
    if not str(u).startswith(("http://", "https://")):
        raise ErroFerramenta(f"url invalida: {u!r}")
    return {"url": str(u).rstrip("/"), "status": 200}


def _read_file(a: dict) -> Any:
    """Mundo ABERTO: qualquer caminho 'existe' e devolve conteudo derivado dele.
    O que decide o acerto e o modelo ter pedido o MESMO arquivo que a referencia."""
    (p,) = _exigir(a, "path")
    return {"arquivo": _norm(p), "conteudo_id": _det("read", p)}


def _write_file(a: dict) -> Any:
    p, c = _exigir(a, "path", "content")
    return {"escrito": _norm(p), "bytes": len(str(c).encode("utf-8"))}


def _list_dir(a: dict) -> Any:
    (p,) = _exigir(a, "path")
    return {"dir": _norm(p), "listagem_id": _det("ls", p)}


def _run_sql(a: dict) -> Any:
    (q,) = _exigir(a, "query")
    if not str(q).strip().lower().startswith("select"):
        raise ErroFerramenta("apenas SELECT e permitido")
    return {"linhas": [{"n": 1}]}


def _run_python(a: dict) -> Any:
    (c,) = _exigir(a, "code")
    try:
        compile(str(c), "<tool>", "exec")
    except SyntaxError as e:
        raise ErroFerramenta(f"codigo nao compila: {e.msg}") from e
    return {"compila": True}


def _calculator(a: dict) -> Any:
    (e,) = _exigir(a, "expression")
    return {"resultado": _calcular(str(e))}


def _get_weather(a: dict) -> Any:
    """Qualquer cidade. 'São Paulo' e 'sao paulo' dao o mesmo tempo — e a mesma cidade."""
    (c,) = _exigir(a, "city")
    h = _det("clima", c)
    return {"cidade": _norm(c), "temp_c": 10 + h % 25,
            "cond": ["limpo", "nublado", "chuvoso", "encoberto"][h % 4]}


def _send_email(a: dict) -> Any:
    to, s, b = _exigir(a, "to", "subject", "body")
    if "@" not in str(to):
        raise ErroFerramenta(f"destinatario invalido: {to!r}")
    return {"enviado_para": str(to).strip().lower(), "tem_assunto": bool(str(s).strip()),
            "tem_corpo": bool(str(b).strip())}


def _create_calendar_event(a: dict) -> Any:
    t, s = _exigir(a, "title", "start")
    # ISO 8601 e exigencia do catalogo: "amanha as 10h" nao serve, e o holdout cobra isso.
    txt = str(s)
    if not (len(txt) >= 10 and txt[4] == "-" and txt[7] == "-" and txt[:4].isdigit()):
        raise ErroFerramenta(f"start nao esta em ISO 8601: {s!r}")
    return {"titulo_ok": bool(str(t).strip()), "inicio": txt[:16]}


def _get_stock_price(a: dict) -> Any:
    (t,) = _exigir(a, "ticker")
    return {"ticker": _norm(t).upper(), "preco": round(5 + _det("acao", t) % 30000 / 100, 2)}


def _translate_text(a: dict) -> Any:
    t, lang = _exigir(a, "text", "target_lang")
    return {"idioma": str(lang).strip().lower()[:2], "n_chars": len(str(t))}


def _summarize_url(a: dict) -> Any:
    (u,) = _exigir(a, "url")
    if not str(u).startswith(("http://", "https://")):
        raise ErroFerramenta(f"url invalida: {u!r}")
    return {"url": str(u).rstrip("/"), "resumo": "[resumo simulado]"}


FERRAMENTAS = {
    "web_search": _web_search, "http_get": _http_get, "read_file": _read_file,
    "write_file": _write_file, "list_dir": _list_dir, "run_sql": _run_sql,
    "run_python": _run_python, "calculator": _calculator, "get_weather": _get_weather,
    "send_email": _send_email, "create_calendar_event": _create_calendar_event,
    "get_stock_price": _get_stock_price, "translate_text": _translate_text,
    "summarize_url": _summarize_url,
}


def executar(chamada: dict) -> tuple[bool, Any]:
    """Executa {"tool": ..., "args": {...}}. Devolve (ok, resultado_ou_erro)."""
    if not isinstance(chamada, dict):
        return False, "chamada nao e objeto"
    nome = chamada.get("tool")
    args = chamada.get("args") or {}
    fn = FERRAMENTAS.get(nome)
    if fn is None:
        return False, f"ferramenta inexistente: {nome!r}"
    if not isinstance(args, dict):
        return False, "args nao e objeto"
    try:
        return True, fn(args)
    except ErroFerramenta as e:
        return False, str(e)
    except Exception as e:                                   # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def resultados_batem(a: Any, b: Any) -> bool:
    """Igualdade funcional dos resultados, canonizada."""
    return json.dumps(a, sort_keys=True, ensure_ascii=False, default=str) == \
        json.dumps(b, sort_keys=True, ensure_ascii=False, default=str)


def garantir_fixtures() -> None:
    """Cria o mundo de arquivos. Deterministico: mesmo conteudo sempre."""
    RAIZ_FIXTURES.mkdir(parents=True, exist_ok=True)
    (RAIZ_FIXTURES / "docs").mkdir(exist_ok=True)
    (RAIZ_FIXTURES / "notas.txt").write_text(
        "Reuniao de equipe as 10h.\nComprar cafe.\n", encoding="utf-8")
    (RAIZ_FIXTURES / "relatorio.md").write_text(
        "# Relatorio\n\nVendas subiram 12% no trimestre.\n", encoding="utf-8")
    (RAIZ_FIXTURES / "docs" / "leia-me.txt").write_text(
        "Documentacao do projeto Bee.\n", encoding="utf-8")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    garantir_fixtures()
    provas = [
        ({"tool": "calculator", "args": {"expression": "6*9"}},
         {"tool": "calculator", "args": {"expression": "9*6"}}, True,
         "ordem diferente, mesmo resultado -> acerto"),
        ({"tool": "calculator", "args": {"expression": "8/3"}},
         {"tool": "calculator", "args": {"expression": "5/8*100"}}, False,
         "ferramenta certa, argumento errado -> erro (o que 'tool_right' perdoava)"),
        ({"tool": "get_weather", "args": {"city": "São Paulo"}},
         {"tool": "get_weather", "args": {"city": "sao paulo"}}, True,
         "acento/caixa normalizados -> acerto"),
        ({"tool": "create_calendar_event", "args": {"title": "Reuniao", "start": "amanha 10h"}},
         {"tool": "create_calendar_event", "args": {"title": "Reuniao", "start": "2026-08-13T10:00"}},
         False, "start fora do ISO 8601 -> erro"),
        ({"tool": "read_file", "args": {"path": "../../segredo.txt"}},
         {"tool": "read_file", "args": {"path": "notas.txt"}}, False,
         "escape da sandbox barrado"),
    ]
    falhou = 0
    for pred, ref, esperado, desc in provas:
        ok_p, rp = executar(pred)
        ok_r, rr = executar(ref)
        obtido = ok_p and ok_r and resultados_batem(rp, rr)
        marca = "OK " if obtido == esperado else "FALHOU"
        if obtido != esperado:
            falhou += 1
        print(f"[{marca}] {desc}")
        if obtido != esperado:
            print(f"         pred={rp!r} ref={rr!r}")
    print(f"\n{len(provas)-falhou}/{len(provas)} provas passaram")
    raise SystemExit(1 if falhou else 0)
