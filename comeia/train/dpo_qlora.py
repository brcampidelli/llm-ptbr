"""Fase 4 — DPO (Direct Preference Optimization) via QLoRA no Qwen3.5-4B.

ESQUELETO. Roda DEPOIS do SFT: refina o modelo com pares de preferência
(escolhido > rejeitado) sem precisar de reward model nem RL (o "barato e alto
impacto" do roadmap). Espelha train/sft_qlora.py (mesma calibração de VRAM para L4).

═══════════════════════════════════════════════════════════════════════════════
⚠️ DUAS DEPENDÊNCIAS QUE AINDA NÃO EXISTEM (marcar antes de rodar de verdade):

1) DADOS DE PREFERÊNCIA (`data/processed/preferences_ptbr.jsonl`)
   Formato por linha (não-conversacional, o que o TRL DPOTrainer consome):
       {"prompt": "...", "chosen": "resposta boa", "rejected": "resposta pior"}
   NÃO temos isso ainda. Falta um `data/06_build_preferences.py` que gere os pares.
   Estratégias possíveis (a decidir):
     - amostrar 2 respostas do professor por prompt (temperaturas diferentes) e o
       juiz aberto (mesmo do quantibias_gate) escolhe a melhor → chosen/rejected;
     - chosen = resposta do professor forte (DeepSeek V4 Pro), rejected = resposta
       do próprio 4B pós-SFT (o modelo aprende a preferir o que é melhor que ele);
     - datasets de preferência PT-BR traduzidos (UltraFeedback) com QC (script 02).
   O 2º casa com o "error bootstrapping" (Learn2Zinc) que ficou no estudo.

2) MODELO DE REFERÊNCIA (escolha teórica — ler o bloco em `main`):
   O DPO precisa de um ref model congelado. Aqui usamos o base (adapter desligado)
   como referência implícita — simples e funciona, mas o ideal teórico é a
   referência ser o próprio SFT. Ver TODO no código para a versão de 2 adapters.
═══════════════════════════════════════════════════════════════════════════════

Uso (na L4 do Colab, depois de ter os dados de preferência):
    python train/dpo_qlora.py --sft-adapter /content/drive/MyDrive/qwen35-4b-ptbr-sft \
        --data data/processed/preferences_ptbr.jsonl --epochs 1
    python train/dpo_qlora.py --data ... --dry-run     # valida config sem treinar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from transformers import TrainerCallback

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "models" / "bee-dpo-adapter"   # era "qwen3.5-4b-ptbr-dpo"


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
    ap.add_argument("--sft-adapter", default=None,
                    help="adapter LoRA do SFT — ponto de partida do DPO (recomendado). "
                         "Sem ele, treina DPO direto sobre o base (menos eficaz).")
    ap.add_argument("--data", type=Path,
                    default=ROOT / "data" / "processed" / "preferences_ptbr.jsonl")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    # DPO segura chosen+rejected → ~2x memória do SFT. Sequência mais curta por padrão.
    # 🔴 max_prompt_len ERA 512, E ISSO TERIA APAGADO O AGENTICO INTEIRO.
    #    O censo por token (comeia/data/censo_tokens.py, 2026-08-19) mediu que o prompt
    #    agentico tem **1.094 tokens de media** — so' o catalogo de ferramentas. Com corte
    #    em 512, todo par de preferencia agentico perderia o catalogo, o modelo veria uma
    #    pergunta sem as ferramentas disponiveis, e o DPO aprenderia a preferir respostas
    #    para um problema que nao e' o problema.
    #    ⚠️ E nao daria erro: e' a MESMA familia que ja descartou 150 de 150 exemplos
    #    agenticos no SFT do Bee-150M (docs/licoes-de-metodo.md §2b). O default vinha
    #    dimensionado para um Qwen de 4B com dado de chat curto, nao para este projeto.
    #    Agora o default e' o contexto inteiro, e a guarda abaixo conta o que seria cortado.
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--max-prompt-len", type=int, default=1536)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=5e-6, help="DPO usa LR bem menor que SFT")
    ap.add_argument("--kto", action="store_true",
                    help="usa KTOTrainer (dado DESPAREADO: prompt/completion/label). "
                         "O unico braco que alcanca os prompts all_right, que nao formam par.")
    ap.add_argument("--peso-desejavel", type=float, default=1.0)
    ap.add_argument("--peso-indesejavel", type=float, default=1.0)
    ap.add_argument("--loss-type", default="sigmoid",
                    choices=["sigmoid", "ipo", "hinge", "robust"],
                    help="'sigmoid' = DPO classico. 'ipo' = IPO (arXiv:2310.12036): "
                         "preferencia vinda de VERIFICADOR e' deterministica, e esse e' o "
                         "regime exato em que o DPO degenera qualquer que seja o beta.")
    ap.add_argument("--beta", type=float, default=0.1,
                    help="força do KO ao ref: menor=mais livre, maior=mais conservador")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lora-r", type=int, default=16, help="só usado se NÃO houver --sft-adapter")
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--save-steps", type=int, default=100)
    ap.add_argument("--max-steps", type=int, default=-1, help="limita passos (smoke test)")
    ap.add_argument("--max-grad-norm", type=float, default=0.3,
                    help="clipping de gradiente — rede contra spikes no DPO (o estudo sugeriu "
                         "percentile_clipping=5 no bnb; via HF Trainer usamos max_grad_norm)")
    ap.add_argument("--quatro-bits", action="store_true",
                    help="carrega em 4-bit NF4. DESLIGADO por padrao (ver nota no codigo)")
    ap.add_argument("--permitir-modelo-de-terceiros", action="store_true",
                    help="desarma a guarda que exige um modelo do projeto Bee")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def check_data(path: Path) -> int:
    """Valida o formato do jsonl de preferência. Retorna nº de linhas válidas."""
    if not path.exists():
        print(f"ERRO: dados de preferência não encontrados: {path}", file=sys.stderr)
        print("      Falta gerar os pares chosen/rejected (ver docstring). Nada para treinar.",
              file=sys.stderr)
        return 0
    n, bad = 0, 0
    with path.open(encoding="utf-8-sig") as f:  # utf-8-sig: tolera BOM (lição do common.py)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if all(k in row for k in ("prompt", "chosen", "rejected")):
                n += 1
            else:
                bad += 1
    if bad:
        print(f"AVISO: {bad} linhas sem os campos prompt/chosen/rejected.", file=sys.stderr)
    return n


def check_vram() -> None:
    import torch
    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponível.", file=sys.stderr)
        raise SystemExit(1)
    p = torch.cuda.get_device_properties(0)
    print(f"GPU: {p.name} | {p.total_memory/1024**3:.1f} GB | sm_{p.major}{p.minor}")
    if p.total_memory / 1024**3 < 16:
        print("AVISO: DPO segura 2 sequências (chosen+rejected). <16GB pode faltar — "
              "reduza --max-seq-len ou rode na L4.")



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

class GuardaDeslocamento(TrainerCallback):
    """🔴 GUARDA OBRIGATORIA — likelihood displacement (arXiv:2402.13228).

    Pares vindos de verificador tem DISTANCIA DE EDICAO MINIMA: mesma trajetoria, um
    argumento trocado. E' o gatilho exato do deslocamento de verossimilhanca, confirmado ate'
    OLMo-1B (arXiv:2410.08847): a margem chosen-rejected sobe bonito no log **enquanto as
    duas log-probs CAEM**, e a massa migra para respostas de sentido oposto.

    ⚠️ Nada disso da' erro. O log fica lindo — `rewards/margins` subindo — e o modelo piora.
    A unica leitura que denuncia e' `logps/chosen` ABSOLUTO: se ele cai abaixo do valor do
    primeiro passo, a margem esta' sendo comprada empurrando o CERTO para baixo.
    """

    def __init__(self, folga: float = 0.0):
        self.inicial: float | None = None
        self.folga = folga
        self.pior = None

    def on_log(self, args, state, control, logs=None, **kw):
        if not logs or "logps/chosen" not in logs:
            return
        v = float(logs["logps/chosen"])
        if self.inicial is None:
            self.inicial = v
            print(f"  [guarda] logps/chosen inicial = {v:.4f} — abortar se cair abaixo disso")
            return
        self.pior = v if self.pior is None else min(self.pior, v)
        if v < self.inicial - self.folga:
            print()
            print(f"🔴 ABORTANDO: logps/chosen caiu de {self.inicial:.4f} para {v:.4f}.")
            print("   A margem esta' subindo porque o CHOSEN esta' sendo empurrado para baixo")
            print("   (likelihood displacement). Continuar so' produziria um log bonito.")
            control.should_training_stop = True


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

    n_valid = check_data(args.data)
    effective_batch = args.batch_size * args.grad_accum
    print("=== Config DPO QLoRA ===")
    print(f"  modelo        : {args.model}")
    print(f"  sft-adapter   : {args.sft_adapter or '(nenhum — DPO direto no base)'}")
    print(f"  dados         : {args.data} ({n_valid} pares válidos)")
    print(f"  saida         : {args.out}")
    print(f"  max_seq/prompt: {args.max_seq_len} / {args.max_prompt_len}")
    print(f"  epochs        : {args.epochs} | beta: {args.beta} | lr: {args.lr}")
    print(f"  batch efetivo : {effective_batch} ({args.batch_size} x {args.grad_accum})")

    if args.dry_run:
        print("\n[dry-run] config validada, nada foi treinado.")
        if n_valid == 0:
            print("[dry-run] ⚠️ 0 pares de preferência — gerar os dados antes do run real.")
        return 0

    if n_valid == 0:
        return 1

    check_vram()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer, KTOConfig, KTOTrainer

    # 🔴 4-bit e' OPT-IN. Ver a mesma nota em sft_qlora.py: o Bee-350M em bf16 sao 691 MB;
    #    quantizar economiza ~0,5 GB que nao fazem falta e custa 20-30% de throughput.
    print(f"\ncarregando base em {'4-bit NF4' if args.quatro_bits else 'bf16'}...")
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
        args.model, dtype=torch.bfloat16,
        device_map={"": 0}, trust_remote_code=True, **extra,
    )
    model.config.use_cache = False
    if args.quatro_bits:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    else:
        model.gradient_checkpointing_enable()

    # ── POLÍTICA (o que treinamos) ──
    # Se há adapter do SFT, partimos DELE (o DPO refina o modelo já instruído).
    # Senão, criamos um LoRA novo sobre o base.
    peft_config = None
    if args.sft_adapter:
        print(f"partindo do adapter SFT: {args.sft_adapter}")
        model = PeftModel.from_pretrained(model, args.sft_adapter, is_trainable=True)
    else:
        peft_config = LoraConfig(
            r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
        )

    # ── REFERÊNCIA ──
    # ref_model=None + modelo PEFT → o DPOTrainer usa "adapter desligado" como
    # referência. Como o único adapter é o que treinamos, a referência = BASE.
    # ⚠️ TODO teórico: o ideal é ref = SFT congelado (não o base). Para isso, usar
    # DOIS adapters: carregar o SFT como `ref_adapter_name` (congelado) e um NOVO
    # adapter DPO como `model_adapter_name` (treinável). Requer criar o adapter DPO
    # separado e passar model_adapter_name/ref_adapter_name ao DPOConfig. Fica como
    # melhoria — o base-como-ref já roda e é usado na prática.
    ref_model = None

    dataset = load_dataset("json", data_files=str(args.data), split="train")
    # 🔴 GUARDA DE FORMATO. KTO quer prompt/completion/label; DPO quer prompt/chosen/rejected.
    #    Passar um ao outro nao da' erro claro — da' erro de coluna la' dentro, ou pior, treina
    #    em algo que nao e' o que se pensa. Abortar aqui e' barato.
    cols = set(dataset.column_names)
    if args.kto and not {"prompt", "completion", "label"} <= cols:
        print(f"ERRO: --kto exige prompt/completion/label; o arquivo tem {sorted(cols)}",
              file=sys.stderr)
        return 2
    if not args.kto and not {"prompt", "chosen", "rejected"} <= cols:
        print(f"ERRO: DPO/IPO exige prompt/chosen/rejected; o arquivo tem {sorted(cols)}",
              file=sys.stderr)
        return 2

    Config, Trainer = (KTOConfig, KTOTrainer) if args.kto else (DPOConfig, DPOTrainer)
    extra = {}
    if args.kto:
        extra = {"desirable_weight": args.peso_desejavel,
                 "undesirable_weight": args.peso_indesejavel}
    else:
        extra = {"loss_type": args.loss_type}
    cfg = Config(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        beta=args.beta,
        max_length=args.max_seq_len,
        max_prompt_length=args.max_prompt_len,
        max_grad_norm=args.max_grad_norm,
        optim="paged_adamw_8bit",
        report_to="none",
        seed=42,
        **extra,
    )

    trainer = Trainer(
        model=model,
        ref_model=ref_model,
        args=cfg,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,  # None se partimos do adapter SFT
    )
    trainer.add_callback(GuardaDeslocamento())
    print(f"perda  : {'KTO' if args.kto else args.loss_type.upper()}")

    print("\ntreinando DPO... (Ctrl+C interrompe; checkpoints em save_steps)")
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "training_args.json").write_text(
        json.dumps(vars(args), default=str, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nAdapter DPO salvo em {args.out}")
    print("Proximo: avaliar (eval/run_baseline.py --peft ...) e comparar com o SFT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
