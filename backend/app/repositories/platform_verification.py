"""Live managed-platform probe results. Configuration is not verification."""

from __future__ import annotations

from typing import Any

FALSE_FLAGS = {
    "managed_agent_runtime_verified": False,
    "managed_memory_bank_verified": False,
    "managed_registry_verified": False,
    "managed_agent_identity_verified": False,
    "managed_agent_gateway_verified": False,
    "otel_cloud_trace_verified": False,
    "cloud_logging_verified": False,
    "cloud_monitoring_verified": False,
}

SAFE_ID_KEYS = ("agent_runtime_resource", "registry_urn", "agent_identity_principal")


class InMemoryPlatformVerificationStore:
    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        data = dict(FALSE_FLAGS)
        data.update({key: self._payload.get(key) for key in SAFE_ID_KEYS})
        for flag in FALSE_FLAGS:
            if flag in self._payload:
                data[flag] = bool(self._payload[flag])
        return data

    def allowed_principals(self) -> set[str]:
        raw = self._payload.get("allowed_principals") or []
        return {str(item) for item in raw if item}

    def write(self, payload: dict[str, Any]) -> None:
        self._payload = dict(payload)


class FirestorePlatformVerificationStore:
    def __init__(self, client: Any) -> None:
        self._doc = client.collection("eir_platform_verification").document("managed")

    def snapshot(self) -> dict[str, Any]:
        data = dict(FALSE_FLAGS)
        snapshot = self._doc.get()
        if not snapshot.exists:
            return data
        payload = snapshot.to_dict() or {}
        for key in SAFE_ID_KEYS:
            data[key] = payload.get(key)
        for flag in FALSE_FLAGS:
            data[flag] = bool(payload.get(flag, False))
        return data

    def allowed_principals(self) -> set[str]:
        snapshot = self._doc.get()
        if not snapshot.exists:
            return set()
        payload = snapshot.to_dict() or {}
        raw = payload.get("allowed_principals") or []
        return {str(item) for item in raw if item}

    def write(self, payload: dict[str, Any]) -> None:
        self._doc.set(payload, merge=True)
