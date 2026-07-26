"""Validador DETERMINÍSTICO da abelha de extração estruturada.

É o análogo do `code_exec.py` da coder: o juiz aqui não é um LLM, é código. Duas
verificações independentes, e a segunda é a que dá a esta abelha um sinal que a
coder não tinha:

  1. CONFORMIDADE — o JSON bate com o schema? (campos obrigatórios presentes,
     tipos certos, enum dentro do domínio, array do tipo declarado, nenhum campo
     inventado fora do schema)

  2. ⭐ GROUNDEDNESS — todo valor marcado `grounded` APARECE no documento? É a
     verificação de ALUCINAÇÃO, e ela é decidível: se o modelo escreveu
     "R$ 1.240,00" e esse número não existe no texto, ele inventou. Campos
     inferidos (enum, booleano, data reformatada) não passam por aqui — para
     eles a conformidade é o que dá para checar honestamente.

Comparação de valores é TOLERANTE onde tem que ser (a alternativa é rejeitar
acerto por formatação):
  - números: 1.240,00 / 1,240.00 / 1240.0 são o mesmo valor;
  - datas: aceita ISO e as formas comuns pt/en/es/fr, comparadas como data;
  - strings: casefold + colapso de espaço + remoção de acento na comparação.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

SCHEMAS_FILE = Path(__file__).resolve().parent / "extraction_schemas.json"

TIPOS = {"string", "number", "integer", "boolean", "date", "enum", "array[string]"}

# Prefixos de mês em pt/en/es/fr. Casamento por prefixo MAIS LONGO primeiro:
# em francês "juin" (6) e "juillet" (7) colidem em 3 letras ("jui"), então 3
# caracteres não bastam. Nos outros meses o prefixo de 3 serve para os 4 idiomas
# (março/march/mars/marzo → "mar").
_MESES = {
    "juin": 6, "juil": 7,                                        # desempate fr
    "jan": 1, "ene": 1,
    "fev": 2, "feb": 2,
    "mar": 3,
    "abr": 4, "apr": 4, "avr": 4,
    "mai": 5, "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8, "aug": 8, "aou": 8,
    "set": 9, "sep": 9,
    "out": 10, "oct": 10,
    "nov": 11,
    "dez": 12, "dec": 12, "dic": 12,
}
_MESES_ORD = sorted(_MESES, key=len, reverse=True)


def load_schemas(path: Path | str = SCHEMAS_FILE) -> dict:
    """Catálogo {nome: schema}. Mesma fonte para gerar, validar, treinar e servir."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return {s["name"]: s for s in data["schemas"]}


# -------------------------------------------------- prompt (fonte única também) ---

def render_schema(schema: dict) -> str:
    """O schema como texto, para ir DENTRO do pedido.

    Marca explicitamente quais campos são COPIADOS do documento e quais são
    INFERIDOS. Sem isso o modelo (e o professor, na geração) não tem como saber
    de quais valores se cobra literalidade — e é justamente neles que o
    validador de groundedness reprova.
    """
    linhas = []
    for nome, spec in schema["fields"].items():
        t = spec["type"]
        if t == "enum":
            t = "um de: " + " | ".join(spec.get("values", []))
        obrig = "obrigatorio" if spec.get("required") else "opcional"
        origem = "COPIAR literal do documento" if spec.get("grounded") else "inferir/normalizar"
        linhas.append(f'- "{nome}" ({t}, {obrig}) — {origem}')
    return "\n".join(linhas)


def build_task_prompt(schema: dict, documento: str) -> str:
    """O pedido EXATO que a abelha recebe — no treino, no eval e em produção.

    ⚠️ Vai no turno do USUÁRIO, e a abelha NÃO tem system prompt. Isso é
    deliberado: medimos na `coder` que um system prompt em português arrasta a
    saída para o português mesmo mandando o contrário (inglês 0/6 com prompt PT,
    6/6 sem prompt). Como o schema muda a cada pedido, ele tem que ir no turno do
    usuário de qualquer forma — então não sobra motivo para ter system prompt, e
    o confound de idioma desaparece junto.
    """
    return (
        f"Extraia os campos abaixo do documento e responda SOMENTE com um objeto JSON.\n\n"
        f"CAMPOS ({schema['name']} — {schema['description']}):\n{render_schema(schema)}\n\n"
        "REGRAS:\n"
        "1. Responda SO o JSON, sem texto antes ou depois, sem ```.\n"
        "2. Copie os valores COMO ESTAO no documento. NAO invente nada.\n"
        "3. Campo opcional que nao aparece no documento: OMITA a chave. "
        "Nao chute, nao preencha com vazio.\n"
        "4. Nao acrescente campos que nao estao na lista.\n"
        "5. Datas no formato AAAA-MM-DD. Numeros sem simbolo de moeda.\n"
        "6. Texto livre (resumo, titulo) no MESMO IDIOMA do documento.\n\n"
        f"DOCUMENTO:\n{documento}"
    )


