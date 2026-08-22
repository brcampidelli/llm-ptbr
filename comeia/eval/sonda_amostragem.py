"""Sonda: por que amostrar (k>1) derruba a execucao de 80% para 0%?

Mesmo exemplo, mesmo prompt, mesma parada — muda so' o modo de decodificacao.
Imprime as saidas CRUAS (skip_special_tokens=False), que e' a unica coisa que separa
"o modelo nao sabe" de "a regua nao escuta".
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import torch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl                              # noqa: E402
from paradas import ids_de_parada                          # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from peft import PeftModel                                 # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = "BrCamp/bee-350m-pt-base"
ADAP = RAIZ / "models" / "e2-b-ferramenta-lr0p0012"
DADOS = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"

tok = AutoTokenizer.from_pretrained(BASE)
modelo = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16).to("cuda")
modelo = PeftModel.from_pretrained(modelo, str(ADAP)).eval()
PARADAS = ids_de_parada(tok, chat=True)
print("ids de parada:", PARADAS, "->", [tok.decode([i]) for i in PARADAS])

linhas = [r for r in read_jsonl(DADOS) if r.get("kind") == "tool_call"][:3]

for idx, row in enumerate(linhas, 1):
    msgs = row.get("messages") or (list(row.get("prompt") or []) + list(row.get("completion") or []))
    sistema = next((m["content"] for m in msgs if m["role"] == "system"), None)
    usuario = next((m["content"] for m in msgs if m["role"] == "user"), "")
    ref = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

    m2 = ([{"role": "system", "content": sistema}] if sistema else []) + \
         [{"role": "user", "content": usuario}]
    txt = tok.apply_chat_template(m2, tokenize=False, add_generation_prompt=True)
    ent = tok(txt, return_tensors="pt").to("cuda")
    n = ent["input_ids"].shape[1]

    print("\n" + "=" * 78)
    print(f"[{idx}] prompt {n} tokens · pedido: {usuario[:110]}")
    print(f"    REF: {ref[:150]}")

    for rot, cfg in [
        ("greedy               ", dict(do_sample=False)),
        ("amostra temp0.8/p0.95", dict(do_sample=True, temperature=0.8, top_p=0.95,
                                       num_return_sequences=3)),
        ("amostra temp0.3      ", dict(do_sample=True, temperature=0.3, top_p=0.95,
                                       num_return_sequences=3)),
    ]:
        torch.manual_seed(20260822)
        with torch.no_grad():
            g = modelo.generate(**ent, max_new_tokens=320, eos_token_id=PARADAS,
                                pad_token_id=tok.pad_token_id or tok.eos_token_id, **cfg)
        for j, s in enumerate(g):
            cru = tok.decode(s[n:], skip_special_tokens=False)
            obj = _d7.extract_json(cru)
            marca = "JSON-OK" if obj else "SEM-JSON"
            print(f"\n  {rot} [{j}] {marca} · {len(s) - n} tokens novos")
            print("      " + repr(cru[:280]))
