"""Baixa só as 5 configs do `gigaverbo-v2-sft` que atacam buracos medidos do E2.

⭐ POR QUE 5 E NÃO 12. O dataset tem 4,09M linhas e 4,4 GB. Dois configs — `retrieval`
(1,98M) e `general` (1,24M) — são **78% do volume** e não atacam nenhum dos buracos que o E2
mediu. As cinco escolhidas somam ~464K linhas e ~576 MB, e cada uma tem um alvo numérico:

| config | linhas | alvo medido no E2 |
|---|---|---|
| function_call | 45.891 | `argumentos exatos` 37,6% |
| translation | 45.204 | 25 pontos de BLEU presos atrás do formato |
| structured | 163.542 | atendimento: `json_ok` 0,0% |
| code | 80.774 | código: o modelo pede esclarecimento em vez de escrever |
| summarization | 128.669 | resumo: copia a fonte, compressão 0,90 |

⚠️ **O download é cru, de propósito.** Filtro de qualidade, conversão de convenção e
descontaminação são passos SEPARADOS, porque cada um tem um limiar que vai mudar e nenhum
deles justifica baixar 576 MB de novo. O que entra em disco é o que a origem publicou.

Uso:
    python comeia/data/baixar_gigaverbo.py --dry-run
    python comeia/data/baixar_gigaverbo.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DESTINO = RAIZ / "comeia" / "data" / "raw" / "gigaverbo"
REPO = "Polygl0t/gigaverbo-v2-sft"

# config -> (linhas esperadas, alvo do E2)
CONFIGS = {
    "function_call": (45_891, "argumentos exatos 37,6%"),
    "translation": (45_204, "25 pp de BLEU presos no formato"),
    "structured": (163_542, "atendimento json_ok 0,0%"),
    "code": (80_774, "codigo: pede esclarecimento"),
    "summarization": (128_669, "resumo: copia a fonte"),
}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="*", default=list(CONFIGS))
    ap.add_argument("--destino", type=Path, default=DESTINO)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print("=" * 78)
    print(f"DOWNLOAD DIRIGIDO — {REPO}")
    print("=" * 78)
    total = sum(CONFIGS[c][0] for c in a.configs if c in CONFIGS)
    for c in a.configs:
        n, alvo = CONFIGS.get(c, (0, "?"))
        print(f"  {c:16} {n:>8,} linhas   alvo: {alvo}")
    print(f"  {'TOTAL':16} {total:>8,} linhas  (~11% do dataset; retrieval+general ficam fora)")
    if a.dry_run:
        print("\n✅ DRY-RUN: nada baixado.")
        return 0

    from huggingface_hub import snapshot_download

    a.destino.mkdir(parents=True, exist_ok=True)
    caminho = snapshot_download(
        repo_id=REPO, repo_type="dataset", local_dir=str(a.destino),
        allow_patterns=[f"{c}/*" for c in a.configs] + ["README.md"],
    )
    print(f"\nbaixado em {caminho}")

    # ---- conferencia: o que chegou em disco bate com o que a origem declarou?
    # ⚠️ tamanho e' necessario e nao suficiente — o projeto ja' teve corpus do tamanho certo e
    #    conteudo errado. Aqui a checagem e' por CONTAGEM DE LINHAS, que e' o que importa.
    import pyarrow.parquet as pq

    print("\nconferencia (linhas em disco x declaradas pela origem):")
    ok = True
    resumo = {}
    for c in a.configs:
        arquivos = sorted((a.destino / c).glob("*.parquet"))
        if not arquivos:
            print(f"  🔴 {c:16} nenhum parquet")
            ok = False
            continue
        n = sum(pq.ParquetFile(f).metadata.num_rows for f in arquivos)
        esperado = CONFIGS.get(c, (None, ""))[0]
        bate = esperado is None or n == esperado
        ok = ok and bate
        resumo[c] = {"linhas": n, "esperado": esperado, "arquivos": len(arquivos)}
        print(f"  {'✅' if bate else '🔴'} {c:16} {n:>8,} linhas em {len(arquivos)} arquivo(s)"
              + ("" if bate else f"   — esperado {esperado:,}"))

    (RAIZ / "docs" / "gigaverbo-baixado.json").write_text(
        json.dumps({"repo": REPO, "destino": str(a.destino), "configs": resumo},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    if not ok:
        print("\n🔴 A contagem NAO bate com a origem. Nao siga para o filtro sem entender por que.")
        return 1
    print("\n✅ contagem confere com a origem em todas as configs")
    print("   Proximo: filtrar por instruct_score, converter a convencao de chamada,")
    print("   e descontaminar contra os holdouts (04_decontaminate.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
