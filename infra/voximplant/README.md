# Voximplant PSTN + Gemini Live

Idempotent provisioning for EIR real outbound recovery calls.

Orchestration stays on `gemini-3.5-flash`. Voice uses Vertex Gemini Live:

`gemini-live-2.5-flash-native-audio` in `us-central1`, voice `Sulafat`.

Three transports reach the same conversation. `scenario.js` has two entry points --
`AppEvents.Started` for calls EIR places, `AppEvents.CallAlerting` for calls the browser
places -- and both converge on `driveCall()`, so Gemini Live, function calling, and the EIR
callback are identical in all three cases.

| Transport | Entry point | Needs Caller ID | Trigger |
|---|---|---|---|
| **Browser (`webrtc`)** | `CallAlerting` | no | the patient, from `/dev/voice-preview` |
| PSTN | `Started` | yes | `FollowUpDue` -> `VoximplantVoiceProvider` |
| `callUser` preview | `Started` | no | `smoke_test.py --transport user` (CLI) |

The browser transport is the one that works today: the account has no verified Caller ID and
no phone number, so PSTN cannot dial. An inbound leg is forced to `webrtc` by the entry point
itself -- never by custom data, which the browser controls.

## Layout

- `provision.py` — create/update application `eir-recovery`, scenario `eir-gemini-outbound`, rule `eir-outbound`, secrets, least-privilege runtime key, preview user
- `scenario.js` — shared Gemini Live + `submit_recovery_checkin`; `driveCall()` is shared by both entry points, `startDestinationCall` selects `callPSTN` or `callUser`
- `smoke_test.py` — PSTN preflight / optional `--place-call`; preview: `--transport user`

## Credentials

Bootstrap **Admin** key is local-only (`VOXIMPLANT_CREDENTIALS`). Never bind it to Cloud Run. CI on `main` uses the same Admin JSON as a GitHub Actions secret to run `provision.py --sync-scenario` after Cloud Run deploy. Runtime `StartScenarios` still uses the Scenarios-role key.

Cloud Run does **not** execute VoxEngine. Changing `scenario.js` without that CI step (or a local `--sync-scenario`) leaves the live Voximplant app on the previous script.

Runtime worker uses Secret Manager `eir-voximplant-runtime-credentials` (`eir-runtime-caller`, Scenarios role).

Vertex access for Voximplant uses Google SA `eir-voximplant-live` with `roles/aiplatform.user` only. The JSON key is uploaded to Voximplant Secret Storage as `EIR_GEMINI_VERTEX_CREDENTIALS` and then deleted locally.

Preview Web Softphone login is written once to gitignored `.voximplant-preview.env`. Do not commit or print the password.

## Run

```bash
uv run python infra/voximplant/provision.py
uv run python infra/voximplant/provision.py --sync-scenario
uv run python infra/voximplant/smoke_test.py --transport user
uv run python infra/voximplant/smoke_test.py --transport user --place-call --wait
uv run python infra/voximplant/smoke_test.py
```

Do not place paid PSTN calls from CI. Preview `callUser` does not require Caller ID or `EIR_DEMO_PHONE_E164`.

Browser check-in (no CLI, no password prompt):

1. Close https://phone.voximplant.com so `eir-preview-user` is not registered twice
2. Sign in to EIR as a patient (`alex` / `demo-alex`) and open `/dev/voice-preview`
3. Click **Start voice check-in** and allow the microphone

The CLI `callUser` preview still works for exercising the *outbound* path, but the EIR page no
longer answers incoming calls, so register `eir-preview-user` in the hosted
[Web Softphone](https://phone.voximplant.com) instead (password in `.voximplant-preview.env`),
then run `smoke_test.py --transport user --place-call --wait`. Only one client may hold that
registration, so close the softphone before using the in-page check-in.

## Secret Manager (GCP)

| Secret | Used by | Required for |
|---|---|---|
| `eir-voximplant-callback-token` | API | every transport |
| `eir-voximplant-web-password` | API | browser check-in |
| `eir-voximplant-runtime-credentials` | worker | PSTN / `callUser` |
| `eir-voximplant-caller-id` | worker | PSTN only |
| `eir-demo-phone-e164` | worker | PSTN only |

`deploy.py` binds a secret only when it has an enabled version, and flips `VOICE_PROVIDER` to
`voximplant` only when all three PSTN secrets are populated. Until then outbound follow-ups
stay on the synthetic provider and the browser check-in works regardless.

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
| Browser transport | inbound WebRTC to `eir-checkin` (no Caller ID) |
| Production transport | PSTN (`VOXIMPLANT_VOICE_TRANSPORT=pstn`) |
| Preview transport | `callUser` / `eir-preview-user` (CLI only) |
| Recording | disabled |
| Transcript persistence | disabled |
