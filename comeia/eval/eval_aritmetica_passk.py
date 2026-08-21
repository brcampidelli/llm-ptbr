"""pass@k do Bee-350M BASE em aritmetica de multiplos passos — o gate de US$ 0 sobre matematica.

⭐ A DECISAO QUE ESTE SCRIPT TOMA (criterio fixado ANTES de medir, docs/plano-pos-treino-350m.md)

    se pass@256 do modelo BASE ficar abaixo de 3%, matematica esta formalmente encerrada
    como capacidade nos pesos e o orcamento e' realocado.

  O racional: SFT **elicia** matematica que ja esta no pre-treino, nao a cria (arXiv:2403.04706).
  O grupo de controle esta na escala exata — SmolLM2-360M, 4 TRILHOES de tokens *com* FineMath,
  faz 8,1% em GSM8K. O Bee tem 21,75B tokens (0,54% disso) e ZERO fonte matematica no corpus.
  Se nao houver massa, nao ha o que eliciar, e cada dolar gasto em SFT de matematica compra
  nada — pior, pode custar: em Qwen2.5-0.5B o SFT derrubou GSM8K de 45,5% para 30,9%.

⭐ POR QUE pass@k E NAO ACURACIA
  pass@1 num modelo desta escala mede o modo da distribuicao; a pergunta do gate e' se existe
  QUALQUER massa de probabilidade sobre a resposta certa. Large Language Monkeys
  (arXiv:2407.21787) mede cobertura crescendo log-linearmente por quatro ordens de grandeza:
  Pythia-160M vai de pass@1 = 0,27% a pass@10k = 57% no MATH. Medir com k pequeno e concluir
  "nao sabe" e' ler o orcamento de amostragem, nao o modelo.

  ⭐ O estimador e' o NAO-VIESADO do Codex (Chen et al. 2021): pass@k = 1 - C(n-c,k)/C(n,k).
  "Gerou k e acertou alguma" e' viesado para baixo e, num gate que ENCERRA uma capacidade,
  o vies aponta exatamente para a decisao irreversivel.

⭐ AS DUAS GUARDAS QUE RODAM ANTES DE O MODELO SER CARREGADO
  1. todo gabarito do dataset EXECUTA e confere (§ o projeto ja mediu 23,5% onde o real era
     57,6% porque 35 de 85 referencias eram impossiveis por construcao)
  2. o extrator de numero passa uma bateria de autotestes com formato brasileiro
     ("R$ 1.234,56" → 1234.56). Um extrator quebrado devolve 0% e e' indistinguivel de um
     modelo que nao sabe matematica — e a conclusao errada seria permanente
  Ambas rodam tambem em --dry-run, que e' o modo de conferir o aparato sem GPU nenhuma.

⭐ VIES DELIBERADO: na duvida, a favor do modelo
  Onde o formato do numero e' genuinamente ambiguo ("1,000" pode ser mil ou um), o script
  aceita QUALQUER leitura plausivel do ultimo numero. Um veredito que fecha uma capacidade
  nao pode depender de convencao tipografica: se o gate reprovar, tem de ser porque a massa
  nao existe, nunca porque o parser preferiu um ponto a uma virgula.

⚠️ VRAM — a maquina de teste e' uma RTX 5070 de 8 GB
  O vilao e' o tensor de logits do prefill: comprimento x 32.000 x bf16. O script estima o
  custo pela config REAL do modelo antes de comecar, gera em lotes pequenos, chama
  `empty_cache()` entre lotes e, se ainda assim estourar, corta o lote pela metade e segue
  (em vez de morrer depois de horas). `expandable_segments` NAO funciona no Windows.

Uso:
    python comeia/eval/eval_aritmetica_passk.py --dry-run          # so o aparato, sem GPU
    python comeia/eval/eval_aritmetica_passk.py --limite 2 --k 8    # fumaca com modelo
    python comeia/eval/eval_aritmetica_passk.py --k 256             # o gate
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PADRAO_DADOS = RAIZ / "benchmarks" / "aritmetica_pt.jsonl"
DESTINO = RAIZ / "results"

MODELO_PADRAO = "BrCamp/bee-350m-pt-base"
LIMIAR_GATE = 0.03            # o criterio, fixado ANTES de medir
KS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
KS_RELATORIO = [1, 4, 16, 64, 256]   # a curva pedida explicitamente pelo plano

# Onde o few-shot termina e o modelo comecou a inventar o proximo exercicio.
PARADAS = ("\nPergunta:", "\nPergunta ", "\nProblema:", "\n\n\n")


# ======================================================================================
# 1. ESTIMADOR
# ======================================================================================

def pass_at_k(n: int, c: int, k: int) -> float:
    """Estimador NAO-VIESADO do Codex: 1 - C(n-c,k)/C(n,k), em log para nao estourar."""
    if k > n:
        return float("nan")
    if c <= 0:
        return 0.0
    if n - c < k:
        return 1.0
    logp = 0.0
    for i in range(k):
        logp += math.log(n - c - i) - math.log(n - i)
    return 1.0 - math.exp(logp)


def wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """IC de Wilson sobre a proporcao de PROBLEMAS (aproximacao — pass@k e' media de
    estimativas por problema, nao uma binomial pura). Serve para saber se o veredito
    sobrevive ao ruido de ter so ~200 problemas, nao para publicar erro-padrao."""
    if total == 0:
        return (0.0, 0.0)
    p = acertos / total
    d = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / d
    margem = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return (max(0.0, centro - margem), min(1.0, centro + margem))


# ======================================================================================
# 2. EXTRACAO DO NUMERO — a peca que, quebrada, imprime 0% para um modelo que sabe
# ======================================================================================

# Um numero com separadores opcionais: grupos de milhar tem de ter EXATAMENTE 3 digitos,
# e a parte decimal vem por ultimo. Isso ja rejeita "42." (ponto final de frase) sem
# precisar de limpeza posterior.
_TOKEN_NUM = re.compile(r"-?\d+(?:[.,   ]\d{3})*(?:[.,]\d+)?")


def _leituras(token: str) -> list[float]:
    """Todas as leituras plausiveis de UM token numerico; a primeira e' a canonica (pt-BR).

    A ambiguidade e' real e nao tem solucao tipografica: "1.234" e' mil e duzentos e trinta
    e quatro em portugues e um-virgula-dois-tres-quatro em ingles. Como este script decide
    ENCERRAR uma capacidade, ele carrega as duas leituras e aceita qualquer uma que bata —
    o gate tem de reprovar por ausencia de massa, nunca por convencao de pontuacao.
    """
    s = token.replace(" ", "").replace(" ", "").replace(" ", "")
    negativo = s.startswith("-")
    s = s.lstrip("-+")
    leituras: list[str] = []

    tem_ponto, tem_virgula = "." in s, "," in s

    if tem_ponto and tem_virgula:
        # O separador que aparece por ULTIMO e' o decimal; o outro e' milhar. Sem ambiguidade.
        decimal = "." if s.rfind(".") > s.rfind(",") else ","
        milhar = "," if decimal == "." else "."
        leituras.append(s.replace(milhar, "").replace(decimal, "."))
    elif tem_virgula:
        if s.count(",") > 1:
            leituras.append(s.replace(",", ""))            # 1,234,567 → so milhar
        else:
            inteiro, decimal = s.split(",")
            leituras.append(f"{inteiro}.{decimal}")        # canonico pt-BR: virgula = decimal
            if len(decimal) == 3 and 1 <= len(inteiro) <= 3 and not inteiro.startswith("0"):
                leituras.append(inteiro + decimal)         # alternativa: milhar a inglesa
    elif tem_ponto:
        if s.count(".") > 1:
            leituras.append(s.replace(".", ""))            # 1.234.567 → so milhar
        else:
            inteiro, decimal = s.split(".")
            milhar_plausivel = (len(decimal) == 3 and 1 <= len(inteiro) <= 3
                                and not inteiro.startswith("0"))
            if milhar_plausivel:
                leituras.append(inteiro + decimal)         # canonico pt-BR: ponto = milhar
                leituras.append(f"{inteiro}.{decimal}")    # alternativa: decimal a inglesa
            else:
                leituras.append(f"{inteiro}.{decimal}")    # 2.5 / 0.500 — so pode ser decimal
    else:
        leituras.append(s)

    saida: list[float] = []
    for cru in leituras:
        try:
            v = float(cru)
        except ValueError:
            continue
        v = -v if negativo else v
        if v not in saida:
            saida.append(v)
    return saida


def cortar(texto: str) -> str:
    """Corta onde o few-shot acabou e o modelo comecou a inventar o proximo exercicio.

    ⚠️ NAO corta em linha em branco simples: um modelo que pula uma linha no meio do
    raciocinio perderia a resposta final, e o erro cairia para o lado de reprovar o gate.
    """
    corte = len(texto)
    for marca in PARADAS:
        i = texto.find(marca)
        if i != -1:
            corte = min(corte, i)
    return texto[:corte].strip()


def extrair_numero(texto: str) -> float | None:
    """A leitura canonica do ULTIMO numero do texto (padrao GSM8K). None se nao houver."""
    achados = _TOKEN_NUM.findall(texto)
    if not achados:
        return None
    leituras = _leituras(achados[-1])
    return leituras[0] if leituras else None


def extrair_leituras(texto: str) -> list[float]:
    """Todas as leituras plausiveis do ultimo numero — e' o que decide acerto."""
    achados = _TOKEN_NUM.findall(texto)
    if not achados:
        return []
    return _leituras(achados[-1])


