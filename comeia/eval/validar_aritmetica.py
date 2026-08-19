"""Valida `benchmarks/aritmetica_pt.jsonl` ANTES de qualquer modelo ser carregado.

⭐ POR QUE ESTE SCRIPT RODA PRIMEIRO

  O conjunto que ele valida decide um GATE: `pass@256` do Bee-350M base abaixo de 3% encerra
  matematica como capacidade nos pesos e realoca o orcamento. Se um gabarito estiver errado,
  o numero que sai nao e' "um pouco pior" — e' uma decisao errada sobre uma capacidade
  inteira, tomada com a confianca de quem mediu.

  A conta ja foi paga uma vez neste projeto: 35 de 85 referencias eram impossiveis por
  construcao; a taxa medida saiu 23,5% quando a real era 57,6%; e por semanas a teoria
  discutiu o modelo enquanto o defeito estava no avaliador. A regra que sobrou:
  **executar todos os gabaritos antes de carregar qualquer modelo.**

⭐ O QUE ELE CHECA (falha dura → sai com codigo 1)
  1. esquema: campos presentes e com o tipo certo
  2. ⭐ `eval(expressao)` == `resposta`, tolerancia 1e-6 — a checagem que da nome ao script
  3. `passos` declarado == numero de operacoes contado na ARVORE da expressao
  4. resposta com no maximo 2 casas decimais
  5. ids repetidos
  6. enunciados repetidos (normalizados)
  7. ⭐ meta-guarda: se o arquivo estiver vazio, ABORTA — uma guarda que checou zero itens
     e imprime OK e' pior que guarda nenhuma, porque compra confianca sem entregar nada

⭐ O QUE ELE SO AVISA (nao derruba a saida)
  - concentracao de respostas: um valor que resolve mais de 5% dos itens mede chute, nao
    aritmetica
  - literais da expressao que nao aparecem no enunciado: o sintoma barato de o texto e a
    conta terem se soltado. Ha casos legitimos ("de terca a sexta" → 4; "duas vezes por
    dia" → 2), por isso e' aviso para leitura humana, nunca veredito automatico

A checagem 2 nao prova que o enunciado descreve a conta — nenhuma checagem automatica prova
isso. Ela prova que a conta declarada e a resposta declarada sao a mesma coisa, que e'
exatamente o erro que um humano (ou um gerador) comete em silencio.

Uso:
    python comeia/eval/validar_aritmetica.py
    python comeia/eval/validar_aritmetica.py --dados outro.jsonl --verboso
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PADRAO = RAIZ / "benchmarks" / "aritmetica_pt.jsonl"
TOLERANCIA = 1e-6
LIMIAR_CONCENTRACAO = 0.05   # 5% dos itens com a mesma resposta ja e' suspeito

_NOS_OK = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
)


def avaliar(expr: str) -> float:
    """`eval` da expressao, com a arvore checada antes: so aritmetica pura passa.

    O whitelist de nos nao e' paranoia de seguranca — e' a garantia de que `expressao` e'
    legivel por um humano em 2 segundos. Uma expressao que precisa de chamada de funcao para
    produzir o gabarito e' uma expressao que ninguem vai conferir.
    """
    arvore = ast.parse(expr, mode="eval")
    for no in ast.walk(arvore):
        if not isinstance(no, _NOS_OK):
            raise ValueError(f"no proibido: {type(no).__name__}")
    return eval(compile(arvore, "<gabarito>", "eval"), {"__builtins__": {}}, {})


def contar_passos(expr: str) -> int:
    return sum(1 for no in ast.walk(ast.parse(expr, mode="eval")) if isinstance(no, ast.BinOp))


def literais(expr: str) -> list[float]:
    return [float(no.value) for no in ast.walk(ast.parse(expr, mode="eval"))
            if isinstance(no, ast.Constant) and isinstance(no.value, (int, float))]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


# Extrator simples e proposital: serve APENAS ao aviso de literais ausentes. O extrator
# de verdade (formato brasileiro completo) vive em `eval_aritmetica_passk.py`, onde ele
# decide acerto e tem bateria de autotestes. Aqui um parser mais simples so deixaria o
# aviso mais ruidoso — nunca um veredito errado.
_NUM_ENUNCIADO = re.compile(r"\d[\d.]*(?:,\d+)?")


def numeros_do_enunciado(txt: str) -> set[float]:
    achados: set[float] = set()
    for bruto in _NUM_ENUNCIADO.findall(txt):
        s = bruto.rstrip(".,")
        if "," in s:                       # 1.234,56 → milhar com ponto, decimal com virgula
            s = s.replace(".", "").replace(",", ".")
        elif s.count(".") >= 1:            # 1.000 / 1.234.567 → ponto e' separador de milhar
            s = s.replace(".", "")
        try:
            achados.add(float(s))
        except ValueError:
            continue
    return achados


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", type=Path, default=PADRAO)
    ap.add_argument("--verboso", action="store_true", help="lista TODOS os avisos, nao so a amostra")
    args = ap.parse_args()

    if not args.dados.exists():
        print(f"🔴 ABORTA: {args.dados} nao existe.", file=sys.stderr)
        return 1

    itens: list[dict] = []
    with args.dados.open("r", encoding="utf-8-sig") as f:
        for n, linha in enumerate(f, 1):
            linha = linha.strip()
            if not linha:
                continue
            try:
                itens.append(json.loads(linha))
            except json.JSONDecodeError as e:
                print(f"🔴 ABORTA: JSON invalido em {args.dados}:{n}: {e}", file=sys.stderr)
                return 1

    # ⭐ meta-guarda: guarda que verificou zero itens tambem aborta.
    if not itens:
        print("🔴 ABORTA: o arquivo nao tem NENHUM item — a validacao checaria zero gabaritos.",
              file=sys.stderr)
        return 1

    falhas: list[tuple[str, str]] = []      # (id, motivo)
    campos = {"id": str, "pergunta": str, "expressao": str, "passos": int, "tema": str}

    for i, it in enumerate(itens):
        ident = it.get("id", f"<sem id, linha {i + 1}>")

        faltando = [c for c in campos if c not in it]
        if faltando:
            falhas.append((ident, f"campos ausentes: {faltando}"))
            continue
        tipo_errado = [c for c, t in campos.items() if not isinstance(it[c], t)]
        if tipo_errado:
            falhas.append((ident, f"tipo errado em {tipo_errado}"))
            continue
        if "resposta" not in it or not isinstance(it["resposta"], (int, float)) \
                or isinstance(it["resposta"], bool):
            falhas.append((ident, "campo 'resposta' ausente ou nao numerico"))
            continue
        if not it["pergunta"].strip():
            falhas.append((ident, "enunciado vazio"))
            continue

        # ---- 2. ⭐ A CHECAGEM QUE DECIDE: a expressao produz a resposta declarada?
        try:
            valor = avaliar(it["expressao"])
        except Exception as e:
            falhas.append((ident, f"expressao nao avalia: {it['expressao']!r} ({e})"))
            continue
        if abs(valor - it["resposta"]) > TOLERANCIA:
            falhas.append((ident, f"gabarito NAO confere: eval({it['expressao']!r}) = {valor!r}"
                                  f" mas resposta = {it['resposta']!r}"
                                  f"  (delta {abs(valor - it['resposta']):.6g})"))
            continue

        # ---- 3. passos declarado x contado na arvore
        real = contar_passos(it["expressao"])
        if real != it["passos"]:
            falhas.append((ident, f"passos declarado {it['passos']} != contado {real}"
                                  f" em {it['expressao']!r}"))
        if not 2 <= real <= 4:
            falhas.append((ident, f"{real} operacoes — fora da faixa 2..4 de multiplos passos"))

        # ---- 4. no maximo 2 casas decimais
        if abs(it["resposta"] - round(it["resposta"], 2)) > 1e-9:
            falhas.append((ident, f"resposta {it['resposta']!r} tem mais de 2 casas decimais"))

    # ---- 5 e 6. repetidos
    for ident, n in Counter(it.get("id", "?") for it in itens).items():
        if n > 1:
            falhas.append((ident, f"id repetido {n}x"))
    for chave, n in Counter(_norm(it.get("pergunta", "")) for it in itens).items():
        if n > 1:
            exemplo = next(it["id"] for it in itens if _norm(it.get("pergunta", "")) == chave)
            falhas.append((exemplo, f"enunciado repetido {n}x: {chave[:70]}..."))

    print("=" * 78)
    print(f"VALIDACAO — {args.dados.name}: {len(itens)} itens")
    print("=" * 78)

    if falhas:
        print(f"\n🔴 ABORTA: {len(falhas)} item(ns) com defeito.\n")
        for ident, motivo in falhas[: (len(falhas) if args.verboso else 40)]:
            print(f"  [{ident}] {motivo}")
        if not args.verboso and len(falhas) > 40:
            print(f"  ... e mais {len(falhas) - 40} (use --verboso)")
        print("\nIDs com defeito:")
        print("  " + ", ".join(sorted({f[0] for f in falhas})))
        print("\n⚠️  O defeito e' do AVALIADOR, nao do modelo. Corrigir o dataset e rodar de novo.")
        return 1

    print(f"\n✅ {len(itens)}/{len(itens)} gabaritos EXECUTAM e conferem (tolerancia {TOLERANCIA:g}).")
    print("   passos declarados batem com a contagem na arvore em 100% dos itens.")

    # ---------------- distribuicoes
    dist_p = Counter(it["passos"] for it in itens)
    dist_t = Counter(it["tema"] for it in itens)
    respostas = sorted(float(it["resposta"]) for it in itens)

    print("\n-- distribuicao de passos (operacoes encadeadas)")
    for p in sorted(dist_p):
        n = dist_p[p]
        print(f"   {p} operacoes: {n:>4}  ({n / len(itens):>5.1%})  {'#' * round(40 * n / len(itens))}")

    print(f"\n-- temas ({len(dist_t)} distintos)")
    for tema, n in dist_t.most_common():
        print(f"   {tema:<14} {n:>4}  ({n / len(itens):>5.1%})")

    inteiras = sum(1 for r in respostas if abs(r - round(r)) < 1e-9)
    print("\n-- faixa das respostas")
    print(f"   min {respostas[0]:>10.2f}   max {respostas[-1]:>10.2f}")
    print(f"   mediana {statistics.median(respostas):>10.2f}"
          f"   media {statistics.fmean(respostas):>10.2f}")
    q = statistics.quantiles(respostas, n=4)
    print(f"   quartis  Q1 {q[0]:.2f} · Q2 {q[1]:.2f} · Q3 {q[2]:.2f}")
    print(f"   inteiras {inteiras}/{len(itens)} ({inteiras / len(itens):.1%})"
          f"  ·  com decimais {len(itens) - inteiras}")

    # ---------------- avisos
    avisos = 0
    conc = Counter(float(it["resposta"]) for it in itens)
    suspeitas = [(v, n) for v, n in conc.most_common() if n / len(itens) > LIMIAR_CONCENTRACAO]
    print(f"\n-- concentracao de respostas (limiar {LIMIAR_CONCENTRACAO:.0%})")
    if suspeitas:
        avisos += 1
        print(f"   ⚠️  {len(suspeitas)} valor(es) acima do limiar — um chute fixo acertaria de graca:")
        for v, n in suspeitas:
            print(f"       {v} aparece {n}x ({n / len(itens):.1%})")
    else:
        v, n = conc.most_common(1)[0]
        print(f"   ✅ valor mais frequente: {v} com {n}x ({n / len(itens):.1%}) — abaixo do limiar")
        print(f"      {len(conc)} respostas distintas em {len(itens)} itens")

    ausentes: Counter = Counter()
    itens_com_ausente = 0
    for it in itens:
        do_texto = numeros_do_enunciado(it["pergunta"])
        falta = [x for x in literais(it["expressao"]) if x not in do_texto]
        if falta:
            itens_com_ausente += 1
            ausentes.update(falta)
    print("\n-- literais da expressao que NAO aparecem no enunciado (auditoria humana)")
    if ausentes:
        avisos += 1
        print(f"   ⚠️  {itens_com_ausente}/{len(itens)} itens usam algum numero implicito.")
        print("       Legitimo quando o enunciado escreve por extenso ('de terca a sexta' → 4,")
        print("       'duas vezes por dia' → 2). Ilegitimo se o texto e a conta se soltaram —")
        print("       conferir uma vez, por valor, e nao por item:")
        for v, n in ausentes.most_common(12):
            print(f"       {v!r:>10} implicito em {n:>4} itens")
    else:
        print("   ✅ todo literal da expressao aparece escrito no enunciado")

    print("\n" + "=" * 78)
    print(f"✅ DATASET APROVADO — {len(itens)} itens, 0 falhas, {avisos} categoria(s) de aviso.")
    print("   O aparato esta liberado para carregar o modelo.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
