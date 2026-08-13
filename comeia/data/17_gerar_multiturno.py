"""Gera dialogos MULTI-TURNO com papel `tool` — o que falta por completo no treino.

⚠️ O BURACO QUE ISTO PREENCHE (medido em 2026-08-12):
    Dos 1.645 exemplos agenticos, ZERO tem papel `tool` e ZERO tem mais de um turno de
    assistente. Todos seguem exatamente (system, user, assistant). O system prompt chega a
    dizer "chame APENAS a PRIMEIRA ferramenta". Ou seja: **o modelo nunca viu o que fazer
    com o retorno de uma ferramenta** — ele emite a chamada e acabou.

    Isso e o teto de qualquer uso agentico real, e nao se resolve com prompt: e ausencia de
    dado. A literatura mede o tamanho do problema em modelos pequenos (xLAM-2-1b: 53,97%
    geral mas 8,38% multi-turno; Qwen3-0.6B: 45,76% -> 1,38%; TinyLlama: 0,00%).

⭐ COMO OS DADOS SAO GERADOS — sem professor externo, sem alucinacao:
    1. pega a chamada de REFERENCIA de cada exemplo `tool_call` existente;
    2. EXECUTA no mundo simulado (o mesmo `tools_exec.py` que ja usamos para avaliar);
    3. converte o resultado bruto num retorno APRESENTAVEL (o executor devolve hashes,
       uteis para comparar chamadas mas impossiveis de virar dialogo);
    4. escreve a resposta final por MOLDE deterministico, escolhido por hash do exemplo.

    A resposta final e template, e isso e deliberado: o que queremos ensinar aqui nao e
    redacao — o Bee ja escreve portugues excelente — e sim a ESTRUTURA do turno: "depois de
    um `role=tool` vem uma resposta que USA aquele dado". Template garante que o dado citado
    esta correto por construcao, coisa que um professor externo nao garantiria.

⚠️ LIMITE ASSUMIDO: variedade estilistica baixa. Ha 3-4 moldes por ferramenta, escolhidos
   deterministicamente. Se o modelo passar a responder de forma engessada apos o treino, o
   remedio e mais moldes — nao mais exemplos dos mesmos.

Uso:
    python comeia/data/17_gerar_multiturno.py                     # treino
    python comeia/data/17_gerar_multiturno.py --eval              # holdout
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "eval"))

from common import read_jsonl                          # noqa: E402
import tools_exec as TE                                 # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PROC = RAIZ / "data" / "processed"


def _h(s: str, n: int) -> int:
    """Indice estavel a partir do texto — variedade sem aleatoriedade."""
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16) % n


# ── retornos APRESENTAVEIS ────────────────────────────────────────────────────
# O executor devolve hashes (conteudo_id, listagem_id) porque a funcao dele e COMPARAR
# chamadas. Para o dialogo precisamos de algo que uma resposta possa citar. Continua
# deterministico: mesmo argumento, mesmo retorno, sempre.

# ⚠️ O conteudo sintetico tem de ser COERENTE com o que foi pedido. A v1 escolhia por hash
# do caminho e produziu isto: usuario pede "/var/log/apache2/error.log" e a ferramenta devolve
# "lista de tarefas - revisar contrato". O modelo aprenderia a associar log de erro com lista
# de compras. Agora o conteudo e escolhido pelo TIPO do arquivo, inferido do caminho.
_POR_TIPO: dict[str, list[str]] = {
    "log": [
        "[ERROR] 2026-03-12 04:11:02 conexao recusada em db:5432\n[WARN] retry 1/3",
        "[ERROR] timeout apos 30s no servico de pagamento\n[INFO] fallback acionado",
    ],
    "codigo": [
        "def calcular_total(itens):\n    return sum(i.preco for i in itens)",
        "import os\n\ndef main():\n    print('ok')\n\nif __name__ == '__main__':\n    main()",
    ],
    "relatorio": [
        "Relatorio de vendas\n\nTotal do trimestre: R$ 128.400,00\nCrescimento: 12%",
        "Relatorio mensal\n\nReceita: R$ 84.200,00\nDespesas: R$ 61.900,00",
    ],
    "tarefas": [
        "lista de tarefas\n- revisar contrato\n- enviar nota fiscal\n- agendar reuniao",
        "pendencias\n- responder cliente\n- fechar o mes\n- atualizar planilha",
    ],
    "config": [
        "config: producao\ntimeout=30\nretries=3", "[server]\nport=8080\ndebug=false",
    ],
    "generico": [
        "Ata da reuniao de 12/03\nParticipantes: 6\nDecisao: aprovar o orcamento",
        "Anotacoes\n\nRevisar o cronograma ate sexta.",
    ],
}
_LISTAGEM_POR_TIPO: dict[str, list[list[str]]] = {
    "log": [["error.log", "access.log", "syslog"], ["app.log", "db.log"]],
    "codigo": [["main.py", "utils.py", "README.md"], ["index.js", "app.js", "package.json"]],
    "documentos": [["relatorio.pdf", "contrato_v2.docx", "notas.txt"],
                   ["proposta.pdf", "ata.docx"]],
    "imagens": [["foto1.png", "foto2.png", "video.mp4"], ["logo.svg", "banner.png"]],
    "generico": [["backup_01.zip", "backup_02.zip", "log.txt"], ["dados.csv", "leia-me.txt"]],
}


def _tipo_de(caminho: str) -> str:
    """Infere o tipo pelo caminho/extensao, para o retorno fazer sentido com o pedido."""
    p = str(caminho).lower()
    if "log" in p or p.endswith((".log", ".syslog")):
        return "log"
    if p.endswith((".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rb", ".sh")):
        return "codigo"
    if any(k in p for k in ("relatorio", "report", "vendas", "financ", "balanc")):
        return "relatorio"
    if any(k in p for k in ("tarefa", "todo", "lista", "pendenc", "compras")):
        return "tarefas"
    if any(k in p for k in ("config", ".ini", ".conf", ".yaml", ".yml", ".env")):
        return "config"
    return "generico"


def _tipo_dir(caminho: str) -> str:
    p = str(caminho).lower()
    if "log" in p:
        return "log"
    if any(k in p for k in ("src", "codigo", "projeto", "app")):
        return "codigo"
    if any(k in p for k in ("doc", "contrato", "relatorio")):
        return "documentos"
    if any(k in p for k in ("foto", "imagem", "midia", "picture")):
        return "imagens"
    return "generico"
_BUSCAS = [
    "3 resultados relevantes encontrados",
    "5 resultados encontrados nas fontes principais",
    "2 resultados recentes",
]


def retorno_apresentavel(tool: str, args: dict, bruto: dict) -> dict:
    """Converte o retorno do executor em algo que uma resposta possa citar."""
    a = args or {}
    if tool == "read_file":
        opts = _POR_TIPO[_tipo_de(a.get("path", ""))]
        return {"arquivo": a.get("path"), "conteudo": opts[_h(str(a.get("path")), len(opts))]}
    if tool == "list_dir":
        opts = _LISTAGEM_POR_TIPO[_tipo_dir(a.get("path", ""))]
        return {"diretorio": a.get("path"), "itens": opts[_h(str(a.get("path")), len(opts))]}
    if tool in ("web_search", "http_get", "summarize_url"):
        d = dict(bruto)
        d["resumo"] = _BUSCAS[_h(str(a), 3)]
        return d
    if tool == "run_sql":
        return {"linhas": 4, "amostra": [{"id": 1}, {"id": 2}]}
    if tool == "run_python":
        return {"saida": "executado com sucesso", "codigo_ok": True}
    if tool == "translate_text":
        return {"traducao": "[texto traduzido]", "idioma": (bruto or {}).get("idioma")}
    return bruto or {}


# ── moldes de resposta final, por ferramenta ──────────────────────────────────
def resposta_final(tool: str, args: dict, res: dict, semente: str) -> str | None:
    a, r = args or {}, res or {}
    m = lambda opts: opts[_h(semente, len(opts))]      # noqa: E731

    if tool == "get_weather":
        c, t, cond = r.get("cidade", ""), r.get("temp_c"), r.get("cond", "")
        return m([f"Em {c.title()} estão {t}°C, com tempo {cond}.",
                  f"A temperatura em {c.title()} é de {t}°C e o céu está {cond}.",
                  f"Agora em {c.title()}: {t}°C, {cond}."])
    if tool == "get_stock_price":
        return m([f"{r.get('ticker')} está cotada a R$ {r.get('preco')}.",
                  f"O preço atual de {r.get('ticker')} é R$ {r.get('preco')}.",
                  f"{r.get('ticker')}: R$ {r.get('preco')} no último fechamento."])
    if tool == "calculator":
        return m([f"O resultado é {r.get('resultado')}.",
                  f"O cálculo dá {r.get('resultado')}.",
                  f"Resultado: {r.get('resultado')}."])
    if tool == "read_file":
        prim = str(r.get("conteudo", "")).splitlines()[0] if r.get("conteudo") else ""
        return m([f"Li o arquivo. Ele começa com: \"{prim}\".",
                  f"O conteúdo de {r.get('arquivo')} traz: \"{prim}\".",
                  f"Segue o que encontrei no arquivo: \"{prim}\"."])
    if tool == "list_dir":
        itens = r.get("itens") or []
        return m([f"O diretório tem {len(itens)} itens: {', '.join(itens)}.",
                  f"Encontrei {len(itens)} arquivos: {', '.join(itens)}.",
                  f"Conteúdo de {r.get('diretorio')}: {', '.join(itens)}."])
    if tool in ("web_search", "http_get", "summarize_url"):
        return m([f"A busca retornou: {r.get('resumo', 'resultados encontrados')}.",
                  f"Encontrei o seguinte: {r.get('resumo', 'resultados')}.",
                  f"Resultado da consulta: {r.get('resumo', 'dados obtidos')}."])
    if tool == "send_email":
        return m([f"E-mail enviado para {r.get('enviado_para')}.",
                  f"Pronto, a mensagem foi enviada a {r.get('enviado_para')}.",
                  f"Enviei o e-mail para {r.get('enviado_para')} com sucesso."])
    if tool == "create_calendar_event":
        return m([f"Evento criado para {r.get('inicio')}.",
                  f"Agendado: o evento começa em {r.get('inicio')}.",
                  f"Pronto, marquei o evento para {r.get('inicio')}."])
    if tool == "write_file":
        return m([f"Arquivo {r.get('escrito')} gravado ({r.get('bytes')} bytes).",
                  f"Escrevi {r.get('bytes')} bytes em {r.get('escrito')}.",
                  f"Pronto, salvei o conteúdo em {r.get('escrito')}."])
    if tool == "run_sql":
        return m([f"A consulta retornou {r.get('linhas')} linhas.",
                  f"Foram encontradas {r.get('linhas')} linhas.",
                  f"Resultado: {r.get('linhas')} registros."])
    if tool == "run_python":
        return m(["O código foi executado com sucesso.",
                  "Executei o código; rodou sem erros.",
                  "Pronto — o script rodou e terminou sem erro."])
    if tool == "translate_text":
        return m([f"Aqui está a tradução: {r.get('traducao')}",
                  f"Traduzido: {r.get('traducao')}",
                  f"A tradução ficou assim: {r.get('traducao')}"])
    return None                                   # ferramenta sem molde: nao gera exemplo


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", action="store_true", help="usa o holdout em vez do treino")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--tokenizer", default="BrCamp/bee-150m-pt-sft-v2")
    ap.add_argument("--max-len", type=int, default=2048)
    args = ap.parse_args()

    origem = PROC / ("sft_agentic.eval.jsonl" if args.eval else "sft_agentic.jsonl")
    destino = args.out or PROC / ("sft_multiturno.eval.jsonl" if args.eval
                                  else "sft_multiturno.jsonl")
    TE.garantir_fixtures()

    saida, stats = [], Counter()
    for row in read_jsonl(origem):
        if row.get("kind") != "tool_call":
            continue
        msgs = list(row.get("prompt") or [])
        ref = next((m["content"] for m in (row.get("completion") or [])
                    if m["role"] == "assistant"), None)
        obj = _d7.extract_json(ref) if ref else None
        if not obj:
            stats["sem_json"] += 1
            continue

        ok, bruto = TE.executar(obj)
        if not ok:
            # gabarito que nao executa nao vira dialogo — contamos em vez de sumir com ele
            stats["nao_executa"] += 1
            continue

        tool, a = obj.get("tool"), obj.get("args") or {}
        res = retorno_apresentavel(tool, a, bruto)
        usuario = next((m["content"] for m in msgs if m["role"] == "user"), "")
        final = resposta_final(tool, a, res, usuario)
        if not final:
            stats["sem_molde"] += 1
            continue

        # ⚠️ Exemplo que passa de max_seq_len e DESCARTADO EM SILENCIO pelo TRL (licao de
        # 2026-08-12: foi assim que 100% do agentico sumiu de um treino). Aqui cortamos o
        # conteudo do retorno antes de gerar, e contamos o que nao coube.
        bruto_txt = json.dumps(res, ensure_ascii=False)
        if len(bruto_txt) > 1200:
            if isinstance(res.get("conteudo"), str):
                res["conteudo"] = res["conteudo"][:400] + " […]"
            stats["retorno_truncado"] += 1

        saida.append({
            # prompt vai ate o retorno da ferramenta; a loss cobra SO a resposta final —
            # que e exatamente o turno que o modelo nunca viu.
            "prompt": msgs + [
                {"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)},
                {"role": "tool", "content": json.dumps(res, ensure_ascii=False)},
            ],
            "completion": [{"role": "assistant", "content": final}],
            "kind": "multiturno",
            "origem": "executor_deterministico",
        })
        stats[tool] += 1

    # ⚠️ GUARDA DE COMPRIMENTO. O TRL descarta em SILENCIO o exemplo que passa de
    # max_seq_len (foi assim que 100% do agentico sumiu de um treino em 2026-08-12).
    # Preferimos descartar aqui, contando, a descobrir depois pela contagem de passos.
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(args.tokenizer)
        antes = len(saida)
        saida = [r for r in saida
                 if len(tok(tok.apply_chat_template(r["prompt"] + r["completion"],
                                                    tokenize=False)).input_ids) <= args.max_len]
        if antes - len(saida):
            stats["nao_coube"] = antes - len(saida)
    except Exception as e:                                   # noqa: BLE001
        print(f"  aviso: nao deu para conferir comprimento ({e}) — conferir antes de treinar")

    destino.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in saida) + "\n",
                       encoding="utf-8")

    print(f"origem : {origem.name}")
    print(f"gerados: {len(saida)} dialogos multi-turno")
    for k in ("sem_json", "nao_executa", "sem_molde", "retorno_truncado", "nao_coube"):
        if stats[k]:
            print(f"  descartados por {k}: {stats[k]}")
    print("\npor ferramenta:")
    for t, c in sorted(((k, v) for k, v in stats.items()
                        if k not in ("sem_json", "nao_executa", "sem_molde",
                                     "retorno_truncado", "nao_coube")),
                       key=lambda x: -x[1]):
        print(f"  {t:<24} {c}")
    print(f"\n[OK] {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
