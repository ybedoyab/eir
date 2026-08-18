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
