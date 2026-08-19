"""Censo de mistura POR TOKEN — Estagio 1 do plano de pos-treino do Bee-350M.

🔴 POR QUE ISTO EXISTE, E POR QUE CONTAR EXEMPLOS ENGANA

O projeto vinha descrevendo a mistura de SFT em numero de EXEMPLOS ("7.152 exemplos, dos
quais 1.495 agenticos = 20,9%"). Isso e' a metrica errada por duas razoes independentes,
e as duas empurram para o mesmo tipo de erro — achar que uma capacidade esta representada
quando ela e' marginal, ou o contrario.

1. **Exemplos tem tamanhos MUITO diferentes.** Um exemplo agentico carrega um catalogo de
   ferramentas de ~1.100 tokens no prompt; um exemplo de sentimento tem uma frase e um
   rotulo. Chamar os dois de "1 exemplo" e somar e' como medir carga somando caixas sem
   olhar o peso.

2. ⭐ **A loss e' MASCARADA no prompt.** O `bee/sft.py` converte `messages` em
   `{prompt, completion}`, e o TRL entao cobra o modelo APENAS pelo que ele responde. Ou
   seja: os tokens de prompt nao produzem gradiente nenhum. A fracao de treino que cada
   capacidade de fato recebe e' a fracao de tokens de **COMPLETION** — nao de exemplos, e
   nem mesmo de tokens totais.

   Isso inverte a intuicao no caso agentico: e' a capacidade com MAIS tokens totais (por
   causa do catalogo) e pode ser das com MENOS tokens de completion (a resposta e' uma
   chamada de ferramenta curta). Contar tokens totais erraria para o lado oposto de contar
   exemplos, o que e' pior que so' errar.

⚠️ Mesma familia de "o dado some e nada reclama" (docs/licoes-de-metodo.md §2b): ali um
   `max_seq_len` curto descartou 100% do agentico sem erro; aqui a mistura pode estar
   desbalanceada em 10x sem que nenhum numero no log denuncie.

Uso:
    python comeia/data/censo_tokens.py
    python comeia/data/censo_tokens.py --tokenizer models/bee-150m-v3-base --out docs/censo-tokens.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CTX = 2048   # contexto do Bee-350M (e do 150M)
PROC = ROOT / "comeia" / "data" / "processed"

# Os arquivos que o plano de pos-treino considera candidatos a mistura, e a capacidade que
# cada um representa. Arquivos intermediarios (clean, decontaminated) ficam de fora: eles
# sao insumo do pipeline, nao dado de treino.
CANDIDATOS = [
    ("sft_ptbr.jsonl",             "instrucao PT (geral)"),
    ("sft_agentic.jsonl",          "agentico (tool-use)"),
    ("sft_agentic_reforco.jsonl",  "agentico (reforco/rejection)"),
    ("sft_multiturno.jsonl",       "multi-turno"),
    ("sft_bncc.jsonl",             "educacional BNCC"),
    ("sft_misto.jsonl",            "MISTO (ptbr+agentico)"),
    ("sft_reforcado_prop.jsonl",   "MISTO reforcado"),
    ("sft_combinado.jsonl",        "MISTO combinado"),
]


def partes(reg: dict) -> tuple[str, str]:
    """Devolve (texto_do_prompt, texto_da_completion) para os dois formatos do projeto.

    ⚠️ Se um registro nao casar com nenhum formato conhecido, ele NAO e' silenciosamente
    ignorado — o chamador conta isso e o relatorio denuncia. Registro que some calado e'
    exatamente o modo de falha que este script existe para evitar.
    """
    if "prompt" in reg and "completion" in reg:
        p, c = reg["prompt"], reg["completion"]
        tp = "".join(m.get("content", "") for m in p) if isinstance(p, list) else str(p)
        tc = "".join(m.get("content", "") for m in c) if isinstance(c, list) else str(c)
        return tp, tc
    if "messages" in reg:
        msgs = reg["messages"]
        # tudo ate a ULTIMA fala do assistant e' prompt; a ultima fala do assistant e' o alvo
        ult = max((i for i, m in enumerate(msgs) if m.get("role") == "assistant"), default=-1)
        if ult < 0:
            return "".join(m.get("content", "") for m in msgs), ""
        tp = "".join(m.get("content", "") for m in msgs[:ult])
        tc = msgs[ult].get("content", "")
        return tp, tc
    return "", ""


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", default=str(ROOT / "models" / "bee-150m-v3-base"),
                    help="o tokenizador do Bee (32k, PT). O do 350M e' o MESMO.")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "censo-tokens.json")
    a = ap.parse_args()

    # `tokenizers` em vez de `transformers`: contar token nao precisa de torch, e puxar
    # ~2,5 GB de dependencia para ler um tokenizer.json de 2 MB seria desproporcional.
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(str(Path(a.tokenizer) / "tokenizer.json"))
    def tok(s):
        return {"input_ids": tk.encode(s).ids}
    print(f"tokenizador: {a.tokenizer} · vocab {tk.get_vocab_size()}\n")

    linhas, total_desconhecido = [], 0
    for nome, capacidade in CANDIDATOS:
        p = PROC / nome
        if not p.exists():
            print(f"  (ausente) {nome}")
            continue
        n, tp_tot, tc_tot, desconhecido, maior = 0, 0, 0, 0, 0
        # 🔴 O que o truncamento de fato custa. Nao basta saber o MAIOR exemplo: o numero
        #    acionavel e' quantos exemplos estouram 2048 e — pior — em quantos o PROMPT
        #    sozinho ja estoura, porque nesses a completion inteira e' cortada fora e o
        #    exemplo vira 100% mascarado. O TRL descarta esses SEM ERRO (licoes §2b: foi
        #    assim que 150 de 150 exemplos agenticos sumiram em silencio no Bee-150M).
        estoura, prompt_ja_estoura, compl_perdida = 0, 0, 0
        for linha in p.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha:
                continue
            try:
                reg = json.loads(linha)
            except json.JSONDecodeError:
                desconhecido += 1
                continue
            tp, tc = partes(reg)
            if not tp and not tc:
                desconhecido += 1
                continue
            np_, nc = len(tok(tp)["input_ids"]), len(tok(tc)["input_ids"])
            n += 1
            tp_tot += np_
            tc_tot += nc
            maior = max(maior, np_ + nc)
            if np_ + nc > CTX:
                estoura += 1
                if np_ >= CTX:              # prompt sozinho ja estoura -> exemplo INTEIRO perdido
                    prompt_ja_estoura += 1
                    compl_perdida += nc
                else:                        # sobra so' parte da completion
                    compl_perdida += (np_ + nc) - CTX
        total_desconhecido += desconhecido
        linhas.append({
            "arquivo": nome, "capacidade": capacidade, "exemplos": n,
            "tok_prompt": tp_tot, "tok_completion": tc_tot, "tok_total": tp_tot + tc_tot,
            "media_prompt": round(tp_tot / max(1, n), 1),
            "media_completion": round(tc_tot / max(1, n), 1),
            "maior_exemplo": maior, "registros_ilegiveis": desconhecido,
            "estoura_ctx": estoura, "prompt_ja_estoura": prompt_ja_estoura,
            "tok_completion_perdidos": compl_perdida,
        })
        print(f"  {nome:32} {n:>6} ex · {tp_tot+tc_tot:>9,} tok"
              + (f"  ⚠️ {desconhecido} ilegiveis" if desconhecido else ""))

    # ---------------------------------------------------------------- relatorio
    print("\n" + "=" * 100)
    print("CENSO POR TOKEN — o que o modelo de fato APRENDE e' a coluna de completion")
    print("=" * 100)
    print(f"{'capacidade':34} {'exemplos':>8} {'tok total':>12} {'tok compl.':>12} "
          f"{'% compl.':>9} {'md pr':>7} {'md co':>7} {'maior':>7}")
    print("-" * 100)

    puros = [l for l in linhas if not l["capacidade"].startswith("MISTO")]
    base_compl = sum(l["tok_completion"] for l in puros) or 1
    for l in sorted(puros, key=lambda x: -x["tok_completion"]):
        print(f"{l['capacidade']:34} {l['exemplos']:>8,} {l['tok_total']:>12,} "
              f"{l['tok_completion']:>12,} {100*l['tok_completion']/base_compl:>8.1f}% "
              f"{l['media_prompt']:>7.0f} {l['media_completion']:>7.0f} {l['maior_exemplo']:>7,}")

    print("-" * 100)
    print("(os arquivos MISTO sao combinacoes dos acima — listados a parte para nao contar duas vezes)")
    for l in [x for x in linhas if x["capacidade"].startswith("MISTO")]:
        print(f"  {l['arquivo']:32} {l['exemplos']:>6,} ex · {l['tok_total']:>9,} tok · "
              f"compl {l['tok_completion']:>9,}")

    # ⚠️ o numero que decide o truncamento: quantos exemplos NAO cabem em 2048?
    print("\n" + "=" * 100)
    print(f"⚠️ TRUNCAMENTO — o Bee-350M tem contexto de {CTX}")
    print("=" * 100)
    print(f"{'arquivo':32} {'estoura':>9} {'% dos ex':>9} {'PROMPT ja':>11} {'compl. perdida':>15}")
    print("-" * 100)
    for l in linhas:
        if l["estoura_ctx"]:
            marca = "🔴" if l["prompt_ja_estoura"] else "  "
            print(f"{marca}{l['arquivo']:30} {l['estoura_ctx']:>9,} "
                  f"{100*l['estoura_ctx']/max(1,l['exemplos']):>8.1f}% "
                  f"{l['prompt_ja_estoura']:>11,} {l['tok_completion_perdidos']:>15,}")
    print("\n  'PROMPT ja' = exemplos em que o prompt SOZINHO estoura o contexto. Nesses a")
    print("  completion inteira e' cortada, o exemplo fica 100% mascarado e o TRL o DESCARTA")
    print("  sem erro nenhum. Se essa coluna nao for zero, o treino perde dado em silencio.")
    if total_desconhecido:
        print(f"\n🔴 {total_desconhecido} registros ilegiveis no total — investigar antes de treinar")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"tokenizer": a.tokenizer, "arquivos": linhas},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrelatorio: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
