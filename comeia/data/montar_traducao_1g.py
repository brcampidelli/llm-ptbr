"""Corpus do adapter de TRADUÇÃO do Bee-1G (2026-09-24) — adapter separado, receita do E22 do 350M.

Por que: o SFT agêntico derruba a tradução do 1G de 50,85 (base, en→pt chrF2) para 24,2 — perto do piso de
copiar a fonte (21,5); pt→en cai abaixo do piso. No 350M, a capacidade em adapter PRÓPRIO rendeu 2,3× a dose
dentro do agêntico e custou zero no eixo agêntico (E22). O adapter de tradução é servido por roteador.

Fonte: `gigaverbo_translation.jsonl` (41.647 pares, 100% en→pt, 8 prompts de sistema). Nenhuma das 1.200
frases do FLORES devtest (a régua) aparece nele (conferido por substring de 60 caracteres, 0/1200).

Construção, com o mesmo orçamento de passos do C-full (698 × 16 = 11.168 exemplos):
  - metade en→pt (pares originais), metade pt→en (pares DISTINTOS, com origem e destino trocados);
  - em cada direção, metade no estilo do corpus (prompt de sistema variado + texto cru) e metade no estilo
    da RÉGUA (`eval_traducao_pt.py`: só usuário, "Traduza a frase do ... Inglês: X / Português:") — para não
    medir distância de formato (§2e). ⚠️ Declarado: o formato da régua entra no treino; o CONTEÚDO dela não.
Formato prompt/completion (loss mascarada no prompt, como o C-full).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
FONTE = RAIZ / "processed" / "gigaverbo_translation.jsonl"
SAIDA = RAIZ / "processed" / "treino_1g_traducao.jsonl"
N = 698 * 16

REGUA = {"en->pt": "Traduza a frase do inglês para o português.\n\nInglês: {x}\nPortuguês:",
         "pt->en": "Traduza a frase do português para o inglês.\n\nPortuguês: {x}\nInglês:"}
SIS_PT_EN = [
    "Você é um tradutor profissional de português para inglês. Traduza com precisão e mantenha o sentido.",
    "Atue como um tradutor especializado. Converta qualquer texto do português para o inglês mantendo o tom.",
    "Você é um assistente de tradução. Dado um texto em português, retorne sua melhor tradução para o inglês.",
    "Realize traduções do português para o inglês, garantindo que a estrutura e o significado se preservem.",
]


def main() -> int:
    rnd = random.Random(20260924)
    L = [json.loads(l) for l in FONTE.read_text(encoding="utf-8").splitlines() if l.strip()]
    rnd.shuffle(L)
    metade = N // 2
    ida, volta = L[:metade], L[metade:2 * metade]      # pares distintos em cada direção
    out = []
    for k, r in enumerate(ida):
        sis, en, pt = (m["content"] for m in r["messages"])
        if k % 2 == 0:
            prompt = [{"role": "system", "content": sis}, {"role": "user", "content": en}]
        else:
            prompt = [{"role": "user", "content": REGUA["en->pt"].format(x=en)}]
        out.append({"prompt": prompt, "completion": [{"role": "assistant", "content": pt}], "direcao": "en->pt"})
    for k, r in enumerate(volta):
        _, en, pt = (m["content"] for m in r["messages"])
        if k % 2 == 0:
            prompt = [{"role": "system", "content": rnd.choice(SIS_PT_EN)}, {"role": "user", "content": pt}]
        else:
            prompt = [{"role": "user", "content": REGUA["pt->en"].format(x=pt)}]
        out.append({"prompt": prompt, "completion": [{"role": "assistant", "content": en}], "direcao": "pt->en"})
    rnd.shuffle(out)
    SAIDA.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    print(f"{len(out)} exemplos -> {SAIDA.name}  (en->pt {sum(o['direcao']=='en->pt' for o in out)}, "
          f"pt->en {sum(o['direcao']=='pt->en' for o in out)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
