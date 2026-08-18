resource "google_pubsub_topic" "recovery_events" {
  name    = "eir-recovery-events"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "recovery_worker" {
  name    = "eir-recovery-events-worker"
  topic   = google_pubsub_topic.recovery_events.name
  project = var.project_id

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "ops_events" {
  name    = "eir-ops-events"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "ops_events_worker" {
  name    = "eir-ops-events-worker"
  topic   = google_pubsub_topic.ops_events.name
  project = var.project_id

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ops_dlq.id
    max_delivery_attempts = 5
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "ops_dlq" {
  name    = "eir-ops-events-dlq"
  project = var.project_id

  depends_on = [google_project_service.apis]
}
