"""Test and verification script for Module 3: Dated Currency Converter.

Verifies:
- Same-currency conversion (no lookup needed, preserves precision).
- Conversion using real rates from exchange_rates.csv.
- Date-specific conversion (checking correct settlement_date mapping).
- Missing rate handling (raises ExchangeRateNotFoundError).
- Invalid amount handling (raises InvalidAmountError on negative/NaN/None).
- Home currency conversion helper (including financial event conversion).
"""

from datetime import date
from decimal import Decimal
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader
from code.currency_converter import (
    CurrencyConverter,
    ExchangeRateNotFoundError,
    InvalidCurrencyError,
    InvalidAmountError,
)


def run_currency_converter_tests() -> bool:
    """Execute all verification tests on CurrencyConverter."""
    print("=" * 80)
    print("MODULE 3: DATED CURRENCY CONVERTER TEST")
    print("=" * 80)

    try:
        # Load datasets via Module 1
        print("1. Loading exchange_rates dataset via DataLoader...")
        loader = DataLoader()
        datasets = loader.load_all()
        er_df = datasets.exchange_rates
        converter = CurrencyConverter(er_df)
        print(f"[OK] Initialized CurrencyConverter with {len(er_df)} exchange rate records.\n")

        # Test 1: Same-currency conversion
        print("2. Testing same-currency conversion...")
        amt_zar = Decimal("1500.50")
        res_zar = converter.convert(amt_zar, "ZAR", "ZAR", "2024-01-15")
        assert res_zar == amt_zar, f"Expected {amt_zar}, got {res_zar}"

        res_idr = converter.convert(5000000, "IDR", "IDR", "2025-08-05")
        assert res_idr == Decimal("5000000"), f"Expected 5000000, got {res_idr}"
        print(f"[OK] Same-currency conversion preserved exact values: ZAR {res_zar}, IDR {res_idr}\n")

        # Test 2: Actual dataset conversions with real rates and dates
        print("3. Testing actual dataset conversions...")
        # In dataset: 2023-10-15: EUR -> ZAR rate = 20.00
        # 100 EUR -> 2000.00 ZAR
        conv1 = converter.convert(100, "EUR", "ZAR", "2023-10-15")
        assert conv1 == Decimal("2000.00"), f"Expected 2000.00, got {conv1}"
        print(f"[OK] 100 EUR on 2023-10-15 -> ZAR {conv1} (rate: 20.00)")

        # In dataset: 2023-10-15: USD -> IDR rate = 15833.33
        # 1800 USD -> 28499994.00 IDR
        conv2 = converter.convert(Decimal("1800.00"), "USD", "IDR", "2023-10-15")
        assert conv2 == Decimal("28499994.0000"), f"Expected 28499994.0000, got {conv2}"
        print(f"[OK] 1800 USD on 2023-10-15 -> IDR {conv2} (rate: 15833.33)")

        # In dataset: 2024-01-15: USD -> INR rate = 83.33
        # 3048 USD -> 253989.84 INR
        conv3 = converter.convert("3048", "USD", "INR", "2024-01-15")
        assert conv3 == Decimal("253989.84"), f"Expected 253989.84, got {conv3}"
        print(f"[OK] 3048 USD on 2024-01-15 -> INR {conv3} (rate: 83.33)\n")

        # Test 3: Date handling (str vs date object)
        print("4. Testing date object handling...")
        date_obj = date(2023, 10, 15)
        conv_date = converter.convert(50, "EUR", "ZAR", date_obj)
        assert conv_date == Decimal("1000.00"), f"Expected 1000.00, got {conv_date}"
        print(f"[OK] Successfully accepted datetime.date(2023, 10, 15): {conv_date}\n")

        # Test 4: Missing rate scenario
        print("5. Testing missing exchange rate scenario...")
        missing_caught = False
        try:
            # Date 2010-01-01 does not exist in exchange_rates.csv
            converter.convert(100, "USD", "EUR", "2010-01-01")
        except ExchangeRateNotFoundError as e:
            missing_caught = True
            print(f"[OK] Correctly raised ExchangeRateNotFoundError: {e}")
        assert missing_caught, "Expected ExchangeRateNotFoundError for missing date"

        missing_pair_caught = False
        try:
            # Pair ZAR -> USD is not in dataset
            converter.convert(100, "ZAR", "USD", "2023-10-15")
        except ExchangeRateNotFoundError as e:
            missing_pair_caught = True
            print(f"[OK] Correctly raised ExchangeRateNotFoundError for missing direction: {e}\n")
        assert missing_pair_caught, "Expected ExchangeRateNotFoundError for unquoted pair"

        # Test 5: Invalid amount handling
        print("6. Testing invalid amount handling...")
        for bad_amt in [-100, "-50.25", None, float("nan")]:
            caught = False
            try:
                converter.convert(bad_amt, "USD", "IDR", "2023-10-15")
            except InvalidAmountError:
                caught = True
            assert caught, f"Expected InvalidAmountError for bad amount {bad_amt}"
        print("[OK] Correctly rejected negative, None, and NaN amounts with InvalidAmountError.\n")

        # Test 6: Conversion to home currency helper
        print("7. Testing convert_to_home_currency and convert_event helpers...")
        home_res = converter.convert_to_home_currency(
            amount=500,
            currency="USD",
            home_currency="EUR",
            settlement_date="2023-10-15",
            round_digits=2,
        )
        # USD -> EUR rate is 0.92 on 2023-10-15: 500 * 0.92 = 460.00
        assert home_res == Decimal("460.00"), f"Expected 460.00, got {home_res}"
        print(f"[OK] convert_to_home_currency: 500 USD -> EUR {home_res} (rate: 0.92)")

        # Test with a real foreign event row from financial_events.csv (event_2167)
        fe_df = datasets.financial_events
        row_2167 = fe_df[fe_df["event_id"] == "event_2167"].iloc[0]
        # event_2167 is USD 1800 with settlement_date 2023-10-15, user_78 home_currency is IDR
        event_converted = converter.convert_event(row_2167, home_currency="IDR")
        assert event_converted == Decimal("28499994.000"), f"Expected 28499994.000, got {event_converted}"
        print(f"[OK] convert_event on event_2167 (USD 1800 -> IDR) = {event_converted}\n")

        print("=" * 80)
        print("ALL TESTS PASSED: Module 3 CurrencyConverter is fully operational.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAILURE] CurrencyConverter test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_currency_converter_tests()
    sys.exit(0 if success else 1)

