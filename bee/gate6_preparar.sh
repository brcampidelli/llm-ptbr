#!/usr/bin/env bash
# Gate #6 do estudo do arXiv (2609.11917: repeticao em modelo DENSO) — PREPARO DOS DADOS, no pod.
#
# Fonte: /workspace/bee1g/pool/train.bin (20B tokens, 64k-multi, pt-50). Layout MEDIDO em 2026-09-16
# decodificando 60 tokens em cada fronteira: [PT 10.000.048.114][spa][fra][deu][eng][arb][cmn][jpn],
# cada idiomas nao-PT com 1.428.572.570 tokens contiguos (ordem IDIOMAS de tokenizar_naopt_1g.py).
# Nada e' re-tokenizado: sao fatias por memmap. Vai para o disco do container (nao disputa I/O).
#
# BRACOS (2x2 fatorial, declarado antes de rodar):
#   jpn_unico      1,0B tokens UNICOS de jpn                                 (R=1, so' jpn)
#   jpn_rep8       125M tokens unicos de jpn, LADRILHADOS 8x = 1,0B          (R=8, so' jpn)
#   jpn_unico_mix  1,0B jpn unicos + 1,0B PT unicos = 2,0B                   (R=1, misturado)
#   jpn_rep8_mix   125M jpn x 8 = 1,0B + 1,0B PT unicos = 2,0B               (R=8, misturado)
#   val.bin de TODOS = holdout limpo de jpn (pool/val_naopt_partes/jpn.bin, sha1%100<2, 2,8M tok)
# ⚠️ O ladrilho e' embaralhado pelo pretrain junto com tudo (permutacao de blocos): as 8 copias
#    ficam espalhadas, nao em epocas sequenciais. E' o regime de um corpus misto com idioma
#    repetido — o caso real do proximo run — e vai declarado.
# ⚠️ A mistura e' 50/50 jpn/PT, nao os 7% do pt-50: testa "PT unico ao lado de jpn repetido",
#    nao a diluicao exata do run. Declarado no docstring do consolidador.
#
# Uso: bash bee/gate6_preparar.sh   (no pod com /workspace/bee1g montado; escreve em /root/gate6/dados, disco do container)
set -eu
POOL=${POOL:-/workspace/bee1g/pool}; DEST=${DEST:-/root/gate6/dados}; TOK=${TOK:-/workspace/bee1g/bee/tok_t1/64k-multi}
mkdir -p "$DEST"
python3 - "$POOL" "$DEST" "$TOK" <<'PY'
import hashlib, json, pathlib, sys
import numpy as np
from transformers import AutoTokenizer
pool, dest, tokp = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
meta = json.load(open(pool / "meta.json"))
PT, NPT = meta["pt_tokens"], meta["naopt_tokens"]
L = NPT // 7                                   # ≈1.428.572.570 por idioma (NPT nao e' multiplo exato de 7: sobra <7 tokens)
assert abs(NPT - 7 * L) < 100, (NPT, L)
tr = np.memmap(pool / "train.bin", dtype=np.uint16, mode="r")
assert len(tr) == PT + NPT, (len(tr), PT + NPT)
U, K, R = 1_000_000_000, 125_000_000, 8
JPN0 = len(tr) - U                             # jpn e' o ULTIMO bloco (1,43B): os ultimos 1,0B tokens sao jpn com certeza
tok = AutoTokenizer.from_pretrained(tokp)
KANA = lambda s: any("぀" <= c <= "ヿ" for c in s)

def texto(a, b, n=400):
    return tok.decode(np.asarray(tr[a:a + n]).tolist())

# ── GUARDAS de layout (§2t: a fatia errada nao da' erro — treinaria outro idioma em silencio)
assert all(KANA(texto(JPN0 + d, 0)) for d in (1000, K // 2, K, U // 2, U - 5000)), "fatia jpn sem kana em algum ponto"
assert not KANA(texto(len(tr) - L - 100000, 0)), "kana antes do bloco jpn (deveria ser cmn) — layout diferente do medido"
assert not KANA(texto(0, 0)) and not KANA(texto(PT // 2, 0)) and not KANA(texto(U - 5000, 0)), "kana no bloco PT"
print(f"layout confirmado: PT [0, {PT:,}) · fatia jpn [{JPN0:,}, {len(tr):,}) = {U:,} tokens (bloco jpn ≈ {L:,})")

jpn_u = np.asarray(tr[JPN0: JPN0 + U])                     # 1,0B unicos
jpn_k = np.asarray(tr[JPN0: JPN0 + K])                     # os 125M primeiros (subconjunto dos unicos)
jpn_r = np.tile(jpn_k, R)                                  # 1,0B = 125M x 8
pt_u = np.asarray(tr[0: U])                                # 1,0B PT unicos
val = np.fromfile(pool / "val_naopt_partes" / "jpn.bin", dtype=np.uint16)
assert KANA(tok.decode(val[:300].tolist())), "val jpn sem kana"
bracos = {
    "jpn_unico":     (jpn_u,                          {"unicos_jpn": U, "R": 1, "pt": 0}),
    "jpn_rep8":      (jpn_r,                          {"unicos_jpn": K, "R": R, "pt": 0}),
    "jpn_unico_mix": (np.concatenate([jpn_u, pt_u]),  {"unicos_jpn": U, "R": 1, "pt": U}),
    "jpn_rep8_mix":  (np.concatenate([jpn_r, pt_u]),  {"unicos_jpn": K, "R": R, "pt": U}),
}
for nome, (arr, info) in bracos.items():
    d = dest / nome; d.mkdir(parents=True, exist_ok=True)
    arr.astype(np.uint16).tofile(d / "train.bin"); val.tofile(d / "val.bin")
    m = json.load(open(pool / "meta.json")); m.update({"_gate": "6_repeticao_denso", "_braco": nome, **info,
                                                       "_val": "holdout jpn limpo (val_naopt_partes/jpn.bin)",
                                                       "_origem": str(pool / "train.bin"), "_jpn0": JPN0})
    json.dump(m, open(d / "meta.json", "w"), indent=1)
    h = hashlib.md5(open(d / "train.bin", "rb").read(1 << 26)).hexdigest()[:12]
    print(f"  {nome:14s} train {len(arr):>13,} tok · unicos jpn {info['unicos_jpn']:>13,} x R={info['R']} · PT {info['pt']:>13,} · val {len(val):,} · md5(64MB) {h}")
# ⭐ QUANTO AGIU (§2r): o ladrilho tem de ser detectavel — o mesmo bloco de 2049 tokens 8x
rep = bracos["jpn_rep8"][0]
assert np.array_equal(rep[:2049], rep[K:K + 2049]) and np.array_equal(rep[:2049], rep[7 * K:7 * K + 2049]), "ladrilho nao repete"
assert not np.array_equal(bracos["jpn_unico"][0][:2049], bracos["jpn_unico"][0][K:K + 2049]), "unico repete?!"
print("guardas: kana nos 3 pontos do bloco jpn e no val, sem kana no PT; ladrilho repete o bloco 0 nas copias 1 e 7; unico nao repete — OK")
PY
du -sh "$DEST"/*
