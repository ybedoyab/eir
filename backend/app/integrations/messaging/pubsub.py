"""Google Pub/Sub event sink and decode helpers.

Local workflow still uses InMemoryEventBus so handlers run in-process.
This adapter publishes the same DomainEvent JSON to Pub/Sub when enabled.
A separate worker may pull the subscription; it must not re-run handlers
while the API process is already subscribed locally.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Protocol

from eir_shared.event_bus import EventHandler, InMemoryEventBus
from eir_shared.events import DomainEvent, parse_event_dict

logger = logging.getLogger("eir.pubsub")


class EventSink(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


def decode_pubsub_payload(data: bytes) -> DomainEvent:
    raw = json.loads(data.decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Pub/Sub payload must be a JSON object")
    return parse_event_dict(raw)


class GooglePubSubEventBus:
    def __init__(self, project: str, topic: str) -> None:
        from google.cloud import pubsub_v1

        self._publisher = pubsub_v1.PublisherClient()
        self._topic = self._publisher.topic_path(project, topic)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        del event_type, handler
        raise NotImplementedError(
            "Subscribe via a dedicated worker. Local runtime uses InMemoryEventBus."
        )

    async def publish(self, event: DomainEvent) -> None:
        payload = json.dumps(event.model_dump(mode="json"), default=str).encode("utf-8")
        future = self._publisher.publish(
            self._topic,
            payload,
            event_type=event.event_type,
            episode_id=event.episode_id,
        )
        await asyncio.to_thread(future.result, 10)
        logger.info("published %s to %s", event.event_type, self._topic)


class CompositeEventBus:
    """Dispatch locally, optionally mirror to a remote sink."""

    def __init__(
        self,
        local: InMemoryEventBus,
        sink: EventSink | None = None,
    ) -> None:
        self._local = local
        self._sink = sink
        self.published = local.published
        self.sink_errors = 0

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._local.subscribe(event_type, handler)

    async def publish(self, event: DomainEvent) -> None:
        await self._local.publish(event)
        if self._sink is None:
            return
        try:
            await self._sink.publish(event)
        except Exception:
            self.sink_errors += 1
            logger.exception("failed to mirror event %s to Pub/Sub", event.event_type)
