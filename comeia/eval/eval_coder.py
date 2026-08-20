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
    ap.add_argument("--lote", type=int, default=24,
                    help="tarefas por lote de geracao. Era 1 (implicito) ate' 2026-08-19, "
                         "o que dava 5 tarefas/min e ~2,8h nas 877")
    ap.add_argument("--jobs", type=int, default=6,
                    help="subprocessos de teste em paralelo (CPU)")
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

    # ⚠️ GERACAO EM LOTE + TESTES EM PARALELO. A versao anterior fazia uma tarefa por vez,
    #    e as duas metades eram seriais: um `generate` de batch 1 (GPU a ~30% de utilizacao)
    #    seguido de um subprocesso de teste bloqueante. Medido em 2026-08-19 no Bee-350M:
    #    **5 tarefas/min**, ou seja ~2,8 h para as 877 — e no grid do Estagio 2 esta regua
    #    roda UMA VEZ POR BRACO, o que daria 42 h em 15 bracos. Nao era incomodo, era
    #    bloqueador.
    def monta_prompt(t: dict) -> str:
        # 🔴 O CHAT TEMPLATE E' ESCOLHA EXPLICITA (--chat), NAO DETECCAO AUTOMATICA.
        #    O BrCamp/bee-350m-pt-base responde `tok.chat_template is not None` = True: o
        #    `TokenizersBackend` fornece um ChatML padrao mesmo sem nada no
        #    tokenizer_config.json. So' que o base foi pre-treinado em texto cru e **nunca
        #    viu `<|im_start|>`** (os tokens existem no vocabulario, reservados para o SFT).
        #    Medir o base por esse template mede a reacao dele a tokens ineditos, e o
        #    sintoma sai como "o base nao sabe programar" — conclusao sobre o MODELO apoiada
        #    num artefato do APARATO. Regra: BASE = prompt simples; pos-SFT = --chat.
        if args.chat:
            msgs = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": t["prompt"]}]
            try:
                return tok.apply_chat_template(msgs, tokenize=False,
                                               add_generation_prompt=True,
                                               enable_thinking=False)
            except TypeError:
                return tok.apply_chat_template(msgs, tokenize=False,
                                               add_generation_prompt=True)
        return MOLDE_BASE.format(sistema=SYSTEM, prompt=t["prompt"])

    tok.padding_side = "left"          # obrigatorio para geracao em lote em decoder-only
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    from concurrent.futures import ThreadPoolExecutor

    def julga(par):
        """Extrai o codigo e roda os testes. Devolve (nome, ok, motivo)."""
        t, raw = par
        answer, _ = strip_think(raw)
        code = extract_code(answer)
        if not code:
            return t["name"], None, "nao devolveu codigo"
        res = run_tests(code, t["tests"], timeout=args.timeout)
        return t["name"], res.ok, res.reason

    lote, i = args.lote, 0
    while i < len(tasks):
        bloco = tasks[i:i + lote]
        ent = tok([monta_prompt(t) for t in bloco], return_tensors="pt",
                  padding=True, truncation=True, max_length=1024).to("cuda")
        try:
            with torch.no_grad():
                g = model.generate(**ent, max_new_tokens=args.max_new, do_sample=False,
                                   pad_token_id=tok.pad_token_id or tok.eos_token_id)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if lote == 1:
                raise
            lote = max(1, lote // 2)
            print(f"  ⚠️ OOM — lote reduzido para {lote}, refazendo o bloco", flush=True)
            continue
        plen = ent["input_ids"].shape[1]
        brutas = [tok.decode(g[j][plen:], skip_special_tokens=True).strip()
                  for j in range(len(bloco))]
        del g
        torch.cuda.empty_cache()

        # os testes sao subprocessos de CPU: rodam em paralelo enquanto a GPU ja' poderia
        # estar no proximo bloco. Aqui ficam serializados por simplicidade, mas o paralelismo
        # interno ja' corta a maior parte do custo.
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for nome, ok, motivo in ex.map(julga, zip(bloco, brutas)):
                if ok is None:
                    n_nocode += 1
                    motivos["sem codigo"] += 1
                    falhas.append((nome, motivo))
                elif ok:
                    n_pass += 1
                else:
                    cat = ("timeout" if "timeout" in motivo else
                           "assert falhou" if "assert falhou" in motivo else
                           "padrao proibido" if "proibido" in motivo else
                           "erro de execucao")
                    motivos[cat] += 1
                    falhas.append((nome, motivo[:110]))
        i += len(bloco)
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
