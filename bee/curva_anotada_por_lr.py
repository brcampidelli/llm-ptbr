"""A curva de bpb do Bee-150M anotada pelo LR de cada marco — o teste do artefato.

⭐ POR QUE ESTE SCRIPT EXISTE
  O projeto usou "a curva ainda descia no fim" como argumento a favor de comprar mais
  tokens para o Bee-350M. A refutacao adversarial (docs/estudo-bee-350m.md §4.2, item 5)
  contestou: a curva **ACELERA** para baixo, e nenhuma lei de escala faz isso —

      L(D) = E + A·D^-α   =>   dL/d(ln D) = -αA·D^-α

  cuja MAGNITUDE cai monotonicamente com D. Lei de escala **desacelera**, sempre.
  Aceleracao no fim e' assinatura de **decaimento de LR**: os checkpoints intermediarios
  carregam LR ainda alto e estao sistematicamente penalizados, enquanto o ponto final
  colhe o decaimento inteiro. Extrapolar a inclinacao final para 30B SUPERESTIMA o ganho.

⚠️ O QUE ESTE SCRIPT PODE E O QUE NAO PODE
  NAO pode re-medir: os checkpoints intermediarios do 150M nao estao em disco, e remedir
  exigiria retreinar (~US$ 218). O que ele faz e' ANOTAR a curva ja medida com o LR que
  cada marco tinha, e testar se a aceleracao coincide com a queda do LR. Isso decide se o
  argumento "a curva ainda descia" pode ou nao ser usado. Custo: US$ 0.

Uso:
    python bee/curva_anotada_por_lr.py
"""

from __future__ import annotations

import math
import sys

# Curva medida do Bee-150M — mesmo holdout e mesmo procedimento em todos os pontos.
# Fonte: README.md, secao "Curva medida".
MARCOS = [(1e9, 1.021), (3e9, 0.947), (6e9, 0.920), (10e9, 0.897),
          (15e9, 0.870), (21e9, 0.845), (21.75e9, 0.844)]

# O 150M rodou COSINE de 3e-3 ate 10% disso, sobre 21,75B tokens, warmup de 2%.
LR_MAX, LR_MIN_FRAC, TOTAL, WARMUP_FRAC = 3e-3, 0.1, 21.75e9, 0.02


def lr_no_ponto(D: float) -> float:
    """LR do cosine no instante em que o marco D foi salvo."""
    w = TOTAL * WARMUP_FRAC
    if D < w:
        return LR_MAX * D / w
    prog = (D - w) / (TOTAL - w)
    return LR_MAX * (LR_MIN_FRAC + (1 - LR_MIN_FRAC) * 0.5 * (1 + math.cos(math.pi * prog)))


