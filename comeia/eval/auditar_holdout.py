"""T2 — o teto e' do MODELO ou do BENCHMARK? Auditoria objetiva do holdout agentico.

⭐ POR QUE ESTE SCRIPT EXISTE
  O projeto ja produziu **23,5%** onde o real era **57,6%** porque o avaliador tinha mundo
  fechado — 35 das 85 referencias eram impossiveis por construcao. A refutacao adversarial
  (docs/estudo-bee-350m.md) levantou a mesma suspeita sobre o "teto" de pass@16 = 72,9%:

    "Ninguem mediu quantos dos itens nao resolvidos sao impossiveis. Se ~25% do conjunto for
     insoluvel por construcao, 72,9% e' o teto do BENCHMARK — e nenhum tamanho de modelo move
     teto de benchmark."

⭐ COMO ESTE SCRIPT MEDE, SEM OPINIAO
  Nao le o codigo do executor nem julga "isso parece dificil". Faz dois testes objetivos:

  A) SENSIBILIDADE A TEXTO LITERAL — perturba cada argumento de string do gabarito (troca uma
     palavra) e re-executa. Se o resultado MUDA, aquele item so e' resolvivel reproduzindo o
     texto **ao pe da letra**. Se nao muda, o executor ja e' tolerante (foi o caso do
     send_email, que devolve `tem_corpo: bool` em vez do corpo).

  B) DERIVABILIDADE — para os itens sensiveis, verifica se as palavras de conteudo do argumento
     aparecem no pedido do usuario. Palavra que o gabarito exige e o usuario nunca disse
     (ex.: o ano "2025" numa busca) torna o item **impossivel por construcao**: nenhum modelo,
     de nenhum tamanho, adivinha.

  A intersecao (sensivel E nao-derivavel) e' o teto do BENCHMARK.

Uso:
    python comeia/eval/auditar_holdout.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import read_jsonl  # noqa: E402
import tools_exec as TE  # noqa: E402

_spec = importlib.util.spec_from_file_location("d7", RAIZ / "data" / "07_distill_agentic.py")
_d7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d7)

EVAL = RAIZ / "data" / "processed" / "sft_agentic.eval.jsonl"

# ⭐ VEREDITO HUMANO sobre os itens que o teste (B) marca mas que exigem julgamento.
#    O teste (B) usa um sufixo corrompedor para saber se o argumento "decide" o resultado —
#    e isso da FALSO POSITIVO em ferramenta que compara VALOR e nao TEXTO: em `calculator`,
#    "sqrt(1444)" e "38" batem (medido); appender lixo so gera erro de sintaxe. Idem
#    `run_python`, que devolve apenas {"compila": true}.
#    Cada linha abaixo foi lida a mao. Formato: idx -> (impossivel?, motivo).
VEREDITO_HUMANO: dict[int, tuple[bool, str]] = {
    21:  (False, "run_python: qualquer codigo que compile passa. ⚠️ MAS o 'pedido do usuario' e' "
                 "o META-PROMPT de geracao vazado ('Goal: Generate 15 new...') — dado corrompido"),
    31:  (True,  "write_file: exige reproduzir a letra INTEIRA de 'Imagine' (o executor compara "
                 "bytes). Impossivel — e ⚠️ letra de musica sob copyright dentro do holdout"),
    53:  (False, "calculator compara VALOR: (2+1000)*500/2 == 250500. Derivavel por aritmetica"),
    65:  (True,  "http_get: exige a URL exata do feed RSS da BBC, que o pedido nunca da"),
    68:  (False, "calculator compara VALOR: sqrt(1444) == 38 (medido). Derivavel"),
    89:  (False, "get_stock_price: Petrobras->PETR4 e Bovespa->BVMF sao DERIVACAO de dominio, "
                 "nao confabulacao — a mesma distincao ja registrada na regra de ancoragem"),
    105: (True,  "http_get: exige a URL com percent-encoding exato (Mudan%C3%A7as_clim%C3%A1ticas)"),
    110: (False, "calculator compara VALOR. Derivavel"),
    127: (False, "run_python devolve so {'compila': true}; o random sem semente nao atrapalha"),
}

# palavras funcionais que nao contam para derivabilidade
PARADAS = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para com sem
sobre entre ate e ou que qual quais quando onde como me mim meu minha se ao aos as e' eh esta
este esses essa isso aquilo mais menos muito pouco ja nao sim tem ter ha vai vou quero gostaria
poderia pode favor por favor obrigado""".split())


