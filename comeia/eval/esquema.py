"""Decodificacao restrita ao esquema — a chave do argumento so' pode vir do catalogo.

🔴 POR QUE ISTO EXISTE. Medido no E8 (holdout de ferramenta inedita, 728 casos): das 270
falhas com a ferramenta CERTA, **62 tem o valor certo sob uma chave inventada**. O padrao e'
inequivoco:

    recipient -> receptor    49x   <- traducao literal para portugues
    recipient -> receivable   2x
    recipient -> request      2x

O modelo le' o catalogo para escolher a ferramenta (96,9% em ferramentas nunca vistas) e
**deixa de ler para copiar o nome do argumento**. O nome exato esta' escrito no proprio
prompt, na linha `args:`/`obrigatorios:`.

⭐ E o corpus PROVA que decorar nao funciona: `generate_qr_code` aparece com esquemas
diferentes em prompts diferentes (`data`, `input_data`, `qr_size`, `size`, `format`,
`error_correction`, `error_correction_level`). A unica politica que acerta e' LER.

## O desenho, e onde o risco REALMENTE esta'

A restricao so' **remove continuacoes impossiveis**: uma geracao que ja' era valida passa
intacta. A OPORTUNIDADE foi medida antes de escrever uma linha, sobre os dumps existentes:

    casos que PASSAM e tem chave fora do esquema ......   0
    casos que FALHAM com chave fora do esquema ........ 117
      dos quais com o VALOR certo (recuperaveis) ......  61  = 8,4% do holdout

🔴 E EU LI ISSO COMO "risco zero". Estava errado, e o erro e' de metodo, nao de aritmetica:
aquela medicao roda sobre as saidas do modelo SEM restricao — ela nao tem como exibir um
defeito no mecanismo de restricao, porque o mecanismo ainda nao existia. Media a
oportunidade e foi apresentada como se cobrisse o risco. **Sao coisas diferentes.**

O risco real e' o mecanismo mascarar onde nao devia. Aconteceu: ver o bug de array em
`EstadoJson` — 35 casos destruidos, e o sintoma apareceu como "ferramenta certa caiu 5,2 pp",
numa metrica em que a restricao nao devia nem encostar. **A unica medicao que enxerga isso e'
o pareado APOS rodar, contando o que piorou.**

⚠️ A guarda que sustenta isso e' o parser: se ele perder um argumento opcional, proibe uma
chave legitima. O criterio e' a REFERENCIA — `--validar` confere que todo gabarito do holdout
e' aceito. Medido: **2.118 de 2.118**.

⚠️ E em nenhum ponto a restricao pode produzir conjunto permitido VAZIO. Quando nao ha' o que
permitir (ferramenta desconhecida, esquema ausente, todas as chaves ja' usadas), a saida e'
`None` = **nao restringe**. Forcar o modelo a escolher dentro de um conjunto vazio seria
trocar um erro por lixo.

Uso:
    python comeia/eval/esquema.py --validar    # confere o parser contra os gabaritos
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"

RX_TOOL = re.compile(r"^- (\w+):")
RX_ARGS = re.compile(r"\s*args:\s*(.*)")
RX_OBR = re.compile(r"\s*obrigatorios:\s*(.*)")
# nome de argumento = identificador seguido de "(", no inicio da lista ou apos "), "
RX_NOME = re.compile(r"(?:^|\),\s*)([A-Za-z_]\w*)\s*\(")


def esquemas_do_prompt(sistema: str | None) -> dict[str, frozenset[str]]:
    """{ferramenta: chaves declaradas} lido do system prompt DO PROPRIO exemplo.

    ⚠️ UNIAO, nunca sobrescrita: 1 prompt em 728 declara a mesma ferramenta duas vezes com
    esquemas diferentes (`generate_qr_code` com `input_data` e depois com `data`). A primeira
    versao deste parser resetava no segundo bloco e passava a REJEITAR o gabarito.
    """
    if not sistema:
        return {}
    out: dict[str, set[str]] = {}
    atual: str | None = None
    for ln in sistema.splitlines():
        m = RX_TOOL.match(ln)
        if m:
            atual = m.group(1)
            out.setdefault(atual, set())
            continue
        if atual is None:
            continue
        m = RX_ARGS.match(ln)
        if m:
            out[atual].update(RX_NOME.findall(m.group(1)))
        m = RX_OBR.match(ln)
        if m:
            out[atual].update(x.strip() for x in m.group(1).split(",") if x.strip())
    return {k: frozenset(v) for k, v in out.items() if v}


# ─────────────────────────── maquina de estados do JSON ───────────────────────────

class EstadoJson:
    """Onde estamos dentro de `{"tool": ..., "args": {...}}` — char a char.

    🔴 A v1 NAO tinha pilha de conteineres e ignorava `[` / `]`. Consequencia medida: em
    `{"participants": ["John", "Sarah", "Mike"]}` a virgula do ARRAY era lida como virgula de
    objeto, `"Sarah"` virava posicao de chave e era mascarada para uma chave do esquema ->
    `["John", "date": "2022-05-25"` -> JSON invalido -> ferramenta nao parseada. Custou 35
    casos e apareceu no relatorio como "ferramenta certa caiu 5,2 pp", que e' onde a
    restricao nao devia nem encostar.

    ⚠️ O autoteste da v1 cobria chave aninhada, chave dentro de string e aspa escapada — e
    nenhum array. Guarda que nao exercita o caso nao guarda o caso.

    So' precisa enxergar estrutura ASCII. Valores com acento podem chegar corrompidos por
    decodificacao token-a-token e isso NAO afeta a contagem: um par UTF-8 partido vira
    U+FFFD, nunca uma aspa.
    """

    def __init__(self) -> None:
        self.em_str = False
        self.esc = False
        self.buf = ""
        self.str_e_chave = False
        self.str_prof = 0
        self.pilha: list[str] = []          # '{' ou '[' — o conteiner corrente
        self.prof_args: int | None = None   # len(pilha) do objeto de args
        self.esperando_chave = False
        self.ultima_chave: str | None = None
        self.tool: str | None = None
        self.chaves_usadas: set[str] = set()

    def passo(self, c: str) -> None:
        if self.em_str:
            if self.esc:
                self.esc = False
                self.buf += c
            elif c == "\\":
                self.esc = True
            elif c == '"':
                self.em_str = False
                self._fechou_string()
            else:
                self.buf += c
            return
        if c == '"':
            self.em_str = True
            self.esc = False
            self.buf = ""
            self.str_e_chave = self.esperando_chave
            self.str_prof = len(self.pilha)
        elif c == "{":
            self.pilha.append("{")
            if self.ultima_chave == "args" and self.prof_args is None:
                self.prof_args = len(self.pilha)
                self.chaves_usadas = set()
            self.esperando_chave = True
        elif c == "[":
            self.pilha.append("[")
            self.esperando_chave = False     # 🔴 dentro de array NAO ha' chave
        elif c in "}]":
            if self.prof_args is not None and len(self.pilha) == self.prof_args:
                self.prof_args = None
            if self.pilha:
                self.pilha.pop()
            self.esperando_chave = False
        elif c == ",":
            # virgula so' anuncia chave se o conteiner corrente for OBJETO
            self.esperando_chave = bool(self.pilha) and self.pilha[-1] == "{"
        elif c == ":":
            self.esperando_chave = False

    def _fechou_string(self) -> None:
        if self.str_e_chave:
            self.ultima_chave = self.buf
            if self.prof_args is not None and self.str_prof == self.prof_args:
                self.chaves_usadas.add(self.buf)
        else:
            if self.ultima_chave == "tool" and self.tool is None:
                self.tool = self.buf
        self.esperando_chave = False

    def escrevendo_chave_de_args(self) -> bool:
        return (self.em_str and self.str_e_chave
                and self.prof_args is not None
                and self.str_prof == self.prof_args
                and bool(self.pilha) and self.pilha[-1] == "{")


def _cabe(prefixo: str, s: str, chaves: frozenset[str]) -> bool:
    """`prefixo + s` continua rumo a uma chave valida (ou a fecha exatamente)?"""
    q = prefixo
    for ch in s:
        if ch == '"':
            return q in chaves          # fechou: tem de ser chave COMPLETA
        q += ch
        if not any(k.startswith(q) for k in chaves):
            return False
    return True                          # nao fechou: ainda e' prefixo valido


# ─────────────────────────────── o LogitsProcessor ───────────────────────────────

class RestritorDeEsquema:
    """Mascara, e SO' no ponto em que uma chave de `args` esta' sendo escrita.

    Fora desse ponto devolve os scores intactos: nao toca no nome da ferramenta (o modelo ja'
    acerta 96,9% e nunca emitiu ferramenta fora do catalogo em 728 casos), nem nos valores.
    """

    def __init__(self, tok, catalogos: list[dict[str, frozenset[str]]], plen: int,
                 k: int = 1) -> None:
        import torch
        self.torch = torch
        self.tok = tok
        self.catalogos = catalogos
        self.plen = plen
        self.k = k
        self.textos = _textos_de_token(tok)
        self._cache: dict[tuple[frozenset[str], str], object] = {}
        self.n_mascarou = 0
        self.n_passos = 0

    def __call__(self, input_ids, scores):
        torch = self.torch
        self.n_passos += 1
        for linha in range(input_ids.shape[0]):
            cat = self.catalogos[linha // self.k]
            if not cat:
                continue
            est = self._estado(input_ids[linha])
            if not est.escrevendo_chave_de_args():
                continue
            chaves = cat.get(est.tool or "")
            if not chaves:
                continue
            restantes = frozenset(chaves - est.chaves_usadas)
            if not restantes:
                continue                 # 🔴 nunca forcar escolha em conjunto vazio
            perm = self._permitidos(restantes, est.buf, scores.shape[-1])
            if perm is None or perm.numel() == 0:
                continue
            mascara = torch.full_like(scores[linha], float("-inf"))
            mascara[perm] = 0.0
            scores[linha] = scores[linha] + mascara
            self.n_mascarou += 1
        return scores

    def _estado(self, ids) -> EstadoJson:
        est = EstadoJson()
        for t in ids[self.plen:].tolist():
            for c in self.textos[t]:
                est.passo(c)
        return est

    def _permitidos(self, chaves: frozenset[str], prefixo: str, vocab: int):
        ch = (chaves, prefixo)
        if ch not in self._cache:
            ids = [i for i, s in enumerate(self.textos)
                   if i < vocab and s and _cabe(prefixo, s, chaves)]
            self._cache[ch] = self.torch.tensor(ids, dtype=self.torch.long) if ids else None
        v = self._cache[ch]
        return v.to("cpu") if v is None else v

    def relatorio(self) -> str:
        return (f"restricao: {self.n_mascarou} mascaramentos em {self.n_passos} passos · "
                f"{len(self._cache)} prefixos distintos em cache")


def _textos_de_token(tok) -> list[str]:
    """Texto decodificado de cada id, uma vez so'.

    ⚠️ Tokens de byte-fallback decodificam para U+FFFD e simplesmente nao casam com prefixo
    de chave — ficam mascarados, que e' o correto: nome de argumento e' ASCII.
    """
    n = len(tok)
    return [tok.decode([i], skip_special_tokens=False) for i in range(n)]


def catalogos_de(rows: list[dict], partes) -> list[dict[str, frozenset[str]]]:
    out = []
    for row in rows:
        sistema = partes(row)[0]
        out.append(esquemas_do_prompt(sistema))
    return out


# ───────────────────────────────── validacao ─────────────────────────────────

def validar(caminho: Path) -> int:
    """🔴 Se o parser nao aceita o GABARITO, o parser e' que esta' errado."""
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_ref = n_chave = 0
    ruins: list[str] = []
    sem_esquema = 0
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        sistema = next((m["content"] for m in r["prompt"] if m["role"] == "system"), None)
        esq = esquemas_do_prompt(sistema)
        o = json.loads(r["completion"][0]["content"])
        n_ref += 1
        chaves = esq.get(o["tool"])
        if not chaves:
            sem_esquema += 1
            continue
        for k in (o.get("args") or {}):
            n_chave += 1
            if k not in chaves:
                ruins.append(f"{o['tool']}.{k}  esquema={sorted(chaves)}")
    print(f"referencias: {n_ref} · chaves conferidas: {n_chave} · "
          f"sem esquema no prompt: {sem_esquema}")
    if ruins:
        print(f"🔴 chaves de REFERENCIA rejeitadas pelo parser: {len(ruins)}")
        for x in ruins[:15]:
            print("   ", x)
        return 1
    print("✅ o parser aceita 100% dos gabaritos — seguro para restringir")
    return 0


def _autoteste() -> int:
    """A maquina de estados, nos casos que importam."""
    casos = [
        ('{"tool": "send_email", "args": {"rec', True, "rec", "send_email"),
        ('{"tool": "send_email", "args": {"recipient": "a@b.c", "sub', True, "sub", "send_email"),
        ('{"tool": "send_email", "args": {"recipient": "a@b.c"}}', False, "", "send_email"),
        ('{"tool": "send_email", "args": {"recipient": "', False, "", "send_email"),
        ('{"tool": "x", "args": {"a": {"nested": 1}, "b', True, "b", "x"),
        # 🔴 ARRAYS — o buraco que custou 35 casos. A virgula dentro de [] NAO anuncia chave.
        ('{"tool": "x", "args": {"p": ["John", "Sar', False, "", "x"),
        ('{"tool": "x", "args": {"p": ["John", "Sarah"], "d', True, "d", "x"),
        ('{"tool": "x", "args": {"p": [{"n": 1}, {"m', False, "", "x"),
        ('{"tool": "x", "args": {"p": [[1, 2], "a', False, "", "x"),
        ('{"tool": "x", "args": {"p": ["a"], "q": ["b", "c"], "r', True, "r", "x"),
        ('{"tool": "x", "args": {"a": "tem { e } dentro", "b', True, "b", "x"),
        ('{"tool": "x", "args": {"a": "aspa \\" escapada", "b', True, "b", "x"),
        ('{"to', False, "", None),
    ]
    falhas = 0
    for txt, esp_chave, esp_buf, esp_tool in casos:
        e = EstadoJson()
        for c in txt:
            e.passo(c)
        got = (e.escrevendo_chave_de_args(), e.buf if e.escrevendo_chave_de_args() else "", e.tool)
        if got != (esp_chave, esp_buf, esp_tool):
            print(f"🔴 {txt!r}\n   esperado {(esp_chave, esp_buf, esp_tool)} · obtido {got}")
            falhas += 1
    ch = frozenset({"recipient", "subject", "content"})
    for prefixo, s, esp in [("rec", "ipient", True), ("rec", "eptor", False),
                            ("recipient", '":', True), ("recip", '":', False),
                            ("", "sub", True), ("", "rece", False),
                            ("subject", '": "', True)]:
        if _cabe(prefixo, s, ch) != esp:
            print(f"🔴 _cabe({prefixo!r}, {s!r}) != {esp}")
            falhas += 1
    print("✅ autoteste da maquina de estados" if not falhas else f"🔴 {falhas} falhas")
    return 1 if falhas else 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--holdout", type=Path, default=PROC / "holdout_ferramenta.eval.jsonl")
    a = ap.parse_args()
    r = _autoteste()
    if a.validar:
        r |= validar(a.holdout)
    return r


if __name__ == "__main__":
    raise SystemExit(main())
