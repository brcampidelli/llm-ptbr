"""Fase 2 (dados) — Gerar tarefas de função Python VERIFICÁVEIS para a abelha coder.

Escolha de escopo (deliberada): "escrever uma função Python dado assinatura +
docstring", verificada por EXECUÇÃO. Motivo: arXiv 2607.08938 mediu ρ = −0,96
entre diversidade de tarefa e ganho de especialização (89,1% → 68,0% do escopo
mais estreito ao mais amplo). "Assistente de código geral" cairia no regime onde
o ganho evapora; função testável é estreito e tem sinal objetivo.

⭐ A VALIDAÇÃO QUE FAZ ESTE DADO SER LIMPO — auto-consistência do professor:
o professor gera a tarefa (assinatura + docstring), os TESTES e a SOLUÇÃO. Só
guardamos o item se **a solução dele passar nos testes dele**, executados de
verdade (data/code_exec.py). Isso descarta automaticamente:
  - especificação ambígua (a solução não bate com o teste),
  - teste errado,
  - solução errada.
Nenhum juiz LLM envolvido — o veredito é do interpretador.

REGRA DURA: professor ABERTO (assert_teacher_allowed).

Uso:
    python data/08_gen_coder_tasks.py --target 40 --dry-run
    python data/08_gen_coder_tasks.py --target 800 --workers 12

Saída: data/raw/coder_tasks.jsonl  ({name, prompt, tests, solution})
Retomável.
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
from config import DEFAULT_TEACHER, RAW_DIR, assert_teacher_allowed, ensure_dirs  # noqa: E402
from common import jaccard, ngrams, read_jsonl  # noqa: E402
from code_exec import run_tests, extract_code, scan_forbidden  # noqa: E402
from teacher_api import call_teacher  # noqa: E402

OUT = RAW_DIR / "coder_tasks.jsonl"

# Rotação de temas: sem isso o professor gravita para "inverter string" e
# "fibonacci" e o dataset fica grande e redundante.
TEMAS = [
    "manipulação de strings (busca, formatação, validação)",
    "listas e dicionários (agrupar, filtrar, ordenar, achatar)",
    "matemática e números (divisibilidade, primos, bases, arredondamento)",
    "datas e tempo (diferença, formatação, dia útil) usando só datetime",
    "parsing de texto simples (CSV em string, chave=valor, log)",
    "validação de dados brasileiros (CPF, CEP, telefone, placa)",
    "algoritmos clássicos (busca binária, dois ponteiros, janela deslizante)",
    "recursão e programação dinâmica simples (memoização)",
    "conjuntos e contagem (frequência, duplicatas, interseção)",
    "conversão de formatos (snake_case/camelCase, romano, bytes legíveis)",
    "estatística descritiva sem bibliotecas (média, mediana, moda, desvio)",
    "operações com matrizes como lista de listas (transpor, rotacionar, somar)",
]

SYSTEM = (
    "Você cria exercícios de programação Python de alta qualidade, no formato JSON. "
    "As funções devem ser PURAS: sem I/O, sem rede, sem arquivos, sem imports além "
    "de `datetime`, `math`, `re`, `collections`, `itertools` e `functools`."
)

PROMPT_TMPL = """Crie {n} exercícios de função Python sobre o tema: **{tema}**.
{exclusoes}{dificuldade}

Devolva APENAS um array JSON, sem texto em volta. Cada item:
{{
  "name": "nome_da_funcao",
  "prompt": "def nome_da_funcao(args) -> tipo:\\n    \\"\\"\\"Docstring em português explicando o que faz, com um exemplo.\\"\\"\\"",
  "tests": ["assert nome_da_funcao(...) == ...", "assert ...", "assert ..."],
  "solution": "def nome_da_funcao(args) -> tipo:\\n    # implementacao completa\\n    ..."
}}

