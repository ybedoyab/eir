"""Messaging / Pub/Sub adapter boundary.

Domain code uses EventBus. Local runtime stays in-process; Pub/Sub is an optional sink.
`app.worker` pulls `PUBSUB_SUBSCRIPTION` for audit (or `--handle` when the API is not subscribed).
"""

from app.integrations.messaging.pubsub import (
    CompositeEventBus,
    GooglePubSubEventBus,
    decode_pubsub_payload,
)

__all__ = ["CompositeEventBus", "GooglePubSubEventBus", "decode_pubsub_payload"]
