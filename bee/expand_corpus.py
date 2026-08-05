"""BEE — expandir o corpus PT com mais fineweb-2 `por_Latn`, por ARQUIVO parquet (retomável).

⭐ POR QUE UM SCRIPT NOVO (e não mais streaming). O coletor original (`build_corpus.py`) usa
`load_dataset(streaming=True)`, que na RETOMADA relê a fonte DESDE O INÍCIO (o streaming do HF
não tem seek). Correto — o `vistos_sha` mata a duplicata — mas LENTO: cada retomada re-puxa da
rede tudo o que já coletou só para descartar. Foi o que travou a tentativa de `--target-gb 24`.

Aqui processamos os PARQUETS do `por_Latn` UM A UM: baixa → processa → apaga → registra o
arquivo como "feito". A retomada pula arquivo inteiro (sem re-download, sem re-processar). É a
diferença entre O(coletado) e O(0) de trabalho desperdiçado por retomada.

⭐ ANEXA, não reescreve. Os shards novos entram como `bee_corpus_NNNN` a partir do próximo índice
livre. Os shards de validação do Gate 2 ({7,23,41}, escolhidos por índice) NÃO mudam — então o
Gate 2 continua comparável (v3 vs v2 vs v1 no MESMO holdout). Depois rode
`build_corpus.py --reconciliar` para o MANIFEST refletir os shards novos e revalidar integridade.

Filtros/dedup: cópia EXATA do `build_corpus.py` (mantido self-contained de propósito, para não
arrastar a dependência de `comeia/data/common.detect_lang`, que aqui não é usada).

Uso (Colab, corpus na Drive):
    python bee/expand_corpus.py --out /content/drive/MyDrive/BEE/corpus --dry-run   # lista parquets
    python bee/expand_corpus.py --out /content/drive/MyDrive/BEE/corpus \
        --target-new-gb 26 --skip-files 8        # ~26 GB de texto novo ≈ ~8B tokens
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedup_persistente import DedupPersistente  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

REPO = "HuggingFaceFW/fineweb-2"
CONFIG_DIR = "por_Latn"          # parquets em data/por_Latn/train/*.parquet

# ============================ filtros/dedup (cópia de build_corpus.py) =========
_REPETIDO = re.compile(r"(.)\1{9,}")


def qualidade_ok(texto: str, min_chars: int = 200) -> str | None:
    """None se o documento presta; senão o motivo da rejeição (heurísticas do FineWeb)."""
    if not texto or len(texto) < min_chars:
        return "curto"
    n = len(texto)
    if sum(c.isdigit() or (not c.isalnum() and not c.isspace()) for c in texto) / n > 0.30:
        return "muito_simbolo"
    if _REPETIDO.search(texto):
        return "repetido"
    linhas = [l for l in texto.split("\n") if l.strip()]
    if len(linhas) >= 8 and n / len(linhas) < 25:
        return "linhas_curtas"
    letras = sum(c.isalpha() for c in texto)
    if letras / n < 0.50:
        return "pouca_letra"
    return None


def _shingles(texto: str, k: int = 5) -> set[str]:
    palavras = re.findall(r"\w+", unicodedata.normalize("NFKC", texto).casefold())
    if len(palavras) < k:
        return {" ".join(palavras)} if palavras else set()
    return {" ".join(palavras[i:i + k]) for i in range(len(palavras) - k + 1)}


def minhash(texto: str, n_perm: int = 64) -> tuple[int, ...]:
    sh = _shingles(texto)
    if not sh:
        return tuple([0] * n_perm)
    hashes = [int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:16], 16) for s in sh]
    return tuple(min(h ^ (i * 0x9E3779B97F4A7C15) for h in hashes) for i in range(n_perm))


def sha_doc(texto: str) -> int:
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16], 16)


class VistosPersistente:
    """Conjunto de sha_doc que SOBREVIVE ao processo — grava incremental em disco."""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.vistos: set[int] = set()
        self._fh = None
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as fh:
                for linha in fh:
                    linha = linha.strip()
                    if linha:
                        try:
                            self.vistos.add(int(linha, 16))
                        except ValueError:
                            continue

    def _abre(self):
        if self._fh is None:
            self._fh = open(self.caminho, "a", encoding="utf-8")
        return self._fh

    def duplicado_exato(self, texto: str) -> bool:
        h = sha_doc(texto)
        if h in self.vistos:
            return True
        self.vistos.add(h)
        self._abre().write(f"{h:016x}\n")
        return False

    def flush(self):
        if self._fh is not None:
            self._fh.flush()

    def fecha(self):
        self.flush()
        if self._fh is not None:
            self._fh.close()
            self._fh = None


class Dedup:
    """LSH por bandas sobre a assinatura MinHash — aproximado, pega quase-duplicata em RAM."""

    def __init__(self, bandas: int = 16, n_perm: int = 64):
        self.bandas, self.n_perm = bandas, n_perm
        self.por_banda: list[set[int]] = [set() for _ in range(bandas)]
        self.vistos = 0

    def duplicado(self, texto: str) -> bool:
        sig = minhash(texto, self.n_perm)
        largura = self.n_perm // self.bandas
        chaves = [hash(sig[i * largura:(i + 1) * largura]) for i in range(self.bandas)]
        dup = any(c in b for c, b in zip(chaves, self.por_banda))
        if not dup:
            for c, b in zip(chaves, self.por_banda):
                b.add(c)
            self.vistos += 1
        return dup


# ================================= coleta por arquivo =========================
def listar_parquets() -> list[str]:
    from huggingface_hub import HfApi
    arquivos = HfApi().list_repo_files(REPO, repo_type="dataset")
    return sorted(a for a in arquivos
                  if a.endswith(".parquet") and f"/{CONFIG_DIR}/" in a and "/train/" in a)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "bee" / "corpus")
    ap.add_argument("--target-new-gb", type=float, default=26.0,
                    help="GB de TEXTO NOVO aceito a coletar (~26 GB ≈ ~8B tokens do Bee)")
    ap.add_argument("--shard-mb", type=int, default=256)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--skip-files", type=int, default=0,
                    help="pula os N primeiros parquets (região já consumida pelo streaming)")
    ap.add_argument("--minhash", action="store_true",
                    help="liga o dedup MinHash de quase-duplicata (LENTO, ~4-5x o tempo). "
                         "⚠️ MEDIDO em 2026-08-04 (bee/medir_dedup.py): a justificativa antiga "
                         "('o fineweb-2 já vem MinHash-deduplicado, essa passada é redundante') "
                         "está ERRADA — há 0,53-0,73%% de quase-duplicata DENTRO de um único "
                         "parquet do fineweb-2, e 0,90%% cruzando a fronteira entre o corpus já "
                         "coletado e a expansão. O dedup EXATO (vistos_sha) fica sempre ligado.")
    ap.add_argument("--fonte", default="fineweb2-por")
    ap.add_argument("--tmp", type=Path, default=Path("/content/pqtmp"),
                    help="dir temporário p/ baixar cada parquet (apagado após processar)")
    ap.add_argument("--dry-run", action="store_true", help="lista os parquets e sai")
    args = ap.parse_args()

    todos = listar_parquets()
    print(f"[fineweb-2] {REPO}/{CONFIG_DIR}: {len(todos)} parquets no split train")
    if todos:
        print(f"  primeiro: {todos[0]}")
        print(f"  último  : {todos[-1]}")
    if args.dry_run:
        print("[dry-run] nada baixado.")
        return 0

    import pyarrow.parquet as pqmod
    import zstandard as zstd
    from huggingface_hub import hf_hub_download

    alvo_novo = int(args.target_new_gb * 1024 ** 3)
    args.out.mkdir(parents=True, exist_ok=True)
    args.tmp.mkdir(parents=True, exist_ok=True)

    manifesto_path = args.out / "MANIFEST.json"
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8")) \
        if manifesto_path.exists() else {"fontes": {}, "shards": [], "bytes": 0}

    feitos_path = args.out / "fineweb2_feitos.txt"
    feitos = set(feitos_path.read_text(encoding="utf-8").split()) if feitos_path.exists() else set()

    vistos = VistosPersistente(args.out / "vistos_sha.txt")
    # ⭐ DedupPersistente, não Dedup: o Dedup em memória nascia VAZIO a cada execução,
    # então quase-duplicata entre o corpus já coletado e a expansão nunca era pega
    # (0,90% medido). O persistente recarrega as bandas do LSH do disco — é o mesmo
    # conserto que o `vistos_sha` fez para duplicata EXATA em 2026-07-27.
    dedup = DedupPersistente(args.out / "lsh_bandas.bin") if args.minhash else None
    print(f"[dedup] {len(vistos.vistos)} docs já vistos (exato) carregados do disco · "
          f"MinHash {'LIGADO (persistente)' if dedup else 'DESLIGADO'}")

    existentes = sorted(args.out.glob("bee_corpus_*.jsonl.zst"))
    shard_i = max((int(p.name.split("_")[-1].split(".")[0]) for p in existentes), default=-1) + 1
    print(f"[shards] {len(existentes)} shards existentes · novos começam em {shard_i:04d}")

    fila = [f for i, f in enumerate(todos) if i >= args.skip_files and f not in feitos]
    print(f"[fila] {len(fila)} parquets a processar (pulei {args.skip_files}, "
          f"{len(feitos)} já feitos) · alvo {args.target_new_gb} GB de texto novo\n")

    novo_bytes = 0
    buf: list[str] = []
    buf_bytes = 0
    aceitos = rejeitados = dups = 0
    fonte_bytes0 = manifesto["fontes"].get(args.fonte, {}).get("bytes", 0)

    def flush_shard():
        nonlocal buf, buf_bytes, shard_i
        if not buf:
            return
        p = args.out / f"bee_corpus_{shard_i:04d}.jsonl.zst"
        p.write_bytes(zstd.ZstdCompressor(level=3).compress(
            ("\n".join(buf) + "\n").encode("utf-8")))
        manifesto["shards"].append({"arquivo": p.name, "bytes": buf_bytes, "docs": len(buf)})
        manifesto["bytes"] += buf_bytes
        f = manifesto["fontes"].setdefault(args.fonte, {})
        f["bytes"] = fonte_bytes0 + novo_bytes
        f["licenca"] = "ODC-By-1.0"
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
        vistos.flush()
        print(f"  shard {p.name} ({buf_bytes/1024**2:.0f} MB) · "
              f"novo total {novo_bytes/1024**3:.2f}/{args.target_new_gb} GB · "
              f"aceitos {aceitos}", flush=True)
        shard_i += 1
        buf, buf_bytes = [], 0

    for fname in fila:
        if novo_bytes >= alvo_novo:
            break
        try:
            local = hf_hub_download(REPO, fname, repo_type="dataset",
                                    local_dir=str(args.tmp))
        except Exception as e:
            print(f"  ⚠️ falha ao baixar {fname} ({type(e).__name__}: {str(e)[:120]}) — pulando",
                  file=sys.stderr)
            continue
        try:
            pf = pqmod.ParquetFile(local)
            for batch in pf.iter_batches(batch_size=2000, columns=["text"]):
                for texto in batch.column("text").to_pylist():
                    if not texto:
                        continue
                    texto = texto.strip()
                    if qualidade_ok(texto, args.min_chars):
                        rejeitados += 1
                        continue
                    if vistos.duplicado_exato(texto):
                        dups += 1
                        continue
                    if dedup is not None and dedup.duplicado(texto):
                        dups += 1
                        continue
                    aceitos += 1
                    reg = json.dumps({"text": texto, "fonte": args.fonte}, ensure_ascii=False)
                    buf.append(reg)
                    buf_bytes += len(reg.encode("utf-8"))
                    novo_bytes += len(texto.encode("utf-8"))
                    if buf_bytes >= args.shard_mb * 1024 ** 2:
                        flush_shard()
                if novo_bytes >= alvo_novo:
                    break
        except Exception as e:
            print(f"  ⚠️ erro processando {fname} ({type(e).__name__}: {str(e)[:120]})",
                  file=sys.stderr)
        finally:
            try:
                Path(local).unlink()
            except Exception:
                pass
        feitos.add(fname)
        feitos_path.write_text("\n".join(sorted(feitos)), encoding="utf-8")
        print(f"[feito] {fname.split('/')[-1]} · novo {novo_bytes/1024**3:.2f} GB · "
              f"aceitos {aceitos} · rej {rejeitados} · dup {dups}", flush=True)

    flush_shard()          # fecha o buffer pendente
    vistos.fecha()
    if dedup is not None:
        dedup.fechar()     # sem isto o LSH aprendido nesta execução se perde
        print(f"[dedup] LSH gravado: {dedup.itens:,} chaves · "
              f"{dedup.descartados} quase-duplicatas descartadas · "
              f"fp estimado {dedup.fp_atual():.3%}")

    print("\n" + "=" * 72)
    print(f"✅ EXPANSÃO: +{novo_bytes/1024**3:.2f} GB de texto novo · "
          f"{aceitos} docs aceitos · {rejeitados} rejeitados · {dups} duplicados")
    print(f"   corpus agora: {len(list(args.out.glob('bee_corpus_*.jsonl.zst')))} shards")
    aprov = aceitos / max(1, aceitos + rejeitados + dups)
    print(f"   aproveitamento {aprov:.0%}")
    print("\n⭐ PRÓXIMO: rode `python bee/build_corpus.py --reconciliar --out <corpus>` para o "
          "MANIFEST refletir os shards novos e revalidar integridade;")
    print("   depois `prepare_data.py` (holdout {7,23,41} intacto) e `pretrain.py` (1 época).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
