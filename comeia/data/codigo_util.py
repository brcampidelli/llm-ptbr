"""Corpus de CÓDIGO para o Bee-350M — a terceira e última capacidade que nunca teve treino.

🔴 POR QUE ISTO EXISTE. `codigo pass@1` esta' em **0,0% em todos os artefatos** — base, 150M,
e13, C-full, E20, E21, E22, E23 — nos dois benchmarks. E o motivo e' o mesmo do atendimento:

    sem codigo extraivel:  685/877 (base) · 839 (C-full) · 876 (E21)

O modelo **nao emite bloco ```python**. O gargalo e' o formato, nao o algoritmo.

⭐⭐ E AQUI A GUARDA E' MAIS FORTE QUE NAS OUTRAS DUAS CAPACIDADES: codigo se EXECUTA. No resumo
a guarda era compressao medida; no atendimento, o valor aparecer na mensagem. Aqui a guarda e'
**a solucao passar nos proprios testes** — o interpretador julga, e nao ha' criterio a arbitrar.

## Reaproveita o executor da regua, nao um novo

`run_tests` de `comeia/eval/eval_coder.py` ja' roda em subprocesso isolado (`-I`), com timeout,
diretorio temporario e varredura de padrao proibido. Escrever outro executor seria criar um
segundo comportamento para a mesma coisa — e a diferenca entre os dois viraria um defeito de
aparato esperando acontecer.

⚠️ **Isto executa codigo gerado por um modelo.** O risco e' o mesmo que a regua ja' aceita para
avaliar o Bee, com a mesma protecao: `scan_forbidden` barra `open`, `os`, `sys`, `input` e rede
antes de rodar, e o subprocesso vai isolado com teto de tempo.

## O que se compartilha com o holdout, e o que NAO

**Disjunto:** os 877 problemas internos e os 80 do HumanEval-XL nao entram. Os problemas aqui sao
escritos pelo professor (§2o).

**Compartilhado de proposito:** o FORMATO — assinatura com docstring em portugues, resposta em
bloco ```python. E' o que a regua mede e treinar noutro formato mediria o formato (§2g).

Uso:
    python comeia/data/codigo_util.py --dry-run
    python comeia/data/codigo_util.py --validar     # prova que a guarda morde
    python comeia/data/codigo_util.py --n 900 --paralelo 6
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
sys.path.insert(0, str(RAIZ / "eval"))
from eval_coder import SYSTEM, extract_code, run_tests  # noqa: E402

NL = chr(10)
MODELO = "deepseek/deepseek-chat"
URL = "https://openrouter.ai/api/v1/chat/completions"
CORPUS_BASE = PROC / "treino_e19c_neg_uteis.jsonl"

# ⭐ os temas existem para o corpus nao virar 900 variacoes de "somar uma lista" — §2w, contar
#    itens DISTINTOS. Sao dominios, nao enunciados: o professor escreve o problema.
TEMAS = [
    "manipulacao de listas", "strings e texto", "dicionarios", "matematica basica",
    "datas e tempo", "validacao de entrada", "contagem e frequencia", "ordenacao",
    "busca em sequencia", "conversao de unidades", "formatacao de numeros",
    "conjuntos e duplicatas", "tuplas e desempacotamento", "recursao simples",
    "acumuladores e reducoes", "fatiamento", "numeros primos e divisores",
    "matrizes como lista de listas", "parsing de texto simples", "estatistica descritiva",
]

INSTRUCAO = """Você cria exercícios de programação Python em português do Brasil.

Devolva EXATAMENTE três blocos, nesta ordem e sem mais nada:

```prompt
<a assinatura da função com type hints e uma docstring em português explicando o que ela faz,
incluindo 1 ou 2 exemplos no formato >>> ; NÃO inclua o corpo da função>
```

```python
<a função COMPLETA e correta, repetindo a assinatura e a docstring>
```

