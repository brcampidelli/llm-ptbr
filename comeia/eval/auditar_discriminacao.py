"""Para cada ferramenta simulada: O QUE, no resultado, discrimina uma chamada de outra?

🔴 POR QUE ISTO EXISTE (E6, 2026-08-22). O rejection sampling colheu como CORRETO:

    {"tool": "run_python", "args": {"code": "f"}}

porque `_run_python` devolve `{"compila": True}` para qualquer string sintaticamente valida —
resultado CONSTANTE, discriminacao zero. Treinar nesse reforco ensinaria o modelo a emitir
`{"code": "f"}`.

E' o oposto do defeito que o E5c achou: la' `web_search` ecoava a query (severo demais para
texto livre); aqui `run_python` nao olha nada (frouxo a ponto de nao medir).

⭐ O teste: para cada ferramenta, gerar N chamadas com argumentos DIFERENTES e contar quantos
resultados DISTINTOS saem. Se sai 1 resultado para N entradas, a ferramenta nao discrimina e
todo acerto nela e' de graca.

Uso:
    python comeia/eval/auditar_discriminacao.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tools_exec as TE  # noqa: E402

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Argumentos plausiveis e DIFERENTES entre si por ferramenta. A pergunta nao e' "executa?",
# e' "resultados diferentes para entradas diferentes?".
SONDAS: dict[str, list[dict]] = {
    "web_search": [{"query": "clima em Recife"}, {"query": "preco do cafe"},
                   {"query": "clima em Recife hoje"}, {"query": "receita de bolo"}],
    "http_get": [{"url": "https://a.com/x"}, {"url": "https://b.com/y"},
                 {"url": "https://a.com/x?q=1"}, {"url": "https://a.com/x/"}],
    "read_file": [{"path": "/etc/hosts"}, {"path": "/var/log/syslog"},
                  {"path": "/etc/hosts/"}, {"path": "/tmp/a.txt"}],
    "write_file": [{"path": "/tmp/a", "content": "x"}, {"path": "/tmp/b", "content": "x"},
                   {"path": "/tmp/a", "content": "yy"}, {"path": "/tmp/a", "content": "zz"}],
    "list_dir": [{"path": "/etc"}, {"path": "/var"}, {"path": "/etc/"}, {"path": "/tmp"}],
    "run_sql": [{"query": "SELECT 1"}, {"query": "SELECT 2"},
                {"query": "SELECT * FROM t"}, {"query": "DELETE FROM t"}],
    "run_python": [{"code": "f"}, {"code": "print(1)"}, {"code": "x=2**10"},
                   {"code": "'abc'[::-1]"}],
    "calculator": [{"expression": "2+2"}, {"expression": "9876/32"},
                   {"expression": "4"}, {"expression": "sqrt(16)"}],
    "get_weather": [{"city": "Recife"}, {"city": "Curitiba"},
                    {"city": "recife"}, {"city": "Belem"}],
    "send_email": [{"to": "a@x.com", "subject": "s1", "body": "b1"},
                   {"to": "b@x.com", "subject": "s1", "body": "b1"},
                   {"to": "a@x.com", "subject": "s2", "body": "b1"},
                   {"to": "a@x.com", "subject": "s1", "body": "b2"}],
    "create_calendar_event": [{"title": "t1", "start": "2026-01-01T10:00"},
                              {"title": "t2", "start": "2026-01-01T10:00"},
                              {"title": "t1", "start": "2026-01-02T10:00"},
                              {"title": "t1", "start": "2026-01-01T11:00"}],
    "get_stock_price": [{"ticker": "AAPL"}, {"ticker": "MSFT"},
                        {"ticker": "aapl"}, {"ticker": "PETR4"}],
    "translate_text": [{"text": "ola mundo", "target_lang": "en"},
                       {"text": "tchau mundo", "target_lang": "en"},
                       {"text": "ola mundo", "target_lang": "es"},
                       {"text": "ola mund0", "target_lang": "en"}],
    "summarize_url": [{"url": "https://a.com/1"}, {"url": "https://a.com/2"},
                      {"url": "https://b.com/1"}, {"url": "https://a.com/1/"}],
}


def main() -> int:
    TE.garantir_fixtures()
    faltando = sorted(set(TE.FERRAMENTAS) - set(SONDAS))
    if faltando:
        print(f"⚠️ sem sonda (a auditoria NAO as cobre): {faltando}")

    print("=" * 82)
    print("DISCRIMINACAO POR FERRAMENTA — quantos resultados DISTINTOS para N entradas distintas")
    print("=" * 82)
    ruins = []
    for nome in sorted(SONDAS):
        if nome not in TE.FERRAMENTAS:
            continue
        res, erros = [], 0
        for a in SONDAS[nome]:
            ok, r = TE.executar({"tool": nome, "args": a})
            if ok:
                res.append(json.dumps(r, sort_keys=True, ensure_ascii=False, default=str))
            else:
                erros += 1
        n_dist = len(set(res))
        n_in = len(SONDAS[nome])
        if n_dist <= 1 and res:
            marca, nota = "🔴", "CONSTANTE — todo acerto e' de graca"
            ruins.append(nome)
        elif n_dist < len(res):
            marca, nota = "⚠️ ", f"colapsa {len(res) - n_dist} entradas distintas"
        else:
            marca, nota = "✅", ""
        print(f"  {marca} {nome:24} {n_dist} resultado(s) para {n_in} entradas"
              f"{'  · ' + str(erros) + ' erro(s)' if erros else ''}   {nota}")
        if n_dist <= 1 and res:
            print(f"        sempre: {res[0][:70]}")

    print()
    if ruins:
        print(f"🔴 {len(ruins)} ferramenta(s) sem discriminacao: {ruins}")
        print("   Acerto nelas nao e' evidencia de nada, e reforco colhido nelas e' lixo.")
    else:
        print("nenhuma ferramenta constante")
    print()
    print("⚠️ 'colapsa' nem sempre e' defeito: get_weather colapsar 'Recife' e 'recife' e' o")
    print("   comportamento CERTO (mesma cidade). O que decide e' se as entradas colapsadas")
    print("   sao semanticamente a mesma coisa — por isso a tabela nao vira veredito sozinha.")
    return 1 if ruins else 0


if __name__ == "__main__":
    raise SystemExit(main())
