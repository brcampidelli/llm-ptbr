"""Rejection sampling sobre o TREINO: colher as trajetorias que o modelo so acha as vezes.

⭐ POR QUE ISTO E VIAVEL AQUI (medido em 2026-08-12, docs/agentico-medicao.md):
    greedy    57,6% das tarefas cumpridas
    pass@1    52,3%
    pass@16   72,9%   -> folga de +20,6 pp, capturando 43,2% do que faltava

    Ou seja: existem trajetorias corretas que a geracao gulosa NAO acha, e um verificador
    deterministico (executar a chamada) as reconhece sem ambiguidade. E exatamente o
    ingrediente do STaR / rejection-sampling fine-tuning. A condicao nunca foi "ter 1B de
    parametros" — e "ter cauda + verificador barato".

O QUE ESTE SCRIPT FAZ:
    1. amostra k candidatas por exemplo de TREINO (nunca o holdout — isso contaminaria a
       medicao final);
    2. EXECUTA cada candidata e a referencia no mundo simulado e compara os resultados;
    3. guarda as que cumprem a tarefa, deduplicadas;
    4. escreve um dataset de REFORCO — que sera SOMADO ao original, nunca substituindo.
       O dado do professor continua sendo a referencia; o reforco so ensina o modelo a
       fazer com consistencia o que ja sabe fazer as vezes.

⚠️ RISCO CONHECIDO (model collapse): treinar so na propria saida estreita a distribuicao.
    Duas defesas aqui: (a) o filtro e EXTERNO e deterministico, nao auto-julgamento — o
    modelo nao decide o que e bom; (b) o original permanece na mistura. Ainda assim, a
    medicao obrigatoria depois do retreino e pass@k de novo: se pass@1 subir e pass@256
    cair, estreitamos a distribuicao sem ganhar capacidade (arXiv 2504.13837).

⭐ COLHEITA SIMETRICA (--incluir-text), e por que ela e necessaria (medido 2026-08-12):
    A v1 colhia so `tool_call`, porque so a chamada tem verificacao por execucao. Resultado
    do A/B: a proporcao agentica foi de 59,3% para 75,8% de tool, e o modelo aprendeu a
    chamar ferramenta com mais frequencia — over-calling 26,2% -> 33,8%. O metodo entregou
    o que prometia (pass@1 52,3% -> 57,6%, argumentos exatos +7,1 pp) e cobrou noutro eixo.

    O conserto nao e diminuir o reforco: e colher os DOIS lados. Para um exemplo `text`, a
    decisao certa e NAO chamar — e isso e verificavel: se saiu texto em vez de JSON, o
    modelo acertou a decisao.

⚠️ MAS reforcar texto gerado pelo proprio Bee e arriscado: ele escreve portugues excelente
    e INVENTA FATOS. Aceitar qualquer resposta em texto ensinaria a decisao certa com
    conteudo errado. Por isso a colheita de `text` passa por quatro guardas deterministicas
    (ver `texto_aproveitavel`): nao e JSON, tem tamanho plausivel, nao e degenerada por
    repeticao, e cobre parte do vocabulario da referencia do professor — esta ultima e a
    que impede colher uma resposta fluente sobre o assunto errado.

Uso:
    python comeia/data/15_rejection_sampling.py --model BrCamp/bee-150m-pt-sft --k 8
    python comeia/data/15_rejection_sampling.py --incluir-text     # colheita simetrica
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # comeia/
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "eval"))

from common import read_jsonl, strip_think            # noqa: E402
import tools_exec as TE                                # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

TREINO = RAIZ / "data" / "processed" / "sft_agentic.jsonl"
SAIDA = RAIZ / "data" / "processed" / "sft_agentic_reforco.jsonl"


def _palavras(s: str) -> set[str]:
    import re
    import unicodedata
    txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return {p for p in re.findall(r"[a-z0-9]+", txt) if len(p) > 3}


def texto_aproveitavel(pred: str, ref: str, cobertura_min: float = 0.25) -> tuple[bool, str]:
    """A resposta em texto do MODELO serve de reforco? (guardas deterministicas)

    Para `tool_call` o juiz e a execucao. Para `text` nao ha o que executar, e o unico
    fato verificavel e que o modelo NAO chamou ferramenta — acertou a DECISAO. So que
    aceitar qualquer texto ensinaria a decisao certa junto com conteudo inventado, que e
    a fraqueza conhecida deste modelo. Dai as guardas:
    """
    t = (pred or "").strip()
    if not t:
        return False, "vazia"
    if len(t) < 25 or len(t) > 2500:
        return False, "tamanho implausivel"

    # degeneracao por repeticao: modelo pequeno costuma travar em loop
    tokens = t.split()
    if len(tokens) >= 12 and len(set(tokens)) / len(tokens) < 0.35:
        return False, "degenerada (repeticao)"

    # ⭐ a guarda que importa: falar bem sobre o assunto ERRADO nao serve de reforco.
    # Exigimos que a resposta cubra parte do vocabulario da referencia do professor.
    pr, rf = _palavras(t), _palavras(ref)
    if rf:
        cobertura = len(pr & rf) / len(rf)
        if cobertura < cobertura_min:
            return False, f"fora do assunto (cobre {cobertura:.0%} da referencia)"
    return True, "ok"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", default=None,
                    help="adapter LoRA. 🔴 SEM ISTO O SCRIPT AMOSTRA O BASE — o default antigo "
                         "era bee-150m-pt-sft, que contem 'bee' e passa em qualquer guarda de "
                         "nome enquanto mede o modelo da geracao anterior.")
    ap.add_argument("--parar-controle", action="store_true", default=True,
                    help="parar tambem nos ids de byte C0 (E5). Ligado por padrao: sem isto a "
                         "amostragem a T=0,8 nao termina e o parser recebe lixo concatenado.")
    ap.add_argument("--pares", type=Path, default=None,
                    help="grava pares de preferencia (chosen/rejected) para o E6")
    ap.add_argument("--lote", type=int, default=24, help="sequencias por lote de geracao")
    ap.add_argument("--dados", type=Path, default=TREINO)
    ap.add_argument("--out", type=Path, default=SAIDA)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--max-new", type=int, default=320)
    ap.add_argument("--max-por-exemplo", type=int, default=2,
                    help="quantas amostras corretas guardar por exemplo (dedup antes)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--incluir-text", action="store_true",
                    help="colheita SIMETRICA: tambem reforca a decisao de NAO chamar")
    args = ap.parse_args()

    linhas = [r for r in read_jsonl(args.dados)]
    if args.limit:
        linhas = linhas[: args.limit]
    tool_rows = [r for r in linhas if r.get("kind") == "tool_call"]
    text_rows = [r for r in linhas if r.get("kind") != "tool_call"] if args.incluir_text else []

    TE.garantir_fixtures()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(dev)
    if args.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, args.peft)
    modelo.eval()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
    from paradas import (ids_de_parada, cortar_no_controle, primeiro_objeto,
                         ids_de_controle, limpar as limpar_especiais)
    PARADAS = ids_de_parada(tok, chat=True)
    if args.parar_controle:
        PARADAS = PARADAS + [i for i in ids_de_controle(tok) if i not in PARADAS]

    def ler_chamada(bruto: str):
        """Mesmo parser da regua (harness). RS e avaliacao TEM de concordar — senao o
        reforco e' colhido por um criterio e medido por outro, e a diferenca vira
        'o metodo nao funcionou'."""
        t = primeiro_objeto(cortar_no_controle(strip_think(bruto)[0]))
        if t is None:
            return None
        try:
            o = json.loads(t)
        except json.JSONDecodeError:
            return None
        return o if isinstance(o, dict) else None

    def gerar_lote(prompts: list[list[dict]], k: int) -> list[list[str]]:
        """Batelado. O caminho um-a-um deixava a GPU em 8% e projetava horas (E5)."""
        textos = [tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
                  for m in prompts]
        tok.padding_side = "left"
        fora, b, i2 = [], max(1, args.lote // max(1, k)), 0
        t0 = time.time()
        while i2 < len(textos):
            bloco = textos[i2:i2 + b]
            ent = tok(bloco, return_tensors="pt", padding=True, truncation=True,
                      max_length=1536).to(dev)
            try:
                with torch.no_grad():
                    g = modelo.generate(**ent, max_new_tokens=args.max_new, do_sample=True,
                                        temperature=args.temp, top_p=0.95,
                                        num_return_sequences=k, eos_token_id=PARADAS,
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
                fora.append([tok.decode(g[j * k + m][plen:], skip_special_tokens=False)
                             for m in range(k)])
            del g
            if dev == "cuda":
                torch.cuda.empty_cache()
            i2 += len(bloco)
            dt = (time.time() - t0) / 60
            print(f"  gerando {i2}/{len(textos)} · {dt:.1f} min · "
                  f"resta ~{dt / i2 * (len(textos) - i2):.1f} min", flush=True)
        return fora

    print(f"modelo : {args.model} · adapter {args.peft or '(nenhum)'} · {dev}")
    print(f"paradas: {len(PARADAS)} ids")
    print(f"treino : {len(tool_rows)} exemplos tool_call de {args.dados.name}")
    print(f"amostra: k={args.k} · T={args.temp}\n")

    reforco: list[dict] = []
    stats = Counter()
    por_ferramenta = Counter()

    # ── prepara: so' exemplos cuja REFERENCIA executa (o gabarito e' o juiz)
    validos = []
    for row in tool_rows:
        msgs = list(row.get("prompt") or [])
        ref = next((m["content"] for m in (row.get("completion") or [])
                    if m["role"] == "assistant"), None)
        ref_obj = _d7.extract_json(ref) if ref else None
        if not ref_obj:
            stats["ref_sem_json"] += 1
            continue
        ok_ref, res_ref = TE.executar(ref_obj)
        if not ok_ref:
            # gabarito que nao executa nao serve de juiz — descartar em silencio seria
            # o erro que ja custou caro neste projeto, entao contamos.
            stats["ref_nao_executa"] += 1
            continue
        validos.append((msgs, ref_obj, res_ref))

    print()
    print(f"[tool] {len(validos)} exemplos com referencia executavel")
    saidas_tool = gerar_lote([v[0] for v in validos], args.k) if validos else []

    pares: list[dict] = []
    for (msgs, ref_obj, res_ref), saidas in zip(validos, saidas_tool):
        # ⚠️ DOIS TIPOS DE NEGATIVO, e eles ensinam coisas diferentes:
        #   "quase" — parseou, executou, resultado errado. Distancia de edicao MINIMA
        #             (mesma chamada, um argumento trocado). E' o sinal de PRECISAO — e e'
        #             tambem o gatilho exato do likelihood displacement (arXiv:2402.13228).
        #   "lixo"  — nao parseou. Distancia de edicao MAXIMA. Ensina "emitir JSON valido".
        # A v1 descartava o segundo, porque guardava so' a forma ja' parseada e nao sobrava
        # texto para usar como `rejected`. Perdia justamente o negativo mais facil de
        # aprender. Agora os dois entram, ROTULADOS — misturar sem rotulo esconderia qual
        # deles fez efeito.
        certas, erradas, vistos = [], [], set()
        for bruto in saidas:
            obj = ler_chamada(bruto)
            if obj is None:
                cru = cortar_no_controle(strip_think(limpar_especiais(bruto))[0]).strip()
                if cru and cru not in vistos:
                    vistos.add(cru)
                    erradas.append(("lixo", cru[:1200]))
                continue
            chave = json.dumps(obj, sort_keys=True, ensure_ascii=False)
            if chave in vistos:
                continue
            vistos.add(chave)
            ok_p, res_p = TE.executar(obj)
            if ok_p and TE.resultados_batem(res_p, res_ref):
                certas.append(chave)
            else:
                erradas.append(("quase", chave))

        # ⭐ 5a — FILTRO ALL-WRONG (arXiv:2504.11343). A ablacao isola que a vantagem inteira
        #    do GRPO sobre o RAFT vem de DESCARTAR prompts cujas amostras sairam todas
        #    erradas — nao da normalizacao de recompensa, nao dos gradientes negativos.
        #    Aqui ele cai naturalmente: sem amostra certa nao ha' o que reforcar, e sem
        #    amostra errada nao ha' par de preferencia. So' o MISTO carrega sinal.
        if not certas:
            stats["all_wrong"] += 1
        elif not erradas:
            stats["all_right"] += 1
        else:
            stats["misto"] += 1

        for chave in certas[: args.max_por_exemplo]:
            reforco.append({"prompt": msgs,
                            "completion": [{"role": "assistant", "content": chave}],
                            "kind": "tool_call", "origem": "rejection_sampling"})
        if certas:
            por_ferramenta[ref_obj.get("tool")] += 1
        stats["com_acerto" if certas else "sem_acerto"] += 1

        # pares de preferencia: exige os DOIS lados no MESMO prompt
        if args.pares and certas and erradas:
            # "quase" primeiro: e' o negativo dificil, o que carrega sinal de precisao
            ordenadas = ([e for e in erradas if e[0] == "quase"]
                         + [e for e in erradas if e[0] == "lixo"])
            for n_par in range(min(args.max_por_exemplo, len(certas) * len(ordenadas))):
                c = certas[n_par % len(certas)]
                tipo, e = ordenadas[n_par % len(ordenadas)]
                pares.append({"prompt": msgs, "chosen": c, "rejected": e,
                              "tipo_negativo": tipo, "kind": "tool_call",
                              "origem": "rejection_sampling"})
                stats[f"par_{tipo}"] += 1

    # ── colheita SIMETRICA: reforcar a decisao de NAO chamar ──────────────────
    n_text_ok = 0
    motivos_rejeicao = Counter()
    if text_rows:
        prompts_t = [list(r.get("prompt") or []) for r in text_rows]
        refs_t = [next((m["content"] for m in (r.get("completion") or [])
                        if m["role"] == "assistant"), "") for r in text_rows]
        print()
        print(f"[text] {len(prompts_t)} exemplos (decisao de NAO chamar)")
        saidas_txt = gerar_lote(prompts_t, args.k)
        for msgs, ref, saidas in zip(prompts_t, refs_t, saidas_txt):
            guardadas, vistos_t = 0, set()
            for bruto in saidas:
                if guardadas >= args.max_por_exemplo:
                    break
                pred = cortar_no_controle(strip_think(limpar_especiais(bruto))[0]).strip()
                if ler_chamada(bruto) is not None:     # chamou ferramenta: errou a decisao
                    motivos_rejeicao["chamou ferramenta"] += 1
                    continue
                ok, motivo = texto_aproveitavel(pred, ref)
                if not ok:
                    motivos_rejeicao[motivo.split(" (")[0]] += 1
                    continue
                chave = pred[:200]
                if chave in vistos_t:
                    continue
                vistos_t.add(chave)
                guardadas += 1
                reforco.append({"prompt": msgs,
                                "completion": [{"role": "assistant", "content": pred}],
                                "kind": "text", "origem": "rejection_sampling"})
            if guardadas:
                n_text_ok += 1

    n_val = stats["com_acerto"] + stats["sem_acerto"]
    print("\n" + "=" * 66)
    print(f"exemplos avaliados          {n_val}")
    print(f"  com >=1 amostra correta   {stats['com_acerto']}/{n_val} = "
          f"{stats['com_acerto']/max(1,n_val):.1%}   <- pass@{args.k} no TREINO")
    print(f"  sem nenhuma               {stats['sem_acerto']}/{n_val}")
    if text_rows:
        n_tool_ref = sum(1 for r in reforco if r["kind"] == "tool_call")
        n_text_ref = len(reforco) - n_tool_ref
        print(f"\ncolheita de TEXT (decisao de nao chamar)")
        print(f"  exemplos com reforco      {n_text_ok}/{len(text_rows)} = "
              f"{n_text_ok/max(1,len(text_rows)):.1%}")
        print(f"  amostras                  {n_text_ref}")
        print(f"  rejeitadas por: {dict(motivos_rejeicao.most_common(5))}")
        prop = n_tool_ref / max(1, len(reforco))
        print(f"\n⭐ reforco: {n_tool_ref} tool / {n_text_ref} text = {prop:.1%} tool")
        print(f"   (o original e 59,3% tool — quanto mais perto, menos desloca a decisao)")
    print()
    print("⭐ 5a — FILTRO ALL-WRONG (arXiv:2504.11343): so' o MISTO carrega sinal de preferencia")
    tot5a = stats["all_wrong"] + stats["all_right"] + stats["misto"]
    for rot in ("all_wrong", "all_right", "misto"):
        v = stats[rot]
        print(f"  {rot:12} {v:5}/{tot5a} = {v/max(1,tot5a):6.1%}")
    print("  (all_wrong: o modelo nao acha a solucao nem em k tentativas — nada a reforcar")
    print("   all_right: acha sempre — nada a corrigir, e nenhum par de preferencia)")
    if args.pares:
        print()
        print("composicao dos pares (negativos diferentes ensinam coisas diferentes):")
        for t in ("quase", "lixo"):
            v = stats[f"par_{t}"]
            print(f"  {t:6} {v:5}  " + ("(distancia minima — precisao, e o gatilho do "
                                        "likelihood displacement)" if t == "quase"
                                        else "(distancia maxima — 'emita JSON valido')"))
    print(f"amostras de reforco colhidas {len(reforco)}")
    if stats["ref_nao_executa"]:
        print(f"⚠️ referencias descartadas (nao executam): {stats['ref_nao_executa']}")
    print("\ncolheita por ferramenta:")
    for t, c in por_ferramenta.most_common():
        print(f"  {t:<24} {c}")

    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in reforco) + "\n",
        encoding="utf-8")
    print(f"\n[OK] {len(reforco)} exemplos em {args.out}")
    if args.pares:
        args.pares.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in pares),
            encoding="utf-8")
        print(f"[OK] {len(pares)} pares de preferencia em {args.pares}")
    print("Proximo: misturar com o original e retreinar (NAO substituir o original).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
