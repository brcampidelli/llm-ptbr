"""Onde a geração PARA — e por que isso zerava réguas inteiras em silêncio.

🔴 O DEFEITO QUE ISTO CORRIGE

As réguas do Estágio 0 foram escritas contra o **modelo base**, que nunca emite token de
parada: ele fala até o teto de `max_new` e o avaliador corta pelo tamanho. Isso funcionou
para medir o base e **quebra no instante em que o modelo aprende a parar**.

Medido em 2026-08-20, no braço full FT do grid do E2. O modelo emitia a chamada exata:

    {"tool": "get_weather", "args": {"city": "Brasília", "days": 1}}<|im_end|>

…e continuava, porque `<|im_end|>` não estava ligado como parada. A geração ia até o teto, o
caso era contado como **truncado**, e o parser recebia cinco chamadas concatenadas — que não
são JSON. **Resultado reportado: 0%.** O modelo tinha saído de 0/85 para chamada válida na
primeira tentativa, e a régua marcava zero sem uma linha de erro.

⚠️ **E uma decisão que muda a comparação, então fica declarada.** Os adapters LoRA aprenderam
a terminar com `<|im_start|>` (id 1) em vez de `<|im_end|>` (id 2) — erraram o terminador por
**um id**. A explicação provável é que o LoRA não treina `lm_head`/`embed_tokens`, e o full FT
treina. Parar também em `<|im_start|>` **resgata** o LoRA de um laço infinito, o que é
generoso com ele. Por isso o terminador não é escondido: `terminador_correto()` devolve se o
modelo parou pelo token certo, e a régua reporta esse número **junto** do acerto. Separar a
capacidade (o JSON está certo) do defeito de formato (o terminador está errado) é o ponto —
um número só, misturando os dois, não diz qual dos dois consertar.
"""

from __future__ import annotations

# Ordem importa: o primeiro é o terminador CORRETO da convenção ChatML.
ESPECIAIS_CHAT = ["<|im_end|>", "<|im_start|>", "<|endoftext|>"]


def ids_de_parada(tok, chat: bool) -> list[int]:
    """Ids em que `generate` deve parar. Sem `--chat`, só o eos do tokenizador."""
    ids = []
    if chat:
        for t in ESPECIAIS_CHAT:
            i = tok.convert_tokens_to_ids(t)
            if isinstance(i, int) and i >= 0 and i != getattr(tok, "unk_token_id", None):
                ids.append(i)
    if tok.eos_token_id is not None and tok.eos_token_id not in ids:
        ids.append(tok.eos_token_id)
    return ids or [tok.pad_token_id]


def terminador_correto(texto: str) -> bool | None:
    """Qual especial o modelo emitiu para PARAR. `None` = não parou, foi ao teto.

    🔴 A primeira versão olhava o FIM da string e media o padding, não o terminador. No
    caminho em lote a geração só termina quando a sequência MAIS LONGA acaba; as que
    terminaram antes ficam preenchidas com pad até lá. O texto decodificado então acaba em
    pad, e `endswith("<|im_end|>")` dava falso em 30/30 — inclusive no braço que eu tinha
    visto parar corretamente na inspeção manual, um a um.

    ⚠️ Um número que contradiz uma observação direta é o aparato, não o fenômeno. O certo é
    olhar o PRIMEIRO especial depois do conteúdo: é ele que encerrou a resposta.
    """
    primeiro, pos = None, len(texto)
    for e in ESPECIAIS_CHAT:
        i = texto.find(e)
        if 0 <= i < pos:
            primeiro, pos = e, i
    if primeiro is None:
        return None
    return primeiro == ESPECIAIS_CHAT[0]


def limpar(texto: str) -> str:
    """Tira o rabo de especiais para o parser/verificador ver só o conteúdo."""
    t = texto
    for e in ESPECIAIS_CHAT:
        i = t.find(e)
        if i >= 0:
            t = t[:i]
    return t.strip()


# C0 menos \t \n \r: nunca é conteúdo legítimo, nem em JSON (onde teria de vir escapado)
# nem em texto. Medido no E5: o terminador do adapter é INSTÁVEL entre modos de decodificação
# — o greedy emitia `<|im_start|>` (id 1, ligado como parada) e a amostragem caía em bytes de
# controle vizinhos (\x00, \x0f, \x1e), que não param nada. A geração então enchia 320 tokens
# e o parser recebia chamadas concatenadas.
_CONTROLE = {chr(c) for c in range(32)} - {"\t", "\n", "\r"} | {"\x7f"}


def cortar_no_controle(texto: str) -> str:
    """Corta no primeiro caractere de controle. Independe de QUAL id o modelo escolheu."""
    for i, ch in enumerate(texto):
        if ch in _CONTROLE:
            return texto[:i]
    return texto


