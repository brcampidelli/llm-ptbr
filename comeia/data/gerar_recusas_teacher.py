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

# 🔴 NAO USE splitlines() PARA LER JSONL. `json.dumps` NAO escapa U+2028 (LINE
#    SEPARATOR) nem U+2029 (PARAGRAPH SEPARATOR) — sao legais dentro de string JSON —
#    mas `str.splitlines()` do Python os trata como quebra de linha e PARTE o registro
#    ao meio. Medido: 2 ocorrencias em 35.528 registros de codigo bastaram para
#    35.528 virarem 35.530 fragmentos, dois deles JSON invalido. Aqui deu erro alto;
#    com um try/except em volta teria virado registro descartado em silencio.
#    `split(chr(10))` e a iteracao do proprio arquivo quebram SO em quebra de linha de verdade.

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
ENTRADA = RAIZ / "comeia" / "data" / "processed" / "negativos_masking.jsonl"
SAIDA = RAIZ / "comeia" / "data" / "processed" / "negativos_com_recusa.jsonl"

# 🔴 OS MODELOS `:free` TEM TETO DIARIO DE 1.000 CHAMADAS somado em TODOS eles
# (`free-models-per-day-high-balance`). A 70% de aceitacao, os ~9.800 negativos levariam
# ~14 dias. A conta ja' tinha saldo, e modelo PAGO nao tem esse teto: 14 mil chamadas custam
# ~US$ 1. O teto nao era de dinheiro, era de plano — e custou meio dia para ser diagnosticado
# porque o sintoma foi "o arquivo parou de crescer", que se parece com travamento.
#
# ⚠️ DOIS DOS QUATRO CANDIDATOS TESTADOS VAZARAM A CADEIA DE PENSAMENTO como conteudo:
#   nemotron-3-super : "Okay, the user is asking for a QR code... Let me check the tools."
#   qwen3.5-9b       : "Thinking Process: 1. Analyze the Request..."
# A guarda de idioma pega (nao ha marca de portugues), mas rejeitar metade das chamadas de um
# teacher e' desperdicio. Escolher teacher por TESTE na tarefa real, nao por tamanho.
#
# O par ficou com duas familias distintas — e os positivos do gigaverbo sao TODOS Qwen, entao
# usar nao-Qwen nas recusas adiciona diversidade onde ela falta.
# ⭐ TRES FAMILIAS, e todas com licenca VERIFICADA NA ORIGEM (nao no rotulo do agregador):
#    gpt-oss-120b (Apache-2.0) · gemma-4-31b (Google) · mistral-nemo (Apache-2.0).
#    Os positivos do gigaverbo sao 100% Qwen, entao a diversidade das recusas e' onde da'
#    para compensar o vies de familia unica.
#
# 🔴 HERMES-4-70B FOI TESTADO, PASSOU NA QUALIDADE E FICOU DE FORA POR LICENCA: tag `llama3`,
#    base `meta-llama/Meta-Llama-3.1-70B`, e a Llama Community License traz clausula contra
#    usar a saida para melhorar outro modelo de linguagem — que e' exatamente este uso.
#    ⚠️ Nao foi possivel LER o texto na origem (repos da Meta sao gated, pagina publica
#    renderizada por JS). O verificado e' a tag e a base. Como mistral-nemo e phi-4 fazem o
#    mesmo trabalho sob Apache-2.0 e MIT, nao ha' motivo para correr o risco.
#
# ⚠️ E o criterio de escolha e' TESTE NA TAREFA, nao tamanho nem preco: nemotron-3-super-120b
#    e qwen3.5-9b vazaram cadeia de pensamento; phi-4 mandou o usuario "usar algum aplicativo
#    online", saindo do catalogo. O mais barato dos testados (mistral-nemo, US$ 0,20/12k) foi
#    o que produziu a recusa mais bem estruturada.
TEACHERS = ["openai/gpt-oss-120b", "google/gemma-4-31b-it", "mistralai/mistral-nemo"]
RX_FERR = re.compile(r"^- ([a-zA-Z0-9_]+):", re.M)
RX_CHAMADA = re.compile(r'\{\s*"tool"|<tool_call>|"arguments"\s*:')
# marcas de portugues; ausencia total = provavelmente o teacher respondeu em ingles
# 🔴 A PRIMEIRA VERSAO REPROVOU 19,6% e boa parte era dado BOM. A auditoria (que so' foi
#    possivel depois de passar a gravar os rejeitados) mostrou os dois lados:
#      falso positivo: "nao esta' entre as funcoes", "nao possuo", "nao tem nada pra",
#                      "nao pode ser realizado" — e, o pior, "Nao E' possivel", porque o
#                      padrao trazia `e possivel` SEM ACENTO e nao casava com "e'".
#      acerto real   : "Posso gerar esse QR usando a ferramenta generate_qrcode" — o teacher
#                      alucinou a ferramenta REMOVIDA como disponivel.
#    Guarda estreita demais nao e' "conservadora": ela descarta dado bom em silencio, e o
#    unico jeito de saber era guardar o que foi reprovado.
RX_NEGA = re.compile(
    r"(n[aã]o (consigo|posso|tenho|possuo|disponho|encontrei|h[aá]|existe|d[aá]|deu)"
    r"|n[aã]o [eé][' ]?\s?poss[ií]vel"
    r"|n[aã]o (est[aá]|estao|est[aã]o) (entre|dispon[ií]ve|na lista|no meu|ao meu)"
    r"|n[aã]o (pode|podem|poderia) ser"
    r"|n[aã]o tem nada|n[aã]o h[aá] (nenhuma|ferramenta|como)"
    r"|nenhuma (das )?ferramenta|sem ferramenta|fora do (meu|que)"
    r"|infelizmente|lamento|sinto muito|impossibilitad|indispon[ií]ve)", re.I)

