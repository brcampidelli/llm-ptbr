"""Gate T-TRAD estagio B — o portugues traduzido serve como dado de pre-treino?

ESTAGIO A (fechado em 2026-09-02): a duplicacao cross-lingual no Common Corpus e' 0,05%, entao
traduzir NAO instancia o problema do `2606.24998`. Isso liberou o estagio B; nao o respondeu.

O estagio B tem TRES modos de falha independentes, e portanto TRES instrumentos:

    perfil    quanto do documento CABE no tradutor?     CPU, minutos
    probe     quanto custa 1B de tokens traduzidos?     GPU, minutos   (§3, §4)
    traduzir  quanto do texto SOBREVIVE ao pipeline?    GPU            (§2b, §2r)
    avaliar   a traducao presta, contra referencia?     GPU            (§2l: com PISO)

⚠️ A ORDEM IMPORTA, e nao e' a ordem do interesse. `perfil` e `probe` vem ANTES de `avaliar`
   porque um custo proibitivo mata o plano seja qual for a qualidade — medir qualidade primeiro
   seria pagar para responder uma pergunta que outro eixo ja' decidiu.

🔴 A REGUA NAO PODE SER bpb DO PT. O `2607.00890` mede que a loss na lingua-alvo SUBESTIMA
   sistematicamente o valor da mistura: ela captura o efeito de regularizacao, nao o
   conhecimento novo. bpb daria a resposta errada com cara de resposta certa (§2y).

🔴 TRADUTOR — a licenca e' criterio de admissao, nao detalhe:
     Madlad-400 (google)   Apache-2.0   ✅  T5 do Google, 7 idiomas-alvo -> pt num modelo so'
     Opus-MT (Helsinki)    Apache-2.0   ✅  baseline barato, mas pares indiretos via ingles
     NLLB (todas variantes) cc-by-nc-4.0 ❌  contaminaria o modelo publicado
     TowerInstruct         cc-by-nc-4.0 ❌  idem
     ALMA-7B/13B           🔴 declara MIT sobre pesos que sao fine-tune FULL de LLaMA-2.
                              Rotulo permissivo sobre conteudo de licenca diferente — o mesmo
                              padrao que reprovou o Ultra-FineWeb na triagem de 2026-09-02.

Uso:
    python bee/gate_trad_b.py perfil --docs-por-idioma 3000
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# os 7 do common_corpus que sao alvo do Bee-1G. O 8o (pt) e' o que falta la' e o que se quer
# produzir aqui — por isso ele nao aparece nesta lista.
ALVOS = ["en", "fr", "de", "es", "zh", "ja", "ar"]

# ⚠️ O campo `language` vem por EXTENSO ("French"), nao em ISO — verificado no esquema real.
# Filtrar por lang[:2] leria ZERO documentos sem dar erro nenhum (a familia "dado some e nada
# reclama"). Mesmo mapa do estagio A, de proposito: instrumento diferente sobre a mesma fonte
# tem de selecionar os MESMOS documentos, senao a comparacao entre os estagios nao vale.
NOME_PARA_COD = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es", "italian": "it",
    "dutch": "nl", "polish": "pl", "latin": "la", "russian": "ru", "korean": "ko",
    "chinese": "zh", "japanese": "ja", "arabic": "ar",
}

TRADUTOR_PADRAO = "google/madlad400-3b-mt"


def _e_oom(e: BaseException) -> bool:
    """Torch levanta OutOfMemoryError em alguns caminhos e AcceleratorError em outros.

    MEDIDO 2026-09-02: no lote 64 o estouro veio como `torch.AcceleratorError: CUDA error:
    out of memory` dentro do `generate`, o `except torch.cuda.OutOfMemoryError` nao pegou, e
    o script MORREU depois de ja' ter medido tres lotes bons — sem gravar o artefato.
    Perder a medicao por causa do tratamento do erro e' pior que o erro.
    """
    return "out of memory" in str(e).lower() or type(e).__name__ in (
        "OutOfMemoryError", "AcceleratorError")

# Fim de sentenca. ⚠️ Inclui a pontuacao de CJK (。！？) e do arabe (؟ ۔) DE PROPOSITO: um
# separador so' de latim devolveria UMA sentenca gigante para chines, japones e arabe, o
# pipeline truncaria tudo, e o numero sairia sem erro nenhum. A guarda que verifica se isto
# funcionou esta' em `perfil` — sentencas por mil caracteres, POR IDIOMA.
_FIM = re.compile(r"[.!?。！？؟۔]+[\s　]*|\n{2,}")

# Piso abaixo do qual o separador de sentenca esta' claramente inerte naquele idioma. Um texto
# em prosa tem sentencas de ~15-40 palavras; menos de 1 sentenca a cada 1000 caracteres
# significa que o separador nao encontrou a pontuacao daquela escrita.
MIN_SENT_POR_KCHAR = 1.0


def separa_sentencas(t: str) -> list[str]:
    partes = [p.strip() for p in _FIM.split(t) if p and p.strip()]
    return partes


def cmd_perfil(args) -> int:
    """Distribuicao de tamanho dos documentos, em TOKENS DO TRADUTOR.

    ⭐ Em tokens, nao em caracteres: o limite que morde e' o do modelo, e a razao
    token/caractere varia 3x entre latim e CJK. Medir em caractere e depois supor a conversao
    seria trocar a variavel medida por uma suposta — §2ad, o erro do add_tokens.
    """
    from datasets import load_dataset
    from transformers import AutoTokenizer

    print(f"tokenizador do tradutor: {args.tradutor}", flush=True)
    tok = AutoTokenizer.from_pretrained(args.tradutor)

    # §2ad: VERIFICAR o que a API faz, em vez de supor. Antes de medir nada, perguntar ao
    # objeto carregado qual e' o limite dele e o que ele faz ao estourar.
    lim = getattr(tok, "model_max_length", None)
    print(f"model_max_length declarado: {lim}")
    if lim is None or lim > 10 ** 6:
        print("  ⚠️ o tokenizador NAO declara limite util — entao o limite real e' do MODELO,")
        print("     nao do tokenizador, e truncamento silencioso e' possivel. O `probe` mede.")
    amostra = "palavra " * 5000
    n = len(tok(amostra, add_special_tokens=False)["input_ids"])
    print(f"5000 palavras -> {n} tokens SEM truncar (o tokenizador nao corta por conta propria)"
          if n > 4000 else f"🔴 5000 palavras -> {n} tokens: o tokenizador TRUNCOU em silencio")
    print()

    idiomas = [c.strip() for c in args.idiomas.split(",") if c.strip()]
    alvo = {c: args.docs_por_idioma for c in idiomas}
    dados: dict[str, list[tuple[int, int, int]]] = defaultdict(list)  # (car, tok, sent)

    ds = load_dataset(args.repo, split="train", streaming=True)
    t0, lidos = time.time(), 0
    for ex in ds:
        lidos += 1
        cod = NOME_PARA_COD.get(str(ex.get("language", "")).strip().lower())
        if cod not in alvo or len(dados[cod]) >= alvo[cod]:
            if all(len(dados[c]) >= alvo[c] for c in idiomas):
                break
            continue
        txt = ex.get("text") or ""
        if not txt:
            continue
        ntok = len(tok(txt, add_special_tokens=False)["input_ids"])
        dados[cod].append((len(txt), ntok, len(separa_sentencas(txt))))
        if lidos % 200_000 == 0:
            feito = {c: len(dados[c]) for c in idiomas}
            print(f"  {lidos:>9} lidos · {feito} · {(time.time()-t0)/60:.1f} min", flush=True)

    print(f"\n{'='*100}")
    print(f"PERFIL DOS DOCUMENTOS — {lidos} lidos do stream, {(time.time()-t0)/60:.1f} min")
    print(f"{'='*100}")
    print(f"{'idioma':<8}{'docs':>7}{'tok p50':>9}{'p90':>8}{'p99':>9}{'max':>9}"
          f"{'tok/car':>9}{'sent/kcar':>11}")
    print("-" * 100)

    saida = {}
    for c in idiomas:
        v = dados[c]
        if not v:
            print(f"{c:<8}{'0':>7}   🔴 ZERO documentos — o filtro de idioma nao casou")
            continue
        toks = sorted(x[1] for x in v)
        cars = sum(x[0] for x in v)
        sents = sum(x[2] for x in v)
        q = lambda p: toks[min(len(toks) - 1, int(len(toks) * p))]
        spk = 1000 * sents / cars
        alerta = "  🔴 separador inerte" if spk < MIN_SENT_POR_KCHAR else ""
        print(f"{c:<8}{len(v):>7}{q(.50):>9}{q(.90):>8}{q(.99):>9}{toks[-1]:>9}"
              f"{sum(x[1] for x in v)/cars:>9.3f}{spk:>11.2f}{alerta}")
        saida[c] = {"docs": len(v), "tok_p50": q(.50), "tok_p90": q(.90), "tok_p99": q(.99),
                    "tok_max": toks[-1], "tok_por_car": sum(x[1] for x in v) / cars,
                    "sent_por_kcar": spk, "car_total": cars,
                    "sent_mediana_tok": st.median([x[1] / max(1, x[2]) for x in v])}

    print()
    print("FRACAO DOS DOCUMENTOS QUE ESTOURA CADA ORCAMENTO DE TOKENS:")
    orcs = [256, 512, 1024, 2048, 4096]
    print(f"{'idioma':<8}" + "".join(f"{'>'+str(o):>9}" for o in orcs))
    print("-" * (8 + 9 * len(orcs)))
    for c in idiomas:
        if not dados[c]:
            continue
        toks = [x[1] for x in dados[c]]
        linha = "".join(f"{100*sum(1 for t in toks if t > o)/len(toks):>8.1f}%" for o in orcs)
        print(f"{c:<8}{linha}")
        saida[c]["estoura"] = {str(o): sum(1 for t in toks if t > o) / len(toks) for o in orcs}

    doc = {
        "_gate": "T-TRAD estagio B · perfil",
        "_pergunta": "quanto do documento do Common Corpus cabe no tradutor?",
        "_regua": "TOKENS do tokenizador do proprio tradutor, nunca caracteres (§2ad)",
        "_nao_mostra": [
            "qualidade de traducao — e' o `avaliar`, e com PISO de copiar a fonte",
            "custo — e' o `probe`, medido, nunca extrapolado (§3)",
            "o que o MODELO faz ao estourar; isto e' so' o tokenizador",
            "a mediana de tokens por sentenca supoe que o separador funcionou naquele idioma; "
            "a coluna sent/kcar e' a guarda disso (§2r: reportar QUANTO o instrumento agiu)",
        ],
        "tradutor": args.tradutor, "repo": args.repo,
        "docs_lidos_do_stream": lidos, "por_idioma": saida,
    }
    dest = ROOT / "docs" / "gate-trad-b-perfil.json"
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)
    print(f"\nartefato: docs/{dest.name}")
    return 0


# Frase de guarda: curta, sem ambiguidade, e cuja traducao correta e' verificavel a olho.
FRASE_GUARDA = "The European Commission adopted a new regulation on data protection."


def carrega_tradutor(nome, dtype, dev, verboso=True):
    """Carrega o Madlad CONSERTANDO a fiacao de embedding — e prova que consertou.

    🔴🔴 MEDIDO 2026-09-02, e e' a §2ad no nivel da BIBLIOTECA.

    O checkpoint do madlad400 guarda apenas DOIS tensores de embedding:
        decoder.embed_tokens.weight  (256000, 1024)
        lm_head.weight               (256000, 1024)
    Nao ha' `shared` nem `encoder.embed_tokens`. Em T5, `shared` e' a matriz de ENTRADA usada
    por encoder e decoder; neste checkpoint ela e' a do decoder, e o `lm_head` e' proprio
    (config: tie_word_embeddings=False).

    O `transformers` 5.14 fabrica um `shared`, enche com os valores do **lm_head** e aponta o
    ENCODER para la'. O encoder passa a ler a matriz de SAIDA como se fosse a de entrada.
    Sintoma: nenhum erro, nenhuma excecao, e toda traducao vira repeticao de uma letra
    cirilica ate' bater em max_new_tokens. Normas medidas ao carregar:
        shared 2.441 · encoder 2.441 · lm_head 2.441 · decoder 207.971
    Depois do conserto (encoder e shared <- decoder): traducao perfeita, 19 tokens em vez de 81.

    ⚠️ O DANO QUE ISSO JA' CAUSOU AQUI: o primeiro probe mediu 355 tok/s e projetou US$ 774 por
    1B de tokens — tudo sobre saidas degeneradas de 256 tokens. O custo real e' ~14x menor.
    Um numero que matava o plano, produzido por um defeito de carregamento.

    ⚠️ E o conserto tem SENTIDO: `encoder <- decoder`. Na primeira tentativa eu fiz
    `decoder <- shared`, que sobrescreve o embedding BOM com o do lm_head e piora tudo.
    """
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

    tok = AutoTokenizer.from_pretrained(nome)
    m = AutoModelForSeq2SeqLM.from_pretrained(nome, dtype=dtype).to(dev).eval()

    def normas():
        return (m.shared.weight.norm().item(),
                m.encoder.embed_tokens.weight.norm().item(),
                m.decoder.embed_tokens.weight.norm().item(),
                m.lm_head.weight.norm().item())

    n0 = normas()
    # a assinatura do defeito: o encoder casa com o lm_head e DISCORDA do decoder
    torto = abs(n0[1] - n0[3]) < 1e-3 * max(1.0, n0[3]) and abs(n0[1] - n0[2]) > 1e-3 * n0[2]
    if torto:
        d = m.decoder.embed_tokens.weight
        m.shared.weight = d
        m.encoder.embed_tokens.weight = d
        if verboso:
            print(f"  🔴 fiacao torta detectada (encoder=={n0[1]:.0f}=lm_head, decoder="
                  f"{n0[2]:.0f}) — encoder e shared reapontados para o decoder")
    elif verboso:
        print("  fiacao ja' correta neste `transformers` — nada a consertar")

    # GUARDA FUNCIONAL (§2t): a checagem de normas acima e' estrutural e pode ficar inerte se a
    # biblioteca mudar de novo. Esta aqui nao pode: ou o modelo traduz, ou aborta.
    e = tok(f"<2pt> {FRASE_GUARDA}", return_tensors="pt").to(dev)
    n_ent = e["input_ids"].shape[1]
    with torch.no_grad():
        o = m.generate(**e, max_new_tokens=96, num_beams=1)
    ids = o[0].tolist()
    txt = tok.decode(o[0], skip_special_tokens=True)
    razao = len(ids) / n_ent
    distintos = len(set(ids)) / max(1, len(ids))
    if verboso:
        print(f"  guarda: {n_ent} tok -> {len(ids)} tok (razao {razao:.2f}, "
              f"distintos {distintos:.2f}) · {txt[:70]!r}")
    if razao > 3.0 or distintos < 0.5:
        raise SystemExit(
            f"🔴 TRADUTOR DEGENERADO — abortando antes de medir qualquer coisa.\n"
            f"   entrada {n_ent} tok -> saida {len(ids)} tok (razao {razao:.2f}); "
            f"tokens distintos {distintos:.2f} da saida.\n"
            f"   saida: {txt[:120]!r}\n"
            f"   Uma traducao fiel tem razao ~1 e alta diversidade. Isto e' repeticao.\n"
            f"   Normas ao carregar: shared {n0[0]:.0f} · enc {n0[1]:.0f} · "
            f"dec {n0[2]:.0f} · lm_head {n0[3]:.0f}")
    return tok, m


def _amostra_sentencas(repo, idiomas, por_idioma, tok, teto_tok):
    """Sentencas REAIS do Common Corpus, na distribuicao que o pipeline vai encontrar.

    ⚠️ Nao usar frase sintetica nem FLORES aqui: o throughput depende do COMPRIMENTO, e o
    perfil ja' mediu que a sentenca mediana vai de 21,7 tokens (de) a 46,3 (ja). Medir com
    frase de tamanho arbitrario seria medir outra coisa (§2g: mesmos itens?).
    """
    from datasets import load_dataset
    out = defaultdict(list)
    ds = load_dataset(repo, split="train", streaming=True)
    for ex in ds:
        cod = NOME_PARA_COD.get(str(ex.get("language", "")).strip().lower())
        if cod not in idiomas or len(out[cod]) >= por_idioma:
            if all(len(out[c]) >= por_idioma for c in idiomas):
                break
            continue
        for s in separa_sentencas(ex.get("text") or ""):
            if len(out[cod]) >= por_idioma:
                break
            n = len(tok(s, add_special_tokens=False)["input_ids"])
            if 4 <= n <= teto_tok:
                out[cod].append(s)
    return out


def _doc_probe(args, medidas, n_ent, n_sai, txt_sai, longo):
    import torch
    return {"_gate": "T-TRAD estagio B · probe de throughput",
            "_regua": "tokens de SAIDA por segundo, em regime, mediana das 3 ultimas (§3)",
            "_parcial": "gravado a cada lote — um OOM no lote seguinte nao apaga os anteriores",
            "_nao_mostra": [
                "qualidade da traducao — e' o `avaliar`, e com PISO",
                "custo na 5090: medido NESTA placa; §4 mede que o preditor e' o TDP, e "
                "extrapolar entre placas ja' produziu uma recomendacao errada neste projeto",
                "o custo de CPU de ler e re-montar os documentos",
            ],
            "gpu": torch.cuda.get_device_name(0), "tradutor": args.tradutor,
            "max_new_tokens": args.max_novos, "por_lote": medidas,
            "melhor_lote": (max(medidas, key=lambda k: medidas[k]["tok_saida_s"])
                            if medidas else None),
            "entrada_longa": {"tok_entrada": n_ent, "tok_saida": n_sai,
                              "frac_car_preservada": len(txt_sai) / max(1, len(longo))}}


def _grava_probe(doc):
    dest = ROOT / "docs" / "gate-trad-b-probe.json"
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    tmp.replace(dest)
    return dest


def cmd_probe(args) -> int:
    """Throughput MEDIDO do tradutor, e o custo em $/B tokens (§3, §4).

    ⚠️ Vem ANTES de qualquer medicao de qualidade de proposito: se o custo for proibitivo, o
    plano morre seja qual for a qualidade, e medir qualidade primeiro seria pagar para
    responder uma pergunta ja' decidida por outro eixo.
    """
    import torch

    print(f"carregando {args.tradutor} em bf16...", flush=True)
    t0 = time.time()
    try:
        tok, modelo = carrega_tradutor(args.tradutor, torch.bfloat16, "cuda")
    except Exception as erro:
        if not _e_oom(erro):
            raise
        livre, total = torch.cuda.mem_get_info()
        print(f"🔴 OOM ao carregar. VRAM total {total/2**30:.1f} GB, livre {livre/2**30:.1f} GB.")
        print("   Isto E' o resultado da medicao, nao uma falha do teste: nesta placa o "
              "Madlad-3B nao cabe, e o custo tem de ser medido no pod.")
        return 2
    print(f"  carregado em {time.time()-t0:.0f}s · "
          f"VRAM {torch.cuda.memory_allocated()/2**30:.2f} GB")

    idiomas = [c.strip() for c in args.idiomas.split(",") if c.strip()]
    print(f"\namostrando sentencas reais de {len(idiomas)} idiomas...", flush=True)
    amostra = _amostra_sentencas(args.repo, idiomas, args.sentencas, tok, args.teto_tok)
    for c in idiomas:
        ns = [len(tok(s, add_special_tokens=False)["input_ids"]) for s in amostra[c][:200]]
        print(f"  {c}: {len(amostra[c])} sentencas · mediana {st.median(ns) if ns else 0:.0f} tok")

    # 🔴 §2ad — O QUE O MODELO FAZ AO ESTOURAR. O tokenizador nao trunca (perfil mediu
    # model_max_length = 1e30), entao o corte, se existe, e' aqui. Um documento longo entrando
    # inteiro e saindo pela metade nao levanta excecao nenhuma.
    print("\n--- o que o MODELO faz com entrada longa (§2ad) ---")
    longo = " ".join(amostra[idiomas[0]][:80])
    ent = tok(f"<2pt> {longo}", return_tensors="pt").to("cuda")
    n_ent = ent["input_ids"].shape[1]
    with torch.no_grad():
        saida = modelo.generate(**ent, max_new_tokens=args.max_novos, num_beams=1)
    n_sai = int((saida[0] != tok.pad_token_id).sum())
    txt_sai = tok.decode(saida[0], skip_special_tokens=True)
    print(f"  entrada {n_ent} tok -> saida {n_sai} tok ({len(txt_sai)} car)")
    print(f"  entrada tinha {len(longo)} car; a saida tem {100*len(txt_sai)/len(longo):.0f}% disso")
    if n_sai >= args.max_novos - 2:
        print(f"  🔴 a saida BATEU no teto de max_new_tokens={args.max_novos} — truncada, e sem "
              f"erro nenhum. Confirma que a unidade de traducao tem de ser a SENTENCA.")

    # --- throughput em regime (§3: nunca uma leitura solta) ---
    print(f"\n--- throughput por tamanho de lote ---")
    print(f"{'lote':>6}{'lotes':>7}{'tok saida/s':>13}{'sent/s':>9}{'no teto':>9}{'VRAM GB':>9}")
    print("-" * 53)
    todas = [s for c in idiomas for s in amostra[c]]
    medidas = {}
    for lote in [int(x) for x in args.lotes.split(",")]:
        try:
            leituras, n_teto, n_sent, n_tok = [], 0, 0, 0
            t_ini = None
            for i in range(0, min(len(todas), lote * (args.lotes_medidos + args.aquecimento)),
                           lote):
                grupo = [f"<2pt> {s}" for s in todas[i:i + lote]]
                if len(grupo) < lote:
                    break
                ent = tok(grupo, return_tensors="pt", padding=True, truncation=True,
                          max_length=args.teto_tok + 8).to("cuda")
                with torch.no_grad():
                    out = modelo.generate(**ent, max_new_tokens=args.max_novos, num_beams=1)
                # o aquecimento nao entra na conta — §3, so' o regime
                if i // lote == args.aquecimento - 1:
                    torch.cuda.synchronize()
                    t_ini = time.time()
                if t_ini is not None and i // lote >= args.aquecimento:
                    reais = (out != tok.pad_token_id).sum(dim=1)
                    n_tok += int(reais.sum())
                    n_sent += len(grupo)
                    n_teto += int((reais >= args.max_novos - 2).sum())
                    torch.cuda.synchronize()
                    leituras.append(n_tok / max(1e-9, time.time() - t_ini))
            if not leituras:
                continue
            tps = st.median(leituras[-3:]) if len(leituras) >= 3 else leituras[-1]
            vram = torch.cuda.max_memory_allocated() / 2 ** 30
            print(f"{lote:>6}{len(leituras):>7}{tps:>13.0f}{tps/max(1,n_tok/n_sent):>9.1f}"
                  f"{100*n_teto/max(1,n_sent):>8.1f}%{vram:>9.2f}")
            medidas[lote] = {"tok_saida_s": tps, "sentencas": n_sent,
                             "frac_no_teto": n_teto / max(1, n_sent), "vram_gb": vram}
            # 🔴 MEDIDO 2026-09-02: o lote 64 estourou a VRAM, o `except` pegou, e entao o
            #    `torch.cuda.empty_cache()` DENTRO do tratamento estourou tambem — erro de
            #    alocacao no nivel do driver envenena o contexto CUDA e nao ha' recuperacao no
            #    mesmo processo. O script morreu com QUATRO lotes medidos e nao gravou nada.
            #    O conserto nao e' tratar melhor a excecao: e' PERSISTIR A CADA PASSO. Mesma
            #    licao do `grava_meta()` por braco no Gate T1.
            _grava_probe(_doc_probe(args, medidas, n_ent, n_sai, txt_sai, longo))
            torch.cuda.reset_peak_memory_stats()
        except Exception as erro:
            if not _e_oom(erro):
                raise
            print(f"{lote:>6}   🔴 OOM — este lote nao cabe em {torch.cuda.get_device_properties(0).total_memory/2**30:.0f} GB")
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

    if not medidas:
        print("\n🔴 nenhum lote coube — sem medicao de custo nesta placa.")
        return 2

    melhor = max(medidas, key=lambda k: medidas[k]["tok_saida_s"])
    tps = medidas[melhor]["tok_saida_s"]
    gpu = torch.cuda.get_device_name(0)
    print(f"\n{'='*84}\nCUSTO — medido, nunca extrapolado (§4: $/B tokens, nunca $/h)\n{'='*84}")
    print(f"melhor lote {melhor} · {tps:.0f} tok de saida/s nesta placa ({gpu})")
    print(f"{'volume de PT traduzido':<28}{'horas':>9}{'US$ @0,99/h':>14}")
    print("-" * 51)
    for alvo in (0.1e9, 0.5e9, 1e9, 5e9):
        h = alvo / tps / 3600
        print(f"{alvo/1e9:>6.1f}B tokens{'':<14}{h:>9.0f}{h*0.99:>14.0f}")
    print(f"\n⚠️ Esta placa e' uma {gpu}. O numero da 5090 do RunPod e' OUTRO e tem de ser")
    print("   medido la' — a §4 mede que o preditor e' o TDP, e extrapolar entre placas foi")
    print("   exatamente o erro que custou uma recomendacao de hardware errada.")

    dest = _grava_probe(_doc_probe(args, medidas, n_ent, n_sai, txt_sai, longo))
    print(f"\nartefato: docs/{dest.name}")
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("perfil")
    p.add_argument("--repo", default="PleIAs/common_corpus")
    p.add_argument("--tradutor", default=TRADUTOR_PADRAO)
    p.add_argument("--idiomas", default=",".join(ALVOS))
    p.add_argument("--docs-por-idioma", type=int, default=3000)
    p.set_defaults(fn=cmd_perfil)

    q = sub.add_parser("probe")
    q.add_argument("--repo", default="PleIAs/common_corpus")
    q.add_argument("--tradutor", default=TRADUTOR_PADRAO)
    q.add_argument("--idiomas", default="en,fr,de,es")
    q.add_argument("--sentencas", type=int, default=400, help="sentencas amostradas por idioma")
    q.add_argument("--teto-tok", type=int, default=180,
                   help="descarta sentenca acima disto — o pipeline real tambem descartaria")
    q.add_argument("--max-novos", type=int, default=256)
    q.add_argument("--lotes", default="1,8,16,32")
    q.add_argument("--aquecimento", type=int, default=3,
                   help="lotes descartados antes de medir (§3: nunca ler o aquecimento)")
    q.add_argument("--lotes-medidos", type=int, default=12)
    q.set_defaults(fn=cmd_probe)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
