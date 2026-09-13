"""Recusa ESPECIFICA sem template — intervencao (b) do gate #3 (arXiv 2609.04714).

O artigo mede, por teste causal, que a FRASE-PADRAO FIXA de recusa — nao o conteudo, nao a
decisao de recusar — e' a causa da generalizacao excessiva de recusa. Este projeto mediu o
sintoma (§2ab: 91% de negativos em template ensinaram a recusar TUDO) e a saida do E19 foi trocar
recusa por RESPOSTA UTIL — que devolveu as outras capacidades e custou 5,9 pp de execucao.

Este braco e' o TERCEIRO ponto, que ninguem mediu: MANTER a decisao de recusar (o modelo nao
chama ferramenta nem finge que executou) e tirar SO o template — uma recusa especifica ao pedido.
A pergunta: recupera os 5,9 pp mantendo o ganho de over-calling?

Fonte: os 4.421 negativos de `treino_email_diverso.jsonl` (o corpus do e13, recusa em template).
Os positivos sao os mesmos do e13/E19. Reusa `pedir`, `chave`, `tem_formula` de negativos_uteis.

GUARDAS mecanicas, validadas contra o corpus do e13 antes de confiar (§2t — ver _autoteste):
  1. sem template: `tem_formula()` do E19 e mais as aberturas fixas do e13 (RX_ABERTURA)
  2. sem JSON de chamada: nao pode conter {"tool"
  3. RECUSA de fato: contem negacao ("nao consigo/posso/tenho como", "nao e possivel", "nao da")
  4. ESPECIFICA: ao menos uma palavra de conteudo (>= 5 letras) do pedido aparece na resposta
Rejeicao e' contada e impressa (§2r: quanto agiu). Gera em temporario e renomeia (§escrever-em-temporario).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
from negativos_uteis import pedir, chave, chave_do_pedido, tem_formula, nz, PROC, NL   # noqa: E402

RX_ABERTURA = re.compile(r"^(desculpe|sinto muito|lamento|infelizmente|nao consigo|não consigo)[,!.\s]", re.I)
# 🔴 v1 (2026-09-12): 62% das recusas geradas abriam com "Não consigo calcular" — o professor
#    trocou o template proibido por um template novo. Concentracao e' propriedade do CONJUNTO, e
#    as guardas por exemplo nao a veem. v2: cada pedido recebe um ESTILO sorteado, "Nao consigo"
#    fica proibido como abertura, e uma guarda de conjunto reprova abertura > LIMIAR_ABERTURA.
ESTILOS = [
    "Comece pelo OBJETO do pedido, nao por 'nao': ex. 'O calculo desse desconto nao e algo que eu faca por aqui.'",
    "Use a construcao 'Isso — [objeto] — esta fora do que eu faco neste contexto.'",
    "Use a construcao 'Nao da para eu [verbo + objeto] daqui.'",
    "Use a construcao '[Objeto] fica fora do meu alcance neste momento.'",
    "Use a construcao 'Aqui eu nao tenho como [verbo + objeto].'",
    "Use a construcao 'Esse tipo de pedido — [objeto] — eu nao executo.'",
    "Use a construcao '[Verbo + objeto] nao e possivel por este canal.'",
    "Use a construcao 'Sem meios de [verbo + objeto] por aqui.'",
    # ⚠️ piloto v2 (120): estilos de abertura FIXA passam nas guardas com mais facilidade e um
    #    deles chegou a 23%. Mais estilos que comecam pelo OBJETO (abertura variavel por construcao):
    "Comece pelo objeto e feche com 'nao e algo que eu faca aqui': ex. 'A gorjeta dessa conta nao e algo que eu faca aqui.'",
    "Comece com 'Para [objeto], ...' e diga que nao tem como: ex. 'Para o saldo da poupanca, eu nao tenho como consultar daqui.'",
    "Comece pelo verbo no infinitivo: '[Verbo + objeto] esta fora do que eu consigo fazer daqui.'",
    "Comece com 'Quanto a [objeto], ...': ex. 'Quanto ao voo para Lisboa, reservar nao esta ao meu alcance.'",
]
LIMIAR_ABERTURA = 0.15
RX_JSON = re.compile(r'\{\s*"tool"')
RX_NEGACAO = re.compile(r"(nao (consigo|posso|tenho como|e possivel|da para|sou capaz|vou conseguir|tenho acesso|tenho meio"
                        r"|executo|faco|e algo que|realizo|efetuo|processo|tenho|ha como)"
                        r"|impossivel|fora d[oa] (meu|que eu|minha)|nao esta ao meu alcance|sem meios de|sem como)")
STOP = set("sobre para como esta este essa esse aquele aquela entre porque quando onde quero preciso gostaria poderia pode voce voces minha meu minhas meus".split())

INSTRUCAO = """Você é um assistente em português do Brasil. O usuário pediu algo que você NÃO pode \
fazer neste contexto — nenhuma das suas funções cobre este pedido. Você deve RECUSAR.

