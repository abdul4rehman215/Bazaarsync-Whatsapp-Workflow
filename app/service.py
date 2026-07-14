"""
Shared business logic: parse a raw message -> validate -> persist -> log.

Both the WhatsApp webhook and the manual /parse testing endpoint funnel
through this single function so behavior never diverges between the two
entry points.
"""
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm_parser import get_parser
from app.logger import get_logger
from app.models import Transaction, TransactionStatus

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.6


def ingest_message(db: Session, message: str, sender_phone: str | None = None) -> Transaction:
    """
    Parse a raw text message with the LLM and persist the structured result.
    Never raises for "bad" input - unparseable messages are stored with
    status=failed/needs_review so a human can triage them later, which is
    what "production-ready" means for a pipeline fed by messy free text.
    """
    settings = get_settings()
    logger.info("message_received", extra={"ctx_sender": sender_phone, "ctx_length": len(message)})

    try:
        parsed = get_parser().parse(message)
        if parsed.confidence >= CONFIDENCE_THRESHOLD and parsed.item:
            status = TransactionStatus.PARSED
        elif parsed.item or parsed.customer_name:
            status = TransactionStatus.NEEDS_REVIEW
        else:
            status = TransactionStatus.FAILED
    except Exception as exc:  # LLM call itself failed (network, auth, rate limit, etc.)
        logger.error("parse_failed_hard", extra={"ctx_error": str(exc)})
        parsed = None
        status = TransactionStatus.FAILED

    txn = Transaction(
        customer_name=parsed.customer_name if parsed else None,
        action=parsed.action if parsed else None,
        item=parsed.item if parsed else None,
        quantity=parsed.quantity if parsed else None,
        unit=parsed.unit if parsed else None,
        raw_message=message,
        sender_phone=sender_phone,
        status=status,
        confidence=parsed.confidence if parsed else None,
        llm_model=settings.anthropic_model,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    logger.info(
        "transaction_stored",
        extra={"ctx_transaction_id": txn.id, "ctx_status": status.value, "ctx_confidence": txn.confidence},
    )
    return txn
