"""G-C1b — NOUL DE ARGUMENTOS: o modelo sabe quando a PROPRIA chamada esta errada? (estudo §6, G-C1b)

O G-C1 mediu que a confianca da decisao (p_call·p_tool) e' CEGA ao erro de argumento: AUROC fim-a-fim
0,63–0,66, enquanto a decisao de chamar e a selecao tem AUROC ~0,9. O erro que sobra esta' nos ARGUMENTOS
(§2k: 95% executam, 62% acertam). Aqui, dois sinais baratos sobre a chamada greedy ja' gerada (o `bruto`
do despejo da eval), UM forward por caso chamado:

  (A) auto-avaliacao (Noul "Sim/Nao"): prompt + chamada como turno do assistente + turno do usuario
      "A chamada acima esta correta e completa para o pedido? Responda apenas Sim ou Nao." + cabecalho do
      assistente → c_sim = P(Sim) / (P(Sim) + P(Nao)) no 1º token (somando variantes de caixa/espaco).
  (B) verossimilhanca TEACHER-FORCED da propria chamada: logP de cada token do bruto dado o prefixo —
      media e minimo sobre os tokens dos ARGUMENTOS (de `"args"` ao fim) e sobre a chamada inteira.
      ⚠️ O bruto saiu de decodificacao RESTRITA (chave e nome mascarados): o token emitido pode nao ser o
      argmax irrestrito, e a logP aqui e' a IRRESTRITA — o sinal que o modelo tinha, nao o que a mascara
      escolheu. E o bruto re-tokenizado pode diferir dos tokens gerados em raras fronteiras de BPE.

Populacao: casos em que o greedy CHAMOU (ferramenta_pred != None). Correto = exec_ok (caso tool) ou False
(caso texto: over-call e' chamada errada por definicao). Reportado tambem so' nos casos tool.

METRICAS: AUROC de cada sinal contra correto (separa chamada certa de errada?), ECE do c_sim, acc@cobertura
com cada sinal como confianca; e o FIM-A-FIM recomposto (os 804 casos) com a confianca combinada
   chamou:  p_call · p_tool(pred) · c        nao chamou: 1 − p_call
para c ∈ {1 (= G-C1), c_sim, exp(lp_media_args), exp(lp_min_args)} — AUROC / AURC / acc@cob.

PREVISAO PRE-REGISTRADA (escrita antes de rodar): o modelo NUNCA foi treinado a se auto-avaliar; c_sim tem
AUROC < 0,6 e fica quase constante (o 350M diz "Sim" a tudo ou "Nao" a tudo). A verossimilhanca dos
argumentos tem AUROC 0,60–0,70 — o sinal mais barato que existe, nunca lido neste projeto. Combinada, sobe
o AUROC fim-a-fim de ~0,64 para 0,70–0,75; se NAO subir, o erro de argumento nao esta' na incerteza do
modelo (ele erra CONFIANTE — §2u/§2w: sintetiza e-mail, traduz chave), e so' treino conserta.

Uso:
  python comeia/eval/calibracao_argumentos.py --peft comeia/models/e19c-s42 comeia/models/e19c-s43 ...
  (le' comeia/eval/results/casos_calib_<adapter>.jsonl, saida do G-C1 com --casos-dir)
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from calibracao_agentica import auroc, aurc_e_cobertura, ece, resumo   # noqa: E402
from eval_agentic_exec import partes                                     # noqa: E402

PERGUNTA = "A chamada acima está correta e completa para o pedido? Responda apenas Sim ou Não."
SIM = ("Sim", " Sim", "sim", " sim", "SIM")
NAO = ("Não", " Não", "não", " não", "Nao", " Nao", "nao", " nao", "NÃO")
MAX_POS = 2040        # bee-350m: max_position_embeddings 2048; folga para o cabecalho final


def primeiros_ids(tok, variantes):
    """1º token de cada variante — so' quando ele cobre a PALAVRA inteira ('Nao' -> 'Na'+'o' ficaria contando
    tudo que comeca por 'Na'; fica de fora)."""
    ids = []
    for v in variantes:
        t = tok(v, add_special_tokens=False)["input_ids"]
        if t and t[0] not in ids and tok.decode([t[0]]).strip().lower() == v.strip().lower():
            ids.append(t[0])
    return ids


def sinais_de_argumento(lps: list[float], offsets, bruto: str) -> dict:
    """lps = logP de cada token do bruto; offsets = (ini, fim) em caracteres de cada token."""
    k = bruto.find('"args"')
    idx_args = [j for j, (a, b) in enumerate(offsets) if k >= 0 and b > k] or list(range(len(lps)))
    la = [lps[j] for j in idx_args]
    return {"lp_media_all": sum(lps) / len(lps), "lp_min_all": min(lps),
            "lp_media_args": sum(la) / len(la), "lp_min_args": min(la), "n_tok_args": len(la), "n_tok_all": len(lps),
            "args_encontrado": k >= 0}


def bloco(nome: str, sinal: list[float], certo: list[bool]) -> dict:
    a, cov = aurc_e_cobertura(sinal, certo)
    return {"n": len(certo), "acc": sum(certo) / len(certo), "auroc": auroc(sinal, certo), "aurc": a, **cov,
            "sinal_medio_certo": sum(s for s, c in zip(sinal, certo) if c) / max(1, sum(certo)),
            "sinal_medio_errado": sum(s for s, c in zip(sinal, certo) if not c) / max(1, len(certo) - sum(certo))}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", nargs="+", required=True)
    ap.add_argument("--data", type=Path, default=RAIZ / "data" / "processed" / "holdout_balanceado.eval.jsonl")
    ap.add_argument("--casos-dir", type=Path, default=RAIZ / "eval" / "results")
    ap.add_argument("--max-len", type=int, default=1700, help="corte do PREFIXO pela esquerda (como no G-C1)")
    ap.add_argument("--lote", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--saida", default="docs/calibracao-argumentos-350m-2026-09-19.json")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    rows = [json.loads(l) for l in a.data.read_text(encoding="utf-8").splitlines() if l.strip()]
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    ids_sim, ids_nao = primeiros_ids(tok, SIM), primeiros_ids(tok, NAO)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"holdout {len(rows)} · Sim {[tok.decode([i]) for i in ids_sim]} · Nao {[tok.decode([i]) for i in ids_nao]} · {dev}")
    print(f"transformers {__import__('transformers').__version__} · peft {__import__('peft').__version__} · torch {torch.__version__}")
    if set(ids_sim) & set(ids_nao):
        print("🔴 Sim e Nao compartilham o primeiro token — o Noul nao e' legivel neste tokenizador"); return 1

    # prefixos (identicos aos do G-C1 / eval --chat) e o texto do resto do dialogo
    prefixos, textos = [], []
    for r in rows:
        sistema, usuario, ref, kind = partes(r)
        base_msgs = ([{"role": "system", "content": sistema}] if sistema else []) + [{"role": "user", "content": usuario}]
        prefixos.append(tok.apply_chat_template(base_msgs, tokenize=False, add_generation_prompt=True))
        textos.append(base_msgs)

    base = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).to(dev).eval()
    saida = {"_regua": {"data": str(a.data), "pergunta": PERGUNTA, "ids_sim": ids_sim, "ids_nao": ids_nao, "max_len_prefixo": a.max_len,
                        "max_pos": MAX_POS, "lote": a.lote, "transformers": __import__("transformers").__version__,
                        "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else "cpu"}, "adapters": {}}

    for adp in a.peft:
        nome = Path(adp).name
        pc = a.casos_dir / f"casos_calib_{nome}.jsonl"
        if not pc.exists():
            print(f"\n{nome}: sem {pc.name} — rode o G-C1 com --casos-dir"); continue
        calib = {c["i"]: c for c in (json.loads(l) for l in pc.read_text(encoding="utf-8").splitlines() if l.strip())}
        def chamou(g):
            return bool(g and (g.get("chamou") if "chamou" in g else (g.get("ferramenta_pred") or g.get("over_call"))))
        chamados = [c for c in calib.values() if chamou(c.get("greedy")) and c["greedy"].get("bruto")]
        if not chamados:
            print(f"\n{nome}: sem despejo greedy no casos_calib — nada a medir"); continue
        if a.limit:
            chamados = chamados[: a.limit]
        t0 = time.time()
        modelo = PeftModel.from_pretrained(base, adp).eval()

        # sequencias: prefixo (cortado a esquerda) + bruto + resto (im_end, pergunta, cabecalho do assistente)
        seqs, spans, offs, cortados = [], [], [], 0
        for c in chamados:
            i = c["i"]; bruto = c["greedy"]["bruto"]
            full = tok.apply_chat_template(textos[i - 1] + [{"role": "assistant", "content": bruto}, {"role": "user", "content": PERGUNTA}],
                                           tokenize=False, add_generation_prompt=True)
            pre = prefixos[i - 1]
            assert full.startswith(pre) and full[len(pre):].startswith(bruto), f"template nao decompoe no caso {i}"
            resto = full[len(pre) + len(bruto):]
            enc = tok(bruto, add_special_tokens=False, return_offsets_mapping=True)
            ids_b, off_b = enc["input_ids"], enc["offset_mapping"]
            ids_p = tok(pre, add_special_tokens=False)["input_ids"]
            ids_r = tok(resto, add_special_tokens=False)["input_ids"]
            teto = min(a.max_len, MAX_POS - len(ids_b) - len(ids_r))
            if len(ids_p) > teto:
                cortados += 1; ids_p = ids_p[-teto:]
            seqs.append(ids_p + ids_b + ids_r); spans.append((len(ids_p), len(ids_p) + len(ids_b))); offs.append(off_b)
        print(f"\n{nome}: {len(chamados)} casos chamados · prefixos cortados {cortados} · seq max {max(len(s) for s in seqs)} tokens")

        por_caso = {}; top1 = Counter(); exemplos_top = []
        pad = tok.pad_token_id
        with torch.no_grad():
            for b0 in range(0, len(seqs), a.lote):
                lote = seqs[b0: b0 + a.lote]; L = max(len(s) for s in lote)
                X = torch.tensor([[pad] * (L - len(s)) + s for s in lote], device=dev)
                A = torch.tensor([[0] * (L - len(s)) + [1] * len(s) for s in lote], device=dev)
                pos = (A.cumsum(-1) - 1).clamp(min=0)
                lg = modelo(input_ids=X, attention_mask=A, position_ids=pos).logits
                for j, s in enumerate(lote):
                    c = chamados[b0 + j]; off = L - len(s); ini, fim = spans[b0 + j]
                    ult = torch.log_softmax(lg[j, -1].float(), -1)
                    p_sim = float(torch.logsumexp(ult[ids_sim], 0).exp()); p_nao = float(torch.logsumexp(ult[ids_nao], 0).exp())
                    top = torch.topk(ult, 5); top1[tok.decode([int(top.indices[0])])] += 1
                    if len(exemplos_top) < 3:
                        exemplos_top.append([(tok.decode([int(i)]), round(float(v.exp()), 3)) for v, i in zip(top.values, top.indices)])
                    # logP do token t do bruto = log_softmax(logits na posicao t-1)[X[t]]
                    lsm = torch.log_softmax(lg[j, off + ini - 1: off + fim - 1].float(), -1)
                    alvo = X[j, off + ini: off + fim]
                    lps = lsm.gather(1, alvo[:, None])[:, 0].tolist()
                    sig = sinais_de_argumento(lps, offs[b0 + j], c["greedy"]["bruto"])
                    por_caso[c["i"]] = {"c_sim": p_sim / max(1e-12, p_sim + p_nao), "p_sim": p_sim, "p_nao": p_nao, **sig}
        del modelo; torch.cuda.empty_cache()
        base = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).to(dev).eval()

        # ── metricas entre os casos chamados
        R = {"adapter": adp, "n_chamados": len(chamados), "segundos": round(time.time() - t0),
             "prefixos_cortados": cortados, "args_nao_encontrado": sum(1 for v in por_caso.values() if not v["args_encontrado"]),
             "primeiro_token_apos_pergunta": {"top1_mais_comuns": top1.most_common(6), "exemplos_top5": exemplos_top}}
        def certo_de(c):
            return bool(c["greedy"]["exec_ok"]) if c["is_tool"] else False
        for pop, filtro in (("chamados_todos", lambda c: True), ("chamados_tool", lambda c: c["is_tool"])):
            cs = [c for c in chamados if filtro(c)]
            certo = [certo_de(c) for c in cs]
            R[pop] = {"n": len(cs), "acc": sum(certo) / len(certo)}
            for sinal in ("c_sim", "lp_media_args", "lp_min_args", "lp_media_all", "lp_min_all"):
                R[pop][sinal] = bloco(sinal, [por_caso[c["i"]][sinal] for c in cs], certo)
            cs_conf = [por_caso[c["i"]]["c_sim"] for c in cs]
            R[pop]["c_sim"]["ece"] = ece(cs_conf, certo); R[pop]["c_sim"]["media"] = sum(cs_conf) / len(cs_conf)
            R[pop]["c_sim"]["frac>0.5"] = sum(1 for v in cs_conf if v > 0.5) / len(cs_conf)
            R[pop]["c_sim"]["frac_p_sim+p_nao<0.01"] = sum(1 for c in cs if por_caso[c["i"]]["p_sim"] + por_caso[c["i"]]["p_nao"] < 0.01) / len(cs)

        # ── fim-a-fim recomposto sobre os 804 (correto = exec_ok se tool, nao-chamou se texto)
        todos = list(calib.values())
        def conf_e2e(c, fator):
            g = c["greedy"]
            if not chamou(g):
                return 1 - c["p_call"]
            nome = g.get("ferramenta_chamada") or g.get("ferramenta_pred") or c["pred_tool"]
            pt = c["p_tool"].get(nome, 0.0) if c["p_tool"] else 1.0
            return c["p_call"] * pt * fator(c)
        certo_e2e = [(bool(c["greedy"] and c["greedy"].get("exec_ok")) if c["is_tool"] else not chamou(c["greedy"])) for c in todos]
        variantes = {"gc1": lambda c: 1.0,
                     "gc1_x_c_sim": lambda c: por_caso.get(c["i"], {}).get("c_sim", 1.0),
                     "gc1_x_exp_lp_media_args": lambda c: math.exp(por_caso[c["i"]]["lp_media_args"]) if c["i"] in por_caso else 1.0,
                     "gc1_x_exp_lp_min_args": lambda c: math.exp(por_caso[c["i"]]["lp_min_args"]) if c["i"] in por_caso else 1.0}
        R["fim_a_fim"] = {k: resumo(k, [conf_e2e(c, f) for c in todos], certo_e2e) for k, f in variantes.items()}
        saida["adapters"][nome] = R
        pcs = a.casos_dir / f"casos_calibargs_{nome}.jsonl"
        pcs.write_text("\n".join(json.dumps({"i": i, **v}, ensure_ascii=False) for i, v in por_caso.items()) + "\n", encoding="utf-8")

        T = R["chamados_tool"]; A_ = R["chamados_todos"]; E = R["fim_a_fim"]
        print(f"  ({R['segundos']} s)  chamados {A_['n']} (tool {T['n']}, acc {T['acc']:.3f}) · args nao achado {R['args_nao_encontrado']}")
        print(f"  1º token que o modelo emitiria apos a pergunta: {top1.most_common(4)} · ex.: {exemplos_top[0] if exemplos_top else '-'}")
        print(f"  c_sim (tool)     AUROC {T['c_sim']['auroc']:.3f} · ECE {T['c_sim']['ece']:.3f} · media {T['c_sim']['media']:.3f} · frac>0,5 {T['c_sim']['frac>0.5']:.0%} · "
              f"P(Sim)+P(Nao)<1% em {T['c_sim']['frac_p_sim+p_nao<0.01']:.0%} · acc@50 {T['c_sim']['acc@50']:.3f}")
        for s in ("lp_media_args", "lp_min_args", "lp_media_all", "lp_min_all"):
            print(f"  {s:<16} (tool) AUROC {T[s]['auroc']:.3f} · acc@50 {T[s]['acc@50']:.3f} · medio certo {T[s]['sinal_medio_certo']:.3f} errado {T[s]['sinal_medio_errado']:.3f}   "
                  f"(todos) AUROC {A_[s]['auroc']:.3f}")
        for k, d in E.items():
            print(f"  e2e {k:<24} AUROC {d['auroc_conf_vs_certo']:.3f} · AURC {d['aurc']:.3f} · acc@25 {d['acc@25']:.3f} acc@50 {d['acc@50']:.3f} acc@75 {d['acc@75']:.3f} acc@100 {d['acc@100']:.3f} · ECE {d['ece']:.3f}")
        Path(a.saida).write_text(json.dumps(saida, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nsalvo em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
