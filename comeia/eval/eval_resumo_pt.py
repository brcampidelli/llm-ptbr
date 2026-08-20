"""Mede resumo em PT por execução: invenção, omissão e compressão. Nunca por similaridade.

⭐ O NÚMERO SÓ SIGNIFICA ALGUMA COISA AO LADO DO PISO

Copiar as duas primeiras frases da fonte — LEAD-2, nenhum modelo envolvido — passa em
**51,3%** dos itens deste conjunto, porque o texto é escrito em pirâmide invertida e a
abertura já carrega a maior parte dos fatos. Um modelo que pontue 45% não "resume
razoavelmente": ele perde para o `head -2`.

Por isso o LEAD-2 é medido **no mesmo run**, com a mesma régua, e impresso ao lado. É a
lição do `verifier.py`, cujo ganho aparente escondia saldo −4 porque só um lado era medido.

As métricas, todas determinísticas:

  · **útil** — o item passa em TODAS as condições (é o número principal, estilo IFEval estrito)
  · **fidelidade** — % de resumos sem número inventado e sem entidade inventada
  · **cobertura** — % dos fatos essenciais que sobreviveram
  · **compressão** — mediana da razão palavras(resumo)/palavras(fonte)

⚠️ O que o número NÃO diz: se o texto é legível, coerente ou bem escrito. Ver o cabeçalho de
   `resumo_pt_verificadores.py` — isto é um piso de utilidade, não uma nota de qualidade.

Uso:
    python comeia/eval/eval_resumo_pt.py --model BrCamp/bee-350m-pt-base
    python comeia/eval/eval_resumo_pt.py --dry-run       # guardas + LEAD-2, sem modelo
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resumo_pt_verificadores import LIMITES, avaliar_resumo  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent.parent
DADOS = RAIZ / "comeia" / "eval" / "benchmarks" / "resumo_pt.jsonl"
MODELO_PADRAO = "BrCamp/bee-350m-pt-base"

PEDIDO = ("Resuma o texto abaixo em duas frases, mantendo os números e os nomes exatamente "
          "como aparecem.")


def lead_k(fonte: str, k: int = 2) -> str:
    return ". ".join(fonte.split(". ")[:k]) + "."


def agregar(pares: list[tuple[dict, str]]) -> dict:
    """Agrega os vereditos. Devolve o dicionário que vira relatório e JSON."""
    vereditos = [(it, avaliar_resumo(r, it)) for it, r in pares]
    n = len(vereditos)
    falhas = Counter()
    for _, v in vereditos:
        for cond, ok in v["condicoes"].items():
            if not ok:
                falhas[cond] += 1
    cob = [c / m for _, v in vereditos for c, m in [v["cobertura"]] if m]
    return {
        "n": n,
        "util": sum(v["ok"] for _, v in vereditos) / n,
        "sem_invencao": sum(v["condicoes"]["sem_numero_inventado"]
                            and v["condicoes"]["sem_entidade_inventada"]
                            for _, v in vereditos) / n,
        "cobertura_media": st.mean(cob) if cob else 0.0,
        "compressao_mediana": st.median(v["razao_compressao"] for _, v in vereditos),
        "falhas_por_condicao": dict(falhas),
        "vereditos": vereditos,
    }


def guardas() -> None:
    """🔴 Régua validada antes de qualquer modelo. Sem isto o número não é interpretável."""
    print("-- guardas")
    import importlib
    if importlib.import_module("testar_resumo_pt").main() != 0:
        print("🔴 ABORTA: os gabaritos do avaliador de resumo falharam (acima).",
              file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO_PADRAO)
    ap.add_argument("--peft", default=None)
    ap.add_argument("--dados", type=Path, default=DADOS)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--max-new", type=int, default=160)
    ap.add_argument("--lote", type=int, default=8)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--chat", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    itens = [json.loads(l) for l in a.dados.read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limite:
        itens = itens[:a.limite]

    print("=" * 78)
    print("RESUMO PT — invencao, omissao e compressao, verificadas por execucao")
    print("=" * 78)
    print(f"dados : {a.dados.name} · {len(itens)} itens · limites {LIMITES}")
    print(f"modelo: {a.model}" + (f" + adapter {a.peft}" if a.peft else ""))
    guardas()

    # o piso, medido sempre — com ou sem modelo
    base = agregar([(it, lead_k(it["fonte"])) for it in itens])
    ref = agregar([(it, it["resumo_referencia"]) for it in itens])
    print("")
    print(f"  PISO   LEAD-2 (copiar 2 frases): util {100 * base['util']:.1f}% · "
          f"cobertura {100 * base['cobertura_media']:.1f}% · "
          f"compressao {base['compressao_mediana']:.2f}")
    print(f"  TETO   referencia sintetica     : util {100 * ref['util']:.1f}% · "
          f"cobertura {100 * ref['cobertura_media']:.1f}% · "
          f"compressao {ref['compressao_mediana']:.2f}")

    if a.dry_run:
        print("")
        print("✅ DRY-RUN: guardas e piso calculados. Nenhum modelo foi carregado.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    _AQUI = str(Path(__file__).resolve().parent)
    if _AQUI not in sys.path:
        sys.path.insert(0, _AQUI)
    from paradas import ids_de_parada
    # 🔴 Ver comeia/eval/paradas.py: sem parada, um modelo que APRENDEU a terminar
    #    gera ate o teto, o caso vira "truncado" e o parser recebe N respostas
    #    concatenadas. A regua marca 0% justamente no modelo que acertou.
    PARADAS = ids_de_parada(tok, a.chat)
    print(f"paradas: {{PARADAS}}")
    tok.padding_side = "left"
    modelo = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda().eval()
    if a.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, a.peft).eval()

    pares, t0, lote, i = [], time.time(), a.lote, 0
    while i < len(itens):
        bloco = itens[i:i + lote]
        if a.chat:
            textos = [tok.apply_chat_template(
                [{"role": "user", "content": f"{PEDIDO}\n\n{b['fonte']}"}],
                tokenize=False, add_generation_prompt=True) for b in bloco]
        else:
            textos = [f"{PEDIDO}\n\nTexto: {b['fonte']}\n\nResumo:" for b in bloco]
        ent = tok(textos, return_tensors="pt", padding=True, truncation=True,
                  max_length=1024).to("cuda")
        try:
            with torch.no_grad():
                saida = modelo.generate(
                    **ent, max_new_tokens=a.max_new,
                    do_sample=a.temp > 0, temperature=a.temp if a.temp > 0 else None,
                    eos_token_id=PARADAS, pad_token_id=tok.pad_token_id)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if lote == 1:
                raise
            lote = max(1, lote // 2)
            print(f"  ⚠️ OOM — lote reduzido para {lote}, refazendo o bloco", flush=True)
            continue
        for j, b in enumerate(bloco):
            novo = saida[j][ent["input_ids"].shape[1]:]
            pares.append((b, tok.decode(novo, skip_special_tokens=True).strip()))
        i += len(bloco)
        torch.cuda.empty_cache()
        dt = (time.time() - t0) / 60
        print(f"  {i}/{len(itens)} · {dt:.1f} min · resta ~{dt / i * (len(itens) - i):.1f} min",
              flush=True)

    r = agregar(pares)
    print("")
    print("=" * 78)
    print("RESULTADO")
    print("=" * 78)
    print(f"  MODELO {a.model.split('/')[-1]:24}: util {100 * r['util']:.1f}% · "
          f"cobertura {100 * r['cobertura_media']:.1f}% · "
          f"compressao {r['compressao_mediana']:.2f}")
    print(f"  sem invencao (numero e entidade)   : {100 * r['sem_invencao']:.1f}%")

    delta = 100 * (r["util"] - base["util"])
    print("")
    if delta <= 0:
        print(f"  🔴 O MODELO PERDE PARA O LEAD-2 por {-delta:.1f} pp.")
        print("     Copiar as duas primeiras frases da fonte e' melhor que rodar o modelo.")
        print("     'Sabe resumir' e' frase sem lastro enquanto este numero for negativo.")
    else:
        print(f"  ✅ o modelo supera o LEAD-2 por {delta:+.1f} pp — ha' capacidade acima do "
              f"trivial")

    print("")
    print("  o que reprovou (contagem por condicao):")
    for cond, c in Counter(r["falhas_por_condicao"]).most_common():
        print(f"    {cond:26} {c:>4}/{r['n']}   (LEAD-2: "
              f"{base['falhas_por_condicao'].get(cond, 0)})")

    print("")
    print("  exemplos de falha:")
    respostas = {it["id"]: r_ for it, r_ in pares}
    for it, v in [(x, vv) for x, vv in r["vereditos"] if not vv["ok"]][:5]:
        print("")
        print(f"   [{it['id']}] {[k for k, ok in v['condicoes'].items() if not ok]}")
        print(f"     saiu: {respostas[it['id']][:110]!r}")

    saida_json = RAIZ / "docs" / f"resumo-pt{('-' + a.tag) if a.tag else ''}.json"
    saida_json.write_text(json.dumps({
        "modelo": a.model, "peft": a.peft, "n": r["n"], "limites": LIMITES,
        "modelo_util": r["util"], "modelo_cobertura": r["cobertura_media"],
        "modelo_sem_invencao": r["sem_invencao"],
        "modelo_compressao": r["compressao_mediana"],
        "piso_lead2_util": base["util"], "teto_referencia_util": ref["util"],
        "falhas_por_condicao": r["falhas_por_condicao"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  relatorio: {saida_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
