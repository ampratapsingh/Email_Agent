"""
config.py — Centralised configuration loader for the Finance Email Agent.

All settings are read from environment variables (loaded from .env).
No secrets are hardcoded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=False)


class Config:
    # ── LLM ──────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

    # ── Email ─────────────────────────────────────────────────────────────────
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Finance Team")

    # ── Payment ───────────────────────────────────────────────────────────────
    PAYMENT_LINK_BASE: str = os.getenv(
        "PAYMENT_LINK_BASE", "https://pay.yourcompany.com/invoice/"
    )

    # ── Escalation contact ────────────────────────────────────────────────────
    FINANCE_MANAGER_EMAIL: str = os.getenv(
        "FINANCE_MANAGER_EMAIL", "finance-manager@yourcompany.com"
    )
    FINANCE_MANAGER_NAME: str = os.getenv("FINANCE_MANAGER_NAME", "Finance Manager")

    # ── Data & Audit ──────────────────────────────────────────────────────────
    DATA_FILE: Path = _ROOT / os.getenv("DATA_FILE", "data/invoices.csv")
    AUDIT_DB_PATH: Path = _ROOT / os.getenv("AUDIT_DB_PATH", "audit/audit_trail.db")

    @classmethod
    def payment_link(cls, invoice_no: str) -> str:
        """Return a unique payment URL for the given invoice."""
        safe_inv = invoice_no.replace("/", "-").replace(" ", "_")
        return f"{cls.PAYMENT_LINK_BASE}{safe_inv}"

    @classmethod
    def validate(cls) -> None:
        """Raise ValueError if required keys are missing."""
        if cls.LLM_PROVIDER == "gemini" and not cls.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Add it to your .env file (see .env.example)."
            )
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file (see .env.example)."
            )
        if not cls.DRY_RUN and not cls.SMTP_USER:
            raise ValueError(
                "SMTP_USER is required when DRY_RUN=false. "
                "Set it in your .env file."
            )
