#!/bin/bash

# Setup script for Evolving Trade virtual environment
echo "🐍 Setting up Evolving Trade Virtual Environment"
echo "================================================"

# Check if python3-venv is available
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "❌ Error: python3-venv is not installed."
    echo "📋 Please run the following command first:"
    echo "   sudo apt update && sudo apt install python3.10-venv"
    echo ""
    exit 1
fi

# Create virtual environment
echo "1. 📂 Creating virtual environment..."
python3 -m venv venv

# Check if creation was successful
if [ ! -d "venv" ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created successfully!"

# Activate and install dependencies
echo ""
echo "2. 📦 Activating environment and installing dependencies..."

# Activate the environment
source venv/bin/activate

# Upgrade pip
echo "   Upgrading pip..."
pip install --upgrade pip

# Install the package in editable mode
echo "   Installing Evolving Trade package..."
pip install -e .

# Install dashboard dependencies
echo "   Installing dashboard dependencies..."
pip install streamlit plotly

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 To activate the environment and run the system:"
echo "   source venv/bin/activate"
echo "   python examples/test_bybit_connection.py     # Test connection"
echo "   python examples/demo_system.py              # Quick demo"
echo "   python examples/run_realtime.py --dashboard-only  # Dashboard only"
echo ""
echo "🔧 To deactivate when done:"
echo "   deactivate"