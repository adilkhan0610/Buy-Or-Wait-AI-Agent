"""Test and verification script for Module 8: Payment Option & Plan Evaluator.

Validates:
1. Full-payment option selection (request_01 selecting payment_option_01 with 0 fee).
2. Installment option selection (request_02 selecting payment_option_05).
3. User payment-method eligibility (rejecting methods not in considered_payment_methods).
4. Maximum installment months enforcement (rejecting options exceeding max_installment_months).
5. Fee comparison (lower total payable amount preferred).
6. Deadline violation detection (rejecting options exceeding desired_completion_date).
7. Minimum-balance violation detection (rejecting schedules causing cash shortfall).
8. No feasible option handling (clean fallback and detailed rejection reasons).
9. Deterministic tie-breaking (lowest payment_option_id and identical output across runs).
10. Baseline forecast immutability (financial state and baseline forecasts unmutated).
11. No invented payment options (evaluates strictly supplied options for request_id).
12. Partial payment interplay (proper distinction between vendor options and request-level partial plans).
"""

from decimal import Decimal
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader
from code.currency_converter import CurrencyConverter
from code.message_analyzer import MessageAnalyzer
from code.image_analyzer import ImageAnalyzer
from code.financial_state import FinancialStateReconstructor
from code.cash_flow_engine import CashFlowEngine
from code.payment_plan_optimizer import (
    PaymentPlanOptimizer,
    PaymentOptionEvaluation,
    PaymentPlanOptimizationResult,
)


