# Dashboard Launchers

To prevent port conflicts between the Evolution GUI and Realtime Dashboard, use these dedicated launchers:

## 🧬 Evolution GUI (Port 8504)
```bash
python scripts/launch_evolution_gui.py
```
- URL: http://localhost:8504
- Features: Strategy evolution, OpenAI API integration, Hall of Fame

## 🚀 Realtime Dashboard (Port 8501)
```bash
python scripts/launch_realtime_gui.py
```
- URL: http://localhost:8501  
- Features: Live BTC/USDT data, paper trading, orderbook monitoring

## Alternative Methods

**Evolution GUI:**
```bash
python -m streamlit run scripts/gui.py --server.port=8504
```

**Realtime Dashboard:**
```bash
python examples/run_realtime.py --dashboard-only
# OR
python -m streamlit run alphaevolve/realtime/dashboard/realtime_dashboard.py --server.port=8501
```

## Port Assignments
- **8504**: Evolution GUI (AlphaEvolve HFT)
- **8501**: Realtime Dashboard (Bybit Trading)
- **8502-8503**: Available for testing/debugging