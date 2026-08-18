resource "google_storage_bucket" "agent_runtime" {
  name                        = "eir-ata-agent-runtime-${local.project_number}"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "agent_runtime_infra" {
  bucket = google_storage_bucket.agent_runtime.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.infra_ci.email}"
}

resource "google_storage_bucket_iam_member" "agent_runtime_runtime_sa" {
  bucket = google_storage_bucket.agent_runtime.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "agent_runtime_vertex_sa" {
  bucket = google_storage_bucket.agent_runtime.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-aiplatform.iam.gserviceaccount.com"
}
