"""Negativos agênticos por *function masking* — determinístico, US$ 0, e com o difícil no meio.

🔴 O PROBLEMA QUE ISTO RESOLVE

O gigaverbo convertido tem **40.634 positivos contra 82 negativos — 495:1**. O E2 mediu
`over-calling` em **13,8%** (era 0% no baseline apenas porque o modelo não chamava nada), e o
projeto já mediu que deslocar a proporção positivo/negativo move o over-calling: quando a
fatia de tool subiu de 59,3% para 75,8%, o over-calling subiu **+7,6 pp**. Treinar com 495:1
faria isso explodir, e a regressão só apareceria depois de gastar GPU.

⭐ A RECEITA (Hammer, arXiv:2410.04587): pegar um diálogo cuja resposta certa **era** chamar a
ferramenta `t`, **remover `t` do catálogo**, e manter o pedido do usuário. A resposta certa
passa a ser **não chamar nada**. Custo zero, verificável por construção.

⚠️ **E é aqui que a receita pode ficar inútil ou virar veneno.** A qualidade do negativo está
inteira na escolha dos distratores:

- **Distratores aleatórios** dão negativo fácil: o catálogo fica com ferramentas de outro
  mundo e o modelo aprende "assunto diferente = não chamo". Não ataca o over-calling real.
- **Distratores parecidos demais** dão negativo **errado**: removido `get_weather`, se sobrar
  `get_forecast` no catálogo, chamar passa a ser a resposta CERTA e o rótulo mente. Dado com
  rótulo invertido é pior que dado ausente.

A regra usada aqui fica no meio: **mesmo domínio, objeto diferente**. Os distratores vêm de
diálogos vizinhos, e é excluído qualquer um que compartilhe com a ferramenta removida um token
que **não seja verbo genérico** (get/send/create/list…). Removido `send_email`, entram
`create_contact` e `add_calendar_event` — mesmo mundo, nenhum envia e-mail; ficam de fora
`read_email` e `forward_email`, que dividem o objeto e tornariam o rótulo duvidoso.

⚠️ A resposta do assistente NÃO é preenchida aqui. Sai como `None`, para o passo seguinte
gerar recusas variadas com um teacher. Preencher com template faria a métrica `over_call`
melhorar enquanto o modelo decora uma frase — bom número, comportamento degenerado.

Uso:
    python comeia/data/gerar_negativos_masking.py --n 200 --amostra
    python comeia/data/gerar_negativos_masking.py --n 10000 --escrever
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 🔴 NAO USE splitlines() PARA LER JSONL. `json.dumps` NAO escapa U+2028 (LINE
#    SEPARATOR) nem U+2029 (PARAGRAPH SEPARATOR) — sao legais dentro de string JSON —
#    mas `str.splitlines()` do Python os trata como quebra de linha e PARTE o registro
#    ao meio. Medido: 2 ocorrencias em 35.528 registros de codigo bastaram para
#    35.528 virarem 35.530 fragmentos, dois deles JSON invalido. Aqui deu erro alto;
#    com um try/except em volta teria virado registro descartado em silencio.
#    `split(chr(10))` e a iteracao do proprio arquivo quebram SO em quebra de linha de verdade.

RAIZ = Path(__file__).resolve().parent.parent.parent
ENTRADA = RAIZ / "comeia" / "data" / "processed" / "gigaverbo_ferramenta.jsonl"
SAIDA = RAIZ / "comeia" / "data" / "processed" / "negativos_masking.jsonl"

# verbos genericos: compartilha-los NAO torna duas ferramentas intercambiaveis
VERBOS = {"get", "set", "add", "create", "send", "list", "read", "write", "update",
          "delete", "remove", "search", "find", "calculate", "calc", "generate", "gen",
          "convert", "check", "fetch", "make", "new", "run", "execute", "post", "put",
          "do", "start", "stop", "play", "open", "close", "book", "order", "obter",
          "criar", "enviar", "listar", "buscar", "calcular", "gerar", "converter"}

CABECALHO = ("Você é um assistente AGÊNTICO. Você tem acesso às ferramentas abaixo.\n\n"
             "FERRAMENTAS DISPONÍVEIS:\n")
RODAPE = ("\nResponda com UM objeto JSON: "
          '{"tool": "<nome>", "args": {...}}. '
          "Se nenhuma ferramenta servir, responda em texto normal.\n")

RX_FERR = re.compile(r"^- ([a-zA-Z0-9_]+):", re.M)
RX_PALAVRA = re.compile(r"[a-zà-ÿ0-9]{4,}", re.I)
# palavras que aparecem em quase todo pedido e nao indicam dominio nenhum
VAZIAS = {"para", "voce", "você", "pode", "preciso", "quero", "gostaria", "favor", "sobre",
          "como", "qual", "quais", "meu", "minha", "esse", "essa", "isso", "tenho", "estou",
          "fazer", "poderia", "ajudar", "obrigado", "seria", "quanto", "muito", "mais"}


def palavras(texto: str) -> set[str]:
    return {w.lower() for w in RX_PALAVRA.findall(texto)} - VAZIAS


def nucleo(nome: str) -> set[str]:
    """Tokens do nome que NÃO são verbo genérico — o 'objeto' sobre o que a ferramenta age.

    🔴 SEPARA camelCase. A primeira versão cortava só em `_` e `-`, então `generateQRCode`
    virava UM token e não cruzava com `{qr, code}` de `generate_qr_code`. Resultado medido:
    o negativo saiu com a ferramenta removida **presente no catálogo sob outro nome**, e o
    rótulo "não chamar" virou mentira.
    """
    bruto = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", nome)      # generateQRCode -> generate QRCode
    bruto = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", bruto)   # QRCode -> QR Code
    return {t for t in re.split(r"[\s_\-]+", bruto.lower()) if t and t not in VERBOS}


def equivalentes(desc_a: str, desc_b: str) -> bool:
    """Duas ferramentas fazem a MESMA coisa? Decidido pela descrição, não pelo nome.

    🔴 Separar camelCase não basta. `calculate_bmi` e `calculate_body_mass_index` não
    compartilham token nenhum, e são a mesma função — o negativo saiu com as duas e o rótulo
    mentia. Sigla contra nome por extenso é invisível para comparação de nome.

    ⚠️ A descrição resolve porque as duas dizem "índice de massa corporal". O limiar é por
    **fração da menor descrição**, não por contagem absoluta: descrição curta com 3 palavras
    em comum já é o mesmo serviço, enquanto descrição longa divide 3 palavras por acaso.
    """
    a, b = palavras(desc_a), palavras(desc_b)
    if not a or not b:
        return False
    comum = len(a & b)
    return comum / min(len(a), len(b)) >= 0.5 and comum >= 2


def blocos_do_catalogo(system: str) -> dict[str, str]:
    """Reparte o catálogo em prosa de volta em {nome: bloco de texto}, preservando o texto.

    ⚠️ Reconstruir a descrição a partir do nome seria inventar; aqui o bloco original é
    recortado e recolado, então o negativo carrega exatamente a mesma prosa que o positivo.
    """
    corpo = system.split("FERRAMENTAS DISPONÍVEIS:\n", 1)[-1]
    corpo = corpo.split("\nResponda com UM objeto JSON", 1)[0]
    fora, atual, nome = {}, [], None
    for linha in corpo.splitlines(True):
        m = re.match(r"^- ([a-zA-Z0-9_]+):", linha)
        if m:
            if nome:
                fora[nome] = "".join(atual)
            nome, atual = m.group(1), [linha]
        elif nome:
            atual.append(linha)
    if nome:
        fora[nome] = "".join(atual)
    return fora


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ENTRADA)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--distratores", type=int, default=6,
                    help="tamanho do catalogo do negativo (o avaliador do Bee usa 10)")
    ap.add_argument("--semente", type=int, default=20260820)
    ap.add_argument("--amostra", action="store_true", help="imprime 3 negativos e sai")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args()

    rnd = random.Random(a.semente)
    print("=" * 78)
    print("NEGATIVOS POR FUNCTION MASKING — mesmo dominio, objeto diferente")
    print("=" * 78)

    dialogos = []
    catalogo_global: dict[str, str] = {}
    for linha in a.entrada.read_text(encoding="utf-8").split(chr(10)):
        if not linha.strip():
            continue
        d = json.loads(linha)
        if d.get("kind") != "tool_call":
            continue
        msgs = d["messages"]
        sistema = msgs[0]["content"]
        chamada = next((m for m in msgs if m["role"] == "assistant"
                        and m["content"].startswith('{"tool"')), None)
        usuario = next((m for m in msgs if m["role"] == "user"), None)
        if not chamada or not usuario:
            continue
        alvo = json.loads(chamada["content"])["tool"]
        blocos = blocos_do_catalogo(sistema)
        if alvo not in blocos:
            continue
        catalogo_global.update(blocos)
        dialogos.append({"alvo": alvo, "usuario": usuario["content"],
                         "blocos": blocos, "score": d.get("instruct_score")})
    print(f"positivos lidos      : {len(dialogos):,}")
    print(f"ferramentas distintas: {len(catalogo_global):,}")

    # indice por nucleo, para achar distratores do MESMO mundo sem o MESMO objeto
    por_nucleo: dict[str, list[str]] = defaultdict(list)
    for nome in catalogo_global:
        for t in nucleo(nome):
            por_nucleo[t].append(nome)

    todos = sorted(catalogo_global)
    # vocabulario de cada ferramenta = nome + descricao + nomes dos argumentos
    pal_ferramenta = {n: palavras(catalogo_global[n].replace("_", " ")) for n in todos}
    # 🔴 AMOSTRAGEM COM REPOSICAO — o mesmo erro da §2 das licoes, em lugar novo.
    #    `rnd.choice(dialogos)` a cada iteracao produziu, em 10.000 negativos, apenas 3.126
    #    pares (pedido, ferramenta removida) DISTINTOS: 68,7% de duplicacao, com um par
    #    repetindo 292 vezes. Treinar assim ensina a decorar aquele pedido, nao o
    #    comportamento — e cai direto na §2c-6 (repeticao interna do corpus, com dano maximo
    #    justamente em contagem intermediaria).
    #    ⭐ Correto: percorrer a lista PERMUTADA uma vez, e recusar par ja' usado.
    ordem = list(range(len(dialogos)))
    rnd.shuffle(ordem)
    vistos: set[tuple[str, str]] = set()
    fora, motivos = [], Counter()
    tentativas = 0
    for idx in ordem:
        if len(fora) >= a.n:
            break
        tentativas += 1
        d = dialogos[idx]
        par = (d["usuario"], d["alvo"])
        if par in vistos:
            motivos["par_repetido"] += 1
            continue
        vistos.add(par)
        alvo, nuc_alvo = d["alvo"], nucleo(d["alvo"])
        if not nuc_alvo:
            motivos["alvo_so_com_verbo_generico"] += 1
            continue

        # 🔴 candidatos: qualquer ferramenta que NAO divida objeto com a removida.
        #    Dividir objeto (read_email x send_email) e' o caso em que chamar poderia estar
        #    certo — e ai' o rotulo "nao chamar" seria MENTIRA. Melhor perder candidato que
        #    gravar rotulo invertido.
        desc_alvo = catalogo_global[alvo]
        candidatos = [n for n in todos
                      if n != alvo
                      and not (nucleo(n) & nuc_alvo)
                      and not equivalentes(desc_alvo, catalogo_global[n])]
        if len(candidatos) < a.distratores:
            motivos["sem_distratores_suficientes"] += 1
            continue

        # 🔴 DISTRATOR SORTEADO PRODUZ NEGATIVO INUTIL. Medido na primeira versao: removido
        #    `get_movie_details` com o usuario perguntando sobre um filme, o catalogo saia com
        #    `get_random_joke`, `validate_password`, `track_calories` — nada ali tenta o
        #    modelo, e ele aprende "assunto diferente = nao chamo". Isso nao ataca o
        #    over-calling, que na pratica vem do QUASE-ACERTO.
        #    Correto: distrator ATRAENTE — descricao que divide vocabulario com o pedido, sem
        #    dividir o objeto da ferramenta removida (que tornaria chamar legitimo).
        pal_pedido = palavras(d["usuario"])
        atracao = sorted(
            candidatos,
            key=lambda n: (-len(pal_pedido & pal_ferramenta[n]), rnd.random()))
        escolhidos = atracao[:a.distratores]
        rnd.shuffle(escolhidos)

        sistema = CABECALHO + "".join(catalogo_global[n] for n in escolhidos) + RODAPE
        # guarda final: a ferramenta removida NAO pode ter voltado pelo catalogo global
        if re.search(rf"^- {re.escape(alvo)}:", sistema, re.M):
            motivos["alvo_reapareceu_no_catalogo"] += 1
            continue
        fora.append({
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": d["usuario"]},
                         {"role": "assistant", "content": None}],
            "kind": "text",
            "source": "masking_gigaverbo",
            "ferramenta_removida": alvo,
            "catalogo": escolhidos,
            "instruct_score": d["score"],
        })
        motivos["gerado"] += 1

    print(f"\ntentativas: {tentativas:,}")
    for m, c in motivos.most_common():
        print(f"  {'✅' if m == 'gerado' else '  '} {m:34} {c:>8,}")

    # ⭐ DUREZA MEDIDA, nao suposta: sobreposicao lexical media entre o pedido e o catalogo
    #    escolhido, contra a de um catalogo sorteado. Se as duas empatarem, o filtro de
    #    atracao nao esta' fazendo nada e o conjunto voltou a ser facil.
    def sobrepos(pedido: str, nomes: list[str]) -> int:
        pp = palavras(pedido)
        return sum(len(pp & pal_ferramenta[n]) for n in nomes)

    dur = [sobrepos(r["messages"][1]["content"], r["catalogo"]) for r in fora]
    aleat = [sobrepos(r["messages"][1]["content"], rnd.sample(todos, a.distratores))
             for r in fora]
    m_dur = sum(dur) / max(1, len(dur))
    m_ale = sum(aleat) / max(1, len(aleat))
    print()
    print("dureza (sobreposicao lexical pedido x catalogo):")
    print(f"  escolhido por atracao : {m_dur:.2f}")
    print(f"  catalogo sorteado     : {m_ale:.2f}")
    if m_dur <= m_ale * 1.5:
        print("  🔴 o filtro de atracao NAO esta' separando — negativo continua facil")
    else:
        print(f"  ✅ {m_dur/max(0.01,m_ale):.1f}x mais atraente que o acaso")

    pares = {(r["messages"][1]["content"], r["ferramenta_removida"]) for r in fora}
    print(f"pares (pedido, removida) distintos: {len(pares):,} de {len(fora):,} "
          f"({100*len(pares)/max(1,len(fora)):.1f}%)")
    if len(pares) < len(fora):
        print("  🔴 ainda ha duplicata — a permutacao nao esta' cobrindo")

    usados = Counter(r["ferramenta_removida"] for r in fora)
    print(f"\nnegativos gerados    : {len(fora):,}")
    print(f"ferramentas removidas: {len(usados):,} distintas "
          f"(a mais frequente aparece {usados.most_common(1)[0][1] if usados else 0}x)")
    print("⚠️ a resposta do assistente sai como None de proposito — o proximo passo gera as")
    print("   recusas com teacher. Template daria bom `over_call` com frase decorada.")

    if a.amostra and fora:
        for r in fora[:2]:
            print("\n" + "=" * 74)
            print(f"REMOVIDA: {r['ferramenta_removida']}   catalogo: {r['catalogo']}")
            print("--- system (so' os nomes):",
                  RX_FERR.findall(r["messages"][0]["content"]))
            print("--- user:", r["messages"][1]["content"][:220])
    if a.escrever:
        a.saida.parent.mkdir(parents=True, exist_ok=True)
        with a.saida.open("w", encoding="utf-8") as f:
            for r in fora:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n✅ {a.saida} ({len(fora):,} registros, resposta PENDENTE)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
