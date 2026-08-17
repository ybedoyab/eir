"""Pub/Sub pull worker.

Default: decode and log events. Do not run WorkflowRuntime here while the
API process already handles events in-memory (that would double-process).

Set WORKFLOW_SUBSCRIBER=pubsub on the API (so it does not bind handlers)
and pass --handle here when the worker owns the recovery loop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from eir_shared.env import load_root_env, repo_root

from app.core.config import settings
from app.core.deps import get_container
from app.integrations.messaging.pubsub import decode_pubsub_payload

logger = logging.getLogger("eir.worker")


def _inbox_path() -> Path:
    path = repo_root() / settings.data_dir / "pubsub-inbox.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _record(event_type: str, episode_id: str, payload: dict) -> None:
    line = json.dumps(
        {"event_type": event_type, "episode_id": episode_id, "payload": payload},
        default=str,
    )
    with _inbox_path().open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run_worker(*, handle: bool) -> None:
    from google.cloud import pubsub_v1

    load_root_env()
    logging.basicConfig(level=logging.INFO)
    project = settings.google_cloud_project
    subscription = settings.pubsub_subscription
    subscriber = pubsub_v1.SubscriberClient()
    path = subscriber.subscription_path(project, subscription)
    if handle:
        settings.workflow_subscriber = "pubsub"
        get_container.cache_clear()
    container = get_container() if handle else None

    def callback(message: Any) -> None:
        try:
            event = decode_pubsub_payload(message.data)
            _record(event.event_type, event.episode_id, event.payload)
            logger.info("consumed %s episode=%s", event.event_type, event.episode_id)
            if handle and container is not None:
                asyncio.run(container.runtime.handle(event))
            message.ack()
        except Exception:
            logger.exception("failed to consume Pub/Sub message")
            message.nack()

    streaming = subscriber.subscribe(path, callback=callback)
    logger.info("listening on %s handle=%s", path, handle)
    try:
        streaming.result()
    except KeyboardInterrupt:
        streaming.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description="EIR Pub/Sub worker")
    parser.add_argument(
        "--handle",
        action="store_true",
        help="Run WorkflowRuntime on each message. Use only if the API is not subscribed locally.",
    )
    args = parser.parse_args()
    run_worker(handle=args.handle or settings.pubsub_handle)


if __name__ == "__main__":
    main()
