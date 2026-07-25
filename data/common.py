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


# --- Raciocínio (<think>) -----------------------------------------------------

# Bloco fechado: <think>...</think> — o que sobra depois é a resposta.
_THINK_CLOSED = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Bloco ABERTO e nunca fechado: acontece quando max_new_tokens corta no meio do
# raciocínio. Aí NÃO existe resposta — o texto inteiro é raciocínio.
_THINK_OPEN = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)
# Alguns modelos emitem só o fechamento (o <think> vem no template do chat).
_THINK_CLOSE_ONLY = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> tuple[str, bool]:
    """Remove o raciocínio e devolve (resposta, truncado).

    `truncado=True` significa que o modelo foi cortado ANTES de fechar o
    raciocínio — não há resposta final, só raciocínio. Quem chama decide o que
    fazer (avisar, reduzir prompt, ou aumentar max_new_tokens).
    """
    out = _THINK_CLOSED.sub("", text)
    if "</think>" in out.lower():          # fechamento órfão (abertura no template)
        out = _THINK_CLOSE_ONLY.sub("", out, count=1)
    if "<think>" in out.lower():           # abertura sem fechamento -> truncado
        out = _THINK_OPEN.sub("", out)
        return out.strip(), True
    return out.strip(), False


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

# --- Detecção de idioma (pt/en/es/fr) — determinística, sem dependência -------
# Serve para medir se o modelo RESPONDE NO IDIOMA DA PERGUNTA. É o modo de falha
# mais provável de um adapter treinado só em PT-BR sobre um backbone de 201
# idiomas: perguntam em inglês, ele responde em português. Isso é mensurável sem
# juiz e sem API.
#
# ⚠️ Mesma armadilha do _AMBIGUOUS acima, agora entre 4 idiomas: "a", "de", "en",
# "la", "e"... aparecem em vários. Só ficam os marcadores EXCLUSIVOS de cada um.
# ⚠️ PT e ES compartilham quase toda palavra funcional (que, para, mas, porque,
# sobre, ser, esta...). Depois da deduplicação sobravam pouquíssimos marcadores
# de PT e frases factuais sem "não/você" ficavam indetectáveis. Por isso as
# listas incluem MUITAS funcionais de cada idioma — o que sobrevive ao corte é o
# que de fato distingue.
_LANG_RAW = {
    "pt": {"nao", "uma", "com", "voce", "muito", "isso", "seu", "sua", "pelo",
           "pela", "quando", "tambem", "entao", "sao", "fazer", "tem", "pode",
           "ate", "das", "dos", "aos", "nas", "essa", "esse", "onde", "ja",
           "ainda", "sempre", "assim", "sem", "apenas", "depois", "aqui",
           "agora", "quem", "qual", "melhor", "maior", "coisa", "tempo", "vez",
           "dia", "ele", "eles", "elas", "nosso", "meu", "minha", "foi", "eh"},
    "en": {"the", "and", "you", "that", "this", "with", "for", "your", "are",
           "have", "can", "will", "from", "they", "what", "when", "about",
           "which", "there", "would", "should", "make", "more", "but", "because",
           "water", "salt", "rain", "them", "where", "while", "than", "then",
           "some", "such", "also", "into", "over", "after", "before", "each",
           "very", "most", "just", "like", "time", "way", "day", "does", "did"},
    "es": {"una", "con", "usted", "muy", "esto", "pero", "cuando", "tambien",
           "entonces", "puede", "hacer", "tiene", "los", "las", "del", "porque",
           "donde", "ya", "siempre", "asi", "sin", "solo", "despues", "aqui",
           "ahora", "quien", "cual", "mejor", "mayor", "cosa", "tiempo", "vez",
           "dia", "ellos", "ellas", "nuestro", "mi", "fue", "sal", "agua",
           "lluvia", "roca", "mar", "hacia", "sobre", "entre", "entre"},
    "fr": {"une", "avec", "pour", "vous", "tres", "cela", "parce", "quand",
           "aussi", "alors", "peut", "faire", "les", "des", "dans", "votre",
           "nous", "sont", "ce", "qui", "mais", "ou", "deja", "toujours",
           "ainsi", "sans", "seulement", "apres", "ici", "maintenant", "meilleur",
           "chose", "temps", "fois", "jour", "ils", "elles", "notre", "mon",
           "etait", "eau", "sel", "pluie", "roche", "mer", "vers", "entre"},
}
# remove tudo que aparece em mais de um idioma
_seen: dict[str, int] = {}
for _toks in _LANG_RAW.values():
    for _t in _toks:
        _seen[_t] = _seen.get(_t, 0) + 1
LANG_MARKERS = {k: {t for t in v if _seen[t] == 1} for k, v in _LANG_RAW.items()}

# ⭐ ORTOGRAFIA DISTINTIVA — o sinal mais forte, sobretudo para separar PT de ES,
# que compartilham vocabulário demais. Pesa mais que palavra funcional porque
# "ção/nh/lh" só existe em português e "ción/ñ" só em espanhol.
_LANG_PATTERNS = {
    "pt": [r"ç", r"ã", r"õ", r"nh", r"lh", r"ções\b", r"ção\b", r"\bnão\b",
           r"\bvocê\b", r"\bé\b", r"\bmas\b.{0,40}\bque\b"],
    "es": [r"ñ", r"¿", r"¡", r"ción\b", r"ciones\b", r"\bel\b", r"\blos\b",
           r"\bpero\b", r"\bmuy\b", r"\bhay\b"],
    "fr": [r"œ", r"ê", r"û", r"à\b", r"\bqu'", r"\bd'", r"\bl'", r"eux\b",
           r"\bcette\b", r"\best\b", r"\bles\b", r"\bune\b"],
    "en": [r"\bthe\b", r"\bof\b", r"\bto\b", r"\bis\b", r"\bit\b", r"'s\b",
           r"\bing\b|ing\b", r"\byou\b"],
}
_LANG_RE = {k: [re.compile(p, re.IGNORECASE) for p in v]
            for k, v in _LANG_PATTERNS.items()}


def detect_lang(text: str) -> str:
    """'pt' | 'en' | 'es' | 'fr' | '?' — heurística barata, não é detector real.

    Serve para medir CONSISTÊNCIA DE IDIOMA (o modelo respondeu no idioma da
    pergunta?), não para classificar texto em produção. Combina ortografia
    distintiva (peso 2 — é o que separa PT de ES) com palavras funcionais
    exclusivas (peso 1). Devolve '?' quando o sinal é fraco ou empatado: chutar
    seria pior que admitir indefinição.
    """
    if not text or not text.strip():
        return "?"
    low = text.lower()
    score = {k: 0.0 for k in _LANG_RE}
    for k, pats in _LANG_RE.items():
        score[k] += 2.0 * sum(1 for p in pats if p.search(low))
    toks = set(normalize(text).split())
    for k, marks in LANG_MARKERS.items():
        score[k] += len(toks & marks)
    ordenado = sorted(score.values(), reverse=True)
    if ordenado[0] < 3 or (len(ordenado) > 1 and ordenado[0] == ordenado[1]):
        return "?"
    return max(score, key=lambda k: score[k])


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
