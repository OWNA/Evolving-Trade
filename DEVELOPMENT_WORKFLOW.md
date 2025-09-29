# Development Workflow Guide

This document outlines the recommended development workflow for the AlphaEvolve project, designed to maximize productivity while maintaining code quality and experiment tracking.

## 🏗️ Project Structure Overview

```
alphaevolve/
├── alphaevolve/          # Core trading system (version controlled)
├── experiments/          # Local experiment databases (NOT in git)
├── scripts/              # CLI tools and GUI
├── examples/             # Strategy templates and configs
├── tests/                # Unit tests
└── _legacy/             # Archived code
```

## 🔄 Recommended Workflow

### 1. **Local Development (Primary)**

**Why Local?**
- ⚡ Fast strategy iteration and backtesting
- 🔍 Full IDE support with debugging
- 💾 Persistent experiment databases
- 🚀 No network delays during development

**Setup:**
```bash
# Ensure you're in the project directory
cd C:\Users\simon\pwb-alphaevolve

# Create and activate virtual environment (if not done)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install in editable mode
pip install -e .
```

### 2. **Branching Strategy**

Use **Git Flow** approach with feature branches:

```bash
# For new strategies
git checkout -b feature/momentum-volatility-strategy

# For experiments and research
git checkout -b experiment/high-frequency-signals  

# For bug fixes
git checkout -b bugfix/backtester-slippage-issue

# For documentation updates
git checkout -b docs/strategy-performance-analysis
```

### 3. **Daily Development Cycle**

```bash
# 1. Start new feature/experiment
git checkout -b experiment/new-imbalance-metric
git push -u evolving-trade experiment/new-imbalance-metric

# 2. Develop locally
# - Edit strategy files in alphaevolve/strategies/
# - Run experiments (databases stay local)
# - Test with: python scripts/run_example.py --experiment test_run

# 3. Commit meaningful progress
git add alphaevolve/strategies/new_strategy.py
git commit -m "feat: add volume-weighted imbalance metric

- Implements VWAP-based order book imbalance
- Tested on AAPL 1-min data
- Initial Sharpe: 1.2, needs optimization"

# 4. Push regularly
git push
```

### 4. **Experiment Management**

**Local Experiments (Recommended):**
```bash
# Run experiments locally - databases stay on your machine
python scripts/run_example.py --experiment momentum_test
python scripts/gui.py  # Use GUI for monitoring

# Experiment databases are in ~/.alphaevolve/ (excluded from git)
```

**Document Results in Code:**
```python
# In your strategy file, document key findings:
"""
Strategy: Momentum + Volatility Adaptive
Performance Summary (2020-2024 backtest):
- Sharpe Ratio: 1.8
- Max Drawdown: 12%
- Win Rate: 58%
- Best on: High volatility periods
- Avoid: Low volume days
"""
```

## 🚀 Integration with GitHub

### **Pull Request Workflow**

```bash
# When ready to merge feature
git checkout main
git pull evolving-trade main
git checkout feature/your-feature
git rebase main  # Clean up history
git push
# Create PR on GitHub
```

### **What to Commit vs. Keep Local**

**✅ Commit to GitHub:**
- Strategy code (`alphaevolve/strategies/`)
- Configuration updates
- Documentation and README updates
- Test files
- Script improvements
- Performance summaries in comments

**❌ Keep Local (excluded by .gitignore):**
- Experiment databases (`experiments/`)
- Virtual environment (`.venv/`)
- Cache files (`__pycache__/`)
- Personal API keys
- Large backtest data files

## 📊 Strategy Development Best Practices

### **1. Strategy Development Cycle**

