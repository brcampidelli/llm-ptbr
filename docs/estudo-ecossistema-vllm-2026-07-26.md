# Estudo — ecossistema vLLM (6 repos, 2026-07-26)

> Formato: o que o projeto faz → o que muda para a COMEIA → ação. Ferramenta que não muda nada eu
> digo que não muda, em vez de escrever parágrafo bonito.

---

## ⭐ 1. `guidellm` — a ferramenta que desbloqueia duas prioridades paradas

[vllm-project/guidellm](https://github.com/vllm-project/guidellm) — *"SLO-aware Benchmarking and
Evaluation Platform for Optimizing Real-World LLM Inference"*.

O que faz: mede **TTFT, ITL e latência ponta a ponta com distribuição completa** (não só média),
gera **tráfego sintético configurável** (síncrono, concorrente, por taxa) com *sweeps* reprodutíveis,
faz **replay de trace real** (formato Mooncake), e exporta JSON/CSV/**HTML com gráficos**.

**Por que isto importa mais que as outras cinco juntas:** a avaliação do projeto listou duas
prioridades paradas por falta de instrumento, e o `guidellm` é o instrumento das duas.

- **Prioridade 2 — fração de fast-path com carga que eu não escrevi.** Os 80% que estão no README
  foram medidos em **10 queries que eu mesmo redigi** para exercitar cada rota. É anedota com
  aparência de métrica. O gerador de tráfego do `guidellm` produz carga que não foi desenhada para
  casar com os nossos gatilhos — que é exatamente a condição que falta.
- **Prioridade 3 — a comeia ponta a ponta.** Nunca medimos o sistema, só as peças. A latência de
  18,3 s/query que reportamos é uma **média de 10 execuções**, sem percentil, sem concorrência, sem
  TTFT. O `guidellm` dá distribuição.

⚠️ **Ressalva:** ele mede **servidor de inferência**, então exige a comeia servida por HTTP
(vLLM). Hoje o `hive` é uma biblioteca Python que carrega o modelo no processo. Ou seja: usar o
`guidellm` **pressupõe** o passo do vLLM, não é independente dele.

**Ação:** é o próximo item do eixo de medição depois do professor. Ordem natural: servir a comeia no
vLLM → medir com `guidellm` → aí os números de latência e fast-path deixam de ser anedóticos.

---

## 2. `llm-compressor` — o caminho da Fase 5, e onde a tensão do ONNX se resolve

[vllm-project/llm-compressor](https://github.com/vllm-project/llm-compressor) — PTQ simples, GPTQ,
AWQ, SmoothQuant, AutoRound, rotação (SpinQuant/QuIP), poda de experts (REAP). Formatos W8A8
(int8/fp8), W4A16, W8A16, W4AFP8, microscale (NVFP4/MXFP4/MXFP8). Salva em `compressed-tensors`, que
**o vLLM carrega direto**.

**O que muda:** em 2026-07-25 registrei uma tensão sem resposta — *exportar hot-swap para ONNX tende
a exigir merge + N modelos, o que desfaz a economia de VRAM que é a tese da comeia*. O par
`llm-compressor` + vLLM é uma resposta plausível: quantiza o **backbone** e o vLLM serve **N LoRA por
cima**, preservando "1 modelo + N personalidades".

⚠️ **Não confirmado, e é a pergunta que decide:** a doc que consegui ler **não menciona suporte a
LoRA** nem quantização com adapter. Se o adapter tiver de ser mesclado antes de quantizar, voltamos
ao problema de N modelos. **Verificar antes de prometer a Fase 5.**

---

## 3. `aibrix` — resolve um problema que ainda não temos

[vllm-project/aibrix](https://github.com/vllm-project/aibrix) — infraestrutura Kubernetes-nativa para
inferência. Tem **"High-Density LoRA Management"** e gateway com roteamento LLM-aware.

**Leitura honesta:** *conceitualmente* é a comeia em escala de produção — muitos LoRA sobre base
compartilhada, com roteamento. Mas exige **Kubernetes**, e nós temos uma L4 no Colab e nenhum
usuário. Adotar agora seria construir a operação antes do produto.

**Ação:** nenhuma. Fica marcado como o destino natural **se** a comeia algum dia servir tráfego real.
Registrar que existe evita reinventá-lo depois.

---

## 4. `vllm-omni` — a Fase 4 pode ficar bem mais barata

[vllm-project/vllm-omni](https://github.com/vllm-project/vllm-omni) — inferência omni-modal.
**Entrada** texto/imagem/áudio/vídeo; **saída** também multimodal, incluindo TTS. Suporta Qwen3-Omni,
Cosmos3, BAGEL, TTS (Qwen3-TTS, CosyVoice3), difusão (FLUX, Wan2.2). Primeira **release estável**
0.14.0 em fev/2026, já em 0.20.0+.

**O que muda:** o plano previa a Fase 4 como *"abelha multimodal, modelo separado ~9B, a única fora
do backbone único, a mais cara em VRAM"*. Somando com o que vimos no HF — **Qwen3.6 (27B e 35B-A3B) é
multimodal nativo** — a Fase 4 deixa de ser "adicionar um modelo grande separado" e passa a ser
"trocar o backbone por um que já vê imagem". Muda de aditiva para substitutiva.

⚠️ Trocar o backbone **invalida os três adapters** e todas as medições. E o baseline externo de hoje
sugere que o 4B **não é o limitante** (o adapter em 4B ganha do prompt em 4B por +15,1 pp) — o
limitante era método. Então: não trocar agora, e reavaliar quando a barreira for capacidade.

---

## 5-6. `tpu-inference` e `vllm-ascend` — sem ação

[tpu-inference](https://github.com/vllm-project/tpu-inference) (Google TPU) e
[vllm-ascend](https://github.com/vllm-project/vllm-ascend) (Huawei Ascend NPU). Backends de hardware
que não temos e não vamos ter. Contexto: mostram que o vLLM está virando a camada de portabilidade do
ecossistema aberto — o que **reforça** a escolha do vLLM como alvo de serving, mas não muda nada hoje.

---

## Resumo — ordenado por valor para nós

| # | Projeto | O que muda | Custo |
|---|---|---|---|
| 1 | **guidellm** | ⭐ instrumento das Prioridades 2 e 3 (fast-path com carga real, comeia ponta a ponta com percentil) | exige servir no vLLM primeiro |
| 2 | **llm-compressor** | caminho da Fase 5 preservando a tese; ⚠️ suporte a LoRA **não confirmado** | verificar antes de prometer |
| 3 | **vllm-omni** | Fase 4 vira substitutiva (trocar backbone) em vez de aditiva (+9B) | não fazer agora |
| 4 | **aibrix** | destino natural em produção real; exige K8s | nenhuma ação |
| 5-6 | tpu-inference · vllm-ascend | contexto: vLLM como camada de portabilidade | nenhuma |

**A leitura de conjunto:** as seis peças apontam para a mesma decisão — **servir a comeia no vLLM é o
próximo passo estrutural**, não porque queremos escalar, mas porque é o que destrava a medição
honesta (guidellm), o empacotamento (llm-compressor) e, mais adiante, o multimodal (vllm-omni) e a
operação (aibrix). Hoje a comeia é uma biblioteca; isso limita o que dá para medir sobre ela.
