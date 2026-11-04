"""Module 2: Data Validation & Integrity for Buy or Wait Financial Affordability Agent.

Validates schema compliance, duplicate identifiers, referential integrity,
date ranges, numeric constraints, and enumerated values across all challenge datasets.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import logging
import pandas as pd

from .data_loader import Datasets

logger = logging.getLogger(__name__)

# Canonical enum values defined by problem_statement.md and dataset definitions
VALID_REQUEST_TYPES: Set[str] = {
    "purchase",
    "travel",
    "education",
    "family_transfer",
    "debt_repayment",
    "investment",
    "housing",
    "emergency_expense",
    "other",
}

VALID_CURRENCIES: Set[str] = {"INR", "ZAR", "IDR", "USD", "EUR"}

VALID_EVENT_DIRECTIONS: Set[str] = {"credit", "debit", "non_cash"}

VALID_EVENT_STATUSES: Set[str] = {
    "settled",
    "cancelled",
    "pending",
    "scheduled",
    "failed",
    "unrealized",
}

VALID_EVENT_FLEXIBILITIES: Set[str] = {
    "fixed",
    "stoppable",
    "reducible",
    "reducible_or_stoppable",
}

VALID_EVENT_TYPES: Set[str] = {
    "expense",
    "debt_payment",
    "subscription",
    "income",
    "refund",
    "investment_purchase",
    "investment_valuation",
    "investment_sale",
}

VALID_PAYMENT_METHODS_OPTIONS: Set[str] = {"full_payment", "installments"}

VALID_MESSAGE_SOURCE_TYPES: Set[str] = {
    "employer",
    "service_provider",
    "bank",
    "merchant",
    "financial_service",
}

VALID_AFFORDABILITY_STATUSES: Set[str] = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

VALID_RECOMMENDED_PAYMENT_METHODS: Set[str] = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


@dataclass
class ValidationIssue:
    """Represents a single validation error or warning."""

    severity: str  # "ERROR" or "WARNING"
    category: str  # check category
    dataset: str
    field: str
    message: str
    affected_ids: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Summary and details of all validation checks performed."""

    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no ERROR severity issues were found."""
        return self.failed_checks == 0

    def add_issue(
        self,
        severity: str,
        category: str,
        dataset: str,
        field_name: str,
        message: str,
        affected_ids: Optional[List[str]] = None,
    ) -> None:
        """Record an issue and update report counters."""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            dataset=dataset,
            field=field_name,
            message=message,
            affected_ids=affected_ids or [],
        )
        self.issues.append(issue)
        if severity == "ERROR":
            self.failed_checks += 1
        elif severity == "WARNING":
            self.warnings_count += 1

    def record_pass(self) -> None:
        """Record a successful check."""
        self.passed_checks += 1


class DataValidator:
    """Reusable integrity and schema validator for all challenge datasets."""

    def __init__(self, datasets: Datasets, media_dir: Optional[Path] = None):
        """Initialize validator with loaded Datasets."""
        self.datasets = datasets
        if media_dir is not None:
            self.media_dir = Path(media_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent
            self.media_dir = (repo_root / "dataset" / "media" / "images").resolve()

    def validate_all(self) -> ValidationReport:
        """Run all integrity checks and return a ValidationReport."""
        report = ValidationReport()

        self._check_duplicate_identifiers(report)
        self._check_missing_required_identifiers(report)
        self._check_referential_integrity(report)
        self._check_date_validations(report)
        self._check_numeric_validations(report)
        self._check_enumerated_values(report)
        self._check_dataset_consistency(report)

        report.total_checks = report.passed_checks + report.failed_checks + report.warnings_count
        return report

    # -------------------------------------------------------------------------
    # 1. Duplicate Identifiers
    # -------------------------------------------------------------------------
    def _check_duplicate_identifiers(self, report: ValidationReport) -> None:
        checks = [
            ("requests", self.datasets.requests, "request_id"),
            ("sample_requests", self.datasets.sample_requests, "request_id"),
            ("financial_profiles", self.datasets.financial_profiles, "user_id"),
            ("financial_events", self.datasets.financial_events, "event_id"),
            ("messages", self.datasets.messages, "message_id"),
            ("images", self.datasets.images, "image_id"),
            ("request_payment_options", self.datasets.request_payment_options, "payment_option_id"),
        ]

        for ds_name, df, id_col in checks:
            duplicates = df[df[id_col].duplicated(keep=False)]
            if len(duplicates) > 0:
                dup_ids = duplicates[id_col].drop_duplicates().tolist()
                report.add_issue(
                    severity="ERROR",
                    category="duplicate_identifier",
                    dataset=ds_name,
                    field_name=id_col,
                    message=f"Found {len(dup_ids)} duplicate identifiers in {ds_name}.{id_col}",
                    affected_ids=dup_ids[:10],
                )
            else:
                report.record_pass()

    # -------------------------------------------------------------------------
    # 2. Missing Required Identifiers
    # -------------------------------------------------------------------------
    def _check_missing_required_identifiers(self, report: ValidationReport) -> None:
        required_id_checks = [
            ("requests", self.datasets.requests, ["request_id", "user_id"]),
            ("sample_requests", self.datasets.sample_requests, ["request_id", "user_id"]),
            ("financial_profiles", self.datasets.financial_profiles, ["user_id"]),
            ("financial_events", self.datasets.financial_events, ["event_id", "user_id"]),
            ("messages", self.datasets.messages, ["message_id", "user_id"]),
            ("images", self.datasets.images, ["image_id", "user_id", "request_id", "related_event_id"]),
            ("request_payment_options", self.datasets.request_payment_options, ["payment_option_id", "request_id"]),
            ("exchange_rates", self.datasets.exchange_rates, ["from_currency", "to_currency", "rate_date"]),
        ]

        for ds_name, df, cols in required_id_checks:
            for col in cols:
                nulls = df[df[col].isnull() | (df[col].astype(str).str.strip() == "")]
                if len(nulls) > 0:
                    report.add_issue(
                        severity="ERROR",
                        category="missing_required_identifier",
                        dataset=ds_name,
                        field_name=col,
                        message=f"{len(nulls)} rows in {ds_name} have null or blank required identifier '{col}'",
                    )
                else:
                    report.record_pass()

    # -------------------------------------------------------------------------
    # 3. Referential Integrity
    # -------------------------------------------------------------------------
    def _check_referential_integrity(self, report: ValidationReport) -> None:
        profile_users = set(self.datasets.financial_profiles["user_id"])
        all_requests = set(self.datasets.requests["request_id"]).union(
            set(self.datasets.sample_requests["request_id"])
        )
        all_events = set(self.datasets.financial_events["event_id"])

        # Check user_id links to financial_profiles
        user_checks = [
            ("requests", self.datasets.requests),
            ("sample_requests", self.datasets.sample_requests),
            ("financial_events", self.datasets.financial_events),
            ("messages", self.datasets.messages),
            ("images", self.datasets.images),
        ]
        for ds_name, df in user_checks:
            missing_users = set(df["user_id"]) - profile_users
            if missing_users:
                report.add_issue(
                    severity="ERROR",
                    category="referential_integrity",
                    dataset=ds_name,
                    field_name="user_id",
                    message=f"{len(missing_users)} user_ids in {ds_name} do not exist in financial_profiles",
                    affected_ids=list(missing_users)[:10],
                )
            else:
                report.record_pass()

        # Check request_id in request_payment_options
        missing_opt_reqs = set(self.datasets.request_payment_options["request_id"]) - all_requests
        if missing_opt_reqs:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="request_payment_options",
                field_name="request_id",
                message=f"{len(missing_opt_reqs)} request_ids in payment options do not exist in requests/sample_requests",
                affected_ids=list(missing_opt_reqs)[:10],
            )
        else:
            report.record_pass()

        # Check request_id in messages (when non-null)
        msg_reqs = set(self.datasets.messages["request_id"].dropna())
        missing_msg_reqs = msg_reqs - all_requests
        if missing_msg_reqs:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="messages",
                field_name="request_id",
                message=f"{len(missing_msg_reqs)} populated request_ids in messages do not exist in requests/sample_requests",
                affected_ids=list(missing_msg_reqs)[:10],
            )
        else:
            report.record_pass()

        # Check related_event_id in messages (when non-null)
        msg_evts = set(self.datasets.messages["related_event_id"].dropna())
        missing_msg_evts = msg_evts - all_events
        if missing_msg_evts:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="messages",
                field_name="related_event_id",
                message=f"{len(missing_msg_evts)} populated related_event_ids in messages do not exist in financial_events",
                affected_ids=list(missing_msg_evts)[:10],
            )
        else:
            report.record_pass()

        # Check request_id in images
        img_reqs = set(self.datasets.images["request_id"].dropna())
        missing_img_reqs = img_reqs - all_requests
        if missing_img_reqs:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="images",
                field_name="request_id",
                message=f"{len(missing_img_reqs)} request_ids in images do not exist in requests/sample_requests",
                affected_ids=list(missing_img_reqs)[:10],
            )
        else:
            report.record_pass()

        # Check related_event_id in images
        img_evts = set(self.datasets.images["related_event_id"].dropna())
        missing_img_evts = img_evts - all_events
        if missing_img_evts:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="images",
                field_name="related_event_id",
                message=f"{len(missing_img_evts)} related_event_ids in images do not exist in financial_events",
                affected_ids=list(missing_img_evts)[:10],
            )
        else:
            report.record_pass()

        # Check linked_event_id in financial_events
        linked_evts = set(self.datasets.financial_events["linked_event_id"].dropna())
        missing_linked = linked_evts - all_events
        if missing_linked:
            report.add_issue(
                severity="ERROR",
                category="referential_integrity",
                dataset="financial_events",
                field_name="linked_event_id",
                message=f"{len(missing_linked)} linked_event_ids do not exist in financial_events",
                affected_ids=list(missing_linked)[:10],
            )
        else:
            report.record_pass()

    # -------------------------------------------------------------------------
    # 4. Date Validation
    # -------------------------------------------------------------------------
    def _check_date_validations(self, report: ValidationReport) -> None:
        ymd_checks = [
            ("requests", self.datasets.requests, "request_date"),
            ("requests", self.datasets.requests, "desired_completion_date"),
            ("sample_requests", self.datasets.sample_requests, "request_date"),
            ("sample_requests", self.datasets.sample_requests, "desired_completion_date"),
            ("financial_events", self.datasets.financial_events, "event_date"),
            ("financial_events", self.datasets.financial_events, "settlement_date"),
            ("exchange_rates", self.datasets.exchange_rates, "rate_date"),
            ("request_payment_options", self.datasets.request_payment_options, "first_payment_date"),
        ]

        for ds_name, df, col in ymd_checks:
            series = df[col].dropna()
            try:
                parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
                bad_dates = series[parsed.isnull()]
                if len(bad_dates) > 0:
                    report.add_issue(
                        severity="ERROR",
                        category="date_validation",
                        dataset=ds_name,
                        field_name=col,
                        message=f"{len(bad_dates)} invalid date formats in {ds_name}.{col} (expected YYYY-MM-DD)",
                        affected_ids=bad_dates.head(5).tolist(),
                    )
                else:
                    report.record_pass()
            except Exception as e:
                report.add_issue(
                    severity="ERROR",
                    category="date_validation",
                    dataset=ds_name,
                    field_name=col,
                    message=f"Date parsing failed for {ds_name}.{col}: {e}",
                )

        # Check desired_completion_date >= request_date
        for ds_name, df in [("requests", self.datasets.requests), ("sample_requests", self.datasets.sample_requests)]:
            bad_range = df[df["desired_completion_date"] < df["request_date"]]
            if len(bad_range) > 0:
                report.add_issue(
                    severity="ERROR",
                    category="date_validation",
                    dataset=ds_name,
                    field_name="desired_completion_date",
                    message=f"{len(bad_range)} requests have desired_completion_date earlier than request_date",
                    affected_ids=bad_range["request_id"].tolist(),
                )
            else:
                report.record_pass()

        # Check messages.sent_at is valid ISO8601
        try:
            msg_sent = pd.to_datetime(self.datasets.messages["sent_at"], errors="coerce")
            bad_iso = self.datasets.messages["sent_at"][msg_sent.isnull()]
            if len(bad_iso) > 0:
                report.add_issue(
                    severity="ERROR",
                    category="date_validation",
                    dataset="messages",
                    field_name="sent_at",
                    message=f"{len(bad_iso)} invalid ISO timestamps in messages.sent_at",
                )
            else:
                report.record_pass()
        except Exception as e:
            report.add_issue(
                severity="ERROR",
                category="date_validation",
                dataset="messages",
                field_name="sent_at",
                message=f"Timestamp parsing error in messages.sent_at: {e}",
            )

        # Warning for financial_events where settlement_date is null
        null_settle = self.datasets.financial_events[self.datasets.financial_events["settlement_date"].isnull()]
        if len(null_settle) > 0:
            # Check if all null settlement dates are non_cash/unrealized investment_valuations
            non_standard = null_settle[null_settle["status"] != "unrealized"]
            if len(non_standard) > 0:
                report.add_issue(
                    severity="WARNING",
                    category="date_validation",
                    dataset="financial_events",
                    field_name="settlement_date",
                    message=f"{len(non_standard)} non-unrealized events have null settlement_date",
                    affected_ids=non_standard["event_id"].tolist()[:10],
                )
            else:
                report.record_pass()

    # -------------------------------------------------------------------------
    # 5. Numeric Validation
    # -------------------------------------------------------------------------
    def _check_numeric_validations(self, report: ValidationReport) -> None:
        # Requested amount >= 0
        for ds_name, df in [("requests", self.datasets.requests), ("sample_requests", self.datasets.sample_requests)]:
            neg_req = df[df["requested_amount"] < 0]
            if len(neg_req) > 0:
                report.add_issue(
                    severity="ERROR",
                    category="numeric_validation",
                    dataset=ds_name,
                    field_name="requested_amount",
                    message=f"{len(neg_req)} requests have negative requested_amount",
                    affected_ids=neg_req["request_id"].tolist(),
                )
            else:
                report.record_pass()

        # Balances in financial_profiles >= 0
        fp = self.datasets.financial_profiles
        neg_bal = fp[fp["current_available_balance"] < 0]
        if len(neg_bal) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="financial_profiles",
                field_name="current_available_balance",
                message=f"{len(neg_bal)} profiles have negative current_available_balance",
                affected_ids=neg_bal["user_id"].tolist(),
            )
        else:
            report.record_pass()

        neg_min = fp[fp["minimum_balance_to_keep"] < 0]
        if len(neg_min) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="financial_profiles",
                field_name="minimum_balance_to_keep",
                message=f"{len(neg_min)} profiles have negative minimum_balance_to_keep",
                affected_ids=neg_min["user_id"].tolist(),
            )
        else:
            report.record_pass()

        # Exchange rate > 0
        er = self.datasets.exchange_rates
        bad_rate = er[er["rate"] <= 0]
        if len(bad_rate) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="exchange_rates",
                field_name="rate",
                message=f"{len(bad_rate)} exchange rates have non-positive values",
            )
        else:
            report.record_pass()

        # Payment options numeric checks
        opts = self.datasets.request_payment_options
        bad_opt = opts[
            (opts["payment_amount"] < 0)
            | (opts["number_of_payments"] < 1)
            | (opts["financing_fee"] < 0)
            | (opts["total_payable_amount"] < 0)
        ]
        if len(bad_opt) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="request_payment_options",
                field_name="payment_amount/total_payable_amount",
                message=f"{len(bad_opt)} payment options have negative amounts or invalid payment counts",
                affected_ids=bad_opt["payment_option_id"].tolist()[:10],
            )
        else:
            report.record_pass()

        # Financial events amounts (excluding nulls which require image OCR)
        fe = self.datasets.financial_events
        null_amt = fe[fe["amount"].isnull()]
        if len(null_amt) > 0:
            # Verify each null amount has a matching image in images.csv
            img_events = set(self.datasets.images["related_event_id"])
            unsupported_nulls = set(null_amt["event_id"]) - img_events
            if unsupported_nulls:
                report.add_issue(
                    severity="ERROR",
                    category="numeric_validation",
                    dataset="financial_events",
                    field_name="amount",
                    message=f"{len(unsupported_nulls)} events have null amount with no matching image in images.csv",
                    affected_ids=list(unsupported_nulls),
                )
            else:
                report.add_issue(
                    severity="WARNING",
                    category="numeric_validation",
                    dataset="financial_events",
                    field_name="amount",
                    message=f"{len(null_amt)} events have blank amounts requiring image OCR extraction (all {len(null_amt)} linked to images.csv)",
                    affected_ids=null_amt["event_id"].tolist(),
                )
        else:
            report.record_pass()

        neg_amt = fe[(fe["amount"].notnull()) & (fe["amount"] < 0)]
        if len(neg_amt) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="financial_events",
                field_name="amount",
                message=f"{len(neg_amt)} events have negative amounts",
                affected_ids=neg_amt["event_id"].tolist()[:10],
            )
        else:
            report.record_pass()

        # Minimum allowed amount checks
        bad_min_amt = fe[
            (fe["minimum_allowed_amount"].notnull())
            & (
                (fe["minimum_allowed_amount"] < 0)
                | (fe["amount"].notnull() & (fe["minimum_allowed_amount"] > fe["amount"]))
            )
        ]
        if len(bad_min_amt) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="financial_events",
                field_name="minimum_allowed_amount",
                message=f"{len(bad_min_amt)} events have invalid minimum_allowed_amount (> amount or < 0)",
                affected_ids=bad_min_amt["event_id"].tolist()[:10],
            )
        else:
            report.record_pass()

        # Sample requests amount_safe_to_pay check (0 <= safe <= requested)
        sr = self.datasets.sample_requests
        bad_safe = sr[(sr["amount_safe_to_pay"] < 0) | (sr["amount_safe_to_pay"] > sr["requested_amount"])]
        if len(bad_safe) > 0:
            report.add_issue(
                severity="ERROR",
                category="numeric_validation",
                dataset="sample_requests",
                field_name="amount_safe_to_pay",
                message=f"{len(bad_safe)} sample requests violate 0 <= amount_safe_to_pay <= requested_amount",
                affected_ids=bad_safe["request_id"].tolist(),
            )
        else:
            report.record_pass()

    # -------------------------------------------------------------------------
    # 6. Enumerated Values Validation
    # -------------------------------------------------------------------------
    def _check_enumerated_values(self, report: ValidationReport) -> None:
        enum_checks = [
            ("requests", self.datasets.requests, "request_type", VALID_REQUEST_TYPES),
            ("sample_requests", self.datasets.sample_requests, "request_type", VALID_REQUEST_TYPES),
            ("sample_requests", self.datasets.sample_requests, "affordability_status", VALID_AFFORDABILITY_STATUSES),
            ("sample_requests", self.datasets.sample_requests, "recommended_payment_method", VALID_RECOMMENDED_PAYMENT_METHODS),
            ("financial_profiles", self.datasets.financial_profiles, "home_currency", VALID_CURRENCIES),
            ("financial_events", self.datasets.financial_events, "currency", VALID_CURRENCIES),
            ("financial_events", self.datasets.financial_events, "direction", VALID_EVENT_DIRECTIONS),
            ("financial_events", self.datasets.financial_events, "status", VALID_EVENT_STATUSES),
            ("financial_events", self.datasets.financial_events, "flexibility", VALID_EVENT_FLEXIBILITIES),
            ("financial_events", self.datasets.financial_events, "event_type", VALID_EVENT_TYPES),
            ("exchange_rates", self.datasets.exchange_rates, "from_currency", VALID_CURRENCIES),
            ("exchange_rates", self.datasets.exchange_rates, "to_currency", VALID_CURRENCIES),
            ("request_payment_options", self.datasets.request_payment_options, "payment_method", VALID_PAYMENT_METHODS_OPTIONS),
            ("messages", self.datasets.messages, "source_type", VALID_MESSAGE_SOURCE_TYPES),
        ]

        for ds_name, df, col, valid_set in enum_checks:
            series = df[col].dropna()
            invalid = series[~series.isin(valid_set)]
            if len(invalid) > 0:
                report.add_issue(
                    severity="ERROR",
                    category="enumerated_values",
                    dataset=ds_name,
                    field_name=col,
                    message=f"{len(invalid)} rows in {ds_name}.{col} have invalid values outside {valid_set}",
                    affected_ids=invalid.head(5).tolist(),
                )
            else:
                report.record_pass()

    # -------------------------------------------------------------------------
    # 7. Dataset Consistency Checks
    # -------------------------------------------------------------------------
    def _check_dataset_consistency(self, report: ValidationReport) -> None:
        fp = self.datasets.financial_profiles

        # Consistency: users considering installments vs max_installment_months
        no_inst = fp[~fp["payment_methods_user_will_consider"].str.contains("installments", na=False)]
        invalid_no_inst = no_inst[no_inst["max_installment_months"].notnull()]
        if len(invalid_no_inst) > 0:
            report.add_issue(
                severity="WARNING",
                category="dataset_consistency",
                dataset="financial_profiles",
                field_name="max_installment_months",
                message=f"{len(invalid_no_inst)} profiles without installments consideration have populated max_installment_months",
                affected_ids=invalid_no_inst["user_id"].tolist(),
            )
        else:
            report.record_pass()

        with_inst = fp[fp["payment_methods_user_will_consider"].str.contains("installments", na=False)]
        invalid_with_inst = with_inst[with_inst["max_installment_months"].isnull()]
        if len(invalid_with_inst) > 0:
            report.add_issue(
                severity="WARNING",
                category="dataset_consistency",
                dataset="financial_profiles",
                field_name="max_installment_months",
                message=f"{len(invalid_with_inst)} profiles considering installments have blank max_installment_months",
                affected_ids=invalid_with_inst["user_id"].tolist(),
            )
        else:
            report.record_pass()

        # Consistency: request_payment_options payment_frequency_days non-null only for installments
        opts = self.datasets.request_payment_options
        full_with_freq = opts[(opts["payment_method"] == "full_payment") & (opts["payment_frequency_days"].notnull())]
        if len(full_with_freq) > 0:
            report.add_issue(
                severity="WARNING",
                category="dataset_consistency",
                dataset="request_payment_options",
                field_name="payment_frequency_days",
                message=f"{len(full_with_freq)} full_payment options have payment_frequency_days set",
                affected_ids=full_with_freq["payment_option_id"].tolist(),
            )
        else:
            report.record_pass()

        inst_without_freq = opts[(opts["payment_method"] == "installments") & (opts["payment_frequency_days"].isnull())]
        if len(inst_without_freq) > 0:
            report.add_issue(
                severity="ERROR",
                category="dataset_consistency",
                dataset="request_payment_options",
                field_name="payment_frequency_days",
                message=f"{len(inst_without_freq)} installment options are missing payment_frequency_days",
                affected_ids=inst_without_freq["payment_option_id"].tolist(),
            )
        else:
            report.record_pass()

        # Check physical presence of linked image PNG files
        missing_images = []
        for img_id in self.datasets.images["image_id"]:
            img_path = self.media_dir / f"{img_id}.png"
            if not img_path.is_file():
                missing_images.append(f"{img_id}.png")

        if missing_images:
            report.add_issue(
                severity="ERROR",
                category="dataset_consistency",
                dataset="images",
                field_name="image_id",
                message=f"{len(missing_images)} image files are missing on disk in {self.media_dir}",
                affected_ids=missing_images,
            )
        else:
            report.record_pass()


def validate_datasets(datasets: Datasets, media_dir: Optional[Path] = None) -> ValidationReport:
    """Convenience function to run validation on a Datasets container."""
    validator = DataValidator(datasets, media_dir=media_dir)
    return validator.validate_all()

