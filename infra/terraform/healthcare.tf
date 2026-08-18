resource "google_healthcare_dataset" "eir" {
  name     = "eir"
  location = var.region
  project  = var.project_id

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_healthcare_fhir_store" "fhir_r4" {
  name    = "fhir-r4"
  dataset = google_healthcare_dataset.eir.id
  version = "R4"

  enable_update_create          = true
  disable_referential_integrity = false

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.apis]
}
