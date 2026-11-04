"""Test and validation script for Module 2: Data Validation & Integrity.

Loads datasets using Module 1, runs the DataValidator across all integrity checks,
and prints a formatted summary distinguishing errors and warnings.
"""

import sys
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader
from code.data_validator import DataValidator, ValidationReport


def run_data_validator_test() -> bool:
    """Execute validation checks on all challenge datasets and display results."""
    print("=" * 80)
    print("MODULE 2: DATA VALIDATION & INTEGRITY TEST")
    print("=" * 80)

    try:
        # Step 1: Load datasets using Module 1
        print("Loading datasets using Module 1 DataLoader...")
        loader = DataLoader()
        datasets = loader.load_all()
        print(f"[OK] Loaded {len(list(datasets))} datasets from {loader.data_dir}\n")

        # Step 2: Run validation
        print("Executing DataValidator integrity checks...")
        validator = DataValidator(datasets)
        report: ValidationReport = validator.validate_all()

        # Step 3: Print summary metrics
        print("\n" + "-" * 80)
        print("VALIDATION SUMMARY METRICS")
        print("-" * 80)
        print(f"Total Checks Executed : {report.total_checks}")
        print(f"Checks Passed         : {report.passed_checks}")
        print(f"Checks Failed (Errors): {report.failed_checks}")
        print(f"Warnings Reported     : {report.warnings_count}")
        print(f"Overall Status        : {'VALID (0 Errors)' if report.is_valid else 'INVALID'}")
        print("-" * 80)

        # Step 4: Display issues if any
        if report.issues:
            print("\nREPORTED ISSUES & OBSERVATIONS:")
            print("=" * 80)
            for idx, issue in enumerate(report.issues, start=1):
                severity_tag = f"[{issue.severity}]"
                print(
                    f"{idx:2d}. {severity_tag:<10} | {issue.category:<25} | "
                    f"{issue.dataset}.{issue.field}"
                )
                print(f"    Message: {issue.message}")
                if issue.affected_ids:
                    sample_ids = ", ".join(str(i) for i in issue.affected_ids[:5])
                    more = f" ... (+{len(issue.affected_ids) - 5} more)" if len(issue.affected_ids) > 5 else ""
                    print(f"    Sample IDs: {sample_ids}{more}")
            print("=" * 80)
        else:
            print("\n[OK] No issues or warnings reported.")

        # Step 5: Determine pass/fail
        if report.is_valid:
            print("\n[SUCCESS] Module 2 DataValidator executed successfully without crashes.")
            print("All schemas, primary keys, foreign keys, and constraints verified.")
            return True
        else:
            print(f"\n[FAILURE] Validation detected {report.failed_checks} critical error(s).", file=sys.stderr)
            return False

    except Exception as e:
        print(f"\n[CRASH] Validator encountered an unhandled exception: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_data_validator_test()
    # Exit 0 if validator runs properly without crashing (even with dataset warnings)
    sys.exit(0 if success else 1)

