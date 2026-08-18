output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

output "deploy_ci_service_account" {
  value = google_service_account.deploy_ci.email
}

output "infra_ci_service_account" {
  value = google_service_account.infra_ci.email
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "ui_url" {
  value = google_cloud_run_v2_service.ui.uri
}

output "artifact_registry" {
  value = google_artifact_registry_repository.eir.id
}

output "fhir_store" {
  value = google_healthcare_fhir_store.fhir_r4.id
}

output "recovery_topic" {
  value = google_pubsub_topic.recovery_events.id
}

output "ops_topic" {
  value = google_pubsub_topic.ops_events.id
}
