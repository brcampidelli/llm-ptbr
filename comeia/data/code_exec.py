"""Execução isolada de código Python — o JUIZ da abelha coder.

A vantagem desta abelha sobre a agêntica: o veredito não vem de um LLM juiz, vem
do INTERPRETADOR. "A função passa nos testes?" é objetivo, barato e não alucina.

⚠️ SEGURANÇA — estamos executando código gerado por modelo. Mitigações aqui:
  - subprocess separado (não `exec` no nosso processo);
  - timeout duro (mata loop infinito);
  - sys.executable com -I (isolated: ignora env/site-packages do usuário);
  - cwd num diretório temporário descartável;
  - lista de padrões proibidos barrada ANTES de executar (rede, subprocess, fs
    fora do temp, os.system...). É defesa em profundidade, não sandbox real.
NÃO use isto para executar código de fonte não confiável. Aqui a fonte é um
professor aberto resolvendo exercícios de função pura — risco baixo, mas real.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Padrões que não têm o que fazer numa função pura de exercício.
_PROIBIDO = re.compile(
    r"\b(import\s+(os|sys|subprocess|socket|shutil|requests|urllib|http|ftplib|"
    r"smtplib|ctypes|multiprocessing|pathlib)|from\s+(os|sys|subprocess|socket|"
    r"shutil|requests|urllib|ctypes)\s+import|__import__|eval\s*\(|exec\s*\(|"
    r"compile\s*\(|open\s*\(|input\s*\(|globals\s*\(|locals\s*\()",
    re.IGNORECASE,
)

TIMEOUT_DEFAULT = 8


@dataclass
class ExecResult:
    ok: bool
    reason: str = ""          # "" quando ok; senão o motivo da falha
    stderr: str = ""


def scan_forbidden(code: str) -> str | None:
    """Retorna o trecho proibido encontrado, ou None se limpo."""
    m = _PROIBIDO.search(code)
    return m.group(0) if m else None


def run_tests(code: str, tests: list[str], timeout: int = TIMEOUT_DEFAULT,
              allow_forbidden: bool = False) -> ExecResult:
    """Executa `code` + asserts de `tests`. ok=True só se TODOS passarem."""
    if not code.strip():
        return ExecResult(False, "codigo vazio")
    if not allow_forbidden:
        bad = scan_forbidden(code)
        if bad:
            return ExecResult(False, f"padrao proibido: {bad!r}")

    script = code + "\n\n# --- testes ---\n" + "\n".join(tests) + "\nprint('__OK__')\n"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "cand.py"
        f.write_text(script, encoding="utf-8")
        try:
            p = subprocess.run(
                [sys.executable, "-I", str(f)],
                capture_output=True, text=True, timeout=timeout, cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(False, f"timeout ({timeout}s) — possivel loop infinito")
        except Exception as e:                                   # noqa: BLE001
            return ExecResult(False, f"falha ao executar: {type(e).__name__}")

    if "__OK__" in p.stdout:
        return ExecResult(True)
    err = (p.stderr or "").strip().splitlines()
    last = err[-1] if err else "sem stderr"
    kind = "assert falhou" if "AssertionError" in (p.stderr or "") else "erro de execucao"
    return ExecResult(False, f"{kind}: {last[:160]}", p.stderr[-400:] if p.stderr else "")


def extract_code(text: str) -> str:
    """Tira o código de uma resposta de modelo (cerca ```python ... ``` ou cru)."""
    fence = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    # sem cerca: se parece código (tem def/import/return), devolve como está
    if re.search(r"^\s*(def |class |import |from )", text, re.MULTILINE):
        return text.strip()
    return ""
