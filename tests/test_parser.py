"""
Unit tests for the parsing/validation logic. No network calls are made -
we test AnthropicParser._to_parsed_purchase directly against sample LLM
outputs, which is the part of the pipeline most likely to see malformed
input in production.
"""
from app.llm_parser import AnthropicParser
from app.schemas import ParsedPurchase


def test_valid_json_parses_correctly():
    raw = '{"customer_name": "Ramesh", "action": "bought", "item": "Sugar", "quantity": 2, "unit": "kg", "confidence": 0.97}'
    result = AnthropicParser._to_parsed_purchase(raw)
    assert isinstance(result, ParsedPurchase)
    assert result.customer_name == "Ramesh"
    assert result.item == "Sugar"
    assert result.quantity == 2
    assert result.unit == "kg"
    assert result.confidence == 0.97


def test_json_wrapped_in_markdown_fence_is_cleaned():
    raw = '```json\n{"customer_name": "Sita", "action": "returned", "item": "Biscuits", "quantity": 1, "unit": "packet", "confidence": 0.8}\n```'
    result = AnthropicParser._to_parsed_purchase(raw)
    assert result.customer_name == "Sita"
    assert result.action == "returned"


def test_garbage_output_falls_back_gracefully():
    raw = "Sorry, I cannot process this request."
    result = AnthropicParser._to_parsed_purchase(raw)
    assert isinstance(result, ParsedPurchase)
    assert result.confidence == 0.0
    assert result.customer_name is None


def test_unparseable_message_returns_all_nulls():
    raw = '{"customer_name": null, "action": null, "item": null, "quantity": null, "unit": null, "confidence": 0.0}'
    result = AnthropicParser._to_parsed_purchase(raw)
    assert result.item is None
    assert result.confidence == 0.0
