import importlib

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

spec = importlib.util.spec_from_file_location(
    "metrics", "alphaevolve/evaluator/metrics.py"
)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_sharpe_short_series_returns_zero():
    assert metrics.sharpe(np.array([0.01])) == 0.0


def test_max_drawdown():
    curve = np.array([100, 120, 80, 130], dtype=float)
    series = pd.Series(curve)
    assert metrics.max_drawdown(series) == pytest.approx(-1 / 3)


def test_cagr_simple_case():
    curve = pd.Series([1.0, 2.0])
    result = metrics.cagr(curve, periods_per_year=1)
    assert result == pytest.approx(np.sqrt(2) - 1)
