"""Roteador determinístico entre o adapter AGENTICO e o adapter de TEXTO.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-31 (E20/E21), com 698 passos nos tres corpora:

    dose de resumo    0%      2,6%     6,5%
    resumo util     0,0%      0,7%   14,7%
    execucao agent 68,1%     72,6%   59,1%   <- o preco aparece na dose que move o alvo
    macro agentica 76,8%     77,0%   74,4%

**Capacidade e' disputada** (E2, E19, E21). E o E2 ja' mediu a saida: multi-turno por full FT
custou −5,9 pp de execucao; por **adapter LoRA separado** custou **zero**. Este modulo testa
essa saida para o par (agentico, resumo).

## O desenho, e o que o torna um teste de verdade

⚠️ Os exemplos de resumo tem catalogo de ferramentas no `system` **de proposito** (§2u — sem
isso o modelo aprenderia "sem system -> resuma"). Logo o roteador **nao pode** decidir pela
presenca do catalogo: ele tem de ler o TURNO DO USUARIO. Sem essa escolha, o roteamento seria
trivial por uma caracteristica superficial e nao mediria nada.

⭐ Deterministico por decisao, nao por preguica: o recuperador lexical deste projeto (30 linhas,
IDF) bateu o modelo em selecao de ferramenta por **+26,7 pp**, sem GPU. Roteador que precisa de
LLM para rotear paga latencia e introduz um segundo modo de falha.

## ⚠️ E a ressalva honesta, dita antes do numero

Este par de tarefas torna o roteamento **facil**: "Resuma o texto abaixo" e' uma frase quase
unica. A acuracia alta abaixo NAO e' evidencia de que roteamento e' facil em geral — e' evidencia
de que ESTE par e' separavel. O numero que interessa no experimento nao e' o do roteador; e' se
DOIS adapters recuperam as duas capacidades que UM nao consegue segurar juntas.

Uso:
    python comeia/eval/roteador.py --medir      # acuracia do roteador, sem GPU
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
NL = chr(10)

# ⭐ Gatilhos do lado TEXTO. Casam no turno do usuario, nunca no `system`.
RX_TEXTO = re.compile(
    r"\b(resuma|resumir|resumo d[eoa]|sintetize|em duas frases"
    r"|faca um resumo|escreva um resumo)\b")


def nz(s: str) -> str:
    t = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


def rotear(prompt: list[dict]) -> str:
    """'texto' ou 'agentico'. Le' SO' os turnos do usuario — ver o cabecalho sobre a §2u."""
    usuario = NL.join(m["content"] for m in prompt if m.get("role") != "system")
    return "texto" if RX_TEXTO.search(nz(usuario)) else "agentico"


def carregar(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--medir", action="store_true")
    a = ap.parse_args()
    if not a.medir:
        ap.print_help()
        return 0

    # Holdout MISTO: os 3 conjuntos que os dois adapters tem de atender.
    # ⚠️ o rotulo verdadeiro vem da ORIGEM do item, nao de inspecao do texto.
    itens: list[tuple[list[dict], str, str]] = []
    for r in carregar(PROC / "holdout_balanceado.eval.jsonl"):
        itens.append((r["prompt"], "agentico",
                      "agentico/tool" if r.get("kind") == "tool_call" else "agentico/texto"))
    ben = json.loads((RAIZ / "eval" / "benchmarks" / "resumo_pt.jsonl")
                     .read_text(encoding="utf-8").splitlines()[0])
    pedido = ("Resuma o texto abaixo em duas frases, mantendo os números e os nomes exatamente "
              "como aparecem.")
    for r in [json.loads(l) for l in (RAIZ / "eval" / "benchmarks" / "resumo_pt.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]:
        itens.append(([{"role": "user", "content": f"{pedido}{NL}{NL}{r['fonte']}"}],
                      "texto", "resumo"))

    st: Counter = Counter()
    erros: list[str] = []
    for prompt, verdade, origem in itens:
        pred = rotear(prompt)
        st[(origem, "OK" if pred == verdade else f"ERRO->{pred}")] += 1
        if pred != verdade and len(erros) < 5:
            u = NL.join(m["content"] for m in prompt if m.get("role") != "system")
            erros.append(f"    [{origem}] previu {pred}: {u[:90]!r}")

    print(f"holdout misto: {len(itens)} itens")
    print(f"{'origem':22}{'OK':>6}{'ERRO':>7}{'acerto':>9}")
    for origem in ("agentico/tool", "agentico/texto", "resumo"):
        ok = st[(origem, "OK")]
        err = sum(v for (o, k), v in st.items() if o == origem and k != "OK")
        n = ok + err
        if n:
            print(f"{origem:22}{ok:>6}{err:>7}{ok / n:>9.1%}")
    tot_ok = sum(v for (_, k), v in st.items() if k == "OK")
    print(f"{'TOTAL':22}{tot_ok:>6}{len(itens) - tot_ok:>7}{tot_ok / len(itens):>9.1%}")
    if erros:
        print(f"{NL}  erros:")
        print(NL.join(erros))
    print(f"{NL}⚠️ Acuracia alta aqui NAO e' evidencia de que rotear e' facil em geral — este par"
          f" de tarefas e' separavel por uma frase quase unica. O numero que decide o"
          f" experimento e' o das CAPACIDADES, nao o do roteador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
