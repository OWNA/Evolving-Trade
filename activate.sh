#!/bin/bash

# Activation script for Evolving Trade
echo "🐍 Activating Evolving Trade Virtual Environment"

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "💡 Run './setup_venv.sh' first to create it."
    exit 1
fi

# Activate the virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "🎯 You can now run:"
echo "   python examples/test_bybit_connection.py"
echo "   python examples/demo_system.py"
echo "   python examples/run_realtime.py --dashboard-only"
echo ""
echo "🔧 To deactivate when done: deactivate"

# Start a new shell with the environment activated
exec bash