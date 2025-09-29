"""Example configuration values for AlphaEvolve."""

# Default comma-separated tickers for evaluations
DEFAULT_SYMBOLS_RAW = "SPY,EFA,IEF,VNQ,GSG"

# Historical data start date
START_DATE = "1990-01-01"

# Metric used to rank strategies in the hall of fame
HOF_METRIC = "calmar"

# Convenience parsed tuple of symbols
DEFAULT_SYMBOLS = tuple(s.strip().upper() for s in DEFAULT_SYMBOLS_RAW.split(',') if s.strip())

"""Runtime settings for optional features."""

# Enable genetic prompt evolution when True.
ENABLE_PROMPT_EVOLUTION = False

# Runtime flags for examples and demos
# Enable multi-branch mutation to run separate evolutionary flows optimizing
# different metrics.
MULTI_BRANCH_MUTATION = False

# Metrics used when MULTI_BRANCH_MUTATION is enabled
BRANCH_METRICS = ["sharpe", "calmar", "cagr"]
