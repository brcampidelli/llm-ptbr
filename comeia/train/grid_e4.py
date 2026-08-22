"""E4 — otimização da mistura por perturbação por domínio (arXiv:2508.11953).

⭐ O MÉTODO, E A ADAPTAÇÃO QUE O BEE PODE FAZER E O PAPER NÃO PODIA

O paper ajusta, por domínio, uma lei de escala de fine-tuning:

    L(D_i^val) ≈ C_i · (N_i + k_i · |D_∖i|^α_i)^(−β_i) + E_i

onde `N_i` são os **tokens** do domínio i e `|D_∖i|` os tokens de todos os outros — o termo
`k_i·|D_∖i|^α_i` é a **transferência** entre domínios. Ajusta-se com **5 perturbações por
domínio** (razões 0,5 · 0,67 · 1,0 · 2,0 · 3,0 sobre a alocação base, com os outros fixos) e
resolve-se o mínimo por SLSQP sob simplex. Em **Qwen2.5-0.5B** o resultado fica a **0,66%** da
busca exaustiva por 1/4 do custo.

🔴 **MAS O PAPER OTIMIZA LOSS DE VALIDAÇÃO, E ELE MESMO AVISA QUE ISSO PODE NÃO TRANSFERIR:**
no Tulu3 a correlação com desempenho downstream foi positiva; no Orca houve *"discrepância
importante"*. Para o Bee isso é grave — todo veredito deste projeto vem de métrica downstream
(`exec_ok` 64,7%, IFEval 32,0%, BLEU), e a lição §2d já registra perplexidade plana enquanto o
modelo muda.

⭐ **O Bee tem um ativo que os autores não tinham: avaliação downstream barata.** O E2 mediu
27 braços em 7 réguas em **57 minutos**. Então aqui a MESMA forma funcional é ajustada duas
vezes — contra a loss de validação **e** contra a métrica da régua — e os dois ótimos são
comparados. Se discordarem, a discordância **é o resultado**, e o projeto já tem regra sobre
qual dos dois vale.

⚠️ **MISTURA EM TOKENS, NUNCA EM EXEMPLOS.** Medido no inventário: tradução tem 15% dos
exemplos e **4%** dos tokens; código tem 13% dos exemplos e **30%**. Pesar por exemplo daria a
tradução 7× o peso pretendido. O gradiente vê token.

⚠️ **A MISTURA ÓTIMA DEPENDE DO ORÇAMENTO** — é a razão de não herdar proporção do Tulu3 ou do
SmolTalk. Por isso o orçamento-alvo é declarado aqui e o ajuste é feito perto dele, não numa
escala arbitrária.

Uso:
    python comeia/train/grid_e4.py --dry-run
    python comeia/train/grid_e4.py --base-tokens 1000000
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
COMEIA = RAIZ / "comeia"
PROC = COMEIA / "data" / "processed"
PY = sys.executable
MODELO = "BrCamp/bee-350m-pt-base"
SAIDA = RAIZ / "docs" / "grid-e4-resultado.json"
MIX = COMEIA / "data" / "processed" / "mix_e4"

# dominio -> (arquivo, filtro opcional)
DOMINIOS = {
    "traducao": ("gigaverbo_translation.jsonl", None),
    "resumo": ("gigaverbo_summarization.jsonl", None),
    "estruturado": ("gigaverbo_structured.jsonl", None),
    "codigo": ("gigaverbo_code.jsonl", None),
    "agentico_pos": ("gigaverbo_ferramenta.jsonl", "tool_call"),
    "agentico_neg": ("negativos_com_recusa.jsonl", None),
    "texto": ("sft_grupo_texto.jsonl", None),
    "simbolico": ("sft_grupo_simbolico.jsonl", None),
}

# 🔴 AS RAZOES SAO AS DO PAPER, NAO INVENTADAS. Cobrem meia ordem de grandeza para baixo e
#    meia para cima, que e' o minimo para o expoente beta_i ficar identificavel. Menos que
#    isso ajusta uma curva que passa por qualquer coisa.
RAZOES = [0.5, 0.67, 1.0, 2.0, 3.0]


def carregar(nome: str) -> list[dict]:
    arq, filtro = DOMINIOS[nome]
    p = PROC / arq
    regs = [json.loads(l) for l in p.read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    if filtro:
        regs = [r for r in regs if r.get("kind") == filtro]
    return regs


class SemContagem(RuntimeError):
    """Exemplo sem contagem de tokens — ver `tokens_de`."""


def tokens_de(r: dict) -> int:
    """Tokens do exemplo, medidos com o NOSSO tokenizador. LEVANTA se não houver.

    🔴 A PRIMEIRA VERSAO TINHA `or 0` NO FIM, E UM `or 1` NO CHAMADOR. Quatro arquivos nao
    traziam contagem (`gigaverbo_ferramenta`, `negativos_com_recusa` e os dois grupos
    originais do Bee), e o fallback transformou **medicao ausente em custo despresivel**: cada
    exemplo "custava" 1 token, o orcamento nunca fechava, e os quatro dominios entraram
    INTEIROS. A mistura saiu com 49,4% de traducao em vez dos ~33% pretendidos — numero
    plausivel, receita errada, e nada deu erro.

    ⚠️ `token_count` do gigaverbo e' do tokenizador do Qwen e subestima o nosso em ~12% no
    codigo; so' `tokens_bee` vale. Faltando, **aborta** — porque o certo e' medir (custa
    minutos de CPU), nunca chutar.
    """
    n = r.get("tokens_bee")
    if not n:
        raise SemContagem(
            "exemplo sem `tokens_bee`. Rode a contagem com o tokenizador do Bee antes de "
            "montar mistura — fallback aqui vira receita errada em silencio.")
    return n


def montar(dominios: list[str], alvo: str, razao: float, base: int, semente: int,
           destino: Path) -> dict:
    """Monta UM conjunto perturbado: `alvo` recebe base*razao tokens, os outros recebem base.

    ⭐ AMOSTRAGEM SEM REPOSICAO, PERMUTANDO UMA VEZ. E' a licao §2 do projeto, que ja'
    reapareceu duas vezes (no pre-treino e nos negativos do E3): sortear com reposicao a cada
    escolha cobre so' 63,2% do conjunto e repete o resto. Aqui a lista e' permutada e
    percorrida ate' o orcamento de TOKENS fechar.

    ⚠️ O corte e' por TOKEN, nao por exemplo — e o ultimo exemplo entra inteiro, nunca
    truncado. Exemplo truncado no meio da resposta ensina a parar no meio da resposta.
    """
    import random
    rnd = random.Random(semente)
    linhas, resumo = [], {}
    for d in dominios:
        orcamento = int(base * razao) if d == alvo else base
        regs = carregar(d)
        ordem = list(range(len(regs)))
        rnd.shuffle(ordem)
        somados = 0
        n = 0
        for i in ordem:
            t = tokens_de(regs[i])
            if somados + t > orcamento:
                continue
            linhas.append(regs[i])
            somados += t
            n += 1
            if somados >= orcamento * 0.995:
                break
        resumo[d] = {"exemplos": n, "tokens": somados, "orcamento": orcamento}
    rnd.shuffle(linhas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    perdidos = 0
    with destino.open("w", encoding="utf-8") as f:
        for r in linhas:
            u = _uniformizar(r)
            if u is None:
                perdidos += 1
                continue
            f.write(json.dumps(u, ensure_ascii=False) + chr(10))
    if perdidos:
        resumo["_descartados_sem_assistente"] = perdidos
    return resumo


def _uniformizar(r: dict) -> dict | None:
    """TUDO em `prompt`/`completion`. Esquema misto quebra o treino E muda a loss.

    🔴 PEGO PELO TESTE DE FUMACA, e e' a segunda vez que este projeto tropeca aqui. Os
    arquivos do gigaverbo trazem `messages`; os grupos originais do Bee trazem
    `prompt`/`completion`. Num mesmo arquivo, o TRL ve uma coluna `prompt` em ALGUNS registros,
    entra em modo prompt/completion, e morre nos que so' tem `messages`:

        ValueError: You need to specify either `text` or `text_target`.

    ⚠️ E o erro e' o menor dos problemas. Com `messages` o TRL cobra loss em TODOS os tokens,
    prompt incluido; com `prompt`/`completion` ele MASCARA o prompt. Misturar treina metade
    do conjunto sob uma convencao e metade sob outra — o que este projeto ja' pagou em
    2026-07-24, quando um system prompt de 928 tokens repetido derrubou a loss de 1,273 para
    0,0755 decorando o catalogo, com so' 6,2% dos tokens medindo habilidade real.

    ⚠️ Registro sem fala de assistente e' CONTADO, nunca descartado em silencio.
    """
    if isinstance(r.get("prompt"), list) and r.get("completion"):
        return {"prompt": r["prompt"], "completion": r["completion"]}
    msgs = r.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return None
    ult = next((i for i in range(len(msgs) - 1, -1, -1)
                if msgs[i].get("role") == "assistant"), None)
    if ult is None or ult == 0:
        return None
    return {"prompt": msgs[:ult], "completion": [msgs[ult]]}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--base-tokens", type=int, default=450_000,
                    help="tokens por dominio na alocacao BASE (razao 1.0)")
    ap.add_argument("--dominios", nargs="*", default=list(DOMINIOS))
    ap.add_argument("--semente", type=int, default=20260821)
    ap.add_argument("--lr", type=float, default=6e-4,
                    help="MESMO em todos os mini-runs — ver a nota no laco")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print("=" * 78)
    print("E4 — OTIMIZACAO DE MISTURA POR PERTURBACAO")
    print("=" * 78)

    # ---- guarda 1: os dominios existem e tem token suficiente para a maior razao
    inventario = {}
    falta = []
    for d in a.dominios:
        try:
            regs = carregar(d)
        except FileNotFoundError:
            falta.append(f"{d} (arquivo ausente)")
            continue
        try:
            tk = sum(tokens_de(r) for r in regs)
        except SemContagem as e:
            falta.append(f"{d}: {e}")
            continue
        inventario[d] = {"exemplos": len(regs), "tokens": tk}
        preciso = int(a.base_tokens * max(RAZOES))
        if tk < preciso:
            falta.append(f"{d}: {tk:,} tokens, precisa de {preciso:,} para a razao "
                         f"{max(RAZOES)}")

    print(f"orcamento base : {a.base_tokens:,} tokens/dominio (razao 1,0)")
    print(f"razoes         : {RAZOES}")
    print(f"mini-runs      : {len(a.dominios)} dominios x {len(RAZOES)} = "
          f"{len(a.dominios) * len(RAZOES)}")
    print()
    print(f"{'dominio':16}{'exemplos':>10}{'tokens':>13}{'epocas na razao 3,0':>22}")
    print("-" * 62)
    for d, v in inventario.items():
        ep = a.base_tokens * 3.0 / max(1, v["tokens"])
        print(f"  {d:14}{v['exemplos']:>10,}{v['tokens']:>13,}{ep:>21.2f}x")

    if falta:
        print()
        print("🔴 ABORTA: dominio sem token suficiente para a maior razao —")
        print("   (o default de 450k tokens/dominio existe justamente porque `texto` e")
        print("    `simbolico`, o dado original do Bee, tem 1,6M e 1,5M — a base tem de caber")
        print("    3x dentro do MENOR dominio, senao a razao 3,0 repete exemplo.)")
        print("   perturbar 3x um dominio que nao tem 3x de dado significa REPETIR exemplo,")
        print("   e ai' a curva ajustada mede repeticao e nao volume (licao 2c-6).")
        for f in falta:
            print(f"     {f}")
        return 2
    print()
    print("  ✅ guarda 1/2: todo dominio tem token para a razao maxima sem repetir exemplo")

    # ---- guarda 2: a mistura e' em TOKENS
    tot = sum(v["tokens"] for v in inventario.values())
    print("  ✅ guarda 2/2: pesos em TOKENS, nao em exemplos "
          f"(tradução = {100*inventario.get('traducao',{}).get('tokens',0)/tot:.1f}% dos "
          f"tokens contra "
          f"{100*inventario.get('traducao',{}).get('exemplos',0)/sum(v['exemplos'] for v in inventario.values()):.1f}% "
          "dos exemplos)")

    # ⭐ TETO POR DOMINIO — a restricao de simplex NAO basta. `texto` e `simbolico` sao o dado
    #    ORIGINAL do Bee (3.267 e 2.267 exemplos) e nao crescem: o otimizador pode querer dar
    #    a eles um peso que o disco nao tem. Sem o teto, a "mistura otima" e' uma receita
    #    impossivel de cozinhar — e isso so' apareceria na hora de montar o conjunto final.
    #    E' um achado do E4, nao um obstaculo: dois dominios estao LIMITADOS POR OFERTA, e o
    #    E3 seguinte sabe onde gerar dado.
    print()
    print("teto por dominio (fracao maxima do orcamento-alvo, sem repetir exemplo):")
    for alvo_tot in (10_000_000, 20_000_000):
        linha = []
        for d, v in inventario.items():
            linha.append(f"{d[:9]} {100*min(1.0, v['tokens']/alvo_tot):.0f}%")
        print(f"  alvo {alvo_tot//1_000_000:>3}M tok: " + " · ".join(linha))
    print("  ⚠️ dominio com teto abaixo de 100% nao pode receber peso arbitrario do otimizador")

    runs = [{"dominio": d, "razao": r,
             "tag": f"e4-{d}-r{str(r).replace('.', 'p')}"}
            for d in a.dominios for r in RAZOES]
    print(f"\n{len(runs)} mini-runs planejados:")
    for r in runs[:3] + [runs[-1]]:
        alvo = int(a.base_tokens * r["razao"])
        outros = a.base_tokens * (len(a.dominios) - 1)
        print(f"  {r['tag']:30} {alvo:>9,} tok no alvo + {outros:>10,} nos outros")
    if len(runs) > 4:
        print(f"  … e mais {len(runs) - 4}")

    if a.dry_run:
        print("\n✅ DRY-RUN: nada treinado.")
        return 0

    feitos, t0 = {}, time.time()
    if SAIDA.exists():
        # ⭐ RETOMADA: 40 mini-runs sao horas de GPU paga. Refazer o que ja' rodou nao e' so'
        #    desperdicio — muda o ajuste, porque a semente e a ordem seriam outras.
        feitos = json.loads(SAIDA.read_text(encoding="utf-8")).get("runs", {})
        print(f"retomando: {len(feitos)} mini-run(s) ja' feitos")

    for i, r in enumerate(runs, 1):
        if r["tag"] in feitos:
            continue
        mix = MIX / f"{r['tag']}.jsonl"
        comp = montar(a.dominios, r["dominio"], r["razao"], a.base_tokens,
                      a.semente + i, mix)
        tot_tok = sum(v["tokens"] for v in comp.values())
        print()
        print(f"[{i}/{len(runs)}] {r['tag']}  ·  {tot_tok:,} tokens, "
              f"{sum(v['exemplos'] for v in comp.values()):,} exemplos", flush=True)

        # ⚠️ MESMO LR E MESMAS EPOCAS EM TODOS OS MINI-RUNS. A perturbacao tem de isolar o
        #    VOLUME do dominio; variar hiperparametro junto mediria os dois de uma vez — a
        #    familia de erro do 2d, que ja' custou um veredito neste projeto.
        saida_mod = COMEIA / "models" / r["tag"]
        cmd = [PY, str(COMEIA / "train" / "sft_qlora.py"),
               "--model", a.model, "--data", str(mix), "--out", str(saida_mod),
               "--lr", str(a.lr), "--epochs", str(a.epochs),
               "--batch-size", str(a.batch_size), "--grad-accum", str(a.grad_accum),
               "--sem-checkpointing", "--save-steps", "100000"]
        t1 = time.time()
        p_ = subprocess.run(cmd, cwd=str(RAIZ), text=True, encoding="utf-8",
                            errors="replace")
        mins = round((time.time() - t1) / 60, 1)
        if p_.returncode != 0:
            print(f"🔴 {r['tag']} falhou (codigo {p_.returncode})")
            feitos[r["tag"]] = {"erro": p_.returncode, "composicao": comp}
        else:
            feitos[r["tag"]] = {"dominio": r["dominio"], "razao": r["razao"],
                                "adapter": str(saida_mod), "minutos": mins,
                                "tokens": tot_tok, "composicao": comp}
            print(f"   treinado em {mins} min", flush=True)
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        SAIDA.write_text(json.dumps({"data": date.today().isoformat(), "modelo": a.model,
                                     "base_tokens": a.base_tokens, "razoes": RAZOES,
                                     "lr": a.lr, "epochs": a.epochs,
                                     "inventario": inventario, "runs": feitos},
                                    ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [k for k, v in feitos.items() if "erro" not in v]
    ruins = [k for k, v in feitos.items() if "erro" in v]
    print()
    print("=" * 78)
    print(f"mini-runs: {len(ok)}/{len(runs)} | minutos totais: "
          f"{round((time.time() - t0) / 60, 1)}")
    print(f"com erro: {ruins or 'nenhum'}")
    print(f"✅ {SAIDA}")
    print("   Proximo: avaliar cada mini-run e AJUSTAR a lei de escala — contra a loss E")
    print("   contra a regua, que e' a adaptacao que este projeto pode fazer e o paper nao.")
    return 0 if not ruins else 1



if __name__ == "__main__":
    raise SystemExit(main())
