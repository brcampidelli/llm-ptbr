"""Por que resumo, atendimento e código deram ZERO em todos os braços — olhando a saída crua.

🔴 A REGRA QUE ISTO APLICA. Vinte e quatro braços, com LRs diferentes, conjuntos de dados
diferentes e arquiteturas diferentes, marcando **exatamente 0,00** nas mesmas três réguas.
Isso é assinatura de aparato, não de modelo — e já aconteceu duas vezes hoje: a régua
agêntica marcava 0,0% num modelo que emitia a chamada perfeita, e a régua de código abortava
nos três braços de full FT por causa do nome do diretório.

⚠️ Mas "cheira a aparato" não é "é aparato". Resumo tem 135 exemplos no SFT e atendimento 92:
pode ser que o modelo genuinamente não tenha aprendido o formato. As duas explicações dão o
mesmo 0,00, e a única coisa que as separa é **ler o que o modelo escreveu**.

Uso:
    python comeia/eval/diag_zeros.py --peft comeia/models/e2-a-tudo-lr0p0006
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BENCH = AQUI / "benchmarks"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", default=None)
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, str(AQUI))
    from paradas import ids_de_parada, limpar

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    paradas = ids_de_parada(tok, True)
    m = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda()
    if a.peft:
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, a.peft)
    m.eval()
    print(f"modelo : {a.model}")
    print(f"adapter: {a.peft or '(base)'}")

    fontes = [
        ("RESUMO", BENCH / "resumo_pt.jsonl", 420),
        ("ATENDIMENTO", BENCH / "atendimento_pt.jsonl", 260),
        ("CODIGO", RAIZ / "comeia" / "data" / "raw" / "coder_tasks.jsonl", 320),
    ]
    for nome, caminho, teto in fontes:
        print("\n" + "#" * 74)
        print(f"# {nome}  ({caminho.name})")
        if not caminho.exists():
            print("  arquivo ausente")
            continue
        regs = [json.loads(l) for l in caminho.read_text(encoding="utf-8").split(chr(10))
                if l.strip()][:a.n]
        print(f"  chaves do dado: {list(regs[0])[:8]}")
        for r in regs:
            # 🔴 NAO ADIVINHAR O NOME DO CAMPO. A primeira versao procurava
            # prompt/instrucao/pergunta/texto/mensagem; o dado de resumo tem `fonte`, entao o
            # diagnostico mandou prompt VAZIO nos tres exemplos, o modelo respondeu qualquer
            # coisa, e eu quase li isso como "o modelo nao sabe resumir". Cada regua constroi
            # o pedido do seu jeito, e o diagnostico tem de usar o MESMO construtor — senao
            # ele nao diagnostica a regua, diagnostica a si mesmo.
            if "fonte" in r:                      # resumo: ver PEDIDO em eval_resumo_pt.py
                pedido = ("Resuma o texto abaixo em duas frases, mantendo os numeros e os "
                          "nomes exatamente como aparecem." + chr(10) * 2 + r["fonte"])
            else:
                pedido = (r.get("prompt") or r.get("mensagem") or r.get("instrucao") or "")
            if not str(pedido).strip():
                print("  🔴 PEDIDO VAZIO — o diagnostico nao achou o campo; nao interprete "
                      f"a saida. chaves: {list(r)}")
            if isinstance(pedido, list):
                pedido = " ".join(x.get("content", "") for x in pedido)
            sistema = r.get("sistema") or r.get("system")
            msgs = ([{"role": "system", "content": sistema}] if sistema else []) \
                + [{"role": "user", "content": str(pedido)}]
            txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ent = tok(txt, return_tensors="pt", truncation=True, max_length=1400).to("cuda")
            with torch.no_grad():
                g = m.generate(**ent, max_new_tokens=teto, do_sample=False,
                               eos_token_id=paradas, pad_token_id=tok.pad_token_id)
            saida = limpar(tok.decode(g[0][ent["input_ids"].shape[1]:],
                                      skip_special_tokens=False))
            print("-" * 70)
            print(f"  PEDIDO ({len(str(pedido))} chars): {str(pedido)[:150]!r}")
            print(f"  SAIDA  ({len(saida)} chars): {saida[:400]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
