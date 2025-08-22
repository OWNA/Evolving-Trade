"""High-level evolution interface."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alphaevolve.evolution.controller import Controller
from alphaevolve.store.sqlite import ProgramStore
from alphaevolve.config import settings

__all__ = ["AlphaEvolve", "Strategy"]


@dataclass
class Strategy:
    """Simple container for strategy code and metrics."""

    id: str
    code: str
    metrics: dict[str, Any]


class AlphaEvolve:
    """Convenience wrapper for running the evolution loop."""

    def __init__(
        self,
        initial_program_paths: list[str],
        *,
        store: ProgramStore | None = None,
        experiment_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.initial_program_paths = [Path(p) for p in initial_program_paths]
        if store is not None:
            self.store = store
        else:
            if experiment_name:
                base = Path(settings.sqlite_db).expanduser()
                db_path = base.parent / f"{experiment_name}.db"
                self.store = ProgramStore(db_path=db_path)
            else:
                self.store = ProgramStore()

        self.controllers = [
            Controller(
                self.store,
                initial_program_paths=self.initial_program_paths,
                metric=None,
                api_key=api_key,
            )
        ]

    async def run(self, iterations: int = 1) -> Strategy:
        """Run the evolution loop for a fixed number of iterations."""
        for _ in range(iterations):
            for ctrl in self.controllers:
                await ctrl._spawn(None)  # type: ignore[attr-defined]
                await asyncio.sleep(0.01)
        best = self.store.top_k(k=1)
        if not best:
            raise RuntimeError("No strategies generated")
        row = best[0]
        return Strategy(id=row["id"], code=row["code"], metrics=row["metrics"])
