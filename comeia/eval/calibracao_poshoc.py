"""G-C3 — CALIBRACAO POS-HOC do Noul "chamar ferramenta?" (estudo-decisoes-calibradas-2026-09-19.md, §6).

Entrada: casos_calib_<adapter>.jsonl (saida do G-C1): por caso, p_call = P(1º token ∈ {'{', ' {'} | prompt),
is_tool, pred_tool/ref (o Choice) e o greedy da eval (exec_ok, ferramenta_pred) quando ha' despejo.
US$ 0: nenhum forward novo — so' mapas p -> p' sobre numeros ja' medidos.

Tres mapas MONOTONOS, ajustados sem ver o caso avaliado (2 dobras estratificadas sorteadas; cada caso e'
avaliado pelo mapa ajustado na OUTRA metade; 5 sorteios, media ± dp — o dp e' o piso do proprio sorteio):
  temperatura   p' = σ(z/T),   z = logit(p)      1 parametro (Guo et al. 2017)
  platt         p' = σ(a·z + b)                  2 parametros
  isotonica     PAV sobre (p, y), degraus         nao-parametrico
⚠️ Temperatura PURA nao move o corte: z/T = 0 sse z = 0, logo a decisao a 0,5 e' a mesma do p cru — ela so'
corrige a CONFIANCA. Quem pode mover o corte (e recuperar under-call) e' o vies do Platt ou a isotonica.
⚠️ Mapa monotono nao muda o ranking: AUROC(p vs classe) e' invariante por construcao.

Quarto protocolo, o que interessa na pratica: TRANSFERENCIA — mapa ajustado nas OUTRAS DUAS sementes da
mesma receita, aplicado a esta. Se ficar perto da 2-dobras, calibra-se uma vez por receita; se nao, o
mapa e' do artefato.

METRICAS (as do G-C1): sobre a PROBABILIDADE p' contra a classe — ECE_prob, Brier, NLL; sobre a DECISAO
a 0,5 — acuracia, under/over-call, ECE da confianca max(p',1-p') contra o acerto, AUROC, AURC, acc@cob.

VARREDURA DE LIMIAR sobre o p cru (descricao, sem ajuste): τ ∈ {0,5 … 0,1}: under, over, acuracia, e o
TETO do ganho fim-a-fim: casos tool RECUPERADOS (p<0,5 e p>=τ) × P(exec_ok | chamou) do greedy, menos os
casos texto que passam a ser chamados. E' teto (§2k: 95% executam, 62% acertam); ao lado vai o numero
MEDIDO que existe sem gerar: nos recuperados, o Choice ja' escolhe a ferramenta certa em que fracao?

PREVISAO PRE-REGISTRADA (escrita antes de rodar): no C-full, ECE da confianca cai de ~0,13 para <0,05 com
qualquer dos tres mapas; a isotonica e o Platt movem o corte do p cru para 0,2–0,35 e reduzem o under-call
de ~26% para <15%, subindo o over-call em menos do que isso; o teto fim-a-fim e' +5 a +12 pp em exec_ok e o
realizavel e' menor; a transferencia entre sementes fica a <0,02 de ECE da 2-dobras.

Uso:
  python comeia/eval/calibracao_poshoc.py                       # todos os casos_calib_*.jsonl
  python comeia/eval/calibracao_poshoc.py --so e19c             # so o C-full
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calibracao_agentica import auroc, aurc_e_cobertura, ece  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
EPS = 1e-6
LIMIARES = (0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1)
RECEITAS = {"e13-email": "e13", "e19c": "C-full", "gate3-recusa_especifica": "recusa_esp", "gate3-catperturbado": "catpert",
            "final-s": "1G-final", "15B-s": "1G-15B"}   # SFT do Bee-1G (2026-09-24)


def iniciou_greedy(g) -> bool:
    """A DECISAO de chamar: o bruto comeca com '{' (valido ou quebrado). E' isto que um limiar move."""
    if not g:
        return False
    if "iniciou_chamada" in g:
        return bool(g["iniciou_chamada"])
    return (g.get("bruto") or "").lstrip().startswith("{")


def chamou_greedy(g) -> bool:
    """`chamou` gravado pelo G-C1 (--rejuntar); antes disso, ferramenta_pred (tool) ou over_call (texto)."""
    if not g:
        return False
    if "chamou" in g:
        return bool(g["chamou"])
    return bool(g.get("ferramenta_pred") or g.get("over_call"))


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def sigm(z):
    return 1 / (1 + np.exp(-z))


def nll(pp, y):
    pp = np.clip(pp, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(pp) + (1 - y) * np.log(1 - pp)))


