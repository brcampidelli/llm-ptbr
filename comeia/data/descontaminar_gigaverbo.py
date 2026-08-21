"""Descontamina os dados do gigaverbo contra TODOS os holdouts e benchmarks do Bee.

🔴 SEM ISTO, O NÚMERO DO E4 É MENTIRA. Se um exemplo de treino contém a mesma questão que o
avaliador usa, o modelo acerta por ter visto, não por saber — e nada no relatório denuncia,
porque o número sai alto e plausível.

⚠️ **O risco não é uniforme entre as configs, e o maior é o `code`.** HumanEval é o benchmark
mais reciclado do campo: existe traduzido, parafraseado e reempacotado em dezenas de conjuntos
de instrução. O `code` do gigaverbo tem 80 mil exemplos gerados por LLM a partir de "prompts
coletados de fontes públicas" — exatamente o caminho por onde HumanEval entra sem aviso. E o
avaliador de código do Bee usa `coder_tasks.jsonl` mais o `humaneval_xl_pt`.

Método: n-grama de 13 palavras, o padrão da literatura. Se um exemplo de treino compartilha
QUALQUER 13-grama com QUALQUER item de avaliação, ele sai.

⚠️ O removido **não é apagado** — vai para `*_contaminado.jsonl`. Descontaminação que não
deixa auditar é ato de fé: sem ver o que saiu, não dá para distinguir "removeu vazamento" de
"o limiar está errado e removeu metade do corpus".

Uso:
    python comeia/data/descontaminar_gigaverbo.py --dry-run
    python comeia/data/descontaminar_gigaverbo.py --escrever
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
PROC = RAIZ / "comeia" / "data" / "processed"
BENCH = RAIZ / "comeia" / "eval" / "benchmarks"
RAW = RAIZ / "comeia" / "data" / "raw"

ALVOS = ["gigaverbo_translation", "gigaverbo_structured", "gigaverbo_code",
         "gigaverbo_summarization", "gigaverbo_ferramenta", "negativos_com_recusa"]

RX_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokens(t: str) -> list[str]:
    return RX_TOKEN.findall(t.lower())


def ngramas(t: str, n: int) -> set[str]:
    ws = tokens(t)
    return {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def texto_de(reg: dict) -> str:
    """Conteúdo textual do registro — **sem o system prompt**.

    🔴 O SYSTEM PROMPT E' BOILERPLATE E CRIA CONTAMINACAO FALSA. Medido: os arquivos agenticos
    marcaram **100% de contaminacao**, e o unico 13-grama compartilhado era o cabecalho:

        "voce e um assistente agentico voce tem acesso as ferramentas abaixo ferramentas
         disponiveis"

    Ele aparece em todo exemplo dos dois lados, treino e avaliacao. Sem o system: **zero**
    n-gramas em comum — nao havia vazamento nenhum. Descontaminacao contando boilerplate
    apaga o dataset inteiro fazendo exatamente o oposto do que existe para fazer.

    ⚠️ O que interessa e' o PEDIDO e a RESPOSTA. Instrucao compartilhada nao e' vazamento de
    teste; e' convencao do projeto, e ela E' identica de proposito.
    """
    if "messages" in reg:
        return " ".join(m.get("content") or "" for m in reg["messages"]
                        if m.get("role") != "system")
    partes = []
    for k in ("prompt", "completion", "fonte", "texto", "mensagem", "instrucao",
              "resumo_referencia", "solution", "tests", "name"):
        v = reg.get(k)
        if isinstance(v, str):
            partes.append(v)
        elif isinstance(v, list):
            partes.append(" ".join(
                (m.get("content", "") if m.get("role") != "system" else "")
                if isinstance(m, dict) else str(m) for m in v))
    return " ".join(partes)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--ngram", type=int, default=13)
    ap.add_argument("--alvos", nargs="*", default=ALVOS)
    ap.add_argument("--escrever", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # ---- conjuntos de AVALIACAO: tudo que o Bee usa para medir
    fontes_eval = sorted(BENCH.glob("*.jsonl")) + sorted(PROC.glob("*.eval.jsonl"))
    fontes_eval += [RAW / "coder_tasks.jsonl"]
    fontes_eval = [p for p in fontes_eval if p.exists()]

    print("=" * 78)
    print(f"DESCONTAMINACAO — n-grama de {a.ngram} palavras")
    print("=" * 78)
    print(f"conjuntos de avaliacao: {len(fontes_eval)}")
    proibidos: set[str] = set()
    for p in fontes_eval:
        n_reg = 0
        for l in p.read_text(encoding="utf-8", errors="replace").split(chr(10)):
            if not l.strip():
                continue
            try:
                reg = json.loads(l)
            except json.JSONDecodeError:
                continue
            n_reg += 1
            proibidos |= ngramas(texto_de(reg), a.ngram)
        print(f"  {p.name:34} {n_reg:>6,} itens")
    print(f"\n{len(proibidos):,} n-gramas proibidos")
    if a.dry_run:
        print("\n✅ DRY-RUN.")
        return 0

    resumo = {}
    for nome in a.alvos:
        p = PROC / f"{nome}.jsonl"
        if not p.exists():
            print(f"  ⚠️ {nome}: nao existe, pulado")
            continue
        limpos, sujos = [], []
        for l in p.read_text(encoding="utf-8").split(chr(10)):
            if not l.strip():
                continue
            reg = json.loads(l)
            if ngramas(texto_de(reg), a.ngram) & proibidos:
                sujos.append(reg)
            else:
                limpos.append(reg)
        tot = len(limpos) + len(sujos)
        pct = 100 * len(sujos) / max(1, tot)
        marca = "🔴" if pct > 5 else ("⚠️" if pct > 1 else "✅")
        print(f"  {marca} {nome:26} {tot:>7,} -> {len(limpos):>7,}   "
              f"contaminados {len(sujos):>5,} ({pct:.2f}%)")
        resumo[nome] = {"antes": tot, "limpo": len(limpos), "contaminado": len(sujos),
                        "pct": round(pct, 2)}
        # 🔴 GUARDA DE IMPLAUSIBILIDADE. Contaminacao acima de 50% nao e' vazamento: e' o
        #    aparato. Foi assim que 21.223 exemplos foram marcados 100% contaminados por UM
        #    n-grama de boilerplate — e, sem esta guarda, escritos como arquivo vazio.
        if pct > 50:
            print(f"     🔴 ABORTA: {pct:.0f}% e' implausivel para vazamento real. Isso e'")
            print("        assinatura de aparato — provavelmente texto compartilhado por")
            print("        convencao (system prompt, cabecalho, molde). NADA foi escrito.")
            return 2
        if a.escrever:
            with p.open("w", encoding="utf-8") as f:
                for r in limpos:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if sujos:
                # ⚠️ auditavel: descontaminacao sem o que saiu e' ato de fe
                with (PROC / f"{nome}_contaminado.jsonl").open("w", encoding="utf-8") as f:
                    for r in sujos:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")

    (RAIZ / "docs" / "descontaminacao-gigaverbo.json").write_text(
        json.dumps({"ngram": a.ngram, "n_ngramas_proibidos": len(proibidos),
                    "resultado": resumo}, ensure_ascii=False, indent=1), encoding="utf-8")
    if resumo:
        tot = sum(v["limpo"] for v in resumo.values())
        rem = sum(v["contaminado"] for v in resumo.values())
        print(f"\n{'=' * 78}")
        print(f"TOTAL limpo: {tot:,}  ·  removido por contaminacao: {rem:,}")
        print("   O removido esta' em *_contaminado.jsonl — leia antes de confiar no limiar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
