"""LLM clients — DeepSeek (primary), OpenRouter optional fallback."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def _secret(name: str) -> str | None:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            value = str(st.secrets[name]).strip()
            if _is_real_key(value):
                return value
    except Exception:
        pass

    value = os.getenv(name, "").strip()
    if _is_real_key(value):
        return value
    return None


def _is_real_key(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered.startswith("your_"):
        return False
    if "your_real" in lowered or "your_key" in lowered or "your_deepseek" in lowered:
        return False
    if value in {"sk-or-your_real_key", "sk-your_deepseek_key"}:
        return False
    return True


def get_fast_llm() -> ChatOpenAI:
    """Fast model for CV parsing — DeepSeek."""
    deepseek = _secret("DEEPSEEK_API_KEY")
    if not deepseek:
        raise RuntimeError(
            "Set DEEPSEEK_API_KEY in .streamlit/secrets.toml"
        )
    return ChatOpenAI(
        api_key=deepseek,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0.1,
    )


def get_reasoner_llm() -> ChatOpenAI:
    """Reasoning model for scoring — DeepSeek, then OpenRouter."""
    deepseek = _secret("DEEPSEEK_API_KEY")
    if deepseek:
        return ChatOpenAI(
            api_key=deepseek,
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            temperature=0.2,
        )

    openrouter = _secret("OPENROUTER_API_KEY")
    if openrouter:
        return ChatOpenAI(
            api_key=openrouter,
            base_url="https://openrouter.ai/api/v1",
            model="openai/gpt-4o-mini",
            temperature=0.2,
            default_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "Job Matching Agent",
            },
        )

    raise RuntimeError(
        "Set DEEPSEEK_API_KEY (preferred) or OPENROUTER_API_KEY in .streamlit/secrets.toml"
    )
