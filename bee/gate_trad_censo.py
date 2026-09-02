"""Gate T-TRAD, estagio A — censo de repeticao CROSS-LINGUAL, antes de traduzir qualquer coisa.

⭐ POR QUE ESTE CENSO EXISTE, E POR QUE ELE VEM ANTES DA TRADUCAO
  A evidencia mais forte do estudo diz TRADUZIR em vez de coletar: o `2607.00890` (MultiSynt/MT)
  traduziu 100B tokens para 36 idiomas e atinge o escore do dado NATIVO com ~72% menos tokens; o
  `2605.13225` (~1.000 runs, 150M a 1,43B — a nossa faixa) mede que misturar vale 2-3x o dado
  unico do alvo. E o `common_corpus` cobre 7 dos nossos 8 idiomas com procedencia por documento —
  faltando exatamente o portugues, que e' o unico que ja' temos.

  🔴🔴 MAS: busca explicita em ~15.000 resumos achou **zero artigos sobre dedup near-duplicate
  ENTRE idiomas** e zero sobre traducoes paralelas duplicadas no pre-treino. E o `2606.24998`
  (nas nossas licoes, §2c #6) mede que repeticao interna causa dano NAO-MONOTONICO com pico em
  contagem intermediaria (3-10x).

  Se o `common_corpus` for ele proprio multi-paralelo — e o bloco OpenGovernment (documentos
  administrativos da UE) tem tudo para ser —, traduzir en+fr+de para PT produz NEAR-DUPLICATAS em
  portugues, na faixa exata do pico do dano. **Este censo mede isso antes de gastar tradutor.**

⭐⭐ A IMPRESSAO DIGITAL QUE SOBREVIVE A TRADUCAO
  Nao da' para detectar duplicata cross-lingual comparando texto: as palavras mudam. O que NAO
  muda numa traducao fiel e' a **sequencia ordenada de NUMEROS** — datas, valores, numeros de
  artigo, percentuais. Um regulamento da UE em 13 idiomas carrega os mesmos numeros na mesma
  ordem. A digital e' o hash dessa sequencia.

  ⚠️ Guarda: documento com poucos numeros colide por acaso. So' entra no censo quem tem pelo
  menos `--min-numeros`, e a **cobertura** (fracao de documentos com digital admissivel) vai
  impressa — sem ela, "achei pouca duplicata" pode significar "quase nada foi olhado".

⭐⭐ E A AMOSTRAGEM QUE DERROTA O VIES DA §2ac
  A §2ac mede que censo de duplicacao NAO PODE ser pilotado: numa amostra de fracao *f*, uma
  duplicata so' e' detectavel se as DUAS copias cairem nela, entao a taxa medida ~= real x *f*.
  No FineWeb isso deu erro de 170x.

  Aqui o corpus tem 2,27 TRILHOES de tokens e censo completo e' inviavel. A saida NAO e' aceitar
  o vies: e' **amostrar pela DIGITAL, nao pelo documento**. Se duas copias tem a mesma digital,
  elas caem no mesmo balde — ou as duas entram na amostra, ou nenhuma. Dentro dos baldes
  amostrados a medicao e' **sem vies**, e a fracao amostrada vira apenas menos precisao, nao
  menos taxa.

⚠️ O QUE ESTE CENSO NAO MOSTRA (§2q)
  · Digital NUMERICA nao pega texto sem numeros (literatura, ficcao). A cobertura diz quanto.
  · Traducao livre que reescreve numeros por extenso escapa. E' um piso de duplicacao, nao um teto.
  · Mede o corpus FONTE. O que chega ao treino depois de traduzido pode duplicar por outros
    caminhos (o mesmo fato contado por fontes diferentes) que esta digital nao ve'.

Uso:
    python bee/gate_trad_censo.py --idiomas en,fr,de,es,it --baldes 64
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# os 7 do common_corpus que sao alvo do Bee-1G (o 8o, pt, e' o que falta e o que se quer produzir)
ALVOS_BEE = ["en", "fr", "de", "es", "zh", "ja", "ar"]

# ⚠️ O campo `language` do common_corpus vem por EXTENSO ("French"), nao em codigo ISO. Filtrar
# por `lang[:2]` casaria "Fr" com nada e o censo leria zero documentos sem dar erro nenhum —
# exatamente a familia "dado some e nada reclama". Verificado no esquema real em 2026-09-02.
NOME_PARA_COD = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es", "italian": "it",
    "dutch": "nl", "polish": "pl", "latin": "la", "russian": "ru", "korean": "ko",
    "chinese": "zh", "japanese": "ja", "arabic": "ar",
}

_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def digital(texto: str, min_numeros: int, n_shingle: int) -> str | None:
    """Hash da sequencia ordenada de numeros — o que sobrevive a uma traducao fiel.

    ⚠️ Normaliza separador decimal e de milhar, porque `1.234,56` (pt/de) e `1,234.56` (en) sao
    o MESMO numero escrito em convencoes diferentes. Sem isto a digital quebraria exatamente
    entre os idiomas que se quer comparar — o defeito estaria dentro do instrumento.
    """
    nums = [n.replace(".", "").replace(",", "") for n in _NUM.findall(texto)]
    nums = [n.lstrip("0") or "0" for n in nums]
    if len(nums) < min_numeros:
        return None
    # shingle: os primeiros n_shingle numeros. Documento longo cortado ao meio por um crawler
    # ainda casa se o inicio bate; usar a sequencia inteira seria fragil demais.
    chave = "|".join(nums[:n_shingle])
    return hashlib.sha1(chave.encode()).hexdigest()


def balde(dig: str, n_baldes: int) -> int:
    return int(dig[:8], 16) % n_baldes


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="PleIAs/common_corpus")
    ap.add_argument("--idiomas", default=",".join(ALVOS_BEE))
    ap.add_argument("--docs-por-idioma", type=int, default=200_000,
                    help="teto de documentos LIDOS por idioma (o filtro de balde vem depois)")
    ap.add_argument("--baldes", type=int, default=64,
                    help="1 de N baldes de digital e' retido — amostra SEM vies de par (§2ac)")
    ap.add_argument("--min-numeros", type=int, default=8,
                    help="menos que isto colide por acaso; entra na cobertura como nao-admissivel")
    ap.add_argument("--shingle", type=int, default=12)
    ap.add_argument("--arquivos-por-pasta", type=int, default=30,
                    help="quantos parquets de CADA uma das 10 pastas ler — espalha a leitura "
                         "pelo repositorio. 0 = ler sequencial do inicio (nao recomendado)")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "gate-trad-censo.json")
    args = ap.parse_args()

    from datasets import load_dataset

    idiomas = [c.strip() for c in args.idiomas.split(",") if c.strip()]
    print("=" * 96)
    print("GATE T-TRAD estagio A — censo de repeticao CROSS-LINGUAL no corpus FONTE")
    print(f"{args.repo} · {len(idiomas)} idiomas · retendo 1 de {args.baldes} baldes de digital")
    print("=" * 96)

    # digital -> {idioma: contagem}
    vistos: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stats = {}

    # UMA passada sobre o stream: nao ha' idioma no caminho dos 10.020 parquets, entao o filtro
    # e' pelo campo `language` de cada registro. Acumula os idiomas-alvo em paralelo.
    #
    # 🔴 E a leitura e' ESPALHADA pelo repositorio, nao sequencial. A v1 lia do inicio e parou em
    # 69.907 documentos — todos das primeiras pastas, logo das mesmas colecoes. O balde de digital
    # garante que copias caiam juntas SE ambas forem LIDAS; lendo so' o comeco, a copia inglesa
    # esta' no arquivo 1 e a francesa no 5.000, e o vies da §2ac volta pela leitura. Pegar N
    # arquivos de cada uma das 10 pastas cobre a estrutura do corpus em vez de um canto dela.
    arquivos = None
    if args.arquivos_por_pasta:
        import urllib.request
        d = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"https://huggingface.co/api/datasets/{args.repo}?full=true",
            headers={"User-Agent": "bee-1g"}), timeout=120).read())
        todos = sorted(s["rfilename"] for s in d.get("siblings", [])
                       if s["rfilename"].endswith(".parquet"))
        porpasta: dict[str, list[str]] = defaultdict(list)
        for f in todos:
            porpasta[f.split("/")[0]].append(f)
        arquivos = []
        for pasta, fs in sorted(porpasta.items()):
            passo = max(1, len(fs) // args.arquivos_por_pasta)
            arquivos.extend(fs[::passo][:args.arquivos_por_pasta])
        print(f"  leitura espalhada: {len(arquivos)} parquets de {len(porpasta)} pastas "
              f"(de {len(todos)} no repo)\n")
    ds = (load_dataset(args.repo, split="train", streaming=True, data_files=arquivos)
          if arquivos else load_dataset(args.repo, split="train", streaming=True))
    cont = {l: [0, 0, 0] for l in idiomas}          # [lidos, admissiveis, retidos]
    licencas: dict[str, int] = defaultdict(int)
    colecoes: dict[str, int] = defaultdict(int)
    t0 = time.time()
    n_total = n_fora = 0
    alvo_total = args.docs_por_idioma * len(idiomas)
    for ex in ds:
        n_total += 1
        cod = NOME_PARA_COD.get(str(ex.get("language", "")).strip().lower())
        if cod not in cont:
            n_fora += 1
        else:
            c = cont[cod]
            if c[0] < args.docs_por_idioma:
                c[0] += 1
                licencas[str(ex.get("license", "—"))] += 1
                colecoes[str(ex.get("collection", "—"))] += 1
                d = digital(ex.get("text") or "", args.min_numeros, args.shingle)
                if d is not None:
                    c[1] += 1
                    if balde(d, args.baldes) == 0:   # ⭐ amostra pela DIGITAL, nao pelo documento
                        c[2] += 1
                        vistos[d][cod] += 1
        if n_total % 200_000 == 0:
            feito = sum(c[0] for c in cont.values())
            print(f"  {n_total:>10,} lidos · {feito:>9,}/{alvo_total:,} nos alvos · "
                  f"{(time.time()-t0)/60:5.1f} min", flush=True)
        if all(c[0] >= args.docs_por_idioma for c in cont.values()):
            break
    for lang in idiomas:
        lidos, adm, ret = cont[lang]
        cob = adm / max(1, lidos)
        stats[lang] = {"lidos": lidos, "admissiveis": adm, "cobertura": cob, "retidos": ret}
        print(f"  {lang}: {lidos:>8,} lidos · {adm:>8,} com digital ({cob:.1%}) · "
              f"{ret:>7,} no balde")
    print(f"\n  (varridos {n_total:,} documentos; {n_fora:,} fora dos idiomas-alvo)")
    print("\n  procedencia declarada por documento — top licencas:")
    for k, v in sorted(licencas.items(), key=lambda kv: -kv[1])[:6]:
        print(f"    {k[:50]:<52} {v:>8,}")

    # ---------------------------------------------------------------- analise
    print(f"\n{'='*96}\nDUPLICACAO CROSS-LINGUAL (digitais presentes em >1 idioma)\n{'='*96}")
    n_dig = len(vistos)
    cross = {d: v for d, v in vistos.items() if len(v) > 1}
    hist = defaultdict(int)
    for v in cross.values():
        hist[len(v)] += 1
    pares = defaultdict(int)
    for v in cross.values():
        ls = sorted(v)
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                pares[f"{ls[i]}-{ls[j]}"] += 1

    print(f"digitais distintas no balde .......... {n_dig:,}")
    print(f"presentes em MAIS DE UM idioma ....... {len(cross):,} "
          f"({len(cross)/max(1,n_dig):.2%})")
    print(f"\n{'idiomas por digital':<24} documentos")
    for k in sorted(hist):
        marca = "  ⚠️ faixa do pico do dano (2606.24998)" if 3 <= k <= 10 else ""
        print(f"  {k:>2} idiomas{'':<13} {hist[k]:>8,}{marca}")
    print(f"\npares de idioma mais duplicados:")
    for p, n in sorted(pares.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {p:<10} {n:>8,}")

    # duplicacao DENTRO do mesmo idioma (o outro risco, e' de graca no mesmo passe)
    intra = sum(1 for v in vistos.values() if any(c > 1 for c in v.values()))
    print(f"\nduplicacao INTRA-idioma (mesma digital repetida no mesmo idioma): "
          f"{intra:,} ({intra/max(1,n_dig):.2%})")

    doc = {
        "_gate": "T-TRAD estagio A — repeticao cross-lingual no corpus fonte",
        "_metodo": ("digital = hash da sequencia ordenada de numeros (sobrevive a traducao). "
                    "Amostragem por BALDE DE DIGITAL, nao por documento: duplicatas caem no "
                    "mesmo balde, entao a medicao dentro dos baldes retidos e' SEM o vies da "
                    "§2ac (que no FineWeb deu erro de 170x)."),
        "_nao_mostra": ["texto sem numeros (literatura, ficcao) — ver cobertura por idioma",
                        "traducao que escreve numeros por extenso",
                        "duplicacao semantica sem numeros em comum",
                        "e' um PISO de duplicacao, nunca um teto"],
        "parametros": {"baldes": args.baldes, "min_numeros": args.min_numeros,
                       "shingle": args.shingle, "docs_por_idioma": args.docs_por_idioma},
        "por_idioma": stats,
        "licencas_declaradas": dict(sorted(licencas.items(), key=lambda kv: -kv[1])[:20]),
        "colecoes": dict(sorted(colecoes.items(), key=lambda kv: -kv[1])[:20]),
        "digitais_no_balde": n_dig,
        "cross_lingual": {"digitais": len(cross), "fracao": len(cross) / max(1, n_dig),
                          "histograma_idiomas_por_digital": dict(hist),
                          "pares": dict(sorted(pares.items(), key=lambda kv: -kv[1])[:20])},
        "intra_idioma": {"digitais": intra, "fracao": intra / max(1, n_dig)},
    }
    args.out.parent.mkdir(exist_ok=True)
    tmp = args.out.with_suffix(".json.tmp")
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, args.out)
    print(f"\nartefato: {args.out}")

    # ---------------------------------------------------------------- veredito
    pico = sum(v for k, v in hist.items() if 3 <= k <= 10) / max(1, n_dig)
    print(f"\n{'='*96}\nVEREDITO — criterio declarado ANTES de medir")
    print("  o 2606.24998 mede dano NAO-MONOTONICO com pico em 3-10 copias.")
    print(f"  fracao de digitais na faixa 3-10 idiomas: {pico:.2%}")

    # 🔴🔴 GUARDA DE PODER (§2s) — e a v1 dela MEDIA A COISA ERRADA.
    #
    # A v1 exigia 500 digitais NO TOTAL e passou com 2.628 — mas 1.815 delas eram inglesas.
    # Para detectar uma duplicata en-nl e' preciso ter as DUAS copias, e havia 19 digitais em
    # holandes. O par jamais seria visto, e o script imprimiu "🟢 duplicacao baixa" com a mesma
    # cara de quem mediu. **O poder de um censo de PARES e' limitado pelo lado MENOR do par**,
    # nunca pelo total — somar os dois lados esconde exatamente o lado que falta.
    #
    # ⚠️ E ha' um segundo limite, que o balde de digital NAO resolve: o balde garante que copias
    # caiam juntas SE ambas forem lidas. Lendo 70 mil de centenas de milhoes de documentos, a
    # copia inglesa pode estar no arquivo 1 e a francesa no 5.000 — e o vies da §2ac volta pela
    # LEITURA, nao pelo balde. Por isso a cobertura de arquivos tambem entra no veredito.
    MIN_POR_IDIOMA = 300
    fracos = {l: stats[l]["retidos"] for l in idiomas if stats[l]["retidos"] < MIN_POR_IDIOMA}
    if fracos:
        print(f"\n  🔴 CENSO SEM PODER PARA PARES: o poder e' limitado pelo lado MENOR.")
        print(f"     minimo por idioma: {MIN_POR_IDIOMA} digitais no balde. Abaixo disso:")
        for l, n in sorted(fracos.items(), key=lambda kv: kv[1]):
            print(f"       {l}: {n:>5} — nenhum par envolvendo '{l}' seria detectavel")
        print(f"     ⚠️ 'zero duplicacao' nestes idiomas e' indistinguivel de 'nao havia como ver'.")
        print("     NAO leia o veredito abaixo para eles. Aumente --docs-por-idioma,")
        print("     reduza --baldes, ou espalhe a leitura com --arquivos-por-pasta.")
        doc["_sem_poder"] = {"minimo_por_idioma": MIN_POR_IDIOMA, "abaixo": fracos,
                             "_por_que": ("poder de censo de PARES e' limitado pelo lado menor; "
                                          "somar os lados esconde o que falta")}
        tmp = args.out.with_suffix(".json.tmp")
        io.open(tmp, "w", encoding="utf-8", newline="\n").write(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp, args.out)
        return 3

    if pico >= 0.05:
        print("  🔴 traduzir varios idiomas-fonte para PT criaria near-duplicatas na faixa do")
        print("     pico. Dedup cross-lingual e' PRE-REQUISITO, nao opcional.")
    elif len(cross) / max(1, n_dig) >= 0.05:
        print("  ⚠️ ha' duplicacao cross-lingual fora da faixa de pico — traduzir de UMA fonte")
        print("     por documento (nao de varias) evita o problema sem dedup.")
    else:
        print("  🟢 duplicacao cross-lingual baixa neste corpus — traduzir nao cria o problema")
        print("     que o 2606.24998 mede. ⚠️ mas leia a cobertura antes de acreditar.")
    baixa = [l for l, s in stats.items() if s["cobertura"] < 0.30]
    if baixa:
        print(f"\n  ⚠️ COBERTURA BAIXA em {', '.join(baixa)} — nesses idiomas o censo olhou "
              f"menos de 30% dos documentos e o resultado NAO vale para eles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
