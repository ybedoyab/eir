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


def test_local_fhir_reads_jordan_lee_profile() -> None:
    client = LocalFhirClient()
    patient = client.get_patient("patient-synthetic-002")
    assert patient is not None
    assert patient["name"][0]["family"] == "Lee"
    observations = client.get_observations("patient-synthetic-002")
    assert observations
    assert observations[0]["valueInteger"] == 8
