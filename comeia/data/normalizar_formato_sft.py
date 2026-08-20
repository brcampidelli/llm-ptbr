"""Normaliza todo o SFT para `prompt`/`completion` — a convenção que faz o TRL mascarar.

🔴 POR QUE ISTO BLOQUEIA O ESTÁGIO 2

O `sft_misto.jsonl` mistura dois formatos: **79,1% dos registros em `messages`** e 20,9% em
`prompt`/`completion`. E a divisão por afinidade herdou a mistura de um jeito ainda pior —
o grupo FERRAMENTA saiu 100% em `prompt/completion`, e os grupos TEXTO e SIMBÓLICO, 100% em
`messages`.

⚠️ **Isso não é detalhe de esquema. É a convenção de loss.** Com `{"messages"}` o TRL calcula
a loss em **todos os tokens**, prompt incluído (`assistant_only_loss=False` por padrão); com
`prompt`/`completion` ele mascara o prompt e cobra só a completion. O projeto já pagou por
isto em 2026-07-24: com system prompt de 928 tokens repetido nos 1.495 exemplos agênticos, a
loss caiu de 1,273 para 0,0755 **decorando o catálogo**, com só 6,2% dos tokens medindo a
habilidade real.

⭐ **E o efeito sobre o E2 é pior que a diluição de sinal.** O braço (b) treina três adapters
por afinidade e compara os três. Com a mistura atual, o adapter de FERRAMENTA aprenderia sob
loss mascarada e os de TEXTO e SIMBÓLICO sob loss em tudo. Qualquer diferença medida entre
eles seria, em parte, **a convenção de loss e não a afinidade** — exatamente a família de erro
do §2d das lições, em que comparar marcos de schedules de LR diferentes mede o schedule e não
o modelo. Um grid confundido assim produz um veredito de arquitetura que não é sobre
arquitetura.

**A conversão:** para um registro em `messages`, o `prompt` recebe tudo até a última fala do
assistente, e a `completion` recebe essa última fala. Multi-turno é preservado (as falas
anteriores ficam no prompt, que é onde devem estar: são contexto, não alvo).

⚠️ Registro sem nenhuma fala de assistente **não é convertido nem descartado em silêncio** —
   é contado e reportado. Exemplo que some calado é o modo de falha mais caro deste projeto.

Uso:
    python comeia/data/normalizar_formato_sft.py                 # relatorio
    python comeia/data/normalizar_formato_sft.py --escrever      # grava *_norm.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
PROC = RAIZ / "comeia" / "data" / "processed"
ALVOS = ["sft_misto.jsonl"]


def _uniforme(d: dict) -> dict:
    """Esquema IDENTICO em todo registro: prompt, completion, kind, source.

    ⚠️ Uniformizar o formato nao bastou. Depois de converter tudo para prompt/completion o
    `datasets` continuou levantando CastError, agora pelos CAMPOS EXTRAS: os registros
    convertidos carregavam `source` e os originais carregavam `kind`, e o leitor le' o arquivo
    em blocos e tenta casar o esquema entre eles. Campo ausente num bloco e presente noutro e'
    esquema diferente. Preencher com "" e' mais barato que remover, e preserva o `kind`, que o
    rotulador usa para separar o agentico NEGATIVO (a resposta certa e' nao chamar ferramenta)
    — o sinal cuja perda reproduziria o over-calling que este projeto ja' pagou para corrigir.
    """
    return {"prompt": d["prompt"], "completion": d["completion"],
            "kind": d.get("kind", ""), "source": d.get("source", "")}


def converter(reg: dict) -> tuple[dict | None, str]:
    """(registro normalizado, motivo). `None` = nao convertido, e o motivo diz por que."""
    if "prompt" in reg and "completion" in reg:
        return _uniforme(reg), "ja_prompt_completion"
    msgs = reg.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return None, "sem_messages"
    ult = next((i for i in range(len(msgs) - 1, -1, -1)
                if msgs[i].get("role") == "assistant"), None)
    if ult is None:
        return None, "sem_fala_de_assistente"
    if ult == 0:
        return None, "assistente_sem_prompt_antes"
    novo = {k: v for k, v in reg.items() if k != "messages"}
    novo["prompt"] = msgs[:ult]
    novo["completion"] = [msgs[ult]]
    novo = _uniforme(novo)
    # falas DEPOIS da ultima do assistente seriam alvo perdido; nao existem nos nossos dados,
    # mas se aparecerem o registro e' marcado em vez de truncado em silencio
    if ult != len(msgs) - 1:
        return None, "tem_fala_depois_do_ultimo_assistente"
    return novo, "convertido"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--alvos", nargs="*", default=ALVOS)
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args()

    print("=" * 76)
    print("NORMALIZACAO DE FORMATO DO SFT — tudo para prompt/completion")
    print("=" * 76)

    houve_perda = False
    for nome in a.alvos:
        p = PROC / nome
        if not p.exists():
            print(f"  ⚠️ {nome} nao existe — pulado")
            continue
        regs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        saida, motivos = [], Counter()
        for r in regs:
            novo, motivo = converter(r)
            motivos[motivo] += 1
            if novo is not None:
                saida.append(novo)

        print(f"\n{nome}: {len(regs)} registros")
        for m, c in motivos.most_common():
            print(f"   {m:38} {c:>6}")
        perdidos = len(regs) - len(saida)
        if perdidos:
            houve_perda = True
            print(f"   🔴 {perdidos} registro(s) NAO convertidos — ver motivos acima.")
            print("      Nenhum foi descartado em silencio; decida o que fazer com eles.")
        else:
            print(f"   ✅ {len(saida)}/{len(regs)} convertidos, nenhuma perda")

        if a.escrever:
            alvo = PROC / nome.replace(".jsonl", "_norm.jsonl")
            with alvo.open("w", encoding="utf-8") as f:
                for r in saida:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            h = hashlib.sha256(alvo.read_bytes()).hexdigest()[:32]
            print(f"   ✅ {alvo.name} · {len(saida)} registros · sha256[:32] = {h}")

    if a.escrever:
        print("\n⚠️ PROXIMO PASSO OBRIGATORIO: refazer os grupos a partir do arquivo")
        print("   normalizado, senao o braco (b) do E2 continua comparando adapters")
        print("   treinados sob convencoes de loss diferentes:")
        print("   python comeia/data/rotular_capacidades.py "
              "--entrada comeia/data/processed/sft_misto_norm.jsonl --escrever")
    return 1 if houve_perda and not a.escrever else 0


if __name__ == "__main__":
    raise SystemExit(main())
