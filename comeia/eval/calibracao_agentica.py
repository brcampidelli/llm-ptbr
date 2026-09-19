"""G-C1 — CALIBRACAO das decisoes agenticas do Bee-350M (estudo-decisoes-calibradas-2026-09-19.md, §6).

O modelo ja' toma duas decisoes por caso do holdout balanceado; aqui elas sao LIDAS como probabilidade,
nao geradas (2603.06604: um forward, zero geracao):

  Noul  "chamar ferramenta?"   p_call = P(1º token gerado ∈ {'{', ' {'} | prompt)   — o inicio do JSON
  Choice "qual ferramenta?"    p_tool = softmax sobre o catalogo de  logP(nome + '"' | prompt + '{"tool": "')
                               (confianca NORMALIZADA sobre as opcoes validas, eq. 1 do 2603.06604)

MESMA REGUA da eval (§2g): mesmo `partes()` do eval_agentic_exec.py (system + ultima fala do usuario),
mesmo chat template, mesmo max_len 1700 — so' que o corte, se houver, e' pela ESQUERDA (preserva o
cabecalho do assistente; a eval corta pela direita: contamos quantos casos passam de 1700 e reportamos).

METRICAS (2507.16806 / 2607.03528): acuracia da decisao, ECE (10 caixas de largura igual), Brier,
AUROC (a confianca separa certo de errado?), AURC e acuracia@cobertura 25/50/75% (agir so' quando
confiante). E, cruzando com o despejo greedy da eval (casos_<tag>.jsonl, se existir), o FIM-A-FIM:
correto = exec_ok (caso tool) ou nao-chamou (caso texto); confianca = p_call·p_tool(pred) se chamou,
1−p_call se nao.

PREVISAO PRE-REGISTRADA (no estudo, antes de rodar): AUROC 0,70–0,85 na decisao de chamar; ECE > 0,15
(superconfianca de SFT em catalogo balanceado); se AUROC < 0,6 a confianca e' o ATALHO (§2u) e
calibracao pos-hoc nao salva.

Uso:
  python comeia/eval/calibracao_agentica.py --peft comeia/models/e19c-s42 comeia/models/e13-email-s42 ...
        --dumps gate3-ref-cfull-s42 gate3-ref-e13-s42 ...   (tags dos despejos, na mesma ordem; '-' = sem)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data")); sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_agentic_exec import partes                   # noqa: E402
from catalogo_maior import blocos_do_sistema           # noqa: E402

PREFIXO = '{"tool": "'


def ece(conf: list[float], cert: list[bool], caixas: int = 10) -> float:
    n = len(conf)
    tot = 0.0
    for b in range(caixas):
        lo, hi = b / caixas, (b + 1) / caixas
        idx = [i for i, c in enumerate(conf) if (lo < c <= hi) or (b == 0 and c == 0.0)]
        if not idx:
            continue
        acc = sum(cert[i] for i in idx) / len(idx)
        cf = sum(conf[i] for i in idx) / len(idx)
        tot += len(idx) / n * abs(acc - cf)
    return tot


def auroc(score: list[float], pos: list[bool]) -> float:
    """Mann-Whitney: P(score_pos > score_neg), empates valem 0,5."""
    P = [s for s, p in zip(score, pos) if p]; N = [s for s, p in zip(score, pos) if not p]
    if not P or not N:
        return float("nan")
    ordem = sorted(range(len(score)), key=lambda i: score[i])
    ranks = [0.0] * len(score); i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and score[ordem[j + 1]] == score[ordem[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[ordem[k]] = r
        i = j + 1
    soma = sum(ranks[i] for i, p in enumerate(pos) if p)
    return (soma - len(P) * (len(P) + 1) / 2) / (len(P) * len(N))


def aurc_e_cobertura(conf: list[float], cert: list[bool]) -> tuple[float, dict[str, float]]:
    """Ordena por confianca decrescente; risco acumulado; AURC = media dos riscos (2607.03528 eq. 2.12)."""
    ordem = sorted(range(len(conf)), key=lambda i: -conf[i])
    erros = 0; riscos = []
    for k, i in enumerate(ordem, 1):
        erros += 0 if cert[i] else 1
        riscos.append(erros / k)
    acc_cov = {}
    for cov in (0.25, 0.5, 0.75, 1.0):
        k = max(1, int(round(cov * len(ordem))))
        acc_cov[f"acc@{int(cov*100)}"] = 1 - riscos[k - 1]
    return sum(riscos) / len(riscos), acc_cov


def brier(conf: list[float], cert: list[bool]) -> float:
    return sum((c - (1.0 if y else 0.0)) ** 2 for c, y in zip(conf, cert)) / len(conf)


def resumo(nome: str, conf: list[float], cert: list[bool], score_pos=None, pos=None) -> dict:
    a, cov = aurc_e_cobertura(conf, cert)
    d = {"n": len(conf), "acc": sum(cert) / len(cert), "ece": ece(conf, cert), "brier": brier(conf, cert),
         "auroc_conf_vs_certo": auroc(conf, cert), "aurc": a, **cov,
         "conf_media": sum(conf) / len(conf), "frac_conf>0.99": sum(1 for c in conf if c > 0.99) / len(conf)}
    if score_pos is not None:
        d["auroc_score_vs_classe"] = auroc(score_pos, pos)
    return d


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", nargs="+", required=True)
    ap.add_argument("--dumps", nargs="*", default=[], help="tag do despejo por adapter ('-' = nenhum)")
    ap.add_argument("--data", type=Path, default=RAIZ / "data" / "processed" / "holdout_balanceado.eval.jsonl")   # 🔴 NAO o PADRAO_EVAL: e o holdout ANTIGO (150 casos, 14 ferramentas) — pego no smoke test
    ap.add_argument("--max-len", type=int, default=1700)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--saida", default="docs/calibracao-agentica-350m-2026-09-19.json")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    rows = [json.loads(l) for l in a.data.read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limit:
        rows = rows[:a.limit]
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"; tok.truncation_side = "left"
    ids_chave = [i for i in range(len(tok)) if tok.decode([i]).lstrip().startswith("{")]
    ids_prefixo = tok(PREFIXO, add_special_tokens=False)["input_ids"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"holdout {len(rows)} · tokens de chamada {[tok.decode([i]) for i in ids_chave]} · prefixo {len(ids_prefixo)} tokens · {dev}")
    print(f"transformers {__import__('transformers').__version__} · peft {__import__('peft').__version__} · torch {torch.__version__}")

    # prompts (identicos aos da eval com --chat)
    prompts, metas = [], []
    longos = 0
    for k, r in enumerate(rows, 1):
        sistema, usuario, ref, kind = partes(r)
        msgs = ([{"role": "system", "content": sistema}] if sistema else []) + [{"role": "user", "content": usuario}]
        txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(txt, add_special_tokens=False)["input_ids"]
        if len(ids) > a.max_len:
            longos += 1; ids = ids[-a.max_len:]
        nomes = list(blocos_do_sistema(sistema or ""))
        prompts.append(ids)
        metas.append({"i": k, "kind": kind, "is_tool": kind == "tool_call", "ref": r.get("ferramenta"), "nomes": nomes})
    print(f"prompts > {a.max_len} tokens (cortados pela ESQUERDA aqui; a eval corta pela direita): {longos}")

    base = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).to(dev).eval()
    saida_tudo = {"_regua": {"data": str(a.data), "max_len": a.max_len, "prompts_longos": longos, "tokens_chamada": ids_chave,
                             "prefixo": PREFIXO, "transformers": __import__("transformers").__version__,
                             "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else "cpu"}, "adapters": {}}
    dumps = list(a.dumps) + ["-"] * (len(a.peft) - len(a.dumps))

    for adp, tag in zip(a.peft, dumps):
        t0 = time.time()
        modelo = PeftModel.from_pretrained(base, adp).eval() if adp != "-" else base
        casos = []
        with torch.no_grad():
            for ids, m in zip(prompts, metas):
                x = torch.tensor([ids], device=dev)
                lg = modelo(input_ids=x).logits[0, -1].float()
                pr = torch.softmax(lg, -1)
                p_call = float(pr[ids_chave].sum())
                p_tool, pred_tool = {}, None
                if m["nomes"]:
                    seqs = [ids + ids_prefixo + tok(n + '"', add_special_tokens=False)["input_ids"] for n in m["nomes"]]
                    L = max(len(s) for s in seqs)
                    pad = tok.pad_token_id
                    X = torch.tensor([[pad] * (L - len(s)) + s for s in seqs], device=dev)
                    A = torch.tensor([[0] * (L - len(s)) + [1] * len(s) for s in seqs], device=dev)
                    pos = (A.cumsum(-1) - 1).clamp(min=0)          # RoPE certo com padding a esquerda
                    out = modelo(input_ids=X, attention_mask=A, position_ids=pos).logits.float().log_softmax(-1)
                    lps = []
                    for j, s in enumerate(seqs):
                        n_op = len(s) - len(ids) - len(ids_prefixo)
                        off = L - len(s)
                        # logP de cada token da opcao dado tudo antes: posicoes [L-n_op, L)
                        lp = 0.0
                        for t in range(L - n_op, L):
                            lp += float(out[j, t - 1, X[j, t]])
                        lps.append(lp)
                    mx = max(lps); z = sum(math.exp(v - mx) for v in lps)
                    p_tool = {n: math.exp(v - mx) / z for n, v in zip(m["nomes"], lps)}
                    pred_tool = max(p_tool, key=p_tool.get)
                casos.append({**m, "p_call": p_call, "p_tool": p_tool, "pred_tool": pred_tool})
        if adp != "-":
            del modelo; torch.cuda.empty_cache()
            base = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).to(dev).eval()  # base limpo para o proximo

        # ── despejo greedy da eval (mesmos casos, mesmo indice i)
        dump = {}
        if tag != "-":
            p = RAIZ / "eval" / "results" / f"casos_{tag}-cfgref.jsonl"
            if p.exists():
                dump = {d["i"]: d for d in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())}
        # ── metricas
        is_tool = [c["is_tool"] for c in casos]
        dec_call = [c["p_call"] >= 0.5 for c in casos]
        cert_noul = [d == t for d, t in zip(dec_call, is_tool)]
        conf_noul = [max(c["p_call"], 1 - c["p_call"]) for c in casos]
        R = {"adapter": adp, "dump": tag if dump else None, "segundos": round(time.time() - t0)}
        R["noul_chamar"] = resumo("noul", conf_noul, cert_noul, [c["p_call"] for c in casos], is_tool)
        R["noul_chamar"]["over_call_por_logit"] = sum(1 for c in casos if not c["is_tool"] and c["p_call"] >= 0.5) / max(1, sum(1 for c in casos if not c["is_tool"]))
        R["noul_chamar"]["under_call_por_logit"] = sum(1 for c in casos if c["is_tool"] and c["p_call"] < 0.5) / max(1, sum(is_tool))
        multi = [c for c in casos if c["is_tool"] and len(c["nomes"]) >= 2 and c["ref"] in c["nomes"]]
        if multi:
            R["choice_ferramenta_catalogo>=2"] = resumo("choice", [max(c["p_tool"].values()) for c in multi], [c["pred_tool"] == c["ref"] for c in multi])
            R["choice_ferramenta_catalogo>=2"]["tamanhos"] = sorted(set(len(c["nomes"]) for c in multi))
        uni = [c for c in casos if c["is_tool"] and len(c["nomes"]) == 1]
        R["casos_tool_catalogo=1"] = len(uni)
        if dump:
            e2e_c, e2e_conf, conc = [], [], 0
            for c in casos:
                d = dump.get(c["i"])
                if not d: continue
                chamou = d.get("ferramenta_pred") is not None
                correto = bool(d.get("exec_ok")) if c["is_tool"] else (not chamou)
                conf = c["p_call"] * (c["p_tool"].get(d.get("ferramenta_pred"), 0.0) if c["p_tool"] else 1.0) if chamou else (1 - c["p_call"])
                e2e_c.append(correto); e2e_conf.append(conf)
                if chamou and c["pred_tool"] is not None and d.get("ferramenta_pred") == c["pred_tool"]:
                    conc += 1
            R["fim_a_fim_greedy"] = resumo("e2e", e2e_conf, e2e_c)
            R["fim_a_fim_greedy"]["concordancia_choice_logit_vs_greedy"] = conc / max(1, sum(1 for c in casos if dump.get(c["i"], {}).get("ferramenta_pred") is not None))
            R["fim_a_fim_greedy"]["exec_ok_greedy"] = sum(1 for c in casos if c["is_tool"] and dump.get(c["i"], {}).get("exec_ok")) / max(1, sum(is_tool))
        saida_tudo["adapters"][Path(adp).name] = R
        N = R["noul_chamar"]; C = R.get("choice_ferramenta_catalogo>=2", {}); E = R.get("fim_a_fim_greedy", {})
        print(f"\n{Path(adp).name}  ({R['segundos']} s)")
        print(f"  NOUL chamar?   acc {N['acc']:.3f} · ECE {N['ece']:.3f} · Brier {N['brier']:.3f} · AUROC(p_call vs classe) {N['auroc_score_vs_classe']:.3f} · "
              f"AUROC(conf vs certo) {N['auroc_conf_vs_certo']:.3f} · AURC {N['aurc']:.3f} · acc@50 {N['acc@50']:.3f} · conf>0,99 {N['frac_conf>0.99']:.0%} · over {N['over_call_por_logit']:.3f} under {N['under_call_por_logit']:.3f}")
        if C:
            print(f"  CHOICE tool    n {C['n']} · acc {C['acc']:.3f} · ECE {C['ece']:.3f} · AUROC {C['auroc_conf_vs_certo']:.3f} · AURC {C['aurc']:.3f} · acc@50 {C['acc@50']:.3f} · conf>0,99 {C['frac_conf>0.99']:.0%}")
        if E:
            print(f"  FIM-A-FIM      n {E['n']} · acc {E['acc']:.3f} · ECE {E['ece']:.3f} · AUROC {E['auroc_conf_vs_certo']:.3f} · AURC {E['aurc']:.3f} · acc@25 {E['acc@25']:.3f} acc@50 {E['acc@50']:.3f} acc@75 {E['acc@75']:.3f} · choice logit = greedy em {E['concordancia_choice_logit_vs_greedy']:.0%}")
        Path(a.saida).write_text(json.dumps(saida_tudo, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsalvo em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
