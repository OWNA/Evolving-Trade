"""Utilities for evolving prompts using a simple genetic algorithm."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from alphaevolve.config import settings
from alphaevolve.store.sqlite import ProgramStore

if TYPE_CHECKING:
    from alphaevolve.store.prompt_sqlite import PromptStore


@dataclass
class PromptGenome:
    system_msg: str
    user_template: str


# --------------------------------------------------------------
# Genetic operators
# --------------------------------------------------------------


def mutate(prompt: PromptGenome, rate: float | None = None) -> PromptGenome:
    """Return a slightly mutated copy of the prompt."""
    rate = rate if rate is not None else settings.prompt_mutation_rate
    system_msg = prompt.system_msg
    user_template = prompt.user_template

    if random.random() < rate:
        parts = system_msg.split()
        if parts:
            idx = random.randrange(len(parts))
            parts[idx] = parts[idx].upper()
            system_msg = " ".join(parts)

    if random.random() < rate:
        lines = user_template.splitlines()
        if lines:
            idx = random.randrange(len(lines))
            lines[idx] = lines[idx] + " !"
            user_template = "\n".join(lines)

    return PromptGenome(system_msg=system_msg, user_template=user_template)


def crossover(a: PromptGenome, b: PromptGenome) -> PromptGenome:
    """Combine two parents into a child prompt."""
    system_msg = random.choice([a.system_msg, b.system_msg])
    user_template = random.choice([a.user_template, b.user_template])
    return PromptGenome(system_msg=system_msg, user_template=user_template)


# --------------------------------------------------------------
# Evaluation loop
# --------------------------------------------------------------


async def evaluate_prompt(
    prompt: PromptGenome,
    iterations: int | None = None,
    *,
    program_store: ProgramStore | None = None,
) -> dict[str, Any]:
    """Evaluate prompt fitness by running a short evolution cycle."""
    iterations = iterations if iterations is not None else settings.prompt_iterations
    from alphaevolve.evolution.controller import Controller

    store = program_store or ProgramStore(
        sqlite_db=":memory:", population_size=10, archive_size=0, num_islands=1
    )
    ctrl = Controller(store, initial_program_paths=[], max_concurrency=1)
    for _ in range(iterations):
        await ctrl._spawn(None, prompt=prompt)
        await asyncio.sleep(0.01)
    top = store.top_k(k=1)
    if top:
        return top[0]["metrics"] or {}
    return {}


async def evolve_prompts(store: PromptStore, generations: int = 1) -> None:
    """High-level GA loop producing new prompts and storing them."""
    from alphaevolve.llm_engine import prompts

    for _ in range(generations):
        parents = store.sample_pair()
        if parents:
            child = crossover(*parents)
        else:
            base = store.sample_prompt()
            if base is None:
                base = PromptGenome(prompts.SYSTEM_MSG, prompts.USER_TEMPLATE)
            child = base
        child = mutate(child)
        metrics = await evaluate_prompt(child, iterations=settings.prompt_iterations)
        store.insert(child, metrics)
