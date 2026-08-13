"""Diagnostico do OVER-CALLING: onde o Bee chama ferramenta sem precisar, e o que o
verificador deterministico faz a respeito.

Medido em 2026-08-12: 23,1% de over-calling (15/65) na geracao gulosa. E o pior numero
do modelo em tool-use — pior que under-calling (3,5%) — e o unico eixo em que
decodificacao restrita NAO ajuda: o JSON do over-call e perfeitamente valido contra o
catalogo; a gramatica age DEPOIS da decisao de emitir. O problema e a decisao.

Este script mede as duas metades que decidem se o verificador vale a pena:

  GANHO  — quantos over-calls ele intercepta (casos `text` em que o modelo emitiu JSON
           e o verificador diz "esta query nao precisa de ferramenta").
  ⚠️ CUSTO — quantas chamadas LEGITIMAS ele bloqueia (casos `tool_call` em que o
           verificador diz o mesmo). Um falso positivo aqui e pior que o over-call que
           ele conserta: quebra uma tarefa que funcionava.

Sem medir o custo, "o verificador reduziu o over-calling" e uma meia-verdade.

Uso:
    python comeia/eval/diag_overcall.py --model BrCamp/bee-150m-pt-sft
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "orchestrator"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl, strip_think            # noqa: E402
import verifier as VF                                  # noqa: E402
import ancoragem as ANC                                # noqa: E402
import politica as POL                                 # noqa: E402
from eval_agentic_exec import mensagens, partes, wilson  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PADRAO_EVAL = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-150m-pt-sft")
    ap.add_argument("--data", type=Path, default=PADRAO_EVAL)
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    linhas = [r for r in read_jsonl(args.data) if mensagens(r)]
    catalogo = _d7.load_tools()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(dev)
    modelo.eval()
    print(f"modelo: {args.model} · {dev}\n")

    def gerar(sistema: str | None, usuario: str) -> str:
        msgs = ([{"role": "system", "content": sistema}] if sistema else []) \
            + [{"role": "user", "content": usuario}]
        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ent = tok(txt, return_tensors="pt").to(dev)
        n = ent["input_ids"].shape[1]
        with torch.no_grad():
            g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=False,
                                pad_token_id=tok.pad_token_id or tok.eos_token_id)
        return tok.decode(g[0][n:], skip_special_tokens=True).strip()

    overs: list[dict] = []
    n_text = n_tool = 0
    interceptados = 0          # ganho: over-call que o verificador pega
    bloqueios_indevidos = 0    # custo: chamada legitima que o verificador barra
    anc_intercepta = 0         # idem para o verificador de ANCORAGEM
    anc_bloqueios = 0
    pol_intercepta = 0
    pol_bloqueios = 0
    exemplos_fp_pol: list[tuple] = []
    juntos_intercepta = 0      # os dois em serie
    exemplos_fp: list[tuple] = []
    ferramentas = Counter()

    for i, row in enumerate(linhas, 1):
        sistema, usuario, ref, tipo = partes(row)
        bruto = gerar(sistema, usuario)
        pred, _ = strip_think(bruto)
        obj = _d7.extract_json(pred)
        v = VF.verify(usuario, bruto, catalogo)

        anc = ANC.verificar(usuario, obj) if obj is not None else None
        pol = POL.decidir(usuario, obj) if obj is not None else None

        if tipo == "text":
            n_text += 1
            if obj is not None:
                ferramentas[obj.get("tool")] += 1
                pego = not v.ok
                pego_anc = anc is not None and not anc.ancorado
                pego_pol = pol is not None and not pol.procede
                if pego_pol:
                    pol_intercepta += 1
                if pego:
                    interceptados += 1
                if pego_anc:
                    anc_intercepta += 1
                if pego or pego_anc:
                    juntos_intercepta += 1
                overs.append({"query": usuario, "tool": obj.get("tool"),
                              "args": obj.get("args"), "verificador_pegou": pego,
                              "ancoragem_pegou": pego_anc,
                              "campos": anc.campos_inventados if anc else []})
        else:
            n_tool += 1
            # chamada legitima que o verificador rejeita = falso positivo caro
            if obj is not None and not v.ok:
                bloqueios_indevidos += 1
            if anc is not None and not anc.ancorado:
                anc_bloqueios += 1
                if len(exemplos_fp) < 6:
                    exemplos_fp.append((usuario[:60], obj.get("tool"),
                                        ",".join(anc.campos_inventados)))
            if pol is not None and not pol.procede:
                pol_bloqueios += 1
                if len(exemplos_fp_pol) < 6:
                    exemplos_fp_pol.append((usuario[:58], obj.get("tool"),
                                            ",".join(pol.faltando)))

        if i % 30 == 0 or i == len(linhas):
            print(f"  {i}/{len(linhas)}", flush=True)

    n_over = len(overs)
    print("\n" + "=" * 70)
    print(f"OVER-CALLING bruto            {n_over}/{n_text} = {n_over/n_text:.1%}")
    lo, hi = wilson(n_over, n_text)
    print(f"                              IC95 [{lo:.1%}–{hi:.1%}]")
    print("-" * 70)
    print(f"GANHO  verificador intercepta {interceptados}/{n_over} dos over-calls"
          + (f" = {interceptados/n_over:.1%}" if n_over else ""))
    restante = n_over - interceptados
    print(f"       over-calling residual  {restante}/{n_text} = {restante/n_text:.1%}")
    print(f"⚠️ CUSTO chamadas legitimas bloqueadas {bloqueios_indevidos}/{n_tool}"
          f" = {bloqueios_indevidos/max(1,n_tool):.1%}")
    print("=" * 70)
    print("COMPARACAO DOS DOIS VERIFICADORES (ganho / custo / saldo)")
    print(f"{'':<22} {'pega over':>10} {'bloqueia ok':>12} {'saldo':>7}")
    for nome, g, c in (("intencao (atual)", interceptados, bloqueios_indevidos),
                       ("ANCORAGEM (novo)", anc_intercepta, anc_bloqueios),
                       ("POLICY-AS-LOGIC", pol_intercepta, pol_bloqueios),
                       ("ancoragem + politica", max(anc_intercepta, pol_intercepta),
                        anc_bloqueios + pol_bloqueios)):
        print(f"  {nome:<20} {g:>4}/{n_over:<5} {c:>5}/{n_tool:<6} {g - c:>+6}")
    print("=" * 70)
    resid = n_over - anc_intercepta
    print(f"over-calling com ancoragem: {resid}/{n_text} = {resid/n_text:.1%}"
          f"  (era {n_over/n_text:.1%})")
    if exemplos_fp_pol:
        print("\n⚠️ chamadas legitimas que a POLITICA barrou:")
        for q, t, campos in exemplos_fp_pol:
            print(f"  {t} [{campos}] <- {q}")
    if exemplos_fp:
        print("\n⚠️ chamadas legitimas que a ancoragem barrou (falsos positivos):")
        for q, t, campos in exemplos_fp:
            print(f"  {t} [{campos}] <- {q}")

    print("\nferramentas mais invocadas indevidamente:")
    for t, c in ferramentas.most_common():
        print(f"  {t:<24} {c}")

    print("\nos over-calls (v = verificador pegou):")
    for o in overs:
        marca = "v" if o["verificador_pegou"] else " "
        print(f" [{marca}] {o['query'][:66]}")
        print(f"     -> {o['tool']} {json.dumps(o['args'], ensure_ascii=False)[:70]}")

    if args.out:
        args.out.write_text(json.dumps(
            {"n_text": n_text, "n_tool": n_tool, "over": n_over,
             "interceptados": interceptados, "bloqueios_indevidos": bloqueios_indevidos,
             "casos": overs}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
