"""Preenche a fala do assistente nos negativos de masking — com teacher, não com template.

🔴 POR QUE NÃO TEMPLATE. A métrica `over_call` só olha se houve chamada. Uma frase fixa
("Desculpe, não posso fazer isso") faria o número ficar ótimo enquanto o modelo decora uma
frase — bom número, comportamento degenerado. O projeto já tem o hábito de desconfiar de
métrica que melhora sem o comportamento melhorar.

⭐ E a recusa BOA não é só recusa. Medido ao vivo nos dois teachers:

    gpt-oss-20b : "Desculpe, mas com as ferramentas disponíveis não consigo gerar um código QR."
    nemotron    : "Não consigo gerar códigos QR com as ferramentas que tenho. **Posso ajudar a
                   verificar o status do seu site ou analisar o tráfego dele**, se isso for útil."

A segunda ensina recusar **e oferecer o que existe no catálogo** — que é o comportamento que
se quer em produção. Por isso o prompt pede exatamente isso.

⚠️ DOIS TEACHERS, ALTERNANDO. Um único gerador imprime o estilo dele no dataset inteiro, e
esse viés vira propriedade do modelo treinado. Alternar não elimina o viés, mas o divide — e o
relatório mede a diversidade em vez de supô-la.

⚠️ Licenças verificadas na origem: `nemotron-3-ultra` (NVIDIA-open, ToS permite destilar,
verificado 2026-08-02) e `gpt-oss-20b` (Apache-2.0). Ver a memória do projeto sobre a
diferença entre licença de pesos e ToS de API.

Uso:
    python comeia/data/gerar_recusas_teacher.py --limite 40 --amostra
    python comeia/data/gerar_recusas_teacher.py --limite 2000
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
ENTRADA = RAIZ / "comeia" / "data" / "processed" / "negativos_masking.jsonl"
SAIDA = RAIZ / "comeia" / "data" / "processed" / "negativos_com_recusa.jsonl"

TEACHERS = ["nvidia/nemotron-3-ultra-550b-a55b:free", "openai/gpt-oss-20b:free"]
RX_FERR = re.compile(r"^- ([a-zA-Z0-9_]+):", re.M)
RX_CHAMADA = re.compile(r'\{\s*"tool"|<tool_call>|"arguments"\s*:')
# marcas de portugues; ausencia total = provavelmente o teacher respondeu em ingles
RX_PT = re.compile(r"\b(não|nao|com|para|que|você|voce|posso|consigo|ferramenta)\b", re.I)

MOLDE = """Um assistente tem acesso APENAS a estas ferramentas:
{catalogo}

O usuário pediu: "{pedido}"

Nenhuma das ferramentas acima atende esse pedido. Escreva a resposta do assistente em
português brasileiro natural, em 1 a 2 frases:
- diga que não consegue fazer isso com as ferramentas que tem;
- se alguma ferramenta da lista for minimamente útil ao usuário, ofereça-a pelo nome;
- NÃO invente ferramenta que não esteja na lista;
- NÃO escreva JSON nem chamada de função.

