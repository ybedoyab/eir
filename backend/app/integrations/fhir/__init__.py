"""FHIR adapter boundary for the API process.

Clinical records access is owned by the records agent / runtime. This package
hosts the Google Cloud Healthcare API client with a local fixture fallback.
"""

from app.integrations.fhir.client import GoogleHealthcareFhirClient

__all__ = ["GoogleHealthcareFhirClient"]