def ajustar_lei(pontos):
    """Ajusta L = E + A·D^-α por busca em α (E e A saem por minimos quadrados em 1/D^α)."""
    melhor = None
    for i in range(1, 2000):
        a = i * 0.001
        xs = [d ** -a for d, _ in pontos]
        ys = [l for _, l in pontos]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        if den <= 0:
            continue
        A = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        E = my - A * mx
        sse = sum((E + A * x - y) ** 2 for x, y in zip(xs, ys))
        if melhor is None or sse < melhor[0]:
            melhor = (sse, a, A, E)
    return melhor


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 78)
    print("CURVA DE bpb DO BEE-150M, ANOTADA PELO LR DE CADA MARCO")
    print("=" * 78)
    print(f"  {'tokens':>8} {'bpb':>7} {'LR no ponto':>13} {'% do pico':>10} "
          f"{'inclinacao dL/dlnD':>20}")
    ant = None
    inclinacoes = []
    for D, L in MARCOS:
        lr = lr_no_ponto(D)
        inc = ""
        if ant:
            s_ = (L - ant[1]) / (math.log(D) - math.log(ant[0]))
            inclinacoes.append((ant[0], D, s_))
            inc = f"{s_:+.4f}"
        print(f"  {D/1e9:>7.2f}B {L:>7.3f} {lr:>13.3e} {100*lr/LR_MAX:>9.1f}% {inc:>20}")
        ant = (D, L)

    print("\n" + "-" * 78)
    print("A LEI DE ESCALA EXIGE QUE |dL/dlnD| CAIA MONOTONICAMENTE. Ela cai?")
    print("-" * 78)
    viola = 0
    for i in range(1, len(inclinacoes)):
        d0, d1, s0 = inclinacoes[i - 1]
        e0, e1, s1 = inclinacoes[i]
        marca = "🔴 ACELEROU" if abs(s1) > abs(s0) + 1e-9 else "✅ desacelerou"
        viola += abs(s1) > abs(s0) + 1e-9
        print(f"  {d0/1e9:>5.0f}→{d1/1e9:<5.0f} |{abs(s0):.4f}|   vs   "
              f"{e0/1e9:>5.0f}→{e1/1e9:<5.0f} |{abs(s1):.4f}|   {marca}")

    print()
    if viola:
        print(f"🔴 {viola} trechos ACELERAM. Nenhum L=E+A·D^-α com E>=0 e α>0 produz isso.")
        print("   A refutacao esta CONFIRMADA por conta propria: a inclinacao final NAO e' a")
        print("   lei de escala do dado.")
    else:
        print("🟢 a curva desacelera em todo o dominio — comportamento de lei de escala.")

    # ---- a aceleracao coincide com a queda do LR?
    print("\n" + "-" * 78)
    print("A ACELERACAO COINCIDE COM A QUEDA DO LR?")
    print("-" * 78)
    pares = [(0.5 * (a + b), abs(s), 0.5 * (lr_no_ponto(a) + lr_no_ponto(b)))
             for a, b, s in inclinacoes]

    def pearson(ps):
        n = len(ps)
        if n < 3:
            return None
        mi = sum(p[1] for p in ps) / n
        ml = sum(p[2] for p in ps) / n
        num = sum((p[1] - mi) * (p[2] - ml) for p in ps)
        den = math.sqrt(sum((p[1] - mi) ** 2 for p in ps) * sum((p[2] - ml) ** 2 for p in ps))
        return num / den if den else 0.0

    for dm, inc, lr in pares:
        print(f"  ~{dm/1e9:>5.1f}B   |inclinacao| {inc:.4f}   LR medio {lr:.3e}")

    r_tudo = pearson(pares)
    # ⚠️ A CORRELACAO GLOBAL NAO SIGNIFICA NADA AQUI, e reportar so ela seria enganoso.
    # Dois mecanismos DIFERENTES produzem inclinacao alta, em pontas opostas da curva:
    #   - inicio: aprendizado rapido sobre pesos aleatorios (LR ALTO, inclinacao ALTA)
    #   - fim:    decaimento de LR (LR BAIXO, inclinacao ALTA)
    # Jogar os dois no mesmo Pearson faz um cancelar o outro e devolve r ~ 0 — que e'
    # exatamente o que aconteceu na primeira versao deste script (r = +0,059) e teria
    # feito o teste parecer inconclusivo quando o sinal esta la.
    # O ultimo trecho (21 -> 21,75B) tambem sai: sao 0,75B e 0,001 de bpb, abaixo do ruido.
    miolo = pares[1:-1]
    r_miolo = pearson(miolo)
    print(f"\n  Pearson com TODOS os {len(pares)} trechos: r = {r_tudo:+.3f}")
    print(f"  ⚠️ este numero e' ENGANOSO e nao deve ser citado sozinho: ha DOIS mecanismos")
    print(f"     produzindo inclinacao alta em pontas opostas — aprendizado inicial rapido")
    print(f"     (LR alto) e decaimento de LR (LR baixo). Um cancela o outro no Pearson.")
    print(f"\n  Pearson so no MIOLO ({len(miolo)} trechos, de "
          f"{miolo[0][0]/1e9:.1f}B a {miolo[-1][0]/1e9:.1f}B): r = {r_miolo:+.3f}")
    if r_miolo is not None and r_miolo < -0.7:
        print("  ⭐ FORTE e NEGATIVA: no regime em que o modelo ja saiu do transiente inicial,")
        print("     quanto MENOR o LR, MAIOR a queda de bpb no trecho. E' a assinatura do")
        print("     decaimento — o ganho do fim vem do schedule, nao do dado.")
        print("  ⚠️ Com 4 pontos, r alto e' sugestivo, nao prova. O que decide o argumento e' a")
        print("     ACELERACAO acima, que e' incompativel com lei de potencia por construcao.")
    elif r_miolo is not None and r_miolo > 0.7:
        print("  POSITIVA — nao sustenta a hipotese do artefato de LR.")
    else:
        print("  inconclusiva mesmo no miolo.")

    # ---- o que a lei prediz se ajustada SO onde o LR estava alto
    print("\n" + "-" * 78)
    print("EXTRAPOLACAO: ajustar so nos marcos com LR >= 80% do pico (regime comparavel)")
    print("-" * 78)
    limpos = [(d, l) for d, l in MARCOS if lr_no_ponto(d) >= 0.8 * LR_MAX]
    print(f"  marcos usados: {[f'{d/1e9:.0f}B' for d, _ in limpos]}  (n={len(limpos)})")
    if len(limpos) >= 3:
        sse, a, A, E = ajustar_lei(limpos)
        print(f"  L(D) = {E:.4f} + {A:.4f}·D^-{a:.3f}   (SSE {sse:.2e})")
        for alvo in (21.75e9, 30e9):
            print(f"    previsao em {alvo/1e9:>5.1f}B: {E + A * alvo ** -a:.4f}")
        print(f"    MEDIDO   em 21,75B: {MARCOS[-1][1]:.4f}")
        print("\n  ⚠️ O ajuste tem 3 parametros e 3 pontos: passa exato por construcao e NAO")
        print("     valida nada (grau de liberdade zero — licao ja registrada). Serve so para")
        print("     mostrar a ORDEM DE GRANDEZA de quanto a extrapolacao muda quando se tira")
        print("     os pontos contaminados pelo decaimento.")
    else:
        print("  marcos limpos insuficientes para qualquer ajuste.")

    print("\n" + "=" * 78)
    print("CONSEQUENCIA PARA O BEE-350M")
    print("=" * 78)
    print("  1. NAO usar 'a curva ainda descia' como argumento para comprar mais tokens.")
    print("  2. O WSD ja adotado conserta isso na origem: na fase ESTAVEL o LR e constante,")
    print("     entao os checkpoints intermediarios sao comparaveis ENTRE SI e a curva medida")
    print("     no 350M sera lei de escala de verdade, nao schedule disfarcado.")
    print("  3. Salvar os marcos nos MESMOS volumes do 150M (1/3/6/10/15/21B) da 6 pontos")
    print("     pareados em dois N — o suficiente para ajustar L(N,D) COM residuo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
