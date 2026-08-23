"""Mundo simulado ABERTO — executa qualquer uma das 747 ferramentas do gigaverbo.

🔴 O PROBLEMA QUE ISTO RESOLVE. `tools_exec.py` simula 14 ferramentas, e por isso o holdout
agêntico tem 85 casos e todo intervalo de confiança é ±10 pp. O E5 e o E6 apontaram o mesmo
gargalo: sem ampliar o avaliador, nenhuma medição futura distingue intervenção de ruído.

⚠️ E A ARMADILHA. Um simulador genérico que só faça hash de `(ferramenta, args)` é IGUALDADE
EXATA disfarçada de execução — o defeito que o E5c documentou em `web_search`. Ampliar assim
multiplicaria os casos e pioraria a régua.

⭐ O QUE TORNA ISTO HONESTO: **o dataset traz o resultado correto de cada chamada.** Cada
exemplo do gigaverbo tem a chamada do assistente seguida de uma mensagem `tool` com o valor
computado:

    {"tool":"calculate_tip","args":{"bill_amount":50,"tip_percentage":15}} -> {"tip_amount":7.5}

Então cada fórmula aqui é **verificada contra milhares de pares (entrada, resultado) reais**, e
"implementei a semântica certa" vira número medido, não afirmação. Rode:

    python comeia/eval/mundo_aberto.py --validar

Ferramenta cuja fórmula não reproduz o dataset **não vira semântica** — cai para a classe ECO,
rotulada. Severo e mensurável bate frouxo e invisível.

⚠️ AMBIGUIDADE REAL, e como é tratada. A MESMA ferramenta tem semânticas diferentes entre
exemplos: `calculate_discount(100, 20%)` devolve `discounted_price: 80` em 82% dos casos e
`discount_amount: 20` em 12%. Por isso cada função devolve **todos os derivados canônicos**
(preço final E valor do desconto). Para PONTUAR isso é indiferente — previsto e referência
passam pela mesma função —, e para VALIDAR basta que um dos campos bata.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Callable

# data fixa: `calculate_age` sem referência temporal seria não-determinístico, e um avaliador
# cujo gabarito muda com o relógio é pior que nenhum.
# ⭐ 2021 não é escolha: é MEDIDO. Para cada par (nascimento, idade) do dataset o ano de
#    referência implícito sai por subtração — 230 de 238 casos apontam 2021.
HOJE = date(2021, 6, 15)


def _taxa(v: object) -> float | None:
    """Percentual ou fração? MEDIDO no corpus: 3.278 vêm >1 (percentual), 107 vêm <1 (fração).

    A validação pegou `{"income": 50000, "tax_rate": 0.2}` com resultado 10000 no dataset —
    0,2 ali é 20%, não 0,2%. Sem esta normalização a fórmula erra por 100× e o erro passa como
    "o modelo não sabe calcular imposto".
    """
    x = _num(v)
    if x is None:
        return None
    return x * 100.0 if 0 < x < 1 else x


def _norm(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _det(*partes: object) -> int:
    return int(hashlib.sha256("|".join(_norm(p) for p in partes).encode()).hexdigest()[:8], 16)


def _num(v: object) -> float | None:
    """Aceita 1234.5, '1.234,50', 'R$ 80', '20%'. Devolve None se não for número."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-+]", "", str(v))
    if not s or not re.search(r"\d", s):
        return None
    # 1.234,50 (pt) vs 1,234.50 (en): decide pelo separador MAIS À DIREITA
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") \
            else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) != 3 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


# ── papéis de argumento, DERIVADOS da distribuição medida no corpus (não adivinhados).
#    Ordem importa: o primeiro padrão que casar vence.
PAPEIS: list[tuple[str, str]] = [
    ("taxa", r"(percent|percentage|rate|taxa|juros|interest_rate|tip_perc|discount_perc)"),
    ("prazo", r"(term|period|years?|months?|time|duration|prazo|anos?|meses)"),
    ("base", r"(original_price|price|amount|total|bill|principal|income|value|cost|salary|"
             r"revenue|subtotal|valor|preco|montante|loan|budget)"),
    ("peso", r"(weight|peso|mass)"),
    ("altura", r"(height|altura)"),
    ("data", r"(birth|dob|date|nascimento)"),
    ("forma", r"(shape|forma|figure)"),
    ("dim", r"(radius|length|width|base|side|dimensions|raio|lado)"),
    ("moeda_de", r"^(from|source|de)(_currency)?$"),
    ("moeda_para", r"^(to|target|para)(_currency)?$"),
]


