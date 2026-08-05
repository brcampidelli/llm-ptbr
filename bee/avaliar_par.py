"""Avalia um par de checkpoints do gate (cru x filtrado) na CPU.

⚠️ NA CPU DE PROPOSITO: a GPU esta treinando com ~2 GB livres, e estourar VRAM
nesta maquina nao da OOM — da lentidao silenciosa (medido 3x em 2026-08-04).
Nao vale arriscar atrasar o treino para economizar 5 min de avaliacao.

⚠️ SEMPRE o mesmo n de documentos entre pontos: comparar um ponto medido com
150 docs contra outro com 300 introduz uma diferenca que nao e do experimento.
"""
import json, math, sys, torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = Path(__file__).resolve().parent / "gate"
LN2 = math.log(2.0)
torch.set_num_threads(6)                       # deixa nucleos para o treino


def bpb(dir_modelo: Path, holdout: str, tok, n: int) -> float:
    m = AutoModelForCausalLM.from_pretrained(dir_modelo, dtype=torch.float32).eval()
    textos = json.loads((BASE / f"holdout_{holdout}.json").read_text(encoding="utf-8"))[:n]
    bits = byts = 0.0
    with torch.no_grad():
        for t in textos:
            ids = tok(t, add_special_tokens=False, return_tensors="pt")["input_ids"][:, :512]
            if ids.shape[1] < 2:
                continue
            byts += len(tok.decode(ids[0], skip_special_tokens=True).encode("utf-8"))
            lg = m(ids).logits
            bits += torch.nn.functional.cross_entropy(
                lg[0, :-1], ids[0, 1:], reduction="sum").item() / LN2
    del m
    return bits / byts


def main() -> int:
    ponto = sys.argv[1] if len(sys.argv) > 1 else "p1000"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    suf = "" if ponto == "final" else f"_{ponto}"
    tok = AutoTokenizer.from_pretrained(Path(__file__).resolve().parent.parent
                                        / "models" / "bee-150m-v3-base")
    r = {}
    for braco in ("cru", "filtrado"):
        d = BASE / f"modelo_{braco}{suf}"
        if not d.exists():
            print(f"faltando {d.name}", file=sys.stderr)
            return 1
        r[braco] = {h: bpb(d, h, tok, n) for h in ("wiki", "cru")}
    g_neutro = (r["cru"]["wiki"] - r["filtrado"]["wiki"]) / r["cru"]["wiki"]
    g_cru = (r["cru"]["cru"] - r["filtrado"]["cru"]) / r["cru"]["cru"]
    print(f"\n=== {ponto} · {n} docs ===")
    print(f"{'':>10}{'wikipedia (neutro)':>22}{'fineweb cru':>16}")
    print(f"{'cru':>10}{r['cru']['wiki']:>22.4f}{r['cru']['cru']:>16.4f}")
    print(f"{'filtrado':>10}{r['filtrado']['wiki']:>22.4f}{r['filtrado']['cru']:>16.4f}")
    print(f"\nganho no holdout NEUTRO : {g_neutro:+.2%}")
    print(f"ganho no holdout cru     : {g_cru:+.2%}  (favorece o cru, de proposito)")
    saida = BASE / f"par_{ponto}.json"
    saida.write_text(json.dumps({"ponto": ponto, "n_docs": n, "bpb": r,
                                 "ganho_neutro": g_neutro, "ganho_cru": g_cru},
                                indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
