# Managed Gemini Enterprise Agent Platform

Project `eir-ata`, region `us-central1`. Synthetic patients only. No Voximplant calls.

```
ReasoningEngine eir-patient-access
├── ADK Patient Access Agent (gemini-3.5-flash)
├── Managed Sessions
├── Memory Bank (attached contextSpec.memoryBankConfig)
└── Agent Identity (AGENT_IDENTITY)

Agent Registry
└── eir-patient-access (standard REST → ReasoningEngine)
```

Architecture:

```
Managed Agent Runtime
        |
 Google Agent Gateway (eir-agent-egress, AGENT_TO_ANYWHERE)
        |
 Model Armor (native CONTENT_AUTHZ, eir-agent-guard)
        |
 protected EIR tools (X-Agent-Authorization)
        |
      eir-api
        |
 AppointmentService
        |
 Healthcare API FHIR
```

The in-process `AgentGateway` / SafetyGate in the backend is a secondary defense. It is not proof of Google managed Agent Gateway.

## Live resources (2026-08-18)

| Component | Resource | Status |
| --- | --- | --- |
| Agent Runtime | `projects/658898892127/locations/us-central1/reasoningEngines/3041998479602745344` | VERIFIED MANAGED |
| Model | `gemini-3.5-flash` | remote `async_stream_query` |
| Agent Identity | `principal://agents.global.proj-658898892127.system.id.goog/resources/aiplatform/projects/658898892127/locations/us-central1/reasoningEngines/3041998479602745344` | VERIFIED MANAGED (`roles/run.invoker` only) |
| Memory Bank | ReasoningEngine `contextSpec.memoryBankConfig` (not `/memoryBanks`) | VERIFIED MANAGED Session A → generate → Session B |
| Agent Registry | URN `urn:agent:projects-658898892127:projects:658898892127:locations:us-central1:agentregistry:services:eir-patient-access` | VERIFIED MANAGED (manual standard REST; Terraform-imported) |
| Agent Gateway | `projects/eir-ata/locations/us-central1/agentGateways/eir-agent-egress` | VERIFIED MANAGED (`AGENT_TO_ANYWHERE`, IAP ENFORCED) |
| Model Armor | `eir-agent-guard` | VERIFIED MANAGED (native Gateway CONTENT_AUTHZ + application adapter) |

Empty display-name-only reasoningEngines do **not** count. Memory Bank is **not** a top-level `/memoryBanks` collection.

Packaging is pickle-based ADK `AdkApp`. Source-based Runtime deploy was not required to attach Agent Gateway; the live engine ID was preserved.

## Fleet catalog

| Agent | Invocation | Registry |
| --- | --- | --- |
| Patient Access | ReasoningEngine `3041998479602745344` | `eir-patient-access` plus HTTP tool endpoint `eir-api-agent-runtime` |
| Scheduling / Recovery / Records | Cloud Run `eir-api` + `eir-worker` | Documented as the Cloud Run fleet. Not extra ReasoningEngines. |

Do not register agents that cannot actually be invoked.

## Helpers

Idempotent ADC scripts (never print tokens):

- `uv run --package eir-backend python infra/gcp/agent_platform/deploy_patient_access.py`
- `uv run --package eir-backend python infra/gcp/agent_platform/smoke_managed_platform.py`
- `uv run --package eir-agents python infra/gcp/agent_platform/attach_agent_gateway.py`
- `uv run --package eir-agents python infra/gcp/agent_platform/smoke_agent_gateway.py`
- `uv run --package eir-backend python infra/gcp/agent_platform/local_query.py` (local AdkApp; may impersonate `eir-runtime` only when `EIR_ALLOW_IMPERSONATE_TOOL_SA=true`)

`--update` recreates the runtime package. Prefer it only when the live engine cannot start.

Memory Bank generation uses `projects/eir-ata/locations/global/publishers/google/models/gemini-3.5-flash` because the us-central1 publisher path is not available for Memory Bank extraction.

## Terraform

- Provider `hashicorp/google ~> 7.14` (installed 7.44.x).
- `google_agent_registry_service.patient_access` is imported; `terraform plan` is clean.
- `google_network_services_agent_gateway.egress` owns `eir-agent-egress`.
- ReasoningEngine package remains SDK-deployed so Terraform does not create a duplicate runtime.
