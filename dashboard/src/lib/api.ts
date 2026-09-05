const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

/** Error thrown by apiFetch on any non-2xx response. Mirrors ApiError in hooks/useApi. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly path: string;
  readonly detail: string;

  constructor(status: number, path: string, detail: string) {
    super(detail || `API ${status} on ${path}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.path = path;
    this.detail = detail;
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const cleanPath = path.startsWith('/') ? path : '/' + path;
  const res = await fetch(`${API_BASE}${cleanPath}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    // FastAPI puts the message in `detail`; fall back to raw text for anything else.
    const raw = await res.text().catch(() => "");
    let detail = raw;
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.detail === "string") detail = parsed.detail;
    } catch {
      /* not JSON — keep the raw body */
    }
    throw new ApiRequestError(res.status, cleanPath, detail);
  }
  return res.json();
}

export const apiPost = <T>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });

/** Razorpay webhook events the backend handles. */
export type WebhookEvent =
  | "invoice.paid"
  | "invoice.partially_paid"
  | "payment_link.paid"
  | "payment.dispute.created"
  | "payment.failed"
  | "virtual_account.credited";

export interface WebhookResult {
  status: string;
  event: string;
  invoice_id: number | null;
  matched: boolean;
  old_status: string | null;
  new_status: string | null;
}

/**
 * Single entry point for firing a simulated Razorpay webhook.
 * Sends the Razorpay-native envelope, which is the shape the real gateway posts —
 * every caller must go through here so the payload shape cannot drift again.
 */
export function fireWebhook(event: WebhookEvent | string, invoiceId: number): Promise<WebhookResult> {
  return apiPost<WebhookResult>("/api/webhooks/razorpay", {
    event,
    payload: {
      invoice: {
        entity: {
          id: `inv_${invoiceId}`,
          receipt: `rcpt_${invoiceId}`,
          status: event.includes("paid") ? "paid" : "issued",
        },
      },
    },
  });
}

export interface ClientReplyResult {
  status: string;
  invoice_id: number;
  intent: string | null;
  confidence: number | null;
  entities: Record<string, unknown> | null;
  old_status: string;
  new_status: string;
  audit_entries_written: number;
}

/** Submit a simulated client reply and get the structured classification back. */
export function sendClientReply(invoiceId: number, message: string): Promise<ClientReplyResult> {
  return apiPost<ClientReplyResult>(`/api/invoices/${invoiceId}/reply`, { message });
}
