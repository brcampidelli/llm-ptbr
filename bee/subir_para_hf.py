"""Sobe o Bee-350M para o Hugging Face, com model card gerado a partir dos numeros medidos.

🔑 O TOKEN NUNCA E' PASSADO NA LINHA DE COMANDO NEM COLADO NO TERMINAL. Ele vem de variavel
   de ambiente, alimentada pelo cofre de Secrets do RunPod (ou do Colab). A licao esta
   registrada no projeto: um token ja vazou por ter sido colado numa celula.

⚠️ Container com pouca RAM: o Xet vem DESLIGADO por padrao aqui (ver o comentario no
   corpo). Sem isso, um pod de 488 MB mata o upload no meio com um "Killed" seco.

Uso (no pod, com o secret HF_TOKEN cadastrado no RunPod):
    python bee/subir_para_hf.py --modelo /workspace/bee-350m/modelo \
                                --repo BrCamp/bee-350m-pt-base
    python bee/subir_para_hf.py ... --privado      # se nao for publicar ainda
    python bee/subir_para_hf.py ... --so-card      # imprime o card e sai, sem subir nada
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Numeros medidos em 2026-08-19. Ver docs/bee-350m-resultado-final.md.
CARD = """---
language: [pt]
license: apache-2.0
library_name: transformers
pipeline_tag: text-generation
tags: [portuguese, pt-br, from-scratch, bee]
---

# Bee-350M PT (base)

Modelo de linguagem de **345,4M parametros** pre-treinado **do zero em portugues**, com
tokenizador proprio de 32k. Nao e' fine-tune de nada: pesos aleatorios -> 21,75B tokens.

Este e' o modelo **BASE**. Ele nao segue instrucoes — para isso e' preciso SFT.

## Resultado medido

`bits-por-byte` (bpb) num holdout limpo do fineweb-2 PT (400 documentos, sha256
`2273c5e4…9663e028c`). **Menor e' melhor.** bpb e' agnostico ao tokenizador, entao compara
modelos com vocabularios diferentes de forma justa.

| modelo | parametros | tokens | tok/param | bpb |
|---|---:|---:|---:|---:|
| **Bee-350M (este)** | 345,4M | 21,75B | 63 | **0,8207** |
| Bee-150M | 151,2M | 21,75B | 143 | 0,8438 |

O Bee-350M supera o Bee-150M em **2,76%** usando **3,3x menos tokens por parametro**.

## Como foi treinado

| | |
|---|---|
| arquitetura | Llama-like, 32 camadas, d_model 960, 15q/5kv GQA, intermediate 2560 |
| contexto | 2048 tokens |
| corpus | 21,75B tokens de portugues (fineweb-2 PT + dominio publico) |
| schedule | WSD — warmup 2%, plato em 55% do pico, decaimento `1-sqrt(t)` nos ultimos 20% |
| LR de pico | 2,181e-03 (Step Law) |
| hardware | 1x RTX 5090, 115,5 h |
| custo | ~US$ 118 |

## O que aprendemos treinando ele

Dois resultados medidos que valem mais que o modelo:

1. **O decaimento de LR vale ~10% de bpb.** O mesmo modelo, nos mesmos 15,00B tokens, mede
   0,9167 no plato e **0,8223** decaido. Comparar marcos intermediarios de modelos com
   schedules diferentes mede o *schedule*, nao o modelo.
2. **O volume de tokens saturou antes da escala.** 15,00B -> 21,75B (**+45% de dado**)
   rendeu **0,19%** de bpb. Ja 151M -> 345M parametros rendeu **2,76%**.

## Limitacoes

- Modelo **base**: nao segue instrucoes, nao conversa, nao usa ferramentas.
- 345M parametros e 2048 de contexto — alucina fatos com facilidade.
- Treinado predominantemente em web PT; herda os vieses dessa fonte.
- `bpb` mede modelagem de linguagem. Fluencia de resposta e uso de ferramenta so' se medem
  pos-SFT, por execucao.

## Uso

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("{repo}")
modelo = AutoModelForCausalLM.from_pretrained("{repo}")
ids = tok("O Brasil e' um pais", return_tensors="pt")
print(tok.decode(modelo.generate(**ids, max_new_tokens=40)[0]))
```
"""


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", type=Path, required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--privado", action="store_true")
    ap.add_argument("--so-card", action="store_true",
                    help="imprime o model card e sai — nao sobe nada, nao precisa de token")
    a = ap.parse_args()

    card = CARD.replace("{repo}", a.repo)
    if a.so_card:
        print(card)
        return 0

    # 🔴 GUARDA 1: o modelo existe e esta completo?
    faltando = [f for f in ("config.json", "model.safetensors", "tokenizer.json")
                if not (a.modelo / f).exists()]
    if faltando:
        print(f"🔴 ABORTA: falta {faltando} em {a.modelo}", file=sys.stderr)
        return 1
    mb = sum(f.stat().st_size for f in a.modelo.rglob("*") if f.is_file()) / 1e6
    print(f"  modelo  {a.modelo} · {mb:.0f} MB · {len(list(a.modelo.iterdir()))} arquivos")

    # 🔴 GUARDA 2: o token vem do AMBIENTE. Nunca de argumento — argumento vai para o
    #    histórico do shell, para o `ps` de qualquer processo e para os logs.
    token = (os.environ.get("HF_TOKEN")
             or os.environ.get("RUNPOD_SECRET_HF_TOKEN")
             or os.environ.get("HUGGING_FACE_HUB_TOKEN"))
    if not token:
        print("🔴 ABORTA: sem token no ambiente.", file=sys.stderr)
        print("   Cadastre HF_TOKEN no cofre de Secrets do RunPod e injete no pod.",
              file=sys.stderr)
        print("   NAO passe o token como argumento nem cole no terminal.", file=sys.stderr)
        return 1

    # 🔴 XET DESLIGADO, E ISSO NAO E' OPCIONAL AQUI.
    #    O backend Xet faz dedup em RAM antes de enviar. Num container com pouca memoria
    #    ele estoura: medido em 2026-08-19 num pod de **488 MB** de cgroup — o processo
    #    morreu com "Killed" aos 656 MB de 1,38 GB, sem traceback, so' a palavra Killed.
    #    Com HF_HUB_DISABLE_XET=1 o mesmo upload passou em 37 s a 37 MB/s.
    #    ⚠️ A licao ja estava registrada no projeto (uso do Drive) e mesmo assim foi
    #    repetida — por isso agora ela mora no codigo, e nao so' na memoria.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    quem = api.whoami()
    print(f"  conta   {quem['name']}")
    dono = a.repo.split("/")[0]
    orgs = {o["name"] for o in quem.get("orgs", [])}
    if dono != quem["name"] and dono not in orgs:
        print(f"🔴 ABORTA: '{dono}' nao e' a conta nem uma org dela.", file=sys.stderr)
        return 1

    print(f"  destino {a.repo} ({'PRIVADO' if a.privado else 'PUBLICO'})")
    api.create_repo(a.repo, repo_type="model", private=a.privado, exist_ok=True)
    (a.modelo / "README.md").write_text(card, encoding="utf-8")
    api.upload_folder(folder_path=str(a.modelo), repo_id=a.repo, repo_type="model",
                      commit_message="Bee-350M PT base — 21,75B tokens, bpb 0,8207")
    print(f"\n✅ https://huggingface.co/{a.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
