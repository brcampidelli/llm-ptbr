"""Muon — otimizador por ortogonalizacao do momento (Newton-Schulz) para as MATRIZES 2D.

Gate #1 do estudo do arXiv (2026-09-12): o artigo 2609.04577 mede 1,3-1,9x de eficiencia de token
sobre AdamW na faixa de overtraining (>= 20 tok/param). Este projeto nunca variou o otimizador.

O que e', em uma frase: em vez de dividir o gradiente pela raiz da variancia (Adam), o Muon toma o
momento M de cada matriz de peso e substitui por  U V^T  (a "parte ortogonal" de M = U S V^T),
calculada por 5 iteracoes de Newton-Schulz em bf16 — todas as direcoes singulares recebem o mesmo
passo, o que evita que umas poucas dominem a atualizacao.

⚠️ SO PARA MATRIZES 2D DAS CAMADAS (atencao, MLP). Embedding, lm_head, bias e RMSNorm ficam no
   AdamW, como nas implementacoes de referencia (Jordan 2024; Liu et al. 2025 "Muon is Scalable").

⚠️ ESCALA DO PASSO. Usa-se a variante com RMS casado ao do Adam (0,2 * sqrt(max(m, n)), Liu et al.
   2025), para que a MESMA lr do AdamW seja um ponto de partida razoavel. Isso e' uma escolha de
   desenho do gate, nao um fato: §2f — a grade tem de cercar o otimo dos DOIS otimizadores, e o
   gate roda um braco extra a 3x lr por otimizador para nao comparar um no otimo com outro fora.

Referencias: github.com/KellerJordan/Muon (a NS5 com coeficientes (3.4445, -4.7750, 2.0315));
arXiv 2502.16982 (Muon is Scalable — RMS matching e weight decay).
"""
from __future__ import annotations

import torch


@torch.no_grad()
def newton_schulz5(G: torch.Tensor, passos: int = 5, eps: float = 1e-7) -> torch.Tensor:
    """Aproxima U V^T de G (ortogonalizacao) com 5 iteracoes quinticas, em bf16.
    Os coeficientes sao os de Jordan (2024): convergem para o sinal da matriz sem precisar de
    exatidao — basta que os valores singulares fiquem perto de 1."""
    a, b, c = 3.4445, -4.7750, 2.0315
    X = G.to(torch.bfloat16)
    X = X / (X.norm() + eps)
    transposta = G.size(0) > G.size(1)
    if transposta:
        X = X.T
    for _ in range(passos):
        A = X @ X.T
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    if transposta:
        X = X.T
    return X.to(G.dtype)


class Muon(torch.optim.Optimizer):
    """Muon para os parametros 2D. Combine com um AdamW para o resto (ver `construir_muon_adamw`)."""

    def __init__(self, params, lr: float = 3e-4, momentum: float = 0.95, nesterov: bool = True,
                 ns_passos: int = 5, weight_decay: float = 0.1):
        super().__init__(params, dict(lr=lr, momentum=momentum, nesterov=nesterov,
                                      ns_passos=ns_passos, weight_decay=weight_decay))

    @torch.no_grad()
    def step(self, closure=None):
        for g in self.param_groups:
            lr, mom, wd = g["lr"], g["momentum"], g["weight_decay"]
            for p in g["params"]:
                if p.grad is None:
                    continue
                grad = p.grad
                if grad.dim() != 2:
                    raise RuntimeError(f"Muon so' aceita matrizes 2D; recebeu {tuple(grad.shape)}")
                st = self.state[p]
                if "buf" not in st:
                    st["buf"] = torch.zeros_like(grad)
                buf = st["buf"]
                buf.mul_(mom).add_(grad)
                upd = grad.add(buf, alpha=mom) if g["nesterov"] else buf
                upd = newton_schulz5(upd, g["ns_passos"])
                # RMS casado ao Adam (Liu et al. 2025): mesma lr do AdamW vira ponto de partida
                upd = upd * (0.2 * max(p.size(0), p.size(1)) ** 0.5)
                if wd > 0:
                    p.mul_(1 - lr * wd)
                p.add_(upd, alpha=-lr)


