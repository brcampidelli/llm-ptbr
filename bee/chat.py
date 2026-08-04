"""Conversar com o Bee (base ou pos-SFT) — o teste que realmente importa.

Uso:
    python bee/chat.py                                   # usa o SFT local
    python bee/chat.py --modelo BrCamp/bee-150m-v3       # o BASE (compara antes/depois)
    python bee/chat.py --sonda                           # roda 8 perguntas fixas e sai
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PADRAO = ROOT / "models" / "bee-150m-v3-sft"

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
    ap.add_argument("--modelo", default=str(PADRAO))
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
    print(f"pronto ({dispositivo}) · chat_template: {'sim' if tem_template else 'NAO — usando texto cru'}\n")

    def responder(pergunta: str) -> str:
        if tem_template:
            texto = tok.apply_chat_template([{"role": "user", "content": pergunta}],
                                            tokenize=False, add_generation_prompt=True)
        else:
            texto = pergunta
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
