"""Gate T1 do Bee-1G — varredura de tamanho de vocabulario sobre os 8 idiomas-alvo.

⭐ O QUE ESTE GATE DECIDE, E POR QUE E' O PRIMEIRO
  O censo exato do vocabulario atual achou **arabe 0 · han 0 · kana 0** tokens em 32.000, e a
  medicao de fertilidade confirmou no comportamento: `tok/byte` = 0,978 (arb) e 0,954 (cmn), ou
  seja **um token por byte** — fallback puro. Entao o gate nao decide SE expande; decide COMO.

  E decide cedo porque **vocab e' orcamento de parametro**: com d_model 2048, um vocab de 128k
  poe 262M so' no embedding de entrada — mais de um quarto de um modelo de 1B. Nao da' para fixar
  profundidade x largura (Gate T0) sem este numero.

⚠️ TRES EIXOS DE CRITERIO, DECLARADOS ANTES — E ESTE SCRIPT COBRE DOIS
  1. **custo** (aqui) — fertilidade em PT nao pode piorar mais que 15% (0,218 -> 0,251 tok/byte),
     e nenhum idioma acima de 3,0 tok/palavra;
  3. **incompletude** (aqui) — fracao de tokens **indecodificaveis sozinhos** por escrita. BPE
     byte-level aprende merges que atravessam fronteira de caractere UTF-8; `2410.23684` mediu
     -90% de alucinacao no Llama-3.1 so' trocando a tokenizacao da MESMA frase.
     ⚠️ NAO e' redundante com fertilidade: no extremo as duas disparam juntas, mas na faixa
     intermediaria — onde um vocab multilingue de 128k vai cair — da' para ter fertilidade
     aceitavel E fracao grande de merges atravessando fronteira.
  2. 🔴 **qualidade** (NAO COBERTO AQUI) — bpb por idioma, mesmo orcamento de passos em todos os
     bracos. Exige GPU. `2607.24276` e `2310.08754` mediram que **fertilidade nao e' preditiva de
     qualidade**, entao este gate NAO pode ser lido como aprovacao final. O artefato marca o eixo
     2 como `nao_medido` de proposito (§2z: celula nao medida nunca deve ler como medida).

⚠️ REPORTAR POR IDIOMA, NUNCA A MEDIA (§2y)
  Media entre 8 idiomas e' agregado de componentes heterogeneos: latim e CJK respondem em
  direcoes opostas a cada merge gasto, e a media esconde exatamente o trade-off que o gate mede.

⚠️ A REGUA E' tokens/CARACTERE, nao tokens/palavra (§2g)
  `\\w+` nao segmenta han nem kana. Ver `bee/fertilidade_multilingue.py`.

Uso:
    python bee/gate_t1_vocab.py --vocabs 32000,64000,96000,128000
    python bee/gate_t1_vocab.py --vocabs 64000 --pular-expansao      # rapido
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

ESPECIAIS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<|pad|>"]
ORDEM = ["por", "spa", "fra", "deu", "eng", "arb", "cmn", "jpn"]
NAO_LATINO = ["arb", "cmn", "jpn"]

# ancoras publicadas — §2aa: sem reproduzir numero conhecido nao ha' comparacao a fazer
ANCORAS = {"por": 0.218, "eng": 0.3128}

# criterio do eixo 1, declarado ANTES de medir
TETO_PIORA_PT = 0.15          # PT nao pode piorar mais que 15% em tok/byte
BASE_PT = 0.218
TETO_TOK_PALAVRA = 3.0        # teto europeu medido em 2605.24718

D_MODEL_REF = 2048            # referencia do Bee-1G para custo de embedding
ALVO_PARAMS = 1_000_000_000


# ------------------------------------------------------------------ corpus
def textos(corpus: Path, cod: str, limite_bytes: int, parte: str):
    """Gera textos de um idioma. `parte`: 'treino' | 'holdout' | 'tudo'.

    Holdout por hash sha1 do texto (mesma tecnica do train_tokenizer.py): o conjunto e' o
    MESMO nas duas leituras e disjunto do treino. Fatia por posicao poria o holdout dentro
    do treino, e o gate se auto-aprovaria.
    """
    import hashlib
    import zstandard as zstd
    lidos = 0
    for shard in sorted(glob.glob(str(corpus / f"bee_corpus_{cod}_*.jsonl.zst"))):
        bruto = zstd.ZstdDecompressor().decompress(open(shard, "rb").read()).decode("utf-8")
        for linha in bruto.splitlines():
            if not linha.strip():
                continue
            try:
                t = json.loads(linha)["text"]
            except Exception:
                continue
            if parte != "tudo":
                no_hold = int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16) % 100 < 2
                if (parte == "holdout") != no_hold:
                    continue
            lidos += len(t.encode("utf-8"))
            yield t
            if lidos >= limite_bytes:
                return


def mistura(corpus: Path, bytes_por_idioma: int):
    """Itera os 8 idiomas intercalando — o BPE ve' todos, nao um depois do outro."""
    gers = {c: textos(corpus, c, bytes_por_idioma, "treino") for c in ORDEM}
    vivos = dict(gers)
    while vivos:
        for c in list(vivos):
            try:
                yield next(vivos[c])
            except StopIteration:
                del vivos[c]


