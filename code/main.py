"""Main entry point for Buy or Wait? AI-Powered Financial Decision Agent.

HackerRank Orchestrate (September 2026).
Executes the complete end-to-end decision pipeline and generates output.csv.
"""

from datetime import datetime
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.decision_pipeline import DecisionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("buy_or_wait")


def main() -> int:
    """Run full end-to-end prediction pipeline and generate output.csv."""
    print("=" * 80)
    print("BUY OR WAIT? — AI-POWERED FINANCIAL AFFORDABILITY AGENT")
    print("HackerRank Orchestrate (September 2026)")
    print("=" * 80)

    start_time = datetime.now()

    try:
        pipeline = DecisionPipeline()
        print("\n1. Initialized analytical modules (DataLoader, Reconstructor, CashFlowEngine, Optimizers).")

        print("2. Processing evaluation requests from dataset/requests.csv...")
        output_df = pipeline.run()

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n[SUCCESS] Successfully processed {len(output_df)} requests in {duration:.2f} seconds!")

        # Summary statistics
        print("\n" + "-" * 80)
        print("PREDICTION SUMMARY BREAKDOWN")
        print("-" * 80)

        print("\n* Affordability Status:")
        for status, count in output_df["affordability_status"].value_counts().items():
            print(f"  - {status:<25}: {count:>4} ({count / len(output_df) * 100:.1f}%)")

        print("\n* Recommended Payment Method:")
        for method, count in output_df["recommended_payment_method"].value_counts().items():
            print(f"  - {method:<25}: {count:>4} ({count / len(output_df) * 100:.1f}%)")

        changes_count = (output_df["spending_changes_needed"] != "none").sum()
        print(f"\n* Requests Requiring Spending Changes: {changes_count} ({changes_count / len(output_df) * 100:.1f}%)")

        print("\n* Output Locations:")
        print(f"  - Repository Root: {repo_root / 'output.csv'}")
        print(f"  - Dataset Folder : {repo_root / 'dataset' / 'output.csv'}")
        print(f"  - Usage Report   : {repo_root / 'evaluation' / 'usage_report.md'}")
        print("=" * 80)
        return 0

    except Exception as e:
        logger.exception("Pipeline failed with error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

