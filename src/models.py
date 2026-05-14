"""
models.py — Pydantic data models for the Finance Email Agent.

Using Pydantic v2 for:
  - Input validation / sanitisation (security: prevents prompt injection via
    malformed data fields)
  - Structured LLM output parsing (prevents hallucination of wrong fields)
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Escalation Stage Enum
# ─────────────────────────────────────────────────────────────────────────────

class EscalationStage(IntEnum):
    """Maps follow_up_count → tone stage."""
    STAGE_1 = 1  # 1–7 days overdue  — Warm & Friendly
    STAGE_2 = 2  # 8–14 days overdue — Polite but Firm
    STAGE_3 = 3  # 15–21 days overdue — Formal & Serious
    STAGE_4 = 4  # 22–30 days overdue — Stern & Urgent
    ESCALATED = 5  # 30+ days — Flag for Legal / Human Review


STAGE_META = {
    EscalationStage.STAGE_1: {
        "label": "1st Follow-Up",
        "tone": "Warm & Friendly",
        "days_range": "1–7 days overdue",
        "cta": "Pay now via the payment link below.",
        "urgency_color": "#4CAF50",
    },
    EscalationStage.STAGE_2: {
        "label": "2nd Follow-Up",
        "tone": "Polite but Firm",
        "days_range": "8–14 days overdue",
        "cta": "Please confirm your payment date by replying to this email.",
        "urgency_color": "#FF9800",
    },
    EscalationStage.STAGE_3: {
        "label": "3rd Follow-Up",
        "tone": "Formal & Serious",
        "days_range": "15–21 days overdue",
        "cta": "Please respond within 48 hours.",
        "urgency_color": "#F44336",
    },
    EscalationStage.STAGE_4: {
        "label": "4th Follow-Up",
        "tone": "Stern & Urgent",
        "days_range": "22–30 days overdue",
        "cta": "Pay immediately or call us to avoid legal escalation.",
        "urgency_color": "#9C27B0",
    },
    EscalationStage.ESCALATED: {
        "label": "⚠️ Legal Escalation",
        "tone": "Flagged for Human Review",
        "days_range": "30+ days overdue",
        "cta": "Assign to Finance Manager — no auto email.",
        "urgency_color": "#000000",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Input Model — Invoice Record
# ─────────────────────────────────────────────────────────────────────────────

_SAFE_TEXT_RE = re.compile(r"[^\w\s\.,\-@#₹$£€%/:()+]")


def _sanitise(value: str) -> str:
    """
    Security: Strip characters that could be used for prompt injection.
    Keeps alphanumeric, common punctuation, and currency symbols.
    """
    return _SAFE_TEXT_RE.sub("", str(value)).strip()


class InvoiceRecord(BaseModel):
    """Validated, sanitised invoice record read from the data source."""

    invoice_no: str = Field(..., min_length=1, max_length=50)
    client_name: str = Field(..., min_length=1, max_length=100)
    client_email: str = Field(..., max_length=254)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    due_date: date
    follow_up_count: int = Field(default=0, ge=0)
    contact_person: str = Field(..., max_length=100)
    company_name: str = Field(..., max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)

    # Computed fields (set after validation)
    days_overdue: int = Field(default=0)
    escalation_stage: EscalationStage = Field(default=EscalationStage.STAGE_1)

    @field_validator("invoice_no", "client_name", "contact_person", "company_name", mode="before")
    @classmethod
    def sanitise_text(cls, v: str) -> str:
        cleaned = _sanitise(v)
        if not cleaned:
            raise ValueError("Field cannot be empty after sanitisation.")
        return cleaned

    @field_validator("client_email", mode="before")
    @classmethod
    def sanitise_email(cls, v: str) -> str:
        """Basic email sanitisation — remove whitespace."""
        return str(v).strip().lower()

    @field_validator("currency", mode="before")
    @classmethod
    def sanitise_currency(cls, v: str) -> str:
        return re.sub(r"[^A-Z₹$£€]", "", str(v).upper())[:10]

    @model_validator(mode="after")
    def compute_overdue(self) -> "InvoiceRecord":
        today = date.today()
        self.days_overdue = max(0, (today - self.due_date).days)
        self.escalation_stage = _resolve_stage(
            self.days_overdue, self.follow_up_count
        )
        return self

    @property
    def amount_formatted(self) -> str:
        symbol = "₹" if self.currency == "INR" else self.currency
        return f"{symbol}{self.amount:,.0f}"

    @property
    def due_date_formatted(self) -> str:
        return self.due_date.strftime("%d %b %Y")


def _resolve_stage(days_overdue: int, follow_up_count: int) -> EscalationStage:
    """
    Determine the correct escalation stage based on days overdue AND
    how many follow-ups have already been sent.
    """
    if days_overdue > 30 or follow_up_count >= 4:
        return EscalationStage.ESCALATED
    if days_overdue >= 22 or follow_up_count == 3:
        return EscalationStage.STAGE_4
    if days_overdue >= 15 or follow_up_count == 2:
        return EscalationStage.STAGE_3
    if days_overdue >= 8 or follow_up_count == 1:
        return EscalationStage.STAGE_2
    return EscalationStage.STAGE_1


# ─────────────────────────────────────────────────────────────────────────────
# Output Model — Generated Email
# ─────────────────────────────────────────────────────────────────────────────

class GeneratedEmail(BaseModel):
    """
    Structured LLM output — enforced via Pydantic to prevent hallucinations.
    The LLM must return valid JSON matching this schema.
    """

    subject: str = Field(..., min_length=5, max_length=200)
    body: str = Field(..., min_length=50)
    tone_used: str = Field(..., max_length=50)
    stage_label: str = Field(..., max_length=50)
    key_message: str = Field(..., max_length=300)

    @field_validator("subject", "body", "key_message", mode="before")
    @classmethod
    def no_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("LLM returned an empty field — generation failed.")
        return str(v).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Entry
# ─────────────────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    """One row in the audit trail."""

    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    invoice_no: str
    client_name: str
    client_email: str
    amount: float
    currency: str
    days_overdue: int
    follow_up_count: int
    escalation_stage: int
    tone_used: str
    email_subject: str
    email_body: str
    send_status: str          # "sent" | "dry_run" | "error" | "escalated"
    error_message: Optional[str] = None
    dry_run: bool = True
