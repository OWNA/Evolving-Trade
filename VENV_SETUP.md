# 🐍 Virtual Environment Setup Guide

This guide shows you how to set up and run the Evolving Trade system in a Python virtual environment.

## 🔧 Prerequisites

First, ensure you have the required system packages:

```bash
# On Ubuntu/Debian systems:
sudo apt update
sudo apt install python3.10-venv

# On other systems, ensure you have Python 3.10+ with venv support
```

## 🚀 Quick Setup (Automated)

Run the automated setup script:

```bash
./setup_venv.sh
```

## 📋 Manual Setup (Step by Step)

### Step 1: Create Virtual Environment

```bash
# Create the virtual environment
python3 -m venv venv

# Verify creation
ls -la venv/
```

### Step 2: Activate Virtual Environment

```bash
# Activate the environment
source venv/bin/activate

# You should see (venv) in your prompt
# (venv) user@machine:~/Evolving-Trade$
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install the project in editable mode
pip install -e .

# Install dashboard dependencies
pip install streamlit plotly

# Verify installation
pip list | grep -E "(evolving-trade|streamlit|pybit)"
```

## 🧪 Testing in Virtual Environment

### Test 1: Connection Test

```bash
# Make sure venv is activated
source venv/bin/activate

# Run connection test
python examples/test_bybit_connection.py
```

### Test 2: Quick System Demo

```bash
# Run 30-second system demo
python examples/demo_system.py
```

### Test 3: Dashboard Only

```bash
# Start just the dashboard
python examples/run_realtime.py --dashboard-only

# Visit: http://localhost:8501
```

### Test 4: Full System

```bash
# Run complete real-time trading system
python examples/run_realtime.py --config examples/realtime_config.yaml
```

## 🎯 Common Commands

### Activate Environment
```bash
source venv/bin/activate
```

### Check What's Installed
```bash
pip list
pip show evolving-trade
```

### Update Dependencies
```bash
pip install --upgrade -e .
```

### Deactivate Environment
```bash
deactivate
```

### Remove Environment (if needed)
```bash
rm -rf venv/
```

## 📁 Virtual Environment Structure

After setup, your project structure will be:

```
Evolving-Trade/
├── venv/                          # Virtual environment
│   ├── bin/                       # Python binaries
│   ├── lib/                       # Installed packages
│   └── ...
├── alphaevolve/                   # Main package
├── examples/                      # Run scripts
├── credentials/                   # API credentials
├── setup_venv.sh                  # Automated setup
└── requirements.txt               # (optional)
```

## 🔍 Troubleshooting

### Issue: "python3-venv not available"
```bash
sudo apt update
sudo apt install python3.10-venv
```

### Issue: "Permission denied"
```bash
chmod +x setup_venv.sh
```

### Issue: "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall in editable mode
pip install -e .
```

### Issue: "Port already in use"
```bash
# Kill existing Streamlit processes
pkill -f streamlit

# Or use different port
streamlit run dashboard.py --server.port 8502
```

## 🎉 Success Indicators

You know everything is working when:

✅ `(venv)` appears in your terminal prompt  
✅ `python examples/test_bybit_connection.py` shows "2/3 tests passed"  
✅ `python examples/demo_system.py` shows live market data  
✅ Dashboard loads at http://localhost:8501  
✅ No import errors when running scripts  

## 🚀 Production Usage

For production use in virtual environment:

```bash
# Always start with environment activation
source venv/bin/activate

# Run your preferred mode
python examples/run_realtime.py --config examples/realtime_config.yaml

# When done, deactivate
deactivate
```

## 📝 Notes

- **Isolation**: Virtual environment keeps dependencies separate from system Python
- **Reproducibility**: Same environment can be recreated on different machines  
- **Safety**: Won't interfere with other Python projects
- **Portability**: Can be easily moved or recreated

## 🆘 Need Help?

If you encounter issues:

1. Make sure virtual environment is activated: `source venv/bin/activate`
2. Check Python version: `python --version` (should be 3.10+)
3. Verify package installation: `pip show evolving-trade`
4. Test basic imports: `python -c "import alphaevolve; print('OK')"`