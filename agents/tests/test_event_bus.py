import asyncio

from eir_shared.event_bus import InMemoryEventBus
from eir_shared.events import FollowUpDue


def test_event_bus_publish_subscribe() -> None:
    bus = InMemoryEventBus()
    received: list[str] = []

    async def handler(event) -> None:
        received.append(event.event_type)

    bus.subscribe("FollowUpDue", handler)
    event = FollowUpDue(episode_id="ep-1")
    asyncio.run(bus.publish(event))

    assert received == ["FollowUpDue"]
    assert bus.published[0].episode_id == "ep-1"