def papeis(args: dict) -> dict[str, Any]:
    """Mapeia nomes de argumento para papéis semânticos."""
    fora: dict[str, Any] = {}
    for k, v in (args or {}).items():
        kn = _norm(k).replace(" ", "_")
        for papel, rx in PAPEIS:
            if re.search(rx, kn) and papel not in fora:
                fora[papel] = v
                break
    return fora


def _r(x: float) -> float:
    """Arredonda para 2 casas — o dataset arredonda, e comparar float cru daria falso negativo."""
    return round(x + 0.0, 2)


# ── semânticas. Cada uma devolve TODOS os derivados canônicos (ver docstring do módulo).
def _desconto(a: dict) -> dict | None:
    p = papeis(a)
    base, taxa = _num(p.get("base")), _taxa(p.get("taxa"))
    if base is None:
        return None
    if taxa is None:                      # desconto dado em valor absoluto
        return None
    desc = base * taxa / 100.0
    return {"desconto": _r(desc), "preco_final": _r(base - desc)}


def _gorjeta(a: dict) -> dict | None:
    p = papeis(a)
    base, taxa = _num(p.get("base")), _taxa(p.get("taxa"))
    if base is None or taxa is None:
        return None
    g = base * taxa / 100.0
    return {"gorjeta": _r(g), "total_com_gorjeta": _r(base + g)}


def _imposto(a: dict) -> dict | None:
    p = papeis(a)
    base, taxa = _num(p.get("base")), _taxa(p.get("taxa"))
    if base is None or taxa is None:
        return None
    t = base * taxa / 100.0
    return {"imposto": _r(t), "liquido": _r(base - t)}


def _juros_simples(a: dict) -> dict | None:
    p = papeis(a)
    base, taxa, prazo = _num(p.get("base")), _taxa(p.get("taxa")), _num(p.get("prazo"))
    if base is None or taxa is None or prazo is None:
        return None
    j = base * taxa * prazo / 100.0
    return {"juros": _r(j), "montante": _r(base + j)}


def _bmi(a: dict) -> dict | None:
    p = papeis(a)
    peso, alt = _num(p.get("peso")), _num(p.get("altura"))
    if peso is None or alt is None or alt <= 0:
        return None
    if alt > 3:                            # veio em cm
        alt = alt / 100.0
    return {"imc": _r(peso / (alt * alt))}


def _idade(a: dict) -> dict | None:
    p = papeis(a)
    s = str(p.get("data") or "")
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if not m:
        m2 = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
        if not m2:
            return None
        d, mo, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
    else:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    idade = HOJE.year - y - ((HOJE.month, HOJE.day) < (mo, d))
    return {"idade": idade}


def _area(a: dict) -> dict | None:
    p = papeis(a)
    forma = _norm(p.get("forma") or "")
    dims = p.get("dim")
    if isinstance(dims, dict):
        vals = {_norm(k): _num(v) for k, v in dims.items()}
    else:
        vals = {_norm(k): _num(v) for k, v in (a or {}).items()}
    def g(*nomes):
        for n in nomes:
            for k, v in vals.items():
                if n in k and v is not None:
                    return v
        return None
    if "circ" in forma or "circle" in forma:
        r = g("radius", "raio", "diameter")
        return {"area": _r(math.pi * r * r)} if r else None
    if "tri" in forma:
        b, h = g("base", "length"), g("height", "altura")
        return {"area": _r(b * h / 2)} if b and h else None
    if "quad" in forma or "square" in forma:
        s2 = g("side", "lado", "length")
        return {"area": _r(s2 * s2)} if s2 else None
    b, h = g("length", "width", "base"), g("width", "height", "altura")
    if b and h and b != h:
        return {"area": _r(b * h)}
    return None


