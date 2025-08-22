"""LLM engine selection wrapper."""

from __future__ import annotations

from importlib import import_module

from alphaevolve.config import settings

from . import prompts  # re-export for convenience
from .base_client import LLMClient


def _load_client(api_key: str | None = None) -> LLMClient:
    backend = settings.llm_backend.lower()
    if backend == "openai":
        module = import_module("alphaevolve.llm_engine.openai_client")
        return module.OpenAIClient(api_key=api_key)  # type: ignore[no-any-return]
    if backend == "local":
        module = import_module("alphaevolve.llm_engine.local_client")
        return module.LocalClient()  # type: ignore[no-any-return]
    raise ValueError(f"Unknown LLM backend: {settings.llm_backend}")


client: LLMClient | None = None

__all__ = ["prompts", "client", "LLMClient", "_load_client"]
