export type EpisodeStatus =
  | "ACTIVE"
  | "WAITING"
  | "WAITING_FOR_NEXT_FOLLOWUP"
  | "ESCALATED"
  | "COMPLETED"
  | "CANCELLED";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ContactChannel = "voice" | "sms" | "email";

export interface Patient {
  id: string;
  name: string;
  date_of_birth: string;
  preferred_language: string;
  preferred_contact_channel: ContactChannel;
}

export interface PatientMedication {
  sku: string;
  name: string;
  dose: string;
  critical: boolean;
  rxnorm_code: string;
  status: string;
}

export interface RecoveryEpisode {
  id: string;
  patient_id: string;
  status: EpisodeStatus;
  started_at: string;
  next_follow_up_at: string | null;
  risk_level: RiskLevel;
  assigned_agents: string[];
}

export interface DomainEvent {
  event_id: string;
  event_type: string;
  episode_id: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface HumanReview {
  id: string;
  episode_id: string;
  workflow?: string;
  reason: string;
  capability: string;
  agent_name: string;
  status: "pending" | "resolved";
  created_at: string;
  resolved_at: string | null;
  note: string;
  pending_capability?: string;
}

export interface AgentDescriptor {
  name: string;
  version: string;
  capabilities: string[];
  risk_level: string;
  description: string;
}

export interface WorkflowTrace {
  workflow_id: string;
  episode_id: string;
  trace_id: string;
  agent_name: string;
  event_type: string;
  timestamp: string;
  status: string;
}

export interface AdkWorkerTelemetry {
  timestamp: string;
  service: string;
  model: string;
  model_location: string;
  capability: string;
  agent_name: string;
  tools_invoked: string[];
  success: boolean;
  used_direct_fallback: boolean;
  episode_id?: string;
  trace_id?: string;
  error_type?: string | null;
  error_message?: string | null;
  security_adapter?: string | null;
  security_category?: string | null;
}

export interface DemoBootstrapResponse {
  episode_id: string;
  patient_id: string;
  patient_name?: string;
  status: EpisodeStatus;
  risk_level: RiskLevel;
  next_follow_up_at: string | null;
  fast_forwarded: boolean;
  monitoring?: boolean;
  medications?: PatientMedication[];
}

export interface DemoAdvanceResponse {
  advanced: boolean;
  episode_id: string;
  event: string | null;
  reason?: string;
}

export interface RuntimeStatus {
  adk_worker: AdkWorkerTelemetry | null;
  content_guard: {
    adapter: string;
    managed_model_armor_available: boolean;
  };
  model_armor: {
    configured?: boolean;
    mode: string;
    location: string;
    template: string;
    available: boolean;
    managed_available?: boolean;
    last_screening_success: boolean | null;
    last_decision_adapter?: string | null;
    last_error_type?: string | null;
    last_filter_category?: string | null;
    last_blocked?: boolean | null;
  };
  fleet: {
    gemini_model: string;
    gemini_location: string;
    vertex_probe_success: boolean;
    adk_mode: string;
    adk_allow_direct_fallback: boolean;
    runtime_region: string;
    event_bus: string;
    fhir_mode: string;
    pubsub_handle: boolean;
    workflow_subscriber: string;
    voice?: {
      configured_provider: string;
      active_provider: string;
      mode: string;
      pstn_enabled: boolean;
      synthetic_patients_only: boolean;
      gemini_live_model: string;
      gemini_live_location: string;
      gemini_live_voice: string;
      admin_credentials_used_at_runtime: boolean;
      browser_voice_enabled?: boolean;
      browser_voice_login_configured?: boolean;
    };
    recovery_video?: {
      configured: boolean;
      mode: string;
      adapter: string;
      model?: string;
      storage?: { backend: string; bucket?: string };
      last_success?: boolean | null;
      last_error?: string | null;
    };
    platform?: {
      managed_agent_runtime_verified?: boolean;
      managed_memory_bank_verified?: boolean;
      managed_registry_verified?: boolean;
      managed_agent_identity_verified?: boolean;
      managed_agent_gateway_verified?: boolean;
      managed_model_armor_verified?: boolean;
      otel_cloud_trace_verified?: boolean;
      cloud_logging_verified?: boolean;
    };
  };
}

export type StockStatus = "HEALTHY" | "LOW" | "CRITICAL" | "OUT_OF_STOCK";

export type SupplyUrgency = "NORMAL" | "HIGH" | "CRITICAL";

export type ReplenishmentStatus =
  | "ACTIVE"
  | "SOURCING"
  | "AWAITING_APPROVAL"
  | "BLOCKED"
  | "ORDERED"
  | "COMPLETED"
  | "CANCELLED";

export type PurchaseOrderStatus =
  | "DRAFT"
  | "APPROVED"
  | "PLACED"
  | "RECEIVED"
  | "CANCELLED";

export interface InventoryItem {
  sku: string;
  name: string;
  form: string;
  unit: string;
  on_hand: number;
  reorder_point: number;
  target_level: number;
  daily_usage: number;
  critical: boolean;
  rxnorm_code?: string;
  patient_count?: number;
  updated_at: string;
  status: StockStatus;
  days_of_cover: number | null;
}

export interface SupplierCatalogEntry {
  sku: string;
  unit_price: number;
  available_units: number;
  currency: string;
}

export interface Supplier {
  id: string;
  name: string;
  contact_name: string;
  phone_e164: string;
  lead_time_days: number;
  catalog: SupplierCatalogEntry[];
}

export interface SupplierQuote {
  supplier_id: string;
  supplier_name: string;
  sku: string;
  unit_price: number;
  currency: string;
  available_units: number;
  lead_time_days: number;
  quoted_at: string;
  call_id: string;
  provider: string;
  transcript: Array<{ role: string; text: string }>;
}

export interface PurchaseOrder {
  id: string;
  case_id: string;
  sku: string;
  supplier_id: string;
  supplier_name: string;
  quantity: number;
  unit_price: number;
  currency: string;
  lead_time_days: number;
  status: PurchaseOrderStatus;
  drafted_at: string;
  approved_by: string;
  approved_at: string | null;
  expected_delivery: string | null;
  total_cost: number;
}

export interface ReplenishmentCase {
  id: string;
  sku: string;
  item_name: string;
  status: ReplenishmentStatus;
  urgency: SupplyUrgency;
  opened_at: string;
  closed_at: string | null;
  requested_quantity: number;
  rationale: string;
  quotes: SupplierQuote[];
  purchase_order: PurchaseOrder | null;
  contacted_supplier_ids: string[];
  assigned_agents: string[];
}
