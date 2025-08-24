#!/usr/bin/env python3
"""
Dedicated launcher for the Realtime Trading Dashboard on port 8501.
This prevents conflicts with the evolution GUI.
"""
import subprocess
import sys
from pathlib import Path

def main():
    """Launch the realtime dashboard on dedicated port 8501."""
    dashboard_path = Path(__file__).parent.parent / "alphaevolve" / "realtime" / "dashboard" / "realtime_dashboard.py"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard not found at: {dashboard_path}")
        return 1
    
    print("🚀 Launching Realtime Bybit Trading Dashboard...")
    print("📍 URL: http://localhost:8501")
    print("🔄 Starting Streamlit...")
    
    cmd = [
        sys.executable, 
        "-m", "streamlit", 
        "run", 
        str(dashboard_path),
        "--server.port=8501",
        "--server.headless=false",
        "--browser.gatherUsageStats=false"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Realtime dashboard stopped.")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())