"""Gabaritos das guardas do mundo simulado (`tools_exec.py`). Rodar antes de medir agêntico.

🔴 POR QUE ESTE ARQUIVO EXISTE — o avaliador travou de verdade

2026-08-20, durante o baseline do Bee-350M: a régua agêntica ficou **21 minutos parada** entre
os exemplos 21 e 39, com **1.604 s de CPU e 2,5 GB de working set** num único processo. O
modelo BASE gerou uma chamada de calculadora com uma potência enorme, e o avaliador foi
calcular o inteiro gigante.

⚠️ A CALCULADORA SEMPRE FOI "SEGURA", E ISSO NÃO BASTAVA. Ela usa AST em vez de `eval()`,
   então não executa código arbitrário — verdade, e irrelevante para esta falha. `9**9**9` é
   uma expressão **inteiramente válida** que exaure memória e CPU sem executar nada proibido.
   Segurança contra execução e segurança contra exaustão de recurso são ameaças diferentes, e
   o vocabulário de "sandbox seguro" tende a esconder a segunda.

⭐ E O SINTOMA NÃO ERA ERRO: era o run **parado**, indistinguível de lentidão. Quem estivesse
   olhando o log veria um número que não avança e concluiria "está devagar". Foi o monitor de
   estagnação — que dispara quando o log não cresce — que separou uma coisa da outra. Esta é a
   razão de o monitor cobrir o caso de falha, e não só o de sucesso.

⚠️ E UM BUG ANTERIOR, achado por acidente ao testar a guarda nova: `factorial` estava na tabela
   de funções desde sempre e **nunca funcionou uma única vez**. O avaliador de AST devolve
   `float`, `math.factorial` exige `int`, e toda chamada levantava `TypeError` — contado como
   falha do MODELO. Ninguém tinha executado a função.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools_exec import ErroFerramenta, _calcular  # noqa: E402

# (expressao, resultado esperado) — precisam continuar funcionando
LEGITIMOS: list[tuple[str, float]] = [
    ("2 + 3*4", 14.0),
    ("100 * 1.5", 150.0),
    ("sqrt(1444)", 38.0),
    ("2**10", 1024.0),
    ("log(e)", 1.0),
    ("factorial(10)", 3628800.0),          # nunca funcionou antes de 2026-08-20
    ("2**64", 2.0**64),                    # bem na borda da guarda: tem de PASSAR
    ("(1500 - 250) / 4", 312.5),
]

# expressoes validas que exaurem recurso — precisam ABORTAR, e rapido
PERIGOSOS: list[str] = [
    "9**9**9",
    "2**999999999",
    "10**400",
    "factorial(1000000)",
    "pow(10, 100000)",
]

LIMITE_MS = 200.0        # uma guarda que demora ja' falhou no seu proposito


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 74)
    print("GUARDAS DE EXAUSTAO DE RECURSO — tools_exec._calcular")
    print("=" * 74)
    falhas: list[str] = []

    print("-- expressoes legitimas (precisam FUNCIONAR)")
    for e, esperado in LEGITIMOS:
        t = time.time()
        try:
            r = _calcular(e)
            ms = 1000 * (time.time() - t)
            ok = abs(r - esperado) <= max(1e-6, abs(esperado) * 1e-9)
            print(f"  {'✅' if ok else '🔴'} {e:22} = {r:<22.6g} ({ms:.1f} ms)")
            if not ok:
                falhas.append(f"{e}: esperado {esperado}, obtido {r}")
        except Exception as ex:                                  # noqa: BLE001
            print(f"  🔴 {e:22} {type(ex).__name__}: {str(ex)[:40]}")
            falhas.append(f"{e}: levantou {type(ex).__name__} — {str(ex)[:60]}")

    print("\n-- expressoes que TRAVAVAM (precisam abortar rapido)")
    for e in PERIGOSOS:
        t = time.time()
        try:
            r = _calcular(e)
            print(f"  🔴 {e:22} devolveu {str(r)[:30]} — NAO abortou")
            falhas.append(f"{e}: nao abortou (devolveu resultado)")
        except ErroFerramenta as ex:
            ms = 1000 * (time.time() - t)
            marca = "✅" if ms <= LIMITE_MS else "🔴"
            print(f"  {marca} {e:22} abortou em {ms:6.1f} ms · {str(ex)[:40]}")
            if ms > LIMITE_MS:
                falhas.append(f"{e}: abortou, mas levou {ms:.0f} ms (> {LIMITE_MS:.0f})")
        except Exception as ex:                                  # noqa: BLE001
            print(f"  🔴 {e:22} excecao errada: {type(ex).__name__}")
            falhas.append(f"{e}: {type(ex).__name__} em vez de ErroFerramenta")

    print("\n" + "=" * 74)
    if falhas:
        print(f"🔴 {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"   · {f}")
        print("\nABORTADO. Nao meça agêntico com o mundo simulado nesse estado.")
        return 1
    print(f"✅ {len(LEGITIMOS)} legitimas passam · {len(PERIGOSOS)} perigosas abortam em "
          f"<{LIMITE_MS:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
