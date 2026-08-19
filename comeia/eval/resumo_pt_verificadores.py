"""Verificadores determinísticos de resumo em PT — por execução, nunca por similaridade.

⭐ POR QUE NÃO ROUGE, E POR QUE NÃO JUIZ-LLM

ROUGE mede sobreposição de n-gramas com uma referência. Um resumo correto escrito com outras
palavras pontua mal; um resumo que copia trechos ao acaso pontua bem. É similaridade, não
verificação — e este projeto tem regra explícita contra medir por similaridade quando dá para
medir por execução.

Juiz-LLM resolve o problema de vocabulário e cria dois piores: o juiz é mais caro que o modelo
avaliado, e — pela lição já registrada — *quem gera não pode avaliar*. Um juiz generoso produz
um número bonito que ninguém questiona.

O que dá para verificar por execução num resumo:

  · **fidelidade** — todo número e toda entidade do resumo existem na fonte? (invenção)
  · **cobertura** — os fatos essenciais da fonte sobreviveram ao resumo? (omissão)
  · **compressão** — o resumo é de fato menor que a fonte?

🔴 A COMPRESSÃO NÃO É DETALHE DE FORMATO — É O QUE FECHA A PORTA DOS FUNDOS.
   Sem ela, copiar a fonte inteira pontua **100% em fidelidade e 100% em cobertura**. Toda
   métrica de resumo baseada em fidelidade tem essa porta, e ela é exatamente o tipo de falha
   que só melhora o número — o modo que este projeto já aprendeu a temer. Há caso adversarial
   no gabarito só para isso.

⚠️ O QUE ISTO NÃO MEDE: coerência, fluência, escolha do que é importante além da lista
   declarada, e compreensão. Um resumo pode passar em tudo aqui e ser ilegível. O número deste
   arquivo é um **piso de utilidade**, não uma nota de qualidade — e chamá-lo de outra coisa
   seria repetir a confusão que torna avaliação de geração fácil de fraudar.
"""

from __future__ import annotations

