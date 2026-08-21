"""Mede análise de sentimento em PT sobre review real (B2W), com os dois pisos que importam.

⭐ ACURÁCIA SOZINHA NÃO DIZ SE HÁ CAPACIDADE. Três números precisam vir juntos:

  · **acurácia** — quantos acertou;
  · **distribuição das respostas** — um modelo que responde "positivo" em 95% dos casos e
    acerta 52% não está lendo sentimento, está repetindo um prior. O sintoma é invisível na
    acurácia e óbvio na distribuição;
  · **acurácia balanceada** — média das duas revocações. É ela que desmonta o prior: um
    modelo enviesado tem acurácia perto de 50% e balanceada também, mas com revocações de
    95% e 8%, e aí a leitura muda completamente.

⭐ E DOIS PISOS, medidos no mesmo run:

  · **classe majoritária** = 50,0% por construção (o conjunto é balanceado de propósito);
  · **léxico de 60 palavras** — contar palavra boa menos palavra ruim. Não usa modelo nenhum,
    roda em milissegundos, e marca **79,0%** neste conjunto. Se o Bee-350M não passa disso,
    "faz análise de sentimento" é frase sem lastro.

🔴 E O LÉXICO PRECISOU SER DESMONTADO ANTES DE VIRAR REFERÊNCIA. A ablação, impressa a cada
   run, mostra de onde vêm os 79%:

       léxico completo (60 palavras) ....... 79,0%
       sem a palavra "não" ................. 62,8%   (−16,2 pp)
       SÓ a palavra "não" como negativa .... 73,2%
       3 palavras boas / 3 ruins ........... 54,3%

   Ou seja: **uma única palavra carrega 73,2%**, e as outras 59 acrescentam 5,8 pp. Em review
   de e-commerce brasileiro a negação é o sinal dominante de superfície — "não gostei", "não
   funciona", "não recomendo". Isso muda como o resultado do modelo se lê: superar 79% não
   prova compreensão de sentimento, prova que ele faz melhor que detectar negação. E ficar
   *abaixo* de 73% significa perder para um `grep -c "não"`, o que é um diagnóstico bem mais
   duro que "acurácia modesta".

⚠️ COMO O MODELO BASE É PERGUNTADO: por **verossimilhança**, não por geração livre. Compara-se
   o logprob de " positivo" e de " negativo" como continuação do mesmo prompt. Geração livre
   num modelo base mede formatação — se ele escreve "O produto parece bom" em vez de
   "positivo", o parser reprova algo que o modelo acertou. É a distinção estrito/frouxo do
   IFEval aplicada aqui, e a versão por verossimilhança é a que o campo usa (lm-eval-harness).

Uso:
    python comeia/eval/eval_sentimento_pt.py --model BrCamp/bee-350m-pt-base
    python comeia/eval/eval_sentimento_pt.py --dry-run     # so' os pisos, sem modelo
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DADOS = Path(__file__).resolve().parent / "benchmarks" / "sentimento_pt.jsonl"
MODELO_PADRAO = "BrCamp/bee-350m-pt-base"

MOLDE = ("Avalie o sentimento da avaliação de produto abaixo.\n\n"
         "Avaliação: {texto}\n\nSentimento (positivo ou negativo):")
ROTULOS = [" positivo", " negativo"]

# léxico mínimo — 30 de cada lado, escolhidas por frequência em português comercial
BOAS = """otimo otima excelente bom boa maravilhoso maravilhosa perfeito perfeita adorei amei
gostei recomendo recomendado satisfeito satisfeita rapido rapida lindo linda top show
qualidade eficiente confortavel barato vale supera atendeu funciona""".split()
RUINS = """ruim pessimo pessima horrivel terrivel decepcionado decepcionada decepcao odiei
detestei quebrado quebrada defeito nao demorou atrasou atrasado devolvi devolucao estorno
reclamacao problema falso lixo caro fraco frustrado arrependido pior nunca""".split()


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def lexico(texto: str) -> str:
    """Piso trivial: conta palavra boa menos palavra ruim. Empate → positivo (classe maior
    no corpus original, então é o chute que um sistema ingênuo daria)."""
    t = set(re.findall(r"[a-z]+", _norm(texto)))
    return "positivo" if len(t & set(BOAS)) >= len(t & set(RUINS)) else "negativo"


def ablacoes() -> list[tuple[str, list, list]]:
    """(nome, palavras boas, palavras ruins) — quatro recortes do mesmo lexico."""
    sem_nao = [w for w in RUINS if w != "nao"]
    return [
        ("lexico completo (60 palavras)", BOAS, RUINS),
        ("sem a palavra nao", BOAS, sem_nao),
        ("SO a palavra nao como ruim", BOAS, ["nao"]),
        ("3 boas / 3 ruins", ["bom", "otimo", "recomendo"],
         ["ruim", "pessimo", "defeito"]),
    ]


def lexico_com(texto: str, boas: list[str], ruins: list[str]) -> str:
    t = set(re.findall(r"[a-z]+", _norm(texto)))
    return "positivo" if len(t & set(boas)) >= len(t & set(ruins)) else "negativo"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


def relatar(nome: str, itens: list[dict], previstos: list[str]) -> dict:
    n = len(itens)
    acertos = sum(it["rotulo"] == p for it, p in zip(itens, previstos))
    dist = Counter(previstos)
    rev = {}
    for cls in ("positivo", "negativo"):
        alvo = [(it, p) for it, p in zip(itens, previstos) if it["rotulo"] == cls]
        rev[cls] = sum(it["rotulo"] == p for it, p in alvo) / max(1, len(alvo))
    bal = sum(rev.values()) / 2
    lo, hi = wilson(acertos, n)
    print(f"  {nome:34} acuracia {100 * acertos / n:5.1f}% "
          f"[{100 * lo:.1f}–{100 * hi:.1f}] · balanceada {100 * bal:5.1f}% · "
          f"respondeu {dict(dist)}")
    return {"nome": nome, "n": n, "acuracia": acertos / n, "balanceada": bal,
            "revocacao": rev, "ic95": [lo, hi], "distribuicao": dict(dist)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO_PADRAO)
    ap.add_argument("--peft", default=None)
    ap.add_argument("--dados", type=Path, default=DADOS)
    ap.add_argument("--lote", type=int, default=16)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    if not a.dados.exists():
        print(f"🔴 {a.dados.name} nao existe. Rode comeia/eval/preparar_sentimento_pt.py.",
              file=sys.stderr)
        return 1
    itens = [json.loads(l) for l in a.dados.read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    if a.limite:
        itens = itens[:a.limite]

    print("=" * 78)
    print("SENTIMENTO PT — B2W-Reviews01, binario e balanceado")
    print("=" * 78)
    print(f"dados : {a.dados.name} · {len(itens)} itens · "
          f"{dict(Counter(i['rotulo'] for i in itens))}")
    print(f"modelo: {a.model}" + (f" + adapter {a.peft}" if a.peft else ""))
    print("")
    print("-- pisos (nenhum modelo envolvido)")
    r_maj = relatar("PISO classe majoritaria", itens, ["positivo"] * len(itens))
    r_lex = relatar("PISO lexico de 60 palavras", itens, [lexico(it["texto"]) for it in itens])

    # ⭐ de onde vem o piso do lexico — sem isto ele parece um sistema, e e' quase uma palavra
    print("")
    print("   ablacao do lexico (de onde vem a acuracia dele):")
    for nome, boas, ruins in ablacoes():
        prev = [lexico_com(it["texto"], boas, ruins) for it in itens]
        acc = sum(it["rotulo"] == pv for it, pv in zip(itens, prev)) / len(itens)
        print(f"     {nome:32} {100 * acc:5.1f}%")
    print("   ⚠️ a negacao sozinha ja' explica quase todo o piso. Superar 79% nao prova")
    print("      compreensao de sentimento; ficar abaixo de 73% e' perder para um grep.")

    if a.dry_run:
        print("\n✅ DRY-RUN: pisos calculados. Nenhum modelo foi carregado.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda().eval()
    if a.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, a.peft).eval()

    def logprob(prompts: list[str], sufixos: list[str]) -> list[float]:
        """logprob total do sufixo dado o prompt, um par por posição."""
        fora = []
        for p_, s_ in zip(prompts, sufixos):
            ids_p = tok(p_, return_tensors="pt").input_ids
            ids_ps = tok(p_ + s_, return_tensors="pt").input_ids.to("cuda")
            n_p = ids_p.shape[1]
            with torch.no_grad():
                lg = modelo(input_ids=ids_ps).logits.float().log_softmax(-1)
            alvo = ids_ps[0, n_p:]
            fora.append(sum(lg[0, n_p - 1 + k, t].item() for k, t in enumerate(alvo)))
        return fora

    previstos, t0 = [], time.time()
    for i, it in enumerate(itens, 1):
        p = MOLDE.format(texto=it["texto"])
        lps = logprob([p, p], ROTULOS)
        previstos.append("positivo" if lps[0] >= lps[1] else "negativo")
        if i % 100 == 0 or i == len(itens):
            dt = (time.time() - t0) / 60
            print(f"  {i}/{len(itens)} · {dt:.1f} min · "
                  f"resta ~{dt / i * (len(itens) - i):.1f} min", flush=True)

    print("")
    print("=" * 78)
    print("RESULTADO")
    print("=" * 78)
    r_mod = relatar(f"MODELO {a.model.split('/')[-1][:24]}", itens, previstos)

    delta = 100 * (r_mod["acuracia"] - r_lex["acuracia"])
    print("")
    if delta <= 0:
        print(f"  🔴 O MODELO PERDE PARA O LEXICO por {-delta:.1f} pp.")
        print("     Contar adjetivo de uma lista de 60 palavras e' melhor que rodar o modelo.")
    else:
        print(f"  ✅ o modelo supera o lexico por {delta:+.1f} pp")
    vies = max(r_mod["distribuicao"].values()) / r_mod["n"]
    if vies > 0.80:
        print(f"  ⚠️ VIES FORTE: {100 * vies:.0f}% das respostas sao de uma classe so'. A")
        print("     acuracia aqui e' prior, nao leitura de sentimento — olhe a balanceada.")

    alvo = RAIZ / "docs" / f"sentimento-pt{('-' + a.tag) if a.tag else ''}.json"
    alvo.write_text(json.dumps({"modelo": a.model, "peft": a.peft,
                                "modelo_r": r_mod, "piso_lexico": r_lex,
                                "piso_majoritaria": r_maj},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  relatorio: {alvo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
