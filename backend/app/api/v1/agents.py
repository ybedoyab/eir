from fastapi import APIRouter

from app.core.deps import get_container

router = APIRouter()


@router.get("")
def list_agents() -> list[dict]:
    return [item.model_dump(mode="json") for item in get_container().registry.list_agents()]
