"""Prova que TODO prompt do IFEval-PT é satisfazível — antes de carregar qualquer modelo.

🔴 O QUE ESTE ARQUIVO EVITA, EM NÚMEROS

Este projeto mediu **23,5%** de execução agêntica quando a taxa real era **57,6%**. A causa:
**35 de 85** referências do avaliador eram impossíveis de satisfazer por construção. O modelo
estava certo; a régua estava quebrada, e ninguém tinha testado a régua.

Num benchmark de instrução o risco é ainda maior, porque as instruções se **combinam**:
"responda em JSON" + "não use vírgulas" é impossível para qualquer JSON de mais de um campo,
e "escreva em MAIÚSCULAS" + "comece com a palavra Claro" é impossível porque `Claro != CLARO`.
Cada item impossível puxa a nota do modelo para baixo sem medir nada dele.

⭐ COMO A PROVA FUNCIONA — SATISFAÇÃO POR CONSTRUÇÃO

Para cada item, um **solucionador** monta uma resposta que tenta obedecer todas as
instruções, e essa resposta é submetida aos MESMOS verificadores que julgarão o modelo.

  · solucionador conseguiu → o item é satisfazível. Prova positiva, não opinião.
  · solucionador falhou    → ou o item é impossível, ou o solucionador é fraco. Nos dois
                             casos o item é REPORTADO para inspeção, nunca aceito calado.

⚠️ O solucionador é deliberadamente burro: ele escreve texto de enchimento, não texto bom.
Isso é proposital — se um gerador burro satisfaz as restrições, elas são satisfazíveis, e é
só isso que precisa ser provado aqui. Qualidade não é assunto deste arquivo.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifeval_pt_verificadores import contar_palavras, verificar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DADOS = ROOT / "comeia" / "eval" / "benchmarks" / "ifeval_pt.jsonl"

# Frases de enchimento sem virgula, sem algarismo e sem as palavras que costumam ser
# proibidas — assim a mesma base serve para quase todas as combinacoes.
BASE = ("O assunto pedido merece atencao e cuidado no dia a dia das pessoas "
        "que precisam resolver questoes praticas com clareza e paciencia")


def sintetizar(instrucoes: list[dict], alvo_palavras: int | None = None) -> str:
    """Monta uma resposta que tenta satisfazer todas as instruções do item.

    ⚠️ A PRIMEIRA VERSAO DESTA FUNCAO ESCOLHIA UMA estrutura com `elif` e ignorava as
    demais: com "duas respostas" + "lista de marcadores" ela produzia só a lista, e o item
    aparecia como insatisfazivel quando na verdade e' satisfazivel ("- a\\n- b ****** - c").
    Isso importa porque um solucionador fraco e um item impossivel se parecem — os dois dao
    "nao consegui" — e confundir os dois levaria a CORTAR do benchmark itens legitimos.
    Agora as estruturas se COMPOEM, e `resolver()` itera ajustando o comprimento.
    """
    ins = {i["tipo"]: i for i in instrucoes}

    # ---- corpo base, respeitando proibicoes de conteudo antes de tudo
    palavras = BASE.split()
    proibidas = []
    if "nao_contem" in ins:
        p = ins["nao_contem"].get("palavras", [])
        proibidas = [p] if isinstance(p, str) else list(p)
    palavras = [w for w in palavras if w.lower() not in {x.lower() for x in proibidas}]

    # ---- palavra obrigatoria
    obrig = ""
    if "contem_palavra" in ins:
        w, v = ins["contem_palavra"]["palavra"], int(ins["contem_palavra"].get("vezes", 1))
        obrig = " ".join([w] * v) + " "

    def texto_com(n_palavras_alvo: int) -> str:
        """Repete a base ate atingir o numero de palavras pedido."""
        saida = obrig.split()
        while len(saida) < n_palavras_alvo:
            saida += palavras
        return " ".join(saida[:max(n_palavras_alvo, len(obrig.split()))])

    # ---- quantos vamos escrever
    alvo = 40
    if "n_palavras" in ins:
        mn = ins["n_palavras"].get("minimo")
        mx = ins["n_palavras"].get("maximo")
        if mn is not None:
            alvo = int(mn) + 5
        if mx is not None:
            alvo = min(alvo, int(mx)) if mn is not None else max(3, int(mx) - 3)

    if alvo_palavras is not None:
        alvo = alvo_palavras

    # ---- ESTRUTURAS QUE SE COMPOEM (nada de elif: um item pode pedir varias de uma vez)
    def bloco(n_pal: int, prefixo: str = "") -> str:
        """Um pedaco de texto com aproximadamente n_pal palavras."""
        ws = (prefixo + " " if prefixo else "").split() if prefixo else []
        while len(ws) < max(1, n_pal):
            ws += palavras
        return " ".join(ws[:max(1, n_pal)])

    def unidade(n_pal: int, primeiro: bool) -> str:
        """Uma 'resposta' completa: pode ser lista, paragrafos, frases ou texto corrido."""
        pre = obrig.strip() if (primeiro and obrig) else ""
        if "n_marcadores" in ins:
            n = int(ins["n_marcadores"].get("exato") or ins["n_marcadores"].get("minimo") or 3)
            por = max(3, n_pal // n)
            linhas = [f"- {bloco(por, pre if i == 0 else '')}" for i in range(n)]
            return "\n".join(linhas)
        if "n_paragrafos" in ins:
            n = int(ins["n_paragrafos"].get("exato") or ins["n_paragrafos"].get("minimo") or 2)
            por = max(2, n_pal // n)
            return "\n\n".join(bloco(por, pre if i == 0 else "") for i in range(n))
        if "n_frases" in ins:
            n = int(ins["n_frases"].get("exato") or ins["n_frases"].get("minimo") or 3)
            # ⚠️ "termine com a frase X" CONSOME uma das frases pedidas — gerar n e depois
            #    somar a final daria n+1 e reprovaria um item que e' satisfazivel.
            if "termina_com" in ins:
                n = max(1, n - 1)
            por = max(2, n_pal // max(1, n))
            return " ".join(bloco(por, pre if i == 0 else "") + "." for i in range(n))
        return bloco(n_pal, pre)

    # ⚠️ JSON e' EXCLUSIVO: nao se combina com lista/paragrafos/frases (o gerador ja recusa
    #    essas combinacoes). Mas ele NAO pode dar return antecipado — a primeira versao
    #    retornava aqui e pulava `tudo_minusculo`, fazendo item satisfazivel parecer
    #    impossivel so' porque a chave "resposta" tinha ficado fora da transformacao final.
    if "e_json_valido" in ins:
        corpo = json.dumps({"resposta": bloco(alvo, obrig.strip())}, ensure_ascii=False)
    elif "duas_respostas" in ins:
        metade = max(4, alvo // 2)
        corpo = f"{unidade(metade, True)} ****** {unidade(metade, False)}"
    else:
        corpo = unidade(alvo, True)

    # ---- bordas
    if "comeca_com" in ins:
        # ⚠️ separador de LINHA, nao espaco: com "lista de marcadores" um espaco deixaria
        #    "Claro - item" na mesma linha e o regex `^\s*[-*]` nao casaria — o item pareceria
        #    impossivel quando basta a palavra numa linha e a lista na seguinte.
        sep = "\n" if ("n_marcadores" in ins or "n_paragrafos" in ins) else " "
        corpo = f"{ins['comeca_com']['texto']}{sep}{corpo}"
    if "tem_titulo_markdown" in ins:
        n = int(ins["tem_titulo_markdown"].get("nivel") or 1)
        corpo = f"{'#' * n} Titulo\n\n{corpo}"
    if "termina_com" in ins:
        corpo = f"{corpo} {ins['termina_com']['texto']}"

    # ---- transformacoes finais (a ordem importa: caixa por ultimo)
    if "sem_virgula" in ins:
        corpo = corpo.replace(",", "")
    if "sem_numeros" in ins:
        corpo = "".join(c for c in corpo if not c.isdigit())
    if "envolvido_em_aspas" in ins:
        corpo = f'"{corpo}"'
    if "tudo_maiusculo" in ins:
        corpo = corpo.upper()
    if "tudo_minusculo" in ins:
        corpo = corpo.lower()
    return corpo


def resolver(instrucoes: list[dict], tentativas: int = 60) -> tuple[str, bool]:
    """Procura um comprimento que satisfaça todas as instruções. Devolve (resposta, achou).

    ⭐ POR QUE BUSCAR EM VEZ DE CALCULAR: as restrições interagem de formas que não fecham
    em fórmula. "Termine com esta frase" soma palavras depois que o corpo já foi montado;
    "não use algarismos" remove caracteres e pode remover palavras inteiras; "entre aspas"
    muda o começo. Calcular o comprimento exato exigiria modelar cada interação — buscar
    sobre uma faixa de comprimentos custa microssegundos e não tem esse acoplamento.

    ⚠️ Isto NÃO relaxa a exigência: a resposta candidata é submetida aos mesmos
    verificadores que julgarão o modelo. Buscar o comprimento é como um humano faria ao
    obedecer "escreva mais de 150 palavras" — escreve, conta, ajusta.
    """
    ins = {i["tipo"]: i for i in instrucoes}
    mn = ins.get("n_palavras", {}).get("minimo")
    mx = ins.get("n_palavras", {}).get("maximo")
    if mn is not None and mx is not None:
        faixa = range(int(mn), int(mx) + 1)
    elif mn is not None:
        faixa = range(int(mn), int(mn) * 3 + 40)
    elif mx is not None:
        faixa = range(max(1, int(mx) // 4), int(mx) + 1)
    else:
        faixa = range(8, 260)

    candidatos = list(faixa)[:tentativas] or [40]
    for alvo in candidatos:
        r = sintetizar(instrucoes, alvo_palavras=alvo)
        ok, _ = verificar(r, instrucoes)
        if ok:
            return r, True
    # último recurso: sem alvo explícito
    r = sintetizar(instrucoes)
    ok, _ = verificar(r, instrucoes)
    return r, ok


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", type=Path, default=DADOS)
    ap.add_argument("--mostrar", type=int, default=6, help="quantos insatisfeitos detalhar")
    a = ap.parse_args()

    if not a.dados.exists():
        print(f"🔴 ABORTA: {a.dados} nao existe.", file=sys.stderr)
        return 1

    itens = [json.loads(l) for l in a.dados.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("=" * 78)
    print("VALIDACAO DO IFEval-PT — todo prompt tem de ser SATISFAZIVEL")
    print("=" * 78)
    print(f"  {len(itens)} prompts · {sum(i['n_instrucoes'] for i in itens)} instrucoes\n")

    insatisfeitos, por_tipo_falha = [], Counter()
    for it in itens:
        resp, ok = resolver(it["instrucoes"])
        _, det = verificar(resp, it["instrucoes"])
        if not ok:
            insatisfeitos.append((it, resp, det))
            for d in det:
                if not d["ok"]:
                    por_tipo_falha[d["tipo"]] += 1

    n_ok = len(itens) - len(insatisfeitos)
    print(f"  satisfazíveis por construcao: {n_ok}/{len(itens)} = {100*n_ok/len(itens):.1f}%")

    if insatisfeitos:
        print(f"\n🔴 {len(insatisfeitos)} PROMPT(S) QUE O SOLUCIONADOR NAO CONSEGUIU SATISFAZER")
        print("   Ou o item e' impossivel (e contamina a medicao), ou o solucionador e'")
        print("   fraco. Nos dois casos: INSPECIONAR, nunca aceitar calado.\n")
        print("   instrucoes que mais falharam:")
        for t, c in por_tipo_falha.most_common():
            print(f"     {t:32} {c:>4}")
        print(f"\n   primeiros {a.mostrar} casos:")
        for it, resp, det in insatisfeitos[:a.mostrar]:
            ruins = [d["tipo"] for d in det if not d["ok"]]
            print(f"\n   [{it['id']}] falhou em: {ruins}")
            print(f"     prompt : {it['prompt'][:100]}")
            print(f"     tentou : {resp[:100]!r}")
        print("\nABORTADO — corrigir antes de medir qualquer modelo.")
        return 1

    print("\n" + "=" * 78)
    print("✅ TODOS OS PROMPTS SAO SATISFAZIVEIS. A regua nao tem item impossivel.")
    print("   Pode carregar modelo.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
