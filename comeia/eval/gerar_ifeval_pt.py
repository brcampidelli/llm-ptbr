"""Gera o IFEval-PT — 541 prompts com instruções verificáveis por execução.

⭐ POR QUE GERAR E NÃO TRADUZIR

O IFEval original (arXiv:2311.07911) tem 541 prompts em inglês. A tentação é traduzi-los,
e ela está errada por duas razões:

1. **Várias instruções do original não têm sentido em português.** "Start every sentence
   with the letter Q", "your answer must contain the letter 'e' at least 10 times",
   "use only words that begin with 'p'" — traduzidas, viram exercícios de dificuldade
   completamente diferente, porque a distribuição de letras do PT não é a do inglês. Medir
   isso não diz nada sobre seguir instrução; diz sobre ortografia comparada.

2. **Traduzir prompt é fácil; traduzir o VERIFICADOR é onde se erra.** "No commas" num
   texto em português tem de aceitar "1,50". Se o prompt vem traduzido e o verificador não,
   o avaliador reprova resposta correta — e o número sai errado para baixo, que é o pior
   sentido do erro: parece que o modelo é ruim.

Então: as instruções são as **verificáveis em PT** (ver `ifeval_pt_verificadores.py`, cujos
gabaritos passam 100%), e os prompts são escritos em torno delas, com temas de contexto
brasileiro. Cada prompt nasce já com suas instruções em formato de máquina.

⚠️ O QUE ESTE BENCHMARK NÃO MEDE: se a resposta é BOA. Ele mede se a resposta OBEDECE.
Um modelo pode escrever besteira em 3 parágrafos exatos e pontuar 100%. É deliberado —
"seguir instrução" e "escrever bem" são capacidades distintas, e misturá-las num número só
é o que torna avaliação de geração de conteúdo tão fácil de fraudar. Qualidade se mede
noutro lugar, contra baseline declarado.

Determinístico: mesma semente → mesmo arquivo (confira pelo sha256 no fim).

Uso:
    python comeia/eval/gerar_ifeval_pt.py
    python comeia/eval/gerar_ifeval_pt.py --n 541 --semente 20260819
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SAIDA = ROOT / "comeia" / "eval" / "benchmarks" / "ifeval_pt.jsonl"

# ---------------------------------------------------------------------------- os temas
# Assuntos de pedido real, em contexto brasileiro. O tema NAO e' avaliado — ele existe
# para o prompt ser plausivel e para o modelo nao responder sempre sobre a mesma coisa.
TAREFAS = [
    ("escreva um e-mail para o síndico do prédio pedindo o conserto do portão", "email"),
    ("escreva uma mensagem de WhatsApp avisando os colegas sobre a reunião de amanhã", "msg"),
    ("explique o que é o PIX para uma pessoa idosa", "explicacao"),
    ("escreva um anúncio de venda de uma bicicleta usada", "anuncio"),
    ("faça um resumo do que é a Lei Geral de Proteção de Dados", "resumo"),
    ("escreva uma receita de brigadeiro", "receita"),
    ("descreva as vantagens de morar perto do trabalho", "opiniao"),
    ("escreva um convite para uma festa junina da escola", "convite"),
    ("explique como funciona o sistema de cotas nas universidades", "explicacao"),
    ("escreva uma reclamação sobre um produto que chegou quebrado", "reclamacao"),
    ("faça uma lista de itens para uma viagem de praia", "lista"),
    ("explique a diferença entre CLT e PJ", "explicacao"),
    ("escreva uma mensagem de agradecimento para um professor", "agradecimento"),
    ("descreva o clima da região Nordeste do Brasil", "descricao"),
    ("escreva um texto sobre a importância da reciclagem", "dissertacao"),
    ("explique como abrir uma conta em banco digital", "tutorial"),
    ("escreva uma sinopse de um filme brasileiro que você conheça", "sinopse"),
    ("faça um roteiro de estudos para o ENEM", "roteiro"),
    ("explique o que é inflação usando um exemplo do dia a dia", "explicacao"),
    ("escreva um pedido de desculpas por ter faltado a um compromisso", "desculpa"),
    ("descreva como preparar um café coado", "tutorial"),
    ("escreva sobre os benefícios de caminhar todos os dias", "dissertacao"),
    ("explique o que faz um desenvolvedor de software", "explicacao"),
    ("escreva um aviso de mudança de horário de funcionamento de uma loja", "aviso"),
    ("faça um resumo sobre a Amazônia", "resumo"),
    ("explique como funciona o transporte público da sua cidade", "explicacao"),
    ("escreva uma carta de apresentação para uma vaga de emprego", "carta"),
    ("descreva um prato típico da culinária mineira", "descricao"),
    ("explique por que é importante economizar água", "dissertacao"),
    ("escreva uma mensagem de aniversário para um amigo", "felicitacao"),
]

# ------------------------------------------------------------------- moldes de instrucao
# (texto que vai ao modelo, instrucao em formato de maquina). Toda instrucao aqui e'
# decidivel por programa — nada de "seja claro" ou "use bom portugues".
def moldes(rng: random.Random) -> list[tuple[str, dict]]:
    n_p = rng.choice([80, 100, 120, 150, 200])
    n_max = rng.choice([50, 60, 80, 100])
    n_par = rng.choice([2, 3, 4])
    n_fra = rng.choice([2, 3, 4, 5])
    n_mar = rng.choice([3, 4, 5])
    palavra = rng.choice(["Brasil", "importante", "cuidado", "atenção", "qualidade"])
    vezes = rng.choice([2, 3])
    proibida = rng.choice(["muito", "coisa", "legal"])
    fim = rng.choice(["Espero ter ajudado.", "Fico à disposição.", "Obrigado pela atenção."])
    inicio = rng.choice(["Claro", "Com certeza", "Vamos lá"])
    return [
        (f"Sua resposta deve ter mais de {n_p} palavras.",
         {"tipo": "n_palavras", "minimo": n_p}),
        (f"Sua resposta deve ter no máximo {n_max} palavras.",
         {"tipo": "n_palavras", "maximo": n_max}),
        (f"Escreva exatamente {n_par} parágrafos, separados por uma linha em branco.",
         {"tipo": "n_paragrafos", "exato": n_par}),
        (f"Escreva exatamente {n_fra} frases.",
         {"tipo": "n_frases", "exato": n_fra}),
        ("Não use nenhuma vírgula na sua resposta.",
         {"tipo": "sem_virgula"}),
        ("Escreva toda a resposta em letras MAIÚSCULAS.",
         {"tipo": "tudo_maiusculo"}),
        ("Escreva toda a resposta em letras minúsculas, sem nenhuma maiúscula.",
         {"tipo": "tudo_minusculo"}),
        ("Coloque a resposta inteira entre aspas duplas.",
         {"tipo": "envolvido_em_aspas"}),
        ("Responda em formato JSON válido.",
         {"tipo": "e_json_valido"}),
        (f"Use a palavra \"{palavra}\" pelo menos {vezes} vezes.",
         {"tipo": "contem_palavra", "palavra": palavra, "vezes": vezes}),
        (f"Não use a palavra \"{proibida}\" em nenhum momento.",
         {"tipo": "nao_contem", "palavras": [proibida]}),
        (f"Apresente a resposta como uma lista com pelo menos {n_mar} itens com marcadores.",
         {"tipo": "n_marcadores", "minimo": n_mar}),
        ("Comece a resposta com um título em markdown (usando #).",
         {"tipo": "tem_titulo_markdown"}),
        (f"Termine a resposta exatamente com a frase: {fim}",
         {"tipo": "termina_com", "texto": fim}),
        (f"Comece a resposta com a palavra \"{inicio}\".",
         {"tipo": "comeca_com", "texto": inicio}),
        ("Não use nenhum algarismo — escreva os números por extenso, se precisar.",
         {"tipo": "sem_numeros"}),
        ("Dê duas respostas diferentes, separadas por ******.",
         {"tipo": "duas_respostas"}),
        ("Nenhuma frase pode começar com a palavra \"Eu\".",
         {"tipo": "sem_palavra_proibida_inicio", "palavra": "Eu"}),
        ("Responda em português.",
         {"tipo": "idioma_portugues"}),
    ]


# 🔴 PARES INCOMPATIVEIS. Um prompt que pede duas coisas contraditorias e' IMPOSSIVEL de
#    satisfazer, e um item impossivel no holdout puxa a nota para baixo sem medir nada do
#    modelo. Foi exatamente assim que este projeto mediu 23,5% quando o real era 57,6%:
#    35 de 85 referencias do avaliador eram impossiveis por construcao.
INCOMPATIVEIS = [
    {"tudo_maiusculo", "tudo_minusculo"},
    {"e_json_valido", "sem_virgula"},          # JSON com 2+ campos exige virgula
    {"e_json_valido", "n_paragrafos"},         # JSON nao tem paragrafos
    {"e_json_valido", "tem_titulo_markdown"},
    {"e_json_valido", "n_marcadores"},
    {"e_json_valido", "envolvido_em_aspas"},
    {"e_json_valido", "duas_respostas"},
    {"e_json_valido", "n_frases"},
    {"e_json_valido", "termina_com"},
    {"e_json_valido", "comeca_com"},
    {"e_json_valido", "tudo_maiusculo"},
    # 🔴 AS DUAS ABAIXO FORAM DESCOBERTAS PELO VALIDADOR, nao previstas por mim.
    #    Sao impossiveis por uma razao sutil: "comece a resposta com a palavra X" e' medido
    #    no PRIMEIRO CARACTERE da resposta. Um titulo markdown poe "# " antes, e as aspas
    #    poem '"' antes — nos dois casos a resposta comeca com outra coisa, e nenhum texto
    #    satisfaz as duas instrucoes ao mesmo tempo. 13 itens do primeiro sorteio caiam aqui.
    {"comeca_com", "tem_titulo_markdown"},
    {"comeca_com", "envolvido_em_aspas"},
    {"envolvido_em_aspas", "tem_titulo_markdown"},
    {"envolvido_em_aspas", "n_marcadores"},
    {"envolvido_em_aspas", "duas_respostas"},
    {"envolvido_em_aspas", "termina_com"},
    {"n_marcadores", "n_frases"},              # itens de lista nao sao frases pontuadas
    {"n_marcadores", "n_paragrafos"},
    {"duas_respostas", "n_paragrafos"},
    {"duas_respostas", "n_frases"},
    {"duas_respostas", "termina_com"},
    {"tudo_maiusculo", "comeca_com"},          # "Claro" != "CLARO"
    {"tudo_minusculo", "comeca_com"},
    {"tudo_maiusculo", "termina_com"},
    {"tudo_minusculo", "termina_com"},
    {"tudo_maiusculo", "contem_palavra"},
    {"sem_numeros", "e_json_valido"},
    {"n_paragrafos", "n_frases"},              # ambiguo: frases por paragrafo ou no total?
    # 🔴 AMBIGUIDADE CONTA COMO IMPOSSIBILIDADE, e esta e' a razao:
    #    "escreva exatamente 2 paragrafos" + "comece com titulo markdown" — o titulo conta
    #    como paragrafo ou nao? Da para resolver com uma quebra de linha so' em vez de duas,
    #    mas isso e' convencao de formatacao, nao obediencia a instrucao. Se EU nao sei a
    #    resposta certa, o modelo tambem nao sabe, e o item vira loteria: metade das
    #    respostas corretas seria reprovada por uma escolha tipografica.
    #    Um benchmark ambiguo nao mede o modelo, mede o azar dele.
    {"n_paragrafos", "tem_titulo_markdown"},
]


def compativel(escolhidas: list[dict], nova: dict) -> bool:
    """Recusa a combinação se ela for impossível de satisfazer."""
    tipos = {i["tipo"] for i in escolhidas}
    t = nova["tipo"]
    if t in tipos:                                   # nunca a mesma instrucao duas vezes
        return False
    for par in INCOMPATIVEIS:
        if t in par and (par - {t}) & tipos:
            return False
    # min de palavras nao pode brigar com max de palavras
    if t == "n_palavras":
        for i in escolhidas:
            if i["tipo"] == "n_palavras":
                return False
    return True


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=541, help="541 = tamanho do IFEval original")
    ap.add_argument("--semente", type=int, default=20260819)
    ap.add_argument("--out", type=Path, default=SAIDA)
    a = ap.parse_args()

    rng = random.Random(a.semente)
    itens, vistos = [], set()
    tentativas = 0
    while len(itens) < a.n and tentativas < a.n * 100:
        tentativas += 1
        tarefa, categoria = rng.choice(TAREFAS)
        disponiveis = moldes(rng)
        rng.shuffle(disponiveis)
        # 1 a 3 instrucoes por prompt — a distribuicao do IFEval original
        alvo = rng.choices([1, 2, 3], weights=[35, 45, 20])[0]
        texto_ins, maquina = [], []
        for txt, ins in disponiveis:
            if len(maquina) >= alvo:
                break
            if compativel(maquina, ins):
                texto_ins.append(txt)
                maquina.append(ins)
        if not maquina:
            continue
        prompt = tarefa[0].upper() + tarefa[1:] + ". " + " ".join(texto_ins)
        chave = (prompt, json.dumps(maquina, sort_keys=True))
        if chave in vistos:
            continue
        vistos.add(chave)
        itens.append({
            "id": f"ifpt_{len(itens)+1:03d}",
            "prompt": prompt,
            "instrucoes": maquina,
            "categoria": categoria,
            "n_instrucoes": len(maquina),
        })

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in itens) + "\n",
                     encoding="utf-8")

    h = hashlib.sha256(a.out.read_bytes()).hexdigest()
    from collections import Counter
    por_n = Counter(i["n_instrucoes"] for i in itens)
    por_tipo = Counter(ins["tipo"] for i in itens for ins in i["instrucoes"])
    print(f"IFEval-PT gerado: {len(itens)} prompts  (pedidos {a.n}, {tentativas} tentativas)")
    print(f"  sha256: {h[:32]}")
    print(f"  instrucoes por prompt: " + " · ".join(f"{k}:{v}" for k, v in sorted(por_n.items())))
    print(f"  total de instrucoes: {sum(por_n[k]*k for k in por_n)}")
    print("\n  cobertura por verificador:")
    for t, c in por_tipo.most_common():
        print(f"    {t:32} {c:>4}")
    faltando = set(moldes(random.Random(0))[i][1]["tipo"] for i in range(len(moldes(random.Random(0))))) - set(por_tipo)
    if faltando:
        print(f"\n  ⚠️ verificadores sem nenhum prompt: {sorted(faltando)}")
    print(f"\n  arquivo: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
