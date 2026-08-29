from fastapi import APIRouter, Query

from app.core.deps import get_container

router = APIRouter()


@router.get("/status")
def runtime_status() -> dict:
    container = get_container()
    latest = container.adk_telemetry.latest()
    adapters = container.adapter_status()
    probe = adapters["runtime_verification"]["vertex_model_probe"]
    guard_status = getattr(container.content_guard, "status", lambda: {})()
    return {
        "adk_worker": latest,
        "content_guard": {
            "adapter": getattr(container.content_guard, "adapter_name", "unknown"),
            "managed_model_armor_available": getattr(
                container.content_guard, "managed_available", False
            ),
        },
        "model_armor": guard_status,
        "fleet": {
            "gemini_model": probe["model"],
            "gemini_location": probe["location"],
            "vertex_probe_success": probe["success"],
            "adk_mode": adapters["adk_runner_mode"],
            "adk_allow_direct_fallback": adapters["adk_allow_direct_fallback"],
            "runtime_region": adapters["runtime_verification"]["enterprise"]["runtime_region"],
            "event_bus": adapters["event_bus"],
            "fhir_mode": adapters["fhir_mode"],
            "pubsub_handle": adapters["pubsub_handle"],
            "workflow_subscriber": adapters["workflow_subscriber"],
            "voice": adapters.get("voice", {}),
            # Every adapter the fleet page draws has to reach it from here; /health alone is
            # not enough, or a degraded Veo is invisible in the UI.
            "recovery_video": adapters.get("recovery_video", {}),
            "platform": adapters.get("platform_verification", {}),
        },
    }


@router.get("/history")
def runtime_history(
    limit: int = Query(default=25, ge=1, le=50),
    episode_id: str | None = Query(default=None),
) -> dict:
    container = get_container()
    return {
        "items": container.adk_telemetry.history(limit=limit, episode_id=episode_id),
    }
