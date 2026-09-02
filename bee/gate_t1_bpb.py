"""Gate T1, EIXO 2 — bpb POR IDIOMA. O eixo que decide, e o unico que exige GPU.

⭐ POR QUE ELE EXISTE
  Os eixos 1 (fertilidade) e 3 (incompletude) rodaram em CPU e ELIMINARAM candidatos: o 32k
  atual reprova pelo arabe, o 32k-multi pelo portugues. Nenhum dos dois ELEGE. `2607.24276` e
  `2310.08754` mediram que **fertilidade nao e' preditiva de qualidade**, entao escolher o
  vocabulario pelo eixo 1 seria escolher pelo proxy em vez de pelo alvo.

⭐⭐ A REGUA E' bpb — E ESSA E' A UNICA ESCOLHA QUE TORNA O GATE POSSIVEL
  Comparar tokenizadores por LOSS e' impossivel: cada um produz uma distribuicao de tokens
  diferente, entao a loss nao e' a mesma quantidade em bracos diferentes. `bpb` normaliza por
  **BYTE do texto original**, que e' identico em todos os bracos:

      bpb = (nats_totais / ln 2) / bytes_do_holdout

  O holdout e' fixado em BYTES por idioma, e cada braco o tokeniza com o proprio tokenizador.

⚠️ O DESENHO E' DELIBERADAMENTE GENEROSO COM VOCABULARIO GRANDE — E POR ISSO E' UNILATERAL
  O transformer e' **identico** em todos os bracos (30 camadas · d_model 576 · GQA 9/3); so' o
  vocabulario muda. Logo o total de parametros muda junto (medido):

      32k  -> 151,2M   (embedding 12,2%)
      64k  -> 169,6M   (embedding 21,7%)
      96k  -> 188,0M   (embedding 29,4%)
      128k -> 206,5M   (embedding 35,7%)

  O braco de 128k e' um modelo **37% maior**, com 55M de parametros de graca. **Se mesmo assim
  ele nao ganhar, esta' morto** — e essa e' a leitura que este gate autoriza. Se ganhar, o gate
  da' o TETO do beneficio, e a pergunta seguinte (se ele se paga quando os parametros saem do
  transformer) fica em aberto e declarada.

  ⚠️ E a escala distorce contra o vocabulario grande: no Bee-1G (d_model 2048) a mesma troca
  custa cerca de metade da fracao que custa aqui. O gate nao mede o trade-off do 1G; mede se
  ha' sinal, e de que tamanho.

⚠️ MESMOS PASSOS, NAO MESMO TEXTO
  Todos os bracos veem o mesmo numero de TOKENS. O tokenizador mais eficiente cobre mais TEXTO
  no mesmo orcamento — e' exatamente o beneficio sob teste, nao um confundidor.
  ⚠️ Mas "mesmos passos" NAO e' "mesmos FLOPs": a projecao de saida custa d_model x vocab a
  cada token, entao o braco de 128k faz 4x o trabalho de cabeca do de 32k. O script reporta
  tok/s e minutos por braco — esse custo aparece em relogio e em dolar, nao no bpb.

⚠️ O QUE ESTE GATE NAO CONTROLA (declarado antes, §2q)
  · LR unico para todos (3e-3, o otimo medido a 151M). Vocabulario grande pode preferir outro,
    e varrer LR por braco multiplicaria o custo por 3. Fica como limitacao, nao como suposicao.
  · Geometria fixa. Trocar d_model junto com o vocab introduziria uma segunda variavel (§2g).

Uso:
    python bee/gate_t1_bpb.py preparar
    python bee/gate_t1_bpb.py treinar --sementes 42,43,44
    python bee/gate_t1_bpb.py avaliar
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))
BASE = ROOT / "bee" / "gate_t1_bpb"
CORPUS = ROOT / "bee" / "corpus_multi"
IDIOMAS = ["por", "spa", "fra", "deu", "eng", "arb", "cmn", "jpn"]

# Os seis bracos. Os quatro que passaram o eixo 1, mais os dois que reprovaram — porque
# "reprovou na fertilidade" nao implica "perde em bpb", e e' justamente isso que se mede.
BRACOS = {
    "32k-atual":       "models/bee-150m-v3-base",       # ancora: bpb PT ja' publicado (§2aa)
    "32k-multi":       "bee/tok_t1/32k-multi",          # reprovou o eixo 1 pelo PT (+19,4%)
    "64k-multi":       "bee/tok_t1/64k-multi",
    "96k-multi":       "bee/tok_t1/96k-multi",
    "128k-multi":      "bee/tok_t1/128k-multi",
    "32k+32k-inplace": "bee/tok_t1/32k+32k-inplace",
}
CONTROLE = "32k-atual"

HOLDOUT_PCT = 2        # mesmo balde sha1 do Gate T1 — holdout disjunto por construcao


def _no_holdout(t: str) -> bool:
    return int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16) % 100 < HOLDOUT_PCT


def textos(cod: str, parte: str, limite_bytes: int):
    import zstandard as zstd
    lidos = 0
    for shard in sorted(glob.glob(str(CORPUS / f"bee_corpus_{cod}_*.jsonl.zst"))):
        bruto = zstd.ZstdDecompressor().decompress(open(shard, "rb").read()).decode("utf-8")
        for linha in bruto.splitlines():
            if not linha.strip():
                continue
            try:
                t = json.loads(linha)["text"]
            except Exception:
                continue
            if (parte == "holdout") != _no_holdout(t):
                continue
            lidos += len(t.encode("utf-8"))
            yield t
            if lidos >= limite_bytes:
                return


def caminho(cam: str) -> str:
    return cam if cam.startswith("models") else str(ROOT / cam)


# ---------------------------------------------------------------- preparar

def grava_meta(meta: dict) -> None:
    """Escreve o meta.json AGORA, atomicamente. Chamado a cada braco.

    🔴 Nasceu de um defeito real (2026-09-01): a v1 so' gravava no FIM de `preparar`. Quando
    o script abortou no 2o braco, ficou UM pool de 480 MB em disco e **nenhum meta** — e o
    `treinar` seguinte morreu com FileNotFoundError. Morrer foi o bom caso: um meta VELHO
    descrevendo pools que nao sao os que estao ali e' a §2z em forma pura, e ninguem notaria
    lendo justamente o arquivo que existe para dizer o que ha' no diretorio.
    E' a mesma licao que a guarda 5 do `coletar_multilingue.py` ja' tinha aprendido — e que
    eu nao transportei para ca' quando escrevi este script.
    """
    tmp = BASE / "meta.json.tmp"
    open(tmp, "w", encoding="utf-8").write(json.dumps(meta, indent=2, ensure_ascii=False))
    os.replace(tmp, BASE / "meta.json")


def preparar(args) -> int:
    import numpy as np
    from transformers import AutoTokenizer

    BASE.mkdir(parents=True, exist_ok=True)
    meta = {"_regua": "bpb = nats/ln2 / BYTES do holdout — comparavel entre tokenizadores",
            "_desenho": "transformer identico; so' o vocab muda. Generoso com vocab grande.",
            "holdout_bytes_por_idioma": args.holdout_bytes, "holdout": {}, "bracos": {}}

    # O holdout e' fixado em BYTES e e' o MESMO texto em todos os bracos.
    hold = {c: list(textos(c, "holdout", args.holdout_bytes)) for c in IDIOMAS}
    for c in IDIOMAS:
        nb = sum(len(t.encode("utf-8")) for t in hold[c])
        print(f"  holdout {c}: {len(hold[c]):>5} docs · {nb/1e6:.2f} MB")
        meta["holdout"][c] = {"docs": len(hold[c]), "bytes": nb}
    open(BASE / "holdout.json", "w", encoding="utf-8").write(
        json.dumps(hold, ensure_ascii=False))

    for nome, cam in BRACOS.items():
        p = BASE / f"pool_{nome}.bin"
        if p.exists() and not args.refazer:
            print(f"  {nome}: pool ja' existe, pulando")
            continue
        tok = AutoTokenizer.from_pretrained(caminho(cam))
        vocab = len(tok)
        # 🔴 96k e 128k NAO cabem em uint16 — e o perigo e' que ele DEPENDE DO CAMINHO.
        # Medido em numpy 2.4.4:
        #     np.asarray(lista, dtype=np.uint16)   -> OverflowError    (aborta, seguro)
        #     np.asarray(lista).astype(np.uint16)  -> 70000 vira 4464  (ZERO avisos)
        # O segundo caminho e' o que os `.bin` deste projeto usaram ate' hoje, porque com
        # vocab 32k nunca houve o que estourar. Com 128k ele produziria ids validos e
        # errados: o treino roda, a loss cai, o bpb sai plausivel e o veredito e' sobre lixo.
        # Por isso uint32 em TODOS os bracos (uniforme, sem caso especial) mais a verificacao
        # de ida-e-volta logo abaixo, que nao depende de qual caminho o numpy tomou.
        if vocab >= 65536:
            print(f"  {nome}: vocab {vocab:,} — uint32 obrigatorio "
                  f"(uint16 daria wrap silencioso)")
        eos = tok.convert_tokens_to_ids("<|endoftext|>")

        # ⚠️ Grava INCREMENTAL. Acumular 120M ids numa lista Python custaria ~3,4 GB de RAM
        # (28 bytes por int), e esta maquina ja' bateu o teto de commit hoje na varredura do
        # eixo 1. O buffer descarrega a cada `descarga` tokens e o maximo global e' mantido a
        # parte, para a verificacao de ida-e-volta continuar valendo sobre o arquivo inteiro.
        t0 = time.time()
        cont = {c: [0, 0] for c in IDIOMAS}
        gers = {c: textos(c, "treino", args.treino_bytes) for c in IDIOMAS}
        vivos = dict(gers)
        buf: list[int] = []
        n_total = 0
        max_id = 0
        tmp_bin = p.with_suffix(".bin.tmp")
        with open(tmp_bin, "wb") as fh:
            def descarrega() -> None:
                nonlocal buf, n_total, max_id
                if not buf:
                    return
                corte = buf[:max(0, args.pool_tokens - n_total)]
                if corte:
                    a = np.asarray(corte, dtype=np.uint32)   # dtype direto: estoura em vez
                    max_id = max(max_id, int(a.max()))       # de dar wrap (medido, numpy 2.4)
                    a.tofile(fh)
                    n_total += len(a)
                buf = []

            while vivos and n_total < args.pool_tokens:
                for c in list(vivos):
                    try:
                        t = next(vivos[c])
                    except StopIteration:
                        del vivos[c]
                        continue
                    ids = tok(t, add_special_tokens=False)["input_ids"]
                    buf.extend(ids)
                    buf.append(eos)
                    cont[c][0] += len(ids) + 1
                    cont[c][1] += len(t.encode("utf-8"))
                    if len(buf) >= args.descarga:
                        descarrega()
                        if n_total >= args.pool_tokens:
                            break
            descarrega()
        if max_id >= vocab:
            raise SystemExit(f"🔴 {nome}: id {max_id} >= vocab {vocab} — pool corrompido")
        os.replace(tmp_bin, p)
        # ida-e-volta sobre o ARQUIVO gravado, nao sobre o buffer que ja' foi embora
        conf = np.fromfile(p, dtype=np.uint32)
        if len(conf) != n_total or int(conf.max()) != max_id:
            raise SystemExit(f"🔴 {nome}: arquivo gravado nao confere "
                             f"({len(conf)} vs {n_total} tokens, max {conf.max()} vs {max_id})")
        a = conf
        meta["bracos"][nome] = {
            "tokenizador": cam, "vocab": vocab, "eos": int(eos),
            "pool_tokens": int(len(a)), "dtype": "uint32",
            "minutos": (time.time() - t0) / 60,
            "por_idioma": {c: {"tokens": cont[c][0], "bytes": cont[c][1],
                               "tok_por_byte": cont[c][0] / max(1, cont[c][1])}
                           for c in IDIOMAS}}
        grava_meta(meta)          # 🔴 a cada braco, nunca so' no fim — ver grava_meta()
        print(f"  {nome}: vocab {vocab:>7,} · pool {len(a)/1e6:.1f}M tok · "
              f"{(time.time()-t0)/60:.1f} min")

    grava_meta(meta)
    print(f"\nmeta: {BASE / 'meta.json'}")
    return 0


# ---------------------------------------------------------------- amostrador e guardas

class SemReposicao:
    """Permuta blocos NAO-SOBREPOSTOS e percorre ate' o fim (§2). Mesmo do gate_faixas."""

    def __init__(self, dados, seq_len: int, semente: int):
        import numpy as np
        self.dados, self.seq_len = dados, seq_len
        self.rng = np.random.default_rng(semente)
        self.n_blocos = (len(dados) - 1) // seq_len
        self.ordem = self.rng.permutation(self.n_blocos)
        self.pos = self.epocas = self.blocos_servidos = 0

    def lote(self, tamanho: int):
        import numpy as np
        idx = []
        for _ in range(tamanho):
            if self.pos >= self.n_blocos:
                self.ordem = self.rng.permutation(self.n_blocos)
                self.pos = 0
                self.epocas += 1
            idx.append(self.ordem[self.pos])
            self.pos += 1
            self.blocos_servidos += 1
        return np.stack([self.dados[i * self.seq_len:(i + 1) * self.seq_len] for i in idx])

    @property
    def cobertura_distinta(self) -> float:
        return min(self.blocos_servidos, self.n_blocos) / max(1, self.n_blocos)


