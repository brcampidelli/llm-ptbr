"""Corpus de ATENDIMENTO para o Bee-350M — a segunda capacidade que nunca teve treino.

🔴 POR QUE ISTO EXISTE. `atendimento util` esta' em **0,0% em todos os artefatos** do projeto —
base, e13, C-full, E20, E21, E22 — contra um piso de **60,4%** feito de palavra-chave e regex.
E `json_ok` vai de 0,0% (base) a 30,9% (C-full): o gargalo e' **emitir o formato**.

    util = intencao certa **E** todos os campos extraidos certos

⭐ E A TAREFA TEM A MESMA FORMA DA AGENTICA: classificar num rotulo fechado (10 intencoes, como
um catalogo de ferramentas) e extrair argumentos do pedido. O modelo faz 77,7% de selecao de
ferramenta — a capacidade existe; o que falta e' o formato desta regua.

## ⭐⭐ O desenho: o rotulo e' verdade POR CONSTRUCAO

O caminho obvio — pedir ao professor que leia uma mensagem e a classifique — treinaria no
**julgamento do professor**, que ninguem verificou. Aqui e' o inverso:

  1. eu **sorteio** (intencao, dados) — os valores sao meus;
  2. o professor escreve uma mensagem de cliente natural que os contenha;
  3. a referencia e' exatamente o que eu sorteei.

⚠️ **E a guarda e' a §2n:** todo valor da referencia tem de **aparecer na mensagem**. Sem isso o
gabarito nao e' derivavel do que o modelo recebe — o defeito que ja' tornou 17,3% de um holdout
deste projeto impossivel por construcao. Aqui a verificacao e' mecanica e recusa o exemplo.

## ⚠️ O que se compartilha com o holdout, e o que NAO

**Compartilhado de proposito:** as 10 intencoes e as chaves de dados. E' um espaco de rotulos
fechado — treinar noutro espaco mediria outra tarefa (§2g).

**Disjunto de proposito:** a **superficie**. O holdout vem de 10 moldes em
`comeia/eval/gerar_atendimento_pt.py`; aqui a mensagem e' escrita pelo professor. Usar os moldes
ensinaria o template e o holdout mediria memorizacao (§2o).

## §2w — os valores sao DIVERSOS, nao 22 cadeias repetidas

Numero de pedido, e-mail, CEP e valor sao **cadeia arbitraria**: so' se aprende copiando. O E13
mediu que 724 e-mails com apenas **22 distintos** ensinavam a decorar, e diversificar deu +12 pp
de copia. Aqui cada exemplo sorteia valores novos.

## E a politica, que e' o eixo de SEGURANCA

A regua conta `violou_politica` **separado** do acerto, de proposito: prometer estorno "hoje
mesmo" e' passivo, nao erro de classificacao. As 14 frases proibidas entram como guarda —
geracao que promete o impossivel **nao entra no corpus**.

Uso:
    python comeia/data/atendimento_util.py --dry-run
    python comeia/data/atendimento_util.py --validar    # prova que as guardas mordem
    python comeia/data/atendimento_util.py --n 900 --paralelo 8
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
sys.path.insert(0, str(RAIZ / "eval"))
from gerar_atendimento_pt import POLITICA, PROIBIDAS  # noqa: E402

NL = chr(10)
MODELO = "deepseek/deepseek-chat"
URL = "https://openrouter.ai/api/v1/chat/completions"
CORPUS_BASE = PROC / "treino_e19c_neg_uteis.jsonl"

# ⭐ mesmo PEDIDO da regua, copiado de `comeia/eval/eval_atendimento_pt.py`. Treinar numa
#    formulacao e medir noutra mede a formulacao (§2g).
PEDIDO = ("Voce e o atendimento de uma loja online. {politica}\n\n"
          "Responda ao cliente e classifique o pedido dele.\n"
          "Formato da resposta: primeiro uma linha JSON "
          '{{"intencao": "...", "dados": {{...}}}} e depois a mensagem ao cliente.\n\n'
          "Cliente: {mensagem}\n\nAtendimento:")

# as 10 intencoes e as chaves que cada uma carrega — lidas do holdout, nao inventadas
CAMPOS = {
    "alterar_endereco": ["numero_pedido", "cep"],
    "cancelar_assinatura": ["email"],
    "cancelar_pedido": ["numero_pedido"],
    "duvida_prazo": ["cep"],
    "problema_pagamento": ["valor"],
    "rastrear_pedido": ["numero_pedido"],
    "reclamar_atendimento": ["numero_pedido"],
    "segunda_via_boleto": ["numero_pedido"],
    "solicitar_reembolso": ["numero_pedido", "valor"],
    "trocar_produto": ["numero_pedido"],
}
CONTEXTO = {
    "alterar_endereco": "quer mudar o endereco de entrega",
    "cancelar_assinatura": "quer cancelar a assinatura",
    "cancelar_pedido": "quer cancelar o pedido",
    "duvida_prazo": "quer saber o prazo de entrega para o CEP dele",
    "problema_pagamento": "teve um problema com a cobranca",
    "rastrear_pedido": "quer saber onde esta' o pedido",
    "reclamar_atendimento": "esta' reclamando do atendimento que recebeu",
    "segunda_via_boleto": "perdeu o boleto e quer a segunda via",
    "solicitar_reembolso": "quer o dinheiro de volta",
    "trocar_produto": "quer trocar o produto",
}

INSTRUCAO = """Você escreve mensagens de clientes reais para uma loja online brasileira.

