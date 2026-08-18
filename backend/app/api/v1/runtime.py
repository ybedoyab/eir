from fastapi import APIRouter

from app.core.deps import get_container

router = APIRouter()


@router.get("/status")
def runtime_status() -> dict:
    container = get_container()
    latest = container.adk_telemetry.latest()
    return {
        "adk_worker": latest,
        "content_guard": {
            "adapter": getattr(container.content_guard, "adapter_name", "unknown"),
            "managed_model_armor_available": getattr(
                container.content_guard, "managed_available", False
            ),
        },
    }
