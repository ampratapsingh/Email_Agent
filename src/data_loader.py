"""
data_loader.py — Load and validate invoice records from CSV / Excel.

Security note:
  - All records are validated through InvoiceRecord (Pydantic) which
    sanitises text fields to prevent prompt injection.
  - Invalid rows are logged and skipped, not silently used.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from .models import InvoiceRecord, EscalationStage

logger = logging.getLogger(__name__)


def load_invoices(file_path: str | Path) -> Tuple[List[InvoiceRecord], List[dict]]:
    """
    Load invoice records from a CSV or Excel file.

    Returns:
        (valid_records, error_rows)
        valid_records: List of validated InvoiceRecord objects
        error_rows:    List of dicts with 'row' and 'error' for failed rows
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, dtype=str)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .xlsx")

    logger.info(f"Loaded {len(df)} rows from {path.name}")

    valid_records: List[InvoiceRecord] = []
    error_rows: List[dict] = []

    for idx, row in df.iterrows():
        raw = row.to_dict()
        try:
            # Convert numeric & date fields
            record = InvoiceRecord(
                invoice_no=raw.get("invoice_no", ""),
                client_name=raw.get("client_name", ""),
                client_email=raw.get("client_email", ""),
                amount=float(str(raw.get("amount", "0")).replace(",", "")),
                currency=str(raw.get("currency", "INR")),
                due_date=pd.to_datetime(raw.get("due_date")).date(),
                follow_up_count=int(float(str(raw.get("follow_up_count", "0")))),
                contact_person=raw.get("contact_person", ""),
                company_name=raw.get("company_name", ""),
                phone=raw.get("phone"),
            )
            valid_records.append(record)
        except Exception as exc:
            logger.warning(f"Row {idx} skipped — validation error: {exc}")
            error_rows.append({"row": idx, "data": raw, "error": str(exc)})

    overdue = [r for r in valid_records if r.days_overdue > 0]
    escalated = [r for r in valid_records if r.escalation_stage == EscalationStage.ESCALATED]

    logger.info(
        f"Parsed: {len(valid_records)} valid | "
        f"{len(overdue)} overdue | "
        f"{len(escalated)} escalated to legal | "
        f"{len(error_rows)} skipped"
    )

    return valid_records, error_rows


def get_overdue_records(file_path: str | Path) -> List[InvoiceRecord]:
    """Convenience wrapper — returns only overdue (actionable) records."""
    all_records, _ = load_invoices(file_path)
    return [r for r in all_records if r.days_overdue > 0]
