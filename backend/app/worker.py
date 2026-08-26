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
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Any

from eir_shared.env import load_root_env, repo_root

from app.core.config import settings
from app.core.deps import get_container
from app.integrations.enterprise.adk_otel import setup_adk_otel
from app.integrations.messaging.pubsub import decode_pubsub_payload

logger = logging.getLogger("eir.worker")
HANDLE_TIMEOUT_S = 180.0


def _spawn_async_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    started = Event()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        started.set()
        loop.run_forever()

    Thread(target=_run, daemon=True, name="eir-worker-async").start()
    if not started.wait(timeout=5):
        raise RuntimeError("worker async loop failed to start")
    return loop


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args: object) -> None:
        return


def _start_health_server() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("", port), _HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    logger.info("health server on port %s", port)


def _inbox_path() -> Path:
    path = repo_root() / settings.data_dir / "pubsub-inbox.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _record(event_type: str, episode_id: str, payload: dict) -> None:
    if settings.environment.strip().lower() == "production":
        return
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
    setup_adk_otel(
        service_name="eir-worker",
        project_id=settings.google_cloud_project,
        enabled=settings.adk_otel_enabled and settings.environment == "production",
    )
    _start_health_server()
    project = settings.google_cloud_project
    subscription = settings.pubsub_subscription
    subscriber = pubsub_v1.SubscriberClient()
    path = subscriber.subscription_path(project, subscription)
    if handle:
        settings.pubsub_handle = True
        get_container.cache_clear()
    container = get_container() if handle else None
    loop = _spawn_async_loop() if handle else None

    def callback(message: Any) -> None:
        try:
            event = decode_pubsub_payload(message.data)
            _record(event.event_type, event.episode_id, event.payload)
            logger.info("consumed %s episode=%s", event.event_type, event.episode_id)
            if handle and container is not None and loop is not None:
                try:
                    message.modify_ack_deadline(int(HANDLE_TIMEOUT_S))
                except Exception:
                    logger.debug("modify_ack_deadline skipped", exc_info=True)
                future = asyncio.run_coroutine_threadsafe(
                    container.runtime.handle(event),
                    loop,
                )
                future.result(timeout=HANDLE_TIMEOUT_S)
            message.ack()
        except Exception:
            logger.exception("failed to consume Pub/Sub message")
            message.nack()

    flow_control = None
    try:
        from google.cloud.pubsub_v1.types import FlowControl

        flow_control = FlowControl(max_messages=1)
    except Exception:
        logger.debug("Pub/Sub FlowControl unavailable", exc_info=True)
    subscribe_kwargs: dict[str, Any] = {"callback": callback}
    if flow_control is not None:
        subscribe_kwargs["flow_control"] = flow_control
    streaming = subscriber.subscribe(path, **subscribe_kwargs)
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
