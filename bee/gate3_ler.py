"""Consolida o gate #3 (catalogo perturbado · recusa especifica) a partir dos ARTEFATOS — por codigo, nao a mao (§2z).

Le comeia/eval/results/exec_gate3-*-cfgref.json (os do pod, todos na MESMA regua e no MESMO hardware):
  gate3-controle-cfull-s42 · gate3-ref-cfull-s43/44     -> braco  cfull            (resposta util, E19 C-full)
  gate3-ref-e13-s42/43/44                              -> braco  e13              (recusa em template)
  gate3-catperturbado-s4x                              -> braco  catperturbado    (a) 2609.04184, sobre o corpus do C-full
  gate3-recusa_especifica-s4x                          -> braco  recusa_especifica (b) 2609.04714, sobre o corpus do e13

Imprime, por braco: cada semente, media e dp de exec_ok, over_call, under_call, tool_right, args_exact.
Depois os PAREADOS por semente (§2x: tres sementes decidem) contra as duas referencias, com o piso de
ruido AO LADO (§2h): dp dos deltas /sqrt(3) e o erro amostral da diferenca sqrt(2p(1-p)/n).
Perguntas pre-registradas (tracker, gates-estudo-arxiv-2026-09-12.md):
  (a) catperturbado x cfull: renomear 27% dos alvos melhora a SELECAO (tool_right/exec_ok) sem subir over_call?
  (b) recusa_especifica x e13 e x cfull: recupera os ~5,9 pp de exec_ok do C-full MANTENDO o over_call do C-full?
Criterio declarado ANTES de ler: efeito "alem do ruido" = |media dos deltas| > 2 x max(dp/sqrt(3), SE amostral)
E as tres sementes com o mesmo sinal. Senao: dentro do ruido.
Tambem imprime a DERIVA DE HARDWARE: referencia no pod x mesmo adapter medido na 5070 (artefatos locais).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

RX = re.compile(r"exec_gate3-(?:controle-|ref-)?(cfull|e13|catperturbado|recusa_especifica)-s(\d+)-cfgref\.json$")
METRICAS = (("exec_ok", "n_tool"), ("over_call", "n_text"), ("under_call", "n_tool"), ("tool_right", "n_tool"), ("args_exact", "n_tool"))
LOCAIS = {("cfull", 42): "exec_e19c-cfgref.json", ("cfull", 43): "exec_e19c-s43-cfgref.json",
          ("cfull", 44): "exec_e19c-s44-cfgref.json", ("e13", 42): "exec_e13-email-s42-cfgref.json"}


def pct(d: dict, num: str, den: str) -> float:
    return 100.0 * d[num] / d[den]


def media_dp(xs: list[float]) -> tuple[float, float]:
    m = sum(xs) / len(xs)
    dp = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else float("nan")
    return m, dp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="comeia/eval/results")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    D = Path(args.dir)
    bracos: dict[str, dict[int, dict]] = {}
    for p in sorted(D.glob("exec_gate3-*-cfgref.json")):
        m = RX.search(p.name)
        if not m:
            continue
        d = json.load(open(p, encoding="utf-8"))
        assert d["n_tool"] == 536 and d["n_text"] == 268, f"{p.name}: n diferente do holdout de referencia"
        bracos.setdefault(m.group(1), {})[int(m.group(2))] = d
    if not bracos:
        print(f"nenhum exec_gate3-*-cfgref.json em {D}"); return 1

    print(f"{'braco':18s} {'sem':>3s} {'exec_ok':>9s} {'over':>8s} {'under':>8s} {'tool_ok':>8s} {'args':>8s}")
    resumo: dict[str, dict[str, list[float]]] = {}
    for b in ("e13", "cfull", "catperturbado", "recusa_especifica"):
        if b not in bracos:
            continue
        for s, d in sorted(bracos[b].items()):
            vals = {k: pct(d, k, den) for k, den in METRICAS}
            for k, v in vals.items():
                resumo.setdefault(b, {}).setdefault(k, []).append(v)
            print(f"{b:18s} {s:3d} " + " ".join(f"{vals[k]:8.1f}%" if k != "exec_ok" else f"{vals[k]:8.1f}%" for k, _ in METRICAS))
        n = len(bracos[b])
        linha = []
        for k, _ in METRICAS:
            m, dp = media_dp(resumo[b][k])
            linha.append(f"{m:5.1f}±{dp:3.1f}" if n > 1 else f"{m:5.1f}     ")
        print(f"{b:18s} {'m±dp':>3s} " + " ".join(f"{x:>9s}" for x in linha) + f"   (n={n} sementes)")

    # ── deriva de hardware: mesmo adapter, 5070 (artefato local) x 4090 (pod)
    print("\nDERIVA DE HARDWARE (mesmo adapter, mesma config: local 5070 -> pod):")
    derivas = []
    for (b, s), nome in LOCAIS.items():
        loc = D / nome
        if b in bracos and s in bracos[b] and loc.exists():
            L, P = json.load(open(loc, encoding="utf-8")), bracos[b][s]
            de, do = P["exec_ok"] - L["exec_ok"], P["over_call"] - L["over_call"]
            derivas.append((de, do))
            print(f"  {b:6s} s{s}: exec_ok {L['exec_ok']} -> {P['exec_ok']} ({de:+d} = {100*de/536:+.1f} pp) · over_call {L['over_call']} -> {P['over_call']} ({do:+d} = {100*do/268:+.1f} pp)")
    if derivas:
        print(f"  => |deriva| media: exec_ok {sum(abs(x) for x, _ in derivas)/len(derivas):.1f} casos · over_call {sum(abs(y) for _, y in derivas)/len(derivas):.1f} casos"
              f"  (por isso as referencias foram REMEDIDAS no pod — comparacao so' pod-com-pod, §2g)")

    # ── pareados por semente, com o piso de ruido ao lado
    out = {"bracos": {b: {str(s): {k: d[k] for k, _ in METRICAS} for s, d in v.items()} for b, v in bracos.items()}, "pareados": {}}
    pares = [("catperturbado", "cfull"), ("recusa_especifica", "e13"), ("recusa_especifica", "cfull")]
    for novo, ref in pares:
        if novo not in bracos or ref not in bracos:
            continue
        comuns = sorted(set(bracos[novo]) & set(bracos[ref]))
        if not comuns:
            continue
        print(f"\nPAREADO {novo} - {ref} (sementes {comuns}):")
        out["pareados"][f"{novo}-{ref}"] = {"_n_sementes": len(comuns)}
        for k, den in METRICAS:
            deltas = [pct(bracos[novo][s], k, den) - pct(bracos[ref][s], k, den) for s in comuns]
            m, dp = media_dp(deltas)
            p = sum(pct(bracos[ref][s], k, den) for s in comuns) / len(comuns) / 100
            n = bracos[ref][comuns[0]][den]
            se_am = 100 * math.sqrt(2 * p * (1 - p) / n)          # erro amostral da DIFERENCA (§2x)
            se_sem = dp / math.sqrt(len(deltas)) if len(deltas) > 1 else float("nan")
            piso = max(se_sem if not math.isnan(se_sem) else 0.0, se_am)
            mesmo_sinal = len(comuns) >= 3 and (all(x > 0 for x in deltas) or all(x < 0 for x in deltas))
            alem = abs(m) > 2 * piso and mesmo_sinal
            tag = "ALEM DO RUIDO" if alem else ("dentro do ruido" if len(comuns) >= 3 else "so' alerta (<3 sementes)")
            print(f"  {k:10s} " + " ".join(f"s{s} {x:+5.1f}" for s, x in zip(comuns, deltas))
                  + f"  | media {m:+5.1f} pp · dp/√n {se_sem:4.1f} · SE amostral {se_am:4.1f} · 2×piso {2*piso:4.1f} -> {tag}")
            out["pareados"][f"{novo}-{ref}"][k] = {"deltas": deltas, "media": m, "piso": piso, "alem_do_ruido": alem}

    # ── veredito por pergunta pre-registrada
    def v(par, k):
        return out["pareados"].get(par, {}).get(k)
    print("\nVEREDITO (criterio declarado no docstring):")
    decide = {par: out["pareados"][par]["_n_sementes"] >= 3 for par in out["pareados"]}   # §2x: tres sementes DECIDEM
    for par, ok in decide.items():
        if not ok:
            print(f"  {par}: SEM VEREDITO — {out['pareados'][par]['_n_sementes']} semente(s) em comum, precisa de 3")
    a_e, a_o, a_t = v("catperturbado-cfull", "exec_ok"), v("catperturbado-cfull", "over_call"), v("catperturbado-cfull", "tool_right")
    if a_e and decide.get("catperturbado-cfull"):
        ganho = (a_e["alem_do_ruido"] and a_e["media"] > 0) or (a_t and a_t["alem_do_ruido"] and a_t["media"] > 0)
        custo = a_o["alem_do_ruido"] and a_o["media"] > 0
        print(f"  (a) catalogo perturbado x C-full: exec_ok {a_e['media']:+.1f} · tool_right {a_t['media'] if a_t else float('nan'):+.1f} · over_call {a_o['media']:+.1f} -> "
              + ("ADOTAR (selecao melhor alem do ruido, over_call nao piorou)" if ganho and not custo else
                 "TROCA (melhora selecao E piora over_call)" if ganho and custo else
                 "NAO ADOTAR (sem efeito alem do ruido)" if not custo else "NAO ADOTAR (piora over_call)"))
    b_e13, b_o13 = v("recusa_especifica-e13", "exec_ok"), v("recusa_especifica-e13", "over_call")
    b_ecf, b_ocf = v("recusa_especifica-cfull", "exec_ok"), v("recusa_especifica-cfull", "over_call")
    if b_e13 and b_ecf and decide.get("recusa_especifica-e13") and decide.get("recusa_especifica-cfull"):
        # 🔴 v1 deste bloco lia "nao perde para o e13" E "nao sobe sobre o C-full" — duas ausencias de efeito —
        #    como "TERCEIRO PONTO CONFIRMADO". Ruido puro confirmaria (§2q). O terceiro ponto exige evidencia
        #    POSITIVA nos dois lados: recuperar execucao ALEM do ruido sobre o C-full E cortar over_call ALEM
        #    do ruido sobre o e13. Sem isso, o braco e' indistinguivel das referencias, nao um ponto novo.
        recupera = b_ecf["alem_do_ruido"] and b_ecf["media"] > 0             # execucao acima do C-full, alem do ruido
        mantem = b_o13["alem_do_ruido"] and b_o13["media"] < 0               # over_call abaixo do e13, alem do ruido
        print(f"  (b) recusa especifica: exec_ok x e13 {b_e13['media']:+.1f} · x C-full {b_ecf['media']:+.1f} · over_call x e13 {b_o13['media']:+.1f} · x C-full {b_ocf['media']:+.1f} -> "
              + ("TERCEIRO PONTO: execucao acima do C-full E over_call abaixo do e13, ambos alem do ruido" if recupera and mantem else
                 "recupera execucao sobre o C-full, mas o over_call NAO se distingue do e13 (= e13 sem template)" if recupera else
                 "corta over_call sobre o e13, mas a execucao NAO se distingue do C-full" if mantem else
                 "INDISTINGUIVEL das duas referencias dentro do ruido — sem terceiro ponto demonstrado"))
        dp_novo = media_dp(resumo["recusa_especifica"]["exec_ok"])[1]
        dp_ref = max(media_dp(resumo["cfull"]["exec_ok"])[1], media_dp(resumo["e13"]["exec_ok"])[1])
        se1 = 100 * math.sqrt(0.72 * 0.28 / 536)
        print(f"      dispersao entre sementes (exec_ok): recusa_especifica dp {dp_novo:.1f} pp · referencias ate {dp_ref:.1f} · "
              f"erro amostral de UMA medida {se1:.1f} -> {'variancia de treino REAL (> 2x amostral)' if dp_novo > 2 * se1 else 'compativel com amostragem'}")
    print("\n⚠️ RESSALVAS: 3 sementes por braco · n=536/268 · regua greedy bf16 na 4090 (deriva de hardware medida acima) ·"
          "\n   as outras capacidades (resumo/traducao/sentimento, §2ab) NAO foram medidas aqui — so' o eixo agentico.")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"salvo em {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
