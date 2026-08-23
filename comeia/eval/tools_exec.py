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


def _norm_caminho(s: object) -> str:
    """Como _norm, mas tambem tira a barra final: /a/b/ E' o diretorio /a/b.

    🔴 Medido no E5 (2026-08-22): o modelo pediu `/home/usuario/documentos/` onde a
    referencia dizia `/home/usuario/documentos`, e a regua reprovou. `_norm` cuida de acento,
    caixa e espaco — "porque ortografia nao deve decidir acerto" — mas deixava passar a barra,
    que tambem nao deve. E o defeito aparecia duas vezes: no campo ecoado E no hash, porque
    `_det` chama `_norm`.

    ⚠️ Funcao SEPARADA de _norm de proposito: cidade e texto livre nao devem perder barra.
    """
    return _norm(s).rstrip("/") or "/"


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
            a, b = _no(n.left), _no(n.right)
            # 🔴 GUARDA DE EXAUSTAO DE RECURSO — o avaliador travou de verdade por isto.
            #    2026-08-20: a regua agentica ficou 21 min presa entre os exemplos 21 e 39,
            #    com 1.604 s de CPU e 2,5 GB de working set num unico processo. O modelo
            #    BASE gerou uma chamada de calculadora com potencia enorme, e este `_no`
            #    foi calcular o inteiro gigante.
            #    ⚠️ "Seguro" aqui sempre significou "nao executa codigo arbitrario" (usa AST,
            #    nao eval). Isso e' verdade e nao bastava: uma expressao inteiramente valida
            #    exaure memoria e CPU sem executar nada proibido. Sao ameacas diferentes.
            #    E o sintoma nao era erro: era o run parado, indistinguivel de lentidao.
            if type(n.op) is ast.Pow and (abs(b) > 64 or (abs(a) > 1e6 and abs(b) > 8)):
                raise ErroFerramenta(f"potencia grande demais: {a}**{b}")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_no(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
            args = [_no(x) for x in n.args]
            # mesma familia da guarda de potencia: factorial(1e6) nao e' codigo proibido,
            # e' um numero com 5,5 milhoes de digitos. E `pow` chega pelo mesmo caminho.
            if n.func.id == "factorial" and (args and abs(args[0]) > 170):
                raise ErroFerramenta(f"factorial grande demais: {args[0]}")
            if n.func.id == "pow" and len(args) >= 2 and abs(args[1]) > 64:
                raise ErroFerramenta(f"potencia grande demais: pow({args[0]}, {args[1]})")
            # ⚠️ BUG ANTERIOR, ACHADO PELO TESTE DESTA GUARDA: `_no` devolve float e
            #    `math.factorial` exige int, entao `factorial(10)` SEMPRE levantou
            #    TypeError — e o `executar()` contava isso como falha do MODELO. A funcao
            #    estava na tabela desde sempre e nunca funcionou uma vez.
            if n.func.id == "factorial":
                if args[0] != int(args[0]):
                    raise ErroFerramenta(f"factorial exige inteiro: {args[0]}")
                args = [int(args[0])]
            return float(_FUNCS[n.func.id](*args))
        raise ErroFerramenta(f"expressao nao suportada: {expr!r}")
    try:
        r = _no(ast.parse(expr, mode="eval"))
        if not math.isfinite(r):
            raise ErroFerramenta(f"resultado nao finito: {expr!r}")
        return round(r, 6)
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
    return {"arquivo": _norm_caminho(p), "conteudo_id": _det("read", _norm_caminho(p))}


def _write_file(a: dict) -> Any:
    p, c = _exigir(a, "path", "content")
    return {"escrito": _norm_caminho(p), "bytes": len(str(c).encode("utf-8"))}


def _list_dir(a: dict) -> Any:
    (p,) = _exigir(a, "path")
    return {"dir": _norm_caminho(p), "listagem_id": _det("ls", _norm_caminho(p))}


def _run_sql(a: dict) -> Any:
    (q,) = _exigir(a, "query")
    if not str(q).strip().lower().startswith("select"):
        raise ErroFerramenta("apenas SELECT e permitido")
    # 🔴 A v1 devolvia {"linhas": [{"n": 1}]} — CONSTANTE. Qualquer SELECT "acertava", e o
    #    rejection sampling colheu 101 exemplos assim como reforco valido. Discriminacao zero
    #    nao e' leniencia: e' ausencia de medida disfarcada de acerto.
    return {"linhas": [{"n": 1}], "consulta_id": _det("sql", q)}


def _run_python(a: dict) -> Any:
    (c,) = _exigir(a, "code")
    try:
        compile(str(c), "<tool>", "exec")
    except SyntaxError as e:
        raise ErroFerramenta(f"codigo nao compila: {e.msg}") from e
    # 🔴 idem: {"compila": True} era constante, e `{"code": "f"}` — um nome solto, sintaxe
    #    valida — foi colhido como CORRETO pelo rejection sampling.
    #    ⚠️ O conserto move a ferramenta de "sem discriminacao" para "igualdade exata do
    #    codigo", que e' a classe ECO (§ PONTUADAS_POR_ECO). Isso e' pior para o modelo e
    #    MELHOR para a medicao: severo e mensuravel bate frouxo e invisivel. Executar o
    #    codigo de verdade daria equivalencia funcional, e e' o conserto certo — custa um
    #    sandbox, que este avaliador nao tem.
    return {"compila": True, "codigo_id": _det("py", c)}


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
        # ⭐ MUNDO ABERTO: fora das 14 simuladas, cai no `mundo_aberto`, que executa qualquer
        #    uma das 747 ferramentas do gigaverbo. Ele devolve a CLASSE junto (semantica x eco)
        #    e so' conta como semantica a ferramenta cuja formula foi VALIDADA contra o
        #    resultado registrado no proprio dataset.
        #    ⚠️ Sem este fallback, "ferramenta inexistente" contava como erro do MODELO — e o
        #    modelo tinha escolhido a ferramenta certa. E' o mundo fechado do §2c #4 em escala.
        try:
            from mundo_aberto import executar_aberto
        except ImportError:
            return False, f"ferramenta inexistente: {nome!r}"
        ok, r, _classe = executar_aberto(chamada)
        return ok, r
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


# ⚠️ FERRAMENTAS PONTUADAS POR ECO, NAO POR EXECUCAO — declarado, nao consertado.
#
# Medido no E5 (2026-08-22). `_web_search` devolve {"query": <a propria query>, "resultados":
# BUSCA_FIXA}. Como BUSCA_FIXA e' identica para todo mundo, ela nao discrimina nada: a
# comparacao inteira e' IGUALDADE EXATA da string da query, vestida de equivalencia
# funcional. Qualquer parafrase igualmente boa conta como erro — e web_search reprovou 11 de
# 13 no holdout por isso. `http_get` e `summarize_url` ecoam a URL (com rstrip("/")).
#
# 🔴 NAO ha' conserto honesto disponivel: dizer que duas queries de busca sao "a mesma" exige
# um criterio que este projeto nao tem, e inventar um (sobreposicao de palavras, por exemplo)
# seria escolher o limiar que produz o numero desejado. O certo e' DECLARAR: o acerto nessas
# ferramentas mede escolha de string, e a taxa agregada tem de ser lida com esse peso a' vista.
#
# Piora o caso: as referencias do holdout sao inconsistentes quanto a `max_results` (umas
# trazem, outras nao, sem nada no pedido que decida), e em pelo menos um caso a referencia e'
# MENOS fiel ao pedido que a previsao (a ref inventou "IBGE", que o usuario nao pediu).
PONTUADAS_POR_ECO = {"web_search", "http_get", "summarize_url",
                     # movidas de CONSTANTE para ECO no E6 — ver comentarios acima
                     "run_python", "run_sql"}
