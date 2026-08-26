"""Parse a supplier quote out of a call transcript.

Only the supplier's own words are parsed. Nothing is inferred: a transcript that
does not state a number yields no quote, and the case moves to human review
rather than guessing a price.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_UNITS = re.compile(r"([\d][\d,]*)\s+units\b", re.IGNORECASE)
_PRICE = re.compile(
    r"([\d]+(?:\.[\d]{1,2})?)\s*(?:usd|us dollars|dollars|per unit)",
    re.IGNORECASE,
)
_LEAD = re.compile(r"(\d+)\s*(?:business\s+)?days?\b", re.IGNORECASE)
_OUT_OF_STOCK = re.compile(r"out of stock|cannot supply|no stock|unavailable", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedQuote:
    available_units: int
    unit_price: float
    lead_time_days: int


def supplier_text(conversation: list[dict[str, Any]]) -> str:
    return " ".join(
        str(turn.get("text", ""))
        for turn in conversation
        if str(turn.get("role", "")).lower() == "supplier"
    )


def quote_from_conversation(conversation: list[dict[str, Any]]) -> ParsedQuote | None:
    text = supplier_text(conversation)
    if not text or _OUT_OF_STOCK.search(text):
        return None

    units = _UNITS.search(text)
    price = _PRICE.search(text)
    lead = _LEAD.search(text)
    if units is None or price is None:
        return None

    return ParsedQuote(
        available_units=int(units.group(1).replace(",", "")),
        unit_price=float(price.group(1)),
        lead_time_days=int(lead.group(1)) if lead else 0,
    )
