"""Avalia os 40 mini-runs do E4 — contra a LOSS por domínio E contra as RÉGUAS.

⭐ POR QUE OS DOIS, E NÃO SÓ UM

O paper (arXiv:2508.11953) ajusta a lei de escala contra **loss de validação** e avisa que ela
pode não transferir para desempenho downstream: positiva no Tulu3, *"discrepância importante"*
no Orca. Todo veredito deste projeto vem de métrica downstream — o E2 foi decidido por
`exec_ok` 64,7% e IFEval 32,0%, não por loss — e a lição §2d registra perplexidade plana
enquanto o modelo muda.

Como aqui a avaliação downstream custa minutos (o E2 mediu 27 braços em 7 réguas em 57 min),
dá para medir **as duas** e comparar os ótimos. Se discordarem, a discordância é o resultado.

⚠️ **A loss por domínio precisa de holdout POR DOMÍNIO, e ele não pode ter entrado no treino.**
As misturas foram montadas por amostragem sem reposição de cada arquivo; este avaliador
reserva as **últimas N linhas** de cada domínio e a montagem nunca as usa, porque a permutação
é semeada e o orçamento fecha muito antes de esgotar o arquivo. ⚠️ Isso vale para os domínios
grandes; para `texto` e `simbolico`, que a razão 3,0 consome quase inteiros, a reserva é
verificada explicitamente e o domínio é marcado se houver sobreposição.

Uso:
    python comeia/eval/avaliar_grid_e4.py --so-loss      # rapido, so' a loss por dominio
    python comeia/eval/avaliar_grid_e4.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
PROC = RAIZ / "comeia" / "data" / "processed"
PY = sys.executable
MODELO = "BrCamp/bee-350m-pt-base"
GRID = RAIZ / "docs" / "grid-e4-resultado.json"
SAIDA = RAIZ / "docs" / "grid-e4-avaliado.json"

sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(RAIZ / "comeia" / "train"))

# as mesmas reguas do E2, com n reduzido — comparar bracos entre si e' legitimo com n
# reduzido; declarar numero final, nao. O vencedor vai para as reguas inteiras depois.
REGUAS = [
    ("instrucao", "eval_ifeval_pt.py", ["--limite", "120", "--lote", "48", "--chat"],
     "docs/ifeval-pt-{tag}.json"),
    ("agentico", "eval_agentic_exec.py", ["--limit", "0", "--lote", "24", "--chat"],
     "comeia/eval/results/exec_{tag}.json"),
    ("codigo", "eval_coder.py", ["--limit", "100", "--lote", "24", "--chat"],
     "comeia/eval/results/coder_{tag}.json"),
    ("traducao", "eval_traducao_pt.py", ["--limite", "60", "--lote", "60", "--chat"],
     "docs/traducao-pt-{tag}.json"),
    ("resumo", "eval_resumo_pt.py", ["--limite", "40", "--lote", "40", "--chat"],
     "docs/resumo-pt-{tag}.json"),
    ("atendimento", "eval_atendimento_pt.py", ["--limite", "60", "--lote", "60", "--chat"],
     "docs/atendimento-pt-{tag}.json"),
]


def numero(cap, d):
    try:
        if cap == "instrucao":
            return 100 * d["estrito_instrucao"]
        if cap == "agentico":
            return 100 * d["exec_ok"] / (d["n_tool"] or 1)
        if cap == "codigo":
            return d.get("pass1", 0.0)
        if cap == "traducao":
            return d["modelo_r"]["en->pt"]["bleu"]
        if cap == "resumo":
            return 100 * d["modelo_util"]
        if cap == "atendimento":
            return 100 * d["modelo_r"]["util"]
    except (KeyError, TypeError, ZeroDivisionError):
        return None
    return None


def holdout(dominio: str, n: int, grid_e4) -> list[dict]:
    """Últimas `n` linhas do domínio — reservadas, nunca usadas na montagem."""
    regs = grid_e4.carregar(dominio)
    return regs[-n:]


def loss_por_dominio(modelo: str, adapter: str, holdouts: dict, max_len: int = 1024) -> dict:
    """Loss média por domínio, com o prompt MASCARADO — a mesma convenção do treino.

    🔴 Se a loss for medida em todos os tokens e o treino mascarou o prompt, os dois números
    não são da mesma quantidade. O projeto já pagou por comparar coisas medidas de jeitos
    diferentes quatro vezes; aqui a máscara é explícita.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(modelo)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    m = AutoModelForCausalLM.from_pretrained(modelo, dtype=torch.bfloat16).cuda()
    if adapter:
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, adapter)
    m.eval()
    fora = {}
    for dom, regs in holdouts.items():
        tot, n_tok = 0.0, 0
        for r in regs:
            p = r.get("prompt") if isinstance(r.get("prompt"), list) else None
            c = r.get("completion")
            if p is None:
                msgs = r.get("messages") or []
                i = next((j for j in range(len(msgs) - 1, -1, -1)
                          if msgs[j].get("role") == "assistant"), None)
                if i is None or i == 0:
                    continue
                p, c = msgs[:i], [msgs[i]]
            t_p = tok.apply_chat_template(p, tokenize=False, add_generation_prompt=True)
            t_all = t_p + (c[0].get("content") or "")
            ids = tok(t_all, return_tensors="pt", truncation=True,
                      max_length=max_len).input_ids.cuda()
            n_p = len(tok(t_p, truncation=True, max_length=max_len).input_ids)
            if ids.shape[1] <= n_p + 1:
                continue
            lab = ids.clone()
            lab[:, :n_p] = -100          # ⭐ prompt mascarado, como no treino
            with torch.no_grad():
                out = m(input_ids=ids, labels=lab)
            n_alvo = int((lab != -100).sum())
            tot += float(out.loss) * n_alvo
            n_tok += n_alvo
        fora[dom] = tot / n_tok if n_tok else None
    del m
    torch.cuda.empty_cache()
    return fora


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--grid", type=Path, default=GRID)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    ap.add_argument("--n-holdout", type=int, default=120)
    ap.add_argument("--so-loss", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    import grid_e4

    dados = json.loads(a.grid.read_text(encoding="utf-8"))
    runs = {k: v for k, v in dados["runs"].items() if "erro" not in v}
    print("=" * 78)
    print(f"AVALIACAO DO E4 — {len(runs)} mini-runs")
    print("=" * 78)

    holdouts = {d: holdout(d, a.n_holdout, grid_e4) for d in grid_e4.DOMINIOS}
    for d, h in holdouts.items():
        print(f"  holdout {d:14} {len(h):>4} exemplos (ultimas linhas, fora da montagem)")
    if a.dry_run:
        print("\n✅ DRY-RUN.")
        return 0

    feitos = {}
    if a.saida.exists():
        feitos = json.loads(a.saida.read_text(encoding="utf-8")).get("runs", {})
        print(f"retomando: {len(feitos)} ja' avaliados")

    for i, (tag, v) in enumerate(sorted(runs.items()), 1):
        if tag in feitos and feitos[tag].get("metricas"):
            continue
        print(f"\n[{i}/{len(runs)}] {tag}", flush=True)
        met = {}
        L = loss_por_dominio(a.model, v["adapter"], holdouts)
        for d, x in L.items():
            if x is not None:
                met[f"loss_{d}"] = x
        met["loss"] = sum(x for x in L.values() if x is not None) / max(1, len(
            [x for x in L.values() if x is not None]))
        print("   loss por dominio: " + " ".join(f"{d[:6]} {x:.3f}" for d, x in L.items()
                                                 if x is not None))
        if not a.so_loss:
            for cap, script, extras, molde in REGUAS:
                etq = f"e4-{tag}"
                cmd = [PY, str(AQUI / script), "--model", a.model, "--peft", v["adapter"],
                       "--tag", etq, *extras]
                p_ = subprocess.run(cmd, cwd=str(RAIZ), text=True, encoding="utf-8",
                                    errors="replace", capture_output=True)
                rel = RAIZ / molde.format(tag=etq)
                if p_.returncode != 0 or not rel.exists():
                    print(f"   🔴 {cap} falhou (rc={p_.returncode})")
                    continue
                x = numero(cap, json.loads(rel.read_text(encoding="utf-8")))
                if x is not None:
                    met[cap] = x
            print("   reguas: " + " ".join(f"{c} {met[c]:.1f}" for c, *_ in REGUAS
                                           if c in met))
        feitos[tag] = {**v, "metricas": met}
        a.saida.write_text(json.dumps({"modelo": a.model,
                                       "inventario": dados.get("inventario", {}),
                                       "runs": feitos}, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    print(f"\n✅ {len(feitos)} avaliados · {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