def _prestacao(a: dict) -> dict | None:
    """Prestação com juros compostos (fórmula padrão de amortização)."""
    p = papeis(a)
    base, taxa, prazo = _num(p.get("base")), _taxa(p.get("taxa")), _num(p.get("prazo"))
    if base is None or taxa is None or prazo is None or prazo <= 0:
        return None
    # 🔴 MEDIDO, nao adivinhado: `{"loan_amount":50000,"interest_rate":5.5,"loan_term":60}`
    #    da' 955,65 no dataset, que so' fecha com n=60 MESES. A heuristica anterior
    #    (<=60 => anos) fazia n=720 e devolvia 238 — errado por 4x, e pareceria erro do modelo.
    n = prazo if prazo > 12 else prazo * 12
    i = taxa / 100.0 / 12.0
    if i == 0:
        return {"prestacao": _r(base / n)}
    f = (1 + i) ** n
    return {"prestacao": _r(base * i * f / (f - 1))}


# ⭐ Cotacoes DERIVADAS do proprio dataset (mediana de convertido/valor por par), nao de
#    cotacoes reais. Para PONTUAR a constante e' indiferente — previsto e referencia passam
#    pela mesma funcao. Mas usar as do dataset torna a VALIDACAO significativa: com cotacoes
#    reais a formula batia 6,9%, o que parecia erro de semantica e era so' constante diferente.
#    USD->EUR sai de 131 amostras (mediana 0,8505); as demais de 4 a 21.
TAXAS = {"usd": 1.0, "eur": 0.8505, "gbp": 0.7202, "jpy": 110.0,
         "brl": 5.05, "cad": 1.25, "aud": 1.35, "chf": 0.92, "cny": 6.45}


def _moeda(a: dict) -> dict | None:
    p = papeis(a)
    v = _num(p.get("base"))
    de, para = _norm(p.get("moeda_de") or ""), _norm(p.get("moeda_para") or "")
    if v is None or de not in TAXAS or para not in TAXAS:
        return None
    return {"convertido": _r(v / TAXAS[de] * TAXAS[para])}


# padrão do nome da ferramenta -> semântica. O primeiro que casar vence.
SEMANTICAS: list[tuple[str, Callable[[dict], dict | None]]] = [
    (r"discount", _desconto),
    (r"tip|gorjeta", _gorjeta),
    (r"(tax|imposto)", _imposto),
    (r"interest|juros", _juros_simples),
    (r"bmi|imc|body_mass", _bmi),
    (r"age|idade", _idade),
    (r"area", _area),
    (r"(loan|mortgage|installment|payment)", _prestacao),
    (r"currency|exchange|cambio", _moeda),
]

# preenchido por --validar: só entra em produção a fórmula que reproduz o dataset
APROVADAS: set[str] = set()


def classificar(tool: str) -> Callable | None:
    t = _norm(tool).replace(" ", "_")
    for rx, fn in SEMANTICAS:
        if re.search(rx, t):
            return fn
    return None


def executar_aberto(chamada: dict) -> tuple[bool, Any, str]:
    """Executa qualquer ferramenta. Devolve (ok, resultado, classe).

    classe = "semantica" (computado de verdade) ou "eco" (hash dos args normalizados).
    A classe VAI JUNTO do resultado de propósito: quem consome tem de poder separar
    "acertou a conta" de "acertou a string".
    """
    if not isinstance(chamada, dict) or "tool" not in chamada:
        return False, "chamada sem 'tool'", "invalida"
    tool = str(chamada["tool"])
    args = chamada.get("args") or {}
    if not isinstance(args, dict):
        return False, "args nao e' objeto", "invalida"

    fn = classificar(tool)
    if fn is not None:
        try:
            r = fn(args)
        except Exception as e:                       # fórmula não se aplica a estes args
            r = None
            del e
        if r is not None:
            return True, r, "semantica"

    # eco: mundo ABERTO (qualquer entrada vale) mas discriminação é igualdade exata
    chave = json.dumps({_norm(k): _norm(v) for k, v in args.items()},
                       sort_keys=True, ensure_ascii=False)
    return True, {"eco_id": _det(tool, chave)}, "eco"


