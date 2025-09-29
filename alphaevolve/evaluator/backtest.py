"""
Evaluation engine for high-frequency, event-driven strategies.
"""
import asyncio
import importlib.util
import sys
import tempfile
import types
from functools import partial
from pathlib import Path
from typing import Any, Dict
import logging

import pandas as pd
import numpy as np

from alphaevolve.config import settings
from alphaevolve.evaluator.hft_backtester import HFTBacktester
from alphaevolve.strategies.hft_base import HFTStrategy
from alphaevolve.evaluator import metrics as mt

def _load_module_from_code(code: str, name: str | None = None) -> types.ModuleType:
    """Create a temporary module from a source code string."""
    name = name or f"strategy_{hash(code)}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    spec = importlib.util.spec_from_file_location(name, tmp_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore
    tmp_path.unlink(missing_ok=True)
    return mod

def _find_strategy_class(mod: types.ModuleType) -> type[HFTStrategy]:
    """Finds the HFTStrategy subclass in a module."""
    for name, obj in mod.__dict__.items():
        if isinstance(obj, type) and issubclass(obj, HFTStrategy) and obj is not HFTStrategy:
            return obj
    raise ValueError("No HFTStrategy subclass found in the provided code.")

def _run_hft_backtest(strategy_class: type[HFTStrategy]) -> Dict[str, Any]:
    """Runs a single HFT backtest and returns performance KPIs."""
    if not settings.local_data_path:
        raise ValueError("local_data_path must be set for HFT backtesting.")
    
    data = pd.read_parquet(settings.local_data_path)
    # This is the definitive fix: ensure the DataFrame has a DatetimeIndex.
    if 'timestamp' in data.columns:
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
    
    strategy_instance = strategy_class()
    backtester = HFTBacktester(data, strategy_instance)
    
    backtester.run()
    
    kpis = mt.calculate_metrics_from_trades(backtester.trades, backtester.initial_cash)
    return kpis

def evaluate_sync(code: str) -> Dict[str, Any]:
    """Blocking evaluation for a single HFT strategy."""
    mod = _load_module_from_code(code)
    strategy_class = _find_strategy_class(mod)
    return _run_hft_backtest(strategy_class)

async def evaluate(code: str) -> Dict[str, Any]:
    """Async wrapper for the HFT evaluation."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(evaluate_sync, code))
