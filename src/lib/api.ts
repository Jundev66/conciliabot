import type { AppSettings, AuditEntry, Invoice } from "../types";

const BASE = "/api";
const TOKEN_KEY = "conciliabot_token";

export function getApiToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setApiToken(token: string): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore storage errors (private mode)
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function authHeaders(): Record<string, string> {
  const token = getApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface SpreadsheetImportResult {
  filename?: string;
  headers: string[];
  count: number;
  rows: Record<string, number | string>[];
  errors: { row: number; field: string; message: string }[];
  truncated?: boolean;
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`No se pudo descargar (HTTP ${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadSpreadsheet(path: string, filename: string): Promise<void> {
  return downloadFile(path, filename);
}

export async function ingestFile(
  file: File,
  source = "carpeta",
  useBrowser = false,
  deliveryNote = ""
): Promise<Invoice> {
  const form = new FormData();
  form.append("file", file);
  form.append("source", source);
  form.append("use_browser", String(useBrowser));
  if (deliveryNote) form.append("delivery_note", deliveryNote);
  const res = await fetch(`${BASE}/ingest/file`, {
    method: "POST",
    headers: authHeaders(),
    body: form
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      // keep status
    }
    throw new Error(detail);
  }
  return (await res.json()) as Invoice;
}

export async function importSpreadsheet(file: File): Promise<SpreadsheetImportResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/spreadsheet/import`, {
    method: "POST",
    headers: authHeaders(),
    body: form
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      // keep the status message
    }
    throw new Error(detail);
  }
  return (await res.json()) as SpreadsheetImportResult;
}

export const api = {
  invoices: () => req<Invoice[]>("/invoices"),
  invoice: (id: string) => req<Invoice>(`/invoices/${id}`),
  audit: () => req<AuditEntry[]>("/audit"),
  settings: () => req<AppSettings>("/settings"),
  saveSettings: (settings: AppSettings) =>
    req<AppSettings>("/settings", { method: "PUT", body: JSON.stringify(settings) }),
  approve: (id: string, actor: string) =>
    req<Invoice>(`/invoices/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ actor })
    }),
  confirm: (id: string, actor: string) =>
    req<Invoice>(`/invoices/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({ actor })
    }),
  reject: (id: string, actor: string) =>
    req<Invoice>(`/invoices/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ actor })
    }),
  correct: (id: string, actor: string, note: string) =>
    req<Invoice>(`/invoices/${id}/correct`, {
      method: "POST",
      body: JSON.stringify({ actor, note })
    }),
  ingest: (text: string, filename: string, source: string, useBrowser = false, deliveryNote = "") =>
    req<Invoice>("/ingest", {
      method: "POST",
      body: JSON.stringify({ text, filename, source, useBrowser, deliveryNote })
    }),
  ingestFile,
  reset: () => req<{ status: string }>("/reset", { method: "POST" }),
  runEvals: () => req<EvalResult>("/evals/run", { method: "POST" }),
  toolsStatus: () => req<ToolsStatus>("/tools/status"),
  mcpTools: () => req<{ tools: McpTool[] }>("/tools/mcp/tools"),
  browserOrder: (number: string) => req<BrowserOrder>(`/tools/browser-order/${number}`),
  erpConfig: () => req<ErpConfig>("/erp/config"),
  saveErpConfig: (config: ErpConfig) =>
    req<ErpConfig>("/erp/config", { method: "PUT", body: JSON.stringify(config) }),
  testErp: (sampleNumber = "NE-5001") =>
    req<ProbeResult>("/erp/test", {
      method: "POST",
      body: JSON.stringify({ sampleNumber })
    }),
  downloadTemplate: () =>
    downloadSpreadsheet("/spreadsheet/template", "notas-de-entrega-ejemplo.xlsx"),
  downloadPdfTemplate: (number?: string) =>
    downloadFile(
      number ? `/documents/template-pdf?number=${encodeURIComponent(number)}` : "/documents/template-pdf",
      number ? `nota-de-entrega-${number}.pdf` : "nota-de-entrega-ejemplo.pdf"
    ),
  downloadInvoicePdf: (id: string) =>
    downloadFile(`/invoices/${id}/pdf`, `comprobante-${id}.pdf`),
  downloadRecords: () =>
    downloadSpreadsheet("/spreadsheet/export", "conciliabot-registros.xlsx"),
  importSpreadsheet
};

export interface CorebizConfig {
  baseUrl: string;
  apiKey: string;
  tenantId: string;
  tokenHeader: string;
  tokenPrefix: string;
  recordsPath: string;
}

export interface ErpConfig {
  provider: string;
  corebiz: CorebizConfig;
}

export interface ProbeStep {
  key: string;
  status: string;
  detail: string;
}

export interface ProbeResult {
  ok: boolean;
  provider: string;
  mode?: string;
  steps: ProbeStep[];
  sample?: Record<string, unknown>;
  preview?: string;
}

export interface McpTool {
  name: string;
  description: string;
}

export interface ToolsStatus {
  erp: { backend: string; mcpEnabled: boolean };
  browser: { available: boolean; enabled: boolean };
}

export interface BrowserOrder {
  number: string | null;
  vendorTaxId: string | null;
  vendorName: string | null;
  amount: number | null;
  currency: string | null;
  receivedAmount: number | null;
  text: string;
  source_url: string;
}

export interface EvalResult {
  cases: {
    id: string;
    expected_status: string;
    actual_status: string;
    ok: boolean;
    status_ok: boolean;
    format_ok: boolean;
    fiscal_ok: boolean;
    discrepancy_ok: boolean;
    trajectory_ok: boolean;
  }[];
  metrics: Record<string, number>;
  thresholds: Record<string, number>;
  passed: boolean;
  case_count: number;
}
