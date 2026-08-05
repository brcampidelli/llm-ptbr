"""Etapa 1 do FineWeb-Edu em portugues: anotar valor educacional com professor aberto.

⭐ POR QUE ISTO E' A HIPOTESE VIVA DO PROJETO
  O Gate 2 mostrou que o Bee nao esta na curva de scaling (0,1% observado contra
  23,8% previstos ao triplicar o corpus). Geometria e LR foram refutados; duplicata
  foi medida e eliminada (0,90%). Sobrou qualidade/composicao do corpus. A magnitude
  bate: o FineWeb-Edu descartou 91% do corpus e subiu MMLU 33->37% e ARC 46->57%,
  igualando um baseline com 10x mais tokens. Corpus MENOR e MELHOR.

A RECEITA (Penedo et al., FineWeb-Edu):
  1. anotar ~500k docs com um LLM numa escala 0-5 de valor educacional  <- ESTE SCRIPT
  2. treinar um classificador barato (regressao linear sobre embeddings)
  3. aplicar ao corpus inteiro, manter score >= 3
  O passo 1 e' o caro; o 2 e o 3 sao baratos e rodam em CPU.

⚠️ ADAPTACOES CONSCIENTES AO NOSSO CONTEXTO
  - O original usa Llama-3-70B. Usamos `deepseek/deepseek-v3.2` (professor ABERTO,
    ja em ALLOWED_TEACHERS — `assert_teacher_allowed` barra modelo fechado).
  - O original anota 500k docs. Comecamos com milhares: o objetivo aqui e' medir se
    o classificador SEPARA em portugues, nao produzir o corpus final. Se separar,
    a anotacao escala com dinheiro; se nao separar, economizamos o dinheiro.
  - A rubrica foi reescrita em PT-BR e ancorada em exemplos brasileiros, em vez de
    traduzida — traducao arrasta sintaxe e criterio da lingua de origem.

Uso:
    python bee/anotar_edu.py --n 3000 --paralelo 12
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))
sys.path.insert(0, str(ROOT / "comeia" / "data"))

SAIDA = ROOT / "bee" / "edu" / "anotado.jsonl"

# Rubrica aditiva de 0 a 5 — mesma ESTRUTURA do FineWeb-Edu (cada criterio soma 1
# ponto), reescrita para o portugues e para o que o Bee precisa aprender.
RUBRICA = """Voce avalia o valor EDUCACIONAL de um trecho de texto da web em portugues, para
uso em treino de um modelo de linguagem. Some 1 ponto para cada criterio atendido:

+1 se traz alguma informacao basica relevante para aprendizado escolar, mesmo misturada
   com conteudo nao-educacional (menu de site, propaganda, comentario).
+1 se aborda um tema escolar ou tecnico e esta em portugues compreensivel, ainda que
   nao seja aprofundado ou tenha trechos irrelevantes.
+1 se e' coerente e util para estudo — explica, define ou desenvolve um assunto,
   mesmo que nao pareca material didatico formal.
+1 se e' claramente didatico, com raciocinio ou explicacao encadeada, no nivel de um
   livro escolar ou de um bom artigo de divulgacao, com pouco conteudo irrelevante.
+1 se e' excelente: autocontido, preciso, sem ruido de navegacao ou propaganda, no
   nivel de um capitulo de livro-texto ou de um tutorial bem escrito.

Dao 0: pagina so de links, lista de produtos, texto quebrado, spam, conteudo adulto,
generico sem informacao, ou repeticao.

