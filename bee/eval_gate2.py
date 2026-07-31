"""GATE 2 — Bee-150M (PT, do zero) vs SmolLM2-135M (EN) em holdout PT.

A pergunta que decide a aposta do projeto: **um 150M treinado em português bate um
135M treinado em inglês, NO português?** Se sim, o nicho valeu. Se não, o diagnóstico
(falta token / dado / arquitetura) informa o próximo degrau.

────────────────────────────────────────────────────────────────────────────────
⭐ POR QUE bits-por-byte (bpb) E NÃO perplexidade
Perplexidade só é comparável sob o MESMO tokenizador. O Bee tem vocab 32k próprio; o
SmolLM2 tem 49k. "Perplexidade 72 vs 60" entre tokenizadores diferentes não significa
nada — cada um fatia o texto em números diferentes de tokens. bpb normaliza pela
representação em BYTES: a mesma string tem os mesmos bytes para os dois modelos, então
bpb mede **compressão real do texto**, independente de como cada um o corta. É a métrica
canônica para comparar LMs de tokenizadores distintos (The Pile, GPT-3 paper, etc).

⭐ POR QUE bpb E NÃO múltipla escolha
Um modelo BASE de 150M sem SFT não "responde" — só completa texto. Múltipla escolha a
150M fica perto do acaso E já nos enganou uma vez (a chat_ptbr passou por 7 benchmarks
com defeito grosseiro invisível). bpb mede o que o modelo base REALMENTE faz: modelar a
distribuição do português. É a régua honesta para esta comparação.

⭐ DECOMPOSTO POR FONTE + TRADE-OFF EN (lições dos estudos)
Não reporta só o agregado — a média esconde regressão por fonte. E mede EN também, para
expor o trade-off: o Bee DEVE ganhar em PT (o nicho) e PERDER em EN (o preço consciente
de concentrar 32k de vocab em português). Ganhar em PT e perder em EN É a aposta se
confirmando, não um defeito.

⭐ CONTAMINAÇÃO VERIFICADA
O holdout são os shards {7,23,41} do corpus — os MESMOS que `prepare_data.py` excluiu do
treino do Bee (SHARDS_VAL). O Bee nunca viu este texto. O SmolLM2 foi treinado em corpus
inglês próprio; este PT específico também é novo para ele. Páreo limpo dos dois lados.
────────────────────────────────────────────────────────────────────────────────

Uso (Colab, com o modelo e o corpus na Drive):
    python bee/eval_gate2.py \
        --corpus /content/drive/MyDrive/BEE/corpus \
        --bee    /content/drive/MyDrive/BEE/bee-150m/modelo \
        --rival  HuggingFaceTB/SmolLM2-135M \
        --n-docs 400 --max-chars 4000
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Os MESMOS shards que prepare_data.py segura fora do treino (SHARDS_VAL).
SHARDS_VAL = {7, 23, 41}
FONTES_PT = ("fineweb2-por", "portuguese-pd", "wikipedia-pt", "legal-pt")
FONTES_EN = ("fineweb-edu-en", "cosmopedia-en")


def carregar_holdout(corpus_dir, max_chars, n_por_fonte):
    """Lê os shards de validação e devolve {fonte: [textos crus]}.

    ⭐ Texto CRU (não tokenizado): cada modelo vai tokenizar com o SEU tokenizador.
    Trunca cada doc em `max_chars` para caber em 2048 tokens nos DOIS tokenizadores
    (o do SmolLM2 é ~1,6× mais 'gordo' em PT, então o limite é ditado por ele).
    """
    import zstandard as zstd

    shards = sorted(corpus_dir.glob("bee_corpus_*.jsonl.zst"))
    if not shards:
        print(f"ERRO: nenhum shard em {corpus_dir}", file=sys.stderr)
        return None
    dctx = zstd.ZstdDecompressor()
    por_fonte: dict[str, list[str]] = {}
    for i, shard in enumerate(shards):
        if i not in SHARDS_VAL:
            continue
        dados = dctx.decompress(shard.read_bytes()).decode("utf-8")
        for linha in dados.splitlines():
            if not linha.strip():
                continue
            try:
                reg = json.loads(linha)
            except Exception:
                continue
            fonte, texto = reg.get("fonte", "?"), reg.get("text", "")
            if not texto or len(texto) < 200:  # descarta fragmentos curtos demais p/ medir
                continue
            bucket = por_fonte.setdefault(fonte, [])
            if len(bucket) < n_por_fonte:
                bucket.append(texto[:max_chars])
    return por_fonte


def bits_por_byte(modelo_id, textos_por_fonte, seq_len, device):
    """Para um modelo, devolve {fonte: (bits, bytes)} — acumulados, não médias.

    bpb do documento = NLL_total_em_nats / ln(2) / n_bytes_utf8. Somamos bits e bytes
    por fonte e dividimos no fim (média ponderada por documento, o certo).
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(modelo_id)
    modelo = AutoModelForCausalLM.from_pretrained(
        modelo_id, torch_dtype=torch.bfloat16).to(device).eval()

    LN2 = math.log(2.0)
    out: dict[str, list[float]] = {}
    ferts: list[float] = []  # tokens/byte, p/ reportar a 'gordura' do tokenizador
    with torch.no_grad():
        for fonte, textos in textos_por_fonte.items():
            bits_acc = 0.0
            bytes_acc = 0
            for texto in textos:
                nb = len(texto.encode("utf-8"))
                if nb == 0:
                    continue
                ids = tok(texto, add_special_tokens=False,
                          return_tensors="pt")["input_ids"][:, :seq_len].to(device)
                if ids.shape[1] < 2:
                    continue
                logits = modelo(ids).logits
                # NLL total (soma, não média) de prever tok[1:] dado tok[:-1].
                nll = torch.nn.functional.cross_entropy(
                    logits[0, :-1].float(), ids[0, 1:], reduction="sum").item()
                bits_acc += nll / LN2
                bytes_acc += nb
                ferts.append(ids.shape[1] / nb)
            if bytes_acc:
                out[fonte] = [bits_acc, bytes_acc]
    fert = sum(ferts) / max(1, len(ferts))
    del modelo
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return out, fert


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "bee" / "corpus")
    ap.add_argument("--bee", type=str, default=str(ROOT / "bee" / "bee-150m" / "modelo"))
    ap.add_argument("--rival", type=str, default="HuggingFaceTB/SmolLM2-135M")
    ap.add_argument("--n-docs", type=int, default=400, help="docs por fonte")
    ap.add_argument("--max-chars", type=int, default=4000)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "gate-2-resultado.json")
    args = ap.parse_args()

    import torch
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 76)
    print("⭐ GATE 2 — Bee-150M (PT) vs SmolLM2-135M (EN), em holdout PT (+ trade-off EN)")
    print("=" * 76)
    print(f"  métrica    : bits-por-byte (bpb) — MENOR é melhor · comparável entre tokenizadores")
    print(f"  holdout    : shards {sorted(SHARDS_VAL)} (excluídos do treino do Bee — sem contaminação)")
    print(f"  dispositivo: {dev}\n")

    holdout = carregar_holdout(args.corpus, args.max_chars, args.n_docs)
    if not holdout:
        return 1
    for fonte in sorted(holdout):
        nb = sum(len(t.encode("utf-8")) for t in holdout[fonte])
        print(f"    {fonte:<16} {len(holdout[fonte]):>4} docs · {nb/1e6:.2f} MB")
    print()

    print("  medindo Bee-150M…", flush=True)
    bee, fert_bee = bits_por_byte(args.bee, holdout, args.seq_len, dev)
    print("  medindo SmolLM2-135M…", flush=True)
    rival, fert_rival = bits_por_byte(args.rival, holdout, args.seq_len, dev)

    # ---------------- relatório ----------------
    print("\n" + "=" * 76)
    print("RESULTADO — bits por byte (menor = melhor)")
    print("=" * 76)
    print(f"  {'fonte':<16} {'idioma':<7} {'Bee':>8} {'SmolLM2':>9} {'Δ':>8}  vencedor")
    print("  " + "-" * 62)

    def bpb(d, f):
        return d[f][0] / d[f][1] if f in d and d[f][1] else float("nan")

    agg_bee = {"pt": [0.0, 0], "en": [0.0, 0]}
    agg_riv = {"pt": [0.0, 0], "en": [0.0, 0]}
    for fonte in sorted(set(bee) | set(rival)):
        lang = "pt" if fonte in FONTES_PT else ("en" if fonte in FONTES_EN else "code")
        b, r = bpb(bee, fonte), bpb(rival, fonte)
        venc = "Bee" if b < r else "SmolLM2"
        print(f"  {fonte:<16} {lang:<7} {b:>8.3f} {r:>9.3f} {r-b:>+8.3f}  {venc}"
              + (" ⭐" if venc == "Bee" else ""))
        if lang in ("pt", "en"):
            if fonte in bee:
                agg_bee[lang][0] += bee[fonte][0]; agg_bee[lang][1] += bee[fonte][1]
            if fonte in rival:
                agg_riv[lang][0] += rival[fonte][0]; agg_riv[lang][1] += rival[fonte][1]

    print("  " + "-" * 62)
    resumo = {}
    for lang in ("pt", "en"):
        if agg_bee[lang][1] and agg_riv[lang][1]:
            b = agg_bee[lang][0] / agg_bee[lang][1]
            r = agg_riv[lang][0] / agg_riv[lang][1]
            venc = "Bee" if b < r else "SmolLM2"
            pct = 100 * (r - b) / r
            print(f"  {'AGREGADO '+lang.upper():<16} {'':<7} {b:>8.3f} {r:>9.3f} {r-b:>+8.3f}  "
                  f"{venc}  ({pct:+.1f}%)")
            resumo[lang] = {"bee": b, "rival": r, "vencedor": venc, "delta_pct": pct}

    print(f"\n  fertilidade (tokens/byte, menor = tokenizador mais eficiente):")
    print(f"    Bee {fert_bee:.4f}  ·  SmolLM2 {fert_rival:.4f}")

    # ---------------- veredito ----------------
    print("\n" + "=" * 76)
    pt = resumo.get("pt")
    if pt and pt["vencedor"] == "Bee":
        print(f"✅ A APOSTA VALEU: em PORTUGUÊS o Bee-150M vence o SmolLM2-135M por "
              f"{pt['delta_pct']:+.1f}% de bpb.")
        print("   Um 150M treinado em PT modela o português melhor que um 135M treinado em EN.")
    elif pt:
        print(f"🔴 A APOSTA NÃO SE CONFIRMOU EM bpb: o SmolLM2 fez {-pt['delta_pct']:.1f}% melhor em PT.")
        print("   Diagnóstico provável: falta de tokens (subtreino) — 3,74B é pouco. Ou dado, ou arquitetura.")
    en = resumo.get("en")
    if en:
        lado = "como esperado (trade-off consciente)" if en["vencedor"] == "SmolLM2" else "surpreendentemente"
        print(f"   Em INGLÊS: {en['vencedor']} vence ({en['delta_pct']:+.1f}% p/ o Bee) — {lado}.")
    print("=" * 76)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "metrica": "bits_por_byte", "shards_val": sorted(SHARDS_VAL),
        "bee_por_fonte": {k: (v[0] / v[1]) for k, v in bee.items()},
        "rival_por_fonte": {k: (v[0] / v[1]) for k, v in rival.items()},
        "agregado": resumo, "fertilidade": {"bee": fert_bee, "rival": fert_rival},
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ salvo em {args.out}")
    print("\n⚠️ RESSALVA: bpb mede modelagem de linguagem do modelo BASE. Fluência de RESPOSTA")
    print("   (e consistência sob paráfrase) só se avalia após o SFT — é o gate da próxima fase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
