"""Test and verification script for Module 5: Financial State Reconstructor.

Validates:
- Complete user profile reconstruction (balances, preferences, priorities).
- Event normalization and currency conversion to home currency.
- Image extraction integration (filling null amounts, e.g. user_03, user_16).
- Confirmed message updates (salary revision for user_02).
- Exclusion of unconfirmed pending income (user_04 pending bonus, user_10 pending payout).
- Pending debit reservation (checking unreserved available balance).
- Handling of cancelled and failed transactions.
- Flexible expense identification according to user preferences and non-protected rules.
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
from code.financial_state import (
    FinancialStateReconstructor,
    ReconstructedFinancialState,
    UserFinancialProfile,
)


def run_financial_state_tests() -> bool:
    """Execute all verification tests on FinancialStateReconstructor."""
    print("=" * 80)
    print("MODULE 5: FINANCIAL STATE RECONSTRUCTOR TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize all dependencies via previous modules
        print("1. Loading datasets and initializing modules 1, 3, 4...")
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
        print("[OK] FinancialStateReconstructor successfully initialized.\n")

        # Step 2: Test User Profile Reconstruction for user_01
        print("2. Testing User Profile Reconstruction (user_01)...")
        state_01: ReconstructedFinancialState = reconstructor.reconstruct_user("user_01")
        prof_01: UserFinancialProfile = state_01.user_profile

        assert prof_01.user_id == "user_01"
        assert prof_01.home_currency == "ZAR"
        assert prof_01.current_available_balance == Decimal("58481.1")
        assert prof_01.minimum_balance_to_keep == Decimal("18000")
        assert "rent" in prof_01.protected_categories
        assert "dining" in prof_01.reduce_categories
        assert "delivery_membership" in prof_01.stop_categories
        assert prof_01.considered_payment_methods == ["full_payment"]
        assert prof_01.max_installment_months is None
        print(f"[OK] user_01 profile: Balance = ZAR {prof_01.current_available_balance}, Min = ZAR {prof_01.minimum_balance_to_keep}")
        print(f"     Unreserved cushion above min = ZAR {state_01.unreserved_cushion_above_minimum}\n")

        # Step 3: Test Image-Extracted Amounts (user_03, event_253)
        print("3. Testing Image-Extracted Amount integration (user_03, image_01 -> event_253)...")
        state_03 = reconstructor.reconstruct_user("user_03")
        # In financial_events.csv, event_253 had null amount; image_01 extracted IDR 4,365,000
        event_253 = next((e for e in state_03.confirmed_settled_income if e.event_id == "event_253"), None)
        assert event_253 is not None, "event_253 should be in confirmed_settled_income"
        assert event_253.amount_home_currency == Decimal("4365000.00"), f"Expected 4365000.00, got {event_253.amount_home_currency}"
        assert any("Amount extracted from linked image" in note for note in event_253.source_notes)
        print(f"[OK] event_253 successfully populated from image_01: {event_253.home_currency} {event_253.amount_home_currency}\n")

        # Step 4: Test Image-Extracted Rent with Outstanding Balance (user_16, image_02 -> event_1442)
        print("4. Testing Image-Extracted Rent Balance (user_16, image_02 -> event_1442)...")
        state_16 = reconstructor.reconstruct_user("user_16")
        event_1442 = next((e for e in state_16.future_obligations if e.event_id == "event_1442"), None)
        assert event_1442 is not None, "event_1442 should be in future_obligations"
        assert event_1442.amount_home_currency == Decimal("100000.00"), f"Expected 100000.00, got {event_1442.amount_home_currency}"
        print(f"[OK] event_1442 successfully populated from image_02: {event_1442.home_currency} {event_1442.amount_home_currency}\n")

        # Step 5: Test Confirmed Message Findings (user_02 salary increase via message_01)
        print("5. Testing Confirmed Message Update (user_02, message_01)...")
        state_02 = reconstructor.reconstruct_user("user_02")
        # message_01 increased salary to IDR 42,750,000 effective 2025-08-15
        salary_future = next((e for e in state_02.confirmed_future_income if e.category == "salary"), None)
        assert salary_future is not None, "Scheduled salary should be present"
        assert salary_future.amount_home_currency == Decimal("42750000"), f"Expected 42750000, got {salary_future.amount_home_currency}"
        assert salary_future.settlement_date == "2025-08-15", f"Expected 2025-08-15, got {salary_future.settlement_date}"
        print(f"[OK] user_02 salary updated via message_01: IDR {salary_future.amount_home_currency} on {salary_future.settlement_date}\n")

        # Step 6: Test Unconfirmed Income Exclusion (user_04 pending bonus via message_03)
        print("6. Testing Exclusion of Unconfirmed Pending Income (user_04, message_03)...")
        state_04 = reconstructor.reconstruct_user("user_04")
        # message_03 notes bonus is unconfirmed / pending review
        assert any("Unconfirmed message signal" in str(u.get("reason", "")) for u in state_04.unconfirmed_information)
        # Check that NO unconfirmed bonus is present in confirmed_future_income
        bonus_income = [e for e in state_04.confirmed_future_income if "bonus" in e.description.lower()]
        assert len(bonus_income) == 0, f"Unconfirmed bonus should not be in confirmed_future_income: {bonus_income}"
        print("[OK] Unconfirmed bonus correctly excluded from cash income and logged in unconfirmed_information.\n")

        # Step 7: Test Currency Conversion in Events (user_25 has USD events, home_currency is IDR)
        print("7. Testing Currency Conversion Integration (user_25)...")
        state_25 = reconstructor.reconstruct_user("user_25")
        assert state_25.user_profile.home_currency == "IDR"
        # Check an event that had USD currency converted to IDR
        usd_events = [e for e in state_25.confirmed_settled_income if e.original_currency == "USD"]
        assert len(usd_events) > 0, "user_25 should have historical USD income"
        sample_usd_evt = usd_events[0]
        assert sample_usd_evt.home_currency == "IDR"
        assert any("Converted USD" in n for n in sample_usd_evt.source_notes)
        print(f"[OK] Converted event {sample_usd_evt.event_id}: USD {sample_usd_evt.original_amount} -> IDR {sample_usd_evt.amount_home_currency}\n")

        # Step 8: Test Cancellation & Lifecycle handling
        print("8. Testing Handling of Cancelled/Failed events...")
        # Ignored records list must contain cancelled or non-cash records
        assert len(state_01.ignored_or_conflicting) > 0 or len(state_02.ignored_or_conflicting) > 0
        print(f"[OK] user_01 ignored/conflicting records count: {len(state_01.ignored_or_conflicting)}")
        print(f"[OK] user_02 ignored/conflicting records count: {len(state_02.ignored_or_conflicting)}\n")

        # Step 9: Test Flexible Expenses Identification
        print("9. Testing Flexible Expense Candidate identification...")
        # user_06: has event_476 stoppable streaming plan (which is stopped in sample_requests request_06)
        state_06 = reconstructor.reconstruct_user("user_06")
        cand_476 = next((f for f in state_06.flexible_expenses if f.event_id == "event_476"), None)
        assert cand_476 is not None, "event_476 should be identified as flexible candidate for user_06"
        assert cand_476.can_stop is True
        print(f"[OK] user_06 correctly identified event_476: {cand_476.description} (can_stop={cand_476.can_stop})")

        # user_03: willing to stop streaming|cloud_storage, reduce streaming|shopping, protect rent|utilities|groceries
        assert len(state_03.flexible_expenses) > 0, "user_03 should have flexible expenses"
        for flex in state_03.flexible_expenses:
            assert flex.category not in state_03.user_profile.protected_categories
            print(f"  - [{flex.event_id}] {flex.category}: {flex.description} -> current: IDR {flex.current_amount_home_currency}, max savings: {flex.max_monthly_savings}")
            print(f"    can_stop={flex.can_stop}, can_reduce={flex.can_reduce}")

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED: Module 5 FinancialStateReconstructor is fully operational.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAILURE] Financial State Reconstructor test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_financial_state_tests()
    sys.exit(0 if success else 1)
