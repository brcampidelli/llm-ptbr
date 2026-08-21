"""Executa as SOLUÇÕES DE REFERÊNCIA das 877 tarefas de código contra os próprios testes.

🔴 POR QUE ISTO PRECISA RODAR ANTES DE MEDIR QUALQUER MODELO

O critério do Estágio 0 é literal: os gabaritos de todo avaliador executam corretamente
**antes** de qualquer modelo ser carregado. O `eval_coder.py` é anterior a esse critério e
nunca passou por ele — mede pass@1 por execução desde julho sem que ninguém tenha conferido
se as soluções de referência passam nos testes que acompanham cada tarefa.

Se uma tarefa tem gabarito que falha no próprio teste, ela é **impossível por construção**, e
todo pass@1 medido nela é ruído descontado do modelo. É exatamente a falha que fez este
projeto medir 23,5% de execução agêntica quando a taxa real era 57,6%: 35 de 85 referências
eram irrealizáveis, e a conclusão errada durou semanas.

⭐ O sintoma de que o teto é menor que 100% NÃO aparece no resultado: um modelo que acerta 40%
   num conjunto com teto de 92% parece um modelo de 40%. Só a execução do gabarito revela.

Uso:
    python comeia/eval/testar_gabaritos_coder.py            # todas as 877
    python comeia/eval/testar_gabaritos_coder.py --limite 50
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
from code_exec import run_tests  # noqa: E402

TAREFAS = RAIZ / "data" / "raw" / "coder_tasks.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--tarefas", type=Path, default=TAREFAS)
    a = ap.parse_args()

    itens = [json.loads(l) for l in a.tarefas.read_text(encoding="utf-8").split(chr(10))
             if l.strip()]
    if a.limite:
        itens = itens[:a.limite]

    print("=" * 78)
    print("GABARITOS DE CODIGO — as solucoes de referencia passam nos proprios testes?")
    print("=" * 78)
    print(f"tarefas: {len(itens)} · {a.tarefas.name}")

    def rodar(it: dict):
        # a solucao de referencia costuma vir SEM a assinatura; o prompt e' o cabecalho
        for montagem in (it["solution"], it["prompt"] + "\n" + it["solution"]):
            r = run_tests(montagem, it["tests"])
            if r.ok:
                return it, True, ""
        return it, False, r.detail[:120]

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(rodar, itens))

    maus = [(it, d) for it, ok, d in res if not ok]
    por_tema = Counter(it["tema"] for it, _ in maus)
    n_ok = len(itens) - len(maus)

    print(f"\n  teto do conjunto: {n_ok}/{len(itens)} = {100 * n_ok / len(itens):.1f}%")
    if maus:
        print(f"\n  🔴 {len(maus)} tarefa(s) sao IMPOSSIVEIS por construcao — o gabarito delas")
        print("     nao passa no proprio teste. Todo pass@1 medido nelas e' ruido.")
        print("\n  por tema:")
        for tema, c in por_tema.most_common(10):
            print(f"    {tema:24} {c:>3}")
        print("\n  exemplos:")
        for it, d in maus[:8]:
            print(f"    · {it['name']:34} {d}")
        alvo = Path(__file__).resolve().parent / "results" / "coder_gabaritos_ruins.json"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(
            {"n_total": len(itens), "n_ruins": len(maus),
             "teto": n_ok / len(itens),
             "ruins": [{"name": it["name"], "tema": it["tema"], "erro": d} for it, d in maus]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  lista completa: {alvo}")
        print("\n  ⚠️ NAO e' motivo para abortar a medicao — e' motivo para DESCONTAR estas")
        print("     tarefas do denominador, ou corrigi-las. Medir sem saber o teto e' que")
        print("     produz numero nao-interpretavel.")
        return 1
    print("  ✅ 100% dos gabaritos passam. O teto do conjunto e' 100%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
