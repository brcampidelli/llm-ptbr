"""Corpus de RESUMO para o Bee-350M — a capacidade que nunca teve treino.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-20 (E0) e reconfirmado em 30/08:

    resumo — util          0,0%   em TODOS os artefatos     (piso LEAD-2 = 51,3%)
    resumo — `comprimiu`   falha 150/150 no 150M E no 350M
    resumo — cobertura     73,2% (150M) · 84,0% (350M) · 77,8% (C-full)

⭐ **O gargalo e' COMPRESSAO, e so' ela.** O modelo le' o texto e cobre os fatos; ele nao
encurta. E dobrar o parametro nao move: 151M e 345M falham `comprimiu` nos mesmos 150/150.
Faltam DADOS, nao parametros — medido em `docs/bpb-compra-capacidade.md`.

## As fontes

`bee/edu/anotado.jsonl` — texto REAL em PT do fineweb-2, ja' local, com nota de qualidade.

⚠️ **NAO se usa o gerador do holdout.** `comeia/eval/gerar_resumo_pt.py` monta os 150 itens de
avaliacao a partir de 10 moldes; treinar com os mesmos moldes ensinaria o TEMPLATE e o holdout
mediria memorizacao, nao resumo (§2o). Texto real contra holdout sintetico e' teste de
generalizacao de verdade.

## 🔴 O CATALOGO DE FERRAMENTAS VAI NO SYSTEM, DE PROPOSITO

Todo exemplo do corpus agentico tem catalogo no `system`. Se os de resumo nao tivessem, o
modelo aprenderia **"sem system -> resuma"** — uma caracteristica superficial separando as
classes, que e' a §2u literal (la', o tamanho do catalogo separava chamar de recusar e o modelo
aprendeu a CONTAR). Aqui o catalogo entra igual, e o modelo tem de ler o pedido do usuario.

⭐ E isso torna o exemplo mais honesto: um agente com ferramentas disponiveis, recebendo uma
tarefa para a qual nenhuma serve, e **fazendo a tarefa** — a extensao natural do E19.

## As guardas: a regua VIRA a guarda

Tres das quatro condicoes de `avaliar_resumo` nao precisam de `fatos_essenciais` e entram
direto no laco de geracao. Uma geracao que reprova NAO entra no corpus e vai contada.

⚠️ E a guarda e' validada contra o ESTADO QUEBRADO (`--validar`): rodada sobre as saidas atuais
do modelo, ela tem de reprovar quase tudo. Guarda que nunca dispara pode estar inerte — ou
quebrada, como a de `esquema.py:459`, que era codigo nunca executado.

Uso:
    python comeia/data/resumos_uteis.py --dry-run      # so' o custo e 3 exemplos
    python comeia/data/resumos_uteis.py --validar      # prova que as guardas mordem
    python comeia/data/resumos_uteis.py --paralelo 6
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
from resumo_pt_verificadores import (  # noqa: E402
    LIMITES, cobertura, entidades_inventadas, extrair_entidades, extrair_numeros,
    numeros_inventados, razao_compressao,
)

NL = chr(10)
MODELO = "deepseek/deepseek-chat"
URL = "https://openrouter.ai/api/v1/chat/completions"
FONTE = RAIZ.parent / "bee" / "edu" / "anotado.jsonl"
CORPUS_BASE = PROC / "treino_e19c_neg_uteis.jsonl"

# ⭐ O MESMO PEDIDO QUE A REGUA USA. Treinar numa formulacao e medir noutra mede a formulacao
#    (§2g). Copiado de `comeia/eval/eval_resumo_pt.py`.
PEDIDO = ("Resuma o texto abaixo em duas frases, mantendo os números e os nomes exatamente "
          "como aparecem.")

INSTRUCAO = """Você resume textos em português do Brasil.

