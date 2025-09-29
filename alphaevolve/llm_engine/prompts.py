"""
Generate chat messages to prompt an LLM to create a high-frequency trading
strategy based on Level 2 order book data.
"""
import textwrap
from datetime import datetime
from typing import Any

from alphaevolve.evolution.prompt_ga import PromptGenome
from alphaevolve.store.sqlite import ProgramStore

SYSTEM_MSG = """\
You are Alpha-Trader Evolution-Engine. Your task is to write a high-frequency
trading strategy in Python. The strategy will operate on tick-level order book
data for a single cryptocurrency pair (e.g., BTCUSDT).

You must implement a Python class that inherits from `HFTStrategy`. This base
class provides an `on_tick(self, tick, backtester)` method, which your strategy
must implement.

The `tick` object is a pandas Series representing a single snapshot of the
order book. It contains the following relevant columns:
- `asks[0].price`, `asks[0].amount`, `asks[1].price`, ... `asks[49].amount`
- `bids[0].price`, `bids[0].amount`, `bids[1].price`, ... `bids[49].amount`

The `backtester` object provides two methods to execute trades:
- `backtester.buy(size: float)`: Executes a market buy order.
- `backtester.sell(size: float)`: Executes a market sell order.

Your goal is to generate a strategy that identifies order book imbalances to
make trading decisions. You should consider entry/exit logic, position sizing,
and risk management. The objective is to maximize the Sharpe ratio, Calmar
ratio, and CAGR.

**Return ONLY valid Python code** for the full strategy class. Do NOT include
any markdown, prose explanation, or any other text outside of the code.
"""

USER_TEMPLATE = """\
Today's date: {today}

Parent Strategy Performance (KPIs):
{metrics_tbl}

Parent Strategy Code:
```python
{parent_code}
```

Hall-of-Fame (Top {k} strategies by {metric}):
{hof}

Your Task:
1.  Mutate the parent strategy to create a new, improved version. The goal is
    to find a better strategy for trading on order book imbalances.
2.  Focus on improving the risk-adjusted returns (Sharpe and Calmar).
3.  You can modify any part of the strategy: the imbalance calculation, the
    entry/exit thresholds, position sizing, risk management logic, etc.
4.  Your response must be a single, complete Python code block containing the
    full strategy class definition.
"""

def _format_metrics(metrics: dict[str, Any] | None) -> str:
    if not metrics:
        return "  (N/A - This is a seed strategy)"
    return "\n".join(f"  {k}: {v:.4g}" for k, v in metrics.items())

def _format_hof(store: ProgramStore, k: int = 3, *, metric: str = "sharpe") -> str:
    rows = store.top_k(k=k, metric=metric)
    if not rows:
        return "  (The Hall of Fame is currently empty)"
    lines = []
    for r in rows:
        m = r["metrics"]
        lines.append(
            f"  Sharpe {m['sharpe']:.3f} | Calmar {m['calmar']:.3f} | "
            f"CAGR {m['cagr']:.2%}"
        )
    return "\n".join(lines)

def build(
    parent: dict[str, Any] | None,
    store: ProgramStore,
    metric: str = "sharpe",
    prompt: PromptGenome | None = None,
) -> list[dict[str, str]]:
    """Return messages list ready for the LLM."""
    prompt = prompt or PromptGenome(system_msg=SYSTEM_MSG, user_template=USER_TEMPLATE)
    today = datetime.utcnow().date().isoformat()
    
    parent_code = textwrap.dedent(parent["code"] if parent else "")
    
    user_msg = prompt.user_template.format(
        today=today,
        metrics_tbl=_format_metrics(parent["metrics"] if parent else None),
        parent_code=parent_code or "(No parent, this is the first generation)",
        hof=_format_hof(store, k=3, metric=metric),
        k=3,
        metric=metric,
    )
    return [
        {"role": "system", "content": prompt.system_msg},
        {"role": "user", "content": user_msg},
    ]
