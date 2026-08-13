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

⭐ COLHEITA SIMETRICA (--incluir-text), e por que ela e necessaria (medido 2026-08-12):
    A v1 colhia so `tool_call`, porque so a chamada tem verificacao por execucao. Resultado
    do A/B: a proporcao agentica foi de 59,3% para 75,8% de tool, e o modelo aprendeu a
    chamar ferramenta com mais frequencia — over-calling 26,2% -> 33,8%. O metodo entregou
    o que prometia (pass@1 52,3% -> 57,6%, argumentos exatos +7,1 pp) e cobrou noutro eixo.

    O conserto nao e diminuir o reforco: e colher os DOIS lados. Para um exemplo `text`, a
    decisao certa e NAO chamar — e isso e verificavel: se saiu texto em vez de JSON, o
    modelo acertou a decisao.

⚠️ MAS reforcar texto gerado pelo proprio Bee e arriscado: ele escreve portugues excelente
    e INVENTA FATOS. Aceitar qualquer resposta em texto ensinaria a decisao certa com
    conteudo errado. Por isso a colheita de `text` passa por quatro guardas deterministicas
    (ver `texto_aproveitavel`): nao e JSON, tem tamanho plausivel, nao e degenerada por
    repeticao, e cobre parte do vocabulario da referencia do professor — esta ultima e a
    que impede colher uma resposta fluente sobre o assunto errado.

Uso:
    python comeia/data/15_rejection_sampling.py --model BrCamp/bee-150m-pt-sft --k 8
    python comeia/data/15_rejection_sampling.py --incluir-text     # colheita simetrica
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


def _palavras(s: str) -> set[str]:
    import re
    import unicodedata
    txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return {p for p in re.findall(r"[a-z0-9]+", txt) if len(p) > 3}


def texto_aproveitavel(pred: str, ref: str, cobertura_min: float = 0.25) -> tuple[bool, str]:
    """A resposta em texto do MODELO serve de reforco? (guardas deterministicas)

    Para `tool_call` o juiz e a execucao. Para `text` nao ha o que executar, e o unico
    fato verificavel e que o modelo NAO chamou ferramenta — acertou a DECISAO. So que
    aceitar qualquer texto ensinaria a decisao certa junto com conteudo inventado, que e
    a fraqueza conhecida deste modelo. Dai as guardas:
    """
    t = (pred or "").strip()
    if not t:
        return False, "vazia"
    if len(t) < 25 or len(t) > 2500:
        return False, "tamanho implausivel"

    # degeneracao por repeticao: modelo pequeno costuma travar em loop
    tokens = t.split()
    if len(tokens) >= 12 and len(set(tokens)) / len(tokens) < 0.35:
        return False, "degenerada (repeticao)"

    # ⭐ a guarda que importa: falar bem sobre o assunto ERRADO nao serve de reforco.
    # Exigimos que a resposta cubra parte do vocabulario da referencia do professor.
    pr, rf = _palavras(t), _palavras(ref)
    if rf:
        cobertura = len(pr & rf) / len(rf)
        if cobertura < cobertura_min:
            return False, f"fora do assunto (cobre {cobertura:.0%} da referencia)"
    return True, "ok"


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
    ap.add_argument("--incluir-text", action="store_true",
                    help="colheita SIMETRICA: tambem reforca a decisao de NAO chamar")
    args = ap.parse_args()

    linhas = [r for r in read_jsonl(args.dados)]
    if args.limit:
        linhas = linhas[: args.limit]
    tool_rows = [r for r in linhas if r.get("kind") == "tool_call"]
    text_rows = [r for r in linhas if r.get("kind") != "tool_call"] if args.incluir_text else []

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

    # ── colheita SIMETRICA: reforcar a decisao de NAO chamar ──────────────────
    n_text_ok = 0
    motivos_rejeicao = Counter()
    for i, row in enumerate(text_rows, 1):
        msgs = list(row.get("prompt") or [])
        ref = next((m["content"] for m in (row.get("completion") or [])
                    if m["role"] == "assistant"), "")
        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ent = tok(txt, return_tensors="pt").to(dev)
        n = ent["input_ids"].shape[1]
        with torch.no_grad():
            g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=True,
                                temperature=args.temp, top_p=0.95,
                                num_return_sequences=args.k,
                                pad_token_id=tok.pad_token_id or tok.eos_token_id)
        guardadas = 0
        vistos_t: set[str] = set()
        for seq in g:
            if guardadas >= args.max_por_exemplo:
                break
            saida = tok.decode(seq[n:], skip_special_tokens=True).strip()
            pred, _ = strip_think(saida)
            if _d7.extract_json(pred) is not None:      # chamou ferramenta: errou a decisao
                motivos_rejeicao["chamou ferramenta"] += 1
                continue
            ok, motivo = texto_aproveitavel(pred, ref)
            if not ok:
                motivos_rejeicao[motivo.split(" (")[0]] += 1
                continue
            chave = pred[:200]
            if chave in vistos_t:
                continue
            vistos_t.add(chave)
            guardadas += 1
            reforco.append({"prompt": msgs,
                            "completion": [{"role": "assistant", "content": pred}],
                            "kind": "text", "origem": "rejection_sampling"})
        if guardadas:
            n_text_ok += 1
        if i % 100 == 0 or i == len(text_rows):
            print(f"  [text] {i}/{len(text_rows)} · {n_text_ok} com reforco", flush=True)

    n_val = stats["com_acerto"] + stats["sem_acerto"]
    print("\n" + "=" * 66)
    print(f"exemplos avaliados          {n_val}")
    print(f"  com >=1 amostra correta   {stats['com_acerto']}/{n_val} = "
          f"{stats['com_acerto']/max(1,n_val):.1%}   <- pass@{args.k} no TREINO")
    print(f"  sem nenhuma               {stats['sem_acerto']}/{n_val}")
    if text_rows:
        n_tool_ref = sum(1 for r in reforco if r["kind"] == "tool_call")
        n_text_ref = len(reforco) - n_tool_ref
        print(f"\ncolheita de TEXT (decisao de nao chamar)")
        print(f"  exemplos com reforco      {n_text_ok}/{len(text_rows)} = "
              f"{n_text_ok/max(1,len(text_rows)):.1%}")
        print(f"  amostras                  {n_text_ref}")
        print(f"  rejeitadas por: {dict(motivos_rejeicao.most_common(5))}")
        prop = n_tool_ref / max(1, len(reforco))
        print(f"\n⭐ reforco: {n_tool_ref} tool / {n_text_ref} text = {prop:.1%} tool")
        print(f"   (o original e 59,3% tool — quanto mais perto, menos desloca a decisao)")
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
