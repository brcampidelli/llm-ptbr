"""Fertilidade de um tokenizador nos 8 idiomas-alvo — a regua do Gate T1.

⚠️ POR QUE **NAO** tokens/PALAVRA, que e' a metrica historica deste projeto (§2g)
  `\\w+` nao segmenta han nem kana: em chines nao ha' espaco, entao uma "palavra" vira uma corrida
  inteira de caracteres e o numero fica **incomparavel entre escritas**. Trocar a regua entre os
  grupos que se quer comparar e' exatamente o erro da §2g. Aqui a regua e' **tokens/CARACTERE**
  (comparavel entre escritas) com **tokens/BYTE** ao lado.

⭐ E tokens/BYTE tem uma leitura direta que tokens/palavra nao tem:
  **tok/byte ~ 1,00 significa 1 token por byte** — ou seja, o vocabulario nao tem NADA para
  aquela escrita e tudo esta' caindo em fallback de byte, cada token um fragmento incompleto.

⭐ A REGUA SE VALIDA DE GRACA: o PT tem de reproduzir os **0,218 tok/byte** ja' publicados no
  projeto, e o EN os **0,3128** medidos no prep de 14,4B tokens do FineWeb. Se nao reproduzir,
  o defeito e' desta medicao e nao do tokenizador (§2aa: ao menos um braco reproduz numero
  conhecido, senao nao ha' comparacao a fazer).

Uso:
    python bee/fertilidade_multilingue.py --tokenizador models/bee-150m-v3-base
    python bee/fertilidade_multilingue.py --tokenizador X --corpus bee/corpus_multi
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ORDEM = ["por", "spa", "fra", "deu", "eng", "arb", "cmn", "jpn"]

# ancoras publicadas — a validacao gratuita da regua
ANCORAS = {"por": 0.218, "eng": 0.3128}
TOLERANCIA = 0.05          # 5% relativo


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizador", default="models/bee-150m-v3-base")
    ap.add_argument("--corpus", type=Path, default=ROOT / "bee" / "corpus_multi")
    ap.add_argument("--docs", type=int, default=400, help="documentos por idioma")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    import zstandard as zstd
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.tokenizador)
    print(f"tokenizador: {args.tokenizador}  ·  vocab {tok.vocab_size:,}")
    print(f"corpus:      {args.corpus}\n")

    linhas: dict[str, dict] = {}
    for cod in ORDEM:
        shards = sorted(glob.glob(str(args.corpus / f"bee_corpus_{cod}_*.jsonl.zst")))
        if not shards:
            print(f"  ⚠️ {cod}: sem shards em {args.corpus} — pulando")
            continue
        bruto = zstd.ZstdDecompressor().decompress(open(shards[0], "rb").read()).decode("utf-8")
        txts = [json.loads(l)["text"] for l in bruto.splitlines()[: args.docs] if l.strip()]
        n_tok = sum(len(tok(t, add_special_tokens=False)["input_ids"]) for t in txts)
        n_car = sum(len(t) for t in txts)
        n_byt = sum(len(t.encode("utf-8")) for t in txts)
        linhas[cod] = {"documentos": len(txts), "tokens": n_tok, "caracteres": n_car,
                       "bytes": n_byt, "tok_por_caractere": n_tok / max(1, n_car),
                       "tok_por_byte": n_tok / max(1, n_byt),
                       "bytes_por_caractere": n_byt / max(1, n_car)}

    if not linhas:
        raise SystemExit("🔴 nenhum idioma encontrado — rode bee/coletar_multilingue.py antes")

    # ---------------------------------------------------------- guarda das ancoras
    problemas = []
    for cod, esperado in ANCORAS.items():
        if cod not in linhas:
            continue
        obtido = linhas[cod]["tok_por_byte"]
        desvio = abs(obtido - esperado) / esperado
        marca = "OK" if desvio <= TOLERANCIA else "🔴 NAO REPRODUZ"
        print(f"[ancora] {cod}: {obtido:.4f} tok/byte contra {esperado} publicado "
              f"({desvio:+.1%})  {marca}")
        if desvio > TOLERANCIA:
            problemas.append(f"{cod}: {obtido:.4f} contra {esperado} publicado ({desvio:+.1%})")

    # ---------------------------------------------------------- tabela
    base = linhas.get("por", {}).get("tok_por_caractere")
    print(f"\n{'idioma':7} {'tok/car':>8} {'tok/byte':>9} {'B/car':>6} {'vs PT':>7}  leitura")
    print("-" * 74)
    for cod, m in linhas.items():
        tb = m["tok_por_byte"]
        nota = ("  ← FALLBACK DE BYTE" if tb > 0.90
                else "  ← quase fallback" if tb > 0.70 else "")
        rel = f"{m['tok_por_caractere']/base:>6.1f}x" if base else "     —"
        print(f"{cod:7} {m['tok_por_caractere']:>8.3f} {tb:>9.3f} "
              f"{m['bytes_por_caractere']:>6.2f} {rel}{nota}")

    print("\n⭐ tok/byte ≈ 1,00 == 1 token por byte == o vocabulario nao tem NADA "
          "para aquela escrita.")
    if base:
        print(f"\nConsequencia direta numa janela de 2.048 tokens:")
        for cod, m in linhas.items():
            print(f"   {cod}: {2048/m['tok_por_caractere']:>7,.0f} caracteres")

    saida = args.out or (ROOT / "docs" /
                         f"fertilidade-{Path(args.tokenizador).name}.json")
    saida.parent.mkdir(parents=True, exist_ok=True)
    doc = {"tokenizador": str(args.tokenizador), "vocab": int(tok.vocab_size),
           "corpus": str(args.corpus), "docs_por_idioma": args.docs,
           "_regua": "tokens/CARACTERE — tokens/palavra nao e' comparavel entre escritas (§2g)",
           "_ancoras": {k: {"publicado": v, "medido": linhas[k]["tok_por_byte"]}
                        for k, v in ANCORAS.items() if k in linhas},
           "idiomas": linhas}
    tmp = saida.with_suffix(".json.tmp")
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, saida)
    print(f"\nartefato: {saida}")

    if problemas:
        print(f"\n🔴 A REGUA NAO REPRODUZ ANCORA CONHECIDA — nao use estes numeros (§2aa):")
        for p in problemas:
            print(f"   · {p}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
