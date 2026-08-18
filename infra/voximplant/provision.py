"""Idempotent Voximplant provisioning for EIR recovery voice outreach.

Admin bootstrap credentials (VOXIMPLANT_CREDENTIALS) are for this script only.
Never print secret values, private keys, phone numbers, or callback tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.integrations.voice.voximplant_api import VoximplantAPI, load_credentials  # noqa: E402

APP_NAME = "eir-recovery"
SCENARIO_NAME = "eir-gemini-outbound"
RULE_NAME = "eir-outbound"
RUNTIME_KEY_NAME = "eir-runtime-caller"
PREVIEW_USER = "eir-preview-user"
PREVIEW_ENV = ROOT / ".voximplant-preview.env"
GOOGLE_SA = "eir-voximplant-live"
GOOGLE_PROJECT = "eir-ata"
VERTEX_ROLE = "roles/aiplatform.user"
SECRET_CALLBACK_TOKEN = "EIR_CALLBACK_TOKEN"
SECRET_CALLBACK_URL = "EIR_CALLBACK_URL"
SECRET_VERTEX = "EIR_GEMINI_VERTEX_CREDENTIALS"
SECRET_DESTINATION = "EIR_DEMO_PHONE_E164"
SECRET_CALLER = "VOXIMPLANT_CALLER_ID_E164"
GCP_CALLBACK_SECRET = "eir-voximplant-callback-token"
GCP_RUNTIME_SECRET = "eir-voximplant-runtime-credentials"
GCP_DEMO_PHONE_SECRET = "eir-demo-phone-e164"
GCP_CALLER_SECRET = "eir-voximplant-caller-id"
API_URL = "https://eir-api-658898892127.us-central1.run.app"
CALLBACK_PATH = "/api/v1/voice/voximplant/callback"


class ManualActionRequired(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _env_path(name: str) -> str:
    return os.environ.get(name, "").strip()


def _load_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _api_error(payload: dict[str, Any]) -> str:
    error = payload.get("error") or {}
    if isinstance(error, dict):
        return str(error.get("msg") or error)
    return str(error or "voximplant_error")


def _result(payload: dict[str, Any]) -> Any:
    if "error" in payload:
        raise RuntimeError(_api_error(payload))
    return payload.get("result", payload)


def _matches_name(item: dict[str, Any], name_key: str, name: str) -> bool:
    value = str(item.get(name_key) or "")
    return value == name or value.startswith(f"{name}.")


def _find(items: list[dict[str, Any]], name_key: str, name: str, id_key: str) -> int | None:
    for item in items:
        if _matches_name(item, name_key, name):
            value = item.get(id_key)
            return int(value) if value is not None else None
    return None


def _as_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("result", "applications", "scenarios", "rules", "caller_ids", "keys", "secrets"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _gcloud() -> str:
    found = shutil.which("gcloud")
    if found:
        return found
    if sys.platform == "win32":
        candidate = Path.home() / "AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
        if candidate.is_file():
            return str(candidate)
    return "gcloud"


def _gcloud_run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "gcloud":
        args = [_gcloud(), *args[1:]]
    completed = subprocess.run(args, check=False, capture_output=True, text=True)
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "gcloud failed")
    return completed


def discover(api: VoximplantAPI) -> dict[str, Any]:
    raw_account = api.call("GetAccountInfo", return_live_balance="true")
    account = _result(raw_account)
    if isinstance(account, list):
        account = account[0] if account else {}
    api_host = str(raw_account.get("api_address") or account.get("api_host") or "")
    if api_host:
        api.use_host(api_host)
    applications = _as_list(_result(api.call("GetApplications")))
    scenarios = _as_list(_result(api.call("GetScenarios")))
    rules: list[dict[str, Any]] = []
    for app in applications:
        app_id = app.get("application_id")
        if app_id is None:
            continue
        rules.extend(_as_list(_result(api.call("GetRules", application_id=app_id))))
    caller_ids = _as_list(_result(api.call("GetCallerIDs")))
    keys = _as_list(_result(api.call("GetKeys")))
    return {
        "account_id": account.get("account_id") or api.account_id,
        "account_name": account.get("account_name") or account.get("account_email") or "",
        "api_host": f"https://{api_host}/platform_api" if api_host else "https://api.voximplant.com/platform_api",
        "balance": account.get("balance"),
        "live_balance": account.get("live_balance", account.get("balance")),
        "applications": [
            {"id": item.get("application_id"), "name": item.get("application_name")}
            for item in applications
        ],
        "scenarios": [
            {"id": item.get("scenario_id"), "name": item.get("scenario_name")} for item in scenarios
        ],
        "rules": [{"id": item.get("rule_id"), "name": item.get("rule_name")} for item in rules],
        "caller_ids": [
            {
                "verified": bool(item.get("verified") or item.get("active") or item.get("callerid_active")),
                "configured": True,
            }
            for item in caller_ids
        ],
        "keys": [{"id": item.get("key_id"), "description": item.get("description") or item.get("key_name")} for item in keys],
    }


def ensure_application(api: VoximplantAPI) -> int:
    apps = _as_list(_result(api.call("GetApplications")))
    existing = _find(apps, "application_name", APP_NAME, "application_id")
    if existing:
        return existing
    created = api.call("AddApplication", application_name=APP_NAME)
    if "error" not in created:
        result = created.get("result") or created
        if isinstance(result, dict) and result.get("application_id"):
            return int(result["application_id"])
    apps = _as_list(_result(api.call("GetApplications")))
    found = _find(apps, "application_name", APP_NAME, "application_id")
    if found is None:
        raise RuntimeError(
            _api_error(created) if "error" in created else "failed to create application"
        )
    return found


def ensure_scenario(api: VoximplantAPI, application_id: int) -> int:
    source = (Path(__file__).resolve().parent / "scenario.js").read_text(encoding="utf-8")
    scenarios = _as_list(_result(api.call("GetScenarios", application_id=application_id)))
    if not scenarios:
        scenarios = _as_list(_result(api.call("GetScenarios")))
    existing = _find(scenarios, "scenario_name", SCENARIO_NAME, "scenario_id")
    if existing:
        _result(api.call("SetScenarioInfo", scenario_id=existing, scenario_script=source))
        return existing
    created = api.call(
        "AddScenario",
        scenario_name=SCENARIO_NAME,
        scenario_script=source,
        application_id=application_id,
    )
    if "error" not in created:
        result = created.get("result") or created
        if isinstance(result, dict) and result.get("scenario_id"):
            return int(result["scenario_id"])
    scenarios = _as_list(_result(api.call("GetScenarios")))
    found = _find(scenarios, "scenario_name", SCENARIO_NAME, "scenario_id")
    if found is None:
        raise RuntimeError(
            _api_error(created) if "error" in created else "failed to create scenario"
        )
    _result(api.call("SetScenarioInfo", scenario_id=found, scenario_script=source))
    return found


def ensure_rule(api: VoximplantAPI, application_id: int, scenario_id: int) -> int:
    rules = _as_list(_result(api.call("GetRules", application_id=application_id)))
    existing = _find(rules, "rule_name", RULE_NAME, "rule_id")
    if existing is None:
        created = _result(
            api.call(
                "AddRule",
                application_id=application_id,
                rule_name=RULE_NAME,
                rule_pattern=".*",
                scenario_id=scenario_id,
            )
        )
        if isinstance(created, dict) and created.get("rule_id"):
            existing = int(created["rule_id"])
        else:
            rules = _as_list(_result(api.call("GetRules", application_id=application_id)))
            existing = _find(rules, "rule_name", RULE_NAME, "rule_id")
    if existing is None:
        raise RuntimeError("failed to create Voximplant routing rule")
    _result(
        api.call(
            "BindScenario",
            rule_id=existing,
            scenario_id=scenario_id,
            bind="true",
        )
    )
    return existing


def _secrets(api: VoximplantAPI, application_id: int) -> list[dict[str, Any]]:
    return _as_list(_result(api.call("GetSecrets", application_id=application_id)))


def upsert_secret(api: VoximplantAPI, application_id: int, name: str, value: str) -> None:
    existing = next((item for item in _secrets(api, application_id) if item.get("secret_name") == name), None)
    if existing is None:
        _result(
            api.call(
                "AddSecret",
                application_id=application_id,
                secret_name=name,
                secret_value=value,
            )
        )
        return
    secret_id = existing.get("secret_id")
    try:
        _result(
            api.call(
                "SetSecretInfo",
                application_id=application_id,
                secret_id=secret_id,
                secret_name=name,
                secret_value=value,
            )
        )
    except RuntimeError:
        _result(api.call("DelSecret", application_id=application_id, secret_id=secret_id))
        _result(
            api.call(
                "AddSecret",
                application_id=application_id,
                secret_name=name,
                secret_value=value,
            )
        )


def _ensure_gcp_secret(name: str, value: str) -> None:
    describe = _gcloud_run(
        ["gcloud", "secrets", "describe", name, f"--project={GOOGLE_PROJECT}"],
        check=False,
    )
    if describe.returncode != 0:
        _gcloud_run(["gcloud", "secrets", "create", name, f"--project={GOOGLE_PROJECT}"])
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
        handle.write(value)
        tmp = Path(handle.name)
    try:
        _gcloud_run(
            [
                "gcloud",
                "secrets",
                "versions",
                "add",
                name,
                f"--project={GOOGLE_PROJECT}",
                f"--data-file={tmp}",
            ]
        )
    finally:
        tmp.unlink(missing_ok=True)
    _gcloud_run(
        [
            "gcloud",
            "secrets",
            "add-iam-policy-binding",
            name,
            f"--project={GOOGLE_PROJECT}",
            f"--member=serviceAccount:eir-runtime@{GOOGLE_PROJECT}.iam.gserviceaccount.com",
            "--role=roles/secretmanager.secretAccessor",
        ],
        check=False,
    )


def _gcp_secret_exists(name: str) -> bool:
    versions = _gcloud_run(
        ["gcloud", "secrets", "versions", "list", name, f"--project={GOOGLE_PROJECT}", "--limit=1"],
        check=False,
    )
    return versions.returncode == 0 and bool(versions.stdout.strip())


def ensure_callback_token(api: VoximplantAPI, application_id: int) -> list[str]:
    manuals: list[str] = []
    token = ""
    try:
        if _gcp_secret_exists(GCP_CALLBACK_SECRET):
            pulled = _gcloud_run(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "access",
                    "latest",
                    f"--secret={GCP_CALLBACK_SECRET}",
                    f"--project={GOOGLE_PROJECT}",
                ],
                check=False,
            )
            token = (pulled.stdout or "").strip()
    except FileNotFoundError:
        manuals.append(
            "Install/configure gcloud, then rerun this provisioner so the callback token "
            f"is stored in Secret Manager as {GCP_CALLBACK_SECRET}."
        )
    if not token:
        token = secrets.token_urlsafe(32)
        try:
            _ensure_gcp_secret(GCP_CALLBACK_SECRET, token)
        except FileNotFoundError:
            local = ROOT / ".cursor" / "eir-voximplant-callback-token.txt"
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(token, encoding="utf-8")
            manuals.append(
                f"gcloud was not available. Callback token saved locally at .cursor/eir-voximplant-callback-token.txt. "
                f"After gcloud works: gcloud secrets create {GCP_CALLBACK_SECRET} --project={GOOGLE_PROJECT} "
                f"then gcloud secrets versions add {GCP_CALLBACK_SECRET} --project={GOOGLE_PROJECT} "
                "--data-file=.cursor/eir-voximplant-callback-token.txt"
            )
        except RuntimeError as exc:
            manuals.append(str(exc))
    upsert_secret(api, application_id, SECRET_CALLBACK_TOKEN, token)
    upsert_secret(api, application_id, SECRET_CALLBACK_URL, API_URL + CALLBACK_PATH)
    return manuals


def ensure_phone_secrets(api: VoximplantAPI, application_id: int) -> list[str]:
    missing: list[str] = []
    demo_phone = _env_path("EIR_DEMO_PHONE_E164")
    caller_id = _env_path("VOXIMPLANT_CALLER_ID_E164")
    if demo_phone:
        upsert_secret(api, application_id, SECRET_DESTINATION, demo_phone)
        try:
            _ensure_gcp_secret(GCP_DEMO_PHONE_SECRET, demo_phone)
        except FileNotFoundError:
            missing.append("gcloud is required to store EIR_DEMO_PHONE_E164 in Secret Manager.")
    else:
        missing.append(
            "Set EIR_DEMO_PHONE_E164 to the demo cellphone in E.164, then rerun this provisioner. "
            "Do not put it in Git."
        )
    if caller_id:
        upsert_secret(api, application_id, SECRET_CALLER, caller_id)
        try:
            _ensure_gcp_secret(GCP_CALLER_SECRET, caller_id)
        except FileNotFoundError:
            missing.append("gcloud is required to store VOXIMPLANT_CALLER_ID_E164 in Secret Manager.")
    else:
        missing.append(
            "Set VOXIMPLANT_CALLER_ID_E164 to a verified Voximplant Caller ID, then rerun."
        )
    return missing


def verified_caller_ids(api: VoximplantAPI) -> list[dict[str, Any]]:
    items = _as_list(_result(api.call("GetCallerIDs")))
    verified = []
    for item in items:
        if item.get("verified") or item.get("active") or item.get("callerid_active"):
            verified.append(item)
    return verified


def ensure_runtime_key(api: VoximplantAPI) -> list[str]:
    try:
        if _gcp_secret_exists(GCP_RUNTIME_SECRET):
            return []
    except FileNotFoundError:
        pass
    keys = _as_list(_result(api.call("GetKeys")))
    existing = next(
        (
            item
            for item in keys
            if RUNTIME_KEY_NAME in str(item.get("description") or "")
            or RUNTIME_KEY_NAME in str(item.get("key_name") or "")
        ),
        None,
    )
    if existing is not None:
        return [
            "Voximplant Settings -> Service accounts -> Add\n"
            f"name: {RUNTIME_KEY_NAME}\n"
            "role: Scenarios\n"
            "Generate key, save JSON locally, then:\n"
            f"gcloud secrets create {GCP_RUNTIME_SECRET} --project={GOOGLE_PROJECT}  (if needed)\n"
            f"gcloud secrets versions add {GCP_RUNTIME_SECRET} --project={GOOGLE_PROJECT} --data-file=<runtime-json>"
        ]
    created = api.call(
        "CreateKey",
        key_name=RUNTIME_KEY_NAME,
        description=RUNTIME_KEY_NAME,
        role_name="Scenarios",
    )
    if "error" in created:
        return [
            "Voximplant Settings -> Service accounts -> Add\n"
            f"name: {RUNTIME_KEY_NAME}\n"
            "role: Scenarios\n"
            "Generate key and store it in GCP Secret Manager as "
            f"{GCP_RUNTIME_SECRET}. Do not deploy the Admin bootstrap key."
        ]
    result = created.get("result") or created
    payload = {
        "account_id": result.get("account_id") or api.account_id,
        "key_id": result.get("key_id"),
        "private_key": result.get("private_key"),
    }
    if not payload["key_id"] or not payload["private_key"]:
        return [
            "Voximplant Settings -> Service accounts -> Add\n"
            f"name: {RUNTIME_KEY_NAME}\n"
            "role: Scenarios\n"
            "Generate key and store JSON in GCP Secret Manager "
            f"{GCP_RUNTIME_SECRET}."
        ]
    try:
        _ensure_gcp_secret(GCP_RUNTIME_SECRET, json.dumps(payload))
        return []
    except FileNotFoundError:
        local = ROOT / ".cursor" / "eir-runtime-caller.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps(payload), encoding="utf-8")
        return [
            "gcloud was not available. Runtime Voximplant key saved at "
            ".cursor/eir-runtime-caller.json (gitignored). After gcloud works:\n"
            f"gcloud secrets create {GCP_RUNTIME_SECRET} --project={GOOGLE_PROJECT}\n"
            f"gcloud secrets versions add {GCP_RUNTIME_SECRET} --project={GOOGLE_PROJECT} "
            "--data-file=.cursor/eir-runtime-caller.json"
        ]


def ensure_google_live_sa(api: VoximplantAPI, application_id: int) -> list[str]:
    existing = next(
        (item for item in _secrets(api, application_id) if item.get("secret_name") == SECRET_VERTEX),
        None,
    )
    if existing is not None:
        return []
    sa_email = f"{GOOGLE_SA}@{GOOGLE_PROJECT}.iam.gserviceaccount.com"
    try:
        describe = _gcloud_run(
            ["gcloud", "iam", "service-accounts", "describe", sa_email, f"--project={GOOGLE_PROJECT}"],
            check=False,
        )
    except FileNotFoundError:
        return [
            "gcloud is required to create Google SA eir-voximplant-live "
            f"with {VERTEX_ROLE}, generate a JSON key, upload it to Voximplant "
            f"Secret Storage as {SECRET_VERTEX}, then delete the local key."
        ]
    if describe.returncode != 0:
        created = _gcloud_run(
            [
                "gcloud",
                "iam",
                "service-accounts",
                "create",
                GOOGLE_SA,
                f"--project={GOOGLE_PROJECT}",
                "--display-name=EIR Voximplant Gemini Live",
            ],
            check=False,
        )
        if created.returncode != 0:
            return [created.stderr.strip() or "Could not create eir-voximplant-live service account"]
    _gcloud_run(
        [
            "gcloud",
            "projects",
            "add-iam-policy-binding",
            GOOGLE_PROJECT,
            f"--member=serviceAccount:{sa_email}",
            f"--role={VERTEX_ROLE}",
        ],
        check=False,
    )
    with tempfile.TemporaryDirectory() as tmp:
        key_path = Path(tmp) / "eir-voximplant-live.json"
        keyed = _gcloud_run(
            [
                "gcloud",
                "iam",
                "service-accounts",
                "keys",
                "create",
                str(key_path),
                f"--iam-account={sa_email}",
                f"--project={GOOGLE_PROJECT}",
            ],
            check=False,
        )
        if keyed.returncode != 0:
            return [
                "Organization policy prevented creating a Google service-account key.\n"
                "Do not weaken the org policy.\n"
                "If a key already exists outside Git, upload it to Voximplant Secret Storage "
                f"as {SECRET_VERTEX} and rerun."
            ]
        credential_json = key_path.read_text(encoding="utf-8")
        upsert_secret(api, application_id, SECRET_VERTEX, credential_json)
        key_path.unlink(missing_ok=True)
    return []


def _preview_password() -> str:
    return f"{secrets.token_urlsafe(18)}Aa1!"


def _read_preview_password() -> str:
    if not PREVIEW_ENV.is_file():
        return ""
    for line in PREVIEW_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("VOXIMPLANT_PREVIEW_PASSWORD="):
            return line.split("=", 1)[1].strip()
    return ""


def preview_login(account_name: str) -> str:
    account = str(account_name).split("@")[0]
    return f"{PREVIEW_USER}@{APP_NAME}.{account}.voximplant.com"


def _write_preview_env(*, login: str, password: str) -> None:
    PREVIEW_ENV.write_text(
        "\n".join(
            [
                f"VOXIMPLANT_PREVIEW_USER={PREVIEW_USER}",
                f"VOXIMPLANT_PREVIEW_LOGIN={login}",
                f"VOXIMPLANT_PREVIEW_PASSWORD={password}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def ensure_preview_user(api: VoximplantAPI, application_id: int, account_name: str) -> list[str]:
    payload = api.call("GetUsers", application_id=application_id, user_name=PREVIEW_USER)
    users = _as_list(_result(payload)) if "error" not in payload else []
    existing = next(
        (
            item
            for item in users
            if str(item.get("user_name") or "").split("@")[0] == PREVIEW_USER
        ),
        None,
    )
    stored = _read_preview_password()
    password = stored or _preview_password()
    login = preview_login(account_name)
    if existing is None:
        created = api.call(
            "AddUser",
            user_name=PREVIEW_USER,
            user_display_name="EIR preview",
            user_password=password,
            application_id=application_id,
            user_active="true",
            parent_accounting="true",
        )
        if "error" in created:
            return [
                "Voximplant Control Panel -> Applications -> eir-recovery -> Users -> Add\n"
                f"username: {PREVIEW_USER}\n"
                "Generate a strong password and save it locally as .voximplant-preview.env. "
                "Do not paste the password into chat."
            ]
    elif not stored:
        user_id = existing.get("user_id")
        updated = api.call(
            "SetUserInfo",
            user_id=user_id,
            application_id=application_id,
            user_name=PREVIEW_USER,
            user_password=password,
            user_active="true",
        )
        if "error" in updated:
            return [
                "Could not reset the preview user password via API.\n"
                f"Voximplant Control Panel -> Applications -> eir-recovery -> Users -> {PREVIEW_USER}\n"
                "Set a password and save it to .voximplant-preview.env. Do not paste it into chat."
            ]
    _write_preview_env(login=login, password=password)
    return []


def route_price(api: VoximplantAPI, destination: str) -> dict[str, Any]:
    prefix = "".join(ch for ch in destination if ch.isdigit())[:4] or destination
    payload = api.call("GetResourcePrice", resource_type="1", resource_param=prefix)
    if "error" in payload:
        payload = api.call("GetResourcePrice", resource_type="1")
    result = payload.get("result") or payload
    return {"raw_present": "error" not in payload, "groups": _as_list(result)}


def _write_runtime_env(application_id: int, rule_id: int) -> None:
    cursor = ROOT / ".cursor"
    cursor.mkdir(parents=True, exist_ok=True)
    (cursor / "voximplant-runtime.env").write_text(
        "\n".join(
            [
                "VOICE_PROVIDER=voximplant",
                f"VOXIMPLANT_APPLICATION_ID={application_id}",
                f"VOXIMPLANT_RULE_ID={rule_id}",
                "GEMINI_LIVE_MODEL=gemini-live-2.5-flash-native-audio",
                "GEMINI_LIVE_LOCATION=us-central1",
                "GEMINI_LIVE_VOICE=Sulafat",
                "VOXIMPLANT_VOICE_TRANSPORT=pstn",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _admin_client() -> VoximplantAPI:
    creds_path = _env_path("VOXIMPLANT_CREDENTIALS")
    if not creds_path:
        raise ManualActionRequired(
            "Voximplant:\n"
            "Settings -> Service accounts -> Add\n"
            "name: eir-bootstrap\n"
            "role: Admin\n"
            "Generate key\n"
            "save JSON locally\n"
            "set VOXIMPLANT_CREDENTIALS to its path"
        )
    return VoximplantAPI(load_credentials(creds_path))


def sync_scenario() -> int:
    """Upload scenario.js only. Used by CI; does not touch PSTN secrets or Cloud Run."""
    _load_env_file()
    api = _admin_client()
    info = discover(api)
    application_id = ensure_application(api)
    scenario_id = ensure_scenario(api, application_id)
    print("Voximplant scenario synced")
    print(f"  account_id: {info['account_id']}")
    print(f"  application: {APP_NAME} ({application_id})")
    print(f"  scenario: {SCENARIO_NAME} ({scenario_id})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotent Voximplant provisioning")
    parser.add_argument(
        "--sync-scenario",
        action="store_true",
        help="Upload infra/voximplant/scenario.js only. Does not require PSTN secrets.",
    )
    args = parser.parse_args()
    _load_env_file()
    if args.sync_scenario:
        return sync_scenario()
    creds_path = _env_path("VOXIMPLANT_CREDENTIALS")
    if not creds_path:
        print("MANUAL_ACTION_REQUIRED")
        print()
        print("Voximplant:")
        print("Settings -> Service accounts -> Add")
        print("name: eir-bootstrap")
        print("role: Admin")
        print("Generate key")
        print("save JSON locally")
        print("set VOXIMPLANT_CREDENTIALS to its path")
        return 2

    api = VoximplantAPI(load_credentials(creds_path))
    info = discover(api)
    print("Voximplant account discovered")
    print(f"  account_id: {info['account_id']}")
    print(f"  account_name: {info['account_name']}")
    print(f"  api: {info['api_host']}")
    print(f"  live_balance: {info['live_balance']}")
    print(f"  applications: {len(info['applications'])}")
    print(f"  scenarios: {len(info['scenarios'])}")
    print(f"  rules: {len(info['rules'])}")
    print(f"  caller_ids_configured: {len(info['caller_ids'])}")

    application_id = ensure_application(api)
    scenario_id = ensure_scenario(api, application_id)
    rule_id = ensure_rule(api, application_id, scenario_id)
    manuals = ensure_callback_token(api, application_id)
    manuals.extend(ensure_preview_user(api, application_id, str(info["account_name"])))
    manuals.extend(ensure_phone_secrets(api, application_id))
    manuals.extend(ensure_runtime_key(api))
    manuals.extend(ensure_google_live_sa(api, application_id))
    _write_runtime_env(application_id, rule_id)

    verified = verified_caller_ids(api)
    print()
    print("Provisioned")
    print(f"  application: {APP_NAME} ({application_id})")
    print(f"  scenario: {SCENARIO_NAME} ({scenario_id})")
    print(f"  rule: {RULE_NAME} ({rule_id})")
    print(f"  preview_user: {PREVIEW_USER}")
    print("  preview credentials: .voximplant-preview.env")
    print(f"  verified_caller_ids: {len(verified)}")
    print("  runtime env: .cursor/voximplant-runtime.env")

    if not verified:
        manuals.append(
            "Voximplant Control Panel -> Settings / Caller IDs -> verify a number by phone/code.\n"
            "Then set VOXIMPLANT_CALLER_ID_E164 and rerun this provisioner.\n"
            "Do not use a Voximplant test number as Caller ID."
        )

    if manuals:
        print()
        print("MANUAL_ACTION_REQUIRED")
        print()
        for item in manuals:
            print(item)
            print()
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManualActionRequired as exc:
        print("MANUAL_ACTION_REQUIRED")
        print()
        print(exc.message)
        raise SystemExit(2) from exc
