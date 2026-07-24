"""Bootstrap de ambiente para o Colab (L4/A100) — evita o hand-typing frágil.

Uso no Colab (3 células curtas, nesta ordem):

    # Célula 1 — instalar deps na ORDEM certa e reiniciar
    !pip install -q -U bitsandbytes flash-linear-attention
    import os; os.kill(os.getpid(), 9)   # força restart do runtime

    # (o Colab reconecta sozinho; rode a Célula 2)

    # Célula 2 — clonar o pipeline e conferir ambiente
    !git clone https://github.com/brcampidelli/llm-ptbr.git 2>/dev/null || (cd llm-ptbr && git pull)
    !python llm-ptbr/colab/env_check.py

    # Célula 3 — treinar de verdade (nada de digitar código a mao)
    !cd llm-ptbr && python train/sft_qlora.py --data <dados> --epochs 1

## Lições aprendidas em 2026-07-24 (Colab L4, sessão de validação)

### 1. Ordem de instalação + restart (bitsandbytes)
- O Colab pré-instala um bitsandbytes antigo (< 0.46.1); o transformers 5.x exige
  >= 0.46.1. Por isso o `-U`.
- Instalar e importar na MESMA sessão falha: o transformers cacheia
  `is_bitsandbytes_available()=False` no início e não re-verifica.
  Resultado: `ImportError: requires bitsandbytes>=0.46.1` mesmo com 0.49.2 instalado.
  **Correção: instalar tudo, REINICIAR o runtime, e só então importar.** Validado:
  após restart, o modelo carregou em 4-bit (VRAM 4.17 GB).

### 2. ⚠️ flash-linear-attention SOZINHO NÃO ativa o caminho rápido (correção importante)
- Instalar `flash-linear-attention` NÃO basta. Com só ele, o transformers ainda diz:
  `"The fast path is not available because one of the required library is not installed"`.
  O gated delta rule do Qwen3.5 precisa **também de `causal-conv1d`** (e ambos têm
  que importar limpo). Minha afirmação anterior ("fla instala → velocidade resolvida")
  estava PREMATURA: instalar ≠ ativar.
- **Fix a testar:** `pip install -U flash-linear-attention causal-conv1d` + restart,
  e VERIFICAR que o warning some antes de confiar na velocidade.

### 3. O fallback torch do gated delta rule é O(seq²) de memória
- Com o caminho rápido inativo, um forward+backward em **seq 2341 deu OutOfMemory
  MESMO na L4 de 22 GB**. O fallback aloca `attn[:i,:i]` num laço — explode com o
  comprimento. Isso reforça por que o caminho rápido (item 2) é essencial, não opcional.
- Enquanto o fast path não estiver ativo: manter `max_seq_len` baixo (≤1024) OU
  resolver o item 2 antes de treinar de verdade.

### 4. Hand-typing de células no navegador é frágil — não repetir
- Auto-fechamento de parênteses, cache de sessão, edição multi-linha: custou muito
  tempo. **Doravante: clonar o repo e rodar `!python train/...`**, não digitar código.

## Repo privado — autenticação do clone
O repo llm-ptbr é privado. Duas opções para o clone no Colab:
  (a) Secret do Colab: adicionar GH_TOKEN em Secrets (icone de chave) e usar
      `from google.colab import userdata; token = userdata.get('GH_TOKEN')`
      `!git clone https://$token@github.com/brcampidelli/llm-ptbr.git`
  (b) Tornar o repo publico temporariamente (contem so codigo, sem segredos/dados).
Preferir (a) — nao expoe token no notebook salvo.

## Dados
O dataset (data/processed/sft_ptbr.jsonl) NAO vai no repo (.gitignore). No Colab,
montar o Drive e apontar --data para o arquivo la, OU regenerar via pipeline data/.
"""

print("Este arquivo e documentacao do fluxo Colab. Ver docstring.")
