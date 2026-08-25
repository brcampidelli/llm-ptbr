"""Pontuação POR ARGUMENTO — o que destrava as 149 ferramentas diversas do corpus.

🔴 O QUE ISTO CONSERTA. O `mundo_aberto.py` só pontua por execução ferramenta cuja **fórmula**
dá para implementar — e no gigaverbo isso seleciona exatamente as aritméticas **templadas**.
Medido: o holdout de 600 casos tinha **87** tuplas (ferramenta, args) distintas, uma delas 42%
do total, e resolução real de ±10,3 pp — idêntica à do holdout de 85 que ele substituía.
Validabilidade de fórmula e diversidade são anticorrelacionadas neste corpus.

⭐ A SAÍDA: parar de tratar "eco" como defeito único. Há **três tipos de argumento**, e eles
pedem critérios diferentes:

    extraído   o valor está literalmente no pedido      -> igualdade normalizada E' a semantica
    temporal   o pedido diz "amanha as 15h", a chamada diz 2026-03-15T15:00
    formulado  o modelo REDIGE (subject, body, task)    -> nao ha' criterio exato

O defeito que o E5c achou em `web_search` era do terceiro tipo: duas queries diferentes podem
ser igualmente boas. Mas `send_email(to=...)` é do primeiro — ali igualdade **é** a semântica
certa, não um atalho.

⭐⭐ E A CLASSE É MEDIDA, NÃO DECLARADA: um argumento é "extraído" se o valor aparece
literalmente no pedido, e isso se conta no corpus inteiro. A divisão sai quase binária:

    send_email.recipient  94,8%      send_email.subject  0,0%
    send_email.to         96,7%      send_email.body     0,0%
    create_todo.due_date  56,7% (data)   create_todo.task   0,0%

⚠️ E A HONESTIDADE OBRIGATÓRIA: excluir os formulados torna o escore MAIS FÁCIL. Por isso o
comparador devolve sempre **quantos argumentos foram pontuados e quantos ficaram de fora**, e
uma chamada sem nenhum argumento pontuável é **recusada**, nunca contada como acerto trivial.

Uso:
    python comeia/eval/argumentos.py --perfilar     # deriva e valida o perfil
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

PERFIL = Path(__file__).with_name("argumentos_perfil.json")

CORTE_EXTRAIDO = 0.80        # >= isto e' extraido
CORTE_FORMULADO = 0.10       # <= isto e' formulado (e nao temporal)
MIN_AMOSTRAS = 5             # abaixo disto nao se classifica: fica "raro"
CORTE_CONVENCAO = 0.90       # <- abaixo disto o par temporal e' AMBIGUO e sai do escore

RX_TEMPORAL = re.compile(r"(date|time|data|hora|dia|prazo|deadline|due|start|end|when)", re.I)
RX_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
RX_HORA = re.compile(r"(\d{1,2})[:h](\d{2})")


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def num(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-+]", "", str(v))
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) != 3 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def temporal_norm(v: object) -> str | None:
    """Reduz data/hora a uma forma canônica. `2026-3-15 15:00` e `2026-03-15T15:00` batem."""
    s = str(v)
    d = RX_ISO.search(s)
    h = RX_HORA.search(s)
    if not d and not h:
        return None
    partes = []
    if d:
        partes.append(f"{int(d.group(1)):04d}-{int(d.group(2)):02d}-{int(d.group(3)):02d}")
    if h:
        partes.append(f"{int(h.group(1)):02d}:{int(h.group(2)):02d}")
    return " ".join(partes)


RX_FORMA_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")
RX_FORMA_D = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RX_FORMA_H = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?$")


def forma_de(v: object) -> str:
    """Em que CONVENCAO a referencia escreveu este valor temporal."""
    t = str(v).strip()
    if RX_FORMA_DT.match(t):
        return "ISO_DATETIME"
    if RX_FORMA_D.match(t):
        return "ISO_DATE"
    if RX_FORMA_H.match(t):
        return "HORA"
    return "TEXTO_LIVRE"


def _classificar(taxa: float, nome: str, n: int, formas: Counter | None = None) -> str:
    """
    🔴 `temporal` era decidido por REGEX NO NOME — declarado, nao medido. E' justamente a
    regra que este projeto ja' pagou para aprender (a classe e' MEDIDA), e o temporal tinha
    ficado de fora dela.

    Medido em 2026-08-24: este corpus **nao tem convencao temporal**. Por par (tool,arg), so'
    12,1% das referencias do holdout e 18,9% das do treino seguem uma forma unica.
    `schedule_meeting.date` tem 32 referencias em ISO e 29 em frase crua — cara ou coroa.
    Com igualdade de string, isso reprova o modelo pela escolha do corpus, e nenhum treino
    conserta: o dado de treino tem o mesmo defeito, entao **nao ha' convencao a aprender**.

    Par temporal de convencao MISTA vira `temporal_ambiguo` e sai do escore, do mesmo jeito
    que `formulado`. ⚠️ Isso ENCOLHE o escopo da regua — e' o preco de nao inventar um
    criterio. Declarar "estas duas datas sao a mesma" seria escolher o limiar que da' o
    numero desejado.
    """
    if n < MIN_AMOSTRAS:
        return "raro"
    if taxa >= CORTE_EXTRAIDO:
        return "extraido"
    if RX_TEMPORAL.search(nome):
        if formas and sum(formas.values()) >= MIN_AMOSTRAS:
            dom = formas.most_common(1)[0][1] / sum(formas.values())
            if dom < CORTE_CONVENCAO:
                return "temporal_ambiguo"
        return "temporal"
    return "formulado"


def perfilar(caminho: Path) -> dict:
    """Deriva, do corpus, a taxa de extração de cada (ferramenta, argumento)."""
    cont: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    formas: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for ln in caminho.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ms = json.loads(ln).get("messages") or []
        i = next((k for k, m in enumerate(ms)
                  if m.get("role") == "assistant"
                  and (m.get("content") or "").strip().startswith("{")), None)
        if i is None or i == 0:
            continue
        try:
            o = json.loads(ms[i]["content"])
        except Exception:
            continue
        if not isinstance(o, dict) or "tool" not in o:
            continue
        ctx = nz(" ".join(m.get("content") or "" for m in ms[:i]))
        for k, v in (o.get("args") or {}).items():
            if isinstance(v, (dict, list)):
                continue
            val = nz(v)
            if len(val) < 2:
                continue
            cont[(o["tool"], k)][1] += 1
            if val in ctx:
                cont[(o["tool"], k)][0] += 1
            if RX_TEMPORAL.search(k):
                formas[(o["tool"], k)][forma_de(v)] += 1
    return {f"{t}	{k}": {"achou": a, "n": n,
                          "formas": dict(formas.get((t, k), {})),
                          "classe": _classificar(a / n if n else 0.0, k, n,
                                                 formas.get((t, k)))}
            for (t, k), (a, n) in cont.items()}


def carregar() -> dict:
    if not PERFIL.exists():
        return {}
    return json.loads(PERFIL.read_text(encoding="utf-8"))


def classe_de(perfil: dict, tool: str, arg: str) -> str:
    e = perfil.get(f"{tool}\t{arg}")
    return e["classe"] if e else "raro"


def comparar(pred: dict, ref: dict, perfil: dict) -> tuple[bool, int, int]:
    """Compara duas chamadas ARGUMENTO A ARGUMENTO.

    Devolve (bate, n_pontuados, n_excluidos). ⚠️ `n_pontuados == 0` significa que a chamada
    NAO E' PONTUAVEL — quem consome tem de recusar o caso, nunca contar como acerto.
    """
    if not isinstance(pred, dict) or pred.get("tool") != ref.get("tool"):
        return False, 0, 0
    t = ref["tool"]
    ap, ar = pred.get("args") or {}, ref.get("args") or {}
    pontuados = excluidos = 0
    bate = True
    for k, vr in ar.items():
        c = classe_de(perfil, t, k)
        if c in ("formulado", "raro", "temporal_ambiguo"):
            excluidos += 1
            continue
        if k not in ap:
            pontuados += 1
            bate = False                       # argumento pontuavel AUSENTE e' erro
            continue
        vp = ap[k]
        pontuados += 1
        if c == "temporal":
            tp, tr = temporal_norm(vp), temporal_norm(vr)
            if tp is not None and tr is not None:
                if tp != tr:
                    bate = False
                continue
        np_, nr = num(vp), num(vr)
        if np_ is not None and nr is not None:
            if abs(np_ - nr) > max(0.01, abs(nr) * 1e-6):
                bate = False
        elif nz(vp) != nz(vr):
            bate = False
    # argumento pontuavel a MAIS que a referencia nao tem: alucinacao, conta como erro
    for k in ap:
        if k not in ar and classe_de(perfil, t, k) in ("extraido", "temporal"):
            bate = False
            pontuados += 1
    return bate, pontuados, excluidos


# ─────────────────────────────────────────────────────────────────────────────
def validar(caminho: Path) -> int:
    """Split-half: a classificacao tem de ser a MESMA nas duas metades do corpus.

    🔴 Sem isto, "derivei do corpus" nao vale nada: um limiar aplicado a contagem ruidosa
    produz classes que mudam se o corpus mudar, e a regua passa a depender da amostra.
    """
    linhas = [l for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    metades = []
    for lado in (linhas[::2], linhas[1::2]):
        tmp = caminho.with_suffix(f".half{len(metades)}.tmp")
        tmp.write_text("\n".join(lado), encoding="utf-8")
        metades.append(perfilar(tmp))
        tmp.unlink()
    a, b = metades
    comuns = [k for k in a if k in b and a[k]["n"] >= MIN_AMOSTRAS and b[k]["n"] >= MIN_AMOSTRAS]
    igual = sum(1 for k in comuns if a[k]["classe"] == b[k]["classe"])
    print(f"split-half: {len(comuns)} pares (ferramenta,arg) com n>= {MIN_AMOSTRAS} nos dois lados")
    print(f"  classe IGUAL nas duas metades: {igual}/{len(comuns)} = {igual/max(1,len(comuns)):.1%}")
    disc = [(k, a[k]["classe"], b[k]["classe"], a[k]["n"], b[k]["n"])
            for k in comuns if a[k]["classe"] != b[k]["classe"]]
    for k, ca, cb, na, nb in disc[:8]:
        print(f"    discorda: {k.replace(chr(9), '.'):40} {ca}({na}) x {cb}({nb})")
    if igual / max(1, len(comuns)) < 0.95:
        print("\n🔴 classificacao INSTAVEL entre metades — o limiar esta' pegando ruido",
              file=sys.stderr)
        return 1
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--perfilar", action="store_true")
    ap.add_argument("--dados", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data" / "processed"
                    / "gigaverbo_ferramenta.jsonl")
    a = ap.parse_args()
    if not a.perfilar:
        return 0

    print("=" * 78)
    print("VALIDACAO — a classificacao e' estavel entre metades do corpus?")
    print("=" * 78)
    rc = validar(a.dados)

    perfil = perfilar(a.dados)
    PERFIL.write_text(json.dumps(perfil, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter(v["classe"] for v in perfil.values())
    inst = Counter()
    for v in perfil.values():
        inst[v["classe"]] += v["n"]
    print()
    print(f"{'classe':12}{'pares (tool,arg)':>18}{'instancias':>13}")
    for k in ("extraido", "temporal", "temporal_ambiguo", "formulado", "raro"):
        print(f"{k:12}{c[k]:18}{inst[k]:13}")
    amb = c["temporal_ambiguo"]
    if amb:
        print()
        print(f"⚠️  {amb} pares temporais de convencao MISTA sairam do escore "
              f"({inst['temporal_ambiguo']} instancias).")
        print("   O corpus nao tem convencao ali: nao ha' criterio nem para o modelo "
              "aprender, nem para a regua cobrar. Ver _classificar().")
    pont = inst["extraido"] + inst["temporal"]
    print(f"{'PONTUAVEL':12}{c['extraido']+c['temporal']:18}{pont:13}  "
          f"= {pont/max(1,sum(inst.values())):.1%} das instancias")
    print()
    print(f"[OK] perfil em {PERFIL.name}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
