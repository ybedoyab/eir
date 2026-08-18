"""Firestore persistence for patient access sessions."""

from __future__ import annotations

from typing import Any

from app.domain.access.models import PatientAccessSession


class FirestorePatientAccessSessionRepository:
    def __init__(self, client: Any, collection: str = "patient_access_sessions") -> None:
        self._col = client.collection(collection)

    def get(self, session_id: str) -> PatientAccessSession | None:
        snapshot = self._col.document(session_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        session = data.get("session")
        return PatientAccessSession.model_validate(session) if session else None

    def save(self, session: PatientAccessSession) -> PatientAccessSession:
        self._col.document(session.id).set({"session": session.model_dump(mode="json")})
        return session

    def list_for_patient(self, patient_id: str) -> list[PatientAccessSession]:
        docs = self._col.where("session.patient_id", "==", patient_id).stream()
        items: list[PatientAccessSession] = []
        for doc in docs:
            data = doc.to_dict() or {}
            session = data.get("session")
            if session:
                items.append(PatientAccessSession.model_validate(session))
        return items
