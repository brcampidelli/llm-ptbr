"""Catálogo de ferramentas da abelha agêntica — FONTE ÚNICA DA VERDADE.

Por que este módulo existe: o system prompt da agêntica era construído em
`07_distill_agentic.py` (destilação/treino) e escrito À MÃO, resumido, no
`orchestrator/bees.json` (produção). Duas fontes → elas divergiram: a versão de
produção não listava ferramenta nenhuma, e mesmo assim pedia um tool-call. A
abelha era treinada com o catálogo à vista e servida às cegas.

Agora treino, avaliação e produção importam a MESMA função daqui. Editar
`agentic_tools.json` muda os três de uma vez — não há como divergirem de novo.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
TOOLS_FILE = DATA_DIR / "agentic_tools.json"


def load_tools(path: Path | str = TOOLS_FILE) -> dict:
    """Catalogo {nome: spec}. Mesma fonte para o prompt E para a validação."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return {t["name"]: t for t in data["tools"]}


def tools_prompt(tools: dict) -> str:
    """Renderiza o catálogo para dentro do system prompt."""
    lines = []
    for spec in tools.values():
        req = ", ".join(spec.get("required", [])) or "(nenhum)"
        args = ", ".join(f"{k} ({v})" for k, v in spec.get("args", {}).items())
        lines.append(f"- {spec['name']}: {spec['description']}\n"
                     f"    args: {args}\n    obrigatorios: {req}")
    return "\n".join(lines)


def build_system(tools: dict | None = None) -> str:
    """O system prompt EXATO com que a abelha agêntica foi treinada.

    A regra 7 (idioma) não é decoração: é o que fez o comportamento agêntico
    atravessar inglês/espanhol/francês sem ter sido treinado neles (24/24 no
    teste multilíngue). Mexer nela sem medir é desfazer esse resultado.
    """
    tools = load_tools() if tools is None else tools
    return (
        "Você é um assistente AGÊNTICO. Você tem acesso às ferramentas abaixo.\n\n"
        f"FERRAMENTAS DISPONÍVEIS:\n{tools_prompt(tools)}\n\n"
        "REGRAS (siga à risca):\n"
        "1. Se o pedido EXIGE uma ferramenta, responda SOMENTE com um JSON, sem texto "
        'antes ou depois, no formato: {"tool": "nome_da_ferramenta", "args": {...}}\n'
        "2. Use APENAS ferramentas da lista. Use APENAS os args documentados. "
        "Inclua todos os args obrigatórios.\n"
        "3. Se o pedido NÃO precisa de ferramenta (conversa, conhecimento geral, opinião, "
        "explicação), responda direto em texto natural, SEM JSON.\n"
        "3b. ARITMÉTICA: só faça de cabeça contas com números de 1 ou 2 dígitos "
        "(ex: 2+2, 15% de 200). QUALQUER conta com número de 3 dígitos ou mais "
        "(multiplicação, divisão, raiz, potência) DEVE usar a ferramenta calculator. "
        "Não arrisque errar uma conta que a ferramenta faz exata.\n"
        "4. Se o pedido for AMBÍGUO ou faltar informação obrigatória, responda em texto "
        "pedindo exatamente o que falta. NÃO invente valores.\n"
        "5. Ação irreversível (enviar e-mail) só com pedido explícito e dados completos.\n"
        "6. Se a tarefa exigir várias etapas, chame APENAS a PRIMEIRA ferramenta.\n"
        "7. Texto em português brasileiro, exceto se o usuário escrever em outro idioma."
    )
