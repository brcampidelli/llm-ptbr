"""COMEIA — CLI do orquestrador (Fase 0 do plano).

Junta registry + roteador + engine de hot-swap. Prova a arquitetura da comeia com a
abelha SFT-v2 que ja temos + o backbone base como fallback, e reporta a metrica-chave
(fracao de fast-path).

Modos:
    # 1) TESTAR o roteador SEM GPU (valida rota + metrica de graca, roda em qualquer lugar):
    python orchestrator/run.py --route-only --sample
    python orchestrator/run.py --route-only --batch prompts.txt

    # 2) Comeia de verdade (precisa de GPU + o adapter):
    python orchestrator/run.py                                   # chat interativo
    python orchestrator/run.py --batch prompts.txt --max-new 256
    # local: aponte o adapter do chat para onde ele estiver
    python orchestrator/run.py --chat-adapter models/qwen3.5-4b-ptbr-sft

Formato do --batch: .txt (uma query por linha) ou .jsonl ({"prompt"} ou {"instruction"}).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# o diretorio do script entra no sys.path automaticamente -> import direto
from registry import load_registry
from router import Router

# Amostra representativa para --sample: exercita cada rota (agentica, coder, chat, dificil).
SAMPLE_QUERIES = [
    "Oi, tudo bem? Me conta uma curiosidade sobre o Brasil.",
    "Escreva uma funcao Python que inverte uma string.",
    "Chame a ferramenta de busca com os parametros corretos em JSON.",
    "Qual a capital de Pernambuco?",
    "Prove passo a passo que a soma dos angulos de um triangulo e 180 graus.",
    "Refatore este codigo:\n```python\ndef f(x):\n  return x*2\n```",
    "Traduza 'good morning' para o portugues.",
    "Analise a fundo, detalhadamente, os trade-offs entre microservicos e monolito, justificando.",
    "Monte um agente que orquestra a chamada de duas ferramentas.",
    "Me da uma receita rapida de bolo de cenoura.",
]


def load_batch(path: Path) -> list[str]:
    if path.suffix == ".jsonl":
        out = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            q = row.get("prompt") or row.get("instruction")
            if q:
                out.append(q.strip())
        return out
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    # console do Windows e cp1252 por padrao -> forca UTF-8 para nao quebrar em emoji/acentos
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path,
                    default=Path(__file__).resolve().parent / "bees.json")
    ap.add_argument("--backbone", default=None, help="sobrepoe o backbone do registry")
    ap.add_argument("--chat-adapter", default=None,
                    help="sobrepoe o caminho do adapter da abelha chat_ptbr (util no local)")
    ap.add_argument("--batch", type=Path, default=None, help=".txt (1/linha) ou .jsonl")
    ap.add_argument("--sample", action="store_true", help="usa a amostra embutida de queries")
    ap.add_argument("--route-only", action="store_true",
                    help="so decide a rota e mede fast-path — NAO carrega modelo (sem GPU)")
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--max-new", type=int, default=512)
    ap.add_argument("--thinking", action="store_true",
                    help="deixa o modelo raciocinar (<think>) antes de responder. "
                         "Padrao: DESLIGADO — na comeia raciocinio gasta os tokens do "
                         "fast-path (achado do teste na L4)")
    ap.add_argument("--no-verify", action="store_true",
                    help="desliga o verificador deterministico de tool-call")
    ap.add_argument("--max-retries", type=int, default=1,
                    help="tentativas corretivas por violacao. 1 basta: no interwhen o "
                         "PRIMEIRO feedback entrega o grosso do ganho (+32,6 pp)")
    args = ap.parse_args()

    reg = load_registry(args.registry)
    if args.backbone:
        reg.backbone = args.backbone
    if args.chat_adapter and "chat_ptbr" in reg.bees:
        reg.bees["chat_ptbr"].adapter_path = args.chat_adapter

    router = Router(reg)

    print(f"COMEIA — backbone: {reg.backbone}")
    print(f"abelhas: {', '.join(reg.bees)}")
    print(f"default: {reg.default_bee} | fallback: {reg.fallback_bee}\n")

    # fonte das queries
    queries: list[str] | None = None
    if args.sample:
        queries = SAMPLE_QUERIES
    elif args.batch:
        queries = load_batch(args.batch)

    # ---- modo route-only: valida rota + metrica SEM modelo -------------------
    if args.route_only:
        if not queries:
            print("route-only precisa de --sample ou --batch.", file=sys.stderr)
            return 1
        print("=== ROTA (sem gerar) ===")
        for q in queries:
            d = router.route(q)
            path = "FAST" if d.fast_path else "slow"
            print(f"[{path}] {d.bee_name:<12} | {d.reason}")
            print(f"        q: {q[:70]}")
        print("\n" + router.summary())
        return 0

    # ---- modo real: carrega a comeia e gera ---------------------------------
    from hive import Hive

    hive = Hive(reg, four_bit=not args.no_4bit, max_new_tokens=args.max_new,
                thinking=args.thinking)
    print(f"raciocinio (<think>): {'LIGADO' if args.thinking else 'desligado'}")
    hive.load()

    latencies: list[float] = []
    # estatistica do verificador: quantas violacoes e de que tipo
    violations: dict[str, int] = {}
    n_corrected = 0

    tools = {}
    if not args.no_verify:
        import verifier as vf
        tools = vf._d7.load_tools()

    def answer(q: str) -> None:
        nonlocal n_corrected
        d = router.route(q)
        bee = reg.get(d.bee_name)
        text, dt = hive.generate(bee, q, max_new_tokens=args.max_new)
        total_dt = dt
        tag = "FAST" if d.fast_path else "slow"
        print(f"\n[{tag}] abelha={d.bee_name} ({dt:.1f}s) — {d.reason}")

        # ── laco de verificacao (padrao interwhen: verificar no laco, em codigo) ──
        if not args.no_verify:
            for attempt in range(args.max_retries + 1):
                v = vf.verify(q, text, tools)
                if v.ok:
                    if attempt:
                        n_corrected += 1
                    break
                violations[v.violation] = violations.get(v.violation, 0) + 1
                print(f"   ⚠️ verificador: {v.violation}")
                if attempt >= args.max_retries:
                    print("   (sem tentativas restantes — devolvendo como esta)")
                    break
                # retry com feedback corretivo injetado na query
                print(f"   ↻ corrigindo: {v.feedback[:80]}")
                text, dt2 = hive.generate(
                    bee, f"{q}\n\n[CORREÇÃO OBRIGATÓRIA] {v.feedback}",
                    max_new_tokens=args.max_new)
                total_dt += dt2

        latencies.append(total_dt)
        print(text)

    if queries:
        for q in queries:
            print("\n" + "=" * 60)
            print(f"Q: {q}")
            answer(q)
    else:
        print("Chat interativo. Ctrl+C ou linha vazia para sair.\n")
        try:
            while True:
                q = input("voce> ").strip()
                if not q:
                    break
                answer(q)
        except (KeyboardInterrupt, EOFError):
            print()

    print("\n" + router.summary())
    if latencies:
        print(f"latencia media: {sum(latencies)/len(latencies):.1f}s "
              f"(min {min(latencies):.1f}s / max {max(latencies):.1f}s)")
    if not args.no_verify:
        total_v = sum(violations.values())
        if total_v:
            det = " | ".join(f"{k}={v}" for k, v in sorted(violations.items()))
            print(f"verificador: {total_v} violacao(oes) detectada(s) — {det}")
            print(f"             {n_corrected} corrigida(s) no retry")
        else:
            print("verificador: nenhuma violacao (todas as saidas passaram)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
