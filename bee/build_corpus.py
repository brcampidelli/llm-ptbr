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
sys.path.insert(0, str(ROOT / "comeia" / "data"))   # detect_lang vive na camada COMEIA
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
    # ⚠️ CODIGO — a fonte foi TROCADA em 2026-07-27 depois de voltar 0%.
    # O que NAO serve, e por que (achado medindo, nao lendo doc):
    #   • `HuggingFaceTB/smollm-corpus/python-edu` — so traz blob_id/repo_name/path;
    #     o conteudo vive no S3 do Software Heritage. O campo `text` vem VAZIO sempre.
    #   • `bigcode/the-stack-v2` — mesmo problema, e tambem so ponteiro.
    #   • `bigcode/the-stack-dedup` e `the-stack-smol` — GATED (exigem aceite manual),
    #     inviavel num pipeline automatico.
    # O `github-code-clean` resolve os tres: conteudo inline, aberto, e — o que decide —
    # tem coluna `license`, entao pegamos SO configs permissivas em vez de confiar que
    # "alguem ja filtrou". Coerente com a regra de procedencia do projeto.
    {"nome": "code-mit", "peso": 0.05, "lang": "?", "licenca": "MIT (por arquivo)",
     "hf": ("codeparrot/github-code-clean", "all-mit"), "campo": "code",
     "filtro_campo": ("language", None),          # None = usa LINGUAGENS_OK
     "nota": "codigo; licenca permissiva por arquivo; detect_lang nao se aplica"},
    {"nome": "code-apache", "peso": 0.05, "lang": "?", "licenca": "Apache-2.0 (por arquivo)",
     "hf": ("codeparrot/github-code-clean", "all-apache-2.0"), "campo": "code",
     "filtro_campo": ("language", None),
     "nota": "codigo; licenca permissiva por arquivo"},
]

# So logica. Fora: HTML/Markdown/CSS/TeX — sao markup, ja temos texto de sobra, e o
# `github-code-clean` esta cheio de HTML de javadoc GERADO (verificado no preview).
LINGUAGENS_OK = {"Python", "JavaScript", "TypeScript", "Java", "C", "C++", "C#",
                 "Go", "Rust", "Ruby", "PHP", "Shell", "SQL"}

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


def qualidade_codigo_ok(texto: str, min_chars: int = 200) -> str | None:
    """Filtro SEPARADO para código. `None` se presta; senão o motivo.

    ⭐ POR QUE NÃO REUSAR `qualidade_ok`: ele foi escrito para PROSA e reprova código
    legítimo por motivos que, em código, são normais. Medido em 2026-07-27:
      • o nosso próprio `bee/train_tokenizer.py` → "repetido" (as réguas `---` do print);
      • um `main()` em C → "linhas_curtas" (linha curta é a norma em C, não defeito);
      • qualquer linguagem chaveada estoura o teto de 30% de símbolos e o piso de 50%
        de letras — `{`, `}`, `;`, `=`, `(`, `)` são o corpo da linguagem.
    Isso importa além do bug: a fatia de código estava condenada por DOIS motivos
    independentes (fonte sem texto **e** filtro errado). Consertar só a fonte deixaria
    o segundo de pé, e o sintoma seria o mesmo — aproveitamento perto de zero.

    O que este filtro procura é o que de fato estraga código como dado de treino:
    arquivo gerado, minificado, blob de dados disfarçado de fonte.
    """
    if not texto or len(texto) < min_chars:
        return "curto"
    n = len(texto)
    if n > 200_000:
        return "gigante"                       # quase sempre gerado ou concatenado
    linhas = texto.split("\n")
    if max((len(l) for l in linhas), default=0) > 2000:
        return "minificado"                    # bundle .min.js, blob base64 numa linha
    # arquivo GERADO se declara — e treinar nisso ensina o gerador, não a linguagem
    cabeca = texto[:1500].lower()
    if any(m in cabeca for m in ("do not edit", "auto-generated", "autogenerated",
                                 "generated by", "@generated", "code generated by")):
        return "gerado"
    imprimivel = sum(c.isprintable() or c in "\n\t" for c in texto)
    if imprimivel / n < 0.95:
        return "binario"                       # bytes crus travestidos de texto
    # densidade de identificadores: código tem palavras; dado tabular não tem
    if len(re.findall(r"[A-Za-z_]{3,}", texto)) < n / 200:
        return "sem_identificador"
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


