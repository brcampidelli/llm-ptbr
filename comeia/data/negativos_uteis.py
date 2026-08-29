"""Reescreve a classe NEGATIVA do corpus agentico: resposta util no lugar da formula de recusa.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-28/29 (E18 e E19):

  · 91,1% dos 4.421 exemplos negativos sao recusas — 36% do corpus inteiro;
  · o modelo generalizou "sem ferramenta -> recuse" para TODA tarefa: pedido de traducao
    respondido com *"nao consigo traduzir com as ferramentas disponiveis"*;
  · tirar os negativos (E19-B) devolve a resposta (resumo 0->84/150, atendimento JSON
    0->27,6%) mas explode o over-calling de 17,2% para **84,7%** e perde o sentimento.

⭐ A classe negativa acumulava TRES funcoes: marcar quando nao chamar, fornecer o unico texto
livre variado do corpus, e — sem necessidade nenhuma — ensinar a recusar. So' a terceira e'
indesejada. Este script troca a FORMA, mantendo prompt e decisao de nao emitir chamada.

⚠️ E O ALVO NAO E' "NUNCA RECUSAR". Boa parte dos pedidos exige acao no mundo (criar fatura,
verificar disponibilidade de e-mail, registrar despesa). Ensinar o modelo a dizer que fez
seria ensinar a mentir. O alvo e': **recusar a ACAO sem formula, e ser util no turno** — e,
quando o pedido e' respondivel so' com raciocinio (conta, conversao, explicacao), RESPONDER.

🔴 GUARDA OBRIGATORIA. Sem ela este script pode trocar recusa por recusa e nada reclamaria —
a familia de defeitos que nao da' erro. Toda geracao passa por `tem_formula()`; a que reprova
NAO entra no corpus e vai contada no relatorio.

Uso:
    python comeia/data/negativos_uteis.py --n 500 --dry-run   # so' o custo e 3 exemplos
    python comeia/data/negativos_uteis.py --n 500
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
NL = chr(10)
MODELO = "deepseek/deepseek-chat"
URL = "https://openrouter.ai/api/v1/chat/completions"

# 🔴 as marcas da formula que o corpus atual ensina. Uma geracao que contenha qualquer uma
#    delas e' recusa vestida de resposta e NAO entra.
FORMULA = re.compile(
    r"(ferramentas? disponiveis|com as ferramentas|minhas (funcoes|ferramentas)"
    r"|nao (disponho|possuo)|funcoes (disponiveis|estao limitadas)"
    r"|posso ajudar apenas|nao tenho (uma |a )?ferramenta"
    r"|sinto muito, mas nao|desculpe, mas nao consigo)")

# 🔴 SEGUNDA GUARDA, medida em 2026-08-29 na fatia de 500: 2,4% [1,4–4,2%] das geracoes
#    AFIRMAM um valor vivo — "hoje 1 USD vale 0,93 EUR" — que o professor nao tem como saber.
#    Treinar nisso ensina a inventar cotacao. Nao da' erro nenhum: a resposta e' fluente,
#    util na aparencia, e so' aparece se alguem for conferir o numero.
#
#    ⚠️ A instrucao do professor NAO foi alterada de proposito. Mudar instrucao E dose entre a
#    fatia e o corpus completo faria a comparacao medir as duas coisas (§2g). A correcao entra
#    como rejeicao, que e' o que foi feito a mao nos 500.
VALOR_VIVO = re.compile(
    r"(cotacao|taxa de cambio|hoje.{0,20}(vale|esta valendo)"
    r"|atualmente.{0,15}(vale|equivale)|1 usd|1 eur|1 dolar)")

INSTRUCAO = """Você é um assistente em português do Brasil. Responda à mensagem do usuário de \
forma útil e natural.

REGRAS:
1. Se o pedido pode ser atendido só com raciocínio ou conhecimento (uma conta, uma conversão, \
uma explicação, uma recomendação, redigir um texto), ATENDA. Faça a conta, dê a resposta.
2. Se o pedido exige uma ação no mundo real que você não pode executar (criar registro, enviar \
algo, consultar um sistema externo), diga isso em poucas palavras e SEJA ÚTIL MESMO ASSIM: \
explique o que é preciso, ofereça o rascunho, ou dê a informação que dá para dar.
3. NUNCA invente que executou a ação, e NUNCA invente dados que o usuário não deu.
4. NUNCA use estas construções: "com as ferramentas disponíveis", "minhas funções estão \
limitadas", "não disponho de uma ferramenta", "posso ajudar apenas com". Elas estão proibidas.
5. Não liste suas capacidades. Não ofereça um menu de funções.
6. De 1 a 4 frases. Português do Brasil, tom natural e variado."""


def nz(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def tem_formula(t: str) -> bool:
    return bool(FORMULA.search(nz(t)))


def afirma_valor_vivo(t: str) -> bool:
    return bool(VALOR_VIVO.search(nz(t)))


def chave_do_pedido(r: dict) -> str:
    """Identidade do exemplo, para nao regerar o que ja' existe."""
    return NL.join(m["content"] for m in r["prompt"] if m["role"] != "system")


