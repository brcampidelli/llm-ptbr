"""Verificadores determinísticos do IFEval-PT — Estágio 0 do pós-treino do Bee-350M.

⭐ POR QUE ISTO EXISTE

"Geração de conteúdo" e "seguir instrução" são as capacidades mais fáceis de auto-enganar.
Um juiz-LLM diz que a resposta "ficou boa" e o número sobe sem que nada tenha melhorado —
e o projeto já pagou por confiar em avaliador frouxo (docs/agentico-medicao.md §2 e §5b).

O IFEval resolve isso restringindo as instruções àquelas **verificáveis por execução**:
"escreva mais de 400 palavras", "não use vírgulas", "responda em JSON", "cite X pelo menos
3 vezes". Um programa decide, não um modelo. O veredito é reproduzível e não tem opinião.

⚠️ O IFEval original é só em inglês. O M-IFEval cobre fr/ja/es — **não há versão em
português**. Por isso os verificadores são reimplementados aqui, com as adaptações que o
português exige e que uma tradução ingênua erraria:

  · **acentuação** — contar letras/palavras tem de normalizar NFC e tratar "ç", "ã", "é";
  · **maiúsculas** — `str.upper()` em português precisa preservar acento ("AÇÃO", não "ACAO");
  · **número por extenso** — "três" e "3" são a mesma coisa numa instrução de contagem;
  · **aspas** — o português usa «», "" e "" além de ' e ";
  · **decimal** — vírgula, não ponto: "1,5" é um número, "1.500" é mil e quinhentos.

🔴 REGRA DE OURO DESTE ARQUIVO
   Todo verificador vem com GABARITOS — casos que DEVEM passar e casos que DEVEM falhar.
   `testar_verificadores.py` executa todos ANTES de qualquer modelo ser carregado. Se um
   gabarito não passa, o defeito é do verificador, não do modelo.
   Isto não é zelo abstrato: este projeto mediu 23,5% de execução agêntica quando a taxa
   real era 57,6%, porque 35 de 85 referências do avaliador eram impossíveis por construção.
   O modelo estava certo; a régua estava quebrada.
"""

from __future__ import annotations

import json
import re
import unicodedata

# ---------------------------------------------------------------------------- utilidades

# Numeros por extenso em PT ate 20 + dezenas — instrucoes de contagem costumam escrever
# "tres paragrafos" em vez de "3 paragrafos", e as duas formas tem de valer.
EXTENSO = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
    "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
    "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
    "trinta": 30, "quarenta": 40, "cinquenta": 50, "cem": 100,
}

ASPAS = '"“”«»‘’\''


def sem_acento(s: str) -> str:
    """Remove acentos para COMPARAR, nunca para exibir."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def normalizar(s: str) -> str:
    """Forma canônica para comparação: NFC, minúsculas, espaços colapsados."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


def contar_palavras(texto: str) -> int:
    """Palavras em PT: separa por espaço e descarta tokens que são só pontuação.

    ⚠️ ESTA FUNÇÃO JÁ ESTAVA ERRADA E O GABARITO PEGOU. A primeira versão usava um regex
    de "sequências alfanuméricas", que conta `R$ 1.500,00` como **cinco** palavras — quebra
    em `R`, `1`, `500`, `00`. Numa instrução "escreva no máximo 50 palavras" isso inflaria
    a contagem e reprovaria respostas corretas que citam valores em reais, que é metade dos
    prompts de contexto brasileiro.

    A regra adotada é a que um humano usa ao contar: um token por bloco entre espaços,
    desde que tenha ao menos um caractere alfanumérico. Assim `R$` conta 1, `1.500,00`
    conta 1, `pé-de-moleque` conta 1, e um travessão solto não conta.
    """
    return sum(1 for t in texto.split()
               if any(c.isalnum() for c in unicodedata.normalize("NFC", t)))


def contar_frases(texto: str) -> int:
    """Frases por pontuação final. Protege abreviações comuns em PT antes de dividir."""
    t = texto
    for abrev in ("Sr.", "Sra.", "Dr.", "Dra.", "Prof.", "Ex.", "etc.", "p.ex.", "a.C.", "d.C."):
        t = t.replace(abrev, abrev.replace(".", "\x00"))
    partes = [p for p in re.split(r"[.!?]+(?:\s|$)", t) if p.strip()]
    return len(partes)


