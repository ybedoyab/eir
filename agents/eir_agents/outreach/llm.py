"""Optional Gemini phrasing for outreach. Never sets risk or diagnosis fields."""

from __future__ import annotations

from typing import Any, Protocol


class FollowUpSummarizer(Protocol):
    def summarize(self, payload: dict[str, Any]) -> str: ...


class TemplateFollowUpSummarizer:
    def summarize(self, payload: dict[str, Any]) -> str:
        return (
            f"Simulated follow-up on {payload.get('care_plan')}; "
            f"pain_score={payload.get('pain_score')}"
        )


class GeminiFollowUpSummarizer:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def summarize(self, payload: dict[str, Any]) -> str:
        fallback = TemplateFollowUpSummarizer().summarize(payload)
        try:
            from eir_shared.gemini_config import configure_genai_environment, genai_client_kwargs
            from google import genai

            configure_genai_environment()
            client = genai.Client(**genai_client_kwargs(api_key=self.api_key or None))
            prompt = (
                "Write one short clinician-facing sentence summarizing a synthetic "
                "recovery follow-up. Do not diagnose. Do not give medical advice. "
                f"Data: care_plan={payload.get('care_plan')}, "
                f"pain_score={payload.get('pain_score')}, "
                f"reported_issue={payload.get('reported_issue')}."
            )
            response = client.models.generate_content(model=self.model, contents=prompt)
            text = (response.text or "").strip()
            return text or fallback
        except Exception:
            return fallback
