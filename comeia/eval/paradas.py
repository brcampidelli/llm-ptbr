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
