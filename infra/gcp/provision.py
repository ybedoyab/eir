"""Idempotent GCP bootstrap for project eir-ata.

Enables APIs and creates Pub/Sub, optional Firestore, and optional FHIR store.
Does not print or upload secrets.
"""

from __future__ import annotations

import subprocess
import sys

PROJECT = "eir-ata"
LOCATION = "us-central1"
TOPIC = "eir-recovery-events"
SUBSCRIPTION = "eir-recovery-events-worker"
DATASET = "eir"
FHIR_STORE = "fhir-r4"


def _run(args: list[str], *, ok_codes: set[int] | None = None) -> int:
    ok_codes = ok_codes or {0}
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(args, check=False)
    if completed.returncode not in ok_codes:
        print(f"command failed with {completed.returncode}", file=sys.stderr)
    return completed.returncode


def main() -> int:
    _run(
        [
            "gcloud",
            "services",
            "enable",
            "pubsub.googleapis.com",
            "healthcare.googleapis.com",
            "firestore.googleapis.com",
            f"--project={PROJECT}",
        ]
    )
    if _run(["gcloud", "pubsub", "topics", "describe", TOPIC, f"--project={PROJECT}"]) != 0:
        _run(["gcloud", "pubsub", "topics", "create", TOPIC, f"--project={PROJECT}"])
    if (
        _run(
            [
                "gcloud",
                "pubsub",
                "subscriptions",
                "describe",
                SUBSCRIPTION,
                f"--project={PROJECT}",
            ]
        )
        != 0
    ):
        _run(
            [
                "gcloud",
                "pubsub",
                "subscriptions",
                "create",
                SUBSCRIPTION,
                f"--topic={TOPIC}",
                "--ack-deadline=60",
                f"--project={PROJECT}",
            ]
        )
    firestore = _run(
        [
            "gcloud",
            "firestore",
            "databases",
            "describe",
            f"--project={PROJECT}",
            "--database=(default)",
        ]
    )
    if firestore != 0:
        _run(
            [
                "gcloud",
                "firestore",
                "databases",
                "create",
                f"--project={PROJECT}",
                f"--location={LOCATION}",
                "--type=firestore-native",
            ]
        )
    dataset = _run(
        [
            "gcloud",
            "healthcare",
            "datasets",
            "describe",
            DATASET,
            f"--location={LOCATION}",
            f"--project={PROJECT}",
        ]
    )
    if dataset != 0:
        _run(
            [
                "gcloud",
                "healthcare",
                "datasets",
                "create",
                DATASET,
                f"--location={LOCATION}",
                f"--project={PROJECT}",
            ]
        )
    store = _run(
        [
            "gcloud",
            "healthcare",
            "fhir-stores",
            "describe",
            FHIR_STORE,
            f"--dataset={DATASET}",
            f"--location={LOCATION}",
            f"--project={PROJECT}",
        ]
    )
    if store != 0:
        _run(
            [
                "gcloud",
                "healthcare",
                "fhir-stores",
                "create",
                FHIR_STORE,
                f"--dataset={DATASET}",
                f"--location={LOCATION}",
                "--version=R4",
                f"--project={PROJECT}",
            ]
        )
    print("provision finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