Regras rígidas:
- "prompt" contém SÓ a assinatura + docstring (NÃO inclua a implementação).
- "solution" é a implementação COMPLETA e correta, repetindo a assinatura.
- "tests" tem 3 a 5 asserts que passam com a solution, cobrindo caso normal, borda e vazio/zero.
- Função PURA: sem input(), open(), os, sys, requests, print obrigatório.
- Docstring em português brasileiro.
- Varie a dificuldade: algumas triviais, a maioria média, algumas difíceis.
- Nomes de função em snake_case e em inglês ou português, mas consistentes com a docstring."""

_ARRAY_RE = re.compile(r"\[\s*\{.*\}\s*\]", re.DOTALL)

# ─────────────────────── pressão de diversidade e dificuldade ─────────────────
# Achado real (2026-07-25): 189 de ~619 candidatas (30%) saíram DUPLICADAS — o
# professor converge para as mesmas tarefas apesar da rotação de temas. E o filtro
# "o base erra" mostrou que só 20,3% são difíceis o bastante para ensinar algo.
# Estas duas injeções atacam os dois gargalos direto no prompt.

def bloco_exclusoes(nomes: list[str], k: int = 40) -> str:
    """Manda uma amostra dos nomes já criados como PROIBIDOS (anti-duplicata)."""
    if not nomes:
        return ""
    amostra = random.sample(nomes, min(k, len(nomes)))
    return ("\n\n⚠️ Estes exercícios JÁ EXISTEM. NÃO os repita nem crie variações "
            "próximas deles:\n" + ", ".join(sorted(amostra)))


# O modelo-alvo (Qwen3.5-4B) acerta 80% dos exercícios de livro-texto. Pedir
# dificuldade explicitamente eleva o aproveitamento do filtro. As categorias vêm
# de COMO o base erra de fato: 78% por assert falhou (caso de borda / detalhe de
# especificação), 22% por erro de execução.
BLOCO_DIFICULDADE = """

⚠️ DIFICULDADE — um modelo de 4B já resolve exercício de livro-texto. Faça exercícios
que exijam PRECISÃO, não só a ideia geral. Priorize:
- casos de borda que quebram a solução ingênua (vazio, um elemento, empate, negativo,
  zero, limites, unicode/acentos, maiúsculas, duplicatas);
- detalhes de ESPECIFICAÇÃO que precisam ser seguidos à risca (regra de arredondamento
  e desempate, ordem exata da saída, formato exato da string, o que fazer em erro);
- restrições que proíbem o caminho óbvio ("sem usar math", "sem sorted", "in-place",
  "uma passada só", "sem regex");
- composição de duas regras que interagem (ex.: filtrar E agrupar E ordenar por 2 chaves).
Inclua nos testes ao menos um assert de caso de borda que a solução ingênua erraria."""


def parse_items(raw: str) -> list[dict]:
    """Extrai o array JSON da resposta (tolera cerca ```json e texto em volta)."""
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = s.rsplit("```", 1)[0]
    m = _ARRAY_RE.search(s)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)]


