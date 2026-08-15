"""Sonda de ATIVACOES MASSIVAS e ATTENTION SINK — o fenomeno acontece na escala do Bee?

⭐ POR QUE ESTA SONDA EXISTE
  *Massive Activations in Large Language Models* (arXiv:2402.17762) mede que alguns modelos
  desenvolvem ativacoes com magnitude ordens de grandeza acima das demais, quase sempre em
  **dimensoes fixas** e em **tokens delimitadores** (o primeiro token, ponto final, quebra de
  linha). Elas funcionam como um *vies fixo* e estao na origem do **attention sink** —
  a massa de atencao que se acumula no primeiro token (arXiv:2309.17453, StreamingLLM).

  Isso importa para o Bee por dois motivos PRATICOS, nenhum deles teorico:
  1. **Quantizacao.** Uma ativacao 1000x maior que a mediana destroi a escala de um
     quantizador por-tensor. O projeto quer servir local; se o fenomeno existe, int8
     por-tensor esta descartado e o certo e por-canal.
  2. **Poda de contexto.** Se ha sink, jogar fora os primeiros tokens ao encurtar o
     historico degrada o modelo desproporcionalmente — e o Bee tem seq_len 2048 com um
     catalogo de ferramentas de ~1.100 tokens no inicio do prompt.

⚠️ O QUE ESTA SONDA NAO FAZ: nao mede qualidade, nao prova causalidade, e nao decide
   quantizacao sozinha. Ela responde UMA pergunta: **o fenomeno esta la, e onde?**

Uso:
    python bee/sonda_ativacoes.py --modelo models/bee-150m-v3-base
    python bee/sonda_ativacoes.py --modelo models/_marco_1B --rotulo bee-350m-1B
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Frases PT reais — o fenomeno e' sensivel a tokens delimitadores, entao o texto importa.
FRASES = [
    "O Brasil é um país de dimensões continentais. A sua população é diversa.",
    "A inteligência artificial mudou a forma como escrevemos software.",
    "Em 1988 foi promulgada a Constituição Federal do Brasil.\nEla tem 250 artigos.",
    "Receita de pão de queijo: polvilho, queijo minas, ovos e óleo.",
]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True)
    ap.add_argument("--rotulo", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    rotulo = a.rotulo or Path(a.modelo).name
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(a.modelo)
    # ⚠️ eager: o SDPA NAO expoe as matrizes de atencao, e sem elas metade desta sonda fica
    #    muda. A primeira versao rodou assim e imprimiu apenas um aviso do transformers no
    #    meio da saida — a secao de attention sink simplesmente nao apareceu, e passaria
    #    despercebida como "nao tem sink" em vez de "nao foi medido".
    modelo = AutoModelForCausalLM.from_pretrained(
        a.modelo, dtype=torch.float32, attn_implementation="eager").to(dev).eval()
    n_camadas = modelo.config.num_hidden_layers
    d = modelo.config.hidden_size
    print("=" * 78)
    print(f"SONDA DE ATIVACOES — {rotulo}")
    print(f"  {n_camadas} camadas · d_model {d} · {sum(p.numel() for p in modelo.parameters())/1e6:.1f}M params")
    print("=" * 78)

    piores = []          # (razao, camada, token, dim)
    por_camada = []

    for frase in FRASES:
        ent = tok(frase, return_tensors="pt").to(dev)
        with torch.no_grad():
            saida = modelo(**ent, output_hidden_states=True, output_attentions=True)
        ids = ent["input_ids"][0].tolist()
        toks = tok.convert_ids_to_tokens(ids)

        for c, h in enumerate(saida.hidden_states):     # (1, T, d)
            x = h[0].abs()
            mediana = x.median().item()
            mx, idx = x.flatten().max(0)
            t_i, d_i = divmod(idx.item(), x.shape[1])
            razao = mx.item() / max(mediana, 1e-9)
            piores.append((razao, c, toks[t_i] if t_i < len(toks) else "?", d_i, mx.item(), mediana))
            if len(por_camada) <= c:
                por_camada.append([])
            por_camada[c].append(razao)

        # attention sink: fracao da massa de atencao no PRIMEIRO token
        if saida.attentions:  # so existe com attn_implementation="eager"
            sinks = []
            for c, att in enumerate(saida.attentions):   # (1, heads, T, T)
                # media sobre heads e sobre queries a partir da 2a posicao
                m = att[0, :, 1:, 0].mean().item()
                sinks.append(m)
            print(f"\n  frase: {frase[:52]!r}...  ({len(ids)} tokens)")
            print(f"    attention no 1o token (media por camada): "
                  f"min {min(sinks):.3f} · mediana {sorted(sinks)[len(sinks)//2]:.3f} · MAX {max(sinks):.3f} "
                  f"(camada {sinks.index(max(sinks))})")

    piores.sort(reverse=True)
    print("\n" + "-" * 78)
    print("MAIORES ATIVACOES (razao |x|max / |x|mediana no mesmo estado oculto)")
    print("-" * 78)
    print(f"  {'razao':>9}  {'camada':>6}  {'dim':>5}  {'|x|max':>10}  {'mediana':>9}  token")
    for razao, c, t, d_i, mx, med in piores[:8]:
        print(f"  {razao:>9.1f}x  {c:>6}  {d_i:>5}  {mx:>10.2f}  {med:>9.4f}  {t!r}")

    pico = piores[0][0]
    dims = {p[3] for p in piores[:12]}
    print("\n" + "=" * 78)
    if pico >= 100:
        print(f"🔴 ATIVACOES MASSIVAS PRESENTES — pico de {pico:.0f}x a mediana.")
        print("   CONSEQUENCIAS PRATICAS:")
        print("   · quantizacao por-TENSOR esta descartada; usar por-CANAL (ou manter fp16 nessas dims)")
        print("   · medir bpb antes/depois de qualquer quantizacao, sem excecao")
    elif pico >= 20:
        print(f"🟡 ativacoes destacadas, mas moderadas — pico de {pico:.0f}x a mediana.")
        print("   Quantizacao por-canal continua sendo a escolha segura; por-tensor exige medir.")
    else:
        print(f"🟢 SEM ativacoes massivas — pico de apenas {pico:.1f}x a mediana.")
        print("   O fenomeno descrito em modelos grandes NAO aparece nesta escala.")
    print(f"   dimensoes envolvidas nos 12 maiores: {sorted(dims)}")
    print(f"   {'⭐ CONCENTRADAS em poucas dims (assinatura do fenomeno)' if len(dims) <= 3 else 'espalhadas por muitas dims — NAO e a assinatura do fenomeno'}")
    print("=" * 78)

    if a.out:
        Path(a.out).write_text(json.dumps({
            "modelo": a.modelo, "rotulo": rotulo, "camadas": n_camadas, "d_model": d,
            "pico_razao": pico, "dims_envolvidas": sorted(dims),
            "top": [{"razao": r, "camada": c, "token": t, "dim": di} for r, c, t, di, _, _ in piores[:8]],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
