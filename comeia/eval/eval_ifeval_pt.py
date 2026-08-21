"""Mede o IFEval-PT: quanto o modelo OBEDECE a instruções verificáveis por execução.

⭐ O QUE ESTE NÚMERO É, E O QUE ELE NÃO É

Ele mede **obediência**, não qualidade. Um modelo pode escrever besteira em exatamente 3
parágrafos e pontuar 100%. Isso é deliberado: "seguir instrução" e "escrever bem" são
capacidades distintas, e o hábito de misturá-las num número só é o que torna avaliação de
geração de conteúdo tão fácil de fraudar — basta um juiz-LLM generoso.

Quatro métricas são reportadas, e a diferença entre elas importa:

  · **estrito por instrução** — das 1.002 instruções, quantas foram cumpridas;
  · **estrito por prompt**    — dos 541 prompts, em quantos TODAS foram cumpridas;
  · **frouxo por instrução**  — idem, mas sobre variantes da resposta (ver abaixo);
  · **frouxo por prompt**     — idem.

⚠️ POR QUE EXISTE UMA MÉTRICA "FROUXA" — e por que ela não é indulgência

O IFEval original (arXiv:2311.07911) reporta as duas porque modelos costumam obedecer e
**estragar na embalagem**: acrescentam "Claro! Aqui está:" antes da resposta, ou envolvem
tudo em ```markdown```. A instrução foi cumprida; o invólucro é que reprova.

A variante frouxa testa a resposta também sem esses invólucros. É importante para um modelo
pequeno: o Bee-350M **base** não tem chat template, e a diferença entre estrito e frouxo diz
se o problema é *não saber obedecer* ou *não saber calar a boca* — duas causas com curas
completamente diferentes. Uma se resolve com SFT de formato; a outra com dado melhor.

🔴 GUARDA OBRIGATÓRIA: este script recusa rodar se `validar_ifeval_pt.py` não passar antes.
   Um benchmark com item impossível mede o azar do modelo, não a capacidade dele — e este
   projeto já mediu 23,5% quando o real era 57,6% exatamente assim.

Uso:
    python comeia/eval/eval_ifeval_pt.py --model BrCamp/bee-350m-pt-base
    python comeia/eval/eval_ifeval_pt.py --model ... --peft models/bee-sft-adapter --chat
    python comeia/eval/eval_ifeval_pt.py --dry-run     # guardas, sem carregar modelo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifeval_pt_verificadores import verificar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DADOS = ROOT / "comeia" / "eval" / "benchmarks" / "ifeval_pt.jsonl"
MODELO_PADRAO = "BrCamp/bee-350m-pt-base"


# ------------------------------------------------------------------ variantes "frouxas"
def variantes(resposta: str) -> list[str]:
    """Formas alternativas da mesma resposta, sem invólucros que o modelo costuma somar.

    ⚠️ Cada transformação aqui é uma DECISÃO sobre o que conta como "a resposta". Elas são
    conservadoras de propósito: removem apenas envelope óbvio (preâmbulo de cortesia, cerca
    de código), nunca conteúdo. Se uma variante removesse conteúdo, a métrica frouxa
    inflaria — que é o oposto do que este arquivo existe para fazer.
    """
    v = {resposta, resposta.strip()}
    t = resposta.strip()

    # 1) cerca de codigo em volta de tudo
    m = re.match(r"^```[a-zA-Z]*\s*\n(.*?)\n?```$", t, re.S)
    if m:
        v.add(m.group(1).strip())

    # 2) preambulo de cortesia ate os dois-pontos, na PRIMEIRA linha apenas
    linhas = t.split("\n")
    if linhas and len(linhas[0]) < 90 and ":" in linhas[0]:
        cabeca = linhas[0].lower()
        if any(p in cabeca for p in ("claro", "aqui está", "aqui esta", "segue",
                                     "com certeza", "resposta")):
            v.add("\n".join(linhas[1:]).strip())

    # 3) primeira linha inteira, se for so' saudacao curta sem dois-pontos
    if len(linhas) > 1 and len(linhas[0]) < 60 and linhas[0].rstrip().endswith(("!", ".")):
        if any(p in linhas[0].lower() for p in ("claro", "certeza", "vamos", "olá", "ola")):
            v.add("\n".join(linhas[1:]).strip())

    return [x for x in v if x]


def avaliar_item(resposta: str, instrucoes: list[dict]) -> dict:
    """Avalia um item nos dois regimes. Devolve contagens e detalhe."""
    ok_estrito, det = verificar(resposta, instrucoes)
    n_ok_estrito = sum(1 for d in det if d["ok"])

    # frouxo: a MELHOR variante, por instrucao (nao por prompt) — uma variante pode
    # resolver a instrucao A e outra a B, e as duas contam.
    melhor_por_ins = [False] * len(instrucoes)
    ok_frouxo_prompt = False
    for var in variantes(resposta):
        okv, detv = verificar(var, instrucoes)
        ok_frouxo_prompt = ok_frouxo_prompt or okv
        for i, d in enumerate(detv):
            melhor_por_ins[i] = melhor_por_ins[i] or d["ok"]

    return {
        "ok_estrito_prompt": ok_estrito,
        "n_ok_estrito": n_ok_estrito,
        "ok_frouxo_prompt": ok_frouxo_prompt,
        "n_ok_frouxo": sum(melhor_por_ins),
        "n_instrucoes": len(instrucoes),
        "detalhe": det,
    }


def guardas(itens: list[dict]) -> None:
    """🔴 Recusa medir com régua não validada. Duas provas, nesta ordem:

    1. todo prompt tem PELO MENOS uma resposta que o satisfaz (satisfazibilidade);
    2. essa resposta, passada pelo avaliador deste arquivo, pontua 100%.

    A segunda não é redundante: o validador prova que a régua do `validar_ifeval_pt.py`
    aceita a resposta; esta prova que a régua DESTE runner — que inclui `variantes()` e a
    agregação estrito/frouxo — também aceita. Um bug aqui reprovaria um modelo perfeito, e
    o sintoma seria indistinguível de "o modelo é ruim".
    """
    print("-- guardas")

    # 1-2) as duas suites de gabarito. Rodam AQUI, e nao "por fora", porque guarda fora do
    #      fluxo nao guarda nada — este projeto ja' escreveu uma guarda de rotulos, commitou,
    #      e nunca a chamou. O custo e' de um segundo.
    import importlib
    for mod, rotulo in (("testar_verificadores_ifeval_pt", "verificadores"),
                        ("testar_variantes_ifeval_pt", "metrica frouxa")):
        if importlib.import_module(mod).main() != 0:
            print(f"🔴 ABORTA: os gabaritos de {rotulo} falharam (acima).", file=sys.stderr)
            raise SystemExit(1)
    print(f"   ✅ gabaritos de verificadores e da metrica frouxa: 100%")

    from validar_ifeval_pt import resolver
    refs, ruins = [], []
    for it in itens:
        texto, ok = resolver(it["instrucoes"])
        refs.append(texto)
        if not ok:
            ruins.append(it["id"])
    if ruins:
        print(f"🔴 ABORTA: {len(ruins)} prompt(s) sao INSATISFAZIVEIS: {ruins[:8]}",
              file=sys.stderr)
        print("   Um item impossivel mede o azar do modelo, nao a capacidade dele.",
              file=sys.stderr)
        print("   Rode comeia/eval/validar_ifeval_pt.py e corrija antes.", file=sys.stderr)
        raise SystemExit(1)
    print(f"   ✅ 3/4: {len(itens)}/{len(itens)} prompts sao satisfaziveis")

    falhos = [it["id"] for it, ref in zip(itens, refs)
              if not avaliar_item(ref, it["instrucoes"])["ok_estrito_prompt"]]
    if falhos:
        print(f"🔴 ABORTA: a resposta de referencia falha em {len(falhos)} item(ns): "
              f"{falhos[:8]}", file=sys.stderr)
        print("   O defeito e' do AVALIADOR, nao do modelo — nenhum modelo foi carregado.",
              file=sys.stderr)
        raise SystemExit(1)
    print(f"   ✅ 4/4: resposta de referencia pontua {len(itens)}/{len(itens)} = 100%")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO_PADRAO)
    ap.add_argument("--peft", default=None, help="adapter LoRA opcional")
    ap.add_argument("--dados", type=Path, default=DADOS)
    ap.add_argument("--temp", type=float, default=0.0, help="0 = greedy (o padrao do IFEval)")
    ap.add_argument("--max-new", type=int, default=512)
    ap.add_argument("--lote", type=int, default=8)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--chat", action="store_true",
                    help="usa chat template (so' pos-SFT; o BASE nao tem)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    itens = [json.loads(l) for l in a.dados.read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    if a.limite:
        itens = itens[:a.limite]

    print("=" * 78)
    print("IFEval-PT — obediencia a instrucao, verificada por execucao")
    print("=" * 78)
    print(f"dados : {a.dados.name} · {len(itens)} prompts · "
          f"{sum(i['n_instrucoes'] for i in itens)} instrucoes")
    print(f"modelo: {a.model}" + (f" + adapter {a.peft}" if a.peft else ""))
    guardas(itens)

    if a.dry_run:
        print("\n✅ DRY-RUN: guardas passaram. Nenhum modelo foi carregado.")
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
    tok.padding_side = "left"                 # geracao em lote exige padding a esquerda
    modelo = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda().eval()
    if a.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, a.peft).eval()

    respostas, t0 = [], time.time()
    lote = a.lote
    i = 0
    while i < len(itens):
        bloco = itens[i:i + lote]
        if a.chat:
            textos = [tok.apply_chat_template([{"role": "user", "content": b["prompt"]}],
                                              tokenize=False, add_generation_prompt=True)
                      for b in bloco]
        else:
            # ⚠️ O modelo BASE nao tem chat template. O formato abaixo e' o minimo que
            #    sinaliza "aqui comeca a resposta" sem ensinar formato nenhum — usar um
            #    template inventado aqui contaminaria a medicao com uma escolha de prompt.
            textos = [f"Pedido: {b['prompt']}\nResposta:" for b in bloco]
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
            respostas.append((b, tok.decode(novo, skip_special_tokens=True).strip()))
        i += len(bloco)
        torch.cuda.empty_cache()
        if i % (lote * 5) == 0 or i >= len(itens):
            dt = (time.time() - t0) / 60
            print(f"  {i}/{len(itens)} · {dt:.1f} min · resta ~{dt/max(1,i)*(len(itens)-i):.1f} min",
                  flush=True)

    # ---------------------------------------------------------------- agregacao
    n_ins = sum(i["n_instrucoes"] for i in itens)
    est_p = est_i = fro_p = fro_i = 0
    falhas_por_tipo, exemplos = Counter(), []
    for it, resp in respostas:
        r = avaliar_item(resp, it["instrucoes"])
        est_p += r["ok_estrito_prompt"]
        est_i += r["n_ok_estrito"]
        fro_p += r["ok_frouxo_prompt"]
        fro_i += r["n_ok_frouxo"]
        for d in r["detalhe"]:
            if not d["ok"]:
                falhas_por_tipo[d["tipo"]] += 1
        if not r["ok_estrito_prompt"] and len(exemplos) < 5:
            exemplos.append((it, resp, [d["tipo"] for d in r["detalhe"] if not d["ok"]]))

    print("\n" + "=" * 78)
    print("RESULTADO")
    print("=" * 78)
    print(f"  estrito · por prompt    {est_p:>4}/{len(respostas):<4} = {100*est_p/len(respostas):>5.1f}%")
    print(f"  estrito · por instrucao {est_i:>4}/{n_ins:<4} = {100*est_i/n_ins:>5.1f}%")
    print(f"  frouxo  · por prompt    {fro_p:>4}/{len(respostas):<4} = {100*fro_p/len(respostas):>5.1f}%")
    print(f"  frouxo  · por instrucao {fro_i:>4}/{n_ins:<4} = {100*fro_i/n_ins:>5.1f}%")

    delta = 100 * (fro_i - est_i) / n_ins
    print(f"\n  diferenca frouxo-estrito: {delta:+.1f} pp por instrucao")
    if delta > 5:
        print("  ⚠️ diferenca GRANDE: o modelo obedece mas embrulha a resposta (preambulo,")
        print("     cerca de codigo). Isso se conserta com SFT de FORMATO, que e' barato —")
        print("     nao confundir com 'nao sabe obedecer', que exigiria dado melhor.")

    print("\n  instrucoes que mais falharam:")
    for t, c in falhas_por_tipo.most_common(8):
        print(f"    {t:32} {c:>4}")

    print("\n  exemplos de falha:")
    for it, resp, ruins in exemplos:
        print(f"\n   [{it['id']}] falhou em: {ruins}")
        print(f"     prompt: {it['prompt'][:95]}")
        print(f"     saiu  : {resp[:95]!r}")

    ref = {"modelo": a.model, "peft": a.peft, "tag": a.tag, "n_prompts": len(respostas),
           "n_instrucoes": n_ins,
           "estrito_prompt": est_p / len(respostas), "estrito_instrucao": est_i / n_ins,
           "frouxo_prompt": fro_p / len(respostas), "frouxo_instrucao": fro_i / n_ins,
           "falhas_por_tipo": dict(falhas_por_tipo)}
    saida_json = ROOT / "docs" / f"ifeval-pt{('-' + a.tag) if a.tag else ''}.json"
    saida_json.write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  relatorio: {saida_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
