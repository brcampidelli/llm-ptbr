"""COMEIA — engine: 1 backbone + hot-swap de adapters LoRA.

O coracao da comeia. Carrega o backbone Qwen3.5-4B UMA vez (4-bit NF4, mesmo padrao
de eval/run_baseline.py) e troca os adapters LoRA a quente por chamada — em vez de
carregar N modelos. Isso transforma "N modelos" em "1 modelo + N personalidades":
resolve VRAM (backbone ~3 GB + adapters de dezenas de MB) e coordenacao de uma vez.

API do PEFT usada:
  - 1o adapter: PeftModel.from_pretrained(base, path, adapter_name=...)
  - demais:     model.load_adapter(path, adapter_name=...)
  - ativar:     model.set_adapter(name)
  - base (fallback): `with model.disable_adapter(): ...`  (desliga todos os adapters)

Adapter ausente no disco (ex.: caminho do Drive do Colab rodando localmente) NAO
quebra: a abelha e degradada para o backbone base, com aviso. Assim o MVP roda em
qualquer lugar e trocar o adapter real depois e so ajustar o bees.json.
"""

from __future__ import annotations

import sys
import time
from contextlib import nullcontext
from pathlib import Path

from registry import Bee, Registry

# Reusa a limpeza de <think> do pipeline de dados (mesmo problema, um só lugar).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from common import strip_think  # noqa: E402


class Hive:
    def __init__(self, registry: Registry, four_bit: bool = True,
                 max_new_tokens: int = 512, thinking: bool = False) -> None:
        self.reg = registry
        self.four_bit = four_bit
        self.max_new_tokens = max_new_tokens
        # O Qwen3.5 raciocina (<think>) por padrao e gasta os tokens de saida
        # pensando — na comeia isso e desperdicio (o fast-path quer resposta
        # curta e barata). Desligamos na origem; a limpeza fica como rede.
        self.thinking = thinking
        self.model = None
        self.tokenizer = None
        self._is_peft = False
        self.loaded_adapters: set[str] = set()   # nomes de abelha com adapter ativo no disco

    # ---- carga ---------------------------------------------------------------
    def load(self) -> None:
        import torch
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  BitsAndBytesConfig)

        if not torch.cuda.is_available():
            print("AVISO: CUDA indisponivel — vai rodar em CPU (lento).", file=sys.stderr)
        dev_total = (torch.cuda.get_device_properties(0).total_memory / 1024**3
                     if torch.cuda.is_available() else 0.0)

        kwargs: dict = {"dtype": torch.bfloat16}
        if torch.cuda.is_available():
            kwargs["device_map"] = {"": 0}
        if self.four_bit and torch.cuda.is_available():
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            print("quantizacao: 4-bit NF4")

        print(f"backbone: {self.reg.backbone} — carregando uma vez...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.reg.backbone)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(self.reg.backbone, **kwargs)

        # Carrega cada adapter existente sobre o MESMO backbone (hot-swap).
        adapter_bees = [b for b in self.reg.bees.values() if b.adapter_path]
        for b in adapter_bees:
            if not Path(b.adapter_path).exists():
                print(f"  [adapter ausente] abelha '{b.name}': {b.adapter_path} "
                      f"nao encontrado -> degradada para o backbone base.", file=sys.stderr)
                continue
            from peft import PeftModel
            if not self._is_peft:
                model = PeftModel.from_pretrained(model, b.adapter_path, adapter_name=b.name)
                self._is_peft = True
            else:
                model.load_adapter(b.adapter_path, adapter_name=b.name)
            self.loaded_adapters.add(b.name)
            print(f"  [adapter] '{b.name}' <- {b.adapter_path}")

        model.eval()
        self.model = model

        if torch.cuda.is_available():
            used = torch.cuda.memory_allocated() / 1024**3
            print(f"VRAM ocupada: {used:.2f} GB de {dev_total:.1f} GB "
                  f"| abelhas com adapter: {len(self.loaded_adapters)} "
                  f"({', '.join(sorted(self.loaded_adapters)) or 'nenhuma — so backbone base'})\n")

    # ---- geracao -------------------------------------------------------------
    def _build_messages(self, bee: Bee, query: str) -> list[dict]:
        msgs: list[dict] = []
        if bee.system_prompt:
            msgs.append({"role": "system", "content": bee.system_prompt})
        msgs.append({"role": "user", "content": query})
        return msgs

    def generate(self, bee: Bee, query: str, max_new_tokens: int | None = None) -> tuple[str, float]:
        """Gera a resposta pela abelha escolhida. Retorna (texto, segundos)."""
        import torch

        if self.model is None:
            raise RuntimeError("Hive nao carregada. Chame .load() antes.")

        use_adapter = bee.name in self.loaded_adapters
        msgs = self._build_messages(bee, query)
        # ⚠️ transformers 5.x: apply_chat_template devolve um BatchEncoding (dict),
        # nao um tensor puro. Passar isso direto para generate() quebra em
        # `inputs_tensor.shape[0]`. Pedimos return_dict e expandimos com **inputs
        # (leva o attention_mask de brinde). Tolera as duas formas de retorno.
        tpl_kwargs: dict = {"add_generation_prompt": True, "return_tensors": "pt",
                            "return_dict": True}
        if not self.thinking:
            # convencao da familia Qwen3; templates que nao conhecem o kwarg
            # levantam TypeError -> caimos no caminho sem ele (a limpeza resolve).
            tpl_kwargs["enable_thinking"] = False
        try:
            enc = self.tokenizer.apply_chat_template(msgs, **tpl_kwargs)
        except TypeError:
            tpl_kwargs.pop("enable_thinking", None)
            enc = self.tokenizer.apply_chat_template(msgs, **tpl_kwargs)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if hasattr(enc, "input_ids") or isinstance(enc, dict):
            inputs = {k: v.to(device) for k, v in dict(enc).items()
                      if hasattr(v, "to")}
        else:                                  # retorno legado: tensor puro
            inputs = {"input_ids": enc.to(device)}
        prompt_len = inputs["input_ids"].shape[1]

        # abelha COM adapter -> ativa esse adapter; abelha base -> desliga todos.
        if self._is_peft:
            if use_adapter:
                self.model.set_adapter(bee.name)
                ctx = nullcontext()
            else:
                ctx = self.model.disable_adapter()
        else:
            ctx = nullcontext()  # nenhum adapter carregado: so backbone base

        t0 = time.time()
        with torch.no_grad(), ctx:
            out = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens or self.max_new_tokens,
                do_sample=False, pad_token_id=self.tokenizer.eos_token_id,
            )
        dt = time.time() - t0
        raw = self.tokenizer.decode(out[0][prompt_len:], skip_special_tokens=True).strip()
        # Rede de seguranca: mesmo com enable_thinking=False alguns checkpoints
        # (incl. adapters treinados com <think> no alvo) ainda raciocinam.
        text, truncated = strip_think(raw)
        if truncated or not text:
            # cortou no meio do raciocinio: nao ha resposta final. Ser honesto em
            # vez de devolver raciocinio como se fosse resposta.
            text = (text or "").strip() or (
                f"[sem resposta final: o modelo gastou os {max_new_tokens or self.max_new_tokens} "
                "tokens raciocinando. Aumente --max-new ou use --thinking off]"
            )
        return text, dt
