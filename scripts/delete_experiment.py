"""
A command-line tool to safely delete an AlphaEvolve experiment database.
"""
import os
import sys
from pathlib import Path

def delete_experiment(experiment_name: str):
    """
    Deletes the database file associated with a given experiment name.
    """
    # Note: We are now using a local 'experiments' directory
    db_path = Path("experiments") / f"{experiment_name}.db"
    
    if db_path.exists():
        try:
            os.remove(db_path)
            print(f"Successfully deleted experiment '{experiment_name}' at: {db_path}")
        except OSError as e:
            print(f"Error: Failed to delete experiment '{experiment_name}'.")
            print(f"Reason: {e}")
            print("Please ensure that the Streamlit application is not running.")
    else:
        print(f"Error: Experiment '{experiment_name}' not found at: {db_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/delete_experiment.py <experiment_name>")
        sys.exit(1)
        
    experiment_name_to_delete = sys.argv[1]
    delete_experiment(experiment_name_to_delete)
