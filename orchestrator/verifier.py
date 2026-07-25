"""COMEIA — verificador determinístico de tool-call (ataca o over-calling SEM treinar).

Padrão do interwhen (arXiv 2602.11202): verificação de PROCESSO no laço do agente,
em código, interrompendo só quando detecta violação. No paper isso rendeu +55,53 pp
em tarefa agêntica a 96,93% do custo de tokens — verificar saiu mais BARATO, porque
evita trajetórias longas erradas. Aqui atacamos o custo medido do nosso treino: a
abelha agêntica ganhou +28,5 pp no score, mas o over-calling subiu de 4% -> 16%
(chamar ferramenta quando não precisava).

Quatro checagens, na ordem do paper:
  1. JSON parseável
  2. ferramenta existe no catálogo
  3. args obrigatórios presentes, nenhum arg desconhecido
  4. ⭐ MODO corresponde à intenção da query (JSON vs texto) — é esta que mata o
     over-calling, e a única que precisa de um sinal externo ao modelo.

⚠️ PRINCÍPIO DE PROJETO: o verificador só pode ajudar se acertar quando afirma
"esta query NÃO precisa de ferramenta". Um falso positivo aqui PIORA o sistema
(bloqueia uma chamada legítima). Por isso as regras são deliberadamente
CONSERVADORAS: na dúvida, devolve `unknown` e não interfere. A precisão real é
medida em `orchestrator/test_verifier.py` contra o holdout rotulado — sem GPU.

Reusa o validador do catálogo de `data/07_distill_agentic.py` (uma só fonte de
verdade para a regra) e o `strip_think` de `data/common.py`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import strip_think  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", ROOT / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

# ─────────────────────────── sinais de "NÃO precisa de ferramenta" ────────────
# Conservador de propósito: só dispara quando o pedido é claramente conversa,
# conhecimento/definição, opinião, ou aritmética trivial.

_SOCIAL = re.compile(
    r"^\s*(oi|ol[áa]|bom dia|boa tarde|boa noite|e a[íi]|tudo bem|obrigad[oa]|"
    r"valeu|hi|hello|good morning|thanks|thank you)\b",
    re.IGNORECASE,
)
_OPINIAO = re.compile(
    r"\b(voc[êe] (acha|prefere|gosta|recomendaria)|o que voc[êe] (acha|pensa)|"
    r"na sua opini[ãa]o|do you (think|prefer|like)|what do you think)\b",
    re.IGNORECASE,
)
# Conhecimento/definição: o modelo responde de cabeça, não consulta nada.
_CONHECIMENTO = re.compile(
    r"^\s*(o que (é|e|significa|s[ãa]o)|qual (é |e )?(a|o) (diferen[çc]a|f[óo]rmula|"
    r"conceito|defini[çc][ãa]o)|quem (escreveu|foi|inventou|criou|descobriu)|"
    r"por que|porqu[êe]|explique|explica|defina|d[êe] um exemplo|"
    r"what (is|are|does)|who (wrote|was|invented)|why (is|are|do)|explain)\b",
    re.IGNORECASE,
)
_ESCRITA_CRIATIVA = re.compile(
    r"\b(escreva (um|uma) (haiku|poema|piada|hist[óo]ria curta)|"
    r"me d[êe] (\d+ )?(ideias?|sugest[õo]es|dicas)|"
    r"write a (haiku|poem|joke|short story)|give me (\d+ )?(ideas|tips))\b",
    re.IGNORECASE,
)

# Sinais de que a query REALMENTE quer uma ação externa. Se qualquer um bater,
# NÃO declaramos "sem ferramenta" (evita falso positivo).
_ACAO_EXTERNA = re.compile(
    r"\b(busque|busca|pesquise|procure|consulte|cota[çc][ãa]o|pre[çc]o d[ao]|"
    r"previs[ãa]o do tempo|vai chover|clima em|leia o arquivo|abra o arquivo|"
    r"liste os arquivos|grave|salve|crie o arquivo|execute|rode|envie (um )?e-?mail|"
    r"agende|crie um evento|marque na agenda|traduza|resuma (a p[áa]gina|o site)|"
    r"fa[çc]a um get|requisi[çc][ãa]o|endpoint|no banco|query|sql|"
    r"search|look up|read the file|list (all )?files|run this|send an email|"
    r"schedule|translate|summarize the page|fetch)\b",
    re.IGNORECASE,
)
_MATH_TRIVIAL = re.compile(
    r"\b(quanto (é|e|vale|s[ãa]o)|calcul\w*|resolva|resolver|porcentagem|percentual|"
    r"equa[çc][ãa]o|tabuada|m[ée]dia|fra[çc][ãa]o|somat[óo]rio|"
    r"quantos?\s+\w+\s+(tem|h[áa]|existem|cabem)|"
    r"how much is|what is \d|solve|percentage|average of)\b",
    re.IGNORECASE,
)
# ⚠️ Guarda descoberta medindo: as palavras de matemática ("média", "how much is")
# aparecem em perguntas que PRECISAM de dado externo — "média de temperatura em
# São Paulo nos últimos 7 dias", "how much is a share of GOOGL right now". Sem
# esta guarda a precisão caía de 100% para 88,9% (2 falsos positivos perigosos).
# Regra: aritmética trivial só vale para cálculo AUTOCONTIDO — sem referência a
# entidade do mundo real, cotação ou instante presente.
_DADO_VIVO = re.compile(
    r"\b(agora|hoje|atual(mente)?|neste momento|right now|today|current(ly)?|"
    r"[úu]ltimos?\s+\d+\s+(dias?|horas?|meses|semanas)|last\s+\d+\s+(days?|hours?)|"
    r"temperatura|temperature|cota[çc][ãa]o|share of|a[çc][ãa]o d[aeo]|stock|"
    r"pre[çc]o (atual|d[aeo])|price of|vale (a a[çc][ãa]o|hoje))\b"
    r"|\([A-Z]{2,5}\d?\)",          # ticker entre parênteses: (GOOGL), (PETR4)
    re.IGNORECASE,
)
_TEM_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_TEM_CAMINHO = re.compile(r"(/[\w.-]+){2,}|\b[\w-]+\.(csv|txt|json|ya?ml|log|md|py|jsonl)\b",
                          re.IGNORECASE)


@dataclass
class Verdict:
    ok: bool
    violation: str | None = None     # tipo da violação (para log/estatística)
    feedback: str | None = None      # instrução corretiva para o retry
    answer: str | None = None        # resposta limpa (sem <think>)


def expected_mode(query: str) -> str:
    """'text' | 'tool' | 'unknown'. Conservador: prefere 'unknown' à aposta errada."""
    # Qualquer indício de ação externa OU de dado vivo desliga a hipótese de
    # "sem ferramenta". Ordem importa: isto roda ANTES das regras de texto.
    if (_ACAO_EXTERNA.search(query) or _TEM_URL.search(query)
            or _TEM_CAMINHO.search(query) or _DADO_VIVO.search(query)):
        return "tool"
    if _SOCIAL.search(query) or _OPINIAO.search(query) or _ESCRITA_CRIATIVA.search(query):
        return "text"
    if _CONHECIMENTO.search(query):
        return "text"
    # Aritmética: reusa a regra da destilação. Conta com número de 3+ dígitos
    # PRECISA de calculator; conta trivial NÃO precisa (e chamar é over-calling).
    if _d7.looks_like_hard_math(query):
        return "tool"
    # Vocabulário matemático AMPLO + nenhum número de 3+ dígitos => de cabeça.
    # Calibrado contra os over-calls reais observados na avaliação: "resolva a
    # equação 2x+5=15", "qual a porcentagem", "gere a tabuada do 7 até o 10".
    # Seguro porque _ACAO_EXTERNA já capturou antes tudo que pede ação externa
    # (ex.: "quantos pedidos... consulte o banco" vira 'tool' acima).
    if _MATH_TRIVIAL.search(query):
        return "text"
    return "unknown"


def verify(query: str, raw_output: str, tools: dict) -> Verdict:
    """Verifica a saída da abelha. ok=False traz feedback corretivo para o retry."""
    answer, truncated = strip_think(raw_output)
    obj = _d7.extract_json(answer)

    # (0) truncado no meio do raciocínio: não há resposta final.
    if truncated and not answer:
        return Verdict(False, "raciocinio_truncado",
                       "Responda direto, sem raciocinar em voz alta.", answer)

    # (0b) JSON cortado pelo limite de tokens: a chamada podia estar certa.
    if obj is None and answer.lstrip().startswith("{"):
        return Verdict(False, "json_truncado",
                       "Sua resposta foi cortada. Emita o JSON completo e curto, "
                       "sem conteúdo longo dentro dos args.", answer)

    exp = expected_mode(query)

    if obj is not None:
        # (1-3) é chamada de ferramenta: validar contra o catálogo.
        reason = _d7.validate_call(obj, tools)
        if reason:
            nomes = ", ".join(sorted(tools))
            return Verdict(False, "tool_invalida",
                           f"Sua chamada é inválida ({reason}). Use SOMENTE estas "
                           f"ferramentas: {nomes}. Inclua todos os args obrigatórios "
                           "e nenhum arg fora do documentado.", answer)
        # (4) ⭐ o modo bate com a intenção?
        if exp == "text":
            return Verdict(False, "over_calling",
                           "Este pedido NÃO exige ferramenta externa — é conversa, "
                           "conhecimento geral ou conta trivial. Responda direto em "
                           "texto natural, SEM JSON.", answer)
        return Verdict(True, answer=answer)

    # saída em texto
    if exp == "tool":
        return Verdict(False, "under_calling",
                       "Este pedido EXIGE uma ferramenta externa. Responda SOMENTE "
                       'com o JSON {"tool": "...", "args": {...}}, sem texto em volta.',
                       answer)
    return Verdict(True, answer=answer)
