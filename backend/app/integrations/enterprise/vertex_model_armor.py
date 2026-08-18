"""Google Cloud Model Armor adapter with regex fallback for local/test."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from google.api_core.client_options import ClientOptions

from app.integrations.enterprise.model_armor import ArmorDecision, RegexContentGuardFallback

logger = logging.getLogger("eir.model_armor")

MATCH_FOUND = "MATCH_FOUND"


def managed_model_armor_available() -> bool:
    try:
        from google.cloud import modelarmor_v1
    except Exception:
        return False
    return hasattr(modelarmor_v1, "ModelArmorClient")


def _match_state_is_hit(value: Any) -> bool:
    name = getattr(value, "name", None)
    if isinstance(name, str) and name.upper() == MATCH_FOUND:
        return True
    try:
        from google.cloud.modelarmor_v1.types import FilterMatchState

        if value == FilterMatchState.MATCH_FOUND:
            return True
        if int(value) == int(FilterMatchState.MATCH_FOUND):
            return True
    except Exception:
        pass
    text = str(value).upper()
    return text == MATCH_FOUND or text.endswith("." + MATCH_FOUND)


def _filter_category_label(key: str) -> str:
    labels = {
        "pi_and_jailbreak": "prompt_injection",
        "piandjailbreakfilterresult": "prompt_injection",
        "sdp": "sensitive_data",
        "sdpfilterresult": "sensitive_data",
        "rai": "responsible_ai",
        "raifilterresult": "responsible_ai",
        "malicious_uri": "malicious_uri",
        "maliciousurifilterresult": "malicious_uri",
    }
    normalized = key.lower().replace("_", "")
    return labels.get(key.lower(), labels.get(normalized, key))


@dataclass
class ModelArmorStatus:
    configured: bool = False
    mode: str = "fallback"
    location: str = ""
    template: str = ""
    managed_available: bool = False
    last_screening_success: bool | None = None
    last_decision_adapter: str | None = None
    last_error_type: str | None = None
    last_filter_category: str | None = None
    last_blocked: bool | None = None


class ContentGuard(Protocol):
    adapter_name: str
    managed_available: bool

    def inspect_ingress(self, text: str) -> ArmorDecision: ...

    def inspect_egress(self, text: str) -> ArmorDecision: ...

    def status(self) -> dict[str, Any]: ...


class VertexModelArmorAdapter:
    """Managed Model Armor screening with deterministic regex fallback."""

    adapter_name = "vertex_model_armor"

    def __init__(
        self,
        *,
        project: str,
        location: str,
        template: str,
        fallback: RegexContentGuardFallback,
    ) -> None:
        self._project = project
        self._location = location
        self._template = template
        self._fallback = fallback
        sdk_available = managed_model_armor_available()
        configured = bool(sdk_available and template)
        self.managed_available = configured
        self._status = ModelArmorStatus(
            configured=configured,
            mode="managed" if configured else "fallback",
            location=location,
            template=template,
            managed_available=configured,
        )
        self._client: Any | None = None

    def status(self) -> dict[str, Any]:
        return {
            "configured": self._status.configured,
            "mode": self._status.mode,
            "location": self._status.location,
            "template": self._status.template,
            "managed_available": self._status.managed_available,
            "available": self._status.configured,
            "last_screening_success": self._status.last_screening_success,
            "last_decision_adapter": self._status.last_decision_adapter,
            "last_error_type": self._status.last_error_type,
            "last_filter_category": self._status.last_filter_category,
            "last_blocked": self._status.last_blocked,
        }

    def inspect_ingress(self, text: str) -> ArmorDecision:
        if not self._status.configured:
            return self._record_fallback(self._fallback.inspect_ingress(text), mode="fallback")
        try:
            decision = self._screen_prompt(text)
            return self._record_managed(decision)
        except Exception as exc:
            logger.exception("Managed Model Armor ingress screening failed")
            fallback = self._fallback.inspect_ingress(text)
            return self._record_fallback(fallback, error_type=type(exc).__name__)

    def inspect_egress(self, text: str) -> ArmorDecision:
        fallback = self._fallback.inspect_egress(text)
        if not fallback.allowed:
            return self._record_fallback(fallback, mode=self._status.mode)
        if not self._status.configured:
            return self._record_fallback(fallback, mode="fallback")
        try:
            decision = self._screen_response(text)
            return self._record_managed(decision)
        except Exception as exc:
            logger.exception("Managed Model Armor egress screening failed")
            return self._record_fallback(fallback, error_type=type(exc).__name__)

    def _record_managed(self, decision: ArmorDecision) -> ArmorDecision:
        self._status.mode = "managed"
        self._status.last_screening_success = True
        self._status.last_error_type = None
        self._status.last_decision_adapter = decision.adapter
        self._status.last_blocked = not decision.allowed
        self._status.last_filter_category = decision.filter_category or None
        return decision

    def _record_fallback(
        self,
        decision: ArmorDecision,
        *,
        mode: str = "degraded",
        error_type: str | None = None,
    ) -> ArmorDecision:
        self._status.mode = mode
        if error_type is not None:
            self._status.last_screening_success = False
            self._status.last_error_type = error_type
        self._status.last_decision_adapter = decision.adapter
        self._status.last_blocked = not decision.allowed
        self._status.last_filter_category = decision.filter_category or None
        return ArmorDecision(
            allowed=decision.allowed,
            reason=decision.reason,
            sanitized_text=decision.sanitized_text,
            adapter=decision.adapter,
            filter_category=decision.filter_category,
            degraded=mode == "degraded",
        )

    def _client_instance(self) -> Any:
        if self._client is not None:
            return self._client
        from google.cloud import modelarmor_v1

        self._client = modelarmor_v1.ModelArmorClient(
            transport="rest",
            client_options=ClientOptions(
                api_endpoint=f"modelarmor.{self._location}.rep.googleapis.com",
            ),
        )
        return self._client

    def _template_name(self) -> str:
        return f"projects/{self._project}/locations/{self._location}/templates/{self._template}"

    def _screen_prompt(self, text: str) -> ArmorDecision:
        from google.cloud import modelarmor_v1

        request = modelarmor_v1.SanitizeUserPromptRequest(
            name=self._template_name(),
            user_prompt_data=modelarmor_v1.DataItem(text=text),
        )
        response = self._client_instance().sanitize_user_prompt(request=request)
        return self._map_sanitization(response.sanitization_result, direction="ingress")

    def _screen_response(self, text: str) -> ArmorDecision:
        from google.cloud import modelarmor_v1

        request = modelarmor_v1.SanitizeModelResponseRequest(
            name=self._template_name(),
            model_response_data=modelarmor_v1.DataItem(text=text),
        )
        response = self._client_instance().sanitize_model_response(request=request)
        return self._map_sanitization(response.sanitization_result, direction="egress")

    def _map_sanitization(self, result: Any, *, direction: str) -> ArmorDecision:
        if result is None:
            return ArmorDecision(
                allowed=False,
                reason=f"model armor returned empty {direction} result",
                adapter="google_model_armor",
                filter_category="empty_result",
            )

        if _match_state_is_hit(getattr(result, "filter_match_state", "")):
            return ArmorDecision(
                allowed=False,
                reason="model armor aggregate filter match",
                adapter="google_model_armor",
                filter_category="prompt_injection",
            )

        matches = self._collect_matches(result)
        if matches:
            category = matches[0]
            return ArmorDecision(
                allowed=False,
                reason=f"model armor blocked {direction}: {category}",
                adapter="google_model_armor",
                filter_category=category,
            )

        sanitized = ""
        metadata = getattr(result, "sanitization_metadata", None)
        if metadata is not None:
            sanitized = str(getattr(metadata, "sanitized_text", "") or "").strip()
        return ArmorDecision(
            allowed=True,
            sanitized_text=sanitized,
            adapter="google_model_armor",
        )

    def _collect_matches(self, result: Any) -> list[str]:
        matches: list[str] = []
        filter_results = getattr(result, "filter_results", None)
        if filter_results:
            for key, entry in filter_results.items():
                if entry is None:
                    continue
                if _match_state_is_hit(getattr(entry, "match_state", "")):
                    matches.append(_filter_category_label(str(key)))
                    continue
                nested_attrs = (
                    "pi_and_jailbreak_filter_result",
                    "sdp_filter_result",
                    "rai_filter_result",
                    "malicious_uri_filter_result",
                )
                for attr in nested_attrs:
                    nested = getattr(entry, attr, None)
                    if nested is not None and _match_state_is_hit(
                        getattr(nested, "match_state", "")
                    ):
                        matches.append(_filter_category_label(attr.replace("_filter_result", "")))

        nested_checks = (
            ("pi_and_jailbreak_filter_result", "prompt_injection"),
            ("sdp_filter_result", "sensitive_data"),
            ("rai_filter_result", "responsible_ai"),
            ("malicious_uri_filter_result", "malicious_uri"),
        )
        for attr, label in nested_checks:
            nested = getattr(result, attr, None)
            if nested is not None and _match_state_is_hit(getattr(nested, "match_state", "")):
                matches.append(label)
        return matches


class RegexContentGuardWithStatus(RegexContentGuardFallback):
    managed_available = False

    def status(self) -> dict[str, Any]:
        return {
            "configured": False,
            "mode": "fallback",
            "location": "",
            "template": "",
            "managed_available": False,
            "available": False,
            "last_screening_success": None,
            "last_decision_adapter": "regex_fallback",
            "last_error_type": None,
            "last_filter_category": None,
            "last_blocked": None,
        }


def build_content_guard(
    *,
    project: str,
    location: str,
    template: str,
    prefer_managed: bool,
) -> ContentGuard:
    fallback = RegexContentGuardFallback()
    if prefer_managed and template:
        return VertexModelArmorAdapter(
            project=project,
            location=location,
            template=template,
            fallback=fallback,
        )
    return RegexContentGuardWithStatus()
