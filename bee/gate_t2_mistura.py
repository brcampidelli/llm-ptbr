"""Gate T2 — a mistura multilingue ajuda ou machuca o PORTUGUES?

O Gate T1 decidiu o tokenizador (`64k-multi`). Este decide a MISTURA: quanto do orcamento de
tokens vai para o portugues, que e' a capacidade que o projeto tem hoje.

    braco       PT no total   os outros 7
    bal-12      12,5%         12,5% cada (mistura uniforme)
    pt-25       25,0%         10,7% cada
    pt-50       50,0%          7,1% cada

⭐ POR QUE ESTE GATE E' VALIDO ONDE O T1 PRECISOU DE CUIDADO. No T1 os bracos tinham vocabularios
   diferentes, entao tokens/parametro DIFERIA entre eles (0,59 contra 0,53) e isso virou um vies.
   Aqui o tokenizador, a arquitetura e o total de tokens sao IDENTICOS em todos os bracos: so' a
   PROPORCAO muda. tokens/parametro e' igual, e a comparacao de bpb PT entre bracos e' direta —
   mesma coluna, mesmo tokenizador, mesmos itens de holdout (§2g).

🔴 O QUE ESTE GATE NAO MOSTRA, e vai escrito no artefato:
   · mede bpb, nao capacidade. O E2 mediu que sao coisas diferentes.
   · mede a 150M params e ~1,3 tok/param. O Bee-1G treina em 20-170 tok/param, e o proprio
     projeto mediu em 2026-09-03 que a folga entre bracos ENCOLHE quando o treino cresce —
     entao efeitos medidos aqui sao um TETO, nao o valor no modelo final.
   · o braco `pt-50` e' o limite do corpus: 110M tokens de PT contra 157M disponiveis. Nao ha'
     braco 100% PT, e um seria repeticao (220M pedidos contra 157M existentes).

🔴 VAZAMENTO — a guarda que este gate PRECISA ter. O PT extra veio de um stream NOVO do
   fineweb-2, e o holdout do T1 tambem saiu de fineweb-2 PT. Documento repetido entre os dois
   nao daria erro nenhum: entraria no treino, sairia no holdout, e o bpb do braco com mais PT
   ficaria artificialmente bom — exatamente o braco cuja vantagem se quer medir.
   ✅ O filtro `sha1(texto) % 100 < 2` e' por CONTEUDO, nao por posicao: aplicado ao corpus novo
   ele remove qualquer documento que cairia no holdout, inclusive uma copia identica vinda de
   outro shard. O gate reporta quantos foram removidos — se der zero, a guarda esta' inerte e o
   numero nao vale (§2t).

Uso:
    python bee/gate_t2_mistura.py preparar --pool-tokens 250000000
    python bee/gate_t2_mistura.py treinar  --sementes 42,43,44 --passos 6700
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_t1_bpb as T1  # noqa: E402
from gate_t1_bpb import IDIOMAS, HOLDOUT_PCT, _no_holdout, caminho  # noqa: E402

# 🔴🔴 MEDIDO 2026-09-03, e custou um pool inteiro: `_no_holdout` e' PORTUGUES — significa
# "[o documento esta'] NO holdout" e devolve True para quem DEVE ficar de fora do treino.
# Eu li como o ingles "no holdout" = "nao e' holdout", inverti a condicao, e montei os pools de
# TREINO a partir do HOLDOUT. Nada daria erro: o treino rodaria, a loss cairia, e o bpb sairia
# absurdamente bom porque o modelo teria visto exatamente o texto da avaliacao.
# O alias abaixo existe para que a polaridade seja impossivel de reler errado no ponto de uso.
esta_no_holdout = _no_holdout

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "bee" / "gate_t2_mistura"
CORPUS = ROOT / "bee" / "corpus_multi"
# Corpora coletados em 2026-09-03 para destravar o T2. MEDIDO: o `corpus_multi` original tinha
# so' 23,5M tokens de espanhol (o idioma que limita), e o braco `bal-12` precisa de pool/8 de
# CADA idioma. A guarda de mistura efetiva (§2r) pegou isso — os bracos teriam sido rotulados
# `bal-12` com a mistura real por 14,1% / spa 10,6% / ... e o gate mediria outra proporcao.
_EXTRA_PT = ROOT / "bee" / "corpus_pt_extra"        # 500 Mcar -> ~122M tokens
_EXTRA_MULTI = ROOT / "bee" / "corpus_multi_extra"  # 300 Mcar por idioma, os outros 7
CORPUS_EXTRA = {c: (_EXTRA_PT if c == "por" else _EXTRA_MULTI) for c in IDIOMAS}

TOKENIZADOR = "bee/tok_t1/64k-multi"   # decidido no Gate T1 (t=-0,61 contra 96k, e -9,6% de custo)

# fracao do orcamento de tokens que cada braco da' ao portugues; o resto e' dividido igualmente
# entre os outros 7. `bal-12` = 1/8, a mistura uniforme.
MISTURAS = {"bal-12": 0.125, "pt-25": 0.25, "pt-50": 0.50}


def pesos(fr_pt: float) -> dict[str, float]:
    outros = (1.0 - fr_pt) / (len(IDIOMAS) - 1)
    return {c: (fr_pt if c == "por" else outros) for c in IDIOMAS}


def docs_de(cod: str, so_treino: bool = True):
    """Documentos de um idioma, do corpus base MAIS o extra, ja' filtrados contra o holdout.

    ⚠️ A ORDEM importa para a reprodutibilidade: shards do corpus base primeiro, extras depois,
    ambos em ordem alfabetica. Sem isso dois `preparar` da mesma config montariam pools
    diferentes e nada disto seria comparavel.
    """
    pastas = [CORPUS] + ([CORPUS_EXTRA[cod]] if cod in CORPUS_EXTRA else [])
    for pasta in pastas:
        for shard in sorted(glob.glob(str(pasta / f"bee_corpus_{cod}_*.jsonl.zst"))):
            import zstandard as zstd
            bruto = zstd.ZstdDecompressor().decompress(open(shard, "rb").read()).decode("utf-8")
            for linha in bruto.splitlines():
                if not linha.strip():
                    continue
                t = json.loads(linha).get("text") or ""
                if not t:
                    continue
                if so_treino and esta_no_holdout(t):
                    yield None          # sinaliza "descartado por PERTENCER ao holdout"
                    continue
                yield t


def cmd_preparar(args) -> int:
    import numpy as np
    from transformers import AutoTokenizer

    BASE.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(caminho(TOKENIZADOR))
    vocab = len(tok)
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    print(f"tokenizador {TOKENIZADOR} · vocab {vocab:,}")

    meta = {"_gate": "T2 — mistura multilingue", "tokenizador": TOKENIZADOR,
            "vocab": vocab, "pool_tokens": args.pool_tokens, "bracos": {}}

    for nome, fr in MISTURAS.items():
        p = BASE / f"pool_{nome}.bin"
        if p.exists() and not args.refazer:
            print(f"  {nome}: pool ja' existe, pulando")
            continue
        w = pesos(fr)
        cota = {c: int(args.pool_tokens * w[c]) for c in IDIOMAS}
        print(f"\n{nome}: PT {100*fr:.1f}% · cota por idioma "
              + " ".join(f"{c} {cota[c]/1e6:.0f}M" for c in IDIOMAS))

        t0 = time.time()
        obtido = {c: 0 for c in IDIOMAS}
        descartados = {c: 0 for c in IDIOMAS}
        docs = {c: 0 for c in IDIOMAS}
        n_total, max_id = 0, 0
        tmp = p.with_suffix(".bin.tmp")
        buf: list[int] = []

        with open(tmp, "wb") as fh:
            def descarrega():
                nonlocal buf, n_total, max_id
                if not buf:
                    return
                a = np.asarray(buf, dtype=np.uint32)   # uint32 SEMPRE (§ wrap silencioso do T1)
                max_id = max(max_id, int(a.max()))
                a.tofile(fh)
                n_total += len(a)
                buf = []

            for c in IDIOMAS:
                for t in docs_de(c):
                    if t is None:
                        descartados[c] += 1
                        continue
                    if obtido[c] >= cota[c]:
                        break
                    ids = tok(t, add_special_tokens=False)["input_ids"]
                    buf.extend(ids)
                    buf.append(eos)
                    obtido[c] += len(ids) + 1
                    docs[c] += 1
                    if len(buf) >= args.descarga:
                        descarrega()
                descarrega()
                # 🔴 A TAXA DE DESCARTE E' A GUARDA DIRETA DA POLARIDADE. O filtro deve tirar
                # ~HOLDOUT_PCT% dos documentos; se tirar 98%, ele esta' invertido e o pool sai
                # do holdout. A guarda de mistura (§2r) chegou a pegar isso, mas por um sintoma
                # — cota nao atingida — e nomeando a causa errada ("reduza --pool-tokens").
                vistos = docs[c] + descartados[c]
                taxa = 100 * descartados[c] / max(1, vistos)
                # ⚠️ Limite dos DOIS lados: `abs(taxa - PCT) > 3*PCT` pegava o caso invertido
                # (98%) e DEIXAVA PASSAR o filtro morto (0%), porque |0-2| = 2 < 6. Com 1000
                # documentos vistos o esperado e' 20 descartes (dp ~4,4), entao a faixa
                # [PCT/3, PCT*3] esta' a muitos desvios de qualquer flutuacao real.
                if vistos > 1000 and not (HOLDOUT_PCT / 3 <= taxa <= HOLDOUT_PCT * 3):
                    raise SystemExit(
                        f"🔴 {c}: o filtro descartou {taxa:.1f}% dos documentos, e o holdout e' "
                        f"{HOLDOUT_PCT}%. A polaridade de `esta_no_holdout` esta' invertida — "
                        f"com {taxa:.0f}% de descarte o pool de TREINO sairia do HOLDOUT.")
                print(f"    {c}: {obtido[c]/1e6:>6.1f}M tok de {cota[c]/1e6:>5.1f}M pedidos "
                      f"({100*obtido[c]/max(1,cota[c]):>5.1f}%) · {docs[c]:,} docs · "
                      f"{descartados[c]:,} descartados pelo filtro de holdout", flush=True)

        if max_id >= vocab:
            raise SystemExit(f"🔴 {nome}: id {max_id} >= vocab {vocab}")
        os.replace(tmp, p)
        conf = np.fromfile(p, dtype=np.uint32)
        if len(conf) != n_total:
            raise SystemExit(f"🔴 {nome}: arquivo {len(conf)} != {n_total} tokens")

        # 🔴 §2r — QUANTO A MISTURA REALMENTE AGIU. O rotulo do braco e' uma INTENCAO; se um
        # idioma acabar antes da cota, a mistura efetiva e' outra e o nome passa a mentir.
        real = {c: obtido[c] / max(1, n_total) for c in IDIOMAS}
        pior = max(abs(real[c] - w[c]) for c in IDIOMAS)
        print(f"    mistura EFETIVA: " + " ".join(f"{c} {100*real[c]:.1f}%" for c in IDIOMAS))
        print(f"    maior desvio do alvo: {100*pior:.2f} pp", end="")
        if pior > args.tol_mistura:
            raise SystemExit(f"\n🔴 {nome}: mistura efetiva desviou {100*pior:.2f} pp do alvo "
                             f"(teto {100*args.tol_mistura:.2f}). Algum idioma acabou antes da "
                             f"cota — o rotulo do braco mentiria. Reduza --pool-tokens.")
        print("  ✅")

        # 🔴 §2t — a guarda de vazamento nao pode estar INERTE. Se ela nao descartou nada, ou
        # o corpus e' minusculo ou o filtro nao rodou; nos dois casos o numero nao vale.
        if sum(descartados.values()) == 0:
            raise SystemExit("🔴 o filtro de holdout nao descartou NENHUM documento — ele nao "
                             "rodou, e o bpb ficaria contaminado sem dar erro nenhum.")

        meta["bracos"][nome] = {"fr_pt_alvo": fr, "pool_tokens": n_total,
                                "mistura_alvo": w, "mistura_efetiva": real,
                                "docs": docs, "descartados_holdout": descartados,
                                "maior_desvio_pp": 100 * pior,
                                "minutos": (time.time() - t0) / 60}
        tmpm = BASE / "meta.json.tmp"
        tmpm.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        tmpm.replace(BASE / "meta.json")   # grava a CADA braco (licao de 2026-09-02/03)

    print(f"\nmeta: {BASE / 'meta.json'}")
    return 0



def _liga_t1(args):
    """Aponta a maquinaria do Gate T1 para os pools do T2.

    ⭐ REAPROVEITAR em vez de reescrever: o `treinar_um` do T1 carrega a guarda de rotulos
    (§1, que aborta antes do passo 1), o amostrador SEM REPOSICAO com cobertura reportada (§2),
    a leitura de throughput em regime (§3) e o `avaliar` com a regua canonica e o nome de saida
    derivado da config (§2z). Escrever tudo de novo aqui seria escrever tudo de novo ERRADO.

    ⚠️ Aqui os "bracos" sao MISTURAS, nao tokenizadores — todos apontam para o MESMO
    tokenizador. E' exatamente por isso que este gate e' mais limpo que o T1: tokens/parametro
    e' identico entre os bracos.
    """
    T1.BASE = BASE
    T1.BRACOS = {nome: TOKENIZADOR for nome in MISTURAS}
    T1.CONTROLE = "bal-12"          # a mistura uniforme e' a referencia natural
    return T1


def _garante_holdout():
    """Escreve o holdout do T2 — e ele e' o MESMO do T1, de proposito.

    🔴 O `textos()` do T1 le' so' de `corpus_multi`, nao dos corpora extras coletados hoje.
    Isso e' o que se quer: o holdout tem de ser identico ao do T1 para que os numeros dos dois
    gates sejam comparaveis (§2g, "mesmos itens?"). Os extras entram so' no TREINO, e ja'
    passaram pelo filtro `esta_no_holdout` documento a documento.
    """
    alvo = BASE / "holdout.json"
    if alvo.exists():
        return
    hold = {c: list(T1.textos(c, "holdout", 1_500_000)) for c in IDIOMAS}
    for c in IDIOMAS:
        nb = sum(len(t.encode("utf-8")) for t in hold[c])
        print(f"  holdout {c}: {len(hold[c]):>5} docs · {nb/1e6:.2f} MB")
    alvo.write_text(json.dumps(hold, ensure_ascii=False), encoding="utf-8")


def cmd_treinar(args) -> int:
    t1 = _liga_t1(args)
    m = json.loads((BASE / "meta.json").read_text(encoding="utf-8"))
    for nome in m["bracos"]:                      # o treinar_um do T1 le' o vocab daqui
        m["bracos"][nome]["vocab"] = m["vocab"]
    (BASE / "meta.json").write_text(json.dumps(m, indent=2, ensure_ascii=False),
                                    encoding="utf-8")
    return t1.treinar(args)


def cmd_avaliar(args) -> int:
    t1 = _liga_t1(args)
    _garante_holdout()
    return t1.avaliar(args)


def main() -> int:
    from config import ESCADA
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("--pool-tokens", type=int, default=250_000_000)
    p.add_argument("--descarga", type=int, default=8_000_000)
    p.add_argument("--tol-mistura", type=float, default=0.01,
                   help="desvio maximo da mistura efetiva em relacao ao alvo (fracao)")
    p.add_argument("--refazer", action="store_true")
    p.set_defaults(fn=cmd_preparar)

    t = sub.add_parser("treinar")
    t.add_argument("--bracos", default="")
    t.add_argument("--sementes", default="42,43,44")
    t.add_argument("--tokens", type=int, default=0)
    t.add_argument("--passos", type=int, default=6700)
    t.add_argument("--seq-len", type=int, default=2048)
    t.add_argument("--micro-batch", type=int, default=4)
    t.add_argument("--grad-accum", type=int, default=4)
    t.add_argument("--lr", type=float, default=3e-3)
    t.add_argument("--refazer", action="store_true")
    t.add_argument("--escala", default="150m", choices=list(ESCADA),
                   help="150m e' o T2 original; 350m e' o braco de TRANSFERENCIA (#6)")
    t.set_defaults(fn=cmd_treinar)

    a = sub.add_parser("avaliar")
    a.add_argument("--bracos", default="")
    a.add_argument("--sementes", default="42,43,44")
    a.add_argument("--seq-len", type=int, default=2048)
    a.add_argument("--bytes-holdout", type=int, default=1_500_000)
    a.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda")
    a.add_argument("--escala", default="150m", choices=list(ESCADA))
    a.set_defaults(fn=cmd_avaliar)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
