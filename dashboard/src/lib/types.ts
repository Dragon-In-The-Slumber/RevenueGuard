// Must match the backend's InvoiceStatus enum and API responses exactly
export type InvoiceStatus =
  | "ISSUED" | "OVERDUE" | "NOTIFIED_1" | "NOTIFIED_2" | "NOTIFIED_3"
  | "PAUSED_PTP" | "DISPUTE" | "LEGAL_HOLD" | "UNRESPONSIVE"
  | "RECOVERED" | "HUMAN_ESCALATED";

export interface Invoice {
  id: number;
  amount: number;
  client_name: string;
  client_email: string;
  due_date: string;
  status: InvoiceStatus;
  promised_date: string | null;
  escalation_stage: string;
  razorpay_payment_link_id: string | null;
  razorpay_payment_link_url: string | null;
  razorpay_virtual_account_id: string | null;
  contact_attempts?: number;
  relationship_score?: number;
  last_contact_date?: string | null;
  next_contact_allowed_date?: string | null;
  escalations_blocked?: number;
}

export interface AuditLogEntry {
  id: number;
  invoice_id: number;
  client_name?: string;
  timestamp: string;
  event_type: string;
  agent_reasoning: string | null;
  action_taken: string;
  rule_applied: string | null;
  content_snapshot: string | null;
  compliance_verdict: string | null;
  approved_content?: string | null;
}

export interface WsTickPayload {
  virtual_date: string;
  processed_count: number;
  active_nodes: string[];
}

export interface Metrics {
  totalAtRisk: number;
  totalRecovered: number;
  recoveryRate: number;
  totalInvoices: number;
  recoveredInvoices: number;
}

export interface FunnelEntry {
  status: InvoiceStatus;
  count: number;
  amount: number;
}
