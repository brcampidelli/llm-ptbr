"""Catalogo perturbado — intervencao (a) do gate #3 (arXiv 2609.04184), sobre o corpus do E19.

O QUE FAZ, por exemplo do corpus:
  1. RENOMEIA ~20% das ferramentas do catalogo daquele exemplo, de forma CONSISTENTE entre o bloco
     "- nome:" do system, o {"tool": ...} da completion, o campo `ferramenta`, e as chamadas em
     turnos assistant anteriores (1.798 prompts sao multi-turno). Renomear = trocar o verbo por um
     sinonimo (calculate->compute, get->fetch, ...) ou, sem verbo conhecido, sufixo _v2. O nome
     novo continua casando ^- (\\w+): e [A-Za-z_][A-Za-z0-9_]*.
     O sorteio e' POR EXEMPLO: a mesma ferramenta pode virar nomes diferentes em exemplos
     diferentes — e' o que forca o modelo a LER o nome no prompt em vez de lembrar.
  2. REEMBARALHA os blocos com outra semente (o corpus ja foi embaralhado uma vez; com ~1 epoca
     isso sozinho quase nao age — esta' aqui porque o artigo faz, e custa nada).

O QUE NAO FAZ, de proposito: NAO remove as ferramentas nao usadas. Nos positivos isso colapsaria o
catalogo para 1 ferramenta e REINTRODUZIRIA o atalho da §2u (tamanho do catalogo => classe), que
`balancear_catalogo.py` existe para matar. O artigo talvez nao tivesse esse atalho; o Bee mediu
que tem (100% -> 0% ao reordenar duas ferramentas). Rode `conferir()` de balancear_catalogo no
corpus de saida: a distribuicao de tamanhos tem de sair IDENTICA a de entrada.

GUARDAS (rodam sempre; abortam):
  - cabecalho e rodape do system BYTE A BYTE iguais (so os blocos mudam)
  - o conjunto de ferramentas de saida == conjunto de entrada passado pelo mapa (nenhuma perdida)
  - toda completion tool_call aponta para um nome que EXISTE no catalogo de saida
  - o corpus de saida reporta QUANTO agiu (§2r): exemplos tocados, nomes trocados, alvos renomeados
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "comeia" / "data")); sys.path.insert(0, str(ROOT / "comeia" / "eval"))
from balancear_catalogo import cabecalho, remontar, conferir, RX_TOOL   # noqa: E402
from catalogo_maior import blocos_do_sistema                               # noqa: E402

SINONIMOS = {
    "calculate": ["compute", "estimate", "evaluate"], "get": ["fetch", "retrieve", "lookup"],
    "check": ["verify", "validate", "inspect"], "find": ["locate", "search", "discover"],
    "generate": ["create", "produce", "build"], "search": ["find", "query", "lookup"],
    "create": ["make", "generate", "new"], "analyze": ["inspect", "examine", "assess"],
    "convert": ["transform", "translate", "change"], "send": ["dispatch", "deliver", "transmit"],
    "add": ["insert", "append", "register"], "play": ["start", "run", "stream"],
    "track": ["monitor", "follow", "trace"], "transfer": ["move", "send", "wire"],
    "predict": ["forecast", "estimate", "project"], "purchase": ["buy", "order", "acquire"],
    "schedule": ["book", "plan", "arrange"], "post": ["publish", "share", "submit"],
    "make": ["create", "build", "prepare"], "identify": ["detect", "recognize", "classify"],
    "book": ["reserve", "schedule", "arrange"], "update": ["modify", "change", "edit"],
    "delete": ["remove", "erase", "drop"], "list": ["enumerate", "show", "fetch"],
}
RX_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def renomear(nome: str, rnd: random.Random) -> str:
    """Sinonimo do verbo inicial; sem verbo conhecido, sufixo _v2. Sempre um identificador valido."""
    partes = nome.split("_")
    verbo = partes[0].lower()
    if verbo in SINONIMOS and len(partes) > 1:
        novo = "_".join([rnd.choice(SINONIMOS[verbo])] + partes[1:])
    else:
        # camelCase (calculateInterest) ou sem underscore: sufixo
        novo = nome + "_v2"
    assert RX_IDENT.match(novo), novo
    return novo if novo != nome else nome + "_v2"


def trocar_tool_em_json(texto: str, mapa: dict[str, str]) -> str:
    """Troca "tool": "velho" por "tool": "novo" em qualquer JSON dentro do texto (completion ou turno)."""
    def sub(m):
        velho = m.group(2)
        return f'{m.group(1)}{mapa.get(velho, velho)}{m.group(3)}'
    return re.sub(r'("tool"\s*:\s*")([A-Za-z_][A-Za-z0-9_]*)(")', sub, texto)


def perturbar_exemplo(r: dict, rnd: random.Random, frac: float) -> tuple[dict, dict]:
    s = next((m["content"] for m in r["prompt"] if m["role"] == "system"), "")
    cr = cabecalho(s)
    if cr is None:
        return r, {"sem_catalogo": 1}
    blocos = blocos_do_sistema(s)                      # {nome: bloco}
    nomes = list(blocos)
    k = max(1, round(frac * len(nomes))) if len(nomes) >= 2 else (1 if rnd.random() < frac else 0)
    escolhidos = rnd.sample(nomes, k) if k else []
    mapa = {n: renomear(n, rnd) for n in escolhidos}
    # 1) blocos: so' a linha "- nome:" muda
    novos = []
    for n in nomes:
        b = blocos[n]
        if n in mapa:
            b = re.sub(r"^- " + re.escape(n) + ":", "- " + mapa[n] + ":", b, count=1, flags=re.M)
        novos.append(b)
    # 2) reembaralha
    rnd.shuffle(novos)
    novo_s = remontar(s, novos)
    assert novo_s is not None
    # 3) prompt: system + turnos assistant com JSON
    prompt = []
    for m in r["prompt"]:
        if m["role"] == "system":
            prompt.append({**m, "content": novo_s})
        elif m["role"] == "assistant":
            prompt.append({**m, "content": trocar_tool_em_json(m["content"], mapa)})
        else:
            prompt.append(m)
    # 4) completion e campo ferramenta
    comp = [{**m, "content": trocar_tool_em_json(m["content"], mapa)} for m in r["completion"]]
    out = {**r, "prompt": prompt, "completion": comp}
    if r.get("ferramenta") in mapa:
        out["ferramenta"] = mapa[r["ferramenta"]]
    out["_perturbado"] = {"renomeados": mapa}
    return out, {"tocados": 1, "nomes_trocados": len(mapa),
                 "alvo_renomeado": int(r.get("ferramenta") in mapa)}


def guardas(entrada: list[dict], saida: list[dict]) -> None:
    for a, b in zip(entrada, saida):
        sa = next((m["content"] for m in a["prompt"] if m["role"] == "system"), "")
        sb = next((m["content"] for m in b["prompt"] if m["role"] == "system"), "")
        ca, cb = cabecalho(sa), cabecalho(sb)
        if ca is None:
            continue
        assert ca[0] == cb[0] and ca[1] == cb[1], "cabecalho/rodape mudaram — o estimulo alheio ao experimento foi tocado"
        mapa = b.get("_perturbado", {}).get("renomeados", {})
        esperado = {mapa.get(n, n) for n in blocos_do_sistema(sa)}
        obtido = set(blocos_do_sistema(sb))
        assert esperado == obtido, f"ferramentas perdidas/inventadas: {esperado ^ obtido}"
        if b.get("kind") == "tool_call":
            m = re.search(r'"tool"\s*:\s*"([A-Za-z_][A-Za-z0-9_]*)"', b["completion"][0]["content"])
            assert m and m.group(1) in obtido, f"completion aponta para ferramenta fora do catalogo: {m and m.group(1)}"
            assert b.get("ferramenta") == m.group(1), "campo ferramenta e completion divergem"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", default="comeia/data/processed/treino_e19c_neg_uteis.jsonl")
    ap.add_argument("--saida", default="comeia/data/processed/treino_e19c_catperturbado.jsonl")
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=2609)
    args = ap.parse_args()
    ent = ROOT / args.entrada; sai = ROOT / args.saida
    if sai.exists():
        raise SystemExit(f"🔴 {sai} ja existe — nao sobrescrevo (§2z)")
    linhas = [json.loads(l) for l in ent.read_text(encoding="utf-8").splitlines() if l.strip()]
    rnd = random.Random(args.seed)
    tot = Counter(); out = []
    for r in linhas:
        o, c = perturbar_exemplo(r, rnd, args.frac)
        out.append(o); tot.update(c)
    guardas(linhas, out)
    tmp = sai.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    tmp.replace(sai)
    n_tc = sum(1 for r in linhas if r.get("kind") == "tool_call")
    print(f"{ent.name} -> {sai.name}: {len(out)} exemplos")
    print(f"  ⭐ QUANTO AGIU (§2r): tocados {tot['tocados']} · nomes trocados {tot['nomes_trocados']} · "
          f"alvos (ferramenta da completion) renomeados {tot['alvo_renomeado']} de {n_tc} positivos "
          f"({100*tot['alvo_renomeado']/max(n_tc,1):.1f}%) · sem catalogo {tot['sem_catalogo']}")
    print("  guardas: cabecalho/rodape byte a byte, conjunto de ferramentas preservado, completion no catalogo — OK")
    print("\n  conferir() do balancear_catalogo (o tamanho NAO pode prever a classe):")
    return conferir(sai)


if __name__ == "__main__":
    raise SystemExit(main())
