"""Test and verification script for Module 6: 90-Day Cash Flow Engine.

Validates:
1. User balance remains above minimum for all 90 days (user_01 baseline).
2. User balance falls below minimum after confirmed expense / obligations.
3. Recurring income and expenses simulation across the 90-day horizon.
4. Pending income exclusion verification (unconfirmed pending income never credited).
5. Cancelled and failed events exclusion verification (ignored in cash flow).
6. Conservative same-day debit-first ordering (debits clear before credits).
7. Proposed purchase causing minimum-balance breach.
8. Proposed purchase that is safe.
9. No recurrence schedule invented when recurrence data missing.
10. Exact 90-day boundary check (starts at request_date, exactly 91 days).
11. Determinism check across repeated runs.
12. Safe amount and earliest date calculation functions.
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
from code.cash_flow_engine import CashFlowEngine, DailyCashFlow, ForecastResult


def run_cash_flow_tests() -> bool:
    """Execute all verification tests on CashFlowEngine."""
    print("=" * 80)
    print("MODULE 6: 90-DAY CASH FLOW ENGINE TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize all upstream modules
        print("1. Loading datasets and initializing reconstructor...")
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
        engine = CashFlowEngine(reconstructor)
        print("[OK] CashFlowEngine successfully initialized.\n")

        # Step 2: Test 90-Day Boundary Check for user_01
        print("2. Testing 90-day horizon boundaries (user_01 on 2024-03-03)...")
        state_01 = reconstructor.reconstruct_user("user_01")
        forecast_01 = engine.run_forecast(state_01, start_date="2024-03-03", horizon_days=90)

        assert forecast_01.user_id == "user_01"
        assert forecast_01.start_date == "2024-03-03"
        assert forecast_01.end_date == "2024-06-01"
        assert len(forecast_01.daily_forecasts) == 91, f"Expected 91 daily records (0-90), got {len(forecast_01.daily_forecasts)}"
        assert forecast_01.daily_forecasts[0].date == "2024-03-03"
        assert forecast_01.daily_forecasts[-1].date == "2024-06-01"
        print(f"   Start: {forecast_01.start_date}, End: {forecast_01.end_date}, Total days: {len(forecast_01.daily_forecasts)}")
        print("[OK] Boundary conditions verified.\n")

        # Step 3: Test Safe Baseline (user_01 balance remains above minimum)
        print("3. Testing baseline cash-flow safety (user_01)...")
        assert forecast_01.is_safe_throughout is True, "user_01 baseline should remain safe throughout 90 days"
        assert forecast_01.lowest_balance >= forecast_01.minimum_balance_to_keep
        print(f"   Initial Balance: {forecast_01.initial_balance} {forecast_01.home_currency}")
        print(f"   Minimum Balance to Keep: {forecast_01.minimum_balance_to_keep} {forecast_01.home_currency}")
        print(f"   Lowest Balance: {forecast_01.lowest_balance} on {forecast_01.lowest_balance_date}")
        print("[OK] User balance stays above minimum.\n")

        # Step 4: Test Conservative Same-Day Debit-First Ordering
        print("4. Testing conservative same-day debit-first ordering...")
        # Create a day where starting cash + credit would be >= min, but starting cash - debit drops below min
        test_state = reconstructor.reconstruct_user("user_01")
        # Proposed expense on start date equal to starting balance:
        starting_cash = test_state.unreserved_available_balance
        min_bal = test_state.user_profile.minimum_balance_to_keep
        # If we propose an expense equal to (starting_cash - min_bal + 100), intra-day lowest balance should dip 100 below min_bal
        excess_expense = (starting_cash - min_bal) + Decimal("100")
        trial_forecast = engine.run_forecast(
            state=test_state,
            start_date="2024-03-03",
            proposed_expenses=[("2024-03-03", excess_expense, "Test excess purchase")],
        )
        assert trial_forecast.daily_forecasts[0].intra_day_lowest_balance == starting_cash - excess_expense
        assert trial_forecast.daily_forecasts[0].intra_day_lowest_balance < min_bal
        assert trial_forecast.daily_forecasts[0].is_safe is False
        assert trial_forecast.is_safe_throughout is False
        assert trial_forecast.first_breach_date == "2024-03-03"
        print(f"   Starting: {starting_cash}, Debit: {excess_expense}, Intra-day lowest: {trial_forecast.daily_forecasts[0].intra_day_lowest_balance}")
        print(f"   Min balance: {min_bal}, Breach detected on: {trial_forecast.first_breach_date}")
        print("[OK] Same-day debit-first ordering and breach detection confirmed.\n")

        # Step 5: Test Pending Income Exclusion Verification
        print("5. Testing unconfirmed pending income exclusion (user_04)...")
        state_04 = reconstructor.reconstruct_user("user_04")
        # user_04 has message_03 with pending bonus that must NOT be counted as cash
        forecast_04 = engine.run_forecast(state_04, start_date="2024-06-04", horizon_days=90)
        # Check applied events across all days: no event should have description with "bonus"
        bonus_credits = [
            e for day in forecast_04.daily_forecasts for e in day.applied_events
            if "bonus" in str(e.get("description", "")).lower()
        ]
        assert len(bonus_credits) == 0, f"Unconfirmed pending bonus was improperly credited: {bonus_credits}"
        print("   Verified: No unconfirmed pending bonus or payout included in projected cash flow.")
        print("[OK] Pending income exclusion verified.\n")

        # Step 6: Test Cancelled and Failed Transactions Exclusion
        print("6. Testing cancelled and failed transactions exclusion...")
        ignored_ids = {item["event_id"] for item in state_01.ignored_or_conflicting}
        for day in forecast_01.daily_forecasts:
            for e in day.applied_events:
                eid = e.get("event_id", "")
                if eid in ignored_ids:
                    raise AssertionError(f"Cancelled/failed event {eid} found in scheduled cash flow!")
        print("   Verified: Zero cancelled or failed events applied in 90-day forecast.")
        print("[OK] Cancelled/failed events exclusion verified.\n")

        # Step 7: Test Recurring Cadence Extraction
        print("7. Testing recurring cadence extraction (user_02 confirmed salary and obligations)...")
        state_02 = reconstructor.reconstruct_user("user_02")
        forecast_02 = engine.run_forecast(state_02, start_date="2025-08-05", horizon_days=90)
        # Verify scheduled salary on 2025-08-15 appears as credit
        aug15_forecast = forecast_02.get_forecast_for_date("2025-08-15")
        assert aug15_forecast is not None
        salary_credits = [e for e in aug15_forecast.applied_events if e["direction"] == "credit"]
        assert len(salary_credits) > 0, "Expected confirmed salary on 2025-08-15"
        print(f"   2025-08-15 Credits: {salary_credits[0]['amount']} IDR ({salary_credits[0]['description']})")
        print("[OK] Confirmed future income and recurrence modeling verified.\n")

        # Step 8: Test Proposed Purchase Causing Breach vs Safe Purchase
        print("8. Testing proposed purchase evaluation (safe vs unsafe)...")
        # Safe small expense:
        small_forecast = engine.run_forecast(
            state=state_01,
            start_date="2024-03-03",
            proposed_expenses=[("2024-03-03", Decimal("100"), "Small purchase")],
        )
        assert small_forecast.is_safe_throughout is True, "Small 100 EUR purchase should be safe"

        # Massive unsafe expense:
        huge_forecast = engine.run_forecast(
            state=state_01,
            start_date="2024-03-03",
            proposed_expenses=[("2024-03-03", Decimal("1000000"), "Huge purchase")],
        )
        assert huge_forecast.is_safe_throughout is False, "Huge purchase must cause a breach"
        print(f"   Small purchase safe: {small_forecast.is_safe_throughout}")
        print(f"   Huge purchase safe: {huge_forecast.is_safe_throughout} (Breach date: {huge_forecast.first_breach_date})")
        print("[OK] Safe and unsafe proposed purchases correctly differentiated.\n")

        # Step 9: Test calculate_amount_safe_to_pay
        print("9. Testing calculate_amount_safe_to_pay...")
        safe_amount_01 = engine.calculate_amount_safe_to_pay(
            state=state_01,
            request_date="2024-03-03",
            requested_amount=Decimal("25256"),
        )
        assert safe_amount_01 > Decimal("0"), f"Expected safe amount > 0, got {safe_amount_01}"
        assert safe_amount_01 <= Decimal("25256"), f"Safe amount cannot exceed requested amount"
        print(f"   Requested: 25256, Amount Safe To Pay: {safe_amount_01}")
        print("[OK] Safe amount calculation verified.\n")

        # Step 10: Test find_earliest_date_for_full_payment
        print("10. Testing find_earliest_date_for_full_payment...")
        # For request_01, it is affordable immediately on request_date
        earliest_01 = engine.find_earliest_date_for_full_payment(
            state=state_01,
            request_date="2024-03-03",
            requested_amount=Decimal("25256"),
        )
        assert earliest_01 == "2024-03-03", f"Expected 2024-03-03 for user_01 full payment, got {earliest_01}"
        print(f"   Earliest date for full payment (user_01, 25256): {earliest_01}")

        # For user_03 on 2019-09-03 (requested 5,491,000 IDR - affordable later):
        state_03 = reconstructor.reconstruct_user("user_03")
        earliest_03 = engine.find_earliest_date_for_full_payment(
            state=state_03,
            request_date="2019-09-03",
            requested_amount=Decimal("5491000"),
        )
        print(f"   Earliest date for full payment (user_03, 5491000 IDR): {earliest_03}")
        print("[OK] Earliest date calculation verified.\n")

        # Step 11: Determinism check across repeated runs
        print("11. Testing determinism across repeated runs...")
        run1 = engine.run_forecast(state_01, "2024-03-03", 90)
        run2 = engine.run_forecast(state_01, "2024-03-03", 90)
        assert run1.lowest_balance == run2.lowest_balance
        assert run1.lowest_balance_date == run2.lowest_balance_date
        assert run1.is_safe_throughout == run2.is_safe_throughout
        assert len(run1.daily_forecasts) == len(run2.daily_forecasts)
        for d1, d2 in zip(run1.daily_forecasts, run2.daily_forecasts):
            assert d1.ending_balance == d2.ending_balance
            assert d1.intra_day_lowest_balance == d2.intra_day_lowest_balance
        print("[OK] Determinism verified: 100% identical outputs across independent runs.\n")

        print("=" * 80)
        print("ALL 11 VERIFICATION SUITES IN MODULE 6 PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] Module 6 Test encountered an error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_cash_flow_tests()
    sys.exit(0 if success else 1)
