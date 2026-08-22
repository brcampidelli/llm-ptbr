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
    ap.add_argument("--parar-controle", action="store_true",
                    help="E5b: tambem parar nos ids de byte C0, onde o terminador do adapter "
                         "cai sob amostragem. Intervencao de runtime, zero treino.")
    ap.add_argument("--dump", action="store_true",
                    help="grava um JSONL por caso (ref, previsto, veredito, saida crua). "
                         "Sem isto so' sobram agregados, e nenhuma analise de MODO DE FALHA "
                         "e' possivel sem re-gerar tudo.")
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
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from paradas import (ids_de_parada, terminador_correto, limpar,
                         cortar_no_controle, primeiro_objeto, ids_de_controle)

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

    PARADAS = ids_de_parada(tok, args.chat)
    if args.parar_controle:
        ctrl = [i for i in ids_de_controle(tok) if i not in PARADAS]
        PARADAS = PARADAS + ctrl
        print(f"parada : +{len(ctrl)} ids de controle (C0) — intervencao de RUNTIME do E5b")
    # 🔴 SEM ISTO A REGUA ZERA MODELOS QUE ACERTAM. Ver comeia/eval/paradas.py: o braco full
    #    FT emitia a chamada exata seguida de <|im_end|>, a geracao nao parava, o caso virava
    #    "truncado" e o parser recebia cinco chamadas concatenadas -> 0%.
    print(f"paradas: {PARADAS} (<|im_end|> primeiro = terminador correto)")
    terminadores: list[bool | None] = []

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
        cfg = dict(max_new_tokens=args.max_new, eos_token_id=PARADAS,
                   pad_token_id=tok.pad_token_id or tok.eos_token_id)
        if k > 1:
            cfg.update(do_sample=True, temperature=args.temp, top_p=0.95, num_return_sequences=k)
        else:
            cfg.update(do_sample=False)
        with torch.no_grad():
            g = modelo.generate(**ent, **cfg)
        crus = [tok.decode(s[n:], skip_special_tokens=False) for s in g]
        terminadores.append(terminador_correto(crus[0]))
        return [limpar(c) for c in crus]

    def gerar_em_lote(rows: list[dict], lote: int, k: int = 1) -> list[list[str]]:
        """Gera para TODAS as linhas, em lotes. Serve para k=1 (greedy) e k>1 (pass@k).

        ⭐ O caminho k>1 era um-a-um, com `num_return_sequences` "enchendo o batch sozinho".
        Nao enchia: medido no E5, batch 4 num modelo de 350M deixa a GPU em 8% — o gargalo
        e' lancamento de kernel por passo de decodificacao, nao computacao. Dava ~100 s por
        exemplo e projetava 4 HORAS para 150 exemplos. Batelando B exemplos x k amostras a
        GPU volta a trabalhar.
        ⚠️ Diagnostico por `py-spy dump --locals` (i: 12 depois de 20 min), nao por deducao:
        o log so' imprime a cada 20 exemplos e nao havia saida nenhuma para ler.

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
            cfg = dict(max_new_tokens=args.max_new, eos_token_id=PARADAS,
                       pad_token_id=tok.pad_token_id or tok.eos_token_id)
            if k > 1:
                cfg.update(do_sample=True, temperature=args.temp, top_p=0.95,
                           num_return_sequences=k)
            else:
                cfg.update(do_sample=False)
            try:
                with torch.no_grad():
                    g = modelo.generate(**ent, **cfg)
            except torch.OutOfMemoryError:
                torch.cuda.empty_cache()
                if b == 1:
                    raise
                b = max(1, b // 2)
                print(f"  ⚠️ OOM — lote {b}, refazendo", flush=True)
                continue
            plen = ent["input_ids"].shape[1]
            # com num_return_sequences=k a saida vem agrupada por linha: [l0k0..l0k(k-1), l1k0..]
            for j in range(len(bloco)):
                crus = [tok.decode(g[j * k + m][plen:], skip_special_tokens=False)
                        for m in range(k)]
                terminadores.append(terminador_correto(crus[0]))
                fora.append([limpar(c) for c in crus])
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
    despejo: list[dict] = []
    exec_ok_h = 0            # regua HARNESS: primeira chamada completa (ver paradas.py)
    servidas_ok = 0          # E5b: acerto da politica "primeira executavel" (realizavel)
    servidas_n = 0           # casos em que alguma amostra executou
    passou_alguma_h = 0
    soma_taxa_h = 0.0
    over_h = 0

    def parse_harness(bruto: str):
        """Le a PRIMEIRA chamada completa, como um harness real faria.

        ⚠️ Regua DIFERENTE da estrita, reportada AO LADO dela — nunca no lugar. A diferenca
        entre as duas e' o tamanho do problema de terminacao; trocar uma pela outra no meio
        de uma comparacao seria mudar o instrumento entre os grupos.
        """
        s = primeiro_objeto(cortar_no_controle(strip_think(bruto)[0]))
        if s is None:
            return None
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            return None
        return o if isinstance(o, dict) else None

    # k>1 (pass@k) continua um-a-um: `num_return_sequences` ja' enche o batch sozinho
    # lote efetivo = lote x k sequencias; divide para nao estourar os 8 GB da 5070
    lote_ef = max(1, args.lote // max(1, args.k))
    prontas = gerar_em_lote(linhas, lote_ef, args.k)

    for i, row in enumerate(linhas, 1):
        sistema, usuario, ref, tipo = partes(row)
        saidas = prontas[i - 1] if prontas is not None else gerar(sistema, usuario, args.k)
        ref_obj = _d7.extract_json(ref)

        if tipo == "text":
            n_text += 1
            # over-calling conta na PRIMEIRA amostra (a que seria servida)
            chamou = _d7.extract_json(strip_think(saidas[0])[0]) is not None
            if chamou:
                over += 1
            # o harness enxerga MAIS chamadas (nao exige que a saida inteira seja uma so'),
            # entao o over-calling dele e' >= o estrito. Medir os dois lados (ver §5).
            if parse_harness(saidas[0]) is not None:
                over_h += 1
            if args.dump:
                despejo.append({"i": i, "tipo": "text", "usuario": usuario,
                                "over_call": chamou, "bruto": saidas[0][:1200]})
            continue

        n_tool += 1
        nome_ref = (ref_obj or {}).get("tool", "?")
        ok_ref, res_ref = TE.executar(ref_obj) if ref_obj else (False, None)

        acertos = acertos_h = 0
        primeira = True
        obj0 = None                              # 1a amostra: a que seria servida
        # 🔴 POLITICA REALIZAVEL EM RUNTIME (E5b). pass@k usa a REFERENCIA para decidir se a
        #    amostra prestou — e em producao nao ha' referencia. O que um harness real sabe
        #    checar e' se a chamada PARSEIA e EXECUTA. Entao a politica honesta e':
        #    "gerar; se nao parseia ou nao executa, retentar; servir a PRIMEIRA executavel".
        #    O acerto dessa politica e' o que o E5b pode entregar; pass@k e' o teto, nao a
        #    entrega.
        servida = None                           # 1a amostra que EXECUTA (sem olhar a ref)
        for bruto in saidas:
            pred, _ = strip_think(bruto)
            obj = _d7.extract_json(pred)

            if primeira:                         # metricas classicas: so a 1a amostra
                obj0 = obj
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

            obj_h = parse_harness(bruto)
            if obj_h is not None and ok_ref:
                ok_h, res_h = TE.executar(obj_h)
                if ok_h and servida is None:
                    # primeira que EXECUTA — decidido sem olhar a referencia
                    servida = TE.resultados_batem(res_h, res_ref)
                if ok_h and TE.resultados_batem(res_h, res_ref):
                    acertos_h += 1

        if acertos and saidas:
            passou_alguma += 1
        if acertos_h and saidas:
            passou_alguma_h += 1
        soma_taxa += acertos / max(1, len(saidas))
        soma_taxa_h += acertos_h / max(1, len(saidas))
        if acertos and args.k == 1:
            exec_ok += 1
        if acertos_h and args.k == 1:
            exec_ok_h += 1
        if servida is not None:
            servidas_n += 1
            servidas_ok += 1 if servida else 0
        por_ferramenta.setdefault(nome_ref, []).append(1 if acertos else 0)
        if args.dump:
            despejo.append({
                "i": i, "tipo": "tool", "usuario": usuario,
                "ferramenta_ref": nome_ref,
                "ferramenta_pred": (obj0 or {}).get("tool"),
                "args_ref": (ref_obj or {}).get("args") or {},
                "args_pred": (obj0 or {}).get("args") or {},
                "acertos_de_k": acertos, "k": len(saidas),
                "exec_ok": bool(acertos),
                # E5b hibrido: "executou" e' o que o harness sabe checar SEM referencia;
                # "servida_certa" e' se a 1a executavel por acaso estava certa.
                "executou": servida is not None,
                "servida_certa": bool(servida),
                "bruto": saidas[0][:1200],
            })

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
        print(linha("⭐ EXECUTOU E CUMPRIU (estrito)", exec_ok, n_tool))
        print(linha("⭐ EXECUTOU E CUMPRIU (harness)", exec_ok_h, n_tool))
        print(f"  {'   ^ diferenca = custo do terminador':34} "
              f"{exec_ok_h - exec_ok:+d} casos")
    print(linha("under-calling", under, n_tool))
    print(linha("truncado (--max-new)", trunc, n_tool))
    if terminadores:
        certo = sum(1 for t in terminadores if t is True)
        errado = sum(1 for t in terminadores if t is False)
        nunca = sum(1 for t in terminadores if t is None)
        print(linha("terminou com <|im_end|> (certo)", certo, len(terminadores)))
        print(f"  {'terminou com especial ERRADO':34} {errado}/{len(terminadores)}")
        print(f"  {'nao terminou (foi ao teto)':34} {nunca}/{len(terminadores)}")
    print("-" * 72)
    print(f"CASOS QUE NAO EXIGEM FERRAMENTA: {n_text}")
    print(linha("⚠️ over-calling (estrito)", over, n_text))
    print(linha("⚠️ over-calling (harness)", over_h, n_text))

    resultado = {
        "modelo": args.model, "peft": args.peft, "k": args.k, "temp": args.temp if amostrado else None,
        "n_tool": n_tool, "n_text": n_text, "json_ok": json_ok, "tool_right": tool_right,
        "args_exact": args_exact, "exec_ok": exec_ok if args.k == 1 else None,
        "exec_ok_harness": exec_ok_h if args.k == 1 else None,
        "under_call": under, "truncado": trunc,
        "over_call": over, "over_call_harness": over_h,
        "terminador_certo": sum(1 for t in terminadores if t is True),
        "terminador_errado": sum(1 for t in terminadores if t is False),
        "terminador_ausente": sum(1 for t in terminadores if t is None),
        "n_geracoes": len(terminadores),
    }

    if amostrado:
        p1 = soma_taxa / max(1, n_tool)
        pk = passou_alguma / max(1, n_tool)
        p1h = soma_taxa_h / max(1, n_tool)
        pkh = passou_alguma_h / max(1, n_tool)
        print("=" * 72)
        print("           regua ESTRITA        regua HARNESS (1a chamada)")
        print(f"pass@1     {p1:6.1%}                 {p1h:6.1%}")
        print(f"pass@{args.k:<2}    {pk:6.1%}                 {pkh:6.1%}")
        print(f"folga      {(pk - p1) * 100:+5.1f} pp                {(pkh - p1h) * 100:+5.1f} pp")
        print()
        print("⚠️ Sob AMOSTRAGEM o terminador do adapter escapa do conjunto de parada (cai em")
        print("   bytes de controle vizinhos), a geracao vai ao teto e a regua estrita ve'")
        print("   chamadas concatenadas. A coluna HARNESS mede a capacidade; a ESTRITA mede")
        print("   capacidade E terminacao juntas. Comparar entre modelos: sempre a MESMA coluna.")
        print()
        # ⚠️ O criterio de decisao e a folga ABSOLUTA e a fracao do espaco restante que a
        # cauda captura — nunca uma razao pk/p1. A v1 usava `pk > p1 * 1.5` e declarou
        # "sem cauda" para p1=52,3% / pk=72,9%: com p1 alto, exigir 1,5x equivale a exigir
        # 78%, quase o teto. Criterio multiplicativo pune justamente o modelo que ja e bom.
        # ⭐ O veredito de CAUDA usa a coluna HARNESS: a pergunta e' se existe solucao correta
        #    que o greedy nao acha, e a estrita confunde isso com "o adapter nao sabe parar".
        captura = (pkh - p1h) / (1 - p1h) if p1h < 1 else 0.0
        print(f"[harness] do espaco que faltava, a cauda captura {captura:5.1%}")
        print()
        print("-" * 72)
        print("E5b — POLITICA REALIZAVEL: retentar ate' a chamada EXECUTAR, servir a 1a")
        print(f"  alguma amostra executou   {servidas_n}/{n_tool} = {servidas_n/max(1,n_tool):6.1%}")
        print(f"  e a servida estava certa  {servidas_ok}/{n_tool} = {servidas_ok/max(1,n_tool):6.1%}")
        print("  ⚠️ pass@k acima usa a REFERENCIA para escolher a melhor das k — em producao")
        print("     nao ha' referencia. pass@k e' o TETO; esta linha e' a ENTREGA.")
        print()
        if (pkh - p1h) >= 0.05 and captura >= 0.15:
            print("VEREDITO: HA CAUDA. Rejection sampling / STaR e VIAVEL neste modelo —")
            print(f"          {round((pkh - p1h) * n_tool)} exemplos tem solucao correta que a geracao")
            print("          gulosa nao acha, e um verificador deterministico as reconhece.")
        else:
            print("VEREDITO: cauda insuficiente. Amostrar quase nao acrescenta ao greedy;")
            print("          rejection sampling teria pouco o que colher.")
        resultado.update({"pass_1": round(p1, 4), f"pass_{args.k}": round(pk, 4),
                          "servidas_ok": servidas_ok, "servidas_n": servidas_n,
                          "pass_1_harness": round(p1h, 4),
                          f"pass_{args.k}_harness": round(pkh, 4)})

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
        if args.dump:
            dj = saida.with_name(f"casos_{args.tag}.jsonl")
            with dj.open("w", encoding="utf-8") as fh:
                for r in despejo:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"despejo por caso em {dj} ({len(despejo)} casos)")
    elif args.dump:
        print("⚠️ --dump exige --tag (o nome do arquivo sai da tag)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
