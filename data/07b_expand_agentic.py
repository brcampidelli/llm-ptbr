"""Fase 1 (dados) — Expandir as sementes AGENTICAS de dezenas para milhares.

Espelha o 01b_self_instruct (mesma convencao 01/01b do repo), mas o 01b NAO serve
para a abelha agentica: ele rejeita instrucoes que citam arquivos ("no arquivo
acima", "anexado") — justamente o que read_file/write_file/list_dir precisam — e
exige pt_ratio >= 0.7, o que barraria as sementes em ingles (a comeia nao e
restrita a PT-BR).

Aqui a ROTACAO DE CATEGORIA e o proprio catalogo de ferramentas: cada ferramenta
e uma categoria, mais tres categorias que nao usam ferramenta nenhuma. Sem essa
rotacao o professor gravita para web_search e o dataset fica enviesado.

Dedup por Jaccard de n-gramas (reusa common.py) — sem isso o professor gera
parafrases da mesma frase e o dataset fica grande e inutil.

Uso:
    python data/07b_expand_agentic.py --target 300 --dry-run
    python data/07b_expand_agentic.py --target 1500 --workers 12

Saida: data/seeds_agentic_expanded.txt (inclui as sementes originais)
Retomavel: rele a saida e continua.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, DEFAULT_TEACHER, assert_teacher_allowed  # noqa: E402
from common import jaccard, ngrams  # noqa: E402
from teacher_api import call_teacher  # noqa: E402

SEEDS_BASE = DATA_DIR / "seeds_agentic.txt"
OUT_DEFAULT = DATA_DIR / "seeds_agentic_expanded.txt"
TOOLS_FILE = DATA_DIR / "agentic_tools.json"

# Categorias que NAO usam ferramenta. Sao ~1/3 do dataset de proposito:
# over-calling (chamar ferramenta quando nao precisa) e a falha classica.
NO_TOOL_CATEGORIES = [
    ("conhecimento geral", "perguntas de fato/conceito que o modelo responde de cabeca, "
                           "sem consultar nada (historia, ciencia, definicoes)"),
    ("conversa e opiniao", "saudacoes, agradecimentos, pedidos de ideia/opiniao, "
                           "escrita criativa curta"),
    ("pedido AMBIGUO", "pedidos que claramente FALTAM informacao obrigatoria para agir "
                       "(ex: 'leia o arquivo' sem dizer qual). O assistente deve pedir o que falta"),
]

SYSTEM = (
    "Você gera PEDIDOS DE USUÁRIO para treinar um assistente agêntico (que usa "
    "ferramentas). Gere apenas os PEDIDOS, NUNCA as respostas nem os JSONs. "
    "Cada pedido deve ser autocontido, concreto e realista."
)

PROMPT_TOOL = """Um assistente tem esta ferramenta disponível:

  nome: {name}
  descrição: {desc}
  argumentos: {args}

Exemplos de pedidos de usuário que levariam a usar ferramentas:
{examples}

Gere {n} pedidos NOVOS e variados que um usuário faria e que exigiriam a ferramenta **{name}**.

Regras:
- Cada pedido em UMA linha, numerado (1. 2. 3. ...).
- Escreva como o usuário falaria, NÃO mencione o nome da ferramenta.
- Concreto: use cidades, tickers, caminhos, URLs, valores e nomes específicos e plausíveis.
- Varie a forma: pergunta, ordem, pedido educado, frase curta.
- A maioria em português brasileiro; cerca de 1 em 6 em inglês.
- NÃO escreva respostas nem JSON, só os pedidos."""

PROMPT_NO_TOOL = """Exemplos de pedidos de usuário a um assistente:
{examples}

Gere {n} pedidos NOVOS da seguinte categoria: **{name}** — {desc}.

Regras:
- Cada pedido em UMA linha, numerado (1. 2. 3. ...).
- IMPORTANTE: estes pedidos NÃO devem exigir nenhuma ferramenta externa
  (nada de buscar na internet, ler arquivo, consultar banco, cotação, clima, e-mail).
