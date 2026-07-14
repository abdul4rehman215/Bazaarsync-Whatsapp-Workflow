"""
Public REST API.

- POST /parse            manually run the pipeline on arbitrary text (no WhatsApp needed - great for demos/tests)
- GET  /transactions      list stored, structured transactions with filters
- GET  /transactions/{id} fetch a single transaction
- GET  /health            liveness/readiness probe
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Transaction
from app.schemas import ParseTextRequest, TransactionListResponse, TransactionOut
from app.service import ingest_message

router = APIRouter()


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """
    Lightweight shared-secret auth for the API. No-op if API_KEY is unset
    (local dev); enforced automatically once you set API_KEY in .env.
    """
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/parse", response_model=TransactionOut, dependencies=[Depends(require_api_key)])
def parse_message(payload: ParseTextRequest, db: Session = Depends(get_db)):
    """Run the exact same LLM -> DB pipeline the WhatsApp webhook uses, for a raw string."""
    txn = ingest_message(db, message=payload.message, sender_phone=payload.sender_phone)
    return txn


@router.get("/transactions", response_model=TransactionListResponse, dependencies=[Depends(require_api_key)])
def list_transactions(
    db: Session = Depends(get_db),
    customer_name: Optional[str] = None,
    item: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    q = db.query(Transaction)
    if customer_name:
        q = q.filter(Transaction.customer_name.ilike(f"%{customer_name}%"))
    if item:
        q = q.filter(Transaction.item.ilike(f"%{item}%"))
    if status:
        q = q.filter(Transaction.status == status)
    total = q.count()
    results = q.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    return {"count": total, "results": results}


@router.get("/transactions/{transaction_id}", response_model=TransactionOut, dependencies=[Depends(require_api_key)])
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
