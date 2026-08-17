"""Messaging / Pub/Sub adapter boundary.

Domain code uses EventBus. Local runtime stays in-process; Pub/Sub is an optional sink.

TODO: subscribe GooglePubSubEventBus from a Cloud Run worker.
"""

from app.integrations.messaging.pubsub import CompositeEventBus, GooglePubSubEventBus

__all__ = ["CompositeEventBus", "GooglePubSubEventBus"]
