"""Records agent uses FhirClient. Never call an EHR vendor SDK here."""

from eir_agents.records.fhir_client import FhirClient, LocalFhirClient

__all__ = ["FhirClient", "LocalFhirClient"]