def separar_parametros(modelo):
    """(muon_2d, adamw_decay, adamw_no_decay). Embedding e lm_head NAO vao para o Muon."""
    muon, decay, no_decay = [], [], []
    for nome, p in modelo.named_parameters():
        if not p.requires_grad:
            continue
        eh_emb = ("embed" in nome) or ("lm_head" in nome)
        if p.dim() == 2 and not eh_emb:
            muon.append(p)
        elif p.dim() >= 2:
            decay.append(p)
        else:
            no_decay.append(p)
    return muon, decay, no_decay


class MuonAdamW:
    """Par (Muon nas matrizes das camadas, AdamW no resto) com a interface minima que o
    pretrain.py usa: zero_grad, step, state_dict/load_state_dict, param_groups (para a lr)."""

    def __init__(self, modelo, lr: float, weight_decay: float = 0.1, fused: bool = True):
        muon, decay, no_decay = separar_parametros(modelo)
        self.muon = Muon(muon, lr=lr, weight_decay=weight_decay)
        self.adamw = torch.optim.AdamW(
            [{"params": decay, "weight_decay": weight_decay},
             {"params": no_decay, "weight_decay": 0.0}],
            lr=lr, betas=(0.9, 0.95), eps=1e-8, fused=fused)
        self.n_muon, self.n_adamw = len(muon), len(decay) + len(no_decay)

    @property
    def param_groups(self):
        return self.muon.param_groups + self.adamw.param_groups

    def zero_grad(self, set_to_none: bool = True):
        self.muon.zero_grad(set_to_none); self.adamw.zero_grad(set_to_none)

    def step(self):
        self.muon.step(); self.adamw.step()

    def state_dict(self):
        return {"muon": self.muon.state_dict(), "adamw": self.adamw.state_dict()}

    def load_state_dict(self, sd):
        self.muon.load_state_dict(sd["muon"]); self.adamw.load_state_dict(sd["adamw"])


def _autoteste() -> int:
    """§2t: (1) NS5 devolve matriz ~ortogonal; (2) um passo de Muon reduz a loss de um problema
    quadratico; (3) embedding fica FORA do Muon."""
    torch.manual_seed(0)
    G = torch.randn(64, 32)
    O = newton_schulz5(G).float()
    S = torch.linalg.svdvals(O)
    assert (S.max() < 1.3) and (S.min() > 0.6), f"valores singulares fora de ~1: {S.min():.2f}..{S.max():.2f}"

    W = torch.nn.Parameter(torch.randn(16, 16))
    alvo = torch.randn(16, 16)
    opt = Muon([W], lr=0.05, weight_decay=0.0)
    l0 = ((W - alvo) ** 2).mean(); l0.backward(); opt.step()
    l1 = ((W - alvo) ** 2).mean().item()
    assert l1 < l0.item(), f"a loss nao caiu: {l0.item():.4f} -> {l1:.4f}"

    class Mini(torch.nn.Module):
        def __init__(s):
            super().__init__(); s.embed_tokens = torch.nn.Embedding(10, 8); s.q_proj = torch.nn.Linear(8, 8)
            s.norm = torch.nn.RMSNorm(8) if hasattr(torch.nn, "RMSNorm") else torch.nn.LayerNorm(8); s.lm_head = torch.nn.Linear(8, 10)
    m = Mini(); mu, de, nd = separar_parametros(m)
    assert len(mu) == 1 and len(de) == 2 and len(nd) >= 1, (len(mu), len(de), len(nd))
    print("muon: autoteste OK (NS5 ortogonal, passo reduz loss, embedding/lm_head fora do Muon)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_autoteste())