def acertou(saida: str, esperado: float) -> tuple[bool, float | None]:
    """Acerta se ALGUMA leitura plausivel do ultimo numero bate com o gabarito.

    Compara com tolerancia 1e-6 e, alem disso, aceita igualdade ate 2 casas decimais —
    o dataset so tem respostas com ate 2 casas, entao arredondar nao afrouxa nada.
    """
    leituras = extrair_leituras(saida)
    for v in leituras:
        if abs(v - esperado) < 1e-6 or round(v, 2) == round(esperado, 2):
            return True, v
    return False, (leituras[0] if leituras else None)


# ⭐ A BATERIA QUE PROVA QUE O EXTRATOR FUNCIONA. Roda SEMPRE, antes de tudo.
#    Sem ela, "0% de acerto" e "o parser esta quebrado" sao a mesma tela.
AUTOTESTES: list[tuple[str, float | None]] = [
    ("A resposta é R$ 1.234,56", 1234.56),          # milhar com ponto + decimal com virgula
    ("A resposta é 42.", 42.0),                     # ponto final de frase nao e' decimal
    ("O total custa R$ 3,50 no fim", 3.5),          # decimal brasileiro
    ("Total: 12.000 reais", 12000.0),               # ponto como separador de milhar
    ("são 7 caixas e sobram 2 unidades", 2.0),      # ultimo numero, nao o primeiro
    ("O resultado é -5", -5.0),                     # negativo
    ("aproximadamente 3,14", 3.14),
    ("a populacao e' de 1.234.567 pessoas", 1234567.0),
    ("50% de 200 é 100", 100.0),                    # porcentagem nao atrapalha
    ("custa R$ 0,99", 0.99),
    ("resposta: 1,5", 1.5),
    ("deu R$ 1 234,50 no total", 1234.5),           # espaco como separador de milhar
    ("o valor e' 1,234.56 dolares", 1234.56),       # formato ingles misto
    ("sobrou 0,500 litro", 0.5),                    # zero a esquerda: nao pode ser milhar
    ("R$ 10.500", 10500.0),
    ("pi vale 2.5 vezes", 2.5),                     # 1 digito depois do ponto = decimal
    ("A resposta é 84,80.", 84.8),                  # decimal seguido de ponto final
    ("nao sei responder", None),                    # sem numero nenhum
    ("", None),
]


