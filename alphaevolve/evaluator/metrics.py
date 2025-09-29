"""
Common performance-metric helpers (numpy-friendly, no external deps).
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any


def _to_np(arr):
    if isinstance(arr, (pd.Series | pd.DataFrame)):
        arr = arr.values
    return np.asarray(arr, dtype=float)


# ------------------------------------------------------------------ #
# METRICS FROM TRADES
# ------------------------------------------------------------------ #
def trade_log_to_returns(trades: List[Dict[str, Any]]) -> pd.Series:
    """Converts a list of trades into a series of daily returns."""
    if len(trades) < 2:
        return pd.Series(dtype=float)
        
    trade_df = pd.DataFrame(trades)
    trade_df['pnl'] = np.where(trade_df['type'] == 'buy', -trade_df['price'] * trade_df['size'], trade_df['price'] * trade_df['size'])
    
    # This is a simplified PnL calculation. A more robust implementation would
    # account for open/close of positions. For now, we'll use a simple daily sum.
    daily_pnl = trade_df.set_index('timestamp')['pnl'].resample('D').sum()
    
    # Assume a constant portfolio value for calculating returns, as we don't have
    # a full equity curve. This is an approximation.
    initial_equity = 100_000
    daily_equity = initial_equity + daily_pnl.cumsum()
    
    return daily_equity.pct_change().dropna()


def cagr_from_trades(trades: List[Dict[str, Any]], initial_equity: float = 100_000) -> float:
    """Calculates CAGR from a trade log."""
    if not trades:
        return 0.0
        
    trade_df = pd.DataFrame(trades)
    start_date = trade_df['timestamp'].min()
    end_date = trade_df['timestamp'].max()
    
    pnl = np.where(trade_df['type'] == 'buy', -trade_df['price'] * trade_df['size'], trade_df['price'] * trade_df['size']).sum()
    final_equity = initial_equity + pnl
    
    n_seconds = (end_date - start_date).total_seconds()
    if n_seconds < 1:
        return 0.0
    n_years = n_seconds / (365.25 * 24 * 60 * 60)
    
    return (final_equity / initial_equity) ** (1 / n_years) - 1 if n_years > 0 else 0.0


def calculate_metrics_from_trades(trades: List[Dict[str, Any]], initial_equity: float = 100_000) -> Dict[str, Any]:
    """Calculates a full suite of performance metrics from a trade log."""
    if len(trades) < 2:
        return {
            "total_return": 0.0, "cagr": 0.0, "sharpe": 0.0,
            "max_drawdown": 0.0, "calmar": 0.0, "num_trades": len(trades),
        }

    trade_df = pd.DataFrame(trades)
    trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
    trade_df.set_index('timestamp', inplace=True)
    
    trade_df['pnl'] = np.where(trade_df['type'] == 'buy', -trade_df['price'] * trade_df['size'], trade_df['price'] * trade_df['size'])
    
    equity_curve = initial_equity + trade_df['pnl'].cumsum()
    
    # --- Robust Metrics Calculation ---
    total_return = equity_curve.iloc[-1] / initial_equity - 1
    
    start_date = equity_curve.index.min()
    end_date = equity_curve.index.max()
    n_seconds = (end_date - start_date).total_seconds()
    n_years = n_seconds / (365.25 * 24 * 60 * 60) if n_seconds > 1 else 0

    cagr = (equity_curve.iloc[-1] / initial_equity) ** (1 / n_years) - 1 if n_years > 0 else 0.0

    daily_returns = equity_curve.resample('D').last().pct_change().dropna()
    
    if len(daily_returns) > 1 and daily_returns.std() != 0:
        # Annualize from daily returns, requires at least 2 days of trades
        if len(daily_returns) < 2:
            sharpe_ratio = 0.0
        else:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365.25)
    else:
        sharpe_ratio = 0.0

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_dd = drawdown.min()

    calmar_ratio = cagr / abs(max_dd) if max_dd != 0 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe_ratio,
        "max_drawdown": max_dd,
        "calmar": calmar_ratio,
        "num_trades": len(trades),
    }

# ------------------------------------------------------------------ #
# LEGACY METRICS (from equity curve) - Keep for now
# ------------------------------------------------------------------ #
def daily_returns(equity_curve: pd.Series) -> pd.Series:
    return equity_curve.pct_change().dropna()


def cagr(equity_curve: pd.Series) -> float:
    """Calculates CAGR for a high-frequency equity curve."""
    if len(equity_curve) < 2:
        return 0.0
        
    start_val = equity_curve.iloc[0]
    end_val = equity_curve.iloc[-1]
    
    start_date = equity_curve.index.min()
    end_date = equity_curve.index.max()
    
    n_seconds = (end_date - start_date).total_seconds()
    if n_seconds < 1:
        return 0.0
    n_years = n_seconds / (365.25 * 24 * 60 * 60)
    
    return (end_val / start_val) ** (1 / n_years) - 1 if n_years > 0 else 0.0


def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    """Calculates annualized Sharpe ratio for high-frequency returns."""
    if len(returns) < 2:
        return 0.0
    
    # Calculate annualized sharpe
    n_seconds = (returns.index.max() - returns.index.min()).total_seconds()
    if n_seconds < 1:
        return 0.0
    n_years = n_seconds / (365.25 * 24 * 60 * 60)
        
    periods_per_year = len(returns) / n_years if n_years > 0 else 0
    if periods_per_year == 0:
        return 0.0

    excess_returns = returns - rf / periods_per_year
    std = excess_returns.std(ddof=1)
    if std == 0 or np.isnan(std):
        return 0.0
        
    return np.sqrt(periods_per_year) * excess_returns.mean() / std


def max_drawdown(equity_curve: pd.Series) -> float:
    """Return *percentage* max drawdown (negative value)."""
    cummax = equity_curve.cummax()
    dd = (equity_curve - cummax) / cummax
    return dd.min()


def calmar(cagr_: float, mdd: float) -> float:
    return cagr_ / abs(mdd) if mdd != 0 else 0