def sha_doc(texto: str) -> int:
    """Impressão digital EXATA do documento, em 8 bytes.

    ⭐ POR QUE ISTO EXISTE (bug achado em 2026-07-27, acompanhando a coleta ao vivo):
    o `Dedup` MinHash vive só em MEMÓRIA e morre com o processo. Na retomada, o
    streaming do HF não tem "seek": o script relê a fonte DESDE O INÍCIO e, com o
    dedup nascido vazio, **aceita de novo** documentos que já estão nos shards
    gravados. O corpus acumulava duplicatas a cada queda — e houve três.

    Isso não é cosmético num pré-treino: duplicata é memorização e FLOPs pagos duas
    vezes pelo mesmo texto (Lee et al., *Deduplicating Training Data Makes Language
    Models Better*). O MinHash continua pegando quase-duplicatas DENTRO de uma
    execução; este sha pega as EXATAS ATRAVÉS de execuções, que é o caso da retomada.

    8 bytes por documento: 1,5 M de docs ≈ 12 MB de RAM. Cabe folgado, e é barato de
    persistir em disco entre execuções.
    """
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
    """LSH por bandas sobre a assinatura MinHash. Aproximado e streaming.

    ⚠️ In-memory de propósito (pega quase-duplicata, que exige as bandas em RAM). A
    duplicata EXATA entre execuções é responsabilidade da `VistosPersistente`.
    """

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
    ap.add_argument("--out", type=Path, default=ROOT / "bee" / "corpus")
    ap.add_argument("--target-gb", type=float, default=2.0,
                    help="tamanho-alvo em GB de texto. 2 GB basta para o tokenizador; "
                         "o treino de 3B tokens pede ~12 GB")
    ap.add_argument("--shard-mb", type=int, default=256)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--no-dedup", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="mostra a receita e sai")
    ap.add_argument("--purgar-duplicatas", dest="purgar", action="store_true",
                    help="reescreve os shards SEM as duplicatas exatas. Rode depois de "
                         "`--reconciliar` acusar duplicata. Grava em .novo e so troca no "
                         "fim, para uma queda no meio nao destruir o corpus.")
    ap.add_argument("--reconciliar", action="store_true",
                    help="reconstroi o MANIFEST a partir dos shards que existem em disco. "
                         "Use quando uma queda deixou shards orfaos (gravados mas fora do "
                         "manifesto) — sem isso a retomada os SOBRESCREVE em silencio.")
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

    if args.purgar:
        # Reescreve cada shard sem os documentos repetidos. ⚠️ Escreve em `.novo` e só
        # substitui no fim de cada arquivo: uma queda no meio deixa o shard original
        # intacto em vez de um corpus meio-reescrito, que seria pior que a duplicata.
        print("\n⭐ PURGANDO duplicatas exatas dos shards…")
        dctx, cctx = zstd.ZstdDecompressor(), zstd.ZstdCompressor(level=3)
        sha_vistos: set[int] = set()
        rem_docs = rem_bytes = mantidos = 0
        for p in sorted(args.out.glob("bee_corpus_*.jsonl.zst")):
            try:
                dados = dctx.decompress(p.read_bytes()).decode("utf-8")
            except Exception as e:
                print(f"  🔴 {p.name}: ILEGÍVEL ({type(e).__name__}) — deixando como está",
                      file=sys.stderr)
                continue
            saida, tirados = [], 0
            for linha in dados.splitlines():
                if not linha.strip():
                    continue
                try:
                    reg = json.loads(linha)
                except Exception:
                    continue
                h = sha_doc(reg.get("text", ""))
                if h in sha_vistos:
                    tirados += 1
                    rem_bytes += len(reg.get("text", "").encode("utf-8"))
                    continue
                sha_vistos.add(h)
                saida.append(linha)
            rem_docs += tirados
            mantidos += len(saida)
            if tirados:
                tmp = p.with_suffix(".zst.novo")
                tmp.write_bytes(cctx.compress(("\n".join(saida) + "\n").encode("utf-8")))
                tmp.replace(p)                      # troca atômica
                print(f"  {p.name}: -{tirados} docs duplicados")
        (args.out / "vistos_sha.txt").write_text(
            "".join(f"{h:016x}\n" for h in sha_vistos), encoding="utf-8")
        print(f"\nremovidos {rem_docs} docs ({rem_bytes/1024**2:.0f} MB) · "
              f"mantidos {mantidos} docs únicos")
        print("✅ purgado. Rode `--reconciliar` para o manifesto refletir os novos tamanhos.")
        return 0

    if args.reconciliar:
        # ⭐ Lê os shards REAIS e reconstrói o manifesto a partir deles. Além de recuperar
        # shards órfãos, é uma verificação de integridade: shard corrompido aparece aqui,
        # não no meio do pré-treino. Conta bytes por FONTE usando o campo `fonte` de cada
        # registro — então a cota por fonte sai exata, não estimada.
        print("\n⭐ RECONCILIANDO o manifesto com os shards em disco…")
        dctx = zstd.ZstdDecompressor()
        shards, por_fonte, total, docs_tot = [], Counter(), 0, 0
        # ⭐ Reconstrói TAMBÉM o registro de vistos, e mede quanta duplicata exata já
        # entrou (o bug do dedup in-memory: cada retomada relia a fonte do zero).
        sha_vistos: set[int] = set()
        dup_bytes = dup_docs = 0
        dup_por_fonte: Counter = Counter()
        for p in sorted(args.out.glob("bee_corpus_*.jsonl.zst")):
            try:
                dados = dctx.decompress(p.read_bytes()).decode("utf-8")
            except Exception as e:
                print(f"  🔴 {p.name}: ILEGÍVEL ({type(e).__name__}) — descartando",
                      file=sys.stderr)
                continue
            b = d = dup_aqui = 0
            for linha in dados.splitlines():
                if not linha.strip():
                    continue
                try:
                    reg = json.loads(linha)
                except Exception:
                    continue
                txt = reg.get("text", "")
                n = len(txt.encode("utf-8"))
                h = sha_doc(txt)
                if h in sha_vistos:
                    dup_bytes += n; dup_docs += 1; dup_aqui += 1
                    dup_por_fonte[reg.get("fonte", "?")] += n
                else:
                    sha_vistos.add(h)
                por_fonte[reg.get("fonte", "?")] += n
                b += len(linha.encode("utf-8")); d += 1
            shards.append({"arquivo": p.name, "bytes": b, "docs": d})
            total += b; docs_tot += d
            marca = f"  ⚠️ {dup_aqui} dup" if dup_aqui else ""
            print(f"  {p.name}  {b/1024**2:>6.0f} MB  {d:>7} docs{marca}")
        # persiste o registro para que a PRÓXIMA retomada não duplique nada
        (args.out / "vistos_sha.txt").write_text(
            "".join(f"{h:016x}\n" for h in sha_vistos), encoding="utf-8")
        print(f"\n[dedup] registro de vistos gravado: {len(sha_vistos)} documentos únicos")
        if dup_docs:
            print(f"⚠️ DUPLICATA EXATA JÁ NO CORPUS: {dup_docs} docs · "
                  f"{dup_bytes/1024**2:.0f} MB ({dup_bytes/max(1,sum(por_fonte.values())):.1%})")
            for nome, n in dup_por_fonte.most_common():
                print(f"     {nome:<18} {n/1024**2:>7.0f} MB duplicados")
            print("     Causa: o dedup MinHash era só em memória e cada retomada relia a")
            print("     fonte do zero. Corrigido — mas estes já entraram. Use "
                  "`--purgar-duplicatas` para reescrever os shards sem eles.")
        else:
            print("✅ nenhuma duplicata exata entre os shards")
        antes = manifesto["bytes"]
        manifesto["shards"] = shards
        manifesto["bytes"] = total
        for nome, n in por_fonte.items():
            manifesto["fontes"].setdefault(nome, {})["bytes"] = n
            manifesto["fontes"][nome].pop("parcial", None)
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
        print(f"\nmanifesto: {antes/1024**3:.2f} GB → {total/1024**3:.2f} GB "
              f"em {len(shards)} shards · {docs_tot} docs")
        print("bytes por fonte:")
        for nome, n in sorted(por_fonte.items(), key=lambda kv: -kv[1]):
            print(f"  {nome:<18} {n/1024**2:>7.0f} MB")
        print("\n✅ reconciliado. Rode de novo SEM --reconciliar para continuar a coleta.")
        return 0

    from datasets import load_dataset

    dedup = None if args.no_dedup else Dedup()
    vistos = None if args.no_dedup else VistosPersistente(args.out / "vistos_sha.txt")
    if vistos and vistos.vistos:
        print(f"[dedup] {len(vistos.vistos)} documentos já vistos carregados do disco "
              f"— a retomada não vai duplicá-los")
    stats: dict[str, Counter] = defaultdict(Counter)
    idiomas_reais: Counter = Counter()
    fontes_vazias: list[str] = []
    fontes_interrompidas: list[str] = []
    escritos = manifesto["bytes"]
    shard_i = len(manifesto["shards"])

    def salva_manifesto():
        """⭐ Chamada a CADA shard, não a cada fonte.

        A versão anterior gravava o MANIFEST só no fim de cada fonte. Quando o
        `Portuguese-PD` estourou no meio (2026-07-27), 6 shards já escritos em disco
        (~1,5 GB) tinham ficado FORA do manifesto — a retomada os sobrescreveria, e a
        perda seria silenciosa. Persistir por shard custa um write de alguns KB e
        transforma qualquer queda em "perde o shard corrente", não "perde a fonte".
        """
        manifesto["bytes"] = escritos
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

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
            # ⭐ `columns=[campo]` quando dá: o Portuguese-PD tem PARQUETS COM SCHEMAS
            # DIFERENTES entre si (uns com 6 colunas, outros com 9: language,
            # language_code, character_count). O streaming infere o schema pelo
            # primeiro arquivo e o `datasets` estoura com CastError no quinto. Pedir só
            # a coluna que interessa faz o cast ignorar os metadados divergentes — que
            # é o defeito real, já que nunca usamos essas colunas.
            campos = [fonte["campo"]] + (
                [fonte["filtro_campo"][0]] if fonte.get("filtro_campo") else [])
            try:
                ds = load_dataset(repo, cfg, split="train", streaming=True, columns=campos)
            except Exception:
                ds = load_dataset(repo, cfg, split="train", streaming=True)
                print("  (sem projeção de colunas — schema heterogêneo pode falhar)",
                      file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️ FALHOU ao abrir ({type(e).__name__}: {e}). Pulando — o MANIFEST "
                  f"vai registrar a ausência, e a mistura real sairá desviada.", file=sys.stderr)
            stats[fonte["nome"]]["erro_abrir"] += 1
            continue

        # código e prosa têm filtros DIFERENTES — ver `qualidade_codigo_ok`
        eh_codigo = fonte["lang"] == "?"
        filtra = qualidade_codigo_ok if eh_codigo else qualidade_ok
        campo_filtro, valores_ok = fonte.get("filtro_campo", (None, None))
        if campo_filtro and valores_ok is None:
            valores_ok = LINGUAGENS_OK

        buf, buf_bytes, desta_fonte = [], 0, ja
        vistos_fonte = 0
        # ⭐ O `try` cobre a ITERAÇÃO, não só o `load_dataset`. Foi essa a lição de
        # 2026-07-27: o `Portuguese-PD` estourou um CastError no 5º parquet e derrubou a
        # coleta INTEIRA — as 6 fontes seguintes nem foram tentadas. Uma fonte que morre
        # no meio agora só perde a própria cota; o corpus continua e a auditoria de
        # mistura no fim reporta o desvio, que é o comportamento certo.
        try:
            for row in ds:
                if desta_fonte >= cota:
                    break
                vistos_fonte += 1
                if campo_filtro and row.get(campo_filtro) not in valores_ok:
                    stats[fonte["nome"]]["fora_do_filtro"] += 1
                    continue
                texto = (row.get(fonte["campo"]) or "").strip()
                motivo = filtra(texto, args.min_chars)
                if motivo:
                    stats[fonte["nome"]][motivo] += 1
                    continue
                # exato PRIMEIRO: é O(1) e é o que resolve a duplicata da retomada
                if vistos is not None and vistos.duplicado_exato(texto):
                    stats[fonte["nome"]]["dup_exata"] += 1
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
                    # registra a cota parcial ANTES de salvar, senão a retomada relê tudo
                    manifesto["fontes"].setdefault(fonte["nome"], {}).update(
                        {"repo": repo, "config": cfg, "licenca": fonte["licenca"],
                         "peso_alvo": fonte["peso"], "bytes": desta_fonte,
                         "aceitos": stats[fonte["nome"]]["ok"], "lidos": vistos_fonte,
                         "parcial": True})
                    salva_manifesto()
                    if vistos:
                        vistos.flush()      # o registro de vistos acompanha os shards
                    print(f"  shard {p.name} ({buf_bytes/1024**2:.0f} MB) · "
                          f"total {escritos/1024**3:.2f} GB", flush=True)
                    buf, buf_bytes = [], 0
        except Exception as e:
            print(f"  ⚠️ FONTE INTERROMPIDA no meio ({type(e).__name__}): "
                  f"{str(e)[:180]}", file=sys.stderr)
            print(f"     Coletado desta fonte antes de morrer: "
                  f"{desta_fonte/1024**2:.0f} MB de {cota/1024**2:.0f} MB. "
                  f"Seguindo para a próxima — o desvio aparece na auditoria do fim.",
                  file=sys.stderr)
            stats[fonte["nome"]]["erro_iterando"] += 1
            fontes_interrompidas.append(fonte["nome"])

        if buf:
            p = args.out / f"bee_corpus_{shard_i:04d}.jsonl.zst"
            with open(p, "wb") as fh:
                fh.write(zstd.ZstdCompressor(level=3).compress(
                    ("\n".join(buf) + "\n").encode("utf-8")))
            manifesto["shards"].append({"arquivo": p.name, "bytes": buf_bytes,
                                        "docs": len(buf)})
            shard_i += 1
            escritos += buf_bytes
            # ⚠️ este print faltava: o shard de FECHAMENTO de fonte era gravado em
            # silêncio, e o log pulava um número (0024 → 0026). Nenhum dado se perdia,
            # mas o rastro mentia por omissão — e um log que pula arquivo faz o leitor
            # concluir que houve falha onde não houve. Observabilidade também é correção.
            print(f"  shard {p.name} ({buf_bytes/1024**2:.0f} MB) · "
                  f"total {escritos/1024**3:.2f} GB  [fecha {fonte['nome']}]", flush=True)
            if vistos:
                vistos.flush()

        # ⭐ GUARD DA FONTE VAZIA — a lição do `python-edu` (2026-07-27).
        # Ele voltou 0% e o script seguiu em silêncio; o defeito só apareceu na auditoria
        # do FIM, depois de 1 h de coleta. Agora quem vê a fonte morrer é quem está
        # olhando a fonte, e na hora. Falhar cedo e alto é mais barato que falhar tarde.
        aceitos = stats[fonte["nome"]]["ok"]
        if vistos_fonte and aceitos == 0:
            top = stats[fonte["nome"]].most_common(3)
            print(f"  🔴 FONTE VAZIA: {vistos_fonte} linhas lidas, 0 aceitas. "
                  f"Motivos: {top}", file=sys.stderr)
            chaves = sorted(row.keys())[:8] if "row" in dir() else "(nenhuma linha lida)"
            print(f"     Campo pedido: '{fonte['campo']}'. Chaves que a fonte devolve: "
                  f"{chaves}", file=sys.stderr)
            print("     Causa mais comum: o dataset guarda PONTEIRO (blob_id/path) em vez "
                  "do texto. Confira o schema antes de gastar mais tempo.", file=sys.stderr)
            fontes_vazias.append(fonte["nome"])
        elif vistos_fonte and aceitos / vistos_fonte < 0.02:
            print(f"  ⚠️ aproveitamento de {aceitos/vistos_fonte:.1%} "
                  f"({aceitos}/{vistos_fonte}) — filtro errado para esta fonte?",
                  file=sys.stderr)

        manifesto["fontes"][fonte["nome"]] = {
            "repo": repo, "config": cfg, "licenca": fonte["licenca"],
            "peso_alvo": fonte["peso"], "bytes": desta_fonte,
            "aceitos": aceitos, "lidos": vistos_fonte,
            "interrompida": fonte["nome"] in fontes_interrompidas,
            "rejeitados": {k: v for k, v in stats[fonte["nome"]].items() if k != "ok"},
        }
        salva_manifesto()

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

    # ⭐ VEREDITO com código de saída. Antes isto era só um aviso impresso no meio de
    # 30 linhas de relatório — fácil de ler como "deu certo". Um corpus com a mistura
    # errada é caro: são 22 h de GPU treinando a proporção errada de idioma.
    problemas = []
    if fontes_vazias:
        problemas.append(f"fonte(s) vazia(s): {', '.join(fontes_vazias)}")
    if fontes_interrompidas:
        problemas.append(f"fonte(s) interrompida(s) no meio: "
                         f"{', '.join(fontes_interrompidas)} — cota incompleta")
    if idiomas_reais:
        pt_real = idiomas_reais.get("pt", 0) / sum(idiomas_reais.values())
        if abs(pt_real - 0.65) > 0.10:
            problemas.append(f"português em {pt_real:.0%} (alvo 65% ±10 pp)")
    if problemas:
        print("\n🔴 CORPUS REPROVADO — não usar para treino:", file=sys.stderr)
        for p in problemas:
            print(f"   • {p}", file=sys.stderr)
        print("   (para o tokenizador ainda serve; para 22 h de GPU, não)", file=sys.stderr)
        return 1
    print("\n✅ corpus aprovado: mistura dentro do alvo e nenhuma fonte vazia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
