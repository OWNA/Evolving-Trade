from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Abstract base class for all LLM backends."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kw) -> Any:
        """Return the LLM response for a list of chat ``messages``."""
        raise NotImplementedError
