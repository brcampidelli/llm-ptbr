"""Fase 0 do BEE — coletor do corpus de PRÉ-TREINO, PT-forte e com procedência auditável.

⚠️ REGRA DURA DE LICENÇA (§1 do plano). Só entra fonte cujo licenciamento permite treinar E
publicar. O que ficou FORA, e por quê:
  • Scribd — conteúdo protegido atrás de paywall. Estar logado dá acesso para LER, não licença
    para treinar e publicar. Um Bee treinado com isso é impublicável e não-investível.
  • GitHub raspado direto — licença varia por repositório. Usamos `the-stack-v2`, que já filtrou.
É a mesma disciplina do `assert_teacher_allowed` que aplicamos na destilação.

⭐ A APOSTA: ~70% português. O SmolLM2-135M é só inglês, então o único lugar onde um modelo nosso
de 150M ganha de alguém é o português. Corpus equilibrado não venceria ninguém em nada — o XLM-R
mediu o *curse of multilinguality* (XNLI 71,8% → 67,7% ao diluir capacidade fixa entre idiomas).

⚠️ AUDITAR, NÃO ASSUMIR: a proporção pedida não é a proporção obtida. Na abelha de extração
pedimos 35% de itens esparsos e o dataset saiu com 46% — efeito de seleção do filtro. Aqui o
mesmo risco existe (fontes têm taxas de rejeição diferentes), então medimos a mistura REAL com
`common.detect_lang` e reportamos o desvio.

Uso:
    python data/20_build_corpus.py --target-gb 2 --dry-run     # ver a receita
    python data/20_build_corpus.py --target-gb 2               # amostra p/ tokenizador
    python data/20_build_corpus.py --target-gb 60 --out ...    # corpus de treino

Saída: shards `bee_corpus_NNNN.jsonl.zst` + `MANIFEST.json` (fonte, licença, docs, bytes).
Retomável: relê o manifesto e continua do último shard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import detect_lang  # noqa: E402

# ---------------------------------------------------------------- receita ---
# `peso` = fração-alvo do corpus final. `lang` = idioma esperado (para auditoria).
# `licenca` vai para o MANIFEST — procedência auditável desde o primeiro token.
FONTES = [
    {"nome": "fineweb2-por", "peso": 0.35, "lang": "pt", "licenca": "ODC-By-1.0",
     "hf": ("HuggingFaceFW/fineweb-2", "por_Latn"), "campo": "text"},
    {"nome": "portuguese-pd", "peso": 0.15, "lang": "pt", "licenca": "public-domain",
     "hf": ("PleIAs/Portuguese-PD", None), "campo": "text",
     "nota": "livros: monografias e periodicos em dominio publico"},
    {"nome": "wikipedia-pt", "peso": 0.10, "lang": "pt", "licenca": "CC-BY-SA-4.0",
     "hf": ("wikimedia/wikipedia", "20231101.pt"), "campo": "text"},
    {"nome": "legal-pt", "peso": 0.05, "lang": "pt", "licenca": "Apache-2.0",
     "hf": ("stjiris/portuguese-legal-sentences-v0", None), "campo": "sentence",
     "nota": "jurisprudencia; texto formal/tecnico"},
    {"nome": "fineweb-edu-en", "peso": 0.15, "lang": "en", "licenca": "ODC-By-1.0",
     "hf": ("HuggingFaceTB/smollm-corpus", "fineweb-edu-dedup"), "campo": "text"},
    {"nome": "cosmopedia-en", "peso": 0.10, "lang": "en", "licenca": "ODC-By-1.0",
     "hf": ("HuggingFaceTB/smollm-corpus", "cosmopedia-v2"), "campo": "text",
     "nota": "livro-texto sintetico; a tese 'textbooks are all you need'"},
    {"nome": "python-edu", "peso": 0.10, "lang": "?", "licenca": "ODC-By-1.0",
     "hf": ("HuggingFaceTB/smollm-corpus", "python-edu"), "campo": "text",
     "nota": "codigo; detect_lang nao se aplica"},
]

# ------------------------------------------------------------- qualidade ---
_REPETIDO = re.compile(r"(.)\1{9,}")          # 10+ do mesmo caractere seguido


def qualidade_ok(texto: str, min_chars: int = 200) -> str | None:
    """None se o documento presta; senão o motivo da rejeição.

    Heurísticas do FineWeb, na ordem mais barata primeiro. Rejeitar cedo importa:
    são centenas de milhões de documentos em streaming.
    """
    if not texto or len(texto) < min_chars:
        return "curto"
    n = len(texto)
    if sum(c.isdigit() or (not c.isalnum() and not c.isspace()) for c in texto) / n > 0.30:
        return "muito_simbolo"          # tabela, log, lixo de OCR
    if _REPETIDO.search(texto):
        return "repetido"
    # ⚠️ Era `count("\n")/n > 0.25`, e um menu de navegação PASSAVA: linhas de ~6
    # caracteres dão razão 0,16, e o limiar exigia linhas de ~4. O que eu queria
    # dizer desde o início era COMPRIMENTO MÉDIO DE LINHA — mais interpretável e
    # sem número mágico invertido.
    linhas = [l for l in texto.split("\n") if l.strip()]
    if len(linhas) >= 8 and n / len(linhas) < 25:
        return "linhas_curtas"          # menu, lista de links, navegação
    letras = sum(c.isalpha() for c in texto)
    if letras / n < 0.50:
        return "pouca_letra"
    return None


# ----------------------------------------------------------------- dedup ---
def _shingles(texto: str, k: int = 5) -> set[str]:
    palavras = re.findall(r"\w+", unicodedata.normalize("NFKC", texto).casefold())
    if len(palavras) < k:
        return {" ".join(palavras)} if palavras else set()
    return {" ".join(palavras[i:i + k]) for i in range(len(palavras) - k + 1)}


def minhash(texto: str, n_perm: int = 64) -> tuple[int, ...]:
    """Assinatura MinHash barata: n_perm mínimos de sha1 sobre shingles de 5 palavras.

    Implementação própria (sem `datasketch`) porque a dependência não se paga para
    64 permutações, e streaming exige algo que não aloque por documento.
    """
    sh = _shingles(texto)
    if not sh:
        return tuple([0] * n_perm)
    hashes = [int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:16], 16) for s in sh]
    # n_perm "permutações" por XOR com semente — aproximação padrão e suficiente
    return tuple(min(h ^ (i * 0x9E3779B97F4A7C15) for h in hashes) for i in range(n_perm))


class Dedup:
    """LSH por bandas sobre a assinatura MinHash. Aproximado e streaming."""

    def __init__(self, bandas: int = 16, n_perm: int = 64):
        self.bandas, self.n_perm = bandas, n_perm
        self.por_banda: list[set[int]] = [set() for _ in range(bandas)]
        self.vistos = 0

    def duplicado(self, texto: str) -> bool:
        sig = minhash(texto, self.n_perm)
        largura = self.n_perm // self.bandas
        chaves = [hash(sig[i * largura:(i + 1) * largura]) for i in range(self.bandas)]
        # duplicado se colide em QUALQUER banda (recall alto, é o que queremos)
        dup = any(c in b for c, b in zip(chaves, self.por_banda))
        if not dup:
            for c, b in zip(chaves, self.por_banda):
                b.add(c)
            self.vistos += 1
        return dup


# ------------------------------------------------------------------ main ---
def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "corpus")
    ap.add_argument("--target-gb", type=float, default=2.0,
                    help="tamanho-alvo em GB de texto. 2 GB basta para o tokenizador; "
                         "o treino de 3B tokens pede ~12 GB")
    ap.add_argument("--shard-mb", type=int, default=256)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--no-dedup", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="mostra a receita e sai")
    args = ap.parse_args()

    alvo_bytes = int(args.target_gb * 1024 ** 3)
    print(f"alvo      : {args.target_gb} GB de texto")
    print(f"saida     : {args.out}")
    print(f"fontes    : {len(FONTES)}\n")
    print(f"{'fonte':<18} {'peso':>6} {'idioma':>7}  {'licenca':<16} nota")
    print("-" * 78)
    for f in FONTES:
        print(f"{f['nome']:<18} {f['peso']:>5.0%} {f['lang']:>7}  {f['licenca']:<16} "
              f"{f.get('nota','')}")
    print("-" * 78)
    pt = sum(f["peso"] for f in FONTES if f["lang"] == "pt")
    en = sum(f["peso"] for f in FONTES if f["lang"] == "en")
    print(f"→ PT {pt:.0%} · EN {en:.0%} · codigo {1-pt-en:.0%}   (soma {sum(f['peso'] for f in FONTES):.0%})")
    print("\n⛔ FORA por licenca: Scribd (paywall/copyright), GitHub raspado (licenca varia)")

    if args.dry_run:
        print("\n[dry-run] nada baixado.")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    manifesto_path = args.out / "MANIFEST.json"
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8")) \
        if manifesto_path.exists() else {"fontes": {}, "shards": [], "bytes": 0}
    if manifesto["bytes"]:
        print(f"\n[retomada] {manifesto['bytes']/1024**3:.2f} GB já coletados em "
              f"{len(manifesto['shards'])} shards")

    import zstandard as zstd
    from datasets import load_dataset

    dedup = None if args.no_dedup else Dedup()
    stats: dict[str, Counter] = defaultdict(Counter)
    idiomas_reais: Counter = Counter()
    escritos = manifesto["bytes"]
    shard_i = len(manifesto["shards"])

    for fonte in FONTES:
        cota = int(alvo_bytes * fonte["peso"])
        ja = manifesto["fontes"].get(fonte["nome"], {}).get("bytes", 0)
        if ja >= cota:
            print(f"\n[{fonte['nome']}] cota já cumprida ({ja/1024**2:.0f} MB)")
            continue
        repo, cfg = fonte["hf"]
        print(f"\n[{fonte['nome']}] alvo {cota/1024**2:.0f} MB · {repo}"
              f"{'/' + cfg if cfg else ''}", flush=True)
        try:
            ds = load_dataset(repo, cfg, split="train", streaming=True)
        except Exception as e:
            print(f"  ⚠️ FALHOU ao abrir ({type(e).__name__}: {e}). Pulando — o MANIFEST "
                  f"vai registrar a ausência, e a mistura real sairá desviada.", file=sys.stderr)
            stats[fonte["nome"]]["erro_abrir"] += 1
            continue

        buf, buf_bytes, desta_fonte = [], 0, ja
        for row in ds:
            if desta_fonte >= cota:
                break
            texto = (row.get(fonte["campo"]) or "").strip()
            motivo = qualidade_ok(texto, args.min_chars)
            if motivo:
                stats[fonte["nome"]][motivo] += 1
                continue
            if dedup and dedup.duplicado(texto):
                stats[fonte["nome"]]["duplicado"] += 1
                continue
            stats[fonte["nome"]]["ok"] += 1
            if fonte["lang"] != "?" and stats[fonte["nome"]]["ok"] % 50 == 0:
                idiomas_reais[detect_lang(texto[:2000])] += 1   # auditoria amostrada
            reg = json.dumps({"text": texto, "fonte": fonte["nome"]}, ensure_ascii=False)
            buf.append(reg)
            buf_bytes += len(reg.encode("utf-8"))
            desta_fonte += len(texto.encode("utf-8"))
            if buf_bytes >= args.shard_mb * 1024 ** 2:
                p = args.out / f"bee_corpus_{shard_i:04d}.jsonl.zst"
                with open(p, "wb") as fh:
                    fh.write(zstd.ZstdCompressor(level=3).compress(
                        ("\n".join(buf) + "\n").encode("utf-8")))
                manifesto["shards"].append({"arquivo": p.name, "bytes": buf_bytes,
                                            "docs": len(buf)})
                shard_i += 1
                escritos += buf_bytes
                print(f"  shard {p.name} ({buf_bytes/1024**2:.0f} MB) · "
                      f"total {escritos/1024**3:.2f} GB", flush=True)
                buf, buf_bytes = [], 0

        if buf:
            p = args.out / f"bee_corpus_{shard_i:04d}.jsonl.zst"
            with open(p, "wb") as fh:
                fh.write(zstd.ZstdCompressor(level=3).compress(
                    ("\n".join(buf) + "\n").encode("utf-8")))
            manifesto["shards"].append({"arquivo": p.name, "bytes": buf_bytes,
                                        "docs": len(buf)})
            shard_i += 1
            escritos += buf_bytes

        manifesto["fontes"][fonte["nome"]] = {
            "repo": repo, "config": cfg, "licenca": fonte["licenca"],
            "peso_alvo": fonte["peso"], "bytes": desta_fonte,
            "aceitos": stats[fonte["nome"]]["ok"],
            "rejeitados": {k: v for k, v in stats[fonte["nome"]].items() if k != "ok"},
        }
        manifesto["bytes"] = escritos
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

    # ---------------- relatório: a mistura REAL, não a pedida ----------------
    print("\n" + "=" * 78)
    print("⭐ MISTURA REAL (auditada), contra a pedida")
    print("=" * 78)
    total = max(1, manifesto["bytes"])
    print(f"{'fonte':<18} {'pedido':>8} {'obtido':>8} {'desvio':>8}   aproveitamento")
    print("-" * 78)
    for fonte in FONTES:
        m = manifesto["fontes"].get(fonte["nome"])
        if not m:
            print(f"{fonte['nome']:<18} {fonte['peso']:>7.0%} {'AUSENTE':>8}"
                  f" {'—':>8}   ⚠️ falhou ao abrir")
            continue
        obtido = m["bytes"] / total
        rej = sum(m["rejeitados"].values())
        apr = m["aceitos"] / max(1, m["aceitos"] + rej)
        flag = " ⚠️" if abs(obtido - fonte["peso"]) > 0.10 else ""
        print(f"{fonte['nome']:<18} {fonte['peso']:>7.0%} {obtido:>7.0%} "
              f"{obtido-fonte['peso']:>+7.0%}   {apr:>5.0%}{flag}")
    print("-" * 78)
    if idiomas_reais:
        tot_l = sum(idiomas_reais.values())
        print("idioma detectado na amostra: " +
              " · ".join(f"{k} {v/tot_l:.0%}" for k, v in idiomas_reais.most_common()))
        pt_real = idiomas_reais.get("pt", 0) / tot_l
        print(f"\n⭐ português real: {pt_real:.0%}  (alvo 65%, tolerância ±10 pp) "
              f"{'✅' if abs(pt_real - 0.65) <= 0.10 else '⚠️ FORA — revisar antes de treinar'}")
    print(f"\ntotal: {manifesto['bytes']/1024**3:.2f} GB em {len(manifesto['shards'])} shards")
    print(f"manifesto (procedência + licenças): {manifesto_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
