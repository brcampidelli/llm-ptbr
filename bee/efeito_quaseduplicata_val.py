"""Quanto a quase-duplicata infla a val loss? — complemento do censo de 13-gramas (gate #5).

🔴 POR QUE EXISTE. O censo (bee/censo_ngram_val.py) achou 1.431 docs de PT (6,0%) com >= 50% dos
   13-gramas no treino, 425 (1,8%) com >= 80%, num holdout que o fingerprint dizia limpo. Contar
   nao e' medir: a pergunta que decide e' QUANTO isso desloca a val loss. Se os docs contaminados
   tem loss muito menor que os limpos, a val loss de todo marco esta' inflada para baixo em PT.

O QUE MEDE, por marco:
  L_sujo  = loss media/token em TODOS os docs com frac >= LIMIAR   (censo completo desse balde)
  L_limpo = loss media/token numa AMOSTRA aleatoria de docs com frac < 0,2, com erro-padrao
  Vies    = L_todos - L_limpo, onde L_todos e' a media ponderada por tokens usando as contagens
            REAIS de tokens de cada balde (nao a amostra). Reporta tambem por balde de frac.

⚠️ Nao roda o holdout inteiro (20M tokens de PT = horas na 5070): o balde sujo entra inteiro e o
   limpo e' amostrado com n grande e SE reportado. O piso de ruido da validacao (0,0076) e' a
   referencia para dizer se o vies importa.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def loss_por_doc(m, val, docs, seq_len, dev):
    import torch
    out = []
    with torch.no_grad():
        for i, f in docs:
            ids = val[i:min(f, i + seq_len)].astype(np.int64)
            if len(ids) < 2:
                out.append((0.0, 0)); continue
            x = torch.from_numpy(ids)[None].to(dev)
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                l = m(input_ids=x, labels=x).loss.item()
            out.append((l, len(ids) - 1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marco", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--por-doc", required=True, help="npy (ini, fim, frac) do censo")
    ap.add_argument("--layout", required=True, help="json [[idioma, n_tokens], ...]")
    ap.add_argument("--idioma", default="por")
    ap.add_argument("--limiar", type=float, default=0.5)
    ap.add_argument("--n-limpo", type=int, default=1500)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--dispositivo", default="cuda")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM

    dest = ROOT / args.saida
    if dest.exists():
        raise SystemExit(f"🔴 {dest} ja existe — nao sobrescrevo (§2z)")

    val = np.fromfile(args.val, dtype=np.uint16)
    pd = np.load(args.por_doc)                                   # (ini, fim, frac)
    lay = json.load(open(args.layout, encoding="utf-8"))
    acc, faixa = 0, None
    for nome, n in lay:
        if nome == args.idioma:
            faixa = (acc, acc + n); break
        acc += n
    assert faixa, args.idioma
    sel = pd[(pd[:, 0] >= faixa[0]) & (pd[:, 0] < faixa[1])]
    frac = sel[:, 2]
    tok_doc = np.minimum(sel[:, 1] - sel[:, 0], args.seq_len) - 1   # tokens preditos por doc (cortado em seq_len)
    print(f"{args.idioma}: {len(sel):,} docs · {int(tok_doc.sum()):,} tokens preditos (cortado em {args.seq_len})")

    sujo = sel[frac >= args.limiar]
    limpo_all = sel[frac < 0.2]
    rng = np.random.default_rng(42)
    limpo = limpo_all[rng.choice(len(limpo_all), size=min(args.n_limpo, len(limpo_all)), replace=False)]
    print(f"  sujo (frac >= {args.limiar}): {len(sujo):,} docs, TODOS · limpo (frac < 0,2): amostra {len(limpo):,} de {len(limpo_all):,}")

    m = AutoModelForCausalLM.from_pretrained(args.marco, dtype=torch.bfloat16).to(args.dispositivo).eval()
    t0 = time.time()
    ls = loss_por_doc(m, val, [(int(a), int(b)) for a, b, _ in sujo], args.seq_len, args.dispositivo)
    ll = loss_por_doc(m, val, [(int(a), int(b)) for a, b, _ in limpo], args.seq_len, args.dispositivo)

    def media_pond(lst):
        n = sum(t for _, t in lst); return sum(l * t for l, t in lst) / max(n, 1), n
    L_sujo, T_sujo_amostra = media_pond(ls)
    L_limpo, T_limpo_amostra = media_pond(ll)
    # SE do limpo: por documento (unidade de amostragem), ponderado
    lv = np.array([l for l, _ in ll]); wv = np.array([t for _, t in ll], dtype=float)
    se_limpo = float(np.sqrt(np.sum((wv / wv.sum()) ** 2 * (lv - L_limpo) ** 2)))

    # vies na val loss do idioma: media ponderada pelas contagens REAIS de tokens de cada balde
    T_sujo = float(tok_doc[frac >= args.limiar].sum())
    T_meio = float(tok_doc[(frac >= 0.2) & (frac < args.limiar)].sum())   # balde intermediario: assumido = limpo (conservador)
    T_limpo = float(tok_doc[frac < 0.2].sum())
    T_tot = T_sujo + T_meio + T_limpo
    L_todos_est = (T_sujo * L_sujo + (T_meio + T_limpo) * L_limpo) / T_tot
    vies = L_todos_est - L_limpo

    # por balde de frac, no que foi medido
    baldes = {}
    for lo in (0.5, 0.6, 0.7, 0.8, 0.9):
        mk = [(l, t) for (l, t), (_, _, f) in zip(ls, sujo) if lo <= f < lo + 0.1 or (lo == 0.9 and f >= 0.9)]
        if mk:
            baldes[f"{lo:.1f}+"] = {"docs": len(mk), "loss": media_pond(mk)[0]}

    res = {"marco": Path(args.marco).name, "idioma": args.idioma, "limiar": args.limiar, "seq_len": args.seq_len,
           "docs": int(len(sel)), "tokens_preditos": int(T_tot),
           "sujo": {"docs": int(len(sujo)), "tokens": int(T_sujo), "loss": L_sujo},
           "limpo": {"docs_amostra": int(len(limpo)), "docs_total": int(len(limpo_all)), "tokens_total": int(T_limpo),
                     "loss": L_limpo, "se": se_limpo},
           "intermediario_0.2_a_limiar": {"tokens": int(T_meio), "_assumido": "igual ao limpo (conservador)"},
           "loss_todos_estimada": L_todos_est, "vies_val_loss": vies,
           "piso_ruido_validacao": 0.0076, "vies_em_pisos": vies / 0.0076,
           "por_balde_frac": baldes, "minutos": round((time.time() - t0) / 60, 1),
           "_leitura": ("vies = quanto a val loss deste idioma esta' abaixo do que seria num holdout sem quase-duplicatas; "
                        "negativo = inflada para baixo")}
    dest.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  L_sujo {L_sujo:.4f} ({len(sujo):,} docs) · L_limpo {L_limpo:.4f} ± {se_limpo:.4f} ({len(limpo):,} docs)")
    print(f"  diferenca sujo-limpo {L_sujo - L_limpo:+.4f} nats")
    print(f"  VIES na val loss de {args.idioma}: {vies:+.4f} nats = {vies/0.0076:+.1f} pisos de ruido")
    for k, v in baldes.items():
        print(f"    frac {k}: {v['docs']} docs · loss {v['loss']:.4f}")
    print(f"  artefato: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
