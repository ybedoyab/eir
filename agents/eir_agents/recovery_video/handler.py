"""Builds a deterministic prompt from approved recovery instructions and asks the video
generation adapter to animate them into a short patient-facing clip.

The wording of the instructions is never produced by a model here — only the video is.
This mirrors the "agents never diagnose" rule the rest of the fleet follows: the prompt is
assembled by plain Python from an explicit allowlist of already-approved fields (episode
event payload, then FHIR CarePlan), never from free LLM generation and never from
patient-identifying fields (name, DOB, MRN, free-text notes).
"""

from __future__ import annotations

from typing import Any

from eir_shared.events import DomainEvent, RecoveryVideoFailed, RecoveryVideoReady

from eir_agents.common.types import HandlerResult

_GENERIC_CONTEXT = "Post-procedure recovery"
_GENERIC_TASKS = [
    "Rest and stay hydrated",
    "Take medications as prescribed",
    "Contact your care team about any new or worsening symptoms",
]


def _allowed_payload_context(event: DomainEvent) -> tuple[str, list[str]]:
    """Reads only an explicit allowlist of event payload keys."""
    payload = event.payload or {}
    context = payload.get("context")
    tasks = payload.get("tasks")
    clean_context = context.strip() if isinstance(context, str) and context.strip() else ""
    clean_tasks = (
        [str(item).strip() for item in tasks if str(item).strip()]
        if isinstance(tasks, list)
        else []
    )
    return clean_context, clean_tasks


def _forced(event: DomainEvent) -> bool:
    """True when this request must bypass the content-addressed cache.

    The "Regenerate video" button sends ``{"force": true}`` — the point of clicking it live is
    to see a real generation happen, not to be handed the identical cached clip back.
    """
    return bool((event.payload or {}).get("force") is True)


def _care_plan_context(care_plan: dict[str, Any] | None) -> tuple[str, list[str]]:
    if not care_plan:
        return "", []
    context = str(care_plan.get("context") or care_plan.get("title") or "").strip()
    activities = care_plan.get("tasks") or care_plan.get("activities") or []
    tasks = [str(item).strip() for item in activities if str(item).strip()]
    return context, tasks


def _episode_started_context(episodes: Any, episode_id: str) -> tuple[str, list[str]]:
    """Reads context/tasks off the episode's own RecoveryEpisodeStarted event.

    RecoveryVideoRequested (whether auto-fired at episode start or from the "Regenerate
    video" button) carries no payload of its own — the real task list lives on the episode's
    original started event, the same one the patient-facing text UI reads. Same allowlist
    discipline as ``_allowed_payload_context``: only ``context``/``tasks``, never
    patient-identifying fields.
    """
    if episodes is None:
        return "", []
    try:
        history = episodes.list_events(episode_id)
    except Exception:  # noqa: BLE001 - episode history is optional context, never fatal here
        return "", []
    started = next((item for item in history if item.event_type == "RecoveryEpisodeStarted"), None)
    return _allowed_payload_context(started) if started is not None else ("", [])


# Calm narration runs at roughly two words per second, and a clip needs a beat of silence at
# each end — so an 8-second video holds about 16 spoken words. One sentence. Asking it to
# recite a numbered care plan (the previous prompt did) only makes Veo speed-talk the
# instructions or cut them off mid-word, which is worse than not speaking them at all.
_WORDS_PER_SECOND = 2
_MIN_WORD_BUDGET = 8
_CLOSING_LINE = "Your full plan is on screen."

# The scene is chosen from the primary task so the imagery is about the right activity. These
# are deliberately generic, non-clinical settings — no procedures, wounds or medication shown.
_SCENES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("walk", "step", "mobil", "exercise", "stretch"),
        "an adult walking slowly and steadily along a bright hallway",
    ),
    (
        ("ice", "swell", "elevate", "rest"),
        "an adult resting on a sofa with one leg raised on a cushion",
    ),
    (
        ("hydrat", "water", "fluid", "drink"),
        "an adult drinking a glass of water in a sunlit kitchen",
    ),
    (
        ("medication", "medicine", "tablet", "pill", "dose", "prescri"),
        "an adult sitting calmly at a kitchen table in morning light",
    ),
    (
        ("symptom", "report", "call", "contact", "pain"),
        "an adult talking calmly on the phone at home",
    ),
    (
        ("wound", "incision", "dressing", "bandage"),
        "a clinician sitting and talking with a patient in a bright consultation room",
    ),
)
_DEFAULT_SCENE = "an adult resting comfortably at home in soft daylight"


def _scene(tasks: list[str]) -> str:
    primary = tasks[0].lower() if tasks else ""
    for keywords, scene in _SCENES:
        if any(keyword in primary for keyword in keywords):
            return scene
    return _DEFAULT_SCENE


