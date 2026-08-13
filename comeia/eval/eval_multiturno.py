"""Avalia o turno que o Bee nunca viu: responder DEPOIS de receber o retorno da ferramenta.

O eval agentico existente mede a CHAMADA (json valido, ferramenta certa, executa). Este mede
o passo seguinte: dado (system, user, assistant=chamada, tool=resultado), a resposta final
USA de fato o dado que voltou?

⭐ A metrica principal e ANCORAGEM: os valores concretos do retorno (temperatura, preco,
   nome de arquivo, itens) aparecem na resposta? E decidivel por comparacao de string, sem
   juiz subjetivo — e e exatamente a fronteira entre "usou a ferramenta" e "inventou".

   Um modelo que responde "Em Fortaleza faz 25°C" quando a ferramenta devolveu 23 nao esta
   usando a ferramenta: esta confabulando com mais passos. Para este projeto, cujo modelo
   ja inventa fatos com confianca, essa e A medida que importa.

Metricas:
  ancorado     — pelo menos um valor concreto do retorno aparece na resposta
  todos_vals   — TODOS os valores concretos aparecem (mais severo)
  contaminado  — a resposta traz numero que NAO estava no retorno (sinal de confabulacao)
  virou_json   — respondeu com outra tool call em vez de falar com o usuario

Uso:
    python comeia/eval/eval_multiturno.py --model models/ab_sim
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl, strip_think            # noqa: E402
from eval_agentic_exec import wilson                   # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PADRAO = RAIZ / "data" / "processed" / "sft_multiturno.eval.jsonl"


def _norm(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def valores_concretos(res: dict) -> list[str]:
    """Valores que uma resposta honesta citaria: numeros, nomes, itens de lista.

    Ignora chaves estruturais (booleanos, ids internos) — citar 'true' nao prova nada.
    """
    out: list[str] = []

    def _rec(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k.endswith("_id") or isinstance(x, bool):
                    continue
                _rec(x)
        elif isinstance(v, list):
            for x in v[:6]:
                _rec(x)
        elif isinstance(v, (int, float)):
            out.append(str(v))
        elif isinstance(v, str) and v.strip():
            # so a primeira linha de textos longos, e nada de placeholder
            primeiro = v.strip().splitlines()[0]
            if primeiro and not primeiro.startswith("["):
                out.append(primeiro[:60])
    _rec(res)
    return [v for v in out if len(str(v)) >= 2]


def aparece(valor: str, resposta: str) -> bool:
    v, r = _norm(valor), _norm(resposta)
    if v in r:
        return True
    # numero: aceitar com separador diferente (128400 vs 128.400,00 vs 128400.0)
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        so_digitos = v.replace(".", "").rstrip("0").rstrip(".")
        r_digitos = re.sub(r"[.,\s]", "", r)
        return bool(so_digitos) and so_digitos.replace(".", "") in r_digitos
    return False


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--peft", default=None,
                    help="adapter LoRA a carregar sobre o modelo (arquitetura de abelhas)")
    ap.add_argument("--data", type=Path, default=PADRAO)
    ap.add_argument("--max-new", type=int, default=160)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    linhas = list(read_jsonl(args.data))
    if args.limit:
        linhas = linhas[: args.limit]

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(dev)
    if args.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, args.peft)
        print(f"adapter: {args.peft}")
    modelo.eval()
    print(f"modelo : {args.model} · {dev}")
    print(f"holdout: {len(linhas)} dialogos multi-turno\n")

    n = ancorado = todos = contaminado = virou_json = vazio = 0
    exemplos: list[tuple] = []

    for i, row in enumerate(linhas, 1):
        msgs = list(row.get("prompt") or [])
        retorno = next((m["content"] for m in reversed(msgs) if m["role"] == "tool"), "{}")
        try:
            res = json.loads(retorno)
        except Exception:
            res = {}
        vals = valores_concretos(res)

        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ent = tok(txt, return_tensors="pt").to(dev)
        p = ent["input_ids"].shape[1]
        with torch.no_grad():
            g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=False,
                                pad_token_id=tok.pad_token_id or tok.eos_token_id)
        resposta, _ = strip_think(tok.decode(g[0][p:], skip_special_tokens=True).strip())

        n += 1
        if not resposta:
            vazio += 1
            continue
        if _d7.extract_json(resposta) is not None:
            virou_json += 1                       # respondeu com outra chamada, nao ao usuario
            continue

        achados = [v for v in vals if aparece(v, resposta)]
        if achados:
            ancorado += 1
        if vals and len(achados) == len(vals):
            todos += 1

        # numeros na resposta que NAO vieram do retorno = confabulacao
        nums_resp = set(re.findall(r"-?\d+(?:[.,]\d+)?", resposta))
        nums_res = set(re.findall(r"-?\d+(?:[.,]\d+)?", retorno))
        if nums_resp - nums_res:
            contaminado += 1
            if len(exemplos) < 5:
                exemplos.append((sorted(nums_resp - nums_res)[:3], resposta[:80]))

        if i % 20 == 0 or i == len(linhas):
            print(f"  {i}/{len(linhas)}", flush=True)

    def linha(rot: str, k: int) -> str:
        lo, hi = wilson(k, n)
        return f"  {rot:<38} {k}/{n} = {k/max(1,n):6.1%}   [{lo:.1%}–{hi:.1%}]"

    print("\n" + "=" * 74)
    print(f"DIALOGOS MULTI-TURNO: {n}")
    print(linha("⭐ ANCORADO (cita o dado do retorno)", ancorado))
    print(linha("todos os valores citados", todos))
    print(linha("⚠️ contaminado (numero que nao veio)", contaminado))
    print(linha("respondeu com outra tool call", virou_json))
    print(linha("resposta vazia", vazio))
    print("=" * 74)

    if exemplos:
        print("\nexemplos de contaminacao (numero inventado -> resposta):")
        for nums, r in exemplos:
            print(f"  {nums} -> {r}")

    if args.tag:
        out = Path(__file__).resolve().parent / "results" / f"multiturno_{args.tag}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"modelo": args.model, "n": n, "ancorado": ancorado, "todos_valores": todos,
             "contaminado": contaminado, "virou_json": virou_json, "vazio": vazio},
            indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
