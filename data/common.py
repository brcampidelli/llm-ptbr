"""Utilitários compartilhados do pipeline de dados (I/O jsonl, normalização, n-gramas)."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator


# --- I/O ----------------------------------------------------------------------

def read_jsonl(path: Path) -> Iterator[dict]:
    # utf-8-sig: remove o BOM se existir e funciona igual em arquivo sem BOM.
    # No Windows, `Set-Content -Encoding UTF8` (PS 5.1) grava COM BOM e o BOM
    # quebra o json.loads da primeira linha.
    with path.open("r", encoding="utf-8-sig") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON invalido em {path}:{lineno}: {e}") from e


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


# --- Normalização e n-gramas --------------------------------------------------

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(text: str) -> str:
    """Normaliza para comparação: minúsculas, sem acento, sem pontuação, espaços colapsados."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()


def ngrams(text: str, n: int) -> set[str]:
    """Conjunto de n-gramas de PALAVRAS do texto normalizado."""
    toks = normalize(text).split()
    if len(toks) < n:
        return set()
    return {" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# --- Heurística de "portuguesidade" ------------------------------------------
# Barato e sem dependência: detecta se o texto parece PT-BR pela presença de
# stopwords/marcas do idioma. Não substitui um detector real, mas pega tradução
# malfeita e texto que ficou em inglês.

_PT_MARKERS = {
    "de", "que", "e", "o", "a", "os", "as", "do", "da", "dos", "das", "em", "um",
    "uma", "para", "com", "nao", "por", "mais", "como", "mas", "ao", "ele", "ela",
    "seu", "sua", "ou", "quando", "muito", "ja", "esta", "voce", "sao", "pelo",
}
_EN_MARKERS = {
    "the", "of", "and", "to", "in", "is", "you", "that", "it", "for", "on", "with",
    "as", "are", "this", "be", "or", "at", "your", "from", "have", "was", "we",
}

# Tokens que existem nos DOIS idiomas não carregam sinal — pior, distorcem a conta.
# Ex.: "às 8h" normaliza para "as", que também é palavra inglesa; sem esta remoção,
# todo texto português com horários era penalizado como se fosse inglês.
_AMBIGUOUS = _PT_MARKERS & _EN_MARKERS
_PT_MARKERS -= _AMBIGUOUS
_EN_MARKERS -= _AMBIGUOUS


_FENCED = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_INDENTED = re.compile(r"^(?: {4}|\t).*$", re.MULTILINE)


def strip_code(text: str) -> str:
    """Remove blocos de código antes de medir 'portuguesidade'.

    Sem isto, uma resposta em português com um trecho de Python/SQL é rejeitada
    porque `import`, `from`, `return`, `select`, `where` contam como marcadores
    de inglês. Era a causa de falso positivo em TODO exemplo de código.
    """
    text = _FENCED.sub(" ", text)
    text = _INLINE_CODE.sub(" ", text)
    text = _INDENTED.sub(" ", text)
    return text


def pt_ratio(text: str, ignore_code: bool = True) -> float:
    """Fração PT vs (PT+EN) entre as palavras-marcador. 1.0 = claramente português.

    Mede só a PROSA (código removido por padrão).
    """
    if ignore_code:
        text = strip_code(text)
    toks = normalize(text).split()
    if not toks:
        return 0.0
    pt = sum(1 for t in toks if t in _PT_MARKERS)
    en = sum(1 for t in toks if t in _EN_MARKERS)
    total = pt + en
    if total < 3:
        # poucos marcadores (resposta matematica/curta) — o sinal e fraco demais
        # para julgar idioma. Nao rejeitar por isto; outros filtros cuidam.
        return 1.0
    return pt / total