def valid_shape(it: dict) -> str | None:
    """Checagem estrutural antes de gastar execução."""
    for k in ("name", "prompt", "tests", "solution"):
        if k not in it:
            return f"falta campo {k}"
    if not isinstance(it["tests"], list) or len(it["tests"]) < 2:
        return "menos de 2 testes"
    if not all(isinstance(t, str) and t.strip().startswith("assert") for t in it["tests"]):
        return "teste que nao e assert"
    name = it["name"]
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", str(name)):
        return f"nome invalido: {name!r}"
    if f"def {name}" not in it["prompt"]:
        return "prompt nao declara a funcao"
    if f"def {name}" not in it["solution"]:
        return "solution nao declara a funcao"
    if '"""' not in it["prompt"] and "'''" not in it["prompt"]:
        return "prompt sem docstring"
    for campo in ("prompt", "solution"):
        bad = scan_forbidden(it[campo])
        if bad:
            return f"{campo} usa padrao proibido: {bad}"
    return None


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=800, help="tarefas VALIDADAS desejadas")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--per-call", type=int, default=6)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--temperature", type=float, default=1.0,
                    help="mais alta = mais diversidade (30%% das candidatas saiam duplicadas)")
    ap.add_argument("--no-exclusions", action="store_true",
                    help="desliga a lista de nomes proibidos (anti-duplicata)")
    ap.add_argument("--no-hard-hint", action="store_true",
                    help="desliga a pressao por dificuldade (so 20,3%% passavam no filtro)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.teacher)       # REGRA DURA: professor aberto
    ensure_dirs()
    random.seed(args.seed)

    # Retomada + dedup por nome e por similaridade da docstring.
    existentes: list[dict] = list(read_jsonl(OUT)) if OUT.exists() else []
    nomes = {r["name"] for r in existentes if "name" in r}
    grams = [ngrams(r.get("prompt", ""), 3) for r in existentes]
    if existentes:
        print(f"[retomada] {len(existentes)} tarefas validadas ja no arquivo")

    print(f"professor : {args.teacher}")
    print(f"temas     : {len(TEMAS)}")
    print(f"meta      : {args.target} tarefas VALIDADAS (solucao passa nos proprios testes)")
    print(f"saida     : {OUT}")

    if args.dry_run:
        print(f"temperatura: {args.temperature} | exclusoes: {not args.no_exclusions} "
              f"| pressao de dificuldade: {not args.no_hard_hint}")
        print("\n[dry-run] nada chamado. Prompt do primeiro tema:\n")
        print(PROMPT_TMPL.format(
            n=args.per_call, tema=TEMAS[0],
            exclusoes=bloco_exclusoes(sorted(nomes)) if not args.no_exclusions else "",
            dificuldade="" if args.no_hard_hint else BLOCO_DIFICULDADE))
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY.", file=sys.stderr)
        return 1

    c = {"ok": 0, "shape": 0, "exec_fail": 0, "dup": 0, "api_fail": 0}
    lock = threading.Lock()
    stop = threading.Event()

    def rodada(i: int) -> None:
        if stop.is_set():
            return
        tema = TEMAS[i % len(TEMAS)]
        with lock:
            excl = bloco_exclusoes(sorted(nomes)) if not args.no_exclusions else ""
        prompt = PROMPT_TMPL.format(
            n=args.per_call, tema=tema, exclusoes=excl,
            dificuldade="" if args.no_hard_hint else BLOCO_DIFICULDADE)
        try:
            raw = call_teacher(prompt, args.teacher, api_key, system=SYSTEM,
                               temperature=args.temperature, max_tokens=3500)
        except Exception as e:
            with lock:
                c["api_fail"] += 1
                print(f"  FALHA API: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(15.0 if "429" in str(e) else 2.0)
            return

        for it in parse_items(raw):
            why = valid_shape(it)
            if why:
                with lock:
                    c["shape"] += 1
                continue
            # ⭐ o juiz: a solucao do professor passa nos testes do professor?
            res = run_tests(it["solution"], it["tests"], timeout=args.timeout)
            if not res.ok:
                with lock:
                    c["exec_fail"] += 1
                continue
            g = ngrams(it["prompt"], 3)
            with lock:
                if it["name"] in nomes or any(jaccard(g, o) > 0.8 for o in grams):
                    c["dup"] += 1
                    continue
                nomes.add(it["name"]); grams.append(g)
                fout.write(json.dumps({
                    "name": it["name"], "prompt": it["prompt"],
                    "tests": it["tests"], "solution": it["solution"], "tema": tema,
                }, ensure_ascii=False) + "\n")
                fout.flush()
                c["ok"] += 1
                total = len(existentes) + c["ok"]
                print(f"  validadas={total}/{args.target} | descartadas: forma={c['shape']} "
                      f"exec={c['exec_fail']} dup={c['dup']} | api_fail={c['api_fail']}",
                      flush=True)
                if total >= args.target:
                    stop.set()

    falta = max(0, args.target - len(existentes))
    rodadas = max(1, (falta // max(1, args.per_call // 2)) + 4)
    print(f"workers   : {args.workers} | rodadas estimadas: {rodadas}\n")
    with OUT.open("a", encoding="utf-8") as fout:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(rodada, range(rodadas)))

    total = len(existentes) + c["ok"]
    print(f"\nConcluido: {total} tarefas validadas -> {OUT}")
    print(f"  descartadas: forma={c['shape']} | solucao NAO passou nos testes={c['exec_fail']} "
          f"| duplicadas={c['dup']} | falhas de API={c['api_fail']}")
    print("Proximo: eval/eval_coder.py para medir o BASE antes de treinar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
