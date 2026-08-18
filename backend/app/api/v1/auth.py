from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps.auth import _claims_from_header
from app.core.deps import get_container
from app.integrations.enterprise.demo_identity import DEMO_USERS, authenticate_demo_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest) -> dict:
    user = authenticate_demo_user(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    token = get_container().identity.issue_token(user)
    return {
        "token": token,
        "role": user.role.value,
        "display_name": user.display_name,
        "patient_id": user.patient_id,
    }


@router.get("/demo-users")
def list_demo_users() -> list[dict]:
    return [
        {
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
            "patient_id": user.patient_id,
            "password_hint": f"demo-{user.username}",
        }
        for user in DEMO_USERS.values()
    ]


@router.get("/me")
def current_user(claims: Annotated[dict[str, Any], Depends(_claims_from_header)]) -> dict:
    return claims
