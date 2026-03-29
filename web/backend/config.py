"""Configuration management for GeoPipeAgent Web UI."""
import json
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # GeoPipeAgent root
DATA_DIR = BASE_DIR / "data"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
PIPELINES_DIR = DATA_DIR / "pipelines"
EXTERNAL_SKILLS_DIR = DATA_DIR / "external_skills"
LLM_CONFIG_FILE = DATA_DIR / "llm_config.json"

# Ensure directories exist
for d in [DATA_DIR, CONVERSATIONS_DIR, PIPELINES_DIR, EXTERNAL_SKILLS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_LLM_CONFIG = {
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4096,
    "system_prompt_extra": "",
}


def get_llm_config() -> dict:
    """Load LLM configuration from file."""
    if LLM_CONFIG_FILE.exists():
        with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_LLM_CONFIG, **json.load(f)}
    return DEFAULT_LLM_CONFIG.copy()


def save_llm_config(config: dict) -> None:
    """Save LLM configuration to file."""
    with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def mask_api_key(key: str) -> str:
    """Mask API key for safe display."""
    if not key or len(key) < 8:
        return "***"
    return key[:3] + "..." + key[-4:]
