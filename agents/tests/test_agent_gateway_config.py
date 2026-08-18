from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_TF = (ROOT / "infra" / "terraform" / "agent_gateway.tf").read_text(encoding="utf-8")
REGISTRY_TF = (ROOT / "infra" / "terraform" / "agent_registry.tf").read_text(encoding="utf-8")
ATTACH = (
    ROOT / "infra" / "gcp" / "agent_platform" / "attach_agent_gateway.py"
).read_text(encoding="utf-8")


def test_gateway_is_google_managed_agent_to_anywhere() -> None:
    assert "google_network_services_agent_gateway" in GATEWAY_TF
    assert 'governed_access_path = "AGENT_TO_ANYWHERE"' in GATEWAY_TF
    assert "self_managed" not in GATEWAY_TF
    assert "eir-agent-egress" in GATEWAY_TF


def test_gateway_destinations_are_narrow_http_json() -> None:
    assert "endpoint_spec" in REGISTRY_TF
    assert "/api/v1/agent-runtime/" in REGISTRY_TF
    assert "HTTP_JSON" in REGISTRY_TF
    assert '"*"' not in REGISTRY_TF
    assert "0.0.0.0" not in REGISTRY_TF
    assert "https://www.googleapis.com" not in REGISTRY_TF
    assert "https://aiplatform.mtls.googleapis.com" in REGISTRY_TF
    assert "https://iamcredentials.mtls.googleapis.com" in REGISTRY_TF
    assert "https://cloudresourcemanager.mtls.googleapis.com" in REGISTRY_TF
    assert "endpoint_spec" in REGISTRY_TF
    assert "NO_SPEC" in REGISTRY_TF


def test_gateway_model_armor_uses_existing_template() -> None:
    assert "modelarmor." in GATEWAY_TF and ".rep.googleapis.com" in GATEWAY_TF
    assert "eir-agent-guard" in GATEWAY_TF or "var.model_armor_template" in GATEWAY_TF
    assert "CONTENT_AUTHZ" in GATEWAY_TF
    assert "roles/modelarmor.calloutUser" in GATEWAY_TF
    assert "roles/modelarmor.user" in GATEWAY_TF
    assert "roles/serviceusage.serviceUsageConsumer" in GATEWAY_TF
    assert "roles/owner" not in GATEWAY_TF.lower()
    assert "roles/editor" not in GATEWAY_TF.lower()
    assert "roles/healthcare.admin" not in GATEWAY_TF.lower()


def test_iap_starts_audit_only() -> None:
    assert 'iamEnforcementMode = "DRY_RUN"' in GATEWAY_TF or "DRY_RUN" in GATEWAY_TF
    assert "roles/iap.egressor" in GATEWAY_TF
    assert "patient_access_agent_identity" in GATEWAY_TF


def test_attach_script_does_not_recreate_runtime() -> None:
    assert "3041998479602745344" in ATTACH
    assert "updateMask=spec.deploymentSpec.agentGatewayConfig" in ATTACH
    assert "_wait_operation" in ATTACH
    assert "agent_engines.create" not in ATTACH
    assert "delete" not in ATTACH.lower() or "CUTOFF" in ATTACH
    assert "demo-alex" not in ATTACH
    assert "SESSION_SECRET" not in ATTACH
    assert "BEGIN PRIVATE KEY" not in ATTACH


def test_health_flag_requires_live_proof_not_hardcoded() -> None:
    deps = (ROOT / "backend" / "app" / "core" / "deps.py").read_text(encoding="utf-8")
    smoke = (ROOT / "infra" / "gcp" / "agent_platform" / "smoke_agent_gateway.py").read_text(
        encoding="utf-8"
    )
    assert 'snapshot["managed_agent_gateway_verified"] = True' not in deps
    assert 'snapshot["managed_agent_gateway_verified"] = False' not in deps
    assert 'managed_agent_gateway_verified": True' in smoke
    assert "cardiology" in smoke
    assert "tool:cancel_appointment" in smoke


def test_backend_rbac_remains_final_authorization() -> None:
    identity = (ROOT / "backend" / "app" / "api" / "deps" / "agent_identity.py").read_text(
        encoding="utf-8"
    )
    runtime = (ROOT / "backend" / "tests" / "test_agent_runtime.py").read_text(encoding="utf-8")
    assert "require_agent_runtime_principal" in identity
    assert "test_agent_runtime_rejects_other_patient_ids" in runtime
    assert "roles/owner" not in GATEWAY_TF.lower()
    assert "roles/editor" not in GATEWAY_TF.lower()
