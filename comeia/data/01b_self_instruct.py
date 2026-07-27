"""Fase 2.1b — Self-Instruct: escalar as sementes de dezenas para milhares.

Método (Wang et al., Self-Instruct): amostra instruções do pool existente como
few-shot, pede ao professor N instruções NOVAS, filtra as ruins e as parecidas
demais, e devolve as aprovadas ao pool. Repete até a meta.

O filtro de similaridade é o que impede o colapso de diversidade — sem ele o
modelo gera variações da mesma pergunta e o dataset fica grande e inútil.

Uso:
    python data/01b_self_instruct.py --target 500 --dry-run
    python data/01b_self_instruct.py --target 2000
    python data/01b_self_instruct.py --target 5000 --teacher deepseek/deepseek-v4-flash

Retomável: relê o arquivo de saída e continua de onde parou.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEFAULT_TEACHER, DATA_DIR, assert_teacher_allowed  # noqa: E402
from common import jaccard, ngrams, pt_ratio  # noqa: E402
from teacher_api import TeacherError, call_teacher  # noqa: E402

OUT_DEFAULT = DATA_DIR / "seeds_ptbr_expanded.txt"

# Rotação de domínios: força cobertura ampla. Sem isto o professor gravita para
# 3-4 assuntos favoritos e a diversidade morre.
DOMAINS = [
    "conhecimento geral e ciência",
    "raciocínio lógico e problemas de matemática",
    "programação, tecnologia e dados",
    "escrita e comunicação profissional",
    "resumo, extração e reescrita de texto",
    "análise crítica e tomada de decisão",
    "cultura, história e geografia do Brasil",
    "direito, burocracia e serviços públicos brasileiros",
    "negócios, finanças pessoais e empreendedorismo",
    "saúde e bem-estar (informativo, sem diagnóstico)",
    "educação, concursos e vestibular",
    "tradução e questões de linguagem",
    "segurança digital, privacidade e golpes",
    "vida cotidiana, viagens e serviços",
]

FORMATS = [
    "pergunta direta que exige explicação",
    "pedido de lista ou comparação",
    "pedido de passo a passo / tutorial",
    "cenário prático em que o usuário pede ajuda",
    "pedido de correção ou melhoria de um texto",
    "problema que exige cálculo com números concretos",
]

SYSTEM = (
    "Você gera instruções de treinamento em português brasileiro para um assistente de IA. "
    "Gere apenas as INSTRUÇÕES (o que o usuário pediria), NUNCA as respostas. "
    "Cada instrução deve ser autocontida, concreta e realista."
)

PROMPT_TMPL = """Abaixo estão exemplos de instruções que usuários brasileiros fazem a um assistente:

{examples}

Gere {n} instruções NOVAS e DIFERENTES das acima, sobre o tema: **{domain}**.
Use preferencialmente este formato: {fmt}.

