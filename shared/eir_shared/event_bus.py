"""Event bus protocol and local implementation.

Domain logic depends only on EventBus. A GooglePubSubEventBus adapter can be
added later without changing publishers or subscribers.

TODO: implement GooglePubSubEventBus using Google Cloud Pub/Sub.
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


class GooglePubSubEventBus:
    """Placeholder for the managed Pub/Sub adapter.

    TODO: publish DomainEvent payloads to PUBSUB_TOPIC and subscribe via a
    Cloud Run / Agent Runtime worker. Do not import this from domain modules.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "GooglePubSubEventBus is not implemented. Use InMemoryEventBus locally."
        )
