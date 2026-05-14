"""
audit.py — SQLite-backed audit trail for all email actions.

Every generated email, send attempt, dry-run, and escalation flag
is persisted here for compliance and audit purposes.

Security note:
  - Uses SQLAlchemy parameterised queries — no raw SQL string formatting
    (prevents SQL injection)
  - PII fields (email body, client name) stored locally only
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .models import AuditEntry

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    """ORM model for the audit_log table."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    invoice_no = Column(String(50), nullable=False, index=True)
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(254), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    days_overdue = Column(Integer, nullable=False)
    follow_up_count = Column(Integer, nullable=False)
    escalation_stage = Column(Integer, nullable=False)
    tone_used = Column(String(50), nullable=False)
    email_subject = Column(String(200), nullable=False)
    email_body = Column(Text, nullable=False)
    send_status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    dry_run = Column(Boolean, nullable=False, default=True)


class AuditDB:
    """Manages the SQLite audit trail database."""

    def __init__(self, db_path: str | Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        self._engine = create_engine(url, echo=False)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)
        logger.info(f"Audit DB initialised at {db_path}")

    def log(self, entry: AuditEntry) -> int:
        """Persist one audit entry. Returns the generated row ID."""
        with self._Session() as session:
            row = AuditLog(
                timestamp=entry.timestamp,
                invoice_no=entry.invoice_no,
                client_name=entry.client_name,
                client_email=entry.client_email,
                amount=entry.amount,
                currency=entry.currency,
                days_overdue=entry.days_overdue,
                follow_up_count=entry.follow_up_count,
                escalation_stage=entry.escalation_stage,
                tone_used=entry.tone_used,
                email_subject=entry.email_subject,
                email_body=entry.email_body,
                send_status=entry.send_status,
                error_message=entry.error_message,
                dry_run=entry.dry_run,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            logger.debug(f"Audit entry saved (id={row.id}) for {entry.invoice_no}")
            return row.id

    def get_all(self) -> List[AuditEntry]:
        """Retrieve all audit entries, newest first."""
        with self._Session() as session:
            rows = (
                session.query(AuditLog)
                .order_by(AuditLog.timestamp.desc())
                .all()
            )
            return [
                AuditEntry(
                    id=r.id,
                    timestamp=r.timestamp,
                    invoice_no=r.invoice_no,
                    client_name=r.client_name,
                    client_email=r.client_email,
                    amount=r.amount,
                    currency=r.currency,
                    days_overdue=r.days_overdue,
                    follow_up_count=r.follow_up_count,
                    escalation_stage=r.escalation_stage,
                    tone_used=r.tone_used,
                    email_subject=r.email_subject,
                    email_body=r.email_body,
                    send_status=r.send_status,
                    error_message=r.error_message,
                    dry_run=r.dry_run,
                )
                for r in rows
            ]

    def get_stats(self) -> dict:
        """Return summary statistics for the dashboard."""
        with self._Session() as session:
            total = session.query(AuditLog).count()
            sent = session.query(AuditLog).filter(AuditLog.send_status == "sent").count()
            dry_run = session.query(AuditLog).filter(AuditLog.send_status == "dry_run").count()
            escalated = session.query(AuditLog).filter(AuditLog.send_status == "escalated").count()
            errors = session.query(AuditLog).filter(AuditLog.send_status == "error").count()
            return {
                "total": total,
                "sent": sent,
                "dry_run": dry_run,
                "escalated": escalated,
                "errors": errors,
            }