Escreva UMA mensagem curta (1 a 3 frases), em português do Brasil, no tom de quem escreve para \
um SAC — pode ser informal, com pressa, um pouco irritado, ou educado. Varie o tom.

REGRAS:
1. A mensagem TEM de conter, escritos exatamente como fornecidos, TODOS os dados listados.
2. Escreva como o cliente escreveria de verdade. Se ele quer cancelar um pedido, ele diz \
"cancelar" e "pedido" — isso é português, não é problema.
3. Não invente outros números, e-mails ou códigos além dos fornecidos.
4. Só a mensagem do cliente. Sem aspas em volta, sem rótulo, sem explicação."""


def nz(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


def chave() -> str:
    for ln in (RAIZ.parent / ".env").read_text(encoding="utf-8").splitlines():
        if ln.startswith("OPENROUTER_API_KEY"):
            return ln.split("=", 1)[1].strip()
    raise SystemExit("OPENROUTER_API_KEY ausente no .env")


def pedir(k: str, msgs: list[dict], tent: int = 3) -> tuple[str, dict]:
    corpo = json.dumps({"model": MODELO, "messages": msgs,
                        "temperature": 0.9, "max_tokens": 160}).encode()
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


def sortear(rnd: random.Random) -> tuple[str, dict]:
    """(intencao, dados) com valores DIVERSOS — §2w: cadeia arbitraria so' se aprende copiando."""
    intencao = rnd.choice(list(CAMPOS))
    d: dict = {}
    for c in CAMPOS[intencao]:
        if c == "numero_pedido":
            d[c] = rnd.choice([
                f"BR-{rnd.randint(100000, 999999)}",
                f"{rnd.randint(1000000, 9999999)}",
                f"{rnd.randint(10000, 99999)}-{rnd.randint(1, 9)}",
                f"PED{rnd.randint(10000, 99999)}",
            ])
        elif c == "valor":
            d[c] = round(rnd.uniform(19.9, 4999.9), 2)
        elif c == "cep":
            d[c] = f"{rnd.randint(10000, 99999)}-{rnd.randint(100, 999)}"
        elif c == "email":
            nome = rnd.choice(["ana", "bruno", "carla", "diego", "elis", "fabio", "gabi",
                               "helio", "ines", "joao", "kau", "lia", "marco", "nina",
                               "otavio", "paula", "rui", "sofia", "tiago", "vera"])
            d[c] = (f"{nome}.{rnd.choice(['silva','souza','lima','costa','rocha','alves'])}"
                    f"{rnd.randint(1, 999)}@"
                    f"{rnd.choice(['gmail.com','uol.com.br','outlook.com','bol.com.br','me.com'])}")
    return intencao, d


def como_texto(v) -> list[str]:
    """As formas em que um valor pode aparecer na mensagem — numero aceita virgula ou ponto.

    ⚠️ `str(v)` ESTA' NA LISTA de proposito. O prompt diz ao professor `valor = 19.9` (via
    f-string), e a v1 so' aceitava `19,90`/`19.90` — entao o professor escrevendo **exatamente o
    que foi pedido** era reprovado. Pego pela propria validacao (292/300 em vez de 300/300), que
    e' o motivo de a guarda ser testada contra casos construidos antes de gastar.
    """
    if isinstance(v, float):
        return [f"{v:.2f}".replace(".", ","), f"{v:.2f}",
                f"{v:,.2f}".replace(",", "."), str(v), str(v).replace(".", ",")]
    return [str(v)]


