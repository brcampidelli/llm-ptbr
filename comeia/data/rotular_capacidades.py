"""Rotula cada exemplo do SFT por capacidade — o que o censo por arquivo não conseguia dar.

⭐ POR QUE FALTAVA, E POR QUE O E2 NÃO ANDA SEM ISTO

O `censo_tokens.py` mede a mistura **por arquivo**: quantos tokens vêm de `sft_agentic.jsonl`,
de `sft_bncc.jsonl`, etc. Isso respondeu a pergunta que ele existia para responder (o agêntico
recebe 2,7% do gradiente, não 20,9%) e não responde a próxima: o braço (b) do Estágio 2 propõe
**três adapters por afinidade** — TEXTO, FERRAMENTA e SIMBÓLICO — e para separar o
`sft_misto.jsonl` em três é preciso um rótulo **por exemplo**. O arquivo misto carrega só
`source` (`distill` ou `?`) e um `kind` presente em 1.495 dos 7.152.

⚠️ O ROTULADOR É HEURÍSTICO, E ISSO IMPORTA MENOS DO QUE PARECE. O rótulo aqui **não pontua
   nada**: ele decide em qual adapter cada exemplo entra. Erro de rotulagem custa pureza de
   mistura, não validade de medição — que é uma falha muito mais barata que a de um avaliador
   errado. Ainda assim, três coisas ficam obrigatórias:

   1. **nada de rótulo silencioso**: todo exemplo que não casa com regra nenhuma cai em
      `indefinido` e o total aparece no relatório. Um rotulador que classifica 100% é suspeito,
      não bom;
   2. **amostra auditável**: `--amostra N` imprime N exemplos por rótulo, para conferência a
      olho. Regra que ninguém leu é regra que ninguém validou;
   3. **contagem por TOKEN DE COMPLETION**, não por exemplo — é a fração de gradiente que cada
      capacidade recebe de fato, e foi ignorá-la que produziu o erro dos 2,7% × 20,9%.

Uso:
    python comeia/data/rotular_capacidades.py                      # relatorio
    python comeia/data/rotular_capacidades.py --amostra 3          # + exemplos por rotulo
    python comeia/data/rotular_capacidades.py --escrever           # grava os 3 arquivos
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
PROC = RAIZ / "comeia" / "data" / "processed"
ENTRADA = PROC / "sft_misto.jsonl"

# ---------------------------------------------------------------- afinidades do braço (b)
AFINIDADE = {
    "ferramenta": {"tool_call", "multiturno_ferramenta", "ferramenta_negativo"},
    "simbolico": {"codigo", "aritmetica"},
    "texto": {"resumo", "traducao", "sentimento", "atendimento", "conteudo", "educacional"},
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def partes(reg: dict) -> tuple[list[dict], str, str]:
    """(mensagens, texto do prompt, texto da completion) nos dois formatos do projeto."""
    if "messages" in reg:
        msgs = reg["messages"]
        prompt = " ".join(m.get("content", "") for m in msgs if m.get("role") != "assistant")
        compl = " ".join(m.get("content", "") for m in msgs if m.get("role") == "assistant")
    else:
        p, c = reg.get("prompt", []), reg.get("completion", [])
        msgs = (p if isinstance(p, list) else []) + (c if isinstance(c, list) else [])
        prompt = " ".join(m.get("content", "") for m in p) if isinstance(p, list) else str(p)
        compl = " ".join(m.get("content", "") for m in c) if isinstance(c, list) else str(c)
    return msgs, prompt, compl


_CODIGO = re.compile(r"```(?:python|py|js|java|sql)|^\s*def \w+\(|\bimport \w+", re.M)
# ⚠️ A PRIMEIRA VERSAO SO' PEDIA `calcule` solto, ou um `x` entre digitos, e engolia prompt de
#    categoria como "SQL (otimizacao, correcao de queries)". Agora o verbo de calculo exige um
#    NUMERO por perto: aritmetica sem numero nao existe, e texto com verbo de calculo existe
#    aos montes.
_ARITMETICA = re.compile(
    r"\d[\d.,]*\s*[+*/×÷]\s*\d"
    r"|\bquanto (?:e|da|fica|sera|custa|sobra)\b[^.]{0,40}\d"
    r"|\bcalcul[ea]\w*\b[^.]{0,40}\d"
    r"|\d[\d.,]*\s*(?:%|por cento)"
    r"|\bdesconto de\b[^.]{0,20}\d")


def rotular(reg: dict) -> str:
    """Um rótulo por exemplo. `indefinido` é resposta legítima e vai contada.

    🔴 O CAMPO `kind` MANDA QUANDO EXISTE, E A DESCOBERTA QUE ISSO TROUXE VALE MAIS QUE O
    ROTULADOR INTEIRO. Conferindo a heurística contra os 1.495 registros que trazem `kind`:

        kind=tool_call → rotulo=tool_call ....... 886/886   (100%, a heuristica acerta)
        kind=text      → rotulo=aritmetica ...... 603/609   (a heuristica erra o GRUPO)

    Os `kind="text"` vêm da destilação agêntica e são os exemplos em que a resposta certa é
    **não chamar ferramenta nenhuma**. A heurística os manda para SIMBÓLICO porque são
    aritméticos na superfície — e o efeito disso no braço (b) do E2 seria treinar o adapter
    FERRAMENTA **só com exemplos positivos**, que é a receita exata do over-calling. Este
    projeto já mediu over-calling de 23,1% e gastou uma política determinística para levá-lo
    a 13,8%; reproduzi-lo por um erro de rotulagem seria pagar duas vezes.

    Por isso `kind` presente ⇒ origem agêntica ⇒ grupo FERRAMENTA, positivo ou negativo.
    """
    msgs, prompt, compl = partes(reg)
    p, c = _norm(prompt), _norm(compl)
    tem_tool = any(m.get("role") == "tool" for m in msgs)

    if reg.get("kind") == "tool_call":
        return "multiturno_ferramenta" if tem_tool else "tool_call"
    if reg.get("kind") == "text":
        return "ferramenta_negativo"

    # 1) FERRAMENTA — a assinatura e' a chamada JSON na resposta, nao a palavra "ferramenta"
    if compl.strip().startswith("{") and '"tool"' in compl:
        return "multiturno_ferramenta" if tem_tool else "tool_call"
    if tem_tool:
        return "multiturno_ferramenta"

    # 2) SIMBOLICO — codigo antes de aritmetica: um exercicio de codigo costuma ter numero,
    #    mas um exercicio de aritmetica raramente tem `def`
    if _CODIGO.search(compl) or _CODIGO.search(prompt):
        return "codigo"
    if _ARITMETICA.search(p) or _ARITMETICA.search(c):
        return "aritmetica"

    # 3) TEXTO — por pedido explicito no prompt, do mais especifico para o mais generico
    for chave, rotulo in (
        ("traduz", "traducao"), ("em ingles", "traducao"), ("para o ingles", "traducao"),
        ("resum", "resumo"), ("sintetiz", "resumo"), ("em poucas palavras", "resumo"),
        ("sentimento", "sentimento"), ("positivo ou negativo", "sentimento"),
        ("cliente", "atendimento"), ("pedido", "atendimento"), ("reembolso", "atendimento"),
        ("explique", "educacional"), ("professor", "educacional"), ("aluno", "educacional"),
    ):
        if chave in p:
            return rotulo
    if len(compl.split()) >= 25:
        return "conteudo"
    return "indefinido"


def grupo(rotulo: str) -> str:
    for g, membros in AFINIDADE.items():
        if rotulo in membros:
            return g
    return "indefinido"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ENTRADA)
    ap.add_argument("--tokenizer", default=str(RAIZ / "models" / "bee-150m-v3-base"),
                    help="mesmo default do censo_tokens.py, para os numeros baterem")
    ap.add_argument("--amostra", type=int, default=0)
    ap.add_argument("--escrever", action="store_true",
                    help="grava sft_grupo_{texto,ferramenta,simbolico}.jsonl")
    a = ap.parse_args()

    regs = [json.loads(l) for l in a.entrada.read_text(encoding="utf-8").split(chr(10))
            if l.strip()]

    # `tokenizers` em vez de `transformers`: contar token nao precisa de torch (mesma escolha
    # do censo_tokens.py). O caminho e' o mesmo que o censo usa, para os dois numeros serem
    # comparaveis — contar com tokenizadores diferentes daria percentuais que nao batem e
    # ninguem saberia por que.
    from tokenizers import Tokenizer
    cam = Path(a.tokenizer) / "tokenizer.json"
    tok = Tokenizer.from_file(str(cam)) if cam.exists() else None
    if tok is None:
        print(f"🔴 {cam} nao encontrado — a contagem sairia em PALAVRAS e NAO seria")
        print("   comparavel com o censo_tokens.py. Passe --tokenizer para o diretorio certo.")
        return 1

    def n_tok(s: str) -> int:
        return len(tok.encode(s).ids) if tok else len(s.split())

    por_rotulo, tok_compl, exemplos = Counter(), Counter(), {}
    for r in regs:
        rot = rotular(r)
        _, _, compl = partes(r)
        por_rotulo[rot] += 1
        tok_compl[rot] += n_tok(compl)
        exemplos.setdefault(rot, []).append(r)

    total_tok = sum(tok_compl.values())
    print("=" * 78)
    print(f"ROTULAGEM POR CAPACIDADE — {a.entrada.name} · {len(regs)} exemplos")
    print("=" * 78)
    print(f"{'rotulo':26} {'grupo':12} {'exemplos':>9} {'% ex':>6} "
          f"{'tok compl.':>11} {'% GRADIENTE':>12}")
    print("-" * 78)
    for rot, n in por_rotulo.most_common():
        print(f"{rot:26} {grupo(rot):12} {n:>9,} {100 * n / len(regs):>5.1f}% "
              f"{tok_compl[rot]:>11,} {100 * tok_compl[rot] / total_tok:>11.1f}%")

    print("-" * 78)
    g_ex, g_tok = Counter(), Counter()
    for rot, n in por_rotulo.items():
        g_ex[grupo(rot)] += n
        g_tok[grupo(rot)] += tok_compl[rot]
    for g in ("texto", "ferramenta", "simbolico", "indefinido"):
        if g_ex[g]:
            print(f"{'GRUPO ' + g:26} {'':12} {g_ex[g]:>9,} {100 * g_ex[g] / len(regs):>5.1f}% "
                  f"{g_tok[g]:>11,} {100 * g_tok[g] / total_tok:>11.1f}%")

    ind = por_rotulo["indefinido"]
    print("")
    if ind:
        print(f"⚠️ {ind} exemplo(s) ficaram INDEFINIDOS ({100 * ind / len(regs):.1f}%). "
              f"Isso e' honestidade do rotulador, nao defeito:")
        print("   regra que classifica 100% e' regra que esta' chutando em algum lugar.")
    else:
        print("⚠️ ZERO indefinidos — desconfie. Um rotulador heuristico que classifica tudo")
        print("   provavelmente tem uma regra final generica engolindo os casos dificeis.")

    if a.amostra:
        print("\n" + "=" * 78)
        print(f"AMOSTRA PARA CONFERENCIA A OLHO ({a.amostra} por rotulo)")
        print("=" * 78)
        print("⚠️ Regra que ninguem leu e' regra que ninguem validou.")
        for rot in sorted(exemplos):
            print(f"\n--- {rot} ({grupo(rot)})")
            for r in exemplos[rot][:a.amostra]:
                _, p, c = partes(r)
                print(f"   P: {p.strip()[:110]!r}")
                print(f"   C: {c.strip()[:110]!r}")

    if a.escrever:
        print("")
        for g in ("texto", "ferramenta", "simbolico"):
            alvo = PROC / f"sft_grupo_{g}.jsonl"
            linhas = [r for r in regs if grupo(rotular(r)) == g]
            with alvo.open("w", encoding="utf-8") as f:
                for r in linhas:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  ✅ {alvo.name}: {len(linhas):,} exemplos")
        # 🔴 os indefinidos NAO sao distribuidos "no maior grupo": some dado de um lado e
        #    aparece do outro sem que nada reclame — a familia de erro mais cara do projeto.
        print(f"  ⚠️ os {ind} indefinidos NAO entraram em nenhum grupo. Somados, os tres "
              f"arquivos tem {sum(1 for r in regs if grupo(rotular(r)) != 'indefinido'):,} "
              f"de {len(regs):,}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
