"""Mede tradução PT↔EN no FLORES-200, com o piso que quase toda avaliação de MT esquece.

⚠️ AQUI O PROJETO ABRE UMA EXCEÇÃO À PRÓPRIA REGRA, E VALE DIZER POR QUÊ

A regra do projeto é medir por execução, nunca por similaridade. Tradução é o caso em que ela
não se aplica: não existe interpretador que decida se "o gato subiu no telhado" é a tradução
certa de "the cat climbed onto the roof". O campo mede por similaridade com referência
humana (chrF++, BLEU) e é assim que os números publicados existem — inclusive o do
`opus-mt-tc-big`, que é a referência externa deste projeto.

Então a similaridade fica, **mas não sozinha**. Três medições determinísticas entram junto,
e cada uma pega uma falha que o chrF++ não pega:

  · **taxa de idioma-alvo** — o modelo traduziu ou copiou? Copiar a fonte é a estratégia
    degenerada clássica de MT, e entre línguas com vocabulário latino comum ela pontua
    surpreendentemente bem no chrF++. Medido neste conjunto: copiar a fonte marca **chrF++
    de ~20 pontos**, que é acima de muitos modelos pequenos de verdade.
  · **preservação de número** — tradução que troca 1.500 por 15.000 está errada, e o chrF++
    quase não nota (um caractere de diferença num texto de 200). ⚠️ Medida no mesmo run, a
    estratégia de copiar já preserva **95%** dos números: este teste é detector de falha
    grosseira, não discriminador entre bom e ótimo. Dito aqui para que ninguém leia "95% de
    números" como desempenho.
  · **taxa de resposta vazia** — separa "traduziu mal" de "não traduziu".

⭐ E O PISO É IMPRESSO NO MESMO RUN. Um modelo abaixo do "copiar a fonte" não traduz: ele
   produz ruído que por acaso compartilha caracteres com a referência.

Uso:
    python comeia/eval/eval_traducao_pt.py --model BrCamp/bee-350m-pt-base
    python comeia/eval/eval_traducao_pt.py --dry-run    # pisos, sem modelo
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from resumo_pt_verificadores import extrair_numeros  # noqa: E402

DADOS = Path(__file__).resolve().parent / "benchmarks" / "traducao_flores_pt_en.jsonl"
MODELO_PADRAO = "BrCamp/bee-350m-pt-base"
POR_DIRECAO = 300
SEMENTE = 20260819

MOLDES = {
    "en->pt": "Traduza a frase do inglês para o português.\n\nInglês: {origem}\nPortuguês:",
    "pt->en": "Traduza a frase do português para o inglês.\n\nPortuguês: {origem}\nInglês:",
}

_FUNC_PT = (" de ", " que ", " para ", " com ", " nao ", " uma ", " dos ", " como ", " mas ",
            " por ", " os ", " as ", " em ", " do ", " da ", " se ", " ao ", " e ")
_FUNC_EN = (" the ", " and ", " of ", " to ", " is ", " for ", " with ", " that ", " in ",
            " on ", " are ", " was ", " it ", " as ")


def idioma(texto: str) -> str:
    """'pt', 'en' ou '?' — com MARGEM, ao contrário do verificador do IFEval.

    ⚠️ O `idioma_portugues` do IFEval devolve True em empate, de propósito: lá a pergunta é
    "está em português?" e a folga favorece o modelo. Aqui a pergunta é "em QUAL idioma
    está?", e um empate honesto precisa sair como indefinido — senão todo texto curto ou
    ambíguo é contado como acerto de direção.
    """
    c = unicodedata.normalize("NFD", f" {texto.lower()} ")
    c = "".join(x for x in c if unicodedata.category(x) != "Mn")
    c = re.sub(r"\s+", " ", c)
    pt = sum(c.count(p) for p in _FUNC_PT)
    en = sum(c.count(p) for p in _FUNC_EN)
    if pt > en:
        return "pt"
    if en > pt:
        return "en"
    return "?"


def numeros_preservados(saida: str, referencia: str) -> bool:
    """Todo número da referência aparece na saída. Tradução que perde ou troca número
    está errada, e o chrF++ mal registra a diferença."""
    ref = extrair_numeros(referencia)
    if not ref:
        return True
    got = extrair_numeros(saida)
    return all(any(abs(v - f) <= max(1e-6, abs(f) * 1e-9) for v in got) for f in ref)


def preparar() -> int:
    """Extrai os pares PT/EN do FLORES-200 devtest e grava o jsonl."""
    import os
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")   # cgroup pequeno mata o Xet
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    caminho = hf_hub_download("mteb/flores", "devtest.parquet", repo_type="dataset")
    tab = pq.read_table(caminho, columns=["eng_Latn", "por_Latn"])
    en = tab.column("eng_Latn").to_pylist()
    pt = tab.column("por_Latn").to_pylist()
    print(f"  FLORES-200 devtest: {len(en)} frases pareadas")

    rng = random.Random(SEMENTE)
    idx = rng.sample(range(len(en)), POR_DIRECAO)
    itens = []
    for k, i in enumerate(idx):
        itens.append({"id": f"en2pt-{k:03d}", "direcao": "en->pt",
                      "origem": en[i], "referencia": pt[i], "linha_flores": i})
        itens.append({"id": f"pt2en-{k:03d}", "direcao": "pt->en",
                      "origem": pt[i], "referencia": en[i], "linha_flores": i})
    DADOS.parent.mkdir(parents=True, exist_ok=True)
    with DADOS.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"  ✅ {len(itens)} itens ({POR_DIRECAO} por direcao) em {DADOS.name}")
    return 0


def pontuar(nome: str, itens: list[dict], saidas: list[str]) -> dict:
    from sacrebleu.metrics import BLEU, CHRF
    fora = {"nome": nome}
    for direcao in ("en->pt", "pt->en"):
        par = [(it, s) for it, s in zip(itens, saidas) if it["direcao"] == direcao]
        if not par:
            continue
        hip = [s for _, s in par]
        ref = [[it["referencia"] for it, _ in par]]
        chrf = CHRF(word_order=2).corpus_score(hip, ref).score        # chrF++
        bleu = BLEU().corpus_score(hip, ref).score
        alvo = "pt" if direcao.endswith("pt") else "en"
        certo = sum(idioma(s) == alvo for _, s in par) / len(par)
        nums = sum(numeros_preservados(s, it["referencia"]) for it, s in par) / len(par)
        vazio = sum(not s.strip() for _, s in par) / len(par)
        fora[direcao] = {"chrf2": chrf, "bleu": bleu, "idioma_alvo": certo,
                         "numeros_ok": nums, "vazio": vazio, "n": len(par)}
        print(f"  {nome:28} {direcao}  chrF++ {chrf:5.1f} · BLEU {bleu:5.1f} · "
              f"idioma-alvo {100 * certo:5.1f}% · numeros {100 * nums:5.1f}%"
              + (f" · vazio {100 * vazio:.0f}%" if vazio else ""))
    return fora


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO_PADRAO)
    ap.add_argument("--peft", default=None)
    ap.add_argument("--preparar", action="store_true", help="so' baixa e monta o jsonl")
    ap.add_argument("--max-new", type=int, default=128)
    ap.add_argument("--lote", type=int, default=8)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--chat", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    print("=" * 78)
    print("TRADUCAO PT<->EN — FLORES-200 devtest")
    print("=" * 78)

    if a.preparar or not DADOS.exists():
        if preparar() != 0:
            return 1
        if a.preparar:
            return 0

    itens = [json.loads(l) for l in DADOS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limite:
        itens = itens[:a.limite]
    print(f"dados : {DADOS.name} · {len(itens)} itens")
    print(f"modelo: {a.model}" + (f" + adapter {a.peft}" if a.peft else ""))
    print("")
    print("-- pisos (nenhum modelo envolvido)")
    piso = pontuar("PISO copiar a fonte", itens, [it["origem"] for it in itens])

    if a.dry_run:
        print("")
        print("✅ DRY-RUN: pisos calculados. Nenhum modelo foi carregado.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    _AQUI = str(Path(__file__).resolve().parent)
    if _AQUI not in sys.path:
        sys.path.insert(0, _AQUI)
    from paradas import ids_de_parada
    # 🔴 Ver comeia/eval/paradas.py: sem parada, um modelo que APRENDEU a terminar
    #    gera ate o teto, o caso vira "truncado" e o parser recebe N respostas
    #    concatenadas. A regua marca 0% justamente no modelo que acertou.
    PARADAS = ids_de_parada(tok, a.chat)
    print(f"paradas: {{PARADAS}}")
    tok.padding_side = "left"
    modelo = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda().eval()
    if a.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, a.peft).eval()

    saidas, t0, lote, i = [], time.time(), a.lote, 0
    while i < len(itens):
        bloco = itens[i:i + lote]
        textos = [MOLDES[b["direcao"]].format(origem=b["origem"]) for b in bloco]
        if a.chat:
            textos = [tok.apply_chat_template([{"role": "user", "content": t}],
                                              tokenize=False, add_generation_prompt=True)
                      for t in textos]
        ent = tok(textos, return_tensors="pt", padding=True, truncation=True,
                  max_length=768).to("cuda")
        try:
            with torch.no_grad():
                g = modelo.generate(**ent, max_new_tokens=a.max_new, do_sample=False,
                                    eos_token_id=PARADAS,
                                    pad_token_id=tok.pad_token_id)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if lote == 1:
                raise
            lote = max(1, lote // 2)
            print(f"  ⚠️ OOM — lote {lote}, refazendo", flush=True)
            continue
        for j in range(len(bloco)):
            bruto = tok.decode(g[j][ent["input_ids"].shape[1]:], skip_special_tokens=True)
            # o modelo base costuma continuar inventando pares; fica so' a primeira linha
            saidas.append(bruto.strip().split("\n")[0].strip())
        i += len(bloco)
        torch.cuda.empty_cache()
        dt = (time.time() - t0) / 60
        if i % (lote * 5) == 0 or i >= len(itens):
            print(f"  {i}/{len(itens)} · {dt:.1f} min · "
                  f"resta ~{dt / i * (len(itens) - i):.1f} min", flush=True)

    print("")
    print("=" * 78)
    print("RESULTADO")
    print("=" * 78)
    r = pontuar(f"MODELO {a.model.split('/')[-1][:18]}", itens, saidas)

    print("")
    for direcao in ("en->pt", "pt->en"):
        d = 100 * (r[direcao]["chrf2"] - piso[direcao]["chrf2"]) / max(1e-9,
                                                                      piso[direcao]["chrf2"])
        if r[direcao]["chrf2"] <= piso[direcao]["chrf2"]:
            print(f"  🔴 {direcao}: o modelo NAO supera copiar a fonte "
                  f"({r[direcao]['chrf2']:.1f} contra {piso[direcao]['chrf2']:.1f} de chrF++).")
            print("     Nao ha' traducao acontecendo — ha' ruido que compartilha caracteres.")
        else:
            print(f"  ✅ {direcao}: supera o piso em {d:+.0f}% de chrF++")
        if r[direcao]["idioma_alvo"] < 0.5:
            print(f"     ⚠️ so' {100 * r[direcao]['idioma_alvo']:.0f}% das saidas estao no "
                  f"idioma-alvo — o problema e' de DIRECAO, nao de qualidade.")

    alvo = RAIZ / "docs" / f"traducao-pt{('-' + a.tag) if a.tag else ''}.json"
    alvo.write_text(json.dumps({"modelo": a.model, "peft": a.peft, "modelo_r": r,
                                "piso_copiar": piso}, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\n  relatorio: {alvo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
