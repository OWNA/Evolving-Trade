import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _install(name: str, module: types.ModuleType, installed: list[tuple[str, object]]):
    prev = sys.modules.get(name)
    sys.modules[name] = module
    installed.append((name, prev))


def _cleanup(installed):
    for name, prev in installed:
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev


def test_alphaevolve_multi_branch_creates_controllers():
    installed: list[tuple[str, object]] = []

    # stub ProgramStore
    store_mod = types.ModuleType("alphaevolve.store.sqlite")

    class DummyStore:
        def __init__(self, *a, **kw):
            pass

    store_mod.ProgramStore = DummyStore
    _install("alphaevolve.store.sqlite", store_mod, installed)

    store_pkg = types.ModuleType("alphaevolve.store")
    store_pkg.__path__ = []
    store_pkg.sqlite = store_mod
    _install("alphaevolve.store", store_pkg, installed)

    # stub Controller
    ctrl_mod = types.ModuleType("alphaevolve.evolution.controller")

    class DummyController:
        def __init__(self, store, *, initial_program_paths=None, metric=None, max_concurrency=4):
            self.metric = metric

    ctrl_mod.Controller = DummyController
    _install("alphaevolve.evolution.controller", ctrl_mod, installed)

    evo_pkg = types.ModuleType("alphaevolve.evolution")
    evo_pkg.__path__ = []
    evo_pkg.controller = ctrl_mod
    _install("alphaevolve.evolution", evo_pkg, installed)

    # stub example config
    ex_cfg = types.ModuleType("examples.config")
    ex_cfg.MULTI_BRANCH_MUTATION = True
    ex_cfg.BRANCH_METRICS = ["a", "b"]
    ex_pkg = types.ModuleType("examples")
    ex_pkg.config = ex_cfg
    _install("examples", ex_pkg, installed)
    _install("examples.config", ex_cfg, installed)

    try:
        spec = importlib.util.spec_from_file_location(
            "alphaevolve.engine", ROOT / "alphaevolve/engine.py"
        )
        engine = importlib.util.module_from_spec(spec)
        _install("alphaevolve.engine", engine, installed)
        spec.loader.exec_module(engine)

        ae = engine.AlphaEvolve(["foo.py"])
        assert len(ae.controllers) == 2
        assert [c.metric for c in ae.controllers] == ["a", "b"]
    finally:
        _cleanup(installed)
