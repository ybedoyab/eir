from eir_agents.records.fhir_client import LocalFhirClient


def test_local_fhir_reads_synthetic_patient() -> None:
    client = LocalFhirClient()
    patient = client.get_patient("patient-synthetic-001")
    assert patient is not None
    assert patient["resourceType"] == "Patient"
    assert client.get_care_plan("patient-synthetic-001") is not None
    assert client.get_encounters("patient-synthetic-001")
    assert client.get_medications("patient-synthetic-001")
    assert client.get_observations("patient-synthetic-001")
