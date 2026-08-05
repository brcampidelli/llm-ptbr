"""Curva completa do gate pareado, com intervalo de confianca por bootstrap.

⭐ POR QUE O BOOTSTRAP E' OBRIGATORIO AQUI
  Os ganhos medidos estao entre 0,7% e 1,6% — da ordem do proprio ruido amostral.
  Reavaliar o mesmo checkpoint com 150 e depois com 300 documentos mudou um dos
  holdouts de -2,46% para -0,48%. Sem IC, "o+1,62% caiu para +0,73%" pode ser
  tendencia real ou pode ser a mesma coisa medida duas vezes.

  O bootstrap e PAREADO sobre documentos: reamostra os MESMOS indices nos dois
  bracos, porque o que interessa e a diferenca entre eles no mesmo texto — nao
  a variancia de cada um isolado.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "bee" / "gate"
LN2 = math.log(2.0)
PONTOS = [("p1000", 33), ("p2000", 66), ("p3000", 98), ("final", 131)]


def por_doc(dir_modelo, holdout, tok, dev):
    """bits e bytes POR DOCUMENTO — o bootstrap precisa do detalhe, nao do total."""
    m = AutoModelForCausalLM.from_pretrained(dir_modelo, dtype=torch.bfloat16).to(dev).eval()
    textos = json.loads((BASE / f"holdout_{holdout}.json").read_text(encoding="utf-8"))
    bits, byts = [], []
    with torch.no_grad():
        for t in textos:
            ids = tok(t, add_special_tokens=False,
                      return_tensors="pt")["input_ids"][:, :512].to(dev)
            if ids.shape[1] < 2:
                continue
            byts.append(len(tok.decode(ids[0], skip_special_tokens=True).encode("utf-8")))
            lg = m(ids).logits
            bits.append(torch.nn.functional.cross_entropy(
                lg[0, :-1].float(), ids[0, 1:], reduction="sum").item() / LN2)
    del m
    torch.cuda.empty_cache()
    return np.array(bits), np.array(byts)


def main() -> int:
    tok = AutoTokenizer.from_pretrained(ROOT / "models" / "bee-150m-v3-base")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rng = np.random.default_rng(42)
    saida = []
    print(f"{'tokens':>8}{'cru':>10}{'filtrado':>10}{'ganho':>9}{'IC 95%':>20}{'P(>0)':>8}")
    print("-" * 65)
    for ponto, mtok in PONTOS:
        suf = "" if ponto == "final" else f"_{ponto}"
        linha = {"ponto": ponto, "tokens_M": mtok}
        for hold in ("wiki", "cru"):
            bc, yc = por_doc(BASE / f"modelo_cru{suf}", hold, tok, dev)
            bf, yf = por_doc(BASE / f"modelo_filtrado{suf}", hold, tok, dev)
            n = len(bc)
            d = []
            for _ in range(5000):
                i = rng.integers(0, n, n)          # PAREADO: mesmos indices nos dois
                a, b = bc[i].sum() / yc[i].sum(), bf[i].sum() / yf[i].sum()
                d.append((a - b) / a)
            d = np.array(d)
            linha[hold] = {"bpb_cru": float(bc.sum()/yc.sum()),
                           "bpb_filtrado": float(bf.sum()/yf.sum()),
                           "ganho": float(d.mean()),
                           "ic": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                           "p_positivo": float((d > 0).mean())}
        w = linha["wiki"]
        print(f"{mtok:>7}M{w['bpb_cru']:>10.4f}{w['bpb_filtrado']:>10.4f}"
              f"{w['ganho']:>+9.2%}   [{w['ic'][0]:+.2%}, {w['ic'][1]:+.2%}]{w['p_positivo']:>8.0%}")
        saida.append(linha)
    (BASE / "curva.json").write_text(json.dumps(saida, indent=2), encoding="utf-8")
    print("\n(holdout neutro = wikipedia; o cru favorece o braco nao-filtrado, de proposito)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
