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

    def escrevendo_nome_da_ferramenta(self) -> bool:
        """Estamos escrevendo o VALOR de `"tool"`, no nivel de cima do objeto?

        🔴 Medido em 2026-08-27: o modelo emite ferramenta que NAO ESTA no catalogo em
        3,0% dos casos com catalogo 1-6 e **10,1% com catalogo 15** — e isso e' de 24% a
        41% de TODOS os erros de selecao, em toda condicao medida.

        Os nomes inventados denunciam o mecanismo, e e' o mesmo do `recipient` -> `receptor`:

            executar_program  9x   <- inventou em PORTUGUES
            search_livros     2x   <- metade ingles, metade portugues
            restaurant_hotel  3x   <- fundiu duas ferramentas do catalogo
            get_movies        3x   <- plural onde o catalogo tem singular

        ⚠️ No E9 eu afirmei que "o modelo nunca emitiu ferramenta fora do catalogo em 728
        casos" e descartei esta extensao. Era falso ate' naquele holdout (3,0% no mesmo
        regime) — a contagem de entao nao separava nome invalido de chamada ausente.

        ⭐ E aqui, ao contrario da restricao de VALOR, **nao existe caso legitimo que a
        restricao bloqueie**: a referencia e' sempre uma ferramenta do catalogo.
        """
        return (self.em_str and not self.str_e_chave
                and self.ultima_chave == "tool"
                and self.prof_args is None
                and self.str_prof == 1
                and bool(self.pilha) and self.pilha[-1] == "{")

    def escrevendo_valor_de_args(self) -> str | None:
        """Se estamos dentro do VALOR (nao da chave) de um argumento, devolve a chave."""
        if not (self.em_str and not self.str_e_chave):
            return None
        if self.prof_args is None or self.str_prof != self.prof_args:
            return None
        if not (self.pilha and self.pilha[-1] == "{"):
            return None
        return self.ultima_chave

    def escrevendo_chave_de_args(self) -> bool:
        return (self.em_str and self.str_e_chave
                and self.prof_args is not None
                and self.str_prof == self.prof_args
                and bool(self.pilha) and self.pilha[-1] == "{")


FIM_DE_TOKEN = set(chr(46)+chr(44)+chr(59)+chr(58)+chr(33)+chr(63)+chr(41)+chr(93)+chr(125)+chr(34)+chr(39))


def pode_fechar(ctx: str, pref: str) -> bool:
    """O valor pode TERMINAR aqui, ou ainda esta' no meio de uma sequencia do pedido?

    🔴 A v1 permitia fechar em qualquer ponto — `zorak` e' trecho valido de
    `zorak.vintel@quandrix-7739.com`, entao o modelo, impedido de SINTETIZAR, passou a
    TRUNCAR (12 -> 15 casos) e o saldo ficou -9,0 pp.

    A sequencia CONTINUA se o proximo char for alfanumerico, ou um ligador (. - @ _)
    seguido de alfanumerico. Qualquer outra coisa e' fronteira.
    ⚠️ A v2 desta funcao listava a pontuacao "que fecha" e esqueceu `%` e `"`, tornando
    39,3% das referencias impossiveis por descuido meu — `20` em `20%`, `SAVE20` em
    `"SAVE20"`. Enumerar o que FECHA e' fragil; enumerar o que CONTINUA e' fechado.
    """
    if not pref:
        return False
    i = ctx.find(pref)
    while i >= 0:
        j = i + len(pref)
        if j >= len(ctx):
            return True
        c = ctx[j]
        continua = c.isalnum() or (c in ".-@_" and j + 1 < len(ctx) and ctx[j + 1].isalnum())
        if not continua:
            return True
        i = ctx.find(pref, i + 1)
    return False


