"""Gera o notebook do gate pareado para o Colab (autocontido, sem clonar o repo)."""
import json
from pathlib import Path

INTRO = """# Gate pareado do Bee — corpus CRU x FILTRADO

Testa se **filtrar por valor educacional melhora o modelo com o MESMO orcamento de tokens**.

**Por que este gate existe:** o Bee v3 custou US$ 34 e 21,76 h de A100 para mover o bpb em 0,1%.
Um gate pareado responde a mesma pergunta *antes* do run longo.

**A armadilha de metodo:** medir na distribuicao crua faz o braco cru ganhar de graca; medir na
filtrada, o inverso. O holdout que decide e a **Wikipedia PT** — fonte diferente do fineweb-2, que
nenhum dos dois bracos ve no treino. O holdout cru vai junto **de proposito**, porque favorece o
braco nao-filtrado: mostrar os dois lados e mais honesto que reportar so o que confirma.

**Pareamento:** mesma arquitetura, semente, passos, LR e schedule. E mesmo numero de **TOKENS**,
nao de documentos — documento bom e mais longo, entao parear por documento daria mais token ao
filtrado e o experimento mediria orcamento, nao qualidade.

Resultado anterior a 13,1M tokens: **+0,77%** no holdout neutro (IC 95% [+0,43%, +1,09%]).
Esta rodada e 10x maior — a pergunta e se o ganho **cresce com escala ou satura**."""

ARQ = """## 2. Arquitetura — a MESMA do Bee-150M

`LlamaConfig` sem codigo de modelagem custom. Esta geometria esta validada por comparacao: e
byte a byte a mesma do SmolLM2-135M e do MobileLLM-125M."""

TREINO_MD = """## 3. Treino dos dois bracos

**micro-batch:** na RTX 5070 (8 GB) o teto medido e 4 — acima disso a VRAM vaza para a RAM do host
e o passo cai ~12x, **sem dar OOM**. Na L4 (22 GB) cabe bem mais."""

PREP_MD = """## 2. Preparo dos dados (FASE 1 — runtime CPU)

O preparo e trabalho de **CPU**: pontuar e tokenizar ~1,26M documentos. Rodar isso numa sessao
L4 queimaria ~2 h de cota de GPU sem usar a GPU. **Rode esta celula em runtime CPU**, depois
troque para L4 e siga da secao 3 — os `.bin` ficam na Drive e sobrevivem a troca.

O braco filtrado e o gargalo: com retencao de ~7,5% ele precisa varrer ~1,26M docs para render
130M tokens, contra ~180k do braco cru."""

AVAL_MD = """## 4. Avaliacao — bits-por-byte nos dois holdouts

Contar os bytes do **trecho realmente pontuado**, nao do documento inteiro. Somar bits de
`SEQ_LEN` tokens e dividir pelos bytes do doc completo subestima o bpb em ~1,7x — foi um bug real
desta analise, pego por checagem de ordem de grandeza contra um numero conhecido, nao por revisao
de codigo."""

LEITURA = """## 5. Leitura

**A coluna que decide e `ganho`** (holdout neutro da Wikipedia), e a pergunta e a TENDENCIA ao
longo dos passos, nao o valor final isolado:

- **cresce** com a escala -> filtrar se paga; vale coletar os 257 GB e filtrar antes do run longo
- **satura** perto de +0,8% (o valor medido a 13M tokens) -> filtragem e detalhe, o gargalo e outro
- **encolhe ou vira negativo** -> a filtragem tirou diversidade; nao escalar assim

`filt_raw` pior que `cru_raw` e **esperado** e nao invalida: um modelo treinado so em texto
educacional modela pior a web crua."""

C_GPU = "!nvidia-smi --query-gpu=name,memory.total --format=csv"

