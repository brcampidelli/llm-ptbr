"""Teste metamórfico do Choice (estudo System One, 2026-09-24): permuta a ORDEM das ferramentas no catálogo.

Gera variantes do holdout balanceado em que só a ordem dos blocos `- nome: ...` do prompt de sistema muda
(`inversa` e `rotacao` de 1). Mesmo conteúdo, mesmos casos, mesmo índice. Lido pelo calibracao_agentica.py,
compara-se o Choice caso a caso: taxa de troca da ferramenta escolhida e distância de variação total entre
as distribuições. A literatura mede 2,6–23% de troca por ordem (JevLite, AnyJev); o nosso §2u já pegou um
modelo que acertava 100% → 0% só por reordenar. Casos com catálogo de 1 ferramenta ficam idênticos.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
FONTE = RAIZ / "processed" / "holdout_balanceado.eval.jsonl"
BLOCO = re.compile(r"(^- [A-Za-z_][A-Za-z0-9_]*:.*?(?=^- [A-Za-z_]|\n\n|\Z))", re.M | re.S)


def permutar(sistema: str, modo: str) -> str:
    blocos = BLOCO.findall(sistema)
    if len(blocos) < 2:
        return sistema
    ini = sistema.index(blocos[0]); fim = sistema.index(blocos[-1]) + len(blocos[-1])
    corpo = [b.rstrip("\n") for b in blocos]
    nova = corpo[::-1] if modo == "inversa" else corpo[1:] + corpo[:1]
    return sistema[:ini] + "\n".join(nova) + ("\n" if blocos[-1].endswith("\n") else "") + sistema[fim:]


def main() -> int:
    linhas = [json.loads(l) for l in FONTE.read_text(encoding="utf-8").splitlines() if l.strip()]
    for modo in ("inversa", "rotacao"):
        out, mudou = [], 0
        for r in linhas:
            r = json.loads(json.dumps(r))
            for campo in ("messages", "prompt"):
                for m in r.get(campo) or []:
                    if m["role"] == "system":
                        novo = permutar(m["content"], modo)
                        mudou += novo != m["content"]
                        norm = lambda s: sorted(b.strip() for b in BLOCO.findall(s))
                        assert norm(novo) == norm(m["content"]), "conteudo do catalogo mudou — so' a ORDEM pode mudar"
                        assert len(novo) == len(m["content"]), "tamanho do prompt mudou"
                        m["content"] = novo
            out.append(r)
        dest = FONTE.with_name(f"holdout_balanceado_{modo}.eval.jsonl")
        dest.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
        print(f"{modo}: {mudou} prompts permutados de {len(out)} -> {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
