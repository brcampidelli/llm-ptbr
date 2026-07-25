"""COMEIA — registry das abelhas (data-driven).

Cada "abelha" é uma especialização. Na arquitetura da comeia, quase toda abelha é
um ADAPTER LoRA sobre UM backbone Qwen3.5-4B carregado uma vez (hot-swap) — o que
resolve VRAM e coordenação de uma vez. A exceção é a abelha multimodal (~9B, modelo
separado), que entra numa fase posterior.

O registry vive em `orchestrator/bees.json` (versionável). Adicionar uma abelha =
editar o JSON, sem tocar no código. Campos por abelha:

    name          identificador único (ex.: "chat_ptbr", "agentica", "coder")
    description   1 linha do foco da abelha
    adapter_path  caminho do adapter LoRA; null = usa o backbone base direto
    triggers      regex (IGNORECASE) que ativam a abelha no roteador
    fast_path     True = abelha barata (evita o modelo caro) → conta na métrica-chave
    system_prompt system message opcional injetado antes da query
    priority      menor = avaliado antes no roteador (desempate de triggers)

O JSON também declara:
    backbone      modelo base (HF id) — o único carregado de fato para os adapters
    default_bee   abelha catch-all barata quando nenhum trigger casa e a query é simples
    fallback_bee  abelha para o raciocínio residual difícil (base 4B hoje; 7-11B/nuvem depois)
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = Path(__file__).resolve().parent / "bees.json"


@dataclass
class Bee:
    name: str
    description: str
    adapter_path: str | None
    triggers: list[str] = field(default_factory=list)
    fast_path: bool = True
    system_prompt: str | None = None
    priority: int = 100
    # regex compilados (preenchido no __post_init__)
    _patterns: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._patterns = [re.compile(t, re.IGNORECASE) for t in self.triggers]

    def matches(self, query: str) -> bool:
        return any(p.search(query) for p in self._patterns)


@dataclass
class Registry:
    backbone: str
    bees: dict[str, Bee]
    default_bee: str
    fallback_bee: str

    def get(self, name: str) -> Bee:
        if name not in self.bees:
            raise KeyError(f"abelha desconhecida: {name!r} (tem: {list(self.bees)})")
        return self.bees[name]

    def specialized(self) -> list[Bee]:
        """Abelhas com trigger, ordenadas por prioridade (para o roteador)."""
        special = [b for b in self.bees.values()
                   if b.name not in (self.default_bee, self.fallback_bee)]
        return sorted(special, key=lambda b: b.priority)


def _expand(path: str | None) -> str | None:
    """Resolve ${VAR} e ~ nos caminhos de adapter (Drive no Colab vs local)."""
    if not path:
        return None
    return os.path.expanduser(os.path.expandvars(path))


def load_registry(path: Path | str = DEFAULT_REGISTRY) -> Registry:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))  # utf-8-sig: tolera BOM
    bees: dict[str, Bee] = {}
    for b in data["bees"]:
        bee = Bee(
            name=b["name"],
            description=b.get("description", ""),
            adapter_path=_expand(b.get("adapter_path")),
            triggers=b.get("triggers", []),
            fast_path=b.get("fast_path", True),
            system_prompt=b.get("system_prompt"),
            priority=b.get("priority", 100),
        )
        bees[bee.name] = bee
    reg = Registry(
        backbone=data.get("backbone", "Qwen/Qwen3.5-4B"),
        bees=bees,
        default_bee=data["default_bee"],
        fallback_bee=data["fallback_bee"],
    )
    # sanidade: default/fallback precisam existir
    for key in (reg.default_bee, reg.fallback_bee):
        if key not in reg.bees:
            raise ValueError(f"registry aponta para abelha inexistente: {key!r}")
    return reg