# ---------------------------------------------------------------- mapas
def ajustar_temperatura(p, y):
    z = logit(p)
    r = minimize_scalar(lambda T: nll(sigm(z / T), y), bounds=(0.05, 50.0), method="bounded")
    T = float(r.x)
    return {"T": T}, (lambda q: sigm(logit(q) / T))


def ajustar_platt(p, y):
    z = logit(p)
    r = minimize(lambda ab: nll(sigm(ab[0] * z + ab[1]), y), x0=np.array([1.0, 0.0]), method="Nelder-Mead",
                 options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 4000})
    a, b = float(r.x[0]), float(r.x[1])
    return {"a": a, "b": b, "corte_em_p_cru": float(sigm(-b / a)) if a > 0 else None}, (lambda q: sigm(a * logit(q) + b))


def ajustar_isotonica(p, y):
    """PAV: blocos [media, n, x_min, x_max]; previsao por interpolacao linear entre os centros dos blocos."""
    o = np.argsort(p, kind="stable"); xs, ys = p[o], y[o].astype(float)
    pilha: list[list[float]] = []
    for xi, yi in zip(xs, ys):
        pilha.append([yi, 1.0, xi, xi])
        while len(pilha) >= 2 and pilha[-2][0] > pilha[-1][0]:
            m2, c2, lo2, hi2 = pilha.pop(); m1, c1, lo1, hi1 = pilha.pop()
            pilha.append([(m1 * c1 + m2 * c2) / (c1 + c2), c1 + c2, lo1, hi2])
    cx = np.array([(b[2] + b[3]) / 2 for b in pilha]); cy = np.array([b[0] for b in pilha])
    corte = None                                   # primeiro x onde a curva cruza 0,5 (None se nunca cruza)
    for b in pilha:
        if b[0] >= 0.5:
            corte = float(b[2]); break
    return {"blocos": len(pilha), "corte_em_p_cru": corte}, (lambda q: np.interp(q, cx, cy))


MAPAS = {"temperatura": ajustar_temperatura, "platt": ajustar_platt, "isotonica": ajustar_isotonica}


# ---------------------------------------------------------------- metricas
def metricas(pp, y):
    pp = np.asarray(pp, float); y = np.asarray(y, bool)
    pred = pp >= 0.5; certo = pred == y; conf = np.where(pred, pp, 1 - pp)
    a, cov = aurc_e_cobertura(conf.tolist(), certo.tolist())
    return {"n": int(len(y)), "acc": float(certo.mean()),
            "under_call": float((~pred[y]).mean()), "over_call": float(pred[~y].mean()),
            "ece_prob": ece(pp.tolist(), y.tolist()), "brier": float(np.mean((pp - y) ** 2)), "nll": nll(pp, y),
            "ece_conf": ece(conf.tolist(), certo.tolist()), "auroc_conf_vs_certo": auroc(conf.tolist(), certo.tolist()),
            "auroc_p_vs_classe": auroc(pp.tolist(), y.tolist()), "aurc": a, **cov,
            "conf_media": float(conf.mean()), "frac_conf>0.99": float((conf > 0.99).mean())}


def media_dp(lista: list[dict]) -> dict:
    chaves = [k for k in lista[0] if isinstance(lista[0][k], (int, float))]
    return {k: {"media": float(np.mean([d[k] for d in lista])),
                "dp": float(np.std([d[k] for d in lista], ddof=1)) if len(lista) > 1 else 0.0}
            for k in chaves}