def rodar_autotestes() -> list[str]:
    """Devolve a lista de falhas (vazia = extrator aprovado)."""
    falhas = []
    for texto, esperado in AUTOTESTES:
        obtido = extrair_numero(cortar(texto))
        ok = (obtido is None and esperado is None) or (
            obtido is not None and esperado is not None and abs(obtido - esperado) < 1e-9
        )
        if not ok:
            falhas.append(f"{texto!r} → esperado {esperado!r}, obtido {obtido!r}")
    return falhas


# ======================================================================================
# 3. PROMPT — few-shot escrito a mao, com gabarito EXECUTAVEL para a guarda
# ======================================================================================

# ⚠️ Escritos a mao de proposito, FORA do dataset: consumir itens do conjunto medido para
#    servir de exemplo contamina a medicao. A guarda confere que nenhum deles vazou para
#    dentro do dataset, e que a conta de cada um fecha.
POUCOS_TIROS: list[dict] = [
    {
        "pergunta": "Pedro comprou 4 cadernos que custam R$ 12,00 cada e pagou com uma nota "
                    "de R$ 100,00. Quantos reais ele recebeu de troco?",
        "resposta": "Os 4 cadernos custaram 4 × 12 = 48 reais. O troco foi 100 − 48 = 52. "
                    "A resposta é 52.",
        "expressao": "100 - 4*12",
    },
    {
        "pergunta": "Um ônibus saiu do terminal com 30 passageiros. No primeiro ponto desceram "
                    "8 pessoas e subiram 5. Quantos passageiros continuaram no ônibus?",
        "resposta": "Depois que 8 desceram sobraram 30 − 8 = 22 passageiros. Com as 5 que "
                    "subiram ficaram 22 + 5 = 27. A resposta é 27.",
        "expressao": "30 - 8 + 5",
    },
    {
        "pergunta": "Uma escola tem 6 turmas com 25 alunos em cada uma. Hoje 14 alunos "
                    "faltaram. Quantos alunos estão presentes?",
        "resposta": "No total são 6 × 25 = 150 alunos. Com 14 faltas, estão presentes "
                    "150 − 14 = 136. A resposta é 136.",
        "expressao": "6*25 - 14",
    },
    {
        "pergunta": "Na feira, Ana comprou 3 quilos de banana a R$ 5,00 o quilo e 2 quilos de "
                    "maçã a R$ 8,00 o quilo. Quantos reais ela gastou ao todo?",
        "resposta": "A banana custou 3 × 5 = 15 reais e a maçã custou 2 × 8 = 16 reais. Ao "
                    "todo foram 15 + 16 = 31. A resposta é 31.",
        "expressao": "3*5 + 2*8",
    },
    {
        "pergunta": "Uma caixa d'água de 500 litros estava cheia. A família consumiu 60 litros "
                    "por dia durante 7 dias. Quantos litros sobraram?",
        "resposta": "Em 7 dias a família consumiu 60 × 7 = 420 litros. Sobraram "
                    "500 − 420 = 80. A resposta é 80.",
        "expressao": "500 - 60*7",
    },
]


