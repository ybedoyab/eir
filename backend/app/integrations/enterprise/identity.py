"""Per-agent least-privilege identity for Agent Identity / Gateway."""

from __future__ import annotations

from eir_shared.identity import AgentIdentity
from eir_shared.registry import AgentDescriptor


def identity_from_descriptor(descriptor: AgentDescriptor) -> AgentIdentity:
    return AgentIdentity(
        name=descriptor.name,
        version=descriptor.version,
        granted_capabilities=descriptor.effective_grants(),
    )
