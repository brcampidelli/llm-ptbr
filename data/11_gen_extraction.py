"""Fase 2 (dados) — Gerar pares (documento, extração) VERIFICÁVEIS para a abelha de extração.

⭐ A VALIDAÇÃO QUE FAZ ESTE DADO SER LIMPO — auto-consistência do professor:
o professor escreve o DOCUMENTO e a EXTRAÇÃO. Só guardamos o item se a extração
dele passar no NOSSO validador (`schema_check.avaliar`), que checa duas coisas
independentes:
  1. conformidade — obrigatórios presentes, tipos certos, enum no domínio,
     nenhum campo inventado;
  2. groundedness — todo valor `grounded` APARECE no documento.
Nenhum juiz LLM. Se o professor alucinar um valor que não está no próprio texto
que ele acabou de escrever, o item é descartado — e isso acontece bastante.

DOIS PONTOS DE DESENHO que vêm de erro caro cometido antes neste projeto:

⚠️ CASOS COM CAMPO AUSENTE (`--frac-ausente`, default 0,35). Se todo documento
contiver todos os campos, a abelha aprende a SEMPRE preencher tudo — e passa a
inventar em produção quando o campo não existe. É o mesmo raciocínio dos 41% de
"não precisa de ferramenta" da agêntica: o dado precisa ensinar a NÃO agir.
Aqui o comportamento a ensinar é **omitir a chave**.

⚠️ MULTILÍNGUE POR CONSTRUÇÃO (pt/en/es/fr, rodízio). A `chat_ptbr` foi treinada
100% em PT-BR e só descobrimos o estrago depois de treinada: respondia em
português a 10 de 12 perguntas em inglês. O mT5 chama isso de *accidental
translation* e mede que o efeito é MAIOR em modelos pequenos — o nosso regime.
Não dá para consertar depois de graça, então já nasce misturado.

REGRA DURA: professor ABERTO (assert_teacher_allowed).

Uso:
    python data/11_gen_extraction.py --target 20 --dry-run
    python data/11_gen_extraction.py --target 900 --workers 12

Saída: data/raw/extraction_tasks.jsonl  ({schema, lang, documento, extracao})
Retomável.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEFAULT_TEACHER, RAW_DIR, assert_teacher_allowed, ensure_dirs  # noqa: E402
from common import jaccard, ngrams, read_jsonl  # noqa: E402
from schema_check import avaliar, load_schemas, render_schema  # noqa: E402
from teacher_api import call_teacher  # noqa: E402

OUT = RAW_DIR / "extraction_tasks.jsonl"

IDIOMAS = {
    "pt": "portugues brasileiro",
    "en": "ingles",
    "es": "espanhol",
    "fr": "frances",
}

# ⚠️ O documento medio da 1a leva ficou em 191 chars (pedi "3 a 10 linhas", vieram
# 3-4 curtas). Documento real — nota fiscal completa, curriculo de pagina inteira —
# e uma ordem de magnitude maior, e NAO sabemos se a abelha transfere. `--doc-len`
# existe para gerar a 2a leva e medir isso, em vez de supor.
TAMANHOS = {
    "curto": "de 3 a 6 linhas, direto ao ponto",
    "medio": "de 8 a 15 linhas, com cabecalho e alguma informacao irrelevante no meio",
    "longo": ("de 25 a 45 linhas, como um documento REAL: cabecalho com endereco e "
              "identificadores, secoes, linhas de tabela, rodape, termos legais, e "
              "BASTANTE informacao irrelevante para os campos pedidos. O modelo "
              "precisa ACHAR os campos no meio do ruido, nao ler um resumo"),
}

# Rodízio de cenário: sem isso o professor gravita para o mesmo documento
# ("Padaria do Joao", "Maria Silva") e o dataset fica grande e redundante.
CENARIOS = [
    "uma empresa pequena de bairro", "uma multinacional de tecnologia",
    "um profissional autonomo", "uma loja online de nicho",
    "um orgao publico", "uma startup em estagio inicial",
    "uma industria tradicional", "um prestador de servico de saude",
    "uma instituicao de ensino", "um escritorio de advocacia",
    "uma transportadora", "um restaurante",
    "uma ONG", "um clube esportivo", "uma imobiliaria",
    "um laboratorio de pesquisa", "uma agencia de viagens",
    "uma construtora", "um marketplace de usados", "uma cooperativa agricola",
]

PROMPT_TMPL = """Gere {n} exemplos DIFERENTES de extracao de dados, em {idioma}.

Cenario para se inspirar: {cenario}

Para cada exemplo, produza:
  (a) um DOCUMENTO realista em {idioma} — texto corrido, e-mail, anuncio, recibo,
      cabecalho ou mensagem, {tamanho}. Escreva como no mundo real:
      formatacao irregular, abreviacoes, ruido. NAO escreva o documento em forma
      de lista de campos.
  (b) a EXTRACAO desse documento, como objeto JSON, seguindo o schema abaixo.

SCHEMA "{schema_nome}" — {schema_desc}
{schema_campos}

