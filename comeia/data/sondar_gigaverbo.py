"""Reconhecimento do `Polygl0t/gigaverbo-v2-sft` — medir ANTES de baixar 4,4 GB.

⭐ POR QUE ESTA SONDA VEM ANTES DO DOWNLOAD

O plano do E3 diz "baixar o gigaverbo-v2-sft e usar as configs que mapeiam nas capacidades".
Duas prévias de duas linhas já mostraram dois problemas que o mapeamento por NOME não vê:

🔴 **A convenção de chamada de ferramenta é outra.** O dataset usa o estilo Qwen/Hermes —
   `<tools>` em XML no sistema, resposta em `<tool_call>{"name":…,"arguments":{…}}</tool_call>`.
   O Bee emite JSON puro `{"tool":…,"args":{…}}` e o avaliador só aceita esse. Misturar as duas
   ensina duas gramáticas, e o resultado sai como "o dado piorou o modelo".

🔴 **Os exemplos ensinam a PEDIR ESCLARECIMENTO antes de chamar** ("Claro, me forneça a lista
   de números"). É exatamente o modo de falha que o E2 diagnosticou: diante de uma assinatura
   de função completa, o Bee pede o que já está no prompt. Dado que reforça isso piora a
   capacidade que se quer consertar.

⚠️ E um terceiro, de alvo: o exemplo de resumo saiu em **português europeu** ("vivia numa
   cave", "está a ser investigado"). O Bee é PT-BR.

Nenhum dos três é decidível com dois exemplos — por isso esta sonda. Ela amostra pela API do
datasets-server (nada de 4,4 GB) e mede o que decide:
  1. fração PT-PT vs PT-BR, por marcadores lexicais e sintáticos
  2. fração de diálogos que pedem esclarecimento ANTES da primeira chamada
  3. convenção de chamada, contada e não suposta
  4. distribuição de `instruct_score`, para saber se ainda sobra dado ao filtrar por qualidade

Uso:
    python comeia/data/sondar_gigaverbo.py --n 300
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
API = "https://datasets-server.huggingface.co/rows"
DATASET = "Polygl0t/gigaverbo-v2-sft"
CONFIGS = ["function_call", "summarization", "code", "structured", "translation",
           "math", "rewriting", "general"]

# --- PT-PT: marcadores lexicais + a perifrase "estar a + infinitivo"
PT_PT = [r"\butilizador", r"\bregisto\b", r"\bcontacto", r"\becr[aã]\b", r"\btelem[oó]vel",
         r"\bautocarro", r"\bcomboio", r"\bcasa de banho", r"\brapariga", r"\bfacto\b",
         r"\bactual", r"\bac[cç][aã]o\b", r"\b[oó]ptim", r"\bdirector", r"\bpequeno-almo[cç]o",
         r"\best[aá] a \w+r\b", r"\bestou a \w+r\b", r"\bestamos a \w+r\b",
         r"\best[aã]o a \w+r\b"]
# --- PT-BR: os pares equivalentes + o gerundio
PT_BR = [r"\busu[aá]rio", r"\bregistro\b", r"\bcontato", r"\btela\b", r"\bcelular",
         r"\b[oô]nibus", r"\btrem\b", r"\bbanheiro", r"\bmenina\b", r"\bterno\b",
         r"\batual", r"\ba[cç][aã]o\b", r"\b[oó]tim", r"\bdiretor", r"\bcaf[eé] da manh[aã]",
         r"\best[aá] \w+ndo\b", r"\bestou \w+ndo\b", r"\bestamos \w+ndo\b",
         r"\best[aã]o \w+ndo\b"]
PT_PT_RX = [re.compile(p, re.I) for p in PT_PT]
PT_BR_RX = [re.compile(p, re.I) for p in PT_BR]

# perguntas de esclarecimento tipicas ANTES de agir
ESCLARECE = re.compile(
    r"(por favor,?\s+(me\s+)?(forne|inform|envi|diga|especifi)"
    r"|voc[eê] (pode|poderia) (me\s+)?(forne|inform|dizer|especifi)"
    r"|preciso (saber|de mais)"
    r"|me (diga|informe|forne[cç]a))", re.I)

CONV_HERMES = re.compile(r"<tool_call>|<tools>")
CONV_BEE = re.compile(r'\{\s*"tool"\s*:.*"args"\s*:', re.S)


def buscar(config: str, offset: int, length: int) -> list[dict]:
    q = urllib.parse.urlencode({"dataset": DATASET, "config": config,
                                "split": "train", "offset": offset, "length": length})
    with urllib.request.urlopen(f"{API}?{q}", timeout=90) as r:
        return json.loads(r.read())["rows"]


def variedade(texto: str) -> str:
    """PT-PT, PT-BR ou indefinido — por CONTAGEM de marcadores, nunca por um só.

    ⚠️ Um marcador isolado não decide: "fato" é terno em PT-PT e fato em PT-BR; "cave" e
    "quinta" são ambíguos. O veredito exige margem de 2 — senão a sonda produz um número
    preciso sobre nada, que é o modo de falha favorito deste projeto.
    """
    pt = sum(1 for rx in PT_PT_RX if rx.search(texto))
    br = sum(1 for rx in PT_BR_RX if rx.search(texto))
    if pt >= br + 2:
        return "pt_pt"
    if br >= pt + 2:
        return "pt_br"
    return "indefinido"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="linhas amostradas por config")
    ap.add_argument("--configs", nargs="*", default=CONFIGS)
    ap.add_argument("--saida", type=Path, default=RAIZ / "docs" / "sonda-gigaverbo.json")
    a = ap.parse_args()

    print("=" * 78)
    print(f"SONDA DO {DATASET} — {a.n} linhas/config, sem baixar o dataset")
    print("=" * 78)
    relatorio = {}
    for cfg in a.configs:
        linhas: list[dict] = []
        # ⚠️ amostra ESPALHADA, nao so' o comeco: as primeiras N linhas de um dump costumam vir
        #    da mesma fonte e produzem um retrato que nao vale para o conjunto.
        passo, lote, off = 10_000, 100, 0
        while len(linhas) < a.n:
            try:
                novas = buscar(cfg, off, min(lote, a.n - len(linhas)))
            except Exception as e:
                print(f"  ⚠️ {cfg} offset {off}: {type(e).__name__} — parando a amostragem")
                break
            if not novas:
                break
            linhas.extend(novas)
            off += passo
            time.sleep(0.3)
        if not linhas:
            print(f"  🔴 {cfg}: nada amostrado")
            continue

        var, conv = Counter(), Counter()
        escl_antes = n_dialogos_tool = 0
        scores: list[float] = []
        toks: list[int] = []
        turnos: list[int] = []
        for r in linhas:
            row = r["row"]
            msgs = row.get("messages") or []
            texto = " ".join(m.get("content", "") for m in msgs)
            var[variedade(texto)] += 1
            if row.get("instruct_score") is not None:
                scores.append(float(row["instruct_score"]))
            if row.get("token_count"):
                toks.append(int(row["token_count"]))
            turnos.append(len(msgs))
            if CONV_HERMES.search(texto):
                conv["hermes_xml"] += 1
            elif CONV_BEE.search(texto):
                conv["bee_json"] += 1
            idx = next((i for i, m in enumerate(msgs)
                        if m.get("role") == "assistant"
                        and "<tool_call>" in m.get("content", "")), None)
            if idx is not None:
                n_dialogos_tool += 1
                antes = [m for m in msgs[:idx] if m.get("role") == "assistant"]
                if any(ESCLARECE.search(m.get("content", "")) for m in antes):
                    escl_antes += 1

        n = len(linhas)
        med = sorted(scores)[len(scores) // 2] if scores else None
        alto = sum(1 for s in scores if s >= 4.0) / len(scores) if scores else None
        relatorio[cfg] = {
            "n": n,
            "pt_pt": var["pt_pt"] / n, "pt_br": var["pt_br"] / n,
            "indefinido": var["indefinido"] / n,
            "convencao": dict(conv),
            "dialogos_com_chamada": n_dialogos_tool,
            "esclarece_antes_de_chamar": (escl_antes / n_dialogos_tool) if n_dialogos_tool else None,
            "score_mediano": med, "fracao_score_4mais": alto,
            "tokens_medianos": sorted(toks)[len(toks) // 2] if toks else None,
            "turnos_medianos": sorted(turnos)[len(turnos) // 2] if turnos else None,
        }
        d = relatorio[cfg]
        print(f"\n{cfg}  (n={n})")
        print(f"  variedade   PT-BR {100*d['pt_br']:5.1f}%  ·  PT-PT {100*d['pt_pt']:5.1f}%"
              f"  ·  indefinido {100*d['indefinido']:5.1f}%")
        if d["score_mediano"] is not None:
            print(f"  qualidade   score mediano {d['score_mediano']:.2f}  ·  "
                  f"score>=4 em {100*d['fracao_score_4mais']:.1f}%")
        print(f"  formato     {d['turnos_medianos']} turnos · "
              f"{d['tokens_medianos']} tokens (medianas)")
        if conv:
            print(f"  convencao   {dict(conv)}")
        if d["esclarece_antes_de_chamar"] is not None:
            print(f"  🔴 pede esclarecimento antes da 1a chamada: "
                  f"{100*d['esclarece_antes_de_chamar']:.1f}% "
                  f"({escl_antes}/{n_dialogos_tool})")

    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