def _trim_words(text: str, limit: int) -> str:
    return " ".join(text.split()[:limit])


def _narration(context: str, tasks: list[str], *, word_budget: int) -> str:
    """The exact sentence the narrator speaks — assembled in Python, never by a model.

    Only the procedure context and, if it fits, the single primary task are spoken. The full
    verified list stays in the portal's text UI beside the video, which is where §7 always
    intended the exact wording to live; the clip's job is to be personal and calm, not to be
    the record. Speaking one instruction keeps it genuinely specific to the episode without
    asking eight seconds of video to recite a care plan.
    """
    topic = _trim_words(context.strip().rstrip(". "), 5)
    primary = tasks[0].strip().rstrip(". ") if tasks else ""
    # A generative narration channel can't be trusted to say a drug name or dose correctly, so
    # it never tries — the same rule the phone outreach channel already follows. A
    # medication-related task simply isn't spoken; it stays in the verified on-page list.
    if primary and not _mentions_medication([primary]):
        with_task = f"{topic}. {primary}. {_CLOSING_LINE}"
        if len(with_task.split()) <= word_budget:
            return with_task
    return f"{topic}. {_CLOSING_LINE}"


def build_prompt(
    event: DomainEvent,
    *,
    episode_context: str = "",
    episode_tasks: list[str] | None = None,
    care_plan: dict[str, Any] | None = None,
    duration_seconds: int = 8,
) -> str:
    context, tasks = _allowed_payload_context(event)
    context = context or episode_context
    tasks = tasks or episode_tasks or []
    if not context or not tasks:
        fallback_context, fallback_tasks = _care_plan_context(care_plan)
        context = context or fallback_context
        tasks = tasks or fallback_tasks
    context = context or _GENERIC_CONTEXT
    tasks = tasks or _GENERIC_TASKS
    budget = max(_MIN_WORD_BUDGET, int(duration_seconds * _WORDS_PER_SECOND))
    narration = _narration(context, tasks, word_budget=budget)
    return (
        "Calm patient-education video for a hospital recovery app. Vertical 9:16, "
        f"{duration_seconds} seconds. "
        f"Scene: {_scene(tasks)}. Soft natural light, gentle camera, reassuring mood. "
        f'One warm narrator says exactly this line, once, unhurried: "{narration}" '
        "No on-screen text or captions. No other dialogue. No medical claims beyond that line."
    )


_MEDICATION_KEYWORDS = ("medication", "medicine", "tablet", "pill", "dose", "prescri")


def _mentions_medication(tasks: list[str]) -> bool:
    return any(keyword in task.lower() for task in tasks for keyword in _MEDICATION_KEYWORDS)


def generate_recovery_video(
    event: DomainEvent,
    *,
    patient_id: str,
    fhir: Any = None,
    video_client: Any = None,
    episodes: Any = None,
) -> HandlerResult:
    if video_client is None or not getattr(video_client, "available", False):
        return HandlerResult(
            summary="Recovery video generation unavailable; text instructions remain primary.",
            next_events=[
                RecoveryVideoFailed(
                    episode_id=event.episode_id,
                    payload={"reason": "video_generation_unavailable"},
                )
            ],
        )

    care_plan: dict[str, Any] | None = None
    if fhir is not None:
        try:
            care_plan = fhir.get_care_plan(patient_id)
        except Exception:  # noqa: BLE001 - care plan is optional context, never fatal here
            care_plan = None

    episode_context, episode_tasks = _episode_started_context(episodes, event.episode_id)
    prompt = build_prompt(
        event,
        episode_context=episode_context,
        episode_tasks=episode_tasks,
        care_plan=care_plan,
        # The narration budget is a function of clip length, so it follows the adapter's
        # configured duration rather than a second hardcoded number.
        duration_seconds=int(getattr(video_client, "duration_seconds", 8) or 8),
    )
    result = video_client.generate(prompt=prompt, episode_id=event.episode_id, force=_forced(event))
    if not result.ok:
        return HandlerResult(
            summary=f"Recovery video generation failed: {result.error or 'unknown error'}.",
            next_events=[
                RecoveryVideoFailed(
                    episode_id=event.episode_id,
                    payload={"reason": result.error or "unknown_error"},
                )
            ],
        )

    return HandlerResult(
        summary=(
            "Reused an existing recovery video for these instructions."
            if result.cached
            else "Personalized recovery video generated."
        ),
        next_events=[
            RecoveryVideoReady(
                episode_id=event.episode_id,
                payload={
                    "video_url": result.video_url,
                    "duration_seconds": result.duration_seconds,
                    "generated_by": getattr(video_client, "adapter_name", "unknown"),
                    "model": result.model,
                    "cached": result.cached,
                },
            )
        ],
    )
