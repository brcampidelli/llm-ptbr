"""COMEIA — roteador deterministico + a metrica-chave (fracao de fast-path).

Topologia "Code Agency" (NVIDIA): o orquestrador e CODIGO, nao um LLM gigante.
Este roteador decide qual abelha atende cada query:

  1. Trigger match: se uma abelha especializada (agentica/coder/...) casa por regex,
     roteia para ela (na ordem de prioridade do registry).
  2. Senao, heuristica de complexidade:
       - query "dificil"  -> fallback_bee (raciocinio residual; NAO e fast-path)
       - query "simples"  -> default_bee (chat barato; e fast-path)

⭐ METRICA QUE DECIDE A COMEIA: a *fracao de fast-path* — quantas queries evitam o
modelo caro (o fallback). Alta => a comeia e economica. Baixa => e so complexidade.
O Router acumula essa estatistica em toda rota.

A heuristica de complexidade aqui e um PLACEHOLDER honesto (regras + tamanho). A
Fase 3 do plano troca isso por um classificador pequeno treinado nos clusters de
tarefa (passo S3/S6 da NVIDIA). Ate la, e transparente e barato.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from registry import Registry

# Sinais de que a query exige raciocinio dificil -> vai para o fallback (modelo caro).
_HARD_MARKERS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(prove|demonstre|deduza|derive)\b",
        r"\bpasso a passo\b",
        r"\b(detalhadamente|minuciosamente|rigorosamente)\b",
        r"\b(analise|explique)\b.{0,30}\b(profund|a fundo|em detalhe)",
        r"\b(compare|contraste)\b.{0,60}\b(justif|argument|trade[- ]?off)",
        r"\bmulti[- ]?passo",
        r"\bprova\b.{0,20}\bmatematic",
    ]
]
_HARD_WORDS = 80   # queries muito longas tendem a exigir mais raciocinio


@dataclass
class RouteDecision:
    bee_name: str
    fast_path: bool
    reason: str


class Router:
    def __init__(self, registry: Registry) -> None:
        self.reg = registry
        self.n_total = 0
        self.n_fast = 0
        self.by_bee: Counter[str] = Counter()

    # ---- decisao -------------------------------------------------------------
    def _is_hard(self, query: str) -> bool:
        if len(query.split()) > _HARD_WORDS:
            return True
        return any(p.search(query) for p in _HARD_MARKERS)

    def decide(self, query: str) -> RouteDecision:
        # 1) trigger de abelha especializada (ordem de prioridade)
        for bee in self.reg.specialized():
            if bee.matches(query):
                return RouteDecision(bee.name, bee.fast_path,
                                     f"trigger da abelha '{bee.name}'")
        # 2) heuristica de complexidade
        if self._is_hard(query):
            bee = self.reg.get(self.reg.fallback_bee)
            return RouteDecision(bee.name, bee.fast_path,
                                 "query dificil -> fallback (raciocinio residual)")
        bee = self.reg.get(self.reg.default_bee)
        return RouteDecision(bee.name, bee.fast_path,
                             "query simples -> abelha default (fast-path)")

    def route(self, query: str) -> RouteDecision:
        """Decide E contabiliza a estatistica (use este no loop de producao)."""
        d = self.decide(query)
        self.n_total += 1
        if d.fast_path:
            self.n_fast += 1
        self.by_bee[d.bee_name] += 1
        return d

    # ---- metrica -------------------------------------------------------------
    def fast_path_fraction(self) -> float:
        return self.n_fast / self.n_total if self.n_total else 0.0

    def summary(self) -> str:
        frac = self.fast_path_fraction()
        lines = [
            "=" * 60,
            f"⭐ FRACAO DE FAST-PATH: {frac:.1%}  ({self.n_fast}/{self.n_total})",
            "   (alta = comeia economica; baixa = so complexidade)",
            "-" * 60,
            "distribuicao por abelha:",
        ]
        for name, n in self.by_bee.most_common():
            lines.append(f"   {name:<14} {n:>4}  ({n / self.n_total:.0%})")
        lines.append("=" * 60)
        return "\n".join(lines)