C_CLONE = """!git clone -q https://github.com/brcampidelli/llm-ptbr.git /content/bee 2>/dev/null || (cd /content/bee && git pull -q)
!pip -q install 'transformers>=4.44' accelerate safetensors joblib scikit-learn pyarrow huggingface_hub datasets zstandard
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/BEE/gate
!cp -r /content/bee/models/bee-150m-v3-base /content/drive/MyDrive/BEE/gate/tokenizer 2>/dev/null; echo pronto"""

C_PREP = """# FASE 1 — PREPARO (rode em runtime CPU: nao gasta cota de GPU).
# Baixa parquets do fineweb-2, pontua com o classificador e escreve os dois bracos.
# ~1-2 h. Se os .bin ja existirem na Drive, esta celula pula sozinha.
import os, subprocess, shutil, glob

DRIVE = "/content/drive/MyDrive/BEE/gate"
if os.path.exists(f"{DRIVE}/filtrado.bin"):
    print("ja existe na Drive — pulando o preparo")
else:
    r = subprocess.run(
        ["python", "bee/gate_preparar_stream.py", "--tokens", "130e6",
         "--classificador", "bee/edu/classificador.joblib"],
        cwd="/content/bee", text=True)
    assert r.returncode == 0, "o preparo falhou — veja o log acima"
    for f in glob.glob("/content/bee/bee/gate/*.bin") + glob.glob("/content/bee/bee/gate/*.json"):
        shutil.copy(f, DRIVE)
    print("copiado para a Drive:", os.listdir(DRIVE))"""

C_DEPS = """!pip -q install 'transformers>=4.44' accelerate safetensors
from google.colab import drive
drive.mount('/content/drive')"""

C_PATHS = '''BASE = "/content/drive/MyDrive/BEE/gate"
TOKENIZER = f"{BASE}/tokenizer"      # pasta com tokenizer.json + tokenizer_config.json
import os
for f in ("cru.bin", "filtrado.bin", "holdout_wiki.json", "holdout_cru.json"):
    p = f"{BASE}/{f}"
    ok = os.path.exists(p)
    print("OK   " if ok else "FALTA", f, f"{os.path.getsize(p)/1e6:.0f} MB" if ok else "")'''

C_ARQ = '''from transformers import LlamaConfig, LlamaForCausalLM, AutoTokenizer
import torch, numpy as np, time, json, math, glob

SEQ_LEN = 512

def novo_modelo():
    return LlamaForCausalLM(LlamaConfig(
        vocab_size=32000, hidden_size=576, intermediate_size=2048,
        num_hidden_layers=30, num_attention_heads=9, num_key_value_heads=3,
        head_dim=64, max_position_embeddings=SEQ_LEN, rope_theta=10000.0,
        rms_norm_eps=1e-5, tie_word_embeddings=True,
        bos_token_id=0, eos_token_id=0, pad_token_id=3, attention_bias=False))

print(f"{sum(p.numel() for p in novo_modelo().parameters())/1e6:.1f}M params")'''

C_TREINO = '''MICRO, ACUM, PASSOS, LR, SEED = 16, 4, 4000, 3e-3, 42
print(f"tokens/passo {MICRO*ACUM*SEQ_LEN:,} - total {MICRO*ACUM*SEQ_LEN*PASSOS/1e6:.0f}M")

def treinar(nome):
    torch.manual_seed(SEED); np.random.seed(SEED)      # mesma semente nos dois
    dados = np.fromfile(f"{BASE}/{nome}.bin", dtype=np.uint16)
    m = novo_modelo().cuda()
    opt = torch.optim.AdamW(m.parameters(), lr=LR, betas=(0.9, 0.95), weight_decay=0.1)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=PASSOS,
                                              pct_start=0.02, anneal_strategy="cos")
    m.train(); t0 = time.time()
    ckpts = {int(PASSOS * f) for f in (0.25, 0.5, 0.75)}
    for passo in range(PASSOS):
        opt.zero_grad(set_to_none=True); acc = 0.0
        for _ in range(ACUM):
            i = np.random.randint(0, len(dados) - SEQ_LEN - 1, size=MICRO)
            x = torch.from_numpy(np.stack([dados[j:j+SEQ_LEN] for j in i]).astype(np.int64)).cuda()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                p = m(input_ids=x, labels=x).loss / ACUM
            p.backward(); acc += p.item()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); sch.step()
        if passo % 100 == 0:
            print(f"  {nome} {passo}/{PASSOS} perda {acc:.3f} {(time.time()-t0)/60:.0f}min", flush=True)
        # checkpoints: a pergunta e se o ganho CRESCE com escala — um numero
        # no fim responde menos que a curva.
        if (passo + 1) in ckpts:
            m.save_pretrained(f"{BASE}/modelo_{nome}_p{passo+1}")
    m.save_pretrained(f"{BASE}/modelo_{nome}")
    del m, opt; torch.cuda.empty_cache()
    return (time.time() - t0) / 60

for n in ("cru", "filtrado"):
    print(f"=== {n} === {treinar(n):.0f} min")'''

