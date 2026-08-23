"""Constrói um holdout agêntico GRANDE, pontuado por EXECUÇÃO de verdade.

🔴 O gargalo que isto ataca: o holdout atual tem 85 casos com ferramenta, dos quais só 61 são
pontuados por execução (os outros 24 são igualdade de string — E5c). Com n=85 o intervalo de
Wilson é ±10 pp e o E6 mostrou que o ruído de semente sozinho vale 4,7 pp. Nenhuma medição
futura distingue intervenção de ruído nesse tamanho.

⭐ REGRA DE ADMISSÃO: só entra caso cuja ferramenta tem **semântica validada** contra o
resultado que o próprio dataset registrou (`mundo_aberto.py --validar`, corte de 95%).
Ferramenta cuja fórmula não reproduz o dataset fica de fora — ampliar o holdout com casos
pontuados por eco multiplicaria o número e pioraria a régua.

⚠️ CONTAMINAÇÃO: os adapters do E2/E6 treinaram em `sft_grupo_ferramenta.jsonl`, não no
gigaverbo — então em princípio tudo aqui é inédito para eles. "Em princípio" não basta: o
script confere sobreposição por hash do par (pedido, chamada) e aborta se passar de 1%.

Uso:
    python comeia/data/construir_holdout_aberto.py --n-holdout 600
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
import mundo_aberto as MA  # noqa: E402

PROC = RAIZ / "data" / "processed"


def chamadas_do_exemplo(ms: list[dict]) -> list[tuple[int, dict]]:
    fora = []
    for i, m in enumerate(ms):
        if m.get("role") != "assistant":
            continue
        c = (m.get("content") or "").strip()
        if not c.startswith("{"):
            continue
        try:
            o = json.loads(c)
        except Exception:
            continue
        if isinstance(o, dict) and "tool" in o:
            fora.append((i, o))
    return fora


def h(*partes: str) -> str:
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "gigaverbo_ferramenta.jsonl")
    ap.add_argument("--negativos", type=Path, default=PROC / "negativos_com_recusa.jsonl")
    ap.add_argument("--treino-existente", type=Path,
                    default=PROC / "sft_grupo_ferramenta.jsonl")
    ap.add_argument("--n-holdout", type=int, default=600)
    ap.add_argument("--n-texto", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20260823)
    a = ap.parse_args()

    aprovadas = set(json.loads(
        (RAIZ / "eval" / "mundo_aberto_aprovadas.json").read_text(encoding="utf-8")))
    print(f"ferramentas com semantica VALIDADA: {len(aprovadas)}")

    # hashes do que ja' foi treinado — para conferir contaminacao, nao para supor que nao ha'
    vistos_treino = set()
    if a.treino_existente.exists():
        for ln in a.treino_existente.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            ms = list(r.get("prompt") or []) + list(r.get("completion") or [])
            u = next((m["content"] for m in ms if m["role"] == "user"), "")
            for _, o in chamadas_do_exemplo(ms):
                vistos_treino.add(h(MA._norm(u), json.dumps(o, sort_keys=True)))

    candidatos, stats = [], Counter()
    for ln in a.fonte.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        ms = r.get("messages") or []
        ch = chamadas_do_exemplo(ms)
        if len(ch) != 1:
            stats["multi_ou_zero_chamada"] += 1
            continue
        idx, obj = ch[0]
        if obj["tool"] not in aprovadas:
            stats["ferramenta_sem_semantica"] += 1
            continue
        ok, _, classe = MA.executar_aberto(obj)
        if not ok or classe != "semantica":
            # 🔴 a guarda do E5: gabarito que nao executa e' caso IMPOSSIVEL, e conta-lo como
            #    erro do modelo foi o que produziu "23,5%" numa versao anterior do avaliador
            stats["gabarito_nao_executa"] += 1
            continue
        # 🔴 O PREFIXO INTEIRO, nao so' a primeira fala do usuario. 37,5% dos dialogos do
        #    gigaverbo sao multi-turno: o assistente pergunta os valores e o usuario responde
        #    no turno seguinte. Pegar so' a primeira mensagem descartava justamente os numeros,
        #    e o caso virava impossivel — 17,3% do holdout na primeira versao.
        prefixo = [m for m in ms[:idx] if m.get("role") in ("system", "user", "assistant")]
        usuario = " ".join(m["content"] for m in prefixo if m["role"] == "user")
        if not usuario.strip() or idx == 0:
            stats["sem_pedido"] += 1
            continue

        # 🔴 GUARDA DE RESPONDIBILIDADE — nova, e a guarda antiga NAO a cobre.
        #    "o gabarito executa" passa mesmo quando a resposta nao esta' no prompt: a chamada
        #    de referencia e' valida, so' nao e' DERIVAVEL. Caso assim conta como erro do
        #    modelo e desloca a taxa para baixo — e' o §2c #4 numa forma que a guarda de
        #    execucao nao enxerga. Todo numero da referencia tem de aparecer no pedido.
        contexto = " ".join(m["content"] for m in prefixo)
        faltando = []
        for v in (obj.get("args") or {}).values():
            x = MA._num(v) if not isinstance(v, (dict, list)) else None
            if x is None:
                continue
            alvo = str(int(x)) if float(x) == int(x) else str(x)
            if alvo not in re.sub(r"[.,](?=\d{3})", "", contexto):
                faltando.append(alvo)
        if faltando:
            stats["nao_derivavel_do_pedido"] += 1
            continue
        if h(MA._norm(usuario), json.dumps(obj, sort_keys=True)) in vistos_treino:
            stats["ja_no_treino"] += 1
            continue
        candidatos.append({
            "prompt": prefixo,
            "completion": [{"role": "assistant",
                            "content": json.dumps(obj, ensure_ascii=False)}],
            "kind": "tool_call", "ferramenta": obj["tool"], "origem": "gigaverbo",
        })

    print(f"candidatos com ferramenta validada: {len(candidatos)}")
    for k, v in stats.most_common():
        print(f"  descartado · {k:26} {v}")
    if stats["ja_no_treino"]:
        frac = stats["ja_no_treino"] / max(1, stats["ja_no_treino"] + len(candidatos))
        print(f"⚠️ sobreposicao com o treino: {frac:.2%}")
        if frac > 0.01:
            print("🔴 ABORTANDO: mais de 1% ja' esta' no treino — o holdout mediria memorizacao",
                  file=sys.stderr)
            return 1

    # texto (para over-calling): pedidos que NAO devem virar chamada
    textos = []
    if a.negativos.exists():
        for ln in a.negativos.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            ms = r.get("messages") or (list(r.get("prompt") or [])
                                       + list(r.get("completion") or []))
            u = next((m["content"] for m in ms if m["role"] == "user"), None)
            s2 = next((m["content"] for m in ms if m["role"] == "system"), None)
            asst = [m["content"] for m in ms if m["role"] == "assistant"]
            if not (u and asst):
                continue
            textos.append({
                "prompt": ([{"role": "system", "content": s2}] if s2 else [])
                          + [{"role": "user", "content": u}],
                "completion": [{"role": "assistant", "content": asst[-1]}],
                "kind": "text", "origem": "negativos",
            })

    rnd = random.Random(a.seed)
    rnd.shuffle(candidatos)
    rnd.shuffle(textos)
    hold = candidatos[: a.n_holdout] + textos[: a.n_texto]
    resto = candidatos[a.n_holdout:]
    rnd.shuffle(hold)

    fh = PROC / "holdout_aberto.eval.jsonl"
    ft = PROC / "gigaverbo_semantico_treino.jsonl"
    fh.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in hold),
                  encoding="utf-8")
    ft.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in resto),
                  encoding="utf-8")

    print()
    print(f"HOLDOUT  {len(hold)} = {sum(1 for r in hold if r['kind']=='tool_call')} tool "
          f"+ {sum(1 for r in hold if r['kind']=='text')} text   -> {fh.name}")
    print(f"  (o atual tem 85 tool + 65 text, dos quais so' 61 sao pontuados por execucao)")
    print(f"TREINO   {len(resto)} sobrando para rejection sampling  -> {ft.name}")
    print()
    print("composicao do holdout por ferramenta:")
    for t, n in Counter(r.get("ferramenta") for r in hold if r["kind"] == "tool_call") \
            .most_common(12):
        print(f"  {t:30} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
