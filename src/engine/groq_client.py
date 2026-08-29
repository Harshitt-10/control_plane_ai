"""
Shared Groq API client factory.

Both the ai_judge tier and chat_pipeline used to each maintain their own
module-level _CLIENT singleton. This module centralises that pattern to avoid
duplication and keep client configuration in one place.
"""
from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_CLIENT: Groq | None = None


def get_groq_client() -> Groq | None:
    """Return a shared Groq client, or None if no API key is configured."""
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        _CLIENT = Groq(
            api_key=api_key,
            http_client=httpx.Client(trust_env=False, timeout=30.0),
        )
    return _CLIENT