```bash
# Create strategy branch
git checkout -b feature/rsi-momentum-combo

# Develop strategy
# 1. Create strategy file: alphaevolve/strategies/rsi_momentum.py
# 2. Add to examples: examples/rsi_momentum_config.py
# 3. Test locally: python scripts/run_example.py --experiment rsi_test
# 4. Iterate and optimize

# Document and commit
git add alphaevolve/strategies/rsi_momentum.py examples/rsi_momentum_config.py
git commit -m "feat: implement RSI-momentum combination strategy

Key Features:
- RSI(14) + SMA(20) momentum filter
- Dynamic position sizing based on volatility
- Stop-loss at 2% / Take-profit at 4%

Backtest Results (SPY 2020-2024):
- Sharpe Ratio: 1.6
- Max Drawdown: 8%
- Total Return: 124%"

git push
```

### **2. Performance Tracking**

Create performance summaries in your strategy files:

```python
# At the top of each strategy file
"""
PERFORMANCE SUMMARY
==================
Strategy: RSI Momentum Combination
Tested: 2024-01-15
Dataset: SPY 1-min, 2020-2024

Results:
- Sharpe Ratio: 1.6
- Max Drawdown: 8%
- Win Rate: 62%
- Avg Trade Duration: 4.2 hours

Notes:
- Performs best during trending markets
- Struggles in sideways/choppy conditions
- Consider adding volatility filter

Next Steps:
- Test on other assets (QQQ, IWM)
- Add volatility regime filter
- Optimize RSI period (test 10, 14, 21)
"""
```

## 🔧 Development Tools Setup

### **IDE Configuration**
```bash
# VS Code settings (recommended)
# Install extensions:
# - Python
# - Git Graph
# - GitLens
# - Jupyter

# Configure Python interpreter to use .venv
```

### **Git Hooks (Optional)**
```bash
# Install pre-commit hooks for code quality
pip install pre-commit
pre-commit install

# This will run black, ruff on each commit
```

## 🎯 Branch Naming Conventions

| Branch Type | Prefix | Example | Purpose |
|-------------|--------|---------|---------|
| New Strategy | `feature/` | `feature/lstm-price-prediction` | New trading strategies |
| Experiments | `experiment/` | `experiment/high-freq-signals` | Research and testing |
| Bug Fixes | `bugfix/` | `bugfix/backtest-slippage` | Fix issues |
| Documentation | `docs/` | `docs/strategy-guide` | Documentation updates |
| Hotfixes | `hotfix/` | `hotfix/critical-data-bug` | Urgent production fixes |

## 📈 Release Management

### **Tagging Successful Strategies**
```bash
# When you have a proven strategy, tag it
git tag -a v1.0-momentum-strategy -m "Momentum strategy - Sharpe 1.8"
git push evolving-trade --tags
```

### **Creating Releases**
Use GitHub releases to mark major milestones:
- New strategy categories
- Performance improvements
- Major feature additions

## 🤝 Collaboration Guidelines

If working with others:

1. **Always create PRs** - no direct pushes to main
2. **Code review required** - at least one approval
3. **Strategy documentation** - include performance metrics
4. **Test coverage** - add tests for new strategies
5. **Experiment isolation** - use separate experiment names

## 🔍 Debugging and Troubleshooting

### **Common Issues**
```bash
# Experiment database locked
rm ~/.alphaevolve/your_experiment.db

# Dependencies issues
pip install -e . --force-reinstall

# Git conflicts during rebase
git rebase --abort
git merge main  # Use merge instead
```

### **Performance Monitoring**
```bash
# Monitor strategy performance
python scripts/gui.py  # Real-time dashboard

# Analyze experiment results
python -c "
from alphaevolve.store.sqlite import SQLiteStore
store = SQLiteStore('your_experiment')
df = store.get_hall_of_fame()
print(df.head())
"
```

## 📚 Additional Resources

- **Strategy Examples**: See `examples/` directory
- **API Documentation**: Run `python -m pydoc alphaevolve`
- **Testing**: `pytest tests/`
- **Performance Analysis**: Use Streamlit GUI for visualization

---

**Remember**: Keep experiments local, commit strategy code, document performance, and use branches for all development!
