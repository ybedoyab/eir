# Voximplant PSTN + Gemini Live

Idempotent provisioning for EIR real outbound recovery calls.

Orchestration stays on `gemini-3.5-flash`. Voice uses Vertex Gemini Live:

`gemini-live-2.5-flash-native-audio` in `us-central1`, voice `Sulafat`.

## Layout

- `provision.py` — create/update application `eir-recovery`, scenario `eir-gemini-outbound`, rule `eir-outbound`, secrets, least-privilege runtime key
- `scenario.js` — outbound `callPSTN`, Gemini Live over Vertex AI, function call `submit_recovery_checkin`, authenticated callback
- `smoke_test.py` — balance / price / Caller ID preflight; optional `--place-call`

## Credentials

Bootstrap **Admin** key is local-only (`VOXIMPLANT_CREDENTIALS`). Never deploy it to Cloud Run.

Runtime worker uses Secret Manager `eir-voximplant-runtime-credentials` (`eir-runtime-caller`, Scenarios role).

Vertex access for Voximplant uses Google SA `eir-voximplant-live` with `roles/aiplatform.user` only. The JSON key is uploaded to Voximplant Secret Storage as `EIR_GEMINI_VERTEX_CREDENTIALS` and then deleted locally.

## Run

```bash
uv run python infra/voximplant/provision.py
uv run python infra/voximplant/smoke_test.py
```

Do not place paid PSTN calls from CI.

## Secrets (Voximplant Secret Storage)

- `EIR_GEMINI_VERTEX_CREDENTIALS`
- `EIR_CALLBACK_TOKEN`
- `EIR_CALLBACK_URL`
- `EIR_DEMO_PHONE_E164`
- `VOXIMPLANT_CALLER_ID_E164`

`scenario.js` reads them with `VoxEngine.getSecretValue`. Custom data is only `{eid,cid,n}` (200-byte limit). Destination and Caller ID are never logged.

Official Vertex examples sometimes keep the service-account JSON in a second scenario because ApplicationStorage is small. Current Secret Storage allows 8192 characters, which is enough for the dedicated Live key.

## Voice configuration

| Setting | Value |
|---------|--------|
| Backend | Vertex AI |
| Project | `eir-ata` |
| Location | `us-central1` |
| Model | `gemini-live-2.5-flash-native-audio` |
| Voice | `Sulafat` (`speechConfig.prebuiltVoiceConfig.voiceName`) |
| Recording | disabled |
| Transcript persistence | disabled |
