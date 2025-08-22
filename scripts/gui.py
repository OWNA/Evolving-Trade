#!/usr/bin/env python
"""Streamlit GUI to run and monitor AlphaEvolve HFT experiments."""
import asyncio
import os
import textwrap
from pathlib import Path
import gc
import time

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from alphaevolve import AlphaEvolve
from alphaevolve.config import settings
from alphaevolve.evaluator.backtest import evaluate_sync, _find_strategy_class, _load_module_from_code
from alphaevolve.evaluator.hft_backtester import HFTBacktester
from alphaevolve.store.sqlite import ProgramStore

st.set_page_config(page_title="AlphaEvolve HFT", layout="wide")
st.title("🧬 AlphaEvolve HFT")

# --- Sidebar controls ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
local_data_path = st.sidebar.text_input(
    "Local Data Path", value=r"C:\Users\simon\Downloads\lob_BTCUSDT_2024-11-27 4.parquet"
)
exp_name = st.sidebar.text_input("Experiment Name", value="hft_exp")
iterations = st.sidebar.number_input("Iterations", 1, 1000, 10, step=1)
TOP_K = st.sidebar.slider("Top K Strategies", 3, 50, 10)
hof_metric = st.sidebar.selectbox("Hall-of-Fame Metric", ["sharpe", "calmar", "cagr", "total_return", "max_drawdown"])

@st.cache_resource
def get_store(db_path):
    """Gets a cached ProgramStore instance."""
    return ProgramStore(db_path)

# --- DB Setup & UI Logic ---
DB_DIR = Path(settings.sqlite_db).expanduser().parent
DB_DIR.mkdir(parents=True, exist_ok=True)
db_path = DB_DIR / f"{exp_name}.db"

run_btn = st.sidebar.button("Run Evolution")

store = get_store(db_path)

progress_bar = st.sidebar.empty()
status_box = st.sidebar.empty()
table_placeholder = st.empty()

# --- Evolution Loop ---
if run_btn:
    if not api_key:
        st.sidebar.error("Please enter your OpenAI API Key.")
        st.stop()
    if not Path(local_data_path).exists():
        st.sidebar.error(f"Data file not found at: {local_data_path}")
        st.stop()

    settings.openai_api_key = api_key
    settings.local_data_path = local_data_path
    
    # The initial seed is now handled by the Controller, so we pass an empty list
    ae = AlphaEvolve([], experiment_name=exp_name, api_key=api_key)

    for i in range(int(iterations)):
        # We now run the controller's spawn method directly
        for ctrl in ae.controllers:
            asyncio.run(ctrl._spawn(None))
        progress_bar.progress((i + 1) / iterations)
        status_box.write(f"Iteration {i + 1}/{iterations}")
        
        hof_rows = store.top_k(k=TOP_K, metric=hof_metric)
        if hof_rows:
            table = pd.DataFrame(
                [
                    {
                        "id": r["id"],
                        "sharpe": r["metrics"].get("sharpe", 0),
                        "calmar": r["metrics"].get("calmar", 0),
                        "cagr": r["metrics"].get("cagr", 0),
                        "max-dd": r["metrics"].get("max_drawdown", 0),
                        "total-ret": r["metrics"].get("total_return", 0),
                    }
                    for r in hof_rows
                ]
            )
            table_placeholder.dataframe(table, use_container_width=True)
    status_box.write("Evolution finished.")

# --- Hall of Fame Display ---
hof_rows = store.top_k(k=TOP_K, metric=hof_metric)

if not hof_rows:
    st.info("Hall-of-Fame is empty – run an evolution to populate it.")
    st.stop()

table = pd.DataFrame(
    [
        {
            "id": r["id"],
            "sharpe": r["metrics"].get("sharpe", 0),
            "calmar": r["metrics"].get("calmar", 0),
            "cagr": r["metrics"].get("cagr", 0),
            "max-dd": r["metrics"].get("max_drawdown", 0),
            "total-ret": r["metrics"].get("total_return", 0),
        }
        for r in hof_rows
    ]
)
st.dataframe(table, use_container_width=True)

selected_id = st.selectbox("Select a program to inspect", table["id"].tolist())
selected = store.get(selected_id)

col_code, col_chart = st.columns([1, 1])

with col_code:
    st.subheader("Source Code")
    st.code(textwrap.dedent(selected["code"]))

with col_chart:
    st.subheader("Equity Curve (Fresh Backtest)")
    try:
        mod = _load_module_from_code(selected["code"])
        strat_cls = _find_strategy_class(mod)
        
        data = pd.read_parquet(local_data_path)
        strategy_instance = strat_cls()
        backtester = HFTBacktester(data, strategy_instance)
        equity_curve = backtester.run()

        fig, ax = plt.subplots()
        equity_curve['equity'].plot(ax=ax)
        ax.set_ylabel("Portfolio Value ($)")
        ax.set_title("Equity Curve")
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Failed to run backtest: {e}")

