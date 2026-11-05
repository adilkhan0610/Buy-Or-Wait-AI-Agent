"""Module 9: Spending Changes Optimizer for Buy or Wait Financial Affordability Agent.

When a purchase or payment plan is not feasible under baseline cash flow,
determines whether changing optional, flexible expenses (up to 3 changes)
can safely make the request feasible while protecting the minimum required balance.

Supported change syntax:
- stop:<event_id>
- reduce_to:<event_id>:<new_amount>

Rules:
- Modifies only flexible debit expenses identified by Module 5.
- Protected categories (rent, essential utilities, groceries, etc.) are NEVER modified.
- An event can be stopped OR reduced, never both simultaneously.
- Reductions respect minimum allowed amounts.
- Changes apply only to applicable future occurrences; historical transactions are untouched.
- Maximum of 3 changes per recommendation.
- Evaluates supplied payment options via Module 8 without inventing terms or schedules.
- Preserves original reconstructed state and baseline forecasts without mutation.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import itertools
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd

from .financial_state import (
    FinancialStateReconstructor,
    FlexibleExpenseCandidate,
    ReconstructedFinancialState,
)
from .cash_flow_engine import CashFlowEngine, ForecastResult
from .payment_plan_optimizer import (
    PaymentOptionEvaluation,
    PaymentPlanOptimizationResult,
    PaymentPlanOptimizer,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpendingChangeAction:
    """A single atomic spending change action on a flexible expense."""

    action_type: str  # 'stop' or 'reduce_to'
    event_id: str
    category: str
    description: str
    original_amount: Decimal
    new_amount: Decimal
    monthly_savings: Decimal
    action_str: str  # stop:event_id or reduce_to:event_id:new_amount


@dataclass
class SpendingChangesOptimizationResult:
    """Complete outcome of the spending changes optimization process."""

    request_id: str
    user_id: str
    has_feasible_solution: bool
    spending_changes_needed: str  # 'none' or pipe-separated actions (e.g. stop:e1|reduce_to:e2:100)
    number_of_changes: int  # 0 to 3
    selected_payment_option_id: str
    recommended_payment_method: str
    payment_plan: str
    total_principal: Decimal
    total_fees: Decimal
    total_amount_paid: Decimal
    baseline_feasible: bool
    adjusted_feasible: bool
    rejection_reasons: Dict[str, str]
    decision_explanation: str
    applied_actions: List[SpendingChangeAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "request_id": self.request_id,
            "has_feasible_solution": self.has_feasible_solution,
            "spending_changes_needed": self.spending_changes_needed,
            "number_of_changes": self.number_of_changes,
            "selected_payment_option_id": self.selected_payment_option_id,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "total_principal": float(self.total_principal),
            "total_fees": float(self.total_fees),
            "total_amount_paid": float(self.total_amount_paid),
            "baseline_feasible": self.baseline_feasible,
            "adjusted_feasible": self.adjusted_feasible,
            "rejection_reasons": self.rejection_reasons,
            "decision_explanation": self.decision_explanation,
        }


class SpendingChangesOptimizer:
    """Optimizes optional flexible spending reductions/stoppages to make purchases feasible."""

    MAX_CHANGES = 3

    def __init__(
        self,
        payment_plan_optimizer: PaymentPlanOptimizer,
        reconstructor: FinancialStateReconstructor,
        cash_flow_engine: CashFlowEngine,
    ):
        """Initialize optimizer with payment plan optimizer and upstream engines."""
        self.payment_plan_optimizer = payment_plan_optimizer
        self.reconstructor = reconstructor
        self.cash_flow_engine = cash_flow_engine

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format monetary amount: integer if integral, else exactly 2 decimal places."""
        if amount == amount.to_integral():
            return f"{int(amount)}"
        return f"{amount:.2f}"

    def _generate_candidate_actions(
        self, flexible_candidates: List[FlexibleExpenseCandidate]
    ) -> List[SpendingChangeAction]:
        """Generate all possible atomic stop and reduce_to actions from flexible expense candidates."""
        actions: List[SpendingChangeAction] = []

        for cand in flexible_candidates:
            # Action 1: Stop expense (if allowed by candidate)
            if cand.can_stop:
                action_str = f"stop:{cand.event_id}"
                actions.append(
                    SpendingChangeAction(
                        action_type="stop",
                        event_id=cand.event_id,
                        category=cand.category,
                        description=cand.description,
                        original_amount=cand.current_amount_home_currency,
                        new_amount=Decimal("0"),
                        monthly_savings=cand.current_amount_home_currency,
                        action_str=action_str,
                    )
                )

            # Action 2: Reduce expense to minimum allowed amount (if allowed and savings > 0)
            if cand.can_reduce:
                min_allowed = cand.minimum_allowed_amount_home_currency
                if min_allowed < cand.current_amount_home_currency:
                    amt_str = self._format_amount(min_allowed)
                    action_str = f"reduce_to:{cand.event_id}:{amt_str}"
                    savings = cand.current_amount_home_currency - min_allowed
                    actions.append(
                        SpendingChangeAction(
                            action_type="reduce_to",
                            event_id=cand.event_id,
                            category=cand.category,
                            description=cand.description,
                            original_amount=cand.current_amount_home_currency,
                            new_amount=min_allowed,
                            monthly_savings=savings,
                            action_str=action_str,
                        )
                    )

        return actions

    def optimize_spending_changes(
        self,
        request: Union[pd.Series, Dict[str, Any]],
        state: Optional[ReconstructedFinancialState] = None,
    ) -> SpendingChangesOptimizationResult:
        """Find the optimal set of up to 3 spending changes to make a request feasible.

        Args:
            request: Row or dict with request_id, user_id, request_date, requested_amount, desired_completion_date.
            state: Optional pre-reconstructed financial state.

        Returns:
            SpendingChangesOptimizationResult with selected plan, changes needed, and explanation.
        """
        request_id = str(request["request_id"]).strip()
        user_id = str(request["user_id"]).strip()
        request_date = str(request["request_date"]).strip()
        requested_amount = Decimal(str(request["requested_amount"]).strip())

        if state is None:
            state = self.reconstructor.reconstruct_user(user_id)

        profile = state.user_profile
        currency = profile.home_currency
        min_balance = profile.minimum_balance_to_keep

        # Step 1: Check baseline plan feasibility without spending changes
        baseline_result: PaymentPlanOptimizationResult = (
            self.payment_plan_optimizer.evaluate_options_for_request(request, state=state)
        )

        # Rule: If baseline is already feasible, require NO spending changes
        if baseline_result.has_feasible_option and baseline_result.selected_option is not None:
            winner = baseline_result.selected_option
            return SpendingChangesOptimizationResult(
                request_id=request_id,
                user_id=user_id,
                has_feasible_solution=True,
                spending_changes_needed="none",
                number_of_changes=0,
                selected_payment_option_id=winner.payment_option_id,
                recommended_payment_method=winner.payment_method,
                payment_plan=winner.payment_schedule,
                total_principal=baseline_result.total_principal,
                total_fees=baseline_result.total_fees,
                total_amount_paid=baseline_result.total_amount_paid,
                baseline_feasible=True,
                adjusted_feasible=False,
                rejection_reasons=baseline_result.rejection_reasons,
                decision_explanation=baseline_result.selection_explanation,
                applied_actions=[],
            )

        # Step 2: Baseline is NOT feasible; evaluate flexible spending changes
        atomic_actions = self._generate_candidate_actions(state.flexible_expenses)

        feasible_solutions: List[Dict[str, Any]] = []

        # Exhaustive search over subsets of size 1, 2, and 3
        for k in range(1, self.MAX_CHANGES + 1):
            for subset in itertools.combinations(atomic_actions, k):
                # Constraint: Never apply both stop and reduce_to to the same event
                event_ids = [a.event_id for a in subset]
                if len(set(event_ids)) != len(event_ids):
                    continue

                # Build spending adjustments mapping (category, description) -> new_amount and event_id -> new_amount
                adjustments: Dict[Any, Decimal] = {}
                for a in subset:
                    adjustments[(a.category, a.description)] = a.new_amount
                    adjustments[a.event_id] = a.new_amount

                # Evaluate supplied payment options under this adjusted cash flow
                adjusted_result = self.payment_plan_optimizer.evaluate_options_for_request(
                    request, state=state, spending_adjustments=adjustments
                )

                if adjusted_result.has_feasible_option and adjusted_result.selected_option is not None:
                    # Sort actions canonically by event_id for consistent output
                    sorted_actions = sorted(subset, key=lambda a: a.event_id)
                    changes_str = "|".join(a.action_str for a in sorted_actions)
                    total_savings_impact = sum(a.monthly_savings for a in sorted_actions)

                    feasible_solutions.append(
                        {
                            "subset": sorted_actions,
                            "changes_str": changes_str,
                            "number_of_changes": len(sorted_actions),
                            "total_savings_impact": total_savings_impact,
                            "adjusted_result": adjusted_result,
                            "selected_option": adjusted_result.selected_option,
                        }
                    )

        # If no valid solution exists within 3 changes
        if not feasible_solutions:
            return SpendingChangesOptimizationResult(
                request_id=request_id,
                user_id=user_id,
                has_feasible_solution=False,
                spending_changes_needed="none",
                number_of_changes=0,
                selected_payment_option_id="",
                recommended_payment_method="not_recommended",
                payment_plan="none",
                total_principal=requested_amount,
                total_fees=Decimal("0"),
                total_amount_paid=requested_amount,
                baseline_feasible=False,
                adjusted_feasible=False,
                rejection_reasons=baseline_result.rejection_reasons,
                decision_explanation=(
                    f"The purchase cannot be safely accommodated even with up to {self.MAX_CHANGES} "
                    f"optional spending changes. All supplied payment options exceed cash-flow capacity "
                    f"or violate minimum balance requirements."
                ),
                applied_actions=[],
            )

        # Step 3: Rank feasible spending-change solutions
        # Priority rules:
        # 1. Total amount paid (including fees)
        # 2. Earlier payment start
        # 3. Fewer payments
        # 4. Lowest payment_option_id
        # 5. Fewer changes (1 change < 2 changes < 3 changes)
        # 6. Lower spending reduction/cancellation impact
        # 7. Deterministic changes string tie-breaker
        feasible_solutions.sort(
            key=lambda s: (
                s["selected_option"].total_amount_paid,
                s["selected_option"].first_payment_date,
                s["selected_option"].number_of_payments,
                s["selected_option"].payment_option_id,
                s["number_of_changes"],
                s["total_savings_impact"],
                s["changes_str"],
            )
        )

        best = feasible_solutions[0]
        best_opt: PaymentOptionEvaluation = best["selected_option"]
        best_actions: List[SpendingChangeAction] = best["subset"]
        best_adj_res: PaymentPlanOptimizationResult = best["adjusted_result"]

        # Build grounded explanation
        action_descriptions: List[str] = []
        for a in best_actions:
            if a.action_type == "stop":
                action_descriptions.append(f"stop the {a.description.lower()}")
            else:
                amt_str = self._format_amount(a.new_amount)
                action_descriptions.append(f"reduce the {a.description.lower()} to {currency} {amt_str}")

        changes_narrative = " and ".join(action_descriptions)
        plan_desc = (
            f"pay {currency} {self._format_amount(best_opt.total_amount_paid)} in full on {best_opt.first_payment_date}"
            if best_opt.payment_method == "full_payment"
            else f"proceed with {best_opt.number_of_payments} installments totaling {currency} {self._format_amount(best_opt.total_amount_paid)}"
        )
        explanation = (
            f"{changes_narrative.capitalize()}, then {plan_desc}. "
            f"This preserves the {currency} {self._format_amount(min_balance)} minimum balance."
        )

        return SpendingChangesOptimizationResult(
            request_id=request_id,
            user_id=user_id,
            has_feasible_solution=True,
            spending_changes_needed=best["changes_str"],
            number_of_changes=best["number_of_changes"],
            selected_payment_option_id=best_opt.payment_option_id,
            recommended_payment_method=best_opt.payment_method,
            payment_plan=best_opt.payment_schedule,
            total_principal=best_adj_res.total_principal,
            total_fees=best_adj_res.total_fees,
            total_amount_paid=best_opt.total_amount_paid,
            baseline_feasible=False,
            adjusted_feasible=True,
            rejection_reasons=best_adj_res.rejection_reasons,
            decision_explanation=explanation,
            applied_actions=best_actions,
        )