- Aritmética: só contas triviais de 1 ou 2 dígitos (números grandes exigiriam calculadora).
- A maioria em português brasileiro; cerca de 1 em 6 em inglês.
- NÃO escreva respostas, só os pedidos."""

NUM_PREFIX = re.compile(r"^\s*\d+\s*[\.\)\-:]\s*")
NEAR_DUP = 0.7          # Jaccard de trigramas acima disto = parafrase
MIN_LEN, MAX_LEN = 12, 300


def parse_lines(raw: str) -> list[str]:
    out = []
    for line in raw.splitlines():
        line = NUM_PREFIX.sub("", line.strip()).strip(" -*•\t\"")
        if line:
            out.append(line)
    return out


def acceptable(text: str) -> str | None:
    if len(text) < MIN_LEN:
        return "curto demais"
    if len(text) > MAX_LEN:
        return "longo demais"
    if text.count("\n"):
        return "multilinha"
    # o professor as vezes vaza o JSON apesar da instrucao
    if '"tool"' in text or text.strip().startswith("{"):
        return "vazou json/resposta"
    return None


class Pool:
    """Pool de sementes com dedup exato + aproximado (Jaccard de trigramas)."""

    def __init__(self, seeds: list[str]) -> None:
        self.items: list[str] = []
        self.grams: list[set[str]] = []
        self.exact: set[str] = set()
        self.lock = threading.Lock()
        for s in seeds:
            self.add(s)

    def add(self, text: str) -> bool:
        key = text.strip().lower()
        with self.lock:
            if key in self.exact:
                return False
            g = ngrams(text, 3)
            if g and any(jaccard(g, other) > NEAR_DUP for other in self.grams):
                return False
            self.exact.add(key)
            self.items.append(text)
            self.grams.append(g)
            return True

    def sample(self, k: int) -> list[str]:
        with self.lock:
            return random.sample(self.items, min(k, len(self.items)))

    def __len__(self) -> int:
        with self.lock:
            return len(self.items)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1500, help="tamanho final do pool")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--per-call", type=int, default=15, help="pedidos gerados por chamada")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.teacher)      # REGRA DURA: professor aberto
    random.seed(args.seed)

    tools = json.loads(TOOLS_FILE.read_text(encoding="utf-8-sig"))["tools"]
    base = [l.strip() for l in SEEDS_BASE.read_text(encoding="utf-8").splitlines() if l.strip()]

    # retomada: se ja existe saida, parte dela (ja contem as originais)
    start = base
    if args.out.exists():
        prev = [l.strip() for l in args.out.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(prev) >= len(base):
            start = prev
            print(f"[retomada] partindo de {len(prev)} sementes existentes")

    pool = Pool(start)
    # cada ferramenta e uma categoria; mais as 3 sem-ferramenta (peso 2 cada,
    # para chegar perto de 1/3 do dataset sem ferramenta)
    categories: list[tuple[str, str, str]] = [
        ("tool", t["name"], t["description"] + " | args: "
         + ", ".join(t.get("args", {}))) for t in tools
    ]
    categories += [("none", n, d) for n, d in NO_TOOL_CATEGORIES] * 2

    print(f"professor : {args.teacher}")
    print(f"pool      : {len(pool)} -> meta {args.target}")
    print(f"categorias: {len(categories)} ({len(tools)} ferramentas + "
          f"{len(NO_TOOL_CATEGORIES)} sem-ferramenta x2)")
    print(f"saida     : {args.out}")

    if args.dry_run:
        print("\n[dry-run] nada chamado. Exemplo de prompt (ferramenta):\n")
        kind, name, desc = categories[0]
        print(PROMPT_TOOL.format(name=name, desc=desc, args="...",
                                 examples="\n".join(f"- {s}" for s in pool.sample(4)),
                                 n=args.per_call)[:1000])
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY.", file=sys.stderr)
        return 1

    counters = {"novos": 0, "dup": 0, "rej": 0, "fail": 0}
    lock = threading.Lock()
    stop = threading.Event()

    def one_round(i: int) -> None:
        if stop.is_set():
            return
        kind, name, desc = categories[i % len(categories)]
        examples = "\n".join(f"- {s}" for s in pool.sample(5))
        if kind == "tool":
            prompt = PROMPT_TOOL.format(name=name, desc=desc.split(" | args: ")[0],
                                        args=desc.split(" | args: ")[-1],
                                        examples=examples, n=args.per_call)
        else:
            prompt = PROMPT_NO_TOOL.format(name=name, desc=desc,
                                           examples=examples, n=args.per_call)
        try:
            raw = call_teacher(prompt, args.teacher, api_key, system=SYSTEM,
                               temperature=1.0, max_tokens=1200)
        except Exception as e:
            with lock:
                counters["fail"] += 1
                print(f"  FALHA: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(15.0 if "429" in str(e) else 2.0)
            return

        for cand in parse_lines(raw):
            why = acceptable(cand)
            if why:
                with lock:
                    counters["rej"] += 1
                continue
            if pool.add(cand):
                with lock:
                    counters["novos"] += 1
            else:
                with lock:
                    counters["dup"] += 1
        with lock:
            n = len(pool)
            print(f"  pool={n}/{args.target} novos={counters['novos']} "
                  f"dup={counters['dup']} rej={counters['rej']} falhas={counters['fail']}",
                  flush=True)
            if n >= args.target:
                stop.set()

    # rodadas suficientes para a meta, com folga para duplicatas
    est = max(1, (args.target - len(pool)) // max(1, args.per_call // 2))
    print(f"workers   : {args.workers} | rodadas estimadas: {est}\n")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(one_round, range(est * 2)))

    args.out.write_text("\n".join(pool.items) + "\n", encoding="utf-8")
    print(f"\nConcluido: {len(pool)} sementes -> {args.out}")
    print(f"Proximo: python data/07_distill_agentic.py --seeds {args.out} --workers 16")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
