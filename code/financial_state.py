"""Module 5: Financial State Reconstructor for Buy or Wait Financial Affordability Agent.

Reconstructs each user's financial profile, cash balances, historical commitments,
pending obligations, recurring cash flows, and flexible spending options
by integrating structured datasets, foreign exchange conversions, image OCR,
and message findings under the challenge's strict conflict-resolution rules.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd

from .data_loader import Datasets
from .currency_converter import CurrencyConverter
from .message_analyzer import MessageAnalyzer, MessageFinding
from .image_analyzer import ImageAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class UserFinancialProfile:
    """Strongly typed representation of a user's financial profile and preferences."""

    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    financial_priorities: List[str]
    protected_categories: List[str]
    reduce_categories: List[str]
    stop_categories: List[str]
    considered_payment_methods: List[str]
    max_installment_months: Optional[int]


@dataclass
class NormalizedEvent:
    """Normalized financial event with amounts converted to home currency."""

    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str  # credit, debit, non_cash
    original_amount: Decimal
    original_currency: str
    amount_home_currency: Decimal
    home_currency: str
    event_date: str
    settlement_date: Optional[str]
    status: str  # settled, scheduled, pending, failed, cancelled, unrealized
    linked_event_id: Optional[str]
    flexibility: str  # fixed, stoppable, reducible, reducible_or_stoppable
    minimum_allowed_amount_home_currency: Optional[Decimal]
    is_recurring: bool
    source_notes: List[str] = field(default_factory=list)


@dataclass
class FlexibleExpenseCandidate:
    """A recurring expense that can be stopped or reduced according to user preferences."""

    event_id: str
    category: str
    description: str
    current_amount_home_currency: Decimal
    minimum_allowed_amount_home_currency: Decimal
    can_stop: bool
    can_reduce: bool
    max_monthly_savings: Decimal
    reason: str


@dataclass
class ReconstructedFinancialState:
    """Complete reconstructed financial state for a single user."""

    user_profile: UserFinancialProfile

    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal

    # Cash state buckets
    confirmed_settled_income: List[NormalizedEvent]
    confirmed_settled_expenses: List[NormalizedEvent]
    pending_debits: List[NormalizedEvent]
    future_obligations: List[NormalizedEvent]
    confirmed_future_income: List[NormalizedEvent]

    # Additional analytical segments
    unconfirmed_information: List[Dict[str, Any]]
    recurring_events: List[NormalizedEvent]
    flexible_expenses: List[FlexibleExpenseCandidate]
    ignored_or_conflicting: List[Dict[str, Any]]

    @property
    def total_pending_debits(self) -> Decimal:
        """Total sum of pending debit transactions in home currency."""
        return sum((e.amount_home_currency for e in self.pending_debits), Decimal("0"))

    @property
    def unreserved_available_balance(self) -> Decimal:
        """Current available balance minus pending debits."""
        return self.current_available_balance - self.total_pending_debits

    @property
    def unreserved_cushion_above_minimum(self) -> Decimal:
        """Available balance above minimum required balance after reserving pending debits."""
        return self.unreserved_available_balance - self.minimum_balance_to_keep


