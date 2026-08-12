"""Conversar com o Bee (base ou pos-SFT) — o teste que realmente importa.

Uso:
    python bee/chat.py                                   # o SFT publicado
    python bee/chat.py --modelo BrCamp/bee-150m-pt-base  # o BASE (compara antes/depois)
    python bee/chat.py --sonda                           # roda 8 perguntas fixas e sai
    python bee/chat.py --system comeia/data/agentic_system.txt   # com catalogo de ferramentas

⚠️ 2026-08-12: dois defeitos consertados aqui, ambos capazes de invalidar qualquer
impressao formada sobre o modelo:

  1. NAO se enviava system message. O SFT agentico foi treinado com o catalogo de
     ferramentas SEMPRE presente no system; servir sem ele e perguntar ao modelo por
     ferramentas que, do ponto de vista dele, nao existem. Mesmo defeito que a COMEIA ja
     tinha corrigido em 2026-07-25 ("treinado com o catalogo a vista, servido as cegas") —
     reintroduzido do lado do Bee.
  2. O --modelo default apontava para models/bee-150m-v3-sft, que e a rodada ANTIGA
     (max_seq_len 1024, 3 epocas, lr 2e-5 — a que descartou 100% do agentico em silencio)
     e cujo tokenizer nem tem chat_template, caindo no caminho de "texto cru".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PADRAO = "BrCamp/bee-150m-pt-sft"

SONDAS = [
    "O que e o Brasil?",
    "Explique o que e fotossintese.",
    "Escreva uma frase sobre o mar.",
    "Qual a capital de Minas Gerais?",
    "Liste tres frutas brasileiras.",
    "Como se faz um bolo de cenoura?",
    "Traduza para o ingles: bom dia.",
    "Quem foi Machado de Assis?",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=PADRAO)
    ap.add_argument("--system", type=Path,
                    help="arquivo com o system prompt (ex.: o catalogo de ferramentas). "
                         "Sem isto o modelo agentico e servido as cegas.")
    ap.add_argument("--max-novos", type=int, default=120)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--sonda", action="store_true", help="roda as perguntas fixas e sai")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"carregando {args.modelo}...")
    tok = AutoTokenizer.from_pretrained(args.modelo)
    modelo = AutoModelForCausalLM.from_pretrained(args.modelo, dtype=torch.bfloat16)
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    modelo.to(dispositivo).eval()

    tem_template = getattr(tok, "chat_template", None) is not None
    print(f"pronto ({dispositivo}) · chat_template: {'sim' if tem_template else 'NAO — usando texto cru'}")

    system = None
    if args.system:
        if not args.system.exists():
            print(f"ERRO: system nao encontrado: {args.system}", file=sys.stderr)
            return 1
        system = args.system.read_text(encoding="utf-8").strip()
        n_sys = len(tok(system).input_ids)
        # A janela e de 2048; um catalogo grande come metade dela antes do usuario falar.
        print(f"system: {args.system.name} · {n_sys} tokens "
              f"({n_sys / 2048:.0%} da janela de 2048)")
    print()

    def responder(pergunta: str) -> str:
        if tem_template:
            msgs = ([{"role": "system", "content": system}] if system else []) \
                + [{"role": "user", "content": pergunta}]
            texto = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        else:
            texto = f"{system}\n\n{pergunta}" if system else pergunta
        ent = tok(texto, return_tensors="pt").to(dispositivo)
        with torch.no_grad():
            saida = modelo.generate(**ent, max_new_tokens=args.max_novos,
                                    temperature=args.temp, top_p=args.top_p,
                                    do_sample=True, pad_token_id=tok.pad_token_id or tok.eos_token_id)
        return tok.decode(saida[0][ent["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    if args.sonda:
        for i, p in enumerate(SONDAS, 1):
            print(f"[{i}] voce> {p}")
            print(f"    bee > {responder(p)}\n")
        return 0

    print("Digite sua pergunta (ou 'sair'):\n")
    while True:
        try:
            pergunta = input("voce> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if pergunta.lower() in {"sair", "exit", "quit", ""}:
            break
        print(f"bee > {responder(pergunta)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
