"""Monta o conjunto de análise de sentimento em PT a partir do B2W-Reviews01.

⭐ POR QUE B2W-REVIEWS01, E NÃO UM CONJUNTO NOSSO

Sentimento é a capacidade em que texto sintético mais engana. Um gerador nosso escreveria
"produto excelente, recomendo" e "péssimo, não comprem" — separáveis por três palavras, e o
número mediria o gerador, não o modelo. O B2W é review real de e-commerce brasileiro (130 mil
avaliações da Americanas, 2018, Real/Oshiro/Mafra STIL-2019), com ironia, erro de digitação,
elogio ao produto e reclamação da entrega na mesma frase.

⚠️ AS TRÊS ESCOLHAS QUE MUDAM O NÚMERO, DECLARADAS ANTES DE MEDIR:

1. **Binário, não ternário.** Nota ≤2 é negativo, ≥4 é positivo, **3 é descartado**. A classe
   neutra de review por estrela é notoriamente ruidosa (um 3 estrelas pode ser texto elogioso
   com uma ressalva) e é o que faz acurácias ternárias publicadas caírem 15 pp sem que o
   modelo tenha piorado. É também o recorte usado nos números publicados em PT, então o
   resultado fica comparável.

2. **Balanceado 50/50.** Sem isso a acurácia da classe majoritária vira o piso — no B2W bruto
   ~70% é positivo, e "responder sempre positivo" pontuaria 70%. Balanceando, o piso trivial
   cai para 50% e sobra espaço para medir capacidade.

3. **Texto entre 40 e 600 caracteres.** Abaixo disso não há sinal ("bom", "ruim"); acima, o
   item vira teste de contexto longo em vez de sentimento.

🔴 CONTAMINAÇÃO, DITA COM TODAS AS LETRAS: o B2W é público e está na web desde 2019. O corpus
   de pré-treino do Bee vem do fineweb-2-por, que raspa a web. **Não há como garantir que
   estes reviews não estejam no pré-treino** — checar 21,75B tokens contra 600 textos é caro,
   e a resposta provavelmente seria "alguns estão". O que este arquivo faz é a checagem
   barata (contra o SFT, onde a contaminação seria fatal) e **declara o risco do pré-treino**
   em vez de fingir que ele não existe. Um número inflado que ninguém avisou que pode estar
   inflado é pior que um número menor e honesto.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BRUTO = Path(__file__).resolve().parent / "benchmarks" / "b2w_bruto.csv"
SAIDA = Path(__file__).resolve().parent / "benchmarks" / "sentimento_pt.jsonl"
SFT = RAIZ / "comeia" / "data" / "processed" / "sft_misto.jsonl"
FONTE = ("https://github.com/americanas-tech/b2w-reviews01 · "
         "commit 4639429ec698d7821fc99a0bc665fa213d9fcd5a")

POR_CLASSE = 300
MIN_CAR, MAX_CAR = 40, 600
SEMENTE = 20260819


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not BRUTO.exists():
        print(f"🔴 {BRUTO.name} nao existe. Baixe com:", file=sys.stderr)
        print(f'   curl -sSL -A "curl/8.5.0" -o {BRUTO} '
              f'https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/'
              f'4639429ec698d7821fc99a0bc665fa213d9fcd5a/B2W-Reviews01.csv', file=sys.stderr)
        return 1

    print("=" * 78)
    print("SENTIMENTO PT — amostragem do B2W-Reviews01")
    print("=" * 78)

    csv.field_size_limit(10_000_000)
    pos, neg, descartados = [], [], Counter()
    with BRUTO.open(encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            texto = (linha.get("review_text") or "").strip()
            nota = (linha.get("overall_rating") or "").strip()
            if not texto or not nota.isdigit():
                descartados["sem texto ou sem nota"] += 1
                continue
            n = int(nota)
            if n == 3:
                descartados["nota 3 (classe neutra, ruidosa)"] += 1
                continue
            if not (MIN_CAR <= len(texto) <= MAX_CAR):
                descartados[f"fora de {MIN_CAR}-{MAX_CAR} caracteres"] += 1
                continue
            (pos if n >= 4 else neg).append({
                "texto": texto, "nota": n, "rotulo": "positivo" if n >= 4 else "negativo",
                "titulo": (linha.get("review_title") or "").strip(),
            })

    # ⚠️ O B2W TEM REVIEW REPETIDO — texto identico postado em produtos diferentes. A guarda
    #    de duplicata disparou na primeira execucao (b2w-0264 == b2w-0572) e estava certa:
    #    duplicata infla o n sem acrescentar informacao, e se cair uma de cada lado do
    #    balanceamento o mesmo texto ganha dois rotulos opostos. Dedupe ANTES de sortear.
    def dedup(ls: list[dict]) -> list[dict]:
        visto, fora = set(), []
        for x in ls:
            h = hashlib.sha256(x["texto"].encode()).hexdigest()
            if h not in visto:
                visto.add(h)
                fora.append(x)
        return fora

    n_pos, n_neg = len(pos), len(neg)
    pos, neg = dedup(pos), dedup(neg)
    print(f"  elegiveis: {len(pos)} positivos · {len(neg)} negativos "
          f"(removidas {n_pos - len(pos)} + {n_neg - len(neg)} duplicatas de texto)")
    for motivo, c in descartados.most_common():
        print(f"    descartado por {motivo}: {c}")

    if min(len(pos), len(neg)) < POR_CLASSE:
        print(f"🔴 ABORTA: menos de {POR_CLASSE} exemplos em alguma classe.", file=sys.stderr)
        return 1

    rng = random.Random(SEMENTE)
    amostra = rng.sample(pos, POR_CLASSE) + rng.sample(neg, POR_CLASSE)
    rng.shuffle(amostra)
    itens = [{"id": f"b2w-{i:04d}", **a, "origem": FONTE} for i, a in enumerate(amostra)]

    # ---- guarda 1: balanceamento exato (o piso trivial precisa ser 50%)
    c = Counter(it["rotulo"] for it in itens)
    print(f"\n  ✅ guarda 1/3: balanceamento {dict(c)} — piso da classe majoritaria = "
          f"{100 * max(c.values()) / len(itens):.1f}%")
    if len(set(c.values())) != 1:
        print("🔴 ABORTA: classes desbalanceadas.", file=sys.stderr)
        return 1

    # ---- guarda 2: nenhum texto duplicado (duplicata infla n sem informacao)
    vistos = {}
    for it in itens:
        h = hashlib.sha256(it["texto"].encode()).hexdigest()
        if h in vistos:
            print(f"🔴 ABORTA: texto duplicado entre {vistos[h]} e {it['id']}.", file=sys.stderr)
            return 1
        vistos[h] = it["id"]
    print(f"  ✅ guarda 2/3: {len(vistos)} textos distintos, zero duplicata")

    # ---- guarda 3: contaminacao contra o SFT (a que seria fatal e da' para checar)
    if SFT.exists():
        corpo = SFT.read_text(encoding="utf-8", errors="ignore")
        batidas = [it["id"] for it in itens if it["texto"][:80] in corpo]
        if batidas:
            print(f"🔴 ABORTA: {len(batidas)} item(ns) aparecem no sft_misto.jsonl: "
                  f"{batidas[:5]}", file=sys.stderr)
            return 1
        print(f"  ✅ guarda 3/3: nenhum dos {len(itens)} textos aparece em {SFT.name}")
    else:
        print(f"  ⚠️ guarda 3/3 PULADA: {SFT.name} nao encontrado")

    with SAIDA.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    h = hashlib.sha256(SAIDA.read_bytes()).hexdigest()[:32]
    print(f"\n  ✅ {len(itens)} itens em {SAIDA.name} · sha256[:32] = {h}")
    print("  ⚠️ contaminacao de PRE-TREINO nao foi checada e nao da' para descartar:")
    print("     o B2W esta publico desde 2019 e o fineweb-2-por raspa a web.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
