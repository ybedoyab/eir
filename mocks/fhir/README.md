# SYNTHETIC FHIR R4 fixtures

These resources are FAKE. They are not derived from any real patient.

Each synthetic patient has its own directory under `mocks/fhir/`:

- `patient-synthetic-001/` — Alex Rivera (low pain, no reported issue)
- `patient-synthetic-002/` — Jordan Lee (high pain, `reported-issue` extension)

Observations may include extension `https://eir.local/extensions/reported-issue` with `valueBoolean`.