REGRAS:
1. Recuse de forma ESPECÍFICA a este pedido: diga exatamente o que você não consegue fazer AQUI, \
citando o objeto do pedido (ex.: "não consigo verificar o saldo da sua conta poupança", "não tenho \
como enviar essa mensagem para a Ana"). Em 1 a 3 frases.
2. NUNCA finja que executou. NUNCA dê a resposta como se tivesse acesso ao sistema.
3. PROIBIDO usar frases-padrão: "Sinto muito, mas não tenho uma ferramenta", "Desculpe, mas \
nenhuma das ferramentas", "com as ferramentas disponíveis", "minhas funções estão limitadas", \
"não disponho de", "posso ajudar apenas com". Não comece com "Desculpe", "Sinto muito", \
"Infelizmente" ou "Lamento".
4. Não ofereça alternativas, não liste capacidades, não faça menu, não dê a informação pedida.
5. NUNCA comece com "Não consigo". Tom natural, direto, sem pedir desculpas.
6. ESTILO OBRIGATÓRIO desta resposta: {estilo}"""


def palavras_conteudo(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", nz(t)) if w not in STOP}


def guardas(resposta: str, pedido: str) -> str | None:
    """None se passa; senao o nome da guarda que reprovou."""
    n = nz(resposta)
    if tem_formula(resposta) or RX_ABERTURA.match(resposta.strip()):
        return "template"
    if RX_JSON.search(resposta):
        return "json"
    if not RX_NEGACAO.search(n):
        return "nao_recusa"
    if not (palavras_conteudo(pedido) & palavras_conteudo(resposta)):
        return "generica"
    return None


def _autoteste() -> int:
    """As guardas tem de REPROVAR o corpus do e13 (template) e ACEITAR uma recusa especifica."""
    e13 = PROC / "treino_email_diverso.jsonl"
    negs = [json.loads(l) for l in e13.read_text(encoding="utf-8").splitlines() if l.strip()]
    negs = [r for r in negs if r.get("kind") == "text"][:500]
    c = Counter(guardas(r["completion"][0]["content"], chave_do_pedido(r)) or "PASSOU" for r in negs)
    print("  guardas contra 500 negativos do e13 (template):", dict(c))
    assert c["PASSOU"] / len(negs) < 0.15, "as guardas deixam passar template demais — inertes"
    ok = guardas("O saldo da sua conta poupança fica fora do que eu tenho como consultar por aqui.",
                 "Qual é o saldo da minha conta poupança?")
    assert ok is None, ok
    print("  recusa especifica de exemplo: PASSOU")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fonte", type=Path, default=PROC / "treino_email_diverso.jsonl")
    ap.add_argument("--saida", type=Path, default=PROC / "treino_e19d_recusa_especifica.jsonl")
    ap.add_argument("--n", type=int, default=0, help="0 = todos os negativos")
    ap.add_argument("--paralelo", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260912)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--autoteste", action="store_true")
    args = ap.parse_args()
    if args.autoteste:
        return _autoteste()
    if args.saida.exists():
        raise SystemExit(f"🔴 {args.saida} ja existe — nao sobrescrevo (§2z)")
    _autoteste()

    linhas = [json.loads(l) for l in args.fonte.read_text(encoding="utf-8").splitlines() if l.strip()]
    pos = [r for r in linhas if r.get("kind") == "tool_call"]
    neg = [r for r in linhas if r.get("kind") == "text"]
    if args.n:
        neg = random.Random(args.seed).sample(neg, args.n)
    tok_in = sum(len(chave_do_pedido(r)) for r in neg) // 4 + 220 * len(neg)
    print(f"fonte {args.fonte.name}: {len(pos)} positivos (intocados) · {len(neg)} negativos a regerar")
    print(f"  custo estimado (deepseek-chat, US$0,27/M in · 1,10/M out): ~US$ {tok_in/1e6*0.27 + len(neg)*90/1e6*1.10:.2f}")
    if args.dry_run:
        return 0

    k = chave()
    rej = Counter(); feitos = []
    t0 = time.time()

    def uma(r):
        pedido = chave_do_pedido(r)
        estilo = ESTILOS[int(hashlib.sha1(pedido.encode()).hexdigest(), 16) % len(ESTILOS)]
        msgs = [{"role": "system", "content": INSTRUCAO.format(estilo=estilo)}] + [m for m in r["prompt"] if m["role"] != "system"]
        for tent in range(3):
            txt, _ = pedir(k, msgs)
            g = guardas(txt, pedido)
            if g is None:
                return r, txt, None
            rej[g] += 1
        return r, None, g

    with ThreadPoolExecutor(args.paralelo) as ex:
        for i, (r, txt, g) in enumerate(ex.map(uma, neg), 1):
            if txt is not None:
                feitos.append({**r, "completion": [{"role": "assistant", "content": txt}], "_recusa_especifica": True})
            if i % 200 == 0:
                print(f"  {i}/{len(neg)} · aceitos {len(feitos)} · rejeicoes {dict(rej)} · {time.time()-t0:.0f}s", flush=True)

    saida = pos + feitos
    random.Random(args.seed).shuffle(saida)
    tmp = args.saida.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in saida) + "\n", encoding="utf-8")
    tmp.replace(args.saida)
    print(f"\n{args.saida.name}: {len(saida)} exemplos = {len(pos)} positivos + {len(feitos)} recusas especificas")
    print(f"  ⭐ QUANTO AGIU (§2r): descartados apos 3 tentativas {len(neg)-len(feitos)} · rejeicoes por guarda {dict(rej)}")
    # 🔴 GUARDA DE CONJUNTO: nenhuma abertura de 3 palavras pode dominar
    ab = Counter(" ".join(nz(f["completion"][0]["content"]).split()[:3]) for f in feitos)
    top = ab.most_common(5)
    print(f"  aberturas mais comuns: {top}")
    pior = top[0][1] / max(len(feitos), 1)
    if pior > LIMIAR_ABERTURA:
        print(f"  🔴 abertura dominante em {pior:.1%} > {LIMIAR_ABERTURA:.0%}: o corpus tem template novo — NAO use para o gate")
        return 3
    print(f"  ✅ abertura mais comum em {pior:.1%} <= {LIMIAR_ABERTURA:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
