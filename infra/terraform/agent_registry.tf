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

locals {
  gateway_destinations = {
    eir-api-agent-runtime = {
      display_name = "EIR protected Patient Access tools"
      description  = "Narrow eir-api tool surface used by the managed Patient Access agent"
      url          = "https://eir-api-658898892127.us-central1.run.app/api/v1/agent-runtime/"
    }
    eir-vertex-aiplatform = {
      display_name = "Vertex AI regional"
      description  = "Gemini, Sessions, and Memory Bank for the live ReasoningEngine"
      url          = "https://${var.region}-aiplatform.googleapis.com"
    }
    eir-vertex-aiplatform-mtls = {
      display_name = "Vertex AI regional mTLS"
      description  = "Regional mTLS variant used by some Agent Runtime SDK paths"
      url          = "https://${var.region}-aiplatform.mtls.googleapis.com"
    }
    eir-vertex-aiplatform-rep = {
      display_name = "Vertex AI regional REP"
      description  = "Regional endpoint variant used by some Agent Runtime SDK paths"
      url          = "https://aiplatform.${var.region}.rep.googleapis.com"
    }
    eir-vertex-aiplatform-global = {
      display_name = "Vertex AI global"
      description  = "Global Vertex host used by Gemini generateContent"
      url          = "https://aiplatform.googleapis.com"
    }
    eir-vertex-aiplatform-global-mtls = {
      display_name = "Vertex AI global mTLS"
      description  = "Observed Runtime Gemini generateContent host"
      url          = "https://aiplatform.mtls.googleapis.com"
    }
    eir-iamcredentials = {
      display_name = "IAM Credentials"
      description  = "Agent Identity token and allowedLocations"
      url          = "https://iamcredentials.googleapis.com"
    }
    eir-iamcredentials-mtls = {
      display_name = "IAM Credentials mTLS"
      description  = "Observed Runtime IAM Credentials host"
      url          = "https://iamcredentials.mtls.googleapis.com"
    }
    eir-cloudresourcemanager = {
      display_name = "Cloud Resource Manager"
      description  = "SDK project resolution during Runtime init"
      url          = "https://cloudresourcemanager.googleapis.com"
    }
    eir-cloudresourcemanager-mtls = {
      display_name = "Cloud Resource Manager mTLS"
      description  = "Observed Runtime GetProject host"
      url          = "https://cloudresourcemanager.mtls.googleapis.com"
    }
    eir-agentregistry = {
      display_name = "Agent Registry"
      description  = "Required for Agent Gateway destination discovery"
      url          = "https://agentregistry.googleapis.com"
    }
    eir-telemetry = {
      display_name = "Cloud Telemetry"
      description  = "Required when Cloud Trace is enabled on Agent Runtime"
      url          = "https://telemetry.googleapis.com"
    }
    eir-telemetry-mtls = {
      display_name = "Cloud Telemetry mTLS"
      description  = "mTLS variant of Cloud Telemetry"
      url          = "https://telemetry.mtls.googleapis.com"
    }
    eir-logging = {
      display_name = "Cloud Logging"
      description  = "Required when Cloud Logging is enabled on Agent Runtime"
      url          = "https://logging.googleapis.com"
    }
    eir-logging-mtls = {
      display_name = "Cloud Logging mTLS"
      description  = "mTLS variant of Cloud Logging"
      url          = "https://logging.mtls.googleapis.com"
    }
  }
}

resource "google_agent_registry_service" "gateway_destinations" {
  for_each = local.gateway_destinations

  project      = var.project_id
  location     = var.region
  service_id   = each.key
  display_name = each.value.display_name
  description  = each.value.description

  endpoint_spec {
    type = "NO_SPEC"
  }

  interfaces {
    url              = each.value.url
    protocol_binding = "HTTP_JSON"
  }

  depends_on = [google_project_service.apis]
}
