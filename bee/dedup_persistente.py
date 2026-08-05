"""Dedup por MinHash-LSH que SOBREVIVE ao processo.

⭐ O BURACO QUE ISTO FECHA (medido em 2026-08-04, `bee/medir_dedup.py`)
  O `Dedup` de `build_corpus.py`/`expand_corpus.py` vive so em RAM e nasce VAZIO a
  cada execucao. Pega quase-duplicata DENTRO de um lote e nao entre o corpus ja
  coletado e a expansao. Medido na fonte: **0,90%** de quase-duplicata atravessa
  essa fronteira (contra 0,53-0,73% dentro do lote, que o MinHash pega).
  E' o mesmo defeito que o `sha_doc` ja resolveu para duplicata EXATA em
  2026-07-27 — so que para quase-duplicata ninguem tinha fechado.

⚠️ DUAS ARMADILHAS QUE TORNAM ISTO NAO-TRIVIAL

1. **`hash()` de tupla e' randomizado por processo** (PYTHONHASHSEED). O `Dedup`
   original usa `hash(sig[...])` — correto dentro de uma execucao, mas persistir
   isso daria chave DIFERENTE na execucao seguinte e o dedup falharia **em
   silencio**, parecendo funcionar. Aqui a chave e' blake2b, estavel entre
   processos, versoes e maquinas.

2. **Escala.** ~10M documentos x 16 bandas = 160M chaves. Em `set` de int do
   Python isso passa de 10 GB. Bloom filter resolve em ~300 MB.

⚠️ O PRECO DO BLOOM: falso positivo descarta documento UNICO (nunca deixa passar
  duplicata — falso negativo e' impossivel). Com a taxa padrao de ~0,1%,
  perde-se 0,1% de documento bom para recuperar os 0,90% de duplicata. Troca
  vantajosa por ~9x, e o numero fica registrado no `.meta` para auditoria.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

_PALAVRA = re.compile(r"\w+")


def shingles(texto: str, k: int = 5) -> set[str]:
    palavras = _PALAVRA.findall(unicodedata.normalize("NFKC", texto).casefold())
    if len(palavras) < k:
        return {" ".join(palavras)} if palavras else set()
    return {" ".join(palavras[i:i + k]) for i in range(len(palavras) - k + 1)}


def minhash(texto: str, n_perm: int = 64) -> tuple[int, ...]:
    """Assinatura MinHash — identica a de build_corpus.py (mesma semente, mesmo XOR)."""
    sh = shingles(texto)
    if not sh:
        return tuple([0] * n_perm)
    hashes = [int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:16], 16) for s in sh]
    return tuple(min(h ^ (i * 0x9E3779B97F4A7C15) for h in hashes) for i in range(n_perm))


class DedupPersistente:
    """LSH por bandas sobre MinHash, em Bloom filter que grava e recarrega do disco.

    Uso:
        d = DedupPersistente(Path("corpus/lsh_bandas.bin"))
        if d.duplicado(texto): ...
        d.fechar()                     # grava; sem isto o aprendizado do run se perde
    """

    def __init__(self, caminho: Path | None = None, bandas: int = 16, n_perm: int = 64,
                 docs_esperados: int = 20_000_000, fp: float = 0.001):
        self.caminho = Path(caminho) if caminho else None
        self.bandas, self.n_perm = bandas, n_perm
        self.largura = n_perm // bandas
        self.vistos = 0
        self.descartados = 0

        # Dimensionamento padrao de Bloom: m = -n·ln(p)/(ln2)², k = (m/n)·ln2
        n = max(1, docs_esperados * bandas)
        self.n_bits = int(-n * math.log(fp) / (math.log(2) ** 2))
        self.n_bits += (-self.n_bits) % 8            # múltiplo de 8
        self.k = max(1, round((self.n_bits / n) * math.log(2)))
        self.fp_alvo = fp

        self.bits = bytearray(self.n_bits // 8)
        self.itens = 0
        if self.caminho and self.caminho.exists():
            self._carregar()

    # ---------------------------------------------------------------- disco --
    def _meta_path(self) -> Path:
        return self.caminho.with_suffix(self.caminho.suffix + ".meta")

    def _carregar(self) -> None:
        meta_p = self._meta_path()
        if not meta_p.exists():
            print(f"  [dedup] {self.caminho.name} sem .meta — ignorando (nao da p/ validar)")
            return
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        # Parametro diferente => as chaves nao sao comparaveis. Falhar alto, nao em silencio.
        for campo in ("n_bits", "k", "bandas", "n_perm"):
            if meta.get(campo) != getattr(self, campo):
                raise ValueError(
                    f"{self.caminho.name}: {campo} do disco ({meta.get(campo)}) difere do "
                    f"atual ({getattr(self, campo)}). As chaves nao sao comparaveis — "
                    f"apague o arquivo para recomecar, ou use os mesmos parametros.")
        dados = self.caminho.read_bytes()
        if len(dados) != len(self.bits):
            raise ValueError(f"{self.caminho.name}: tamanho inesperado")
        self.bits = bytearray(dados)
        self.itens = meta.get("itens", 0)
        print(f"  [dedup] carregado: {self.itens:,} chaves de execucoes anteriores "
              f"({self.ocupacao():.1%} do filtro, fp estimado {self.fp_atual():.3%})")

    def fechar(self) -> None:
        if not self.caminho:
            return
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_bytes(bytes(self.bits))
        self._meta_path().write_text(json.dumps({
            "n_bits": self.n_bits, "k": self.k, "bandas": self.bandas,
            "n_perm": self.n_perm, "itens": self.itens, "fp_alvo": self.fp_alvo,
            "fp_estimado": round(self.fp_atual(), 6),
        }, indent=2), encoding="utf-8")

    # ------------------------------------------------------------- interno ---
    def _posicoes(self, banda: int, chave: bytes):
        # blake2b com a banda no 'person' → estavel entre processos e separa as bandas.
        h = hashlib.blake2b(chave, digest_size=16,
                            person=banda.to_bytes(2, "big") + b"beelsh").digest()
        a = int.from_bytes(h[:8], "big")
        b = int.from_bytes(h[8:], "big") | 1        # ímpar: garante passo != 0
        for i in range(self.k):
            yield ((a + i * b) % self.n_bits)

    def ocupacao(self) -> float:
        return sum(bin(b).count("1") for b in self.bits) / self.n_bits

    def fp_atual(self) -> float:
        """Falso positivo estimado pela ocupacao real — nao pelo n esperado."""
        return self.ocupacao() ** self.k

    # -------------------------------------------------------------- publico --
    def duplicado(self, texto: str) -> bool:
        sig = minhash(texto, self.n_perm)
        # ⚠️ Mascarar em 64 bits: na assinatura o XOR e' com `i * 0x9E3779B9...`, que
        # para i alto passa de 2^64. No original isso nao aparecia porque `hash()`
        # aceita int de qualquer tamanho; aqui empacotamos em bytes fixos.
        chaves = [b"".join((x & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big") for x in
                           sig[i * self.largura:(i + 1) * self.largura])
                  for i in range(self.bandas)]
        # Uma banda inteira batendo já é quase-duplicata (é a semântica do LSH).
        for banda, chave in enumerate(chaves):
            if all(self.bits[p >> 3] & (1 << (p & 7)) for p in self._posicoes(banda, chave)):
                self.descartados += 1
                return True
        for banda, chave in enumerate(chaves):
            for p in self._posicoes(banda, chave):
                self.bits[p >> 3] |= 1 << (p & 7)
        self.itens += self.bandas
        self.vistos += 1
        return False
