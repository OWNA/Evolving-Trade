import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Provide a minimal `alphaevolve.config` to avoid importing the full package
dummy_pkg = types.ModuleType("alphaevolve")
config_mod = types.ModuleType("alphaevolve.config")

class DummySettings:
    sqlite_db = ":memory:"
    population_size = 1000
    archive_size = 100
    num_islands = 5

config_mod.settings = DummySettings()
sys.modules.setdefault("alphaevolve", dummy_pkg)
sys.modules["alphaevolve.config"] = config_mod

spec = importlib.util.spec_from_file_location(
    "sqlite_store", ROOT / "alphaevolve/store/sqlite.py"
)
store_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store_mod)
ProgramStore = store_mod.ProgramStore


def test_program_store_insert_and_get(tmp_path):
    db_file = tmp_path / "db.sqlite"
    store = ProgramStore(db_file, population_size=10, archive_size=0, num_islands=1)
    prog_id = store.insert("print('hi')", metrics={"sharpe": 1.0}, parent_id=None, island=0)
    row = store.get(prog_id)
    assert row["code"] == "print('hi')"
    assert row["metrics"]["sharpe"] == 1.0
    assert row["parent_id"] is None
    sampled = store.sample(prog_id)
    assert sampled["id"] == prog_id


def test_program_store_prune_population_size(tmp_path):
    db_file = tmp_path / "db.sqlite"
    store = ProgramStore(db_file, population_size=2, archive_size=0, num_islands=1)
    ids = [store.insert(f"code {i}") for i in range(3)]
    assert store._count() == 2
    existing = {pid for pid in ids if store.get(pid) is not None}
    assert len(existing) == 2
