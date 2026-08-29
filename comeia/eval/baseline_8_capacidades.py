"""Roda as oito réguas contra o Bee-350M base e consolida `docs/baseline-pre-postreino-350m.json`.

⭐ POR QUE O BASELINE **ANTES** DE QUALQUER TREINO É O ENTREGÁVEL, E NÃO BUROCRACIA

A lição está em arXiv:2604.08880: destilação de CoT **piorou** a matemática na maioria das
configurações testadas, e a literatura anterior não viu porque comparava variantes treinadas
entre si — nunca contra o modelo de partida. Este projeto pagou a mesma conta em casa: o SFT
generalista PT-BR desperdiçou esforço porque o base já ia bem, e a abelha agêntica funcionou
porque o base estava em 45,7%, com espaço de sobra. Sem o número de partida, "melhorou" é
opinião.

⭐ E CADA CAPACIDADE VEM COM O SEU PISO NO MESMO ARQUIVO. Um baseline sem piso deixa a
   pergunta errada em aberto ("o Bee faz 55%, é bom?"). Com piso, a pergunta certa se
   responde sozinha: 55% em sentimento é **pior que contar a palavra "não"**.

Pisos já medidos, todos sem modelo nenhum:

    resumo ............. LEAD-2 (copiar 2 frases da fonte) ...... 51,3%
    sentimento ......... lexico de 60 palavras .................. 79,0%  (so' "nao": 73,2%)
    traducao ........... copiar a fonte sem traduzir ............ chrF++ 21,5 / BLEU 2,5
    atendimento ........ palavra-chave + regex .................. UTIL 60,4%
    codigo ............. (sem piso trivial; teto verificado 100%)
    ifeval ............. (sem piso trivial; referencia 100%)

Uso:
    python comeia/eval/baseline_8_capacidades.py --dry-run   # valida as 8 reguas, sem GPU
    python comeia/eval/baseline_8_capacidades.py             # mede de verdade
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
PY = sys.executable
MODELO = "BrCamp/bee-350m-pt-base"
SAIDA = RAIZ / "docs" / "baseline-pre-postreino-350m.json"

# (capacidade, script, argumentos extras, relatorio json que ele grava)
REGUAS = [
    ("instrucao_conteudo", "eval_ifeval_pt.py", ["--tag", "base350m", "--lote", "48"],
     RAIZ / "docs" / "ifeval-pt-base350m.json"),
    ("resumo", "eval_resumo_pt.py", ["--tag", "base350m", "--lote", "48"],
     RAIZ / "docs" / "resumo-pt-base350m.json"),
    ("traducao", "eval_traducao_pt.py", ["--tag", "base350m", "--lote", "48"],
     RAIZ / "docs" / "traducao-pt-base350m.json"),
    ("sentimento", "eval_sentimento_pt.py", ["--tag", "base350m"],
     RAIZ / "docs" / "sentimento-pt-base350m.json"),
    ("atendimento", "eval_atendimento_pt.py", ["--tag", "base350m", "--lote", "48"],
     RAIZ / "docs" / "atendimento-pt-base350m.json"),
    ("codigo_interno", "eval_coder.py", ["--limit", "0", "--tag", "base350m"],
     AQUI / "results" / "coder_base350m.json"),
    ("codigo_humaneval_xl", "eval_coder.py",
     ["--limit", "0", "--tag", "hxl-base350m",
      "--tasks", str(AQUI / "benchmarks" / "humaneval_xl_pt.jsonl")],
     AQUI / "results" / "coder_hxl-base350m.json"),
    ("agentico", "eval_agentic_exec.py", ["--k", "1", "--tag", "base350m"],
     AQUI / "results" / "exec_base350m.json"),
]
# a matematica NAO entra na lista: ela e' o gate de US$ 0 do proprio Estagio 0, roda separado
# com k=256 e leva ~4,6 h. O consolidador so' LE o relatorio dela, se ja' existir.
MATEMATICA = AQUI / "results" / "aritmetica_passk_gate-matematica.json"

# reguas que aceitam `--chat`. `eval_sentimento_pt.py` NAO aceita e nao precisa: ele pergunta
# por verossimilhanca (logprob de " positivo" contra " negativo") no mesmo molde para os dois
# modelos, entao nao ha' parser nem formato a acertar.
SUPORTA_CHAT = {"eval_ifeval_pt.py", "eval_resumo_pt.py", "eval_traducao_pt.py",
                "eval_atendimento_pt.py", "eval_coder.py", "eval_agentic_exec.py"}


def revisao_do_modelo(nome: str) -> str:
    """SHA do commit do modelo no Hub. Sem isto, 'baseline do Bee-350M' não identifica nada:
    o repositório pode ser reescrito e o número deixaria de ser reproduzível em silêncio."""
    try:
        from huggingface_hub import model_info
        return model_info(nome).sha or "?"
    except Exception as e:                                       # noqa: BLE001
        return f"indisponivel ({type(e).__name__})"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--peft", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--so", default="", help="roda so' esta capacidade")
    ap.add_argument("--chat-nao-precisa", action="store_true",
                    help="declara que este artefato NAO usa chat template (raro)")
    ap.add_argument("--chat", action="store_true",
                    help="aplica o chat template nas reguas que suportam (ver SUPORTA_CHAT). "
                         "OBRIGATORIO para modelo pos-treinado em ChatML.")
    a = ap.parse_args()

    # 🔴 §2e NO CONSOLIDADOR INTEIRO, nao so' na celula agentica. Medido em 2026-08-28: seis
    #    das nove reguas aceitam `--chat` e o consolidador NAO passava em nenhuma. O primeiro
    #    run com `--peft` mediu um adapter treinado em ChatML inteiramente em texto cru, e
    #    produziu uma tabela de "o que o pos-treino quebrou" onde cada numero negativo podia
    #    ser formato. **Medir cada modelo no formato em que foi treinado** — base em cru,
    #    pos-treinado em chat — e' a unica leitura valida, e e' a excecao a "mesma regua" que
    #    a §2e justifica explicitamente.
    if a.peft and not a.chat and not a.chat_nao_precisa and not a.dry_run:
        print("\n🔴 ABORTANDO: --peft sem --chat.\n"
              "   O adapter foi treinado em ChatML; medi-lo em texto cru mede o formato, nao\n"
              "   o modelo (§2e). Rode com --chat, ou com --chat-nao-precisa se este adapter\n"
              "   realmente nao usa chat template.")
        return 1

    print("=" * 78)
    print(f"BASELINE DAS 8 CAPACIDADES — {a.model}")
    print("=" * 78)

    reguas = [r for r in REGUAS if not a.so or r[0] == a.so]
    resultados, falhas = {}, []
    t_total = time.time()

    # 🔴 A TAG TEM DE SEGUIR O ARTEFATO, senao cada regua sobrescreve o relatorio da rodada
    #    anterior. Medido em 2026-08-28: rodar com `--peft e13-email-s42` gravou os numeros do
    #    adapter dentro de `docs/ifeval-pt-base350m.json`, `sentimento-pt-base350m.json` e
    #    outros quatro — arquivos cujo NOME afirma serem do modelo base. O campo `peft` de
    #    dentro era a unica coisa que os desmentia. Mesmo defeito do caminho fixo da saida
    #    consolidada, um nivel abaixo.
    sufixo = (Path(a.peft).name + ("-chat" if a.chat else "")) if a.peft else None

    for capacidade, script, extras, relatorio in reguas:
        if sufixo:
            extras = [f"{e}-{sufixo}" if i and extras[i - 1] == "--tag" else e
                      for i, e in enumerate(extras)]
            relatorio = relatorio.with_name(
                relatorio.name.replace("base350m", f"base350m-{sufixo}"))
        cmd = [PY, str(AQUI / script), "--model", a.model, *extras]
        if a.peft:
            cmd += ["--peft", a.peft]
        if a.chat and script in SUPORTA_CHAT:
            cmd += ["--chat"]
        if a.dry_run:
            cmd += ["--dry-run"]
        print(f"\n{'=' * 78}\n>> {capacidade}  ({script})\n{'=' * 78}", flush=True)
        t0 = time.time()
        # ⚠️ SAIDA STREAMADA, NAO CAPTURADA. A primeira versao usava capture_output=True, o
        #    que bufferiza o filho e so' imprime quando ele termina. Resultado medido em
        #    2026-08-19: nove minutos rodando a primeira regua sem UMA linha de progresso, e
        #    nenhuma forma de perceber que a GPU estava a 31% de utilizacao e 36 W porque o
        #    lote padrao era 8 contra os 96 que o gate usava. Ficar cego por escolha propria
        #    e' pior que log verboso — e impede exatamente a medicao de throughput que o
        #    checklist do projeto exige antes de comprometer um run longo.
        p = subprocess.run(cmd, cwd=str(RAIZ), text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            # stderr do filho ja' saiu direto no log (nao e' mais capturado)
            print(f"🔴 {capacidade} FALHOU (codigo {p.returncode}) — erro acima")
            falhas.append(capacidade)
            continue
        print(f"   ({(time.time() - t0) / 60:.1f} min)")
        if not a.dry_run:
            if relatorio.exists():
                resultados[capacidade] = json.loads(relatorio.read_text(encoding="utf-8"))
            else:
                # ⚠️ script terminou 0 mas nao gravou: e' falha, nao ausencia. Registrar como
                #    "ok" um relatorio que nao existe e' como o avaliador de mundo fechado.
                print(f"🔴 {capacidade}: saiu com codigo 0 mas {relatorio.name} nao existe")
                falhas.append(capacidade)

    if a.dry_run:
        print(f"\n{'=' * 78}")
        if falhas:
            print(f"🔴 {len(falhas)} regua(s) NAO passaram no proprio dry-run: {falhas}")
            print("   Corrija antes de gastar GPU — o baseline sairia com buraco.")
            return 1
        print(f"✅ as {len(reguas)} reguas passam no dry-run. Pode medir.")
        return 0

    # 🔴 A MATEMATICA E' LIDA, NAO MEDIDA — e ate' 2026-08-28 isso nao aparecia no arquivo.
    #
    # Rodar o consolidador com `--peft X` copiava para dentro do relatorio de X a matematica do
    # modelo ANTERIOR (`peft: None`, `minutos: 270.7`), sem marca nenhuma. Lida na tabela, a
    # celula dizia "matematica inalterada" — uma afirmacao sobre uma medicao que nao aconteceu.
    # A unica coisa que separava as duas leituras era abrir o campo e reparar no `peft` de
    # dentro. Agora a procedencia vai explicita, e a celula so' e' comparavel se o `peft` do
    # relatorio lido bater com o desta rodada.
    if MATEMATICA.exists():
        mat = json.loads(MATEMATICA.read_text(encoding="utf-8"))
        mesmo = (mat.get("peft") or None) == (a.peft or None)
        resultados["matematica"] = {
            **mat,
            "_procedencia": f"LIDA de {MATEMATICA.name}, nao medida nesta rodada",
            "_peft_do_relatorio": mat.get("peft"),
            "_comparavel_a_esta_rodada": mesmo,
        }
        print(f"\n   + matematica lida de {MATEMATICA.name} (gate de k=256, roda separado)")
        if not mesmo:
            print(f"   🔴 e ela e' de OUTRO artefato (peft={mat.get('peft')!r} contra "
                  f"{a.peft!r}). NAO e' medicao deste modelo — marcado no arquivo.")
    else:
        print(f"\n   ⚠️ matematica AUSENTE: {MATEMATICA.name} ainda nao existe. O baseline "
              f"sai com 7 de 8 e isso fica registrado no arquivo.")

    # 🔴 O NOME DE SAIDA DERIVA DO ARTEFATO MEDIDO. A v1 gravava sempre no mesmo arquivo, entao
    # a primeira rodada com `--peft` SOBRESCREVEU o baseline do modelo base (recuperado do
    # commit f79e01b). Comparacao antes/depois nao sobrevive a um caminho fixo.
    alvo = SAIDA
    if a.peft:
        alvo = SAIDA.with_name(f"baseline-350m-{Path(a.peft).name}.json")
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps({
        "data": date.today().isoformat(),
        "modelo": a.model,
        "revisao_hub": revisao_do_modelo(a.model),
        "peft": a.peft,
        "capacidades_medidas": sorted(resultados),
        "capacidades_faltando": falhas + ([] if "matematica" in resultados else ["matematica"]),
        "minutos_totais": round((time.time() - t_total) / 60, 1),
        "resultados": resultados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{'=' * 78}")
    print(f"✅ {len(resultados)} capacidades gravadas em {alvo}")
    if falhas:
        print(f"🔴 faltaram: {falhas}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
