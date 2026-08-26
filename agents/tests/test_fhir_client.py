from eir_agents.records.fhir_client import LocalFhirClient
from eir_shared.supply import sku_for_medication_request


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


def test_alex_has_multiple_coded_prescriptions() -> None:
    medications = LocalFhirClient().get_medications("patient-synthetic-001")
    assert len(medications) == 3
    skus = {sku_for_medication_request(item) for item in medications}
    assert skus == {"MED-ENOX-40", "MED-PARA-500", "MED-AMOX-500"}


def test_jordan_ibuprofen_has_rxnorm_but_no_pharmacy_sku() -> None:
    medications = LocalFhirClient().get_medications("patient-synthetic-002")
    assert len(medications) == 1
    coding = medications[0]["medicationCodeableConcept"]["coding"]
    assert any(item["code"] == "5640" for item in coding)
    assert sku_for_medication_request(medications[0]) is None
