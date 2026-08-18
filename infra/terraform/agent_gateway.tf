locals {
  agent_gateway_id   = "eir-agent-egress"
  agent_gateway_name = "projects/${var.project_id}/locations/${var.region}/agentGateways/${local.agent_gateway_id}"
  model_armor_template_name = (
    "projects/${var.project_id}/locations/${var.region}/templates/${var.model_armor_template}"
  )
  gateway_modelarmor_members = toset([
    "serviceAccount:service-${local.project_number}@gcp-sa-dep.iam.gserviceaccount.com",
    "serviceAccount:service-${local.project_number}@gcp-sa-agentgateway.iam.gserviceaccount.com",
  ])
  iap_extension_metadata = merge(
    { iapPolicyVersion = "V1" },
    var.agent_gateway_iap_enforcement_mode == "DRY_RUN" ? { iamEnforcementMode = "DRY_RUN" } : {}
  )
}

resource "google_project_service_identity" "networkservices" {
  provider = google-beta
  project  = var.project_id
  service  = "networkservices.googleapis.com"

  depends_on = [google_project_service.apis]
}

resource "google_network_services_agent_gateway" "egress" {
  name        = local.agent_gateway_id
  location    = var.region
  project     = var.project_id
  description = "EIR Patient Access AGENT_TO_ANYWHERE egress governance"

  google_managed {
    governed_access_path = "AGENT_TO_ANYWHERE"
  }

  registries = [
    "//agentregistry.googleapis.com/projects/${var.project_id}/locations/${var.region}"
  ]

  depends_on = [google_project_service.apis]
}

resource "google_network_services_authz_extension" "iap_request" {
  name        = "eir-iap-request-authz"
  location    = var.region
  project     = var.project_id
  description = "IAP REQUEST_AUTHZ for Agent Gateway (audit-only until ENFORCED)"
  service     = "iap.googleapis.com"
  fail_open   = true
  timeout     = "1s"
  metadata    = local.iap_extension_metadata

  depends_on = [google_project_service.apis]
}

resource "google_network_security_authz_policy" "iap_request" {
  name           = "eir-iap-request-authz"
  location       = var.region
  project        = var.project_id
  description    = "Delegate Agent Gateway request authorization to IAP"
  policy_profile = "REQUEST_AUTHZ"
  action         = "CUSTOM"

  target {
    resources = [google_network_services_agent_gateway.egress.id]
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.iap_request.id]
    }
  }

  depends_on = [google_network_services_agent_gateway.egress]
}

resource "google_network_services_authz_extension" "model_armor_content" {
  name        = "eir-model-armor-content-authz"
  location    = var.region
  project     = var.project_id
  description = "Native Model Armor CONTENT_AUTHZ for Agent Gateway using eir-agent-guard"
  service     = "modelarmor.${var.region}.rep.googleapis.com"
  fail_open   = true
  timeout     = "1s"
  metadata = {
    model_armor_settings = jsonencode([
      {
        request_template_id  = local.model_armor_template_name
        response_template_id = local.model_armor_template_name
      }
    ])
  }

  depends_on = [google_project_service.apis]
}

resource "google_network_security_authz_policy" "model_armor_content" {
  name           = "eir-model-armor-content-authz"
  location       = var.region
  project        = var.project_id
  description    = "Delegate Agent Gateway content inspection to Model Armor"
  policy_profile = "CONTENT_AUTHZ"
  action         = "CUSTOM"

  target {
    resources = [google_network_services_agent_gateway.egress.id]
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.model_armor_content.id]
    }
  }

  http_rules {
    to {
      operations {
        paths {
          prefix = "/"
        }
      }
    }
    when = "request.headers['content-type'] == 'application/json' || request.headers['content-type'].startsWith('text/')"
  }
}

resource "google_project_iam_member" "gateway_modelarmor_callout" {
  for_each = local.gateway_modelarmor_members

  project    = var.project_id
  role       = "roles/modelarmor.calloutUser"
  member     = each.value
  depends_on = [google_project_service_identity.networkservices]
}

resource "google_project_iam_member" "gateway_serviceusage_consumer" {
  for_each = local.gateway_modelarmor_members

  project    = var.project_id
  role       = "roles/serviceusage.serviceUsageConsumer"
  member     = each.value
  depends_on = [google_project_service_identity.networkservices]
}

resource "google_project_iam_member" "gateway_modelarmor_user" {
  for_each = local.gateway_modelarmor_members

  project    = var.project_id
  role       = "roles/modelarmor.user"
  member     = each.value
  depends_on = [google_project_service_identity.networkservices]
}

resource "google_iap_agent_registry_endpoint_iam_member" "gateway_destinations" {
  for_each = google_agent_registry_service.gateway_destinations

  project     = var.project_id
  location    = var.region
  endpoint_id = element(split("/", each.value.registry_resource), length(split("/", each.value.registry_resource)) - 1)
  role        = "roles/iap.egressor"
  member      = var.patient_access_agent_identity
}
