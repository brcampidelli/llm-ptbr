"""Converte o `function_call` do gigaverbo para a convenção agêntica do Bee.

🔴 POR QUE CONVERTER, E NÃO SIMPLESMENTE MISTURAR

As duas convenções são incompatíveis em três pontos, e o Bee já mede 64,7% de execução na
dele. Misturar ensinaria duas gramáticas ao mesmo tempo, e o avaliador só aceita uma — o
efeito sairia medido como "o dado piorou o modelo", que é falso e indistinguível do verdadeiro.

| | Bee | GigaVerbo |
|---|---|---|
| catálogo | prosa (`- web_search: …` / `args: …` / `obrigatorios: …`) | `<tools>` com JSON Schema |
| chamada | `{"tool":…,"args":{…}}` puro | `<tool_call>{"name":…,"arguments":{…}}</tool_call>` |
| retorno | papel **`tool`**, JSON | papel **`user`**, `<tool_response>` com **repr de Python** |

⚠️ O `<tool_response>` traz `{'password': '4&7j#9@1Q6*'}` — aspas simples, `True`/`None` do
Python. Isso **não é JSON** e `json.loads` falha nele. Passa por `ast.literal_eval`, que é
seguro (só literais) ao contrário de `eval`.

⭐ **E uma diferença que é ganho, não problema:** o Bee só viu **10 ferramentas**, sempre as
mesmas; o gigaverbo traz milhares de catálogos diferentes. Treinar assim ensina a **ler o
catálogo do prompt** em vez de decorar dez nomes — que é exatamente o que generaliza. O risco
oposto (piorar nas 10 do avaliador por diluição) é real e **medível**, e é assunto do E4.

⚠️ NADA É DESCARTADO EM SILÊNCIO. Todo diálogo que não converte é contado por motivo, e o
relatório imprime os motivos. Exemplo que some calado é o modo de falha mais caro do projeto.

Uso:
    python comeia/data/converter_gigaverbo_ferramenta.py --limite 500     # amostra
    python comeia/data/converter_gigaverbo_ferramenta.py --escrever
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
ENTRADA = RAIZ / "comeia" / "data" / "raw" / "gigaverbo" / "function_call"
SAIDA = RAIZ / "comeia" / "data" / "processed" / "gigaverbo_ferramenta.jsonl"

RX_TOOLS = re.compile(r"<tools>\s*(.*?)\s*</tools>", re.S)
RX_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
RX_RESP = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.S)
ESCLARECE = re.compile(
    r"(por favor,?\s+(me\s+)?(forne|inform|envi|diga|especifi)"
    r"|voc[eê] (pode|poderia) (me\s+)?(forne|inform|dizer|especifi)"
    r"|preciso (saber|de mais)|me (diga|informe|forne[cç]a))", re.I)

CABECALHO = ("Você é um assistente AGÊNTICO. Você tem acesso às ferramentas abaixo.\n\n"
             "FERRAMENTAS DISPONÍVEIS:\n")


def _tipo_legivel(esquema: dict) -> str:
    t = esquema.get("type", "valor")
    return {"string": "texto", "integer": "inteiro", "number": "numero",
            "boolean": "booleano", "array": "lista", "object": "objeto"}.get(t, str(t))


def catalogo_em_prosa(tools: list[dict]) -> str:
    """`<tools>` (JSON Schema) → o catálogo em prosa que o Bee usa.

    ⚠️ A descrição de cada argumento vem do próprio schema. Onde ela falta, entra só o tipo —
    inventar descrição aqui seria pôr no dado de treino texto que ninguém escreveu.
    """
    linhas = [CABECALHO]
    for t in tools:
        f = t.get("function", t)
        nome = f.get("name")
        if not nome:
            continue
        linhas.append(f"- {nome}: {f.get('description', '').strip()}\n")
        params = f.get("parameters") or {}
        props = params.get("properties") or {}
        if props:
            partes = []
            for k, v in props.items():
                desc = (v.get("description") or "").strip()
                partes.append(f"{k} ({desc})" if desc else f"{k} ({_tipo_legivel(v)})")
            linhas.append("    args: " + ", ".join(partes) + "\n")
        obrig = params.get("required") or []
        if obrig:
            linhas.append("    obrigatorios: " + ", ".join(obrig) + "\n")
    linhas.append("\nResponda com UM objeto JSON: "
                  '{"tool": "<nome>", "args": {...}}. '
                  "Se nenhuma ferramenta servir, responda em texto normal.\n")
    return "".join(linhas)


def _para_json(bruto: str):
    """`<tool_response>` vem em repr de Python. `ast.literal_eval` é seguro; `eval` não."""
    try:
        return json.loads(bruto)
    except json.JSONDecodeError:
        return ast.literal_eval(bruto)


def converter(msgs: list[dict]) -> tuple[list[dict] | None, str]:
    """(mensagens na convenção do Bee, motivo). `None` = não convertido, com o porquê."""
    if not msgs or msgs[0].get("role") != "system":
        return None, "sem_system"
    # 🔴 A PRIMEIRA OCORRENCIA DE <tools> E' VAZIA, DE PROPOSITO. O proprio prompt EXPLICA a
    #    convencao antes de usa-la — "Voce recebe assinaturas de funcoes dentro de tags XML
    #    <tools></tools>:" — e uma regex nao-gulosa casa com essa mencao literal, devolve
    #    string vazia e para ali. Deu 88,3% de "tools_vazio" e por um momento pareceu dado
    #    ruim. Era a regex lendo a DESCRICAO em vez do CONTEUDO.
    #    Correto: pegar o primeiro bloco NAO VAZIO.
    blocos = [b for b in RX_TOOLS.findall(msgs[0].get("content", "")) if b.strip()]
    if not blocos:
        return None, "system_sem_bloco_tools"
    try:
        # o bloco traz um JSON por linha, nao um array
        tools = [json.loads(l) for l in blocos[0].splitlines() if l.strip()]
    except json.JSONDecodeError:
        return None, "tools_nao_e_json"
    if not tools:
        return None, "tools_vazio"

    fora = [{"role": "system", "content": catalogo_em_prosa(tools)}]
    nomes = {(t.get("function", t)).get("name") for t in tools}
    houve_chamada = False
    for msg in msgs[1:]:
        papel, texto = msg.get("role"), msg.get("content", "")
        if papel == "assistant" and RX_CALL.search(texto):
            chamadas = RX_CALL.findall(texto)
            if len(chamadas) != 1:
                # 🔴 chamada paralela: o Bee emite UMA por turno e o avaliador le' UMA.
                #    Converter para uma so' inventaria a resposta; e' descarte declarado.
                return None, "chamadas_paralelas"
            try:
                c = json.loads(chamadas[0])
            except json.JSONDecodeError:
                return None, "tool_call_nao_e_json"
            if c.get("name") not in nomes:
                return None, "chamou_ferramenta_fora_do_catalogo"
            fora.append({"role": "assistant",
                         "content": json.dumps({"tool": c.get("name"),
                                                "args": c.get("arguments") or {}},
                                               ensure_ascii=False)})
            houve_chamada = True
        elif RX_RESP.search(texto):
            try:
                v = _para_json(RX_RESP.search(texto).group(1))
            except (ValueError, SyntaxError):
                return None, "tool_response_ilegivel"
            fora.append({"role": "tool", "content": json.dumps(v, ensure_ascii=False)})
        else:
            fora.append({"role": papel, "content": texto})
    if not houve_chamada:
        return fora, "convertido_sem_chamada"   # negativo: vale ouro, ver §4 do doc do E3
    return fora, "convertido"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ENTRADA)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    ap.add_argument("--score-min", type=float, default=4.0)
    ap.add_argument("--limite", type=int, default=0, help="0 = tudo")
    ap.add_argument("--sem-esclarecimento", action="store_true",
                    help="descarta dialogos que pedem esclarecimento ANTES da 1a chamada")
    ap.add_argument("--com-duplicatas", action="store_true",
                    help="mantem duplicatas (o default DEDUPLICA por (pedido, chamada))")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args()

    import pyarrow.parquet as pq

    arquivos = sorted(a.entrada.glob("*.parquet"))
    if not arquivos:
        print(f"🔴 nenhum parquet em {a.entrada}", file=sys.stderr)
        return 1
    tabela = pq.read_table(arquivos[0])
    n_total = tabela.num_rows
    linhas = tabela.to_pylist()
    if a.limite:
        linhas = linhas[:a.limite]

    print("=" * 78)
    print(f"CONVERSAO function_call: gigaverbo (Hermes XML) -> Bee (JSON puro)")
    print("=" * 78)
    print(f"entrada        : {n_total:,} linhas" + (f" (limite {a.limite:,})" if a.limite else ""))
    print(f"score minimo   : {a.score_min}")
    print(f"esclarecimento : {'DESCARTADO' if a.sem_esclarecimento else 'mantido'}")

    motivos, saida = Counter(), []
    n_score, n_escl = 0, 0
    for reg in linhas:
        if a.score_min and (reg.get("instruct_score") or 0) < a.score_min:
            n_score += 1
            motivos["reprovado_no_score"] += 1
            continue
        msgs = reg.get("messages") or []
        novo, motivo = converter(list(msgs))
        motivos[motivo] += 1
        if novo is None:
            continue
        if a.sem_esclarecimento:
            idx = next((i for i, m in enumerate(novo)
                        if m["role"] == "assistant" and m["content"].startswith('{"tool"')), None)
            if idx is not None and any(ESCLARECE.search(m["content"])
                                       for m in novo[:idx] if m["role"] == "assistant"):
                n_escl += 1
                motivos["descartado_por_esclarecimento"] += 1
                continue
        saida.append({"messages": novo,
                      "kind": "tool_call" if motivo == "convertido" else "text",
                      "source": "gigaverbo_function_call",
                      "instruct_score": reg.get("instruct_score")})

    # 🔴 REDUNDANCIA INTERNA MEDIDA, NAO SUPOSTA. Os 40.716 convertidos colapsam em 14.003
    #    pares (pedido, chamada) distintos e 9.303 pedidos: 65,6% de duplicata, com um par
    #    repetindo 969 vezes. O histograma tem a forma que a licao 2c-6 descreve — dano
    #    maximo em contagem INTERMEDIARIA (3-10x) — e "40.716 exemplos" e' manchete: a
    #    diversidade efetiva e' ~14 mil. A licao manda reportar o HISTOGRAMA, nao a media.
    if not a.com_duplicatas:
        def _par(r):
            u = next((m["content"] for m in r["messages"] if m["role"] == "user"), "")
            c = next((m["content"] for m in r["messages"] if m["role"] == "assistant"
                      and m["content"].startswith(chr(123) + chr(34) + "tool" + chr(34))), "")
            return u + "|" + c
        antes = len(saida)
        rep = Counter(_par(r) for r in saida)
        vistos, unicos = set(), []
        for r in saida:
            k = _par(r)
            if k in vistos:
                continue
            vistos.add(k)
            unicos.append(r)
        saida = unicos
        h = Counter(rep.values())
        print()
        print(f"redundancia interna: {antes:,} -> {len(saida):,} "
              f"({100*(1-len(saida)/max(1,antes)):.1f}% eram duplicata)")
        print("  histograma de repeticao (vezes -> quantos pares):")
        for kk in sorted(h)[:6]:
            print(f"    {kk:>3}x : {h[kk]:>7,}")
        print(f"    max  : {max(rep.values())}x")
    print(f"\nmotivos ({len(linhas):,} lidos):")
    for m, c in motivos.most_common():
        marca = "✅" if m.startswith("convertido") else ("  " if "reprovado" in m or "descartado" in m else "🔴")
        print(f"  {marca} {m:38} {c:>7,}  ({100*c/len(linhas):5.1f}%)")

    positivos = sum(1 for r in saida if r["kind"] == "tool_call")
    negativos = len(saida) - positivos
    print(f"\nsobrevive     : {len(saida):,}")
    print(f"  positivos   : {positivos:,} ({100*positivos/max(1,len(saida)):.1f}%)")
    print(f"  ⚠️ negativos : {negativos:,} ({100*negativos/max(1,len(saida)):.1f}%)"
          "   <- 'nao chamar' e' a resposta certa")
    if negativos and positivos / max(1, negativos) > 3:
        print(f"  🔴 proporcao positivo:negativo = {positivos/max(1,negativos):.1f}:1 — o projeto")
        print("     ja' mediu que deslocar essa proporcao move o over-calling. Gerar negativos")
        print("     casados ANTES de treinar (receita Hammer).")

    if a.escrever:
        a.saida.parent.mkdir(parents=True, exist_ok=True)
        with a.saida.open("w", encoding="utf-8") as f:
            for r in saida:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n✅ {a.saida} ({len(saida):,} registros)")
        print("   ⚠️ AINDA FALTA: descontaminar contra os holdouts (04_decontaminate.py)")
        print("      e normalizar para prompt/completion (normalizar_formato_sft.py).")
    else:
        print("\n(sem --escrever: nada gravado)")
        if saida:
            print("\nAMOSTRA CONVERTIDA:")
            for m in saida[0]["messages"][:5]:
                c = m["content"]
                print(f"  [{m['role']}] {c[:180]}" + ("…" if len(c) > 180 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
