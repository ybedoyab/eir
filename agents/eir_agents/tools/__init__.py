"""Agent tools.

Keep FHIR and voice behind protocols so tools stay vendor-agnostic.
"""

from eir_agents.records.fhir_client import FhirClient, LocalFhirClient

__all__ = ["FhirClient", "LocalFhirClient"]