Regras:
- Português brasileiro natural.
- Cada instrução em UMA linha, numerada (1. 2. 3. ...).
- Autocontida: não faça referência a arquivos, imagens, áudio ou vídeo.
- Concreta: prefira números, nomes e situações específicas a perguntas vagas.
- NÃO escreva as respostas, só as instruções.
- Varie bastante o assunto dentro do tema."""

# Instruções que não servem para treino de modelo de TEXTO.
REJECT_PAT = re.compile(
    r"\b(imagem|foto|figura|áudio|audio|vídeo|video|gráfico anexo|desenhe|ilustre|"
    r"anexad[oa]|no arquivo acima|link acima|planilha anexa)\b",
    re.IGNORECASE,
)
NUM_PREFIX = re.compile(r"^\s*\d+\s*[\.\)\-:]\s*")


def parse_instructions(raw: str) -> list[str]:
    out = []
    for line in raw.splitlines():
        line = NUM_PREFIX.sub("", line.strip())
        line = line.strip(" -*•\t")
        if line:
            out.append(line)
    return out


def acceptable(inst: str) -> str | None:
    """Retorna motivo da rejeição, ou None se passa."""
    n = len(inst)
    if n < 20:
        return "curta demais"
    if n > 320:
        return "longa demais"
    if REJECT_PAT.search(inst):
        return "exige midia/anexo"
    if pt_ratio(inst) < 0.7:
        return "nao parece portugues"
    if inst.count("?") > 3:
        return "multiplas perguntas empilhadas"
    return None


class Pool:
    """Pool de instruções com dedup por similaridade (índice invertido de n-gramas)."""

    def __init__(self, threshold: float, n: int = 3) -> None:
        self.threshold = threshold
        self.n = n
        self.items: list[str] = []
        self._grams: list[set[str]] = []
        self._index: dict[str, list[int]] = defaultdict(list)

    def too_similar(self, text: str) -> bool:
        g = ngrams(text, self.n)
        if not g:
            return False
        cands: set[int] = set()
        for gram in g:
            cands.update(self._index[gram])
        return any(jaccard(g, self._grams[i]) >= self.threshold for i in cands)

    def add(self, text: str) -> None:
        g = ngrams(text, self.n)
        idx = len(self.items)
        self.items.append(text)
        self._grams.append(g)
        for gram in g:
            self._index[gram].append(idx)

    def __len__(self) -> int:
        return len(self.items)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=Path, default=DATA_DIR / "seeds_ptbr.txt")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--target", type=int, default=2000, help="total de instrucoes desejado")
    ap.add_argument("--batch", type=int, default=20, help="instrucoes pedidas por chamada")
    ap.add_argument("--shots", type=int, default=6, help="exemplos few-shot por chamada")
    ap.add_argument("--similarity", type=float, default=0.55, help="limiar de dedup (Jaccard 3-gram)")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.teacher)
    rng = random.Random(args.seed)

    if not args.seeds.exists():
        print(f"ERRO: sementes nao encontradas: {args.seeds}", file=sys.stderr)
        return 1
    original = [l.strip() for l in args.seeds.read_text(encoding="utf-8").splitlines() if l.strip()]

    pool = Pool(threshold=args.similarity)
    for s in original:
        pool.add(s)
    n_original = len(pool)

    # Retomada: o arquivo de saida contem original + geradas.
    generated: list[str] = []
    if args.out.exists():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not pool.too_similar(line):
                pool.add(line)
                generated.append(line)
        print(f"[retomada] {len(generated)} instrucoes ja geradas em {args.out.name}")

    print(f"professor : {args.teacher}")
    print(f"sementes  : {n_original} originais | pool atual: {len(pool)}")
    print(f"meta      : {args.target}")
    print(f"dedup     : Jaccard 3-gram >= {args.similarity}\n")

    if args.dry_run:
        ex = "\n".join(f"- {s}" for s in rng.sample(original, min(args.shots, len(original))))
        print("[dry-run] exemplo de prompt que seria enviado:\n")
        print("-" * 70)
        print(PROMPT_TMPL.format(examples=ex, n=args.batch, domain=DOMAINS[0], fmt=FORMATS[0]))
        print("-" * 70)
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY (ou preencha o .env).", file=sys.stderr)
        return 1

    stats: dict[str, int] = defaultdict(int)
    rounds = 0
    stagnant = 0

    with args.out.open("a", encoding="utf-8") as fout:
        while len(pool) < args.target:
            rounds += 1
            domain = DOMAINS[rounds % len(DOMAINS)]
            fmt = FORMATS[rounds % len(FORMATS)]
            shots = rng.sample(pool.items, min(args.shots, len(pool)))
            prompt = PROMPT_TMPL.format(
                examples="\n".join(f"- {s}" for s in shots),
                n=args.batch,
                domain=domain,
                fmt=fmt,
            )

            try:
                raw = call_teacher(
                    prompt, args.teacher, api_key,
                    system=SYSTEM, temperature=1.0, max_tokens=2048,
                )
            except Exception as e:
                stats["falha_api"] += 1
                print(f"  [round {rounds}] FALHA: {type(e).__name__}: {e}", file=sys.stderr)
                time.sleep(15.0 if "429" in str(e) else 3.0)
                continue

            added = 0
            for inst in parse_instructions(raw):
                why = acceptable(inst)
                if why:
                    stats[why] += 1
                    continue
                if pool.too_similar(inst):
                    stats["similar demais"] += 1
                    continue
                pool.add(inst)
                generated.append(inst)
                fout.write(inst + "\n")
                added += 1

            fout.flush()
            stagnant = stagnant + 1 if added == 0 else 0
            print(f"  [round {rounds}] +{added:>2} | pool={len(pool):>5}/{args.target} | {domain[:38]}")

            if stagnant >= 8:
                print("\nPool saturado: 8 rodadas seguidas sem instrucao nova.")
                print("Aumente --similarity (aceita mais parecidas) ou adicione dominios em DOMAINS.")
                break
            time.sleep(args.sleep)

    print(f"\n{'='*60}")
    print(f"pool final : {len(pool)} instrucoes ({n_original} originais + {len(generated)} geradas)")
    print(f"rodadas    : {rounds}")
    print("rejeicoes  :")
    for why, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"    {why}: {n}")
    print(f"\nsalvo em {args.out}")
    print(f"Proximo: python data/01_distill_teacher.py --seeds {args.out} --teacher {args.teacher}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