def guarda_rotulos(modelo, x) -> None:
    """§1: aborta se a convencao de rotulos estiver errada. Com dado REAL."""
    import torch
    import torch.nn.functional as F
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        saida = modelo(input_ids=x[:1], labels=x[:1])
    manual = F.cross_entropy(saida.logits[0, :-1].float(), x[0, 1:]).item()
    dif = abs(saida.loss.item() - manual)
    print(f"  guarda de rotulos: {saida.loss.item():.4f} vs {manual:.4f} (dif {dif:.5f})")
    if dif > 0.01:
        raise SystemExit("🔴 convencao de rotulos ERRADA — abortando antes do passo 1")


# ---------------------------------------------------------------- treinar

def treinar_um(nome: str, semente: int, args) -> dict:
    import dataclasses
    import numpy as np
    import torch
    from transformers import LlamaForCausalLM

    from config import ESCADA, para_llama_config

    torch.manual_seed(semente)
    np.random.seed(semente)
    meta = json.load(open(BASE / "meta.json", encoding="utf-8"))
    vocab = meta["bracos"][nome]["vocab"]

    dados = np.fromfile(BASE / f"pool_{nome}.bin", dtype=np.uint32)
    if int(dados.max()) >= vocab:
        raise SystemExit(f"🔴 pool corrompido: id {dados.max()} >= vocab {vocab}")

    cfg = dataclasses.replace(ESCADA["150m"], vocab=vocab, seq_len=args.seq_len)
    modelo = LlamaForCausalLM(para_llama_config(cfg)).cuda()
    n_par = sum(p.numel() for p in modelo.parameters())
    n_emb = sum(p.numel() for n, p in modelo.named_parameters()
                if "embed_tokens" in n or "lm_head" in n)

    tok_por_passo = args.micro_batch * args.grad_accum * args.seq_len
    passos = args.passos or int(args.tokens // tok_por_passo)
    vistos = passos * tok_por_passo

    print(f"\n{'='*72}\nBRACO {nome} · semente {semente}\n{'='*72}")
    print(f"  vocab {vocab:,} · {n_par/1e6:.1f}M params ({n_emb/1e6:.1f}M embedding "
          f"= {n_emb/n_par:.1%}) · pool {len(dados)/1e6:.1f}M tok")
    print(f"  {passos} passos x {tok_por_passo} tok = {vistos/1e6:.1f}M vistos "
          f"= {vistos/len(dados):.2f} epocas")

    am = SemReposicao(dados, args.seq_len, semente)
    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr, betas=(0.9, 0.95),
                            weight_decay=0.1)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=passos,
                                                pct_start=0.02, anneal_strategy="cos")
    modelo.train()
    primeiro, t0, leituras = True, time.time(), []
    acc = 0.0
    # 🔴 `acc` e' a perda de UM lote. Guardar os ultimos 100 passos para poder reportar uma
    #    media — ver a nota de `perda_ultimo_lote` no dicionario de saida.
    janela: list[float] = []
    for passo in range(passos):
        opt.zero_grad(set_to_none=True)
        acc = 0.0
        for _ in range(args.grad_accum):
            x = torch.from_numpy(am.lote(args.micro_batch).astype(np.int64)).cuda()
            if primeiro:
                guarda_rotulos(modelo, x)
                primeiro = False
            with torch.autocast("cuda", dtype=torch.bfloat16):
                perda = modelo(input_ids=x, labels=x).loss / args.grad_accum
            perda.backward()
            acc += perda.item()
        janela.append(acc)
        if len(janela) > 100:
            janela.pop(0)
        torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
        opt.step()
        sched.step()
        if passo >= 20 and passo % 20 == 0:
            leituras.append(tok_por_passo * (passo + 1) / (time.time() - t0))
        if passo % 50 == 0 or passo == passos - 1:
            dt = time.time() - t0
            print(f"  passo {passo:>5}/{passos} · perda {acc:.4f} · "
                  f"{tok_por_passo*(passo+1)/dt/1000:.1f}k tok/s · {dt/60:.1f} min "
                  f"· cob {am.cobertura_distinta:.2f}", flush=True)

    modelo.save_pretrained(BASE / f"m_{nome}_s{semente}")
    r = {"braco": nome, "semente": semente, "vocab": vocab, "passos": passos,
         "params": int(n_par), "params_embedding": int(n_emb),
         "tokens_vistos": vistos, "pool_tokens": int(len(dados)),
         "epocas": vistos / len(dados), "cobertura_distinta": am.cobertura_distinta,
         # 🔴 MEDIDO 2026-09-02: o campo chamava-se `perda_final` e era `acc` — a perda de UM
         #    lote. Entre sementes do braco `32k-atual` isso oscilou 1,1773 (2,5953 x 1,4180)
         #    enquanto os bracos multilingues oscilavam 0,05-0,13. Nao e' variancia de treino:
         #    o vocab PT usa byte-fallback pesado em CJK/arabe, entao um lote majoritariamente
         #    chines tem perda baixa (byte e' previsivel) e um majoritariamente portugues tem
         #    perda alta. O NOME afirmava um resumo da corrida e o valor era um sorteio (§2t).
         # ⚠️ E nenhum dos dois compara BRACOS: perda por token depende do tokenizador. So' bpb.
         "perda_ultimo_lote": acc,
         "perda_media_100": sum(janela) / len(janela) if janela else float("nan"),
         "minutos": (time.time() - t0) / 60,
         "tok_s_regime": sorted(leituras)[len(leituras) // 2] if leituras else 0.0,
         "lr": args.lr, "seq_len": args.seq_len, "micro_batch": args.micro_batch,
         "grad_accum": args.grad_accum}
    json.dump(r, open(BASE / f"treino_{nome}_s{semente}.json", "w"), indent=2)
    return r


def treinar(args) -> int:
    sementes = [int(s) for s in args.sementes.split(",")]
    print(f"{len(BRACOS)} bracos x {len(sementes)} sementes = "
          f"{len(BRACOS)*len(sementes)} runs")
    for semente in sementes:
        for nome in BRACOS:
            if (BASE / f"treino_{nome}_s{semente}.json").exists() and not args.refazer:
                print(f"  {nome} s{semente}: ja' rodou, pulando")
                continue
            treinar_um(nome, semente, args)
    return 0


# ---------------------------------------------------------------- avaliar

def bpb_idioma(dev, modelo, tok, txts: list[str], seq_len: int,
               teto_bytes: int) -> tuple[float, int, int]:
    """bits por byte. Normaliza por BYTE do texto original — a unica forma de comparar
    modelos que usam tokenizadores diferentes.

    ⚠️ O corte e' por BYTE e nao por documento: os idiomas tem tamanhos de documento muito
    diferentes (no holdout de 2 MB, 8 docs em arabe contra 90 em alemao), entao cortar em
    "os primeiros N docs" daria orcamentos de texto diferentes por idioma e a precisao de
    cada celula variaria sem aviso.
    """
    import torch
    sel, n_byte = [], 0
    for t in txts:
        b = len(t.encode("utf-8"))
        if n_byte + b > teto_bytes and sel:
            break
        sel.append(t)
        n_byte += b
    txts = sel
    nats = 0.0
    modelo.eval()
    with torch.no_grad():
        for t in txts:
            ids = tok(t, add_special_tokens=False)["input_ids"]
            for i in range(0, len(ids), seq_len):
                p = ids[i:i + seq_len]
                if len(p) < 2:
                    continue
                x = torch.tensor([p], dtype=torch.long).to(dev)
                with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                    perda = modelo(input_ids=x, labels=x).loss
                nats += perda.item() * (len(p) - 1)
    return nats / math.log(2) / n_byte, len(txts), n_byte


def avaliar(args) -> int:
    import statistics
    import torch
    from transformers import AutoTokenizer, LlamaForCausalLM

    meta = json.load(open(BASE / "meta.json", encoding="utf-8"))
    hold = json.load(open(BASE / "holdout.json", encoding="utf-8"))
    sementes = [int(s) for s in args.sementes.split(",")]
    res: dict[str, dict[str, list[float]]] = {}
    usado: dict[str, tuple[int, int]] = {}

    for nome, cam in BRACOS.items():
        tok = AutoTokenizer.from_pretrained(caminho(cam))
        res[nome] = {c: [] for c in IDIOMAS}
        for s in sementes:
            d = BASE / f"m_{nome}_s{s}"
            if not d.exists():
                print(f"  ⚠️ {nome} s{s}: sem modelo, pulando")
                continue
            dt = torch.bfloat16 if args.dispositivo == "cuda" else torch.float32
            m = LlamaForCausalLM.from_pretrained(d, dtype=dt).to(args.dispositivo)
            for c in IDIOMAS:
                b, nd, nb = bpb_idioma(args.dispositivo, m, tok, hold[c],
                                      args.seq_len, args.bytes_holdout)
                res[nome][c].append(b)
                usado[c] = (nd, nb)
            del m
            if args.dispositivo == "cuda":
                torch.cuda.empty_cache()
            print(f"  {nome} s{s}: "
                  + " ".join(f"{c} {res[nome][c][-1]:.3f}" for c in IDIOMAS), flush=True)

    print(f"\n{'='*104}\nEIXO 2 — bpb POR IDIOMA (menor e' melhor) · media de "
          f"{len(sementes)} sementes\n{'='*104}")
    print("🔴 LEIA POR COLUNA, NUNCA ENTRE COLUNAS. `2608.25089` mede que metricas normalizadas —")
    print("   bpb entre elas — carregam vies crosslinguistico de tokenizacao, codificacao e")
    print("   ortografia. Um byte de arabe e um byte de chines NAO carregam a mesma informacao,")
    print("   entao 'arb 1,20 contra cmn 0,90' nao diz nada. A comparacao VALIDA e' braco contra")
    print("   braco DENTRO da mesma coluna — que e' a tabela de DELTA logo abaixo.")
    print("   ⭐ E bpb e' justamente a regua que RESISTE ao fallback de byte: perplexidade POR")
    print("   TOKEN e' deflacionada por ele (dado o byte-lider, os de continuacao sao quase")
    print("   deterministicos), mas bpb normaliza por BYTE e essa deflacao nao passa (2605.09015).")
    print(f"{'braco':<18} {'vocab':>8} {'params':>8} " + " ".join(f"{c:>7}" for c in IDIOMAS))
    print("-" * 104)
    saida = {}
    for nome in BRACOS:
        tr = [json.load(open(p, encoding="utf-8"))
              for p in sorted(glob.glob(str(BASE / f"treino_{nome}_s*.json")))]
        par = tr[0]["params"] if tr else 0
        med = {c: statistics.mean(res[nome][c]) if res[nome][c] else float("nan")
               for c in IDIOMAS}
        amp = {c: (max(res[nome][c]) - min(res[nome][c])) if len(res[nome][c]) > 1 else 0.0
               for c in IDIOMAS}
        saida[nome] = {"params": par, "vocab": meta["bracos"][nome]["vocab"],
                       "bpb": med, "amplitude": amp, "por_semente": res[nome],
                       "minutos_medio": statistics.mean([t["minutos"] for t in tr]) if tr else 0,
                       "tok_s": statistics.mean([t["tok_s_regime"] for t in tr]) if tr else 0}
        print(f"{nome:<18} {saida[nome]['vocab']:>8,} {par/1e6:>7.0f}M "
              + " ".join(f"{med[c]:>7.3f}" for c in IDIOMAS))
    print("-" * 104)
    print(f"{'amplitude media entre sementes':<36}"
          + " ".join(f"{statistics.mean([saida[n]['amplitude'][c] for n in BRACOS]):>7.3f}"
                     for c in IDIOMAS))

    # §2y: delta POR IDIOMA, nunca a media entre idiomas
    print(f"\n{'='*104}\nDELTA contra {CONTROLE} (negativo = melhor) · e o custo em relogio")
    print(f"{'braco':<18} " + " ".join(f"{c:>7}" for c in IDIOMAS)
          + f" {'min':>7} {'tok/s':>8}")
    print("-" * 104)
    base = saida[CONTROLE]["bpb"]
    for nome in BRACOS:
        if nome == CONTROLE:
            continue
        d = {c: (saida[nome]["bpb"][c] - base[c]) / base[c] for c in IDIOMAS}
        saida[nome]["delta_vs_controle"] = d
        print(f"{nome:<18} " + " ".join(f"{d[c]:>+6.1%}" for c in IDIOMAS)
              + f" {saida[nome]['minutos_medio']:>7.1f} {saida[nome]['tok_s']/1000:>7.1f}k")

    doc = {"_gate": "T1 eixo 2 — bpb por idioma",
    "_dispositivo": args.dispositivo,
    "_dtype": "bfloat16" if args.dispositivo == "cuda" else "float32",
    "_aviso_regua": ("cpu/fp32 e cuda/bf16 sao REGUAS DIFERENTES (§2g). Numero desta rodada so' compara com outro de MESMO _dispositivo e mesmo _bytes_holdout."),
    "_bytes_holdout": args.bytes_holdout,
           "_regua": "bpb normaliza por BYTE; loss NAO compara tokenizadores diferentes",
           "_leia_por_coluna": ("bpb carrega vies crosslinguistico (2608.25089): comparar ENTRE "
                                "idiomas e' invalido. Valido: braco x braco DENTRO de um idioma, "
                                "que e' `delta_vs_controle`. E bpb RESISTE ao fallback de byte, "
                                "porque a deflacao do 2605.09015 atinge perplexidade POR TOKEN e "
                                "bpb normaliza por BYTE."),
           "_desenho": ("transformer identico em todos os bracos; so' o vocab muda, entao o "
                        "braco de vocab maior e' um modelo MAIOR. Teste UNILATERAL: se o vocab "
                        "grande nao ganha com parametros de graca, esta' morto. Se ganha, isto "
                        "e' o TETO do beneficio, nao o valor dele no Bee-1G."),
           "_nao_controlado": ["LR unico (3e-3) para todos os vocabularios",
                               "geometria fixa — d_model nao acompanha o vocab",
                               "mesmos PASSOS nao e' mesmos FLOPs: a cabeca custa d_model x vocab",
                               "escala de 150M distorce a fracao de embedding contra o vocab "
                               "grande (no 1G a mesma troca custa ~metade da fracao)"],
           "holdout_usado": {c: {"docs": usado[c][0], "bytes": usado[c][1]}
                             for c in usado},
           "sementes": sementes, "controle": CONTROLE, "bracos": saida}
    # §2z: NOME DE SAIDA DERIVA DO QUE FOI MEDIDO. Um caminho fixo faz uma rodada de
    # smoke-test em cpu/fp32 sobrescrever o resultado canonico de cuda/bf16, e o JSON so'
    # denuncia a troca no campo `_dispositivo`, que ninguem le antes de citar o numero.
    # A config de referencia mantem o nome estavel (os documentos apontam para ele);
    # qualquer desvio ganha sufixo e nao pode colidir.
    canonica = (args.dispositivo == "cuda" and args.bytes_holdout == 1_500_000 and len(sementes) == 3)
    sufixo = "" if canonica else (f"-{args.dispositivo}-{args.bytes_holdout}b" + "-s" + "".join(str(s) for s in sementes))
    dest = ROOT / "docs" / f"gate-t1-bpb{sufixo}.json"
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    open(tmp, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, dest)
    print()
    print(f"artefato: docs/{dest.name}"
          + ("" if canonica else "   [NAO E A CONFIG CANONICA — nao comparar com o"
                                  " numero de referencia]"))
    if len(sementes) < 3:
        print("\n⚠️ menos de 3 sementes: duas ALERTAM, tres DECIDEM (§2x). "
              "Nao afirme nada sobre variancia com o que esta' aqui.")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("preparar")
    p.add_argument("--pool-tokens", type=int, default=120_000_000)
    p.add_argument("--treino-bytes", type=int, default=400 * 1024 ** 2)
    p.add_argument("--holdout-bytes", type=int, default=4 * 1024 ** 2)
    p.add_argument("--descarga", type=int, default=4_000_000,
                   help="tokens no buffer antes de gravar — segura a RAM")
    p.add_argument("--refazer", action="store_true")

    t = sub.add_parser("treinar")
    t.add_argument("--sementes", default="42,43,44")
    t.add_argument("--tokens", type=int, default=100_000_000)
    t.add_argument("--passos", type=int, default=0)
    t.add_argument("--seq-len", type=int, default=2048)
    t.add_argument("--micro-batch", type=int, default=4)
    t.add_argument("--grad-accum", type=int, default=4)
    t.add_argument("--lr", type=float, default=3e-3)
    t.add_argument("--refazer", action="store_true")

    a = sub.add_parser("avaliar")
    a.add_argument("--sementes", default="42,43,44")
    a.add_argument("--seq-len", type=int, default=2048)
    a.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda",
                   help="cpu usa fp32 — REGUA DIFERENTE da bf16/cuda, nunca misturar")
    a.add_argument("--bytes-holdout", type=int, default=1_500_000,
                   help="teto de BYTES por idioma — mesmo orcamento em todos")

    args = ap.parse_args()
    return {"preparar": preparar, "treinar": treinar, "avaliar": avaliar}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
