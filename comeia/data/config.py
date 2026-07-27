"""Configuração central do pipeline de dados PT-BR (Fase 2).

Todos os scripts de `data/` importam daqui. Manter as decisões num só lugar.
"""

import os
from pathlib import Path

# --- Caminhos -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent


def load_dotenv() -> None:
    """Carrega ROOT/.env em os.environ (sem sobrescrever o que já existe).

    Evita ter que repetir a chave em cada comando. O .env está no .gitignore —
    NUNCA versionar. Formato: UMA_VAR=valor por linha, # para comentário.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_dotenv()
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EVAL_DIR = ROOT / "eval"

SFT_OUT = PROCESSED_DIR / "sft_ptbr.jsonl"
PREF_OUT = PROCESSED_DIR / "preferences_ptbr.jsonl"

# --- Professores permitidos (REGRA DURA do projeto) ---------------------------
# Só modelos ABERTOS cuja licença permite redistribuir as saídas.
# NUNCA usar GPT / Claude / Gemini como professor: os ToS proíbem treinar modelo
# concorrente com as saídas, e isso contamina a licença do nosso release aberto.
#
# IDs no formato do OpenRouter (é a API que chamamos). Todos aparecem sob o filtro
# "Distillable" do OpenRouter — ou seja, o provedor permite destilação.
# Verificado em 2026-07-23. Preços por 1M tokens (entrada/saída).
# Todos VERIFICADOS contra a API do OpenRouter em 2026-07-23 (rode 00_check_teachers.py).
# Preços por 1M tokens; "pares/$10" assume 150 tok entrada + 700 saída por par.
ALLOWED_TEACHERS = {
    # === GRATUITOS (custo $0, mas com rate limit) ===
    # ⭐ 550B MoE frontier-reasoning, contexto 1M. O teacher mais forte a custo zero.
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    # 120B MoE (12B ativos), 262K. Alternativa free mais rápida.
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.0-flash:free",

    # === PAGOS BARATOS (sem rate limit — para volume) ===
    # ⭐ padrão: 284B MoE, 13B ativos, contexto 1M. $0,098/$0,196 → ~65.800 pares/$10
    "deepseek/deepseek-v4-flash",
    # mesma família do nosso base (consistência de estilo). $0,10/$0,15
    "qwen/qwen3.5-9b",
    # 1M de contexto, muito barato. $0,065/$0,26
    "qwen/qwen3.5-flash-02-23",
    "qwen/qwen3-32b",                    # $0,08/$0,28
    "mistralai/mistral-nemo",            # 12B Apache-2.0, PT explícito. $0,019/$0,03

    # === PAGOS PREMIUM (para um subconjunto pequeno de alta qualidade) ===
    "deepseek/deepseek-v4-pro",          # 1,6T total / 49B ativos. ~14.800 pares/$10
    "deepseek/deepseek-v3.2",
    "qwen/qwen3.5-397b-a17b",
    "qwen/qwen3.7-max",
}
FORBIDDEN_TEACHER_MARKERS = ("gpt-", "claude", "gemini", "o1", "o3", "openai", "anthropic")

# Professor padrão: melhor relação custo/qualidade para gerar volume.
# ~$0,00014 por par (150 tok entrada + ~700 saída) → US$10 rendem ~35-70 mil pares.
DEFAULT_TEACHER = "deepseek/deepseek-v4-flash"

# --- Modelo alvo --------------------------------------------------------------
# Qwen3.5-4B: Apache-2.0, 262K de contexto (extensível a 1M), 201 idiomas, multimodal.
# Existe também a variante `-Base` (sem pós-treino) se quisermos partir do zero de instrução.
BASE_MODEL = "Qwen/Qwen3.5-4B"         # loop local (8 GB VRAM)
BASE_MODEL_RAW = "Qwen/Qwen3.5-4B-Base"
SCALE_MODEL = "Qwen/Qwen3.5-9B"        # ao escalar para cloud

# --- Parâmetros de qualidade --------------------------------------------------
MIN_RESPONSE_CHARS = 40         # respostas curtas demais viram ruído
MAX_RESPONSE_CHARS = 8000
MIN_PT_RATIO = 0.85             # fração mínima de "portuguesidade" (heurística)
NEAR_DUP_THRESHOLD = 0.85       # similaridade de n-gramas para dedup
DECONTAM_NGRAM = 13             # n-grama usado para detectar vazamento de benchmark


def assert_teacher_allowed(model_id: str) -> None:
    """Falha alto e cedo se alguém tentar destilar de um professor proibido."""
    low = model_id.lower()
    for marker in FORBIDDEN_TEACHER_MARKERS:
        if marker in low:
            raise ValueError(
                f"Professor proibido: {model_id!r}. Saidas de modelos fechados "
                "(GPT/Claude/Gemini) nao podem treinar nosso modelo aberto — "
                "viola ToS e contamina a licenca. Use um professor aberto."
            )
    if model_id not in ALLOWED_TEACHERS:
        raise ValueError(
            f"Professor {model_id!r} nao esta em ALLOWED_TEACHERS. "
            "Confirme a licenca antes de adicionar."
        )


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
