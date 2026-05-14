"""
email_sender.py — Email dispatch with SMTP and dry-run support.

Security mitigations:
  - SMTP credentials loaded from .env only
  - TLS/STARTTLS enforced (no plaintext SMTP)
  - SPF/DKIM note: configure at your mail provider level (see README)
  - dry_run mode prevents accidental sends during testing
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .config import Config
from .models import AuditEntry, GeneratedEmail, InvoiceRecord, EscalationStage, STAGE_META

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends generated emails or logs a dry-run entry."""

    def __init__(self, audit_db=None):
        self.audit_db = audit_db

    def dispatch(
        self,
        record: InvoiceRecord,
        email: Optional[GeneratedEmail],
    ) -> AuditEntry:
        """
        Send (or dry-run) the generated email for a record.

        For ESCALATED records, logs an escalation flag instead of sending.
        Returns the AuditEntry that was (or would be) saved.
        """
        stage = record.escalation_stage

        # ── Escalated — no email, just flag ───────────────────────────────────
        if stage == EscalationStage.ESCALATED or email is None:
            entry = AuditEntry(
                timestamp=datetime.utcnow(),
                invoice_no=record.invoice_no,
                client_name=record.client_name,
                client_email=record.client_email,
                amount=record.amount,
                currency=record.currency,
                days_overdue=record.days_overdue,
                follow_up_count=record.follow_up_count,
                escalation_stage=int(stage),
                tone_used="⚠️ Escalated — Human Review Required",
                email_subject="[ESCALATED] " + record.invoice_no,
                email_body=(
                    f"Invoice {record.invoice_no} for {record.client_name} "
                    f"({record.amount_formatted}) is {record.days_overdue} days overdue. "
                    f"Flagged for review by {Config.FINANCE_MANAGER_NAME}."
                ),
                send_status="escalated",
                dry_run=Config.DRY_RUN,
            )
            if self.audit_db:
                self.audit_db.log(entry)
            logger.warning(
                f"[{record.invoice_no}] ⚠️  ESCALATED — "
                f"assigned to {Config.FINANCE_MANAGER_NAME} for manual review."
            )
            return entry

        # ── Build MIME message ────────────────────────────────────────────────
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject
        msg["From"] = f"{Config.EMAIL_FROM_NAME} <{Config.EMAIL_FROM}>"
        msg["To"] = record.client_email

        # Plain-text part
        msg.attach(MIMEText(email.body, "plain", "utf-8"))
        # HTML part (simple wrap)
        html_body = _text_to_html(email.body)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # ── Dry Run ───────────────────────────────────────────────────────────
        if Config.DRY_RUN:
            logger.info(
                f"[DRY RUN] [{record.invoice_no}] To: {record.client_email}\n"
                f"  Subject: {email.subject}\n"
                f"  Body (first 200 chars): {email.body[:200]}..."
            )
            entry = AuditEntry(
                timestamp=datetime.utcnow(),
                invoice_no=record.invoice_no,
                client_name=record.client_name,
                client_email=record.client_email,
                amount=record.amount,
                currency=record.currency,
                days_overdue=record.days_overdue,
                follow_up_count=record.follow_up_count,
                escalation_stage=int(stage),
                tone_used=email.tone_used,
                email_subject=email.subject,
                email_body=email.body,
                send_status="dry_run",
                dry_run=True,
            )
            if self.audit_db:
                self.audit_db.log(entry)
            return entry

        # ── Real SMTP Send ─────────────────────────────────────────────────────
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)    # Enforce TLS
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(
                    Config.EMAIL_FROM,
                    record.client_email,
                    msg.as_string(),
                )
            logger.info(
                f"[SENT] [{record.invoice_no}] → {record.client_email} "
                f"| Stage {int(stage)} | {email.tone_used}"
            )
            status = "sent"
            error_msg = None
        except Exception as exc:
            logger.error(f"[FAILED] [{record.invoice_no}] SMTP error: {exc}")
            status = "error"
            error_msg = str(exc)

        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            invoice_no=record.invoice_no,
            client_name=record.client_name,
            client_email=record.client_email,
            amount=record.amount,
            currency=record.currency,
            days_overdue=record.days_overdue,
            follow_up_count=record.follow_up_count,
            escalation_stage=int(stage),
            tone_used=email.tone_used,
            email_subject=email.subject,
            email_body=email.body,
            send_status=status,
            error_message=error_msg,
            dry_run=False,
        )
        if self.audit_db:
            self.audit_db.log(entry)
        return entry


def _text_to_html(text: str) -> str:
    """Convert plain text email body to simple HTML."""
    lines = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_lines = [
        f"<p>{line}</p>" if line.strip() else "<br/>"
        for line in lines.split("\n")
    ]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
    p {{ margin: 0 0 12px; }}
  </style>
</head>
<body>
{"".join(html_lines)}
</body>
</html>"""
