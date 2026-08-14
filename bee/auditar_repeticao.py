"""Auditoria de REPETICAO INTERNA do corpus — o quarto membro da familia de falhas silenciosas.

⭐ POR QUE ESTE SCRIPT EXISTE
  arXiv:2606.24998 (*Internal Data Repetition Destroys Language Models*), medido num modelo de
  **344M** — o tamanho exato do Bee-350M: quando documentos repetidos consomem **10% do orcamento
  de FLOPs**, o resultado equivale a treinar SEM repeticao usando so **67% dos FLOPs**. Um terco
  da computacao perdido, e **nada no log reclama**.

  E o dano **nao e monotono**: tem PICO em contagem INTERMEDIARIA (documento repetido 3-10x
  machuca mais que repetido 1000x ou 2x). Por isso a saida deste script e um **HISTOGRAMA**, e
  nao uma taxa media — a taxa media esconde exatamente a faixa que mais dói.

⭐ POR QUE MEDIR NO CORPUS TOKENIZADO, E NAO NA FONTE
  `bee/medir_dedup.py` estima por AMOSTRA de dois parquets do fineweb-2. Este script e' um
  **CENSO**: le o `train.bin` que o treino vai efetivamente consumir. Se alguma duplicata entrou
  na juncao, na expansao ou na retokenizacao, ela aparece aqui e nao apareceria na fonte.
  Bonus: sem download, sem rate-limit, e o eixo de peso ja e' o certo (tokens == FLOPs, por 6ND).

⭐ DUAS CAMADAS, com honestidade sobre o que cada uma mede
  T1 EXATO      — hash de 64 bits da sequencia INTEIRA de tokens do documento. Censo, exato,
                  barato. Responde: quantos tokens estao em documentos byte-identicos repetidos?
  T2 QUASE-DUP  — MinHash bottom-k sobre 5-gramas de TOKEN + LSH por bandas. Censo, aproximado.
                  Responde: quantos tokens estao em documentos ~iguais (Jaccard >= limiar)?
                  Pega o boilerplate juridico e o portal que republica a mesma materia com outro
                  cabecalho — que e' o perfil de web PT-BR e a razao de o dano ser intermediario.

⚠️ GUARDAS (o script aborta em vez de reportar numero errado — licao propria)
  - a soma dos tokens dos documentos + separadores tem de bater com o tamanho do arquivo;
  - o numero de documentos tem de bater com a contagem de EOS;
  - qualquer divergencia acima de 0,01% aborta. Um censo que perde documento nao e' censo.

Uso:
    python bee/auditar_repeticao.py --limite-tokens 500_000_000   # piloto, ~minutos
    python bee/auditar_repeticao.py                                # censo completo
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- hashing

_B = np.uint64(0x100000001B3)  # base do rolling hash (primo do FNV)


def _mix(h: np.ndarray) -> np.ndarray:
    """splitmix64 finalizer — espalha os bits. Sem ele, n-gramas parecidos colidem em faixas."""
    h = h ^ (h >> np.uint64(30))
    h = h * np.uint64(0xBF58476D1CE4E5B9)
    h = h ^ (h >> np.uint64(27))
    h = h * np.uint64(0x94D049BB133111EB)
    return h ^ (h >> np.uint64(31))


def hashes_de_ngramas(toks: np.ndarray, n: int = 5) -> np.ndarray:
    """Hash rolante de todos os n-gramas de TOKEN. Vetorizado; overflow de uint64 e' o mod."""
    if len(toks) < n:
        return np.empty(0, dtype=np.uint64)
    x = toks.astype(np.uint64)
    m = len(x) - n + 1
    h = np.zeros(m, dtype=np.uint64)
    for j in range(n):
        h = h * _B + x[j : j + m]
    return _mix(h)


def hash_do_documento(toks: np.ndarray) -> np.uint64:
    """Hash da sequencia INTEIRA — identidade exata do documento (T1)."""
    if len(toks) == 0:
        return np.uint64(0)
    x = toks.astype(np.uint64)
    # Merkle-ish: dobra o vetor ate sobrar um valor. Vetorizado, sem laco por token.
    h = _mix(x * _B + np.uint64(len(x)))
    while len(h) > 1:
        if len(h) % 2:
            h = np.append(h, np.uint64(0x9E3779B97F4A7C15))
        h = _mix(h[0::2] * _B + h[1::2])
    return np.uint64(h[0])


