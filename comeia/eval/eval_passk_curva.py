"""A CURVA de pass@k — o teste que pode derrubar a premissa do "teto" (T1 do estudo).

⭐ POR QUE ESTE SCRIPT EXISTE
  O projeto declarou que 72,9% de pass@16 era um TETO, e usou isso para argumentar que so
  escala levanta o numero. A refutacao adversarial (docs/estudo-bee-350m.md §4) derrubou:

    Large Language Monkeys (arXiv:2407.21787, Stanford) mede cobertura de 70M a 70B e acha
    crescimento LOG-LINEAR por QUATRO ordens de grandeza, sem saturacao. Pythia-160M — que e
    praticamente o tamanho do Bee — vai de pass@1 = 0,27% para pass@10k = 57% no MATH.

  Em k=16 voce esta no PRIMEIRO ponto da curva. Declarar teto ali e ler o APARATO e nao o
  fenomeno — exatamente o erro que este projeto ja pagou cinco vezes.

⭐ O DESENHO CERTO: UMA corrida, a curva INTEIRA
  Gera n amostras por exemplo UMA vez e calcula pass@k para todo k <= n com o estimador
  NAO-VIESADO do Codex (Chen et al. 2021):

      pass@k = 1 - C(n-c, k) / C(n, k)

  onde c = amostras corretas. Rodar k=1, depois k=16, depois k=256 separadamente daria tres
  medicoes com ruido independente e a curva pareceria ter degraus que nao existem.

⭐ O QUE MAIS SAI DESTA CORRIDA, DE GRACA
  T2 — os itens que NENHUMA amostra resolveu vao para um arquivo separado, para auditoria a
       mao. O projeto ja produziu 23,5% onde o real era 57,6% por gabarito impossivel; se
       ~25% do conjunto for insoluvel por construcao, o "teto" e do BENCHMARK e nenhum
       tamanho de modelo o move.
  T4 — o resultado POR PROBLEMA e salvo, permitindo o diff pre/pos-autoaprendizado. O paper
       arXiv:2608.11829 mede que o agregado pode ficar estavel enquanto o conjunto de
       problemas resolviveis DEGRADA (esquece mais do que aprende).

Uso:
    python comeia/eval/eval_passk_curva.py --model BrCamp/bee-150m-pt-sft-v2 --n 256
    python comeia/eval/eval_passk_curva.py --model ... --n 64 --temp 1.0 --tag T1.0   # T3
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl, strip_think  # noqa: E402
import tools_exec as TE  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PADRAO_EVAL = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"
KS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]


def pass_at_k(n: int, c: int, k: int) -> float:
    """Estimador NAO-VIESADO do Codex: 1 - C(n-c,k)/C(n,k). Calculado em log para nao estourar."""
    if k > n:
        return float("nan")
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    # prod_{i=0}^{k-1} (n-c-i)/(n-i)
    logp = 0.0
    for i in range(k):
        logp += math.log(n - c - i) - math.log(n - i)
    return 1.0 - math.exp(logp)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def mensagens(row: dict) -> list[dict]:
    if row.get("messages"):
        return row["messages"]
    return list(row.get("prompt") or []) + list(row.get("completion") or [])


def partes(row: dict) -> tuple[str | None, str, str, str]:
    sistema = usuario = ref = None
    for m in mensagens(row):
        if m["role"] == "system":
            sistema = m["content"]
        elif m["role"] == "user":
            usuario = m["content"]
        elif m["role"] == "assistant":
            ref = m["content"]
    return sistema, usuario or "", ref or "", row.get("kind", "?")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-150m-pt-sft-v2")
    ap.add_argument("--peft", default=None)
    ap.add_argument("--data", type=Path, default=PADRAO_EVAL)
    ap.add_argument("--n", type=int, default=256, help="amostras por exemplo TOOL (a curva)")
    ap.add_argument("--n-text", type=int, default=0,
                    help="amostras nos exemplos TEXT (over-calling). 0 = igual a --n. "
                         "⭐ 16 ja da >1000 observacoes agregadas e corta 40%% do custo: "
                         "over-calling e taxa por amostra, nao curva em k.")
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--min-p", type=float, default=0.0)
    ap.add_argument("--lote", type=int, default=64, help="sequencias por chamada de generate")
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    linhas = [r for r in read_jsonl(args.data)]
    if args.limit:
        linhas = linhas[: args.limit]
    catalogo = _d7.TOOLS if hasattr(_d7, "TOOLS") else None

    # ---- GUARDA (a que se pagou na primeira execucao): o gabarito EXECUTA?
    #      Se a referencia nao roda, o avaliador esta errado e nenhum numero vale.
    # ⚠️ o campo e' kind="tool_call" (nao "tool"). A convencao em todo o projeto e'
    #    "text" vs *o resto* — escrever `!= "tool"` aqui fez a guarda pular os 85 exemplos
    #    e imprimir OK tendo verificado ZERO. Guarda fora do fluxo nao guarda nada.
    ruins, checadas = [], 0
    for i, row in enumerate(linhas):
        _, _, ref, tipo = partes(row)
        if tipo == "text":
            continue
        checadas += 1
        obj = _d7.extract_json(ref)
        ok, _ = TE.executar(obj) if obj else (False, None)
        if not ok:
            ruins.append((i, (obj or {}).get("tool", "?")))
    if ruins:
        print(f"🔴 ABORTA: {len(ruins)}/{checadas} referencias NAO executam — o avaliador esta errado.",
              file=sys.stderr)
        for i, t in ruins[:10]:
            print(f"    linha {i}: {t}", file=sys.stderr)
        return 3
    # ⭐ meta-guarda: uma guarda que verificou zero itens tambem aborta.
    if checadas == 0:
        print("🔴 ABORTA: a guarda nao verificou NENHUMA referencia — o filtro de tipo esta errado.",
              file=sys.stderr)
        return 3
    print(f"✅ guarda: {checadas} referencias executam")

    disp = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(disp)
    if args.peft:
        from peft import PeftModel

        modelo = PeftModel.from_pretrained(modelo, args.peft).to(disp)
    modelo.eval()

    print(f"modelo : {args.model}{' + ' + args.peft if args.peft else ''}")
    print(f"holdout: {len(linhas)} exemplos · {disp}")
    print(f"amostra: n={args.n}  T={args.temp}  top_p={args.top_p}"
          f"{'  min_p=%.2f' % args.min_p if args.min_p else ''}  lote={args.lote}\n")

    def gerar(sistema: str | None, usuario: str, n: int) -> list[str]:
        msgs = ([{"role": "system", "content": sistema}] if sistema else []) + [
            {"role": "user", "content": usuario}
        ]
        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ent = tok(txt, return_tensors="pt").to(disp)
        pre = ent["input_ids"].shape[1]
        saidas: list[str] = []
        while len(saidas) < n:
            b = min(args.lote, n - len(saidas))
            cfg = dict(
                max_new_tokens=args.max_new,
                pad_token_id=tok.pad_token_id or tok.eos_token_id,
                do_sample=True,
                temperature=args.temp,
                top_p=args.top_p,
                num_return_sequences=b,
            )
            if args.min_p:
                cfg["min_p"] = args.min_p
            with torch.no_grad():
                g = modelo.generate(**ent, **cfg)
            saidas += [tok.decode(s[pre:], skip_special_tokens=True).strip() for s in g]
        return saidas

    por_problema: list[dict] = []
    t0 = time.time()
    n_tool = 0
    over_amostras = 0
    tot_text_amostras = 0

    def progresso(i: int) -> None:
        # ⚠️ a versao anterior imprimia DEPOIS do `continue` dos exemplos 'text' — ficavam
        #    minutos sem sinal nenhum e nao dava para saber se estava travado ou lento.
        if i % 5 and i != len(linhas):
            return
        dt = time.time() - t0
        res = torch.cuda.memory_reserved() / 2**20 if disp == "cuda" else 0
        alo = torch.cuda.memory_allocated() / 2**20 if disp == "cuda" else 0
        print(f"  {i}/{len(linhas)} · {dt/60:.1f} min · resta ~{dt*(len(linhas)-i)/i/60:.1f} min"
              f" · VRAM {alo:.0f}/{res:.0f} MiB", flush=True)

    n_text = args.n_text or args.n
    for i, row in enumerate(linhas, 1):
        sistema, usuario, ref, tipo = partes(row)
        saidas = gerar(sistema, usuario, n_text if tipo == "text" else args.n)
        if disp == "cuda":
            torch.cuda.empty_cache()
        ref_obj = _d7.extract_json(ref)

        if tipo == "text":
            # ⭐ over-calling medido em TODAS as n amostras, nao so na primeira: da uma
            #    estimativa com ~n vezes menos ruido e permite ver se e' cauda ou regra.
            emitiu = sum(1 for b in saidas if _d7.extract_json(strip_think(b)[0]) is not None)
            over_amostras += emitiu
            tot_text_amostras += len(saidas)
            por_problema.append(
                {"idx": i - 1, "tipo": "text", "n": len(saidas), "over": emitiu,
                 "taxa_over": round(emitiu / max(1, len(saidas)), 4)}
            )
            progresso(i)
            continue

        n_tool += 1
        nome_ref = (ref_obj or {}).get("tool", "?")
        _, res_ref = TE.executar(ref_obj)

        acertos = 0
        ferramentas: dict[str, int] = {}
        for bruto in saidas:
            pred, _ = strip_think(bruto)
            obj = _d7.extract_json(pred)
            if obj is None:
                ferramentas["<sem-json>"] = ferramentas.get("<sem-json>", 0) + 1
                continue
            t = str(obj.get("tool", "?"))
            ferramentas[t] = ferramentas.get(t, 0) + 1
            ok_p, res_p = TE.executar(obj)
            if ok_p and TE.resultados_batem(res_p, res_ref):
                acertos += 1

        por_problema.append(
            {
                "idx": i - 1,
                "tipo": "tool",
                "ferramenta_ref": nome_ref,
                "n": len(saidas),
                "acertos": acertos,
                "taxa": round(acertos / max(1, len(saidas)), 4),
                "ferramentas_previstas": dict(sorted(ferramentas.items(), key=lambda x: -x[1])[:5]),
                "usuario": usuario[:400],
                "referencia": ref[:400],
            }
        )

        progresso(i)

    # ---------------- a curva
    tools = [p for p in por_problema if p["tipo"] == "tool"]
    print("\n" + "=" * 74)
    print(f"CURVA DE pass@k — {len(tools)} exemplos tool, n={args.n} amostras cada")
    print("=" * 74)
    print(f"  {'k':>5}   {'pass@k':>8}   {'IC 95% (Wilson sobre exemplos)':<32}  {'ganho vs k anterior':>19}")
    curva = []
    ant = None
    for k in KS:
        if k > args.n:
            break
        v = sum(pass_at_k(p["n"], p["acertos"], k) for p in tools) / max(1, len(tools))
        # limite superior conservador: quantos exemplos tem PELO MENOS 1 acerto
        resolviveis = sum(1 for p in tools if p["acertos"] > 0)
        lo, hi = wilson(round(v * len(tools)), len(tools))
        d = "" if ant is None else f"{(v - ant) * 100:+5.2f} pp"
        print(f"  {k:>5}   {v:>7.1%}   [{lo:.1%} – {hi:.1%}]{'':<12}  {d:>19}")
        curva.append({"k": k, "pass_at_k": round(v, 4), "ic95": [round(lo, 4), round(hi, 4)]})
        ant = v

    resolviveis = sum(1 for p in tools if p["acertos"] > 0)
    nunca = [p for p in tools if p["acertos"] == 0]
    print("-" * 74)
    print(f"  teto EMPIRICO desta corrida (>=1 acerto em {args.n}): "
          f"{resolviveis}/{len(tools)} = {resolviveis/max(1,len(tools)):.1%}")
    print(f"  NUNCA resolvidos em {args.n} amostras: {len(nunca)} exemplos "
          f"({len(nunca)/max(1,len(tools)):.1%}) → auditar a mao (T2)")
    if tot_text_amostras:
        print(f"  over-calling (todas as amostras 'text'): "
              f"{over_amostras}/{tot_text_amostras} = {over_amostras/tot_text_amostras:.1%}")

    # ---------------- veredito sobre "teto"
    print()
    if len(curva) >= 2:
        ultimo = curva[-1]["pass_at_k"]
        penultimo = curva[-2]["pass_at_k"]
        ganho_final = (ultimo - penultimo) * 100
        if ganho_final >= 1.0:
            print(f"🔴 A CURVA AINDA SOBE no ultimo degrau ({ganho_final:+.2f} pp de k={curva[-2]['k']}"
                  f" para k={curva[-1]['k']}).")
            print("   72,9% em k=16 NAO era teto — era orcamento de amostragem. A palavra 'teto'")
            print("   sai do vocabulario do projeto ate que a curva ACHATE.")
        else:
            print(f"🟢 a curva achatou no fim ({ganho_final:+.2f} pp no ultimo degrau).")
            print("   Consistente com teto real — mas ver T2 antes de concluir: pode ser do BENCHMARK.")

    tag = args.tag or f"n{args.n}_T{args.temp}"
    dest = Path(__file__).resolve().parent / "results"
    dest.mkdir(exist_ok=True)
    alvo = dest / f"passk_curva_{tag}.json"
    alvo.write_text(
        json.dumps(
            {
                "modelo": args.model,
                "peft": args.peft,
                "n": args.n,
                "n_text": n_text,
                "temp": args.temp,
                "top_p": args.top_p,
                "min_p": args.min_p,
                "exemplos_tool": len(tools),
                "curva": curva,
                "teto_empirico": round(resolviveis / max(1, len(tools)), 4),
                "nunca_resolvidos": len(nunca),
                "over_calling_amostrado": round(over_amostras / max(1, tot_text_amostras), 4),
                "minutos": round((time.time() - t0) / 60, 1),
                "por_problema": por_problema,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    # T2: os nunca resolvidos, em arquivo proprio, prontos para leitura humana
    aud = dest / f"nunca_resolvidos_{tag}.json"
    aud.write_text(json.dumps(nunca, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ncurva:  {alvo}")
    print(f"T2:     {aud}   ({len(nunca)} itens para auditoria a mao)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