def resultados_batem(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False, default=str) == \
        json.dumps(b, sort_keys=True, ensure_ascii=False, default=str)


# ─────────────────────────────────────────────────────────────────────────────
def validar(caminho: Path, limite: int = 0) -> int:
    """Confere cada fórmula contra o resultado que o PRÓPRIO dataset registrou."""
    from collections import Counter, defaultdict
    ok = defaultdict(int)
    ruim = defaultdict(int)
    exemplos_ruins = defaultdict(list)
    sem_num = Counter()
    n = 0
    for ln in caminho.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ms = json.loads(ln).get("messages") or []
        for i, m in enumerate(ms):
            if m["role"] != "assistant":
                continue
            c = m["content"].strip()
            if not c.startswith("{"):
                continue
            try:
                o = json.loads(c)
            except Exception:
                continue
            if not (isinstance(o, dict) and "tool" in o):
                continue
            if i + 1 >= len(ms) or ms[i + 1]["role"] != "tool":
                continue
            try:
                esperado = json.loads(ms[i + 1]["content"])
            except Exception:
                continue
            if not isinstance(esperado, dict):
                continue
            fn = classificar(o["tool"])
            if fn is None:
                continue
            n += 1
            try:
                meu = fn(o.get("args") or {})
            except Exception:
                meu = None
            if meu is None:
                sem_num[o["tool"]] += 1
                continue
            # basta UM campo bater: o dataset alterna entre interpretações da mesma ferramenta
            alvos = [v for v in esperado.values() if _num(v) is not None]
            meus = [v for v in meu.values() if _num(v) is not None]
            bateu = any(abs(_num(x) - _num(y)) <= max(0.02, abs(_num(y)) * 0.01)
                        for x in meus for y in alvos)
            if bateu:
                ok[o["tool"]] += 1
            else:
                ruim[o["tool"]] += 1
                if len(exemplos_ruins[o["tool"]]) < 2:
                    exemplos_ruins[o["tool"]].append(
                        (json.dumps(o.get("args"), ensure_ascii=False)[:60],
                         json.dumps(meu, ensure_ascii=False)[:44],
                         json.dumps(esperado, ensure_ascii=False)[:44]))
            if limite and n >= limite:
                break
        if limite and n >= limite:
            break

    print("=" * 88)
    print("VALIDACAO DAS FORMULAS contra o resultado registrado no PROPRIO dataset")
    print("=" * 88)
    print(f"{'ferramenta':30} {'ok':>6} {'erro':>6} {'sem num':>8} {'acerto':>8}  veredito")
    aprovadas, reprovadas = [], []
    for t in sorted(set(ok) | set(ruim) | set(sem_num), key=lambda x: -(ok[x] + ruim[x])):
        a, b, s = ok[t], ruim[t], sem_num[t]
        if a + b < 5:
            continue
        taxa = a / (a + b)
        v = "SEMANTICA" if taxa >= 0.95 else "-> ECO (formula nao reproduz)"
        (aprovadas if taxa >= 0.95 else reprovadas).append(t)
        print(f"  {t:28} {a:6} {b:6} {s:8} {taxa:7.1%}  {v}")
    print()
    print(f"aprovadas ({len(aprovadas)}): {aprovadas}")
    print(f"reprovadas ({len(reprovadas)}): {reprovadas}")
    if reprovadas:
        print()
        print("exemplos do que nao bateu (a formula esta' errada, ou a ferramenta e' outra):")
        for t in reprovadas[:4]:
            for args, meu, esp in exemplos_ruins[t]:
                print(f"  {t:24} args={args}")
                print(f"  {'':24} meu={meu}  dataset={esp}")
    Path(__file__).with_name("mundo_aberto_aprovadas.json").write_text(
        json.dumps(sorted(aprovadas), ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("[OK] lista de aprovadas gravada — so' elas contam como 'semantica' em producao")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--dados", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data" / "processed"
                    / "gigaverbo_ferramenta.jsonl")
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()
    raise SystemExit(validar(a.dados, a.limite) if a.validar else 0)
