"""Roda os baselines EXTERNOS de sentimento e tradução nos MESMOS conjuntos do Bee.

⭐ POR QUE ISTO É INDISPENSÁVEL, E NÃO UM LUXO

Todo número deste projeto até aqui tem a forma "o Bee contra o próprio Bee, ou contra um piso
trivial". Piso trivial diz se há capacidade; ele não diz se a capacidade **serve para
alguma coisa**. Um léxico marca 79% em sentimento — se um modelo publicado de 167M marca 95%,
o Bee superar 80% é uma frase muito diferente do que se o publicado marcar 82%.

⚠️ E CADA BASELINE VEM COM O SEU DESCASAMENTO DECLARADO, porque nenhum deles é uma comparação
   perfeita e fingir que é seria pior que não ter baseline nenhum:

   · `nlptown/bert-base-multilingual-uncased-sentiment` (167M) — treinado em **review de
     produto**, exatamente o nosso domínio, mas em en/nl/de/fr/it/es: **português não está na
     lista**. É transferência zero-shot de língua. Acerta o domínio, erra a língua.
   · `pysentimiento/bertweet-pt-sentiment` (125M) — treinado em **português**, mas em
     **tweet**. Acerta a língua, erra o domínio.
   · `Helsinki-NLP/opus-mt-tc-big-en-pt` (~230M) — este é comparação limpa: tradução en→pt,
     mesma direção, e o FLORES é conjunto de avaliação publicado para ele.

   Os dois primeiros formam um par útil justamente por errarem coisas opostas: se o Bee ficar
   abaixo dos dois, não há desculpa de domínio nem de língua.

🔴 RODA EM CPU DE PROPÓSITO. São modelos de 125–230M; a GPU está ocupada pelo gate de
   matemática, e bloquear um run de 4,6 h para medir baseline seria trocar a medição cara
   pela barata na ordem errada.

Uso:
    python comeia/eval/baselines_externos.py --o-que sentimento
    python comeia/eval/baselines_externos.py --o-que traducao
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

SENT_DADOS = Path(__file__).resolve().parent / "benchmarks" / "sentimento_pt.jsonl"
TRAD_DADOS = Path(__file__).resolve().parent / "benchmarks" / "traducao_flores_pt_en.jsonl"

SENTIMENTO = [
    # (id, descasamento declarado, funcao de mapeamento do rotulo)
    ("nlptown/bert-base-multilingual-uncased-sentiment",
     "dominio CERTO (review de produto), lingua ERRADA (PT nao esta' no treino)"),
    ("pysentimiento/bertweet-pt-sentiment",
     "lingua CERTA (PT), dominio ERRADO (tweet, nao review)"),
]
TRADUCAO_EN_PT = "Helsinki-NLP/opus-mt-tc-big-en-pt"
# ⚠️ A Helsinki nao publica um `opus-mt-tc-big-pt-en`. Os candidatos abaixo sao tentados em
#    ordem e o que carregar e' o usado — com o id impresso no relatorio, porque comparar
#    contra "um modelo da Helsinki" sem dizer qual nao e' comparacao.
TRADUCAO_PT_EN = ["Helsinki-NLP/opus-mt-tc-big-cat_oci_spa-eng",
                  "Helsinki-NLP/opus-mt-ROMANCE-en",
                  "Helsinki-NLP/opus-mt-mul-en"]


def rotulo_binario(nome_modelo: str, etiqueta: str, pontuacoes: dict) -> str | None:
    """Traduz a saída de cada modelo para positivo/negativo. None = o modelo disse neutro.

    ⚠️ O nlptown devolve estrelas ('1 star'..'5 stars') e o pysentimiento devolve POS/NEU/NEG.
    Mapear 3 estrelas ou NEU para uma das classes seria inventar decisão que o modelo não
    tomou; esses casos viram abstenção e são contados como ERRO, que é o tratamento honesto
    num conjunto onde a resposta neutra não existe.
    """
    e = etiqueta.lower()
    if "star" in e:
        n = int(e[0])
        return None if n == 3 else ("positivo" if n >= 4 else "negativo")
    if e.startswith("pos"):
        return "positivo"
    if e.startswith("neg"):
        return "negativo"
    return None


def rodar_sentimento(limite: int) -> int:
    from transformers import pipeline
    from eval_sentimento_pt import ablacoes, lexico, lexico_com, relatar

    itens = [json.loads(l) for l in SENT_DADOS.read_text(encoding="utf-8").split(chr(10))
             if l.strip()]
    if limite:
        itens = itens[:limite]

    print("=" * 78)
    print("BASELINES EXTERNOS — SENTIMENTO (CPU)")
    print("=" * 78)
    print(f"dados: {SENT_DADOS.name} · {len(itens)} itens")
    print("")
    print("-- pisos internos, para o baseline externo ficar no mesmo eixo")
    relatar("PISO classe majoritaria", itens, ["positivo"] * len(itens))
    relatar("PISO lexico de 60 palavras", itens, [lexico(it["texto"]) for it in itens])
    for nome, boas, ruins in ablacoes():
        if "SO a palavra" in nome:
            relatar("PISO so' a palavra 'nao'", itens,
                    [lexico_com(it["texto"], boas, ruins) for it in itens])

    fora = {}
    for mid, descasamento in SENTIMENTO:
        print("")
        print(f"-- {mid}")
        print(f"   descasamento: {descasamento}")
        # ⚠️ O LIMITE DE POSICAO E' DO MODELO, NAO NOSSO. Um `max_length=256` fixo derrubou o
        #    bertweet-pt no item 160 com "index 130 is out of bounds": ele tem 130 posicoes,
        #    nao 512. O erro veio como RuntimeError no meio do loop, depois de o baseline
        #    anterior ja' ter impresso resultado — o tipo de falha que deixa um JSON velho no
        #    disco parecendo atual. Le-se o teto do config e trunca-se por ele.
        try:
            from transformers import AutoConfig
            cfg = AutoConfig.from_pretrained(mid)
            teto = min(int(getattr(cfg, "max_position_embeddings", 512) or 512), 512)
            teto = max(16, teto - 2)                  # desconta [CLS]/[SEP]
            print(f"   limite de posicao do modelo: {teto} tokens")
            clf = pipeline("text-classification", model=mid, device=-1, truncation=True,
                           max_length=teto)
        except Exception as e:                                   # noqa: BLE001
            print(f"   ⚠️ nao carregou ({type(e).__name__}: {str(e)[:110]}) — pulado")
            continue
        t0, prev, abst = time.time(), [], 0
        try:
            for i in range(0, len(itens), 16):
                for it, r in zip(itens[i:i + 16],
                                 clf([x["texto"] for x in itens[i:i + 16]])):
                    p = rotulo_binario(mid, r["label"], r)
                    if p is None:
                        abst += 1
                        p = "abstencao"                 # conta como erro, sempre
                    prev.append(p)
                if (i + 16) % 160 == 0:
                    print(f"   {min(i + 16, len(itens))}/{len(itens)} · "
                          f"{(time.time() - t0) / 60:.1f} min", flush=True)
        except Exception as e:                                   # noqa: BLE001
            # falha de UM baseline nao pode derrubar os outros nem impedir a gravacao
            print(f"   🔴 quebrou no item {len(prev)}: {type(e).__name__}: {str(e)[:120]}")
            fora[mid] = {"erro": f"{type(e).__name__}: {str(e)[:200]}",
                         "itens_antes_de_quebrar": len(prev),
                         "descasamento": descasamento}
            continue
        r = relatar(f"EXTERNO {mid.split('/')[-1][:22]}", itens, prev)
        r["abstencoes"] = abst
        r["descasamento"] = descasamento
        if abst:
            print(f"   ⚠️ {abst} abstencoes (neutro/3 estrelas) contadas como erro — "
                  f"o conjunto e' binario por construcao")
        fora[mid] = r

    alvo = RAIZ / "docs" / "baselines-externos-sentimento.json"
    alvo.write_text(json.dumps(fora, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  relatorio: {alvo}")
    return 0


def rodar_traducao(limite: int) -> int:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from eval_traducao_pt import pontuar

    itens = [json.loads(l) for l in TRAD_DADOS.read_text(encoding="utf-8").split(chr(10))
             if l.strip()]
    if limite:
        itens = itens[:limite]

    print("=" * 78)
    print("BASELINES EXTERNOS — TRADUCAO (CPU)")
    print("=" * 78)
    print(f"dados: {TRAD_DADOS.name} · {len(itens)} itens")
    print("")
    print("-- piso interno")
    pontuar("PISO copiar a fonte", itens, [it["origem"] for it in itens])

    escolhidos = {"en->pt": TRADUCAO_EN_PT, "pt->en": None}
    for cand in TRADUCAO_PT_EN:
        try:
            AutoTokenizer.from_pretrained(cand)
            escolhidos["pt->en"] = cand
            break
        except Exception:                                        # noqa: BLE001
            print(f"   (pt->en: {cand} indisponivel)")
    print(f"\n  modelos: en->pt = {escolhidos['en->pt']} · pt->en = {escolhidos['pt->en']}")

    saidas = [""] * len(itens)
    for direcao, mid in escolhidos.items():
        if not mid:
            print(f"  ⚠️ {direcao} SEM baseline externo — nenhum candidato carregou. O numero")
            print("     do Bee nesta direcao fica sem referencia publicada, e isso e' dito.")
            continue
        print(f"\n-- {direcao}: {mid}")
        tok = AutoTokenizer.from_pretrained(mid)
        mod = AutoModelForSeq2SeqLM.from_pretrained(mid).eval()
        idx = [k for k, it in enumerate(itens) if it["direcao"] == direcao]
        t0 = time.time()
        for a in range(0, len(idx), 8):
            bloco = idx[a:a + 8]
            entrada = [itens[k]["origem"] for k in bloco]
            if "ROMANCE" in mid or "mul-en" in mid:
                entrada = entrada                     # esses modelos nao pedem tag na entrada
            ent = tok(entrada, return_tensors="pt", padding=True, truncation=True,
                      max_length=256)
            with torch.no_grad():
                g = mod.generate(**ent, max_new_tokens=180, num_beams=1)
            for k, s in zip(bloco, tok.batch_decode(g, skip_special_tokens=True)):
                saidas[k] = s.strip()
            if (a + 8) % 80 == 0:
                print(f"   {min(a + 8, len(idx))}/{len(idx)} · "
                      f"{(time.time() - t0) / 60:.1f} min", flush=True)

    print("")
    print("=" * 78)
    r = pontuar("EXTERNO opus-mt", itens, saidas)
    r["modelos"] = escolhidos
    alvo = RAIZ / "docs" / "baselines-externos-traducao.json"
    alvo.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  relatorio: {alvo}")
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--o-que", choices=["sentimento", "traducao"], required=True)
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()
    return rodar_sentimento(a.limite) if a.o_que == "sentimento" else rodar_traducao(a.limite)


if __name__ == "__main__":
    raise SystemExit(main())
