"""BEE — pré-treino do zero. Pesos aleatórios → modelo de linguagem.

⭐ ESTE É O ARQUIVO QUE FAZ O BEE SER NOSSO. Tudo antes dele (corpus, tokenizador,
arquitetura) é preparação; é aqui que os pesos deixam de ser ruído.

⚠️ O COLAB VAI CAIR. Nesta sessão o runtime foi reciclado 4 vezes. O plano não torce
contra isso: checkpoint a cada N passos direto na Drive, retomada automática que
restaura modelo + otimizador + scheduler + POSIÇÃO NO DADO. Retomar sem a posição
faria o modelo reler o mesmo começo do corpus a cada queda — e memorizar justamente
o que já viu mais.

⭐ O QUE MONITORAR, em ordem de honestidade:
  1. amostras de texto geradas — o sinal mais cru de que está aprendendo
  2. perplexidade em holdout PT e EN SEPARADOS (misturar esconde regressão num idioma)
  3. norma do gradiente — dispara antes de a loss explodir
  4. loss — o menos informativo, porque cai mesmo quando o modelo está decorando

Uso:
    python bee/pretrain.py --tamanho 150m --dados bee/dados --out <drive>/bee-150m
    python bee/pretrain.py --passos 50 --dry-run     # valida o pipeline em 2 min
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))


def perda_do_lote(modelo, x):
    """⭐ O UNICO lugar deste arquivo que chama o modelo com `labels=`.

    Existe para que haja **um** call site a auditar, e para que
    `conferir_convencao_de_rotulos()` possa testa-lo por espionagem em vez de por
    magnitude de loss (que e' cega num modelo recem-inicializado).

    O rotulo e' o PROPRIO `x`: o transformers desloca por dentro
    (`loss = CE(logits[..., :-1, :], labels[..., 1:])`). Passar `x[1:]` desloca duas
    vezes e treina o modelo para prever t+2 — o bug que custou duas semanas e ~US$ 34.
    """
    return modelo(input_ids=x, labels=x).loss


def conferir_convencao_de_rotulos(modelo, x, dev) -> None:
    """🔴 GUARDA CONTRA DESLOCAMENTO DUPLO DE ROTULOS — o bug que custou o projeto inteiro.

    `LlamaForCausalLM.forward(labels=L)` JA desloca internamente:
        loss = CE(logits[..., :-1, :], L[..., 1:])
    Entao o rotulo correto e' o PROPRIO input (`labels=x`). Passar um `y` ja deslocado
    (`y = janela[1:]`) desloca DUAS vezes, e o modelo passa a ser treinado para prever
    **t+2** em vez de t+1.

    ⚠️ O QUE ISSO CUSTOU (2026-07-24 a 2026-08-07): treinou o Bee v1, o v3 e os tres
    pontos da escada de scaling. E NAO DA ERRO NENHUM — a loss cai, a perplexidade de
    validacao cai (77->63), o treino parece saudavel do inicio ao fim, porque a validacao
    usava a MESMA convencao errada. So aparece quando se mede o modelo com a convencao
    certa, e ai ele parece simplesmente ruim. Medido no v3:
        prever t+1 (correto) : ppl 898,2
        prever t+2 (o bug)   : ppl 130,2   <- e' aqui que o modelo esta
    Diagnosticos errados que este bug gerou e que foram publicados como conclusao:
    "mais token nao resolve", "o corpus saturou", "o gargalo e o tamanho do modelo",
    "trocar para 100% PT rende 0,37%". Nenhum deles era verdade.

    Esta funcao roda UMA vez, antes do passo 1, e custa um forward. Compara a loss que o
    modelo reporta com a loss calculada a mao na convencao t+1. Se divergirem, aborta.
    """
    import torch
    import torch.nn.functional as F

    # ------------------------------------------------------------------ 1) ESTRUTURAL
    # 🔴 A VERSAO ANTERIOR DESTA GUARDA NAO PEGAVA O BUG QUE ELA EXISTE PARA PEGAR.
    # Ela comparava magnitudes de loss — e roda ANTES do passo 1, com o modelo recem
    # inicializado, cujas previsoes sao ~uniformes sobre o vocabulario. Prever t+1 ou t+2
    # da praticamente a MESMA loss (~ln 32000 = 10,37). Medido no proprio Bee-350M:
    #     convencao correta (labels=x) : 10,5384
    #     convencao errada  (labels=y) : 10,5414   -> diferenca de 0,003
    # O limiar era 0,01. **A guarda passaria com o bug ativo.** A regra do projeto avisava
    # sobre *tokens aleatorios*; o problema real e' o *modelo aleatorio*, e acontece mesmo
    # com dado de treino real.
    #
    # A correcao e' estrutural, nao numerica: o unico jeito de o bug voltar e' alguem mudar
    # o call site, entao e' o call site que tem de ser testado. `perda_do_lote()` e' o UNICO
    # lugar do arquivo que chama o modelo com `labels=`, e o espiao abaixo confere que o
    # tensor de rotulos e' **o mesmo objeto** do de entrada. Exato, instantaneo, e vale em
    # qualquer estado de treino.
    class _EspiaoDeRotulos:
        visto = None

        def __call__(self, input_ids=None, labels=None, **kw):
            _EspiaoDeRotulos.visto = (input_ids, labels)
            from types import SimpleNamespace
            return SimpleNamespace(loss=torch.zeros((), device=input_ids.device), logits=None)

    espiao = _EspiaoDeRotulos()
    perda_do_lote(espiao, x[:1])
    ids_vistos, rot_vistos = _EspiaoDeRotulos.visto
    # ⚠️ igualdade de VALOR, nao identidade de objeto: `labels=x.clone()` e' correto e a
    # versao por identidade abortava nele — falso positivo. `torch.equal` aceita o clone e
    # continua rejeitando qualquer deslocamento (o shift muda o shape, entao nem compara).
    ok = (ids_vistos is not None and rot_vistos is not None
          and rot_vistos.shape == ids_vistos.shape and torch.equal(rot_vistos, ids_vistos))
    if not ok:
        raise SystemExit("\n".join((
            "",
            "🔴 ABORTADO: o call site passa um tensor de rotulos DIFERENTE do de entrada.",
            "   O modelo ja desloca por dentro — o rotulo tem de ser o PROPRIO input.",
            "   Confira `perda_do_lote()`.")))
    print("  convencao    ✅ call site passa labels == input_ids (teste estrutural, exato)")

    # ------------------------------------------------------------------ 2) SEMANTICO
    # Confere que a formula do transformers e' a que supomos — se uma versao futura parar
    # de deslocar por dentro, `labels=x` passa a estar errado e nada avisaria.
    #
    # ⚠️ ESTE TESTE TEM POUCO PODER ANTES DO PASSO 1, E ISSO E' DECLARADO EM VEZ DE
    # DISFARCADO. Num modelo recem-inicializado as previsoes sao quase uniformes, entao
    # t+1 e t+2 dao quase a mesma loss (medido: 10,5384 vs 10,5414). Tentei dar 30 passos
    # de sobreajuste para dar poder ao teste e foi PIOR: com AdamW estourou os 8 GB da 5070,
    # e com SGD lr=0,5 o modelo COLAPSOU para uniforme exato (loss 10,3735 = ln 32000) —
    # t+1 e t+2 passaram a empatar em 0,0000, isto e, o remedio cegou o teste que vinha
    # curar. Um teste que danifica o modelo para ganhar poder marginal e depois se declara
    # cego e' pior que nao ter teste. Voltou a ser um forward, e o **estrutural acima** e'
    # quem de fato guarda a convencao.
    modelo.eval()
    with torch.no_grad():
        saida = modelo(input_ids=x[:1], labels=x[:1])
        lg = saida.logits
        manual = F.cross_entropy(lg[0, :-1].float(), x[0, 1:]).item()
        t2 = F.cross_entropy(lg[0, :-2].float(), x[0, 2:]).item()   # a tarefa do bug
    modelo.train()
    dif = abs(saida.loss.item() - manual)
    folga = abs(t2 - manual)
    print(f"  convencao    loss {saida.loss.item():.4f} · t+1 na mao {manual:.4f} "
          f"(dif {dif:.5f}) · t+2 daria {t2:.4f} (folga {folga:.4f})")
    if folga < 0.05:
        print(f"  convencao    ⚠️ folga t+1/t+2 de apenas {folga:.4f} — o teste NUMERICO nao"
              f" distingue as convencoes neste ponto (modelo ainda nao aprendeu nada).\n"
              f"               Quem guarda aqui e' o teste estrutural. Isto e' esperado antes"
              f" do passo 1, NAO e' um problema.")
    if dif > 0.01:
        raise SystemExit("\n".join((
            "",
            f"🔴 ABORTADO: convencao de rotulos errada. O modelo reporta "
            f"{saida.loss.item():.4f} e a tarefa t+1 calculada a mao da {manual:.4f}.",
            "   Isso significa que o treino NAO esta otimizando 'prever o proximo token'.",
            "   Confira a chamada `modelo(input_ids=..., labels=...)`: o rotulo tem de ser",
            "   o PROPRIO input, porque o Llama ja desloca por dentro.")))


class AmostradorPermutado:
    """Percorre blocos NAO SOBREPOSTOS em ordem aleatoria — cobertura de 100% por epoca.

    🟠 POR QUE ISTO SUBSTITUIU `torch.randint` (medido em 2026-08-07)
      A versao anterior sorteava offsets COM REPOSICAO em todo o `train.bin`. Com 1 epoca
      nominal, cada token tem probabilidade `(1-1/n)^n -> 1/e` de nunca ser sorteado:

          --epocas 1.0 -> cobertura real 63,5%   (teorico 1-1/e = 63,2%)
          --epocas 2.0 -> 86,5%      --epocas 3.0 -> 94,9%

      Dos 9,87B tokens do v3, **~3,6B nunca entraram no treino**, enquanto outros foram
      repetidos. O log dizia "1.00 epocas" e o relatorio dizia "9,87B tokens"; os dois
      eram falsos, e nada no treino denunciava.

    ⚠️ A aleatoriedade CONTINUA necessaria, e pelo motivo documentado abaixo: o
      `train.bin` esta ordenado por fonte (web, depois livros, depois codigo), entao ler
      em ordem seria um curriculo acidental. A solucao nao e' voltar a ler sequencial —
      e' embaralhar a ORDEM DOS BLOCOS e percorrer a permutacao ate o fim.
    """

    def __init__(self, dados, seq_len: int, gerador):
        import torch
        self.dados, self.seq_len, self.g = dados, seq_len, gerador
        self.n_blocos = (len(dados) - 1) // seq_len
        if self.n_blocos < 1:
            raise ValueError(f"dados curtos demais: {len(dados)} tokens para seq_len {seq_len}")
        self.ordem = torch.randperm(self.n_blocos, generator=gerador).numpy()
        self.pos = 0
        self.epocas = 0

    def __call__(self, batch: int, device):
        import numpy as np
        import torch
        escolhidos = np.empty(batch, dtype=np.int64)
        n = 0
        while n < batch:
            if self.pos >= self.n_blocos:            # fim da epoca: nova permutacao
                self.ordem = torch.randperm(self.n_blocos, generator=self.g).numpy()
                self.pos, self.epocas = 0, self.epocas + 1
            k = min(batch - n, self.n_blocos - self.pos)
            escolhidos[n:n + k] = self.ordem[self.pos:self.pos + k]
            self.pos += k
            n += k
        ini = escolhidos * self.seq_len
        idx = ini[:, None] + np.arange(self.seq_len + 1)[None, :]
        janelas = torch.from_numpy(self.dados[idx].astype(np.int64))
        x = janelas[:, :-1]
        if device.type == "cuda":
            return x.pin_memory().to(device, non_blocking=True)
        return x.to(device)


def lote(dados, batch, seq_len, device, gerador):
    """Amostra `batch` janelas de `seq_len+1`. x = [:-1], y = [1:].

    ⚠️ `y` existe por razoes historicas e NAO deve ser passado como `labels` — ver
    conferir_convencao_de_rotulos(). Use `labels=x`.

    ⚠️ Amostragem ALEATÓRIA e não sequencial: com dado ordenado por fonte (o nosso é —
    as fontes foram coletadas uma após a outra), ler em ordem faria o modelo ver 4 GB de
    web, depois 1,8 GB de livros, depois código. Isso é currículo acidental, não
    escolhido: o modelo esqueceria a primeira fonte ao chegar na última.

    Vetorizado: um `take` com índices pré-computados em vez de list comprehension.
    2× mais rápido que a versão anterior — mas ⚠️ **isto NÃO era o gargalo**, e vale
    registrar para ninguém repetir a caçada:

    O treino ficou travado em 16–18k tok/s (~26% do teto da L4) em QUATRO configurações
    diferentes. Testei três hipóteses, e as três falharam:
      1. gradient checkpointing → desligar deu +32%, não o 13× que eu esperava;
      2. I/O da Drive por FUSE → copiar os 7,5 GB para o SSD local **piorou** (16,0k
         contra 17,9k);
      3. laço Python no carregador → medido: 0,14 ms/lote = 56M tok/s equivalentes,
         **0,03% do tempo de passo**. Irrelevante.

    O que sobra é a explicação estrutural: a arquitetura **fundo-e-fina** (30 camadas
    para apenas 576 de largura) é ótima em qualidade por parâmetro e ruim em eficiência
    de GPU — 30 camadas são 30× mais lançamentos de kernel, cada um com GEMMs pequenas
    que não saturam os tensor cores. O `torch.compile` deveria atacar exatamente isso e
    rendeu só +2%. **16k tok/s provavelmente é o que esta arquitetura roda nesta GPU**,
    e a conclusão certa é ajustar o ORÇAMENTO DE TOKENS, não continuar otimizando.
    """
    import numpy as np
    import torch
    ix = torch.randint(len(dados) - seq_len - 1, (batch,), generator=gerador).numpy()
    # offsets[i, j] = ix[i] + j  →  todas as janelas de uma vez, sem laço Python
    idx = ix[:, None] + np.arange(seq_len + 1)[None, :]
    janelas = torch.from_numpy(dados[idx].astype(np.int64))     # (batch, seq_len+1)
    x, y = janelas[:, :-1], janelas[:, 1:]
    if device.type == "cuda":
        return (x.pin_memory().to(device, non_blocking=True),
                y.pin_memory().to(device, non_blocking=True))
    return x.to(device), y.to(device)


def init_pesos(modelo, n_camadas: int):
    """normal(0, 0.02), com as projeções residuais escaladas por 1/sqrt(2*n_camadas).

    ⭐ SEM ESSA ESCALA REDES PROFUNDAS DIVERGEM nos primeiros passos. A intuição: cada
    bloco SOMA sua saída ao residual, então a variância cresce com a profundidade; se
    todas as projeções de saída começam com a mesma escala, o sinal explode ao atravessar
    30 camadas. Escalar as projeções que ESCREVEM no residual (`o_proj` da atenção e
    `down_proj` do MLP) mantém a variância estável na entrada de cada bloco.
    É o que GPT-2 faz, e o motivo de ele treinar sem warmup heroico.
    """
    import torch.nn as nn
    std_res = 0.02 / math.sqrt(2 * n_camadas)
    n_esc = 0
    for nome, p in modelo.named_parameters():
        if p.dim() >= 2:
            if nome.endswith(("o_proj.weight", "down_proj.weight")):
                nn.init.normal_(p, mean=0.0, std=std_res)
                n_esc += 1
            else:
                nn.init.normal_(p, mean=0.0, std=0.02)
    return std_res, n_esc


def lr_step_law(N: int, D: float) -> float:
    """η* = 1,79 · N^-0,713 · D^0,307 — Step Law, ajustada sobre ~3.700 modelos.

    ⚠️ **O LR DEPENDE DOS DOIS**, e por isso não se herda de outro degrau NEM de outro
    volume de dados. Foi o que aconteceu com o Bee-150M: os 3e-3 foram calculados quando
    o alvo era 3B de tokens; o corpus cresceu para 21,75B e o LR nunca foi recalculado.
    Para N=151M e D=21,75B a lei pede **3,93e-3** — o 150M treinou ~24% abaixo do ótimo.
    Para o 350M (N=345M, D=21,75B) ela pede **2,18e-3**.
    """
    return 1.79 * (N ** -0.713) * (D ** 0.307)


def lr_do_passo(passo: int, total: int, lr_max: float, warmup: int, lr_min_frac: float = 0.1,
                *, schedule: str = "wsd", inicio_decaimento: int | None = None):
    """Warmup linear + **WSD** (warmup-stable-decay) ou cosine.

    ⚠️ O warmup não é ritual: com LR alto (que modelos pequenos toleram e aproveitam), os
    primeiros passos sobre pesos aleatórios produzem gradientes enormes. Sem warmup, o
    otimizador dá um passo gigante numa direção sem sentido e a loss trava num platô.

    ⭐ POR QUE WSD E NÃO COSINE (docs/estudo-bee-350m.md §1.4)
    O cosine precisa saber o horizonte no passo 1. Sob teto de US$ 300, se a corrida
    precisar parar antes do fim, o cosine deixa o modelo num estado ruim — LR ainda alto,
    sem ter decaído. O WSD é **horizon-free**: warmup → fase estável em `lr_max` →
    decaimento só nos últimos `frac` passos. A decisão de onde decair pode ser tomada
    DEPOIS, com `--decair-a-partir-de`, o que permite estender a fase estável se sobrar
    orçamento sem replanejar nada.

    Medido em: arXiv:2602.02522 (IMU-1, modelo final de 430M com ablações num proxy de
    70M — abaixo do Bee-150M) reporta que 20% de decaimento **iguala o cosine**; e
    arXiv:2602.03702 (*Anytime Pretraining*) avalia exatamente **150M e 300M**, as duas
    escalas do Bee.

    ⭐ **A FASE ESTÁVEL FICA EM 55% DO PICO** — verificado no HTML do IMU-1 (§3.4), que era
    um `[VERIFICAR]` do estudo: *"set stable-phase LR to 55% of peak cosine LR based on
    preliminary experiments (0.013 for Muon 2D params, 0.0039 for 1D params)"*. Confere com
    os picos declarados: 0,0235 × 0,55 = 0,0129 ≈ 0,013.

    O racional, que é o que torna o número transferível: um cosine passa a maior parte do
    tempo **abaixo** do pico — a média fica em ~55% dele. A Step Law foi ajustada sobre runs
    com cosine, então o η* dela é um **pico**, não um LR constante. Segurar 100% do η* por
    todo o treino colocaria a média muito acima do regime em que a lei foi calibrada.

    ⚠️ **Ressalva honesta:** os 55% vêm de *preliminary experiments* com **Muon**, não de uma
    ablação publicada, e o Bee usa AdamW. O racional é agnóstico ao otimizador, mas o número
    exato não foi medido para o nosso caso. Ajustável por `--lr-estavel-frac`.

    O decaimento usa **1−√t** (a forma do IMU-1), que cai rápido no começo da fase.
    """
    if passo < warmup:
        return lr_max * (passo + 1) / warmup
    if schedule == "cosine":
        prog = (passo - warmup) / max(1, total - warmup)
        return lr_max * (lr_min_frac + (1 - lr_min_frac) * 0.5 * (1 + math.cos(math.pi * prog)))
    # ---- WSD
    ini = total if inicio_decaimento is None else inicio_decaimento
    if passo < ini:
        return lr_max                                  # fase ESTÁVEL
    prog = (passo - ini) / max(1, total - ini)
    return lr_max * (lr_min_frac + (1 - lr_min_frac) * (1 - math.sqrt(min(1.0, prog))))


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--tamanho", default="150m")
    ap.add_argument("--dados", type=Path, default=ROOT / "bee" / "dados")
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "bee" / "tokenizer")
    ap.add_argument("--out", type=Path, default=Path("/content/drive/MyDrive/BEE/bee-150m"))
    ap.add_argument("--tokens-alvo", type=float, default=3e9)
    ap.add_argument("--epocas", type=float, default=0.0,
                    help="se >0, IGNORA --tokens-alvo e deriva do tamanho REAL do train.bin. "
                         "1.0 = ve cada token exatamente uma vez. Mais robusto que estimar: "
                         "o numero sai do arquivo, nao de uma conta minha com bytes/palavra.")
    ap.add_argument("--micro-batch", type=int, default=4,
                    help="⚠️ 8 ESTOURA a VRAM da L4: a matriz de logits e "
                         "mb x 2048 x 32000 em fp32 = 2 GB, e o cross_entropy precisa de "
                         "outra copia pro softmax. O termo que domina escala com o VOCAB, "
                         "nao com os parametros — e num modelo de 150M o vocab e enorme "
                         "em relacao ao resto.")
    ap.add_argument("--grad-accum", type=int, default=64,
                    help="batch efetivo = micro-batch * grad_accum * seq_len tokens. "
                         "4x64 da os MESMOS 524k tokens/passo que 8x32 — o batch efetivo "
                         "nao muda, so o pico de memoria")
    ap.add_argument("--sem-checkpointing", action="store_true",
                    help="desliga o gradient checkpointing (mais rapido, muito mais VRAM)")
    ap.add_argument("--compilar", action="store_true", default=True,
                    help="torch.compile: funde kernels, ataca o overhead de lancamento "
                         "que e o nosso gargalo real (rodavamos a 26%% do teto da L4)")
    ap.add_argument("--sem-compilar", dest="compilar", action="store_false")
    ap.add_argument("--liger", action="store_true", default=True,
                    help="Liger Kernel: fused linear cross-entropy. NAO materializa a "
                         "matriz de logits (mb x 2048 x 32000 fp32 = 2 GB por micro-batch), "
                         "que e o gargalo de VRAM da L4 e escala com o VOCAB, nao com os "
                         "parametros. Libera micro-batch grande => throughput perto do pico.")
    ap.add_argument("--sem-liger", dest="liger", action="store_false")
    ap.add_argument("--auto-batch", action="store_true", default=True,
                    help="ao dar OOM, reduz o micro-batch pela metade e dobra o accum, "
                         "preservando o batch efetivo. Melhor que morrer no passo 3000")
    ap.add_argument("--lr", type=float, default=0.0,
                    help="0 = calculado pela Step Law a partir de N e D (recomendado). "
                         "⚠️ NAO herdar o LR de outro degrau nem de outro volume de dados")
    ap.add_argument("--warmup-frac", type=float, default=0.02)
    ap.add_argument("--schedule", choices=("wsd", "cosine"), default="wsd",
                    help="wsd = horizon-free (padrao); cosine exige saber o horizonte no passo 1")
    ap.add_argument("--lr-estavel-frac", type=float, default=0.55,
                    help="fracao do pico (Step Law) usada na FASE ESTAVEL do WSD. 0,55 vem do "
                         "IMU-1 §3.4: um cosine passa a maior parte do tempo abaixo do pico, "
                         "entao segurar 100%% do eta* constante extrapola o regime da lei")
    ap.add_argument("--frac-decaimento", type=float, default=0.20,
                    help="fracao FINAL dos passos em decaimento (IMU-1 mede que 20%% iguala o cosine)")
    ap.add_argument("--decair-a-partir-de", type=int, default=0,
                    help="passo em que o decaimento comeca; 0 = derivado de --frac-decaimento. "
                         "⭐ e' isto que torna o WSD horizon-free: da para estender a fase estavel "
                         "e so entao decidir onde decair, sem replanejar o run")
    ap.add_argument("--ckpt-cada", type=int, default=250)
    ap.add_argument("--marcos", default="",
                    help="⭐ INSTRUMENTACAO. Lista de marcos em BILHOES de tokens "
                         "(ex.: 1,3,6,10,15,22). Em cada marco salva um SNAPSHOT completo "
                         "do modelo em <out>/marco_<N>B/. Isso transforma UM run numa "
                         "escada de scaling inteira: avaliar bpb nos snapshots depois "
                         "custa centavos e da N pontos de curva pelo preco de um treino. "
                         "⚠️ Sem isto o ckpt e' sobrescrito e so sobra o ponto final.")
    ap.add_argument("--aval-cada", type=int, default=250)
    ap.add_argument("--amostra-cada", type=int, default=500)
    ap.add_argument("--passos", type=int, default=0, help="0 = derivado de --tokens-alvo")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="valida o pipeline e sai")
    args = ap.parse_args()

    import numpy as np
    import torch
    from transformers import AutoTokenizer
    from config import ESCADA, classe_do_modelo, para_hf_config

    cfg = ESCADA[args.tamanho]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    g = torch.Generator().manual_seed(args.seed)

    meta_p = args.dados / "meta.json"
    if not meta_p.exists():
        print(f"ERRO: {meta_p} não existe. Rode bee/prepare_data.py antes.", file=sys.stderr)
        return 1
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    treino = np.memmap(args.dados / "train.bin", dtype=np.uint16, mode="r")
    val = np.memmap(args.dados / "val.bin", dtype=np.uint16, mode="r")

    tokens_por_passo = args.micro_batch * args.grad_accum * cfg.seq_len
    # ⭐ `--epocas` deriva o alvo do arquivo REAL. Estimar tokens a partir de GB de texto
    # depende de "bytes por palavra" e da fertilidade — duas aproximações minhas que
    # erram fácil. O `len(treino)` não erra: é o número de tokens que existe no disco.
    alvo = args.epocas * len(treino) if args.epocas else args.tokens_alvo
    passos = args.passos or int(alvo / tokens_por_passo)
    warmup = max(10, int(passos * args.warmup_frac))
    tokens_totais = passos * tokens_por_passo
    if args.lr <= 0:
        args.lr = lr_step_law(cfg.params, tokens_totais)
        origem_lr = f"Step Law (N={cfg.params/1e6:.0f}M, D={tokens_totais/1e9:.2f}B)"
    else:
        origem_lr = "informado na linha de comando"
    ini_dec = (args.decair_a_partir_de if args.decair_a_partir_de > 0
               else int(passos * (1 - args.frac_decaimento)))
    # ⭐ no WSD o LR que o treino de fato usa e' a FASE ESTAVEL, nao o pico do cosine.
    lr_pico = args.lr
    lr_efetivo = args.lr * args.lr_estavel_frac if args.schedule == "wsd" else args.lr

    print("=" * 76)
    print(f"⭐ PRÉ-TREINO {cfg.nome} — pesos aleatórios → modelo")
    print("=" * 76)
    print(f"  dispositivo   {dev}  {torch.cuda.get_device_name(0) if dev.type=='cuda' else ''}")
    print(f"  parâmetros    {cfg.params/1e6:.1f}M · vocab {cfg.vocab} · seq_len {cfg.seq_len}")
    print(f"  dados         treino {len(treino)/1e9:.3f}B tok · val {len(val)/1e6:.1f}M tok")
    print(f"  batch         {args.micro_batch} x {args.grad_accum} x {cfg.seq_len} = "
          f"{tokens_por_passo/1e3:.0f}k tokens/passo")
    print(f"  passos        {passos} (warmup {warmup}) → {passos*tokens_por_passo/1e9:.2f}B tokens")
    print(f"  épocas        {passos*tokens_por_passo/max(1,len(treino)):.2f}")
    if args.schedule == "wsd":
        print(f"  LR            pico {lr_pico:.3e} ({origem_lr})")
        print(f"                → fase estável em {lr_efetivo:.3e} "
              f"({100*args.lr_estavel_frac:.0f}% do pico, IMU-1 §3.4)")
        print(f"  schedule      WSD: warmup {warmup} → estável até {ini_dec} → decai 1−√t "
              f"nos últimos {passos-ini_dec} passos ({100*(passos-ini_dec)/max(1,passos):.0f}%)")
        print(f"                ⭐ horizon-free: --decair-a-partir-de permite estender a fase "
              f"estável sem replanejar")
    else:
        print(f"  LR            {args.lr:.3e} cosine → {args.lr*0.1:.3e} · {origem_lr}")
    print(f"  horas est.    {cfg.horas_treino_l4(passos*tokens_por_passo):.1f} h de L4")
    print(f"  checkpoint    a cada {args.ckpt_cada} passos em {args.out}")

    if meta["vocab"] != cfg.vocab:
        print(f"\n🔴 INCOMPATÍVEL: dados tokenizados com vocab {meta['vocab']}, "
              f"modelo espera {cfg.vocab}. Os ids não significam a mesma coisa — "
              f"retokenize ou troque o config.", file=sys.stderr)
        return 1

    # ⭐ LIGER KERNEL — fused linear cross-entropy. O pico de VRAM neste modelo e a matriz
    # de logits (mb x 2048 x 32000 fp32 = 2 GB por unidade de micro-batch), que escala com o
    # VOCAB, nao com os parametros. O Liger funde a projecao final + o cross_entropy num
    # kernel que NUNCA materializa os logits inteiros — corta o pico drasticamente e libera
    # micro-batch grande, que era o que segurava a L4 em ~26%% de utilizacao. Aplica-se ANTES
    # de instanciar o modelo (faz monkey-patch da classe Llama). O loop passa `labels=` ao
    # forward (linha ~320), entao o fused CE entra sozinho.
    # ⚠️ O PATCH E POR FAMILIA. Este bloco chamava `apply_liger_kernel_to_llama` FIXO; com o
    # 350M em Qwen3 isso nao patcharia absolutamente nada e o log ainda imprimiria sucesso —
    # mais um caso da familia "nao da erro, so nao acontece". O despacho abaixo, mais a guarda
    # pos-instanciacao, fecham o buraco.
    liger_pedido = args.liger
    if liger_pedido:
        try:
            import liger_kernel.transformers as _lk
            aplicar = getattr(_lk, f"apply_liger_kernel_to_{cfg.arquitetura}", None)
            if aplicar is None:
                raise AttributeError(
                    f"liger nao tem apply_liger_kernel_to_{cfg.arquitetura} nesta versao")
            aplicar(fused_linear_cross_entropy=True, cross_entropy=False,
                    rms_norm=True, rope=True, swiglu=True)
            print(f"  liger        patch de {cfg.arquitetura}: fused linear CE + RMSNorm/RoPE/SwiGLU")
        except Exception as e:
            print(f"  liger        indisponivel ({type(e).__name__}: {e}) — seguindo sem. "
                  f"pip install liger-kernel", file=sys.stderr)
            liger_pedido = False
    # ⭐ a FAMILIA vem do config (llama ou qwen3). Qwen3 = Llama + QK-Norm, sem custom code.
    modelo = classe_do_modelo(cfg)(para_hf_config(cfg))

    # ⭐ GUARDA: o patch do Liger e monkey-patch de classe. Se ele "aplicou" mas o modelo nao
    # carrega uma classe do liger, o patch nao pegou — e a unica evidencia seria a corrida
    # ficar mais lenta e usar mais VRAM do que o previsto, sem nenhuma mensagem.
    if liger_pedido:
        alvos = [type(modelo.model.layers[0].input_layernorm).__module__,
                 type(modelo.model.layers[0].mlp).__module__]
        if not any("liger" in m for m in alvos):
            print(f"\n🔴 ABORTA: liger foi aplicado mas o modelo nao carrega classe do liger "
                  f"({alvos}). O patch nao pegou — rode com --sem-liger ou conserte.",
                  file=sys.stderr)
            return 1
        print("  liger        ✅ conferido no modelo instanciado")
    # ⭐ GRADIENT CHECKPOINTING: não guarda as ativações intermediárias do forward;
    # recomputa-as no backward. Troca ~30% de tempo por uma queda grande de VRAM.
    # Num treino de 31 h, 30% mais lento é muito melhor que um OOM no passo 3.000 —
    # e o OOM ACONTECEU no dry-run com micro-batch 8.
    if not args.sem_checkpointing:
        modelo.gradient_checkpointing_enable()
        modelo.config.use_cache = False        # incompatível com checkpointing
    std_res, n_esc = init_pesos(modelo, cfg.n_camadas)
    # ⭐ torch.compile: funde kernels e elimina overhead de lançamento — que é
    # exatamente o nosso gargalo. Medido em 2026-07-27: rodávamos a 26% do teto da L4
    # (17,5k de 66k tok/s teóricos) porque cada micro-batch de 2×2048 = 4.096 tokens é
    # pequeno demais para saturar a GPU; ela passava mais tempo lançando kernels do que
    # calculando. ⚠️ A primeira chamada compila (1-3 min) e só depois acelera.
    if args.compilar:
        print("  compilando   torch.compile (1-3 min na primeira chamada)…", flush=True)
        modelo = torch.compile(modelo)
    print(f"\n  init          normal(0, 0.02); {n_esc} projeções residuais com std="
          f"{std_res:.5f} (=0.02/sqrt(2*{cfg.n_camadas}))")
    modelo.to(dev)

    def cru(m):
        """Desembrulha o `torch.compile`. Sem isto o state_dict sai com prefixo
        `_orig_mod.` e o `save_pretrained` não existe — o treino rodaria 20 h e
        quebraria exatamente na hora de salvar."""
        return getattr(m, "_orig_mod", m)

    real = sum(p.numel() for p in modelo.parameters())
    print(f"  conferido     {real/1e6:.1f}M params instanciados")

    # ⭐ weight decay SÓ nas matrizes. Aplicar em bias e RMSNorm encolhe parâmetros que
    # controlam escala, e isso atrapalha em vez de regularizar — erro comum e silencioso.
    decay = [p for n, p in modelo.named_parameters() if p.dim() >= 2]
    no_decay = [p for n, p in modelo.named_parameters() if p.dim() < 2]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": 0.1},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=args.lr, betas=(0.9, 0.95), eps=1e-8, fused=(dev.type == "cuda"))
    print(f"  otimizador    AdamW β(0.9,0.95) wd 0.1 em {len(decay)} matrizes, "
          f"0.0 em {len(no_decay)} bias/norm")

    inicio = 0
    args.out.mkdir(parents=True, exist_ok=True)
    ckpt_p = args.out / "checkpoint.pt"
    if ckpt_p.exists():
        # ⭐ RETOMADA COMPLETA: modelo + otimizador + passo. Sem o estado do Adam, os
        # momentos zeram e o treino leva centenas de passos para se recuperar — o que
        # numa sessão com 4 quedas significaria nunca convergir.
        ck = torch.load(ckpt_p, map_location=dev, weights_only=False)
        cru(modelo).load_state_dict(ck["modelo"])
        opt.load_state_dict(ck["opt"])
        inicio = ck["passo"] + 1
        if "gerador" in ck:
            # ⭐ `map_location=dev` move TODOS os tensores do checkpoint para a GPU —
            # inclusive o estado do gerador aleatório, que `torch.Generator.set_state()`
            # exige que seja SEMPRE um ByteTensor de CPU. Sem forçar `.cpu()` aqui, a
            # retomada quebra com "RNG state must be a torch.ByteTensor" assim que o
            # runtime recicla (achado ao vivo na 1ª retomada real desta sessão).
            g.set_state(ck["gerador"].cpu())
        print(f"\n♻️  RETOMANDO do passo {inicio}/{passos} "
              f"(loss {ck.get('loss', float('nan')):.4f})")

    if args.dry_run:
        print("\n[dry-run] validando 3 passos…")
        passos, args.ckpt_cada, args.aval_cada, args.amostra_cada = 3, 999, 999, 999

    tok = AutoTokenizer.from_pretrained(str(args.tokenizer))

    @torch.no_grad()
    def perplexidade(dados_, n_lotes=20):
        modelo.eval()
        perdas = []
        gv = torch.Generator().manual_seed(1234)          # fixo: comparável entre passos
        for _ in range(n_lotes):
            x, _ = lote(dados_, args.micro_batch, cfg.seq_len, dev, gv)
            with torch.autocast(device_type=dev.type, dtype=torch.bfloat16,
                                enabled=dev.type == "cuda"):
                perdas.append(perda_do_lote(modelo, x).item())
        modelo.train()
        m = sum(perdas) / len(perdas)
        return m, math.exp(min(20, m))

    @torch.no_grad()
    def amostra(prompt="O Brasil é", n=60):
        modelo.eval()
        ids = torch.tensor([tok(prompt, add_special_tokens=False)["input_ids"]], device=dev)
        out = modelo.generate(ids, max_new_tokens=n, do_sample=True, temperature=0.8,
                              top_k=50, pad_token_id=meta["eos"])
        modelo.train()
        return tok.decode(out[0], skip_special_tokens=True)

    # ⭐ Marcos convertidos de bilhoes-de-tokens para numero de passo.
    marcos_passo = []
    if args.marcos:
        for b in args.marcos.split(","):
            b = b.strip()
            if not b:
                continue
            n = int(float(b) * 1e9 / tokens_por_passo)
            if 0 < n <= passos:
                marcos_passo.append((n, f"{b}B"))
        marcos_passo.sort()
        print(f"  marcos        " + " · ".join(f"{r} (passo {n:,})" for n, r in marcos_passo))

    # Amostrador com cobertura de 100% por epoca (ver AmostradorPermutado).
    amostrador = AmostradorPermutado(treino, cfg.seq_len, g)
    print(f"  amostragem   {amostrador.n_blocos:,} blocos de {cfg.seq_len} tokens · "
          f"permutacao percorrida ate o fim (cobertura 100%/epoca)")

    # 🔴 Guarda de convencao de rotulos — roda ANTES do passo 1 e aborta se o treino nao
    # estiver otimizando "prever o proximo token". Custa um forward. Ver a docstring de
    # conferir_convencao_de_rotulos() para o que a ausencia dele custou a este projeto.
    # ⚠️ Usa dado de TREINO real: com tokens aleatorios a diferenca cai para ~0,007 e o
    # guarda nao dispara — sem estrutura no texto o modelo nao distingue t+1 de t+2.
    _x_teste = amostrador(min(2, args.micro_batch), dev)
    conferir_convencao_de_rotulos(modelo, _x_teste, dev)
    del _x_teste

    print("\n" + "-" * 76)
    modelo.train()
    t0, t_ult = time.time(), time.time()
    hist = []
    for passo in range(inicio, passos):
        lr = lr_do_passo(passo, passos, lr_efetivo, warmup,
                         schedule=args.schedule, inicio_decaimento=ini_dec)
        for grupo in opt.param_groups:
            grupo["lr"] = lr

        opt.zero_grad(set_to_none=True)
        perda_acc = 0.0
        for _ in range(args.grad_accum):
            # ⭐ AUTO-RECUPERAÇÃO DE OOM. A VRAM disponível no Colab varia entre sessões
            # (outro processo, fragmentação, o próprio driver). Um treino de 31 h que
            # morre no passo 3.000 por 100 MB a menos perde tudo desde o último
            # checkpoint. Aqui reduzimos o micro-batch pela metade e DOBRAMOS o accum —
            # o batch efetivo fica idêntico, então o treino continua estatisticamente
            # igual, só com pico de memória menor.
            try:
                x = amostrador(args.micro_batch, dev)
                with torch.autocast(device_type=dev.type, dtype=torch.bfloat16,
                                    enabled=dev.type == "cuda"):
                    perda = perda_do_lote(modelo, x) / args.grad_accum
                perda.backward()
                perda_acc += perda.item()
            except torch.OutOfMemoryError:
                if not args.auto_batch or args.micro_batch <= 1:
                    raise
                torch.cuda.empty_cache()
                args.micro_batch //= 2
                args.grad_accum *= 2
                print(f"  ⚠️ OOM no passo {passo} — micro-batch → {args.micro_batch}, "
                      f"accum → {args.grad_accum} (batch efetivo INALTERADO). Retomando.",
                      file=sys.stderr, flush=True)
                opt.zero_grad(set_to_none=True)
                perda_acc = 0.0
                break                      # refaz o passo inteiro com o novo tamanho
        # clip global: o gradiente dispara ANTES de a loss explodir — é o alarme precoce
        gnorm = torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0).item()
        opt.step()

        if passo % 10 == 0 or passo == passos - 1:
            dt = time.time() - t_ult
            t_ult = time.time()
            tks = 10 * tokens_por_passo / max(1e-9, dt) if passo else 0
            resta = (passos - passo) * dt / 10 / 3600
            print(f"passo {passo:>5}/{passos} · loss {perda_acc:.4f} · gnorm {gnorm:>6.2f} · "
                  f"lr {lr:.2e} · {tks/1e3:>5.1f}k tok/s · faltam {resta:>4.1f}h", flush=True)
            hist.append({"passo": passo, "loss": perda_acc, "gnorm": gnorm, "lr": lr})
            if gnorm > 50:
                print(f"  ⚠️ gnorm {gnorm:.1f} muito alto — se persistir, baixe o LR",
                      file=sys.stderr)

        if passo and passo % args.aval_cada == 0:
            lv, ppl = perplexidade(val)
            print(f"  ⭐ VALIDAÇÃO passo {passo}: loss {lv:.4f} · perplexidade {ppl:.1f}",
                  flush=True)
            hist.append({"passo": passo, "val_loss": lv, "ppl": ppl})

        if passo and passo % args.amostra_cada == 0:
            print(f"  💬 amostra: {amostra()!r}", flush=True)

        # ⭐ Marcos de instrumentacao: snapshot permanente do modelo, para a escada.
        if marcos_passo and passo >= marcos_passo[0][0]:
            n_passo, rotulo = marcos_passo.pop(0)
            destino = args.out / f"marco_{rotulo}"
            cru(modelo).save_pretrained(destino)
            tok.save_pretrained(destino)
            lm_, ppl_ = perplexidade(val, n_lotes=20)
            (destino / "marco.json").write_text(json.dumps(
                {"tokens": passo * tokens_por_passo, "passo": passo,
                 "val_loss": lm_, "val_ppl": ppl_}, indent=1), encoding="utf-8")
            print(f"  ⭐ MARCO {rotulo}: {passo*tokens_por_passo/1e9:.2f}B tokens · "
                  f"val loss {lm_:.4f} · ppl {ppl_:.1f} → {destino}", flush=True)

        if passo and passo % args.ckpt_cada == 0:
            torch.save({"modelo": cru(modelo).state_dict(), "opt": opt.state_dict(),
                        "passo": passo, "loss": perda_acc, "gerador": g.get_state(),
                        "cfg": args.tamanho}, ckpt_p)
            (args.out / "historico.json").write_text(json.dumps(hist, indent=1),
                                                     encoding="utf-8")
            print(f"  💾 checkpoint no passo {passo} → {ckpt_p}", flush=True)

    # ---------------------------------------------------------------- fim ---
    lv, ppl = perplexidade(val, n_lotes=50)
    print("\n" + "=" * 76)
    print(f"✅ TREINO CONCLUÍDO em {(time.time()-t0)/3600:.2f} h")
    print(f"   validação final: loss {lv:.4f} · perplexidade {ppl:.1f}")
    print(f"   amostra: {amostra()!r}")
    cru(modelo).save_pretrained(str(args.out / "modelo"))
    tok.save_pretrained(str(args.out / "modelo"))
    (args.out / "historico.json").write_text(json.dumps(hist, indent=1), encoding="utf-8")
    print(f"   modelo salvo em {args.out / 'modelo'}")
    print("\n   Próximo: eval/eval_bee_vs_smollm.py — ⭐ o GATE 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
