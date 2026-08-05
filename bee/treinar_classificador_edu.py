"""Etapas 2 e 3 do FineWeb-Edu em portugues: classificador barato + aplicacao.

Recebe o `anotado.jsonl` da etapa 1 (nota 0-5 do professor) e treina um regressor
sobre embeddings. O FineWeb-Edu usa exatamente isso: um LLM anota uma amostra, um
classificador barato generaliza para o corpus inteiro. Anotar 30 GB com LLM seria
proibitivo; anotar 3k e generalizar custa quase nada.

⭐ A PERGUNTA QUE ESTE SCRIPT RESPONDE
  Nao e' "qual a nota media" — e' **o classificador SEPARA em portugues?**
  Se ele nao reproduz o julgamento do professor num holdout, filtrar o corpus com
  ele so introduz ruido caro. Este e' o gate barato ANTES de gastar em anotacao
  de larga escala ou em GPU de treino.

⚠️ HOLDOUT POR HASH, NAO POR POSICAO — a licao mais cara do projeto, aprendida
  duas vezes na COMEIA. `sha1(texto) % 100 < 20` da o mesmo split sempre, e imune
  a reordenacao do arquivo.

Uso:
    python bee/treinar_classificador_edu.py
    python bee/treinar_classificador_edu.py --corte 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANOTADO = ROOT / "bee" / "edu" / "anotado.jsonl"
MODELO = ROOT / "bee" / "edu" / "classificador.joblib"


def split_por_hash(texto: str, pct_teste: int = 20) -> bool:
    """True se o doc vai para o TESTE. Estavel: depende so do conteudo."""
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest(), 16) % 100 < pct_teste


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anotado", type=Path, default=ANOTADO)
    ap.add_argument("--corte", type=int, default=3, help="nota minima para manter (FineWeb-Edu usa 3)")
    ap.add_argument("--max-chars", type=int, default=2500)
    ap.add_argument("--out", type=Path, default=MODELO)
    args = ap.parse_args()

    if not args.anotado.exists():
        print(f"ERRO: rode bee/anotar_edu.py antes — falta {args.anotado}", file=sys.stderr)
        return 1

    regs = [json.loads(l) for l in args.anotado.open(encoding="utf-8")]
    print("=" * 66)
    print("FineWeb-Edu PT — etapas 2 e 3: classificador de valor educacional")
    print("=" * 66)
    print(f"  anotados : {len(regs)}")

    treino = [r for r in regs if not split_por_hash(r["texto"])]
    teste = [r for r in regs if split_por_hash(r["texto"])]
    print(f"  treino   : {len(treino)} · teste {len(teste)}  (split por sha1, nao por posicao)")

    import numpy as np

    # ⭐ Vetorizacao: TF-IDF de caractere + palavra. O FineWeb-Edu usa embeddings de
    # um encoder; aqui TF-IDF e' o baseline HONESTO e roda em CPU em segundos. Se o
    # TF-IDF ja separar, embedding neural so melhora — e se NAO separar, o problema
    # e' o sinal, nao a representacao, e embedding caro nao salvaria.
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.pipeline import make_union

    vet = make_union(
        TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=3, max_features=60000,
                        sublinear_tf=True, strip_accents="unicode", lowercase=True),
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, max_features=40000,
                        sublinear_tf=True, lowercase=True),
    )
    Xtr = vet.fit_transform([r["texto"][: args.max_chars] for r in treino])
    Xte = vet.transform([r["texto"][: args.max_chars] for r in teste])
    ytr = np.array([r["nota"] for r in treino])
    yte = np.array([r["nota"] for r in teste])
    print(f"  features : {Xtr.shape[1]:,}")

    # --- regressao (a nota como numero) ---------------------------------------
    reg = Ridge(alpha=1.0).fit(Xtr, ytr)
    pred = reg.predict(Xte)
    corr = float(np.corrcoef(pred, yte)[0, 1])
    mae = float(np.abs(pred - yte).mean())
    # baseline honesto: prever sempre a media do treino
    mae_base = float(np.abs(ytr.mean() - yte).mean())
    print(f"\n{'='*66}\nREGRESSAO (reproduz a nota do professor?)\n{'='*66}")
    print(f"  correlacao de Pearson : {corr:.3f}")
    print(f"  erro absoluto medio   : {mae:.3f}  (baseline 'chuta a media': {mae_base:.3f})")
    print(f"  ganho sobre baseline  : {(1-mae/mae_base):.1%}")

    # --- classificacao binaria (manter ou descartar) ---------------------------
    print(f"\n{'='*66}\nDECISAO BINARIA — manter se nota >= {args.corte}\n{'='*66}")
    clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xtr, ytr >= args.corte)
    pb = clf.predict(Xte)
    yb = yte >= args.corte
    print(classification_report(yb, pb, target_names=["descartar", "manter"], digits=3))
    tn, fp, fn, tp = confusion_matrix(yb, pb).ravel()
    print(f"  matriz: manteve certo {tp} · descartou certo {tn} · "
          f"manteve lixo {fp} · descartou bom {fn}")

    print(f"\n{'='*66}\nO QUE ISSO SIGNIFICA PARA O CORPUS\n{'='*66}")
    taxa_prof = float((np.array([r["nota"] for r in regs]) >= args.corte).mean())
    taxa_clf = float(pb.mean())
    print(f"  o professor manteria : {taxa_prof:.1%} do corpus")
    print(f"  o classificador manteria : {taxa_clf:.1%}")
    print(f"  (FineWeb-Edu original manteve ~9% — descartou 91%)")

    from sklearn.metrics import f1_score
    f1 = f1_score(yb, pb)
    if f1 >= 0.70 and corr >= 0.50:
        veredito = "PASSA — o classificador reproduz o julgamento do professor."
    elif f1 >= 0.55:
        veredito = "LIMITROFE — separa, mas com ruido. Mais anotacao antes de filtrar o corpus."
    else:
        veredito = ("NAO PASSA — filtrar com este classificador introduz mais ruido que sinal. "
                    "Antes de gastar em GPU, investigar: rubrica ambigua? amostra pequena? "
                    "sinal fraco em PT?")
    print(f"\n>>> VEREDITO (F1 {f1:.3f}, correlacao {corr:.3f}): {veredito}")

    import joblib
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vetorizador": vet, "regressor": reg, "classificador": clf,
                 "corte": args.corte, "n_treino": len(treino),
                 "f1": f1, "correlacao": corr}, args.out)
    print(f"\nmodelo salvo em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
