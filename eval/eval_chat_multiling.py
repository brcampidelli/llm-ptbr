"""Avaliação MULTILÍNGUE da abelha chat — a régua que ela nunca teve.

Por que existe: a `chat_ptbr` (SFT-v2, 5.657 exemplos 100% PT-BR) é a abelha
DEFAULT — recebe ~40% do tráfego no roteamento — e é a ÚNICA sem ganho
comprovado. Foi avaliada só em múltipla escolha (n=300, 0 de 7 tasks, tudo no
ruído), que é a régua errada: SFT muda estilo e formato, não conhecimento.

⭐ E há um risco NÃO MEDIDO: o backbone cobre 201 idiomas; o adapter viu só
PT-BR. Acabamos de medir na abelha coder o que treino estreito faz com o que
está fora dele: +40 pp nas difíceis, −17,5 pp nas fáceis. Não há razão para os
outros 200 idiomas escaparem do mesmo mecanismo. Este script mede isso.

Desenho (as lições caras deste projeto, aplicadas):
  • prompts HELD-OUT de verdade — escritos à mão, NÃO vêm de seeds_ptbr*;
  • MESMA régua para os dois: mesma decodificação, mesmo max_new, mesmo prompt;
  • juiz ABERTO (regra dura de licença) com veredito DELIMITADO `VEREDITO=X` e
    max_tokens folgado — sem isso, letras soltas do raciocínio viram falso
    empate (bug real do 06_build_preferences);
  • posição A/B RANDOMIZADA por item, para o juiz não ter viés de ordem;
  • empate é resultado legítimo e é reportado (não forçamos vencedor).

Uso (na L4):
    python eval/eval_chat_multiling.py --peft <adapter_chat>
    python eval/eval_chat_multiling.py --peft ... --langs pt,en --limit 8

Requer OPENROUTER_API_KEY (juiz).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402
from config import DEFAULT_TEACHER, assert_teacher_allowed  # noqa: E402
from teacher_api import call_teacher  # noqa: E402

PROBES = ROOT / "eval" / "chat_probes_multiling.jsonl"
NOMES = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês"}

JUDGE_SYSTEM = (
    "Você é um avaliador imparcial de qualidade de respostas de assistentes de IA. "
    "Dada uma PERGUNTA e duas respostas (A e B), escolha a melhor considerando: "
    "(1) responde de fato o que foi pedido, (2) correção, (3) clareza e organização, "
    "(4) está no MESMO IDIOMA da pergunta e soa natural nesse idioma. "
    "Ignore diferenças de tamanho que não afetem a qualidade. "
    "Ao FINAL escreva exatamente 'VEREDITO=A', 'VEREDITO=B' ou 'VEREDITO=E' (empate)."
)
# Delimitador inequívoco: juiz com reasoning solta letras soltas no meio do texto
# (o 'E' de "processo" já causou falso empate neste projeto).
_VERDICT = re.compile(r"VEREDITO\s*=\s*([ABE])", re.IGNORECASE)


def gerar(model, tok, prompt: str, max_new: int) -> str:
    import torch
    msgs = [{"role": "user", "content": prompt}]
    tpl = {"add_generation_prompt": True, "return_tensors": "pt", "return_dict": True}
    try:
        enc = tok.apply_chat_template(msgs, enable_thinking=False, **tpl)
    except TypeError:
        enc = tok.apply_chat_template(msgs, **tpl)
    inputs = {k: v.to("cuda") for k, v in dict(enc).items() if hasattr(v, "to")}
    plen = inputs["input_ids"].shape[1]
    with torch.no_grad():
        g = model.generate(**inputs, max_new_tokens=max_new, do_sample=False,
                           pad_token_id=tok.eos_token_id)
    return strip_think(tok.decode(g[0][plen:], skip_special_tokens=True).strip())[0]


def julgar(pergunta: str, a: str, b: str, juiz: str, key: str) -> str:
    q = (f"PERGUNTA:\n{pergunta}\n\nRESPOSTA A:\n{a}\n\nRESPOSTA B:\n{b}\n\n"
         "Qual é melhor? Justifique em 1-2 frases e termine com VEREDITO=A, "
         "VEREDITO=B ou VEREDITO=E.")
    try:
        raw = call_teacher(q, juiz, key, system=JUDGE_SYSTEM, temperature=0.0,
                           max_tokens=512)
    except Exception as e:
        print(f"  juiz falhou: {type(e).__name__}", file=sys.stderr)
        return "E"
    m = _VERDICT.search(raw)
    return m.group(1).upper() if m else "E"


def main() -> int:
    import os
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", required=True, help="adapter da abelha chat a testar")
    ap.add_argument("--probes", type=Path, default=PROBES)
    ap.add_argument("--langs", default="pt,en,es,fr")
    ap.add_argument("--limit", type=int, default=0, help="por idioma; 0 = todos")
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--judge", default=DEFAULT_TEACHER)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    assert_teacher_allowed(args.judge)          # REGRA DURA: juiz aberto
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("ERRO: defina OPENROUTER_API_KEY (juiz).", file=sys.stderr)
        return 1

    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    por_lang: dict[str, list[str]] = defaultdict(list)
    for r in read_jsonl(args.probes):
        if r.get("lang") in langs:
            por_lang[r["lang"]].append(r["prompt"])
    if args.limit:
        por_lang = {k: v[: args.limit] for k, v in por_lang.items()}
    total = sum(len(v) for v in por_lang.values())
    if not total:
        print("ERRO: nenhum prompt.", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kw: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)

    print(f"modelo : {args.model}")
    print(f"adapter: {args.peft}")
    print(f"juiz   : {args.judge}  (aberto)")
    print(f"prompts: {total} em {len(por_lang)} idiomas ({', '.join(langs)})\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    # Uma carga só: com adapter ligado = abelha; desligado = base. Mesma régua.
    resultados: dict[str, dict[str, int]] = {l: {"base": 0, "adapter": 0, "empate": 0}
                                             for l in por_lang}
    rng = random.Random(args.seed)
    exemplos: list[dict] = []
    feito = 0

    for lang, prompts in por_lang.items():
        for p in prompts:
            model.set_adapter(model.active_adapters[0] if model.active_adapters else "default")
            r_adapter = gerar(model, tok, p, args.max_new)
            with model.disable_adapter():
                r_base = gerar(model, tok, p, args.max_new)

            swap = rng.random() < 0.5          # randomiza posição A/B
            a, b = (r_base, r_adapter) if swap else (r_adapter, r_base)
            v = julgar(p, a, b, args.judge, key)
            if v == "E":
                venc = "empate"
            else:
                escolhido = a if v == "A" else b
                venc = "base" if escolhido is r_base else "adapter"
            resultados[lang][venc] += 1
            exemplos.append({"lang": lang, "prompt": p[:80], "vencedor": venc})

            feito += 1
            if feito % 8 == 0 or feito == total:
                print(f"  {feito}/{total}", flush=True)

    print("\n" + "=" * 68)
    print(f"{'idioma':<12} {'base':>8} {'ADAPTER':>9} {'empate':>8}   leitura")
    print("-" * 68)
    tot = {"base": 0, "adapter": 0, "empate": 0}
    for lang in por_lang:
        r = resultados[lang]
        n = sum(r.values())
        for k in tot:
            tot[k] += r[k]
        # Só conta como regressão/ganho quando há vencedor claro.
        decididos = r["base"] + r["adapter"]
        if decididos == 0:
            leitura = "empate total (adapter neutro)"
        elif r["adapter"] > r["base"]:
            leitura = f"adapter melhor ({r['adapter']}/{decididos})"
        elif r["base"] > r["adapter"]:
            leitura = f"⚠️ REGRESSAO ({r['base']}/{decididos} p/ o base)"
        else:
            leitura = "empate tecnico"
        print(f"{NOMES.get(lang, lang):<12} {r['base']:>8} {r['adapter']:>9} "
              f"{r['empate']:>8}   {leitura}")
    print("-" * 68)
    dec = tot["base"] + tot["adapter"]
    print(f"{'TOTAL':<12} {tot['base']:>8} {tot['adapter']:>9} {tot['empate']:>8}")
    if dec:
        print(f"\ntaxa de vitoria do adapter (entre os decididos): "
              f"{tot['adapter']}/{dec} = {tot['adapter']/dec:.1%}")
    print(f"empates: {tot['empate']}/{total} = {tot['empate']/total:.1%}  "
          "(empate alto = adapter nao muda nada)")
    print("=" * 68)

    if args.tag:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"chat_multiling_{args.tag}.json"
        p.write_text(json.dumps({"tag": args.tag, "peft": args.peft, "judge": args.judge,
                                 "por_idioma": resultados, "total": tot,
                                 "exemplos": exemplos}, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
