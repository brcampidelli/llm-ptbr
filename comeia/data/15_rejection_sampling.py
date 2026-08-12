"""Rejection sampling sobre o TREINO: colher as trajetorias que o modelo so acha as vezes.

⭐ POR QUE ISTO E VIAVEL AQUI (medido em 2026-08-12, docs/agentico-medicao.md):
    greedy    57,6% das tarefas cumpridas
    pass@1    52,3%
    pass@16   72,9%   -> folga de +20,6 pp, capturando 43,2% do que faltava

    Ou seja: existem trajetorias corretas que a geracao gulosa NAO acha, e um verificador
    deterministico (executar a chamada) as reconhece sem ambiguidade. E exatamente o
    ingrediente do STaR / rejection-sampling fine-tuning. A condicao nunca foi "ter 1B de
    parametros" — e "ter cauda + verificador barato".

O QUE ESTE SCRIPT FAZ:
    1. amostra k candidatas por exemplo de TREINO (nunca o holdout — isso contaminaria a
       medicao final);
    2. EXECUTA cada candidata e a referencia no mundo simulado e compara os resultados;
    3. guarda as que cumprem a tarefa, deduplicadas;
    4. escreve um dataset de REFORCO — que sera SOMADO ao original, nunca substituindo.
       O dado do professor continua sendo a referencia; o reforco so ensina o modelo a
       fazer com consistencia o que ja sabe fazer as vezes.

⚠️ RISCO CONHECIDO (model collapse): treinar so na propria saida estreita a distribuicao.
    Duas defesas aqui: (a) o filtro e EXTERNO e deterministico, nao auto-julgamento — o
    modelo nao decide o que e bom; (b) o original permanece na mistura. Ainda assim, a
    medicao obrigatoria depois do retreino e pass@k de novo: se pass@1 subir e pass@256
    cair, estreitamos a distribuicao sem ganhar capacidade (arXiv 2504.13837).

Uso:
    python comeia/data/15_rejection_sampling.py --model BrCamp/bee-150m-pt-sft --k 8
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # comeia/
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "eval"))

from common import read_jsonl, strip_think            # noqa: E402
import tools_exec as TE                                # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

TREINO = RAIZ / "data" / "processed" / "sft_agentic.jsonl"
SAIDA = RAIZ / "data" / "processed" / "sft_agentic_reforco.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-150m-pt-sft")
    ap.add_argument("--dados", type=Path, default=TREINO)
    ap.add_argument("--out", type=Path, default=SAIDA)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--max-por-exemplo", type=int, default=2,
                    help="quantas amostras corretas guardar por exemplo (dedup antes)")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    linhas = [r for r in read_jsonl(args.dados)]
    if args.limit:
        linhas = linhas[: args.limit]
    tool_rows = [r for r in linhas if r.get("kind") == "tool_call"]

    TE.garantir_fixtures()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(dev)
    modelo.eval()

    print(f"modelo : {args.model} · {dev}")
    print(f"treino : {len(tool_rows)} exemplos tool_call de {args.dados.name}")
    print(f"amostra: k={args.k} · T={args.temp}\n")

    reforco: list[dict] = []
    stats = Counter()
    por_ferramenta = Counter()

    for i, row in enumerate(tool_rows, 1):
        msgs = list(row.get("prompt") or [])
        ref = next((m["content"] for m in (row.get("completion") or [])
                    if m["role"] == "assistant"), None)
        ref_obj = _d7.extract_json(ref) if ref else None
        if not ref_obj:
            stats["ref_sem_json"] += 1
            continue
        ok_ref, res_ref = TE.executar(ref_obj)
        if not ok_ref:
            # gabarito que nao executa nao serve de juiz — descartar em silencio seria
            # o erro que ja custou caro neste projeto, entao contamos.
            stats["ref_nao_executa"] += 1
            continue

        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ent = tok(txt, return_tensors="pt").to(dev)
        n = ent["input_ids"].shape[1]
        with torch.no_grad():
            g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=True,
                                temperature=args.temp, top_p=0.95,
                                num_return_sequences=args.k,
                                pad_token_id=tok.pad_token_id or tok.eos_token_id)

        vistos: set[str] = set()
        guardadas = 0
        for seq in g:
            if guardadas >= args.max_por_exemplo:
                break
            saida = tok.decode(seq[n:], skip_special_tokens=True).strip()
            pred, _ = strip_think(saida)
            obj = _d7.extract_json(pred)
            if obj is None:
                continue
            chave = json.dumps(obj, sort_keys=True, ensure_ascii=False)
            if chave in vistos:
                continue
            ok_p, res_p = TE.executar(obj)
            if not (ok_p and TE.resultados_batem(res_p, res_ref)):
                continue
            vistos.add(chave)
            guardadas += 1
            reforco.append({
                "prompt": msgs,
                "completion": [{"role": "assistant", "content": chave}],
                "kind": "tool_call",
                "origem": "rejection_sampling",
            })

        stats["com_acerto" if guardadas else "sem_acerto"] += 1
        if guardadas:
            por_ferramenta[ref_obj.get("tool")] += 1

        if i % 50 == 0 or i == len(tool_rows):
            aproveito = stats["com_acerto"] / max(1, stats["com_acerto"] + stats["sem_acerto"])
            print(f"  {i}/{len(tool_rows)} · com acerto {aproveito:.1%} · "
                  f"{len(reforco)} amostras colhidas", flush=True)

    n_val = stats["com_acerto"] + stats["sem_acerto"]
    print("\n" + "=" * 66)
    print(f"exemplos avaliados          {n_val}")
    print(f"  com >=1 amostra correta   {stats['com_acerto']}/{n_val} = "
          f"{stats['com_acerto']/max(1,n_val):.1%}   <- pass@{args.k} no TREINO")
    print(f"  sem nenhuma               {stats['sem_acerto']}/{n_val}")
    print(f"amostras de reforco colhidas {len(reforco)}")
    if stats["ref_nao_executa"]:
        print(f"⚠️ referencias descartadas (nao executam): {stats['ref_nao_executa']}")
    print("\ncolheita por ferramenta:")
    for t, c in por_ferramenta.most_common():
        print(f"  {t:<24} {c}")

    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in reforco) + "\n",
        encoding="utf-8")
    print(f"\n[OK] {len(reforco)} exemplos em {args.out}")
    print("Proximo: misturar com o original e retreinar (NAO substituir o original).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