RX_PT = re.compile(r"\b(não|nao|com|para|que|você|voce|posso|consigo|ferramenta)\b", re.I)


def tem_letra_estrangeira(t: str) -> bool:
    """🔴 LETRA fora do alfabeto latino — o teacher às vezes injeta outro sistema de escrita.

    Medido: *"Desculpe, **περιο** não consigo converter moedas com as ferramentas que tenho"*.
    A guarda de idioma passou porque exigia apenas UMA marca de português **presente**, e não
    a ausência de lixo. Presença de sinal não é ausência de ruído.

    ⚠️ Só LETRA. O espaço estreito (U+202F) em "Nova York" é tipografia, não contaminação —
    reprová-lo descartaria resposta boa num free tier limitado por minuto.
    """
    import unicodedata
    for ch in t:
        if ch.isalpha() and "LATIN" not in unicodedata.name(ch, ""):
            return True
    return False

# 🔴 O PROMPT UNICO CONVERGE. Medido: no piloto de 29 recusas, 83% de aberturas distintas;
#    em 332, apenas 30%, com "desculpe, mas nao consigo" repetindo 39x e a TTR caindo de
#    0,354 para 0,130. O problema do template chegou assim mesmo, pela porta do teacher — e
#    caro. A causa e' o proprio molde: ele DITA a frase ("diga que nao consegue fazer isso"),
#    e um pedido identico 4.000 vezes produz a mesma resposta 4.000 vezes, por mais alta que
#    seja a temperatura.
#    ⭐ A correcao nao e' subir temperatura: e' variar o PEDIDO. Cada recusa sorteia um
#    registro diferente, e registros diferentes forcam construcoes diferentes.
ESTILOS = [
    "direto e objetivo, sem pedir desculpas",
    "cordial, comecando por reconhecer o que o usuario quer",
    "informal, como um colega de trabalho falaria",
    "formal e conciso, de atendimento profissional",
    "prestativo: gaste a maior parte da resposta na alternativa que VOCE PODE fazer",
    "explicativo: diga em uma frase por que a ferramenta certa nao esta' disponivel",
    "breve — no maximo uma frase",
]

MOLDE = """Um assistente tem acesso APENAS a estas ferramentas:
{catalogo}

O usuário pediu: "{pedido}"

Nenhuma das ferramentas acima atende esse pedido. Escreva a resposta do assistente em
português brasileiro natural.

ESTILO DESTA RESPOSTA: {estilo}

Regras: deixe claro que o pedido não pode ser atendido com as ferramentas disponíveis; se
alguma da lista for minimamente útil, ofereça-a; NÃO invente ferramenta fora da lista; NÃO
escreva JSON nem chamada de função; escreva SOMENTE em português.

Responda SÓ com a fala do assistente, sem aspas e sem comentário."""


