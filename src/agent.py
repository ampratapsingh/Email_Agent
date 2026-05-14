"""
agent.py — Main orchestration agent for the Finance Email workflow.

Flow:
  1. Load & validate invoice records from CSV
  2. Identify overdue records
  3. For each record, determine escalation stage
  4. Generate email with LLM (or flag for escalation)
  5. Send / dry-run / flag
  6. Log everything to audit trail
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .audit import AuditDB
from .config import Config
from .data_loader import load_invoices
from .email_sender import EmailSender
from .llm_engine import EmailGenerator
from .models import AuditEntry, EscalationStage, InvoiceRecord

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Summary of one agent run."""
    total_records: int = 0
    overdue_records: int = 0
    emails_generated: int = 0
    emails_sent: int = 0
    dry_runs: int = 0
    escalated: int = 0
    errors: int = 0
    skipped_invalid: int = 0
    audit_entries: List[AuditEntry] = field(default_factory=list)

    def summary(self) -> str:
        mode = "DRY RUN" if Config.DRY_RUN else "LIVE"
        return (
            f"\n{'='*55}\n"
            f"  Finance Email Agent — Run Summary [{mode}]\n"
            f"{'='*55}\n"
            f"  Total records loaded  : {self.total_records}\n"
            f"  Overdue (actionable)  : {self.overdue_records}\n"
            f"  Emails generated      : {self.emails_generated}\n"
            f"  Emails sent           : {self.emails_sent}\n"
            f"  Dry-run logged        : {self.dry_runs}\n"
            f"  Escalated to legal    : {self.escalated}\n"
            f"  Errors                : {self.errors}\n"
            f"  Invalid rows skipped  : {self.skipped_invalid}\n"
            f"{'='*55}\n"
        )


class FinanceEmailAgent:
    """
    Orchestrates the full Finance Credit Follow-Up Email workflow.

    Usage:
        agent = FinanceEmailAgent()
        result = agent.run()
        print(result.summary())
    """

    def __init__(self):
        self.audit_db = AuditDB(Config.AUDIT_DB_PATH)
        self.generator = EmailGenerator()
        self.sender = EmailSender(audit_db=self.audit_db)

    def run(
        self,
        data_file: Optional[str] = None,
        invoice_filter: Optional[List[str]] = None,
    ) -> AgentResult:
        """
        Execute the full email agent workflow.

        Args:
            data_file:      Override the CSV/Excel path.
            invoice_filter: If provided, only process these invoice numbers.

        Returns:
            AgentResult with run statistics and audit entries.
        """
        result = AgentResult()
        file_path = data_file or Config.DATA_FILE

        # ── Step 1: Load & validate ───────────────────────────────────────────
        logger.info(f"Loading invoice data from: {file_path}")
        all_records, error_rows = load_invoices(file_path)
        result.total_records = len(all_records) + len(error_rows)
        result.skipped_invalid = len(error_rows)

        # ── Step 2: Filter overdue records ────────────────────────────────────
        overdue = [r for r in all_records if r.days_overdue > 0]
        if invoice_filter:
            overdue = [r for r in overdue if r.invoice_no in invoice_filter]
        result.overdue_records = len(overdue)

        if not overdue:
            logger.info("No overdue records found. Nothing to do.")
            return result

        logger.info(
            f"Processing {len(overdue)} overdue records "
            f"({'DRY RUN' if Config.DRY_RUN else 'LIVE MODE'})..."
        )

        # ── Step 3: Process each record ───────────────────────────────────────
        for record in overdue:
            entry = self._process_record(record, result)
            if entry:
                result.audit_entries.append(entry)

        logger.info(result.summary())
        return result

    def _process_record(
        self, record: InvoiceRecord, result: AgentResult
    ) -> Optional[AuditEntry]:
        """Process a single invoice record end-to-end."""
        try:
            # ── Generate email (or skip for escalated) ────────────────────────
            email = self.generator.generate(record)

            if email:
                result.emails_generated += 1

            # ── Send / dry-run / escalate ─────────────────────────────────────
            entry = self.sender.dispatch(record, email)

            # ── Tally results ─────────────────────────────────────────────────
            if entry.send_status == "sent":
                result.emails_sent += 1
            elif entry.send_status == "dry_run":
                result.dry_runs += 1
            elif entry.send_status == "escalated":
                result.escalated += 1
            elif entry.send_status == "error":
                result.errors += 1

            return entry

        except Exception as exc:
            logger.error(
                f"[{record.invoice_no}] Unexpected error during processing: {exc}",
                exc_info=True,
            )
            result.errors += 1
            # Log error to audit even on failure
            error_entry = AuditEntry(
                invoice_no=record.invoice_no,
                client_name=record.client_name,
                client_email=record.client_email,
                amount=record.amount,
                currency=record.currency,
                days_overdue=record.days_overdue,
                follow_up_count=record.follow_up_count,
                escalation_stage=int(record.escalation_stage),
                tone_used="ERROR",
                email_subject="ERROR",
                email_body="",
                send_status="error",
                error_message=str(exc),
                dry_run=Config.DRY_RUN,
            )
            self.audit_db.log(error_entry)
            return error_entry
