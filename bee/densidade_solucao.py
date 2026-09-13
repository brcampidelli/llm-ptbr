"""Densidade de solucao dos marcos do Bee-1G — gate #2 do estudo do arXiv (2026-09-12).

🔴 POR QUE EXISTE. O artigo 2609.08966 (Aleph Alpha, MoE de 30B) mediu que o checkpoint de MELHOR
   loss — o decaido — foi o PIOR ponto de partida para SFT, e que a "densidade de solucao" (quanto
   o escore sobrevive a perturbacoes gaussianas nos pesos) separava os checkpoints treinaveis dos
   nao-treinaveis: CONSTANT 27%, MERGE 13%, COOLDOWN 0% a tau=0,90. O Bee-1G ia assumir "o
   pos-treino parte do 20B decaido" sem medir. Este script e' a medicao.

Definicao (eq. 1 do artigo):  delta(tau) = Pr_eps[ s(theta + eps) >= tau * s(theta) ],
eps ~ N(0, sigma^2) por peso, sigma ABSOLUTO em {0,005; 0,001}, 100 amostras, tau = 0,90.

⚠️ ADAPTACOES, declaradas antes de medir:
  1. s(theta) = exp(-loss media por token) no holdout wiki/limpo (o Bee-1G e' base; nao ha GSM8K).
     Com isso tau=0,90 significa "a loss subiu no maximo -ln(0,90) = 0,105 nats" — ~13x o piso de
     ruido da validacao (0,0076). Reporta-se tambem tau = 0,95 (0,051 nats) e 0,99 (0,010 nats).
  2. As MESMAS 100 amostras de ruido para todos os marcos (semente = indice da amostra), para a
     comparacao entre marcos ser PAREADA. Ruido diferente por marco confundiria ruido com sinal.
  3. O sweep roda num SUBCONJUNTO fixo do holdout (as primeiras N sequencias) por custo — 600
     avaliacoes numa RTX 5070. A regua e' ancorada de outro jeito: ver a guarda abaixo.

✅ GUARDA (§2aa): antes do sweep, o bpb SEM perturbacao no holdout wiki/limpo COMPLETO tem de
   reproduzir o que bee/ancora_pt.py mediu (docs/bpb-pt-bee1g-marcos.json). Se nao reproduzir, a
   regua mudou e o resultado nao vale — aborta.

⚠️ O que este numero NAO mostra: e' geometria local, nao treinabilidade medida. O artigo mesmo diz
   que nao estabelece causalidade. A leitura decisiva vem no fim do run: 15B (plato) x 20B (decaido).
   Os marcos de plato de agora estabelecem a LINHA DE BASE e o metodo.

Uso:
  .venv/Scripts/python.exe bee/densidade_solucao.py --marcos <dir1> <dir2> ... --saida docs/x.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

SIGMAS = (0.01, 0.005, 0.001)   # os dois do artigo + 0,01 para a parte ingreme
TAUS = (0.99, 0.95, 0.90)
TOL_ANCORA = 0.002          # bpb: reproducao da ancora (a regua e' deterministica entre rodadas)


def carregar(caminho: str, dev: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(caminho)
    m = AutoModelForCausalLM.from_pretrained(caminho, dtype=torch.bfloat16).to(dev).eval()
    return m, tok


def sequencias(tok, textos: list[str], seq_len: int) -> list[list[int]]:
    """Mesmo corte de ancora_pt/gate_t1_bpb: doc a doc, janelas de seq_len, sem tokens especiais."""
    seqs = []
    for t in textos:
        ids = tok(t, add_special_tokens=False)["input_ids"]
        for i in range(0, len(ids), seq_len):
            p = ids[i:i + seq_len]
            if len(p) >= 2:
                seqs.append(p)
    return seqs


def loss_media(m, seqs: list[list[int]], dev: str) -> float:
    """Loss media POR TOKEN (nats), ponderada pelo numero de tokens preditos — igual ao gate."""
    import torch
    nats, n = 0.0, 0
    with torch.no_grad():
        for p in seqs:
            x = torch.tensor([p], dtype=torch.long, device=dev)
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                l = m(input_ids=x, labels=x).loss
            nats += l.item() * (len(p) - 1)
            n += len(p) - 1
    return nats / n


def bpb_completo(m, tok, textos: list[str], seq_len: int, dev: str) -> float:
    """bpb no holdout completo, como ancora_pt.py — a GUARDA de reproducao."""
    n_byte = sum(len(t.encode("utf-8")) for t in textos)
    seqs = sequencias(tok, textos, seq_len)
    nats = 0.0
    import torch
    with torch.no_grad():
        for p in seqs:
            x = torch.tensor([p], dtype=torch.long, device=dev)
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                nats += m(input_ids=x, labels=x).loss.item() * (len(p) - 1)
    return nats / math.log(2) / n_byte


def perturbar(m, originais: dict, sigma: float, semente: int):
    """theta <- theta_orig + N(0, sigma^2), com gerador fixo pela semente (mesmo eps para todo marco).
    Perturba TODOS os parametros, como o artigo (pesos do modelo inteiro)."""
    import torch
    g = torch.Generator(device="cuda").manual_seed(int(semente))
    with torch.no_grad():
        for nome, p in m.named_parameters():
            eps = torch.randn(p.shape, generator=g, device=p.device, dtype=torch.float32) * sigma
            p.copy_((originais[nome].float() + eps).to(p.dtype))


def restaurar(m, originais: dict):
    import torch
    with torch.no_grad():
        for nome, p in m.named_parameters():
            p.copy_(originais[nome])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marcos", nargs="+", required=True, help="diretorios dos snapshots")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--n-pert", type=int, default=100)
    ap.add_argument("--n-seqs", type=int, default=32, help="sequencias do holdout usadas no sweep")
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--ancora", default="docs/bpb-pt-bee1g-marcos.json")
    ap.add_argument("--dispositivo", default="cuda")
    args = ap.parse_args()

    from ancora_pt import holdouts, parte_por_contaminacao, _contaminados
    from transformers import AutoTokenizer
    import torch

    dest = ROOT / args.saida
    if dest.exists():
        raise SystemExit(f"🔴 {dest} ja existe — nome de saida deriva do que se mede; nao sobrescrevo (§2z)")

    # holdout wiki/limpo, EXATAMENTE como a ancora
    conj = holdouts(1_500_000)
    excl = _contaminados()
    tok64 = AutoTokenizer.from_pretrained(str(ROOT / "bee" / "tok_t1" / "64k-multi"))
    wiki_limpo, _ = parte_por_contaminacao(conj["wiki"], tok64, excl)
    print(f"holdout wiki/limpo: {len(wiki_limpo)} docs · {sum(len(t.encode('utf-8')) for t in wiki_limpo)/1e6:.2f} MB")

    ancora = json.loads((ROOT / args.ancora).read_text(encoding="utf-8"))["bpb"] if (ROOT / args.ancora).exists() else {}
    def bpb_ancora(caminho: str):
        nome = Path(caminho).name
        for k, v in ancora.items():
            if k.replace("\\", "/").rstrip("/").endswith(nome):
                return v.get("wiki/limpo")
        return None

    doc = {"_definicao": "delta(tau)=Pr_eps[s(theta+eps)>=tau*s(theta)], s=exp(-loss/token), eps~N(0,sigma^2) absoluto, "
                         "mesmas amostras de ruido para todos os marcos (semente=indice)",
           "_artigo": "2609.08966", "sigmas": list(SIGMAS), "taus": list(TAUS), "n_pert": args.n_pert,
           "n_seqs_sweep": args.n_seqs, "seq_len": args.seq_len, "holdout": "wiki/limpo (ancora_pt)",
           "_nao_mostra": ["treinabilidade medida — e' geometria local; o artigo nao estabelece causalidade",
                           "a leitura decisiva e' 15B plato x 20B decaido, no fim do run"],
           "marcos": {}}

    for caminho in args.marcos:
        nome = Path(caminho).name
        t0 = time.time()
        m, tok = carregar(caminho, args.dispositivo)

        # --- GUARDA §2aa: reproduz a ancora no holdout completo?
        b = bpb_completo(m, tok, wiki_limpo, args.seq_len, args.dispositivo)
        ref = bpb_ancora(caminho)
        if ref is not None and abs(b - ref) > TOL_ANCORA:
            raise SystemExit(f"🔴 {nome}: bpb sem perturbacao {b:.4f} NAO reproduz a ancora {ref:.4f} "
                             f"(tol {TOL_ANCORA}) — a regua mudou; abortando")
        print(f"{nome}: bpb wiki/limpo completo {b:.4f}" + (f" · ancora {ref:.4f} ✅" if ref else " · (sem ancora)"))

        # --- subconjunto fixo para o sweep
        seqs = sequencias(tok, wiki_limpo, args.seq_len)[: args.n_seqs]
        n_tok = sum(len(p) - 1 for p in seqs)
        L0 = loss_media(m, seqs, args.dispositivo)
        originais = {n: p.detach().clone() for n, p in m.named_parameters()}
        # magnitude tipica dos pesos, para o leitor julgar o que sigma significa AQUI
        stds = sorted(float(p.float().std()) for p in originais.values() if p.dim() == 2)
        std_mediana = stds[len(stds) // 2]
        print(f"  sweep: {len(seqs)} seqs · {n_tok:,} tokens · L0 {L0:.4f} · std mediana dos pesos 2D {std_mediana:.4f}")

        res = {"bpb_wiki_limpo_completo": b, "ancora": ref, "L0_sweep": L0, "n_tokens_sweep": n_tok,
               "std_mediana_pesos_2d": std_mediana, "por_sigma": {}}
        for sigma in SIGMAS:
            deltas = []
            for k in range(args.n_pert):
                perturbar(m, originais, sigma, semente=k)
                deltas.append(loss_media(m, seqs, args.dispositivo) - L0)
                if (k + 1) % 25 == 0:
                    print(f"    sigma {sigma}: {k+1}/{args.n_pert} · dL mediana ate agora {sorted(deltas)[len(deltas)//2]:+.4f}", flush=True)
            restaurar(m, originais)
            deltas_s = sorted(deltas)
            dens = {f"{tau:.2f}": sum(1 for d in deltas if d <= -math.log(tau)) / len(deltas) for tau in TAUS}
            res["por_sigma"][str(sigma)] = {
                "dL_mediana": deltas_s[len(deltas_s) // 2], "dL_p10": deltas_s[len(deltas_s) // 10],
                "dL_p90": deltas_s[9 * len(deltas_s) // 10], "dL_min": deltas_s[0], "dL_max": deltas_s[-1],
                "densidade": dens, "dL_todos": deltas}
            print(f"  sigma {sigma}: dL mediana {deltas_s[len(deltas_s)//2]:+.4f} [p10 {deltas_s[len(deltas_s)//10]:+.4f} · p90 {deltas_s[9*len(deltas_s)//10]:+.4f}] · "
                  f"densidade tau=0,99 {dens['0.99']:.0%} · 0,95 {dens['0.95']:.0%} · 0,90 {dens['0.90']:.0%}")
        res["minutos"] = round((time.time() - t0) / 60, 1)
        doc["marcos"][nome] = res
        del m, originais
        torch.cuda.empty_cache()

    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)
    print(f"\nartefato: {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