def contar_paragrafos(texto: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", texto.strip()) if p.strip()])


def num_do_arg(v) -> int:
    """Aceita 3, '3' ou 'três' — instruções em PT usam as três formas."""
    if isinstance(v, (int, float)):
        return int(v)
    s = normalizar(str(v))
    if s.isdigit():
        return int(s)
    return EXTENSO.get(sem_acento(s), int(re.sub(r"\D", "", s) or 0))


# ------------------------------------------------------------------------ verificadores
# Cada funcao recebe (resposta, **kwargs) e devolve bool. Nada de opiniao: so' execucao.

def n_palavras(resp: str, minimo: int | None = None, maximo: int | None = None, **_) -> bool:
    n = contar_palavras(resp)
    if minimo is not None and n < num_do_arg(minimo):
        return False
    if maximo is not None and n > num_do_arg(maximo):
        return False
    return True


def n_frases(resp: str, minimo=None, maximo=None, exato=None, **_) -> bool:
    n = contar_frases(resp)
    if exato is not None:
        return n == num_do_arg(exato)
    if minimo is not None and n < num_do_arg(minimo):
        return False
    if maximo is not None and n > num_do_arg(maximo):
        return False
    return True


def n_paragrafos(resp: str, exato=None, minimo=None, **_) -> bool:
    n = contar_paragrafos(resp)
    if exato is not None:
        return n == num_do_arg(exato)
    return n >= num_do_arg(minimo) if minimo is not None else True


def sem_virgula(resp: str, **_) -> bool:
    """⚠️ Só a vírgula de pontuação. '1,5' é decimal em PT e NÃO conta como vírgula."""
    return not re.search(r",(?!\d)", resp)


def contem_palavra(resp: str, palavra: str, vezes: int = 1, **_) -> bool:
    """Conta ocorrências como PALAVRA INTEIRA, ignorando acento e caixa.

    ⚠️ Sem a fronteira \\b, "ação" casaria dentro de "ações" e "coração"; com ela e com a
    remoção de acento, "acao"/"ação"/"Ação" contam como a mesma palavra, que é o que uma
    instrução em português quer dizer.
    """
    alvo = sem_acento(normalizar(palavra))
    corpo = sem_acento(normalizar(resp))
    n = len(re.findall(rf"\b{re.escape(alvo)}\b", corpo))
    return n >= num_do_arg(vezes)


def nao_contem(resp: str, palavras: list[str] | str, **_) -> bool:
    lista = [palavras] if isinstance(palavras, str) else palavras
    corpo = sem_acento(normalizar(resp))
    return all(not re.search(rf"\b{re.escape(sem_acento(normalizar(p)))}\b", corpo)
               for p in lista)


def tudo_maiusculo(resp: str, **_) -> bool:
    """⚠️ Compara com upper() que PRESERVA acento: 'AÇÃO' é maiúscula válida em PT."""
    letras = [c for c in resp if c.isalpha()]
    return bool(letras) and all(c == c.upper() for c in letras)


def tudo_minusculo(resp: str, **_) -> bool:
    letras = [c for c in resp if c.isalpha()]
    return bool(letras) and all(c == c.lower() for c in letras)


def envolvido_em_aspas(resp: str, **_) -> bool:
    """Aceita as aspas do português: «», "" e '' além de \" e '."""
    t = resp.strip()
    pares = [('"', '"'), ("“", "”"), ("«", "»"),
             ("‘", "’"), ("'", "'")]
    return any(t.startswith(a) and t.endswith(b) and len(t) >= 2 for a, b in pares)


def e_json_valido(resp: str, **_) -> bool:
    """Aceita JSON puro ou dentro de cerca ```json — modelos pequenos quase sempre cercam."""
    t = resp.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        json.loads(t)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def n_marcadores(resp: str, exato=None, minimo=None, **_) -> bool:
    """Conta itens de lista com marcador (-, *, • ou '1.')."""
    n = len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+", resp, re.M))
    if exato is not None:
        return n == num_do_arg(exato)
    return n >= num_do_arg(minimo) if minimo is not None else n > 0


def tem_titulo_markdown(resp: str, nivel: int | None = None, **_) -> bool:
    if nivel is None:
        return bool(re.search(r"^#{1,6}\s+\S", resp, re.M))
    return bool(re.search(rf"^#{{{num_do_arg(nivel)}}}\s+\S", resp, re.M))


def termina_com(resp: str, texto: str, **_) -> bool:
    return normalizar(resp).endswith(normalizar(texto))


def comeca_com(resp: str, texto: str, **_) -> bool:
    return normalizar(resp).startswith(normalizar(texto))


def n_secoes(resp: str, separador: str, minimo=None, **_) -> bool:
    n = len([s for s in resp.split(separador) if s.strip()])
    return n >= num_do_arg(minimo) if minimo is not None else n > 1


def sem_numeros(resp: str, **_) -> bool:
    """Nenhum algarismo. Números por extenso são permitidos — a instrução é sobre dígitos."""
    return not re.search(r"\d", resp)


def repete_pedido(resp: str, pedido: str, **_) -> bool:
    """A resposta começa repetindo o pedido literalmente (instrução clássica do IFEval)."""
    return normalizar(resp).startswith(normalizar(pedido))


def duas_respostas(resp: str, separador: str = "******", **_) -> bool:
    partes = [p for p in resp.split(separador) if p.strip()]
    return len(partes) == 2


def sem_palavra_proibida_inicio(resp: str, palavra: str, **_) -> bool:
    """Nenhuma FRASE começa com a palavra dada (ex.: não comece frases com 'Eu')."""
    alvo = sem_acento(normalizar(palavra))
    for frase in re.split(r"[.!?]+\s*", resp):
        f = frase.strip()
        if f and sem_acento(normalizar(f)).split(" ")[0] == alvo:
            return False
    return True


def n_caracteres(resp: str, minimo=None, maximo=None, **_) -> bool:
    """⚠️ Conta em NFC: 'ç' é UM caractere, não 'c'+cedilha."""
    n = len(unicodedata.normalize("NFC", resp))
    if minimo is not None and n < num_do_arg(minimo):
        return False
    if maximo is not None and n > num_do_arg(maximo):
        return False
    return True


def idioma_portugues(resp: str, **_) -> bool:
    """Heurística barata: presença de palavras funcionais do PT e ausência das do EN.

    ⚠️ É a ÚNICA verificação deste arquivo que não é exata, e está aqui porque "responda em
    português" é uma instrução real e frequente. Ela é deliberadamente FROUXA (favorece o
    modelo) para não reprovar texto correto — o objetivo é pegar resposta escrita em inglês,
    não julgar qualidade de português.
    """
    corpo = sem_acento(normalizar(resp))
    pt = sum(1 for p in (" de ", " que ", " para ", " com ", " nao ", " uma ", " dos ",
                         " como ", " mas ", " por ") if p in f" {corpo} ")
    en = sum(1 for p in (" the ", " and ", " of ", " to ", " is ", " for ", " with ",
                         " that ") if p in f" {corpo} ")
    return pt >= en


VERIFICADORES = {
    "n_palavras": n_palavras, "n_frases": n_frases, "n_paragrafos": n_paragrafos,
    "sem_virgula": sem_virgula, "contem_palavra": contem_palavra, "nao_contem": nao_contem,
    "tudo_maiusculo": tudo_maiusculo, "tudo_minusculo": tudo_minusculo,
    "envolvido_em_aspas": envolvido_em_aspas, "e_json_valido": e_json_valido,
    "n_marcadores": n_marcadores, "tem_titulo_markdown": tem_titulo_markdown,
    "termina_com": termina_com, "comeca_com": comeca_com, "n_secoes": n_secoes,
    "sem_numeros": sem_numeros, "repete_pedido": repete_pedido,
    "duas_respostas": duas_respostas,
    "sem_palavra_proibida_inicio": sem_palavra_proibida_inicio,
    "n_caracteres": n_caracteres, "idioma_portugues": idioma_portugues,
}


def verificar(resposta: str, instrucoes: list[dict]) -> tuple[bool, list[dict]]:
    """Aplica todas as instruções de um item. Devolve (passou_todas, detalhe_por_instrucao).

    ⚠️ Uma instrução DESCONHECIDA nunca é tratada como satisfeita. Contar como sucesso o
    que não se sabe medir infla o resultado em silêncio — o modo de falha exato que este
    arquivo existe para evitar.
    """
    det = []
    for ins in instrucoes:
        nome = ins.get("tipo")
        fn = VERIFICADORES.get(nome)
        if fn is None:
            det.append({"tipo": nome, "ok": False, "erro": "VERIFICADOR DESCONHECIDO"})
            continue
        args = {k: v for k, v in ins.items() if k != "tipo"}
        try:
            ok = bool(fn(resposta, **args))
            det.append({"tipo": nome, "ok": ok})
        except Exception as e:                       # noqa: BLE001
            det.append({"tipo": nome, "ok": False, "erro": f"{type(e).__name__}: {e}"})
    return all(d["ok"] for d in det), det