REGRAS INEGOCIAVEIS (o exemplo e DESCARTADO se quebrar alguma):
1. Todo valor de campo marcado como copiado precisa APARECER LITERALMENTE no
   documento. Nao reescreva, nao traduza, nao normalize nome proprio.
2. Campos obrigatorios: sempre presentes no JSON.
3. Campo opcional que NAO aparece no documento: OMITA a chave do JSON.
   Nao use null, nao use "" e nao invente um valor plausivel.
4. Nao acrescente nenhum campo fora do schema.
5. Datas no JSON em AAAA-MM-DD (no documento podem estar em qualquer formato).
6. Campo "number"/"integer" e NUMERO JSON, nao string. O simbolo da moeda vai no
   campo de moeda, nunca junto do valor:
     CERTO : "valor_total": 1295.00,  "moeda": "GBP"
     ERRADO: "valor_total": "GBP 1,295.00"
     ERRADO: "valor_total": "1.295,00"
7. Valores de enum EXATAMENTE como listados, respeitando maiuscula/minuscula.
{bloco_ausente}
Responda SOMENTE com um array JSON, sem texto antes ou depois:
[{{"documento": "...", "extracao": {{...}}}}, ...]"""

BLOCO_AUSENTE = """
IMPORTANTE — em {k} dos {n} exemplos, escreva o documento de forma que ALGUNS
campos OPCIONAIS genuinamente NAO existam no texto, e omita essas chaves no JSON.
Documento incompleto e o caso mais comum no mundo real; o modelo precisa aprender
a deixar de fora em vez de inventar.
"""

_lock = threading.Lock()


def parse_lote(texto: str) -> list[dict]:
    """Array JSON do professor → lista de {documento, extracao}. Tolerante a lixo em volta."""
    if not texto:
        return []
    ini, fim = texto.find("["), texto.rfind("]")
    if ini < 0 or fim <= ini:
        return []
    try:
        arr = json.loads(texto[ini:fim + 1])
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    return [x for x in arr
            if isinstance(x, dict) and isinstance(x.get("documento"), str)
            and isinstance(x.get("extracao"), dict)]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=900, help="itens VALIDADOS desejados")
    ap.add_argument("--teacher", default=DEFAULT_TEACHER)
    ap.add_argument("--per-call", type=int, default=4)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--langs", default="pt,en,es,fr")
    ap.add_argument("--schemas", default="", help="subconjunto separado por virgula; vazio = todos")
    ap.add_argument("--doc-len", default="curto", choices=list(TAMANHOS),
                    help="tamanho do documento. A 1a leva saiu com media de 191 chars "
                         "('curto'); 'longo' gera documento de tamanho REAL para medir "
                         "se a abelha transfere — nao sabemos ainda.")
    ap.add_argument("--frac-ausente", type=float, default=0.35,
                    help="fracao dos exemplos com campo opcional GENUINAMENTE ausente. "
                         "0 desliga — mas ai a abelha aprende a sempre preencher tudo.")
    ap.add_argument("--cap-esparso", type=float, default=0.0,
                    help="⭐ TETO para a fracao de itens ACEITOS com campo opcional "
                         "ausente. A 1a leva pediu 35%% e o dataset saiu com 46%% — nao "
                         "e o prompt desobedecendo, e EFEITO DE SELECAO DO FILTRO: item "
                         "com menos campos tem menos chance de errar tipo ou alucinar, "
                         "logo sobrevive mais. Pedir menos no prompt seria chute; este "
                         "teto CORRIGE na aceitacao, que e onde o vies nasce. "
                         "0 = desligado (mantem o comportamento da 1a leva).")
    ap.add_argument("--sim-max", type=float, default=0.6,
                    help="jaccard de 3-gramas acima disso = documento duplicado")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_teacher_allowed(args.teacher)          # REGRA DURA: professor aberto
    ensure_dirs()
    random.seed(args.seed)

    todos = load_schemas()
    nomes_schema = [s.strip() for s in args.schemas.split(",") if s.strip()] or list(todos)
    faltando = [n for n in nomes_schema if n not in todos]
    if faltando:
        print(f"ERRO: schema desconhecido: {faltando} (tem: {list(todos)})", file=sys.stderr)
        return 1
    langs = [l.strip() for l in args.langs.split(",") if l.strip() in IDIOMAS]

    # Retomada + dedup por similaridade do documento.
    existentes: list[dict] = list(read_jsonl(OUT)) if OUT.exists() else []
    grams = [ngrams(r.get("documento", ""), 3) for r in existentes]
    if existentes:
        print(f"[retomada] {len(existentes)} itens validados ja no arquivo")

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key and not args.dry_run:
        print("ERRO: defina OPENROUTER_API_KEY (ou use --dry-run).", file=sys.stderr)
        return 1

    def monta_prompt(schema_nome: str, lang: str, cenario: str) -> str:
        sch = todos[schema_nome]
        k = round(args.per_call * args.frac_ausente)
        return PROMPT_TMPL.format(
            n=args.per_call, idioma=IDIOMAS[lang], cenario=cenario,
            tamanho=TAMANHOS[args.doc_len],
            schema_nome=sch["name"], schema_desc=sch["description"],
            schema_campos=render_schema(sch),
            bloco_ausente=BLOCO_AUSENTE.format(k=k, n=args.per_call) if k else "")

    print(f"professor : {args.teacher}")
    print(f"schemas   : {len(nomes_schema)} | idiomas: {','.join(langs)} | cenarios: {len(CENARIOS)}")
    print(f"meta      : {args.target} itens VALIDADOS (conformes + grounded)")
    print(f"ausentes  : {args.frac_ausente:.0%} dos exemplos com campo opcional faltando")
    print(f"saida     : {OUT}")

    if args.dry_run:
        print("\n[dry-run] nada chamado. Prompt do primeiro combo:\n")
        print("=" * 76)
        print(monta_prompt(nomes_schema[0], langs[0], CENARIOS[0]))
        print("=" * 76)
        return 0

    # contadores de rejeicao — saber POR QUE cai e o que mais rende no ajuste
    stats = {"gerados": 0, "sem_json": 0, "nao_conforme": 0, "alucinado": 0,
             "duplicado": 0, "cap_esparso": 0, "ok": 0, "esparsos": 0}
    motivos: dict[str, int] = {}

    def trabalho(i: int) -> None:
        if stats["ok"] + len(existentes) >= args.target:
            return
        rng = random.Random(args.seed + i)
        # rodizio determinístico: rng.choice deixou um schema com 38% do lote
        schema_nome = nomes_schema[(i // len(langs)) % len(nomes_schema)]
        lang = langs[i % len(langs)]                 # rodizio garante equilibrio
        sch = todos[schema_nome]
        try:
            raw = call_teacher(monta_prompt(schema_nome, lang, rng.choice(CENARIOS)),
                               args.teacher, key, temperature=args.temperature,
                               max_tokens=3000)
        except Exception as e:
            with _lock:
                motivos[f"api:{type(e).__name__}"] = motivos.get(f"api:{type(e).__name__}", 0) + 1
            return

        for item in parse_lote(raw):
            doc = item["documento"].strip()
            ver = avaliar(json.dumps(item["extracao"], ensure_ascii=False), sch, doc,
                          strict=True)   # dado de TREINO: tipo JSON exato
            with _lock:
                stats["gerados"] += 1
                if not ver["json_ok"]:
                    stats["sem_json"] += 1
                    continue
                if not ver["conforme"]:
                    stats["nao_conforme"] += 1
                    for e in ver["erros"][:1]:
                        m = e.split(":")[-1].strip()[:40]
                        motivos[m] = motivos.get(m, 0) + 1
                    continue
                if not ver["grounded"]:
                    stats["alucinado"] += 1
                    continue
                g = ngrams(doc, 3)
                if any(jaccard(g, h) > args.sim_max for h in grams):
                    stats["duplicado"] += 1
                    continue

                # ⭐ teto de esparsidade: corrige o vies ONDE ELE NASCE (na aceitacao)
                opc = [k for k, v in sch["fields"].items() if not v.get("required")]
                esparso = any(k not in ver["obj"] or ver["obj"][k] is None for k in opc)
                if args.cap_esparso and esparso:
                    aceitos = stats["ok"] + len(existentes)
                    if aceitos >= 20 and stats["esparsos"] / aceitos > args.cap_esparso:
                        stats["cap_esparso"] += 1
                        continue
                stats["esparsos"] += int(esparso)
                grams.append(g)
                stats["ok"] += 1
                reg = {"schema": schema_nome, "lang": lang, "documento": doc,
                       "extracao": ver["obj"]}
                with OUT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(reg, ensure_ascii=False) + "\n")
                feitos = stats["ok"] + len(existentes)
                if feitos % 25 == 0:
                    print(f"  {feitos}/{args.target} validados "
                          f"(de {stats['gerados']} gerados)", flush=True)

    faltam = max(0, args.target - len(existentes))
    # margem: historicamente ~metade das candidatas cai no filtro
    chamadas = max(1, int(faltam / max(1, args.per_call) * 2.5))
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(trabalho, range(chamadas)))

    print("\n" + "=" * 60)
    print(f"gerados pelo professor : {stats['gerados']}")
    print(f"  JSON invalido        : {stats['sem_json']}")
    print(f"  fora do schema       : {stats['nao_conforme']}")
    print(f"  ⚠️ ALUCINADO          : {stats['alucinado']}  "
          "(valor que nao existe no proprio documento que ele escreveu)")
    print(f"  duplicado            : {stats['duplicado']}")
    if args.cap_esparso:
        print(f"  cortado pelo teto    : {stats['cap_esparso']}  (esparsos acima de "
              f"{args.cap_esparso:.0%})")
    print(f"  ✅ VALIDADOS          : {stats['ok']}")
    if stats["gerados"]:
        print(f"aproveitamento         : {stats['ok'] / stats['gerados']:.1%}")
    if motivos:
        print("\nmotivos mais comuns de nao-conformidade:")
        for m, c in sorted(motivos.items(), key=lambda x: -x[1])[:8]:
            print(f"  {c:>4}x  {m}")
    print(f"\ntotal no arquivo: {len(existentes) + stats['ok']} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
