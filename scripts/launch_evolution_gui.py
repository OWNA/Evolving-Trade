#!/usr/bin/env python3
"""
Dedicated launcher for the Evolution GUI on port 8504.
This prevents conflicts with the realtime dashboard.
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the evolution GUI on dedicated port 8504."""
    gui_path = Path(__file__).parent / "gui.py"
    
    print("🧬 Launching AlphaEvolve Evolution GUI...")
    print("📍 URL: http://localhost:8504")
    print("🔄 Starting Streamlit...")
    
    cmd = [
        sys.executable, 
        "-m", "streamlit", 
        "run", 
        str(gui_path),
        "--server.port=8504",
        "--server.headless=false",
        "--browser.gatherUsageStats=false"
    ]
    
    # Set environment to skip email prompt
    env = dict(os.environ)
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    try:
        subprocess.run(cmd, check=True, env=env)
    except KeyboardInterrupt:
        print("\n👋 Evolution GUI stopped.")
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())