Responda EXATAMENTE assim, sem mais nada:
JUSTIFICATIVA: <ate 25 palavras>
NOTA: <0, 1, 2, 3, 4 ou 5>"""


def carregar_amostra(n: int, arquivos_idx: list[int]) -> list[str]:
    """Amostra de fineweb-2 por_Latn, com os MESMOS filtros do coletor."""
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    from expand_corpus import listar_parquets, qualidade_ok

    arqs = listar_parquets()
    por_arq = max(1, n // len(arquivos_idx))
    textos: list[str] = []
    for idx in arquivos_idx:
        caminho = hf_hub_download("HuggingFaceFW/fineweb-2", arqs[idx], repo_type="dataset")
        pegos = 0
        for lote in pq.ParquetFile(caminho).iter_batches(batch_size=1000, columns=["text"]):
            for t in lote.column("text").to_pylist():
                if qualidade_ok(t) is None:
                    textos.append(t)
                    pegos += 1
                if pegos >= por_arq:
                    break
            if pegos >= por_arq:
                break
        print(f"  parquet {idx:03d}: +{pegos} docs")
    return textos[:n]


def parse_nota(txt: str) -> tuple[int, str] | None:
    m = re.search(r"NOTA:\s*([0-5])", txt)
    if not m:
        return None
    j = re.search(r"JUSTIFICATIVA:\s*(.+?)(?=\s*NOTA:|$)", txt, re.S)
    return int(m.group(1)), " ".join(j.group(1).split())[:200] if j else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--arquivos", default="0,12,25,40", help="indices de parquet (diversidade)")
    ap.add_argument("--professor", default="deepseek/deepseek-v3.2")
    ap.add_argument("--paralelo", type=int, default=12)
    ap.add_argument("--max-chars", type=int, default=2500, help="trecho enviado ao professor")
    ap.add_argument("--out", type=Path, default=SAIDA)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from config import assert_teacher_allowed
    assert_teacher_allowed(args.professor)

    idxs = [int(x) for x in args.arquivos.split(",")]
    print("=" * 66)
    print("FineWeb-Edu em portugues — etapa 1: anotar valor educacional")
    print("=" * 66)
    print(f"  amostra    : {args.n} docs de {len(idxs)} parquets ({idxs})")
    print(f"  professor  : {args.professor}")
    print(f"  escala     : 0-5 aditiva (rubrica PT-BR, nao traduzida)")

    textos = carregar_amostra(args.n, idxs)
    print(f"  carregados : {len(textos)}")

    if args.dry_run:
        print("\n--- rubrica ---")
        print(RUBRICA[:600])
        print(f"\n--- exemplo de doc ({len(textos[0])} chars) ---")
        print(textos[0][:400])
        return 0

    chave = os.environ.get("OPENROUTER_API_KEY")
    if not chave:
        for linha in (ROOT / ".env").open(encoding="utf-8"):
            if linha.startswith("OPENROUTER_API_KEY="):
                chave = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not chave:
        print("ERRO: OPENROUTER_API_KEY ausente", file=sys.stderr)
        return 1

    from teacher_api import call_teacher

    trava = threading.Lock()
    estado = {"ok": 0, "falha": 0, "sem_nota": 0}
    hist = {i: 0 for i in range(6)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    saida = args.out.open("w", encoding="utf-8")

    def tarefa(texto: str):
        trecho = texto[: args.max_chars]
        try:
            r = call_teacher(f"{RUBRICA}\n\n--- TEXTO ---\n{trecho}",
                             args.professor, chave, temperature=0.0, max_tokens=120)
        except Exception as e:
            with trava:
                estado["falha"] += 1
                if estado["falha"] <= 3:
                    print(f"  falha: {str(e)[:100]}")
            return
        p = parse_nota(r)
        with trava:
            if not p:
                estado["sem_nota"] += 1
                return
            nota, just = p
            saida.write(json.dumps({"texto": texto, "nota": nota,
                                    "justificativa": just}, ensure_ascii=False) + "\n")
            estado["ok"] += 1
            hist[nota] += 1
            if estado["ok"] % 100 == 0:
                print(f"  {estado['ok']}/{len(textos)} · hist {hist} · "
                      f"falha {estado['falha']}", flush=True)

    print(f"\nanotando com {args.paralelo} threads...\n")
    with ThreadPoolExecutor(max_workers=args.paralelo) as ex:
        list(ex.map(tarefa, textos))
    saida.close()

    tot = max(1, estado["ok"])
    print(f"\n[OK] {estado['ok']} anotados em {args.out}")
    print(f"     sem nota parseavel: {estado['sem_nota']} · falhas de API: {estado['falha']}")
    print("\ndistribuicao das notas:")
    for n in range(6):
        barra = "#" * int(60 * hist[n] / tot)
        print(f"  {n}: {hist[n]:>5} ({hist[n]/tot:>5.1%}) {barra}")
    manter = sum(hist[n] for n in (3, 4, 5))
    print(f"\n>>> com corte em >=3 (o do FineWeb-Edu): manteria {manter/tot:.1%} do corpus")
    print(f"   (o FineWeb-Edu original manteve ~9% — descartou 91%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
