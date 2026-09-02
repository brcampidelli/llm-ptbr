"""Valida os artefatos de corrida do gate T1 depois de uma queda — e apaga os que nao passam.

🔴 POR QUE ISTO EXISTE (2026-09-02)
  O `/workspace` do RunPod e' um filesystem de REDE (FUSE/mfs) e ele parou de responder no meio
  do gate: GPU em 0%, load 51, VRAM presa, `ls /workspace` estourando o timeout. O processo de
  treino ficou dormindo a espera de I/O que nunca voltou.

  Um arquivo cortado no meio de uma escrita e' o pior caso possivel aqui, porque o
  `treinar()` PULA as corridas cujo `treino_*.json` existe. Um JSON truncado que passasse
  despercebido viraria "corrida feita" e entraria na media — a familia "nada reclama" aplicada
  ao proprio mecanismo de retomada.

⭐ A VERIFICACAO QUE IMPORTA E' A DE ORDEM, NAO A DE CONTEUDO
  O `treinar_um()` grava o CHECKPOINT primeiro e o JSON depois. Entao um JSON valido, com todos
  os campos certos, SEM o modelo ao lado e' impossivel num fluxo integro — e seria a versao mais
  silenciosa do defeito: passa em toda inspecao direta do arquivo e mente sobre o que aconteceu.

⚠️ E A CORRIDA QUE ESTAVA EM EXECUCAO CAI POR PROCEDENCIA, NAO POR CONTEUDO
  Mesmo que valide em tudo, ela foi escrita por um processo que morreu com o disco pendurado.
  `--suspeita` marca essa e ela vai para o lixo sem discussao (§2z: celula de procedencia
  duvidosa nao pode ler como celula medida).

Uso:
    python bee/validar_corridas.py --base /workspace/bee/gate_t1_bpb
    python bee/validar_corridas.py --base ... --suspeita 64k-multi_s43 --apagar
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

OBRIGATORIOS = ["braco", "semente", "vocab", "passos", "params", "params_embedding",
                "tokens_vistos", "pool_tokens", "epocas", "cobertura_distinta",
                "minutos", "tok_s_regime", "lr", "seq_len",
                "micro_batch", "grad_accum"]
# ⚠️ O campo da perda foi RENOMEADO em 2026-09-02 (`perda_final` era a perda de UM lote e o
#    nome afirmava um resumo da corrida). Artefatos gravados ANTES da renomeacao continuam
#    validos e trazem o nome antigo — exigir so' o novo reprovaria corridas boas por causa
#    de uma mudanca minha, que e' o oposto do que este validador existe para fazer.
ALTERNATIVOS = [("perda_ultimo_lote", "perda_final")]
PASSOS_ESPERADOS = 3051
COBERTURA_ESPERADA = 0.83
TOL_COBERTURA = 0.02


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--suspeita", default="",
                    help="lista '<braco>_s<semente>' que estavam rodando na queda — caem por "
                         "procedencia, mesmo que validem")
    ap.add_argument("--apagar", action="store_true",
                    help="sem isto, so' relata (dry-run)")
    args = ap.parse_args()

    suspeitas = {s.strip() for s in args.suspeita.split(",") if s.strip()}
    arquivos = sorted(args.base.glob("treino_*.json"))
    print(f"{'artefato':<26} {'json':<6} {'campos':<7} {'passos':<7} {'cobert':<8} "
          f"{'modelo':<7} veredito")
    print("-" * 96)

    reprovados: list[tuple[Path, str]] = []
    sem_modelo = 0
    for p in arquifos_ord(arquivos):
        nome = p.stem.replace("treino_", "")
        cel = {"json": "—", "campos": "—", "passos": "—", "cobert": "—", "modelo": "—"}
        motivos = []

        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            cel["json"] = "ok"
        except Exception as e:
            cel["json"] = "🔴"
            motivos.append(f"JSON invalido ({type(e).__name__}) — truncado na queda")
            d = None

        if d is not None:
            faltam = [c for c in OBRIGATORIOS if c not in d]
            faltam += [alt[0] for alt in ALTERNATIVOS if not any(n in d for n in alt)]
            cel["campos"] = "ok" if not faltam else "🔴"
            if faltam:
                motivos.append(f"faltam campos: {','.join(faltam[:4])}")

            pas = d.get("passos")
            cel["passos"] = str(pas) if pas is not None else "—"
            if pas != PASSOS_ESPERADOS:
                cel["passos"] = f"🔴{pas}"
                motivos.append(f"passos {pas} != {PASSOS_ESPERADOS}")

            cob = d.get("cobertura_distinta")
            if cob is None:
                cel["cobert"] = "🔴"
                motivos.append("sem cobertura")
            else:
                cel["cobert"] = f"{cob:.3f}"
                if abs(cob - COBERTURA_ESPERADA) > TOL_COBERTURA:
                    cel["cobert"] = f"🔴{cob:.3f}"
                    motivos.append(f"cobertura {cob:.3f} fora de "
                                   f"{COBERTURA_ESPERADA}±{TOL_COBERTURA}")

        # ⭐ a verificacao de ORDEM: o checkpoint e' gravado ANTES do JSON
        mdir = args.base / f"m_{nome}"
        peso = mdir / "model.safetensors"
        if peso.exists() and peso.stat().st_size > 1_000_000:
            cel["modelo"] = "ok"
        else:
            cel["modelo"] = "🔴"
            sem_modelo += 1
            motivos.append("checkpoint ausente ou vazio — mas o JSON e' gravado DEPOIS dele, "
                           "logo esta ordem e' impossivel num fluxo integro")

        if nome in suspeitas:
            motivos.append("PROCEDENCIA: estava em execucao na queda do filesystem")

        ok = not motivos
        print(f"{nome:<26} {cel['json']:<6} {cel['campos']:<7} {cel['passos']:<7} "
              f"{cel['cobert']:<8} {cel['modelo']:<7} "
              + ("✅ vale" if ok else "🔴 REPROVA"))
        for m in motivos:
            print(f"{'':>26} └─ {m}")
        if not ok:
            reprovados.append((p, mdir))

    print("-" * 96)
    print(f"{len(arquivos) - len(reprovados)} de {len(arquivos)} artefatos valem")

    if not reprovados:
        print("\n✅ nada a apagar — o `treinar` pode retomar direto")
        return 0

    # GUARDA DE DIRETORIO ERRADO (medido 2026-09-02, causando o dano): rodei isto numa copia
    # LOCAL que tinha so' os `treino_*.json` baixados por scp, sem os checkpoints — que ficam
    # no pod. Os 10 artefatos reprovaram por 'checkpoint ausente' e `--apagar` APAGOU os 10,
    # imprimindo 'o treinar vai refaze-las' — verdade no pod e MENTIRA numa copia.
    # Se NENHUM artefato tem modelo ao lado, a hipotese provavel nao e' 'todas as corridas
    # corromperam' e sim 'este nao e' o diretorio de trabalho'. Um destruidor que nao sabe
    # onde esta' e' pior que nenhum.
    if sem_modelo == len(arquivos) and len(arquivos) > 1:
        print()
        print(f'[ABORTADO] {sem_modelo} de {len(arquivos)} artefatos estao sem checkpoint ao'
              f' lado — TODOS.')
        print("   Isto quase certamente nao e' corrupcao, e' o diretorio errado (uma copia")
        print("   so' com os JSONs). Rode contra o diretorio de trabalho, onde os")
        print('   `m_<braco>_s<semente>/` existem. Nada foi apagado.')
        return 2

    print(f"\n🔴 {len(reprovados)} para apagar (o `treinar` vai refaze-las):")
    for p, mdir in reprovados:
        print(f"   {p.name}" + (f" + {mdir.name}/" if mdir.exists() else ""))
    if not args.apagar:
        print("\n(dry-run — rode com --apagar para remover)")
        return 1
    for p, mdir in reprovados:
        p.unlink(missing_ok=True)
        if mdir.exists():
            shutil.rmtree(mdir, ignore_errors=True)
    print(f"\n✅ {len(reprovados)} removidos. Retome com `gate_t1_bpb.py treinar`.")
    return 0


def arquifos_ord(a):
    return sorted(a, key=lambda p: (p.stat().st_mtime))


if __name__ == "__main__":
    raise SystemExit(main())