def chave_openrouter() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if k:
        return k
    env = RAIZ / ".env"
    if env.exists():
        for l in env.read_text(encoding="utf-8").split(chr(10)):
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
    if tem_letra_estrangeira(t):
        return "letra_fora_do_alfabeto_latino"
    # 🔴 A RECUSA TEM DE RECUSAR. Sem esta guarda passou "Ola! Entendo que voce gostaria de
    #    descobrir restaurantes nas proximidades da sua localizacao atual" — que ACOLHE o
    #    pedido e nunca diz que nao da'. Como exemplo de treino isso ensina o oposto do
    #    pretendido, e a metrica `over_call` nao veria diferenca: nenhuma chamada foi emitida
    #    nos dois casos. Numero bom, comportamento errado.
    if not RX_NEGA.search(t):
        return "nao_contem_recusa"
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

    linhas = [json.loads(l) for l in a.entrada.read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    # ⭐ RETOMADA: o free tier e' limitado por minuto, e este job leva horas. Reprocessar o
    #    que ja' foi feito seria desperdicio E mudaria as recusas ja' aceitas.
    feitos = set()
    if a.saida.exists():
        for l in a.saida.read_text(encoding="utf-8").split(chr(10)):
            if not l.strip():
                continue
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
    rejeitos_f = (a.saida.parent / "recusas_rejeitadas.jsonl").open("a", encoding="utf-8")
    try:
        for i, d in enumerate(pendentes):
            sistema = d["messages"][0]["content"]
            nomes = set(RX_FERR.findall(sistema))
            prompt = MOLDE.format(catalogo=catalogo_curto(sistema),
                                  pedido=d["messages"][1]["content"],
                                  estilo=ESTILOS[i % len(ESTILOS)])
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
                # ⚠️ REJEITADO TAMBEM E' DADO. Sem guardar o texto nao ha' como saber se a
                #    guarda reprovou lixo ou se ela esta' estreita demais — e "19,6% reprovados
                #    por nao_contem_recusa" e' exatamente o tipo de numero que pode significar
                #    as duas coisas opostas.
                if rejeitos_f:
                    rejeitos_f.write(json.dumps(
                        {"motivo": motivo, "teacher": teacher, "texto": r.strip()[:600],
                         "removida": d["ferramenta_removida"]}, ensure_ascii=False) + chr(10))
                    rejeitos_f.flush()
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
        rejeitos_f.close()

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
        # 🔴 AS DUAS METRICAS ANTERIORES DEPENDIAM DO TAMANHO DA AMOSTRA, e por isso o alarme
        #    disparou sem motivo. "Aberturas distintas" cai mecanicamente conforme n cresce
        #    (mais amostras, mais colisao), e TTR cai por definicao. Comparar 83% em n=29 com
        #    32% em n=555 media o n, nao a diversidade.
        #    ⭐ O controle resolve: os PEDIDOS do usuario sao texto natural, todos distintos
        #    entre si, e nao foram gerados por teacher nenhum. Medidos com a MESMA regua e no
        #    MESMO n, dao 23% — abaixo dos 32% das recusas. O portugues tem poucas maneiras de
        #    comecar uma recusa, e poucas de comecar um pedido; o nivel absoluto nao diz nada.
        pedidos = [r["messages"][1]["content"] for r in aceitos]
        ab_ctrl = Counter(" ".join(t.split()[:4]).lower() for t in pedidos)
        frac_ctrl = len(ab_ctrl) / len(aceitos)
        frac = len(aberturas) / len(aceitos)
        top3 = sum(c for _, c in aberturas.most_common(3)) / len(aceitos)
        print(f"  top-3 aberturas     : {100*top3:.0f}% do total")
        print(f"  CONTROLE (pedidos)  : {100*frac_ctrl:.0f}% de aberturas distintas, "
              f"mesmo n, texto natural")
        if frac < frac_ctrl * 0.8:
            print(f"  🔴 as recusas ({100*frac:.0f}%) sao MENOS diversas que o texto natural "
                  f"({100*frac_ctrl:.0f}%) — convergindo para template")
        else:
            print(f"  ✅ {100*frac:.0f}% contra {100*frac_ctrl:.0f}% do controle — "
                  "diversidade compativel com texto natural")
    if not a.amostra:
        print(f"\n✅ {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
