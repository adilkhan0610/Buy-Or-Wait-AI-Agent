"""Validation and test script for Module 1: Data Loader.

Verifies that all 8 datasets load properly from the dataset folder and prints:
- Dataset name
- Number of rows
- Number of columns
- Column names
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'code' can be imported cleanly
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader, Datasets, load_all_datasets


def run_data_loader_test() -> bool:
    """Execute validation tests on DataLoader and print detailed dataset metrics."""
    print("=" * 80)
    print("MODULE 1: DATA LOADER VERIFICATION TEST")
    print("=" * 80)

    try:
        loader = DataLoader()
        print(f"Target dataset directory: {loader.data_dir}\n")

        datasets: Datasets = loader.load_all()
        print("[SUCCESS] All 8 datasets loaded and schema-validated successfully!\n")

        print("-" * 80)
        print(f"{'DATASET NAME':<25} | {'ROWS':<8} | {'COLS':<6} | {'FILE NAME':<25}")
        print("-" * 80)

        for summary in datasets.summary():
            print(
                f"{summary['name']:<25} | "
                f"{summary['rows']:<8} | "
                f"{summary['columns']:<6} | "
                f"{summary['file']:<25}"
            )

        print("-" * 80)
        print("\nDETAILED COLUMN SPECIFICATIONS:")
        print("=" * 80)

        for summary in datasets.summary():
            print(f"\n* Dataset: {summary['name']} ({summary['file']})")
            print(f"  Rows   : {summary['rows']}")
            print(f"  Columns: {summary['columns']}")
            print("  Column List:")
            for idx, col in enumerate(summary["column_names"], start=1):
                print(f"    {idx:2d}. {col}")

        # Basic assertion checks
        assert len(datasets.requests) == 250, f"Expected 250 requests, got {len(datasets.requests)}"
        assert len(datasets.sample_requests) == 25, f"Expected 25 sample requests, got {len(datasets.sample_requests)}"
        assert len(datasets.financial_profiles) == 275, f"Expected 275 profiles, got {len(datasets.financial_profiles)}"
        assert len(datasets.financial_events) == 25342, f"Expected 25342 events, got {len(datasets.financial_events)}"
        assert len(datasets.exchange_rates) == 134, f"Expected 134 rates, got {len(datasets.exchange_rates)}"
        assert len(datasets.request_payment_options) == 790, f"Expected 790 options, got {len(datasets.request_payment_options)}"
        assert len(datasets.messages) == 215, f"Expected 215 messages, got {len(datasets.messages)}"
        assert len(datasets.images) == 16, f"Expected 16 images, got {len(datasets.images)}"

        # Attribute and dict-like access verification
        assert datasets["requests"] is datasets.requests
        assert "financial_events" in datasets

        print("\n" + "=" * 80)
        print("ALL ASSERTIONS PASSED: Module 1 Data Loader is fully operational.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAILURE] Test encountered an error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_data_loader_test()
    sys.exit(0 if success else 1)

