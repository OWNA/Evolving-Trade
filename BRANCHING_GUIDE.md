# Git Branching Quick Reference

## 🌿 Branch Setup Commands

### **Create and Switch to New Branch**
```bash
# For new strategies
git checkout -b feature/lstm-price-prediction
git checkout -b feature/mean-reversion-strategy
git checkout -b feature/volatility-breakout

# For experiments and research
git checkout -b experiment/high-frequency-signals
git checkout -b experiment/crypto-momentum
git checkout -b experiment/options-strategies

# For improvements and fixes
git checkout -b improvement/backtester-performance
git checkout -b bugfix/data-loading-issue
git checkout -b docs/strategy-documentation
```

### **Daily Workflow Commands**
```bash
# 1. Start work on existing branch
git checkout feature/your-branch-name
git pull evolving-trade feature/your-branch-name

# 2. Make changes, then commit
git add .
git status  # Review what's being committed
git commit -m "feat: implement MACD crossover strategy

- Add MACD indicator with 12/26/9 parameters
- Include signal line crossover logic
- Backtested on SPY: Sharpe 1.4, DD 6%"

# 3. Push to GitHub
git push  # or git push -u evolving-trade feature/your-branch-name (first time)

# 4. When feature is complete, merge to main
git checkout main
git pull evolving-trade main
git merge feature/your-branch-name
git push evolving-trade main
git branch -d feature/your-branch-name  # Delete local branch
```

## 🎯 Branch Naming Examples

### **Strategy Development**
- `feature/momentum-mean-reversion`
- `feature/rsi-bollinger-combo`
- `feature/lstm-price-prediction`
- `feature/options-volatility-strategy`

### **System Improvements**
- `improvement/backtester-speed`
- `improvement/gui-performance-charts`
- `improvement/llm-prompt-optimization`

### **Experiments**
- `experiment/crypto-market-analysis`
- `experiment/intraday-patterns`
- `experiment/earnings-momentum`

### **Bug Fixes**
- `bugfix/data-loading-error`
- `bugfix/backtest-calculation`
- `bugfix/gui-display-issue`

## 🔄 Practical Examples

### **Example 1: New Strategy Development**
```bash
# Start new momentum strategy
git checkout -b feature/dual-momentum-strategy
git push -u evolving-trade feature/dual-momentum-strategy

# Create strategy file
# Edit: alphaevolve/strategies/dual_momentum.py
# Edit: examples/dual_momentum_config.py

# Test locally
python scripts/run_example.py --experiment dual_momentum_test

# Commit progress
git add alphaevolve/strategies/dual_momentum.py examples/dual_momentum_config.py
git commit -m "feat: implement dual momentum strategy

Strategy combines:
- 12-month absolute momentum
- 3-month relative momentum vs SPY
- Monthly rebalancing

Backtest Results (2010-2024):
- CAGR: 12.8%
- Sharpe: 1.2
- Max DD: 18%
- Beats SPY by 3.2% annually"

git push
```

### **Example 2: Bug Fix**
```bash
# Fix backtester issue
git checkout -b bugfix/slippage-calculation
git push -u evolving-trade bugfix/slippage-calculation

# Fix the issue
# Edit: alphaevolve/evaluator/backtest.py

# Test the fix
python -m pytest tests/test_backtest.py

# Commit fix
git add alphaevolve/evaluator/backtest.py
git commit -m "fix: correct slippage calculation in backtester

- Fixed percentage-based slippage calculation
- Was using notional instead of percentage
- Added unit test to prevent regression
- Affects all strategies using default slippage"

git push

# Merge quickly for critical fixes
git checkout main
git merge bugfix/slippage-calculation
git push evolving-trade main
```

### **Example 3: Experiment Documentation**
```bash
# Document experiment results
git checkout -b docs/q1-2024-experiment-results
git push -u evolving-trade docs/q1-2024-experiment-results

# Create documentation
# Edit: docs/Q1_2024_RESULTS.md
# Update: README.md with key findings

git add docs/ README.md
git commit -m "docs: add Q1 2024 experiment results

Key Findings:
- Momentum strategies outperformed in trending markets
- Mean reversion worked better during high volatility
- HFT strategies showed promise on liquid stocks
- Added performance comparison table"

git push
```

## 🔧 Useful Git Commands

### **Branch Management**
```bash
# List all branches
git branch -a

# Delete local branch
git branch -d feature/old-branch

# Delete remote branch
git push evolving-trade --delete feature/old-branch

# Rename current branch
git branch -m new-branch-name
```

### **Keeping Branches Updated**
```bash
# Update main and rebase your feature branch
git checkout main
git pull evolving-trade main
git checkout feature/your-branch
git rebase main  # Clean history
# OR
git merge main   # Preserve history
```

### **Viewing Changes**
```bash
# See what changed
git status
git diff
git log --oneline -10

# Compare branches
git diff main..feature/your-branch
```

## 🚀 Pro Tips

1. **Commit Often**: Small, focused commits are easier to review and debug
2. **Descriptive Messages**: Include strategy performance metrics in commit messages
3. **Test Before Committing**: Run backtests and tests locally first
4. **Keep Branches Focused**: One strategy or feature per branch
5. **Clean Up**: Delete merged branches to keep repository tidy

## ⚠️ Important Notes

- **Never commit experiment databases** - they're excluded in `.gitignore`
- **Always test locally first** - don't push broken code
- **Document performance** - include backtest results in commits
- **Use meaningful branch names** - make it clear what you're working on
- **Pull before pushing** - avoid conflicts by staying updated

---

For more detailed information, see [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)
