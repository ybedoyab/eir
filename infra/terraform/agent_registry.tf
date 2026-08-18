resource "google_agent_registry_service" "patient_access" {
  project      = var.project_id
  location     = var.region
  service_id   = "eir-patient-access"
  display_name = "eir-patient-access"
  description  = "EIR Patient Access ADK agent on Gemini Enterprise Agent Runtime"

  agent_spec {
    type = "NO_SPEC"
  }

  interfaces {
    url              = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/${var.project_id}/locations/${var.region}/reasoningEngines/${var.patient_access_reasoning_engine_id}"
    protocol_binding = "HTTP_JSON"
  }
}
