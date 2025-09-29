import asyncio
import importlib.util
import os
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


def _setup_controller(tmp_path, diff_content, metrics, population_size=5):
    installed = []
    os.environ.setdefault("OPENAI_API_KEY", "x")

    # basic stubs for heavy deps
    yaml_mod = types.ModuleType("yaml")
    yaml_mod.safe_load = lambda *a, **kw: {}
    _install("yaml", yaml_mod, installed)
    for name in ["pandas", "numpy", "pwb_toolbox", "pwb_toolbox.datasets", "tqdm"]:
        _install(name, types.ModuleType(name), installed)

    bt_mod = types.ModuleType("backtrader")
    bt_mod.Strategy = type("Strategy", (), {})
    _install("backtrader", bt_mod, installed)

    # stub examples.config used by ProgramStore
    examples_pkg = types.ModuleType("examples")
    examples_cfg = types.ModuleType("examples.config")
    examples_cfg.HOF_METRIC = "sharpe"
    examples_pkg.config = examples_cfg
    _install("examples", examples_pkg, installed)
    _install("examples.config", examples_cfg, installed)

    # config stub
    config_mod = types.ModuleType("alphaevolve.config")
    config_mod.settings = types.SimpleNamespace(
        sqlite_db=":memory:",
        population_size=population_size,
        archive_size=0,
        num_islands=1,
        elite_selection_ratio=0.1,
        exploration_ratio=0.2,
        exploitation_ratio=0.7,
        llm_backend="openai",
    )
    _install("alphaevolve.config", config_mod, installed)

    # real modules loaded from source files
    def load_mod(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        _install(name, mod, installed)
        return mod

    store_mod = load_mod(
        "alphaevolve.store.sqlite",
        ROOT / "alphaevolve/store/sqlite.py",
    )
    patch_mod = load_mod(
        "alphaevolve.evolution.patching",
        ROOT / "alphaevolve/evolution/patching.py",
    )
    prompt_ga_mod = load_mod(
        "alphaevolve.evolution.prompt_ga",
        ROOT / "alphaevolve/evolution/prompt_ga.py",
    )
    prompts_mod = load_mod(
        "alphaevolve.llm_engine.prompts",
        ROOT / "alphaevolve/llm_engine/prompts.py",
    )

    # stubs that depend on runtime values
    client = types.SimpleNamespace()

    async def chat(messages, **kw):
        return types.SimpleNamespace(content=diff_content)

    client.chat = chat

    evaluator_mod = types.ModuleType("alphaevolve.evaluator.backtest")
    # ensure metrics include keys used by prompts._format_hof
    base_metrics = {"sharpe": 0.0, "calmar": 0.0, "cagr": 0.0}
    base_metrics.update(metrics)

    async def evaluate(code, *, symbols=None):
        return base_metrics

    evaluator_mod.evaluate = evaluate
    _install("alphaevolve.evaluator.backtest", evaluator_mod, installed)

    base_file = tmp_path / "base.py"
    base_file.write_text("class BaseLoggingStrategy:\n    def next(self):\n        pass\n")
    spec_base = importlib.util.spec_from_file_location("alphaevolve.strategies.base", base_file)
    base_mod = importlib.util.module_from_spec(spec_base)
    spec_base.loader.exec_module(base_mod)
    _install("alphaevolve.strategies.base", base_mod, installed)

    # package containers
    llm_pkg = types.ModuleType("alphaevolve.llm_engine")
    llm_pkg.__path__ = []
    llm_pkg.prompts = prompts_mod
    llm_pkg.client = client
    _install("alphaevolve.llm_engine", llm_pkg, installed)

    store_pkg = types.ModuleType("alphaevolve.store")
    store_pkg.__path__ = []
    store_pkg.sqlite = store_mod
    _install("alphaevolve.store", store_pkg, installed)

    evolution_pkg = types.ModuleType("alphaevolve.evolution")
    evolution_pkg.__path__ = []
    evolution_pkg.patching = patch_mod
    evolution_pkg.prompt_ga = prompt_ga_mod
    _install("alphaevolve.evolution", evolution_pkg, installed)

    strat_pkg = types.ModuleType("alphaevolve.strategies")
    strat_pkg.__path__ = []
    strat_pkg.base = base_mod
    _install("alphaevolve.strategies", strat_pkg, installed)

    alpha_pkg = types.ModuleType("alphaevolve")
    alpha_pkg.__path__ = []
    alpha_pkg.llm_engine = llm_pkg
    alpha_pkg.store = store_pkg
    alpha_pkg.evolution = evolution_pkg
    alpha_pkg.strategies = strat_pkg
    alpha_pkg.config = config_mod
    alpha_pkg.evaluator = types.ModuleType("alphaevolve.evaluator")
    alpha_pkg.evaluator.backtest = evaluator_mod
    _install("alphaevolve", alpha_pkg, installed)

    ctrl_mod = load_mod(
        "alphaevolve.evolution.controller",
        ROOT / "alphaevolve/evolution/controller.py",
    )
    Controller = ctrl_mod.Controller
    ProgramStore = ctrl_mod.ProgramStore

    store = ProgramStore(
        tmp_path / "db.sqlite",
        population_size=population_size,
        archive_size=0,
        num_islands=1,
    )
    seed_code = (
        "def foo():\n"
        "    # === EVOLVE-BLOCK: logic ===\n"
        "    a = 1\n"
        "    # === END EVOLVE-BLOCK ===\n"
    )
    seed_path = tmp_path / "seed.py"
    seed_path.write_text(seed_code)

    ctrl = Controller(store, initial_program_paths=[str(seed_path)], max_concurrency=1)
    return ctrl, store, installed


async def _run_spawn(ctrl):
    await ctrl._spawn(None)


def test_controller_spawn_adds_child(tmp_path):
    diff = '{"blocks": {"logic": "b = 2"}}'
    metrics = {"sharpe": 1.0}
    ctrl, store, installed = _setup_controller(tmp_path, diff, metrics)
    try:
        asyncio.run(_run_spawn(ctrl))
        assert store._count() == 2
        child = store.top_k(k=1)[0]
        assert "b = 2" in child["code"]
    finally:
        _cleanup(installed)


def test_controller_stores_metrics(tmp_path):
    diff = '{"code": "print(42)"}'
    metrics = {"sharpe": 2.5, "calmar": 1.1}
    ctrl, store, installed = _setup_controller(tmp_path, diff, metrics)
    try:
        asyncio.run(_run_spawn(ctrl))
        child = list(store.top_k(k=1))[0]
        for k, v in metrics.items():
            assert child["metrics"][k] == v
    finally:
        _cleanup(installed)


def test_controller_respects_population_limit(tmp_path):
    diff = '{"code": "print(0)"}'
    metrics = {"sharpe": 0.0}
    ctrl, store, installed = _setup_controller(tmp_path, diff, metrics, population_size=2)
    try:
        for _ in range(4):
            asyncio.run(_run_spawn(ctrl))
        assert store._count() <= 2
    finally:
        _cleanup(installed)
