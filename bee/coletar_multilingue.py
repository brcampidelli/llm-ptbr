"""Amostra BALANCEADA dos 8 idiomas-alvo do Bee-1G — insumo do Gate T1 (tokenizador).

⭐ POR QUE ESTE SCRIPT EXISTE (2026-09-01)
  O censo do nosso vocabulario de 32k achou **arabe = 0, han = 0, kana = 0 tokens**. Tres dos
  oito idiomas-alvo nao tem UM token e so' podem ser representados por fallback de byte. O Gate T1
  decide entao **como** expandir, nao **se** — e para varrer tamanho de vocabulario e' preciso ter
  os oito idiomas em disco, no formato que o `train_tokenizer.py` ja' le'.

  Fontes, com licenca conferida na origem em 2026-09-01:
    · 7 idiomas  -> `HuggingFaceFW/fineweb-2`  (1.870 configs, licenca **odc-by**)
    · ingles     -> `HuggingFaceFW/fineweb`    (o fineweb-2 NAO tem ingles)

⚠️ A UNIDADE DE BALANCEAMENTO E' UMA DECISAO, NAO UM DETALHE
  Balancear por BYTE da' ao CJK ~1/3 dos caracteres do latim (UTF-8: 3 bytes/caractere contra 1);
  balancear por CARACTERE da' ao CJK ~3x os bytes. Nao ha' escolha neutra, e ela **enviesa
  diretamente quantos merges cada escrita ganha** na varredura de vocabulario. O default aqui e'
  CARACTERE (proxy de conteudo), e o script imprime as DUAS contagens por idioma para que a escolha
  fique visivel e reversivel. Trocar com `--unidade bytes`.

⚠️ E A ARMADILHA QUE ESPERA NO PASSO SEGUINTE (§2g)
  A metrica historica do projeto e' **fertilidade em tokens/PALAVRA**, e `\\w+` **nao segmenta
  chines nem japones** — nessas escritas nao ha' espaco, entao uma "palavra" vira uma corrida
  inteira de caracteres e o numero fica incomparavel entre idiomas. Para os oito, a regua tem de ser
  **tokens/CARACTERE** (ou tokens/byte). Este script ja' grava char e byte por idioma para que a
  medicao seguinte nao dependa de recontar.

⭐ GUARDAS (todas da familia "dado some e nada reclama")
  1. cada config e' verificado na API do HF **antes** de baixar — idioma ausente aborta, nao pula;
  2. **verificacao de escrita**: a amostra de `arb_Arab` tem de conter codepoints arabes, a de
     `cmn_Hani` codepoints han, etc. Config trocado por engano passaria silencioso sem isto;
  3. idioma que fecha abaixo de 90% do alvo **aborta** — coleta parcial nao vira corpus sem aviso;
  4. idioma PEDIDO que nao chegou ao manifesto vira falha explicita, com o motivo;
  5. MANIFEST reescrito **a cada idioma** (nunca so' no fim) e zerado no inicio da corrida.
     🔴 A guarda 5 nasceu de um defeito real, na primeira corrida dos 8 (2026-09-01): o
     `datasets` estourou ao trocar de repo no ultimo idioma, **sete** conjuntos de shards ficaram
     em disco e o MANIFEST seguiu com os **dois** de um teste anterior. Ninguem teria notado lendo
     o manifesto — que e' justamente o arquivo que existe para dizer o que ha' ali (§2z).

Uso:
    python bee/coletar_multilingue.py --mb-por-idioma 300
    python bee/coletar_multilingue.py --idiomas por,arb --mb-por-idioma 50   # teste rapido
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- os 8 idiomas
# `escrita` e' o que a guarda 2 exige encontrar no texto. `fonte` vira o campo do shard e
# e' o que o `train_tokenizer.py` usa para separar os holdouts por idioma.
IDIOMAS = {
    "por": {"repo": "HuggingFaceFW/fineweb-2", "config": "por_Latn", "escrita": "latim"},
    "spa": {"repo": "HuggingFaceFW/fineweb-2", "config": "spa_Latn", "escrita": "latim"},
    "fra": {"repo": "HuggingFaceFW/fineweb-2", "config": "fra_Latn", "escrita": "latim"},
    "deu": {"repo": "HuggingFaceFW/fineweb-2", "config": "deu_Latn", "escrita": "latim"},
    "jpn": {"repo": "HuggingFaceFW/fineweb-2", "config": "jpn_Jpan", "escrita": "kana"},
    "cmn": {"repo": "HuggingFaceFW/fineweb-2", "config": "cmn_Hani", "escrita": "han"},
    "arb": {"repo": "HuggingFaceFW/fineweb-2", "config": "arb_Arab", "escrita": "arabe"},
    "eng": {"repo": "HuggingFaceFW/fineweb", "config": "sample-10BT", "escrita": "latim"},
}

# faixas de codepoint por escrita — a guarda 2
FAIXAS = {
    "latim": [(0x0041, 0x024F)],
    "arabe": [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)],
    "han": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF)],
    "kana": [(0x3040, 0x309F), (0x30A0, 0x30FF)],
}

# fracao minima de caracteres na escrita esperada. Web real e' misturada (URLs, marcas,
# codigo em latim dentro de pagina japonesa), entao o limiar e' de SANIDADE, nao de pureza:
# ele existe para pegar "pedi arabe e vieram 0% de caracteres arabes".
MIN_ESCRITA = 0.10


def perfil_escrita(texto: str) -> dict[str, float]:
    """Fracao de caracteres de cada escrita. Ignora espaco, digito e pontuacao."""
    cont = {k: 0 for k in FAIXAS}
    total = 0
    for ch in texto:
        cat = unicodedata.category(ch)
        if cat[0] in ("Z", "C") or cat in ("Nd", "Po", "Ps", "Pe", "Pd"):
            continue
        total += 1
        cp = ord(ch)
        for nome, faixas in FAIXAS.items():
            if any(a <= cp <= b for a, b in faixas):
                cont[nome] += 1
                break
    return {k: v / max(1, total) for k, v in cont.items()}


def confere_configs(idiomas: list[str]) -> None:
    """Guarda 1: o config existe na origem? Aborta antes de baixar 1 byte."""
    import urllib.request
    cache: dict[str, tuple[set[str], str | None]] = {}
    for cod in idiomas:
        info = IDIOMAS[cod]
        repo = info["repo"]
        if repo not in cache:
            url = f"https://huggingface.co/api/datasets/{repo}?full=true"
            req = urllib.request.Request(url, headers={"User-Agent": "bee-1g"})
            d = json.load(urllib.request.urlopen(req, timeout=90))
            card = d.get("cardData", {}) or {}
            nomes = {c["config_name"] for c in card.get("configs", []) or []}
            cache[repo] = (nomes, card.get("license"))
        nomes, lic = cache[repo]
        if nomes and info["config"] not in nomes:
            raise SystemExit(f"🔴 config '{info['config']}' NAO existe em {repo} — abortando")
        info["licenca"] = lic
        print(f"  {cod}  {repo}/{info['config']:12} licenca={lic}  OK")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--idiomas", default=",".join(IDIOMAS),
                    help="lista separada por virgula (default: os 8)")
    ap.add_argument("--mb-por-idioma", type=float, default=300.0,
                    help="alvo por idioma, na unidade escolhida (MB de bytes ou M de caracteres)")
    ap.add_argument("--unidade", choices=["caracteres", "bytes"], default="caracteres",
                    help="⚠️ enviesa quantos merges cada escrita ganha — ver docstring")
    ap.add_argument("--out", type=Path, default=ROOT / "bee" / "corpus_multi")
    ap.add_argument("--docs-por-shard", type=int, default=50_000)
    ap.add_argument("--min-chars-doc", type=int, default=200,
                    help="documento curto demais nao ensina merge nenhum")
    ap.add_argument("--tolerancia", type=float, default=0.90,
                    help="guarda 3: fracao minima do alvo por idioma; abaixo disso, aborta")
    args = ap.parse_args()

    idiomas = [c.strip() for c in args.idiomas.split(",") if c.strip()]
    desconhecido = [c for c in idiomas if c not in IDIOMAS]
    if desconhecido:
        raise SystemExit(f"🔴 idioma desconhecido: {desconhecido}. Conhecidos: {list(IDIOMAS)}")

    print(f"{'='*78}\nGate T1 — amostra multilingue para o tokenizador do Bee-1G")
    print(f"alvo: {args.mb_por_idioma:.0f} M{'car' if args.unidade=='caracteres' else 'B'}"
          f" por idioma · {len(idiomas)} idiomas · unidade = {args.unidade}\n{'='*78}")

    print("\n[guarda 1] conferindo os configs na origem…")
    confere_configs(idiomas)

    import zstandard as zstd
    from datasets import load_dataset

    args.out.mkdir(parents=True, exist_ok=True)
    alvo = int(args.mb_por_idioma * 1_000_000)
    manifesto: dict[str, dict] = {}
    falhas: list[str] = []

    def grava_manifesto() -> Path:
        """⭐ Escrito DEPOIS DE CADA IDIOMA, nunca so' no fim.

        🔴 Medido em 2026-09-01, na primeira corrida dos 8: o `datasets` estourou
        `RuntimeError: Cannot send a request, as the client has been closed` ao trocar de repo
        (fineweb-2 -> fineweb) no 8o idioma. Sete idiomas estavam em disco e o manifesto ficou
        com os DOIS de um teste anterior — artefato de procedencia contradizendo o proprio
        diretorio, que e' §2z na forma mais pura. Manifesto so' vale se acompanhar o disco.
        """
        man = {
            "_gerado": "bee/coletar_multilingue.py",
            "_gate": "T1 — tokenizador multilingue do Bee-1G",
            "unidade_de_balanceamento": args.unidade,
            "alvo_por_idioma": alvo,
            "_parcial": sorted(set(idiomas) - set(manifesto) - set(erros)) or None,
            "_erros": erros or None,
            "_aviso_metrica": ("fertilidade em tokens/PALAVRA nao e' comparavel entre escritas — "
                               "`\\w+` nao segmenta han nem kana. Usar tokens/CARACTERE (§2g)."),
            "idiomas": manifesto,
        }
        p = args.out / "MANIFEST.json"
        tmp = p.with_suffix(".json.tmp")
        io.open(tmp, "w", encoding="utf-8", newline="\n").write(
            json.dumps(man, indent=2, ensure_ascii=False) + "\n")
        tmp.replace(p)
        return p

    erros: dict[str, str] = {}
    grava_manifesto()          # ⭐ zera o manifesto ANTES: nunca deixar o de outra corrida em pe'

    for cod in idiomas:
        info = IDIOMAS[cod]
        fonte = f"fineweb2-{cod}" if "fineweb-2" in info["repo"] else f"fineweb-{cod}"
        t0 = time.time()
        print(f"\n── {cod} ({info['config']}) ─────────────────────────────────────")

        # o cliente HTTP do `datasets` as vezes fecha ao trocar de repo — uma retentativa resolve,
        # e o idioma que falhar mesmo assim vira ERRO REGISTRADO, nao um buraco silencioso.
        ds = None
        for tentativa in (1, 2):
            try:
                ds = load_dataset(info["repo"], name=info["config"],
                                  split="train", streaming=True)
                break
            except Exception as e:
                print(f"   ⚠️ tentativa {tentativa} falhou: {type(e).__name__}: {e}")
                if tentativa == 2:
                    erros[cod] = f"{type(e).__name__}: {e}"
                    grava_manifesto()
                time.sleep(5)
        if ds is None:
            continue

        n_char = n_byte = n_doc = 0
        amostra_escrita: list[str] = []      # primeiros docs, para a guarda 2
        buf: list[str] = []
        n_shard = 0

        def descarrega() -> None:
            nonlocal buf, n_shard
            if not buf:
                return
            p = args.out / f"bee_corpus_{cod}_{n_shard:04d}.jsonl.zst"
            bruto = "\n".join(buf).encode("utf-8")
            tmp = p.with_suffix(p.suffix + ".tmp")
            with open(tmp, "wb") as fh:                # temp+rename: nunca truncar antes de gravar
                fh.write(zstd.ZstdCompressor(level=6).compress(bruto))
            tmp.replace(p)
            n_shard += 1
            buf = []

        try:
            for ex in ds:
                texto = (ex.get("text") or "").strip()
                if len(texto) < args.min_chars_doc:
                    continue
                b = len(texto.encode("utf-8"))
                buf.append(json.dumps({"text": texto, "fonte": fonte}, ensure_ascii=False))
                n_char += len(texto)
                n_byte += b
                n_doc += 1
                if len(amostra_escrita) < 200:
                    amostra_escrita.append(texto)
                if len(buf) >= args.docs_por_shard:
                    descarrega()
                visto = n_char if args.unidade == "caracteres" else n_byte
                if visto >= alvo:
                    break
        except Exception as e:
            # o que ja' veio fica em disco E no manifesto, marcado como interrompido
            erros[cod] = f"interrompido apos {n_doc} docs: {type(e).__name__}: {e}"
            print(f"   🔴 {erros[cod]}")
        descarrega()

        visto = n_char if args.unidade == "caracteres" else n_byte
        perfil = perfil_escrita("".join(amostra_escrita)[:400_000])
        frac = perfil.get(info["escrita"], 0.0)
        dt = (time.time() - t0) / 60

        print(f"   docs {n_doc:>9,} · {n_char/1e6:8.1f} Mcar · {n_byte/1e6:8.1f} MB "
              f"· {n_byte/max(1,n_char):.2f} B/car · {dt:.1f} min · {n_shard} shards")
        print(f"   [guarda 2] escrita '{info['escrita']}' = {frac:.1%}  "
              + "  ".join(f"{k} {v:.0%}" for k, v in perfil.items() if v >= 0.01))

        if frac < MIN_ESCRITA:
            falhas.append(f"{cod}: escrita '{info['escrita']}' em {frac:.1%} "
                          f"(minimo {MIN_ESCRITA:.0%}) — config errado?")
        if visto < alvo * args.tolerancia:
            falhas.append(f"{cod}: fechou em {visto/alvo:.0%} do alvo "
                          f"({visto/1e6:.0f}M de {alvo/1e6:.0f}M) — fonte esgotou?")

        manifesto[cod] = {
            "repo": info["repo"], "config": info["config"], "licenca": info.get("licenca"),
            "fonte": fonte, "escrita_esperada": info["escrita"],
            "documentos": n_doc, "caracteres": n_char, "bytes_utf8": n_byte,
            "bytes_por_caractere": n_byte / max(1, n_char),
            "shards": n_shard, "minutos": dt,
            "perfil_escrita": {k: round(v, 4) for k, v in perfil.items() if v >= 0.001},
            "interrompido": erros.get(cod),
        }
        p = grava_manifesto()      # ⭐ manifesto acompanha o disco, idioma a idioma

    # ---------------------------------------------------------------- resumo
    print(f"\n{'='*78}")
    print(f"{'idioma':7} {'docs':>10} {'Mcar':>9} {'MB':>9} {'B/car':>6}  escrita")
    for cod, m in manifesto.items():
        print(f"{cod:7} {m['documentos']:>10,} {m['caracteres']/1e6:>9.1f} "
              f"{m['bytes_utf8']/1e6:>9.1f} {m['bytes_por_caractere']:>6.2f}  "
              f"{m['escrita_esperada']} {m['perfil_escrita'].get(m['escrita_esperada'],0):.0%}")
    tot_c = sum(m["caracteres"] for m in manifesto.values())
    tot_b = sum(m["bytes_utf8"] for m in manifesto.values())
    print(f"{'TOTAL':7} {sum(m['documentos'] for m in manifesto.values()):>10,} "
          f"{tot_c/1e6:>9.1f} {tot_b/1e6:>9.1f}")
    print(f"\nmanifesto: {grava_manifesto()}")

    # ⭐ guarda 4: idioma PEDIDO que nao entrou no manifesto e' buraco — e buraco tem de gritar.
    ausentes = [c for c in idiomas if c not in manifesto]
    for c in ausentes:
        falhas.append(f"{c}: NAO COLETADO — {erros.get(c, 'motivo desconhecido')}")
    for c, msg in erros.items():
        if c in manifesto:
            falhas.append(f"{c}: coleta interrompida — {msg}")

    if falhas:
        print(f"\n🔴 {len(falhas)} GUARDA(S) DISPARARAM:")
        for f in falhas:
            print(f"   · {f}")
        print(f"\n{len(manifesto)} de {len(idiomas)} idiomas ficaram completos. Os shards estao em "
              "disco e o MANIFEST registra exatamente quais — mas NAO use este corpus sem "
              "resolver o acima.")
        return 2

    print("\n✅ guardas 1-4 passaram nos", len(manifesto), "idiomas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
