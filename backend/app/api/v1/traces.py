from fastapi import APIRouter

from app.core.deps import get_container

router = APIRouter()


@router.get("")
def list_traces() -> list[dict]:
    logger = get_container().logger
    if hasattr(logger, "list_records"):
        records = logger.list_records()
    else:
        records = logger.records
    return [item.model_dump(mode="json") for item in records]