class FinancialStateReconstructor:
    """Reconstructs full financial states for users from multi-source datasets and evidence."""

    def __init__(
        self,
        datasets: Datasets,
        currency_converter: Optional[CurrencyConverter] = None,
        message_analyzer: Optional[MessageAnalyzer] = None,
        image_analyzer: Optional[ImageAnalyzer] = None,
    ):
        """Initialize reconstructor with datasets and optional domain analyzers."""
        self.datasets = datasets
        self.currency_converter = currency_converter or CurrencyConverter(datasets.exchange_rates)
        self.message_analyzer = message_analyzer or MessageAnalyzer(datasets.messages)
        self.image_analyzer = image_analyzer or ImageAnalyzer(datasets.images)

    def reconstruct_user(self, user_id: str) -> ReconstructedFinancialState:
        """Reconstruct the comprehensive financial state of a given user.

        Args:
            user_id: The ID of the user (e.g. 'user_01').

        Returns:
            ReconstructedFinancialState containing profile, events, obligations,
            recurring streams, flexible expense options, and ignored records.
        """
        # Step 1: User Profile
        profile = self._get_user_profile(user_id)

        # Step 2: Message & Image Evidence for this user
        user_messages = self.message_analyzer.get_findings_for_user(user_id)

        # Step 3: Raw user events
        user_events_df = self.datasets.financial_events[
            self.datasets.financial_events["user_id"] == user_id
        ]

        # Step 4: Normalize events with OCR image extraction and currency conversion
        normalized_events, ignored_or_conflicting, unconfirmed_info = self._normalize_user_events(
            user_events_df, profile, user_messages
        )

        # Step 5: Incorporate message findings into unconfirmed info or salary adjustments
        self._apply_message_findings(user_messages, normalized_events, unconfirmed_info, profile)

        # Step 6: Categorize events into cash buckets according to challenge rules
        (
            confirmed_settled_inc,
            confirmed_settled_exp,
            pending_debits,
            future_obligations,
            confirmed_future_inc,
        ) = self._categorize_events_by_cash_state(normalized_events, ignored_or_conflicting)

        # Step 7: Identify recurring events
        recurring_events = [e for e in normalized_events if e.is_recurring]

        # Step 8: Identify flexible expenses eligible for reduction or stoppage
        flexible_expenses = self._identify_flexible_expenses(normalized_events, profile)

        return ReconstructedFinancialState(
            user_profile=profile,
            current_available_balance=profile.current_available_balance,
            minimum_balance_to_keep=profile.minimum_balance_to_keep,
            confirmed_settled_income=confirmed_settled_inc,
            confirmed_settled_expenses=confirmed_settled_exp,
            pending_debits=pending_debits,
            future_obligations=future_obligations,
            confirmed_future_income=confirmed_future_inc,
            unconfirmed_information=unconfirmed_info,
            recurring_events=recurring_events,
            flexible_expenses=flexible_expenses,
            ignored_or_conflicting=ignored_or_conflicting,
        )

    def _get_user_profile(self, user_id: str) -> UserFinancialProfile:
        """Extract and parse UserFinancialProfile from financial_profiles DataFrame."""
        fp_df = self.datasets.financial_profiles
        user_rows = fp_df[fp_df["user_id"] == user_id]
        if user_rows.empty:
            raise ValueError(f"User '{user_id}' not found in financial_profiles.csv")

        row = user_rows.iloc[0]

        def parse_tokens(val: Any) -> List[str]:
            if pd.isna(val) or val is None or str(val).strip() == "":
                return []
            return [t.strip() for t in str(val).split("|") if t.strip()]

        max_inst = None
        if pd.notna(row["max_installment_months"]):
            try:
                max_inst = int(float(row["max_installment_months"]))
            except (ValueError, TypeError):
                max_inst = None

        return UserFinancialProfile(
            user_id=user_id,
            home_currency=str(row["home_currency"]).strip().upper(),
            current_available_balance=Decimal(str(row["current_available_balance"])),
            minimum_balance_to_keep=Decimal(str(row["minimum_balance_to_keep"])),
            financial_priorities=parse_tokens(row.get("financial_priorities")),
            protected_categories=parse_tokens(row.get("expense_categories_to_protect")),
            reduce_categories=parse_tokens(row.get("expense_categories_user_is_willing_to_reduce")),
            stop_categories=parse_tokens(row.get("expense_categories_user_is_willing_to_stop")),
            considered_payment_methods=parse_tokens(row.get("payment_methods_user_will_consider")),
            max_installment_months=max_inst,
        )

    def _normalize_user_events(
        self,
        events_df: pd.DataFrame,
        profile: UserFinancialProfile,
        user_messages: List[MessageFinding],
    ) -> Tuple[List[NormalizedEvent], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Normalize raw financial events, apply image OCR, foreign exchange, and conflict handling."""
        normalized: List[NormalizedEvent] = []
        ignored_or_conflicting: List[Dict[str, Any]] = []
        unconfirmed_info: List[Dict[str, Any]] = []

        # Map linked events to understand parent-child relationships
        child_links: Set[str] = set(events_df["linked_event_id"].dropna())

        for _, row in events_df.iterrows():
            evt_id = str(row["event_id"]).strip()
            status = str(row["status"]).strip().lower()
            direction = str(row["direction"]).strip().lower()
            evt_type = str(row["event_type"]).strip().lower()
            category = str(row["category"]).strip().lower()
            currency = str(row["currency"]).strip().upper()
            linked_id = str(row["linked_event_id"]).strip() if pd.notna(row["linked_event_id"]) else None
            flexibility = str(row["flexibility"]).strip().lower()

            # Rule 1: Handle failed or cancelled events
            if status in ("cancelled", "failed"):
                ignored_or_conflicting.append({
                    "event_id": evt_id,
                    "reason": f"Event status is '{status}'",
                    "direction": direction,
                    "event_type": evt_type,
                    "category": category,
                })
                continue

            # Rule 2: Handle non-cash unrealized investments
            if status == "unrealized" or direction == "non_cash":
                unconfirmed_info.append({
                    "event_id": evt_id,
                    "reason": "Non-cash unrealized investment valuation (not available cash)",
                    "direction": direction,
                    "event_type": evt_type,
                    "category": category,
                })
                continue

            # Rule 3: Superseded parent events (e.g., an earlier event replaced by a linked settlement/amendment)
            if evt_id in child_links and status not in ("settled", "scheduled"):
                ignored_or_conflicting.append({
                    "event_id": evt_id,
                    "reason": "Superseded by linked event in same transaction lifecycle",
                    "direction": direction,
                    "event_type": evt_type,
                    "category": category,
                })
                continue

            # Extract amount (from raw event or linked image)
            raw_amt = row["amount"]
            source_notes: List[str] = []

            if pd.isna(raw_amt):
                # Missing amount: extract from ImageAnalyzer
                extracted_amt = self.image_analyzer.get_extracted_amount_for_event(evt_id)
                if extracted_amt is not None:
                    amount_dec = extracted_amt
                    source_notes.append(f"Amount extracted from linked image: {amount_dec}")
                else:
                    ignored_or_conflicting.append({
                        "event_id": evt_id,
                        "reason": "Blank amount with no matching image extraction available",
                    })
                    continue
            else:
                amount_dec = Decimal(str(raw_amt))

            # Convert foreign currencies to user's home currency
            settle_date = str(row["settlement_date"]).strip() if pd.notna(row["settlement_date"]) else None
            event_date = str(row["event_date"]).strip()

            if currency != profile.home_currency:
                rate_anchor = settle_date if settle_date else event_date
                try:
                    home_amt = self.currency_converter.convert_to_home_currency(
                        amount=amount_dec,
                        currency=currency,
                        home_currency=profile.home_currency,
                        settlement_date=rate_anchor,
                    )
                    source_notes.append(
                        f"Converted {currency} {amount_dec} -> {profile.home_currency} {home_amt} using date {rate_anchor}"
                    )
                except Exception as e:
                    logger.warning("Currency conversion failed for event %s: %s", evt_id, e)
                    ignored_or_conflicting.append({
                        "event_id": evt_id,
                        "reason": f"Currency conversion failed: {e}",
                    })
                    continue
            else:
                home_amt = amount_dec

            # Handle minimum_allowed_amount for flexible events
            raw_min = row.get("minimum_allowed_amount")
            min_home: Optional[Decimal] = None
            if pd.notna(raw_min):
                min_dec = Decimal(str(raw_min))
                if currency != profile.home_currency:
                    rate_anchor = settle_date if settle_date else event_date
                    min_home = self.currency_converter.convert_to_home_currency(
                        amount=min_dec,
                        currency=currency,
                        home_currency=profile.home_currency,
                        settlement_date=rate_anchor,
                    )
                else:
                    min_home = min_dec

            # Determine recurrence
            is_recurring = self._is_recurring_event(category, evt_type)

            norm_evt = NormalizedEvent(
                event_id=evt_id,
                user_id=profile.user_id,
                event_type=evt_type,
                description=str(row["description"]).strip(),
                category=category,
                direction=direction,
                original_amount=amount_dec,
                original_currency=currency,
                amount_home_currency=home_amt,
                home_currency=profile.home_currency,
                event_date=event_date,
                settlement_date=settle_date,
                status=status,
                linked_event_id=linked_id,
                flexibility=flexibility,
                minimum_allowed_amount_home_currency=min_home,
                is_recurring=is_recurring,
                source_notes=source_notes,
            )
            normalized.append(norm_evt)

        return normalized, ignored_or_conflicting, unconfirmed_info

    @staticmethod
    def _is_recurring_event(category: str, event_type: str) -> bool:
        """Identify naturally recurring income and expense commitments."""
        recurring_categories = {
            "salary",
            "rent",
            "utilities",
            "subscription",
            "debt_repayment",
            "debt_payment",
            "music_subscription",
            "delivery_membership",
            "cloud_storage",
            "streaming",
            "gym",
            "insurance",
            "education",
            "family_support",
        }
        if category in recurring_categories or event_type in ("subscription", "debt_payment"):
            return True
        return False

    def _apply_message_findings(
        self,
        messages: List[MessageFinding],
        events: List[NormalizedEvent],
        unconfirmed_info: List[Dict[str, Any]],
        profile: UserFinancialProfile,
    ) -> None:
        """Apply confirmed message amendments to normalized events (salary changes, dates, rent increases)."""
        for msg in messages:
            if not msg.is_confirmed:
                unconfirmed_info.append({
                    "message_id": msg.message_id,
                    "reason": f"Unconfirmed message signal ({msg.finding_type}): {msg.evidence_text}",
                    "text": msg.original_text,
                })
                continue

            # Confirmed salary update
            if msg.finding_type in ("salary_update", "salary_reduction", "temporary_salary_adjustment", "salary_resumption"):
                if msg.extracted_value is not None and isinstance(msg.extracted_value, Decimal):
                    # Convert to home currency if foreign
                    sal_amt = msg.extracted_value
                    if msg.currency and msg.currency != profile.home_currency:
                        sal_amt = self.currency_converter.convert_to_home_currency(
                            amount=sal_amt,
                            currency=msg.currency,
                            home_currency=profile.home_currency,
                            settlement_date=msg.effective_date or "2025-08-15",
                        )

                    # Update scheduled future salary events if present
                    matched = False
                    for e in events:
                        if e.category == "salary" and e.status == "scheduled":
                            e.amount_home_currency = sal_amt
                            e.source_notes.append(
                                f"Updated salary from {msg.message_id}: {sal_amt} {profile.home_currency}"
                            )
                            if msg.effective_date:
                                e.settlement_date = msg.effective_date
                                e.source_notes.append(f"Effective date updated to {msg.effective_date}")
                            matched = True

                    # If no scheduled salary event existed, create the confirmed future salary event
                    if not matched and msg.effective_date:
                        events.append(
                            NormalizedEvent(
                                event_id=f"msg_salary_{msg.message_id}",
                                user_id=profile.user_id,
                                event_type="income",
                                description=f"Confirmed salary from {msg.source_type} ({msg.message_id})",
                                category="salary",
                                direction="credit",
                                original_amount=sal_amt,
                                original_currency=msg.currency or profile.home_currency,
                                amount_home_currency=sal_amt,
                                home_currency=profile.home_currency,
                                event_date=msg.effective_date,
                                settlement_date=msg.effective_date,
                                status="scheduled",
                                linked_event_id=None,
                                flexibility="fixed",
                                minimum_allowed_amount_home_currency=None,
                                is_recurring=True,
                                source_notes=[f"Created from confirmed message {msg.message_id}: {msg.original_text}"],
                            )
                        )

            # Confirmed invoice payment
            elif msg.finding_type == "confirmed_invoice_payment" and msg.effective_date and msg.extracted_value:
                inv_amt = msg.extracted_value
                if msg.currency and msg.currency != profile.home_currency:
                    inv_amt = self.currency_converter.convert_to_home_currency(
                        amount=inv_amt,
                        currency=msg.currency,
                        home_currency=profile.home_currency,
                        settlement_date=msg.effective_date,
                    )
                events.append(
                    NormalizedEvent(
                        event_id=f"msg_inv_{msg.message_id}",
                        user_id=profile.user_id,
                        event_type="income",
                        description=f"Confirmed invoice payment ({msg.message_id})",
                        category="salary",
                        direction="credit",
                        original_amount=inv_amt,
                        original_currency=msg.currency or profile.home_currency,
                        amount_home_currency=inv_amt,
                        home_currency=profile.home_currency,
                        event_date=msg.effective_date,
                        settlement_date=msg.effective_date,
                        status="scheduled",
                        linked_event_id=None,
                        flexibility="fixed",
                        minimum_allowed_amount_home_currency=None,
                        is_recurring=False,
                        source_notes=[f"Confirmed invoice from {msg.message_id}: {msg.original_text}"],
                    )
                )

            # Confirmed salary date change
            elif msg.finding_type == "salary_date_change" and msg.effective_date:
                for e in events:
                    if e.category == "salary" and e.status == "scheduled":
                        e.settlement_date = msg.effective_date
                        e.source_notes.append(f"Settlement date updated to {msg.effective_date} from {msg.message_id}")

            # Confirmed rent increase percentage (applies to recurring monthly rent)
            elif msg.finding_type == "rent_increase_percentage" and msg.extracted_value is not None:
                pct = Decimal(str(msg.extracted_value)) / Decimal("100")
                for e in events:
                    if e.category == "rent" and "monthly" in e.description.lower() and e.status == "scheduled":
                        old_amt = e.amount_home_currency
                        e.amount_home_currency = (old_amt * (Decimal("1") + pct)).quantize(Decimal("0.01"))
                        e.source_notes.append(
                            f"Rent increased by {msg.extracted_value}% ({old_amt} -> {e.amount_home_currency})"
                        )

    def _categorize_events_by_cash_state(
        self,
        events: List[NormalizedEvent],
        ignored_or_conflicting: List[Dict[str, Any]],
    ) -> Tuple[
        List[NormalizedEvent],
        List[NormalizedEvent],
        List[NormalizedEvent],
        List[NormalizedEvent],
        List[NormalizedEvent],
    ]:
        """Segregate events into settled, pending debits, future obligations, and confirmed future income."""
        confirmed_settled_inc: List[NormalizedEvent] = []
        confirmed_settled_exp: List[NormalizedEvent] = []
        pending_debits: List[NormalizedEvent] = []
        future_obligations: List[NormalizedEvent] = []
        confirmed_future_inc: List[NormalizedEvent] = []

        for e in events:
            if e.direction == "debit":
                if e.status == "settled":
                    confirmed_settled_exp.append(e)
                elif e.status == "pending":
                    # Pending debit: MUST be reserved against available balance
                    pending_debits.append(e)
                elif e.status == "scheduled":
                    future_obligations.append(e)
                else:
                    ignored_or_conflicting.append({
                        "event_id": e.event_id,
                        "reason": f"Unhandled debit status: {e.status}",
                    })

            elif e.direction == "credit":
                if e.status == "settled":
                    confirmed_settled_inc.append(e)
                elif e.status == "scheduled" and e.category == "salary":
                    # Only confirmed salary on settlement date
                    confirmed_future_inc.append(e)
                elif e.status == "pending":
                    # Rule: Pending credits MUST NOT be counted as cash until settled
                    ignored_or_conflicting.append({
                        "event_id": e.event_id,
                        "reason": "Pending credit ignored until settled (challenge safety rule)",
                    })
                else:
                    ignored_or_conflicting.append({
                        "event_id": e.event_id,
                        "reason": f"Unconfirmed credit status: {e.status}",
                    })

        return (
            confirmed_settled_inc,
            confirmed_settled_exp,
            pending_debits,
            future_obligations,
            confirmed_future_inc,
        )

    def _identify_flexible_expenses(
        self,
        events: List[NormalizedEvent],
        profile: UserFinancialProfile,
    ) -> List[FlexibleExpenseCandidate]:
        """Identify which recurring commitments can be reduced or stopped.

        Inspects flexible debit events matching user stop/reduce preferences,
        excluding protected categories. Deduplicates by category and description
        to select the latest event_id representing each recurring flexible stream.
        """
        candidates_by_stream: Dict[Tuple[str, str], Tuple[str, FlexibleExpenseCandidate]] = {}

        for e in events:
            if e.direction != "debit":
                continue

            cat = e.category
            # Protected categories can NEVER be reduced or stopped
            if cat in profile.protected_categories:
                continue

            can_stop = False
            can_reduce = False
            reasons: List[str] = []

            # Check if user allows stopping and event flexibility allows stopping
            if (
                cat in profile.stop_categories
                and e.flexibility in ("stoppable", "reducible_or_stoppable")
            ):
                can_stop = True
                reasons.append("Category in user stop preferences and event marked stoppable")

            # Check if user allows reducing and event flexibility allows reducing
            if (
                cat in profile.reduce_categories
                and e.flexibility in ("reducible", "reducible_or_stoppable")
            ):
                can_reduce = True
                reasons.append("Category in user reduce preferences and event marked reducible")

            if can_stop or can_reduce:
                min_amt = e.minimum_allowed_amount_home_currency or Decimal("0")
                if can_stop:
                    max_savings = e.amount_home_currency
                else:
                    max_savings = max(Decimal("0"), e.amount_home_currency - min_amt)

                candidate = FlexibleExpenseCandidate(
                    event_id=e.event_id,
                    category=cat,
                    description=e.description,
                    current_amount_home_currency=e.amount_home_currency,
                    minimum_allowed_amount_home_currency=min_amt,
                    can_stop=can_stop,
                    can_reduce=can_reduce,
                    max_monthly_savings=max_savings,
                    reason="; ".join(reasons),
                )

                # Keep the latest event date for each stream
                stream_key = (cat, e.description)
                event_date = e.event_date
                if stream_key not in candidates_by_stream or event_date > candidates_by_stream[stream_key][0]:
                    candidates_by_stream[stream_key] = (event_date, candidate)

        return [cand for _, cand in candidates_by_stream.values()]
