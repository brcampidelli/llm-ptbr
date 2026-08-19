"""Gera o conjunto de atendimento automatizado em PT: mensagem do cliente → ação verificável.

⭐ O QUE TORNA "ATENDIMENTO" MENSURÁVEL POR EXECUÇÃO

Atendimento parece a capacidade menos verificável das oito — é conversa, e conversa se julga
por gosto. Mas o que faz um atendimento ser útil ou desastroso **não** é o gosto:

  1. entendeu o que o cliente quer? (intenção — rótulo, comparação exata)
  2. pegou o dado certo? (número do pedido, valor, CEP — comparação exata)
  3. prometeu o que não pode? (política — lista fechada de promessas proibidas)
  4. inventou dado que o cliente não deu? (número que não está na conversa)

As quatro são determinísticas. O que sobra — tom, empatia, redação — é real e fica de fora,
declarado: este número mede **se o atendimento não causa dano**, não se ele é agradável.

🔴 O ITEM 3 É O QUE JUSTIFICA O CONJUNTO EXISTIR. Um modelo de 350M que responde "claro,
   estorno hoje mesmo!" está sendo simpático e criando passivo jurídico. Nenhuma métrica de
   similaridade pega isso; uma lista de promessas proibidas pega todas as vezes.

⚠️ AS MENSAGENS SÃO SINTÉTICAS, com o mesmo preço declarado do conjunto de resumo: são mais
   regulares que cliente de verdade. O que elas preservam de propósito é o que quebra
   sistemas reais — número de pedido com formato variável, cliente que pede duas coisas na
   mesma frase, e o pedido de reembolso rápido, que é a armadilha de política.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

SAIDA = Path(__file__).resolve().parent / "benchmarks" / "atendimento_pt.jsonl"
SEMENTE = 20260819
POR_INTENCAO = 25

NOMES = ["Cleide", "Rogério", "Marina", "Wilson", "Andrea", "Otávio", "Selma", "Ivan",
         "Débora", "Nelson", "Priscila", "Hamilton", "Vanderlei", "Rosangela"]
PRODUTOS = ["a cafeteira", "o notebook", "a impressora", "o fone de ouvido", "a cadeira",
            "o ventilador", "a smart TV", "o micro-ondas", "a bicicleta", "o tablet"]
CIDADES = ["Sorocaba", "Londrina", "Petrolina", "Chapecó", "Uberaba", "Blumenau"]

# ⭐ PROMESSAS PROIBIDAS — a política diz 7 dias úteis para estorno e 5 para troca.
#    Qualquer prazo menor que isso, dito ao cliente, é passivo. A lista é de SUPERFÍCIE
#    (substring normalizada) de propósito: precisa ser auditável por quem não programa.
PROIBIDAS = ["hoje mesmo", "em 24 horas", "em 24h", "ate amanha", "amanha mesmo",
             "imediatamente", "na hora", "agora mesmo", "em 1 dia", "em um dia",
             "em 2 dias", "em dois dias", "no mesmo dia", "instantaneamente"]


def _pedido(rng) -> str:
    return rng.choice([f"{rng.randrange(1000000, 9999999)}",
                       f"BR-{rng.randrange(100000, 999999)}",
                       f"{rng.randrange(10000, 99999)}-{rng.randrange(1, 9)}"])


def _valor(rng) -> tuple[float, str]:
    v = rng.randrange(3990, 499900) / 100
    return v, f"R$ {v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _cep(rng) -> str:
    return f"{rng.randrange(10000, 99999)}-{rng.randrange(100, 999)}"


# cada molde devolve (texto, intencao, dados, exige_politica)
#
# 🔴 A PRIMEIRA VERSAO DESTES MOLDES FOI REPROVADA PELO PROPRIO PISO. Cada intencao tinha uma
#    frase so', com uma palavra-chave exclusiva, e uma regra de 16 linhas de regex acertou
#    **100% das 250**. Um conjunto cujo piso trivial ja' esta' no teto nao mede nada: o modelo
#    so' pode empatar ou parecer ruim.
#
#    A correcao nao foi "piorar a regra" — foi construir **colisao lexica de proposito**, que
#    e' o que existe em atendimento de verdade:
#      · "cancelar"  aparece em cancelar_pedido E em cancelar_assinatura
#      · "trocar"    aparece em trocar_produto E em alterar_endereco ("trocar o endereco")
#      · "prazo"     aparece em duvida_prazo E em rastrear_pedido
#      · "valor/cartao" aparece em solicitar_reembolso E em problema_pagamento
#    Com tres redacoes por intencao, nenhuma palavra sozinha decide a classe.

def _e(rng, *ops):
    return rng.choice(ops)


def m_rastrear(rng):
    p = _pedido(rng)
    return (_e(rng,
              f"Oi, boa tarde. Comprei {rng.choice(PRODUTOS)} no pedido {p} e ate agora nao "
              f"chegou. Da pra ver onde esta?",
              f"O prazo do pedido {p} ja' venceu e nada de chegar. Cade a entrega?",
              f"Pedido {p}: o rastreio nao atualiza ha' cinco dias, isso e' normal?"),
            "rastrear_pedido", {"numero_pedido": p}, False)


def m_cancelar(rng):
    p = _pedido(rng)
    return (_e(rng,
              f"Preciso cancelar o pedido {p}, comprei errado.",
              f"Da' pra cancelar a compra {p} antes de sair pra entrega? Escolhi o modelo "
              f"errado.",
              f"Quero desistir da compra do pedido {p}. Ainda nao foi enviado."),
            "cancelar_pedido", {"numero_pedido": p}, False)


def m_reembolso(rng):
    p, (v, vt) = _pedido(rng), _valor(rng)
    return (_e(rng,
              f"Devolvi {rng.choice(PRODUTOS)} do pedido {p} na semana passada e o valor de "
              f"{vt} nao voltou. Quando cai na minha conta?",
              f"Pedido {p} devolvido e recebido por voces, mas os {vt} continuam sem "
              f"aparecer no cartao. Quando estorna?",
              f"Ja' faz dez dias que devolvi o pedido {p}. Cade os {vt} de volta?"),
            "solicitar_reembolso", {"numero_pedido": p, "valor": v}, True)


def m_troca(rng):
    p = _pedido(rng)
    return (_e(rng,
              f"{rng.choice(PRODUTOS).capitalize()} do pedido {p} veio com defeito. Quero "
              f"trocar por outro igual.",
              f"O produto do pedido {p} chegou quebrado. Como faco pra receber outro?",
              f"Pedido {p}: veio o item errado, quero trocar pelo que pedi."),
            "trocar_produto", {"numero_pedido": p}, True)


def m_pagamento(rng):
    v, vt = _valor(rng)
    return (_e(rng,
              f"Fui pagar e apareceu erro, mas o valor de {vt} saiu do meu cartao duas vezes.",
              f"Cobraram {vt} em duplicidade no cartao e a compra nem foi aprovada.",
              f"Aparece que meu pagamento de {vt} falhou, so' que ja' esta' na fatura."),
            "problema_pagamento", {"valor": v}, True)


def m_endereco(rng):
    p, c = _pedido(rng), _cep(rng)
    return (_e(rng,
              f"Mudei de endereco depois de comprar. Da' pra trocar a entrega do pedido {p} "
              f"pro CEP {c}?",
              f"Preciso que o pedido {p} va' pro CEP {c}, e nao pro antigo.",
              f"Coloquei o endereco errado no pedido {p}. O certo e' o CEP {c}."),
            "alterar_endereco", {"numero_pedido": p, "cep": c}, False)


def m_prazo(rng):
    c = _cep(rng)
    return (_e(rng,
              f"Antes de fechar a compra: qual o prazo de entrega pro CEP {c}? Moro em "
              f"{rng.choice(CIDADES)}.",
              f"Ainda nao comprei nada. Voces entregam no CEP {c} em quantos dias?",
              f"Se eu pedir hoje pro CEP {c}, chega antes do fim do mes?"),
            "duvida_prazo", {"cep": c}, False)


def m_reclamar(rng):
    p = _pedido(rng)
    return (_e(rng,
              f"E' a terceira vez que entro em contato sobre o pedido {p} e ninguem resolve. "
              f"Quero falar com um supervisor.",
              f"Ninguem me responde direito sobre o pedido {p}. Quero registrar reclamacao "
              f"formal.",
              f"Estou sendo enrolado ha' semanas no pedido {p}. Passa pro responsavel."),
            "reclamar_atendimento", {"numero_pedido": p}, False)


def m_boleto(rng):
    p = _pedido(rng)
    return (_e(rng,
              f"O boleto do pedido {p} venceu ontem. Consegue gerar a segunda via?",
              f"Perdi o boleto do pedido {p}, da' pra reenviar?",
              f"Pedido {p}: preciso do boleto atualizado pra pagar hoje."),
            "segunda_via_boleto", {"numero_pedido": p}, False)


def m_assinatura(rng):
    nome = rng.choice(NOMES).lower()
    email = f"{nome}.{rng.randrange(10, 99)}@email.com.br"
    return (_e(rng,
              f"Quero cancelar minha assinatura mensal. Meu cadastro e' {email}.",
              f"Nao quero mais o plano recorrente, pode cancelar? E-mail {email}.",
              f"Como faco pra encerrar a assinatura do {email}? Nao uso mais."),
            "cancelar_assinatura", {"email": email}, True)


MOLDES = [m_rastrear, m_cancelar, m_reembolso, m_troca, m_pagamento,
          m_endereco, m_prazo, m_reclamar, m_boleto, m_assinatura]

POLITICA = ("Politica da loja: estorno em ate 7 dias uteis apos a devolucao ser recebida; "
            "troca por defeito em ate 5 dias uteis; cancelamento so' antes do envio; "
            "assinatura cancelada encerra no fim do ciclo ja' pago.")


def gerar() -> list[dict]:
    rng = random.Random(SEMENTE)
    itens = []
    for molde in MOLDES:
        for k in range(POR_INTENCAO):
            texto, intencao, dados, politica = molde(rng)
            itens.append({
                "id": f"{intencao}-{k:02d}",
                "mensagem": texto,
                "intencao": intencao,
                "dados": dados,
                "checa_politica": politica,
                "politica": POLITICA,
            })
    rng.shuffle(itens)
    return itens


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    itens = gerar()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    h = hashlib.sha256(SAIDA.read_bytes()).hexdigest()[:32]
    print(f"✅ {len(itens)} itens · {len(MOLDES)} intencoes · {SAIDA.name}")
    print(f"   sha256[:32] = {h}")
    print(f"   piso da intencao majoritaria: {100 / len(MOLDES):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
