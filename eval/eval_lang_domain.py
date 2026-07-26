"""Teste de IDIOMA nas abelhas de DOMÍNIO (`coder` e `agentica`).

Por que existe: a `chat_ptbr` foi treinada em 5.657 exemplos 100% PT-BR e
derrubou o inglês de 12/12 para 2/12 — o adapter respondia em português a
perguntas em inglês. A `agentica` foi treinada com ~5/6 dos dados em PT-BR e a
`coder` com docstrings em português. **As duas estão ligadas em produção e
nunca passaram por esse teste.** Este script fecha essa lacuna.

⚠️ Por que NÃO reusar `chat_probes_multiling.jsonl`: o roteador nunca manda
chat genérico para estas abelhas. Medir a `coder` com "por que o mar é salgado"
mede uma rota que não existe. Os probes daqui são DE DOMÍNIO — pedido de código
e pedido de ferramenta — nos 4 idiomas. É o que realmente roda.

O que mede (tudo DETERMINÍSTICO — sem juiz, sem chave de API):

  coder    (expect=code)
    1. TEM CÓDIGO?   — a abelha continua produzindo função em outro idioma, ou
                       colapsa? (mode collapse)
    2. IDIOMA DA PROSA — a explicação saiu no idioma do pedido? Mede-se DEPOIS
                       de `strip_code`, senão `return`/`import` contam como
                       inglês e todo exemplo vira falso positivo.

  agentica (expect=tool)  → JSON VÁLIDO contra o catálogo (mesma validação da
                       destilação). Se ela chama ferramenta em PT mas responde
                       em texto em inglês, o tool-use não é multilíngue.
  agentica (expect=text)  → OVER-CALLING (virou JSON sem precisar) + idioma.

Régua idêntica para base e adapter: mesma decodificação, mesmo system prompt,
uma carga só do modelo (`disable_adapter()` para o base).

⚠️ CONFOUND declarado: os system prompts de produção das DUAS abelhas estão em
PORTUGUÊS. Eles agem igual nos dois modelos, então o DELTA continua sendo do
adapter — mas se o BASE também vazar para PT, a causa é o system prompt, não o
treino, e o conserto é outro (prompt neutro / no idioma da query). A coluna do
base é esse diagnóstico, de graça.

Legenda `[? n/n]`: detector indeciso (resposta curta demais para dar sinal) —
é diferente de idioma errado, e por isso aparece separado.

Uso (na L4):
    python eval/eval_lang_domain.py --bee coder    --peft /content/qwen35-4b-coder
    python eval/eval_lang_domain.py --bee agentica --peft /content/drive/MyDrive/qwen35-4b-agentica
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import detect_lang, read_jsonl, strip_code, strip_think  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", ROOT / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PROBES = ROOT / "eval" / "probes_multiling_domain.jsonl"
BEES = ROOT / "orchestrator" / "bees.json"
NOMES = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês"}


def system_de_producao(bee: str) -> str:
    """O system prompt que a abelha REALMENTE recebe na comeia (bees.json).

    Para a agentica, o catálogo de ferramentas é anexado: sem ele o modelo não
    tem como nomear ferramenta nenhuma, e o teste mediria só a nossa omissão.
    """
    reg = json.loads(BEES.read_text(encoding="utf-8"))
    sp = next((b.get("system_prompt") for b in reg["bees"] if b["name"] == bee), None)
    if bee == "agentica":
        return _d7.build_system(_d7.load_tools())
    return sp or ""


def tem_codigo(t: str) -> bool:
    return "```" in t or "def " in t


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", required=True)
    ap.add_argument("--bee", required=True, choices=["coder", "agentica"])
    ap.add_argument("--probes", type=Path, default=PROBES)
    ap.add_argument("--langs", default="pt,en,es,fr")
    ap.add_argument("--limit", type=int, default=0, help="por idioma; 0 = todos")
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--system", default=None,
                    help="sobrescreve o system prompt de producao. Serve para SEPARAR "
                         "duas causas de fuga de idioma: o system prompt em portugues "
                         "vs o treino em portugues. Rode o mesmo idioma com um prompt "
                         "NEUTRO — se a fuga sumir nos dois modelos, a culpa era do "
                         "prompt; se sobrar so no adapter, a culpa e do treino.")
    args = ap.parse_args()

    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    por_lang: dict[str, list[dict]] = defaultdict(list)
    for r in read_jsonl(args.probes):
        if r.get("bee") == args.bee and r.get("lang") in langs:
            por_lang[r["lang"]].append(r)
    if args.limit:
        por_lang = {k: v[: args.limit] for k, v in por_lang.items()}
    total = sum(len(v) for v in por_lang.values())
    if not total:
        print("ERRO: nenhum probe.", file=sys.stderr)
        return 1

    system = args.system if args.system is not None else system_de_producao(args.bee)
    tools = _d7.load_tools() if args.bee == "agentica" else {}

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kw: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)

    print(f"abelha : {args.bee}")
    print(f"adapter: {args.peft}")
    print(f"probes : {total} em {len(por_lang)} idiomas ({', '.join(langs)})")
    print(f"system : {system[:70]}...\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    def gerar(prompt: str) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        tpl = {"add_generation_prompt": True, "return_tensors": "pt", "return_dict": True}
        try:
            enc = tok.apply_chat_template(msgs, enable_thinking=False, **tpl)
        except TypeError:
            enc = tok.apply_chat_template(msgs, **tpl)
        inputs = {k: v.to("cuda") for k, v in dict(enc).items() if hasattr(v, "to")}
        plen = inputs["input_ids"].shape[1]
        with torch.no_grad():
            g = model.generate(**inputs, max_new_tokens=args.max_new, do_sample=False,
                               pad_token_id=tok.eos_token_id)
        return strip_think(tok.decode(g[0][plen:], skip_special_tokens=True).strip())[0]

    # métricas por idioma, para os dois modelos. Os denominadores (`n_*`) são
    # contados NA MEDIÇÃO — reconstruí-los depois a partir das fugas é frágil.
    def M():
        return {"n_formato": 0, "formato_ok": 0,
                "n_idioma": 0, "idioma_ok": 0, "idioma_ind": 0}
    stats = {l: {"base": M(), "adapter": M()} for l in por_lang}
    fugas: list[dict] = []
    feito = 0

    for lang, rows in por_lang.items():
        for row in rows:
            p, expect = row["prompt"], row["expect"]
            saidas = {"adapter": gerar(p)}
            with model.disable_adapter():
                saidas["base"] = gerar(p)

            for nome, txt in saidas.items():
                d = stats[lang][nome]

                # ── 1. formato: a abelha continua fazendo o trabalho dela? ──
                d["n_formato"] += 1
                if expect == "code":
                    d["formato_ok"] += int(tem_codigo(txt))
                elif expect == "tool":
                    obj = _d7.extract_json(txt)
                    d["formato_ok"] += int(obj is not None
                                           and _d7.validate_call(obj, tools) is None)
                else:                             # text: NÃO pode virar JSON
                    d["formato_ok"] += int(_d7.extract_json(txt) is None)

                # ── 2. idioma da PROSA (código fora; JSON não tem idioma) ──
                if expect == "tool":
                    continue
                prosa = strip_code(txt) if expect == "code" else txt
                det = detect_lang(prosa)
                d["n_idioma"] += 1
                if det == lang:
                    d["idioma_ok"] += 1
                elif det == "?":
                    d["idioma_ind"] += 1
                else:
                    fugas.append({"lang": lang, "modelo": nome, "detectado": det,
                                  "prompt": p[:50], "resposta": prosa.strip()[:90]})

            feito += 1
            if feito % 6 == 0 or feito == total:
                print(f"  {feito}/{total}", flush=True)

    # ── relatório ──
    rotulo = {"coder": "TEM CÓDIGO", "agentica": "FORMATO CERTO (JSON/texto)"}[args.bee]
    print("\n" + "=" * 76)
    print(f"⭐ ABELHA `{args.bee}` — o treino em PT-BR quebrou os outros idiomas?")
    print("=" * 76)
    extra = "  (tool-calls fora: JSON não tem idioma)" if args.bee == "agentica" else ""
    blocos = [(f"1) {rotulo} — a abelha continua fazendo o trabalho dela?",
               "formato_ok", "n_formato"),
              (f"2) IDIOMA DA RESPOSTA — respondeu no idioma do pedido?{extra}",
               "idioma_ok", "n_idioma")]

    for titulo, chave_ok, chave_n in blocos:
        print(f"\n{titulo}")
        print(f"{'idioma':<12} {'base':>12} {'ADAPTER':>12}   leitura")
        print("-" * 76)
        tb = ta = tn = 0
        for lang in por_lang:
            b, a = stats[lang]["base"], stats[lang]["adapter"]
            n = b[chave_n]
            if not n:
                continue
            tb += b[chave_ok]; ta += a[chave_ok]; tn += n
            delta = a[chave_ok] - b[chave_ok]
            leitura = ("igual" if delta == 0 else
                       f"⚠️ ADAPTER PIOR ({delta})" if delta < 0 else f"adapter melhor (+{delta})")
            # '?' = detector indeciso (resposta curta demais), NÃO idioma errado.
            ind = (f"   [? {b['idioma_ind']}/{a['idioma_ind']}]"
                   if chave_ok == "idioma_ok" and (b["idioma_ind"] or a["idioma_ind"]) else "")
            print(f"{NOMES.get(lang, lang):<12} {b[chave_ok]:>5}/{n:<6} "
                  f"{a[chave_ok]:>5}/{n:<6}   {leitura}{ind}")
        print("-" * 76)
        veredito = ("⚠️ REGRESSÃO" if ta < tb else
                    "sem regressão" if ta == tb else "adapter melhor")
        print(f"{'TOTAL':<12} {tb:>5}/{tn:<6} {ta:>5}/{tn:<6}   {veredito}")

    if fugas:
        print(f"\nrespondeu no idioma ERRADO ({len(fugas)} casos):")
        for f in fugas[:10]:
            print(f"   [{f['modelo']:>7}] pediu em {f['lang']}, respondeu em {f['detectado']}: "
                  f"{f['resposta'][:70]}")
    print("=" * 76)

    if args.tag:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"lang_domain_{args.bee}_{args.tag}.json"
        p.write_text(json.dumps({"bee": args.bee, "peft": args.peft, "stats": stats,
                                 "fugas": fugas}, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