def _n(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def palavras(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", _n(s)) if w not in PARADAS and len(w) > 1]


def mensagens(row: dict) -> list[dict]:
    if row.get("messages"):
        return row["messages"]
    return list(row.get("prompt") or []) + list(row.get("completion") or [])


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    linhas = [r for r in read_jsonl(EVAL)]
    itens = []

    for i, row in enumerate(linhas):
        if row.get("kind") == "text":
            continue
        usuario = ref = ""
        for m in mensagens(row):
            if m["role"] == "user":
                usuario = m["content"]
            elif m["role"] == "assistant":
                ref = m["content"]
        obj = _d7.extract_json(ref)
        if not obj:
            continue
        ok, base = TE.executar(obj)
        if not ok:
            itens.append({"idx": i, "tool": obj.get("tool"), "status": "GABARITO NAO EXECUTA"})
            continue

        args = obj.get("args") or {}
        literais, nao_derivaveis = [], []
        for k, v in args.items():
            if not isinstance(v, str) or not v.strip():
                continue

            # (A) EXIGE STRING LITERAL? Perturbacao que PRESERVA O SENTIDO: trocar a ordem das
            #     palavras. Se o resultado muda, nem um modelo perfeito passa escrevendo a
            #     mesma coisa com outra ordem — o item mede ortografia, nao capacidade.
            #     ⚠️ So se aplica a TEXTO LIVRE: em URL, caminho e codigo reordenar destroi o
            #     sentido, e ali a exigencia literal e' legitima.
            #     ⚠️ E so em argumento que e' SACOLA DE PALAVRAS por natureza: uma query de
            #     busca com as mesmas palavras em outra ordem e' a MESMA busca. Nome proprio
            #     nao e': reordenar "Rio de Janeiro" da "Janeiro de Rio", que e' outra coisa —
            #     e por isso `city` e `code` ficam de fora (davam falso positivo medido).
            eh_texto_livre = (
                k.lower() in {"query", "q", "search", "termo", "busca"}
                and len(v.split()) >= 3
                and "://" not in v
                and "\n" not in v
            )
            if eh_texto_livre:
                ws = v.split()
                pert = dict(args)
                pert[k] = " ".join(ws[::-1])
                ok2, alt = TE.executar({"tool": obj["tool"], "args": pert})
                if not ok2 or not TE.resultados_batem(alt, base):
                    literais.append(k)

            # (B) DERIVABILIDADE: o gabarito exige palavra que o usuario nunca disse?
            #     Vale para qualquer argumento — inclusive URL e conteudo de arquivo.
            pu = set(palavras(usuario))
            faltando = [w for w in palavras(v) if w not in pu]
            if faltando:
                # so conta se o argumento REALMENTE decide o resultado
                pert = dict(args)
                pert[k] = v + " zzq"
                ok3, alt3 = TE.executar({"tool": obj["tool"], "args": pert})
                decide = (not ok3) or (not TE.resultados_batem(alt3, base))
                if decide:
                    nao_derivaveis.append({"arg": k, "faltando": faltando[:8],
                                           "total_palavras": len(palavras(v))})

        # o veredito humano SOBREPOE o teste (B); (A) e' medicao e nao se sobrepoe
        humano = VEREDITO_HUMANO.get(i)
        if humano is not None and nao_derivaveis:
            nao_derivaveis = nao_derivaveis if humano[0] else []

        itens.append(
            {
                "idx": i,
                "tool": obj.get("tool"),
                "status": "ok",
                "exige_literal": literais,
                "nao_derivavel": nao_derivaveis,
                "veredito_humano": (humano[1] if humano else None),
                "impossivel": bool(literais) or bool(nao_derivaveis),
                "usuario": usuario[:180],
                "ref_args": {k: (v[:120] if isinstance(v, str) else v) for k, v in args.items()},
            }
        )

    n = len(itens)
    quebrados = [x for x in itens if x["status"] != "ok"]
    literais = [x for x in itens if x.get("exige_literal")]
    nao_deriv = [x for x in itens if x.get("nao_derivavel")]
    impossiveis = [x for x in itens if x.get("impossivel")]

    print("=" * 76)
    print(f"AUDITORIA DO HOLDOUT AGENTICO — {n} exemplos tool")
    print("=" * 76)
    print(f"  gabarito nao executa                        {len(quebrados):>3}/{n} = {len(quebrados)/n:6.1%}")
    print(f"  (A) exige a STRING LITERAL (ordem inclusa)  {len(literais):>3}/{n} = {len(literais)/n:6.1%}")
    print(f"  (B) exige info que o usuario NUNCA deu      {len(nao_deriv):>3}/{n} = {len(nao_deriv)/n:6.1%}")
    print(f"  ⚠️  IMPOSSIVEL POR CONSTRUCAO (A ou B)       {len(impossiveis):>3}/{n} = {len(impossiveis)/n:6.1%}")

    por_tool: dict[str, list[int]] = {}
    for x in itens:
        por_tool.setdefault(x["tool"] or "?", [0, 0])
        por_tool[x["tool"]][0] += 1
        if x.get("impossivel"):
            por_tool[x["tool"]][1] += 1
    print("\n  por ferramenta (impossiveis / total):")
    for t, (tot, imp) in sorted(por_tool.items(), key=lambda kv: -kv[1][1]):
        marca = " ⚠️" if imp else ""
        print(f"    {t:<22} {imp:>2}/{tot:<3}{marca}")

    print("\n  exemplos do que o gabarito exige e o usuario nunca disse:")
    for x in impossiveis[:8]:
        for nd in x["nao_derivavel"][:1]:
            print(f"    [{x['tool']}] pedido: {x['usuario'][:70]}")
            print(f"       exige em '{nd['arg']}' as palavras: {nd['faltando']}")

    teto = 1 - len(impossiveis) / n
    print("\n" + "=" * 76)
    print(f"TETO MAXIMO ALCANCAVEL POR QUALQUER MODELO NESTE HOLDOUT: {teto:.1%}")
    print("=" * 76)
    print("Comparar com o pass@k medido. Se o pass@k bater neste numero, o 'teto' e' do")
    print("BENCHMARK e nenhum tamanho de modelo o move — so consertar o holdout move.")

    dest = Path(__file__).resolve().parent / "results" / "auditoria_holdout.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(
        json.dumps(
            {"exemplos": n, "gabarito_quebrado": len(quebrados), "exige_literal": len(literais), "nao_derivavel": len(nao_deriv),
             "impossiveis": len(impossiveis), "teto_do_benchmark": round(teto, 4),
             "por_ferramenta": {t: {"total": v[0], "impossiveis": v[1]} for t, v in por_tool.items()},
             "itens": itens},
            ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"\nrelatorio: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
