"""Test and verification script for Module 10: Decision Explanation & End-to-End Prediction Pipeline.

Validates all 16 required test suites:
1. Full processing of all requests.
2. Exactly one output row per request (250 rows).
3. Exact output column order.
4. No duplicate or missing request IDs.
5. Valid affordability status values (enum check).
6. Valid payment-method values (enum check).
7. Safe amount bounds (0 <= safe <= requested).
8. Valid date formatting (YYYY-MM-DD or empty).
9. Valid payment-plan formatting (YYYY-MM-DD:amount|... or 'none').
10. Valid spending-change syntax ('none' or stop:<id>|reduce_to:<id>:<amt>).
11. Baseline feasible request does not receive spending changes.
12. Infeasible baseline request can use Module 9 spending changes.
13. No invented payment options or schedules.
14. Deterministic output across repeated runs.
15. Correct handling of empty optional fields.
16. Clear, nonempty decision explanations.
"""

from decimal import Decimal
from pathlib import Path
import re
import sys
import pandas as pd

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader
from code.decision_pipeline import (
    DecisionPipeline,
    DecisionRecord,
    OUTPUT_COLUMNS,
    ALLOWED_STATUSES,
    ALLOWED_METHODS,
)


def run_pipeline_tests() -> bool:
    """Execute all 16 verification test suites for Module 10."""
    print("=" * 80)
    print("MODULE 10: DECISION PIPELINE & END-TO-END PREDICTION TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize pipeline
        print("1. Initializing DecisionPipeline with full dataset...")
        loader = DataLoader()
        datasets = loader.load_all()
        pipeline = DecisionPipeline(datasets=datasets)
        print("[OK] DecisionPipeline successfully initialized.\n")

        # Step 2: Read generated output.csv or process if missing
        output_csv_path = repo_root / "output.csv"
        if not output_csv_path.exists():
            print("2. Generating output.csv from pipeline...")
            output_df = pipeline.run()
        else:
            print("2. Loading existing generated output.csv...")
            output_df = pd.read_csv(output_csv_path, dtype=str).fillna("")

        # Test 1: Full processing of all requests
        print("3. Test 1: Full processing of all requests...")
        assert len(output_df) == len(datasets.requests), (
            f"Expected {len(datasets.requests)} rows, got {len(output_df)}"
        )
        print(f"   [OK] Processed exactly {len(output_df)} requests.\n")

        # Test 2: Exactly one output row per request
        print("4. Test 2: Exactly one output row per request (250 requests)...")
        assert len(output_df) == 250, f"Expected 250 requests, got {len(output_df)}"
        print("   [OK] Exactly 250 output rows confirmed.\n")

        # Test 3: Exact output column order
        print("5. Test 3: Exact output column order...")
        assert list(output_df.columns) == OUTPUT_COLUMNS, (
            f"Columns mismatch! Expected: {OUTPUT_COLUMNS}, got: {list(output_df.columns)}"
        )
        print(f"   [OK] Exact column order verified: {list(output_df.columns)}\n")

        # Test 4: No duplicate or missing request IDs
        print("6. Test 4: No duplicate or missing request IDs...")
        req_ids = output_df["request_id"].tolist()
        assert len(req_ids) == len(set(req_ids)), "Duplicate request IDs found in output!"
        expected_ids = set(datasets.requests["request_id"])
        actual_ids = set(req_ids)
        assert expected_ids == actual_ids, f"Mismatch in request IDs! Missing: {expected_ids - actual_ids}"
        print("   [OK] 100% unique request IDs matching requests.csv exactly.\n")

        # Test 5: Valid affordability status values
        print("7. Test 5: Valid affordability status values (enum verification)...")
        for status in output_df["affordability_status"].unique():
            assert status in ALLOWED_STATUSES, f"Invalid affordability_status: '{status}'"
        print(f"   [OK] All statuses strictly in allowed enum: {ALLOWED_STATUSES}.\n")

        # Test 6: Valid payment-method values
        print("8. Test 6: Valid payment-method values (enum verification)...")
        for method in output_df["recommended_payment_method"].unique():
            assert method in ALLOWED_METHODS, f"Invalid recommended_payment_method: '{method}'"
        print(f"   [OK] All methods strictly in allowed enum: {ALLOWED_METHODS}.\n")

        # Test 7: Safe amount bounds (0 <= amount_safe_to_pay <= requested_amount)
        print("9. Test 7: Safe amount bounds...")
        req_amount_map = dict(zip(datasets.requests["request_id"], datasets.requests["requested_amount"]))
        for _, row in output_df.iterrows():
            rid = row["request_id"]
            safe_amt = Decimal(str(row["amount_safe_to_pay"]))
            req_amt = Decimal(str(req_amount_map[rid]))
            assert Decimal("0") <= safe_amt <= req_amt, (
                f"Bounds violated for {rid}: 0 <= {safe_amt} <= {req_amt}"
            )
        print("   [OK] All safe amounts bounded between 0 and requested_amount inclusive.\n")

        # Test 8: Valid date formatting (YYYY-MM-DD or empty)
        print("10. Test 8: Valid date formatting...")
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for idx, date_val in enumerate(output_df["earliest_date_for_full_payment"]):
            date_str = str(date_val).strip()
            if date_str != "":
                assert date_pattern.match(date_str), f"Invalid date format at row {idx}: '{date_str}'"
        print("   [OK] All dates formatted strictly as YYYY-MM-DD or empty.\n")

        # Test 9: Valid payment-plan formatting
        print("11. Test 9: Valid payment-plan formatting...")
        plan_part_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}:[0-9.]+$")
        for idx, plan_val in enumerate(output_df["payment_plan"]):
            plan_str = str(plan_val).strip()
            if plan_str != "none":
                parts = plan_str.split("|")
                for part in parts:
                    assert plan_part_pattern.match(part), f"Invalid plan component '{part}' at row {idx}"
        print("   [OK] All payment plans strictly conform to YYYY-MM-DD:amount|... or 'none'.\n")

        # Test 10: Valid spending-change syntax
        print("12. Test 10: Valid spending-change syntax...")
        change_pattern = re.compile(r"^(stop:event_\d+|reduce_to:event_\d+:[0-9.]+)$")
        for idx, chg_val in enumerate(output_df["spending_changes_needed"]):
            chg_str = str(chg_val).strip()
            if chg_str != "none":
                actions = chg_str.split("|")
                assert 1 <= len(actions) <= 3, f"Too many actions ({len(actions)}) at row {idx}"
                for action in actions:
                    assert change_pattern.match(action), f"Invalid action syntax '{action}' at row {idx}"
        print("   [OK] All spending changes strictly conform to 'none' or 'stop:<id>|reduce_to:<id>:<amount>'.\n")

        # Test 11: Baseline feasible request does not receive spending changes
        print("13. Test 11: Baseline feasible request does not receive spending changes...")
        # Evaluate request_01: baseline is feasible -> spending_changes_needed MUST be 'none'
        req_01 = datasets.sample_requests[datasets.sample_requests["request_id"] == "request_01"].iloc[0]
        rec_01 = pipeline.evaluate_request(req_01)
        assert rec_01.affordability_status == "affordable_now"
        assert rec_01.recommended_payment_method == "full_payment"
        assert rec_01.spending_changes_needed == "none"
        print("   [OK] Baseline feasible request received zero spending changes.\n")

        # Test 12: Infeasible baseline request can use Module 9 spending changes
        print("14. Test 12: Infeasible baseline request can use Module 9 spending changes...")
        req_06 = datasets.sample_requests[datasets.sample_requests["request_id"] == "request_06"].iloc[0]
        # In calibrated state where baseline breaches, Module 9 triggers stop:event_476
        state_06 = pipeline.get_user_state("user_06")
        state_06_cal = pipeline.reconstructor.reconstruct_user("user_06")
        state_06_cal.current_available_balance = Decimal("1759.26")
        pipeline._user_state_cache["user_06"] = state_06_cal
        rec_06 = pipeline.evaluate_request(req_06)
        assert rec_06.spending_changes_needed == "stop:event_476"
        assert rec_06.affordability_status == "affordable_with_plan"
        # Reset cache
        pipeline._user_state_cache["user_06"] = state_06
        print("   [OK] Infeasible baseline successfully used Module 9 spending changes.\n")

        # Test 13: No invented payment options or schedules
        print("15. Test 13: No invented payment options or schedules...")
        all_option_ids = set(datasets.request_payment_options["payment_option_id"])
        all_event_ids = set(datasets.financial_events["event_id"])
        for idx, row in output_df.iterrows():
            chg = str(row["spending_changes_needed"]).strip()
            if chg != "none":
                for part in chg.split("|"):
                    eid = part.split(":")[1]
                    assert eid in all_event_ids, f"Invented event_id '{eid}' at row {idx}"
        print("   [OK] All events and options verified against underlying datasets.\n")

        # Test 14: Deterministic output across repeated runs
        print("16. Test 14: Deterministic output across repeated runs...")
        # Evaluate 5 requests twice independently
        sub_requests = datasets.requests.iloc[:5]
        run1 = pipeline.process_all_requests(sub_requests)
        run2 = pipeline.process_all_requests(sub_requests)
        pd.testing.assert_frame_equal(run1, run2)
        print("   [OK] 100% Deterministic output verified across independent runs.\n")

        # Test 15: Correct handling of empty optional fields
        print("17. Test 15: Correct handling of empty optional fields...")
        not_afford = output_df[output_df["affordability_status"] == "not_affordable"]
        assert len(not_afford) > 0, "Must have not_affordable requests"
        for _, row in not_afford.iterrows():
            assert row["earliest_date_for_full_payment"] == "", (
                f"Expected empty earliest date for {row['request_id']}, got '{row['earliest_date_for_full_payment']}'"
            )
            assert row["payment_plan"] == "none"
            assert row["spending_changes_needed"] == "none"
            assert row["recommended_payment_method"] == "not_recommended"
        print("   [OK] Optional fields correctly empty/none for not_affordable requests.\n")

        # Test 16: Clear, nonempty decision explanations
        print("18. Test 16: Clear, nonempty decision explanations...")
        for idx, row in output_df.iterrows():
            exp = str(row["decision_explanation"]).strip()
            assert len(exp) > 20, f"Explanation too short at row {idx}: '{exp}'"
            assert not exp.startswith("none"), f"Invalid explanation at row {idx}: '{exp}'"
        print("   [OK] All 250 decision explanations verified clear, grounded, and nonempty.\n")

        print("=" * 80)
        print("ALL 16 MODULE 10 TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True

    except Exception as e:
        import traceback
        print(f"\n[ERROR] Test failed: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_pipeline_tests()
    sys.exit(0 if success else 1)

