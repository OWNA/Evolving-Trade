# Evolving Trade

> **Independent algorithmic trading system inspired by evolutionary principles**—this project leverages LLM-driven strategy evolution to discover and optimize profitable trading algorithms.

**Autonomously discovers and back‑tests high‑performing algorithmic‑trading strategies** using evolutionary LLM prompts, custom backtesting engine, and multiple data sources for YOUR personal trading development.

![CI](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

![AlphaEvolve](alphaevolve-run.png)

---

## 🚀 Quickstart

```bash
# Clone and install in editable mode
$ git clone https://github.com/OWNA/Evolving-Trade.git
$ cd Evolving-Trade
$ pip install -e .

# Set your OpenAI key (model "o3" required)
$ export OPENAI_API_KEY=sk-...
# Set your data source API keys as needed
$ export HF_ACCESS_TOKEN=hf_  # For Hugging Face datasets
$ export ALPHA_VANTAGE_API_KEY=your_key  # For market data
```

**Note**: This is an independent project for personal algorithmic trading development. You can use various data sources and adapt the strategies for your specific trading goals.

Launch and monitor an experiment entirely from the GUI:

```bash
$ streamlit run scripts/gui.py
```

The sidebar lets you paste a seed strategy, tune the options from
`examples/config.py` and pick the number of iterations. Click **Run evolution** to start
the search and watch the hall‑of‑fame table update live.

Alternatively you can launch the evolution controller (create a fresh experiment)

```bash
python scripts/run_example.py --experiment my_exp
```

### Managing experiments

Use the `--experiment` option to keep runs separate:

```bash
python scripts/run_example.py --experiment my_exp
```

This creates a new SQLite file `my_exp.db` under `~/.alphaevolve/`. The GUI lists all experiments, allowing you to switch between them or delete one via the **Delete experiment** sidebar button.

---

## ⚙️  Installation

> **Python ≥ 3.10** required.

```bash
pip install pwb-alphaevolve
```

Or install the bleeding‑edge version:

```bash
pip install git+https://github.com/OWNA/Evolving-Trade.git
```

### Core Dependencies

* [pwb-toolbox](https://github.com/paperswithbacktest/pwb-toolbox)
* [pwb-backtrader](https://github.com/paperswithbacktest/pwb-backtrader)
* openai ≥ 1.0 (structured output)
* tqdm, pandas, numpy, pydantic


(See `pyproject.toml` for the full list.)

---

## 🦙 Using Local LLMs

AlphaEvolve can operate without OpenAI by loading a HuggingFace model or by
forwarding requests to an OpenAI-compatible server. Install the optional
dependencies and download a model first:

```bash
pip install transformers accelerate bitsandbytes
huggingface-cli download microsoft/phi-2 --local-dir ~/.cache/phi-2
```

Configure the environment to use the local backend:

```bash
export LLM_BACKEND=local
export LOCAL_MODEL_PATH=~/.cache/phi-2  # or set LOCAL_MODEL_NAME
# LOCAL_SERVER_URL=http://localhost:8000  # optional OpenAI-style server
```

Run the evolution loop with the local model:

```bash
python scripts/run_example.py --experiment my_exp
```

---


## ✨ Key Features

| Layer      | Highlights                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------- |
| Data       | Zero‑setup loader for any Papers‑With‑Backtest dataset (`pwb_toolbox`) + caching to Feather |
| Strategies | Seed templates with **EVOLVE‑BLOCK** markers that the LLM mutates                           |
| Evaluator  | Deterministic Backtrader walk‑forward, JSON KPIs (Sharpe, CAGR, Calmar, DD)                 |
| LLM Engine | OpenAI o3 structured‑output chat → JSON diff/patch system                                   |
| Evolution  | Async controller, SQLite hall‑of‑fame, optional MAP‑Elites niches                           |
| Dashboard  | (optional) Streamlit live view of metrics & equity curves                                   |

---

## 📂 Project structure (high‑level)

```
alphaevolve/
├── engine.py      # convenience wrapper to run the evolution loop
├── evaluator/     # data loading, metrics & Backtrader evaluation
├── evolution/     # controller, patching, islands
├── llm_engine/    # prompt builder + OpenAI client
├── strategies/    # seed strategies (EVOLVE‑BLOCK markers)
└── store/         # SQLite persistence
scripts/           # CLI entry‑points
```

---

## Prompt Evolution

The `PromptGenome` dataclass allows the LLM instructions themselves to be
evolved using a genetic algorithm. Set `ENABLE_PROMPT_EVOLUTION = True` in
`examples/settings.py` to try this feature. New prompts are mutated, evaluated
for a few iterations and stored in a separate SQLite database.

---

## 🔄 Development Workflow

For detailed development guidelines, branching strategy, and best practices, see **[DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md)**.

**Quick Start for Contributors:**
```bash
# 1. Create feature branch
git checkout -b feature/your-strategy-name

# 2. Develop locally (experiments stay local)
python scripts/run_example.py --experiment test_run

# 3. Commit strategy code (not experiment databases)
git add alphaevolve/strategies/your_strategy.py
git commit -m "feat: add momentum-volatility strategy"

# 4. Push and create PR
git push -u origin feature/your-strategy-name
```

**Key Principles:**
- 🏠 **Develop locally** - Fast iteration, full IDE support
- 🌿 **Use branches** - Feature branches for all development  
- 📊 **Document performance** - Include backtest results in code comments
- 🚫 **Exclude experiments** - Database files stay local (in `.gitignore`)

---

## 🤝 Contributing

1. Read the [Development Workflow Guide](DEVELOPMENT_WORKFLOW.md)
2. Create your feature branch (`git checkout -b feature/new-strategy`)
3. Develop and test locally
4. Commit with descriptive messages including performance metrics
5. Push to the branch (`git push origin feature/new-strategy`)
6. Open a Pull Request with strategy documentation

Please run `black` + `ruff` before submitting.

---

## 📄 License

MIT © 2025 Contributors
