"""Guarda de disco para a coleta em volume — sacrifica parquets antes de o disco estourar.

⭐ POR QUE ESTE ARQUIVO EXISTE (2026-08-07)
  A coleta de 13 parquets tem um pico de disco que so' aparece no fim:

    base do sistema (imagem + torch/cuda) ....  39 GB
    13 parquets temporarios (4,85 GB cada) ...  64 GB
    shards de saida .........................  43,5 GB
    -------------------------------------------------
    pico ..................................... 146,5 GB   de 150 GB de container

  Os 13 processos comecam juntos e terminam quase juntos, entao os parquets NAO vao
  sendo liberados ao longo do caminho — quase tudo coexiste nos ultimos minutos. Sao
  ~3,5 GB de folga num pico que chega depois de ~2h30 de CPU. Estourar ali perde a
  coleta inteira.

⭐ A IDEIA: PERDER 8% EM VEZ DE PERDER 100%
  Se o livre cair abaixo do limite, mata UM worker e apaga o parquet dele (4,85 GB) e
  os shards parciais dele (~3 GB). Sao ~8 GB por sacrificio, e o corpus encolhe ~1,7B
  tokens (~8%) em vez de virar zero.

  ⚠️ A ordem importa: matar ANTES de apagar. No Linux o inode sobrevive enquanto
  houver um descritor aberto — apagar o parquet com o worker vivo NAO devolve um byte,
  so' esconde o arquivo. Foi por isso que o alvo e' encontrado por /proc/<pid>/fd e nao
  por nome.

⭐ POR QUE ISTO NAO CORROMPE O CORPUS
  `coletar_pt_volume.py` so' escreve o indice do parquet em estado.json["concluidos"]
  quando ele fecha inteiro. Um parquet sacrificado nunca entra na lista, e
  `juntar_pt.py` monta o corpus SO' a partir de "concluidos" — ele ja' ignora shards
  parciais por construcao (a guarda contra truncamento silencioso, de b4f8c7e).
  Apagar os .bin parciais aqui e' folga de disco, nao correcao: mesmo que ficassem,
  nao entrariam no train.bin.

Uso:
    nohup python bee/guarda_disco.py --limite-gb 12 > /dev/null 2>&1 &
    tail -f /workspace/guarda_disco.log
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import time

ALVO_PADRAO = "/corpus_pt"


def livre_bytes(caminho: str = "/") -> int:
    s = os.statvfs(caminho)
    return s.f_bavail * s.f_frsize


def workers(marca: str) -> list[int]:
    """PIDs vivos da coleta. Le /proc direto para nao depender de psutil."""
    fora = []
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            with open(f"/proc/{p}/cmdline", "rb") as f:
                if marca.encode() in f.read():
                    fora.append(int(p))
        except OSError:
            pass                      # processo morreu entre o listdir e o open
    return fora


def dono_do_arquivo(pids: list[int], alvo: str) -> int | None:
    """Quem tem `alvo` aberto. E' isto que torna o sacrificio correto: matar o dono."""
    for p in pids:
        try:
            for fd in os.listdir(f"/proc/{p}/fd"):
                try:
                    if os.readlink(f"/proc/{p}/fd/{fd}") == alvo:
                        return p
                except OSError:
                    pass
        except OSError:
            pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite-gb", type=int, default=12)
    ap.add_argument("--corpus", default=ALVO_PADRAO)
    ap.add_argument("--log", default="/workspace/guarda_disco.log")
    ap.add_argument("--marca", default="coletar_pt_volume")
    ap.add_argument("--intervalo", type=int, default=30)
    args = ap.parse_args()

    limite = args.limite_gb * (1 << 30)
    tmp = os.path.join(args.corpus, "_parquet_tmp")
    log = open(args.log, "a", buffering=1, encoding="utf-8")

    def diz(msg: str) -> None:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")

    diz(f"guarda ativo — limite {args.limite_gb} GB, corpus {args.corpus}")
    sacrificados = 0

    while (pids := workers(args.marca)):
        g = livre_bytes() >> 30
        if livre_bytes() < limite:
            parquets = sorted(glob.glob(os.path.join(tmp, "*.parquet")))
            if not parquets:
                diz(f"livre={g}G abaixo do limite mas nao ha parquet para sacrificar")
                break
            alvo = parquets[-1]                       # maior indice = ordem previsivel
            m = re.findall(r"(\d+)", os.path.basename(alvo))
            idx = int(m[-1]) if m else -1
            vitima = dono_do_arquivo(pids, alvo)
            diz(f"livre={g}G < {args.limite_gb}G -> sacrificando {os.path.basename(alvo)} "
                f"(idx {idx}, pid {vitima})")
            if vitima is None:
                diz("  ⚠️ dono nao encontrado — NAO apago (apagar com fd aberto nao "
                    "libera espaco). Aguardando proximo ciclo.")
                time.sleep(args.intervalo)
                continue
            os.kill(vitima, 9)
            time.sleep(3)                             # deixa o fd fechar de verdade
            for f in [alvo] + glob.glob(os.path.join(args.corpus, f"pt_?_{idx:03d}.bin")):
                try:
                    os.remove(f)
                    diz(f"  removido {f}")
                except OSError as e:
                    diz(f"  falhou remover {f}: {e}")
            sacrificados += 1
            diz(f"  livre agora {livre_bytes() >> 30}G · sacrificados {sacrificados}")
        time.sleep(args.intervalo)

    diz(f"coleta terminou — {sacrificados} parquet(s) sacrificado(s), "
        f"livre {livre_bytes() >> 30}G")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
