# Voximplant PSTN + Gemini Live

Idempotent provisioning for EIR real outbound recovery calls.

Orchestration stays on `gemini-3.5-flash`. Voice uses Vertex Gemini Live:

`gemini-live-2.5-flash-native-audio` in `us-central1`, voice `Sulafat`.

Production Cloud Run stays on **PSTN** (`VoxEngine.callPSTN`). A CLI-only preview transport uses `VoxEngine.callUser` against application user `eir-preview-user` and the official [Web Softphone](https://phone.voximplant.com). After the call connects, Gemini Live, function calling, and the EIR callback are the same path.

## Layout

- `provision.py` — create/update application `eir-recovery`, scenario `eir-gemini-outbound`, rule `eir-outbound`, secrets, least-privilege runtime key, preview user
- `scenario.js` — shared Gemini Live + `submit_recovery_checkin`; `startDestinationCall` selects `callPSTN` or `callUser`
- `smoke_test.py` — PSTN preflight / optional `--place-call`; preview: `--transport user`

## Credentials

Bootstrap **Admin** key is local-only (`VOXIMPLANT_CREDENTIALS`). Never deploy it to Cloud Run.

Runtime worker uses Secret Manager `eir-voximplant-runtime-credentials` (`eir-runtime-caller`, Scenarios role).

Vertex access for Voximplant uses Google SA `eir-voximplant-live` with `roles/aiplatform.user` only. The JSON key is uploaded to Voximplant Secret Storage as `EIR_GEMINI_VERTEX_CREDENTIALS` and then deleted locally.

Preview Web Softphone login is written once to gitignored `.voximplant-preview.env`. Do not commit or print the password.

## Run

```bash
uv run python infra/voximplant/provision.py
uv run python infra/voximplant/smoke_test.py --transport user
uv run python infra/voximplant/smoke_test.py --transport user --place-call --wait
uv run python infra/voximplant/smoke_test.py
```

Do not place paid PSTN calls from CI. Preview `callUser` does not require Caller ID or `EIR_DEMO_PHONE_E164`.

Web Softphone login:

1. Open https://phone.voximplant.com
2. Allow microphone
3. Username is `eir-preview-user@eir-recovery.<account>.voximplant.com` (see `.voximplant-preview.env`)
4. Password from `.voximplant-preview.env` (never paste it into chat)
5. Then run the `--place-call` command above and answer in the browser

## Secrets (Voximplant Secret Storage)

- `EIR_GEMINI_VERTEX_CREDENTIALS`
- `EIR_CALLBACK_TOKEN`
- `EIR_CALLBACK_URL`
- `EIR_DEMO_PHONE_E164` (PSTN only)
- `VOXIMPLANT_CALLER_ID_E164` (PSTN only)

`scenario.js` reads them with `VoxEngine.getSecretValue`. Custom data is `{eid,cid,n}` plus optional `{t:user,u:eir-preview-user}` (200-byte limit). Destination phones are never placed in custom data.

Official Vertex examples sometimes keep the service-account JSON in a second scenario because ApplicationStorage is small. Current Secret Storage allows 8192 characters, which is enough for the dedicated Live key.

## Voice configuration

| Setting | Value |
|---------|--------|
| Backend | Vertex AI |
| Project | `eir-ata` |
| Location | `us-central1` |
| Model | `gemini-live-2.5-flash-native-audio` |
| Voice | `Sulafat` (`speechConfig.prebuiltVoiceConfig.voiceName`) |
| Production transport | PSTN (`VOXIMPLANT_VOICE_TRANSPORT=pstn`) |
| Preview transport | `callUser` / `eir-preview-user` (CLI only) |
| Recording | disabled |
| Transcript persistence | disabled |
