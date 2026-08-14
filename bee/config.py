"""BEE — a arquitetura. O MESMO arquivo em toda a escada, do 150M ao 4B.

⭐ A DECISÃO CENTRAL: Llama-style via `LlamaConfig`, **sem código de modelagem custom**.
Não é falta de ambição — é o contrário. Tudo que já construímos (PEFT, TRL, vLLM, os
nossos evals, o `sft_qlora.py`) funciona sobre arquitetura Llama **sem uma linha de
adaptação**. Um bloco custom nos custaria semanas de integração para ganhar, na melhor
das hipóteses, alguns pontos percentuais — e nos tiraria a capacidade de comparar com
qualquer baseline publicado. O que é nosso aqui é o **corpus, o tokenizador e o
treino**, não uma variante de atenção.

⭐ O QUE MUDA ENTRE OS DEGRAUS: só os números deste arquivo. `tokens × params = dinheiro`
é a única equação da escada; o código é constante. É por isso que doação ou investimento
vira capacidade sem reescrever o projeto.

Uso:
    python bee/config.py                  # mostra a escada inteira, com custo
    python bee/config.py --tamanho 150m   # detalha um degrau e valida a conta
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# O tokenizador é NOSSO e já passou no Gate 1 (−5,4% de tokens/palavra em PT vs. Qwen).
# ⚠️ Trocá-lo depois invalida qualquer checkpoint: o embedding é indexado por id de
# token. Por isso ele está congelado antes da arquitetura, e não depois.
VOCAB = 32_000
FERTILIDADE_PT = 1.416     # medida, não estimada — ver docs/gate-1-fertilidade


@dataclass(frozen=True)
class BeeConfig:
    """Um degrau da escada. Os campos são os do `LlamaConfig`, com nomes nossos."""
    nome: str
    n_camadas: int
    d_model: int
    n_heads: int
    n_kv_heads: int          # < n_heads = GQA
    intermediate: int
    seq_len: int = 2048
    vocab: int = VOCAB
    rope_theta: float = 10_000.0
    tied_embeddings: bool = True
    # ⭐ "llama" ou "qwen3". Qwen3 É Llama + QK-Norm — mesmo SwiGLU, RoPE, RMSNorm, GQA,
    # e igualmente suportado por PEFT/TRL/vLLM. O estudo do 350M pede QK-Norm (arXiv:2602.02522,
    # ablação num proxy de 70M — ABAIXO do Bee-150M — mede −0,63% de loss e protege contra
    # instabilidade de atenção). `LlamaConfig` não tem QK-Norm; implementá-lo exigiria código
    # de modelagem custom, que é exatamente o que este arquivo se recusa a fazer.
    # Trocar a FAMÍLIA resolve sem custom code, e custa 4,1k params (0,001% do modelo).
    arquitetura: str = "llama"

    @property
    def qk_norm(self) -> bool:
        return self.arquitetura == "qwen3"

    # ---------------------------------------------------------------- contas ---
    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    @property
    def params_embedding(self) -> int:
        # tied = a matriz de saída REUSA a de entrada. Num modelo pequeno isso não é
        # detalhe: sem tying, 32k × 576 apareceria DUAS vezes (37M em vez de 18M, ~24%
        # do modelo gasto em duplicata).
        return self.vocab * self.d_model * (1 if self.tied_embeddings else 2)

    @property
    def params_por_camada(self) -> int:
        d, hd = self.d_model, self.head_dim
        # atenção: q (d×n_heads·hd) + k,v (d×n_kv·hd cada) + o (n_heads·hd×d)
        attn = d * self.n_heads * hd + 2 * (d * self.n_kv_heads * hd) + self.n_heads * hd * d
        # SwiGLU são TRÊS matrizes (gate, up, down), não duas — erro clássico de conta
        mlp = 3 * d * self.intermediate
        norms = 2 * d                      # RMSNorm de atenção e de MLP
        return attn + mlp + norms

    @property
    def params(self) -> int:
        return self.params_embedding + self.n_camadas * self.params_por_camada + self.d_model

    @property
    def kv_cache_por_token(self) -> int:
        """Bytes de KV-cache por token gerado (bf16). É o que decide se roda local."""
        return 2 * self.n_camadas * self.n_kv_heads * self.head_dim * 2

    def vram_treino_gb(self, otimizador_fp32: bool = True) -> float:
        """Pesos + gradientes + estado do Adam. NÃO inclui ativações nem KV-cache.

        bf16 nos pesos (2 B) + grad bf16 (2 B) + Adam m,v em fp32 (8 B) = 12 B/param.
        É a conta que define as PAREDES da escada — ver `escada()`.
        """
        bytes_por_param = 12 if otimizador_fp32 else 6
        return self.params * bytes_por_param / 1024 ** 3

    def horas_treino_l4(self, tokens: float) -> float:
        """FLOPs ≈ 6ND (Kaplan et al.). L4 ≈ 3e13 FLOP/s efetivos (medido, não de folha)."""
        return (6 * self.params * tokens) / 3e13 / 3600

    def tokens_chinchilla(self) -> float:
        """20 tokens por parâmetro. ⚠️ É o ponto COMPUTE-ÓTIMO para treinar, não o
        melhor modelo possível: o SmolLM2-135M usou ~11 TRILHÕES de tokens, ~4000×
        Chinchilla, porque para um modelo que vai SERVIR muito, treinar além do ótimo
        continua pagando. Nosso alvo de 3B é ~7× Chinchilla — modesto de propósito,
        porque o gargalo aqui é hora de L4, não teoria."""
        return 20 * self.params


# ------------------------------------------------------------------ a escada ---
# ⚠️ FUNDO-E-FINO, não largo-e-raso: 30 camadas para apenas 576 de largura no 150M.
# É a forma que o SmolLM2 encontrou nessa escala — profundidade compra composição
# melhor que largura em modelos pequenos. Não é chute nosso; é copiar um recipe
# publicado e medido, que é o que se deve fazer quando não se tem GPU para ablação.
# ⚠️ As dimensões foram CALIBRADAS para que o nome bata com a contagem real (±6%).
# A primeira versão deste arquivo tinha "Bee-150M" com 125M e "Bee-1B" com 653M — nome
# que promete mais do que entrega é a coisa mais fácil de deixar passar num model card,
# e a mais constrangedora de corrigir depois que alguém baixou. Conferido contra o
# modelo real do transformers em `--verificar`.
ESCADA = {
    "150m": BeeConfig("Bee-150M", n_camadas=30, d_model=576,  n_heads=9,  n_kv_heads=3,  intermediate=2048),
    # ⭐ 350M — geometria do **SmolLM2-360M**, recipe publicado na MESMA escala. O 150M já provou
    # que copiar recipe publicado nesta faixa funciona (bpb 0,844, batendo o Tucano-160m que usou
    # 9× mais tokens). Ver docs/estudo-bee-350m.md §4.1.
    # ⚠️ EVIDÊNCIA DIVIDIDA sobre a razão d_model/camadas: aqui 960/32 = 30,0; o LilMoo
    # (arXiv:2603.03508, 670M hindi — o único ponto MEDIDO perto desta escala) usa 54,9. O estudo
    # marcou o gate pareado de geometria como US$ 40 e OPCIONAL. Ficamos com o recipe publicado.
    # ⚠️ intermediate 2560 = 2,67× d_model, seguindo o SmolLM2-360M. O Bee-150M usa 3,556× — o
    # desvio é do recipe de origem e NÃO foi medido por nós.
    "350m": BeeConfig("Bee-350M", n_camadas=32, d_model=960,  n_heads=15, n_kv_heads=5,
                      intermediate=2560, arquitetura="qwen3"),
    "500m": BeeConfig("Bee-500M", n_camadas=27, d_model=1280, n_heads=20, n_kv_heads=4,  intermediate=3456),
    "1b":   BeeConfig("Bee-1B",   n_camadas=28, d_model=1792, n_heads=28, n_kv_heads=4,  intermediate=4864, seq_len=4096),
    "4b":   BeeConfig("Bee-4B",   n_camadas=40, d_model=3072, n_heads=24, n_kv_heads=8,  intermediate=8192, seq_len=4096),
}

VRAM_L4_GB = 22.0


def para_hf_config(cfg: BeeConfig):
    """Converte para o config do transformers. **Zero código de modelagem custom.**

    Llama e Qwen3 são a mesma arquitetura mais QK-Norm; a escolha vive no `BeeConfig`.
    """
    comum = dict(
        vocab_size=cfg.vocab,
        hidden_size=cfg.d_model,
        intermediate_size=cfg.intermediate,
        num_hidden_layers=cfg.n_camadas,
        num_attention_heads=cfg.n_heads,
        num_key_value_heads=cfg.n_kv_heads,      # GQA
        max_position_embeddings=cfg.seq_len,
        rope_theta=cfg.rope_theta,               # em transformers 5.x vira rope_parameters
        tie_word_embeddings=cfg.tied_embeddings,
        hidden_act="silu",                        # SwiGLU
        rms_norm_eps=1e-5,
        attention_bias=False,
        bos_token_id=0, eos_token_id=0, pad_token_id=3,
    )
    if cfg.arquitetura == "qwen3":
        from transformers import Qwen3Config
        # ⚠️ head_dim EXPLÍCITO: o Qwen3 o trata como campo próprio, e deixar implícito é
        # convite a divergir de d_model/n_heads sem ninguém notar.
        # ⚠️ use_sliding_window=False: o Qwen3 traz janela deslizante opcional, e ela mudaria
        # o modelo sem aparecer em lugar nenhum do log.
        return Qwen3Config(**comum, head_dim=cfg.d_model // cfg.n_heads,
                           use_sliding_window=False)
    from transformers import LlamaConfig
    return LlamaConfig(**comum, mlp_bias=False)


def classe_do_modelo(cfg: BeeConfig):
    if cfg.arquitetura == "qwen3":
        from transformers import Qwen3ForCausalLM
        return Qwen3ForCausalLM
    from transformers import LlamaForCausalLM
    return LlamaForCausalLM


def para_llama_config(cfg: BeeConfig):
    """Compatibilidade com chamadas antigas. Prefira `para_hf_config`."""
    return para_hf_config(cfg)


def _antigo_para_llama_config(cfg: BeeConfig):
    from transformers import LlamaConfig
    return LlamaConfig(
        vocab_size=cfg.vocab,
        hidden_size=cfg.d_model,
        intermediate_size=cfg.intermediate,
        num_hidden_layers=cfg.n_camadas,
        num_attention_heads=cfg.n_heads,
        num_key_value_heads=cfg.n_kv_heads,      # GQA
        max_position_embeddings=cfg.seq_len,
        rope_theta=cfg.rope_theta,
        tie_word_embeddings=cfg.tied_embeddings,
        hidden_act="silu",                        # SwiGLU
        rms_norm_eps=1e-5,
        attention_bias=False,
        mlp_bias=False,
        bos_token_id=0, eos_token_id=0, pad_token_id=3,
    )


def escada(tokens_por_degrau: dict[str, float] | None = None) -> str:
    """A tabela que traduz arquitetura em DINHEIRO e TEMPO. É o mapa do projeto."""
    alvos = tokens_por_degrau or {"150m": 3e9, "350m": 6e9, "500m": 10e9,
                                  "1b": 20e9, "4b": 80e9}
    linhas = [
        "=" * 100,
        "⭐ A ESCADA DO BEE — o codigo e o MESMO; mudam os numeros deste arquivo",
        "=" * 100,
        f"{'degrau':<10} {'params':>9} {'emb%':>6} {'VRAM tr':>9} {'KV/1k tok':>10} "
        f"{'tokens':>8} {'horas L4':>10}  cabe na L4?",
        "-" * 100,
    ]
    for chave, cfg in ESCADA.items():
        tk = alvos.get(chave, cfg.tokens_chinchilla())
        vram = cfg.vram_treino_gb()
        horas = cfg.horas_treino_l4(tk)
        emb_pct = 100 * cfg.params_embedding / cfg.params
        if vram > VRAM_L4_GB:
            cabe = "❌ nao cabe"
        elif horas > 24 * 30:
            cabe = "⚠️ cabe, mas >1 mes"
        elif vram > VRAM_L4_GB * 0.7:
            cabe = "⚠️ apertado"
        else:
            cabe = "✅"
        linhas.append(
            f"{cfg.nome:<10} {cfg.params/1e6:>8.0f}M {emb_pct:>5.0f}% {vram:>8.1f}G "
            f"{cfg.kv_cache_por_token*1000/1024**2:>9.1f}M {tk/1e9:>7.0f}B "
            f"{horas:>9.0f}h  {cabe}")
    linhas += [
        "-" * 100,
        "VRAM tr = pesos + gradientes + Adam fp32 (12 B/param). Nao inclui ativacoes.",
        "horas L4 = 6ND / 3e13 FLOP/s. KV/1k tok = custo de contexto na INFERENCIA.",
        "",
        "⭐ A leitura: ate 500M o Colab basta e o projeto anda de graca. Do 1B pra cima,",
        "   a barreira deixa de ser tecnica e passa a ser fatura — e o codigo nao muda.",
    ]
    return "\n".join(linhas)


def detalhe(cfg: BeeConfig) -> str:
    p_emb, p_cam = cfg.params_embedding, cfg.n_camadas * cfg.params_por_camada
    l = [
        "=" * 76,
        f"⭐ {cfg.nome}",
        "=" * 76,
        f"  {cfg.n_camadas} camadas · d_model {cfg.d_model} · intermediate {cfg.intermediate} (SwiGLU)",
        f"  {cfg.n_heads} heads (head_dim {cfg.head_dim}) · {cfg.n_kv_heads} KV heads (GQA "
        f"{cfg.n_heads // cfg.n_kv_heads}x) · seq_len {cfg.seq_len}",
        f"  vocab {cfg.vocab} · tied_embeddings {cfg.tied_embeddings} · RoPE theta {cfg.rope_theta:.0f}",
        f"  arquitetura {cfg.arquitetura}" + ("  ⭐ QK-Norm ligado" if cfg.qk_norm else "  (sem QK-Norm)"),
        "-" * 76,
        f"  parametros            {cfg.params/1e6:>10.1f}M",
        f"    embedding           {p_emb/1e6:>10.1f}M  ({100*p_emb/cfg.params:.0f}% do total)",
        f"    camadas             {p_cam/1e6:>10.1f}M  ({cfg.params_por_camada/1e6:.2f}M cada)",
        f"  VRAM de treino        {cfg.vram_treino_gb():>10.1f} GB   (12 B/param)",
        f"  KV-cache / 1k tokens  {cfg.kv_cache_por_token*1000/1024**2:>10.1f} MB",
        f"  Chinchilla (20 tok/p) {cfg.tokens_chinchilla()/1e9:>10.1f}B tokens",
        "-" * 76,
    ]
    # ⭐ o embedding come o modelo quando ele e pequeno — a razao de vocab 32k e nao 250k
    if 100 * p_emb / cfg.params > 20:
        l.append(f"  ⚠️ embedding e {100*p_emb/cfg.params:.0f}% do modelo. Com o vocab do Qwen")
        l.append(f"     (248k) seria {100*248044*cfg.d_model/(248044*cfg.d_model+p_cam):.0f}% — inviavel. O Gate 1 pagou por si.")
    return "\n".join(l)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamanho", choices=list(ESCADA), help="detalha um degrau")
    ap.add_argument("--json", action="store_true", help="imprime o config em JSON")
    ap.add_argument("--verificar", action="store_true",
                    help="confere a conta de params contra o modelo REAL do transformers")
    args = ap.parse_args()

    if not args.tamanho:
        print(escada())
        print("\nDetalhe de um degrau:  python bee/config.py --tamanho 150m")
        return 0

    cfg = ESCADA[args.tamanho]
    if args.json:
        print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
        return 0
    print(detalhe(cfg))

    if args.verificar:
        # ⭐ A conta de parametros feita a mao ERRA facil (SwiGLU tem 3 matrizes, nao 2;
        # tying muda o embedding pela metade). Em vez de confiar, INSTANCIAMOS o modelo
        # e contamos os tensores. Se divergir mais de 1%, o erro esta aqui, nao la.
        print("\ninstanciando o modelo real para conferir a conta…")
        import torch
        with torch.device("meta"):                    # sem alocar memoria de verdade
            modelo = classe_do_modelo(cfg)(para_hf_config(cfg))
        real = sum(p.numel() for p in modelo.parameters())
        # com tying, o transformers conta a matriz uma vez so — igual a nossa formula
        erro = abs(real - cfg.params) / real
        print(f"  nossa formula : {cfg.params/1e6:>9.2f}M")
        print(f"  modelo real   : {real/1e6:>9.2f}M")
        print(f"  divergencia   : {erro:>9.2%}  {'OK' if erro < 0.01 else '🔴 CONFERIR A FORMULA'}")
        return 0 if erro < 0.01 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
