"""Module 8: Payment Option & Plan Evaluator for Buy or Wait Financial Affordability Agent.

Evaluates vendor payment options from request_payment_options.csv against:
- User payment method eligibility and maximum installment months.
- Cash-flow feasibility over the 90-day forecast horizon (minimum balance preservation).
- Deadline completion (desired_completion_date).
- Challenge priority ranking:
    1. Complete full request by desired_completion_date.
    2. Require no optional spending changes.
    3. Minimize total amount paid (including fees).
    4. Start payment earlier.
    5. Use fewer payments.
    6. Lowest payment_option_id tie-breaker.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from .financial_state import FinancialStateReconstructor, ReconstructedFinancialState
from .cash_flow_engine import CashFlowEngine, ForecastResult

logger = logging.getLogger(__name__)


@dataclass
class PaymentOptionEvaluation:
    """Evaluation result for a single candidate payment option."""

    payment_option_id: str
    request_id: str
    payment_method: str  # full_payment | installments
    payment_amount: Decimal
    number_of_payments: int
    first_payment_date: str
    last_payment_date: str
    payment_frequency_days: Optional[float]
    financing_fee: Decimal
    total_amount_paid: Decimal
    payment_schedule: str  # YYYY-MM-DD:amount|...
    is_feasible: bool
    rejection_reason: Optional[str] = None
    scheduled_payments: List[Tuple[str, Decimal, str]] = field(default_factory=list)


@dataclass
class PaymentPlanOptimizationResult:
    """Outcome of optimizing payment options for a single request."""

    request_id: str
    user_id: str
    has_feasible_option: bool
    selected_option: Optional[PaymentOptionEvaluation]
    payment_method: str
    payment_schedule: str
    total_principal: Decimal
    total_fees: Decimal
    total_amount_paid: Decimal
    evaluated_options: List[PaymentOptionEvaluation]
    rejection_reasons: Dict[str, str]
    selection_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "request_id": self.request_id,
            "has_feasible_option": self.has_feasible_option,
            "selected_payment_option_id": (
                self.selected_option.payment_option_id if self.selected_option else ""
            ),
            "payment_method": self.payment_method,
            "payment_schedule": self.payment_schedule,
            "total_principal": float(self.total_principal),
            "total_fees": float(self.total_fees),
            "total_amount_paid": float(self.total_amount_paid),
            "rejection_reasons": self.rejection_reasons,
            "selection_explanation": self.selection_explanation,
        }


class PaymentPlanOptimizer:
    """Evaluates and ranks supplied vendor payment options deterministically."""

    def __init__(
        self,
        payment_options_df: pd.DataFrame,
        reconstructor: FinancialStateReconstructor,
        cash_flow_engine: CashFlowEngine,
    ):
        """Initialize optimizer with payment options DataFrame and upstream engines."""
        self.payment_options_df = payment_options_df.copy()
        self.reconstructor = reconstructor
        self.cash_flow_engine = cash_flow_engine

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse YYYY-MM-DD string into datetime."""
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")

    @staticmethod
    def _format_date(dt: datetime) -> str:
        """Format datetime into YYYY-MM-DD string."""
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format monetary amount cleanly (strip redundant trailing zeros)."""
        if amount == amount.to_integral():
            return f"{int(amount)}"
        return f"{amount:.2f}".rstrip("0").rstrip(".")

    def _build_schedule_for_option(
        self, option_row: pd.Series
    ) -> Tuple[str, str, List[Tuple[str, Decimal, str]], str]:
        """Construct chronological payments, last payment date, and formatted plan string.

        Returns:
            Tuple of (first_payment_date, last_payment_date, scheduled_payments, plan_string)
        """
        first_date_str = str(option_row["first_payment_date"]).strip()
        first_dt = self._parse_date(first_date_str)
        num_payments = int(option_row["number_of_payments"])
        amt = Decimal(str(option_row["payment_amount"]))
        desc = f"Payment option {option_row['payment_option_id']}"

        raw_freq = option_row.get("payment_frequency_days")
        freq_days = float(raw_freq) if pd.notna(raw_freq) else 0.0

        scheduled_payments: List[Tuple[str, Decimal, str]] = []
        plan_parts: List[str] = []

        last_dt = first_dt

        for k in range(num_payments):
            # Calculate payment date: k * freq_days
            day_offset = int(round(k * freq_days))
            p_dt = first_dt + timedelta(days=day_offset)
            p_date_str = self._format_date(p_dt)
            scheduled_payments.append((p_date_str, amt, f"{desc} ({k+1}/{num_payments})"))
            plan_parts.append(f"{p_date_str}:{self._format_amount(amt)}")
            if p_dt > last_dt:
                last_dt = p_dt

        last_date_str = self._format_date(last_dt)
        plan_str = "|".join(plan_parts)

        return first_date_str, last_date_str, scheduled_payments, plan_str

    def evaluate_options_for_request(
        self,
        request: Union[pd.Series, Dict[str, Any]],
        state: Optional[ReconstructedFinancialState] = None,
    ) -> PaymentPlanOptimizationResult:
        """Evaluate all supplied payment options for a request and select the best feasible option.

        Args:
            request: Row or dict with request_id, user_id, request_date, requested_amount, desired_completion_date.
            state: Optional pre-reconstructed financial state.

        Returns:
            PaymentPlanOptimizationResult with evaluated candidates and selected plan.
        """
        request_id = str(request["request_id"]).strip()
        user_id = str(request["user_id"]).strip()
        request_date = str(request["request_date"]).strip()
        requested_amount = Decimal(str(request["requested_amount"]).strip())
        desired_completion_date = str(request["desired_completion_date"]).strip()

        if state is None:
            state = self.reconstructor.reconstruct_user(user_id)

        profile = state.user_profile
        currency = profile.home_currency
        min_balance = profile.minimum_balance_to_keep
        user_considered_methods = set(profile.considered_payment_methods)
        max_inst_months = profile.max_installment_months

        # Retrieve vendor options supplied for this exact request_id
        options_sub = self.payment_options_df[
            self.payment_options_df["request_id"] == request_id
        ].copy()

        evaluated_options: List[PaymentOptionEvaluation] = []
        rejection_reasons: Dict[str, str] = {}
        feasible_options: List[PaymentOptionEvaluation] = []

        for _, row in options_sub.iterrows():
            opt_id = str(row["payment_option_id"]).strip()
            method = str(row["payment_method"]).strip()
            num_payments = int(row["number_of_payments"])
            payment_amt = Decimal(str(row["payment_amount"]))
            fee = Decimal(str(row["financing_fee"]))
            total_payable = Decimal(str(row["total_payable_amount"]))
            raw_freq = row.get("payment_frequency_days")
            freq_days = float(raw_freq) if pd.notna(raw_freq) else None

            first_date, last_date, schedule, plan_str = self._build_schedule_for_option(row)

            # Check 1: User payment method eligibility
            if method not in user_considered_methods:
                reason = f"Payment method '{method}' is not in user's considered payment methods"
                rejection_reasons[opt_id] = reason
                evaluated_options.append(
                    PaymentOptionEvaluation(
                        payment_option_id=opt_id,
                        request_id=request_id,
                        payment_method=method,
                        payment_amount=payment_amt,
                        number_of_payments=num_payments,
                        first_payment_date=first_date,
                        last_payment_date=last_date,
                        payment_frequency_days=freq_days,
                        financing_fee=fee,
                        total_amount_paid=total_payable,
                        payment_schedule=plan_str,
                        is_feasible=False,
                        rejection_reason=reason,
                        scheduled_payments=schedule,
                    )
                )
                continue

            # Check 2: Maximum installment months for installment plans
            if method == "installments":
                if max_inst_months is None:
                    reason = "User does not accept installment financing"
                    rejection_reasons[opt_id] = reason
                    evaluated_options.append(
                        PaymentOptionEvaluation(
                            payment_option_id=opt_id,
                            request_id=request_id,
                            payment_method=method,
                            payment_amount=payment_amt,
                            number_of_payments=num_payments,
                            first_payment_date=first_date,
                            last_payment_date=last_date,
                            payment_frequency_days=freq_days,
                            financing_fee=fee,
                            total_amount_paid=total_payable,
                            payment_schedule=plan_str,
                            is_feasible=False,
                            rejection_reason=reason,
                            scheduled_payments=schedule,
                        )
                    )
                    continue

                if num_payments > max_inst_months:
                    reason = (
                        f"Installment count ({num_payments}) exceeds user's maximum allowed "
                        f"installment months ({max_inst_months})"
                    )
                    rejection_reasons[opt_id] = reason
                    evaluated_options.append(
                        PaymentOptionEvaluation(
                            payment_option_id=opt_id,
                            request_id=request_id,
                            payment_method=method,
                            payment_amount=payment_amt,
                            number_of_payments=num_payments,
                            first_payment_date=first_date,
                            last_payment_date=last_date,
                            payment_frequency_days=freq_days,
                            financing_fee=fee,
                            total_amount_paid=total_payable,
                            payment_schedule=plan_str,
                            is_feasible=False,
                            rejection_reason=reason,
                            scheduled_payments=schedule,
                        )
                    )
                    continue

            # Check 3: Desired completion date
            if last_date > desired_completion_date:
                reason = (
                    f"Last payment date ({last_date}) exceeds desired completion date "
                    f"({desired_completion_date})"
                )
                rejection_reasons[opt_id] = reason
                evaluated_options.append(
                    PaymentOptionEvaluation(
                        payment_option_id=opt_id,
                        request_id=request_id,
                        payment_method=method,
                        payment_amount=payment_amt,
                        number_of_payments=num_payments,
                        first_payment_date=first_date,
                        last_payment_date=last_date,
                        payment_frequency_days=freq_days,
                        financing_fee=fee,
                        total_amount_paid=total_payable,
                        payment_schedule=plan_str,
                        is_feasible=False,
                        rejection_reason=reason,
                        scheduled_payments=schedule,
                    )
                )
                continue

            # Check 4: Cash-flow safety test across forecast window
            # Ensure forecast spans at least 90 days and covers the last payment date
            req_dt = self._parse_date(request_date)
            last_dt = self._parse_date(last_date)
            days_to_last = (last_dt - req_dt).days
            sim_horizon = max(90, days_to_last)

            test_forecast = self.cash_flow_engine.run_forecast(
                state=state,
                start_date=request_date,
                horizon_days=sim_horizon,
                proposed_expenses=schedule,
            )

            if not test_forecast.is_safe_throughout:
                reason = (
                    f"Payment schedule breaches minimum balance on {test_forecast.first_breach_date} "
                    f"(shortfall: {test_forecast.max_shortfall:.2f} {currency})"
                )
                rejection_reasons[opt_id] = reason
                evaluated_options.append(
                    PaymentOptionEvaluation(
                        payment_option_id=opt_id,
                        request_id=request_id,
                        payment_method=method,
                        payment_amount=payment_amt,
                        number_of_payments=num_payments,
                        first_payment_date=first_date,
                        last_payment_date=last_date,
                        payment_frequency_days=freq_days,
                        financing_fee=fee,
                        total_amount_paid=total_payable,
                        payment_schedule=plan_str,
                        is_feasible=False,
                        rejection_reason=reason,
                        scheduled_payments=schedule,
                    )
                )
                continue

            # All checks passed: option is FEASIBLE
            eval_opt = PaymentOptionEvaluation(
                payment_option_id=opt_id,
                request_id=request_id,
                payment_method=method,
                payment_amount=payment_amt,
                number_of_payments=num_payments,
                first_payment_date=first_date,
                last_payment_date=last_date,
                payment_frequency_days=freq_days,
                financing_fee=fee,
                total_amount_paid=total_payable,
                payment_schedule=plan_str,
                is_feasible=True,
                rejection_reason=None,
                scheduled_payments=schedule,
            )
            evaluated_options.append(eval_opt)
            feasible_options.append(eval_opt)

        # If no feasible option exists
        if not feasible_options:
            return PaymentPlanOptimizationResult(
                request_id=request_id,
                user_id=user_id,
                has_feasible_option=False,
                selected_option=None,
                payment_method="not_recommended",
                payment_schedule="none",
                total_principal=requested_amount,
                total_fees=Decimal("0"),
                total_amount_paid=requested_amount,
                evaluated_options=evaluated_options,
                rejection_reasons=rejection_reasons,
                selection_explanation=(
                    f"None of the {len(options_sub)} supplied payment options are feasible. "
                    "Options either exceed installment limits, miss the completion deadline, "
                    "or cause balance breaches."
                ),
            )

        # Rank feasible options according to challenge decision rules:
        # 1. Complete by deadline (all feasible options satisfy this)
        # 2. Require no spending changes (0 for all options)
        # 3. Minimize total amount paid, including fees
        # 4. Start payment earlier (first_payment_date ascending)
        # 5. Use fewer payments (number_of_payments ascending)
        # 6. Lowest payment_option_id tie-breaker
        feasible_options.sort(
            key=lambda o: (
                o.total_amount_paid,
                o.first_payment_date,
                o.number_of_payments,
                o.payment_option_id,
            )
        )

        winner = feasible_options[0]

        if winner.payment_method == "full_payment":
            explanation = (
                f"Selected {winner.payment_option_id} ({winner.payment_method}): Pay "
                f"{currency} {self._format_amount(winner.total_amount_paid)} on {winner.first_payment_date} "
                f"with zero financing fees, maintaining minimum balance throughout."
            )
        else:
            explanation = (
                f"Selected {winner.payment_option_id} ({winner.number_of_payments} installments): "
                f"Total {currency} {self._format_amount(winner.total_amount_paid)} (fee: {self._format_amount(winner.financing_fee)}) "
                f"completing by {winner.last_payment_date} while protecting the {currency} "
                f"{self._format_amount(min_balance)} minimum balance."
            )

        return PaymentPlanOptimizationResult(
            request_id=request_id,
            user_id=user_id,
            has_feasible_option=True,
            selected_option=winner,
            payment_method=winner.payment_method,
            payment_schedule=winner.payment_schedule,
            total_principal=winner.total_amount_paid - winner.financing_fee,
            total_fees=winner.financing_fee,
            total_amount_paid=winner.total_amount_paid,
            evaluated_options=evaluated_options,
            rejection_reasons=rejection_reasons,
            selection_explanation=explanation,
        )

