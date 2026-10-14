import type { InvoiceStatus, Severity } from "../types";

export const STATUS_LABEL: Record<InvoiceStatus, string> = {
  ingested: "Recibida",
  processing: "Procesando",
  needs_review: "Requiere revisión",
  matched: "Conciliada",
  discrepancy: "Con diferencia",
  duplicate: "Duplicada",
  approved: "Aprobada",
  rejected: "Rechazada",
  registered: "Registrada"
};

export const STATUS_STYLE: Record<InvoiceStatus, string> = {
  ingested: "bg-slate-100 text-slate-700 border-slate-200",
  processing: "bg-sky-100 text-sky-700 border-sky-200",
  needs_review: "bg-amber-100 text-amber-800 border-amber-200",
  matched: "bg-emerald-100 text-emerald-700 border-emerald-200",
  discrepancy: "bg-orange-100 text-orange-700 border-orange-200",
  duplicate: "bg-rose-100 text-rose-700 border-rose-200",
  approved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  rejected: "bg-slate-200 text-slate-600 border-slate-300",
  registered: "bg-indigo-100 text-indigo-700 border-indigo-200"
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Info",
  warning: "Atención",
  critical: "Crítico"
};

export const STEP_STYLE: Record<string, string> = {
  pending: "text-slate-400",
  running: "text-sky-600",
  done: "text-emerald-600",
  warning: "text-amber-600",
  error: "text-rose-600"
};

export const MODEL_LABEL: Record<string, string> = {
  small: "modelo chico",
  reasoning: "razonamiento",
  none: "sin modelo"
};

export function isOpen(status: InvoiceStatus): boolean {
  return ["ingested", "processing", "needs_review", "matched", "discrepancy", "duplicate"].includes(
    status
  );
}