def montar_prompt(pergunta: str, tiros: int) -> str:
    blocos = [f"Pergunta: {e['pergunta']}\nResposta: {e['resposta']}"
              for e in POUCOS_TIROS[:tiros]]
    blocos.append(f"Pergunta: {pergunta}\nResposta:")
    return "\n\n".join(blocos)


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


# ======================================================================================
# 4. GUARDAS — tudo isto roda ANTES de o modelo existir na memoria
# ======================================================================================

def guardas(itens: list[dict]) -> int:
    """0 = liberado. Qualquer outro valor = o APARATO esta errado, nao o modelo."""
    import ast

    # -- G0: extrator de numero
    falhas = rodar_autotestes()
    if falhas:
        print(f"🔴 ABORTA: extrator de numero falhou em {len(falhas)}/{len(AUTOTESTES)} casos.",
              file=sys.stderr)
        for f in falhas:
            print(f"    {f}", file=sys.stderr)
        print("   Um extrator quebrado devolve 0% e e' indistinguivel de 'o modelo nao sabe'.",
              file=sys.stderr)
        return 3
    print(f"✅ guarda 1/3: extrator de numero passa {len(AUTOTESTES)}/{len(AUTOTESTES)} autotestes")

    # -- G1: TODO gabarito do dataset executa e confere
    if not itens:
        print("🔴 ABORTA: dataset vazio — a guarda verificaria ZERO gabaritos.", file=sys.stderr)
        return 3
    ruins = []
    for it in itens:
        try:
            v = eval(compile(ast.parse(it["expressao"], mode="eval"), "<g>", "eval"),
                     {"__builtins__": {}}, {})
        except Exception as e:
            ruins.append((it.get("id", "?"), f"nao avalia: {e}"))
            continue
        if abs(v - it["resposta"]) > 1e-6:
            ruins.append((it.get("id", "?"), f"eval={v!r} != resposta={it['resposta']!r}"))
    if ruins:
        print(f"🔴 ABORTA: {len(ruins)}/{len(itens)} gabaritos NAO conferem — o avaliador esta"
              f" errado, nao o modelo.", file=sys.stderr)
        for ident, motivo in ruins[:10]:
            print(f"    [{ident}] {motivo}", file=sys.stderr)
        print("   Rode comeia/eval/validar_aritmetica.py para o diagnostico completo.",
              file=sys.stderr)
        return 3
    print(f"✅ guarda 2/3: {len(itens)}/{len(itens)} gabaritos do dataset executam e conferem")

    # -- G2: os exemplos do few-shot fecham a conta E nao vazaram para dentro do dataset
    no_dataset = {_norm(it["pergunta"]) for it in itens}
    for i, e in enumerate(POUCOS_TIROS, 1):
        v = eval(compile(ast.parse(e["expressao"], mode="eval"), "<g>", "eval"),
                 {"__builtins__": {}}, {})
        dito = extrair_numero(e["resposta"])
        if dito is None or abs(v - dito) > 1e-6:
            print(f"🔴 ABORTA: exemplo few-shot {i} ensina a conta errada "
                  f"(expressao={v!r}, texto diz {dito!r}).", file=sys.stderr)
            return 3
        if _norm(e["pergunta"]) in no_dataset:
            print(f"🔴 ABORTA: exemplo few-shot {i} TAMBEM esta no dataset medido — "
                  f"contaminacao.", file=sys.stderr)
            return 3
    print(f"✅ guarda 3/3: {len(POUCOS_TIROS)} exemplos few-shot conferem e nao contaminam "
          f"o conjunto")
    return 0


