"""Module 7: Affordability Engine for Buy or Wait Financial Affordability Agent.

Evaluates financial requests and determines:
- amount_safe_to_pay: Maximum amount the user can safely pay today before optional spending changes.
- affordability_status: affordable_now, affordable_with_plan, affordable_later, not_affordable.
- recommended_payment_method: full_payment, partial_payment, installments, wait, not_recommended.
- payment_plan: Formatted payment schedule or 'none'.
- earliest_date_for_full_payment: Earliest safe date for one full payment, independent of payment preferences.
- decision_explanation: Clear, grounded justification referencing exact figures and minimum balance.
"""

from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Any, Dict, Optional, Union
import pandas as pd

from .financial_state import FinancialStateReconstructor, ReconstructedFinancialState
from .cash_flow_engine import CashFlowEngine, ForecastResult

logger = logging.getLogger(__name__)


@dataclass
class AffordabilityDecision:
    """Core affordability evaluation outcome for a single purchase/payment request."""

    request_id: str
    user_id: str
    request_date: str
    requested_amount: Decimal
    desired_completion_date: str
    home_currency: str

    amount_safe_to_pay: Decimal
    affordability_status: str  # affordable_now | affordable_with_plan | affordable_later | not_affordable
    recommended_payment_method: str  # full_payment | partial_payment | installments | wait | not_recommended
    payment_plan: str  # YYYY-MM-DD:amount|... or 'none'
    earliest_date_for_full_payment: str  # YYYY-MM-DD or empty string
    spending_changes_needed: str  # 'none' or pipe-separated actions
    decision_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to a dictionary conforming to the required schema."""
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": float(self.amount_safe_to_pay),
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }


class AffordabilityEngine:
    """Evaluates purchase requests against 90-day cash-flow forecasts and user constraints."""

    VALID_AFFORDABILITY_STATUSES = {
        "affordable_now",
        "affordable_with_plan",
        "affordable_later",
        "not_affordable",
    }

    VALID_PAYMENT_METHODS = {
        "full_payment",
        "partial_payment",
        "installments",
        "wait",
        "not_recommended",
    }

    def __init__(
        self,
        reconstructor: FinancialStateReconstructor,
        cash_flow_engine: CashFlowEngine,
    ):
        """Initialize with reconstructor and cash flow engine."""
        self.reconstructor = reconstructor
        self.cash_flow_engine = cash_flow_engine

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format monetary amount cleanly: omit trailing zeros if integer, otherwise keep 2 decimals."""
        if amount == amount.to_integral():
            return f"{int(amount)}"
        return f"{amount:.2f}".rstrip("0").rstrip(".")

    def evaluate_request(
        self,
        request: Union[pd.Series, Dict[str, Any]],
        state: Optional[ReconstructedFinancialState] = None,
    ) -> AffordabilityDecision:
        """Evaluate a financial request and determine safe payment parameters.

        Args:
            request: Row or dict with request_id, user_id, request_date, requested_amount,
                     desired_completion_date, allows_partial_payment, etc.
            state: Optional pre-reconstructed financial state. Reconstructed if not supplied.

        Returns:
            AffordabilityDecision with status, safe amount, payment plan, earliest date, and explanation.
        """
        request_id = str(request["request_id"]).strip()
        user_id = str(request["user_id"]).strip()
        request_date = str(request["request_date"]).strip()
        requested_amount = Decimal(str(request["requested_amount"]).strip())
        desired_completion_date = str(request["desired_completion_date"]).strip()

        # Parse allows_partial_payment robustly
        raw_partial = request.get("allows_partial_payment", False)
        if isinstance(raw_partial, str):
            allows_partial_payment = raw_partial.strip().lower() in ("true", "1", "yes")
        else:
            allows_partial_payment = bool(raw_partial)

        # Reconstruct financial state if not provided
        if state is None:
            state = self.reconstructor.reconstruct_user(user_id)

        profile = state.user_profile
        currency = profile.home_currency
        min_balance = profile.minimum_balance_to_keep
        user_methods = profile.considered_payment_methods

        # 1. Calculate amount_safe_to_pay today (capped at requested_amount)
        # Using 90-day forecast from Module 6
        amount_safe_today = self.cash_flow_engine.calculate_amount_safe_to_pay(
            state=state,
            request_date=request_date,
            requested_amount=requested_amount,
            horizon_days=90,
        )

        # Ensure bounds: 0 <= amount_safe_to_pay <= requested_amount
        amount_safe_to_pay = max(Decimal("0"), min(requested_amount, amount_safe_today))

        # 2. Determine earliest_date_for_full_payment
        # Independent of payment preferences and spending changes
        earliest_full_date = self.cash_flow_engine.find_earliest_date_for_full_payment(
            state=state,
            request_date=request_date,
            requested_amount=requested_amount,
            max_search_days=90,
        )
        earliest_date_str = earliest_full_date if earliest_full_date else ""

        # 3. Determine Affordability Status and Recommended Payment Method

        # Case A: Affordable Now (full amount is safe today AND user accepts full_payment)
        if amount_safe_to_pay >= requested_amount and "full_payment" in user_methods:
            affordability_status = "affordable_now"
            recommended_payment_method = "full_payment"
            payment_plan = f"{request_date}:{self._format_amount(requested_amount)}"
            earliest_date_str = request_date  # Must equal request_date for affordable_now
            explanation = (
                f"Pay {currency} {self._format_amount(requested_amount)} in full on {request_date}. "
                f"Your balance remains safely above the {currency} {self._format_amount(min_balance)} "
                f"minimum throughout the 90-day forecast."
            )

        # Case B: Check for Partial Payment under affordable_with_plan
        elif (
            allows_partial_payment
            and "partial_payment" in user_methods
            and Decimal("0") < amount_safe_to_pay < requested_amount
            and earliest_full_date is not None
            and earliest_full_date <= desired_completion_date
        ):
            remaining_amount = requested_amount - amount_safe_to_pay
            affordability_status = "affordable_with_plan"
            recommended_payment_method = "partial_payment"
            payment_plan = (
                f"{request_date}:{self._format_amount(amount_safe_to_pay)}|"
                f"{earliest_full_date}:{self._format_amount(remaining_amount)}"
            )
            explanation = (
                f"Pay {currency} {self._format_amount(amount_safe_to_pay)} on {request_date} and "
                f"{currency} {self._format_amount(remaining_amount)} on {earliest_full_date}. "
                f"Full payment is completed by {desired_completion_date} while protecting your "
                f"{currency} {self._format_amount(min_balance)} minimum balance."
            )

        # Case C: Affordable Later (full payment safe on a later date within horizon and user accepts full_payment)
        elif (
            earliest_full_date is not None
            and earliest_full_date > request_date
            and "full_payment" in user_methods
        ):
            affordability_status = "affordable_later"
            recommended_payment_method = "wait"
            payment_plan = f"{earliest_full_date}:{self._format_amount(requested_amount)}"
            explanation = (
                f"Wait until {earliest_full_date}, then pay {currency} {self._format_amount(requested_amount)} "
                f"in full. Paying sooner would put the {currency} {self._format_amount(min_balance)} "
                f"minimum at risk."
            )

        # Case D: Not Affordable within the 90-day horizon
        else:
            affordability_status = "not_affordable"
            recommended_payment_method = "not_recommended"
            payment_plan = "none"
            earliest_date_str = "" if earliest_full_date is None else earliest_date_str

            if amount_safe_to_pay > Decimal("0"):
                explanation = (
                    f"The expense is not affordable. With only {currency} {self._format_amount(amount_safe_to_pay)} "
                    f"safe to commit today, committing {currency} {self._format_amount(requested_amount)} "
                    f"would breach the {currency} {self._format_amount(min_balance)} minimum balance."
                )
            else:
                explanation = (
                    f"The expense is not affordable within the 90-day forecast. Committing "
                    f"{currency} {self._format_amount(requested_amount)} would reduce available funds "
                    f"below the {currency} {self._format_amount(min_balance)} minimum required balance."
                )

        spending_changes_needed = "none"

        return AffordabilityDecision(
            request_id=request_id,
            user_id=user_id,
            request_date=request_date,
            requested_amount=requested_amount,
            desired_completion_date=desired_completion_date,
            home_currency=currency,
            amount_safe_to_pay=amount_safe_to_pay,
            affordability_status=affordability_status,
            recommended_payment_method=recommended_payment_method,
            payment_plan=payment_plan,
            earliest_date_for_full_payment=earliest_date_str,
            spending_changes_needed=spending_changes_needed,
            decision_explanation=explanation,
        )
