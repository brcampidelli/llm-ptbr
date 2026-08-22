"""E5c — de que MORREM as chamadas agenticas que falham.

O plano do E5c supunha o modo de falha do arXiv:2601.05366: o modelo escolhe a ferramenta
certa e escreve o valor do parametro no idioma do usuario, violando uma convencao de
execucao em ingles.

🔴 ESSA SUPOSICAO NAO PODE SER HERDADA AQUI. As referencias deste holdout ja' usam
portugues nos campos de texto livre (`{"city": "Brasilia"}`, `{"query": "ultimas noticias
..."}`) e ingles so' nos identificadores (`ticker: AAPL`, `/var/log`). A convencao do
benchmark NAO e' a do paper, entao "escrever em portugues" pode ser o comportamento CERTO.
Este script mede em vez de supor.

⭐ E a evidencia principal nao e' a classificacao automatica: sao ~30 falhas, e o script
**imprime todas**. A tabela e' resumo; a leitura e' a prova. O projeto ja' pagou caro por
confiar em rotulo automatico que ninguem conferiu.

Uso:
    python comeia/eval/analisar_falhas_agentico.py --casos comeia/eval/results/casos_TAG.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# Marcas de portugues que NAO existem em ingles. Deliberadamente estreito: a presenca e'
# evidencia, a ausencia nao e' — texto portugues sem acento existe, e por isso o veredito
# final e' a leitura, nao este teste.
RX_DIACRITICO = re.compile(r"[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]")
PALAVRAS_PT = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "por", "que",
               "uma", "um", "as", "os", "no", "na", "nos", "nas", "sobre", "mais"}


def tem_marca_pt(s: str) -> bool:
    if RX_DIACRITICO.search(s):
        return True
    fichas = {t for t in re.split(r"[^\wÀ-ÿ]+", s.lower()) if t}
    return len(fichas & PALAVRAS_PT) >= 2


def norm(v) -> str:
    """Normaliza para comparar: minuscula, sem acento, espacos colapsados."""
    s = str(v).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def numerico(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None


def classificar(c: dict) -> tuple[str, str]:
    """Devolve (bucket, detalhe). Resumo — a evidencia e' a impressao integral."""
    if c.get("ferramenta_pred") is None:
        return "sem_json", "nada parseavel (under-call ou truncado)"
    if c["ferramenta_pred"] != c["ferramenta_ref"]:
        return "ferramenta_errada", f"{c['ferramenta_pred']} em vez de {c['ferramenta_ref']}"

    ap, ar = c.get("args_pred") or {}, c.get("args_ref") or {}
    kp, kr = set(ap), set(ar)
    if kp != kr:
        falta, sobra = sorted(kr - kp), sorted(kp - kr)
        return "chaves_diferentes", f"falta {falta or '-'} · sobra {sobra or '-'}"

    difs = [k for k in kr if norm(ap.get(k)) != norm(ar.get(k))]
    if not difs:
        return "so_acento_ou_caixa", f"identico apos normalizar: {sorted(kr)}"

    # a diferenca e' de IDIOMA? so' quando um lado tem marca de PT e o outro nao.
    de_idioma = []
    for k in difs:
        vp, vr = str(ap.get(k)), str(ar.get(k))
        if tem_marca_pt(vp) != tem_marca_pt(vr):
            de_idioma.append(k)
    if de_idioma and len(de_idioma) == len(difs):
        return "idioma", f"{de_idioma}: {[(str(ap[k])[:40], str(ar[k])[:40]) for k in de_idioma]}"

    num = [k for k in difs if numerico(ap.get(k)) is not None and numerico(ar.get(k)) is not None]
    if num and len(num) == len(difs):
        return "valor_numerico", f"{[(k, ap[k], ar[k]) for k in num]}"

    return "valor_diferente", f"{[(k, str(ap[k])[:40], str(ar[k])[:40]) for k in difs]}"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", type=Path, required=True)
    ap.add_argument("--mostrar-brutos", type=int, default=3,
                    help="quantas saidas CRUAS imprimir por bucket (0 desliga). "
                         "Ler a saida crua e' o que separa 'o modelo nao sabe' de "
                         "'a regua nao escuta'.")
    a = ap.parse_args()

    casos = [json.loads(l) for l in a.casos.read_text(encoding="utf-8").splitlines() if l.strip()]
    tools = [c for c in casos if c["tipo"] == "tool"]
    textos = [c for c in casos if c["tipo"] == "text"]
    falhas = [c for c in tools if not c["exec_ok"]]
    passou = [c for c in tools if c["exec_ok"]]

    print("=" * 78)
    print(f"AGENTICO — {len(tools)} casos com ferramenta · {len(textos)} sem ferramenta")
    print(f"  executou e cumpriu   {len(passou)}/{len(tools)} = {len(passou)/max(1,len(tools)):.1%}")
    print(f"  falhou               {len(falhas)}/{len(tools)}")
    print("=" * 78)

    # ⭐ quantas que PASSARAM tinham argumentos diferentes da referencia? E' a medida de
    #    quanto a equivalencia funcional esta' carregando o numero — e de quanto
    #    "argumentos identicos" subestima a capacidade real.
    eq_func = [c for c in passou
               if {k: norm(v) for k, v in (c.get("args_pred") or {}).items()}
               != {k: norm(v) for k, v in (c.get("args_ref") or {}).items()}]
    print(f"\ndos {len(passou)} que passaram, {len(eq_func)} tinham argumentos DIFERENTES da "
          f"referencia\n  (equivalencia funcional: 'argumentos identicos' subestima em "
          f"{len(eq_func)} casos)")

    baldes: dict[str, list[tuple[dict, str]]] = {}
    for c in falhas:
        b, det = classificar(c)
        baldes.setdefault(b, []).append((c, det))

    print("\n" + "-" * 78)
    print(f"MODO DE FALHA dos {len(falhas)} que falharam:")
    for b, itens in sorted(baldes.items(), key=lambda kv: -len(kv[1])):
        print(f"  {b:22} {len(itens):3}/{len(falhas)} = {len(itens)/max(1,len(falhas)):5.1%}")

    # ⭐ quanto do numero agregado e' decidido por igualdade de string em vez de execucao
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import tools_exec as TE
    eco = [c for c in tools if c["ferramenta_ref"] in TE.PONTUADAS_POR_ECO]
    exe = [c for c in tools if c["ferramenta_ref"] not in TE.PONTUADAS_POR_ECO]
    print("\n" + "-" * 78)
    print("COMO O CASO E' PONTUADO (ver PONTUADAS_POR_ECO em tools_exec.py):")
    for rot, grupo in [("por EXECUCAO  ", exe), ("por ECO de string", eco)]:
        if grupo:
            ok = sum(1 for c in grupo if c["exec_ok"])
            print(f"  {rot}  {ok}/{len(grupo)} = {ok/len(grupo):5.1%}")
    print(f"  ⚠️ {sum(1 for c in eco if not c['exec_ok'])}/{len(falhas)} das falhas estao em "
          f"ferramentas cujo acerto e' igualdade exata de string livre,")
    print("     onde uma parafrase igualmente boa conta como erro.")

    por_tool = Counter(c["ferramenta_ref"] for c in falhas)
    print("\nfalhas por ferramenta de referencia:")
    for t, n in por_tool.most_common():
        tot = sum(1 for c in tools if c["ferramenta_ref"] == t)
        print(f"  {t:20} {n}/{tot}")

    print("\n" + "=" * 78)
    print("TODAS AS FALHAS, UMA A UMA — esta e' a evidencia; a tabela acima e' resumo")
    print("=" * 78)
    for b, itens in sorted(baldes.items(), key=lambda kv: -len(kv[1])):
        print(f"\n### {b} ({len(itens)})")
        for c, det in itens:
            print(f"\n  [{c['i']}] {c['ferramenta_ref']}  ·  {det}")
            print(f"      pedido : {c['usuario'][:150]}")
            print(f"      ref    : {json.dumps(c['args_ref'], ensure_ascii=False)[:170]}")
            print(f"      previu : {json.dumps(c['args_pred'], ensure_ascii=False)[:170]}")

    if a.mostrar_brutos:
        print("\n" + "=" * 78)
        print(f"SAIDAS CRUAS ({a.mostrar_brutos} por balde) — com tokens especiais")
        print("=" * 78)
        for b, itens in sorted(baldes.items(), key=lambda kv: -len(kv[1])):
            print(f"\n### {b}")
            for c, _ in itens[:a.mostrar_brutos]:
                print(f"\n  [{c['i']}] --- bruto ---")
                print("      " + c["bruto"][:600].replace("\n", "\n      "))

    if textos:
        over = [c for c in textos if c.get("over_call")]
        print("\n" + "=" * 78)
        print(f"OVER-CALLING: {len(over)}/{len(textos)} = {len(over)/len(textos):.1%}")
        print("(medir os dois lados: bloquear chamada indevida so' e' ganho se nao matar "
              "chamada boa)")
        for c in over[:8]:
            print(f"\n  [{c['i']}] pedido: {c['usuario'][:120]}")
            print(f"      chamou: {c['bruto'][:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
