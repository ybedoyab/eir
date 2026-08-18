# Managed Gemini Enterprise Agent Platform — attempt log

Project `eir-ata`, region `us-central1`, ADK `2.7.1`.
No Voximplant calls. Synthetic patients only.

Terraform does **not** manage these preview resources. Cloud Run remains the
production Patient Access / Recovery runtime.

## Attempted 2026-08-18

### Agent Runtime (`reasoningEngines`)

- API: `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/eir-ata/locations/us-central1/reasoningEngines`
- List: HTTP 200 (empty after cleanup)
- Create of display-name-only shell `eir-patient-access-probe`: HTTP 200, resource had empty `spec` and a default `memoryBankConfig`
- Shell deleted immediately (no ADK package, no domain tools, would overstate managed runtime)
- `vertexai.agent_engines` was not importable from the repo venv during this sprint (`ModuleNotFoundError: vertexai`)
- `gcloud` has no `agent-registry` / Agents CLI command on this workstation

**MANUAL_ACTION_REQUIRED**

| Field | Value |
| --- | --- |
| component | Agent Runtime (Patient Access front door) |
| API | `aiplatform.googleapis.com` `reasoningEngines` |
| error | Runtime exists as an API, but deploying `patient_access_agent` requires Agent Platform SDK / Agents CLI packaging of ADK source that calls the existing `eir-api` tools. Empty shells are not a fleet. |
| project / region | `eir-ata` / `us-central1` |
| required action | Install current Agent Platform SDK, package `agents/eir_agents/access/agent.py` with HTTP tools to `eir-api`, deploy, then invoke a synthetic appointment read. |
| demo impact | None. Cloud Run ADK worker remains the live path. |

### Memory Bank

- Appears as `contextSpec.memoryBankConfig` on Agent Runtime shells only
- Memory Bank REST `.../memoryBanks` → HTTP 404 `Method not found`
- Preference Session A/B **not run** (no managed runtime to attach memories)

**MANUAL_ACTION_REQUIRED**: deploy a real Agent Runtime with Memory Bank, then store only `preferred_clinic` / `preferred_time_of_day` for synthetic patients.

### Agent Registry (`agentregistry.googleapis.com`)

- API enabled in project and Terraform
- `GET .../locations/us-central1/agents` HTTP 200
- Listed agent is Google **Workspace Agent** only (not an EIR agent)
- `POST .../services?serviceId=eir-patient-access` with `agentSpec.type=NO_SPEC` pointing at `eir-api` returned operation error **code 13** `An internal error has occurred (18e13d0b-ec07-403e-bbd7-27f27c65f6b6)`
- Stopped retrying per blocker policy

**MANUAL_ACTION_REQUIRED**: register Cloud Run Patient Access via an A2A Agent Card or supported `gcloud agent-registry services create` once the Service create path is non-internal. Do not invent registry entries.

Local catalog remains `EnterpriseAgentRegistry` (Patient Access, Scheduling, Recovery, Risk, Records, Escalation).

### Agent Identity / Agent Gateway

- No current public API in this project/region beyond local `AgentGateway` + demo tokens
- Backend RBAC remains the authorization boundary

**MANUAL_ACTION_REQUIRED** if Google exposes Identity/Gateway for `eir-ata` / `us-central1`.

### Model Armor

Already **VERIFIED MANAGED** (`eir-agent-guard`, runtime probe).

### Observability

Cloud Logging request + worker workflow JSON verified live.
Cloud Trace GET `projects/eir-ata/traces/c192b5f897a3cd08a8c0a8acff3331c0` returned Cloud Run `/health` spans (no PHI).
ADK application-span attributes (`tool.name`, `capability`) are present in worker JSON logs, not required on the HTTP load-balancer span.
