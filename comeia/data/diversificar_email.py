"""Troca cada e-mail do treino por um INÉDITO — para o modelo copiar em vez de decorar.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-26, no treino do e12:

    724 ocorrencias de e-mail · 22 DISTINTOS
    boss@company.com 343x (47%) · johndoe@example.com 141x (19%) · john.doe@... 89x (12%)
    os 3 mais comuns cobrem 79% · 16 usuarios · 6 dominios

**O modelo nunca aprendeu a copiar e-mail. Ele decorou `boss@company.com`.** E o dado nao
esta' errado — 711 das 718 referencias sao copia literal, identica ate' na caixa. O problema
nao e' volume (724 exemplos e' bastante) nem fidelidade: e' DIVERSIDADE. Vinte e duas cadeias
distintas ensinam a reproduzir vinte e duas cadeias, nao a transcrever uma arbitraria.

Isso explica cada observacao, inclusive as que me confundiram:

    boss@company.com -> Boss@Company              recuperacao da memoria, nao copia
    Zorak.Vintel@... -> Zorak@Quandrix-7739.com   inedito: nada a recuperar, monta pelo molde
    span maximal PIOROU (-15,8 pp)                nao e' preguica — falta a HABILIDADE
    Zorak-Vintel-Quandrix-7739 (14 tok) 71,3%     nao e' e-mail, nao aciona o molde

⭐ Terceira vez na mesma investigacao que a resposta e' diversidade do dado: o catalogo
(o modelo contava em vez de selecionar) e a variedade de ferramentas (+75 pp) foram as outras.

## O desenho

Cada exemplo que contem e-mail recebe um endereco SORTEADO de um espaco grande, aplicado ao
pedido E a referencia. Mesmas ferramentas, mesmos pedidos, so' o endereco muda — entao nao ha'
o que decorar, so' o que copiar.

⚠️ **Sorteio POR EXEMPLO, nao por corpus.** Trocar `boss@company.com` por um unico endereco
novo em todos os 343 casos so' mudaria qual string e' decorada.

⚠️ **O espaco de teste fica reservado.** Os enderecos usados na sonda e no holdout NUNCA
entram no treino — verificado, nao suposto.

Uso:
    python comeia/data/diversificar_email.py --conferir
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
NL = chr(10)
RX_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")

USUARIOS = ["ana", "bruno", "carla", "diego", "elisa", "fabio", "gisele", "heitor", "iara",
            "joao", "karina", "lucas", "marina", "nuno", "olivia", "pedro", "quesia",
            "rafael", "sofia", "tiago", "ursula", "vitor", "wagner", "ximena", "yuri",
            "zilda", "amanda", "beatriz", "caio", "daniela", "eduardo", "flavia"]
SOBRE = ["silva", "souza", "costa", "pereira", "almeida", "rocha", "martins", "barbosa",
         "ferreira", "gomes", "araujo", "ribeiro", "carvalho", "teixeira", "moreira"]
DOMINIOS = ["contoso", "acmelabs", "nortec", "vertexa", "quantis", "meridian", "solvora",
            "bluepine", "cedrix", "hexanet", "orbita", "prisma", "tornel", "urbano",
            "valente", "zenit", "kaledo", "lumino", "marfim", "nevoa"]
TLDS = [".com", ".com.br", ".net", ".org", ".io", ".co"]
SEPS = ["", ".", "_", "-"]


def gerar(rnd: random.Random) -> str:
    u = rnd.choice(USUARIOS)
    if rnd.random() < 0.6:
        u += rnd.choice(SEPS) + rnd.choice(SOBRE)
    if rnd.random() < 0.25:
        u += str(rnd.randint(2, 99))
    return f"{u}@{rnd.choice(DOMINIOS)}{rnd.choice(TLDS)}"


def processar(entrada: Path, saida: Path, reservados: set[str], seed: int) -> Counter:
    rnd = random.Random(seed)
    st: Counter = Counter()
    novos: Counter = Counter()
    linhas = []
    for ln in entrada.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        blob = json.dumps(r, ensure_ascii=False)
        achados = sorted(set(RX_EMAIL.findall(blob)))
        if not achados:
            linhas.append(r)
            continue
        st["exemplos com e-mail"] += 1
        # 🔴 um endereco novo POR ENDERECO ORIGINAL, POR EXEMPLO: se `boss@company.com`
        #    virasse um unico endereco novo no corpus todo, so' mudaria o que se decora.
        mapa = {}
        for velho in achados:
            for _ in range(50):
                cand = gerar(rnd)
                if cand not in reservados and cand not in mapa.values():
                    break
            mapa[velho] = cand
            novos[cand] += 1
            st["enderecos trocados"] += 1
        for velho, novo in sorted(mapa.items(), key=lambda x: -len(x[0])):
            blob = blob.replace(velho, novo)
        linhas.append(json.loads(blob))
    saida.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in linhas),
                     encoding="utf-8")
    st["_distintos"] = len(novos)
    st["_maior"] = novos.most_common(1)[0][1] if novos else 0
    return st


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

    # 🔴 RESERVA: todo endereco que aparece em qualquer conjunto de TESTE fica proibido
    #    no treino. Verificado sobre os arquivos, nao suposto.
    reservados: set[str] = set()
    testes = list(PROC.glob("holdout_*.eval.jsonl")) + list(PROC.glob("sonda_*.eval.jsonl"))
    for p in testes:
        reservados |= set(RX_EMAIL.findall(p.read_text(encoding="utf-8")))
    print(f"reservados (aparecem em teste): {len(reservados)} enderecos, de {len(testes)} arquivos")

    ent = PROC / "treino_balanceado.jsonl"
    sai = PROC / "treino_email_diverso.jsonl"
    st = processar(ent, sai, reservados, a.seed)
    print(f"{sai.name}: {st['exemplos com e-mail']} exemplos tocados · "
          f"{st['enderecos trocados']} enderecos trocados")
    print(f"  DISTINTOS gerados: {st['_distintos']} (antes: 22) · "
          f"o mais frequente aparece {st['_maior']}x (antes: 343)")

    if a.conferir:
        gerados = set(RX_EMAIL.findall(sai.read_text(encoding="utf-8")))
        vaz = gerados & reservados
        print()
        print(f"  e-mails distintos no treino novo: {len(gerados)}")
        if vaz:
            print(f"  🔴 VAZAMENTO: {len(vaz)} enderecos de teste aparecem no treino: "
                  f"{sorted(vaz)[:5]}")
            return 1
        print("  ✅ nenhum endereco de teste aparece no treino")
        # o resto do exemplo continua identico?
        import difflib
        a1 = ent.read_text(encoding="utf-8").splitlines()
        b1 = sai.read_text(encoding="utf-8").splitlines()
        if len(a1) != len(b1):
            print(f"  🔴 numero de linhas mudou: {len(a1)} -> {len(b1)}")
            return 1
        difs = sum(1 for x, y in zip(a1, b1) if x != y)
        print(f"  linhas alteradas: {difs} (esperado = exemplos com e-mail: "
              f"{st['exemplos com e-mail']})")
        if difs != st["exemplos com e-mail"]:
            print("  🔴 divergencia — alguma linha mudou sem ter e-mail, ou vice-versa")
            return 1
        print("  ✅ so' os exemplos com e-mail foram tocados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
