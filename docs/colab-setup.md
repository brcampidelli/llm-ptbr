# Migração para Google Colab Pro+ — por quê e como

## Por que migrar (motivado por dados, não preferência)

**Todos os incidentes do dia 2026-07-23 tiveram a mesma raiz: 8 GB de VRAM + Windows.**

| Incidente | Causa raiz | No Colab |
|---|---|---|
| Treino a **716 s/passo** (ETA 21 h) | VRAM saturada → thrashing | A100 40 GB (5x) |
| `max_seq_len` teve que cair 2048 → 1536 | idem | 2048+ tranquilo |
| Avaliação a **0,025 req/s** com adapter | idem | idem |
| `expandable_segments` não fez efeito | **não suportado no Windows** | funciona no Linux |
| Fallback lento do *gated delta rule* | `flash-linear-attention` + `causal-conv1d` exigem triton/compilação CUDA — **inviável no Windows** | **instalam via pip** |

⚠️ **O item mais importante é o último.** O Qwen3.5 usa *gated delta rule*; rodamos o tempo todo no
caminho lento em torch puro. No Colab (Linux + toolchain CUDA) o caminho rápido instala — isso pode
valer outro múltiplo de velocidade, somado ao ganho de VRAM.

**Consequência:** o Qwen3.5-9B, planejado como "cloud paga quando houver tração", vira viável agora.

## Setup do colab-mcp (feito em 2026-07-24)

Adicionado em `C:\Users\brcam\.claude.json` → `mcpServers`:
```json
"colab-mcp": {
  "command": "C:/Users/brcam/AppData/Local/hermes/bin/uvx.exe",
  "args": ["--index", "https://pypi.org/simple", "git+https://github.com/googlecolab/colab-mcp"],
  "timeout": 30000
}
```
Backup do config anterior: `C:\Users\brcam\.claude.json.bak-antes-colab-mcp`

**Verificado:** `uvx` 0.11.18 instala o pacote (104 deps) e o binário responde. Expõe um
*runtime proxy* (ligado por padrão) que faz a ponte com a sessão do navegador.

**Para ativar:** reiniciar o Claude Code + manter uma aba do Colab aberta e logada.

### Limitações conhecidas (release recente, doc enxuta)
- **Exige aba do Colab aberta** — faz ponte com a sessão do navegador, não é headless.
- A documentação **não confirma** troca de runtime/GPU nem upload/download de arquivos via MCP.
  Pode ser necessário fazer isso pela interface do Colab.
- Projeto não aceita contribuições externas; feedback via GitHub Discussions.

## Arquitetura proposta (dividir por afinidade, não migrar tudo)

| Onde | O quê | Por quê |
|---|---|---|
| **PC local** | Código, pipeline de dados, destilação, inferência quantizada | Destilação é rede/API, não GPU — rodou perfeito aqui (1.906 pares, 0 falhas) |
| **Colab A100/L4** | Treino e avaliação | É onde os 8 GB doem |
| **Git** | Ponte | A cópia local segue sendo a fonte da verdade; Colab clona/puxa |
| **Google Drive** | Checkpoints | Sobrevive a reset de runtime |

## Cuidados
- **Unidades de computação:** cota mensal do Pro+. A100 consome bem mais rápido que L4.
  Estratégia: **L4 para iterar, A100 só para rodadas longas.** Conferir consumo/hora na conta.
- **Desconexão de runtime:** salvar checkpoints no Drive, não no disco efêmero.
- Pro+ tem execução em segundo plano — o notebook continua rodando com o navegador fechado.

## Primeiro teste ao migrar
**Instalar `flash-linear-attention` e medir o ganho.** Se o caminho rápido do gated delta rule
funcionar, todo o custo/tempo do projeto muda de patamar e as decisões de `max_seq_len` e
`batch_size` tomadas nesta máquina deixam de valer.