def chave() -> str:
    for ln in (RAIZ.parent / ".env").read_text(encoding="utf-8").splitlines():
        if ln.startswith("OPENROUTER_API_KEY"):
            return ln.split("=", 1)[1].strip()
    raise SystemExit("OPENROUTER_API_KEY ausente no .env")


def pedir(k: str, mensagens: list[dict], tent: int = 3) -> tuple[str, dict]:
    corpo = json.dumps({"model": MODELO, "messages": mensagens,
                        "temperature": 0.7, "max_tokens": 220}).encode()
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


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "treino_vocab_diverso.jsonl")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260829)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--todos", action="store_true", help="todos os negativos, ignora --n")
    ap.add_argument("--reaproveitar", type=Path, action="append", default=[],
                    help="jsonl ja' gerado; os pedidos dele NAO sao regerados")
    ap.add_argument("--paralelo", type=int, default=6,
                    help="requisicoes simultaneas. Acima de ~8 o OpenRouter devolve 429.")
    a = ap.parse_args()

    linhas = [json.loads(l) for l in a.fonte.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    neg = [r for r in linhas if r.get("kind") != "tool_call"]
    rnd = random.Random(a.seed)
    alvo = neg if a.todos else rnd.sample(neg, min(a.n, len(neg)))
    # ⚠️ o sorteio da fatia usa a MESMA semente, entao os 500 da fatia sao um subconjunto
    #    identificavel — reaproveitados por identidade do pedido, nao por indice.
    ja = set()
    for f in a.reaproveitar:
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                ja.add(chave_do_pedido(json.loads(l)))
    if ja:
        antes = len(alvo)
        alvo = [r for r in alvo if chave_do_pedido(r) not in ja]
        print(f"  reaproveitados {antes - len(alvo)} ja' gerados · faltam {len(alvo)}")
    print(f"{a.fonte.name}: {len(linhas)} exemplos · negativos {len(neg)} · "
          f"sorteados {len(alvo)} (semente {a.seed})")

    # ⚠️ o custo vai IMPRESSO antes de gastar. deepseek-chat: ~US$0,27/M entrada, 1,10/M saida.
    ent_est = sum(len(INSTRUCAO) + sum(len(m["content"]) for m in r["prompt"]
                                       if m["role"] != "system") for r in alvo) / 3.5
    print(f"  custo estimado: ~US$ {ent_est / 1e6 * 0.27 + len(alvo) * 150 / 1e6 * 1.10:.3f}")

    if a.dry_run:
        for r in alvo[:3]:
            u = [m["content"] for m in r["prompt"] if m["role"] != "system"]
            print(f"{NL}  pedido : {u[0][:120]!r}")
            print(f"  recusa : {r['completion'][0]['content'][:120]!r}")
        print(f"{NL}✅ dry-run: nada foi gerado nem gasto.")
        return 0

    k = chave()
    st: Counter = Counter()
    saida, custo_in, custo_out = [], 0, 0
    t0 = time.time()

    def uma(r):
        turnos = [{"role": m["role"], "content": m["content"]}
                  for m in r["prompt"] if m["role"] != "system"]
        txt, uso = pedir(k, [{"role": "system", "content": INSTRUCAO}, *turnos])
        return r, txt, uso

    from concurrent.futures import ThreadPoolExecutor
    feitos = 0
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for r, txt, uso in ex.map(uma, alvo):
            feitos += 1
            custo_in += uso.get("prompt_tokens", 0)
            custo_out += uso.get("completion_tokens", 0)
            if not txt:
                st[f"🔴 erro da API: {str(uso.get('erro', '?'))[:40]}"] += 1
            elif tem_formula(txt):
                st["🔴 REPROVADO — ainda e' a formula"] += 1
            elif afirma_valor_vivo(txt):
                st["🔴 REPROVADO — afirma valor vivo"] += 1
            else:
                st["aceito"] += 1
                saida.append({**r, "completion": [{"role": "assistant", "content": txt}],
                              "_negativo_util": True})
            if feitos % 200 == 0 or feitos == len(alvo):
                print(f"  {feitos}/{len(alvo)} · {(time.time() - t0) / 60:.1f} min · "
                      f"aceitos {st['aceito']}", flush=True)

    p = PROC / f"negativos_uteis_{len(saida)}.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida),
                 encoding="utf-8")
    print(f"{NL}{p.name}: {len(saida)} negativos uteis")
    for kk, v in st.most_common():
        print(f"  {kk:44} {v}")
    print(f"  custo real: {custo_in} tok entrada + {custo_out} saida = "
          f"US$ {custo_in / 1e6 * 0.27 + custo_out / 1e6 * 1.10:.3f}")
    # ⚠️ taxa de reprovacao alta significa que o professor tambem recusa — e ai' o braco C
    #    nao e' viavel com este professor, o que e' resultado e nao erro.
    rep = st["🔴 REPROVADO — ainda e' a formula"]
    if rep > len(alvo) * 0.2:
        print(f"{NL}🔴 {rep / len(alvo):.1%} das geracoes ainda sao a formula. O professor "
              f"tambem recusa — reescrever a instrucao ou trocar de modelo antes de treinar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
