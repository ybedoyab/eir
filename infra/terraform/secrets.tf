resource "google_secret_manager_secret" "secrets" {
  for_each = toset(local.secret_names)

  secret_id = each.value
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "runtime_accessor" {
  for_each = toset(local.secret_names)

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
