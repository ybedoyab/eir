"""Upload synthetic FHIR fixtures into Healthcare API. Never use real PHI."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from eir_shared.env import load_root_env, repo_root

from app.core.config import settings
from app.integrations.fhir.client import GoogleHealthcareFhirClient

_SEED_ORDER = (
    "patient.json",
    "encounter.json",
    "medication-request.json",
    "observation.json",
    "care-plan.json",
)


def _load_resources(mocks: Path) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for patient_dir in sorted(mocks.iterdir()):
        if not patient_dir.is_dir():
            continue
        for name in _SEED_ORDER:
            path = patient_dir / name
            if not path.is_file():
                continue
            resource = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(resource, dict) and resource.get("resourceType"):
                resources.append(resource)
    return resources


def _rewrite_references(value: Any, urn_for_id: dict[str, str]) -> Any:
    if isinstance(value, dict):
        if "reference" in value and isinstance(value["reference"], str):
            ref = value["reference"]
            if "/" in ref:
                _resource_type, resource_id = ref.split("/", 1)
                urn = urn_for_id.get(resource_id)
                if urn:
                    return {**value, "reference": urn}
        return {key: _rewrite_references(item, urn_for_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite_references(item, urn_for_id) for item in value]
    return value


def _transaction_bundle(resources: list[dict[str, Any]]) -> dict[str, Any]:
    urn_for_id = {str(resource["id"]): f"urn:uuid:{resource['id']}" for resource in resources}
    entries = []
    for resource in resources:
        body = _rewrite_references(copy.deepcopy(resource), urn_for_id)
        entries.append(
            {
                "fullUrl": urn_for_id[str(resource["id"])],
                "resource": body,
                "request": {
                    "method": "POST",
                    "url": resource["resourceType"],
                },
            }
        )
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def main() -> int:
    load_root_env()
    mocks = repo_root() / "mocks" / "fhir"
    resources = _load_resources(mocks)
    if not resources:
        print("no FHIR fixtures found", file=sys.stderr)
        return 1

    client = GoogleHealthcareFhirClient(
        project=settings.fhir_project,
        location=settings.fhir_location,
        dataset=settings.fhir_dataset,
        store=settings.fhir_store,
        fallback_on_miss=False,
    )
    bundle = _transaction_bundle(resources)
    response = httpx.post(
        client._base,
        headers=client._headers(),
        json=bundle,
        timeout=60,
    )
    if response.status_code >= 400:
        print(
            f"transaction failed ({response.status_code}): {response.text[:800]}",
            file=sys.stderr,
        )
        return 1

    client.reachable = True
    print(f"uploaded {len(resources)} synthetic resources via transaction bundle")
    for resource in resources:
        print(f"  {resource['resourceType']}/{resource['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
