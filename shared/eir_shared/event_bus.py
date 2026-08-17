"""Event bus protocol and local implementation.

Domain logic depends only on EventBus. Pub/Sub lives in the backend messaging
adapter so this package stays free of GCP SDKs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Protocol

from eir_shared.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...


class InMemoryEventBus:
    """Process-local pub/sub. Not durable across restarts."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self.published: list[DomainEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for handler in list(self._handlers.get(event.event_type, [])):
            await handler(event)
