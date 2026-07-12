from __future__ import annotations

import os

from langchain.chat_models import init_chat_model
from langchain_deepseek import ChatDeepSeek

DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

def _detect_provider() -> str:
    provider = os.getenv("AGENT_PROVIDER", "").strip().lower()
    if provider:
        return provider
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "deepseek"


def _build_model():
    provider = _detect_provider()

    if provider == "deepseek":
        model_name = os.getenv("AGENT_MODEL", DEFAULT_DEEPSEEK_MODEL)
        if model_name.startswith("deepseek:"):
            model_name = model_name.removeprefix("deepseek:")
        return ChatDeepSeek(model=model_name, temperature=0)
        # return init_chat_model(model=model_name, temperature=0.2, timeout=60,  max_retries=2)

    if provider == "openai":
        model_name = os.getenv("AGENT_MODEL", DEFAULT_OPENAI_MODEL)
        if ":" not in model_name:
            model_name = f"openai:{model_name}"
        return init_chat_model(model_name)

    raise ValueError("AGENT_PROVIDER must be either 'deepseek' or 'openai'.")