# ------------------------------------------------------------------ normalização ---

def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm_texto(s: str) -> str:
    """casefold + sem acento + espaço colapsado. Para comparar e para buscar no doc."""
    return re.sub(r"\s+", " ", _sem_acento(str(s)).casefold()).strip()


def norm_numero(v) -> float | None:
    """1.240,00 · 1,240.00 · 1240 · 'R$ 1.240,00' → 1240.0. None se não for número.

    O ponto delicado é decidir quem é separador decimal e quem é de milhar. Regra:
    o ÚLTIMO separador presente manda, e só se sobrarem <= 2 dígitos depois dele.
    """
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v)).strip(".,")   # ⚠️ 'R$ 1.240,00.' — a
    if not s or not re.search(r"\d", s):               # pontuação da frase vinha
        return None                                    # junto e quebrava o float
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        mil = "." if dec == "," else ","
        s = s.replace(mil, "").replace(dec, ".")
    elif "," in s:
        # vírgula é decimal só se sobrarem <= 2 dígitos (1.240,00 vs 1,240)
        s = s.replace(",", "." if len(s.split(",")[-1]) <= 2 else "")
    elif s.count(".") > 1 or (("." in s) and len(s.split(".")[-1]) == 3):
        s = s.replace(".", "")          # 1.240 ou 1.240.500 = milhar
    try:
        return float(s)
    except ValueError:
        return None


def norm_data(v) -> date | None:
    """ISO, dd/mm/aaaa, mm/dd/aaaa (ambíguo → assume dd/mm), '12 de março de 2026'."""
    s = norm_texto(v)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})", s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        if mo > 12 and d <= 12:          # veio mm/dd
            d, mo = mo, d
        y += 2000 if y < 100 else 0
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    # Mês por NOME, em qualquer ordem ("12 de março de 2026", "March 12, 2026").
    # ⚠️ Não usar \D entre os grupos: \D casa letra, então ele engolia " de m" e
    # sobrava "arco" — nenhum mês batia e só a forma numérica funcionava.
    ano = re.search(r"\b(\d{4})\b", s)
    if not ano:
        return None
    mes = next((_MESES[k] for tok in re.findall(r"[a-z]+", s)
                for k in _MESES_ORD if tok.startswith(k)), None)
    dia = next((int(d) for d in re.findall(r"\b(\d{1,2})\b", s)), None)
    if mes and dia:
        try:
            return date(int(ano[1]), mes, dia)
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------- conformidade ---

def _tipo_ok(valor, spec: dict, strict: bool = False) -> str | None:
    """None se o valor bate com o tipo declarado; senão a mensagem do erro.

    `strict` separa dois usos que exigem rigores DIFERENTES, e confundi-los
    estraga o dataset:

      strict=False (AVALIAÇÃO) — tolerante ao formato. "GBP 1.295,00" conta como
        acerto de 1295.0, porque a pergunta é "o modelo pegou o valor certo?".

      strict=True (ACEITAR DADO DE TREINO) — o tipo tem que ser o tipo JSON
        declarado. Número é número, não string com símbolo de moeda; data é ISO.
        Sem isso, metade do treino sai `312.40` e metade `"GBP 1,295.00"`, a
        abelha aprende a emitir JSON inconsistente, e a parte "estruturada" da
        extração estruturada deixa de valer.
    """
    t = spec["type"]
    if t == "string":
        return None if isinstance(valor, str) and valor.strip() else "esperava string nao-vazia"
    if t == "integer":
        if isinstance(valor, bool):
            return "esperava inteiro, veio booleano"
        if strict and not isinstance(valor, int):
            return f"esperava inteiro JSON, veio {type(valor).__name__}"
        n = norm_numero(valor)
        return None if n is not None and float(n).is_integer() else "esperava inteiro"
    if t == "number":
        if isinstance(valor, bool):
            return "esperava numero, veio booleano"
        if strict and not isinstance(valor, (int, float)):
            return f"esperava numero JSON, veio {type(valor).__name__} ({valor!r})"
        return None if norm_numero(valor) is not None else "esperava numero"
    if t == "boolean":
        return None if isinstance(valor, bool) else "esperava booleano (true/false)"
    if t == "date":
        if strict and not (isinstance(valor, str)
                           and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor.strip())):
            return f"esperava data ISO AAAA-MM-DD, veio {valor!r}"
        return None if norm_data(valor) else "esperava data reconhecivel"
    if t == "enum":
        if strict and valor not in spec.get("values", []):
            return f"esperava enum EXATO de {spec.get('values')}, veio {valor!r}"
        vals = {norm_texto(x) for x in spec.get("values", [])}
        return None if norm_texto(valor) in vals else \
            f"fora do dominio {spec.get('values')}"
    if t == "array[string]":
        if not isinstance(valor, list) or not valor:
            return "esperava lista nao-vazia"
        return None if all(isinstance(x, str) and x.strip() for x in valor) else \
            "lista deve conter strings nao-vazias"
    return f"tipo desconhecido no schema: {t}"


