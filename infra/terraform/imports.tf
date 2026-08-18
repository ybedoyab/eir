import {
  to = google_artifact_registry_repository.eir
  id = "projects/eir-ata/locations/us-central1/repositories/eir"
}

import {
  to = google_service_account.runtime
  id = "projects/eir-ata/serviceAccounts/eir-runtime@eir-ata.iam.gserviceaccount.com"
}

import {
  to = google_pubsub_topic.recovery_events
  id = "projects/eir-ata/topics/eir-recovery-events"
}

import {
  to = google_pubsub_subscription.recovery_worker
  id = "projects/eir-ata/subscriptions/eir-recovery-events-worker"
}

import {
  to = google_firestore_database.default
  id = "projects/eir-ata/databases/(default)"
}

import {
  to = google_healthcare_dataset.eir
  id = "projects/eir-ata/locations/us-central1/datasets/eir"
}

import {
  to = google_healthcare_fhir_store.fhir_r4
  id = "projects/eir-ata/locations/us-central1/datasets/eir/fhirStores/fhir-r4"
}

import {
  to = google_cloud_run_v2_service.api
  id = "projects/eir-ata/locations/us-central1/services/eir-api"
}

import {
  to = google_cloud_run_v2_service.worker
  id = "projects/eir-ata/locations/us-central1/services/eir-worker"
}

import {
  to = google_cloud_run_v2_service.ui
  id = "projects/eir-ata/locations/us-central1/services/eir-ui"
}

import {
  to = google_secret_manager_secret.secrets["eir-gemini-api-key"]
  id = "projects/eir-ata/secrets/eir-gemini-api-key"
}

import {
  to = google_secret_manager_secret.secrets["eir-scheduler-secret"]
  id = "projects/eir-ata/secrets/eir-scheduler-secret"
}

import {
  to = google_secret_manager_secret.secrets["eir-session-secret"]
  id = "projects/eir-ata/secrets/eir-session-secret"
}

import {
  to = google_secret_manager_secret.secrets["eir-voximplant-callback-token"]
  id = "projects/eir-ata/secrets/eir-voximplant-callback-token"
}

import {
  to = google_secret_manager_secret.secrets["eir-voximplant-runtime-credentials"]
  id = "projects/eir-ata/secrets/eir-voximplant-runtime-credentials"
}

import {
  to = google_secret_manager_secret.secrets["eir-demo-phone-e164"]
  id = "projects/eir-ata/secrets/eir-demo-phone-e164"
}

import {
  to = google_secret_manager_secret.secrets["eir-voximplant-caller-id"]
  id = "projects/eir-ata/secrets/eir-voximplant-caller-id"
}
