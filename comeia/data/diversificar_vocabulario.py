"""Cobre o VOCABULÁRIO real de argumentos de conjunto fechado (cozinha, moeda, unidade…).

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-26, no e13:

    PALAVRA — acerto de copia por familia
      A. vocabulario (cuisine/genre/unit)   visto 90%  ·  INEDITO 72%   +18 pp
      B. arbitraria (username/password)     visto 100% ·  inedito 100%   +0 pp  (n=9/14)

**A memorizacao esta' no vocabulario FECHADO, nao nas cadeias arbitrarias** — o inverso do que
eu previ ao generalizar do caso do e-mail. O modelo ve' `italian` 209 vezes e `mexican` 2, e
falha numa cozinha que nunca viu.

⚠️ A familia B tem n=9 e n=14: "100%" ali nao decide nada (Wilson +-30 pp) e NAO foi tratado.

## Por que isto e' mais arriscado que o e-mail

Trocar `boss@company.com` por `ana@contoso.com` mantem o pedido plausivel. Trocar `Italian` num
pedido que diz *"comida italiana"* exige FLEXIONAR, nao substituir string. Medido:

    token inteiro (fahrenheit, jazz — igual em PT e EN)   288 = 48,2%
    DENTRO de palavra flexionada (italian em italiana)    309 = 51,8%

Dois tratamentos:
  - **token inteiro**: troca direta por outro item do mesmo vocabulario real;
  - **flexionado**: so' com PAR EXPLICITO (EN, PT) — e a troca e' VERIFICADA
    mecanicamente: o novo valor tem de entrar e o velho tem de sair, no pedido E na
    referencia. Sem par, o exemplo e' recusado.

⭐ E o vocabulario e' REAL, nunca inventado: diversificar `cuisine` com palavras aleatorias
ensinaria que cozinha e' string arbitraria e pioraria a selecao de ferramenta. O objetivo aqui
e' COBRIR o conjunto que existe no mundo, nao criar um novo.

⚠️ Ganho esperado menor que o do e-mail: a partida e' 72%, nao 35,6%.

Uso:
    python comeia/data/diversificar_vocabulario.py --conferir
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
import argumentos as ARG      # noqa: E402

PROC = RAIZ / "data" / "processed"
NL = chr(10)

# (valor de referencia, forma como aparece no pedido em PT). Iguais quando nao flexiona.
VOCAB: dict[str, list[tuple[str, str]]] = {
    "cuisine": [("Italian", "italiana"), ("Japanese", "japonesa"), ("Mexican", "mexicana"),
                ("Chinese", "chinesa"), ("French", "francesa"), ("Indian", "indiana"),
                ("Thai", "tailandesa"), ("Greek", "grega"), ("Spanish", "espanhola"),
                ("Lebanese", "libanesa"), ("Korean", "coreana"), ("Portuguese", "portuguesa"),
                ("Peruvian", "peruana"), ("Vietnamese", "vietnamita")],
    "genre": [("jazz", "jazz"), ("rock", "rock"), ("pop", "pop"), ("blues", "blues"),
              ("samba", "samba"), ("reggae", "reggae"), ("funk", "funk"),
              ("classical", "classica"), ("bossa nova", "bossa nova"),
              ("sertanejo", "sertanejo"), ("forro", "forro"), ("metal", "metal")],
    "moeda": [("EUR", "euros"), ("USD", "dolares"), ("GBP", "libras"), ("JPY", "ienes"),
              ("BRL", "reais"), ("CHF", "francos"), ("CAD", "dolares canadenses"),
              ("AUD", "dolares australianos"), ("MXN", "pesos mexicanos")],
    "unidade": [("Celsius", "celsius"), ("Fahrenheit", "fahrenheit"), ("Kelvin", "kelvin")],
}
CHAVE_PARA_VOCAB = {
    "cuisine": "cuisine", "genre": "genre", "music_genre": "genre",
    "to_currency": "moeda", "from_currency": "moeda", "currency": "moeda",
    "target_currency": "moeda", "source_currency": "moeda",
    "from_unit": "unidade", "to_unit": "unidade", "unit": "unidade",
    "temperature_unit": "unidade",
}


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def _forma_no_pedido(vocab: str, ref: str) -> str | None:
    for en, pt in VOCAB[vocab]:
        if nz(en) == nz(ref):
            return pt
    return None


def _trocar(txt: str, velho: str, novo: str) -> tuple[str, int]:
    """Troca `velho` por `novo` respeitando fronteira de palavra, sem tocar em acento."""
    rx = re.compile(rf"(?<![A-Za-zÀ-ÿ0-9]){re.escape(velho)}(?![A-Za-zÀ-ÿ0-9])", re.I)
    return rx.subn(novo, txt)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--conferir", action="store_true")
    a = ap.parse_args()
    perfil = ARG.carregar()
    rnd = random.Random(a.seed)

    # 🔴 RESERVA POR DESENHO, nao por "aparece no teste".
    #
    # A v1 proibia no treino todo valor que aparecesse em qualquer holdout. Isso esta' certo
    # para e-mail — cadeia arbitraria, e o teste e' justamente copiar uma inedita — e ERRADO
    # para vocabulario fechado: `celsius` e `blues` existem no mundo e o modelo tem de
    # aprende-los. Consequencia medida: com celsius e c reservados, TODA substituicao de
    # unidade caiu em `kelvin` (71x) e eu reconcentrei o que vim desconcentrar.
    #
    # Aqui reservam-se 2 itens de cada vocabulario, SORTEADOS — para o eixo "item inedito"
    # continuar mensuravel — e o resto entra no treino.
    # ⚠️ Isso significa que o holdout deixa de medir "vocabulario inedito" nos itens
    #    cobertos. E' o preco, e vai declarado: compartilhar VALOR de vocabulario fechado nao
    #    e' vazamento (ferramenta, pedido e tupla seguem disjuntos), mas tambem nao e'
    #    generalizacao.
    reservados: set[str] = set()
    for vc, itens in VOCAB.items():
        # ⚠️ reservar 2 de 3 unidades deixava TODA substituicao caindo em fahrenheit.
        #    A reserva tem de ser proporcional ao tamanho do vocabulario.
        for en, _ in rnd.sample(itens, max(1, len(itens) // 5)):
            reservados.add(nz(en))
    print(f"reservados POR DESENHO (2 por vocabulario): {sorted(reservados)}")

    ent = PROC / "treino_email_diverso.jsonl"
    sai = PROC / "treino_vocab_diverso.jsonl"
    st: Counter = Counter()
    usados: Counter = Counter()
    linhas = []
    for ln in ent.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("kind") != "tool_call":
            linhas.append(r)
            continue
        o = json.loads(r["completion"][0]["content"])
        f = o["tool"]
        args = dict(o.get("args") or {})
        alvo = None
        for k, v in args.items():
            vc = CHAVE_PARA_VOCAB.get(k.lower())
            if not vc or ARG.classe_de(perfil, f, k) != "extraido":
                continue
            pt = _forma_no_pedido(vc, str(v))
            if pt is None:
                st["valor fora do vocabulario conhecido"] += 1
                continue
            alvo = (k, str(v), pt, vc)
            break
        if alvo is None:
            linhas.append(r)
            continue
        k, ref_velho, pt_velho, vc = alvo
        # ⚠️ candidato: outro item do MESMO vocabulario, que nao esteja reservado
        cands = [(en, p) for en, p in VOCAB[vc]
                 if nz(en) != nz(ref_velho) and nz(en) not in reservados]
        if not cands:
            linhas.append(r)
            st["sem candidato livre"] += 1
            continue
        # prefere o menos usado, para COBRIR o vocabulario em vez de reconcentrar
        rnd.shuffle(cands)
        ref_novo, pt_novo = min(cands, key=lambda x: usados[nz(x[0])])

        pr = []
        n_txt = 0
        for m in r["prompt"]:
            c = m["content"]
            if m["role"] != "system":
                c2, n1 = _trocar(c, pt_velho, pt_novo)
                if pt_velho.lower() != ref_velho.lower():
                    c3, n2 = _trocar(c2, ref_velho, ref_novo)
                    c2, n1 = c3, n1 + n2
                n_txt += n1
                c = c2
            pr.append({**m, "content": c})
        if n_txt == 0:
            linhas.append(r)
            st["valor nao encontrado no pedido"] += 1
            continue
        args[k] = ref_novo
        novo_r = {**r, "prompt": pr,
                  "completion": [{"role": "assistant",
                                  "content": json.dumps({"tool": f, "args": args},
                                                        ensure_ascii=False)}]}
        # 🔴 VERIFICACAO MECANICA: o novo entrou e o velho saiu, no pedido E na referencia
        ctx_novo = nz(" ".join(m["content"] for m in pr if m["role"] != "system"))
        if nz(pt_novo) not in ctx_novo or nz(pt_velho) in ctx_novo:
            linhas.append(r)
            st["🔴 troca nao verificou — RECUSADO"] += 1
            continue
        usados[nz(ref_novo)] += 1
        st["TROCADO"] += 1
        linhas.append(novo_r)

    sai.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in linhas),
                   encoding="utf-8")
    print(f"{sai.name}: {len(linhas)} linhas")
    for k, v in st.most_common():
        print(f"  {k:38} {v}")
    print(f"  vocabulario coberto: {len(usados)} valores distintos usados")
    print(f"    {dict(usados.most_common(8))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
