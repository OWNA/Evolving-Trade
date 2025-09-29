import argparse
import asyncio

from alphaevolve import AlphaEvolve

parser = argparse.ArgumentParser(description="Run AlphaEvolve demo")
parser.add_argument(
    "--experiment",
    type=str,
    default=None,
    help="Experiment name (creates or resumes a SQLite DB)",
)
parser.add_argument(
    "--iterations", type=int, default=10, help="Number of evolution iterations"
)
args = parser.parse_args()

# Initialize the system
evolve = AlphaEvolve(
    initial_program_paths=["examples/sma_momentum.py"],
    experiment_name=args.experiment,
)


# Run the evolution
async def main() -> None:
    best_strategy = await evolve.run(iterations=args.iterations)
    print("Best strategy metrics:")
    for name, value in best_strategy.metrics.items():
        print(f"  {name}: {value:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
