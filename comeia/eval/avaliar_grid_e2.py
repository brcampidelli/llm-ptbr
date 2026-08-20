"""Avalia os 15 adapters do grid do E2 e monta a tabela braço × capacidade.

⭐ O QUE ESTE ARQUIVO DECIDE — e o que ele NÃO pode decidir

O grid treinou 15 variantes. Treino não é resultado: o veredito sai daqui. Cada adapter é
medido nas mesmas réguas do baseline, com o mesmo modelo base, e o número de partida
(`docs/baseline-pre-postreino-350m.json`) entra na tabela como primeira linha — porque sem o
ponto de partida "melhorou" é opinião (arXiv:2604.08880).

⚠️ n REDUZIDO, DECLARADO. Avaliar as réguas inteiras em 15 braços custaria mais que treinar os
   15. Cada régua roda com `--limite`, o que alarga o intervalo de confiança. Isso é legítimo
   para **comparar braços entre si** e ilegítimo para **declarar um número final**: o braço
   vencedor é reavaliado com as réguas completas antes de qualquer decisão.

🔴 E UMA RESSALVA SOBRE O BRAÇO (b) QUE MUDA COMO A TABELA SE LÊ. Ele produz TRÊS adapters que
   deveriam trabalhar juntos, com um roteador escolhendo qual atende cada pedido. Este script
   mede **cada adapter em todas as capacidades** e reporta, para o braço (b), o **melhor dos
   três por capacidade**. Isso é o que um roteador PERFEITO alcançaria — ou seja, um **teto**,
   não o desempenho do sistema. O roteador não está medido aqui, e comparar o teto do braço
   (b) com o número real dos braços (a) e (c) favorece o (b). Está dito na tabela.

⚠️ Capacidades com menos de 1,5% do gradiente (sentimento, atendimento, resumo, tradução) são
   medidas mas marcadas: nenhum arranjo de adapter cria sinal onde não há dado, e empate nelas
   não é evidência sobre arquitetura.

⭐ POR QUE TODA RÉGUA LEVA `--chat` AQUI, e o baseline NÃO levava.

O `prompt` do SFT normalizado é **lista de mensagens com papéis**, então o TRL aplicou
`apply_chat_template`: os 15 braços aprenderam ChatML. O modelo base nunca viu `<|im_start|>`
e foi medido em texto cru. Cada modelo é medido no formato em que foi treinado — que é a
comparação certa para "o pós-treino ajudou", e não é uma comparação de formato único. Medido
ao vivo: o adapter de ferramenta sem `--chat` marcava 0/10 em tudo; com `--chat`, emitia a
chamada correta.

⚠️ `eval_sentimento_pt` mede por verossimilhança e não tem `--chat` — os braços são medidos
ali no formato do base. Sentimento já está na lista de não-discrimináveis (4 exemplos no SFT
inteiro), então isso não muda veredito nenhum, mas está dito.

Uso:
    python comeia/eval/avaliar_grid_e2.py --dry-run
    python comeia/eval/avaliar_grid_e2.py
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
GRID = RAIZ / "docs" / "grid-e2-resultado.json"
SAIDA = RAIZ / "docs" / "grid-e2-avaliado.json"
COLAPSO = RAIZ / "docs" / "grid-e2-colapso.json"

# (capacidade, script, args reduzidos, arquivo de relatorio, chave do numero principal)
REGUAS = [
    ("instrucao", "eval_ifeval_pt.py", ["--limite", "150", "--lote", "48", "--chat"],
     "docs/ifeval-pt-{tag}.json", "estrito_instrucao"),
    ("resumo", "eval_resumo_pt.py", ["--limite", "60", "--lote", "48", "--chat"],
     "docs/resumo-pt-{tag}.json", "modelo_util"),
    ("traducao", "eval_traducao_pt.py", ["--limite", "120", "--lote", "48", "--chat"],
     "docs/traducao-pt-{tag}.json", None),
    ("sentimento", "eval_sentimento_pt.py", ["--limite", "200"],
     "docs/sentimento-pt-{tag}.json", None),
    ("atendimento", "eval_atendimento_pt.py", ["--limite", "100", "--lote", "48", "--chat"],
     "docs/atendimento-pt-{tag}.json", None),
    ("codigo", "eval_coder.py", ["--limit", "120", "--lote", "24", "--chat"],
     "comeia/eval/results/coder_{tag}.json", "pass1"),
    ("agentico", "eval_agentic_exec.py", ["--limit", "0", "--lote", "24", "--chat"],
     "comeia/eval/results/exec_{tag}.json", None),
]

SEM_DADO = {"sentimento", "atendimento", "resumo", "traducao"}


def numero(cap: str, dados: dict) -> float | None:
    """O número principal de cada régua, normalizado para 'maior é melhor'."""
    if dados is None:
        return None
    try:
        if cap == "instrucao":
            return 100 * dados["estrito_instrucao"]
        if cap == "resumo":
            return 100 * dados["modelo_util"]
        if cap == "traducao":
            return dados["modelo_r"]["en->pt"]["bleu"]
        if cap == "sentimento":
            return 100 * dados["modelo_r"]["acuracia"]
        if cap == "atendimento":
            return 100 * dados["modelo_r"]["util"]
        if cap == "codigo":
            return dados.get("pass1", 0.0)
        if cap == "agentico":
            n = dados.get("n_tool") or 1
            return 100 * dados.get("exec_ok", 0) / n
    except (KeyError, TypeError, ZeroDivisionError):
        return None
    return None


def rota(diretorio: Path, sem_lora: bool, base: str) -> list[str] | None:
    """Como CARREGAR este artefato — e a guarda de que ele é o que o grid disse que é.

    🔴 O braço (c) é full FT: o diretório tem um MODELO INTEIRO, não um adapter. O grid grava
    os 15 sob a mesma chave `adapter`, e passar um modelo inteiro como `--peft` não carrega
    nada de útil — `PeftModel.from_pretrained` procura `adapter_config.json`. O que sairia
    disso é o **modelo base medido três vezes**, com o relatório dizendo "braço (c)". O
    veredito seria "full FT não muda nada", que é falso e indistinguível do verdadeiro.

    Por isso a decisão não é por convenção de nome nem pelo campo do grid sozinho: é pelo
    disco, e os dois têm de concordar. Discordância aborta.
    """
    tem_adapter = (diretorio / "adapter_config.json").exists()
    tem_modelo = any((diretorio / n).exists() for n in
                     ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json"))
    if sem_lora:
        if tem_adapter or not tem_modelo:
            print(f"🔴 {diretorio.name}: grid diz full FT, disco diz "
                  f"{'adapter' if tem_adapter else 'vazio'} — ABORTA", file=sys.stderr)
            return None
        return ["--model", str(diretorio)]
    if not tem_adapter:
        print(f"🔴 {diretorio.name}: grid diz LoRA, mas nao ha adapter_config.json — ABORTA",
              file=sys.stderr)
        return None
    return ["--model", base, "--peft", str(diretorio)]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--grid", type=Path, default=GRID)
    ap.add_argument("--so", default="", help="avalia so' as tags que contenham este texto")
    ap.add_argument("--medir-colapsados", action="store_true",
                    help="mede tambem os bracos que a sonda deu como mortos (custa GPU "
                         "para produzir zeros ja' conhecidos)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.grid.exists():
        print(f"🔴 {a.grid} nao existe — rode o grid antes.", file=sys.stderr)
        return 1
    runs = json.loads(a.grid.read_text(encoding="utf-8"))["runs"]

    # ⭐ SONDA DE COLAPSO: pular braco morto, mas NUNCA em silencio.
    # Medir um adapter degenerado nas 7 reguas custa ~50 min de GPU para produzir 49 zeros
    # que ja' se conhecem. O risco de pular e' outro: um braco ausente da tabela le'-se como
    # "nao testado" quando foi testado e morreu. Por isso ele ENTRA na tabela, com o motivo.
    mortos: dict[str, str] = {}
    if COLAPSO.exists() and not a.medir_colapsados:
        c = json.loads(COLAPSO.read_text(encoding="utf-8"))
        mortos = {t: v["motivo"] for t, v in c.items() if not v["vivo"]}
        print(f"sonda de colapso: {len(mortos)} braco(s) mortos, medidos e reportados como "
              f"tal, nao avaliados nas reguas")
    elif not COLAPSO.exists():
        print("⚠️ sem docs/grid-e2-colapso.json — todos serao avaliados, inclusive mortos.")
    tags = [t for t, v in sorted(runs.items()) if "erro" not in v and (not a.so or a.so in t)]

    print("=" * 78)
    print(f"AVALIACAO DO GRID DO E2 — {len(tags)} adapters x {len(REGUAS)} reguas")
    print("=" * 78)
    for t in tags:
        print(f"  {t}")
    if a.dry_run:
        print("\n✅ DRY-RUN: nada avaliado.")
        return 0

    resultados, falhas_de_carga, t0 = {}, [], time.time()
    for i, tag in enumerate(tags, 1):
        d = Path(runs[tag]["adapter"])
        if not d.exists():
            print(f"🔴 {tag}: {d} nao existe — pulado")
            continue
        # ⚠️ o grid antigo nao gravava `sem_lora`; nesse caso deriva-se do braco, e a `rota`
        #    ainda confere contra o disco — duas fontes tem de concordar.
        sem_lora = runs[tag].get("sem_lora", runs[tag].get("braco") == "c")
        carga = rota(d, bool(sem_lora), a.model)
        if carga is None:
            falhas_de_carga.append(tag)
            continue
        if tag in mortos:
            resultados[tag] = {"lr": runs[tag]["lr"], "braco": runs[tag]["braco"],
                               "parte": runs[tag]["parte"], "colapsado": mortos[tag],
                               "capacidades": {c: None for c, *_ in REGUAS}}
            print()
            print(f"[{i}/{len(tags)}] {tag} · COLAPSADO ({mortos[tag]}) — nao avaliado")
            continue
        resultados[tag] = {"lr": runs[tag]["lr"], "braco": runs[tag]["braco"],
                           "parte": runs[tag]["parte"],
                           "carregado_como": "full" if "--peft" not in carga else "lora",
                           "capacidades": {}}
        for cap, script, extras, molde, _ in REGUAS:
            etiqueta = f"e2-{tag}"
            cmd = [PY, str(AQUI / script), *carga, "--tag", etiqueta, *extras]
            print(f"\n[{i}/{len(tags)}] {tag} · {cap}", flush=True)
            p = subprocess.run(cmd, cwd=str(RAIZ), text=True, encoding="utf-8",
                               errors="replace", capture_output=True)
            rel = RAIZ / molde.format(tag=etiqueta)
            if p.returncode != 0 or not rel.exists():
                print(f"   🔴 falhou (rc={p.returncode})")
                print("   " + "\n   ".join((p.stderr or "").strip().splitlines()[-4:]))
                resultados[tag]["capacidades"][cap] = None
                continue
            d = json.loads(rel.read_text(encoding="utf-8"))
            v = numero(cap, d)
            resultados[tag]["capacidades"][cap] = v
            print(f"   {cap} = {v:.2f}" if v is not None else f"   {cap} = ?")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "data": date.today().isoformat(), "modelo": a.model,
        "minutos": round((time.time() - t0) / 60, 1),
        "n_reduzido": {c: e for c, _, e, _, _ in REGUAS},
        "capacidades_nao_discriminaveis": sorted(SEM_DADO),
        "colapsados": mortos,
        "falhas_de_carga": falhas_de_carga,
        "resultados": resultados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ {len(resultados)} adapters avaliados em "
          f"{(time.time() - t0) / 60:.1f} min · {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
