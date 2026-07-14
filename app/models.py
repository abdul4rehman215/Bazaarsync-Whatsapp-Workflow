"""ORM models."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TransactionStatus(str, enum.Enum):
    PARSED = "parsed"           # LLM parsed successfully with high confidence
    NEEDS_REVIEW = "needs_review"  # LLM parsed but low confidence / ambiguous
    FAILED = "failed"           # Could not parse into structured data


class Transaction(Base):
    """
    A single structured record derived from an inbound WhatsApp message,
    e.g. "Ramesh bought 2kg Sugar" ->
        customer_name="Ramesh", action="bought", item="Sugar", quantity=2, unit="kg"
    """
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=_uuid)

    # Structured, parsed fields
    customer_name = Column(String, nullable=True, index=True)
    action = Column(String, nullable=True)          # bought / returned / paid / etc.
    item = Column(String, nullable=True, index=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)             # kg, g, l, pcs, ...

    # Provenance / audit
    raw_message = Column(Text, nullable=False)
    sender_phone = Column(String, nullable=True, index=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PARSED, nullable=False)
    confidence = Column(Float, nullable=True)
    llm_model = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