def validar_conformidade(obj, schema: dict, strict: bool = False) -> list[str]:
    """Lista de erros. Vazia = conforme. Ver `_tipo_ok` sobre `strict`."""
    erros: list[str] = []
    if not isinstance(obj, dict):
        return ["a saida nao e um objeto JSON"]
    campos = schema["fields"]
    for nome, spec in campos.items():
        if nome not in obj or obj[nome] is None:
            if spec.get("required"):
                erros.append(f"campo obrigatorio ausente: {nome}")
            continue
        err = _tipo_ok(obj[nome], spec, strict)
        if err:
            erros.append(f"{nome}: {err}")
    for extra in set(obj) - set(campos):
        erros.append(f"campo inventado (fora do schema): {extra}")
    return erros


# ------------------------------------------------------------------- groundedness ---

def _no_doc(valor, doc_norm: str, doc_num: set[float]) -> bool:
    n = norm_numero(valor)
    if n is not None and not isinstance(valor, str):
        return n in doc_num
    alvo = norm_texto(valor)
    if not alvo:
        return False
    if alvo in doc_norm:
        return True
    # número escrito como string ("R$ 1.240,00") — compara pelo valor
    return n is not None and n in doc_num


def validar_groundedness(obj, schema: dict, documento: str) -> list[str]:
    """Valores `grounded` que NÃO aparecem no documento = alucinação."""
    if not isinstance(obj, dict):
        return ["a saida nao e um objeto JSON"]
    doc_norm = norm_texto(documento)
    doc_num = {n for n in (norm_numero(t) for t in
                           re.findall(r"[\d][\d.,]*", documento)) if n is not None}
    fugas: list[str] = []
    for nome, spec in schema["fields"].items():
        if not spec.get("grounded") or nome not in obj or obj[nome] is None:
            continue
        valores = obj[nome] if isinstance(obj[nome], list) else [obj[nome]]
        for v in valores:
            if not _no_doc(v, doc_norm, doc_num):
                fugas.append(f"{nome}: {v!r} NAO aparece no documento (alucinacao)")
    return fugas


# ------------------------------------------------------------------------ extração ---

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extrair_json(texto: str) -> dict | None:
    """Primeiro objeto JSON do texto (aceita cercado por ``` e texto ao redor)."""
    if not texto:
        return None
    m = _FENCE.search(texto)
    candidatos = [m.group(1)] if m else []
    ini = texto.find("{")
    if ini >= 0:
        candidatos.append(texto[ini:texto.rfind("}") + 1])
    candidatos.append(texto)
    for c in candidatos:
        try:
            obj = json.loads(c.strip())
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def avaliar(saida: str, schema: dict, documento: str, strict: bool = False) -> dict:
    """Veredito completo de uma saída. É o que o filtro, o eval e o treino usam.

    `strict=True` ao ACEITAR dado de treino (tipo JSON exato); `strict=False` ao
    AVALIAR o modelo (tolerante a formato). Ver `_tipo_ok`.
    """
    obj = extrair_json(saida)
    if obj is None:
        return {"json_ok": False, "conforme": False, "grounded": False,
                "erros": ["nao foi possivel extrair JSON da saida"], "obj": None}
    conf = validar_conformidade(obj, schema, strict)
    grd = validar_groundedness(obj, schema, documento) if not conf else []
    return {"json_ok": True, "conforme": not conf, "grounded": not grd,
            "erros": conf + grd, "obj": obj}


def campos_certos(obj, ref: dict, schema: dict) -> tuple[int, int]:
    """(acertos, total) campo a campo contra a referência — a métrica do eval.

    Comparação por TIPO, não por string: 1.240,00 == 1240.0, '12/03/2026' ==
    '2026-03-12', lista compara como conjunto normalizado.
    """
    acertos = total = 0
    for nome, spec in schema["fields"].items():
        if nome not in ref or ref[nome] is None:
            continue
        total += 1
        got = (obj or {}).get(nome)
        if got is None:
            continue
        t = spec["type"]
        if t in ("number", "integer"):
            ok = norm_numero(got) == norm_numero(ref[nome])
        elif t == "date":
            ok = norm_data(got) == norm_data(ref[nome])
        elif t == "boolean":
            ok = got is ref[nome]
        elif t == "array[string]":
            ok = (isinstance(got, list) and
                  {norm_texto(x) for x in got} == {norm_texto(x) for x in ref[nome]})
        else:
            ok = norm_texto(got) == norm_texto(ref[nome])
        acertos += int(bool(ok))
    return acertos, total
