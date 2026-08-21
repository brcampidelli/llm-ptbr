"""Prepara as 4 configs NÃO-agênticas do gigaverbo: filtro, deduplicação e censo de redundância.

Estas quatro atacam buracos que o E2 mediu, e cada uma tem um alvo numérico:

| config | linhas | o que o E2 mediu |
|---|---|---|
| `translation` | 45.204 | 25 pontos de BLEU presos atrás do formato de chat |
| `structured` | 163.542 | atendimento: `json_ok` **0,0%** |
| `code` | 80.774 | código: o modelo **pede esclarecimento** em vez de escrever |
| `summarization` | 128.669 | resumo: **copia a fonte**, compressão 0,90 contra limite 0,35 |

🔴 REDUNDÂNCIA INTERNA, MEDIDA E NÃO SUPOSTA. No `function_call` os 40.716 convertidos
colapsaram em **14.003** pares distintos — 65,6% era duplicata, com um par repetindo 969
vezes. Não há razão para supor que as outras configs sejam diferentes, e a lição §2c-6 diz
que o dano da repetição interna **pica em contagem intermediária (3–10×)**, que é o regime
mais fácil de não notar. Por isso: histograma impresso por config, nunca a taxa média.

⚠️ E o filtro de qualidade não é decoração. Pelo classificador do PRÓPRIO dataset, as duas
configs de pior nota são justamente dois dos nossos zeros: `summarization` (3,84, só 28,0%
com nota ≥4) e `code` (3,94, 42,0%). Filtrar por `instruct_score ≥ 4` corta muito — e cortar
muito é o ponto, porque treinar resumo ruim para consertar resumo é o pior dos mundos.

Uso:
    python comeia/data/preparar_gigaverbo_texto.py --dry-run
    python comeia/data/preparar_gigaverbo_texto.py --escrever
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BRUTO = RAIZ / "comeia" / "data" / "raw" / "gigaverbo"
PROC = RAIZ / "comeia" / "data" / "processed"

CONFIGS = {
    "translation": "25 pp de BLEU presos no formato",
    "structured": "atendimento json_ok 0,0%",
    "code": "codigo: pede esclarecimento",
    "summarization": "resumo: copia a fonte",
}


def par(msgs: list[dict]) -> str:
    """Chave de identidade do exemplo: último pedido do usuário + resposta do assistente."""
    u = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
    a = next((m["content"] for m in reversed(msgs) if m.get("role") == "assistant"), "")
    return u.strip() + "|" + a.strip()


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="*", default=list(CONFIGS))
    ap.add_argument("--score-min", type=float, default=4.0)
    ap.add_argument("--escrever", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    import pyarrow.parquet as pq

    print("=" * 78)
    print(f"PREPARO DAS CONFIGS DE TEXTO — score >= {a.score_min}, deduplicado")
    print("=" * 78)
    resumo = {}
    for cfg in a.configs:
        arquivos = sorted((BRUTO / cfg).glob("*.parquet"))
        if not arquivos:
            print(f"  🔴 {cfg}: nenhum parquet em {BRUTO / cfg}")
            continue
        if a.dry_run:
            n = sum(pq.ParquetFile(f).metadata.num_rows for f in arquivos)
            print(f"  {cfg:16} {n:>8,} linhas   alvo: {CONFIGS.get(cfg, '?')}")
            continue

        linhas = pq.read_table(arquivos[0]).to_pylist()
        bruto = len(linhas)
        # 1) filtro de qualidade
        passou = [r for r in linhas if (r.get("instruct_score") or 0) >= a.score_min]
        # 2) deduplicacao por (pedido, resposta) + histograma
        rep = Counter(par(r["messages"]) for r in passou)
        vistos, unicos = set(), []
        for r in passou:
            k = par(r["messages"])
            if k in vistos:
                continue
            vistos.add(k)
            unicos.append({"messages": r["messages"], "kind": "text", "source": f"gigaverbo_{cfg}",
                           "instruct_score": r.get("instruct_score"),
                           "token_count": r.get("token_count")})
        h = Counter(rep.values())
        red = 100 * (1 - len(unicos) / max(1, len(passou)))
        print(f"\n{cfg}   ({CONFIGS.get(cfg, '')})")
        print(f"  bruto {bruto:,} -> score>={a.score_min:.0f} {len(passou):,} "
              f"({100*len(passou)/bruto:.1f}%) -> dedup {len(unicos):,} "
              f"({red:.1f}% era duplicata)")
        print("  histograma de repeticao (vezes -> quantos pares):")
        for kk in sorted(h)[:5]:
            print(f"    {kk:>3}x : {h[kk]:>7,}")
        if rep:
            print(f"    max  : {max(rep.values())}x")
        toks = sorted(r["token_count"] for r in unicos if r.get("token_count"))
        if toks:
            # ⚠️ p95 importa por causa do truncamento silencioso (licao 2b): exemplo maior que
            #    max_seq_len some INTEIRO, sem erro, e a metrica so' fica "estranha".
            print(f"  tokens: mediana {toks[len(toks)//2]:,} · p95 {toks[int(.95*len(toks))]:,} "
                  f"· max {toks[-1]:,}   (max_seq_len do projeto: 2048)")
            acima = sum(1 for t in toks if t > 2048)
            if acima:
                print(f"    🔴 {acima:,} exemplos ({100*acima/len(toks):.1f}%) passam de 2048 "
                      "tokens e SERIAM DESCARTADOS EM SILENCIO no treino")
        resumo[cfg] = {"bruto": bruto, "pos_score": len(passou), "final": len(unicos),
                       "redundancia_pct": round(red, 1),
                       "acima_2048": sum(1 for t in toks if t > 2048) if toks else 0}
        if a.escrever:
            alvo = PROC / f"gigaverbo_{cfg}.jsonl"
            with alvo.open("w", encoding="utf-8") as f:
                for r in unicos:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  ✅ {alvo.name}")

    if a.dry_run:
        print("\n✅ DRY-RUN.")
        return 0
    if resumo:
        (RAIZ / "docs" / "gigaverbo-texto-preparado.json").write_text(
            json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        tot = sum(v["final"] for v in resumo.values())
        print(f"\n{'=' * 78}")
        print(f"TOTAL utilizavel: {tot:,} exemplos")
        print("⚠️ AINDA FALTA descontaminar contra os holdouts antes de treinar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