Responda SÓ com a fala do assistente, sem aspas e sem comentário."""


def chave_openrouter() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if k:
        return k
    env = RAIZ / ".env"
    if env.exists():
        for l in env.read_text(encoding="utf-8").splitlines():
            if l.startswith("OPENROUTER_API_KEY="):
                return l.split("=", 1)[1].strip()
    return ""


def catalogo_curto(system: str) -> str:
    """Só as linhas `- nome: descrição` — o teacher não precisa dos argumentos."""
    return "\n".join(l for l in system.splitlines() if l.startswith("- "))


def valida(texto: str, nomes: set[str], removida: str) -> str | None:
    """`None` = aceita. String = motivo da rejeição.

    ⚠️ A guarda mais importante é a última: se o teacher citar a ferramenta que foi REMOVIDA,
    ele escreveu uma recusa que se contradiz — e o exemplo ensinaria que a ferramenta existe.
    """
    t = texto.strip()
    if not t:
        return "vazio"
    if RX_CHAMADA.search(t):
        return "contem_chamada"
    if not RX_PT.search(t):
        return "provavelmente_nao_e_portugues"
    # ⚠️ 400 rejeitava 15% no piloto, e recusa util de 3 frases e' legitima. Rejeitar
    #    resposta boa desperdica chamada num free tier limitado por minuto.
    if len(t) > 520:
        return "longo_demais"
    if re.search(rf"\b{re.escape(removida)}\b", t):
        return "citou_a_ferramenta_removida"
    citadas = set(re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", t))
    if citadas - nomes:
        return f"citou_ferramenta_inexistente:{sorted(citadas - nomes)[:2]}"
    return None


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ENTRADA)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    ap.add_argument("--limite", type=int, default=0, help="0 = todos")
    ap.add_argument("--temp", type=float, default=0.9)
    ap.add_argument("--pausa", type=float, default=1.0, help="segundos entre chamadas")
    ap.add_argument("--amostra", action="store_true")
    a = ap.parse_args()

    from teacher_api import call_teacher

    k = chave_openrouter()
    if not k:
        print("🔴 OPENROUTER_API_KEY nao encontrada (ambiente nem .env)", file=sys.stderr)
        return 1

    linhas = [json.loads(l) for l in a.entrada.read_text(encoding="utf-8").splitlines()]
    # ⭐ RETOMADA: o free tier e' limitado por minuto, e este job leva horas. Reprocessar o
    #    que ja' foi feito seria desperdicio E mudaria as recusas ja' aceitas.
    feitos = set()
    if a.saida.exists():
        for l in a.saida.read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            feitos.add(d["messages"][1]["content"] + "|" + d["ferramenta_removida"])
        print(f"retomando: {len(feitos):,} ja' gravados")
    pendentes = [d for d in linhas
                 if d["messages"][1]["content"] + "|" + d["ferramenta_removida"] not in feitos]
    if a.limite:
        pendentes = pendentes[:a.limite]

    print("=" * 78)
    print(f"RECUSAS POR TEACHER — {len(pendentes):,} pendentes de {len(linhas):,}")
    print(f"teachers: {TEACHERS}")
    print("=" * 78)

    motivos, aceitos, t0 = Counter(), [], time.time()
    saida_f = None if a.amostra else a.saida.open("a", encoding="utf-8")
    try:
        for i, d in enumerate(pendentes):
            sistema = d["messages"][0]["content"]
            nomes = set(RX_FERR.findall(sistema))
            prompt = MOLDE.format(catalogo=catalogo_curto(sistema),
                                  pedido=d["messages"][1]["content"])
            teacher = TEACHERS[i % len(TEACHERS)]
            try:
                r = call_teacher(prompt, teacher, k, temperature=a.temp,
                                 max_tokens=200, timeout=120)
            except Exception as e:
                motivos[f"erro_api:{type(e).__name__}"] += 1
                if "429" in str(e):
                    time.sleep(8)
                continue
            motivo = valida(r, nomes, d["ferramenta_removida"])
            if motivo:
                motivos[motivo] += 1
                continue
            reg = dict(d)
            reg["messages"] = [d["messages"][0], d["messages"][1],
                               {"role": "assistant", "content": r.strip()}]
            reg["teacher"] = teacher
            motivos["aceito"] += 1
            aceitos.append(reg)
            if saida_f:
                saida_f.write(json.dumps(reg, ensure_ascii=False) + "\n")
                saida_f.flush()
            if (i + 1) % 25 == 0:
                dt = (time.time() - t0) / 60
                print(f"  {i+1}/{len(pendentes)} · aceitos {motivos['aceito']} · "
                      f"{dt:.1f} min · resta ~{dt/(i+1)*(len(pendentes)-i-1):.0f} min",
                      flush=True)
            time.sleep(a.pausa)
    except KeyboardInterrupt:
        print("\n(interrompido — o que foi gravado esta' salvo e a retomada continua daqui)")
    finally:
        if saida_f:
            saida_f.close()

    print(f"\nresultado ({sum(motivos.values())} tentativas):")
    for m, c in motivos.most_common():
        print(f"  {'✅' if m == 'aceito' else '  '} {m:40} {c:>6,}")

    if aceitos:
        # ⭐ DIVERSIDADE MEDIDA. Se as recusas convergirem para a mesma abertura, o efeito e' o
        #    do template que este arquivo existe para evitar — so' que caro.
        aberturas = Counter(" ".join(r["messages"][2]["content"].split()[:4]).lower()
                            for r in aceitos)
        vocab = set()
        total_tok = 0
        for r in aceitos:
            ws = r["messages"][2]["content"].lower().split()
            vocab.update(ws)
            total_tok += len(ws)
        print(f"\ndiversidade ({len(aceitos)} recusas):")
        print(f"  aberturas distintas : {len(aberturas)}/{len(aceitos)} "
              f"({100*len(aberturas)/len(aceitos):.0f}%)")
        print(f"  vocabulario         : {len(vocab):,} tipos / {total_tok:,} tokens "
              f"(TTR {len(vocab)/max(1,total_tok):.3f})")
        mais = aberturas.most_common(1)[0]
        print(f"  abertura mais comum : {mais[1]}x  {mais[0]!r}")
        if mais[1] / len(aceitos) > 0.3:
            print("  🔴 mais de 30% comecam igual — esta' virando template com custo de API")
        for r in aceitos[:3] if a.amostra else []:
            print(f"\n  removida {r['ferramenta_removida']} ({r['teacher'].split('/')[-1]})")
            print(f"    pedido: {r['messages'][1]['content'][:110]}")
            print(f"    recusa: {r['messages'][2]['content'][:230]}")
    if not a.amostra:
        print(f"\n✅ {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