def primeiro_objeto(texto: str) -> str | None:
    """Extrai o PRIMEIRO objeto JSON balanceado, ignorando o que vier depois.

    ⚠️ Esta é uma régua DIFERENTE da estrita, não um conserto dela. A estrita
    (`extract_json`) exige que a saída inteira seja um objeto só — foi escrita para CURAR
    dado de destilação, onde texto solto ao lado do JSON significa exemplo ruim, e ali está
    certa. Como régua de avaliação ela mede junto o terminador, que é instável.

    Esta imita o que um harness real faz: lê a primeira chamada completa e descarta o resto.
    As duas devem ser reportadas LADO A LADO — a diferença entre elas é o tamanho do problema
    de terminação, e trocar uma pela outra no meio de uma comparação seria mudar o
    instrumento entre os grupos.
    """
    i = texto.find("{")
    if i < 0:
        return None
    prof = 0
    dentro_str = False
    escapa = False
    for j in range(i, len(texto)):
        ch = texto[j]
        if dentro_str:
            if escapa:
                escapa = False
            elif ch == "\\":
                escapa = True
            elif ch == '"':
                dentro_str = False
            continue
        if ch == '"':
            dentro_str = True
        elif ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0:
                return texto[i:j + 1]
    return None


def _autoteste() -> int:
    """Regua sem teste e' regua em que nao se pode confiar — o projeto ja' pagou por isso."""
    casos = [
        # (entrada, esperado de primeiro_objeto)
        ('{"tool": "x", "args": {}}', '{"tool": "x", "args": {}}'),
        # o caso do E5: chamada boa + lixo depois
        ('{"tool": "a", "args": {"c": 1}}\x1e\n{"c": 2}}', '{"tool": "a", "args": {"c": 1}}'),
        # aninhamento tem de ser respeitado, senao corta no } de dentro
        ('{"a": {"b": {"c": 1}}, "d": 2} sobra', '{"a": {"b": {"c": 1}}, "d": 2}'),
        # chave com } dentro de string nao pode fechar o objeto
        ('{"q": "fecha } aqui", "n": 1} resto', '{"q": "fecha } aqui", "n": 1}'),
        # aspas escapadas dentro da string
        (r'{"q": "diz \"oi\" }", "n": 1} x', r'{"q": "diz \"oi\" }", "n": 1}'),
        # texto antes da chamada
        ('Claro! {"tool": "y", "args": {}}', '{"tool": "y", "args": {}}'),
        # nao ha objeto
        ('desculpe, nao consigo', None),
        # objeto truncado (sem fechar) -> None, nao um palpite
        ('{"tool": "z", "args": {"a": 1}', None),
    ]
    falhas = 0
    for entrada, esperado in casos:
        obtido = primeiro_objeto(entrada)
        if obtido != esperado:
            falhas += 1
            print(f"  FALHOU: {entrada!r}\n    esperado {esperado!r}\n    obtido   {obtido!r}")
    ctrl = [("abc\x00def", "abc"), ("sem controle", "sem controle"),
            ("linha\nquebra", "linha\nquebra"), ("\x1ecomeca", "")]
    for entrada, esperado in ctrl:
        obtido = cortar_no_controle(entrada)
        if obtido != esperado:
            falhas += 1
            print(f"  FALHOU cortar_no_controle: {entrada!r} -> {obtido!r} (esperado {esperado!r})")
    total = len(casos) + len(ctrl)
    print(f"autoteste paradas.py: {total - falhas}/{total} passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_autoteste())


def ids_de_controle(tok, teto: int = 2048) -> list[int]:
    """Ids cujo texto decodificado E' um caractere de controle. DERIVADO, nao adivinhado.

    O terminador de-facto deste adapter sob amostragem cai nesses ids (\x00, \x0f, \x1e...),
    que nao param a geracao: ela vai ao teto de max_new e desperdica ~280 tokens por amostra.
    Parar neles e' intervencao de RUNTIME (o que o E5b e'), nao mudanca de modelo — e nao pode
    custar conteudo legitimo, porque C0 nunca e' conteudo legitimo.

    🔴 E' DELIBERADO que isto NAO inclua os bytes altos (0x80-0xF7), que tambem aparecem no
    fim das geracoes decodificando como U+FFFD. Em BPE de byte, um caractere acentuado E' uma
    SEQUENCIA desses bytes — o `i` de "Brasilia" sai como 0xC3 0xAD, e cada um sozinho
    decodifica para U+FFFD. Parar neles truncaria portugues valido no meio da palavra.
    Os C0 sao seguros porque 0x00-0x1F nunca ocorre dentro de UTF-8 multibyte (continuacao e'
    0x80-0xBF, lider e' 0xC0-0xF7). A diferenca entre as duas faixas e' a diferenca entre uma
    guarda e um bug.
    """
    fora = []
    for i in range(min(teto, len(tok))):
        try:
            s = tok.decode([i])
        except Exception:
            continue
        if s and all(c in _CONTROLE for c in s):
            fora.append(i)
    return fora
