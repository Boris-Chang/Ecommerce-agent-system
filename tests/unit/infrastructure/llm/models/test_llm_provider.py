from infrastructure.llm.models import llm_provider


def test_llm_provider_prefers_new_configuration(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("AGENT_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "gpt-4.1-mini")
    monkeypatch.setattr(
        llm_provider,
        "init_chat_model",
        lambda model_name, **kwargs: (model_name, kwargs),
    )

    model_name, kwargs = llm_provider.build_llm()

    assert model_name == "openai:gpt-4.1-mini"
    assert kwargs == {"temperature": 0}


def test_llm_provider_keeps_legacy_env_fallback(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("AGENT_PROVIDER", "deepseek")
    monkeypatch.setenv("AGENT_MODEL", "deepseek:legacy-model")
    monkeypatch.setattr(
        llm_provider,
        "ChatDeepSeek",
        lambda **kwargs: kwargs,
    )

    model = llm_provider.build_llm()

    assert model == {"model": "legacy-model", "temperature": 0}


def test_deepseek_default_supports_agent_tool_calling(monkeypatch) -> None:
    for name in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "AGENT_PROVIDER",
        "AGENT_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-for-test")
    monkeypatch.setattr(
        llm_provider,
        "ChatDeepSeek",
        lambda **kwargs: kwargs,
    )

    model = llm_provider.build_llm()

    assert model == {"model": "deepseek-chat", "temperature": 0}
