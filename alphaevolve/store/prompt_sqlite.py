"""SQLite persistence for prompt genomes."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from alphaevolve.config import settings
from alphaevolve.evolution.prompt_ga import PromptGenome
from examples import config as example_config


class PromptStore:
    def __init__(
        self,
        db_path: str | os.PathLike = None,
        *,
        population_size: int = settings.prompt_population_size,
        archive_size: int = settings.archive_size,
    ) -> None:
        db_path = (
            Path(db_path)
            if db_path is not None
            else Path(settings.sqlite_db).with_name("prompts.db")
        )
        db_path = db_path.expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.population_size = population_size
        self.archive_size = archive_size
        self.conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS prompts(
                 id TEXT PRIMARY KEY,
                 system_msg TEXT NOT NULL,
                 user_template TEXT NOT NULL,
                 metrics TEXT,
                 created REAL
               )"""
        )

    # --------------------------------------------------------------
    # basic CRUD
    # --------------------------------------------------------------
    def insert(
        self,
        prompt: PromptGenome,
        metrics: dict[str, Any] | None = None,
        prompt_id: str | None = None,
    ) -> str:
        prompt_id = prompt_id or str(uuid.uuid4())
        self.conn.execute(
            (
                "INSERT INTO prompts(id, system_msg, user_template, metrics, created)"
                " VALUES (?,?,?,?,?)"
            ),
            (
                prompt_id,
                prompt.system_msg,
                prompt.user_template,
                json.dumps(metrics) if metrics is not None else None,
                time.time(),
            ),
        )
        self._prune()
        return prompt_id

    def update_metrics(self, prompt_id: str, metrics: dict[str, Any]) -> None:
        self.conn.execute(
            "UPDATE prompts SET metrics=? WHERE id=?",
            (json.dumps(metrics), prompt_id),
        )

    def get(self, prompt_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM prompts WHERE id=?", (prompt_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def sample_prompt(self) -> PromptGenome | None:
        cur = self.conn.execute("SELECT * FROM prompts ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        data = self._row_to_dict(row)
        return PromptGenome(data["system_msg"], data["user_template"])

    def sample_pair(self) -> tuple[PromptGenome, PromptGenome] | None:
        cur = self.conn.execute("SELECT * FROM prompts ORDER BY RANDOM() LIMIT 2")
        rows = cur.fetchall()
        if len(rows) < 2:
            return None
        data = [self._row_to_dict(r) for r in rows]
        return (
            PromptGenome(data[0]["system_msg"], data[0]["user_template"]),
            PromptGenome(data[1]["system_msg"], data[1]["user_template"]),
        )

    def top_k(self, k: int = 5, metric: str = example_config.HOF_METRIC) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM prompts WHERE metrics IS NOT NULL")
        rows = [self._row_to_dict(r) for r in cur.fetchall()]
        rows.sort(key=lambda r: r["metrics"].get(metric, 0.0), reverse=True)
        return rows[:k]

    # --------------------------------------------------------------
    # helpers
    # --------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        (
            prompt_id,
            system_msg,
            user_template,
            metrics_json,
            created,
        ) = row
        return {
            "id": prompt_id,
            "system_msg": system_msg,
            "user_template": user_template,
            "metrics": json.loads(metrics_json) if metrics_json else None,
            "created": created,
        }

    # --------------------------------------------------------------
    # pruning helpers
    # --------------------------------------------------------------
    def _count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM prompts")
        return cur.fetchone()[0]

    def _prune(self) -> None:
        count = self._count()
        if count <= self.population_size:
            return
        elite_ids = {r["id"] for r in self.top_k(k=self.archive_size)}
        if elite_ids:
            placeholders = ",".join("?" * len(elite_ids))
            cur = self.conn.execute(
                f"SELECT id FROM prompts WHERE id NOT IN ({placeholders})",
                tuple(elite_ids),
            )
        else:
            cur = self.conn.execute("SELECT id FROM prompts")
        candidates = [row[0] for row in cur.fetchall()]
        excess = count - self.population_size
        for pid in random.sample(candidates, min(excess, len(candidates))):
            self.conn.execute("DELETE FROM prompts WHERE id=?", (pid,))
