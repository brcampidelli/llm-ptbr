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
    """`True` se parou por `<|im_end|>`, `False` por outro especial, `None` se não parou.

    `None` (não parou) e `False` (parou pelo token errado) são falhas DIFERENTES: a primeira
    é o modelo que não aprendeu a terminar, a segunda é o que aprendeu a terminar errado.
    """
    t = texto.rstrip()
    if t.endswith("<|im_end|>"):
        return True
    return False if any(t.endswith(e) for e in ESPECIAIS_CHAT[1:]) else None


def limpar(texto: str) -> str:
    """Tira o rabo de especiais para o parser/verificador ver só o conteúdo."""
    t = texto
    for e in ESPECIAIS_CHAT:
        i = t.find(e)
        if i >= 0:
            t = t[:i]
    return t.strip()
