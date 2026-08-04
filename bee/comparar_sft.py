"""Compara modelos pos-SFT com a mesma regua, em DOIS holdouts + sondas.

⚠️ POR QUE DOIS HOLDOUTS
  O holdout antigo (sft_ptbr.eval) so representa a distribuicao ANTIGA. Medir nele
  um modelo que treinou com 23% de dado da BNCC penaliza justamente o que foi
  acrescentado — a regua fica viciada CONTRA o modelo novo. O holdout da BNCC
  corrige isso, e vem de habilidades que NENHUM treino viu (fatia disjunta do
  sorteio, mesma semente). Reportar os dois separados; a media esconderia o efeito.

Uso:
    python bee/comparar_sft.py --modelos models/bee-150m-v3-sft models/bee-v3-sft-A ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SONDAS = [
    "O que e o Brasil?",
    "Explique o que e fotossintese.",
    "Escreva uma frase sobre o mar.",
    "Qual a capital de Minas Gerais?",
    "Liste tres frutas brasileiras.",
    "Como se faz um bolo de cenoura?",
    "Traduza para o ingles: bom dia.",
    "Quem foi Machado de Assis?",
]


def carregar(caminho: Path, limite: int) -> list[dict]:
    saida = []
    for linha in caminho.open(encoding="utf-8"):
        o = json.loads(linha)
        m = o.get("messages")
        if m and len(m) >= 2 and m[-1].get("role") == "assistant":
            saida.append({"prompt": m[:-1], "resposta": m[-1]["content"]})
        if len(saida) >= limite:
            break
    return saida


def perda(modelo, tok, exemplos, dispositivo) -> tuple[float, float]:
    """NLL media por token SO na resposta (o prompt e mascarado, como no treino)."""
    import torch

    soma_nll, n_tok, acertos = 0.0, 0, 0
    with torch.no_grad():
        for ex in exemplos:
            texto_p = tok.apply_chat_template(ex["prompt"], tokenize=False,
                                              add_generation_prompt=True)
            ids_p = tok(texto_p, return_tensors="pt")["input_ids"]
            ids_r = tok(ex["resposta"], return_tensors="pt",
                        add_special_tokens=False)["input_ids"]
            ids = torch.cat([ids_p, ids_r], dim=1)[:, :1024].to(dispositivo)
            n_p = ids_p.shape[1]
            if ids.shape[1] <= n_p + 1:
                continue
            logits = modelo(ids).logits[0, n_p - 1:-1].float()
            alvo = ids[0, n_p:]
            nll = torch.nn.functional.cross_entropy(logits, alvo, reduction="sum").item()
            soma_nll += nll
            n_tok += alvo.numel()
            acertos += (logits.argmax(-1) == alvo).sum().item()
    return soma_nll / max(1, n_tok), acertos / max(1, n_tok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "comparacao-sft.json")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    proc = ROOT / "comeia" / "data" / "processed"
    holdouts = {}
    for nome, arq in [("ptbr_antigo", "sft_ptbr.eval.jsonl"),
                      ("bncc_novo", "sft_bncc.eval.jsonl")]:
        p = proc / arq
        if p.exists():
            holdouts[nome] = carregar(p, args.n)
            print(f"holdout {nome:12s}: {len(holdouts[nome])} exemplos")
        else:
            print(f"holdout {nome:12s}: AUSENTE ({p.name})")

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    resultado = {}
    for mid in args.modelos:
        nome = Path(mid).name
        print(f"\n{'='*62}\n{nome}\n{'='*62}")
        tok = AutoTokenizer.from_pretrained(mid)
        mod = AutoModelForCausalLM.from_pretrained(mid, dtype=torch.bfloat16).to(dev).eval()
        r = {"holdouts": {}}
        for hn, ex in holdouts.items():
            nll, acc = perda(mod, tok, ex, dev)
            r["holdouts"][hn] = {"nll": round(nll, 4), "acuracia": round(acc, 4)}
            print(f"  {hn:12s} nll {nll:.4f}  acuracia {acc:.1%}")

        # Sondas: nao dependem de distribuicao nenhuma — e' o teste mais honesto.
        torch.manual_seed(42)
        r["sondas"] = []
        for s in SONDAS:
            t = tok.apply_chat_template([{"role": "user", "content": s}],
                                        tokenize=False, add_generation_prompt=True)
            ent = tok(t, return_tensors="pt").to(dev)
            with torch.no_grad():
                out = mod.generate(**ent, max_new_tokens=70, do_sample=True,
                                   temperature=0.7, top_p=0.9,
                                   pad_token_id=tok.pad_token_id or 3)
            resp = tok.decode(out[0][ent["input_ids"].shape[1]:],
                              skip_special_tokens=True).strip()
            r["sondas"].append({"pergunta": s, "resposta": resp})
            print(f"  [{s[:34]:<34}] {resp[:90]}")
        # vazio = o modelo emitiu fim-de-turno de cara; sinal de colapso
        r["sondas_vazias"] = sum(1 for x in r["sondas"] if len(x["resposta"]) < 5)
        resultado[nome] = r
        del mod
        torch.cuda.empty_cache()

    args.out.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{'='*62}\nRESUMO  (nll menor = melhor)\n{'='*62}")
    cab = f"{'modelo':<24}" + "".join(f"{h:>16}" for h in holdouts) + f"{'sond.vazias':>13}"
    print(cab)
    for nome, r in resultado.items():
        linha = f"{nome:<24}"
        for h in holdouts:
            linha += f"{r['holdouts'][h]['nll']:>16.4f}"
        print(linha + f"{r['sondas_vazias']:>13}")
    print(f"\nDetalhe em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
