"""Async local LLM client used when ``LLM_BACKEND`` is ``local``.

This implementation supports two operating modes:

1. If ``LOCAL_SERVER_URL`` is configured, requests are forwarded to an
   OpenAI-compatible server using ``openai.AsyncOpenAI``.
2. Otherwise a local HuggingFace model is loaded via ``transformers.pipeline``
   for text generation.

Both modes return an object with a ``content`` attribute matching the
:class:`openai.types.chat.chat_completion_message.ChatCompletionMessage`
interface used by :mod:`openai_client`.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from alphaevolve.config import settings

from .base_client import LLMClient


class LocalClient(LLMClient):
    """Concrete :class:`LLMClient` for local models."""

    def __init__(self) -> None:
        self.server_url = settings.local_server_url
        self.model_name = settings.local_model_name
        self.model_path = settings.local_model_path
        if self.server_url:
            import openai

            # API key is ignored by many local servers but required by the client
            self._client = openai.AsyncOpenAI(base_url=self.server_url, api_key="x")
        else:
            from transformers import pipeline

            model = self.model_path or self.model_name or "gpt2"
            self._pipeline = pipeline("text-generation", model=model)

    async def chat(self, messages: list[dict[str, str]], **kw) -> Any:
        """Return the LLM response for a list of ``messages``."""
        if self.server_url:
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": settings.max_completion_tokens,
            }
            params.update(kw)
            completion = await self._client.chat.completions.create(**params)
            return completion.choices[0].message

        prompt = "\n".join(m["content"] for m in messages)
        max_tokens = kw.get("max_new_tokens", settings.max_completion_tokens)

        def _run() -> str:
            result = self._pipeline(prompt, max_new_tokens=max_tokens)
            return result[0]["generated_text"]

        generated = await asyncio.to_thread(_run)
        return SimpleNamespace(content=generated)
