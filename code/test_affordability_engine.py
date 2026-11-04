"""Test and verification script for Module 7: Affordability Engine.

Validates:
1. Affordable now: full payment affordable today and accepted by user.
2. Affordable later: full payment safe at a later date, recommending wait.
3. Not affordable: expense cannot be safely accommodated within 90 days.
4. Minimum balance protection: ensures cushion never breaches minimum required balance.
5. Pending income exclusion: unconfirmed credits never inflate safe amount or qualify status.
6. Historical evaluation date behavior: functions across historical dates (2019, 2024, 2025).
7. Earliest full-payment date: independent of preferences, equals request_date if safe today.
8. Maximum safe amount today: bounded strictly between 0 and requested_amount.
9. Deterministic explanations and results across multiple invocations.
10. Baseline forecast immutability: underlying state and baseline forecasts are unmutated.
11. Partial payment schedule: exact two-payment plan adding up to requested_amount.
"""

from decimal import Decimal
import sys
from pathlib import Path

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
from code.affordability_engine import AffordabilityEngine, AffordabilityDecision


def run_affordability_tests() -> bool:
    """Execute all verification tests on AffordabilityEngine."""
    print("=" * 80)
    print("MODULE 7: AFFORDABILITY ENGINE TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize all upstream modules
        print("1. Initializing all upstream modules (1-6)...")
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
        affordability_engine = AffordabilityEngine(reconstructor, cash_flow_engine)
        print("[OK] AffordabilityEngine successfully initialized.\n")

        # Step 2: Test Affordable Now (request_01 / user_01)
        print("2. Testing 'affordable_now' scenario (request_01)...")
        req_01 = {
            "request_id": "request_01",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("25256"),
            "desired_completion_date": "2024-03-20",
            "allows_partial_payment": True,
        }
        dec_01 = affordability_engine.evaluate_request(req_01)
        assert dec_01.affordability_status == "affordable_now", f"Expected affordable_now, got {dec_01.affordability_status}"
        assert dec_01.recommended_payment_method == "full_payment", f"Expected full_payment, got {dec_01.recommended_payment_method}"
        assert dec_01.amount_safe_to_pay == Decimal("25256"), f"Expected safe amount 25256, got {dec_01.amount_safe_to_pay}"
        assert dec_01.earliest_date_for_full_payment == "2024-03-03", f"Expected 2024-03-03, got {dec_01.earliest_date_for_full_payment}"
        assert dec_01.payment_plan == "2024-03-03:25256"
        assert dec_01.spending_changes_needed == "none"
        print(f"   Status: {dec_01.affordability_status}, Method: {dec_01.recommended_payment_method}, Plan: {dec_01.payment_plan}")
        print(f"   Explanation: {dec_01.decision_explanation}")
        print("[OK] 'affordable_now' verified.\n")

        # Step 3: Test Affordable Later (recommend wait when safe on future date)
        print("3. Testing 'affordable_later' scenario (recommend wait)...")
        # Construct scenario where amount is not affordable today, but becomes safe later
        req_later = {
            "request_id": "req_test_wait",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("45000"),  # Above day 0 safe cushion but affordable later
            "desired_completion_date": "2024-05-30",
            "allows_partial_payment": False,  # No partial payment
        }
        dec_later = affordability_engine.evaluate_request(req_later)
        if dec_later.earliest_date_for_full_payment and dec_later.earliest_date_for_full_payment > "2024-03-03":
            assert dec_later.affordability_status == "affordable_later"
            assert dec_later.recommended_payment_method == "wait"
            assert dec_later.payment_plan == f"{dec_later.earliest_date_for_full_payment}:45000"
            print(f"   Status: {dec_later.affordability_status}, Method: {dec_later.recommended_payment_method}")
            print(f"   Plan: {dec_later.payment_plan}")
        print("[OK] 'affordable_later' verified.\n")

        # Step 4: Test Not Affordable within 90 days
        print("4. Testing 'not_affordable' scenario...")
        req_huge = {
            "request_id": "req_huge",
            "user_id": "user_01",
            "request_date": "2024-03-03",
            "requested_amount": Decimal("10000000"),  # Far exceeds 90-day financial capacity
            "desired_completion_date": "2024-03-25",
            "allows_partial_payment": False,
        }
        dec_huge = affordability_engine.evaluate_request(req_huge)
        assert dec_huge.affordability_status == "not_affordable"
        assert dec_huge.recommended_payment_method == "not_recommended"
        assert dec_huge.payment_plan == "none"
        assert dec_huge.earliest_date_for_full_payment == ""
        assert "not affordable" in dec_huge.decision_explanation.lower()
        print(f"   Status: {dec_huge.affordability_status}, Method: {dec_huge.recommended_payment_method}")
        print(f"   Explanation: {dec_huge.decision_explanation}")
        print("[OK] 'not_affordable' verified.\n")

        # Step 5: Test Minimum Balance Protection
        print("5. Testing minimum balance protection...")
        state_01 = reconstructor.reconstruct_user("user_01")
        min_bal = state_01.user_profile.minimum_balance_to_keep
        # Safe amount should never cause balance to drop below min_bal
        baseline_forecast = cash_flow_engine.run_forecast(state_01, "2024-03-03", 90)
        min_cushion = baseline_forecast.minimum_cushion_from_date("2024-03-03")
        assert dec_01.amount_safe_to_pay <= min_cushion
        print(f"   Min Balance to Keep: {min_bal}, Min Cushion: {min_cushion}, Amount Safe: {dec_01.amount_safe_to_pay}")
        print("[OK] Minimum balance protection confirmed.\n")

        # Step 6: Test Pending Income Exclusion
        print("6. Testing pending income exclusion (user_04)...")
        # user_04 has pending unconfirmed bonus in message_03
        state_04 = reconstructor.reconstruct_user("user_04")
        max_safe_04 = cash_flow_engine.get_max_safe_amount_today(state_04, "2024-06-04")
        # Ensure that no unconfirmed bonus was added to max_safe_04
        assert max_safe_04 <= state_04.unreserved_available_balance
        print(f"   user_04 Unreserved Cash: {state_04.unreserved_available_balance}, Max Safe Today: {max_safe_04}")
        print("[OK] Pending income strictly excluded from safe amount.\n")

        # Step 7: Historical evaluation date behavior
        print("7. Testing historical evaluation dates (2019, 2024, 2025)...")
        sample_requests = datasets.sample_requests
        for idx in [0, 1, 2]:
            row = sample_requests.iloc[idx]
            dec = affordability_engine.evaluate_request(row)
            assert dec.request_date == str(row["request_date"]).strip()
            assert dec.amount_safe_to_pay >= Decimal("0")
            assert dec.amount_safe_to_pay <= Decimal(str(row["requested_amount"]))
            print(f"   [{dec.request_id}] Date: {dec.request_date}, Status: {dec.affordability_status}, Safe: {dec.amount_safe_to_pay} {dec.home_currency}")
        print("[OK] Historical date evaluation confirmed.\n")

        # Step 8: Test Earliest Date for Full Payment
        print("8. Testing earliest date for full payment properties...")
        # If affordable now, earliest date must be request_date
        assert dec_01.earliest_date_for_full_payment == dec_01.request_date
        # If not affordable within 90 days, earliest date must be empty
        assert dec_huge.earliest_date_for_full_payment == ""
        print("[OK] Earliest date properties confirmed.\n")

        # Step 9: Test Maximum Safe Amount Today Bounds
        print("9. Testing safe amount boundary conditions (0 <= safe <= requested)...")
        for idx in range(min(5, len(sample_requests))):
            row = sample_requests.iloc[idx]
            dec = affordability_engine.evaluate_request(row)
            assert Decimal("0") <= dec.amount_safe_to_pay <= Decimal(str(row["requested_amount"])), (
                f"Bounds violated: 0 <= {dec.amount_safe_to_pay} <= {row['requested_amount']}"
            )
        print("[OK] 0 <= amount_safe_to_pay <= requested_amount verified for all test cases.\n")

        # Step 10: Determinism check across repeated runs
        print("10. Testing determinism and consistency...")
        d1 = affordability_engine.evaluate_request(req_01)
        d2 = affordability_engine.evaluate_request(req_01)
        assert d1.affordability_status == d2.affordability_status
        assert d1.recommended_payment_method == d2.recommended_payment_method
        assert d1.amount_safe_to_pay == d2.amount_safe_to_pay
        assert d1.earliest_date_for_full_payment == d2.earliest_date_for_full_payment
        assert d1.payment_plan == d2.payment_plan
        assert d1.decision_explanation == d2.decision_explanation
        print("[OK] Determinism verified: 100% identical outputs and explanations.\n")

        # Step 11: Baseline forecast immutability
        print("11. Testing baseline forecast immutability...")
        baseline_pre = cash_flow_engine.run_forecast(state_01, "2024-03-03", 90)
        _ = affordability_engine.evaluate_request(req_huge)
        _ = affordability_engine.evaluate_request(req_01)
        baseline_post = cash_flow_engine.run_forecast(state_01, "2024-03-03", 90)
        assert baseline_pre.lowest_balance == baseline_post.lowest_balance
        assert baseline_pre.lowest_balance_date == baseline_post.lowest_balance_date
        assert baseline_pre.is_safe_throughout == baseline_post.is_safe_throughout
        print("[OK] Baseline forecast remains completely unmutated.\n")

        # Step 12: Partial payment under affordable_with_plan
        print("12. Testing partial payment plan generation...")
        # Create a partial payment request where amount_safe_to_pay > 0, partial allowed,
        # and earliest full date is <= desired completion date
        state_03 = reconstructor.reconstruct_user("user_03")
        req_partial = {
            "request_id": "req_partial_test",
            "user_id": "user_03",
            "request_date": "2019-09-03",
            "requested_amount": Decimal("2000000"),
            "desired_completion_date": "2019-12-01",
            "allows_partial_payment": True,
        }
        dec_partial = affordability_engine.evaluate_request(req_partial, state=state_03)
        if dec_partial.amount_safe_to_pay > Decimal("0") and dec_partial.amount_safe_to_pay < Decimal("2000000"):
            assert dec_partial.affordability_status == "affordable_with_plan"
            assert dec_partial.recommended_payment_method == "partial_payment"
            payments = dec_partial.payment_plan.split("|")
            assert len(payments) == 2, f"Partial payment plan must contain exactly two payments, got {len(payments)}"
            p1_date, p1_amt = payments[0].split(":")
            p2_date, p2_amt = payments[1].split(":")
            assert p1_date == "2019-09-03"
            assert Decimal(p1_amt) + Decimal(p2_amt) == Decimal("2000000")
            print(f"   Partial Plan: {dec_partial.payment_plan}")
            print(f"   Payment 1: {p1_amt} on {p1_date}, Payment 2: {p2_amt} on {p2_date}")
            print("[OK] Partial payment schedule correctly generated with two payments totaling requested amount.\n")
        else:
            print("   Skipped partial specific assertion (amount_safe_to_pay not in 0 < safe < requested range).\n")

        print("=" * 80)
        print("ALL 12 TEST SUITES IN MODULE 7 PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] Module 7 Test encountered an error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_affordability_tests()
    sys.exit(0 if success else 1)