import re
import unicodedata


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def normalizar(s: str) -> str:
    """Minúsculas, sem acento, espaços colapsados. Para comparar entidades e respostas."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ números
# ⚠️ EM PT A VÍRGULA É DECIMAL E O PONTO É MILHAR — o oposto do inglês. Um extrator portado
#    de código em inglês lê "1.500" como 1,5 e "2,5" como 25. Os dois erros passam
#    despercebidos porque produzem números plausíveis.
_NUM = re.compile(r"\d[\d.  ]*(?:,\d+)?|\d+(?:,\d+)?")
_ESCALAS = {"mil": 1_000, "milhao": 1_000_000, "milhoes": 1_000_000,
            "bilhao": 1_000_000_000, "bilhoes": 1_000_000_000}
_ESCALAS_ORD = sorted(_ESCALAS.items(), key=lambda kv: -len(kv[0]))


def _para_float(bruto: str) -> float | None:
    t = bruto.replace(" ", "").replace(" ", "").rstrip(".")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") >= 1:
        partes = t.split(".")                    # ponto e' milhar se os grupos tem 3 digitos
        t = "".join(partes) if all(len(p) == 3 for p in partes[1:]) else t
    try:
        return float(t)
    except ValueError:
        return None


def extrair_numeros(texto: str) -> set[float]:
    """Os valores numéricos do texto, já com a escala por extenso aplicada.

    ⭐ 'R$ 2,5 milhões' e 'R$ 2.500.000' são O MESMO NÚMERO. Se o extrator não resolver a
    escala, um resumo que parafraseia a magnitude é acusado de inventar dado — e o avaliador
    passa a punir justamente a paráfrase competente. Há caso de gabarito para isso.
    """
    fora, t = set(), _nfc(texto)
    for m in _NUM.finditer(t):
        v = _para_float(m.group())
        if v is None:
            continue
        cauda = normalizar(t[m.end():m.end() + 14]).lstrip()
        # 🔴 PREFIXO MAIS LONGO PRIMEIRO. 'milhoes'.startswith('mil') e' verdadeiro, entao
        #    a ordem ingenua le 'R$ 2,5 milhoes' como 2.500 — erro de MIL VEZES que sai um
        #    numero plausivel e passa direto. Pego pelo teste de fumaca, nao pelo raciocinio.
        mult = next((f for pfx, f in _ESCALAS_ORD if cauda.startswith(pfx)), 1)
        fora.add(v * mult)      # ⚠️ SO' o valor semantico, NUNCA tambem o `v` cru: guardar
    return fora                 #    2,5 junto de 2.500.000 faz a fonte que escreveu o
                                #    numero por extenso acusar de invencao o resumo que o
                                #    escreveu por extenso tambem — os dois estao certos.


def numeros_inventados(resumo: str, fonte: str) -> list[float]:
    """Números do resumo que não existem na fonte. Lista vazia = fiel."""
    da_fonte = extrair_numeros(fonte)
    ruins = []
    for v in extrair_numeros(resumo):
        # tolerancia de 2%: ARREDONDAMENTO honesto (2,47 mi -> "2,5 mi") nao e' invencao
        if any(abs(v - f) <= max(1e-6, abs(f) * 0.02) for f in da_fonte):
            continue
        ruins.append(v)
    return sorted(ruins)


# ------------------------------------------------------------------ entidades
_PARADAS = {"o", "a", "os", "as", "de", "da", "do", "das", "dos", "e", "em", "no", "na",
            "nos", "nas", "um", "uma", "para", "por", "com", "que", "ao", "aos", "se",
            "sao", "foi", "ja", "mais", "sobre", "entre", "ate", "apos", "segundo", "tambem"}
_MAIUSC = re.compile(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç-]{2,}")


def extrair_entidades(texto: str) -> set[str]:
    """Sequências capitalizadas que não abrem frase — aproximação de nome próprio.

    ⚠️ ISTO NÃO É NER, E A APROXIMAÇÃO ERRA NOS DOIS SENTIDOS: perde nome próprio no início da
    frase e captura palavra capitalizada por ênfase. A calibragem é empírica e está no
    gabarito: os resumos de referência, que por construção só usam entidades da fonte,
    precisam medir **zero** entidade inventada. Se um dia medirem mais que zero, o detector é
    que está errado — não o resumo.
    """
    t = _nfc(texto)
    inicios = {m.start(1) for m in
               re.finditer(r"(?:^|[.!?:;]\s+|\n\s*[-•*]?\s*)([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]\w*)", t)}
    fora = set()
    for m in _MAIUSC.finditer(t):
        if m.start() in inicios:
            continue
        n = normalizar(m.group())
        if n and n not in _PARADAS:
            fora.add(n)
    return fora


def entidades_inventadas(resumo: str, fonte: str) -> list[str]:
    """Nomes próprios do resumo ausentes da fonte.

    Compara também token a token, para que 'Prefeitura de Sorocaba' não seja acusada de
    invenção quando a fonte escreveu 'Prefeitura Municipal de Sorocaba'.
    """
    da_fonte = extrair_entidades(fonte)
    tokens_fonte = {tk for e in da_fonte for tk in e.split()} | set(normalizar(fonte).split())
    return sorted(e for e in extrair_entidades(resumo)
                  if e not in da_fonte and not all(tk in tokens_fonte for tk in e.split()))


# ------------------------------------------------------------------ cobertura e tamanho

def fato_presente(resumo: str, fato: dict) -> bool:
    """Um fato está no resumo se qualquer uma de suas formas aparece.

    Número compara por VALOR (via extrator, resolvendo escala); texto compara por substring
    normalizada. Comparar número por substring reprovaria 'R$ 2,5 milhões' contra o gabarito
    '2500000' — de novo, punindo a paráfrase certa.
    """
    if fato.get("tipo") == "numero":
        alvo = float(fato["valor"])
        return any(abs(v - alvo) <= max(1e-6, abs(alvo) * 0.02) for v in extrair_numeros(resumo))
    r = normalizar(resumo)
    return any(normalizar(f) in r for f in [fato["valor"], *fato.get("aliases", [])])


def cobertura(resumo: str, fatos: list[dict]) -> tuple[int, int]:
    return sum(fato_presente(resumo, f) for f in fatos), len(fatos)


def contar_palavras(s: str) -> int:
    return sum(1 for t in s.split() if any(c.isalnum() for c in t))


def razao_compressao(resumo: str, fonte: str) -> float:
    """Palavras do resumo ÷ palavras da fonte. Menor é mais comprimido."""
    return contar_palavras(resumo) / max(1, contar_palavras(fonte))


# ------------------------------------------------------------------ veredito por item

LIMITES = {"compressao_max": 0.35, "compressao_min": 0.05,
           "cobertura_min": 0.60, "qa_min": 0.50}


def avaliar_resumo(resumo: str, item: dict, limites: dict | None = None) -> dict:
    """Veredito de um resumo. `ok` exige TODAS as condições — como o IFEval estrito.

    O piso de compressão existe pelo motivo simétrico ao teto: um resumo de três palavras
    também não é resumo. Sem piso, a resposta vazia passa em fidelidade (nada inventado) e a
    única coisa que a reprova é a cobertura — proteção fina demais para uma falha tão banal.
    """
    L = {**LIMITES, **(limites or {})}
    fonte = item["fonte"]
    n_inv = numeros_inventados(resumo, fonte)
    e_inv = entidades_inventadas(resumo, fonte)
    cob_ok, cob_n = cobertura(resumo, item["fatos_essenciais"])
    qa_ok, qa_n = cobertura(resumo, [p["fato"] for p in item.get("perguntas", [])])
    razao = razao_compressao(resumo, fonte)

    cond = {
        "comprimiu": L["compressao_min"] <= razao <= L["compressao_max"],
        "sem_numero_inventado": not n_inv,
        "sem_entidade_inventada": not e_inv,
        "cobriu": cob_n == 0 or cob_ok / cob_n >= L["cobertura_min"],
        "respondeu": qa_n == 0 or qa_ok / qa_n >= L["qa_min"],
    }
    return {
        "ok": all(cond.values()), "condicoes": cond, "razao_compressao": round(razao, 3),
        "numeros_inventados": n_inv, "entidades_inventadas": e_inv,
        "cobertura": [cob_ok, cob_n], "qa": [qa_ok, qa_n],
    }
