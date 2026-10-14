export type InvoiceStatus =
  | "ingested"
  | "processing"
  | "needs_review"
  | "matched"
  | "discrepancy"
  | "duplicate"
  | "approved"
  | "rejected"
  | "registered";

export type Country = "MX" | "BR" | "CO" | "CL" | "PE" | "AR" | "EC";

export type DocFormat = "CFDI" | "NF-e" | "DIAN" | "DTE" | "SUNAT" | "PDF" | "NOTA_ENTREGA";

export type Severity = "info" | "warning" | "critical";

export interface Provider {
  name: string;
  taxId: string;
  country: Country;
}

export interface PurchaseOrder {
  number: string;
  amount: number;
  receivedAmount: number;
  currency: string;
}

export interface DeliveryNote {
  number: string;
  amount: number;
  receivedAmount: number;
  currency: string;
}

export interface Discrepancy {
  field: string;
  invoiceValue: string;
  expectedValue: string;
  severity: Severity;
  message: string;
}

export interface PipelineStep {
  key: string;
  label: string;
  status: "pending" | "running" | "done" | "warning" | "error";
  detail: string;
  model?: "small" | "reasoning" | "none";
  tokens?: number;
  durationMs?: number;
}

export interface FiscalCheck {
  verified: boolean;
  authority: string;
  reference: string;
  message: string;
}

export interface Invoice {
  id: string;
  folio: string;
  uuid: string;
  format: DocFormat;
  country: Country;
  provider: Provider;
  issueDate: string;
  dueDate: string;
  currency: string;
  subtotal: number;
  tax: number;
  total: number;
  status: InvoiceStatus;
  source: "email" | "carpeta" | "api";
  purchaseOrder?: PurchaseOrder;
  deliveryNote?: DeliveryNote;
  discrepancies: Discrepancy[];
  duplicateOf?: string;
  fiscal: FiscalCheck;
  pipeline: PipelineStep[];
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  note?: string;
}

export interface AuditEntry {
  id: string;
  invoiceId: string;
  action:
    | "ingested"
    | "classified"
    | "extracted"
    | "fiscal_verified"
    | "matched"
    | "delivery_note_matched"
    | "discrepancy_found"
    | "duplicate_found"
    | "approved"
    | "rejected"
    | "corrected"
    | "registered";
  actor: "agente" | "usuario" | "sistema";
  detail: string;
  at: string;
}

export interface AppSettings {
  country: Country;
  mode: "seguro" | "conectado";
  connectionAuthorized: boolean;
  autoApproveThreshold: number;
  requireFiscalVerification: boolean;
  erp: string;
  piiRedaction: boolean;
  promptInjectionGuard: boolean;
  modelRouting: boolean;
}
