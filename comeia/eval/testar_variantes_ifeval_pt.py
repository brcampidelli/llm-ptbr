"""Gabaritos da métrica FROUXA do IFEval-PT. Roda junto com os verificadores.

🔴 POR QUE ESTE ARQUIVO EXISTE, SEPARADO DOS VERIFICADORES

`testar_verificadores_ifeval_pt.py` prova que cada verificador mede o que promete. Não prova
nada sobre `variantes()` — a função que produz a métrica **frouxa**, e que é o único lugar do
avaliador com liberdade para INFLAR um resultado.

O risco é assimétrico e vale nomear: se um verificador estiver errado, o número sai errado
para os dois lados e alguém estranha. Se `variantes()` for generosa demais, o número sai
**melhor**, e resultado bom não desperta desconfiança em ninguém. Foi assim que este projeto
mediu 23,5% achando que media capacidade, e assim que quase publicou "não há cauda útil".

⭐ A propriedade que os casos abaixo defendem: **variante pode salvar EMBALAGEM, nunca
   CONTEÚDO.** Um texto que viola a instrução de verdade continua reprovado depois de todas
   as transformações. Se algum dia isso deixar de valer, o teste falha aqui — antes de virar
   um ponto percentual num relatório.

(A desigualdade frouxo ≥ estrito é garantida por construção, não por teste: `variantes()`
sempre inclui a própria resposta no conjunto.)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_ifeval_pt import avaliar_item, variantes  # noqa: E402

# (descricao, resposta, instrucoes, estrito_esperado, frouxo_esperado)
CASOS: list[tuple[str, str, list[dict], bool, bool]] = [
    ("preambulo de cortesia estraga so' o ESTRITO",
     "Claro, aqui esta:\nTEXTO TOTALMENTE MAIUSCULO",
     [{"tipo": "tudo_maiusculo"}], False, True),
    ("cerca de codigo em volta do JSON passa nos dois",
     '```json\n{"a": 1}\n```', [{"tipo": "e_json_valido"}], True, True),
    # 🔴 OS DOIS CASOS QUE IMPORTAM: violacao real sobrevive a toda variante
    ("violacao real NAO pode ser salva por variante",
     "uma duas tres quatro cinco", [{"tipo": "n_palavras", "maximo": 3}], False, False),
    ("violacao real com envelope tambem NAO",
     "Claro, aqui esta:\numa duas tres quatro cinco",
     [{"tipo": "n_palavras", "maximo": 3}], False, False),
    # ⭐ variante nao pode DERRUBAR quem ja' passava: o minimo so' e' atingido com o texto
    #    inteiro, e a variante enxuta ficaria abaixo dele
    ("texto que so' passa INTEIRO continua passando",
     "Claro, aqui esta:\numa duas tres quatro cinco seis",
     [{"tipo": "n_palavras", "minimo": 8}], True, True),
    ("resposta limpa passa nos dois",
     "uma duas tres", [{"tipo": "n_palavras", "maximo": 3}], True, True),
    ("saudacao curta em linha propria e' envelope",
     "Claro!\ntudo em caixa baixa aqui", [{"tipo": "tudo_minusculo"}], False, True),
    ("linha longa com dois-pontos NAO e' envelope (pode ser conteudo)",
     "A regra e a seguinte, e vale para todos os casos que envolvam pagamento a prazo: "
     "SEMPRE CONFERIR", [{"tipo": "tudo_maiusculo"}], False, False),
]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 78)
    print("GABARITOS DA METRICA FROUXA (variantes) DO IFEval-PT")
    print("=" * 78)

    falhas = []
    for desc, resp, ins, e_est, e_fro in CASOS:
        r = avaliar_item(resp, ins)
        est, fro = r["ok_estrito_prompt"], r["ok_frouxo_prompt"]
        if fro < est:                       # nunca pode acontecer: a resposta esta no conjunto
            falhas.append((desc, "frouxo < estrito — variantes() perdeu a propria resposta"))
        elif (est, fro) != (e_est, e_fro):
            falhas.append((desc, f"esperado estrito={e_est}/frouxo={e_fro}, "
                                 f"obtido estrito={est}/frouxo={fro}"))
        else:
            print(f"  ✅ estrito={str(est):5} frouxo={str(fro):5}  {desc}")

    print("\n" + "=" * 78)
    if falhas:
        print(f"🔴 {len(falhas)} CASO(S) FALHARAM — a metrica frouxa esta errada")
        for desc, motivo in falhas:
            print(f"   · {desc}\n     {motivo}")
        print("\nABORTADO. Uma variante generosa demais infla o numero e ninguem estranha.")
        return 1
    print(f"✅ {len(CASOS)} casos · variantes() salva embalagem, nunca conteudo")
    exemplo = variantes("Claro, aqui esta:\nTEXTO")
    print(f"   exemplo: {exemplo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
