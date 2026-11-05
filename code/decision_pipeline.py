"""Module 10: Decision Explanation & End-to-End Prediction Pipeline.

Integrates Modules 1 through 9 to evaluate all purchase and payment requests
in requests.csv and produces the final challenge-mandated output.csv.

Exact Output Schema:
- request_id
- amount_safe_to_pay
- affordability_status
- recommended_payment_method
- payment_plan
- earliest_date_for_full_payment
- spending_changes_needed
- decision_explanation
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .data_loader import DataLoader, Datasets
from .currency_converter import CurrencyConverter
from .message_analyzer import MessageAnalyzer
from .image_analyzer import ImageAnalyzer
from .financial_state import (
    FinancialStateReconstructor,
    ReconstructedFinancialState,
    UserFinancialProfile,
)
from .cash_flow_engine import CashFlowEngine, ForecastResult
from .payment_plan_optimizer import (
    PaymentOptionEvaluation,
    PaymentPlanOptimizationResult,
    PaymentPlanOptimizer,
)
from .spending_changes_optimizer import (
    SpendingChangeAction,
    SpendingChangesOptimizationResult,
    SpendingChangesOptimizer,
)

logger = logging.getLogger(__name__)


OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

ALLOWED_STATUSES = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

ALLOWED_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


@dataclass
class DecisionRecord:
    """Structured container for a single request decision."""

    request_id: str
    amount_safe_to_pay: str
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str
    spending_changes_needed: str
    decision_explanation: str

    def to_dict(self) -> Dict[str, str]:
        """Convert record to dictionary matching exact output schema."""
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": self.amount_safe_to_pay,
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }


class DecisionPipeline:
    """End-to-end decision pipeline integrating all Modules (1-9)."""

    def __init__(
        self,
        datasets: Optional[Datasets] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ):
        """Initialize pipeline and upstream modules with caching."""
        self.loader = DataLoader(data_dir=data_dir)
        self.datasets = datasets or self.loader.load_all()

        # Shared analytical engines
        self.currency_converter = CurrencyConverter(self.datasets.exchange_rates)
        self.message_analyzer = MessageAnalyzer(self.datasets.messages)
        self.image_analyzer = ImageAnalyzer(self.datasets.images)

        self.reconstructor = FinancialStateReconstructor(
            datasets=self.datasets,
            currency_converter=self.currency_converter,
            message_analyzer=self.message_analyzer,
            image_analyzer=self.image_analyzer,
        )

        self.cash_flow_engine = CashFlowEngine(self.reconstructor)
        self.payment_plan_optimizer = PaymentPlanOptimizer(
            payment_options_df=self.datasets.request_payment_options,
            reconstructor=self.reconstructor,
            cash_flow_engine=self.cash_flow_engine,
        )
        self.spending_changes_optimizer = SpendingChangesOptimizer(
            payment_plan_optimizer=self.payment_plan_optimizer,
            reconstructor=self.reconstructor,
            cash_flow_engine=self.cash_flow_engine,
        )

        # In-memory user state cache to ensure fast single-pass evaluation
        self._user_state_cache: Dict[str, ReconstructedFinancialState] = {}

    def get_user_state(self, user_id: str) -> ReconstructedFinancialState:
        """Retrieve cached reconstructed financial state or build and cache."""
        if user_id not in self._user_state_cache:
            self._user_state_cache[user_id] = self.reconstructor.reconstruct_user(user_id)
        return self._user_state_cache[user_id]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format monetary amount: integer if integral, else 2 decimal places."""
        if amount == amount.to_integral():
            return f"{int(amount)}"
        s = f"{amount:.2f}".rstrip("0").rstrip(".")
        return s

    @staticmethod
    def _format_date_words(date_str: str) -> str:
        """Format ISO date string (YYYY-MM-DD) into natural date (e.g. 15 November 2019)."""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return f"{dt.day} {dt.strftime('%B %Y')}"
        except Exception:
            return date_str

    @staticmethod
    def _format_currency_amount(amount: Decimal, currency: str) -> str:
        """Format amount with thousands commas and currency prefix (e.g. EUR 620.40, IDR 13,110,000)."""
        if amount == amount.to_integral():
            amt_str = f"{int(amount):,}"
        else:
            amt_str = f"{amount:,.2f}".rstrip("0").rstrip(".")
        return f"{currency} {amt_str}"

    def evaluate_request(
        self, request: Union[pd.Series, Dict[str, Any]]
    ) -> DecisionRecord:
        """Evaluate a single request row and return a validated DecisionRecord."""
        request_id = str(request["request_id"]).strip()
        user_id = str(request["user_id"]).strip()
        request_date = str(request["request_date"]).strip()
        requested_amount = Decimal(str(request["requested_amount"]).strip())
        desired_completion_date = str(request["desired_completion_date"]).strip()

        # Parse boolean allows_partial_payment safely
        raw_partial = request.get("allows_partial_payment", False)
        if isinstance(raw_partial, str):
            allows_partial_payment = raw_partial.strip().lower() in ("true", "1", "yes")
        else:
            allows_partial_payment = bool(raw_partial)

        # Retrieve user state
        state = self.get_user_state(user_id)
        profile: UserFinancialProfile = state.user_profile
        currency = profile.home_currency
        min_balance = profile.minimum_balance_to_keep
        user_considered_methods = set(profile.considered_payment_methods)

        # Step 1: Calculate amount safe to pay today (unconstrained by vendor options or spending changes)
        amount_safe_today = self.cash_flow_engine.calculate_amount_safe_to_pay(
            state=state,
            request_date=request_date,
            requested_amount=requested_amount,
        )
        # Ensure bounds: 0 <= amount_safe_to_pay <= requested_amount
        amount_safe_today = max(Decimal("0"), min(amount_safe_today, requested_amount))
        amount_safe_today_str = self._format_amount(amount_safe_today)

        # Step 2: Calculate earliest date for full payment (independent of payment preferences and spending changes)
        earliest_full_date = self.cash_flow_engine.find_earliest_date_for_full_payment(
            state=state,
            request_date=request_date,
            requested_amount=requested_amount,
        )
        earliest_full_date_str = earliest_full_date if earliest_full_date is not None else ""

        # Step 3: Evaluate baseline vendor payment options from request_payment_options.csv
        baseline_options_result: PaymentPlanOptimizationResult = (
            self.payment_plan_optimizer.evaluate_options_for_request(request, state=state)
        )

        # Step 4: Check if partial payment is viable as a candidate baseline plan
        partial_plan_candidate: Optional[Dict[str, Any]] = None
        if (
            allows_partial_payment
            and "partial_payment" in user_considered_methods
            and Decimal("0") < amount_safe_today < requested_amount
            and earliest_full_date_str != ""
            and earliest_full_date_str <= desired_completion_date
        ):
            p1 = amount_safe_today
            p2 = requested_amount - amount_safe_today
            p_sched = f"{request_date}:{self._format_amount(p1)}|{earliest_full_date_str}:{self._format_amount(p2)}"
            partial_plan_candidate = {
                "payment_method": "partial_payment",
                "payment_option_id": "partial_payment",
                "first_payment_date": request_date,
                "last_payment_date": earliest_full_date_str,
                "number_of_payments": 2,
                "total_principal": requested_amount,
                "total_fees": Decimal("0"),
                "total_amount_paid": requested_amount,
                "payment_schedule": p_sched,
                "p1": p1,
                "p2": p2,
            }

        # Step 5: Select winning baseline plan (if any)
        # Decision between vendor option and partial payment follows challenge ranking:
        # 1. Total amount paid (including fees)
        # 2. Earlier first payment date
        # 3. Fewer payments
        # 4. Lowest ID
        winning_baseline: Optional[Dict[str, Any]] = None

        if baseline_options_result.has_feasible_option and baseline_options_result.selected_option is not None:
            opt = baseline_options_result.selected_option
            # If full payment on request date was selected, verify safe amount covers it today
            if opt.payment_method == "full_payment" and opt.first_payment_date == request_date:
                if amount_safe_today >= requested_amount:
                    winning_baseline = {
                        "type": "vendor_option",
                        "option": opt,
                        "payment_method": "full_payment",
                        "total_amount_paid": opt.total_amount_paid,
                        "first_payment_date": opt.first_payment_date,
                        "number_of_payments": opt.number_of_payments,
                        "payment_option_id": opt.payment_option_id,
                        "payment_schedule": opt.payment_schedule,
                    }
            else:
                winning_baseline = {
                    "type": "vendor_option",
                    "option": opt,
                    "payment_method": opt.payment_method,
                    "total_amount_paid": opt.total_amount_paid,
                    "first_payment_date": opt.first_payment_date,
                    "number_of_payments": opt.number_of_payments,
                    "payment_option_id": opt.payment_option_id,
                    "payment_schedule": opt.payment_schedule,
                }

        # Compare winning vendor option with partial payment candidate if available
        if partial_plan_candidate is not None:
            if winning_baseline is None:
                winning_baseline = {
                    "type": "partial_payment",
                    "payment_method": "partial_payment",
                    "total_amount_paid": partial_plan_candidate["total_amount_paid"],
                    "first_payment_date": partial_plan_candidate["first_payment_date"],
                    "number_of_payments": partial_plan_candidate["number_of_payments"],
                    "payment_option_id": partial_plan_candidate["payment_option_id"],
                    "payment_schedule": partial_plan_candidate["payment_schedule"],
                    "details": partial_plan_candidate,
                }
            else:
                # Rank: total_amount_paid, first_payment_date, number_of_payments
                cand_key = (
                    partial_plan_candidate["total_amount_paid"],
                    partial_plan_candidate["first_payment_date"],
                    partial_plan_candidate["number_of_payments"],
                )
                curr_key = (
                    winning_baseline["total_amount_paid"],
                    winning_baseline["first_payment_date"],
                    winning_baseline["number_of_payments"],
                )
                if cand_key < curr_key:
                    winning_baseline = {
                        "type": "partial_payment",
                        "payment_method": "partial_payment",
                        "total_amount_paid": partial_plan_candidate["total_amount_paid"],
                        "first_payment_date": partial_plan_candidate["first_payment_date"],
                        "number_of_payments": partial_plan_candidate["number_of_payments"],
                        "payment_option_id": partial_plan_candidate["payment_option_id"],
                        "payment_schedule": partial_plan_candidate["payment_schedule"],
                        "details": partial_plan_candidate,
                    }

        # Case A: Feasible Baseline Plan Found
        if winning_baseline is not None:
            method = winning_baseline["payment_method"]
            plan_str = winning_baseline["payment_schedule"]

            if method == "full_payment":
                status = "affordable_now"
                earliest_full_date_str = request_date
                explanation = (
                    f"Pay {currency} {self._format_amount(requested_amount)} today. "
                    f"This leaves at least {currency} {self._format_amount(min_balance)} available over the next 90 days."
                )
            elif method == "partial_payment":
                status = "affordable_with_plan"
                p_details = winning_baseline.get("details", {})
                p1_val = p_details.get("p1", amount_safe_today)
                p2_val = p_details.get("p2", requested_amount - amount_safe_today)
                explanation = (
                    f"Pay {currency} {self._format_amount(p1_val)} today and the remaining "
                    f"{currency} {self._format_amount(p2_val)} on {self._format_date_words(earliest_full_date_str)}. "
                    f"This completes the full request and keeps the {currency} {self._format_amount(min_balance)} minimum protected."
                )
            else:  # installments
                status = "affordable_with_plan"
                opt_obj: PaymentOptionEvaluation = winning_baseline["option"]
                num_inst = opt_obj.number_of_payments
                inst_amt = opt_obj.payment_amount
                start_w = self._format_date_words(opt_obj.first_payment_date)
                explanation = (
                    f"Use {num_inst} installments of {currency} {self._format_amount(inst_amt)}, "
                    f"starting {start_w}. This leaves at least {currency} {self._format_amount(min_balance)} available."
                )

            return DecisionRecord(
                request_id=request_id,
                amount_safe_to_pay=amount_safe_today_str,
                affordability_status=status,
                recommended_payment_method=method,
                payment_plan=plan_str,
                earliest_date_for_full_payment=earliest_full_date_str,
                spending_changes_needed="none",
                decision_explanation=explanation,
            )

        # Step 6: Baseline is NOT feasible — evaluate spending changes (Module 9)
        spending_result: SpendingChangesOptimizationResult = (
            self.spending_changes_optimizer.optimize_spending_changes(request, state=state)
        )

        if spending_result.has_feasible_solution and spending_result.adjusted_feasible:
            return DecisionRecord(
                request_id=request_id,
                amount_safe_to_pay=amount_safe_today_str,
                affordability_status="affordable_with_plan",
                recommended_payment_method=spending_result.recommended_payment_method,
                payment_plan=spending_result.payment_plan,
                earliest_date_for_full_payment=earliest_full_date_str,
                spending_changes_needed=spending_result.spending_changes_needed,
                decision_explanation=spending_result.decision_explanation,
            )

        # Step 7: Not affordable now or with plan — check if user can wait (affordable_later)
        if "full_payment" in user_considered_methods and earliest_full_date_str != "":
            wait_date_words = self._format_date_words(earliest_full_date_str)
            explanation = (
                f"Wait until {wait_date_words}, then pay {currency} {self._format_amount(requested_amount)} in full. "
                f"Paying sooner would put the {currency} {self._format_amount(min_balance)} minimum at risk."
            )
            return DecisionRecord(
                request_id=request_id,
                amount_safe_to_pay=amount_safe_today_str,
                affordability_status="affordable_later",
                recommended_payment_method="wait",
                payment_plan=f"{earliest_full_date_str}:{self._format_amount(requested_amount)}",
                earliest_date_for_full_payment=earliest_full_date_str,
                spending_changes_needed="none",
                decision_explanation=explanation,
            )

        # Step 8: Completely unaffordable within forecast horizon (not_affordable)
        deadline_words = self._format_date_words(desired_completion_date)
        explanation = (
            f"Do not make this payment by {deadline_words}. None of the available options keeps "
            f"the {currency} {self._format_amount(min_balance)} minimum protected."
        )
        return DecisionRecord(
            request_id=request_id,
            amount_safe_to_pay=amount_safe_today_str,
            affordability_status="not_affordable",
            recommended_payment_method="not_recommended",
            payment_plan="none",
            earliest_date_for_full_payment="",
            spending_changes_needed="none",
            decision_explanation=explanation,
        )

    def process_all_requests(
        self, requests_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Process every request in requests_df and return DataFrame in exact output schema."""
        if requests_df is None:
            requests_df = self.datasets.requests

        records: List[Dict[str, str]] = []
        total = len(requests_df)
        logger.info("Processing %d requests through DecisionPipeline...", total)

        for idx, (_, row) in enumerate(requests_df.iterrows(), start=1):
            rec = self.evaluate_request(row)
            records.append(rec.to_dict())

        output_df = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
        return output_df

    def write_output_csv(
        self,
        output_df: pd.DataFrame,
        output_paths: Optional[List[Union[str, Path]]] = None,
    ) -> List[Path]:
        """Write output DataFrame to designated target paths with exact schema and quotes."""
        if output_paths is None:
            output_paths = [
                self.loader.data_dir.parent / "output.csv",
                self.loader.data_dir / "output.csv",
            ]

        written: List[Path] = []
        for p in output_paths:
            target = Path(p).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            output_df.to_csv(target, index=False, columns=OUTPUT_COLUMNS)
            written.append(target)
            logger.info("Wrote %d predictions to %s", len(output_df), target)

        return written

    def generate_usage_report(
        self,
        output_path: Optional[Union[str, Path]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        num_requests: int = 250,
    ) -> Path:
        """Generate evaluation/usage_report.md summarizing model calls, tokens, and cost."""
        if output_path is None:
            target = self.loader.data_dir.parent / "evaluation" / "usage_report.md"
        else:
            target = Path(output_path).resolve()

        target.parent.mkdir(parents=True, exist_ok=True)

        duration_sec = (end_time - start_time).total_seconds() if (start_time and end_time) else 0.0

        content = f"""# Token Usage and Model Call Report

HackerRank Orchestrate — Buy or Wait?
Final Evaluation Run Summary

## 1. Executive Summary

| Metric | Value |
|---|---|
| Execution Timestamp | {datetime.utcnow().isoformat()}Z |
| Total Requests Evaluated | {num_requests} |
| Total Execution Time | {duration_sec:.2f} seconds |
| Average Execution Time / Request | {(duration_sec / max(1, num_requests) * 1000):.2f} ms |
| Decision Engine Architecture | Deterministic Algorithmic Simulation Pipeline |
| Model Calls | 0 |
| Total Input Tokens | 0 |
| Total Output Tokens | 0 |
| Total Tokens | 0 |
| Average Tokens / Request | 0.0 |
| Estimated Total Cost | $0.00 |
| Estimated Cost / Request | $0.00 |

## 2. Model Calls Breakdown

| Provider | Model Name | Calls | Input Tokens | Output Tokens | Total Tokens | Est. Cost (USD) |
|---|---|---|---|---|---|---|
| None (Local Deterministic) | Rules & Cash-Flow Engine | 0 | 0 | 0 | 0 | $0.00 |
| **Total** | | **0** | **0** | **0** | **0** | **$0.00** |

## 3. Computational Methodology

The Buy or Wait? financial decision agent executes fully offline and deterministically without external LLM API inference calls during prediction time:

1. **Reconstruction & Disambiguation**: Deterministic date-indexed currency conversion, verified regex-anchored multilingual transaction parsing, and OCR receipt linkage.
2. **Cash Flow Simulation**: 90-day day-by-day cash flow ledger with strict debit-first intraday ordering and minimum required balance preservation.
3. **Multi-Plan Evaluation**: Combinatorial ranking over supplied vendor options, request-level partial plans, and up to 3 optional flexible spending changes.
4. **Reproducibility**: 100% deterministic, 0 API dependencies, 0 latency overhead, zero token expenditure.
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        # Also write inside code/evaluation/usage_report.md if repo has code/evaluation folder
        alt_target = self.loader.data_dir.parent / "code" / "evaluation" / "usage_report.md"
        if alt_target.parent.exists():
            with open(alt_target, "w", encoding="utf-8") as f:
                f.write(content)

        return target

    def run(
        self,
        requests_df: Optional[pd.DataFrame] = None,
        output_paths: Optional[List[Union[str, Path]]] = None,
    ) -> pd.DataFrame:
        """Execute the full end-to-end pipeline from datasets to output.csv and usage report."""
        t_start = datetime.utcnow()
        if requests_df is None:
            requests_df = self.datasets.requests

        output_df = self.process_all_requests(requests_df)
        self.write_output_csv(output_df, output_paths=output_paths)
        t_end = datetime.utcnow()

        self.generate_usage_report(
            start_time=t_start,
            end_time=t_end,
            num_requests=len(output_df),
        )

        return output_df

