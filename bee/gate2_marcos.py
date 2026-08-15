"""GATE 2 do Bee-350M — bpb dos marcos no MESMO holdout que mediu o 150M.

⭐ O QUE ESTE SCRIPT ENTREGA QUE O `holdout_limpo.py` NAO ENTREGA
  Nao e' so' "medir o 350M". E' produzir **pontos PAREADOS**: o mesmo volume de tokens,
  o mesmo texto, o mesmo procedimento, em DOIS tamanhos de modelo. Com 6 marcos em 2 N,
  L(N,D) passa a ser ajustavel **com residuo** — em vez de um ajuste de 3 parametros
  passando por 3 pontos, que descreve e nao valida (licao ja registrada no projeto).

  O 150M ja tem a curva medida (README):
      1B 1,021 · 3B 0,947 · 6B 0,920 · 10B 0,897 · 15B 0,870 · 21B 0,845 · final 0,844

⭐ A GUARDA QUE FAZ ESTE SCRIPT VALER: **HASH DO HOLDOUT**
  A curva do 150M foi medida num texto especifico (parquet 40, 400 docs, 4000 chars, com
  o filtro `qualidade_ok`). Se qualquer coisa mudar — a versao do dataset no HF, a ordem
  das linhas, o filtro — o texto muda e a comparacao vira uma ilusao numerica: dois
  numeros parecidos medidos em coisas diferentes.
  Por isso o holdout e' **hasheado** e o hash e' gravado. Se um dia divergir, o script
  AVISA em vez de deixar a comparacao passar em silencio. E' exatamente o modo de falha
  que este projeto mais paga.

⚠️ RESSALVA HERDADA: bpb deste holdout NAO e' comparavel em absoluto com o do holdout
   [7,23] usado em medicoes antigas — e outro texto. So' vale contra numeros medidos AQUI.

Uso (no pod, depois do treino):
    python bee/gate2_marcos.py --marcos /workspace/bee-350m --final /workspace/bee-350m/modelo
    python bee/gate2_marcos.py --marcos /workspace/bee-350m --so-marcos 1,3   # parcial, durante o run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

# Curva do Bee-150M no MESMO holdout (parquet 40). Fonte: README.md, secao Gate 2.
CURVA_150M = {1: 1.021, 3: 0.947, 6: 0.920, 10: 0.897, 15: 0.870, 21: 0.845}
FINAL_150M = 0.844

# ⭐ O 150M CORRIGIDO vive no HF, NAO em models/bee-150m-v3-base — essa pasta local guarda
# os pesos do v3 BUGADO (o que previa t+2) e mede bpb 2,2284 neste mesmo holdout. Ela serve
# como TOKENIZADOR (e o corpus foi tokenizado com ela, vocab 32k — isso esta correto), mas
# quem a usar como "o Bee-150M" vai medir o modelo errado e nao vai receber aviso nenhum.
# Descoberto ao validar esta regua: o teste de fumaca devolveu 2,2284 em vez de 0,844.
REF_150M = "BrCamp/bee-150m-pt-base"

# Gate declarado ANTES de gastar, em docs/estudo-bee-350m.md §"Gate de sucesso".
ALVO_BPB = 0.80

RIVAIS_PADRAO = (
    "SmolLM2-360M=HuggingFaceTB/SmolLM2-360M,"
    "Qwen3-0.6B=Qwen/Qwen3-0.6B,"
    "Tucano-160m=TucanoBR/Tucano-160m,"
    "SmolLM2-135M=HuggingFaceTB/SmolLM2-135M"
)


def hash_holdout(textos: list[str]) -> str:
    """sha256 do texto do holdout, na ordem. E' a identidade da regua."""
    h = hashlib.sha256()
    for t in textos:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def marcos_em(pasta: Path) -> list[tuple[int, Path]]:
    """Acha marco_1B, marco_3B... e ordena por volume de tokens."""
    achados = []
    for p in sorted(pasta.glob("marco_*")):
        m = re.match(r"marco_(\d+)B$", p.name)
        if m and p.is_dir():
            achados.append((int(m.group(1)), p))
    return sorted(achados)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--marcos", type=Path, required=True, help="pasta com marco_<N>B/")
    ap.add_argument("--final", type=Path, default=None, help="modelo final (opcional)")
    ap.add_argument("--rivais", default=RIVAIS_PADRAO, help="'nome=id,...' ou '' para nenhum")
    ap.add_argument("--so-marcos", default="", help="ex.: 1,3 — mede so' esses (parcial durante o run)")
    ap.add_argument("--parquet-idx", type=int, default=40, help="⚠️ 40 = o que mediu o 150M")
    ap.add_argument("--n-docs", type=int, default=400)
    ap.add_argument("--max-chars", type=int, default=4000)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--sem-ancora", action="store_true",
                    help="pula a remedicao do Bee-150M. ⚠️ so' use se ja' remediu nesta sessao")
    ap.add_argument("--tmp", type=Path, default=ROOT / "_holdout_tmp")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "gate2-350m.json")
    a = ap.parse_args()

    import pyarrow.parquet as pq
    import torch
    from huggingface_hub import hf_hub_download

    from eval_gate2 import bits_por_byte
    from expand_corpus import listar_parquets, qualidade_ok

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    arq = listar_parquets()[a.parquet_idx]

    print("=" * 78)
    print("GATE 2 — Bee-350M nos marcos, contra o 150M no MESMO texto")
    print("=" * 78)
    print(f"  holdout : parquet [{a.parquet_idx}] {arq}")
    print(f"  regra   : {a.n_docs} docs · {a.max_chars} chars · seq {a.seq_len} · {dev}")
    print(f"  alvo    : bpb < {ALVO_BPB} (declarado ANTES de gastar)\n")

    # ---------------------------------------------------------------- holdout
    a.tmp.mkdir(parents=True, exist_ok=True)
    print("  baixando o parquet...", flush=True)
    cam = Path(hf_hub_download("HuggingFaceFW/fineweb-2", arq, repo_type="dataset",
                               local_dir=str(a.tmp)))
    textos: list[str] = []
    vistos = 0
    for lote in pq.ParquetFile(cam).iter_batches(batch_size=2000, columns=["text"]):
        for t in lote.column("text").to_pylist():
            vistos += 1
            if qualidade_ok(t) is None:          # None = o doc PRESTA
                textos.append(t[:a.max_chars])
        if len(textos) >= a.n_docs:
            break
    textos = textos[: a.n_docs]
    nb = sum(len(t.encode("utf-8")) for t in textos)
    h = hash_holdout(textos)
    print(f"  holdout : {len(textos)} docs · {nb/1e6:.2f} MB · de {vistos:,} lidos")
    print(f"  sha256  : {h}")

    # ⭐ GUARDA: a regua e' a mesma de antes?
    ref = ROOT / "docs" / "holdout-hash.txt"
    if ref.exists():
        antigo = ref.read_text(encoding="utf-8").strip()
        if antigo != h:
            print(f"\n🔴 ATENCAO: o holdout MUDOU desde a ultima medicao.")
            print(f"     esperado {antigo}")
            print(f"     obtido   {h}")
            print("   A curva do Bee-150M foi medida no texto ANTIGO. Comparar os dois")
            print("   numeros seria comparar coisas diferentes — a comparacao pareada")
            print("   perde a validade. Investigue antes de usar qualquer resultado.\n",
                  file=sys.stderr)
        else:
            print("  ✅ hash confere com a medicao anterior — comparacao pareada valida")
    else:
        ref.write_text(h, encoding="utf-8")
        print(f"  (primeira medicao — hash gravado em {ref.name})")
    print()

    # ---------------------------------------------------------------- alvos
    filtro = {int(x) for x in a.so_marcos.split(",") if x.strip()} if a.so_marcos else None
    alvos: list[tuple[str, str, int | None]] = []
    for n, p in marcos_em(a.marcos):
        if filtro and n not in filtro:
            continue
        alvos.append((f"Bee-350M @{n}B", str(p), n))
    if a.final and Path(a.final).exists():
        alvos.append(("Bee-350M final", str(a.final), None))
    if not alvos:
        print(f"🔴 nenhum marco encontrado em {a.marcos}", file=sys.stderr)
        return 1
    # ⭐ A ANCORA. Remede o Bee-150M final AGORA, no mesmo texto. E o unico ponto da curva
    # de referencia que ainda pode ser reproduzido — os checkpoints intermediarios do 150M
    # nao existem mais. Se ele nao voltar em 0,844, a tabela inteira do README esta suspeita
    # e a comparacao pareada nao vale. Confiar numa tabela sem poder reconferi-la e' o
    # oposto do que este projeto aprendeu a fazer.
    if not a.sem_ancora:
        alvos.append(("Bee-150M final (âncora)", REF_150M, None))
    for par in filter(None, a.rivais.split(",")):
        nome, _, ident = par.partition("=")
        alvos.append((nome, ident, None))

    # ---------------------------------------------------------------- medir
    res: dict[str, dict] = {}
    for nome, ident, n in alvos:
        print(f"  medindo {nome}...", flush=True)
        try:
            r, fert = bits_por_byte(ident, {"holdout": textos}, a.seq_len, dev)
        except Exception as e:
            print(f"    FALHOU: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        bits, bytes_ = r["holdout"]
        res[nome] = {"bpb": bits / bytes_, "fertilidade": fert, "modelo": ident, "tokens_B": n}

    if not res:
        print("🔴 nenhum modelo mediu", file=sys.stderr)
        return 1

    # ---------------------------------------------------------------- GUARDA DA ANCORA
    anc = res.get("Bee-150M final (âncora)")
    if anc:
        d = anc["bpb"] - FINAL_150M
        print(f"\n  ancora: Bee-150M final remedido = {anc['bpb']:.4f} · "
              f"referencia {FINAL_150M} · dif {d:+.4f}")
        if abs(d) > 0.01:
            print("  🔴 A ANCORA NAO BATE. A curva de referencia do README foi medida em outra")
            print("     condicao (outro texto, outro procedimento ou outro checkpoint). A")
            print("     comparacao pareada abaixo NAO VALE ate isso ser explicado.", file=sys.stderr)
        else:
            print("  ✅ ancora confere — a curva de referencia do 150M e reproduzivel")

    # ---------------------------------------------------------------- a curva pareada
    print("\n" + "=" * 78)
    print("CURVA PAREADA — mesmo texto, mesmo procedimento, dois tamanhos")
    print("=" * 78)
    print(f"  {'tokens':>7} {'Bee-150M':>10} {'Bee-350M':>10} {'ganho':>9}   {'ganho %':>8}")
    pareados = []
    for n in sorted(CURVA_150M):
        k = f"Bee-350M @{n}B"
        if k not in res:
            continue
        b150, b350 = CURVA_150M[n], res[k]["bpb"]
        d = b350 - b150
        pareados.append((n, b150, b350))
        print(f"  {n:>6}B {b150:>10.4f} {b350:>10.4f} {d:>+9.4f} {100*d/b150:>+8.2f}%")

    if len(pareados) >= 2:
        ganhos = [100 * (b3 - b1) / b1 for _, b1, b3 in pareados]
        print(f"\n  ganho medio do 350M sobre o 150M: {sum(ganhos)/len(ganhos):+.2f}%")
        if all(g < 0 for g in ganhos):
            print("  ⭐ o 350M vence em TODOS os marcos pareados — o degrau se pagou")
        elif all(g > 0 for g in ganhos):
            print("  🔴 o 350M PERDE em todos os marcos. Nao e ruido: investigar antes de publicar.")
        else:
            print("  ⚠️ resultado MISTO entre marcos — reportar marco a marco, nunca a media.")

    # ---------------------------------------------------------------- ranking
    print("\n" + "=" * 78)
    print(f"RANKING — bpb no holdout limpo (parquet {a.parquet_idx}). MENOR e melhor.")
    print("=" * 78)
    ordem = sorted(res, key=lambda k: res[k]["bpb"])
    melhor = res[ordem[0]]["bpb"]
    print(f"  {'modelo':<22} {'bpb':>8} {'vs melhor':>10} {'fertilidade':>12}")
    for k in ordem:
        d = res[k]
        marca = "⭐" if k == ordem[0] else "  "
        print(f"{marca}{k:<22} {d['bpb']:>8.4f} {100*(d['bpb']/melhor-1):>+9.1f}% {d['fertilidade']:>12.4f}")

    # ---------------------------------------------------------------- veredito
    final = res.get("Bee-350M final") or res.get(f"Bee-350M @21B")
    print("\n" + "=" * 78)
    if final:
        b = final["bpb"]
        print(f"GATE: bpb {b:.4f} contra alvo {ALVO_BPB} declarado antes de gastar")
        if b < ALVO_BPB:
            print(f"  ✅ PASSOU por {ALVO_BPB - b:.4f}")
        else:
            print(f"  🔴 NAO PASSOU — faltaram {b - ALVO_BPB:.4f}")
            print("     A leitura registrada no plano: se o 350M nao passar de 0,80, o gargalo")
            print("     e' o CORPUS e nao a escala — e isso muda o degrau seguinte.")
        print(f"\n  contra o Bee-150M final ({FINAL_150M}): {100*(b/FINAL_150M-1):+.2f}%")
    else:
        print("GATE: modelo final nao medido (corrida parcial) — sem veredito.")
    print("=" * 78)
    print("\n⚠️ bpb mede o modelo BASE. Fluencia de resposta e uso de ferramenta so' se medem")
    print("   pos-SFT, por EXECUCAO — ver comeia/eval/eval_agentic_exec.py.")

    a.out.write_text(json.dumps({
        "holdout": {"parquet_idx": a.parquet_idx, "parquet": arq, "n_docs": len(textos),
                    "bytes": nb, "sha256": h, "max_chars": a.max_chars, "seq_len": a.seq_len},
        "curva_150m_referencia": CURVA_150M, "final_150m": FINAL_150M,
        "alvo_bpb": ALVO_BPB, "resultados": res,
        "pareados": [{"tokens_B": n, "bee_150m": b1, "bee_350m": b3} for n, b1, b3 in pareados],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrelatorio: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
