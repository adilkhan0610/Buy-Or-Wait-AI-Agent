"""Module 6: 90-Day Cash Flow Engine for Buy or Wait Financial Affordability Agent.

Simulates and projects daily available cash balances over a 90-day forecast horizon
based on reconstructed financial state, confirmed obligations, and recurring streams.
Enforces minimum balance protection and conservative intra-day debit-first ordering.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd

from .financial_state import (
    FinancialStateReconstructor,
    NormalizedEvent,
    ReconstructedFinancialState,
    UserFinancialProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class DailyCashFlow:
    """Cash flow record for a single forecast day."""

    date: str  # YYYY-MM-DD
    day_index: int  # 0 to 90
    starting_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    intra_day_lowest_balance: Decimal
    ending_balance: Decimal
    minimum_required_balance: Decimal
    cushion_above_minimum: Decimal
    is_safe: bool
    shortfall: Decimal
    applied_events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ForecastResult:
    """Complete 90-day cash flow simulation outcome."""

    user_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD (start_date + 90 days)
    horizon_days: int
    home_currency: str
    initial_balance: Decimal
    minimum_balance_to_keep: Decimal

    daily_forecasts: List[DailyCashFlow]

    is_safe_throughout: bool
    lowest_balance: Decimal
    lowest_balance_date: str
    first_breach_date: Optional[str]
    max_shortfall: Decimal

    def get_forecast_for_date(self, target_date: str) -> Optional[DailyCashFlow]:
        """Retrieve daily cash flow for a specific date within the forecast."""
        for d in self.daily_forecasts:
            if d.date == target_date:
                return d
        return None

    def minimum_cushion_from_date(self, from_date: str) -> Decimal:
        """Calculate the lowest cushion above minimum balance from a given date onwards."""
        cushions = [
            d.intra_day_lowest_balance - self.minimum_balance_to_keep
            for d in self.daily_forecasts
            if d.date >= from_date
        ]
        return min(cushions) if cushions else Decimal("0")


class CashFlowEngine:
    """Deterministic, high-precision cash-flow forecasting engine."""

    def __init__(self, reconstructor: FinancialStateReconstructor):
        """Initialize CashFlowEngine with a FinancialStateReconstructor."""
        self.reconstructor = reconstructor

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse YYYY-MM-DD string into a datetime object."""
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")

    @staticmethod
    def _format_date(dt: datetime) -> str:
        """Format datetime object into YYYY-MM-DD string."""
        return dt.strftime("%Y-%m-%d")

    def run_forecast(
        self,
        state: ReconstructedFinancialState,
        start_date: str,
        horizon_days: int = 90,
        proposed_expenses: Optional[List[Tuple[str, Decimal, str]]] = None,
    ) -> ForecastResult:
        """Execute a 90-day daily cash-flow simulation.

        Args:
            state: ReconstructedFinancialState from Module 5.
            start_date: The evaluation date (YYYY-MM-DD).
            horizon_days: Number of forecast days (default: 90).
            proposed_expenses: Optional list of proposed payments as (date, amount, description).

        Returns:
            ForecastResult with full day-by-day cash flows, safety flags, and minimum balances.
        """
        start_dt = self._parse_date(start_date)
        end_dt = start_dt + timedelta(days=horizon_days)
        end_date = self._format_date(end_dt)

        profile = state.user_profile
        min_balance = profile.minimum_balance_to_keep

        # Starting cash on start_date is the unreserved available balance
        # (current balance minus pending debits that are clearing immediately)
        current_cash = state.unreserved_available_balance

        # Build chronological event schedule for the 90-day window
        scheduled_cash_flows = self._build_event_schedule(
            state, start_dt, end_dt, proposed_expenses
        )

        daily_results: List[DailyCashFlow] = []
        is_safe_throughout = True
        lowest_balance = current_cash
        lowest_balance_date = start_date
        first_breach_date: Optional[str] = None
        max_shortfall = Decimal("0")

        for day_idx in range(horizon_days + 1):
            day_dt = start_dt + timedelta(days=day_idx)
            day_str = self._format_date(day_dt)

            starting_bal = current_cash
            day_events = scheduled_cash_flows.get(day_str, [])

            # Separate credits and debits
            day_debits = sum(
                (Decimal(str(e["amount"])) for e in day_events if e["direction"] == "debit"),
                Decimal("0"),
            )
            day_credits = sum(
                (Decimal(str(e["amount"])) for e in day_events if e["direction"] == "credit"),
                Decimal("0"),
            )

            # Conservative Same-Day Cash-Flow Ordering:
            # Debits clear FIRST before incoming credits settle on the same day.
            intra_day_lowest = starting_bal - day_debits
            ending_bal = starting_bal - day_debits + day_credits

            # Evaluate safety against the minimum balance to keep
            effective_min = intra_day_lowest
            is_day_safe = effective_min >= min_balance

            if not is_day_safe:
                is_safe_throughout = False
                if first_breach_date is None:
                    first_breach_date = day_str
                shortfall = min_balance - effective_min
                if shortfall > max_shortfall:
                    max_shortfall = shortfall
            else:
                shortfall = Decimal("0")

            if effective_min < lowest_balance:
                lowest_balance = effective_min
                lowest_balance_date = day_str

            cushion = ending_bal - min_balance

            daily_results.append(
                DailyCashFlow(
                    date=day_str,
                    day_index=day_idx,
                    starting_balance=starting_bal,
                    total_debits=day_debits,
                    total_credits=day_credits,
                    intra_day_lowest_balance=intra_day_lowest,
                    ending_balance=ending_bal,
                    minimum_required_balance=min_balance,
                    cushion_above_minimum=cushion,
                    is_safe=is_day_safe,
                    shortfall=shortfall,
                    applied_events=day_events,
                )
            )

            # Next day's starting balance is today's ending balance
            current_cash = ending_bal

        return ForecastResult(
            user_id=profile.user_id,
            start_date=start_date,
            end_date=end_date,
            horizon_days=horizon_days,
            home_currency=profile.home_currency,
            initial_balance=state.unreserved_available_balance,
            minimum_balance_to_keep=min_balance,
            daily_forecasts=daily_results,
            is_safe_throughout=is_safe_throughout,
            lowest_balance=lowest_balance,
            lowest_balance_date=lowest_balance_date,
            first_breach_date=first_breach_date,
            max_shortfall=max_shortfall,
        )

    def _build_event_schedule(
        self,
        state: ReconstructedFinancialState,
        start_dt: datetime,
        end_dt: datetime,
        proposed_expenses: Optional[List[Tuple[str, Decimal, str]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate confirmed future obligations, confirmed future income, recurring streams,

        and optional proposed payments into a date-indexed schedule.
        """
        schedule: Dict[str, List[Dict[str, Any]]] = {}

        def add_event(date_str: str, event_dict: Dict[str, Any]) -> None:
            if date_str not in schedule:
                schedule[date_str] = []
            schedule[date_str].append(event_dict)

        # 1. Confirmed Future Obligations (scheduled debits with dates in window)
        covered_streams: Set[Tuple[str, str, int]] = set()  # (category, description, month)

        for e in state.future_obligations:
            date_to_use = e.settlement_date or e.event_date
            if not date_to_use:
                continue
            e_dt = self._parse_date(date_to_use)
            if start_dt <= e_dt <= end_dt:
                add_event(
                    date_to_use,
                    {
                        "event_id": e.event_id,
                        "description": e.description,
                        "category": e.category,
                        "direction": "debit",
                        "amount": e.amount_home_currency,
                        "source": "future_obligation",
                    },
                )
                covered_streams.add((e.category, e.description, e_dt.month))

        # 2. Confirmed Future Income (e.g. scheduled salary on its settlement date)
        for e in state.confirmed_future_income:
            date_to_use = e.settlement_date or e.event_date
            if not date_to_use:
                continue
            e_dt = self._parse_date(date_to_use)
            if start_dt <= e_dt <= end_dt:
                add_event(
                    date_to_use,
                    {
                        "event_id": e.event_id,
                        "description": e.description,
                        "category": e.category,
                        "direction": "credit",
                        "amount": e.amount_home_currency,
                        "source": "confirmed_future_income",
                    },
                )
                covered_streams.add((e.category, e.description, e_dt.month))

        # 3. Model Monthly Recurring Streams from History
        # For streams that recur monthly and don't yet have an explicit scheduled row in that month
        recurring_streams = self._extract_recurring_cadence(state)
        for stream in recurring_streams:
            cat = stream["category"]
            desc = stream["description"]
            direction = stream["direction"]
            day_of_month = stream["day_of_month"]
            amount = stream["amount"]

            # Project across the 3 calendar months spanning the 90 days
            cur = start_dt
            while cur <= end_dt:
                # Target date in this month
                try:
                    # Handle varying days per month
                    import calendar
                    max_day = calendar.monthrange(cur.year, cur.month)[1]
                    target_day = min(day_of_month, max_day)
                    proj_dt = datetime(cur.year, cur.month, target_day)
                except ValueError:
                    proj_dt = None

                if proj_dt and start_dt <= proj_dt <= end_dt:
                    # Check if already covered by an explicit scheduled event
                    if (cat, desc, proj_dt.month) not in covered_streams:
                        proj_date_str = self._format_date(proj_dt)
                        add_event(
                            proj_date_str,
                            {
                                "event_id": f"rec_{cat}_{proj_date_str}",
                                "description": desc,
                                "category": cat,
                                "direction": direction,
                                "amount": amount,
                                "source": "projected_recurring",
                            },
                        )

                # Move to next month
                if cur.month == 12:
                    cur = datetime(cur.year + 1, 1, 1)
                else:
                    cur = datetime(cur.year, cur.month + 1, 1)

        # 4. Proposed payments/expenses (if evaluating purchase affordability)
        if proposed_expenses:
            for p_date, p_amt, p_desc in proposed_expenses:
                p_dt = self._parse_date(p_date)
                if start_dt <= p_dt <= end_dt:
                    add_event(
                        p_date,
                        {
                            "event_id": "proposed_expense",
                            "description": p_desc,
                            "category": "proposed",
                            "direction": "debit",
                            "amount": p_amt,
                            "source": "proposed_expense",
                        },
                    )

        return schedule

    def _extract_recurring_cadence(
        self, state: ReconstructedFinancialState
    ) -> List[Dict[str, Any]]:
        """Identify supported recurring streams from historical settled events.

        Excludes bonuses, commissions, refunds, and one-off windfalls from recurring income,
        per AGENTS.md §6.3.
        """
        streams: List[Dict[str, Any]] = []

        # Combine settled income and settled expenses
        all_settled = state.confirmed_settled_expenses + state.confirmed_settled_income

        # Group by (category, description, direction)
        groups: Dict[Tuple[str, str, str], List[NormalizedEvent]] = {}
        for e in all_settled:
            if not e.is_recurring:
                continue
            # Rule: AGENTS.md §6.3 - Never count bonuses, commissions, refunds, or gains
            if e.direction == "credit":
                desc_lower = e.description.lower()
                if any(w in desc_lower for w in ["bonus", "commission", "refund", "gain", "dividend", "lottery", "gift", "reimbursement"]):
                    continue
            key = (e.category, e.description, e.direction)
            if key not in groups:
                groups[key] = []
            groups[key].append(e)

        for (cat, desc, direction), evts in groups.items():
            # For income credits, require regular history (at least 2 occurrences)
            if direction == "credit" and len(evts) < 2:
                continue
            # Must have at least 2 occurrences or be a recognized fixed recurring expense category
            if len(evts) < 2 and cat not in ("rent", "utilities", "subscription"):
                continue

            # Sort chronologically
            evts_sorted = sorted(evts, key=lambda x: x.event_date)
            latest_evt = evts_sorted[-1]

            # Detect day of month from the latest event's date
            try:
                latest_dt = self._parse_date(latest_evt.event_date)
                day_of_month = latest_dt.day
            except Exception:
                continue

            # Use latest amount in home currency
            streams.append(
                {
                    "category": cat,
                    "description": desc,
                    "direction": direction,
                    "day_of_month": day_of_month,
                    "amount": latest_evt.amount_home_currency,
                }
            )

        return streams

    def get_max_safe_amount_today(
        self,
        state: ReconstructedFinancialState,
        request_date: str,
        horizon_days: int = 90,
    ) -> Decimal:
        """Calculate the absolute maximum amount safe to pay today (unconstrained by requested amount).

        Evaluates the lowest cushion above minimum balance across the 90-day forecast horizon.
        Returns 0 if any baseline breach occurs.
        """
        baseline = self.run_forecast(state, start_date=request_date, horizon_days=horizon_days)
        min_cushion = baseline.minimum_cushion_from_date(request_date)
        return max(Decimal("0"), min_cushion)

    def calculate_amount_safe_to_pay(
        self,
        state: ReconstructedFinancialState,
        request_date: str,
        requested_amount: Decimal,
        horizon_days: int = 90,
    ) -> Decimal:
        """Calculate amount_safe_to_pay on request_date before optional spending changes.

        The safe amount is the maximum amount the user can pay on request_date such that
        the daily balance never drops below minimum_balance_to_keep across all 90 days.
        Bounded between 0 and requested_amount inclusive.
        """
        max_safe = self.get_max_safe_amount_today(state, request_date, horizon_days=horizon_days)
        return min(max(Decimal("0"), requested_amount), max_safe)

    def find_earliest_date_for_full_payment(
        self,
        state: ReconstructedFinancialState,
        request_date: str,
        requested_amount: Decimal,
        max_search_days: int = 90,
    ) -> Optional[str]:
        """Find the earliest conservative projected date for one safe full payment.

        Tests each candidate date from request_date through request_date + max_search_days.
        Guarantees:
        1. It never returns a date before request_date.
        2. The evaluation stays within the 90-day forecast horizon.
        3. Paying requested_amount on candidate_date keeps the user at or above
           minimum_balance_to_keep throughout the forecast horizon.
        """
        req_dt = self._parse_date(request_date)
        end_dt = req_dt + timedelta(days=max_search_days)

        if requested_amount <= Decimal("0"):
            return request_date

        for day_offset in range(max_search_days + 1):
            candidate_dt = req_dt + timedelta(days=day_offset)
            candidate_str = self._format_date(candidate_dt)

            # Safety check: candidate must be >= request_date and <= end_dt
            if candidate_dt < req_dt:
                continue
            if candidate_dt > end_dt:
                break

            # Test paying full requested_amount on candidate_str within the 90-day forecast window
            test_forecast = self.run_forecast(
                state=state,
                start_date=request_date,
                horizon_days=max_search_days,
                proposed_expenses=[(candidate_str, requested_amount, "Full payment trial")],
            )

            # Check if test_forecast is safe throughout the 90-day horizon
            if test_forecast.is_safe_throughout:
                return candidate_str

        return None
