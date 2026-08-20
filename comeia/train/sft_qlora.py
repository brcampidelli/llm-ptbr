"""SFT com LoRA sobre os modelos do projeto Bee.

⚠️ ESTE ARQUIVO NASCEU PARA OUTRO MODELO. Ele foi escrito quando o plano era fine-tunar um
Qwen3.5-4B de terceiros — daí o nome "qlora", os defaults apertados de 8 GB e o 4-bit
obrigatório. Aquele plano foi ABANDONADO: o projeto pré-treina modelos próprios. Em
2026-08-19 o arquivo foi reapontado (Estágio 1 do plano de pós-treino), e o que sobrou de
herança está marcado com ⚠️ no ponto exato.

O que mudou, e por quê:
  - `--model` é OBRIGATÓRIO e há guarda de nome: o default "Qwen/Qwen3.5-4B" sobreviveu ao
    abandono e teria baixado 8 GB para treinar o modelo errado sem um aviso.
  - 4-bit virou OPT-IN (`--quatro-bits`). O Bee-350M em bf16 são 691 MB.
  - `--lr` continua com o default herdado, marcado como não-validado: medir é o Estágio 2.

Uso:
    python comeia/train/sft_qlora.py --model BrCamp/bee-350m-pt-base \\
        --data comeia/data/processed/sft_misto.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# O nome antigo era "qwen3-4b-ptbr-sft": gravaria o adapter do Bee numa pasta com o nome
# do modelo que este projeto NAO treina mais. Confusao barata de evitar, cara de depurar.
DEFAULT_OUT = ROOT / "models" / "bee-sft-adapter"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    # 🔴 SEM DEFAULT, DE PROPOSITO. Este arquivo nasceu do plano de fine-tunar um
    #    Qwen3.5-4B, que foi ABANDONADO — o projeto pre-treina modelos proprios. O default
    #    antigo ("Qwen/Qwen3.5-4B") sobreviveu ao abandono: rodar isto hoje baixaria 8 GB e
    #    treinaria o modelo ERRADO sem emitir um unico aviso. Mesma familia de "o dado some
    #    e nada reclama" que ja custou tres vezes a este projeto (ver docs/licoes-de-metodo).
    #    Agora e' obrigatorio dizer qual modelo se esta treinando.
    #    Os modelos do projeto: BrCamp/bee-350m-pt-base · BrCamp/bee-150m-pt-base
    ap.add_argument("--model", required=True,
                    help="OBRIGATORIO. ex.: BrCamp/bee-350m-pt-base")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "processed" / "sft_ptbr.jsonl")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=2.0)
    # ⚠️ 2e-4 E' HERANCA DO QWEN-4B E QUASE CERTAMENTE ESTA ERRADO AQUI — mas nao vou
    #    trocar por um chute. Dois fatos que se somam: (a) o projeto MEDIU 6e-4 como otimo
    #    de full FT no Bee-150M (curva em U, ruido 0,001, docs/sft-resultado.md §1);
    #    (b) o estudo de pos-treino achou que LoRA quer LR ~10x o de full FT, quase
    #    independente do rank. Os dois juntos apontam para a casa de 6e-3, ou seja **30x**
    #    este default.
    #    🔴 Nao fixo esse valor aqui porque seria repetir o erro que custou duas semanas:
    #    herdar numero medido noutro modelo. O Estagio 2 do plano existe exatamente para
    #    medir LR, rank e lambda_prompt num grid conjunto (~US$ 7). Ate la, passe --lr
    #    explicito e saiba que o default nao foi validado para o Bee.
    ap.add_argument("--lr", type=float, default=2e-4,
                    help="⚠️ default herdado do Qwen-4B, NAO validado no Bee. Ver E2 do plano")
    ap.add_argument("--batch-size", type=int, default=1, help="por dispositivo — manter 1 em 8GB")
    ap.add_argument("--grad-accum", type=int, default=16, help="batch efetivo = batch-size * grad-accum")
    ap.add_argument("--sem-checkpointing", action="store_true",
                    help="desliga o gradient checkpointing. Ele troca ~30% de "
                         "velocidade por memoria — bom nos 8 GB da 5070, desperdicio "
                         "numa 5090 de 32 GB onde a memoria sobra")
    ap.add_argument("--sem-lora", action="store_true",
                    help="full fine-tuning, sem adapter. E o controle NEGATIVO do E2; "
                         "exige LR ~10x menor que o de LoRA")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--max-steps", type=int, default=-1,
                    help="limita os passos (use para smoke test antes do treino real)")
    ap.add_argument("--packing", action="store_true",
                    help="empacota exemplos curtos numa mesma sequencia (mediana dos nossos "
                         "dados e ~450 tokens contra max_seq_len 2048 — reduz passos)")
    ap.add_argument("--quatro-bits", action="store_true",
                    help="carrega em 4-bit NF4. DESLIGADO por padrao: o Bee-350M em bf16 sao "
                         "691 MB e a quantizacao custaria 20-30%% de throughput a toa")
    ap.add_argument("--permitir-modelo-de-terceiros", action="store_true",
                    help="desarma a guarda que exige um modelo do projeto Bee")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def check_vram() -> None:
    import torch

    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponivel. Confira o setup (torch cu128).", file=sys.stderr)
        raise SystemExit(1)
    name = torch.cuda.get_device_name(0)
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    cap = torch.cuda.get_device_capability(0)
    print(f"GPU: {name} | {total:.1f} GB | compute sm_{cap[0]}{cap[1]}")
    if total < 7.0:
        print("AVISO: menos de 7 GB de VRAM — reduza --max-seq-len para 1024.")



def guarda_modelo_do_projeto(nome: str, permitir_terceiro: bool) -> None:
    """Aborta se o modelo nao for do projeto Bee.

    Estes scripts nasceram do plano de fine-tunar um Qwen3.5-4B de terceiros, ABANDONADO
    quando o projeto passou a pre-treinar modelos proprios. O default antigo sobreviveu ao
    abandono: rodar isto baixaria 8 GB e treinaria o modelo ERRADO sem um unico aviso.

    Tornar --model obrigatorio resolve o esquecimento, mas nao o engano: quem colar um
    comando antigo de um log ou README ainda passa o Qwen explicitamente. Esta guarda fecha
    esse caminho, e --permitir-modelo-de-terceiros torna a excecao uma DECISAO visivel na
    linha de comando em vez de um acidente silencioso.
    """
    import sys
    if "bee" in nome.lower() or permitir_terceiro:
        return
    print(f"\n[ABORTADO] '{nome}' nao parece um modelo do projeto Bee.", file=sys.stderr)
    print("   Modelos do projeto: BrCamp/bee-350m-pt-base | BrCamp/bee-150m-pt-base",
          file=sys.stderr)
    print("   Se for MESMO intencional treinar modelo de terceiros, passe",
          file=sys.stderr)
    print("   --permitir-modelo-de-terceiros e assuma a escolha.", file=sys.stderr)
    raise SystemExit(1)

def main() -> int:
    # O console do Windows usa cp1252 e explode ao imprimir emoji. Os scripts do projeto ja
    # tratam isso; estes dois nao tratavam, e quebravam DEPOIS de validar tudo — a pior hora.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = parse_args()
    guarda_modelo_do_projeto(args.model, args.permitir_modelo_de_terceiros)

    if not args.data.exists():
        print(f"ERRO: dataset nao encontrado: {args.data}", file=sys.stderr)
        print("Rode o pipeline de dados (data/01..05) antes.", file=sys.stderr)
        return 1

    n_examples = sum(1 for _ in args.data.open(encoding="utf-8") if _.strip())
    effective_batch = args.batch_size * args.grad_accum
    print("=== Config SFT QLoRA ===")
    print(f"  modelo        : {args.model}")
    print(f"  dados         : {args.data} ({n_examples} exemplos)")
    print(f"  saida         : {args.out}")
    print(f"  max_seq_len   : {args.max_seq_len}")
    print(f"  epochs        : {args.epochs}")
    print(f"  batch efetivo : {effective_batch} ({args.batch_size} x {args.grad_accum})")
    print(f"  LoRA          : r={args.lora_r} alpha={args.lora_alpha}")
    print(f"  lr            : {args.lr}")

    if args.dry_run:
        print("\n[dry-run] config validada, nada foi treinado.")
        return 0

    check_vram()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    # 🔴 4-BIT AGORA E' OPT-IN, E O DEFAULT E' bf16.
    #    O QLoRA foi escolhido quando o alvo era um Qwen de 4B (8 GB em bf16, apertado na
    #    5070). O Bee-350M em bf16 sao **691 MB** — quantizar economizaria ~0,5 GB que nao
    #    fazem falta e cobraria 20-30% de throughput por isso.
    #    ⚠️ E o vilao de memoria aqui nem e' o peso: e' o tensor de logits, que com
    #    2048 x 32.000 x bf16 da **131 MB por sequencia**. Quantizar o modelo nao mexe nisso.
    print(f"\ncarregando tokenizer/modelo em {'4-bit NF4' if args.quatro_bits else 'bf16'}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    extra = {}
    if args.quatro_bits:
        extra["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=torch.bfloat16,
        device_map={"": 0},
        trust_remote_code=True,
        **extra,
    )
    model.config.use_cache = False
    if args.quatro_bits:
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=not args.sem_checkpointing)
    elif not args.sem_checkpointing:
        model.gradient_checkpointing_enable()

    if args.sem_lora:
        # ⚠️ FULL FINE-TUNING — no Estagio 2 este e' o CONTROLE NEGATIVO, esperado abaixo do
        #    proprio base em pelo menos uma capacidade. Em 151M ja' se mediu: full FT de
        #    multi-turno custou -5,9 pp de execucao single-turn, e o adapter custou zero.
        #    O LR aqui e' outra ordem de grandeza (~1/10 do de LoRA) — passar o LR de adapter
        #    num full FT destroi o modelo, e o sintoma e' "o braco (c) foi mal", nao "o LR
        #    estava errado".
        print("modo     : FULL FINE-TUNING (sem LoRA) — controle negativo do E2")
        for p in model.parameters():
            p.requires_grad_(True)
    else:
        lora = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
        )
        model = get_peft_model(model, lora)
        model.print_trainable_parameters()

    n_treinaveis = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if n_treinaveis == 0:
        print("\n[ABORTADO] ZERO parametros treinaveis. O treino rodaria inteiro sem erro e "
              "produziria delta exatamente zero.", file=sys.stderr)
        raise SystemExit(1)
    print(f"treinaveis: {n_treinaveis:,} parametros")

    dataset = load_dataset("json", data_files=str(args.data), split="train")

    # ⚠️ DIAGNOSTICO DE MASCARAMENTO DA LOSS — nunca treinar as cegas de novo.
    # Bug real (2026-07-24): com {"messages"} + system prompt grande, o TRL calcula
    # a loss em TODOS os tokens (assistant_only_loss=False por padrao). No dataset
    # agentico o system tinha 928 tok (92,1% do exemplo) e era IDENTICO nos 1495
    # exemplos -> a loss caiu 1,273->0,0755 DECORANDO o catalogo, com so 6,2% dos
    # tokens medindo a habilidade real. O formato prompt/completion faz o TRL
    # mascarar o prompt sozinho (e nao exige {% generation %} no chat template).
    cols = set(dataset.column_names)
    if {"prompt", "completion"} <= cols:
        print("loss     : MASCARADA no prompt (dataset prompt/completion) ✅")
    elif "messages" in cols:
        print("loss     : em TODOS os tokens (dataset 'messages')")
        print("           ⚠️ se houver system prompt grande e repetido, o sinal fica")
        print("           diluido. Regere os splits com 05_build_splits --prompt-completion.")
    else:
        print(f"AVISO: colunas inesperadas no dataset: {sorted(cols)}", file=sys.stderr)

    cfg = SFTConfig(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=not args.sem_checkpointing,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        max_length=args.max_seq_len,
        packing=args.packing,
        optim="paged_adamw_8bit",
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(model=model, args=cfg, train_dataset=dataset, processing_class=tokenizer)

    # 🔴 GUARDA DE PESO QUE NAO MEXE — item 5 do checklist de run longo do projeto, escrito
    #    ha' semanas e nunca implementado. arXiv:2607.25091 mediu em Pythia-70M e SmolLM2-135M
    #    que um adapter marcado silenciosamente como nao-treinavel em PEFT/TRL produz delta
    #    **exatamente zero** e o treino roda inteiro sem um erro: a loss cai (e' a loss do
    #    modelo congelado sobre dado novo), o checkpoint sai, o adapter carrega, e a avaliacao
    #    devolve o numero do base. Nada denuncia.
    #    A guarda compara a norma dos treinaveis antes e depois do passo 1 e ABORTA se
    #    identica. Custa uma passada de soma sobre os parametros.
    from transformers import TrainerCallback

    class GuardaDelta(TrainerCallback):
        """🔴 A PRIMEIRA VERSAO DESTA GUARDA DAVA FALSO POSITIVO, e o erro era de estatistica.

        Ela comparava **a norma dos parametros** antes e depois: `|‖θ_depois‖ − ‖θ_antes‖|`.
        Dois problemas, e os dois disparam alarme num treino saudavel:

        1. ⭐ **A norma pode ficar identica com θ mudando.** Dois pesos que se movem em
           direcoes opostas mantem ‖θ‖ constante. A estatistica certa e' a norma da MUDANCA,
           `‖θ_depois − θ_antes‖`, que so' e' zero se nada mexeu.
        2. ⚠️ **Precisao.** Somar 345M quadrados em float32 da' ~5,5e5; a variacao de um passo
           e' da ordem de 1e-6 relativa e **desaparece no arredondamento**. Medido: a guarda
           imprimiu 554946.125000 -> 554946.125000 e abortou um full FT que estava treinando
           normalmente.

        A versao correta guarda uma AMOSTRA dos pesos (limitada, para nao copiar 1,4 GB) e
        compara elemento a elemento. Amostra basta: se o otimizador andou, andou em tudo que
        recebeu gradiente; se o adapter estava congelado, nao andou em lugar nenhum.
        """

        POR_TENSOR = 64             # elementos amostrados de CADA tensor treinavel

        def __init__(self):
            self.antes = None
            self.conferido = False

        def _amostra(self):
            """Uma fatia pequena de CADA tensor treinavel — nao um bloco do primeiro.

            🔴 A SEGUNDA VERSAO DESTA GUARDA TAMBEM DEU FALSO POSITIVO, agora por VIES DE
            AMOSTRAGEM. Ela pegava os primeiros 262.144 elementos varrendo os parametros em
            ordem — e o primeiro tensor do Qwen3 e' `embed_tokens.weight`, cujas primeiras
            linhas sao os tokens de ID mais baixo. **Linha de embedding de token que nao
            aparece no lote recebe gradiente ZERO.** A amostra caia justamente sobre os pesos
            com maior chance de nao se mover, e o alarme disparava num treino saudavel.
            ⭐ "Amostrar os primeiros N" nao e' amostrar: e' escolher o comeco, e num tensor
            indexado por token o comeco tem significado.
            Pegar poucos elementos de TODOS os tensores cobre atencao, MLP e normalizacao —
            que recebem gradiente em qualquer lote nao-vazio.
            """
            import torch as _t
            with _t.no_grad():
                pedacos = []
                for p in model.parameters():
                    if not p.requires_grad:
                        continue
                    achatado = p.detach().reshape(-1)
                    n = min(achatado.numel(), self.POR_TENSOR)
                    # do MEIO do tensor, nao do inicio
                    ini = max(0, (achatado.numel() - n) // 2)
                    pedacos.append(achatado[ini:ini + n].float().cpu().clone())
                return _t.cat(pedacos) if pedacos else None

        def on_train_begin(self, *a, **k):
            self.antes = self._amostra()
            n = 0 if self.antes is None else self.antes.numel()
            print(f"guarda   : amostra de {n:,} pesos treinaveis capturada antes do passo 1")

        PASSOS_DE_GRACA = 3         # so' aborta se NENHUM destes tiver mexido

        def on_step_end(self, arg, estado, controle, **k):
            """⚠️ CHECAR SO' O PASSO 1 E' FRAGIL, e me custou dois diagnosticos errados.
            Com acumulacao de gradiente, warmup e schedule, o primeiro passo pode legitimamente
            nao mover a amostra. A guarda so' aborta se a amostra continuar IDENTICA depois de
            PASSOS_DE_GRACA passos — a essa altura, silencio e' defeito.
            """
            if self.conferido or estado.global_step < 1:
                return
            import torch as _t
            depois = self._amostra()
            if self.antes is None or depois is None:
                print("\n[ABORTADO] nenhum peso treinavel para amostrar.", file=sys.stderr)
                raise SystemExit(1)
            d = (depois - self.antes).abs()
            mexeram = int((d > 0).sum())
            if mexeram:
                self.conferido = True
                print(f"guarda   : {mexeram:,}/{d.numel():,} pesos amostrados mudaram ate' o "
                      f"passo {estado.global_step} · delta max {float(d.max()):.3e} [OK]")
                return
            print(f"guarda   : passo {estado.global_step} — amostra ainda identica "
                  f"({d.numel():,} pesos)", flush=True)
            if estado.global_step >= self.PASSOS_DE_GRACA:
                self.conferido = True
                print(f"\n[ABORTADO] os {d.numel():,} pesos amostrados continuam IDENTICOS "
                      f"depois de {estado.global_step} passos.", file=sys.stderr)
                print("O treino rodaria inteiro sem erro e sairia sem aprender nada.",
                      file=sys.stderr)
                raise SystemExit(1)

    trainer.add_callback(GuardaDelta())

    print("\ntreinando... (Ctrl+C interrompe; checkpoints em save_steps)")
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "training_args.json").write_text(
        json.dumps(vars(args), default=str, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nAdapter LoRA salvo em {args.out}")
    print("Proximo: avaliar (eval/) e comparar com o baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
