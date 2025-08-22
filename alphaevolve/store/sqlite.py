"""
Tiny persistence layer for *programs* and their KPI metrics.

Schema
------
programs(id TEXT PK,
         code TEXT NOT NULL,
         parent_id TEXT,
         metrics TEXT,           -- JSON string (nullable until eval completed)
         created REAL,           -- Unix seconds
         island INTEGER)
"""

import os, sqlite3, uuid, json, time, random
from pathlib import Path
from typing import Optional, Dict, Any, List

from alphaevolve.config import settings


class ProgramStore:
    def __init__(
        self,
        db_path: str | os.PathLike = settings.sqlite_db,
        *,
        population_size: int = settings.population_size,
        archive_size: int = settings.archive_size,
        num_islands: int = settings.num_islands,
    ):
        db_path = Path(db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.population_size = population_size
        self.archive_size = archive_size
        self.num_islands = num_islands
        self.conn = sqlite3.connect(
            db_path, check_same_thread=False, isolation_level=None  # autocommit
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS programs(
                 id TEXT PRIMARY KEY,
                 code TEXT NOT NULL,
                 parent_id TEXT,
                 metrics TEXT,
                 created REAL,
                 island INTEGER
               )"""
        )

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    # -------------------------------------------------------------- #
    # basic CRUD
    # -------------------------------------------------------------- #
    def insert(
        self,
        code: str,
        metrics: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        prog_id: Optional[str] = None,
        *,
        island: Optional[int] = None,
    ) -> str:
        prog_id = prog_id or str(uuid.uuid4())
        island = island if island is not None else random.randrange(self.num_islands)
        self.conn.execute(
            "INSERT INTO programs(id, code, parent_id, metrics, created, island) VALUES (?,?,?,?,?,?)",
            (
                prog_id,
                code,
                parent_id,
                json.dumps(metrics) if metrics is not None else None,
                time.time(),
                island,
            ),
        )
        self._prune()
        return prog_id

    def update_metrics(self, prog_id: str, metrics: Dict[str, Any]) -> None:
        self.conn.execute(
            "UPDATE programs SET metrics=? WHERE id=?",
            (json.dumps(metrics), prog_id),
        )

    def get(self, prog_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM programs WHERE id=?", (prog_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def sample(
        self,
        prog_id: Optional[str] = None,
        *,
        island: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if prog_id:
            return self.get(prog_id)
        if island is None:
            cur = self.conn.execute(
                "SELECT * FROM programs ORDER BY RANDOM() LIMIT 1"
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM programs WHERE island=? ORDER BY RANDOM() LIMIT 1",
                (island,),
            )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def top_k(
        self, k: int = 5, metric: str = "sharpe"
    ) -> List[Dict[str, Any]]:
        query = f"""
            SELECT * FROM programs
            WHERE metrics IS NOT NULL
            ORDER BY CAST(json_extract(metrics, '$.{metric}') AS REAL) DESC
            LIMIT ?
        """
        cur = self.conn.execute(query, (k,))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------- #
    # helpers
    # -------------------------------------------------------------- #
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        (
            prog_id,
            code,
            parent_id,
            metrics_json,
            created,
            island,
        ) = row
        return {
            "id": prog_id,
            "code": code,
            "parent_id": parent_id,
            "metrics": json.loads(metrics_json) if metrics_json else None,
            "created": created,
            "island": island,
        }

    # -------------------------------------------------------------- #
    # pruning helpers
    # -------------------------------------------------------------- #
    def _count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM programs")
        return cur.fetchone()[0]

    def _prune(self) -> None:
        """Ensure population does not exceed configured size."""
        count = self._count()
        if count <= self.population_size:
            return
        # Keep archive of top performers
        elite_ids = {r["id"] for r in self.top_k(k=self.archive_size)}
        if elite_ids:
            placeholders = ','.join('?' * len(elite_ids))
            cur = self.conn.execute(
                f"SELECT id FROM programs WHERE id NOT IN ({placeholders})",
                tuple(elite_ids),
            )
        else:
            cur = self.conn.execute("SELECT id FROM programs")
        candidates = [row[0] for row in cur.fetchall()]
        excess = count - self.population_size
        for prog_id in random.sample(candidates, min(excess, len(candidates))):
            self.conn.execute("DELETE FROM programs WHERE id=?", (prog_id,))
