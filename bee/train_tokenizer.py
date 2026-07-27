"""BEE — treina o tokenizador nosso e roda o PRIMEIRO GATE do projeto.

⭐ POR QUE UM TOKENIZADOR NOSSO, e não um emprestado. O do Qwen é otimizado para
chinês; o do SmolLM2 para inglês. Ambos gastam **mais tokens por palavra em
português** do que o necessário. Menos tokens/palavra significa, ao mesmo tempo:
  • mais texto útil dentro da mesma janela de contexto;
  • inferência mais barata (menos tokens para gerar a mesma resposta);
  • mais informação por passo de treino, com o mesmo orçamento de FLOPs.
É a primeira coisa genuinamente nossa e a mais barata de acertar.

⭐ E É O GATE MAIS BARATO DO PROJETO. A aposta inteira do Bee é o nicho
português. Se o nosso tokenizador NÃO for mais eficiente em português que o do
Qwen e o do SmolLM2, a aposta já falhou — e é muito melhor descobrir isso em
~10 minutos de CPU do que depois de 22 horas de GPU.

A métrica é **fertilidade**: tokens por palavra num holdout de português. Menor é
melhor. Reportamos também o holdout em inglês, porque um tokenizador que só
melhora PT à custa de destruir EN não serve — o corpus tem 25% de inglês.

Uso:
    python tokenizer/train_bee_tokenizer.py --corpus data/corpus --vocab 32000
    python tokenizer/train_bee_tokenizer.py --só-gate      # já treinado: só compara
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "bee" / "tokenizer"

# ChatML desde o início: o SFT com TRL depois funciona sem adaptação de template.
ESPECIAIS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<|pad|>"]

# Concorrentes do gate — a régua externa. Todos abertos e baixáveis.
# ⭐ `tiktoken` (GPT-4o) entrou depois do estudo de 2026-07-27: é a MESMA família do nosso
# algoritmo (ByteLevel BPE), então é o baseline mais honesto que existe para nós. Bater
# um tokenizador de outra família seria fácil e pouco informativo.
RIVAIS = {
    "Qwen3.5-4B": "Qwen/Qwen3.5-4B",
    "SmolLM2-135M": "HuggingFaceTB/SmolLM2-135M",
}
RIVAL_TIKTOKEN = "o200k_base"      # GPT-4o; carregado à parte, API diferente

_PALAVRA = re.compile(r"\w+", re.UNICODE)


def conta_palavras(texto: str) -> int:
    return len(_PALAVRA.findall(texto))


HOLDOUT_PCT = 2          # 2% dos documentos ficam FORA do treino do tokenizador


def bucket(texto: str) -> int:
    """Balde estável 0-99 do documento. Mesma técnica de data/13: `sha1`, não shuffle.

    ⭐ POR QUE HASH E NÃO "os primeiros N docs": o holdout precisa ser o MESMO
    conjunto nas duas leituras (treino e avaliação) e precisa ser DISJUNTO do
    treino. Com fatia por posição, o holdout cai dentro do treino — o Bee veria o
    texto de teste e os rivais não, o que inflaria o nosso resultado no gate.
    """
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8], 16) % 100


def ler_corpus(pasta: Path, max_bytes: int, so_fontes: set[str] | None = None,
               parte: str = "treino"):
    """Gera textos dos shards `.jsonl.zst`, com teto de bytes.

    `parte`: "treino" (bucket >= HOLDOUT_PCT) · "holdout" (bucket < HOLDOUT_PCT) ·
    "tudo". Treino e holdout são disjuntos por construção.

    ⚠️ Amostra BALANCEADA, não a web crua: treinar o tokenizador só em web enche o
    vocab de lixo de HTML e de fragmentos de URL, que depois custam tokens em todo
    documento limpo.
    """
    import zstandard as zstd
    lidos = 0
    for shard in sorted(pasta.glob("bee_corpus_*.jsonl.zst")):
        with open(shard, "rb") as fh:
            dados = zstd.ZstdDecompressor().decompress(fh.read())
        for linha in dados.decode("utf-8").splitlines():
            if not linha.strip():
                continue
            try:
                reg = json.loads(linha)
            except Exception:
                continue
            if so_fontes and reg.get("fonte") not in so_fontes:
                continue
            texto = reg.get("text", "")
            if parte != "tudo":
                no_hold = bucket(texto) < HOLDOUT_PCT
                if (parte == "holdout") != no_hold:
                    continue
            lidos += len(texto.encode("utf-8"))
            yield texto
            if lidos >= max_bytes:
                return


def fertilidade(tok, textos: list[str]) -> tuple[float, int, int]:
    """(tokens/palavra, tokens, palavras). Menor é melhor."""
    n_tok = n_pal = 0
    for t in textos:
        n_tok += len(tok.encode(t).ids) if hasattr(tok, "encode") and not hasattr(tok, "tokenize") \
            else len(tok(t)["input_ids"])
        n_pal += conta_palavras(t)
    return (n_tok / max(1, n_pal)), n_tok, n_pal


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "bee" / "corpus")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--vocab", type=int, default=32000,
                    help="32k é o trade-off escolhido: vocab maior corta tokens/palavra "
                         "mas engorda o embedding — 32k × 576 = 18,4M params, ~12%% de um "
                         "modelo de 150M")   # %% porque o argparse faz %-formatting no help
    ap.add_argument("--train-bytes", type=int, default=2 * 1024 ** 3)
    ap.add_argument("--holdout-docs", type=int, default=400)
    ap.add_argument("--so-gate", "--só-gate", dest="so_gate", action="store_true",
                    help="não treina; só roda o gate contra os rivais")
    ap.add_argument("--normalizar", choices=["nenhum", "nfc", "nfkc"], default="nfc",
                    help="NFC unifica acento precomposto/decomposto (o problema do PT) sem "
                         "perder informacao. NFKC tambem converte ①→1 e ﬁ→fi, o que NAO e "
                         "reversivel. 'nenhum' e o que o tiktoken/GPT-2 fazem.")
    ap.add_argument("--varrer-vocab", type=str, default="",
                    help="treina varios vocabs e compara (ex: 32000,48000,64000). Cada um "
                         "custa ~4 min de CPU; o trade-off e fertilidade x tamanho do embedding")
    args = ap.parse_args()

    if not args.corpus.exists() or not list(args.corpus.glob("bee_corpus_*.jsonl.zst")):
        print(f"ERRO: nenhum shard em {args.corpus}. Rode data/20_build_corpus.py antes.",
              file=sys.stderr)
        return 1

    # ---- holdout: docs que NÃO vão para o treino do tokenizador ----
    # ⭐ TRÊS domínios, não dois. A v1 media só PT e EN — mas o corpus v1 tinha 0% de
    # código, então não havia o que medir. Agora que 10% é código, medir só PT/EN
    # esconderia exatamente a regressão que este retreino existe para evitar: um
    # tokenizador que melhora em prosa e piora em `def`/`};`/indentação.
    FONTES_PT = {"fineweb2-por", "portuguese-pd", "wikipedia-pt", "legal-pt"}
    FONTES_EN = {"fineweb-edu-en", "cosmopedia-en"}
    FONTES_CODE = {"code-stack", "code-mit", "code-apache"}
    hold_pt = [t for t in ler_corpus(args.corpus, 8 * 1024 ** 2, FONTES_PT, "holdout")
               ][: args.holdout_docs]
    hold_en = [t for t in ler_corpus(args.corpus, 8 * 1024 ** 2, FONTES_EN, "holdout")
               ][: args.holdout_docs]
    hold_code = [t for t in ler_corpus(args.corpus, 8 * 1024 ** 2, FONTES_CODE, "holdout")
                 ][: args.holdout_docs]
    print(f"holdout: {len(hold_pt)} docs PT · {len(hold_en)} EN · {len(hold_code)} código  "
          f"(buckets < {HOLDOUT_PCT}, disjuntos do treino)")
    if len(hold_pt) < 50:
        print("⚠️ holdout PT pequeno demais para o gate ser confiável. Colete mais corpus.",
              file=sys.stderr)
        return 1
    if len(hold_code) < 20:
        print(f"⚠️ holdout de código com {len(hold_code)} docs — a coluna CODE do gate "
              f"não é confiável. O corpus tem fonte de código?", file=sys.stderr)

    if not args.so_gate:
        from tokenizers import Tokenizer, decoders, normalizers, pre_tokenizers, processors, trainers
        from tokenizers.models import BPE

        print(f"\ntreinando BPE ByteLevel · vocab {args.vocab} · normalizer "
              f"{args.normalizar} · até {args.train_bytes/1024**3:.1f} GB de texto")
        tok = Tokenizer(BPE(unk_token=None))     # ByteLevel nunca produz <unk>
        # ⭐ NORMALIZER — o gap do v1, que não tinha nenhum (achado no estudo de 2026-07-27).
        # Em PORTUGUÊS isto não é detalhe: "ã" pode vir como U+00E3 (precomposto/NFC) ou como
        # "a"+U+0303 (combinando/NFD). São BYTES diferentes, e num BPE ByteLevel viram TOKENS
        # diferentes — o vocabulário gasta entradas com o mesmo caractere. Nosso corpus mistura
        # web, Wikipédia e livros digitalizados, que chegam nas duas formas.
        #
        # ⚠️ NFC e não NFKC de propósito. NFKC é *compatibilidade*: converte ①→1, ﬁ→fi, ½→1⁄2.
        # Isso NÃO é reversível, e reversibilidade é justamente a propriedade que o paper do
        # SentencePiece defende e que o tiktoken/GPT-2 preserva não normalizando nada.
        # NFC unifica as formas de acento (o problema real do PT) sem destruir informação.
        # As três opções ficam mensuráveis em vez de escolhidas por dogma.
        if args.normalizar == "nfc":
            tok.normalizer = normalizers.NFC()
        elif args.normalizar == "nfkc":
            tok.normalizer = normalizers.NFKC()
        tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tok.decoder = decoders.ByteLevel()
        tok.post_processor = processors.ByteLevel(trim_offsets=False)
        treinador = trainers.BpeTrainer(
            vocab_size=args.vocab, special_tokens=ESPECIAIS,
            min_frequency=2, show_progress=True,
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
        tok.train_from_iterator(ler_corpus(args.corpus, args.train_bytes, None, "treino"),
                                trainer=treinador)

        args.out.mkdir(parents=True, exist_ok=True)
        tok.save(str(args.out / "tokenizer.json"))
        # Embrulha em PreTrainedTokenizerFast para o resto do stack (TRL, vLLM) usar
        from transformers import PreTrainedTokenizerFast
        fast = PreTrainedTokenizerFast(
            tokenizer_file=str(args.out / "tokenizer.json"),
            eos_token="<|endoftext|>", bos_token="<|endoftext|>",
            unk_token=None, pad_token="<|pad|>",
            additional_special_tokens=["<|im_start|>", "<|im_end|>"])
        fast.chat_template = (
            "{% for m in messages %}{{'<|im_start|>' + m['role'] + '\n' + m['content'] + "
            "'<|im_end|>\n'}}{% endfor %}"
            "{% if add_generation_prompt %}{{'<|im_start|>assistant\n'}}{% endif %}")
        fast.save_pretrained(str(args.out))
        print(f"✅ tokenizador salvo em {args.out}  (vocab real: {fast.vocab_size})")

    # ------------------------- ⭐ O GATE -------------------------
    from transformers import AutoTokenizer
    nosso = AutoTokenizer.from_pretrained(str(args.out))
    resultados = {"Bee (nosso)": nosso}
    for nome, repo in RIVAIS.items():
        try:
            resultados[nome] = AutoTokenizer.from_pretrained(repo)
        except Exception as e:
            print(f"⚠️ não consegui baixar {nome} ({type(e).__name__}) — o gate fica "
                  f"incompleto e NÃO deve ser lido como aprovado.", file=sys.stderr)
    # ⭐ tiktoken entra à parte: API diferente (`.encode`, sem `vocab_size`), e é a MESMA
    # família do nosso algoritmo (ByteLevel BPE). É o baseline mais duro que temos — bater
    # tokenizador de outra família seria fácil e diria pouco.
    try:
        import tiktoken
        enc = tiktoken.get_encoding(RIVAL_TIKTOKEN)

        class _TikWrap:
            vocab_size = enc.n_vocab
            def __call__(self, t):     # a `fertilidade()` aceita este formato
                return {"input_ids": enc.encode(t, disallowed_special=())}
        resultados[f"tiktoken {RIVAL_TIKTOKEN}"] = _TikWrap()
    except Exception as e:
        print(f"(tiktoken indisponível: {type(e).__name__} — gate segue sem ele)",
              file=sys.stderr)

    print("\n" + "=" * 78)
    print("⭐ GATE 1 — FERTILIDADE (tokens por palavra · MENOR é melhor)")
    print("=" * 78)
    print(f"{'tokenizador':<22} {'vocab':>7} {'PT':>9} {'EN':>9} {'CODE':>9}")
    print("-" * 78)
    tab = {}
    for nome, tk in resultados.items():
        f_pt, _, _ = fertilidade(tk, hold_pt)
        f_en, _, _ = fertilidade(tk, hold_en) if hold_en else (float("nan"), 0, 0)
        f_cd, _, _ = fertilidade(tk, hold_code) if hold_code else (float("nan"), 0, 0)
        tab[nome] = (f_pt, f_en, f_cd)
        print(f"{nome:<22} {tk.vocab_size:>7} {f_pt:>9.3f} {f_en:>9.3f} {f_cd:>9.3f}")
    print("-" * 78)

    nosso_pt = tab["Bee (nosso)"][0]
    rivais_pt = {k: v[0] for k, v in tab.items() if k != "Bee (nosso)"}
    if not rivais_pt:
        print("⚠️ sem rival baixado: GATE INCONCLUSIVO.")
        return 1
    melhor_rival, melhor_val = min(rivais_pt.items(), key=lambda kv: kv[1])
    ganho = (melhor_val - nosso_pt) / melhor_val

    print(f"\nmelhor rival em PT: {melhor_rival} ({melhor_val:.3f})")
    print(f"Bee: {nosso_pt:.3f}  →  {ganho:+.1%} de tokens por palavra em português")
    if ganho > 0.05:
        print("\n✅ GATE APROVADO. O tokenizador nosso é mais eficiente em português por")
        print("   margem folgada. A aposta do nicho tem base — seguir para a arquitetura.")
    elif ganho > 0:
        print("\n⚠️ GATE MARGINAL. Ganho existe mas é pequeno (<5%). Vale tentar vocab maior")
        print("   (48k) ou mais dado de treino do tokenizador antes de gastar GPU.")
    else:
        print("\n🔴 GATE REPROVADO. Nosso tokenizador NÃO é melhor em português que o rival.")
        print("   A aposta do nicho falhou na etapa mais barata. NÃO seguir para o treino:")
        print("   revisar corpus (PT de fato dominante?) e vocab antes de qualquer GPU.")

    # ⭐ Os outros domínios não podem ser destruídos — 25% do corpus é EN e 10% é código.
    # Vigiar só o PT deixaria passar o pior desfecho possível deste retreino: ganhar em
    # português à custa de ficar péssimo em código, que é exatamente o que muda no corpus.
    for i, (rotulo, fatia) in enumerate([("inglês", 0.25), ("código", 0.10)], start=1):
        nosso_x, rival_x = tab["Bee (nosso)"][i], tab[melhor_rival][i]
        if rival_x and rival_x == rival_x and nosso_x > rival_x * 1.25:   # != NaN
            print(f"\n⚠️ ATENÇÃO: em {rotulo} somos {nosso_x/rival_x-1:+.0%} PIORES que o "
                  f"{melhor_rival}. {fatia:.0%} do corpus é {rotulo} — perder tanto assim "
                  f"encarece essa fatia inteira do treino.")

    (args.out / "gate_fertilidade.json").write_text(
        json.dumps({"fertilidade": {k: {"pt": v[0], "en": v[1], "code": v[2]}
                                    for k, v in tab.items()},
                    "ganho_pt_vs_melhor_rival": ganho, "melhor_rival": melhor_rival,
                    "vocab": args.vocab, "normalizer": args.normalizar,
                    "holdout": {"pt": len(hold_pt), "en": len(hold_en),
                                "code": len(hold_code)}},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if ganho > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
