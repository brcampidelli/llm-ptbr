"""Qual token o modelo QUER emitir depois de fechar a chamada?

Nao amostra e nao gera: monta prompt + chamada de REFERENCIA e le a distribuicao do
proximo token numa unica passada. Responde de forma direta o que a amostragem so' insinua —
se o terminador do adapter e' um token so' ou uma BANDA de ids.

Motivo: no E5 o greedy parava em <|im_start|> (id 1, ligado como parada) e a amostragem caia
em \\x1e, \\x00, \\x0f... (ids baixos vizinhos, NAO ligados), gerando 320 tokens de lixo.
Se o terminador for banda, ligar so' um id e' remendo; e adivinhar quais ligar sem medir e'
como o projeto ja' errou antes.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import torch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl                                 # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from peft import PeftModel                                    # noqa: E402

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = "BrCamp/bee-350m-pt-base"
ADAP = RAIZ / "models" / "e2-b-ferramenta-lr0p0012"
DADOS = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"
N = 30

tok = AutoTokenizer.from_pretrained(BASE)
modelo = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16).to("cuda")
modelo = PeftModel.from_pretrained(modelo, str(ADAP)).eval()

linhas = [r for r in read_jsonl(DADOS) if r.get("kind") == "tool_call"][:N]
topo = Counter()
massa_por_id: dict[int, float] = {}
soma_p_baixos = 0.0

for row in linhas:
    msgs = row.get("messages") or (list(row.get("prompt") or []) + list(row.get("completion") or []))
    sistema = next((m["content"] for m in msgs if m["role"] == "system"), None)
    usuario = next((m["content"] for m in msgs if m["role"] == "user"), "")
    ref = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

    m2 = ([{"role": "system", "content": sistema}] if sistema else []) + \
         [{"role": "user", "content": usuario}]
    txt = tok.apply_chat_template(m2, tokenize=False, add_generation_prompt=True) + ref.strip()
    ent = tok(txt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        logits = modelo(**ent).logits[0, -1].float()
    p = torch.softmax(logits, dim=-1)
    v, i = p.topk(10)
    topo[int(i[0])] += 1
    for pv, pi in zip(v.tolist(), i.tolist()):
        massa_por_id[pi] = massa_por_id.get(pi, 0.0) + pv
    soma_p_baixos += float(p[:64].sum())

print("=" * 78)
print(f"DISTRIBUICAO DO TOKEN DE FIM — {len(linhas)} chamadas de referencia")
print("=" * 78)
print(f"\nmassa media nos ids 0-63: {soma_p_baixos / len(linhas):.1%}")
print("\ntoken mais provavel (argmax), por frequencia:")
for tid, n in topo.most_common(10):
    print(f"  id {tid:<6} {n:3}/{len(linhas)}  repr={tok.decode([tid])!r}")

print("\nmassa de probabilidade ACUMULADA por id (top-10 de cada exemplo):")
for tid, m in sorted(massa_por_id.items(), key=lambda kv: -kv[1])[:18]:
    print(f"  id {tid:<6} massa media {m / len(linhas):6.1%}  repr={tok.decode([tid])!r}")

banda = {tid for tid in massa_por_id if tid < 64}
print(f"\nids < 64 que aparecem no top-10: {sorted(banda)}")
print(f"massa media so' desses: "
      f"{sum(massa_por_id[t] for t in banda) / len(linhas):.1%}")
print("\n(ids especiais conhecidos: 0=<|endoftext|> 1=<|im_start|> 2=<|im_end|>)")
