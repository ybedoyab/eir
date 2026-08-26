from typing import Annotated, Any

from eir_shared.auth import DemoRole
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps.auth import assert_patient_record_access, require_role
from app.core.deps import get_container
from app.domain.patients.models import Patient
from app.services.medications import PatientMedication, medications_for_patient

router = APIRouter()

StaffClaims = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.CLINICIAN, DemoRole.OPERATIONS_ADMIN)),
]
PortalClaims = Annotated[
    dict[str, Any],
    Depends(require_role(DemoRole.PATIENT, DemoRole.CLINICIAN, DemoRole.OPERATIONS_ADMIN)),
]


@router.get("", response_model=list[Patient])
def list_patients(_claims: StaffClaims) -> list[Patient]:
    return get_container().patients.list()


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str, claims: PortalClaims) -> Patient:
    assert_patient_record_access(claims, patient_id)
    patient = get_container().patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}/medications", response_model=list[PatientMedication])
def list_patient_medications(patient_id: str, claims: PortalClaims) -> list[PatientMedication]:
    assert_patient_record_access(claims, patient_id)
    container = get_container()
    patient = container.patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return medications_for_patient(
        container.fhir.get_medications(patient_id),
        container.supply.list_items(),
    )