C_AVAL = '''tok = AutoTokenizer.from_pretrained(TOKENIZER)
LN2 = math.log(2.0)

def bpb(dir_modelo, holdout):
    m = LlamaForCausalLM.from_pretrained(dir_modelo, torch_dtype=torch.bfloat16).cuda().eval()
    textos = json.load(open(f"{BASE}/holdout_{holdout}.json"))
    bits = byts = 0
    with torch.no_grad():
        for t in textos:
            ids = tok(t, add_special_tokens=False,
                      return_tensors="pt")["input_ids"][:, :SEQ_LEN].cuda()
            if ids.shape[1] < 2:
                continue
            nb = len(tok.decode(ids[0], skip_special_tokens=True).encode("utf-8"))
            lg = m(ids).logits
            bits += torch.nn.functional.cross_entropy(
                lg[0, :-1].float(), ids[0, 1:], reduction="sum").item() / LN2
            byts += nb
    del m; torch.cuda.empty_cache()
    return bits / byts

pontos = sorted({d.split("_p")[-1] for d in glob.glob(f"{BASE}/modelo_cru_p*")}, key=int) + ["final"]
cab = ("passos".rjust(8) + "cru wiki".rjust(12) + "filt wiki".rjust(12)
       + "ganho".rjust(9) + "cru raw".rjust(10) + "filt raw".rjust(10))
print(cab)
linhas = []
for p in pontos:
    suf = "" if p == "final" else f"_p{p}"
    cw = bpb(f"{BASE}/modelo_cru{suf}", "wiki")
    fw = bpb(f"{BASE}/modelo_filtrado{suf}", "wiki")
    cr = bpb(f"{BASE}/modelo_cru{suf}", "cru")
    fr = bpb(f"{BASE}/modelo_filtrado{suf}", "cru")
    g = (cw - fw) / cw
    linhas.append({"passos": p, "cru_wiki": cw, "filt_wiki": fw,
                   "ganho": g, "cru_raw": cr, "filt_raw": fr})
    print(f"{p:>8}{cw:>12.4f}{fw:>12.4f}{g:>+9.2%}{cr:>10.4f}{fr:>10.4f}")
json.dump(linhas, open(f"{BASE}/resultado_130M.json", "w"), indent=2)'''


def md(txt):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in txt.split("\n")]}


def code(txt):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": [l + "\n" for l in txt.split("\n")]}


nb = {
    "cells": [md(INTRO), code(C_GPU), md("## 1. Repo, dependencias e Drive"), code(C_CLONE),
              md(PREP_MD), code(C_PREP), code(C_PATHS), md(ARQ), code(C_ARQ), md(TREINO_MD), code(C_TREINO),
              md(AVAL_MD), code(C_AVAL), md(LEITURA)],
    "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "L4"},
                 "kernelspec": {"display_name": "Python 3", "name": "python3"},
                 "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 0,
}
saida = Path(__file__).parent / "gate_pareado_bee.ipynb"
saida.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"notebook: {saida} ({len(nb['cells'])} celulas)")
