"""Supplier voice channel. Separate from the patient channel by design.

The patient outreach provider carries a ``patient_id`` and is guarded by the
synthetic-patient rule. A supplier call is a business call to a vendor, so it
gets its own protocol rather than borrowing — and loosening — that one.

Synthetic providers complete in-process. A real PSTN provider only starts the
call; the quote would arrive later through an authenticated callback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import uuid4

SupplierVoiceMode = Literal["sync", "async"]


@dataclass
class SupplierCallResult:
    call_id: str
    correlation_id: str
    provider: str
    mode: SupplierVoiceMode
    conversation: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SupplierVoiceProvider(Protocol):
    provider_name: str
    mode: SupplierVoiceMode

    async def start_supplier_call(
        self,
        *,
        to: str,
        case_id: str,
        supplier_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> SupplierCallResult: ...

    async def end_call(self, call_id: str) -> None: ...


class SyntheticSupplierVoiceProvider:
    """Scripted vendor stub. Places no calls and reaches no real network.

    The catalog figures are handed in as call metadata and spoken back in the
    transcript, which the handler then parses. That parse step is deliberate: it
    is the same code path a real PSTN transcript would take, so swapping in a
    live provider does not change how a quote is read.
    """

    provider_name = "synthetic-supplier-voice"
    mode: SupplierVoiceMode = "sync"

    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}
        self._seq = 0

    async def start_supplier_call(
        self,
        *,
        to: str,
        case_id: str,
        supplier_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> SupplierCallResult:
        self._seq += 1
        meta = dict(metadata or {})
        call_id = f"supplier-call-{self._seq}"
        correlation_id = str(uuid4())
        conversation = _scripted_quote_call(meta)
        self.calls[call_id] = {
            "to": to,
            "case_id": case_id,
            "supplier_id": supplier_id,
            "metadata": meta,
            "conversation": conversation,
            "correlation_id": correlation_id,
            "ended": False,
        }
        return SupplierCallResult(
            call_id=call_id,
            correlation_id=correlation_id,
            provider=self.provider_name,
            mode=self.mode,
            conversation=conversation,
            metadata=meta,
        )

    async def end_call(self, call_id: str) -> None:
        if call_id in self.calls:
            self.calls[call_id]["ended"] = True


class UnavailableSupplierVoiceProvider:
    """Every vendor line goes unanswered. Used to exercise the no-quote path."""

    provider_name = "synthetic-supplier-unreachable"
    mode: SupplierVoiceMode = "sync"

    async def start_supplier_call(
        self,
        *,
        to: str,
        case_id: str,
        supplier_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> SupplierCallResult:
        return SupplierCallResult(
            call_id=f"unanswered-{uuid4().hex[:8]}",
            correlation_id=str(uuid4()),
            provider=self.provider_name,
            mode=self.mode,
            conversation=[],
            metadata={"answered": False},
        )

    async def end_call(self, call_id: str) -> None:
        return None


def _scripted_quote_call(meta: dict[str, Any]) -> list[dict[str, str]]:
    item_name = str(meta.get("item_name") or meta.get("sku") or "the item")
    quantity = int(meta.get("quantity") or 0)
    unit = str(meta.get("unit") or "unit")
    contact = str(meta.get("contact_name") or "there")
    available = int(meta.get("available_units") or 0)
    unit_price = float(meta.get("unit_price") or 0.0)
    lead_time = int(meta.get("lead_time_days") or 0)

    if available <= 0:
        return [
            {
                "role": "agent",
                "text": (
                    f"Hello {contact}, this is the EIR pharmacy assistant calling about "
                    f"{item_name}. We need {quantity} {unit}."
                ),
            },
            {
                "role": "supplier",
                "text": f"We are out of stock on {item_name} right now.",
            },
        ]

    return [
        {
            "role": "agent",
            "text": (
                f"Hello {contact}, this is the EIR pharmacy assistant calling about a "
                f"restock of {item_name}. We need {quantity} {unit}. What can you do?"
            ),
        },
        {
            "role": "supplier",
            "text": (
                f"Let me check. We can ship {available} units at {unit_price:.2f} USD "
                f"per unit, delivered in {lead_time} days."
            ),
        },
        {
            "role": "agent",
            "text": (
                "Thank you. I am recording that quote and our pharmacy lead will "
                "authorize the order before it is placed."
            ),
        },
    ]