def julgar(msg: str, dados: dict, intencao: str) -> tuple[bool, str]:
    """§2n: todo valor da referencia aparece na MENSAGEM. Sem isso o gabarito nao e' derivavel."""
    if not msg or len(msg.split()) < 4:
        return False, "vazia ou curta demais"
    m = nz(msg)
    for c, v in dados.items():
        if not any(nz(f) in m for f in como_texto(v)):
            return False, f"valor de '{c}' NAO aparece na mensagem"
    # 🔴🔴 AQUI HAVIA UMA GUARDA "o professor nao pode entregar o rotulo de bandeja", que
    #     rejeitava a mensagem se ela contivesse qualquer palavra do nome da intencao com mais
    #     de 5 letras. Ela REPROVOU 642 de 900 (71%) e deixou CINCO das dez intencoes com ZERO
    #     exemplos: cancelar_pedido, rastrear_pedido, segunda_via_boleto, trocar_produto e
    #     cancelar_assinatura.
    #
    #     O motivo e' obvio depois de ver: um cliente que quer cancelar um pedido escreve
    #     "cancelar meu pedido". Nao e' vazamento de rotulo — e' portugues. E o HOLDOUT tem a
    #     mesma propriedade ("Perdi o **boleto** do **pedido** BR-292042" para
    #     `segunda_via_boleto`), entao a guarda fazia o treino vir de um processo DIFERENTE do
    #     teste (§2g) com **vies de selecao correlacionado ao rotulo** (§2u ao contrario).
    #
    #     Treinar naquele corpus ensinaria que "pedido" nunca ocorre com cancelar/rastrear/
    #     trocar — falso, e ativamente prejudicial. A guarda que fica e' a §2n, acima.
    return True, ""


def resposta(intencao: str, dados: dict) -> str:
    """A completion: a linha JSON exigida pela regua, e depois a mensagem ao cliente.

    ⚠️ A mensagem ao cliente e' DETERMINISTICA e conservadora de proposito. A regua conta
    `violou_politica` separado do acerto, e as 14 frases proibidas sao promessas de prazo —
    nenhuma delas pode sair daqui. Gerar a resposta com o professor arriscaria isso sem ganho:
    o que se esta' ensinando e' o FORMATO e a extracao, nao redacao.
    """
    linha = json.dumps({"intencao": intencao, "dados": dados}, ensure_ascii=False)
    texto = {
        "alterar_endereco": "Certo, registrei o novo CEP para o seu pedido. A alteração vale se o pedido ainda não tiver sido enviado.",
        "cancelar_assinatura": "Certo, registrei o cancelamento da assinatura. Ela encerra no fim do ciclo já pago.",
        "cancelar_pedido": "Verifiquei aqui: o cancelamento só é possível antes do envio. Vou checar o status e retorno.",
        "duvida_prazo": "Consultei o prazo para esse CEP e retorno com a estimativa da transportadora.",
        "problema_pagamento": "Localizei a cobrança e vou abrir a verificação com o financeiro.",
        "rastrear_pedido": "Localizei seu pedido e vou verificar a posição com a transportadora.",
        "reclamar_atendimento": "Sinto muito pela experiência. Registrei sua reclamação e ela será analisada.",
        "segunda_via_boleto": "Certo, vou providenciar o reenvio da segunda via do boleto.",
        "solicitar_reembolso": "Registrei seu pedido de reembolso. O estorno ocorre em até 7 dias úteis após a devolução ser recebida.",
        "trocar_produto": "Registrei a solicitação de troca. Troca por defeito ocorre em até 5 dias úteis.",
    }[intencao]
    return f"{linha}{NL}{texto}"


