"""Gabaritos do avaliador de resumo. RODAR ANTES DE CARREGAR QUALQUER MODELO.

🔴 O QUE ESTE ARQUIVO DEFENDE

Um avaliador de resumo tem duas maneiras de estar quebrado, e elas não são simétricas:

  · **frouxo demais** — dá nota alta para lixo. O sintoma é um número bom, e número bom não
    desperta desconfiança em ninguém. É a falha perigosa.
  · **rígido demais** — reprova resumo correto escrito com outras palavras. O sintoma é um
    número baixo, que costuma ser lido como "o modelo é ruim" e vira teoria sobre dado,
    arquitetura e escala — em cima de um artefato do aparato.

Os dois já aconteceram neste projeto. Por isso a suíte tem as duas metades:

  ⭐ **ESTRATÉGIAS DEGENERADAS que precisam FALHAR** — copiar a fonte inteira, devolver
     nada, trocar um número, inventar um nome, cortar metade dos fatos. Se qualquer uma
     passar, a métrica tem porta dos fundos e o número que ela produz não significa nada.

  ⭐ **PARÁFRASES LEGÍTIMAS que precisam PASSAR** — mudar a magnitude ('R$ 2.500.000' →
     'R$ 2,5 milhões'), acrescentar preâmbulo, encurtar o nome de uma instituição. Se
     qualquer uma falhar, o avaliador está punindo a competência que deveria premiar.

  ⭐ **PROVA DE QUE O DETECTOR DISPARA** — injetar uma entidade falsa nos 150 resumos de
     referência e exigir que os 150 reprovem. Um detector que nunca acusa nada passa em todo
     teste positivo e não mede coisa alguma; é assim que um avaliador quebrado se parece:
     tudo verde, nada medido.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resumo_pt_verificadores import (avaliar_resumo, entidades_inventadas,  # noqa: E402
                                     extrair_numeros, numeros_inventados)

DADOS = Path(__file__).resolve().parent / "benchmarks" / "resumo_pt.jsonl"


def carregar() -> list[dict]:
    return [json.loads(l) for l in DADOS.read_text(encoding="utf-8").split(chr(10)) if l.strip()]


# ---------------------------------------------------------------- unidades isoladas
# (descricao, resumo, fonte, esperado_de_numeros_inventados)
CASOS_NUMERO: list[tuple[str, str, str, list[float]]] = [
    ("magnitude por extenso == magnitude por algarismo",
     "custou R$ 2,5 milhões", "o valor foi de R$ 2.500.000", []),
    ("e o inverso tambem",
     "custou R$ 2.500.000", "o valor foi de R$ 2,5 milhões", []),
    ("'3 mil' == '3.000'", "foram 3 mil pessoas", "compareceram 3.000 pessoas", []),
    # 🔴 EM PT O PONTO E' MILHAR: ler '1.500' como 1,5 e' o erro classico de codigo portado
    ("ponto e' separador de milhar", "foram 1.500 alunos", "matriculou 1.500 alunos", []),
    ("virgula e' decimal", "a taxa e de 2,5%", "a taxa ficou em 2,5%", []),
    ("arredondamento honesto nao e' invencao",
     "cerca de 2,5 milhões", "o total foi de R$ 2.470.000", []),
    ("invencao de ordem de grandeza", "custou R$ 9,9 milhões", "o valor foi R$ 2.500.000",
     [9_900_000.0]),
    ("troca sutil de digito", "foram 2.700 alunos", "foram 2.500 alunos", [2700.0]),
]

CASOS_ENTIDADE: list[tuple[str, str, str, bool]] = [
    ("nome encurtado NAO e' invencao",
     "A Prefeitura de Sorocaba investe.", "A Prefeitura Municipal de Sorocaba anunciou.", False),
    ("nome novo E' invencao",
     "A Fundação Getúlio participa.", "A Prefeitura Municipal de Sorocaba anunciou.", True),
    ("palavra capitalizada no inicio da frase nao vira entidade",
     "Obras seguem no prazo.", "A prefeitura informou que as obras seguem no prazo.", False),
]


def testar_unidades() -> list[str]:
    falhas = []
    print("-- numeros")
    for desc, res, fonte, esp in CASOS_NUMERO:
        got = numeros_inventados(res, fonte)
        ok = got == esp
        print(f"  {'✅' if ok else '🔴'} {desc}")
        if not ok:
            falhas.append(f"numero · {desc}: esperado {esp}, obtido {got}")
    print("-- entidades")
    for desc, res, fonte, esp_tem in CASOS_ENTIDADE:
        got = entidades_inventadas(res, fonte)
        ok = bool(got) == esp_tem
        print(f"  {'✅' if ok else '🔴'} {desc}")
        if not ok:
            falhas.append(f"entidade · {desc}: esperado {'alguma' if esp_tem else 'nenhuma'}, "
                          f"obtido {got}")
    return falhas


# ---------------------------------------------------------------- item completo

N_DEGENERADAS = 7
N_LEGITIMAS = 2


def testar_itens(itens: list[dict]) -> list[str]:
    falhas = []

    # 1) a referencia passa em 100% — prova que TODO item e' resolvivel
    maus = [it["id"] for it in itens if not avaliar_resumo(it["resumo_referencia"], it)["ok"]]
    print(f"\n-- referencia: {len(itens) - len(maus)}/{len(itens)} passam")
    if maus:
        falhas.append(f"referencia falha em {len(maus)} item(ns): {maus[:6]} — "
                      f"item irresolvivel mede o azar do modelo, nao a capacidade")

    # 2) 🔴 ESTRATEGIAS DEGENERADAS: precisam falhar em TODOS os itens
    degeneradas = {
        "copiar a fonte inteira": lambda it: it["fonte"],
        "devolver vazio": lambda it: "",
        "devolver uma palavra": lambda it: "Resumo.",
        "trocar um numero": lambda it: it["resumo_referencia"].replace(
            str(int(sorted(extrair_numeros(it["resumo_referencia"]))[-1])), "987654321", 1)
            + " 987654321",
        "inventar uma instituicao": lambda it: it["resumo_referencia"]
            + " O aporte veio da Fundação Bradesco Ipiranga.",
        # ⚠️ A PRIMEIRA VERSAO DESTE CASO CORTAVA METADE DAS FRASES e passava em 62/150 —
        #    e o defeito era do CASO, nao do avaliador: nesta escrita (piramide invertida,
        #    igual a de jornal) a frase de abertura ja' carrega a maior parte dos fatos.
        #    Cortar frase nao e' cortar fato. A versao correta monta o resumo A PARTIR da
        #    metade da lista de fatos, e ai' a cobertura cai abaixo do minimo por construcao.
        "carregar so' metade dos fatos": lambda it: "Resumo: " + ", ".join(
            str(f["valor"]) for f in it["fatos_essenciais"][:len(it["fatos_essenciais"]) // 2]),
        # numeros sem texto em volta: fiel, curto, e inutil
        "despejar so' os numeros": lambda it: "Numeros: " + ", ".join(
            str(f["valor"]) for f in it["fatos_essenciais"] if f["tipo"] == "numero"),
    }
    for nome, fn in degeneradas.items():
        passaram = [it["id"] for it in itens if avaliar_resumo(fn(it), it)["ok"]]
        ok = not passaram
        print(f"  {'✅' if ok else '🔴'} '{nome}' reprova em {len(itens) - len(passaram)}"
              f"/{len(itens)}")
        if not ok:
            falhas.append(f"DEGENERADA '{nome}' PASSOU em {len(passaram)} item(ns): "
                          f"{passaram[:6]} — a metrica tem porta dos fundos")

    # 3) ⭐ PARAFRASES LEGITIMAS: precisam passar em TODOS
    legitimas = {
        "preambulo de cortesia": lambda it: "Claro, segue o resumo:\n" + it["resumo_referencia"],
        "marcador de lista": lambda it: "- " + it["resumo_referencia"],
    }
    for nome, fn in legitimas.items():
        maus2 = [(it["id"], avaliar_resumo(fn(it), it)) for it in itens
                 if not avaliar_resumo(fn(it), it)["ok"]]
        ok = not maus2
        print(f"  {'✅' if ok else '🔴'} '{nome}' passa em {len(itens) - len(maus2)}"
              f"/{len(itens)}")
        if not ok:
            id_, r = maus2[0]
            falhas.append(f"LEGITIMA '{nome}' REPROVOU em {len(maus2)} item(ns) (ex.: {id_} "
                          f"{[k for k, v in r['condicoes'].items() if not v]}) — o avaliador "
                          f"esta punindo parafrase correta")
    # 4) ⭐ CONTROLE TRIVIAL — nao e' falha, e' o PISO contra o qual o modelo sera lido.
    #    Copiar as duas primeiras frases da fonte nao exige modelo nenhum. Se o Bee nao
    #    passar disto, "sabe resumir" e' frase sem lastro. Reportar os dois lados e' a
    #    licao do verifier.py, cujo ganho aparente escondia saldo -4.
    lead = [avaliar_resumo(". ".join(it["fonte"].split(". ")[:2]) + ".", it) for it in itens]
    n_lead = sum(r["ok"] for r in lead)
    print("")
    print(f"-- controle: LEAD-2 (copiar as 2 primeiras frases da fonte) passa em "
          f"{n_lead}/{len(itens)} = {100 * n_lead / len(itens):.1f}%")
    print("   ⚠️ este e' o PISO. Modelo abaixo disto nao demonstrou capacidade nenhuma.")
    return falhas


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 78)
    print("GABARITOS DO AVALIADOR DE RESUMO PT")
    print("=" * 78)
    if not DADOS.exists():
        print(f"🔴 {DADOS.name} nao existe. Rode comeia/eval/gerar_resumo_pt.py.",
              file=sys.stderr)
        return 1
    itens = carregar()
    falhas = testar_unidades() + testar_itens(itens)

    print("\n" + "=" * 78)
    if falhas:
        print(f"🔴 {len(falhas)} FALHA(S) — o defeito e' do AVALIADOR, nao do modelo")
        for f in falhas:
            print(f"   · {f}")
        print("\nABORTADO. Corrija antes de medir qualquer modelo.")
        return 1
    print(f"✅ {len(CASOS_NUMERO) + len(CASOS_ENTIDADE)} casos unitarios · {len(itens)} itens · "
          f"{N_DEGENERADAS} estrategias degeneradas reprovadas · "
          f"{N_LEGITIMAS} parafrases legitimas aprovadas")
    print("   A regua esta calibrada. Pode carregar modelo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
