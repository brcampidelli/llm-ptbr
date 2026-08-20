"""Avaliacao FUNCIONAL do tool-use: a chamada EXECUTA e cumpre a tarefa? (+ pass@k)

Responde duas perguntas que o projeto nunca mediu:

  1. TAXA DE SUCESSO REAL — executa a chamada prevista e a de referencia no mundo
     simulado (tools_exec.py) e compara os RESULTADOS. Equivalencia funcional:
     "6*9" e "9*6" contam igual; "8/3" com a ferramenta certa conta como ERRO.
     Ate agora so tinhamos eval_loss (predicao de token sob mascara) e "ferramenta
     certa" — e da para acertar a ferramenta e falhar a tarefa.

  2. ⭐ pass@k — a UNICA medicao que decide se AUTOAPRENDIZADO e viavel neste modelo.
     STaR/rejection-sampling nao exige que o modelo seja bom em media; exige que a
     CAUDA contenha acertos que um verificador barato saiba reconhecer. Se
     pass@16 >> pass@1, ha o que colher e o laco fecha. Se pass@16 ~ pass@1, nao ha
     diversidade util e o caminho esta fechado — por falta de cauda, nao por
     contagem de parametros (ver docs/agentico-e-autoaprendizado.md).

Uso:
    python comeia/eval/eval_agentic_exec.py --model BrCamp/bee-150m-pt-sft            # greedy
    python comeia/eval/eval_agentic_exec.py --model ... --k 16 --temp 0.8 --tag passk
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # comeia/
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl, strip_think           # noqa: E402
import tools_exec as TE                               # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

PADRAO_EVAL = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson. Com n=85 o erro e da ordem de +-10pp — reportar ponto seria mentira."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def mensagens(row: dict) -> list[dict]:
    if row.get("messages"):
        return row["messages"]
    return list(row.get("prompt") or []) + list(row.get("completion") or [])


def partes(row: dict) -> tuple[str | None, str, str, str]:
    sistema = usuario = ref = None
    for m in mensagens(row):
        if m["role"] == "system":
            sistema = m["content"]
        elif m["role"] == "user":
            usuario = m["content"]
        elif m["role"] == "assistant":
            ref = m["content"]
    return sistema, usuario or "", ref or "", row.get("kind", "?")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", default=None, help="adapter LoRA opcional")
    ap.add_argument("--data", type=Path, default=PADRAO_EVAL)
    ap.add_argument("--k", type=int, default=1, help="amostras por exemplo (k>1 liga pass@k)")
    ap.add_argument("--temp", type=float, default=0.8, help="so usado quando k>1")
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--lote", type=int, default=24,
                    help="exemplos por lote de geracao (so' vale para k=1)")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--chat", action="store_true",
                    help="usa o chat template. So' DEPOIS do SFT — ver comentario em gerar()")
    ap.add_argument("--dry-run", action="store_true",
                    help="executa as referencias e sai, sem carregar modelo")
    args = ap.parse_args()

    linhas = [r for r in read_jsonl(args.data) if mensagens(r)]
    if args.limit:
        linhas = linhas[: args.limit]

    TE.garantir_fixtures()
    catalogo = _d7.load_tools()

    # ⚠️ GUARDA — ABORTA (2026-08-12). Antes de medir qualquer modelo, executar as
    # REFERENCIAS. Se o proprio gabarito nao executa, o exemplo e impossivel de acertar
    # e o numero final sai artificialmente baixo — culpando o modelo por um defeito do
    # avaliador. Foi exatamente o que aconteceu na v1 deste script: mundo simulado
    # fechado, 35/85 referencias falhando, taxa de sucesso "23,5%" que nao existia.
    impossiveis = []
    for row in linhas:
        _, _, ref, tipo = partes(row)
        if tipo != "tool_call":
            continue
        obj = _d7.extract_json(ref)
        ok, motivo = TE.executar(obj) if obj else (False, "referencia sem JSON")
        if not ok:
            impossiveis.append(((obj or {}).get("tool", "?"), str(motivo)[:70]))
    if impossiveis:
        n_ref = sum(1 for r in linhas if r.get("kind") == "tool_call")
        print(f"ERRO: {len(impossiveis)}/{n_ref} chamadas de REFERENCIA nao executam.",
              file=sys.stderr)
        print("O avaliador esta errado, nao o modelo. Primeiras:", file=sys.stderr)
        for t, m in impossiveis[:6]:
            print(f"  {t}: {m}", file=sys.stderr)
        return 1
    print(f"guarda: as {sum(1 for r in linhas if r.get('kind') == 'tool_call')} "
          f"referencias executam [OK]\n")

    if args.dry_run:
        # a guarda acima ja' e' o dry-run inteiro: executar todos os gabaritos ANTES de
        # carregar modelo e' exatamente o criterio do Estagio 0. Aqui so' se sai antes da GPU.
        print("✅ DRY-RUN: referencias validadas. Nenhum modelo foi carregado.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(dispositivo)
    if args.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, args.peft)
    modelo.eval()

    amostrado = args.k > 1
    n_par = sum(p.numel() for p in modelo.parameters())
    # ⚠️ O NUMERO DE PARAMETROS VAI IMPRESSO porque o nome nao basta. O default deste arquivo
    #    era `bee-150m-pt-sft`: contem "bee", passa em qualquer guarda de nome, e mediria o
    #    modelo da geracao anterior sem que uma linha do relatorio denunciasse.
    print(f"modelo : {args.model}  ({n_par / 1e6:.1f}M parametros)")
    print(f"adapter: {args.peft or '(base, sem adapter)'}")
    print(f"holdout: {len(linhas)} exemplos · {dispositivo}")
    print(f"modo   : {'amostragem k=%d T=%.2f (pass@k)' % (args.k, args.temp) if amostrado else 'greedy (k=1)'}\n")

    def gerar(sistema: str | None, usuario: str, k: int) -> list[str]:
        msgs = ([{"role": "system", "content": sistema}] if sistema else []) \
            + [{"role": "user", "content": usuario}]
        # 🔴 CHAT TEMPLATE E' ESCOLHA EXPLICITA (--chat), NAO DETECCAO AUTOMATICA.
        #    `tok.chat_template` do bee-350m-pt-base devolve **True**: o `TokenizersBackend`
        #    oferece um ChatML padrao mesmo sem nada no tokenizer_config.json. Mas o base foi
        #    pre-treinado em texto cru e nunca viu `<|im_start|>` — medi-lo por esse template
        #    mede a reacao a tokens ineditos, e o sintoma sai como "o base nao sabe usar
        #    ferramenta". BASE = prompt simples; depois do SFT com ChatML = --chat.
        if args.chat:
            txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        else:
            txt = (f"{sistema}\n\n" if sistema else "") + f"Usuario: {usuario}\nAssistente:"
        ent = tok(txt, return_tensors="pt").to(dispositivo)
        n = ent["input_ids"].shape[1]
        cfg = dict(max_new_tokens=args.max_new, pad_token_id=tok.pad_token_id or tok.eos_token_id)
        if k > 1:
            cfg.update(do_sample=True, temperature=args.temp, top_p=0.95, num_return_sequences=k)
        else:
            cfg.update(do_sample=False)
        with torch.no_grad():
            g = modelo.generate(**ent, **cfg)
        return [tok.decode(s[n:], skip_special_tokens=True).strip() for s in g]

    def gerar_em_lote(rows: list[dict], lote: int) -> list[list[str]]:
        """Gera greedy para TODAS as linhas, em lotes. So' vale para k=1.

        ⚠️ POR QUE ISTO EXISTE. Com batch 1 esta regua levou 21 min sem sair dos exemplos
        21-39 e disparou o monitor de estagnacao DUAS vezes. Nas duas eu diagnostiquei
        errado: na primeira culpei a calculadora do mundo simulado (que de fato tinha um bug
        de exaustao de recurso, corrigido — mas nao era este caso), e na segunda chamei de
        travamento o que era lentidao. O `py-spy dump` foi o que resolveu: a pilha estava
        dentro de `generate` → `_sample` → forward do Qwen3, e o CPU subia de forma
        constante. Estava trabalhando, a 22% de GPU.
        ⭐ A licao e' de instrumentacao: `utilization.gpu` de 22% com progresso invisivel e'
        indistinguivel de travamento SE a regua so' imprime a cada 20 exemplos. Ou o passo
        e' menor, ou o log e' mais frequente — mas nao os dois grandes ao mesmo tempo.
        """
        textos = []
        for row in rows:
            sistema, usuario, _, _ = partes(row)
            if args.chat:
                msgs = ([{"role": "system", "content": sistema}] if sistema else []) \
                    + [{"role": "user", "content": usuario}]
                textos.append(tok.apply_chat_template(msgs, tokenize=False,
                                                      add_generation_prompt=True))
            else:
                textos.append((f"{sistema}\n\n" if sistema else "")
                              + f"Usuario: {usuario}\nAssistente:")
        tok.padding_side = "left"
        fora: list[list[str]] = []
        b, i2 = lote, 0
        t0 = time.time()
        while i2 < len(textos):
            bloco = textos[i2:i2 + b]
            ent = tok(bloco, return_tensors="pt", padding=True, truncation=True,
                      max_length=1536).to(dispositivo)
            try:
                with torch.no_grad():
                    g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=False,
                                        pad_token_id=tok.pad_token_id or tok.eos_token_id)
            except torch.OutOfMemoryError:
                torch.cuda.empty_cache()
                if b == 1:
                    raise
                b = max(1, b // 2)
                print(f"  ⚠️ OOM — lote {b}, refazendo", flush=True)
                continue
            plen = ent["input_ids"].shape[1]
            for j in range(len(bloco)):
                fora.append([tok.decode(g[j][plen:], skip_special_tokens=True).strip()])
            del g
            if dispositivo == "cuda":
                torch.cuda.empty_cache()
            i2 += len(bloco)
            dt = (time.time() - t0) / 60
            print(f"  gerando {i2}/{len(textos)} · {dt:.1f} min · "
                  f"resta ~{dt / i2 * (len(textos) - i2):.1f} min", flush=True)
        return fora

    n_tool = n_text = 0
    json_ok = tool_right = args_exact = exec_ok = 0
    over = under = trunc = 0
    passou_alguma = 0          # pass@k
    soma_taxa = 0.0            # pass@1 estimado a partir das k amostras
    por_ferramenta: dict[str, list[int]] = {}

    # k>1 (pass@k) continua um-a-um: `num_return_sequences` ja' enche o batch sozinho
    prontas = gerar_em_lote(linhas, args.lote) if args.k == 1 else None

    for i, row in enumerate(linhas, 1):
        sistema, usuario, ref, tipo = partes(row)
        saidas = prontas[i - 1] if prontas is not None else gerar(sistema, usuario, args.k)
        ref_obj = _d7.extract_json(ref)

        if tipo == "text":
            n_text += 1
            # over-calling conta na PRIMEIRA amostra (a que seria servida)
            if _d7.extract_json(strip_think(saidas[0])[0]) is not None:
                over += 1
            continue

        n_tool += 1
        nome_ref = (ref_obj or {}).get("tool", "?")
        ok_ref, res_ref = TE.executar(ref_obj) if ref_obj else (False, None)

        acertos = 0
        primeira = True
        for bruto in saidas:
            pred, _ = strip_think(bruto)
            obj = _d7.extract_json(pred)

            if primeira:                         # metricas classicas: so a 1a amostra
                if obj is None:
                    if pred.lstrip().startswith("{"):
                        trunc += 1
                    else:
                        under += 1
                else:
                    if _d7.validate_call(obj, catalogo) is None:
                        json_ok += 1
                    if ref_obj and obj.get("tool") == ref_obj.get("tool"):
                        tool_right += 1
                        if (obj.get("args") or {}) == (ref_obj.get("args") or {}):
                            args_exact += 1
                primeira = False

            if obj is not None and ok_ref:
                ok_p, res_p = TE.executar(obj)
                if ok_p and TE.resultados_batem(res_p, res_ref):
                    acertos += 1

        if acertos and saidas:
            passou_alguma += 1
        soma_taxa += acertos / max(1, len(saidas))
        if acertos and args.k == 1:
            exec_ok += 1
        por_ferramenta.setdefault(nome_ref, []).append(1 if acertos else 0)

        if i % 20 == 0 or i == len(linhas):
            print(f"  {i}/{len(linhas)}", flush=True)

    def linha(rot: str, k: int, n: int) -> str:
        if not n:
            return f"  {rot:<34} n/a"
        lo, hi = wilson(k, n)
        return f"  {rot:<34} {k}/{n} = {k/n:6.1%}   [{lo:.1%}–{hi:.1%}]"

    print("\n" + "=" * 72)
    print(f"CASOS QUE EXIGEM FERRAMENTA: {n_tool}")
    print(linha("JSON valido (catalogo)", json_ok, n_tool))
    print(linha("ferramenta certa", tool_right, n_tool))
    print(linha("argumentos identicos", args_exact, n_tool))
    if args.k == 1:
        print(linha("⭐ EXECUTOU E CUMPRIU A TAREFA", exec_ok, n_tool))
    print(linha("under-calling", under, n_tool))
    print(linha("truncado (--max-new)", trunc, n_tool))
    print("-" * 72)
    print(f"CASOS QUE NAO EXIGEM FERRAMENTA: {n_text}")
    print(linha("⚠️ over-calling", over, n_text))

    resultado = {
        "modelo": args.model, "peft": args.peft, "k": args.k, "temp": args.temp if amostrado else None,
        "n_tool": n_tool, "n_text": n_text, "json_ok": json_ok, "tool_right": tool_right,
        "args_exact": args_exact, "exec_ok": exec_ok if args.k == 1 else None,
        "under_call": under, "truncado": trunc, "over_call": over,
    }

    if amostrado:
        p1 = soma_taxa / max(1, n_tool)
        pk = passou_alguma / max(1, n_tool)
        print("=" * 72)
        print(f"pass@1  (media das {args.k} amostras)  {p1:6.1%}")
        print(f"pass@{args.k} (>=1 amostra correta)     {pk:6.1%}")
        print(f"folga pass@{args.k} - pass@1        {(pk - p1) * 100:+5.1f} pp")
        # ⚠️ O criterio de decisao e a folga ABSOLUTA e a fracao do espaco restante que a
        # cauda captura — nunca uma razao pk/p1. A v1 usava `pk > p1 * 1.5` e declarou
        # "sem cauda" para p1=52,3% / pk=72,9%: com p1 alto, exigir 1,5x equivale a exigir
        # 78%, quase o teto. Criterio multiplicativo pune justamente o modelo que ja e bom.
        captura = (pk - p1) / (1 - p1) if p1 < 1 else 0.0
        print(f"do espaco que faltava, a cauda captura {captura:5.1%}")
        print()
        if (pk - p1) >= 0.05 and captura >= 0.15:
            print("VEREDITO: HA CAUDA. Rejection sampling / STaR e VIAVEL neste modelo —")
            print(f"          {round((pk - p1) * n_tool)} exemplos tem solucao correta que a geracao")
            print("          gulosa nao acha, e um verificador deterministico as reconhece.")
        else:
            print("VEREDITO: cauda insuficiente. Amostrar quase nao acrescenta ao greedy;")
            print("          rejection sampling teria pouco o que colher.")
        resultado.update({"pass_1": round(p1, 4), f"pass_{args.k}": round(pk, 4)})

    duros = {k: v for k, v in por_ferramenta.items() if len(v) >= 4}
    if duros:
        print("\npor ferramenta (>=4 exemplos; abaixo disso nao e decidivel):")
        for nome, v in sorted(duros.items(), key=lambda x: sum(x[1]) / len(x[1])):
            print(f"  {nome:<24} {sum(v)}/{len(v)} = {sum(v)/len(v):.0%}")
    resultado["por_ferramenta"] = {k: [sum(v), len(v)] for k, v in por_ferramenta.items()}

    if args.tag:
        saida = Path(__file__).resolve().parent / "results" / f"exec_{args.tag}.json"
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