def nz(v: object) -> str:
    """Mesma normalizacao do avaliador: sem acento, minusculas, espaco colapsado."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


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
                 k: int = 1, contextos: list[str] | None = None,
                 perfil: dict | None = None, span_maximal: bool = False,
                 restringir_ferramenta: bool = False) -> None:
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
        # ── restricao de VALOR (opcional): so' age se contextos E perfil vierem juntos
        self.contextos = [nz(c) for c in contextos] if contextos else None
        self.span_maximal = span_maximal
        self.restringir_ferramenta = restringir_ferramenta
        self.n_ferramenta = 0
        self.perfil = perfil or {}
        self._cache_val: dict[tuple[int, str], object] = {}
        self.n_valor = 0
        self._por_char: dict[str, list[int]] = {}
        if self.contextos is not None:
            for i, t in enumerate(self.textos):
                z = nz(t)
                if z:
                    self._por_char.setdefault(z[0], []).append(i)

    def __call__(self, input_ids, scores):
        torch = self.torch
        self.n_passos += 1
        for linha in range(input_ids.shape[0]):
            cat = self.catalogos[linha // self.k]
            if not cat:
                continue
            est = self._estado(input_ids[linha])
            if self.restringir_ferramenta and est.escrevendo_nome_da_ferramenta():
                nomes = frozenset(cat)
                perm = self._permitidos(nomes, est.buf, scores.shape[-1])
                if perm is not None and perm.numel():
                    mascara = torch.full_like(scores[linha], float("-inf"))
                    mascara[perm] = 0.0
                    scores[linha] = scores[linha] + mascara
                    self.n_ferramenta += 1
                continue
            if not est.escrevendo_chave_de_args():
                if self.contextos is not None:
                    self._passo_valor(linha, est, scores)
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

    def _passo_valor(self, linha, est, scores):
        """🔴 O VALOR de um argumento `extraido` tem de ser um TRECHO do pedido.

        Medido: o modelo nao copia e-mail, **sintetiza** um. Com tudo igual e so' o `@`
        mudando, a copia cai de 60,2% para 41,7% (108 casos pareados, McNemar p=0,0000), e o
        que ele escreve denuncia o mecanismo:

            alvo   Zorak.Vintel@Quandrix-7739.com
            previu Zorak@Quandrix-7739.com    16x   <- descartou o que nao cabe no molde

        `Zorak@Quandrix-7739.com` NAO e' trecho do pedido, entao a restricao o torna
        impossivel. E toda referencia literal E' trecho — medido 0 de 985 inalcancaveis, o
        que a lista de candidatos nao conseguia garantir (9,4% ficavam impossiveis).

        ⚠️ O que ela NAO impede e' TRUNCAR: `Zorak` sozinho e' trecho valido. Por isso o
        ganho tem de ser medido, nao deduzido.

        🔴 MEDIDO E REPROVADO (2026-08-25). NAO LIGAR SEM RELER ISTO.

            sonda d5 (com @, onde o mecanismo vive)  +5,5 pp · p=0,125   nao significativo
            sonda d6 (sem @, controle)               +1,8 pp · p=0,219
            HOLDOUT, 2 sementes                      -9,0 pp · p=0,0000
                                                     ganhou 5, PERDEU 54

        E eu tinha medido "risco zero" antes de implementar: conferi se o VALOR PREVISTO
        estava no pedido nos casos que passavam, e estava em 100%. **Medi o destino e conclui
        sobre o caminho.** A restricao age token a token: um valor pode ser trecho do pedido
        sem que todo prefixo ate' ele seja permitido, e a mascara desvia a trajetoria.
        Terceira roupa do §2r — a verificacao rodava sobre saidas geradas SEM a restricao,
        entao nao podia exibir efeito de trajetoria.

        ⭐ Onde ela AGE (`extraido`) o comportamento e' o prometido: zero sintese, so'
        truncagem. Os `Zorak@Quandrix-7739.com` que sobram estao em chaves `formulado` e
        `raro`, fora do escopo por desenho. O problema e' que trocar sintese por truncagem
        (12 -> 15 casos) nao e' progresso, e a trajetoria mascarada estraga casos que iam bem.

        🔴 E O SPAN MAXIMAL (`--span-maximal`) FOI TENTADO E E' PIOR: -15,8 pp no teste vivo
        (152 casos), ganhou 1 e perdeu 25, p=0,0000.

        ⭐ A pre-checagem de DESTINO previa ganho 24 / perda 18 = saldo +6. Errou os DOIS
        lados na mesma direcao: o ganho virou 1 (bloquear a previsao errada nao faz o modelo
        produzir a certa — ele acha outro span valido) e a perda subiu para 25 (a mascara
        desvia trajetoria de casos que a pre-checagem dava como intocados).
        **Verificacao de destino e' otimista nos dois sentidos, nao so' num.**

        ⭐⭐ E o span maximal ser PIOR reinterpreta o achado do `@`: o modelo nao estava
        truncando por preguica, estava truncando porque NAO CONSEGUE transcrever a cadeia
        inteira. Sintetizar e' o que sobra. **Restricao de decodificacao nao conserta
        incapacidade — so' troca a forma do erro.** O `@` e' problema de TREINO.
        """
        chave = est.escrevendo_valor_de_args()
        if chave is None or not est.tool:
            return False
        if self.perfil.get(f"{est.tool}	{chave}", {}).get("classe") != "extraido":
            return False
        ctx = self.contextos[linha // self.k]
        pref = nz(est.buf)
        ch = (linha // self.k, pref)
        if ch not in self._cache_val:
            # caracteres que podem seguir o prefixo, em QUALQUER ocorrencia dele no pedido
            seguintes = set()
            if pref:
                i = ctx.find(pref)
                while i >= 0:
                    if i + len(pref) < len(ctx):
                        seguintes.add(ctx[i + len(pref)])
                    i = ctx.find(pref, i + 1)
            else:
                seguintes = set(ctx)
            ids = []
            for c in seguintes:
                for tid in self._por_char.get(c, ()):
                    z = nz(self.textos[tid])
                    if z and (pref + z) in ctx:
                        ids.append(tid)
            # ⭐ fechar so' e' permitido em FRONTEIRA (span maximal) — ver pode_fechar()
            if self.span_maximal:
                if pode_fechar(ctx, pref):
                    ids.extend(tid for tid, t in enumerate(self.textos) if t.startswith('"'))
            else:
                ids.extend(tid for tid, t in enumerate(self.textos) if t.startswith('"'))
            # 🔴 token que CONTEM aspa no meio tambem fecha a string. Se ele nao for
            #    permitido explicitamente, o modelo o usa e escapa da restricao.
            ids = [t for t in ids
                   if '"' not in self.textos[t][1:] or not self.span_maximal
                   or pode_fechar(ctx, pref + nz(self.textos[t].split(chr(34))[0]))]
            self._cache_val[ch] = (self.torch.tensor(sorted(set(ids)),
                                                     dtype=self.torch.long) if ids else None)
        perm = self._cache_val[ch]
        if perm is None or perm.numel() == 0:
            return False
        mascara = self.torch.full_like(scores[linha], float("-inf"))
        mascara[perm] = 0.0
        scores[linha] = scores[linha] + mascara
        self.n_valor += 1
        return True

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
        return (f"restricao: {self.n_mascarou} chave · {self.n_valor} valor · "
                f"{self.n_ferramenta} ferramenta · {self.n_passos} passos")


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
    # ⭐ estado de VALOR — o metodo novo precisa de teste proprio, senao repito o buraco
    #    de array que o autoteste da v1 nao cobria.
    valor = [
        ('{"tool": "x", "args": {"a": "bos', "a"),
        ('{"tool": "x", "args": {"a": "boss@x.com", "b": "ze', "b"),
        ('{"tool": "x", "args": {"a', None),          # escrevendo CHAVE, nao valor
        ('{"tool": "x", "args": {"a": "v"}}', None),  # fora de string
        ('{"tool": "x", "args": {"a": ["um", "do', None),  # dentro de ARRAY
        ('{"tool": "x", "args": {"a": {"n": "v', None),    # objeto aninhado
        ('{"tool": "x", "arg', None),
    ]
    for txt, esp in valor:
        e = EstadoJson()
        for c in txt:
            e.passo(c)
        got = e.escrevendo_valor_de_args()
        if got != esp:
            print(f"🔴 valor {txt!r}: esperado {esp}, obtido {got}")
            falhas += 1
    e = EstadoJson()
    for c in '{"tool": "x", "args": {"a": "bos':
        e.passo(c)
    if e.buf != "bos":
        print(f"🔴 buffer do valor = {e.buf!r}, esperado 'bos'")
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
