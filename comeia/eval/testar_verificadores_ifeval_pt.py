"""Gabaritos dos verificadores do IFEval-PT. RODAR ANTES DE CARREGAR QUALQUER MODELO.

🔴 POR QUE ESTE ARQUIVO EXISTE

O critério do Estágio 0 é literal: *"os gabaritos de 100% dos avaliadores novos executam
corretamente antes de qualquer modelo ser carregado"*. Não é formalidade.

Este projeto já mediu **23,5%** de execução agêntica quando a taxa real era **57,6%**,
porque 35 de 85 referências do avaliador eram impossíveis por construção. Duas semanas de
conclusões erradas saíram de um avaliador quebrado que ninguém tinha testado. O modelo
estava certo o tempo todo.

⭐ CADA VERIFICADOR TEM DOIS TIPOS DE CASO, e os dois importam:
   · POSITIVO — texto que satisfaz a instrução e DEVE passar;
   · NEGATIVO — texto que a viola e DEVE falhar.
   Só positivos não detectam um verificador que devolve `True` sempre — que é exatamente
   como um avaliador quebrado costuma se parecer: tudo verde, nada medido.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ifeval_pt_verificadores import VERIFICADORES, verificar  # noqa: E402

# (verificador, kwargs, texto, esperado)
CASOS: list[tuple[str, dict, str, bool]] = [
    # ---------------------------------------------------------------- contagem
    ("n_palavras", {"minimo": 5}, "uma duas tres quatro cinco", True),
    ("n_palavras", {"minimo": 5}, "uma duas tres", False),
    ("n_palavras", {"maximo": 3}, "uma duas tres", True),
    ("n_palavras", {"maximo": 3}, "uma duas tres quatro", False),
    # ⭐ hifen e moeda: "pe-de-moleque" e 1 palavra, "R$ 1.500,00" nao vira 3
    ("n_palavras", {"minimo": 2, "maximo": 2}, "pé-de-moleque delicioso", True),
    ("n_palavras", {"minimo": 3, "maximo": 3}, "custa R$ 1.500,00", True),
    # 🔴 CASO QUE PEGOU UM BUG REAL: o regex antigo contava isto como 5 palavras.
    ("n_palavras", {"minimo": 2, "maximo": 2}, "R$ 1.500,00", True),
    ("n_palavras", {"minimo": 4, "maximo": 4}, "sobrou 3,5 kg hoje", True),
    # pontuacao solta nao e' palavra
    ("n_palavras", {"minimo": 2, "maximo": 2}, "sim — nao", True),

    ("n_frases", {"exato": 2}, "Primeira frase. Segunda frase.", True),
    ("n_frases", {"exato": 2}, "Primeira. Segunda. Terceira.", False),
    # ⭐ abreviacao nao pode contar como fim de frase
    ("n_frases", {"exato": 1}, "O Dr. Silva chegou cedo.", True),

    ("n_paragrafos", {"exato": 2}, "Primeiro parágrafo.\n\nSegundo parágrafo.", True),
    ("n_paragrafos", {"exato": 2}, "Um só parágrafo aqui.", False),
    # ⭐ numero por extenso na instrucao
    ("n_paragrafos", {"exato": "dois"}, "Um.\n\nDois.", True),

    # ---------------------------------------------------------------- pontuacao
    ("sem_virgula", {}, "Frase simples sem pontuação dupla.", True),
    ("sem_virgula", {}, "Frase com vírgula, aqui.", False),
    # 🔴 O CASO QUE UMA TRADUCAO INGENUA ERRARIA: virgula decimal em PT nao e' pontuacao
    ("sem_virgula", {}, "O produto custa 1,50 reais.", True),

    ("sem_numeros", {}, "Texto sem algarismo nenhum.", True),
    ("sem_numeros", {}, "Tem 3 itens.", False),
    ("sem_numeros", {}, "Tem três itens.", True),

    # ---------------------------------------------------------------- palavras
    ("contem_palavra", {"palavra": "ação", "vezes": 2}, "A ação e a AÇÃO novamente.", True),
    ("contem_palavra", {"palavra": "ação", "vezes": 2}, "Só uma ação aqui.", False),
    # 🔴 fronteira de palavra: "acoes" e "coracao" NAO contam como "acao"
    ("contem_palavra", {"palavra": "ação", "vezes": 1}, "As ações do coração.", False),
    ("contem_palavra", {"palavra": "acao", "vezes": 1}, "Uma ação qualquer.", True),

    ("nao_contem", {"palavras": ["erro", "falha"]}, "Tudo certo por aqui.", True),
    ("nao_contem", {"palavras": ["erro", "falha"]}, "Houve um erro.", False),
    ("nao_contem", {"palavras": "não"}, "Isso nao pode aparecer? Nao.", False),

    ("sem_palavra_proibida_inicio", {"palavra": "Eu"},
     "Ontem fui à feira. Depois voltei.", True),
    ("sem_palavra_proibida_inicio", {"palavra": "Eu"},
     "Ontem fui à feira. Eu voltei depois.", False),

    # ---------------------------------------------------------------- caixa
    ("tudo_maiusculo", {}, "TEXTO TOTALMENTE MAIÚSCULO", True),
    ("tudo_maiusculo", {}, "Texto Misto", False),
    # 🔴 acento em maiuscula: 'AÇÃO' e' valido e uma checagem ASCII reprovaria
    ("tudo_maiusculo", {}, "AÇÃO E REAÇÃO", True),
    ("tudo_minusculo", {}, "tudo em caixa baixa, com ação", True),
    ("tudo_minusculo", {}, "Tem Uma Maiúscula", False),

    # ---------------------------------------------------------------- formato
    ("envolvido_em_aspas", {}, '"resposta entre aspas"', True),
    ("envolvido_em_aspas", {}, "«resposta com aspas portuguesas»", True),
    ("envolvido_em_aspas", {}, "“aspas curvas”", True),
    ("envolvido_em_aspas", {}, "sem aspas nenhuma", False),

    ("e_json_valido", {}, '{"chave": "valor"}', True),
    ("e_json_valido", {}, '```json\n{"a": 1}\n```', True),
    ("e_json_valido", {}, "isto nao e json", False),
    ("e_json_valido", {}, '{"quebrado": ', False),

    ("n_marcadores", {"minimo": 3}, "- um\n- dois\n- três", True),
    ("n_marcadores", {"minimo": 3}, "1. um\n2. dois\n3. três", True),
    ("n_marcadores", {"minimo": 3}, "- só um", False),

    ("tem_titulo_markdown", {}, "# Título\n\ntexto", True),
    ("tem_titulo_markdown", {"nivel": 2}, "## Subtítulo", True),
    ("tem_titulo_markdown", {"nivel": 2}, "# Título", False),
    ("tem_titulo_markdown", {}, "sem título", False),

    ("duas_respostas", {}, "primeira resposta ****** segunda resposta", True),
    ("duas_respostas", {}, "só uma resposta", False),

    ("n_secoes", {"separador": "---", "minimo": 3}, "a\n---\nb\n---\nc", True),
    ("n_secoes", {"separador": "---", "minimo": 3}, "a\n---\nb", False),

    # ---------------------------------------------------------------- bordas
    ("termina_com", {"texto": "Espero ter ajudado."},
     "Segue o resumo. Espero ter ajudado.", True),
    ("termina_com", {"texto": "Espero ter ajudado."}, "Segue o resumo.", False),
    ("comeca_com", {"texto": "Claro"}, "Claro, vamos lá.", True),
    ("comeca_com", {"texto": "Claro"}, "Vamos lá.", False),
    ("repete_pedido", {"pedido": "Explique o que é fotossíntese"},
     "Explique o que é fotossíntese — a fotossíntese é...", True),
    ("repete_pedido", {"pedido": "Explique o que é fotossíntese"},
     "A fotossíntese é o processo...", False),

    # ---------------------------------------------------------------- caracteres
    ("n_caracteres", {"minimo": 10}, "texto com mais de dez", True),
    ("n_caracteres", {"maximo": 5}, "curto", True),
    ("n_caracteres", {"maximo": 5}, "texto grande demais", False),
    # 🔴 'ç' e' UM caractere em NFC; contar em NFD daria 2 e o teste falharia
    ("n_caracteres", {"minimo": 5, "maximo": 5}, "ações", True),

    # ---------------------------------------------------------------- idioma
    ("idioma_portugues", {},
     "Este texto está em português e não deixa dúvida para o verificador.", True),
    ("idioma_portugues", {},
     "This text is written in English and should be rejected by the checker.", False),
]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 78)
    print("GABARITOS DOS VERIFICADORES DO IFEval-PT")
    print("=" * 78)

    falhas, por_verif = [], {}
    for nome, kwargs, texto, esperado in CASOS:
        fn = VERIFICADORES.get(nome)
        if fn is None:
            falhas.append((nome, texto, "VERIFICADOR INEXISTENTE"))
            continue
        try:
            obtido = bool(fn(texto, **kwargs))
        except Exception as e:                        # noqa: BLE001
            falhas.append((nome, texto, f"EXCECAO {type(e).__name__}: {e}"))
            continue
        d = por_verif.setdefault(nome, {"ok": 0, "erro": 0})
        if obtido == esperado:
            d["ok"] += 1
        else:
            d["erro"] += 1
            falhas.append((nome, texto, f"esperado {esperado}, obtido {obtido}"))

    for nome in sorted(VERIFICADORES):
        d = por_verif.get(nome)
        if d is None:
            print(f"  ⚠️  {nome:30} SEM GABARITO")          # cobertura incompleta e' defeito
            continue
        marca = "✅" if d["erro"] == 0 else "🔴"
        print(f"  {marca} {nome:30} {d['ok']:>2} ok · {d['erro']} erro")

    sem_gabarito = [n for n in VERIFICADORES if n not in por_verif]
    print("\n" + "=" * 78)
    if falhas:
        print(f"🔴 {len(falhas)} CASO(S) FALHARAM — o defeito e' do VERIFICADOR, nao do modelo")
        for nome, texto, motivo in falhas:
            print(f"   · {nome}: {motivo}\n     texto: {texto[:70]!r}")
    if sem_gabarito:
        print(f"🔴 {len(sem_gabarito)} verificador(es) SEM GABARITO: {sem_gabarito}")
        print("   Um verificador nao testado pode devolver True sempre e ninguem notaria.")
    if falhas or sem_gabarito:
        print("\nABORTADO. Corrija antes de medir qualquer modelo.")
        return 1

    print(f"✅ {len(CASOS)} casos · {len(VERIFICADORES)} verificadores · 100% dos gabaritos passam")
    print("   A regua esta calibrada. Pode carregar modelo.")

    # sanidade do orquestrador `verificar()`: instrucao desconhecida NAO pode passar
    ok, det = verificar("qualquer coisa", [{"tipo": "verificador_que_nao_existe"}])
    if ok:
        print("\n🔴 FALHA GRAVE: instrucao desconhecida foi contada como satisfeita.")
        return 1
    print("   ✅ instrucao desconhecida e' reprovada, nao ignorada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
