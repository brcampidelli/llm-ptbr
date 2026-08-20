"""Separa "o braço foi mal" de "o braço está morto" — antes de gastar 2 h de GPU nos dois.

🔴 POR QUE ISTO EXISTE. Um adapter colapsado gera só `\n\n\n…` e marca 0% em TODAS as sete
réguas. Um adapter que aprendeu mal também marca perto de 0%. Na tabela final os dois viram a
mesma linha de zeros, e a leitura natural — "essa arquitetura não funciona" — é falsa num dos
dois casos. Medido no grid do E2: LoRA a 6e-3 e a 1,2e-2 colapsou nos braços (a) e (b); a 3e-3
o MESMO braço emite a chamada de ferramenta correta. Sem esta sonda, o veredito seria
"adapters não funcionam" quando o certo é "adapters não funcionam ACIMA de 3e-3".

Custa ~3 gerações curtas por artefato (segundos) e evita ~50 min de GPU medindo modelo morto.
⚠️ O que a sonda detecta é **degenerescência**, não qualidade: passar aqui não é aprovação.

Uso:
    python comeia/eval/sonda_colapso.py                     # le' docs/grid-e2-resultado.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BASE_PADRAO = "BrCamp/bee-350m-pt-base"

PEDIDOS = [
    [{"role": "user", "content": "Qual e a capital da Franca?"}],
    [{"role": "user", "content": "Escreva uma frase sobre o mar."}],
    [{"role": "user", "content": "Some 2 mais 2 e responda so o numero."}],
]


def vivo(saidas: list[str]) -> tuple[bool, str]:
    """Vivo = alguma saída tem conteúdo que não seja só espaço/pontuação repetida."""
    uteis = [s for s in saidas if len(set(s.strip())) > 3 and len(s.strip()) > 3]
    if not uteis:
        return False, "so espaco/repeticao — COLAPSADO"
    return True, f"{len(uteis)}/{len(saidas)} com conteudo"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=Path, default=RAIZ / "docs" / "grid-e2-resultado.json")
    ap.add_argument("--base", default=BASE_PADRAO)
    ap.add_argument("--saida", type=Path, default=RAIZ / "docs" / "grid-e2-colapso.json")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, str(AQUI))
    from paradas import ids_de_parada, limpar

    runs = json.loads(a.grid.read_text(encoding="utf-8"))["runs"]
    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    paradas = ids_de_parada(tok, True)
    entradas = [tok(tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True),
                    return_tensors="pt").to("cuda") for m in PEDIDOS]

    print("=" * 74)
    print("SONDA DE COLAPSO — 3 geracoes curtas por artefato")
    print("=" * 74)
    veredito = {}
    for tag in sorted(runs):
        if "erro" in runs[tag]:
            continue
        d = Path(runs[tag]["adapter"])
        lora = (d / "adapter_config.json").exists()
        m = AutoModelForCausalLM.from_pretrained(a.base if lora else str(d),
                                                 dtype=torch.bfloat16).cuda()
        if lora:
            from peft import PeftModel
            m = PeftModel.from_pretrained(m, str(d))
        m.eval()
        saidas = []
        for ent in entradas:
            with torch.no_grad():
                g = m.generate(**ent, max_new_tokens=40, do_sample=False,
                               eos_token_id=paradas, pad_token_id=tok.pad_token_id)
            saidas.append(limpar(tok.decode(g[0][ent["input_ids"].shape[1]:],
                                            skip_special_tokens=False)))
        ok, motivo = vivo(saidas)
        veredito[tag] = {"vivo": ok, "motivo": motivo, "amostra": saidas[0][:90]}
        print(f"  {'✅' if ok else '🔴'} {tag:26} {motivo:28} {saidas[0][:44]!r}")
        del m
        torch.cuda.empty_cache()

    a.saida.write_text(json.dumps(veredito, ensure_ascii=False, indent=1), encoding="utf-8")
    mortos = [t for t, v in veredito.items() if not v["vivo"]]
    print(f"\n{len(veredito) - len(mortos)}/{len(veredito)} vivos · "
          f"{len(mortos)} colapsados: {mortos or 'nenhum'}")
    print(f"✅ {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