def dobras(y, semente):
    """2 dobras estratificadas: metade dos tool e metade dos texto em cada."""
    rng = np.random.default_rng(semente)
    A = np.zeros(len(y), bool)
    for classe in (True, False):
        idx = np.flatnonzero(y == classe); rng.shuffle(idx)
        A[idx[: len(idx) // 2]] = True
    return A


def duas_dobras(p, y, nome_mapa, sementes=5):
    """Cada caso previsto pelo mapa ajustado na outra metade; agregados sobre os n casos; media ± dp nos sorteios."""
    rs, params = [], []
    for s in range(sementes):
        A = dobras(y, s); pp = np.empty_like(p)
        for fit, ev in ((A, ~A), (~A, A)):
            prm, f = MAPAS[nome_mapa](p[fit], y[fit]); pp[ev] = f(p[ev]); params.append(prm)
        rs.append(metricas(pp, y))
    return {"sorteios": sementes, **media_dp(rs), "parametros_exemplo": params[:2]}


# ---------------------------------------------------------------- varredura
def varredura(p, y, casos):
    """Descricao do p cru: a cada τ, under/over/acc; e o teto do ganho fim-a-fim sobre os RECUPERADOS."""
    tool = y; texto = ~y
    chamou_g = np.array([chamou_greedy(c["greedy"]) for c in casos])              # chamada VALIDA (a da eval)
    iniciou_g = np.array([iniciou_greedy(c["greedy"]) for c in casos])            # DECISAO de chamar (comecou '{')
    exec_g = np.array([bool(c["greedy"] and c["greedy"].get("exec_ok")) for c in casos])
    tem_greedy = any(c["greedy"] for c in casos)
    p_exec_dado_chamou = float(exec_g[tool & chamou_g].mean()) if tem_greedy and (tool & chamou_g).any() else None
    tool_right = np.array([c["pred_tool"] == c["ref"] for c in casos])
    # ⚠️ A decisao do greedy e' ARGMAX do 1º token, nao "p_call >= 0,5": com a massa restante espalhada por
    #    muitos tokens de texto, '{' e' argmax com p bem abaixo de 0,5. Logo "under-call por logit" (p<0,5)
    #    SUPERESTIMA o under-call do greedy, e o que um τ recupera se conta a partir do que o GREEDY nao
    #    chamou (quando ha' despejo), nao a partir de p<0,5.
    nao_chamou = ~iniciou_g if tem_greedy else (p < 0.5)
    greedy = None
    if tem_greedy:
        pc_ch = p[iniciou_g]; pc_nc = p[~iniciou_g]
        greedy = {"under_call": float((~iniciou_g[tool]).mean()), "over_call": float(chamou_g[texto].mean()),
                  "chamada_quebrada_tool": int((iniciou_g & ~chamou_g & tool).sum()),
                  "chamados_com_p<0.5": int((pc_ch < 0.5).sum()), "p_min_entre_chamados": float(pc_ch.min()) if len(pc_ch) else None,
                  "p_max_entre_nao_chamados": float(pc_nc.max()) if len(pc_nc) else None,
                  "nao_chamados_com_p>=0.5": int((pc_nc >= 0.5).sum())}
    linhas = []
    for t in LIMIARES:
        pred = p >= t
        rec = tool & nao_chamou & pred          # tool que o greedy (ou o corte 0,5) perdia e τ recupera
        novos_over = texto & nao_chamou & pred   # texto que passa a ser chamado
        d = {"tau": t, "acc": float((pred == y).mean()), "under_call": float((~pred[tool]).mean()),
             "over_call": float(pred[texto].mean()), "recuperados": int(rec.sum()),
             "recuperados_choice_certo": int((rec & tool_right).sum()), "novos_over_call": int(novos_over.sum())}
        if p_exec_dado_chamou is not None:
            d["teto_ganho_exec_ok_casos"] = float(rec.sum() * p_exec_dado_chamou)
            d["saldo_teto_casos"] = float(rec.sum() * p_exec_dado_chamou - novos_over.sum())
            d["teto_pp_exec_ok"] = 100 * d["teto_ganho_exec_ok_casos"] / max(1, tool.sum())
            d["novos_over_pp_texto"] = 100 * novos_over.sum() / max(1, texto.sum())
        linhas.append(d)
    return {"p_exec_ok_dado_chamou_greedy": p_exec_dado_chamou, "n_tool_chamados_greedy": int((tool & chamou_g).sum()),
            "greedy": greedy, "base_da_varredura": "greedy nao chamou" if tem_greedy else "p_call < 0,5", "por_limiar": linhas}


# ---------------------------------------------------------------- main
def carregar(caminho: Path):
    casos = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    p = np.array([c["p_call"] for c in casos], float); y = np.array([bool(c["is_tool"]) for c in casos])
    return casos, p, y


def receita(nome: str) -> str | None:
    for pref, r in RECEITAS.items():
        if nome.startswith(pref):
            return r
    return None


def fmt_params(prm: dict) -> str:
    return json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in prm.items() if k != "blocos"})


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--casos-dir", type=Path, default=RAIZ / "eval" / "results")
    ap.add_argument("--so", default="", help="so adapters cujo nome contenha isto")
    ap.add_argument("--sorteios", type=int, default=5)
    ap.add_argument("--saida", default="docs/calibracao-poshoc-350m-2026-09-19.json")
    a = ap.parse_args()

    arquivos = [f for f in sorted(a.casos_dir.glob("casos_calib_*.jsonl")) if a.so in f.name]
    if not arquivos:
        print("🔴 nenhum casos_calib_*.jsonl — rode o G-C1 (calibracao_agentica.py) primeiro"); return 1
    dados = {re.sub(r"^casos_calib_|\.jsonl$", "", f.name): carregar(f) for f in arquivos}

    saida = {"_regua": {"fonte": "casos_calib_<adapter>.jsonl (G-C1)", "dobras": 2, "sorteios": a.sorteios,
                        "mapas": list(MAPAS), "limiares": LIMIARES,
                        "nota": "mapa monotono nao muda AUROC(p vs classe); temperatura pura nao move o corte a 0,5"},
             "adapters": {}}
    for nome, (casos, p, y) in dados.items():
        R = {"n": int(len(y)), "n_tool": int(y.sum()), "cru": metricas(p, y)}
        for m in MAPAS:
            R[f"2dobras_{m}"] = duas_dobras(p, y, m, a.sorteios)
        rec = receita(nome)                                  # transferencia entre sementes da mesma receita
        irmaos = [k for k in dados if k != nome and receita(k) == rec] if rec else []
        if irmaos:
            pf = np.concatenate([dados[k][1] for k in irmaos]); yf = np.concatenate([dados[k][2] for k in irmaos])
            R["transferencia"] = {"ajustado_em": irmaos}
            for m in MAPAS:
                prm, f = MAPAS[m](pf, yf)
                R["transferencia"][m] = {"parametros": prm, **metricas(f(p), y)}
        R["varredura_p_cru"] = varredura(p, y, casos)
        saida["adapters"][nome] = R

        c = R["cru"]
        print(f"\n{nome}  (n {R['n']}, tool {R['n_tool']})")
        print(f"  cru                  acc {c['acc']:.3f} · under {c['under_call']:.3f} over {c['over_call']:.3f} · "
              f"ECE_prob {c['ece_prob']:.3f} Brier {c['brier']:.3f} NLL {c['nll']:.3f} · ECE_conf {c['ece_conf']:.3f} "
              f"AUROC {c['auroc_conf_vs_certo']:.3f} AURC {c['aurc']:.3f} acc@50 {c['acc@50']:.3f} · conf>0,99 {c['frac_conf>0.99']:.0%}")
        for m in MAPAS:
            d = R[f"2dobras_{m}"]
            print(f"  2dobras {m:<12} acc {d['acc']['media']:.3f}±{d['acc']['dp']:.3f} · under {d['under_call']['media']:.3f} "
                  f"over {d['over_call']['media']:.3f} · ECE_prob {d['ece_prob']['media']:.3f}±{d['ece_prob']['dp']:.3f} "
                  f"Brier {d['brier']['media']:.3f} NLL {d['nll']['media']:.3f} · ECE_conf {d['ece_conf']['media']:.3f}±{d['ece_conf']['dp']:.3f} "
                  f"AUROC {d['auroc_conf_vs_certo']['media']:.3f} AURC {d['aurc']['media']:.3f} acc@50 {d['acc@50']['media']:.3f} · "
                  f"conf>0,99 {d['frac_conf>0.99']['media']:.0%}   ex. {fmt_params(d['parametros_exemplo'][0])}")
        if "transferencia" in R:
            for m in MAPAS:
                d = R["transferencia"][m]
                print(f"  transf. {m:<12} acc {d['acc']:.3f} · under {d['under_call']:.3f} over {d['over_call']:.3f} · "
                      f"ECE_prob {d['ece_prob']:.3f} Brier {d['brier']:.3f} NLL {d['nll']:.3f} · ECE_conf {d['ece_conf']:.3f} "
                      f"AUROC {d['auroc_conf_vs_certo']:.3f} AURC {d['aurc']:.3f} acc@50 {d['acc@50']:.3f}   params {fmt_params(d['parametros'])}")
        v = R["varredura_p_cru"]
        pe = v["p_exec_ok_dado_chamou_greedy"]
        g = v["greedy"]
        if g:
            print(f"  greedy (argmax)      under {g['under_call']:.3f} over {g['over_call']:.3f} · chamados com p<0,5: {g['chamados_com_p<0.5']} "
                  f"(p min entre chamados {g['p_min_entre_chamados']:.3f}) · nao chamados com p>=0,5: {g['nao_chamados_com_p>=0.5']}")
        print(f"  varredura do p cru a partir de [{v['base_da_varredura']}]  (P(exec_ok | chamou) no greedy = {'—' if pe is None else f'{pe:.3f}'} em {v['n_tool_chamados_greedy']} tool chamados)")
        for d in v["por_limiar"]:
            extra = (f" · teto exec_ok +{d['teto_ganho_exec_ok_casos']:.1f} casos (+{d['teto_pp_exec_ok']:.1f} pp) · "
                     f"saldo {d['saldo_teto_casos']:+.1f} casos") if "saldo_teto_casos" in d else ""
            print(f"    τ {d['tau']:.2f}  acc {d['acc']:.3f} under {d['under_call']:.3f} over {d['over_call']:.3f} · "
                  f"recupera {d['recuperados']:3d} (Choice certo {d['recuperados_choice_certo']:3d}) · novos over {d['novos_over_call']:3d}{extra}")

    Path(a.saida).write_text(json.dumps(saida, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    print(f"\nsalvo em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
