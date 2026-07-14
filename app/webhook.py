"""
WhatsApp inbound webhook.

Built against Twilio's WhatsApp Sandbox payload shape (application/x-www-form-urlencoded
with `From` and `Body` fields) since that's the fastest way to get a real
WhatsApp number sending messages into this service for a demo/trial.

To move to Meta's WhatsApp Cloud API in production: swap this router's
parsing of the payload (Meta sends JSON, not form-encoded) - the rest of
the pipeline (ingest_message) does not change. See README for details.
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.logger import get_logger
from app.service import ingest_message

router = APIRouter()
logger = get_logger(__name__)


def _verify_twilio_signature(request: Request) -> None:
    """
    Optional Twilio request-signature validation. Enabled via
    TWILIO_VALIDATE_SIGNATURE=true in production so only Twilio can hit
    this endpoint. Disabled by default for easy local testing.
    """
    settings = get_settings()
    if not settings.twilio_validate_signature:
        return
    from twilio.request_validator import RequestValidator  # imported lazily; optional dep

    signature = request.headers.get("X-Twilio-Signature", "")
    validator = RequestValidator(settings.twilio_auth_token)
    # NOTE: in production, reconstruct the exact URL Twilio signed (including
    # scheme/host as seen by Twilio, e.g. behind your load balancer) and pass
    # the parsed form dict here.
    if not validator.validate(str(request.url), {}, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db),
):
    """Receives an inbound WhatsApp message forwarded by Twilio and ingests it."""
    _verify_twilio_signature(request)

    logger.info("webhook_hit", extra={"ctx_from": From})
    txn = ingest_message(db, message=Body, sender_phone=From)

    # Twilio expects a TwiML (XML) response, even if empty, to acknowledge receipt.
    return_status = "recorded" if txn.status.value != "failed" else "could not parse - stored for review"
    twiml = f"<Response><Message>BazaarSync: {return_status}.</Message></Response>"
    from fastapi import Response
    return Response(content=twiml, media_type="application/xml")