# ======================================================================================
# 5. PRINCIPAL
# ======================================================================================

def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO_PADRAO)
    ap.add_argument("--peft", default=None, help="adapter LoRA opcional")
    ap.add_argument("--dados", type=Path, default=PADRAO_DADOS)
    ap.add_argument("--k", type=int, default=256,
                    help="amostras por problema; define o maior k da curva (padrao 256)")
    ap.add_argument("--n", type=int, default=None, help="apelido de --k")
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--tiros", type=int, default=5,
                    help=f"exemplos few-shot (0..{len(POUCOS_TIROS)}); modelo BASE precisa deles")
    ap.add_argument("--lote", type=int, default=16,
                    help="sequencias por chamada de generate — o teto de VRAM na 5070 de 8 GB")
    ap.add_argument("--max-new", type=int, default=160)
    ap.add_argument("--limite", type=int, default=0, help="roda so os N primeiros problemas")
    ap.add_argument("--chat", action="store_true",
                    help="usa o chat template (so para modelo pos-SFT; o BASE nao tem)")
    ap.add_argument("--dry-run", action="store_true",
                    help="so as guardas e o prompt de exemplo — NAO carrega o modelo")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    n_amostras = args.n or args.k
    if not 0 <= args.tiros <= len(POUCOS_TIROS):
        print(f"🔴 --tiros tem de estar entre 0 e {len(POUCOS_TIROS)}.", file=sys.stderr)
        return 2

    if not args.dados.exists():
        print(f"🔴 ABORTA: {args.dados} nao existe. Gere com gerar_aritmetica_pt.py.",
              file=sys.stderr)
        return 2
    itens = [json.loads(l) for l in args.dados.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    if args.limite:
        itens = itens[: args.limite]

    print("=" * 78)
    print("GATE DE MATEMATICA — pass@k do modelo BASE em aritmetica de multiplos passos")
    print("=" * 78)
    print(f"dataset : {args.dados.name} · {len(itens)} problemas")

    codigo = guardas(itens)
    if codigo:
        return codigo

    exemplo = montar_prompt(itens[0]["pergunta"], args.tiros)
    if args.dry_run:
        print("\n" + "-" * 78)
        print(f"PROMPT DE EXEMPLO ({args.tiros} tiros, {len(exemplo)} caracteres)")
        print("-" * 78)
        print(exemplo)
        print("-" * 78)
        print("\n-- extracao numerica nos autotestes (o que o script le de cada formato)")
        for texto, esperado in AUTOTESTES:
            obtido = extrair_numero(cortar(texto))
            print(f"   {texto[:44]:<46} → {obtido!r:>12}   (esperado {esperado!r})")
        print("\n✅ DRY-RUN: aparato validado. Nenhum modelo foi carregado.")
        print(f"   Para medir de verdade: python {Path(__file__).name} --k {n_amostras}")
        return 0

    # ---------------------------------------------------------------- modelo
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    disp = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to(disp)
    if args.peft:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, args.peft).to(disp)
    modelo.eval()

    if args.chat and not getattr(tok, "chat_template", None):
        print("🔴 ABORTA: --chat pedido mas o tokenizador nao tem chat template. "
              "O modelo BASE nao tem — use few-shot (padrao).", file=sys.stderr)
        return 2

    cfg = modelo.config
    vocab = getattr(cfg, "vocab_size", 32000)
    n_prompt = len(tok(exemplo)["input_ids"])
    mb_logits = args.lote * n_prompt * vocab * 2 / 2**20
    print(f"\nmodelo  : {args.model}{' + ' + args.peft if args.peft else ''} · {disp}")
    print(f"amostra : k={n_amostras}  T={args.temp}  top_p={args.top_p}  "
          f"lote={args.lote}  max_new={args.max_new}  tiros={args.tiros}")
    print(f"VRAM    : prompt ~{n_prompt} tokens · logits de prefill ~{mb_logits:.0f} MiB "
          f"(lote x {n_prompt} x {vocab} x bf16)")
    if disp == "cuda":
        total = torch.cuda.get_device_properties(0).total_memory / 2**30
        print(f"          GPU {torch.cuda.get_device_name(0)} · {total:.1f} GiB")
        if mb_logits > 1500:
            print(f"          ⚠️ estimativa alta — considere --lote {max(1, args.lote // 2)}")
    print(f"custo   : {len(itens) * n_amostras:,} geracoes no total\n")

    lote_atual = [args.lote]      # mutavel: cai sozinho se estourar VRAM e nunca volta a subir

    def gerar(prompt: str, quantas: int) -> list[str]:
        ent = tok(prompt, return_tensors="pt").to(disp)
        pre = ent["input_ids"].shape[1]
        saidas: list[str] = []
        while len(saidas) < quantas:
            b = min(lote_atual[0], quantas - len(saidas))
            try:
                with torch.no_grad():
                    g = modelo.generate(
                        **ent,
                        max_new_tokens=args.max_new,
                        do_sample=True,
                        temperature=args.temp,
                        top_p=args.top_p,
                        num_return_sequences=b,
                        pad_token_id=tok.pad_token_id or tok.eos_token_id,
                    )
            except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
                if "out of memory" not in str(e).lower() and not isinstance(
                        e, torch.cuda.OutOfMemoryError):
                    raise
                if disp == "cuda":
                    torch.cuda.empty_cache()
                if lote_atual[0] <= 1:
                    print("🔴 OOM com lote=1 — reduza --max-new ou --tiros.", file=sys.stderr)
                    raise
                lote_atual[0] = max(1, lote_atual[0] // 2)
                print(f"   ⚠️ OOM: lote {b} → {lote_atual[0]} (permanente daqui em diante)",
                      flush=True)
                continue
            saidas += [tok.decode(s[pre:], skip_special_tokens=True) for s in g]
            del g
            if disp == "cuda":
                torch.cuda.empty_cache()
        return saidas

    # ---------------------------------------------------------------- medicao
    # ⭐ PARCIAL EM DISCO, UM PROBLEMA POR LINHA. Este run leva ~4,6 h na 5070; sem gravar
    #    nada ate' o fim, qualquer queda no minuto 270 custa as 4,5 h anteriores. E' o mesmo
    #    item do checklist que ja' existe para o pre-treino ("checkpoint em disco
    #    persistente") aplicado ao lado da avaliacao, onde faltava.
    #    Retomar e' automatico: o que ja' esta' no .parcial nao e' regerado.
    parcial = DESTINO / f"aritmetica-passk{('-' + args.tag) if args.tag else ''}.parcial.jsonl"
    parcial.parent.mkdir(parents=True, exist_ok=True)
    feitos: dict[str, dict] = {}
    if parcial.exists():
        for linha in parcial.read_text(encoding="utf-8").split(chr(10)):
            if linha.strip():
                r = json.loads(linha)
                # so' aproveita quem foi medido com o MESMO n de amostras — parcial de um
                # k diferente nao e' comparavel e reaproveita-lo falsearia o resultado
                if r.get("n") == n_amostras:
                    feitos[r["id"]] = r
        if feitos:
            print(f"   ↻ retomando: {len(feitos)}/{len(itens)} problemas ja' medidos em "
                  f"{parcial.name}", flush=True)

    por_problema: list[dict] = []
    t0 = time.time()
    sem_numero = 0
    total_amostras = 0
    fparcial = parcial.open("a", encoding="utf-8")

    for i, it in enumerate(itens, 1):
        if it["id"] in feitos:
            r = feitos[it["id"]]
            por_problema.append(r)
            total_amostras += r["n"]
            continue
        prompt = montar_prompt(it["pergunta"], args.tiros)
        brutas = gerar(prompt, n_amostras)

        acertos = 0
        primeira_saida = None
        primeira_lida = None
        for j, bruta in enumerate(brutas):
            saida = cortar(bruta)
            ok, lido = acertou(saida, float(it["resposta"]))
            if j == 0:
                primeira_saida, primeira_lida = saida[:300], lido
            if lido is None:
                sem_numero += 1
            acertos += int(ok)
        total_amostras += len(brutas)

        por_problema.append({
            "id": it["id"], "passos": it["passos"], "tema": it["tema"],
            "resposta": it["resposta"], "n": len(brutas), "acertos": acertos,
            "taxa": round(acertos / max(1, len(brutas)), 4),
            "amostra_saida": primeira_saida, "amostra_numero_lido": primeira_lida,
        })
        fparcial.write(json.dumps(por_problema[-1], ensure_ascii=False) + chr(10))
        fparcial.flush()

        if i % 5 == 0 or i == len(itens):
            dt = time.time() - t0
            vram = (f" · VRAM {torch.cuda.memory_allocated() / 2**20:.0f}/"
                    f"{torch.cuda.memory_reserved() / 2**20:.0f} MiB" if disp == "cuda" else "")
            print(f"  {i}/{len(itens)} · {dt / 60:.1f} min · resta ~"
                  f"{dt * (len(itens) - i) / i / 60:.1f} min{vram}", flush=True)

    fparcial.close()
    return relatar(args, itens, por_problema, n_amostras, sem_numero, total_amostras, t0)


def relatar(args, itens, por_problema, n_amostras, sem_numero, total_amostras, t0) -> int:
    n_probs = len(por_problema)
    ks = [k for k in KS if k <= n_amostras]
    if n_amostras not in ks:
        ks.append(n_amostras)

    print("\n" + "=" * 78)
    print(f"CURVA DE pass@k — {n_probs} problemas, {n_amostras} amostras cada")
    print("=" * 78)
    print(f"  {'k':>5}   {'pass@k':>8}   {'IC 95% (sobre problemas)':<28} {'ganho':>10}")
    curva, anterior = [], None
    for k in ks:
        v = sum(pass_at_k(p["n"], p["acertos"], k) for p in por_problema) / max(1, n_probs)
        lo, hi = wilson(round(v * n_probs), n_probs)
        ganho = "" if anterior is None else f"{(v - anterior) * 100:+6.2f} pp"
        marca = " ⭐" if k in KS_RELATORIO else ""
        print(f"  {k:>5}   {v:>7.2%}   [{lo:>6.2%} – {hi:>6.2%}]{'':<9} {ganho:>10}{marca}")
        curva.append({"k": k, "pass_at_k": round(v, 5), "ic95": [round(lo, 5), round(hi, 5)]})
        anterior = v

    resolvidos = [p for p in por_problema if p["acertos"] > 0]
    print("-" * 78)
    print(f"  problemas com >=1 acerto em {n_amostras} amostras: "
          f"{len(resolvidos)}/{n_probs} = {len(resolvidos) / max(1, n_probs):.2%}")
    print(f"  amostras sem NENHUM numero na saida: {sem_numero}/{total_amostras} "
          f"= {sem_numero / max(1, total_amostras):.1%}")
    if sem_numero / max(1, total_amostras) > 0.5:
        print("  ⚠️ mais da metade das saidas nao tem numero nenhum — antes de creditar isso ao")
        print("     modelo, confira o formato do prompt e --max-new: pode ser o APARATO.")

    # -- sub-sinal diagnostico: onde a capacidade morre
    print("\n-- pass@%d por profundidade (a sub-taxa que diz ONDE quebra)" % n_amostras)
    for passos in sorted({p["passos"] for p in por_problema}):
        grupo = [p for p in por_problema if p["passos"] == passos]
        v = sum(pass_at_k(p["n"], p["acertos"], n_amostras) for p in grupo) / len(grupo)
        print(f"   {passos} operacoes ({len(grupo):>3} problemas): {v:>7.2%}")

    # ---------------------------------------------------------------- VEREDITO
    final = curva[-1]
    valor, (lo, hi) = final["pass_at_k"], final["ic95"]
    print("\n" + "=" * 78)
    print(f"VEREDITO — criterio fixado ANTES de medir: pass@256 < {LIMIAR_GATE:.0%} encerra "
          f"matematica")
    print("=" * 78)
    if n_amostras < 256:
        print(f"⚠️ MEDICAO PARCIAL: k={n_amostras} < 256. O gate exige pass@256 e a curva de")
        print("   cobertura cresce log-linearmente por ordens de grandeza (arXiv:2407.21787) —")
        print("   um k menor SUBESTIMA e nao pode encerrar a capacidade. Isto e' fumaca, nao gate.")
    elif valor < LIMIAR_GATE:
        print(f"🔴 GATE REPROVADO: pass@{n_amostras} = {valor:.2%} < {LIMIAR_GATE:.0%}")
        print()
        print("   O QUE ISSO IMPLICA, explicitamente:")
        print("   · Matematica esta formalmente ENCERRADA como capacidade nos pesos. Em 256")
        print("     tentativas por problema o modelo nao coloca massa de probabilidade sobre a")
        print("     resposta certa nem por acidente.")
        print("   · SFT de matematica NAO deve ser financiado. A lei (arXiv:2403.04706) e' que")
        print("     SFT ELICIA o que ja esta no pre-treino; sem massa nao ha o que eliciar, e o")
        print("     precedente na escala e' de PIORA (Qwen2.5-0.5B: 45,5% → 30,9% em GSM8K).")
        print("   · O orcamento e' realocado, e matematica volta como SUB-CASO DO AGENTICO:")
        print("     reconhecer o problema aritmetico e emitir a chamada de calculadora correta,")
        print("     que o interpretador executa — que e' o que o TinyGSM 350M de fato faz, e")
        print("     reaproveita o ativo mais forte do projeto.")
        print("   · A causa e' o CORPUS, nao o treino: 0% de fonte matematica em 21,75B tokens.")
        print("     Se um dia isso mudar, muda no pre-treino/mid-training, nao no fine-tuning.")
        if hi >= LIMIAR_GATE:
            print()
            print(f"   ⚠️ RESSALVA: o teto do IC 95% e' {hi:.2%}, ACIMA do limiar. Com "
                  f"{n_probs} problemas")
            print("      o conjunto nao separa o veredito do ruido. Antes de encerrar em")
            print("      definitivo, ampliar o conjunto ou reamostrar.")
        else:
            print()
            print(f"   ✅ O veredito sobrevive ao ruido: teto do IC 95% = {hi:.2%}, abaixo do "
                  f"limiar.")
    else:
        print(f"🟢 GATE APROVADO: pass@{n_amostras} = {valor:.2%} >= {LIMIAR_GATE:.0%}")
        print()
        print("   O QUE ISSO IMPLICA, explicitamente:")
        print("   · Existe massa de probabilidade sobre a resposta certa — ha o que ELICIAR.")
        print("     A hipotese de que o corpus sem matematica zera a capacidade fica REFUTADA")
        print("     por medicao, e a refutacao vale mais que o argumento que ela derruba.")
        print("   · Matematica continua na lista de capacidades, e o proximo passo e' o metodo")
        print("     mais barato de mover pass@1 para perto de pass@k: amostragem por rejeicao")
        print("     com verificador por EXECUCAO (o gabarito ja e' executavel).")
        print(f"   · ⚠️ pass@1 = {curva[0]['pass_at_k']:.2%} continua sendo o numero que o "
              f"usuario ve.")
        print("     pass@k alto com pass@1 baixo e' potencial, nao produto.")
        if lo < LIMIAR_GATE:
            print()
            print(f"   ⚠️ RESSALVA: o piso do IC 95% e' {lo:.2%}, ABAIXO do limiar — a aprovacao")
            print("      nao sobrevive ao ruido. Reamostrar antes de comprometer orcamento.")
    print("=" * 78)

    tag = args.tag or f"k{n_amostras}_T{args.temp}"
    DESTINO.mkdir(exist_ok=True)
    alvo = DESTINO / f"aritmetica_passk_{tag}.json"
    alvo.write_text(json.dumps({
        "modelo": args.model, "peft": args.peft, "dataset": str(args.dados),
        "problemas": n_probs, "k": n_amostras, "temp": args.temp, "top_p": args.top_p,
        "tiros": args.tiros, "max_new": args.max_new,
        "limiar_gate": LIMIAR_GATE,
        "veredito": ("PARCIAL" if n_amostras < 256
                     else ("REPROVADO" if valor < LIMIAR_GATE else "APROVADO")),
        "curva": curva,
        "por_profundidade": {
            str(p): round(sum(pass_at_k(q["n"], q["acertos"], n_amostras)
                              for q in por_problema if q["passos"] == p)
                          / max(1, sum(1 for q in por_problema if q["passos"] == p)), 5)
            for p in sorted({q["passos"] for q in por_problema})
        },
        "problemas_com_algum_acerto": len(resolvidos),
        "amostras_sem_numero": sem_numero,
        "total_amostras": total_amostras,
        "minutos": round((time.time() - t0) / 60, 1),
        "por_problema": por_problema,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nresultado: {alvo}")
    print(f"tempo    : {(time.time() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
