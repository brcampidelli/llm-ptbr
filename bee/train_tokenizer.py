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

# Concorrentes do gate. Ambos abertos e baixáveis; são a régua externa.
RIVAIS = {
    "Qwen3.5-4B": "Qwen/Qwen3.5-4B",
    "SmolLM2-135M": "HuggingFaceTB/SmolLM2-135M",
}

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
    args = ap.parse_args()

    if not args.corpus.exists() or not list(args.corpus.glob("bee_corpus_*.jsonl.zst")):
        print(f"ERRO: nenhum shard em {args.corpus}. Rode data/20_build_corpus.py antes.",
              file=sys.stderr)
        return 1

    # ---- holdout: docs que NÃO vão para o treino do tokenizador ----
    # Vem das fontes PT e EN separadamente, para medir os dois idiomas.
    FONTES_PT = {"fineweb2-por", "portuguese-pd", "wikipedia-pt", "legal-pt"}
    FONTES_EN = {"fineweb-edu-en", "cosmopedia-en"}
    hold_pt = [t for t in ler_corpus(args.corpus, 8 * 1024 ** 2, FONTES_PT, "holdout")
               ][: args.holdout_docs]
    hold_en = [t for t in ler_corpus(args.corpus, 8 * 1024 ** 2, FONTES_EN, "holdout")
               ][: args.holdout_docs]
    print(f"holdout: {len(hold_pt)} docs PT · {len(hold_en)} docs EN  "
          f"(buckets < {HOLDOUT_PCT}, disjuntos do treino)")
    if len(hold_pt) < 50:
        print("⚠️ holdout PT pequeno demais para o gate ser confiável. Colete mais corpus.",
              file=sys.stderr)
        return 1

    if not args.so_gate:
        from tokenizers import Tokenizer, decoders, pre_tokenizers, processors, trainers
        from tokenizers.models import BPE

        print(f"\ntreinando BPE ByteLevel · vocab {args.vocab} · até "
              f"{args.train_bytes/1024**3:.1f} GB de texto")
        tok = Tokenizer(BPE(unk_token=None))     # ByteLevel nunca produz <unk>
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

    print("\n" + "=" * 72)
    print("⭐ GATE 1 — FERTILIDADE (tokens por palavra · MENOR é melhor)")
    print("=" * 72)
    print(f"{'tokenizador':<16} {'vocab':>7} {'PT':>9} {'EN':>9}   leitura")
    print("-" * 72)
    tab = {}
    for nome, tk in resultados.items():
        f_pt, _, _ = fertilidade(tk, hold_pt)
        f_en, _, _ = fertilidade(tk, hold_en) if hold_en else (float("nan"), 0, 0)
        tab[nome] = (f_pt, f_en)
        print(f"{nome:<16} {tk.vocab_size:>7} {f_pt:>9.3f} {f_en:>9.3f}")
    print("-" * 72)

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

    # o inglês não pode ser destruído — 25% do corpus é EN
    nosso_en, rival_en = tab["Bee (nosso)"][1], tab[melhor_rival][1]
    if nosso_en > rival_en * 1.25:
        print(f"\n⚠️ ATENÇÃO: em inglês somos {nosso_en/rival_en-1:+.0%} PIORES que o rival.")
        print("   25% do corpus é EN — perder tanto assim encarece um quarto do treino.")

    (args.out / "gate_fertilidade.json").write_text(
        json.dumps({"fertilidade": {k: {"pt": v[0], "en": v[1]} for k, v in tab.items()},
                    "ganho_pt_vs_melhor_rival": ganho, "melhor_rival": melhor_rival},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if ganho > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
