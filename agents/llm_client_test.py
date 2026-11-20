
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    base_url = os.getenv(
        "LLM_BASE_URL",
        "https://api.groq.com/openai/v1"
    ).strip()

    if not api_key or "YOUR_" in api_key:
        raise RuntimeError("Set GROQ_API_KEY in your .env file.")

    return OpenAI(
        api_key=api_key,
        base_url=base_url or None,
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "90")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
    )


def get_model_name() -> str:
    return os.getenv(
        "LLM_MODEL",
        "openai/gpt-oss-120b"
    ).strip()


def response_text(response) -> str:
    """Safely extract text from an OpenAI-compatible response."""

    content = response.choices[0].message.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))

        return "\n".join(parts).strip()

    return str(content or "").strip()
