"""Quantifica o mecanismo: das 600 frases do FLORES (en->pt e pt->en) e dos 150 itens de resumo,
quantas saidas do adapter sao RECUSA (regex das negacoes que o proprio corpus v2 usa)."""
import json, re, sys, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
base = "BrCamp/bee-350m-pt-base"; adp = sys.argv[1]
tok = AutoTokenizer.from_pretrained(base); tok.pad_token = tok.pad_token or tok.eos_token; tok.padding_side = "left"
m = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16).cuda(), adp).eval()
RX = re.compile(r"(n[aã]o (consigo|posso|tenho como|é possível|e possivel|dá para|da para|executo|faço|faco|é algo|e algo|realizo|tenho meio)|fora d[oa] (meu|que eu|minha)|sem meios de|impossível|não está ao meu alcance|nao esta ao meu alcance|sinto muito|desculpe|infelizmente|lamento)", re.I)
def gerar(prompts, max_new=64):
    outs = []
    for i in range(0, len(prompts), 16):
        txts = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True) for p in prompts[i:i+16]]
        ids = tok(txts, return_tensors="pt", padding=True).to("cuda")
        with torch.no_grad():
            out = m.generate(**ids, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        for j in range(out.shape[0]):
            g = tok.decode(out[j][ids["input_ids"].shape[1]:], skip_special_tokens=False)
            outs.append(g.split("<|im_start|>")[0].split("<|im_end|>")[0].strip())
    return outs
fl = [json.loads(l) for l in open("comeia/eval/benchmarks/traducao_flores_pt_en.jsonl", encoding="utf-8")]
en = [x for x in fl if x["direcao"] == "en->pt"][:200]; pt = [x for x in fl if x["direcao"] == "pt->en"][:200]
res = {}
for nome, prompts in (("en->pt", [f"Traduza para o português: {x['origem']}" for x in en]),
                      ("pt->en", [f"Translate to English: {x['origem']}" for x in pt])):
    o = gerar(prompts); r = sum(1 for g in o if RX.search(g))
    res[nome] = {"n": len(o), "recusas": r, "exemplos": o[:3]}
    print(f"{nome}: recusas {r}/{len(o)} = {100*r/len(o):.0f}%")
    for g in o[:3]: print("   ›", g[:140].replace("\n", " ⏎ "))
rs = [json.loads(l) for l in open("comeia/eval/benchmarks/resumo_pt.jsonl", encoding="utf-8")]
kt = next(k for k in rs[0] if k in ("fonte", "texto", "documento", "source"))
o = gerar([f"Resuma em duas frases: {x[kt]}" for x in rs], 96); r = sum(1 for g in o if RX.search(g))
res["resumo"] = {"n": len(o), "recusas": r, "exemplos": o[:3]}
print(f"resumo: recusas {r}/{len(o)} = {100*r/len(o):.0f}%")
for g in o[:3]: print("   ›", g[:140].replace("\n", " ⏎ "))
json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
