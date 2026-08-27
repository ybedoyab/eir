resource "google_storage_bucket" "recovery_media" {
  name                        = "eir-ata-recovery-media-${local.project_number}"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  # Synthetic demo clips only — no retention requirement.
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "recovery_media_runtime_sa" {
  bucket = google_storage_bucket.recovery_media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "recovery_media_vertex_sa" {
  bucket = google_storage_bucket.recovery_media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-aiplatform.iam.gserviceaccount.com"
}
