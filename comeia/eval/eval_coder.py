"""Avaliação da abelha CODER — pass@1 por EXECUÇÃO (o juiz é o interpretador).

Régua certa para esta abelha: a função gerada passa nos testes? Objetivo, barato e
sem alucinação de juiz. Nada de múltipla escolha (foi a régua errada que fez o SFT
generalista parecer "sem resultado").

⭐ USO MAIS IMPORTANTE — medir o BASE ANTES de treinar. A lição do dia: o SFT
generalista PT-BR desperdiçou esforço porque o base já era forte (0,93 no belebele,
sem espaço). A abelha agêntica funcionou porque o base estava em 45,7% (muito
espaço). Se o base já resolver quase tudo aqui, NÃO vale treinar — e é melhor
descobrir isso em 10 minutos de avaliação que em 3 horas de GPU.

Mede:
  pass@1        — % de funções que passam em TODOS os asserts
  sintaxe ok    — % que ao menos parseia/roda (separa "errou a lógica" de "nem compila")
  sem código    — % de respostas em que não veio código nenhum
  motivos       — distribuição das falhas (assert / erro de execução / timeout)

Uso:
    python eval/eval_coder.py --limit 30                       # BASE (referência)
    python eval/eval_coder.py --peft <adapter> --limit 30
    python eval/eval_coder.py --limit 0 --tag base-completo
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl, strip_think  # noqa: E402
from code_exec import extract_code, run_tests  # noqa: E402

DEFAULT_TASKS = ROOT / "data" / "raw" / "coder_tasks.jsonl"

SYSTEM = (
    "Você é um programador Python. Complete a função pedida. Responda SOMENTE com o "
    "código da função completa, dentro de um bloco ```python. Sem explicação antes "
    "ou depois. A função deve ser pura: sem input(), open(), os, sys ou rede."
)

# Prompt para modelo BASE, que não tem chat template. Fica o mais próximo possível do
# formato de continuação natural: a assinatura já começa, e o modelo só precisa seguir.
MOLDE_BASE = "# {sistema}\n\n{prompt}"


def guarda_modelo_do_projeto(nome: str, permitir_terceiro: bool) -> None:
    """🔴 Aborta se o modelo avaliado não for do projeto.

    A mesma guarda do `sft_qlora.py`, e pelo mesmo motivo: o default deste arquivo era
    `Qwen/Qwen3.5-4B`, herdado de quando ele foi escrito para outra coisa. Rodar o baseline
    do Bee com o default errado produz um número plausível de um modelo que não é o nosso —
    e nada no relatório denunciaria, porque o campo `modelo` sairia preenchido e correto.
    """
    if "bee" in nome.lower() or permitir_terceiro:
        return
    print(f"\n[ABORTADO] '{nome}' nao parece um modelo do projeto Bee.", file=sys.stderr)
    print("Se e' proposital (baseline externo), passe --permitir-modelo-de-terceiros.",
          file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BrCamp/bee-350m-pt-base")
    ap.add_argument("--peft", default=None)
    ap.add_argument("--permitir-modelo-de-terceiros", action="store_true")
    ap.add_argument("--quatro-bits", action="store_true",
                    help="quantiza em 4 bits. NAO e' mais o padrao: o base bf16 sao 691 MB, "
                         "e o QLoRA custa 20-30%% de throughput para poupar memoria que "
                         "nao falta")
    ap.add_argument("--chat", action="store_true",
                    help="usa o chat template. So' DEPOIS do SFT: o base nunca viu "
                         "<|im_start|>, e o tokenizador oferece um ChatML padrao que "
                         "engana a deteccao automatica")
    ap.add_argument("--dry-run", action="store_true",
                    help="valida tarefas e gabaritos sem carregar modelo")
    ap.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--limit", type=int, default=30, help="0 = todas")
    ap.add_argument("--max-new", type=int, default=420,
                    help="codigo precisa de mais tokens que JSON de tool-call")
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--show-fails", type=int, default=4)
    args = ap.parse_args()

    tasks = [t for t in read_jsonl(args.tasks) if t.get("prompt") and t.get("tests")]
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        print(f"ERRO: nenhuma tarefa em {args.tasks}", file=sys.stderr)
        return 1

    guarda_modelo_do_projeto(args.model, args.permitir_modelo_de_terceiros)

    # 🔴 O TETO DO CONJUNTO, EXECUTADO ANTES DE CARREGAR O MODELO. Tarefa cujo gabarito nao
    #    passa no proprio teste e' impossivel por construcao, e o sintoma nao aparece no
    #    resultado: um modelo que acerta 40% num conjunto de teto 92% parece um modelo de 40%.
    from code_exec import run_tests as _rt
    ruins = [t["name"] for t in tasks
             if t.get("solution") and not _rt(t["solution"], t["tests"]).ok
             and not _rt(t["prompt"] + "\n" + t["solution"], t["tests"]).ok]
    if ruins:
        print(f"⚠️ TETO ABAIXO DE 100%: {len(ruins)}/{len(tasks)} gabaritos falham no proprio "
              f"teste: {ruins[:6]}", file=sys.stderr)
        print("   O pass@1 medido abaixo esta' descontado desse teto.", file=sys.stderr)
    else:
        print(f"✅ teto do conjunto verificado: {len(tasks)}/{len(tasks)} gabaritos executam")

    if args.dry_run:
        print("\n✅ DRY-RUN: tarefas e gabaritos validados. Nenhum modelo foi carregado.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    kwargs: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if args.quatro_bits:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
        )
    print(f"modelo : {args.model}")
    print(f"adapter: {args.peft or '(base, sem adapter)'}")
    print(f"tarefas: {len(tasks)} de {args.tasks.name}\n")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    if args.peft:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    n_pass = n_nocode = 0
    motivos: Counter[str] = Counter()
    falhas: list[tuple[str, str]] = []

    for i, t in enumerate(tasks, 1):
        # 🔴 O CHAT TEMPLATE E' ESCOLHA EXPLICITA (--chat), NAO DETECCAO AUTOMATICA.
        #    A primeira versao desta linha perguntava `if tok.chat_template` — e o
        #    BrCamp/bee-350m-pt-base responde **True**: o `TokenizersBackend` fornece um
        #    template ChatML padrao mesmo sem nada no tokenizer_config.json. So' que o base
        #    foi pre-treinado em texto cru e **nunca viu `<|im_start|>`** (os tokens existem
        #    no vocabulario, reservados para o SFT, e praticamente nao aparecem no corpus).
        #    Medir o base atraves desse template mede a reacao dele a tokens ineditos, e o
        #    sintoma sai como "o base nao sabe programar" — conclusao sobre o modelo apoiada
        #    num artefato do aparato, que e' o erro assinatura deste projeto.
        #    Regra: BASE = prompt simples. Depois do SFT com ChatML = --chat.
        if args.chat:
            msgs = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": t["prompt"]}]
            tpl = {"add_generation_prompt": True, "return_tensors": "pt", "return_dict": True}
            try:
                enc = tok.apply_chat_template(msgs, enable_thinking=False, **tpl)
            except TypeError:
                enc = tok.apply_chat_template(msgs, **tpl)
        else:
            enc = tok(MOLDE_BASE.format(sistema=SYSTEM, prompt=t["prompt"]),
                      return_tensors="pt")
        inputs = {k: v.to("cuda") for k, v in dict(enc).items() if hasattr(v, "to")}
        plen = inputs["input_ids"].shape[1]
        with torch.no_grad():
            g = model.generate(**inputs, max_new_tokens=args.max_new, do_sample=False,
                               pad_token_id=tok.eos_token_id)
        raw = tok.decode(g[0][plen:], skip_special_tokens=True).strip()
        answer, _ = strip_think(raw)
        code = extract_code(answer)

        if not code:
            n_nocode += 1
            motivos["sem codigo"] += 1
            falhas.append((t["name"], "nao devolveu codigo"))
        else:
            res = run_tests(code, t["tests"], timeout=args.timeout)
            if res.ok:
                n_pass += 1
            else:
                # categoriza o motivo (separa "errou a logica" de "nem roda")
                r = res.reason
                cat = ("timeout" if "timeout" in r else
                       "assert falhou" if "assert falhou" in r else
                       "padrao proibido" if "proibido" in r else
                       "erro de execucao")
                motivos[cat] += 1
                falhas.append((t["name"], r[:110]))

        if i % 10 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  pass@1 parcial: {n_pass/i:.1%}", flush=True)

    n = len(tasks)
    rodou = n - n_nocode
    print("\n" + "=" * 66)
    print(f"tarefas avaliadas   : {n}")
    print(f"⭐ pass@1 (execucao) : {n_pass}/{n} = {n_pass/n:.1%}")
    print(f"devolveu codigo      : {rodou}/{n} = {rodou/n:.1%}")
    if rodou:
        print(f"pass@1 entre as que devolveram codigo: {n_pass}/{rodou} = {n_pass/rodou:.1%}")
    print("-" * 66)
    print("motivos das falhas:")
    for k, v in motivos.most_common():
        print(f"   {k:<20} {v:>3}  ({v/n:.0%})")
    print("=" * 66)

    if args.show_fails and falhas:
        print(f"\nprimeiras {min(args.show_fails, len(falhas))} falhas:")
        for nome, r in falhas[: args.show_fails]:
            print(f"   {nome}: {r}")

    if args.tag:
        outdir = ROOT / "eval" / "results"
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / f"coder_{args.tag}.json"
        p.write_text(json.dumps({
            "tag": args.tag, "model": args.model, "peft": args.peft,
            "n": n, "pass1": n_pass / n, "n_pass": n_pass,
            "no_code": n_nocode, "motivos": dict(motivos),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsalvo em {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
