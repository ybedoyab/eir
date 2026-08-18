from app.repositories.runtime_telemetry import InMemoryAdkRuntimeTelemetryStore
from eir_shared.runtime_telemetry import AdkInvocationTelemetry


def test_runtime_telemetry_store_records_latest() -> None:
    store = InMemoryAdkRuntimeTelemetryStore()
    store.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:00Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="patient.contact",
            agent_name="outreach_agent",
            episode_id="ep-1",
            trace_id="trace-1",
            tools_invoked=["read_patient", "conduct_outreach"],
            success=True,
            used_direct_fallback=False,
        )
    )
    latest = store.latest()
    assert latest is not None
    assert latest["success"] is True
    assert latest["tools_invoked"] == ["read_patient", "conduct_outreach"]
    assert latest["model_location"] == "global"
    history = store.history(limit=10)
    assert len(history) == 1
    assert history[0]["agent_name"] == "outreach_agent"
    store.record(
        AdkInvocationTelemetry(
            timestamp="2026-08-18T00:00:01Z",
            service="eir-worker",
            model="gemini-3.5-flash",
            model_location="global",
            capability="risk.assess",
            agent_name="risk_agent",
            episode_id="ep-2",
            trace_id="trace-2",
            tools_invoked=["assess_patient_response"],
            success=True,
            used_direct_fallback=False,
        )
    )
    scoped = store.history(limit=10, episode_id="ep-1")
    assert len(scoped) == 1
    assert scoped[0]["episode_id"] == "ep-1"
