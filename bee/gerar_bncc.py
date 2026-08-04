"""Gera material de ensino em PT-BR a partir das habilidades da BNCC.

⭐ POR QUE A BNCC E NAO OS LIVROS DO ACERVO
  A BNCC e o Anexo da Resolucao CNE/CP 2/2017 — ato normativo federal. Pela Lei
  9.610/98 art. 8, IV ("leis, decretos, regulamentos... e demais atos oficiais"),
  esta FORA do regime autoral: nao ha direito a licenciar. Os 91 PDFs do acervo
  sao protegidos, e 11 deles sequer tem camada de texto.
  Ver docs/estudo-curriculo/00-CONSOLIDADO.md.

⚠️ A BNCC descreve O QUE ensinar, nunca EXPLICA o conteudo — nao ha nela um
  paragrafo sobre mitose. Ela vale 100% como INDICE, 0% como prosa. Por isso a
  habilidade entra como SEMENTE e o professor aberto escreve o texto.

FORMATOS (o porque de cada um):
  explicacao  -> prosa expositiva. E o que faltou no v3: o SFT passou no gate de
                 FORMA e falhou no de CONTEUDO.
  qa          -> par instrucao/resposta curto, o formato que o SFT consome.
  distrator   -> resposta certa + por que 3 alternativas erradas erram. De um item
                 sai 1 par de SFT e 3 negativos de DPO de graca.

Uso:
    python bee/gerar_bncc.py --dry-run              # mostra prompts, nao chama a API
    python bee/gerar_bncc.py --n 300 --paralelo 8
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "comeia" / "data"))

HABILIDADES = ROOT / "bee" / "bncc" / "habilidades.jsonl"
SAIDA = ROOT / "comeia" / "data" / "processed" / "sft_bncc.jsonl"

# Componentes que rendem TEXTO PURO. Educacao Fisica (EF), Arte (AR) e Ensino
# Religioso (ER) ficam de fora: sao praticos/visuais ou de carga confessional —
# ver o alerta de viés em docs/estudo-curriculo/00-CONSOLIDADO.md.
COMPONENTES_OK = {"LP", "MA", "HI", "GE", "CI", "LI", "MAT", "CHS", "CNT", "LGG"}

SISTEMA = (
    "Voce e um professor brasileiro experiente escrevendo material didatico em portugues "
    "do Brasil. Escreve com clareza, frases diretas e exemplos concretos do cotidiano "
    "brasileiro. Nunca inventa dado, numero ou citacao: se nao tem certeza de um fato, "
    "escreve sobre o conceito sem afirmar o numero. Nao usa markdown, cabecalho, lista "
    "com marcador nem emoji — apenas paragrafos de texto corrido."
)

MOLDES = {
    "explicacao": (
        "Habilidade da BNCC ({codigo}), etapa {etapa}:\n\"{descricao}\"\n\n"
        "Escreva uma explicacao didatica de 3 a 4 paragrafos sobre o conteudo que essa "
        "habilidade exige, para um aluno que esta vendo o assunto pela primeira vez.\n"
        "Estrutura: comece pelo caso concreto, depois generalize, depois de o contraexemplo "
        "que costuma confundir, e termine com uma regra pratica curta para lembrar.\n"
        "Nao mencione a BNCC, nem o codigo, nem a palavra 'habilidade'. Escreva como se "
        "fosse um trecho de livro didatico."
    ),
    "qa": (
        "Habilidade da BNCC ({codigo}), etapa {etapa}:\n\"{descricao}\"\n\n"
        "Crie UMA pergunta que um aluno faria sobre esse conteudo, e a resposta.\n"
        "A pergunta deve ser curta e natural (como alguem pergunta de verdade, nao como "
        "enunciado de prova). A resposta deve ter 1 a 2 paragrafos, ser completa e terminar "
        "de forma conclusiva.\n"
        "Responda EXATAMENTE neste formato, sem mais nada:\n"
        "PERGUNTA: <a pergunta>\nRESPOSTA: <a resposta>"
    ),
    "distrator": (
        "Habilidade da BNCC ({codigo}), etapa {etapa}:\n\"{descricao}\"\n\n"
        "Crie uma pergunta objetiva sobre esse conteudo, a resposta correta explicada, e "
        "TRES respostas erradas — cada uma com a explicacao de por que erra.\n"
        "Os erros devem ser os que alunos cometem de verdade (confusao de conceitos "
        "parecidos, regra generalizada demais, troca de causa por consequencia), nunca "
        "absurdos obvios.\n"
        "Responda EXATAMENTE neste formato, sem mais nada:\n"
        "PERGUNTA: <pergunta>\nCERTA: <resposta correta explicada>\n"
        "ERRADA1: <resposta errada> || <por que erra>\n"
        "ERRADA2: <resposta errada> || <por que erra>\n"
        "ERRADA3: <resposta errada> || <por que erra>"
    ),
}


def etapa_de(codigo: str) -> str:
    if codigo.startswith("EI"):
        return "Educacao Infantil"
    if codigo.startswith("EM"):
        return "Ensino Medio"
    m = re.match(r"EF(\d{2})", codigo)
    return f"{int(m.group(1))}o ano do Ensino Fundamental" if m else "Ensino Fundamental"


def componente_de(codigo: str) -> str:
    if codigo.startswith("EM13"):
        return re.sub(r"\d.*$", "", codigo[4:]) or "?"
    return codigo[4:6]


def carregar_habilidades() -> list[dict]:
    if not HABILIDADES.exists():
        print(f"ERRO: rode a extracao da BNCC antes — falta {HABILIDADES}", file=sys.stderr)
        sys.exit(1)
    out = []
    for linha in HABILIDADES.open(encoding="utf-8"):
        h = json.loads(linha)
        comp = componente_de(h["codigo"])
        if comp not in COMPONENTES_OK:
            continue
        if len(h["descricao"]) < 40:  # descricao truncada na extracao
            continue
        h["componente"], h["etapa"] = comp, etapa_de(h["codigo"])
        out.append(h)
    return out


# ⚠️ O professor tende a falar da ESCOLA em vez de ensinar o CONTEUDO — no piloto
# saiu "Essa habilidade da BNCC nao cobra que voce fale perfeito". Isso ensinaria o
# Bee a comentar curriculo, nao a saber a materia. Rejeitar em TODOS os formatos.
META = re.compile(r"\bBNCC\b|essa habilidade|esta habilidade|nesta habilidade|"
                  r"a habilidade (exige|pede|cobra|valoriza)|em sala de aula|"
                  r"o professor prop|nesta atividade|nesta etapa de ensino", re.I)
# Vazamento de raciocinio de modelo reasoning (o texto vem em ingles, na 1a pessoa).
RACIOCINIO = re.compile(r"^\s*(We need|Let me|The user|I should|First,|Okay,|Alright)", re.I)


def limpo(texto: str) -> bool:
    return not META.search(texto) and not RACIOCINIO.match(texto)


def parse_qa(txt: str) -> list[dict] | None:
    m = re.search(r"PERGUNTA:\s*(.+?)\s*RESPOSTA:\s*(.+)", txt, re.S)
    if not m:
        return None
    p, r = " ".join(m.group(1).split()), m.group(2).strip()
    if len(p) < 10 or len(r) < 60 or not limpo(r) or not limpo(p):
        return None
    return [{"messages": [{"role": "user", "content": p},
                          {"role": "assistant", "content": r}]}]


def parse_distrator(txt: str) -> list[dict] | None:
    m = re.search(r"PERGUNTA:\s*(.+?)\s*CERTA:\s*(.+?)\s*ERRADA1:", txt, re.S)
    if not m:
        return None
    p, certa = " ".join(m.group(1).split()), m.group(2).strip()
    if len(p) < 10 or len(certa) < 40 or not limpo(certa) or not limpo(p):
        return None
    reg = {"messages": [{"role": "user", "content": p},
                        {"role": "assistant", "content": certa}]}
    rej = [x.split("||")[0].strip()
           for x in re.findall(r"ERRADA\d:\s*(.+?)(?=\s*ERRADA\d:|$)", txt, re.S)]
    reg["rejeitadas"] = [r for r in rej if len(r) > 15]  # negativos p/ DPO futuro
    return [reg]


def parse_explicacao(txt: str, hab: dict) -> list[dict] | None:
    t = txt.strip()
    if len(t) < 300 or t.count("\n\n") < 1:
        return None
    if not limpo(t):
        return None  # vazou a instrucao/raciocinio para dentro do texto
    pedido = (f"Explique, como um professor explicaria a quem esta vendo pela primeira vez: "
              f"{hab['descricao'][:180]}")
    return [{"messages": [{"role": "user", "content": pedido},
                          {"role": "assistant", "content": t}]}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="quantas habilidades sortear")
    # Holdout honesto: mesma semente, fatia DISJUNTA — as habilidades usadas no
    # treino (as `--pular` primeiras do sorteio) nunca reaparecem aqui.
    ap.add_argument("--pular", type=int, default=0,
                    help="pula as N primeiras do sorteio, para gerar holdout")
    ap.add_argument("--formatos", default="explicacao,qa,distrator")
    ap.add_argument("--professor", default="deepseek/deepseek-v3.2",
                    help="NAO usar modelo de reasoning: vaza o raciocinio no texto")
    ap.add_argument("--paralelo", type=int, default=8)
    ap.add_argument("--out", type=Path, default=SAIDA)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from config import assert_teacher_allowed
    assert_teacher_allowed(args.professor)  # nao destilar de modelo fechado

    habs = carregar_habilidades()
    formatos = [f.strip() for f in args.formatos.split(",")]
    rng = random.Random(42)
    rng.shuffle(habs)
    alvo = habs[args.pular : args.pular + args.n]

    import collections
    print("=" * 62)
    print("Gerador BNCC -> material didatico PT-BR")
    print("=" * 62)
    print(f"  habilidades elegiveis : {len(habs)} (de {sum(1 for _ in HABILIDADES.open(encoding='utf-8'))})")
    print(f"  sorteadas             : {len(alvo)} (pulando as {args.pular} primeiras)")
    print(f"  formatos              : {formatos}")
    print(f"  itens a gerar         : {len(alvo) * len(formatos)}")
    print(f"  professor             : {args.professor}")
    print(f"  componentes           : {dict(collections.Counter(h['componente'] for h in alvo).most_common())}")

    if args.dry_run:
        h = alvo[0]
        print(f"\n--- exemplo de prompt ({h['codigo']}, {h['etapa']}) ---")
        print(MOLDES["qa"].format(codigo=h["codigo"], etapa=h["etapa"],
                                  descricao=h["descricao"])[:700])
        return 0

    chave = os.environ.get("OPENROUTER_API_KEY")
    if not chave:
        for linha in (ROOT / ".env").open(encoding="utf-8"):
            if linha.startswith("OPENROUTER_API_KEY="):
                chave = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not chave:
        print("ERRO: OPENROUTER_API_KEY ausente (.env ou ambiente)", file=sys.stderr)
        return 1

    from teacher_api import TeacherError, call_teacher

    trava = threading.Lock()
    estado = {"ok": 0, "falha": 0, "descartado": 0}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    saida = args.out.open("w", encoding="utf-8")

    def tarefa(par):
        hab, fmt = par
        prompt = MOLDES[fmt].format(codigo=hab["codigo"], etapa=hab["etapa"],
                                    descricao=hab["descricao"])
        try:
            txt = call_teacher(prompt, args.professor, chave, system=SISTEMA,
                               temperature=0.8, max_tokens=1200)
        except Exception as e:
            with trava:
                estado["falha"] += 1
                if estado["falha"] <= 3:
                    print(f"  falha ({hab['codigo']}/{fmt}): {str(e)[:110]}")
            return
        regs = (parse_explicacao(txt, hab) if fmt == "explicacao" else
                parse_qa(txt) if fmt == "qa" else parse_distrator(txt))
        with trava:
            if not regs:
                estado["descartado"] += 1
                return
            for r in regs:
                r.update(fonte="bncc", codigo=hab["codigo"],
                         componente=hab["componente"], formato=fmt)
                saida.write(json.dumps(r, ensure_ascii=False) + "\n")
            estado["ok"] += len(regs)
            n = estado["ok"] + estado["falha"] + estado["descartado"]
            if n % 25 == 0:
                print(f"  {n}/{len(alvo)*len(formatos)} · ok {estado['ok']} · "
                      f"descartado {estado['descartado']} · falha {estado['falha']}", flush=True)

    pares = [(h, f) for h in alvo for f in formatos]
    print(f"\ngerando {len(pares)} itens com {args.paralelo} threads...\n")
    with ThreadPoolExecutor(max_workers=args.paralelo) as ex:
        list(ex.map(tarefa, pares))
    saida.close()

    print(f"\n[OK] {estado['ok']} exemplos em {args.out}")
    print(f"     descartados no controle de qualidade: {estado['descartado']} · "
          f"falhas de API: {estado['falha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
