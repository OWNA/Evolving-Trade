"""Async evolution controller.

High‑level loop:
1. Choose a *parent* strategy (elite or random) from `ProgramStore`.
2. Build prompt, call OpenAI → JSON diff/full code.
3. Apply patch ⇒ child code.
4. Evaluate back‑test KPIs.
5. Insert child into store (which updates MAP‑Elites grid).
"""

import asyncio
import inspect
import json
import logging
import random
import textwrap
from collections.abc import Sequence
from pathlib import Path

from alphaevolve.config import settings
from alphaevolve.evaluator.backtest import evaluate
from alphaevolve.evolution.patching import apply_patch
from alphaevolve.evolution.prompt_ga import PromptGenome
from alphaevolve.llm_engine import _load_client
from alphaevolve.llm_engine import prompts
from alphaevolve.store.sqlite import ProgramStore

logger = logging.getLogger(__name__)


class Controller:
    def __init__(
        self,
        store: ProgramStore,
        *,
        initial_program_paths: Sequence[str | Path] | None = None,
        metric: str | None = None,
        max_concurrency: int = 4,
        prompt: PromptGenome | None = None,
        api_key: str | None = None,
    ):
        self.store = store
        self.sem = asyncio.Semaphore(max_concurrency)
        self.initial_program_paths = [Path(p) for p in initial_program_paths or []]
        self.prompt = prompt or PromptGenome(prompts.SYSTEM_MSG, prompts.USER_TEMPLATE)
        self.metric = metric or "calmar"
        self._ensure_seed_population()
        self.llm_client = _load_client(api_key=api_key)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _ensure_seed_population(self):
        """If DB empty, insert seed strategies w/out metrics (lazy eval)."""
        if self.store._count() > 0:
            return  # already seeded

        # Use the HFT imbalance strategy as the initial seed
        seed_path = Path(__file__).resolve().parent.parent.parent / "examples" / "hft_imbalance.py"
        try:
            code = seed_path.read_text()
        except Exception as e:
            logger.error(f"Failed to read seed program {seed_path}: {e}")
            return
            
        self.store.insert(
            textwrap.dedent(code),
            metrics=None,
            parent_id=None,
            island=0,
        )
        logger.info("Seed HFT strategy inserted into store.")

    def _select_parent(self, parent_id: str | None):
        if parent_id:
            return self.store.get(parent_id)
        r = random.random()
        if r < settings.elite_selection_ratio:
            elites = self.store.top_k(k=settings.archive_size, metric=self.metric)
            return random.choice(elites) if elites else self.store.sample()
        r -= settings.elite_selection_ratio
        if r < settings.exploitation_ratio:
            best = self.store.top_k(k=1, metric=self.metric)
            return best[0] if best else self.store.sample()
        r -= settings.exploitation_ratio
        if r < settings.exploration_ratio:
            island = random.randrange(settings.num_islands)
            return self.store.sample(island=island)
        return self.store.sample()

    async def _spawn(self, parent_id: str | None, *, prompt: PromptGenome | None = None):
        """Generate, evaluate & store one child strategy."""
        prompt = prompt or self.prompt
        async with self.sem:
            # 1) Select parent
            parent = self._select_parent(parent_id)
            if parent is None:
                logger.warning("No parent found; skipping spawn.")
                return

            # 2) Build prompt & call OpenAI
            messages = prompts.build(parent, self.store, metric=self.metric, prompt=prompt)
            try:
                msg = await self.llm_client.chat(messages)
                child_code = msg.content
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return

            # 3) Evaluate
            try:
                # The LLM's response is the full code, no patching needed
                kpis = await evaluate(child_code)
            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                return

            # 4) Persist
            self.store.insert(
                child_code,
                kpis,
                parent_id=parent["id"],
                island=parent.get("island", 0),
            )
            logger.info("Child stored (%s %.2f)", self.metric, kpis.get(self.metric, 0))

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    async def run_forever(self):
        """Continuous evolution loop (no termination)."""
        while True:
            await self._spawn(None, prompt=self.prompt)
            # Optional: back‑off to be polite to API limits when concurrency=1
            await asyncio.sleep(0.01)

    async def run(self, iterations: int) -> None:
        """Run the evolution loop for a fixed number of iterations."""
        for _ in range(iterations):
            await self._spawn(None, prompt=self.prompt)
            await asyncio.sleep(0.01)
