"""Messaging / Pub/Sub adapter boundary.

Domain code uses eir_shared.event_bus.EventBus. This package is the future
home of GooglePubSubEventBus wiring for the API process.

TODO: wire InMemoryEventBus -> GooglePubSubEventBus via PUBSUB_TOPIC.
"""
