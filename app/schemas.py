"""Pydantic schemas: the contracts for LLM output and API I/O."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParsedPurchase(BaseModel):
    """Strict schema the LLM must return. Used to validate its JSON output."""
    customer_name: Optional[str] = Field(None, description="Name of the customer/buyer")
    action: Optional[str] = Field(None, description="e.g. bought, returned, paid, ordered")
    item: Optional[str] = Field(None, description="Product/item name")
    quantity: Optional[float] = Field(None, description="Numeric quantity")
    unit: Optional[str] = Field(None, description="Unit, e.g. kg, g, l, pcs")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="LLM's self-reported confidence")


class ParseTextRequest(BaseModel):
    """Body for the manual /parse testing endpoint."""
    message: str = Field(..., min_length=1, examples=["Ramesh bought 2kg Sugar"])
    sender_phone: Optional[str] = None


class TransactionOut(BaseModel):
    id: str
    customer_name: Optional[str]
    action: Optional[str]
    item: Optional[str]
    quantity: Optional[float]
    unit: Optional[str]
    raw_message: str
    sender_phone: Optional[str]
    status: str
    confidence: Optional[float]
    llm_model: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    count: int
    results: list[TransactionOut]
