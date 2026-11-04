"""Module 3: Dated Currency Converter for Buy or Wait Financial Affordability Agent.

Provides high-precision monetary conversions using dated, fixed exchange rates
from exchange_rates.csv according to the challenge specification.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional, Set, Tuple, Union
import logging
import pandas as pd

logger = logging.getLogger(__name__)

VALID_CURRENCIES: Set[str] = {"INR", "ZAR", "IDR", "USD", "EUR"}


class CurrencyConverterError(Exception):
    """Base exception for all currency conversion errors."""
    pass


class ExchangeRateNotFoundError(CurrencyConverterError):
    """Raised when an exchange rate is missing for the given date and currency pair."""
    pass


class InvalidCurrencyError(CurrencyConverterError):
    """Raised when an invalid, unsupported, or blank currency code is provided."""
    pass


class InvalidAmountError(CurrencyConverterError):
    """Raised when an invalid, negative, or unparseable amount is provided."""
    pass


class CurrencyConverter:
    """High-precision dated currency converter backed by exchange_rates.csv."""

    def __init__(self, exchange_rates_df: pd.DataFrame):
        """Initialize the converter with an exchange_rates DataFrame.

        Args:
            exchange_rates_df: DataFrame containing rate_date, from_currency,
                               to_currency, and rate columns.

        Raises:
            ValueError: If required columns are missing from exchange_rates_df.
        """
        required_cols = {"rate_date", "from_currency", "to_currency", "rate"}
        missing_cols = required_cols - set(exchange_rates_df.columns)
        if missing_cols:
            raise ValueError(
                f"exchange_rates_df missing required columns: {sorted(list(missing_cols))}"
            )

        self._rates: Dict[Tuple[str, str, str], Decimal] = {}
        self._available_pairs: Set[Tuple[str, str]] = set()
        self._available_dates: Set[str] = set()

        self._index_rates(exchange_rates_df)

    def _index_rates(self, df: pd.DataFrame) -> None:
        """Parse and store exchange rates into an indexed lookup dictionary."""
        for _, row in df.iterrows():
            date_str = str(row["rate_date"]).strip()
            from_curr = str(row["from_currency"]).strip().upper()
            to_curr = str(row["to_currency"]).strip().upper()

            try:
                rate_val = Decimal(str(row["rate"]))
            except (InvalidOperation, TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid exchange rate value '{row['rate']}' for {from_curr}->{to_curr} on {date_str}: {e}"
                ) from e

            if rate_val <= Decimal("0"):
                raise ValueError(
                    f"Non-positive exchange rate '{rate_val}' for {from_curr}->{to_curr} on {date_str}"
                )

            key = (date_str, from_curr, to_curr)
            self._rates[key] = rate_val
            self._available_pairs.add((from_curr, to_curr))
            self._available_dates.add(date_str)

    @staticmethod
    def _normalize_date(rate_date: Union[str, date, datetime]) -> str:
        """Convert string, date, or datetime into a canonical YYYY-MM-DD string."""
        if isinstance(rate_date, (datetime, date)):
            return rate_date.strftime("%Y-%m-%d")
        if isinstance(rate_date, str):
            clean_date = rate_date.strip()
            # If ISO timestamp (e.g. contains 'T'), take the date component
            if "T" in clean_date:
                clean_date = clean_date.split("T")[0]
            if len(clean_date) == 10 and clean_date[4] == "-" and clean_date[7] == "-":
                return clean_date
            # Try parsing
            try:
                dt = datetime.strptime(clean_date, "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError as e:
                raise ValueError(f"Invalid date format '{rate_date}', expected YYYY-MM-DD") from e
        raise TypeError(f"Expected str, date, or datetime for rate_date, got {type(rate_date).__name__}")

    @staticmethod
    def _normalize_currency(currency: str, param_name: str = "currency") -> str:
        """Validate and return normalized uppercase 3-letter currency code."""
        if not isinstance(currency, str):
            raise InvalidCurrencyError(f"{param_name} must be a string, got {type(currency).__name__}")
        clean = currency.strip().upper()
        if not clean:
            raise InvalidCurrencyError(f"{param_name} cannot be blank")
        if clean not in VALID_CURRENCIES:
            raise InvalidCurrencyError(
                f"Unsupported currency '{clean}' for {param_name}. Supported: {sorted(list(VALID_CURRENCIES))}"
            )
        return clean

    @staticmethod
    def _normalize_amount(amount: Union[Decimal, float, int, str], allow_negative: bool = False) -> Decimal:
        """Convert amount to Decimal and validate."""
        if amount is None:
            raise InvalidAmountError("Amount cannot be None")

        try:
            # Handle float NaN / Inf
            if isinstance(amount, float):
                import math
                if math.isnan(amount) or math.isinf(amount):
                    raise InvalidAmountError(f"Invalid floating-point amount '{amount}'")
            dec_amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError) as e:
            raise InvalidAmountError(f"Cannot convert amount '{amount}' to Decimal: {e}") from e

        if not allow_negative and dec_amount < Decimal("0"):
            raise InvalidAmountError(f"Amount cannot be negative: {dec_amount}")

        return dec_amount

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Union[str, date, datetime],
    ) -> Decimal:
        """Retrieve the exact exchange rate for the given currency pair and date.

        If from_currency == to_currency, returns Decimal('1.0') without requiring
        a rate record.

        Raises:
            InvalidCurrencyError: If currency codes are invalid or unsupported.
            ExchangeRateNotFoundError: If no rate exists for the pair on the given date.
        """
        source = self._normalize_currency(from_currency, "from_currency")
        target = self._normalize_currency(to_currency, "to_currency")

        if source == target:
            return Decimal("1.0")

        date_key = self._normalize_date(rate_date)
        key = (date_key, source, target)

        if key in self._rates:
            return self._rates[key]

        raise ExchangeRateNotFoundError(
            f"No exchange rate found for {source} -> {target} on date '{date_key}'. "
            f"Available dates count: {len(self._available_dates)}"
        )

    def convert(
        self,
        amount: Union[Decimal, float, int, str],
        from_currency: str,
        to_currency: str,
        rate_date: Union[str, date, datetime],
        round_digits: Optional[int] = None,
        allow_negative: bool = False,
    ) -> Decimal:
        """Convert a monetary amount from source currency to target currency.

        Args:
            amount: The monetary amount to convert.
            from_currency: Source currency code (e.g. 'USD').
            to_currency: Target currency code (e.g. 'IDR').
            rate_date: The date for the fixed exchange rate (settlement_date for events).
            round_digits: Optional number of decimal places to round to using ROUND_HALF_UP.
            allow_negative: Whether negative amounts are allowed.

        Returns:
            Converted amount as Decimal.

        Raises:
            InvalidAmountError: If amount is invalid or negative (when not allowed).
            InvalidCurrencyError: If currency codes are unknown.
            ExchangeRateNotFoundError: If no matching rate exists on rate_date.
        """
        dec_amount = self._normalize_amount(amount, allow_negative=allow_negative)
        source = self._normalize_currency(from_currency, "from_currency")
        target = self._normalize_currency(to_currency, "to_currency")

        if source == target:
            result = dec_amount
        else:
            rate = self.get_rate(source, target, rate_date)
            result = dec_amount * rate

        if round_digits is not None:
            if round_digits < 0:
                raise ValueError("round_digits cannot be negative")
            quantize_pattern = Decimal("1") if round_digits == 0 else Decimal("1." + "0" * round_digits)
            result = result.quantize(quantize_pattern, rounding=ROUND_HALF_UP)

        return result

    def convert_to_home_currency(
        self,
        amount: Union[Decimal, float, int, str],
        currency: str,
        home_currency: str,
        settlement_date: Union[str, date, datetime],
        round_digits: Optional[int] = None,
        allow_negative: bool = False,
    ) -> Decimal:
        """Convert an event amount to the user's home currency using settlement_date.

        Convenience wrapper following AGENTS.md §6.1:
        'For a foreign-currency cash event, use the row for its settlement date
        and the stated from_currency to to_currency direction.'
        """
        return self.convert(
            amount=amount,
            from_currency=currency,
            to_currency=home_currency,
            rate_date=settlement_date,
            round_digits=round_digits,
            allow_negative=allow_negative,
        )

    def convert_event(
        self,
        event_row: Union[pd.Series, Dict[str, Any]],
        home_currency: str,
        round_digits: Optional[int] = None,
    ) -> Decimal:
        """Convert a financial event's amount to the user's home currency.

        Reads event_row['amount'], event_row['currency'], and event_row['settlement_date'].
        If settlement_date is missing or blank, falls back to event_row['event_date'].

        Raises:
            InvalidAmountError: If event_row has blank or null amount.
            ExchangeRateNotFoundError: If rate is missing.
        """
        amt = event_row.get("amount") if isinstance(event_row, dict) else event_row["amount"]
        if amt is None or pd.isna(amt):
            evt_id = event_row.get("event_id", "unknown")
            raise InvalidAmountError(
                f"Financial event '{evt_id}' has blank amount (requires image extraction first)"
            )

        curr = event_row.get("currency") if isinstance(event_row, dict) else event_row["currency"]

        # Date selection: use settlement_date per §6.1, fallback to event_date if absent
        settle_dt = event_row.get("settlement_date") if isinstance(event_row, dict) else event_row["settlement_date"]
        if settle_dt is None or pd.isna(settle_dt) or str(settle_dt).strip() == "":
            settle_dt = event_row.get("event_date") if isinstance(event_row, dict) else event_row["event_date"]

        return self.convert_to_home_currency(
            amount=amt,
            currency=str(curr),
            home_currency=home_currency,
            settlement_date=settle_dt,
            round_digits=round_digits,
        )