```tests
<de 3 a 5 linhas `assert nome_da_funcao(...) == ...`, cobrindo caso normal e caso de borda>
```

REGRAS:
1. A função tem de ser PURA: sem input(), open(), os, sys, rede ou aleatoriedade.
2. O nome da função em inglês ou português, minúsculo com underscore. A docstring em PORTUGUÊS.
3. Nada de bibliotecas externas. `typing`, `math` e `collections` são permitidos.
4. O problema deve ser resolvível em 3 a 12 linhas.
5. Os asserts têm de passar na função que você escreveu. Confira antes de responder."""

RX_BLOCO = re.compile(r"```(prompt|python|tests)\s*\n(.*?)```", re.S)


def chave() -> str:
    for ln in (RAIZ.parent / ".env").read_text(encoding="utf-8").splitlines():
        if ln.startswith("OPENROUTER_API_KEY"):
            return ln.split("=", 1)[1].strip()
    raise SystemExit("OPENROUTER_API_KEY ausente no .env")


def pedir(k: str, msgs: list[dict], tent: int = 3) -> tuple[str, dict]:
    corpo = json.dumps({"model": MODELO, "messages": msgs,
                        "temperature": 0.9, "max_tokens": 900}).encode()
    req = urllib.request.Request(URL, data=corpo, headers={
        "Authorization": "Bearer " + k, "Content-Type": "application/json"})
    for i in range(tent):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=120))
            return d["choices"][0]["message"]["content"].strip(), d.get("usage", {})
        except Exception as e:                                    # noqa: BLE001
            if i == tent - 1:
                return "", {"erro": f"{type(e).__name__}: {e}"}
            time.sleep(2 * (i + 1))
    return "", {}


def julgar(bruto: str) -> tuple[dict | None, str]:
    """Extrai os tres blocos e EXECUTA a solucao contra os asserts. O interpretador decide."""
    blocos = {k: v.strip() for k, v in RX_BLOCO.findall(bruto)}
    faltam = {"prompt", "python", "tests"} - set(blocos)
    if faltam:
        return None, f"faltou bloco {sorted(faltam)}"
    sol, testes = blocos["python"], blocos["tests"]
    if "def " not in blocos["prompt"] or "def " not in sol:
        return None, "sem assinatura de funcao"
    linhas = [l for l in testes.splitlines() if l.strip().startswith("assert")]
    if len(linhas) < 3:
        return None, f"menos de 3 asserts ({len(linhas)})"
    # 🔴 A GUARDA: o interpretador. `run_tests` ja' barra padrao proibido e roda isolado.
    res = run_tests(sol, linhas, timeout=8)
    if not res.ok:
        return None, f"nao passa nos proprios testes: {res.reason[:60]}"
    return {"prompt": blocos["prompt"], "solution": sol, "tests": linhas}, ""


def catalogos() -> list[str]:
    """§2u: catalogo de ferramentas no `system`, como em todo exemplo do corpus."""
    out = []
    for l in CORPUS_BASE.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        s = next((m["content"] for m in json.loads(l)["prompt"] if m["role"] == "system"), None)
        if s:
            out.append(s)
    return out


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=900)
    ap.add_argument("--seed", type=int, default=20260831)
    ap.add_argument("--paralelo", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validar", action="store_true")
    a = ap.parse_args()

    if a.validar:
        # 🔴 A guarda tem de REPROVAR solucao errada e ACEITAR solucao certa. Testada contra os
        #    dois estados, porque guarda que so' aceita nao guarda nada (§2t).
        certa = ("```prompt\ndef dobro(x: int) -> int:\n    \"\"\"Devolve o dobro.\"\"\"\n```\n"
                 "```python\ndef dobro(x: int) -> int:\n    \"\"\"Devolve o dobro.\"\"\"\n"
                 "    return x * 2\n```\n"
                 "```tests\nassert dobro(2) == 4\nassert dobro(0) == 0\nassert dobro(-3) == -6\n```")
        errada = certa.replace("return x * 2", "return x + 2")
        poucos = certa.replace("assert dobro(-3) == -6\n", "")
        proibida = certa.replace("return x * 2", "import os\n    return x * 2")
        for nome, bruto in (("solucao CERTA", certa), ("solucao ERRADA", errada),
                            ("so' 2 asserts", poucos), ("padrao proibido", proibida)):
            ok, motivo = julgar(bruto)
            print(f"  {nome:20} -> {'ACEITO' if ok else 'reprovado: ' + motivo}")
        print(f"{NL}⚠️ 'solucao CERTA' tem de ser ACEITO e os outros tres reprovados. Se a errada"
              f" passar, o interpretador nao esta' julgando nada.")
        return 0

    rnd = random.Random(a.seed)
    alvos = [(i, TEMAS[i % len(TEMAS)]) for i in range(a.n)]
    est = a.n * (len(INSTRUCAO) + 60) / 3.5
    print(f"{a.n} problemas · {len(TEMAS)} temas")
    print(f"  custo estimado: ~US$ {est / 1e6 * 0.27 + a.n * 420 / 1e6 * 1.10:.3f}")
    if a.dry_run:
        print(f"{NL}✅ dry-run: nada gerado nem gasto.")
        return 0

    k = chave()
    cats = catalogos()
    st: Counter = Counter()
    saida, c_in, c_out = [], 0, 0
    t0 = time.time()

    def uma(alvo):
        i, tema = alvo
        p = (f"Crie um exercicio de Python sobre **{tema}**. "
             f"Varie o estilo em relacao a exercicios comuns desse tema.")
        txt, uso = pedir(k, [{"role": "system", "content": INSTRUCAO},
                             {"role": "user", "content": p}])
        return tema, txt, uso

    from concurrent.futures import ThreadPoolExecutor
    feitos = 0
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for tema, txt, uso in ex.map(uma, alvos):
            feitos += 1
            c_in += uso.get("prompt_tokens", 0)
            c_out += uso.get("completion_tokens", 0)
            if not txt:
                st[f"🔴 erro da API: {str(uso.get('erro', '?'))[:34]}"] += 1
                continue
            item, motivo = julgar(txt)
            if item is None:
                st[f"🔴 REPROVADO — {motivo.split(':')[0].strip()}"] += 1
                continue
            st["aceito"] += 1
            # ⭐ a completion e' o bloco ```python — exatamente o que `extract_code` procura
            saida.append({
                "kind": "codigo",
                "tema": tema,
                "prompt": [{"role": "system", "content": rnd.choice(cats)},
                           {"role": "user", "content": item["prompt"]}],
                "completion": [{"role": "assistant",
                                "content": f"```python{NL}{item['solution']}{NL}```"}],
            })
            if feitos % 100 == 0 or feitos == len(alvos):
                print(f"  {feitos}/{len(alvos)} · {(time.time() - t0) / 60:.1f} min · "
                      f"aceitos {st['aceito']}", flush=True)

    p = PROC / f"codigo_util_{len(saida)}.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida), encoding="utf-8")
    print(f"{NL}{p.name}: {len(saida)} exemplos")
    for kk, v in st.most_common():
        print(f"  {kk:46} {v}")
    print(f"  custo real: US$ {c_in / 1e6 * 0.27 + c_out / 1e6 * 1.10:.3f}")
    if saida:
        # ⚠️ §2w: contar itens DISTINTOS, nao linhas. Nome de funcao repetido = problema repetido.
        nomes = [re.search(r"def\s+(\w+)", x["completion"][0]["content"]).group(1)
                 for x in saida]
        print(f"  funcoes DISTINTAS: {len(set(nomes))}/{len(nomes)} "
              f"({len(set(nomes)) / len(nomes):.1%})")
        print(f"  mais repetidas: {dict(Counter(nomes).most_common(5))}")
        print(f"  temas: {len(set(x['tema'] for x in saida))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
