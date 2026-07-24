"""Fase 2.1 — Destilação de professor ABERTO para gerar SFT PT-BR.

Lê prompts-semente (PT-BR), chama um modelo professor aberto via OpenRouter e grava
os pares instrução→resposta em data/raw/distill_<tag>.jsonl.

REGRA DURA: só professores abertos (ver ALLOWED_TEACHERS em config.py).
Nunca GPT/Claude/Gemini — viola ToS e contamina a licença do nosso release.

Uso:
    python data/01_distill_teacher.py --seeds data/raw/seeds_ptbr.txt --teacher Qwen/Qwen3-235B-A22B
    python data/01_distill_teacher.py --seeds ... --limit 50 --dry-run

Requer: variável de ambiente OPENROUTER_API_KEY.
Retomável: se o arquivo de saída já existe, pula os prompts já processados.

Modo CoT (--cot): o professor raciocina passo a passo em PT-BR dentro de <think>...</think>
antes da resposta. Guardamos o raciocínio no campo `reasoning` e a resposta em `response`
separados. O 05_build_splits decide se treina com "raciocínio + resposta" ou só a resposta.
É o upgrade de destilação nº1 (o SOTA transfere o raciocínio do professor, não só a saída final).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEFAULT_TEACHER, RAW_DIR, assert_teacher_allowed, ensure_dirs  # noqa: E402
from common import read_jsonl  # noqa: E402

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class TeacherError(RuntimeError):
    """Falha ao obter resposta do professor (HTTP, rate limit, upstream)."""

SYSTEM_PROMPT = (
    "Você é um assistente brasileiro especialista. Responda SEMPRE em português "
    "brasileiro natural e correto. Seja preciso, direto e completo. Não invente "
    "fatos: se não souber, diga que não sabe."
)

# Modo CoT. Duas fontes de raciocínio, em ordem de confiabilidade:
#   1) canal de reasoning NATIVO do OpenRouter (param "reasoning") — separação limpa
#      no protocolo; a resposta (content) já vem sem o raciocínio. É o preferido.
#   2) fallback: tags <think> no próprio texto, se o modelo não usar o canal nativo.
# O prompt reforça: raciocinar antes, e NÃO repetir o raciocínio na resposta final.
SYSTEM_PROMPT_COT = (
    "Você é um assistente brasileiro especialista. Responda SEMPRE em português "
    "brasileiro natural e correto. Raciocine passo a passo antes de responder. "
    "Na RESPOSTA FINAL, dê apenas a resposta ao usuário — NÃO repita o raciocínio, "
    "NÃO use títulos como 'Raciocínio'. Não invente fatos: se não souber, diga que não sabe."
)

# Preâmbulo de raciocínio que alguns modelos vazam no início da resposta final.
# Ex.: "## Raciocínio\n...\n\n" ou "**Raciocínio:**". Removemos se sobrar.
_LEAKED_REASONING = re.compile(
    r"^\s*(#{1,4}\s*|\*{0,2})racioc[íi]nio\b[:\*]*\s*.*?(?:\n\s*\n)",
    re.IGNORECASE | re.DOTALL,
)


def clean_answer(text: str) -> str:
    """Remove um bloco de 'Raciocínio' vazado no começo da resposta final."""
    cleaned = _LEAKED_REASONING.sub("", text, count=1)
    return cleaned.strip() or text.strip()

_THINK_RE = re.compile(r"<think>(.*?)</think>(.*)", re.DOTALL | re.IGNORECASE)


def split_cot(text: str) -> tuple[str, str]:
    """Separa (raciocínio, resposta) de um texto com tags <think>.

    Sem as tags, devolve ('', texto) — trata como resposta pura.
    """
    m = _THINK_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", text.strip()


def load_seeds(path: Path) -> list[str]:
    """Aceita .txt (um prompt por linha) ou .jsonl (campo 'prompt' ou 'instruction')."""
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de sementes nao encontrado: {path}\n"
            "Crie um .txt com um prompt PT-BR por linha (ver data/README.md)."
        )
    if path.suffix == ".jsonl":
        seeds = []
        for row in read_jsonl(path):
            s = row.get("prompt") or row.get("instruction")
            if s:
                seeds.append(s.strip())
        return seeds
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def call_teacher(
    prompt: str, teacher: str, api_key: str, cot: bool = False, timeout: int = 180
) -> dict:
    """Chama o professor. Retorna {'answer': str, 'reasoning': str}.

    Sem --cot, 'reasoning' vem vazio. Com --cot, pede raciocínio em <think> e separa.
    """
    body = json.dumps(
        {
            "model": teacher,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_COT if cot else SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            # CoT precisa de mais espaço (raciocínio + resposta).
            "max_tokens": 4096 if cot else 2048,
            # Liga o canal de reasoning NATIVO (separação limpa). Modelos que não
            # suportam ignoram o campo — sem erro.
            **({"reasoning": {"enabled": True}} if cot else {}),
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise TeacherError(f"HTTP {e.code}: {detail}") from e

    # O OpenRouter devolve 200 com corpo de erro em vários casos (rate limit,
    # modelo indisponivel, upstream fora). Sem isto, o erro vira KeyError opaco.
    if "choices" not in payload:
        err = payload.get("error") or payload
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise TeacherError(f"resposta sem 'choices': {msg}")

    choices = payload.get("choices") or []
    if not choices:
        raise TeacherError("lista 'choices' vazia")

    msg_obj = choices[0].get("message") or {}
    content = msg_obj.get("content")
    native_reasoning = msg_obj.get("reasoning") or msg_obj.get("reasoning_content") or ""

    # Modelos de reasoning as vezes devolvem content=None e colocam o texto em
    # 'reasoning'/'reasoning_content'. Sem este fallback, o lote inteiro quebrava.
    if not content:
        content = native_reasoning

    if not content or not content.strip():
        finish = choices[0].get("finish_reason", "?")
        raise TeacherError(f"conteudo vazio (finish_reason={finish})")

    if not cot:
        return {"answer": content.strip(), "reasoning": ""}

    # CoT — preferência: canal nativo (separação limpa). Se o modelo não usou o canal,
    # tenta as tags <think> no texto. Por fim, limpa preâmbulo de raciocínio vazado.
    if native_reasoning.strip():
        reasoning = native_reasoning.strip()
        answer = clean_answer(content)
    else:
        reasoning, answer = split_cot(content)
        answer = clean_answer(answer)

    if not answer:
        raise TeacherError("CoT sem resposta final")
    return {"answer": answer, "reasoning": reasoning}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=Path, required=True, help="txt (1 prompt/linha) ou jsonl")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--tag", default=None, help="sufixo do arquivo de saida")
    ap.add_argument("--limit", type=int, default=0, help="0 = todos")
    ap.add_argument("--sleep", type=float, default=0.5, help="pausa entre chamadas (rate limit)")
    ap.add_argument("--workers", type=int, default=1,
                    help="chamadas simultaneas. Cada par leva ~25s; sequencial, 2 mil pares "
                         "levariam ~14h. Com 12 workers cai para ~1h. Use 1 em modelos :free "
                         "(rate limit agressivo).")
    ap.add_argument("--cot", action="store_true",
                    help="destila com raciocínio (CoT): professor pensa em <think> antes de "
                         "responder; guarda 'reasoning' + 'response' separados. Upgrade nº1. "
                         "Use um --tag distinto do run sem-CoT (a retomada dedup por instrução).")
    ap.add_argument("--dry-run", action="store_true", help="nao chama a API, so mostra o plano")
    args = ap.parse_args()

    # Guard de licença — falha alto e cedo.
    assert_teacher_allowed(args.teacher)
    ensure_dirs()

    seeds = load_seeds(args.seeds)
    if args.limit:
        seeds = seeds[: args.limit]

    tag = args.tag or args.teacher.split("/")[-1].lower()
    out_path = RAW_DIR / f"distill_{tag}.jsonl"

    # Retomada: pula o que já foi gerado.
    done: set[str] = set()
    if out_path.exists():
        done = {r["instruction"] for r in read_jsonl(out_path) if "instruction" in r}
        print(f"[retomada] {len(done)} pares ja existentes em {out_path.name}")

    pending = [s for s in seeds if s not in done]
    print(f"professor : {args.teacher}")
    print(f"modo      : {'CoT (raciocínio + resposta)' if args.cot else 'resposta direta'}")
    print(f"sementes  : {len(seeds)} (pendentes: {len(pending)})")
    print(f"saida     : {out_path}")

    if args.dry_run:
        print("\n[dry-run] nada foi chamado. Exemplos de prompts pendentes:")
        for s in pending[:3]:
            print(f"  - {s[:100]}")
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: defina OPENROUTER_API_KEY no ambiente.", file=sys.stderr)
        return 1

    counters = {"ok": 0, "fail": 0, "done": 0}
    lock = threading.Lock()
    total = len(pending)

    def work(prompt: str) -> None:
        try:
            result = call_teacher(prompt, args.teacher, api_key, cot=args.cot)
        except Exception as e:  # nenhum item isolado pode derrubar o lote inteiro
            with lock:
                counters["fail"] += 1
                counters["done"] += 1
                print(f"  FALHA: {type(e).__name__}: {e}", file=sys.stderr)
            # rate limit → recuar antes de liberar o worker
            time.sleep(15.0 if "429" in str(e) or "rate" in str(e).lower() else 2.0)
            return

        rec = {
            "instruction": prompt,
            "response": result["answer"],
            "source": "distill",
            "teacher": args.teacher,
        }
        if result.get("reasoning"):
            rec["reasoning"] = result["reasoning"]
        record = json.dumps(rec, ensure_ascii=False)
        with lock:  # escrita serializada — o arquivo é compartilhado entre threads
            fout.write(record + "\n")
            fout.flush()
            counters["ok"] += 1
            counters["done"] += 1
            d = counters["done"]
            if d % 25 == 0 or d == total:
                print(f"  [{d}/{total}] ok={counters['ok']} falhas={counters['fail']}", flush=True)
        time.sleep(args.sleep)

    print(f"workers   : {args.workers}\n")
    with out_path.open("a", encoding="utf-8") as fout:
        if args.workers <= 1:
            for p in pending:
                work(p)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(work, pending))

    print(f"\nConcluido: {counters['ok']} pares novos, {counters['fail']} falhas -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