REGRAS:
1. EXATAMENTE duas frases. O resumo tem de ser MUITO mais curto que a fonte — entre 10% e 30% \
do tamanho dela. Este é o requisito mais importante.
2. Mantenha os números e os nomes próprios EXATAMENTE como aparecem na fonte.
3. NUNCA inclua um número ou um nome que não esteja na fonte.
4. Cubra os fatos centrais: quem, o quê, quanto, quando.
5. Só o resumo. Sem preâmbulo, sem "Resumo:", sem comentário."""


def chave() -> str:
    for ln in (RAIZ.parent / ".env").read_text(encoding="utf-8").splitlines():
        if ln.startswith("OPENROUTER_API_KEY"):
            return ln.split("=", 1)[1].strip()
    raise SystemExit("OPENROUTER_API_KEY ausente no .env")


def pedir(k: str, msgs: list[dict], tent: int = 3) -> tuple[str, dict]:
    corpo = json.dumps({"model": MODELO, "messages": msgs,
                        "temperature": 0.4, "max_tokens": 220}).encode()
    req = urllib.request.Request(URL, data=corpo, headers={
        "Authorization": "Bearer " + k, "Content-Type": "application/json"})
    for i in range(tent):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=90))
            return d["choices"][0]["message"]["content"].strip(), d.get("usage", {})
        except Exception as e:                                    # noqa: BLE001
            if i == tent - 1:
                return "", {"erro": f"{type(e).__name__}: {e}"}
            time.sleep(2 * (i + 1))
    return "", {}


def julgar(resumo: str, fonte: str, cob_min: float = 0.17) -> tuple[bool, str]:
    """As tres condicoes da regua que nao precisam de `fatos_essenciais`, mais cobertura
    numerica. Devolve (aceito, motivo_da_recusa)."""
    if not resumo or len(resumo.split()) < 5:
        return False, "vazio ou curto demais"
    razao = razao_compressao(resumo, fonte)
    if not (LIMITES["compressao_min"] <= razao <= LIMITES["compressao_max"]):
        return False, f"compressao fora de [{LIMITES['compressao_min']}, "\
                      f"{LIMITES['compressao_max']}] (razao {razao:.2f})"
    if numeros_inventados(resumo, fonte):
        return False, "numero inventado"
    if entidades_inventadas(resumo, fonte):
        return False, "entidade inventada"
    # cobertura sobre os numeros da fonte, com a MESMA funcao da regua
    # ⚠️ GUARDA AFROUXADA em 2026-08-31, e o motivo importa. A v1 exigia 34% dos 6 numeros
    #    mais salientes e rejeitou 157 de 608 geracoes (26%) — a maior causa de recusa. Mas
    #    `cobriu` falha em apenas 17/150 no modelo treinado: **cobertura nao e' o gargalo,
    #    compressao e'**. Filtrar no eixo errado matava de fome o sinal que se quer ensinar.
    #    Agora exige >=1 dos 6 (17%), e a guarda de compressao segue no valor da regua.
    nums = [{"tipo": "numero", "valor": v} for v in sorted(extrair_numeros(fonte))[:6]]
    if nums:
        ok, n = cobertura(resumo, nums)
        if ok / n < cob_min:
            return False, f"cobertura numerica baixa ({ok}/{n})"
    return True, ""


def fontes(nota_min: int, limite: int, min_pal: int = 60, max_pal: int = 600) -> list[dict]:
    out = []
    for l in FONTE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        t = r.get("texto", "")
        p = len(t.split())
        if not (min_pal <= p <= max_pal) or r.get("nota", 0) < nota_min:
            continue
        if len(extrair_numeros(t)) < 2 or len(extrair_entidades(t)) < 2:
            continue
        out.append(r)
        if limite and len(out) >= limite:
            break
    return out


def catalogos() -> list[str]:
    """Os `system` REAIS do corpus agentico — ver o cabecalho sobre a §2u."""
    vistos = []
    for l in CORPUS_BASE.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        s = next((m["content"] for m in json.loads(l)["prompt"] if m["role"] == "system"), None)
        if s:
            vistos.append(s)
    return vistos


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--nota-min", type=int, default=0)
    ap.add_argument("--min-pal", type=int, default=60)
    ap.add_argument("--max-pal", type=int, default=600)
    ap.add_argument("--cobertura-min", type=float, default=0.17)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260830)
    ap.add_argument("--paralelo", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validar", action="store_true",
                    help="prova que as guardas mordem, rodando-as sobre LEAD-2 e sobre a fonte "
                         "inteira (que e' o que o modelo atual faz)")
    a = ap.parse_args()

    srcs = fontes(a.nota_min, a.limite, a.min_pal, a.max_pal)
    print(f"{FONTE.name}: {len(srcs)} fontes utilizaveis "
          f"({a.min_pal}-{a.max_pal} palavras · nota>={a.nota_min} · >=2 numeros e >=2 entidades)")

    if a.validar:
        # 🔴 A GUARDA CONTRA O ESTADO QUEBRADO. O modelo atual devolve ~88% do tamanho da
        #    fonte; o LEAD-2 e' o piso. A guarda tem de reprovar o primeiro quase sempre.
        st: Counter = Counter()
        for r in srcs[:300]:
            f = r["texto"]
            st["fonte inteira REPROVADA" if not julgar(f, f, a.cobertura_min)[0]
               else "🔴 fonte inteira passou"] += 1
            lead = ". ".join(f.split(". ")[:2]) + "."
            st["LEAD-2 aceito" if julgar(lead, f, a.cobertura_min)[0] else "LEAD-2 reprovado"] += 1
        for k, v in st.most_common():
            print(f"  {k:34} {v}")
        print(f"{NL}⭐ a guarda morde: o comportamento atual do modelo (devolver a fonte quase "
              f"inteira) e' reprovado. Se 'fonte inteira passou' for >0, a guarda esta' frouxa.")
        return 0

    ent_est = sum(len(INSTRUCAO) + len(PEDIDO) + len(r["texto"]) for r in srcs) / 3.5
    print(f"  custo estimado: ~US$ {ent_est / 1e6 * 0.27 + len(srcs) * 90 / 1e6 * 1.10:.3f}")

    if a.dry_run:
        for r in srcs[:3]:
            print(f"{NL}  fonte ({len(r['texto'].split())} palavras, nota {r.get('nota')}): "
                  f"{r['texto'][:150]!r}")
        print(f"{NL}✅ dry-run: nada foi gerado nem gasto.")
        return 0

    k = chave()
    cats = catalogos()
    rnd = random.Random(a.seed)
    st2: Counter = Counter()
    saida, c_in, c_out = [], 0, 0
    t0 = time.time()

    def uma(r):
        msgs = [{"role": "system", "content": INSTRUCAO},
                {"role": "user", "content": f"{PEDIDO}{NL}{NL}{r['texto']}"}]
        txt, uso = pedir(k, msgs)
        return r, txt, uso

    from concurrent.futures import ThreadPoolExecutor
    feitos = 0
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for r, txt, uso in ex.map(uma, srcs):
            feitos += 1
            c_in += uso.get("prompt_tokens", 0)
            c_out += uso.get("completion_tokens", 0)
            if not txt:
                st2[f"🔴 erro da API: {str(uso.get('erro', '?'))[:36]}"] += 1
                continue
            txt = re.sub(r"^\s*(resumo|resposta)\s*:\s*", "", txt, flags=re.I).strip()
            ok, motivo = julgar(txt, r["texto"], a.cobertura_min)
            if not ok:
                st2[f"🔴 REPROVADO — {motivo.split('(')[0].strip()}"] += 1
                continue
            st2["aceito"] += 1
            # ⭐ catalogo no system, como todo exemplo do corpus (ver §2u no cabecalho)
            saida.append({
                "kind": "resumo",
                "prompt": [{"role": "system", "content": rnd.choice(cats)},
                           {"role": "user", "content": f"{PEDIDO}{NL}{NL}{r['texto']}"}],
                "completion": [{"role": "assistant", "content": txt}],
            })
            if feitos % 100 == 0 or feitos == len(srcs):
                print(f"  {feitos}/{len(srcs)} · {(time.time() - t0) / 60:.1f} min · "
                      f"aceitos {st2['aceito']}", flush=True)

    p = PROC / f"resumos_uteis_{len(saida)}.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida),
                 encoding="utf-8")
    print(f"{NL}{p.name}: {len(saida)} resumos")
    for kk, v in st2.most_common():
        print(f"  {kk:44} {v}")
    print(f"  custo real: US$ {c_in / 1e6 * 0.27 + c_out / 1e6 * 1.10:.3f}")
    if saida:
        import statistics as sts
        raz = [razao_compressao(x["completion"][0]["content"],
                                x["prompt"][1]["content"].split(NL + NL, 1)[1]) for x in saida]
        print(f"  compressao dos aceitos: mediana {sts.median(raz):.3f} "
              f"(a regua exige <= {LIMITES['compressao_max']}; as referencias do holdout "
              f"ficam em 0,242)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