# ------------------------------------------------------------------ metricas
def treina(vocab: int, corpus: Path, bytes_por_idioma: int, saida: Path):
    from tokenizers import Tokenizer, decoders, normalizers, pre_tokenizers, processors, trainers
    from tokenizers.models import BPE
    tok = Tokenizer(BPE(unk_token=None))
    tok.normalizer = normalizers.NFC()                       # mesma escolha do 32k atual
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    tok.post_processor = processors.ByteLevel(trim_offsets=False)
    tr = trainers.BpeTrainer(vocab_size=vocab, special_tokens=ESPECIAIS, min_frequency=2,
                             show_progress=False,
                             initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator(mistura(corpus, bytes_por_idioma), trainer=tr)
    saida.mkdir(parents=True, exist_ok=True)
    tok.save(str(saida / "tokenizer.json"))
    from transformers import PreTrainedTokenizerFast
    fast = PreTrainedTokenizerFast(
        tokenizer_file=str(saida / "tokenizer.json"), eos_token="<|endoftext|>",
        bos_token="<|endoftext|>", unk_token=None, pad_token="<|pad|>",
        additional_special_tokens=["<|im_start|>", "<|im_end|>"])
    fast.save_pretrained(str(saida))
    return fast


FAIXAS_ALVO = [(0x0600, 0x06FF), (0x0750, 0x077F),      # arabe
               (0x4E00, 0x9FFF), (0x3400, 0x4DBF),      # han
               (0x3040, 0x309F), (0x30A0, 0x30FF)]      # kana


def _e_alvo(txt: str) -> bool:
    """Todo caractere util do token esta' numa das escritas que o 32k nao cobre?

    Exigente de proposito: token MISTO (latim + han) tambem passaria por cima de merge
    latino do 32k. A expansao so' pode acrescentar o que nao existe.
    """
    uteis = [c for c in txt if not c.isspace()]
    if not uteis:
        return False
    return all(any(a <= ord(c) <= b for a, b in FAIXAS_ALVO) for c in uteis)


def expande_in_place(base_dir: str, corpus: Path, bytes_por_idioma: int, n_novos: int,
                     saida: Path):
    """Braco da expansao in-place (`2607.15232`): manter o 32k de PT e ACRESCENTAR.

    ⭐ A forma e' atraente aqui por um motivo medido e nao por analogia: **nao ha' UM token
    nao-latino no 32k**, entao os merges novos nao competem com nada que exista, e a
    preservacao do PT sai quase de graca em vez de ser trade-off.

    ⚠️ Limite honesto da implementacao: `add_tokens` poe os novos por LONGEST-MATCH antes do
    BPE, e nao dentro da tabela de merges. Nao e' identico a re-treinar com o vocab semeado —
    e' o que a pratica de expansao de vocabulario faz, e fica registrado como tal.

    🔴 E UM DEFEITO REAL, MEDIDO EM 2026-09-01, QUE ESTA FUNCAO JA' TEVE
      A v1 acrescentava os tokens na forma **ByteLevel-codificada** (`ØªØ§`), que e' como o BPE
      os guarda. Mas `add_tokens` casa contra o **TEXTO CRU**, e aquela cadeia nunca aparece em
      texto cru. Resultado: 3.770 tokens acrescentados, vocab crescendo de 32.000 para 35.770,
      e fertilidade em arb/cmn/jpn **identica ao baseline ate' a segunda casa**. Nada deu erro.
      O conserto e' DECODIFICAR o token de volta para texto antes de acrescentar — e por isso a
      funcao agora devolve tambem QUANTO a intervencao agiu (§2r), com o chamador abortando a
      leitura do braco se o efeito for zero.
    """
    from tokenizers import Tokenizer, pre_tokenizers, trainers
    from tokenizers.models import BPE
    from transformers import AutoTokenizer

    aux = Tokenizer(BPE(unk_token=None))
    aux.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tr = trainers.BpeTrainer(vocab_size=n_novos + 300, special_tokens=[], min_frequency=2,
                             show_progress=False,
                             initial_alphabet=pre_tokenizers.ByteLevel.alphabet())

    def so_nao_latino():
        for c in NAO_LATINO:
            yield from textos(corpus, c, bytes_por_idioma, "treino")
    aux.train_from_iterator(so_nao_latino(), trainer=tr)

    # ⭐ ByteLevel -> texto. So' entra o que decodifica: fragmento de byte nao pode ser
    # acrescentado como string, e e' justamente o que nao se quer (eixo 3).
    #
    # 🔴 E SO' ENTRA O QUE E' DA ESCRITA-ALVO — segundo defeito medido em 2026-09-01.
    #   O corpus japones e' 9% latino e o chines 12% (URLs, marcas, codigo), entao o BPE
    #   auxiliar aprende merges LATINOS tambem. Acrescentados via `add_tokens`, eles casam
    #   por longest-match ANTES do pre-tokenizador e passam por cima dos merges latinos
    #   eficientes do 32k. Medido sem este filtro: PT de 0,22 para 0,37 tok/caractere,
    #   **+62,9%** — o oposto do "preservacao quase gratuita" que a hipotese previa.
    #   O dano nao vinha de disputa por vocabulario (nao havia disputa: arabe/han/kana = 0);
    #   vinha de COMO o `add_tokens` e' aplicado. Sao coisas diferentes (§2v: intervencao
    #   que age durante a segmentacao nao se avalia so' pelo destino).
    mapa = _mapa_bytelevel()
    cand: list[tuple[int, str]] = []
    for tk_bl, rank in aux.get_vocab().items():
        try:
            txt = bytes(mapa[c] for c in tk_bl).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            continue
        if len(txt) > 1 and txt.strip() and _e_alvo(txt):
            cand.append((rank, txt))
    cand.sort()

    base = AutoTokenizer.from_pretrained(base_dir)
    ja_tem = set(base.get_vocab())
    novos, vistos = [], set()
    for _, txt in cand:
        if txt in ja_tem or txt in vistos:
            continue
        vistos.add(txt)
        novos.append(txt)
        if len(novos) >= n_novos:
            break
    base.add_tokens(novos)
    saida.mkdir(parents=True, exist_ok=True)
    base.save_pretrained(str(saida))
    from transformers import AutoTokenizer as AT
    return AT.from_pretrained(str(saida)), len(novos)


def ids_quebrados(tok) -> tuple[set[int], float, int]:
    """Ids do vocab cujos bytes NAO formam UTF-8 valido sozinhos.

    Num BPE ByteLevel os bytes viram caracteres visiveis; um token e' 'completo' se a
    sequencia de bytes que ele representa decodifica por si so'.

    ⚠️ Retorna o conjunto de ids, nao uma taxa por escrita. Atribuir ESCRITA a um token
    quebrado exigiria adivinhar pelo byte-lider — heuristica que erra em byte de
    continuacao. A medida por idioma sai exata em `incompletude_em_texto()`, contando o
    que o tokenizador REALMENTE emite no holdout daquele idioma. E' tambem o que importa:
    `2410.23684` mede alucinacao em funcao do que o modelo VE', nao do que o vocab guarda.
    """
    mapa = _mapa_bytelevel()
    quebrados, total = set(), 0
    for tk, i in tok.get_vocab().items():
        if tk in ESPECIAIS:
            continue
        try:
            bs = bytes(mapa[c] for c in tk)
        except KeyError:
            continue
        total += 1
        try:
            bs.decode("utf-8")
        except UnicodeDecodeError:
            quebrados.add(i)
    return quebrados, len(quebrados) / max(1, total), total


_MAPA = None


def _mapa_bytelevel() -> dict[str, int]:
    """Inverso da tabela byte->caractere visivel do ByteLevel (a mesma do GPT-2)."""
    global _MAPA
    if _MAPA is None:
        bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
        cs = bs[:]
        n = 0
        for b in range(256):
            if b not in bs:
                bs.append(b)
                cs.append(256 + n)
                n += 1
        _MAPA = {chr(c): b for b, c in zip(bs, cs)}
    return _MAPA


def mede(tok, corpus: Path, docs: int) -> dict:
    """Eixos 1 e 3 juntos, POR IDIOMA — nunca a media (§2y).

    ⭐ A incompletude sai EXATA aqui: conta os tokens que o tokenizador emite de fato no
    holdout de cada idioma e que nao decodificam sozinhos. Sem heuristica de escrita.
    """
    import re
    quebrados, taxa_vocab, n_vocab = ids_quebrados(tok)
    linhas = {"_vocab_quebrado": taxa_vocab, "_vocab_tokens": n_vocab}
    for cod in ORDEM:
        txts = list(textos(corpus, cod, 64 * 1024 ** 2, "holdout"))[:docs]
        if not txts:
            continue
        n_tok = n_qbr = 0
        for t in txts:
            ids = tok(t, add_special_tokens=False)["input_ids"]
            n_tok += len(ids)
            n_qbr += sum(1 for i in ids if i in quebrados)
        n_car = sum(len(t) for t in txts)
        n_byt = sum(len(t.encode("utf-8")) for t in txts)
        n_pal = sum(len(re.findall(r"\w+", t, re.UNICODE)) for t in txts)
        linhas[cod] = {"docs": len(txts), "tok_por_caractere": n_tok / max(1, n_car),
                       "tok_por_byte": n_tok / max(1, n_byt),
                       "tok_por_palavra": n_tok / max(1, n_pal),
                       "frac_tokens_incompletos": n_qbr / max(1, n_tok)}
    return linhas


# ------------------------------------------------------------------ main
def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "bee" / "corpus_multi")
    ap.add_argument("--base", default="models/bee-150m-v3-base", help="o 32k atual")
    ap.add_argument("--vocabs", default="32000,64000,96000,128000")
    ap.add_argument("--bytes-por-idioma", type=int, default=200 * 1024 ** 2)
    ap.add_argument("--docs-holdout", type=int, default=300)
    ap.add_argument("--expansao-novos", type=int, default=32000,
                    help="quantos tokens nao-latinos acrescentar no braco in-place")
    ap.add_argument("--pular-expansao", action="store_true")
    ap.add_argument("--saida-tok", type=Path, default=ROOT / "bee" / "tok_t1")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "gate-t1-vocab.json")
    args = ap.parse_args()

    from transformers import AutoTokenizer

    if not glob.glob(str(args.corpus / "bee_corpus_*.jsonl.zst")):
        raise SystemExit(f"🔴 sem shards em {args.corpus} — rode bee/coletar_multilingue.py")

    print("=" * 92)
    print("GATE T1 — varredura de vocabulario · Bee-1G · 8 idiomas")
    print(f"corpus {args.corpus} · {args.bytes_por_idioma/1024**2:.0f} MB/idioma de treino")
    print("=" * 92)

    bracos: dict[str, dict] = {}

    # ---- braco 0: o 32k atual (o "baseline" que e' um zero) ----
    print(f"\n[braco] 32k-atual ({args.base})")
    tk = AutoTokenizer.from_pretrained(args.base)
    bracos["32k-atual"] = {"vocab": int(tk.vocab_size), "origem": args.base,
                           "idiomas": mede(tk, args.corpus, args.docs_holdout),
                           "minutos": 0.0}

    # ---- bracos do zero, na mistura multilingue ----
    for v in [int(x) for x in args.vocabs.split(",") if x.strip()]:
        nome = f"{v//1000}k-multi"
        print(f"\n[braco] {nome} — treinando BPE…", flush=True)
        t0 = time.time()
        tk = treina(v, args.corpus, args.bytes_por_idioma, args.saida_tok / nome)
        dt = (time.time() - t0) / 60
        print(f"   treinado em {dt:.1f} min · vocab real {tk.vocab_size:,}")
        bracos[nome] = {"vocab": int(tk.vocab_size), "origem": str(args.saida_tok / nome),
                        "idiomas": mede(tk, args.corpus, args.docs_holdout),
                        "minutos": dt}

    # ---- braco da expansao in-place ----
    if not args.pular_expansao:
        nome = f"32k+{args.expansao_novos//1000}k-inplace"
        print(f"\n[braco] {nome} — expandindo o 32k atual…", flush=True)
        t0 = time.time()
        tk, n = expande_in_place(args.base, args.corpus, args.bytes_por_idioma,
                                 args.expansao_novos, args.saida_tok / nome)
        dt = (time.time() - t0) / 60
        print(f"   {n:,} tokens acrescentados em {dt:.1f} min · vocab {len(tk):,}")
        bracos[nome] = {"vocab": int(len(tk)), "origem": str(args.saida_tok / nome),
                        "tokens_acrescentados": n, "idiomas": mede(tk, args.corpus,
                                                                  args.docs_holdout),
                        "minutos": dt,
                        "_ressalva": "add_tokens casa por longest-match ANTES do BPE, nao dentro "
                                     "da tabela de merges — nao e' identico a re-treinar semeado"}

    # ---- guarda das ancoras (§2aa) ----
    print(f"\n{'='*92}\n[ancoras] o 32k-atual reproduz numero publicado?")
    problemas = []
    for cod, esp in ANCORAS.items():
        obt = bracos["32k-atual"]["idiomas"].get(cod, {}).get("tok_por_byte")
        if obt is None:
            continue
        dev = abs(obt - esp) / esp
        print(f"   {cod}: {obt:.4f} contra {esp} ({dev:+.1%})  "
              + ("OK" if dev <= 0.05 else "🔴 NAO REPRODUZ"))
        if dev > 0.05:
            problemas.append(f"{cod}: {obt:.4f} contra {esp}")

    # ---- §2r: TODA intervencao reporta QUANTO agiu ----
    # 🔴 Sem isto, um braco que nao faz nada le'-se como "a ideia nao adiantou". Foi exatamente
    # o que aconteceu na v1 da expansao in-place: 3.770 tokens acrescentados, efeito ZERO nos
    # tres idiomas-alvo, e a tabela saiu publicavel.
    base_ref = bracos.get("32k-atual", {}).get("idiomas", {})
    for nome, b in bracos.items():
        if "inplace" not in nome:
            continue
        efeito = {}
        for c in NAO_LATINO:
            a = base_ref.get(c, {}).get("tok_por_caractere")
            d = b["idiomas"].get(c, {}).get("tok_por_caractere")
            if a and d:
                efeito[c] = (d - a) / a
        b["efeito_vs_32k_atual"] = {k: round(v, 4) for k, v in efeito.items()}
        pior = max((abs(v) for v in efeito.values()), default=0.0)
        b["agiu"] = pior >= 0.01
        print(f"\n[§2r] quanto o braco '{nome}' AGIU nos tres idiomas-alvo:")
        for c, v in efeito.items():
            print(f"       {c}: {v:+.1%}")
        if not b["agiu"]:
            problemas.append(f"{nome}: acrescentou {b.get('tokens_acrescentados')} tokens e "
                             f"mudou <1% em arb/cmn/jpn — o braco NAO AGIU, nao leia como "
                             f"'a expansao nao adianta' (§2r)")
            print(f"       🔴 EFEITO NULO — o braco nao agiu. Nao e' resultado, e' defeito.")

    # ---- tabela: fertilidade POR IDIOMA, nunca a media (§2y) ----
    print(f"\n{'='*92}\nEIXO 1 — CUSTO · tok/caractere por idioma (menor e' melhor)")
    print(f"{'braco':<20} {'vocab':>7} " + " ".join(f"{c:>6}" for c in ORDEM)
          + f" {'emb@2048':>10} {'%1B':>6}")
    print("-" * 92)
    for nome, b in bracos.items():
        cel = " ".join(f"{b['idiomas'].get(c,{}).get('tok_por_caractere', float('nan')):>6.2f}"
                       for c in ORDEM)
        emb = b["vocab"] * D_MODEL_REF
        print(f"{nome:<20} {b['vocab']:>7,} {cel} {emb/1e6:>9.0f}M {emb/ALVO_PARAMS:>5.0%}")

    print(f"\n{'='*92}\nEIXO 3 — INCOMPLETUDE · % dos tokens EMITIDOS que nao decodificam sozinhos")
    print(f"{'braco':<20} {'vocab':>7} " + " ".join(f"{c:>6}" for c in ORDEM))
    print("-" * 92)
    for nome, b in bracos.items():
        cel = " ".join(
            f"{b['idiomas'].get(c, {}).get('frac_tokens_incompletos', float('nan')):>5.1%}"
            for c in ORDEM)
        print(f"{nome:<20} {b['idiomas'].get('_vocab_quebrado', 0):>6.1%} {cel}")

    # ---- veredito do eixo 1, contra o criterio declarado ----
    print(f"\n{'='*92}\nVEREDITO — eixo 1 (custo), criterio declarado ANTES de medir")
    print(f"  PT: piora maxima {TETO_PIORA_PT:.0%} sobre {BASE_PT} tok/byte "
          f"(teto {BASE_PT*(1+TETO_PIORA_PT):.3f}) · nenhum idioma acima de "
          f"{TETO_TOK_PALAVRA} tok/palavra\n")
    for nome, b in bracos.items():
        pt = b["idiomas"].get("por", {}).get("tok_por_byte", float("nan"))
        piora = (pt - BASE_PT) / BASE_PT
        acima = {c: b["idiomas"][c]["tok_por_palavra"] for c in ORDEM
                 if c in b["idiomas"] and b["idiomas"][c]["tok_por_palavra"] > TETO_TOK_PALAVRA}
        ok = piora <= TETO_PIORA_PT and not acima
        b["eixo1_passa"] = bool(ok)
        b["pt_piora"] = piora
        b["acima_do_teto_palavra"] = {k: round(v, 2) for k, v in acima.items()}
        print(f"  {nome:<20} PT {pt:.3f} ({piora:+.1%})  "
              + (f"🔴 acima de {TETO_TOK_PALAVRA} tok/palavra: "
                 + ", ".join(f"{k} {v:.1f}" for k, v in acima.items()) if acima else "")
              + ("  ✅ PASSA" if ok else "  ❌ REPROVA"))

    doc = {"_gate": "T1 — vocabulario multilingue do Bee-1G",
           "_regua": "tokens/CARACTERE — tokens/palavra nao compara entre escritas (§2g)",
           "_criterio_eixo1": {"pt_piora_max": TETO_PIORA_PT, "pt_base_tok_byte": BASE_PT,
                               "teto_tok_palavra": TETO_TOK_PALAVRA},
           "_eixo2_qualidade": {"estado": "NAO MEDIDO",
                                "por_que": "bpb por idioma exige GPU; fertilidade NAO e' "
                                           "preditiva de qualidade (2607.24276, 2310.08754). "
                                           "Este gate nao e' aprovacao final."},
           "_ancoras_problema": problemas or None,
           "d_model_referencia": D_MODEL_REF,
           "corpus": str(args.corpus), "bytes_por_idioma": args.bytes_por_idioma,
           "bracos": bracos}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".json.tmp")
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, args.out)
    print(f"\nartefato: {args.out}")

    print("\n⚠️ EIXO 2 (qualidade, bpb por idioma) NAO FOI MEDIDO — exige GPU. "
          "Fertilidade nao e' preditiva de qualidade; este gate NAO e' aprovacao final.")
    if problemas:
        print(f"\n🔴 o braco de controle nao reproduz ancora publicada — nao leia a tabela (§2aa)")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
