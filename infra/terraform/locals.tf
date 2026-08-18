locals {
  project_number = "658898892127"

  apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "healthcare.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "modelarmor.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "telemetry.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "iam.googleapis.com",
  ]

  runtime_roles = [
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/healthcare.fhirResourceEditor",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
    "roles/modelarmor.user",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
  ]

  deploy_roles = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
    "roles/iam.serviceAccountUser",
    "roles/secretmanager.secretAccessor",
    "roles/healthcare.fhirResourceEditor",
    "roles/storage.admin",
    "roles/serviceusage.serviceUsageConsumer",
  ]

  infra_roles = [
    "roles/editor",
    "roles/iam.securityAdmin",
    "roles/serviceusage.serviceUsageAdmin",
  ]

  secret_names = [
    "eir-session-secret",
    "eir-scheduler-secret",
    "eir-gemini-api-key",
    "eir-voximplant-callback-token",
    "eir-voximplant-runtime-credentials",
    "eir-demo-phone-e164",
    "eir-voximplant-caller-id",
  ]
}