def catalogos() -> list[str]:
    """§2u: o catalogo de ferramentas vai no `system`, como em todo exemplo do corpus."""
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
    ap.add_argument("--paralelo", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validar", action="store_true")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    alvos = [sortear(rnd) for _ in range(a.n)]
    print(f"{a.n} exemplos sorteados · {len(CAMPOS)} intencoes · "
          f"{len({tuple(d.values()) for _, d in alvos})} tuplas de dados DISTINTAS")

    if a.validar:
        # 🔴 GUARDA CONTRA O ESTADO QUEBRADO: mensagem que NAO contem os dados tem de reprovar.
        st: Counter = Counter()
        for intencao, dados in alvos[:300]:
            st["ok — mensagem com os dados"] += julgar(
                "Oi, " + " e ".join(str(v) for v in dados.values()) + ", pode ver isso?",
                dados, intencao)[0]
            st["🔴 mensagem SEM os dados passou"] += julgar(
                "Oi, preciso de ajuda com o meu pedido, por favor.", dados, intencao)[0]
            # ⭐ o holdout diz "Perdi o boleto do pedido BR-292042" para segunda_via_boleto:
            #    palavra do rotulo na mensagem e' NORMAL e tem de ser ACEITA.
            st["mensagem com palavra do rotulo ACEITA (como o holdout)"] += julgar(
                f"Oi, quero {intencao.replace('_', ' ')} "
                + " ".join(str(v) for v in dados.values()), dados, intencao)[0]
        for k, v in st.most_common():
            print(f"  {k:38} {v}")
        print(f"{NL}⚠️ 'mensagem SEM os dados passou' tem de ser 0 — e' a §2n. Se for >0, o "
              f"gabarito nao seria derivavel do que o modelo recebe.")
        return 0

    est = sum(len(INSTRUCAO) + 120 for _ in alvos) / 3.5
    print(f"  custo estimado: ~US$ {est / 1e6 * 0.27 + a.n * 60 / 1e6 * 1.10:.3f}")
    if a.dry_run:
        for intencao, dados in alvos[:4]:
            print(f"    {intencao:22} {dados}")
        print(f"{NL}✅ dry-run: nada gerado nem gasto.")
        return 0

    k = chave()
    cats = catalogos()
    st2: Counter = Counter()
    saida, c_in, c_out = [], 0, 0
    t0 = time.time()

    def uma(alvo):
        intencao, dados = alvo
        campos = ", ".join(f"{c} = {v}" for c, v in dados.items())
        p = (f"O cliente {CONTEXTO[intencao]}.{NL}Dados que a mensagem DEVE conter, "
             f"escritos exatamente assim: {campos}")
        txt, uso = pedir(k, [{"role": "system", "content": INSTRUCAO},
                             {"role": "user", "content": p}])
        return alvo, txt, uso

    from concurrent.futures import ThreadPoolExecutor
    feitos = 0
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for (intencao, dados), txt, uso in ex.map(uma, alvos):
            feitos += 1
            c_in += uso.get("prompt_tokens", 0)
            c_out += uso.get("completion_tokens", 0)
            txt = txt.strip().strip('"').strip()
            if not txt:
                st2[f"🔴 erro da API: {str(uso.get('erro', '?'))[:34]}"] += 1
                continue
            ok, motivo = julgar(txt, dados, intencao)
            if not ok:
                st2[f"🔴 REPROVADO — {motivo.split(chr(39))[0].strip()}"] += 1
                continue
            comp = resposta(intencao, dados)
            if any(p in nz(comp) for p in PROIBIDAS):     # nunca deve disparar, mas e' barato
                st2["🔴 REPROVADO — resposta promete prazo proibido"] += 1
                continue
            st2["aceito"] += 1
            saida.append({
                "kind": "atendimento",
                "prompt": [{"role": "system", "content": rnd.choice(cats)},
                           {"role": "user",
                            "content": PEDIDO.format(politica=POLITICA, mensagem=txt)}],
                "completion": [{"role": "assistant", "content": comp}],
            })
            if feitos % 150 == 0 or feitos == len(alvos):
                print(f"  {feitos}/{len(alvos)} · {(time.time() - t0) / 60:.1f} min · "
                      f"aceitos {st2['aceito']}", flush=True)

    p = PROC / f"atendimento_util_{len(saida)}.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida), encoding="utf-8")
    print(f"{NL}{p.name}: {len(saida)} exemplos")
    for kk, v in st2.most_common():
        print(f"  {kk:46} {v}")
    print(f"  custo real: US$ {c_in / 1e6 * 0.27 + c_out / 1e6 * 1.10:.3f}")
    if saida:
        print(f"  intencoes: {dict(Counter(json.loads(x['completion'][0]['content'].split(NL)[0])['intencao'] for x in saida))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
