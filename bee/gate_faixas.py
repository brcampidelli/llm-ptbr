"""Gate de FAIXAS: filtrar-e-repetir contra passe unico, a tokens vistos IGUAIS.

⭐ POR QUE ESTE GATE EXISTE (2026-09-01)
  O corpus do Bee esta' escrito em tres faixas de qualidade (`corpus_pt/pt_{A,B,C}_*.bin`),
  e a decisao de usar A+B+C veio da razao *"volume vence filtro por ~50x"*. Essa razao
  compara dois numeros — "filtrar a 10% da' +1,6% de bpb" e "o Tucano tem 20x mais token e
  e' 1,88x melhor" — e AMBOS vem de documentos que carregam o banner
  `DOCUMENTO INVALIDO — 2026-08-07` (escada-scaling, gate-corpus-pt-plano, gate-tucano).
  O bug de rotulos foi achado UM DIA depois de o corpus ser construido. Os documentos foram
  invalidados; o corpus que saiu deles nunca foi reexaminado.

  Some-se arXiv:2604.28075 (alemao, 500M documentos, multiplas escalas de modelo e de
  orcamento): **repetir o nucleo duramente filtrado BATE o passe unico num corpus maior e
  menos filtrado**, com a folga persistindo depois de 7 epocas. O gate antigo mediu
  filtrar em PASSE UNICO; ninguem aqui mediu filtrar E REPETIR.

⭐ O DESENHO — o que e' pareado e o que varia
  Varia UMA coisa: qual faixa entra no pool. Tudo o mais e' identico entre bracos:
  mesma arquitetura, mesmo numero de PASSOS, mesmos TOKENS VISTOS, mesmo LR, mesmo
  schedule, mesmas sementes, mesmo holdout.

  Como os pools tem tamanhos diferentes e os tokens vistos sao iguais, o numero de
  EPOCAS difere — e e' exatamente esse o objeto da medicao:

      braco     pool (fracao do total)   epocas a tokens vistos = T
      ABC       1,000                    1,00
      AB        0,543                    1,84
      A         0,176                    5,69

⚠️ ARMADILHAS QUE ESTE SCRIPT DEFENDE

  1. 🔴 **Amostragem COM reposicao mataria o experimento.** O `gate_pareado.py` usa
     `np.random.randint` por lote — em n sorteios a cobertura tende a 63,2% (§2). Num
     gate comum isso e' desperdicio; aqui e' fatal, porque o objeto E' a repeticao
     controlada: o braco de 5,69 epocas veria ~63% da faixa varias vezes, nao a faixa
     inteira 5,69 vezes. Este script permuta blocos NAO-SOBREPOSTOS e reembaralha na
     virada de epoca, e IMPRIME a cobertura — que tem de dar 100% por epoca.

  2. 🔴 **Em que holdout medir** (a armadilha que o gate_pareado ja' documentava). Medir
     na distribuicao CRUA faz o braco cru ganhar de graca; medir na FILTRADA, o inverso.
     O holdout primario e' **Wikipedia em portugues**, fonte que NENHUM braco ve no
     treino. O holdout de fineweb cru vai junto, para mostrar os dois lados.

  3. 🔴 **Convencao de rotulos** (§1): `labels=x`, nunca `labels=y` deslocado. A guarda
     roda com dado REAL antes do passo 1 e ABORTA — com tokens aleatorios ela nao dispara.

  4. ⚠️ **Tres sementes, nao duas** (§2x): duas ALERTAM, tres DECIDEM. O relatorio traz
     media +- desvio, e a folga entre bracos ao lado da amplitude entre sementes.

  5. ⚠️ **A previsao NAO e' monotonica.** arXiv:2305.16264 mede que ate' ~4 epocas de dado
     repetido equivalem a dado unico — o braco A (5,69) esta' FORA dessa faixa. E o
     arXiv:2606.24998 mede que o dano de repeticao PICA em contagem intermediaria. Os tres
     bracos vao juntos justamente porque nenhuma das duas medicoes prediz o mesmo ordenamento.

Uso:
    python bee/gate_faixas.py --preparar --tokens 100e6
    python bee/gate_faixas.py --medir                  # throughput, 40 passos (§3)
    python bee/gate_faixas.py --treinar --sementes 42,43,44
    python bee/gate_faixas.py --avaliar
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

BANDAS = ROOT / "corpus_pt"
BASE = ROOT / "bee" / "gate_faixas"
TOKENIZER = ROOT / "models" / "bee-150m-v3-base"

# Os tres bracos, por quais faixas entram no pool.
BRACOS = {
    "ABC": ("A", "B", "C"),
    "AB": ("A", "B"),
    "A": ("A",),
}


def _tokens_por_faixa() -> dict[str, int]:
    """Conta tokens (uint16) de cada faixa em disco, sem carregar nada."""
    import os
    out = {}
    for f in ("A", "B", "C"):
        arqs = sorted(BANDAS.glob(f"pt_{f}_*.bin"))
        if not arqs:
            raise SystemExit(f"faixa {f}: nenhum arquivo em {BANDAS}")
        out[f] = sum(os.path.getsize(a) for a in arqs) // 2
    return out


# ---------------------------------------------------------------- preparar

def preparar(args) -> int:
    import numpy as np

    BASE.mkdir(parents=True, exist_ok=True)
    tot = _tokens_por_faixa()
    total_geral = sum(tot.values())
    T = int(args.tokens)

    print("=" * 70)
    print("FAIXAS EM DISCO")
    print("=" * 70)
    for f, n in tot.items():
        print(f"  faixa {f}: {n/1e9:6.2f}B tokens")
    print(f"  TOTAL   : {total_geral/1e9:6.2f}B tokens")

    # A fracao f mantem a RAZAO entre os pools. O braco ABC recebe exatamente T.
    frac = T / total_geral
    print(f"\ntokens vistos por braco (T) : {T/1e6:.1f}M")
    print(f"fracao aplicada a cada faixa: {frac:.6f}  (1/{1/frac:.0f})")

    print("\n" + "=" * 70)
    print("POOLS")
    print("=" * 70)
    print(f"{'braco':6} {'faixas':10} {'pool':>12} {'epocas a T':>12}")

    meta = {"tokens_vistos": T, "fracao": frac, "faixas_em_disco": tot, "pools": {}}
    for braco, faixas in BRACOS.items():
        destino = BASE / f"pool_{braco}.bin"
        n_alvo = 0
        if destino.exists() and not args.refazer:
            n_alvo = destino.stat().st_size // 2
            print(f"{braco:6} {'+'.join(faixas):10} {n_alvo/1e6:>10.1f}M "
                  f"{T/n_alvo:>11.2f}  (ja existia)")
        else:
            with open(destino, "wb") as saida:
                for f in faixas:
                    quota_faixa = int(tot[f] * frac)
                    arqs = sorted(BANDAS.glob(f"pt_{f}_*.bin"))
                    # ⭐ fatia proporcional de CADA arquivo, para espalhar pelo corpus
                    # inteiro em vez de pegar so' o comeco de um parquet.
                    por_arq = quota_faixa // len(arqs)
                    for a in arqs:
                        n_disp = a.stat().st_size // 2
                        n = min(por_arq, n_disp)
                        bloco = np.fromfile(a, dtype=np.uint16, count=n)
                        bloco.tofile(saida)
                        n_alvo += len(bloco)
            print(f"{braco:6} {'+'.join(faixas):10} {n_alvo/1e6:>10.1f}M "
                  f"{T/n_alvo:>11.2f}")
        meta["pools"][braco] = {"tokens": n_alvo, "epocas": T / n_alvo,
                                "faixas": list(faixas)}

    # --- holdouts: reusa os do gate anterior (sao TEXTO, imunes ao bug de rotulos)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    print("\n" + "=" * 70)
    print("HOLDOUTS (texto do gate anterior — imune ao bug, e' texto)")
    print("=" * 70)
    for nome in ("wiki", "cru"):
        origem = ROOT / "bee" / "gate" / f"holdout_{nome}.json"
        docs = json.load(open(origem, encoding="utf-8"))
        ids = [tok.encode(d, add_special_tokens=False) for d in docs]
        nb = sum(len(d.encode("utf-8")) for d in docs)
        nt = sum(len(i) for i in ids)
        json.dump({"ids": ids, "bytes": nb, "tokens": nt},
                  open(BASE / f"holdout_{nome}.json", "w"), ensure_ascii=False)
        print(f"  {nome:5}: {len(docs)} docs · {nt:,} tokens · {nb:,} bytes "
              f"· {nt/nb:.4f} tok/byte")
        meta[f"holdout_{nome}"] = {"docs": len(docs), "tokens": nt, "bytes": nb}

    # ⚠️ GUARDA: o holdout wiki tem de ser DISJUNTO dos pools. fineweb-2 e' web crawl e
    # pode conter espelho de Wikipedia. Checagem por 8-grama de token, amostrada.
    print("\n  checando sobreposicao wiki x pool ABC (8-gramas amostrados)...")
    pool = np.fromfile(BASE / "pool_ABC.bin", dtype=np.uint16)
    wiki = json.load(open(BASE / "holdout_wiki.json"))["ids"]
    import random
    random.seed(0)
    grams = set()
    for doc in wiki:
        for _ in range(min(20, max(0, len(doc) - 8))):
            i = random.randrange(0, len(doc) - 8)
            grams.add(tuple(doc[i:i + 8]))
    achados = 0
    passo = 8
    vistos = set()
    for i in range(0, min(len(pool), 40_000_000) - 8, passo):
        vistos.add(tuple(int(x) for x in pool[i:i + 8]))
    achados = len(grams & vistos)
    pct = 100 * achados / max(1, len(grams))
    print(f"  {achados} de {len(grams)} 8-gramas do wiki aparecem no pool = {pct:.2f}%")
    meta["sobreposicao_wiki_pool_pct"] = pct
    if pct > 1.0:
        print("  🔴 AVISO: sobreposicao acima de 1% — o holdout wiki nao e' neutro.")

    json.dump(meta, open(BASE / "meta.json", "w"), indent=2, ensure_ascii=False)
    print(f"\nmeta salvo em {BASE / 'meta.json'}")
    return 0


# ---------------------------------------------------------------- amostrador

class SemReposicao:
    """Permuta blocos NAO-SOBREPOSTOS e percorre ate' o fim; reembaralha na virada.

    ⭐ E' a correcao da §2. `np.random.randint` por lote cobre 63,2% do pool; aqui a
    cobertura e' 100% por epoca, e o script IMPRIME isso.
    """

    def __init__(self, dados, seq_len: int, semente: int):
        import numpy as np
        self.dados = dados
        self.seq_len = seq_len
        self.rng = np.random.default_rng(semente)
        self.n_blocos = (len(dados) - 1) // seq_len
        self.ordem = self.rng.permutation(self.n_blocos)
        self.pos = 0
        self.epocas = 0
        self.blocos_servidos = 0

    def lote(self, tamanho: int):
        import numpy as np
        idx = []
        for _ in range(tamanho):
            if self.pos >= self.n_blocos:
                self.ordem = self.rng.permutation(self.n_blocos)
                self.pos = 0
                self.epocas += 1
            idx.append(self.ordem[self.pos])
            self.pos += 1
            self.blocos_servidos += 1
        return np.stack([self.dados[i * self.seq_len:(i + 1) * self.seq_len] for i in idx])

    @property
    def passes(self) -> float:
        """Quantas vezes o pool foi percorrido (pode passar de 1)."""
        return self.blocos_servidos / max(1, self.n_blocos)

    @property
    def cobertura_distinta(self) -> float:
        """⭐ O NUMERO DA §2: fracao do pool VISTA AO MENOS UMA VEZ.

        Com permutacao cada bloco sai uma unica vez por epoca, entao ate' a primeira
        virada os blocos servidos SAO os distintos. Tem de dar 1,00 em toda rodada
        que complete ao menos uma epoca — contra os 63,2% que `randint` daria.

        ⚠️ NAO confundir com `passes`. Ate' 2026-09-01 o JSON gravava
        `cobertura_por_epoca = passes / epocas_completas`, que dava 1,00/1,84/1,14 nos
        tres bracos e **nao e' cobertura de nada** — campo cujo nome afirmava o que a
        conta nao fazia (§2t). O amostrador sempre esteve correto; o rotulo e' que nao.
        """
        return min(self.blocos_servidos, self.n_blocos) / max(1, self.n_blocos)


# ---------------------------------------------------------------- guarda §1

def guarda_rotulos(modelo, x) -> None:
    """§1: aborta se a convencao de rotulos estiver errada. Com dado REAL."""
    import torch
    import torch.nn.functional as F
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        saida = modelo(input_ids=x[:1], labels=x[:1])
    manual = F.cross_entropy(saida.logits[0, :-1].float(), x[0, 1:]).item()
    dif = abs(saida.loss.item() - manual)
    print(f"  guarda de rotulos: loss {saida.loss.item():.4f} vs manual {manual:.4f} "
          f"(dif {dif:.5f})")
    if dif > 0.01:
        raise SystemExit("🔴 convencao de rotulos ERRADA — abortando antes do passo 1")


# ---------------------------------------------------------------- treinar

def treinar_um(braco: str, semente: int, args) -> dict:
    import dataclasses
    import numpy as np
    import torch
    from transformers import LlamaForCausalLM

    from config import ESCADA, para_llama_config

    torch.manual_seed(semente)
    np.random.seed(semente)

    dados = np.fromfile(BASE / f"pool_{braco}.bin", dtype=np.uint16)
    cfg = dataclasses.replace(ESCADA[args.tamanho], seq_len=args.seq_len)
    modelo = LlamaForCausalLM(para_llama_config(cfg)).cuda()
    n_par = sum(p.numel() for p in modelo.parameters())

    tok_por_passo = args.micro_batch * args.grad_accum * args.seq_len
    passos = args.passos or int(args.tokens // tok_por_passo)
    vistos = passos * tok_por_passo

    print(f"\n{'=' * 70}\nBRACO {braco} · semente {semente}\n{'=' * 70}")
    print(f"  {n_par/1e6:.1f}M params · pool {len(dados)/1e6:.1f}M tokens")
    print(f"  {passos} passos x {tok_por_passo} tok = {vistos/1e6:.1f}M vistos "
          f"= {vistos/len(dados):.2f} epocas")

    amostrador = SemReposicao(dados, args.seq_len, semente)
    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr, betas=(0.9, 0.95),
                            weight_decay=0.1)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=args.lr, total_steps=passos, pct_start=0.02, anneal_strategy="cos")

    modelo.train()
    primeiro = True
    t0 = time.time()
    leituras = []
    for passo in range(passos):
        opt.zero_grad(set_to_none=True)
        perda_acc = 0.0
        for _ in range(args.grad_accum):
            x = torch.from_numpy(amostrador.lote(args.micro_batch).astype(np.int64)).cuda()
            if primeiro:
                guarda_rotulos(modelo, x)
                primeiro = False
            with torch.autocast("cuda", dtype=torch.bfloat16):
                perda = modelo(input_ids=x, labels=x).loss / args.grad_accum
            perda.backward()
            perda_acc += perda.item()
        torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
        opt.step()
        sched.step()
        if passo >= 20 and passo % 20 == 0:
            leituras.append(tok_por_passo * (passo + 1) / (time.time() - t0))
        if passo % 50 == 0 or passo == passos - 1:
            dt = time.time() - t0
            tps = tok_por_passo * (passo + 1) / dt
            print(f"  passo {passo:>5}/{passos} · perda {perda_acc:.4f} · "
                  f"{tps/1000:.1f}k tok/s · {dt/60:.1f} min "
                  f"· ep {amostrador.epocas} cob {amostrador.cobertura_distinta:.2f}", flush=True)

    dest = BASE / f"m_{braco}_s{semente}"
    modelo.save_pretrained(dest)
    r = {"braco": braco, "semente": semente, "passos": passos, "tokens_vistos": vistos,
         "pool_tokens": int(len(dados)), "epocas": vistos / len(dados),
         "cobertura_distinta": amostrador.cobertura_distinta,
         "passes_no_pool": amostrador.passes,
         "epocas_completas": amostrador.epocas, "perda_final": perda_acc,
         "minutos": (time.time() - t0) / 60,
         "tok_s_regime": sorted(leituras)[len(leituras) // 2] if leituras else 0.0}
    json.dump(r, open(BASE / f"treino_{braco}_s{semente}.json", "w"), indent=2)
    return r


def treinar(args) -> int:
    sementes = [int(s) for s in args.sementes.split(",")]
    print(f"bracos {list(BRACOS)} x sementes {sementes} = "
          f"{len(BRACOS) * len(sementes)} runs")
    for semente in sementes:
        for braco in BRACOS:
            if (BASE / f"treino_{braco}_s{semente}.json").exists() and not args.refazer:
                print(f"  {braco} s{semente}: ja rodou, pulando")
                continue
            treinar_um(braco, semente, args)
    return 0


# ---------------------------------------------------------------- avaliar

def bpb(modelo, ids_docs, n_bytes: int, seq_len: int) -> float:
    """bits por byte no holdout. Normaliza por BYTE, nao por token — senao compara
    tokenizadores em vez de modelos."""
    import math
    import torch
    modelo.eval()
    nats = 0.0
    with torch.no_grad():
        for ids in ids_docs:
            for i in range(0, len(ids), seq_len):
                pedaco = ids[i:i + seq_len]
                if len(pedaco) < 2:
                    continue
                x = torch.tensor([pedaco], dtype=torch.long).cuda()
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    perda = modelo(input_ids=x, labels=x).loss
                nats += perda.item() * (len(pedaco) - 1)
    return nats / math.log(2) / n_bytes


def avaliar(args) -> int:
    import statistics
    import torch
    from transformers import LlamaForCausalLM

    hold = {n: json.load(open(BASE / f"holdout_{n}.json")) for n in ("wiki", "cru")}
    sementes = [int(s) for s in args.sementes.split(",")]
    linhas = []
    for braco in BRACOS:
        for semente in sementes:
            d = BASE / f"m_{braco}_s{semente}"
            if not d.exists():
                continue
            m = LlamaForCausalLM.from_pretrained(d, torch_dtype=torch.float32).cuda()
            r = {"braco": braco, "semente": semente}
            for n, h in hold.items():
                r[f"bpb_{n}"] = bpb(m, h["ids"], h["bytes"], args.seq_len)
            t = json.load(open(BASE / f"treino_{braco}_s{semente}.json"))
            r["epocas"] = t["epocas"]
            linhas.append(r)
            print(f"  {braco:4} s{semente}: wiki {r['bpb_wiki']:.4f} · "
                  f"cru {r['bpb_cru']:.4f} · {r['epocas']:.2f} ep")
            del m
            torch.cuda.empty_cache()

    print("\n" + "=" * 70)
    print("RESULTADO — bpb no holdout WIKI (primario; nenhum braco o viu)")
    print("=" * 70)
    print(f"{'braco':6} {'epocas':>7} {'n':>3} {'media':>9} {'dp':>8} {'amplitude':>10}")
    resumo = {}
    for braco in BRACOS:
        v = [x["bpb_wiki"] for x in linhas if x["braco"] == braco]
        if not v:
            continue
        ep = [x["epocas"] for x in linhas if x["braco"] == braco][0]
        dp = statistics.stdev(v) if len(v) > 1 else 0.0
        resumo[braco] = {"media": statistics.mean(v), "dp": dp, "n": len(v),
                         "amplitude": max(v) - min(v), "epocas": ep, "valores": v}
        print(f"{braco:6} {ep:>7.2f} {len(v):>3} {statistics.mean(v):>9.4f} "
              f"{dp:>8.4f} {max(v)-min(v):>10.4f}")

    if "ABC" in resumo:
        base = resumo["ABC"]["media"]
        print(f"\nfolga contra o controle ABC (negativo = MELHOR, bpb menor e' melhor):")
        for braco, r in resumo.items():
            if braco == "ABC":
                continue
            d = 100 * (r["media"] - base) / base
            amp = max(resumo["ABC"]["amplitude"], r["amplitude"])
            marca = "⭐" if abs(d) > 100 * amp / base else "⚠️ dentro da amplitude"
            print(f"  {braco:4}: {d:+6.2f}%   {marca}")

    json.dump({"linhas": linhas, "resumo": resumo},
              open(BASE / "resultado.json", "w"), indent=2, ensure_ascii=False)
    print(f"\nsalvo em {BASE / 'resultado.json'}")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--medir", action="store_true", help="40 passos, le throughput (§3)")
    ap.add_argument("--treinar", action="store_true")
    ap.add_argument("--avaliar", action="store_true")
    ap.add_argument("--tokens", type=float, default=100e6, help="tokens VISTOS por braco")
    ap.add_argument("--tamanho", default="150m")
    ap.add_argument("--seq-len", type=int, default=512)
    ap.add_argument("--micro-batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=32)
    ap.add_argument("--passos", type=int, default=0, help="0 = derivado de --tokens")
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--sementes", default="42,43,44")
    ap.add_argument("--refazer", action="store_true")
    args = ap.parse_args()

    if args.preparar:
        return preparar(args)
    if args.medir:
        args.passos = 40
        r = treinar_um("A", 42, args)
        tps = r["tok_s_regime"]
        print(f"\n{'='*70}\nTHROUGHPUT EM REGIME: {tps/1000:.1f}k tok/s")
        n_runs = len(BRACOS) * len(args.sementes.split(","))
        h = args.tokens * n_runs / tps / 3600
        print(f"{n_runs} runs x {args.tokens/1e6:.0f}M tokens = {h:.1f} h no total")
        return 0
    if args.treinar:
        return treinar(args)
    if args.avaliar:
        return avaliar(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
