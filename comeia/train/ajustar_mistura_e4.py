"""E4 — ajusta a lei de escala por domínio e resolve a mistura ótima (arXiv:2508.11953).

    L_i(N_i, |D_∖i|) = C_i · (N_i + k_i · |D_∖i|^α_i)^(−β_i) + E_i

`N_i` = tokens do domínio i na mistura · `|D_∖i|` = tokens de todos os outros ·
`k_i·|D_∖i|^α_i` = **transferência** dos outros domínios para o i.

---

🔴 A ARMADILHA DOS GRAUS DE LIBERDADE, QUE ESTE PROJETO JÁ PAGOU UMA VEZ

São **5 parâmetros por domínio** (C, k, α, β, E) e cada domínio tem **5 perturbações**. Ajustar
os 5 pontos do próprio domínio dá **grau de liberdade zero**: a curva passa exato por
construção e não sobra resíduo para conferir. A lição do projeto é literal sobre isso —
*"ajuste com graus de liberdade zero descreve, não valida"*.

⭐ **A saída está na própria matriz de runs.** Quando OUTRO domínio é perturbado, o `|D_∖i|` do
domínio *i* muda enquanto o `N_i` dele fica na base. Então cada domínio tem os **40 runs** como
dado, não 5:

| runs | o que varia para o domínio *i* |
|---|---|
| 5 (i perturbado) | `N_i` varia, `|D_∖i|` constante — identifica **β_i** e **C_i** |
| 35 (outros perturbados) | `N_i` constante, `|D_∖i|` varia — identifica **k_i** e **α_i** |

Com 40 pontos e 5 parâmetros sobram **35 graus de liberdade**, e aí o resíduo diz alguma coisa.
⚠️ Ajustar cada domínio só contra os 5 dele é o erro fácil, e ele não dá erro nenhum: produz
parâmetros, produz mistura, e a mistura é ficção.

---

⭐ E A ADAPTAÇÃO QUE O BEE PODE FAZER E O PAPER NÃO PODIA

O paper ajusta contra **loss de validação** e avisa que ela pode não transferir para desempenho
downstream (positiva no Tulu3, *"discrepância importante"* no Orca). Como aqui a avaliação
downstream custa minutos, a MESMA forma é ajustada **duas vezes** — contra a loss e contra a
métrica da régua — e os dois ótimos vão lado a lado. Se discordarem, a discordância é o
resultado, e a regra do projeto diz qual vale.

⚠️ **Teto por domínio na otimização.** A restrição de simplex não basta: `texto` e `simbolico`
são o dado original do Bee e não crescem. Num orçamento de 20M tokens eles podem ser no máximo
8% e 7% da mistura. Sem o teto, a "mistura ótima" é receita que não dá para cozinhar.

Uso:
    python comeia/train/ajustar_mistura_e4.py --autoteste
    python comeia/train/ajustar_mistura_e4.py --metrica agentico --alvo-tokens 20000000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
RESULTADO = RAIZ / "docs" / "grid-e4-resultado.json"
AVALIADO = RAIZ / "docs" / "grid-e4-avaliado.json"
SAIDA = RAIZ / "docs" / "grid-e4-mistura.json"

NOMES = ["C", "k", "alpha", "beta", "E"]


def lei(p, N, D_out):
    """C·(N + k·|D_∖i|^α)^(−β) + E, em log para o ajuste não estourar."""
    import numpy as np
    C, k, alpha, beta, E = p
    efetivo = N + k * np.power(np.maximum(D_out, 1.0), alpha)
    return C * np.power(np.maximum(efetivo, 1.0), -beta) + E


def ajustar(N, D_out, y):
    """Ajusta os 5 parâmetros por mínimos quadrados robusto (Huber + região de confiança).

    ⚠️ Huber e não quadrático puro: um mini-run que deu errado por acaso (OOM, dado ruim)
    puxaria a curva inteira sob perda quadrática. Com Huber ele vira ponto de peso baixo em
    vez de virar a lei.
    """
    import numpy as np
    from scipy.optimize import least_squares

    def residuo(p):
        return lei(p, N, D_out) - y

    melhor, melhor_custo = None, np.inf
    # ⚠️ multi-start: a superficie tem minimos locais, e um unico chute produz "o ajuste
    #    convergiu" com parametros que nao descrevem nada.
    for C0 in (1.0, 10.0, 100.0):
        for beta0 in (0.1, 0.3, 0.6):
            p0 = np.array([C0, 1.0, 0.5, beta0, float(np.min(y))])
            try:
                r = least_squares(residuo, p0, loss="huber", method="trf",
                                  bounds=([1e-6, 0.0, 0.0, 1e-3, -10.0],
                                          [1e6, 1e6, 2.0, 3.0, 10.0]),
                                  max_nfev=20000)
            except Exception:
                continue
            if r.cost < melhor_custo:
                melhor, melhor_custo = r, r.cost
    return melhor


def qualidade(N, D_out, y, p):
    import numpy as np
    pred = lei(p, N, D_out)
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    gl = len(y) - len(p)
    return {"r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "rmse": float(np.sqrt(ss_res / len(y))),
            "graus_de_liberdade": gl,
            "n_pontos": len(y)}


def otimizar(params: dict, alvo_tokens: int, tetos: dict, maximizar: bool,
             escala: dict | None = None, importancia: dict | None = None):
    """Resolve os pesos por SLSQP sob simplex + teto por dominio.

    🔴 SOMAR METRICA CRUA ENTRE DOMINIOS DEIXA A DECISAO COM A REGUA DE MAIOR NUMERO.
    Medido no autoteste do otimizador: com dois dominios de mesma forma mas escalas
    diferentes, o de loss absoluta ~44 dominou a soma e o de loss ~1,2 — que RESPONDIA MUITO
    MAIS a volume — recebeu 1,7% do orcamento. O otimizador estava certo e a funcao-objetivo,
    errada.

    E no E4 real e' pior, porque as reguas nem sao comensuraveis: BLEU vai a ~50, execucao
    agentica e IFEval vao a 100, loss fica abaixo de 3. Somar cru daria a mistura a quem tem
    a escala maior.

    ⭐ Correcao em dois passos:
      1. **escala** — cada dominio e' normalizado pela amplitude observada dele nos mini-runs,
         entao o objetivo mede *fracao da variacao alcancavel*, nao unidade bruta;
      2. **importancia** — peso explicito por capacidade. Quanto o agentico vale contra o
         resumo NAO e' pergunta de matematica, e' decisao de produto. Fica visivel e
         parametrizavel em vez de escondida na escala da metrica.
    """
    import numpy as np
    from scipy.optimize import minimize

    doms = list(params)
    k = len(doms)
    escala = escala or {}
    importancia = importancia or {}

    def objetivo(w):
        total = 0.0
        for i, d in enumerate(doms):
            N = w[i] * alvo_tokens
            D_out = (1.0 - w[i]) * alvo_tokens
            v = float(lei(params[d], np.array([N]), np.array([D_out]))[0])
            amp = escala.get(d) or 1.0
            imp = importancia.get(d, 1.0)
            total += imp * ((-v if maximizar else v) / amp)
        return total

    restr = [{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}]
    limites = [(0.0, min(1.0, tetos.get(d, 1.0))) for d in doms]
    # ⚠️ se a soma dos tetos for < 1 o simplex e' inviavel — e' sinal de que falta DADO, nao
    #    de que o otimizador falhou.
    if sum(hi for _, hi in limites) < 1.0:
        return None, ("a soma dos tetos e' menor que 1: nao ha' dado suficiente para "
                      "preencher o orcamento-alvo. Reduza --alvo-tokens ou gere dado.")
    w0 = np.array([min(1.0 / k, tetos.get(d, 1.0)) for d in doms])
    w0 = w0 / w0.sum()
    r = minimize(objetivo, w0, method="SLSQP", bounds=limites, constraints=restr,
                 options={"maxiter": 1000, "ftol": 1e-12})
    return {d: float(w) for d, w in zip(doms, r.x)}, None


def autoteste() -> int:
    """Gera dado sintético de parâmetros CONHECIDOS e confere se o ajuste os recupera.

    🔴 Sem isto, "o ajuste convergiu" não significa nada. O projeto já produziu duas
    conclusões a partir de aparato defeituoso; ajustar 5 parâmetros por domínio é exatamente
    o tipo de código que produz números plausíveis estando errado.
    """
    import numpy as np
    rng = np.random.default_rng(20260821)
    verdade = {"A": [50.0, 2.0, 0.5, 0.35, 1.20],
               "B": [120.0, 0.5, 0.7, 0.50, 0.80],
               "C": [20.0, 5.0, 0.3, 0.25, 1.50]}
    doms = list(verdade)
    base = 450_000.0
    razoes = [0.5, 0.67, 1.0, 2.0, 3.0]
    # matriz de runs igual a real: um dominio perturbado por vez
    runs = []
    for alvo in doms:
        for r in razoes:
            n = {d: base * (r if d == alvo else 1.0) for d in doms}
            runs.append(n)
    print("=" * 76)
    print("AUTOTESTE — recupera parametros conhecidos?")
    print("=" * 76)
    print(f"{len(runs)} runs sinteticos · {len(doms)} dominios · 5 parametros cada")
    ok = True
    for d in doms:
        N = np.array([r[d] for r in runs])
        D_out = np.array([sum(v for kk, v in r.items() if kk != d) for r in runs])
        y = lei(verdate := verdade[d], N, D_out)
        y = y + rng.normal(0, 0.002, size=len(y))     # ruido realista de medicao
        fit = ajustar(N, D_out, y)
        q = qualidade(N, D_out, y, fit.x)
        pred_v = lei(verdate, N, D_out)
        erro = float(np.max(np.abs(lei(fit.x, N, D_out) - pred_v)))
        marca = "✅" if erro < 0.01 and q["graus_de_liberdade"] > 0 else "🔴"
        if marca == "🔴":
            ok = False
        print(f"  {marca} dominio {d}: R2 {q['r2']:.4f} · RMSE {q['rmse']:.5f} · "
              f"gl {q['graus_de_liberdade']} · erro maximo na curva {erro:.5f}")
    print()
    print("⚠️ O teste checa se a CURVA foi recuperada, nao os 5 parametros um a um: a forma")
    print("   tem degenerescencia (C e k trocam-se parcialmente), e exigir cada parametro")
    print("   isolado reprovaria um ajuste que preve certo — que e' o que interessa.")

    # ---- parte 2: o OTIMIZADOR, que falhou de um jeito silencioso na primeira versao
    print()
    print("=" * 76)
    print("AUTOTESTE DO OTIMIZADOR — normalizacao e teto")
    print("=" * 76)
    ps = {"responde_muito": np.array([50.0, 2.0, 0.5, 0.60, 1.20]),
          "responde_pouco": np.array([50.0, 2.0, 0.5, 0.20, 1.20]),
          "nao_responde": np.array([50.0, 2.0, 0.5, 0.01, 1.20])}
    ALVO = 20_000_000
    esc = {}
    for d, pp in ps.items():
        lo = float(lei(pp, np.array([0.1 * ALVO]), np.array([0.9 * ALVO]))[0])
        hi = float(lei(pp, np.array([0.9 * ALVO]), np.array([0.1 * ALVO]))[0])
        esc[d] = abs(hi - lo) or 1.0
    cru, _ = otimizar(ps, ALVO, {}, False)
    nor, _ = otimizar(ps, ALVO, {}, False, escala=esc)
    tet, _ = otimizar(ps, ALVO, {"responde_muito": 0.10}, False, escala=esc)
    _, err = otimizar(ps, ALVO, {d: 0.2 for d in ps}, False, escala=esc)
    a1 = cru["responde_muito"] < 0.05      # o problema, reproduzido
    a2 = nor["responde_muito"] > 0.20      # a correcao
    a3 = abs(tet["responde_muito"] - 0.10) < 1e-3 and abs(sum(tet.values()) - 1) < 1e-6
    a4 = err is not None
    for marca, txt in ((a1, "soma crua REPRODUZ o problema (responsivo abaixo de 5%)"),
                       (a2, "normalizacao CORRIGE (responsivo acima de 20%)"),
                       (a3, "teto respeitado e simplex fechado em 1,0"),
                       (a4, "tetos somando < 1 sao RECUSADOS, nao inventados")):
        print(f"  {'✅' if marca else '🔴'} {txt}")
    ok = ok and a1 and a2 and a3 and a4
    return 0 if ok else 1


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--avaliado", type=Path, default=AVALIADO)
    ap.add_argument("--metrica", default="loss",
                    help="'loss' (menor e' melhor) ou o nome de uma regua (maior e' melhor)")
    ap.add_argument("--alvo-tokens", type=int, default=20_000_000)
    ap.add_argument("--importancia", default="",
                    help='peso por capacidade em JSON, ex: {"agentico_pos":2}. '
                         "Quanto o agentico vale contra o resumo e' decisao de produto, "
                         "nao de matematica — fica explicito em vez de escondido na escala.")
    a = ap.parse_args()

    if a.autoteste:
        return autoteste()

    import numpy as np
    if not a.avaliado.exists():
        print(f"🔴 {a.avaliado} nao existe — avalie os mini-runs antes de ajustar.",
              file=sys.stderr)
        return 1
    dados = json.loads(a.avaliado.read_text(encoding="utf-8"))
    runs = dados["runs"]
    doms = sorted({d for v in runs.values() for d in v["composicao"]})

    print("=" * 78)
    print(f"AJUSTE DA LEI DE ESCALA — metrica: {a.metrica}")
    print("=" * 78)
    maximizar = a.metrica != "loss"
    params, diag = {}, {}
    for d in doms:
        N, D_out, y = [], [], []
        for v in runs.values():
            if "erro" in v or a.metrica not in (v.get("metricas") or {}):
                continue
            comp = v["composicao"]
            n_i = comp.get(d, {}).get("tokens", 0)
            N.append(n_i)
            D_out.append(sum(c["tokens"] for k2, c in comp.items() if k2 != d))
            y.append(v["metricas"][a.metrica])
        if len(y) < 8:
            print(f"  ⚠️ {d}: so' {len(y)} pontos — pulado")
            continue
        N, D_out, y = np.array(N, float), np.array(D_out, float), np.array(y, float)
        fit = ajustar(N, D_out, y)
        params[d] = fit.x
        q = qualidade(N, D_out, y, fit.x)
        diag[d] = q
        marca = "✅" if q["graus_de_liberdade"] > 0 and q["r2"] > 0.5 else "⚠️"
        print(f"  {marca} {d:14} R2 {q['r2']:>7.4f} · RMSE {q['rmse']:.5f} · "
              f"{q['n_pontos']} pontos, gl {q['graus_de_liberdade']}")

    tetos = {}
    inv = dados.get("inventario", {})
    for d in params:
        disp = inv.get(d, {}).get("tokens", 0)
        tetos[d] = min(1.0, disp / a.alvo_tokens) if disp else 1.0

    # amplitude OBSERVADA por dominio: o quanto a metrica dele de fato variou entre os
    # mini-runs. E' a normalizacao que impede a regua de maior escala de decidir a mistura.
    escala = {}
    for d in params:
        ys = [v["metricas"][a.metrica] for v in runs.values()
              if "erro" not in v and a.metrica in (v.get("metricas") or {})]
        escala[d] = (max(ys) - min(ys)) or 1.0
    importancia = json.loads(a.importancia) if a.importancia else None
    pesos, erro = otimizar(params, a.alvo_tokens, tetos, maximizar, escala, importancia)
    print()
    if erro:
        print(f"🔴 {erro}")
        return 2
    print(f"mistura otima para {a.alvo_tokens:,} tokens (metrica {a.metrica}):")
    for d, w in sorted(pesos.items(), key=lambda kv: -kv[1]):
        no_teto = " ← NO TETO (falta dado)" if abs(w - tetos[d]) < 1e-4 else ""
        print(f"  {d:14} {100*w:>6.2f}%  ({int(w*a.alvo_tokens):>10,} tokens)"
              f"{no_teto}")
    SAIDA.write_text(json.dumps({"metrica": a.metrica, "alvo_tokens": a.alvo_tokens,
                                 "pesos": pesos, "tetos": tetos,
                                 "diagnostico": diag,
                                 "parametros": {d: dict(zip(NOMES, map(float, v)))
                                                for d, v in params.items()}},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
