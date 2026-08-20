# Colab CLI + Pro+ — reavaliação do Colab para o Bee

> **2026-08-19.** O projeto migrou do Colab para o RunPod em 2026-08-03 por um motivo medido, e
> essa decisão continua certa **para o que ela decidiu**. O que mudou desde então é o
> ferramental, e ele muda a resposta para um caso diferente. Este documento separa os dois.

---

## 1. Por que o Colab foi abandonado — e o que aquilo decidiu de fato

Registro de 2026-08-03, durante o pré-treino do Bee v3:

- o Colab **reciclou 2×** no meio de um run de 21,76 h e depois **esgotou a cota de A100 do
  Pro+**, forçando a migração no meio;
- o RunPod entregou as 21,76 h sem uma interrupção, a US$ 1,50/h (~US$ 34 no run inteiro);
- ⚠️ **mas o Colab era mais RÁPIDO**: ~85k tok/s contra ~70k do RunPod, porque o `/workspace`
  do RunPod é network-fs (−18%).

⭐ **O que aquela decisão realmente decidiu:** que **run longo e contínuo** vai para o RunPod.
Ela nunca foi testada contra o caso de **muitos runs curtos**, porque o projeto não tinha esse
caso — agora tem: o grid do E2 são **15 treinos de ~20 min cada**.

Reciclagem a cada poucas horas é fatal para um run de 22 h e **irrelevante** para um job de 20
minutos.

---

## 2. O que mudou no ferramental (verificado hoje)

### 2.1 Colab CLI — o item que muda o jogo

Anunciada em **2026-06-05** (`developers.googleblog.com/introducing-the-google-colab-cli`),
repositório `googlecolab/google-colab-cli`. **Instalada e verificada nesta máquina hoje:
versão 0.6.0.**

```bash
colab run --gpu A100 train.py     # provisiona, roda script LOCAL, baixa saída, derruba a VM
```

O que ela resolve, ponto a ponto contra os problemas conhecidos do projeto:

| problema | o que a CLI faz |
|---|---|
| dependência de aba de navegador aberta | **daemon de keep-alive** próprio: "mantém a alocação ativa **sem exigir abas de navegador abertas**" |
| esquecer a VM ligada queimando cota | `colab run` provisiona, executa e **derruba automaticamente** |
| subir código para a máquina remota | `colab exec -f script.py` lê o arquivo **local** e transmite; não precisa upload |
| recuperar artefato | `colab download` · `colab log -o log.ipynb` |
| acesso interativo | `colab ssh` sobre WebSocket, e serve de `ProxyCommand` do OpenSSH para dev remoto em IDE |

O anúncio cita **Claude Code nominalmente** como cliente previsto, e a CLI traz um *skill file*
com o contexto de uso para agentes.

### 2.2 Aceleradores disponíveis — confirmado no `--help` da CLI instalada

> `--gpu <str>  GPU accelerator variant. Supported: **T4, L4, G4, H100, A100**.`
> `--tpu <str>  TPU accelerator variant. Supported: v5e1, v6e1.`

⭐ **H100 e G4 são novos para este projeto.** O "G4" é o que o painel do Colab anuncia como
*"GPUs Nvidia RTX Pro 6000 Blackwell Server Edition em máquinas G4 **para assinantes do Colab
Pro+**"* — 96 GB de VRAM. O projeto nunca teve acesso a nenhuma das duas.

### 2.3 Plano atual: **Pro+**, não Pro

Verificado na página de preços com a conta logada:

| plano | preço | unidades |
|---|---|---|
| Pay As You Go | R$ 58 / 100 un · R$ 258 / 500 un | expiram em 90 dias |
| Colab Pro | R$ 58/mês | 100 un/mês |
| **Colab Pro+ ← PLANO ATUAL** | **R$ 258/mês** (~US$ 48) | **600 un/mês** |

E o Pro+ é o único com **execução em segundo plano: até 24 h contínuas**, com o timeout de
inatividade valendo só depois que o código termina.

---

## 3. O que NÃO mudou — e por que o RunPod continua no lugar dele

🔴 **A política de recursos não garantidos é a mesma, e está escrita:**

> *"o Colab precisa manter a flexibilidade para o **ajuste dinâmico dos limites de uso e da
> disponibilidade de hardware**"*
> *"GPUs premium (…) sujeitas à disponibilidade e ao saldo de unidades. **Os tipos de GPUs
> disponíveis variam com o tempo.**"*

⚠️ O keep-alive da CLI evita o encerramento por **inatividade**. Ele não evita — e não promete
evitar — interrupção por **cota** ou por indisponibilidade de hardware, que foi exatamente o
que quebrou o run de agosto.

⚠️ **E "os tipos de GPU variam com o tempo" colide de frente com a regra de `$/B tokens` deste
projeto.** Custo por token exige saber qual placa se recebe. No RunPod isso é um contrato; no
Colab é uma expectativa.

⚠️ **A CLI não roda em Windows** — "Linux and macOS only". Aqui foi instalada no **WSL2/Ubuntu**,
que já existia na máquina. Funciona, mas é uma camada a mais, e o acesso à GPU é da VM remota,
não da 5070 local, então o WSL é só o cliente.

❓ **Número que não consegui obter e que falta para fechar a conta: quantas unidades de
computação cada GPU-hora consome.** Não está na página de preços nem no FAQ; só aparece no
painel de recursos de uma sessão ativa — e abrir sessão com GPU **gasta unidade**, então não
fiz. Sem esse número, não dá para comparar Colab e RunPod em `$/B tokens`. **É a primeira
medição a fazer**, e custa poucos minutos de uma sessão T4.

---

## 4. Recomendação

**Manter os dois, com divisão por tipo de carga — não escolher um.**

| carga | onde | por quê |
|---|---|---|
| pré-treino longo e contínuo (dias) | **RunPod** | reciclagem e cota inviabilizam; preço e placa são contrato |
| **grid do E2: 15 SFTs de ~20 min** | **Colab CLI** | `colab run` é feito para isso; reciclagem é irrelevante em 20 min; a assinatura já está paga |
| avaliação pesada com GPU grande | **Colab (G4/H100)** | acesso a 96 GB que o projeto não tem em lugar nenhum |
| avaliação leve, iteração | **5070 local** | US$ 0 |

⭐ **O ganho concreto e imediato:** o Pro+ **já está pago** (R$ 258/mês). As 600 unidades
mensais são custo afundado — se não forem usadas, expiram em 90 dias. Rodar o E2 nelas custa
**zero marginal**, contra os US$ 5–8 orçados no plano para esse estágio.

### Próximos passos, em ordem

1. **Você autentica a CLI** (é OAuth em conta Google — eu não faço isso em seu nome):
   ```bash
   wsl bash -lc '~/.local/bin/colab sessions'
   ```
   ela imprime a URL de autorização; aprovar no navegador e colar o código.
2. **Medir a taxa de queima** numa sessão T4 curta, e só então comparar em `$/B tokens`.
3. **Só depois** decidir se o grid do E2 vai para lá. A ordem importa: este projeto já pagou
   por decidir hardware sem medir (`$/hora` contra `$/B tokens`, a PRO 4500 que era 25% mais
   barata por hora e saiu 36% mais cara por token).

⚠️ **E a regra de credencial continua valendo** ([[bee-segredos-no-colab]]): token do HF vai
pelo cofre 🔑 + `google.colab.userdata`, nunca em célula nem em terminal. Um token já vazou
assim neste projeto, em 2026-07-27.
