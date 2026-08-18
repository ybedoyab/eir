variable "project_id" {
  type        = string
  description = "GCP project ID"
  default     = "eir-ata"
}

variable "region" {
  type        = string
  description = "Primary GCP region"
  default     = "us-central1"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository allowed for workload identity federation"
  default     = "ybedoyab/eir"
}

variable "api_image" {
  type        = string
  description = "Cloud Run API container image (updated by deploy pipeline)"
  default     = "us-central1-docker.pkg.dev/eir-ata/eir/backend:latest"
}

variable "worker_image" {
  type        = string
  description = "Cloud Run worker container image (updated by deploy pipeline)"
  default     = "us-central1-docker.pkg.dev/eir-ata/eir/backend:latest"
}

variable "ui_image" {
  type        = string
  description = "Cloud Run UI container image (updated by deploy pipeline)"
  default     = "us-central1-docker.pkg.dev/eir-ata/eir/frontend:latest"
}

variable "patient_access_reasoning_engine_id" {
  type        = string
  description = "Live Patient Access ReasoningEngine ID deployed by the Agent Platform SDK"
  default     = "3041998479602745344"
}

variable "patient_access_agent_identity" {
  type        = string
  description = "Managed Agent Identity principal for the live Patient Access ReasoningEngine"
  default     = "principal://agents.global.proj-658898892127.system.id.goog/resources/aiplatform/projects/658898892127/locations/us-central1/reasoningEngines/3041998479602745344"
}

variable "agent_gateway_iap_enforcement_mode" {
  type        = string
  description = "IAP authorization extension mode: DRY_RUN (audit-only) or ENFORCED"
  default     = "ENFORCED"

  validation {
    condition     = contains(["DRY_RUN", "ENFORCED"], var.agent_gateway_iap_enforcement_mode)
    error_message = "agent_gateway_iap_enforcement_mode must be DRY_RUN or ENFORCED."
  }
}

variable "model_armor_template" {
  type        = string
  description = "Existing managed Model Armor template used by Agent Gateway CONTENT_AUTHZ"
  default     = "eir-agent-guard"
}
