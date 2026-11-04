"""Module 4A: Message Analyzer for Buy or Wait Financial Affordability Agent.

Extracts structured financial signals from messages (in English and Indonesian),
including salary updates, payment dates, pending income flags, and event amendments.
"""

from dataclasses import dataclass
from decimal import Decimal
import logging
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MessageFinding:
    """Structured financial finding extracted from a user or service message."""

    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    finding_type: str
    extracted_value: Optional[Union[Decimal, float, str]]
    currency: Optional[str]
    effective_date: Optional[str]
    is_confirmed: bool
    confidence: float
    evidence_text: str
    original_text: str
    sent_at: str
    source_type: str


class MessageAnalyzer:
    """Deterministic analyzer for English and Indonesian financial messages."""

    def __init__(self, messages_df: pd.DataFrame):
        """Initialize the MessageAnalyzer with messages DataFrame."""
        self.messages_df = messages_df

    def analyze_all(self) -> List[MessageFinding]:
        """Analyze all messages in messages_df and return a list of findings."""
        findings: List[MessageFinding] = []
        for _, row in self.messages_df.iterrows():
            finding = self.analyze_row(row)
            if finding is not None:
                findings.append(finding)
        return findings

    def analyze_row(self, row: Union[pd.Series, Dict[str, Any]]) -> Optional[MessageFinding]:
        """Analyze a single message record and extract financial findings."""
        msg_id = str(row.get("message_id", "")).strip()
        user_id = str(row.get("user_id", "")).strip()
        req_id = row.get("request_id")
        req_id_str = str(req_id).strip() if pd.notna(req_id) and str(req_id).strip() != "" else None
        evt_id = row.get("related_event_id")
        evt_id_str = str(evt_id).strip() if pd.notna(evt_id) and str(evt_id).strip() != "" else None
        sent_at = str(row.get("sent_at", "")).strip()
        source_type = str(row.get("source_type", "")).strip()
        text = str(row.get("message_text", "")).strip()

        if not text:
            return None

        # ---------------------------------------------------------------------
        # 1. Salary amount and/or date revisions (English & Indonesian)
        # ---------------------------------------------------------------------
        # Regex for salary amount in English or Indonesian
        sal_match = re.search(
            r"(?:gaji\s+bulanan.*?menjadi|gaji\s+pokok.*?adalah|monthly\s+pay\s+is|salary\s+is\s+reduced\s+to|"
            r"regular\s+salary\s+of|salary\s+will\s+be|regular\s+salary.*?is|temporary\s+monthly\s+pay\s+is)\s*"
            r"(IDR|EUR|USD|INR|ZAR)\s*([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        date_match = re.search(
            r"(?:expected\s+on|credit\s+date\s+is|resumes\s+on|berlaku\s+mulai|"
            r"penyelesaian\s+diperkirakan\s+pada)\s*(\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )

        if sal_match:
            currency = sal_match.group(1).upper()
            amt_str = sal_match.group(2).replace(",", "")
            amount = Decimal(amt_str)
            eff_date = date_match.group(1) if date_match else None

            # Determine subtype based on wording
            if re.search(r"reduced\s+to|pengurangan", text, re.IGNORECASE):
                finding_type = "salary_reduction"
            elif re.search(r"temporary|sementara", text, re.IGNORECASE):
                finding_type = "temporary_salary_adjustment"
            elif re.search(r"resumes|kembali", text, re.IGNORECASE):
                finding_type = "salary_resumption"
            else:
                finding_type = "salary_update"

            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type=finding_type,
                extracted_value=amount,
                currency=currency,
                effective_date=eff_date,
                is_confirmed=True,
                confidence=1.0,
                evidence_text=sal_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 2. Confirmed Invoice Payment (Indonesian / English freelancing/services)
        # ---------------------------------------------------------------------
        inv_match = re.search(
            r"(?:pembayaran\s+faktur\s+sebesar|invoice\s+payment\s+of)\s*(IDR|EUR|USD|INR|ZAR)\s*([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if inv_match:
            currency = inv_match.group(1).upper()
            amt_str = inv_match.group(2).replace(",", "")
            amount = Decimal(amt_str)
            eff_date = date_match.group(1) if date_match else None

            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="confirmed_invoice_payment",
                extracted_value=amount,
                currency=currency,
                effective_date=eff_date,
                is_confirmed=True,
                confidence=1.0,
                evidence_text=inv_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 3. Standalone Salary Date Revision
        # ---------------------------------------------------------------------
        if date_match and re.search(r"salary|gaji|payroll|penggajian", text, re.IGNORECASE):
            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="salary_date_change",
                extracted_value=None,
                currency=None,
                effective_date=date_match.group(1),
                is_confirmed=True,
                confidence=1.0,
                evidence_text=date_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 4. Rent / Expense percentage changes (e.g. lease renewal)
        # ---------------------------------------------------------------------
        rent_match = re.search(r"rent\s+by\s*(\d+)%", text, re.IGNORECASE)
        if rent_match:
            pct = float(rent_match.group(1))
            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="rent_increase_percentage",
                extracted_value=pct,
                currency=None,
                effective_date=None,
                is_confirmed=True,
                confidence=0.95,
                evidence_text=rent_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 5. Contract termination / seasonal end
        # ---------------------------------------------------------------------
        if re.search(r"contract\s+has\s+ended|kontrak\s+telah\s+berakhir", text, re.IGNORECASE):
            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="contract_ended",
                extracted_value=None,
                currency=None,
                effective_date=None,
                is_confirmed=True,
                confidence=1.0,
                evidence_text="contract has ended",
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 6. Unconfirmed / Pending / Delayed credit or bonus
        # ---------------------------------------------------------------------
        pending_match = re.search(
            r"(still\s+pending|not\s+reached\s+your\s+account|belum\s+disetujui|masih\s+menunggu|"
            r"no\s+units\s+have\s+been\s+sold|no\s+cash\s+proceeds|not\s+withdrawable\s+until|"
            r"tidak\s+masuk\s+pembayaran)",
            text,
            re.IGNORECASE,
        )
        if pending_match:
            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="unconfirmed_pending_funds",
                extracted_value=None,
                currency=None,
                effective_date=None,
                is_confirmed=False,
                confidence=1.0,
                evidence_text=pending_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 7. Settlement confirmation / event closed
        # ---------------------------------------------------------------------
        settled_match = re.search(
            r"(proceeds\s+have\s+reached\s+your\s+account|claim\s+is\s+now\s+closed|sudah\s+dikonfirmasi)",
            text,
            re.IGNORECASE,
        )
        if settled_match:
            return MessageFinding(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id_str,
                related_event_id=evt_id_str,
                finding_type="payment_settled_confirmed",
                extracted_value=None,
                currency=None,
                effective_date=None,
                is_confirmed=True,
                confidence=1.0,
                evidence_text=settled_match.group(0),
                original_text=text,
                sent_at=sent_at,
                source_type=source_type,
            )

        # ---------------------------------------------------------------------
        # 8. Informational / Notice message
        # ---------------------------------------------------------------------
        return MessageFinding(
            message_id=msg_id,
            user_id=user_id,
            request_id=req_id_str,
            related_event_id=evt_id_str,
            finding_type="general_financial_notice",
            extracted_value=None,
            currency=None,
            effective_date=None,
            is_confirmed=False,
            confidence=0.5,
            evidence_text=text[:60],
            original_text=text,
            sent_at=sent_at,
            source_type=source_type,
        )

    def get_findings_for_user(self, user_id: str) -> List[MessageFinding]:
        """Filter findings relevant to a specific user."""
        return [f for f in self.analyze_all() if f.user_id == user_id]

    def get_findings_for_event(self, event_id: str) -> List[MessageFinding]:
        """Filter findings explicitly linked to a financial event."""
        return [f for f in self.analyze_all() if f.related_event_id == event_id]

