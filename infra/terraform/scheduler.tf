resource "google_cloud_scheduler_job" "process_due_follow_ups" {
  name        = "eir-process-due-follow-ups"
  description = "Trigger recovery follow-up processing"
  schedule    = "*/15 * * * *"
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/recovery/process-due-follow-ups"

    oidc_token {
      service_account_email = google_service_account.runtime.email
      audience              = google_cloud_run_v2_service.api.uri
    }
  }

  retry_config {
    retry_count          = 0
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
    max_retry_duration   = "0s"
  }

  lifecycle {
    ignore_changes = [http_target]
  }

  depends_on = [google_project_service.apis]
}
