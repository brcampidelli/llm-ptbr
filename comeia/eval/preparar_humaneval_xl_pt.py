"""Converte o split português do HumanEval-XL para o formato do `eval_coder.py` — e executa
os 80 gabaritos antes de declarar o arquivo utilizável.

⭐ POR QUE ESTE CONJUNTO, SE JÁ EXISTEM 877 TAREFAS INTERNAS

As 877 tarefas de `coder_tasks.jsonl` são nossas: dão poder estatístico e refletem a
distribuição de dificuldade que nós escolhemos. Justamente por isso **não servem para
comparação externa** — não há número publicado de ninguém nelas.

O HumanEval-XL (arXiv:2402.16694, Apache-2.0, 23 idiomas × 12 linguagens) resolve o outro
lado: são 80 problemas com resultado publicado para dezenas de modelos, então "o Bee faz X%"
passa a ser uma frase com referente. Os dois conjuntos medem coisas diferentes e ambos ficam.

⚠️ 80 itens é POUCO. O intervalo de Wilson a 95% num n=80 tem largura de ~±11 pp perto de
   50% — diferença menor que isso entre dois modelos **não é diferença**. Quem ler o número
   precisa ver o intervalo, e por isso ele é impresso junto.

🔴 O QUE ESTE ARQUIVO GARANTE ANTES DE ENTREGAR O JSONL: que as 80 soluções canônicas passam
   nos 80 testes canônicos, dentro do MESMO executor (`code_exec.run_tests`) que vai julgar o
   modelo. Não basta o dataset ser publicado: o que importa é se ele executa *aqui*, com este
   sandbox, este timeout e esta lista de padrões proibidos. Um gabarito que não roda no nosso
   executor torna o item impossível por construção — e a conta desse erro este projeto já
   pagou uma vez, medindo 23,5% onde o real era 57,6%.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
from code_exec import run_tests  # noqa: E402

BRUTO = Path(__file__).resolve().parent / "benchmarks" / "humaneval_xl_pt_bruto.jsonl"
SAIDA = Path(__file__).resolve().parent / "benchmarks" / "humaneval_xl_pt.jsonl"
FONTE = "https://raw.githubusercontent.com/FloatAI/humaneval-xl/main/data/python/Portuguese.jsonl"


def converter(it: dict) -> dict:
    """Formato interno: name · prompt · tests (lista) · solution · tema.

    O teste do HumanEval-XL é um bloco que define `check(candidate)`; a chamada final não vem
    junto. Ela é acrescentada aqui, referenciando o `entry_point` declarado no próprio item.
    """
    return {
        "name": it["task_id"].replace("/", "_"),
        "prompt": it["prompt"],
        "tests": [it["test"], f"check({it['entry_point']})"],
        "solution": it["prompt"] + it["canonical_solution"],
        "tema": "humaneval-xl-pt",
        "entry_point": it["entry_point"],
        "origem": FONTE,
    }


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not BRUTO.exists():
        print(f"🔴 {BRUTO.name} nao existe. Baixe com:", file=sys.stderr)
        print(f'   curl -sS -A "curl/8.5.0" -o {BRUTO} {FONTE}', file=sys.stderr)
        return 1

    brutos = [json.loads(l) for l in BRUTO.read_text(encoding="utf-8").splitlines() if l.strip()]
    itens = [converter(b) for b in brutos]

    print("=" * 78)
    print("HumanEval-XL · split PORTUGUES — conversao e execucao dos gabaritos")
    print("=" * 78)
    print(f"origem : {FONTE}")
    print(f"itens  : {len(itens)}")

    maus = []
    for it in itens:
        r = run_tests(it["solution"], it["tests"])
        if not r.ok:
            maus.append((it["name"], r.detail[:130]))

    n_ok = len(itens) - len(maus)
    print(f"\n  gabaritos que executam NO NOSSO SANDBOX: {n_ok}/{len(itens)} = "
          f"{100 * n_ok / len(itens):.1f}%")

    if maus:
        print("\n  🔴 itens IMPOSSIVEIS por construcao (a solucao canonica falha no proprio")
        print("     teste, dentro do nosso executor). Sao excluidos do arquivo final —")
        print("     manter um deles rebaixaria o teto sem que ninguem soubesse:")
        for nome, d in maus[:12]:
            print(f"    · {nome:26} {d}")
        ruins = {n for n, _ in maus}
        itens = [it for it in itens if it["name"] not in ruins]

    with SAIDA.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # largura do intervalo de Wilson a 95% no pior caso (p=0,5), so' para constar
    n = len(itens)
    meia = 1.96 * (0.25 / n) ** 0.5 / (1 + 1.96 ** 2 / n) * 100
    print(f"\n  ✅ {n} itens gravados em {SAIDA.name} · teto verificado 100%")
    print(f"  ⚠️ n={n}: o intervalo de Wilson a 95% em torno de 50% e' de ±{meia:.1f} pp.")
    print("     Diferenca menor que isso entre dois modelos NAO e' diferenca.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
