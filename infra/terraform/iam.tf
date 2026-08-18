resource "google_service_account" "runtime" {
  account_id   = "eir-runtime"
  display_name = "EIR runtime"
  project      = var.project_id
}

resource "google_service_account" "deploy_ci" {
  account_id   = "eir-deploy-ci"
  display_name = "EIR deploy CI"
  project      = var.project_id
}

resource "google_service_account" "infra_ci" {
  account_id   = "eir-infra-ci"
  display_name = "EIR infrastructure CI"
  project      = var.project_id
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "deploy_ci" {
  for_each = toset(local.deploy_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deploy_ci.email}"
}

resource "google_project_iam_member" "infra_ci" {
  for_each = toset(local.infra_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.infra_ci.email}"
}

resource "google_service_account_iam_member" "deploy_ci_wif" {
  service_account_id = google_service_account.deploy_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_service_account_iam_member" "infra_ci_wif" {
  service_account_id = google_service_account.infra_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
