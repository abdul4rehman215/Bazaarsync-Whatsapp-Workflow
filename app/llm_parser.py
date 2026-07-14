"""
LLM parsing layer.

Turns a free-text WhatsApp message like "Ramesh bought 2kg Sugar" into a
validated ParsedPurchase object. Designed to be provider-agnostic (an
abstract base class) so swapping Claude for another model later is a
one-class change, not a rewrite.
"""
import json
import re
from abc import ABC, abstractmethod

from anthropic import Anthropic, APIError

from app.config import get_settings
from app.logger import get_logger
from app.schemas import ParsedPurchase

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a strict data-extraction engine for a small retail bookkeeping app called BazaarSync.

You will receive one free-text message (often shorthand, from WhatsApp) describing a shop transaction, e.g.:
"Ramesh bought 2kg Sugar"
"Sita returned 1 packet biscuits"
"paid 500 by Ramesh"

Extract the transaction into JSON with EXACTLY this shape and nothing else:
{
  "customer_name": string or null,
  "action": string or null,      // normalize to one of: bought, returned, paid, ordered, other
  "item": string or null,
  "quantity": number or null,
  "unit": string or null,        // normalize to one of: kg, g, l, ml, pcs, packet, box, or null
  "confidence": number           // 0.0-1.0, your own confidence this extraction is correct
}

Rules:
- Output ONLY the JSON object. No prose, no markdown fences, no explanation.
- If a field cannot be determined, use null for it.
- If the message is not a parseable transaction at all, return all fields null and confidence 0.0.
- Never invent information that is not present or clearly implied in the message.
"""


class BaseLLMParser(ABC):
    @abstractmethod
    def parse(self, message: str) -> ParsedPurchase:
        ...


class AnthropicParser(BaseLLMParser):
    def __init__(self):
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    def parse(self, message: str) -> ParsedPurchase:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message}],
            )
            raw_text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
        except APIError as exc:
            logger.error("llm_call_failed", extra={"ctx_error": str(exc)})
            raise

        return self._to_parsed_purchase(raw_text)

    @staticmethod
    def _to_parsed_purchase(raw_text: str) -> ParsedPurchase:
        # Defensive: strip accidental markdown fences even though the prompt forbids them.
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        try:
            data = json.loads(cleaned)
            return ParsedPurchase(**data)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning(
                "llm_output_validation_failed",
                extra={"ctx_raw_output": raw_text, "ctx_error": str(exc)},
            )
            # Fail safe: return an empty, zero-confidence result rather than crashing
            # the request. The caller stores this as status=failed for human review.
            return ParsedPurchase(confidence=0.0)


_parser_instance: BaseLLMParser | None = None


def get_parser() -> BaseLLMParser:
    """Simple singleton so we don't re-init the API client on every request."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = AnthropicParser()
    return _parser_instance
