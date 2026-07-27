"""Cliente compartilhado do professor (OpenRouter).

Extraído de 01_distill_teacher.py para ser reusado pelo gerador Self-Instruct.
Concentra o tratamento de erro que já nos custou um lote inteiro:
  - OpenRouter devolve 200 com corpo de erro (rate limit / upstream fora)
  - modelos de reasoning devolvem content=None e o texto vai em 'reasoning'
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class TeacherError(RuntimeError):
    """Falha ao obter resposta do professor (HTTP, rate limit, upstream, vazio)."""


def call_teacher(
    prompt: str,
    teacher: str,
    api_key: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = 180,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = json.dumps(
        {
            "model": teacher,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise TeacherError(f"HTTP {e.code}: {detail}") from e

    if "choices" not in payload:
        err = payload.get("error") or payload
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise TeacherError(f"resposta sem 'choices': {msg}")

    choices = payload.get("choices") or []
    if not choices:
        raise TeacherError("lista 'choices' vazia")

    msg_obj = choices[0].get("message") or {}
    content = msg_obj.get("content")
    if not content:
        content = msg_obj.get("reasoning") or msg_obj.get("reasoning_content")
    if not content or not content.strip():
        raise TeacherError(f"conteudo vazio (finish_reason={choices[0].get('finish_reason', '?')})")

    return content.strip()
