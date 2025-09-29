import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _setup(tmp_path, messages_holder):
    os.environ.setdefault("OPENAI_API_KEY", "x")
    installed = []

    yaml_mod = types.ModuleType("yaml")
    yaml_mod.safe_load = lambda *a, **kw: {}
    sys.modules["yaml"] = yaml_mod
    installed.append(("yaml", None))
    for name in ["pandas", "numpy", "pwb_toolbox", "pwb_toolbox.datasets", "tqdm"]:
        sys.modules[name] = types.ModuleType(name)
        installed.append((name, None))

    bt_mod = types.ModuleType("backtrader")
    bt_mod.Strategy = type("Strategy", (), {})
    sys.modules["backtrader"] = bt_mod
    installed.append(("backtrader", None))

    examples_pkg = types.ModuleType("examples")
    examples_cfg = types.ModuleType("examples.config")
    examples_cfg.HOF_METRIC = "sharpe"
    examples_pkg.config = examples_cfg
    sys.modules["examples"] = examples_pkg
    sys.modules["examples.config"] = examples_cfg
    installed.extend([("examples", None), ("examples.config", None)])

    config_mod = types.ModuleType("alphaevolve.config")
    config_mod.settings = types.SimpleNamespace(
        sqlite_db=str(tmp_path / "prog.sqlite"),
        prompt_sqlite_db=str(tmp_path / "prompt.sqlite"),
        population_size=5,
        archive_size=0,
        num_islands=1,
        elite_selection_ratio=0.1,
        exploration_ratio=0.2,
        exploitation_ratio=0.7,
        prompt_population_size=5,
        prompt_mutation_rate=1.0,
        prompt_iterations=1,
        llm_backend="openai",
    )
    sys.modules["alphaevolve.config"] = config_mod
    installed.append(("alphaevolve.config", None))

    alpha_pkg = types.ModuleType("alphaevolve")
    alpha_pkg.__path__ = []
    sys.modules["alphaevolve"] = alpha_pkg
    installed.append(("alphaevolve", None))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        installed.append((name, None))
        return mod

    patch_mod = load(
        "alphaevolve.evolution.patching",
        ROOT / "alphaevolve/evolution/patching.py",
    )
    sqlite_mod = load(
        "alphaevolve.store.sqlite",
        ROOT / "alphaevolve/store/sqlite.py",
    )
    store_pkg = types.ModuleType("alphaevolve.store")
    store_pkg.__path__ = []
    store_pkg.sqlite = sqlite_mod
    sys.modules["alphaevolve.store"] = store_pkg
    installed.append(("alphaevolve.store", None))
    ga_mod = load(
        "alphaevolve.evolution.prompt_ga",
        ROOT / "alphaevolve/evolution/prompt_ga.py",
    )
    prompts_mod = load(
        "alphaevolve.llm_engine.prompts",
        ROOT / "alphaevolve/llm_engine/prompts.py",
    )

    store_mod = load(
        "alphaevolve.store.prompt_sqlite",
        ROOT / "alphaevolve/store/prompt_sqlite.py",
    )
    load("alphaevolve.store.sqlite", ROOT / "alphaevolve/store/sqlite.py")
    evaluator_mod = types.ModuleType("alphaevolve.evaluator.backtest")

    async def evaluate(code, *, symbols=None):
        return {"sharpe": 0.0}

    evaluator_mod.evaluate = evaluate
    sys.modules["alphaevolve.evaluator.backtest"] = evaluator_mod
    installed.append(("alphaevolve.evaluator.backtest", None))

    base_file = tmp_path / "base.py"
    base_file.write_text("class BaseLoggingStrategy:\n    def next(self):\n        pass\n")
    spec_base = importlib.util.spec_from_file_location("alphaevolve.strategies.base", base_file)
    base_mod = importlib.util.module_from_spec(spec_base)
    spec_base.loader.exec_module(base_mod)
    sys.modules["alphaevolve.strategies.base"] = base_mod
    installed.append(("alphaevolve.strategies.base", None))

    client = types.SimpleNamespace()

    async def chat(messages, **kw):
        messages_holder.append(messages)
        return types.SimpleNamespace(content='{"code": "pass"}')

    client.chat = chat
    llm_pkg = types.ModuleType("alphaevolve.llm_engine")
    llm_pkg.__path__ = []
    llm_pkg.prompts = prompts_mod
    llm_pkg.client = client
    sys.modules["alphaevolve.llm_engine"] = llm_pkg
    installed.append(("alphaevolve.llm_engine", None))

    controller_mod = load(
        "alphaevolve.evolution.controller",
        ROOT / "alphaevolve/evolution/controller.py",
    )

    store_pkg.prompt_sqlite = store_mod

    evolution_pkg = types.ModuleType("alphaevolve.evolution")
    evolution_pkg.__path__ = []
    evolution_pkg.patching = patch_mod
    evolution_pkg.prompt_ga = ga_mod
    sys.modules["alphaevolve.evolution"] = evolution_pkg
    installed.append(("alphaevolve.evolution", None))

    alpha_pkg = types.ModuleType("alphaevolve")
    alpha_pkg.__path__ = []
    alpha_pkg.llm_engine = llm_pkg
    alpha_pkg.store = store_pkg
    alpha_pkg.evolution = evolution_pkg
    alpha_pkg.config = config_mod
    alpha_pkg.evaluator = evaluator_mod
    sys.modules["alphaevolve"] = alpha_pkg
    installed.append(("alphaevolve", None))

    return (
        ga_mod.PromptGenome,
        ga_mod.mutate,
        store_mod.PromptStore,
        controller_mod.Controller,
        installed,
    )


def _cleanup(installed):
    for name, prev in installed:
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev


async def _run_spawn(ctrl, prompt):
    await ctrl._spawn(None, prompt=prompt)


def test_controller_uses_custom_prompt(tmp_path):
    messages = []
    (
        PromptGenome,
        mutate,
        PromptStore,
        Controller,
        installed,
    ) = _setup(tmp_path, messages)
    try:
        prog_store = importlib.import_module("alphaevolve.store.sqlite").ProgramStore
        ctrl = Controller(
            prog_store(
                tmp_path / "db.sqlite",
                population_size=2,
                archive_size=0,
                num_islands=1,
            ),
            max_concurrency=1,
        )
        prompt = PromptGenome("SYS", "USER: {today}")
        asyncio.run(_run_spawn(ctrl, prompt))
        assert messages[0][0]["content"] == "SYS"
    finally:
        _cleanup(installed)


def test_prompt_store_insert_get(tmp_path):
    messages = []
    (
        PromptGenome,
        mutate,
        PromptStore,
        Controller,
        installed,
    ) = _setup(tmp_path, messages)
    try:
        store = PromptStore(tmp_path / "p.sqlite", population_size=2, archive_size=0)
        prompt = PromptGenome("a", "b")
        pid = store.insert(prompt, metrics={"sharpe": 1.0})
        row = store.get(pid)
        assert row["metrics"]["sharpe"] == 1.0
    finally:
        _cleanup(installed)


def test_mutate_changes_prompt(tmp_path):
    messages = []
    (
        PromptGenome,
        mutate,
        PromptStore,
        Controller,
        installed,
    ) = _setup(tmp_path, messages)
    try:
        p = PromptGenome("hello world", "line")
        m = mutate(p, rate=1.0)
        assert m.system_msg != p.system_msg or m.user_template != p.user_template
    finally:
        _cleanup(installed)
