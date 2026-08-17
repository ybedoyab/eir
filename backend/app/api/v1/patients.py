from fastapi import APIRouter, HTTPException

from app.core.deps import get_container
from app.domain.patients.models import Patient

router = APIRouter()


@router.get("", response_model=list[Patient])
def list_patients() -> list[Patient]:
    return get_container().patients.list()


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str) -> Patient:
    patient = get_container().patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