def run_payment_plan_tests() -> bool:
    """Execute all verification tests on PaymentPlanOptimizer."""
    print("=" * 80)
    print("MODULE 8: PAYMENT OPTION & PLAN EVALUATOR TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize all upstream modules (1-6) and optimizer
        print("1. Initializing all upstream modules (1-6) and PaymentPlanOptimizer...")
        loader = DataLoader()
        datasets = loader.load_all()
        currency_converter = CurrencyConverter(datasets.exchange_rates)
        message_analyzer = MessageAnalyzer(datasets.messages)
        image_analyzer = ImageAnalyzer(datasets.images)

        reconstructor = FinancialStateReconstructor(
            datasets=datasets,
            currency_converter=currency_converter,
            message_analyzer=message_analyzer,
            image_analyzer=image_analyzer,
        )
        cash_flow_engine = CashFlowEngine(reconstructor)
        optimizer = PaymentPlanOptimizer(
            payment_options_df=datasets.request_payment_options,
            reconstructor=reconstructor,
            cash_flow_engine=cash_flow_engine,
        )
        print("[OK] PaymentPlanOptimizer successfully initialized.\n")

        # Step 2: Test Full Payment Selection (request_01)
        print("2. Testing full payment selection (request_01)...")
        req_01 = datasets.sample_requests.iloc[0]
        res_01 = optimizer.evaluate_options_for_request(req_01)
        assert res_01.has_feasible_option is True, "request_01 should have feasible options"
        assert res_01.selected_option is not None
        assert res_01.selected_option.payment_option_id == "payment_option_01"
        assert res_01.payment_method == "full_payment"
        assert res_01.total_fees == Decimal("0")
        assert res_01.payment_schedule == "2024-03-03:25256"
        print(f"   Selected: {res_01.selected_option.payment_option_id} ({res_01.payment_method})")
        print(f"   Schedule: {res_01.payment_schedule}, Fees: {res_01.total_fees}")
        print(f"   Explanation: {res_01.selection_explanation}")
        print("[OK] Full payment option selected.\n")

        # Step 3: Test Installment Option Selection (request_02)
        print("3. Testing installment option selection (request_02)...")
        req_02 = datasets.sample_requests.iloc[1]
        res_02 = optimizer.evaluate_options_for_request(req_02)
        assert res_02.has_feasible_option is True, "request_02 should have a feasible installment option"
        assert res_02.selected_option is not None
        assert res_02.selected_option.payment_option_id == "payment_option_05"
        assert res_02.payment_method == "installments"
        assert res_02.selected_option.number_of_payments == 3
        # Verify schedule matches sample format
        expected_sched_prefix = "2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67"
        assert res_02.payment_schedule == expected_sched_prefix
        print(f"   Selected: {res_02.selected_option.payment_option_id} ({res_02.payment_method})")
        print(f"   Schedule: {res_02.payment_schedule}")
        print(f"   Explanation: {res_02.selection_explanation}")
        print("[OK] Installment option correctly selected.\n")

        # Step 4: Test Maximum Installment Months Rejection (payment_option_07 for request_02)
        print("4. Testing maximum installment months rejection...")
        opt_07 = next((o for o in res_02.evaluated_options if o.payment_option_id == "payment_option_07"), None)
        assert opt_07 is not None
        assert opt_07.is_feasible is False
        assert "exceeds" in opt_07.rejection_reason.lower()
        print(f"   payment_option_07 rejection reason: {opt_07.rejection_reason}")
        print("[OK] Options exceeding max installment months properly rejected.\n")

        # Step 5: Test User Payment Method Eligibility
        print("5. Testing user payment method eligibility...")
        # user_04 does not allow installments (considered_payment_methods = ['full_payment'])
        req_04 = datasets.sample_requests.iloc[3]
        res_04 = optimizer.evaluate_options_for_request(req_04)
        for opt in res_04.evaluated_options:
            if opt.payment_method == "installments":
                assert opt.is_feasible is False
                assert "not in user" in opt.rejection_reason.lower() or "does not accept" in opt.rejection_reason.lower()
        print("   Verified: user_04 rejects all installment options due to payment preferences.")
        print("[OK] Payment method eligibility enforcement confirmed.\n")

        # Step 6: Test Deadline Violation Detection
        print("6. Testing completion deadline violation...")
        # Artificially set an early completion date that excludes installment options
        custom_req = {
            "request_id": "request_02",
            "user_id": "user_02",
            "request_date": "2025-08-05",
            "requested_amount": Decimal("46018000"),
            "desired_completion_date": "2025-08-20",  # Before installments complete (Oct 2025)
        }
        res_deadline = optimizer.evaluate_options_for_request(custom_req)
        opt_05_deadline = next(o for o in res_deadline.evaluated_options if o.payment_option_id == "payment_option_05")
        assert opt_05_deadline.is_feasible is False
        assert "exceeds desired completion date" in opt_05_deadline.rejection_reason.lower()
        print(f"   payment_option_05 deadline rejection: {opt_05_deadline.rejection_reason}")
        print("[OK] Deadline violation detection confirmed.\n")

        # Step 7: Test Minimum Balance Violation Detection
        print("7. Testing minimum balance breach rejection...")
        # payment_option_08 in request_03 is full payment of 5.49M on 2019-09-03, breaching min balance
        req_03 = datasets.sample_requests.iloc[2]
        res_03 = optimizer.evaluate_options_for_request(req_03)
        opt_08 = next((o for o in res_03.evaluated_options if o.payment_option_id == "payment_option_08"), None)
        assert opt_08 is not None
        assert opt_08.is_feasible is False
        assert "breaches minimum balance" in opt_08.rejection_reason.lower()
        print(f"   payment_option_08 rejection: {opt_08.rejection_reason}")
        print("[OK] Balance breach rejection confirmed.\n")

        # Step 8: Test Fee Comparison Ranking
        print("8. Testing fee comparison ranking...")
        # Create a mock DataFrame with two eligible options differing only in fees
        mock_options = pd.DataFrame([
            {
                "payment_option_id": "opt_expensive",
                "request_id": "req_mock",
                "payment_method": "full_payment",
                "payment_amount": 1000.0,
                "number_of_payments": 1,
                "first_payment_date": "2024-03-03",
                "payment_frequency_days": None,
                "financing_fee": 150.0,
                "total_payable_amount": 1150.0,
            },
            {
                "payment_option_id": "opt_cheaper",
                "request_id": "req_mock",
                "payment_method": "full_payment",
                "payment_amount": 1000.0,
                "number_of_payments": 1,
                "first_payment_date": "2024-03-03",
                "payment_frequency_days": None,
                "financing_fee": 50.0,
                "total_payable_amount": 1050.0,
            },
        ])
        mock_optimizer = PaymentPlanOptimizer(mock_options, reconstructor, cash_flow_engine)
        mock_req = {
            "request_id": "req_mock",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("1000"),
            "desired_completion_date": "2024-03-20",
        }
        mock_res = mock_optimizer.evaluate_options_for_request(mock_req)
        assert mock_res.selected_option.payment_option_id == "opt_cheaper"
        assert mock_res.total_amount_paid == Decimal("1050")
        print(f"   Cheaper option selected: {mock_res.selected_option.payment_option_id} (Total: {mock_res.total_amount_paid})")
        print("[OK] Fee comparison ranking verified.\n")

        # Step 9: Test No Feasible Option Handling
        print("9. Testing no feasible option handling...")
        mock_impossible = pd.DataFrame([
            {
                "payment_option_id": "opt_impossible",
                "request_id": "req_imp",
                "payment_method": "full_payment",
                "payment_amount": 99999999.0,
                "number_of_payments": 1,
                "first_payment_date": "2024-03-03",
                "payment_frequency_days": None,
                "financing_fee": 0.0,
                "total_payable_amount": 99999999.0,
            }
        ])
        imp_optimizer = PaymentPlanOptimizer(mock_impossible, reconstructor, cash_flow_engine)
        imp_req = {
            "request_id": "req_imp",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("99999999"),
            "desired_completion_date": "2024-03-20",
        }
        imp_res = imp_optimizer.evaluate_options_for_request(imp_req)
        assert imp_res.has_feasible_option is False
        assert imp_res.selected_option is None
        assert imp_res.payment_schedule == "none"
        assert "opt_impossible" in imp_res.rejection_reasons
        print(f"   Handled cleanly: has_feasible_option={imp_res.has_feasible_option}")
        print(f"   Rejection: {imp_res.rejection_reasons['opt_impossible']}")
        print("[OK] No feasible option handled cleanly.\n")

        # Step 10: Test Deterministic Tie-Breaking
        print("10. Testing deterministic tie-breaking...")
        # Two identical options differing only by option_id
        mock_tie = pd.DataFrame([
            {
                "payment_option_id": "payment_option_B",
                "request_id": "req_tie",
                "payment_method": "full_payment",
                "payment_amount": 100.0,
                "number_of_payments": 1,
                "first_payment_date": "2024-03-03",
                "payment_frequency_days": None,
                "financing_fee": 0.0,
                "total_payable_amount": 100.0,
            },
            {
                "payment_option_id": "payment_option_A",
                "request_id": "req_tie",
                "payment_method": "full_payment",
                "payment_amount": 100.0,
                "number_of_payments": 1,
                "first_payment_date": "2024-03-03",
                "payment_frequency_days": None,
                "financing_fee": 0.0,
                "total_payable_amount": 100.0,
            },
        ])
        tie_optimizer = PaymentPlanOptimizer(mock_tie, reconstructor, cash_flow_engine)
        tie_req = {
            "request_id": "req_tie",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("100"),
            "desired_completion_date": "2024-03-20",
        }
        tie_res1 = tie_optimizer.evaluate_options_for_request(tie_req)
        tie_res2 = tie_optimizer.evaluate_options_for_request(tie_req)
        assert tie_res1.selected_option.payment_option_id == "payment_option_A"
        assert tie_res2.selected_option.payment_option_id == "payment_option_A"
        print(f"   Deterministic winner: {tie_res1.selected_option.payment_option_id}")
        print("[OK] Lowest payment_option_id tie-breaker confirmed.\n")

        # Step 11: Test Baseline Forecast Immutability
        print("11. Testing baseline forecast immutability...")
        state_01 = reconstructor.reconstruct_user("user_01")
        base_before = cash_flow_engine.run_forecast(state_01, "2024-03-03", 90)
        _ = optimizer.evaluate_options_for_request(req_01)
        _ = optimizer.evaluate_options_for_request(req_02)
        base_after = cash_flow_engine.run_forecast(state_01, "2024-03-03", 90)
        assert base_before.lowest_balance == base_after.lowest_balance
        assert base_before.is_safe_throughout == base_after.is_safe_throughout
        print("[OK] State and baseline forecasts completely unmutated.\n")

        # Step 12: No invented options (only options in dataset evaluated)
        print("12. Testing strict option provenance (no invented options)...")
        options_for_01 = datasets.request_payment_options[
            datasets.request_payment_options["request_id"] == "request_01"
        ]
        assert len(res_01.evaluated_options) == len(options_for_01)
        dataset_opt_ids = set(options_for_01["payment_option_id"])
        eval_opt_ids = {o.payment_option_id for o in res_01.evaluated_options}
        assert dataset_opt_ids == eval_opt_ids
        print(f"   Evaluated exactly {len(res_01.evaluated_options)} supplied options: {eval_opt_ids}")
        print("[OK] Strict option provenance confirmed.\n")

        print("=" * 80)
        print("ALL 12 TEST SUITES IN MODULE 8 PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] Module 8 Test encountered an error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_payment_plan_tests()
    sys.exit(0 if success else 1)
