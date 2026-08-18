resource "google_artifact_registry_repository" "eir" {
  location      = var.region
  repository_id = "eir"
  description   = "EIR container images"
  format        = "DOCKER"
  project       = var.project_id

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.apis]
}