# ---------------------------------------------------------------- leitura

def percorrer_documentos(caminho: Path, eos: int, limite: int | None, chunk: int = 1 << 26):
    """Gera (tokens_do_documento,) em ordem, sem carregar 41 GB na RAM.

    Documento = trecho entre separadores EOS. O ultimo pedaco de cada chunk que nao terminou em
    EOS e' carregado para o chunk seguinte (senao um documento partido viraria dois, e a contagem
    de repeticao ficaria errada por construcao).
    """
    arr = np.memmap(caminho, dtype=np.uint16, mode="r")
    total = len(arr) if limite is None else min(limite, len(arr))
    resto = np.empty(0, dtype=np.uint16)
    lidos = 0
    while lidos < total:
        fim = min(lidos + chunk, total)
        bloco = np.asarray(arr[lidos:fim])
        lidos = fim
        if len(resto):
            bloco = np.concatenate([resto, bloco])
        cortes = np.flatnonzero(bloco == eos)
        ini = 0
        for c in cortes:
            yield bloco[ini:c]
            ini = c + 1
        resto = bloco[ini:].copy()
    if len(resto):
        yield resto


# ---------------------------------------------------------------- T2: sketches

def sketch_bottom_k(hs: np.ndarray, k: int) -> np.ndarray:
    """Bottom-k MinHash: os k menores hashes de n-grama. Estimador nao-viesado de Jaccard."""
    if len(hs) == 0:
        return np.full(k, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    if len(hs) <= k:
        s = np.sort(hs)
        return np.concatenate([s, np.full(k - len(s), np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)])
    return np.sort(np.partition(hs, k)[:k])


class UnionFind:
    def __init__(self, n: int):
        self.pai = np.arange(n, dtype=np.int64)

    def raiz(self, a: int) -> int:
        p = self.pai
        while p[a] != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def unir(self, a: int, b: int) -> None:
        ra, rb = self.raiz(a), self.raiz(b)
        if ra != rb:
            self.pai[max(ra, rb)] = min(ra, rb)


# ---------------------------------------------------------------- histograma

FAIXAS = [(1, 1), (2, 2), (3, 10), (11, 100), (101, 1000), (1001, 10**12)]
ROTULOS = ["1 (unico)", "2", "3-10  ⚠️ PICO DO DANO", "11-100", "101-1000", ">1000"]


def histograma(tam_grupo: np.ndarray, tokens_doc: np.ndarray, total_tokens: int) -> list[dict]:
    linhas = []
    for (lo, hi), rot in zip(FAIXAS, ROTULOS):
        sel = (tam_grupo >= lo) & (tam_grupo <= hi)
        tk = int(tokens_doc[sel].sum())
        linhas.append(
            {
                "faixa": rot,
                "documentos": int(sel.sum()),
                "tokens": tk,
                "pct_tokens": round(100.0 * tk / max(total_tokens, 1), 3),
            }
        )
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default=str(ROOT / "dados_pt_22b" / "train.bin"))
    ap.add_argument("--meta", default=str(ROOT / "dados_pt_22b" / "meta.json"))
    ap.add_argument("--limite-tokens", type=int, default=None, help="piloto: so os N primeiros tokens")
    ap.add_argument("--k", type=int, default=16, help="tamanho do sketch bottom-k")
    ap.add_argument("--bandas", type=int, default=4, help="bandas do LSH (k deve dividir)")
    ap.add_argument("--limiar", type=float, default=0.8, help="Jaccard minimo para quase-duplicata")
    ap.add_argument("--min-tokens", type=int, default=50, help="documentos menores nao entram no T2")
    ap.add_argument("--out", default=str(ROOT / "docs" / "auditoria-repeticao.json"))
    a = ap.parse_args()

    if a.k % a.bandas:
        print(f"ERRO: k={a.k} nao e' divisivel por bandas={a.bandas}", file=sys.stderr)
        return 2

    meta = json.loads(Path(a.meta).read_text(encoding="utf-8"))
    eos = int(meta.get("eos", 0))
    caminho = Path(a.bin)
    tokens_arquivo = caminho.stat().st_size // 2
    alvo = tokens_arquivo if a.limite_tokens is None else min(a.limite_tokens, tokens_arquivo)

    print(f"corpus:  {caminho}")
    print(f"tokens:  {tokens_arquivo:,} ({tokens_arquivo/1e9:.2f}B)   alvo desta corrida: {alvo:,}")
    print(f"EOS={eos}  k={a.k}  bandas={a.bandas}  limiar Jaccard={a.limiar}")
    print("-" * 78)

    t0 = time.time()
    # ⚠️ arrays PRE-ALOCADOS e crescidos por dobra: uma lista de 15,6M arrays de 16 uint64
    # gastaria ~4 GB so em overhead de objeto numpy (128 B de dado, ~230 B de cabecalho).
    cap = 1 << 20
    hx = np.empty(cap, dtype=np.uint64)
    sk = np.empty((cap, a.k), dtype=np.uint64)
    tam = np.empty(cap, dtype=np.int64)
    VAZIO = np.full(a.k, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    n_doc = 0
    tokens_vistos = 0

    for toks in percorrer_documentos(caminho, eos, alvo):
        if n_doc == cap:
            cap *= 2
            hx = np.resize(hx, cap)
            sk = np.resize(sk, (cap, a.k))
            tam = np.resize(tam, cap)
        L = len(toks)
        tokens_vistos += L
        tam[n_doc] = L
        hx[n_doc] = hash_do_documento(toks)
        sk[n_doc] = sketch_bottom_k(hashes_de_ngramas(toks), a.k) if L >= a.min_tokens else VAZIO
        n_doc += 1
        if n_doc % 1_000_000 == 0:
            dt = time.time() - t0
            frac = tokens_vistos / alvo
            print(
                f"  {n_doc:>10,} docs · {tokens_vistos/1e9:6.3f}B tok · {dt/60:5.1f} min"
                f" · resta ~{dt*(1-frac)/max(frac,1e-9)/60:5.1f} min",
                flush=True,
            )

    hx, sk, tam = hx[:n_doc], sk[:n_doc], tam[:n_doc]

    # ---- GUARDA: o censo tem de fechar. Um censo que perde documento nao e' censo.
    esperado = tokens_vistos + n_doc  # cada documento consumiu um separador EOS
    erro = abs(esperado - alvo) / max(alvo, 1)
    print("-" * 78)
    print(f"documentos: {n_doc:,}   tokens em documentos: {tokens_vistos:,}")
    print(f"guarda de fechamento: {esperado:,} vs {alvo:,}  (erro {erro*100:.4f}%)")
    if erro > 1e-4:
        print("🔴 ABORTA: a contagem nao fecha — o particionamento por EOS esta errado.", file=sys.stderr)
        return 3
    print("✅ censo fecha.")

    # ---------------- T1: duplicata EXATA
    _, inv, cont = np.unique(hx, return_inverse=True, return_counts=True)
    grupo_exato = cont[inv]
    h_exato = histograma(grupo_exato, tam, tokens_vistos)

    # ---------------- T2: quase-duplicata (LSH por bandas + verificacao por Jaccard)
    por_banda = a.k // a.bandas
    uf = UnionFind(n_doc)
    pares_testados = 0
    for b in range(a.bandas):
        faixa = sk[:, b * por_banda : (b + 1) * por_banda]
        chave = np.zeros(n_doc, dtype=np.uint64)
        for c in range(por_banda):
            chave = _mix(chave * _B + faixa[:, c])
        ordem = np.argsort(chave, kind="stable")
        ch = chave[ordem]
        # ⚠️ NAO usar np.split: com 15,6M documentos ele cria 15M arrays, quase todos de
        # tamanho 1. Percorrer so os baldes com 2+ membros e' ~100x mais barato.
        ini_grp = np.concatenate([[0], np.flatnonzero(np.diff(ch)) + 1, [len(ch)]])
        tams = np.diff(ini_grp)
        for idx in np.flatnonzero(tams >= 2):
            i0, i1 = ini_grp[idx], ini_grp[idx + 1]
            if i1 - i0 > 5000:  # balde gigante = boilerplate; nao explodir O(n^2)
                continue
            grp = ordem[i0:i1]
            base = int(grp[0])
            sb = sk[base]
            for outro in grp[1:]:
                pares_testados += 1
                inter = np.intersect1d(sb, sk[outro], assume_unique=False).size
                if inter / a.k >= a.limiar:
                    uf.unir(base, int(outro))

    raizes = np.array([uf.raiz(i) for i in range(n_doc)], dtype=np.int64)
    _, inv2, cont2 = np.unique(raizes, return_inverse=True, return_counts=True)
    grupo_quase = cont2[inv2]
    h_quase = histograma(grupo_quase, tam, tokens_vistos)

    # ---------------- relatorio
    def imprimir(titulo: str, linhas: list[dict]) -> None:
        print()
        print(titulo)
        print(f"  {'faixa':<24} {'documentos':>12} {'tokens':>16} {'% tokens':>9}")
        for l in linhas:
            print(f"  {l['faixa']:<24} {l['documentos']:>12,} {l['tokens']:>16,} {l['pct_tokens']:>8.3f}%")

    imprimir("T1 — DUPLICATA EXATA (censo exato)", h_exato)
    imprimir(f"T2 — QUASE-DUPLICATA (Jaccard >= {a.limiar}, censo aproximado)", h_quase)

    pct_rep_exato = 100.0 * float(tam[grupo_exato >= 2].sum()) / max(tokens_vistos, 1)
    pct_rep_quase = 100.0 * float(tam[grupo_quase >= 2].sum()) / max(tokens_vistos, 1)
    pct_pico = 100.0 * float(tam[(grupo_quase >= 3) & (grupo_quase <= 10)].sum()) / max(tokens_vistos, 1)

    print()
    print("=" * 78)
    print(f"FRACAO DOS FLOPs em documentos repetidos:  exato {pct_rep_exato:.2f}%"
          f"   ·   quase-dup {pct_rep_quase:.2f}%")
    print(f"FRACAO na faixa 3-10x (o PICO do dano):    {pct_pico:.2f}%")
    print()
    if pct_rep_quase >= 10:
        print("🔴 >=10% dos FLOPs em repetidos — e' o cenario medido no paper (ate 33% de compute")
        print("   perdido). DEDUPAR ANTES do run. Retorno potencial: ate ~US$ 100 dos US$ 300.")
    elif pct_rep_quase >= 3:
        print("🟡 repeticao moderada. Dedupar e' barato e o dano cresce com o tamanho do modelo —")
        print("   o paper mede lei de potencia em N. Recomendado dedupar.")
    else:
        print("🟢 repeticao baixa. O corpus nao e' o gargalo por este eixo; nao gastar tempo aqui.")
    print("=" * 78)

    saida = {
        "corpus": str(caminho),
        "tokens_analisados": int(tokens_vistos),
        "documentos": int(n_doc),
        "tokens_por_doc_medio": round(tokens_vistos / max(n_doc, 1), 1),
        "parametros": {"k": a.k, "bandas": a.bandas, "limiar": a.limiar, "min_tokens": a.min_tokens},
        "censo_completo": a.limite_tokens is None,
        "t1_exato": h_exato,
        "t2_quase_dup": h_quase,
        "pct_flops_repetidos_exato": round(pct_rep_exato, 3),
        "pct_flops_repetidos_quase": round(pct_rep_quase, 3),
        "pct_flops_faixa_3_a_10": round(pct_pico, 3),
        "pares_testados": int(pares_testados),
        "minutos": round((time.time() - t0) / 60, 1),
        "referencia": "arXiv:2606.24998 — medido em 344M; 10% dos FLOPs em repetidos == perder 33% da computacao",
    }
    Path(a.out).write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrelatorio: {a.out}   ({saida['minutos']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
