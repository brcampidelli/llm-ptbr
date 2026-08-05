"""Qual professor anotar 500k docs? O que decide nao e' o preco por token.

⚠️ LICAO MEDIDA HOJE: `deepseek-v4-flash-0731` custa $0,18/M (metade do v3.2) e
saiu 6x MAIS CARO na pratica — gasta 384 tokens de raciocinio para dar uma nota
que cabe em 27. Modelo de reasoning cobra o raciocinio. Para tarefa estruturada
e curta, isso domina o custo.

Aqui mede-se o que importa: (a) obedece o formato, (b) CONCORDA com o professor
de referencia, (c) quantos tokens gasta. Sem concordancia, barato nao serve.
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "bee"); sys.path.insert(0, "comeia/data")
from anotar_edu import RUBRICA, parse_nota
from config import ALLOWED_TEACHERS

CHAVE = [l.split("=",1)[1].strip().strip('"') for l in open(".env",encoding="utf-8")
         if l.startswith("OPENROUTER_API_KEY=")][0]

def chamar(modelo, prompt, maxtok=700):
    body = json.dumps({"model": modelo, "messages": [{"role":"user","content":prompt}],
                       "temperature": 0, "max_tokens": maxtok}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {CHAVE}", "Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=200) as r:
        p = json.loads(r.read())
    if "choices" not in p:
        raise RuntimeError(str(p.get("error", p))[:120])
    return (p["choices"][0]["message"].get("content") or "",
            p.get("usage", {}).get("completion_tokens", 0))

ref = [json.loads(l) for l in open("bee/edu/anotado.jsonl", encoding="utf-8")][:40]
print(f"referencia: {len(ref)} docs ja anotados por deepseek-v3.2\n")

CANDIDATOS = ["nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3-super-120b-a12b:free",
              "google/gemma-4-31b-it:free", "inclusionai/ling-3.0-flash:free",
              "mistralai/mistral-nemo", "qwen/qwen3.5-flash-02-23"]
print(f"{'modelo':<42}{'formato':>9}{'concord':>9}{'|dif|':>7}{'tok':>6}{'s/doc':>7}  licenca")
print("-"*90)
for m in CANDIDATOS:
    permitido = "OK" if m in ALLOWED_TEACHERS else "NAO-LISTADO"
    def uma(r):
        try:
            txt, tok = chamar(m, f"{RUBRICA}\n\n--- TEXTO ---\n{r['texto'][:2500]}")
            p = parse_nota(txt)
            return (p[0] if p else None, tok)
        except Exception:
            return (None, 0)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(uma, ref))
    dt = (time.time()-t0)/len(ref)
    val = [(a, r["nota"]) for (a, _), r in zip(res, ref) if a is not None]
    toks = [t for _, t in res if t]
    if not val:
        print(f"{m:<42}{'0%':>9}{'—':>9}{'—':>7}{'—':>6}{dt:>6.1f}s  {permitido}")
        continue
    fmt = len(val)/len(ref)
    igual = sum(1 for a, b in val if a == b)/len(val)
    dif = sum(abs(a-b) for a, b in val)/len(val)
    print(f"{m:<42}{fmt:>8.0%}{igual:>9.0%}{dif:>7.2f}{sum(toks)//max(1,len(toks)):>6}"
          f"{dt:>6.1f}s  {permitido}")
