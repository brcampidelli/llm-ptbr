"""Gate #4a — tres sondas no scorer agentico (rodar da raiz do repo): CORRETA, VAZIA, FABRICADA (arXiv 2609.09218).
Usa o codigo REAL (tools_exec, mundo_aberto) e um caso REAL do holdout. ESPELHA os dois
caminhos secundarios (E5b 'servida' e votacao) como ficaram em eval_agentic_exec.py APOS a correcao de
2026-09-12 — pontuar() e' closure dentro de main() e nao se importa. Antes da correcao a FABRICADA dava
True/True nesses dois caminhos; a linha de base esta' em docs/estudo-arxiv-2026-09-12.md (2609.09218)."""
import json, sys
sys.path.insert(0, "comeia/eval"); sys.path.insert(0, "comeia/data")
import tools_exec as TE
import mundo_aberto as MA
from importlib import import_module
extract_json = import_module("07_distill_agentic").extract_json
from paradas import cortar_no_controle, primeiro_objeto
def parse_harness(bruto):   # copia fiel de eval_agentic_exec.py:490-504
    t = primeiro_objeto(cortar_no_controle(bruto))
    if not t: return None
    try: return json.loads(t)
    except Exception: return None

hold = [json.loads(l) for l in open("comeia/data/processed/holdout_cat15.eval.jsonl", encoding="utf-8")]
aprov = set(json.load(open("comeia/eval/mundo_aberto_aprovadas.json", encoding="utf-8")))
# um caso real cuja referencia executa por formula (discount)
caso = next(h for h in hold if h.get("kind") == "tool_call" and h.get("ferramenta") in aprov and h["ferramenta"] == "calculate_sales_tax")
ref = json.loads(caso["completion"][0]["content"]) if isinstance(caso["completion"], list) else json.loads(caso["completion"])
ok_ref, res_ref = TE.executar(ref)
print("caso:", caso["prompt"][-1]["content"][:110].replace("\n"," "))
print("ref :", json.dumps(ref, ensure_ascii=False), "-> executa:", ok_ref, "resultado:", res_ref)
assert ok_ref, "a referencia tem de executar (guarda do proprio eval)"

def caminho_principal(obj):           # pontuar(): formula so' se o nome esta' nas 14 ou nas aprovadas
    nome = obj.get("tool")
    if ok_ref and (nome in TE.FERRAMENTAS or nome in aprov):
        ok_p, res_p = TE.executar(obj); return bool(ok_p and TE.resultados_batem(res_p, res_ref)), "formula"
    if obj.get("tool") != ref.get("tool"): return False, "ferramenta_errada"
    return False, "sem_criterio"

def caminho_servida(obj):             # E5b APOS a correcao: executa, e quem julga e' pontuar()
    ok_h, res_h = TE.executar(obj)
    return (caminho_principal(obj)[0] if (ok_h and ok_ref) else None)

def caminho_votada(obj):              # votacao APOS a correcao: pontuar() decide
    return caminho_principal({"tool": obj["tool"], "args": obj["args"]})[0]

sondas = {
  "CORRETA":   json.dumps(ref, ensure_ascii=False),
  "VAZIA":     "",
  "FABRICADA": json.dumps({"tool": "sales_tax_helper_inventada", "args": ref["args"]}, ensure_ascii=False),
}
print(f"\n{'sonda':10s} {'parse':>6s}  {'principal (exec_ok)':>22s}  {'E5b servida':>12s}  {'votada':>7s}")
for nome, bruto in sondas.items():
    obj = extract_json(bruto) or parse_harness(bruto)
    if obj is None:
        print(f"{nome:10s} {'None':>6s}  {'nao pontua (under)':>22s}  {'-':>12s}  {'-':>7s}"); continue
    p = caminho_principal(obj); s = caminho_servida(obj); v = caminho_votada(obj)
    print(f"{nome:10s} {'ok':>6s}  {str(p):>22s}  {str(s):>12s}  {str(v):>7s}")
print("\nnome fabricado esta' no catalogo do prompt?", "sales_tax_helper_inventada" in caso["prompt"][0]["content"])
