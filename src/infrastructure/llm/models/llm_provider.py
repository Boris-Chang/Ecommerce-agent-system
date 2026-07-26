from __future__ import annotations

import logging
import os

from langchain.chat_models import init_chat_model
from langchain_deepseek import ChatDeepSeek


DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

logger = logging.getLogger(__name__)


def detect_llm_provider() -> str:
    provider = (
        os.getenv("LLM_PROVIDER")
        or os.getenv("AGENT_PROVIDER")
        or ""
    ).strip().lower()
    if provider:
        return provider
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "deepseek"


def build_llm():
    """Build the configured chat model without making a network call."""
    provider = detect_llm_provider()

    if provider == "deepseek":
        model_name = (
            os.getenv("LLM_MODEL")
            or os.getenv("AGENT_MODEL")
            or DEFAULT_DEEPSEEK_MODEL
        )
        if model_name.startswith("deepseek:"):
            model_name = model_name.removeprefix("deepseek:")
        logger.info(
            "llm_provider_selected provider=deepseek model=%s",
            model_name,
        )
        return ChatDeepSeek(model=model_name, temperature=0)

    if provider == "openai":
        model_name = (
            os.getenv("LLM_MODEL")
            or os.getenv("AGENT_MODEL")
            or DEFAULT_OPENAI_MODEL
        )
        if ":" not in model_name:
            model_name = f"openai:{model_name}"
        logger.info(
            "llm_provider_selected provider=openai model=%s",
            model_name,
        )
        return init_chat_model(model_name, temperature=0)

    raise ValueError("LLM_PROVIDER must be either 'deepseek' or 'openai'.")
