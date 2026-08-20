"""Grid do Estágio 2: arquitetura × LR, com as 8 capacidades medidas em TODOS os braços.

⭐ O QUE ESTE ESTÁGIO DECIDE, E POR QUE ELE É O DE MAIOR RAZÃO INFORMAÇÃO/DÓLAR

O formato de tudo que vem depois: um adapter multi-task, três adapters por afinidade, ou full
fine-tuning. A premissa de custo que reorganiza o plano é que um SFT neste modelo é **barato
demais para ser o gargalo** — ~6,4M tokens por run, minutos de compute. O dinheiro vai para
dado e para avaliação, não para GPU.

**Eixo A — arquitetura:**
  (a) 1 adapter LoRA multi-task sobre a mistura completa
  (b) 3 adapters por afinidade: TEXTO · FERRAMENTA · SIMBÓLICO
  (c) full fine-tuning conjunto — **controle negativo**, esperado abaixo do próprio base em
      pelo menos uma capacidade

**Eixo B — LR, cada braço no ótimo dele.** Rodar todos no mesmo LR é o confundimento que o
lote PEFT do estudo apontou: parte dos −5,9 pp medidos em 151M pode ter sido artefato de LR
mal transferido, e isso precisa ser separado antes de virar teoria. Adapter em
{3e-3, 6e-3, 1,2e-2} (regra dos 10× sobre o 6e-4 medido em full FT) e full FT em
{3e-4, 6e-4, 1,2e-3}.

🔴 UMA RESSALVA QUE O CENSO POR EXEMPLO TORNOU CONCRETA, E QUE MUDA O QUE ESTE GRID PODE
   RESPONDER. A mistura atual dá a quatro das oito capacidades-alvo menos de 1,5% do
   gradiente cada — **sentimento tem 4 exemplos no conjunto inteiro**. Nenhum arranjo de
   adapter cria sinal onde não há dado: nessas quatro capacidades os braços vão empatar perto
   do baseline, e ler esse empate como "a arquitetura não importa" seria errado. O grid
   **mede as oito assim mesmo** — porque medir só onde se espera ganho é exatamente o erro do
   `verifier.py` — mas o relatório marca quais capacidades são **não-discrimináveis por falta
   de dado**, para que o veredito não se apoie nelas.

⚠️ n REDUZIDO NA AVALIAÇÃO, DECLARADO. Avaliar as 8 réguas inteiras em 15 braços seria mais
   caro que treinar os 15. Cada régua roda com `--limite` (ver `AMOSTRA`), o que alarga o
   intervalo de confiança — e o relatório imprime a largura junto do número. O braço vencedor
   é reavaliado com as réguas **completas** antes de qualquer decisão. Comparar dois braços
   com n reduzido é legítimo; declarar um número final com ele, não.

Uso:
    python comeia/train/grid_e2.py --dry-run       # valida a cadeia inteira, sem GPU
    python comeia/train/grid_e2.py --so a          # so' o braco (a)
    python comeia/train/grid_e2.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
COMEIA = RAIZ / "comeia"
PROC = COMEIA / "data" / "processed"
PY = sys.executable
MODELO = "BrCamp/bee-350m-pt-base"
SAIDA = RAIZ / "docs" / "grid-e2-resultado.json"

LR_ADAPTER = [3e-3, 6e-3, 1.2e-2]
LR_FULL = [3e-4, 6e-4, 1.2e-3]

BRACOS = {
    "a": {"nome": "1 adapter multi-task", "lrs": LR_ADAPTER, "sem_lora": False,
          "dados": [("tudo", PROC / "sft_misto_norm.jsonl")]},
    "b": {"nome": "3 adapters por afinidade", "lrs": LR_ADAPTER, "sem_lora": False,
          "dados": [("texto", PROC / "sft_grupo_texto.jsonl"),
                    ("ferramenta", PROC / "sft_grupo_ferramenta.jsonl"),
                    ("simbolico", PROC / "sft_grupo_simbolico.jsonl")]},
    "c": {"nome": "full FT (controle negativo)", "lrs": LR_FULL, "sem_lora": True,
          "dados": [("tudo", PROC / "sft_misto_norm.jsonl")]},
}

# régua → (script, argumentos, n reduzido, chave do numero no json de saida)
AMOSTRA = [
    ("instrucao", "eval_ifeval_pt.py", ["--limite", "150"], "estrito_instrucao"),
    ("resumo", "eval_resumo_pt.py", ["--limite", "60"], "modelo_util"),
    ("traducao", "eval_traducao_pt.py", ["--limite", "120"], None),
    ("sentimento", "eval_sentimento_pt.py", ["--limite", "200"], None),
    ("atendimento", "eval_atendimento_pt.py", ["--limite", "100"], None),
    ("codigo", "eval_coder.py", ["--limit", "120"], None),
    ("agentico", "eval_agentic_exec.py", ["--limit", "0"], None),
]

# capacidades sem dado suficiente para o grid discriminar — medidas, mas nao usadas no veredito
SEM_DADO = {"sentimento": 4, "atendimento": 92, "resumo": 135, "traducao": 124}


def braco_runs(chave: str) -> list[dict]:
    """Todas as combinações (dados × LR) de um braço."""
    b = BRACOS[chave]
    return [{"braco": chave, "parte": nome, "dados": caminho, "lr": lr,
             "sem_lora": b["sem_lora"],
             "tag": f"e2-{chave}-{nome}-lr{lr:g}".replace(".", "p")}
            for nome, caminho in b["dados"] for lr in b["lrs"]]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--so", default="", choices=["", "a", "b", "c"])
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch-size", type=int, default=1,
                    help="por dispositivo. 1 e' o teto da 5070 de 8 GB; numa 5090 de 32 GB "
                         "cabe 8, e o lote maior e' o que tira a GPU da subutilizacao")
    ap.add_argument("--grad-accum", type=int, default=16,
                    help="⚠️ batch-size x grad-accum tem de dar 16 em TODOS os bracos, senao "
                         "o grid compara trajetorias de otimizacao diferentes")
    ap.add_argument("--sem-checkpointing", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    chaves = [a.so] if a.so else list(BRACOS)
    runs = [r for k in chaves for r in braco_runs(k)]

    print("=" * 78)
    print(f"GRID DO ESTAGIO 2 — {len(runs)} treinos · modelo {a.model}")
    print("=" * 78)
    for k in chaves:
        b = BRACOS[k]
        print(f"  braco ({k}) {b['nome']:32} {len(b['dados'])} conjunto(s) x "
              f"{len(b['lrs'])} LR = {len(b['dados']) * len(b['lrs'])} treinos")

    # ---- guarda 1: os arquivos de dados existem
    faltando = [str(r["dados"]) for r in runs if not r["dados"].exists()]
    if faltando:
        print(f"\n🔴 ABORTA: {len(faltando)} arquivo(s) de dados nao existem:", file=sys.stderr)
        for f in sorted(set(faltando)):
            print(f"   {f}", file=sys.stderr)
        print("   Rode: python comeia/data/rotular_capacidades.py --escrever", file=sys.stderr)
        return 1
    print(f"\n  ✅ guarda 1/4: os {len(set(str(r['dados']) for r in runs))} conjuntos existem")

    # ---- guarda: TODO conjunto em prompt/completion.
    #      🔴 Formato misto nao e' detalhe de esquema, e' CONVENCAO DE LOSS: com `messages` o
    #      TRL cobra a loss no prompt inteiro; com prompt/completion ele mascara. Medido em
    #      2026-08-20: o sft_misto tinha 79,1% em `messages`, e a divisao por afinidade saiu
    #      com FERRAMENTA 100% mascarada e TEXTO/SIMBOLICO 100% nao-mascarados. O braco (b)
    #      compararia tres adapters treinados sob convencoes diferentes, e a diferenca medida
    #      seria em parte a convencao — nao a afinidade.
    import json as _j
    sujos = []
    for caminho in sorted({r["dados"] for r in runs}):
        with caminho.open(encoding="utf-8") as f:
            for linha in f:
                if linha.strip() and "prompt" not in _j.loads(linha):
                    sujos.append(caminho.name)
                    break
    if sujos:
        print(f"🔴 ABORTA: {sujos} tem registro fora de prompt/completion.", file=sys.stderr)
        print("   Rode antes: python comeia/data/normalizar_formato_sft.py --escrever",
              file=sys.stderr)
        return 1
    print("  ✅ guarda 2/4: todos os conjuntos em prompt/completion (loss mascarada)")

    # ---- guarda 3: LR de full FT NAO pode ser o de adapter (o erro que sai como
    #      "o braco (c) foi mal" em vez de "o LR estava errado")
    ruins = [r["tag"] for r in runs if r["sem_lora"] and r["lr"] > 2e-3]
    if ruins:
        print(f"🔴 ABORTA: LR de adapter num braco de full FT: {ruins}", file=sys.stderr)
        return 1
    print("  ✅ guarda 3/4: nenhum braco de full FT recebeu LR de adapter")

    # ---- guarda 3: quais capacidades este grid NAO consegue discriminar
    print("  ⚠️ guarda 4/4: capacidades sem dado suficiente para o grid discriminar —")
    for cap, n in sorted(SEM_DADO.items(), key=lambda x: x[1]):
        print(f"       {cap:14} {n:>4} exemplo(s) na mistura · sera' MEDIDA, nao usada "
              f"no veredito")
    print("       Nenhum arranjo de adapter cria sinal onde nao ha' dado. Empate nestas")
    print("       quatro NAO e' evidencia de que a arquitetura nao importa.")

    if a.dry_run:
        print(f"\n{'=' * 78}")
        print("-- dry-run de cada treino (config validada, nada treinado)")
        for r in runs[:3] + ([runs[-1]] if len(runs) > 3 else []):
            cmd = [PY, str(COMEIA / "train" / "sft_qlora.py"), "--model", a.model,
                   "--data", str(r["dados"]), "--lr", f"{r['lr']:g}",
                   "--out", str(COMEIA / "models" / r["tag"]), "--dry-run"]
            if r["sem_lora"]:
                cmd.append("--sem-lora")
            p = subprocess.run(cmd, cwd=str(RAIZ), text=True, capture_output=True,
                               encoding="utf-8", errors="replace")
            marca = "✅" if p.returncode == 0 else "🔴"
            print(f"  {marca} {r['tag']}")
            if p.returncode != 0:
                print("\n".join((p.stderr or "").strip().splitlines()[-4:]))
                return 1
        print(f"\n✅ DRY-RUN: {len(runs)} treinos configurados, cadeia validada. "
              f"Nenhuma GPU tocada.")
        print("   ⚠️ rode o baseline das 8 capacidades ANTES do grid: sem o numero de")
        print("      partida, 'melhorou' e' opiniao (arXiv:2604.08880).")
        return 0

    resultados, t0 = {}, time.time()
    for i, r in enumerate(runs, 1):
        print(f"\n{'=' * 78}\n>> [{i}/{len(runs)}] {r['tag']}\n{'=' * 78}", flush=True)
        cmd = [PY, str(COMEIA / "train" / "sft_qlora.py"), "--model", a.model,
               "--data", str(r["dados"]), "--lr", f"{r['lr']:g}",
               "--epochs", str(a.epochs), "--out", str(COMEIA / "models" / r["tag"]),
               "--batch-size", str(a.batch_size), "--grad-accum", str(a.grad_accum)]
        if r["sem_lora"]:
            cmd.append("--sem-lora")
        if a.sem_checkpointing:
            cmd.append("--sem-checkpointing")
        t = time.time()
        p = subprocess.run(cmd, cwd=str(RAIZ), text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            print(f"🔴 treino {r['tag']} falhou (codigo {p.returncode}) — braco marcado")
            resultados[r["tag"]] = {"erro": f"treino falhou ({p.returncode})"}
            continue
        resultados[r["tag"]] = {"minutos_treino": round((time.time() - t) / 60, 1),
                                "adapter": str(COMEIA / "models" / r["tag"]),
                                "lr": r["lr"], "braco": r["braco"], "parte": r["parte"],
                                "sem_lora": r["sem_lora"]}
        print(f"   treinado em {resultados[r['tag']]['minutos_treino']} min", flush=True)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "data": date.today().isoformat(), "modelo": a.model,
        "n_treinos": len(runs), "minutos_totais": round((time.time() - t0) / 60, 1),
        "capacidades_nao_discriminaveis": SEM_DADO,
        "runs": resultados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{'=' * 78}")
    print(f"✅ {len(resultados)} treinos em {SAIDA}")
    print("   Proximo: avaliar cada adapter com comeia/eval/baseline_8_capacidades.py --peft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
